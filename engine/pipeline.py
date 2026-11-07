"""Kundalik skaner: ma'lumot → tahlil → kuzatuv → virtual portfel → musobaqa → o'rganish → JSON.

Ishga tushirish:  python -m engine.pipeline            (haqiqiy ma'lumot, yfinance)
                  python -m engine.pipeline --demo     (sun'iy ma'lumot, internetsiz)
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

from . import config as C
from . import portfolio as PF
from .data import read_json, write_json
from .features import build, earnings_soon, mid_base_mask, mid_entry_mask, mid_exit_reason
from .fundamentals import sector_percentiles
from .market import panel, regime_series
from .scoring import STRATEGY_INFO, layers, screen, total
from .signals import explain_last, scan

FUND_KEYS = ["roe", "net_margin", "op_margin", "gross_margin", "pe", "pb", "ps", "pfcf", "rev_3y", "eps_3y"]


def _f(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


# ── Ma'lumot yuklash ─────────────────────────────────────────────────────────
def load(demo: bool):
    from .data import fetch_earnings_and_dividends, fetch_universe, load_cached_prices, load_snapshot
    if demo:
        from . import demo as D
        uni, src = load_snapshot()
        tickers = list(uni["ticker"])
        prices, fund, earn, divs = D.make(tickers)
        return tickers, prices, fund, earn, divs, src + " (DEMO narxlar)"
    uni, src = fetch_universe()
    tickers = list(uni["yf"])
    extra = C.BENCHMARKS + list(C.SECTOR_ETFS) + [t for t in C.DJIA if t not in tickers]
    prices = load_cached_prices(tickers + extra)
    fund = read_json(C.STATE / "fundamentals.json", {})
    earn = read_json(C.STATE / "earnings.json", {})
    divs = read_json(C.STATE / "dividends.json", {})
    stale = [t for t in tickers if t not in earn or (earn.get("_fetched", {}).get(t, "") < (date.today() - pd.Timedelta(days=7)).isoformat())]
    if stale:
        e2, d2 = fetch_earnings_and_dividends(stale[:90])
        earn.update(e2)
        divs.update(d2)
        earn.setdefault("_fetched", {}).update({t: date.today().isoformat() for t in stale[:90]})
        write_json(C.STATE / "earnings.json", earn)
        write_json(C.STATE / "dividends.json", divs)
    from .fundamentals import refresh
    fund = refresh(fund, tickers, prices, divs)
    write_json(C.STATE / "fundamentals.json", fund)
    return tickers, prices, fund, earn, divs, src


# ── Bozor qoidalari (o'tgan kunlar uchun ham) ────────────────────────────────
def market_day(reg: pd.Series, vix: pd.Series, i: int) -> dict:
    r, v = reg.iat[i], vix.iat[i]
    allow, mult = True, 1.0
    if r == "red" or (pd.notna(v) and v >= C.VIX_HIGH):
        allow = False
    if r == "yellow":
        mult *= 0.5
    if pd.notna(v) and C.VIX_ELEVATED <= v < C.VIX_HIGH:
        mult *= 0.5
    return {"allow_buys": allow, "risk_mult": mult}


def learn(trades: list[dict]) -> dict:
    """Xatolardan o'rganish: kirish paytidagi belgilar bo'yicha natijalar va TAKLIFLAR.
    Dastur o'zi o'zgartirmaydi — taklifni foydalanuvchi tasdiqlaydi (config.py da yangi versiya)."""
    out = {"n": len(trades), "groups": [], "proposals": [], "errors": {}}
    if not trades:
        return out
    df = pd.DataFrame([{**{"r": t["r"], "why": t["why"], "kind": t["kind"]}, **t.get("flags", {})} for t in trades])
    out["errors"] = {
        "stop_gap": int((df["r"] < -1.25).sum()),
        "time_exit_loss": int(((df["why"] == "vaqt chegarasi") & (df["r"] < 0)).sum()),
        "watch_exit": int(df["why"].astype(str).str.startswith("kuzatuvdan").sum()),
    }
    for col in [c for c in df.columns if c not in ("r", "why")]:
        for val, g in df.groupby(col):
            out["groups"].append({"flag": col, "value": str(val), "n": int(len(g)), "exp": float(g["r"].mean()),
                                  "win": float((g["r"] > 0).mean())})
        vals = df.groupby(col)["r"].agg(["mean", "count"])
        if len(vals) >= 2 and vals["count"].min() >= C.LEARN["min_trades"]:
            best, worst = vals["mean"].idxmax(), vals["mean"].idxmin()
            diff = vals.loc[best, "mean"] - vals.loc[worst, "mean"]
            if diff >= C.LEARN["min_diff_r"]:
                out["proposals"].append({
                    "flag": col, "better": str(best), "worse": str(worst), "diff_r": round(float(diff), 3),
                    "text": f"'{col}' = {worst} bo'lgan savdolar o'rtacha {vals.loc[worst, 'mean']:.2f}R, "
                            f"{best} bo'lganlar {vals.loc[best, 'mean']:.2f}R berdi (har birida ≥{C.LEARN['min_trades']} savdo). "
                            f"Taklif: {worst} holatida kirishni cheklash. Tasdiqlansa — yangi qoidalar versiyasi, eski versiya bilan parallel sinaladi."})
    return out


def _chart(d: pd.DataFrame) -> dict:
    x = d.iloc[-C.CHART_DAYS:]
    r = lambda s: [None if pd.isna(v) else round(float(v), 4) for v in s]  # noqa: E731
    return {"t": [i.date().isoformat() for i in x.index], "o": r(x["open"]), "h": r(x["high"]), "l": r(x["low"]),
            "c": r(x["close"]), "v": [int(v) if pd.notna(v) else 0 for v in x["volume"]],
            "ema20": r(x["ema20"]), "ema50": r(x["ema50"]), "sma150": r(x["sma150"]), "sma200": r(x["sma200"])}


def expected_last_day(now: pd.Timestamp | None = None) -> pd.Timestamp:
    """Hozir mavjud bo'lishi kerak bo'lgan oxirgi yopilgan savdo kuni (bayramlarsiz, faqat ish kunlari)."""
    now = now if now is not None else pd.Timestamp.now(tz=C.TZ)
    d = now.tz_localize(None).normalize()
    if now.hour * 60 + now.minute < 16 * 60 + 15:
        d -= pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d -= pd.Timedelta(days=1)
    return d


def _check_freshness(prices: dict) -> None:
    q = prices.get(C.REGIME["index"])
    if q is None or q.empty:
        return
    exp, last = expected_last_day(), q.index[-1]
    if last < exp:
        print(f"[ogohlantirish] {C.REGIME['index']} oxirgi sham {last.date()}, kutilgan {exp.date()}. "
              "Yahoo hali e'lon qilmagan yoki bayram kuni — keyingi ishda to'g'rilanadi.")


def run(demo: bool = False, publish_dir=C.PUBLIC, warmup_days: int | None = None) -> dict:
    if demo:   # demo holati haqiqiy state/ papkasini ifloslamasligi uchun alohida joyda
        C.STATE = C.ROOT / ".demo-state"
    tickers, prices, fund, earn, divs, src = load(demo)
    if not demo:
        _check_freshness(prices)
    sectors = {t: (fund.get(t) or {}).get("sector", "") for t in tickers}
    F = build(prices, tickers, sectors)
    idx = F["index"]
    today_i = len(idx) - 1
    today = idx[today_i].date().isoformat()
    reg = regime_series(prices[C.REGIME["index"]])["regime"].reindex(idx)
    vix = prices["^VIX"]["close"].reindex(idx).ffill() if "^VIX" in prices else pd.Series(np.nan, index=idx)
    mkt = panel(prices)
    spct = sector_percentiles({t: fund[t] for t in F["ind"] if t in fund}, FUND_KEYS)
    universe = set(F["ind"])

    # signallar: butun tarix (o'tkazib yuborilgan kunlar uchun ham)
    sig_by_day: dict[int, list] = {}
    last_sig: dict[str, dict] = {}
    for t, d in F["ind"].items():
        s = scan(d, start=max(260, len(d) - 300))
        for r in s.itertuples():
            i = idx.get_loc(r.date) if r.date in idx else None
            if i is None:
                continue
            sig_by_day.setdefault(i, []).append({"ticker": t, "kind": r.kind, "stop": r.stop, "target": r.target})
            last_sig[t] = {"date": r.date.date().isoformat(), "kind": r.kind}

    # ── kuzatuv ro'yxati + virtual portfel (o'tkazib yuborilgan kunlarni ketma-ket) ──
    W = read_json(C.STATE / "watchlist.json", {"mid": {}, "long": {}, "last_date": None})
    book = read_json(C.STATE / "portfolio.json", None) or PF.new_state()
    hist_path = C.STATE / "watch_history.jsonl"
    new_hist: list[dict] = []
    mask = mid_entry_mask(F)
    base_mask = mid_base_mask(F)
    last_done = W.get("last_date")
    warm = (250 if demo else 0) if warmup_days is None else warmup_days
    start_i = today_i - warm if last_done is None else max(today_i - 30, int(np.searchsorted(idx.values, np.datetime64(last_done), side="right")))
    core = C.CORE_TICKER
    core_px = prices.get(core)
    for i in range(start_i, today_i + 1):
        ds = idx[i].date().isoformat()
        exits: dict[str, str] = {}
        for t in list(W["mid"]):
            why = "Halollik ro'yxatidan chiqdi" if t not in universe else mid_exit_reason(F, i, t)
            if why:
                w = W["mid"].pop(t)
                px = F["close"][t].iat[i] if t in universe else None
                new_hist.append({"ticker": t, "profile": "mid", "entered": w["entered"], "exited": ds,
                                 "reason_in": w["reason"], "reason_out": why, "price_in": w["price"], "price_out": _f(px),
                                 "ret": _f(px / w["price"] - 1) if px and w["price"] else None})
                exits[t] = why
        for t in universe:
            if t not in W["mid"] and bool(mask[t].iat[i]):
                ep = bool(F["ep"][t].iat[i])
                rs, fh = F["rs_pct"][t].iat[i], F["from_high"][t].iat[i]
                main_rule = bool(base_mask[t].iat[i])
                W["mid"][t] = {"entered": ds, "price": _f(F["close"][t].iat[i]),
                               "reason": f"Bosqich 2, nisbiy kuch {rs:.0f}, cho'qqidan {fh * 100:.0f}% pastda, sektor kuchli"
                               + (" + katalizator (EP)" if ep else "") if main_rule else
                               f"Katalizator (EP): katta hajmli gap, nisbiy kuch {rs:.0f}, cho'qqidan {fh * 100:.0f}% pastda"}
        cands = []
        for s in sig_by_day.get(i, []):
            t = s["ticker"]
            if t in W["mid"]:
                cands.append({**s, "score": _f(F["rs_pct"][t].iat[i]) or 0,
                              "flags": {"rejim": reg.iat[i], "vix": "yuqori" if (vix.iat[i] or 0) >= C.VIX_ELEVATED else "normal",
                                        "sektor_kuchli": bool(F["sector_top"][t].iat[i]), "ep": bool(F["ep"][t].iat[i]),
                                        "rs": "80+" if (F["rs_pct"][t].iat[i] or 0) >= 80 else "70-80"}})
        if not book["equity"] or book["equity"][-1][0] < ds:
            cc = core_px["close"].reindex(idx).iat[i] if core_px is not None else None
            PF.step(book, F, i, cands, market_day(reg, vix, i), sectors, earn, exits, _f(cc))
        W["last_date"] = ds
    # uzoq muddat ro'yxati (fundamental — faqat bugun)
    for t in list(W["long"]):
        m = fund.get(t, {})
        c = F["close"][t].iat[today_i] if t in universe else None
        s40 = F["sma40w"][t].iat[today_i] if t in universe else None
        why = None
        if t not in universe:
            why = "Halollik ro'yxatidan chiqdi"
        elif m.get("halal_ok") is False:
            why = "Halollik koeffitsiyentlari chegaradan oshdi"
        elif (m.get("piotroski") or 9) <= C.WATCH_LONG_EXIT["piotroski_max"]:
            why = f"Piotroski {m.get('piotroski'):.0f} ga tushdi"
        elif (_f(m.get("fcf_ttm")) or 1) < 0:
            why = "Erkin pul oqimi manfiy bo'ldi"
        elif c and s40 and c < s40 * (1 - C.WATCH_LONG_EXIT["below_sma200w_pct"]):
            why = "Narx 40 haftalik o'rtachadan 10% dan ko'proq pastda (haftalik Stage 4)"
        if why:
            w = W["long"].pop(t)
            new_hist.append({"ticker": t, "profile": "long", "entered": w["entered"], "exited": today,
                             "reason_in": w["reason"], "reason_out": why, "price_in": w["price"], "price_out": _f(c),
                             "ret": _f(c / w["price"] - 1) if c and w["price"] else None})
    e = C.WATCH_LONG_ENTRY
    for t in universe:
        m = fund.get(t)
        if not m or t in W["long"]:
            continue
        c, s40 = F["close"][t].iat[today_i], F["sma40w"][t].iat[today_i]
        if (m.get("halal_ok") is not False and (m.get("piotroski") or 0) >= e["piotroski_min"]
                and (m.get("roe") or 0) >= e["roe_min"] and (_f(m.get("de")) is not None and m["de"] <= e["de_max"])
                and (_f(m.get("fcf_ttm", m.get("fcf_margin"))) or 0) > 0 and pd.notna(s40) and c > s40):
            W["long"][t] = {"entered": today, "price": _f(c),
                            "reason": f"Piotroski {m['piotroski']:.0f}, ROE {m['roe'] * 100:.0f}%, D/E {m['de']:.2f}, FCF musbat, 40 haftalik o'rtacha ustida"}
    if new_hist:
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        with hist_path.open("a") as fh:
            for h in new_hist:
                fh.write(json.dumps(h, ensure_ascii=False) + "\n")

    # ── bugungi tahlil, ballar, kartalar ──
    ready = {s["ticker"]: s for s in sig_by_day.get(today_i, [])}
    rows, cards = [], {}
    close_today = {t: _f(F["close"][t].iat[today_i]) for t in universe}
    for t in universe:
        L = layers(t, F, today_i, fund.get(t), spct.get(t), True)
        m = fund.get(t, {})
        nxt = next((x for x in earn.get(t, []) if x > today), None)
        mid, lng = total(L, "mid"), total(L, "long")
        status_mid = "tayyor" if t in W["mid"] and t in ready and mkt["allow_buys"] and not earnings_soon(earn.get(t), idx[today_i], C.TRADE["earnings_block_days"]) \
            else "kuzatuvda" if t in W["mid"] else None
        yrs = int(m.get("div_years_up") or 0)
        tags = (["Qirol"] if yrs >= 50 else ["Aristokrat"] if yrs >= 25 else []) + (["EP"] if F["ep"][t].iat[today_i] else [])
        row = {"t": t, "name": m.get("name", t), "sector": m.get("sector", ""), "price": close_today[t],
               "r1d": _f(F["close"][t].pct_change().iat[today_i]), "r21": _f(F["close"][t].pct_change(21).iat[today_i]),
               "rs": _f(F["rs_pct"][t].iat[today_i]), "fh": _f(F["from_high"][t].iat[today_i]),
               "stage": _f(F["stage"][t].iat[today_i]), "mid": mid, "long": lng,
               "L": {k: v["score"] for k, v in L.items() if k != "halal"}, "halal": L["halal"]["ok"],
               "liquid": bool(F["liquid"][t].iat[today_i]), "signal": ready.get(t, {}).get("kind"),
               "watch_mid": status_mid, "watch_long": t in W["long"], "earn": nxt, "tags": tags,
               "last_signal": last_sig.get(t)}
        rows.append(row)
        ex = explain_last(F["ind"][t])
        plan = None
        if t in ready:
            s = ready[t]
            c = close_today[t]
            R = c - s["stop"]
            eq = book["equity"][-1][1] if book["equity"] else C.PORTFOLIO["start_equity"]
            risk_d = eq * C.PORTFOLIO["risk_per_trade"] * book.get("protection", {}).get("risk_mult", 1.0)
            sh = max(0, min(math.floor(risk_d / R) if R > 0 else 0, math.floor(eq * C.PORTFOLIO["max_position_pct"] / c)))
            plan = {"kind": s["kind"], "entry": c, "stop": s["stop"], "target": s["target"],
                    "rr": (s["target"] - c) / R if R > 0 else None, "shares_per_10k": sh, "risk_usd_per_10k": round(sh * R, 2)}
        sig_hist = [{"d": idx[i].date().isoformat(), "k": s["kind"]} for i in range(max(0, today_i - C.CHART_DAYS), today_i + 1)
                    for s in sig_by_day.get(i, []) if s["ticker"] == t]
        cards[t] = {"t": t, "row": row, "layers": L, "explain": ex, "plan": plan, "fund": {k: v for k, v in m.items()},
                    "spct": spct.get(t, {}), "chart": _chart(F["ind"][t]), "signals": sig_hist,
                    "watch": {"mid": W["mid"].get(t), "long": W["long"].get(t)}, "earnings": earn.get(t, [])[-8:]}
    rows.sort(key=lambda r: -(r["mid"] or 0))

    # ── strategiyalar musobaqasi ──
    comp = read_json(C.STATE / "competition.json", {})
    tech = {t: {"trend_ok": bool(F["close"][t].iat[today_i] > F["ind"][t]["sma200"].iat[-1]),
                "rs_pct": _f(F["rs_pct"][t].iat[today_i]), "from_high": _f(F["from_high"][t].iat[today_i]),
                "market_ok": mkt["regime"] != "red"} for t in universe}
    score_of = {r["t"]: (r["long"] or 0) for r in rows}
    comp_close = {**close_today}
    for t in (C.CORE_TICKER, *C.DJIA):
        if t in prices:
            comp_close[t] = _f(prices[t]["close"].iat[-1])
    picks: dict[str, list] = {}
    for name in ("stable_growth", "hyper_growth", "canslim", "up_value", "quality_dcf", "healthy_cash", "aristocrats"):
        ok = [t for t in universe if fund.get(t) and fund[t].get("halal_ok") is not False and screen(name, fund[t], tech[t])]
        picks[name] = sorted(ok, key=lambda t: -score_of.get(t, 0))
    dj = [t for t in C.DJIA if t in universe]
    picks["dogs_of_dow"] = sorted(dj, key=lambda t: -(fund.get(t, {}).get("div_yield") or 0))[:10]
    picks["long_watch"] = sorted(W["long"], key=lambda t: -score_of.get(t, 0))
    picks["SPUS"] = [C.CORE_TICKER] if C.CORE_TICKER in comp_close else []
    day = idx[today_i]
    for name, pk in picks.items():
        s = comp.get(name) or PF.comp_new(name)
        PF.comp_step(s, day, comp_close, pk, yearly=(name == "dogs_of_dow"))
        s["candidates"] = len(pk)
        comp[name] = s
    sat = {"name": "signals", "equity": [[e_[0], e_[1]] for e_ in book["equity"]]}

    # ── natijalarni yozish ──
    learn_rep = learn(book["trades"])
    write_json(C.STATE / "watchlist.json", W)
    write_json(C.STATE / "portfolio.json", book)
    write_json(C.STATE / "competition.json", comp)
    write_json(C.STATE / "learn.json", learn_rep)
    summary = {"date": today, "regime": mkt["regime"], "vix": mkt["vix"], "mid_watch": len(W["mid"]),
               "long_watch": len(W["long"]), "ready": sorted(ready), "equity": book["equity"][-1][1] if book["equity"] else None}
    write_json(C.STATE / "daily" / f"{today}.json", summary)

    pub = publish_dir
    if pub.exists():
        shutil.rmtree(pub)
    (pub / "cards").mkdir(parents=True, exist_ok=True)
    hist = []
    if hist_path.exists():
        hist = [json.loads(x) for x in hist_path.read_text().splitlines() if x.strip()]
    q = prices[C.REGIME["index"]].iloc[-260:]
    rs_ = regime_series(prices[C.REGIME["index"]]).iloc[-260:]
    mkt["history"] = {"t": [d.date().isoformat() for d in q.index], "c": [round(float(x), 2) for x in q["close"]],
                      "sma200": [None if pd.isna(x) else round(float(x), 2) for x in rs_["sma200"]],
                      "regime": list(rs_["regime"])}
    write_json(pub / "meta.json", {"date": today, "generated": datetime.now(timezone.utc).isoformat(), "demo": demo,
                                   "rules_version": C.RULES_VERSION, "universe_source": src, "universe": len(universe),
                                   "fund_coverage": sum(1 for t in universe if t in fund)})
    write_json(pub / "market.json", mkt)
    write_json(pub / "scores.json", rows)
    for t, cd in cards.items():
        write_json(pub / "cards" / f"{t}.json", cd)
    write_json(pub / "watchlist.json", {"mid": W["mid"], "long": W["long"], "history": hist[-500:]})
    p = book["params"]
    open_pos = []
    for x in book["positions"]:
        c = close_today.get(x["ticker"])
        open_pos.append({**x, "price": c, "r_now": (c - x["entry"]) / x["R"] if c and x["R"] else None})
    write_json(pub / "portfolio.json", {
        "params": p, "equity": book["equity"], "positions": open_pos, "pending": book["pending"],
        "trades": book["trades"][-300:], "stats": PF.stats(book["trades"], book["equity"]),
        "protection": book.get("protection", {}), "core_shares": book["core_shares"], "started": book["started"],
        "log": book["log"][-50:]})
    write_json(pub / "competition.json", {
        "strategies": [{"key": k, "title": STRATEGY_INFO[k][0], "rule": STRATEGY_INFO[k][1],
                        "equity": v["equity"], "holdings": v["picks"], "note": v.get("note", ""),
                        "candidates": v.get("candidates", 0)} for k, v in comp.items()]
        + [{"key": "signals", "title": STRATEGY_INFO["signals"][0], "rule": STRATEGY_INFO["signals"][1],
            "equity": sat["equity"], "holdings": [x["ticker"] for x in book["positions"]], "note": "", "candidates": None}]})
    write_json(pub / "learn.json", learn_rep)
    bt = read_json(C.STATE / "backtest" / "latest.json", None)
    if bt:
        write_json(pub / "backtest.json", bt)
    try:
        from .supa import push
        push(summary, rows, W, book, learn_rep)
    except Exception as ex:  # noqa: BLE001
        print(f"[ogohlantirish] Supabase: {ex}")
    print(f"Tayyor: {today} · rejim {mkt['regime']} · o'rta kuzatuv {len(W['mid'])} · uzoq {len(W['long'])} · "
          f"bugun tayyor {len(ready)} · portfel {summary['equity']}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    run(demo=a.demo)
