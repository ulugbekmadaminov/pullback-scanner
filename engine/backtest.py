"""Backtest: kirish signallarida edge bormi? (1:3 maqolasi: avval edge isbotlanadi, keyin risk).

Himoyalar: faqat yopilgan shamlar, xarajatlar, vaqt bo'yicha 70/30 bo'linish, tasodifiy
kirishlar bilan taqqoslash, barcha variantlar jurnalga yoziladi.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config as C
from . import portfolio as PF
from .features import build, earnings_soon, mid_entry_mask
from .indicators import add_all
from .market import regime_series
from .signals import scan

T = C.TRADE


def simulate_trade(F: dict, t: str, i: int, stop: float, target: float) -> tuple[float, int, str] | None:
    """Signal i-kun yopilishida → kirish i+1 ochilishida. Natija: (R, kunlar, sabab) yoki None."""
    o, h, l, c = F["open"][t].values, F["high"][t].values, F["low"][t].values, F["close"][t].values
    n = len(o)
    if i + 1 >= n or not math.isfinite(o[i + 1]):
        return None
    entry = o[i + 1] * (1 + T["slippage"])
    if entry <= stop or entry >= target:
        return None
    R = entry - stop
    cost_r = (2 * T["commission_per_share"] * 100 + entry * T["slippage"] * 2) / (R * 100)   # 100 aksiyaga nisbatan
    for k in range(i + 1, min(n, i + 1 + T["max_hold_days"] + 1)):
        if l[k] <= stop:
            px = (min(o[k], stop) if o[k] < stop else stop) * (1 - T["stop_slippage"])
            return (px - entry) / R - cost_r, k - i, "stop"
        if h[k] >= target and k > i + 1:
            px = max(o[k], target) if o[k] > target else target
            return (px - entry) / R - cost_r, k - i, "maqsad"
    k = min(n - 1, i + T["max_hold_days"] + 1)
    return (c[k] - entry) / R - cost_r, k - i, "vaqt"


def _seg_stats(rs: list[float]) -> dict:
    if not rs:
        return {"n": 0}
    r = np.array(rs)
    w, ls = r[r > 0], r[r <= 0]
    return {"n": int(len(r)), "winrate": float((r > 0).mean()), "expectancy": float(r.mean()),
            "avg_win": float(w.mean()) if len(w) else 0.0, "avg_loss": float(ls.mean()) if len(ls) else 0.0,
            "profit_factor": float(w.sum() / -ls.sum()) if ls.sum() < 0 else None}


def random_baseline(F: dict, sig: pd.DataFrame, pool: list[tuple[str, int]], runs: int, seed: int) -> list[float]:
    """Har bir haqiqiy signal uchun tasodifiy (aksiya, kun) tanlanadi: stop masofasi ATR'da
    va maqsad R'da aynan o'sha signalnikidek. Natija — har bir yugurishning o'rtacha R'i."""
    rng = np.random.default_rng(seed)
    atr = F["atr"]
    plans = []
    for _, s in sig.iterrows():
        a = atr[s["ticker"]].iat[s["t"]]
        c = F["close"][s["ticker"]].iat[s["t"]]
        if not (a > 0):
            continue
        plans.append(((c - s["stop"]) / a, (s["target"] - c) / (c - s["stop"])))
    out = []
    if not plans or not pool:
        return out
    for _ in range(runs):
        rs = []
        for r_atr, rr in plans:
            t, i = pool[rng.integers(len(pool))]
            c, a = F["close"][t].iat[i], atr[t].iat[i]
            if not (a > 0 and c > 0):
                continue
            stop = c - r_atr * a
            res = simulate_trade(F, t, i, stop, c + rr * (c - stop))
            if res:
                rs.append(res[0])
        out.append(float(np.mean(rs)) if rs else 0.0)
    return out


def run(prices: dict, tickers: list[str], sectors: dict, earnings: dict, demo: bool = False) -> dict:
    F = build(prices, tickers, sectors)
    idx = F["index"]
    q = prices[C.REGIME["index"]]
    reg = regime_series(q)["regime"].reindex(idx)
    vix = prices["^VIX"]["close"].reindex(idx).ffill() if "^VIX" in prices else pd.Series(15.0, index=idx)
    watch = mid_entry_mask(F)
    # signallar (har bir aksiya mustaqil)
    rows = []
    for t in F["ind"]:
        s = scan(F["ind"][t])
        if len(s):
            s["ticker"] = t
            s["t"] = s["date"].map(lambda d: idx.get_loc(d) if d in idx else -1)
            rows.append(s[s["t"] >= 0])
    sig = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["t", "date", "kind", "stop", "target", "ticker"])
    sig = sig[[not earnings_soon(earnings.get(r.ticker), r.date, T["earnings_block_days"]) for r in sig.itertuples()]] if len(sig) else sig
    split_i = int(len(idx) * C.BACKTEST["split"])
    split_date = idx[split_i].date().isoformat()
    liquid = F["liquid"]
    pool_all = [(t, i) for t in F["ind"] for i in np.flatnonzero(liquid[t].values) if 260 <= i < len(idx) - 45]

    variants = [
        ("signal", False, False), ("signal+rejim", True, False),
        ("signal+kuzatuv", False, True), ("signal+rejim+kuzatuv", True, True),
    ]
    report = {"generated": datetime.now(timezone.utc).isoformat(), "rules_version": C.RULES_VERSION, "demo": demo,
              "period": [idx[260].date().isoformat(), idx[-1].date().isoformat()], "split_date": split_date,
              "universe": len(F["ind"]), "survivorship_note": "Ro'yxat bugungi SPUS tarkibi — natija biroz optimistik",
              "variants": []}
    for name, use_regime, use_watch in variants:
        for kind in ("pullback", "breakout"):
            s = sig[sig["kind"] == kind]
            if use_regime:
                s = s[[reg.iat[i] in ("green", "yellow") and vix.iat[i] < C.VIX_HIGH for i in s["t"]]]
            if use_watch:
                s = s[[bool(watch[t].iat[i]) for t, i in zip(s["ticker"], s["t"])]]
            res = [(r.t, simulate_trade(F, r.ticker, r.t, r.stop, r.target)) for r in s.itertuples()]
            tr = [x[1][0] for x in res if x[1]]
            tr_tr = [x[1][0] for x in res if x[1] and x[0] < split_i]
            tr_te = [x[1][0] for x in res if x[1] and x[0] >= split_i]
            s_te = s[s["t"] >= split_i]
            pool_te = [p for p in pool_all if p[1] >= split_i]
            rnd = random_baseline(F, s_te, pool_te, C.BACKTEST["random_runs"] if not demo else 60, C.BACKTEST["seed"])
            te = _seg_stats(tr_te)
            pctl = float((np.array(rnd) < te.get("expectancy", -9)).mean() * 100) if rnd and te["n"] else None
            # portfel darajasida (yo'ldosh qoidalari bilan, yadrosiz)
            book = PF.new_state({"core_pct": 0.0, "satellite_pct": 1.0})
            by_day: dict[int, list] = {}
            for r in s.itertuples():
                by_day.setdefault(r.t, []).append({"ticker": r.ticker, "kind": kind, "stop": r.stop, "target": r.target,
                                                   "score": F["rs_pct"][r.ticker].iat[r.t]})
            for i in range(260, len(idx)):
                mk = {"allow_buys": (reg.iat[i] != "red" and vix.iat[i] < C.VIX_HIGH) if use_regime else True,
                      "risk_mult": 0.5 if use_regime and reg.iat[i] == "yellow" else 1.0}
                PF.step(book, F, i, by_day.get(i, []), mk, sectors, earnings)
            ptr = book["trades"]
            p_te = [x for x in ptr if x["entry_date"] >= split_date]
            p_tr = [x for x in ptr if x["entry_date"] < split_date]
            eq = book["equity"]
            pst = PF.stats(ptr, eq)
            d = C.BACKTEST["decision"]
            tr_exp = _seg_stats(tr_tr).get("expectancy")
            checks = [
                {"t": f"Tekshiruv qismida ≥{d['min_trades_test']} signal", "ok": te["n"] >= d["min_trades_test"], "v": te["n"]},
                {"t": f"Kutilma xarajatlardan keyin ≥ +{d['min_expectancy_r']}R", "ok": te.get("expectancy", -1) >= d["min_expectancy_r"], "v": te.get("expectancy")},
                {"t": f"Profit factor ≥ {d['min_profit_factor']}", "ok": (te.get("profit_factor") or 0) >= d["min_profit_factor"], "v": te.get("profit_factor")},
                {"t": f"Tasodifiy kirishlarning yuqori {100 - d['random_pct']}% ida", "ok": (pctl or 0) >= d["random_pct"], "v": pctl},
                {"t": f"Portfel maksimal pasayishi ≤ {d['max_dd'] * 100:.0f}%", "ok": pst.get("max_dd", -1) >= -d["max_dd"], "v": pst.get("max_dd")},
                {"t": "Tekshiruvdagi kutilma sozlashdagining kamida yarmi",
                 "ok": tr_exp is not None and te.get("expectancy") is not None and (tr_exp <= 0 or te["expectancy"] >= d["test_vs_train"] * tr_exp),
                 "v": tr_exp},
            ]
            verdict = "noaniq" if te["n"] < d["min_trades_test"] else ("davom" if all(c["ok"] for c in checks) else "to'xtash")
            weekly = [x for k, x in enumerate(eq) if k % 5 == 0 or k == len(eq) - 1]
            report["variants"].append({
                "variant": name, "kind": kind, "signals": int(len(s)),
                "signal_all": _seg_stats(tr), "signal_train": _seg_stats(tr_tr), "signal_test": te,
                "random": {"runs": len(rnd), "mean": float(np.mean(rnd)) if rnd else None,
                           "p95": float(np.percentile(rnd, 95)) if rnd else None, "percentile": pctl},
                "portfolio": pst, "portfolio_train": PF.stats(p_tr, []), "portfolio_test": PF.stats(p_te, []),
                "equity": [[x[0], x[1]] for x in weekly], "checks": checks, "verdict": verdict,
            })
    return report


def markdown(rep: dict) -> str:
    L = [f"# Backtest hisoboti", "",
         f"Davr: {rep['period'][0]} – {rep['period'][1]} · bo'linish: {rep['split_date']} · aksiyalar: {rep['universe']} · "
         f"qoidalar v{rep['rules_version']}" + (" · **DEMO ma'lumot**" if rep.get("demo") else ""), "",
         f"> {rep['survivorship_note']}", "",
         "| Variant | Tur | Signal (test) | Kutilma (test) | Winrate | PF | Tasodifiy foizlik | Portfel DD | Xulosa |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for v in rep["variants"]:
        te = v["signal_test"]
        f = lambda x, p=2: "—" if x is None else f"{x:.{p}f}"  # noqa: E731
        L.append(f"| {v['variant']} | {v['kind']} | {te.get('n', 0)} | {f(te.get('expectancy'))}R | "
                 f"{f((te.get('winrate') or 0) * 100, 0)}% | {f(te.get('profit_factor'))} | {f(v['random']['percentile'], 0)} | "
                 f"{f((v['portfolio'].get('max_dd') or 0) * 100, 1)}% | {v['verdict']} |")
    L += ["", "Xulosa: **davom** — 6 shartning hammasi bajarildi; **to'xtash** — kamida bittasi bajarilmadi; "
          "**noaniq** — tekshiruv qismida signal yetarli emas.", ""]
    return "\n".join(L)
