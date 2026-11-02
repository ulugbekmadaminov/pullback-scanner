"""Virtual portfel: yadro (SPUS) + yo'ldosh (faol signallar), depozit himoyasi qavatlari bilan.

Bitta `Book` kundalik skanerda ham, backtestda ham ishlaydi — qoidalar bir xil bo'lishi uchun.
Holat oddiy dict (JSON'ga yoziladi va git'da saqlanadi).
"""
from __future__ import annotations

import math

import pandas as pd

from . import config as C
from .features import corr_cluster_ok, earnings_soon

T = C.TRADE


def commission(shares: float) -> float:
    return max(T["commission_min"], T["commission_per_share"] * shares) if shares > 0 else 0.0


def new_state(params: dict | None = None) -> dict:
    p = {**C.PORTFOLIO, **(params or {})}
    return {"params": p, "cash": p["start_equity"], "core_shares": 0.0, "positions": [], "pending": [],
            "trades": [], "equity": [], "peak": p["start_equity"], "rules_version": C.RULES_VERSION,
            "started": None, "log": []}


def _bar(F: dict, t: str, i: int):
    return (F["open"][t].iat[i], F["high"][t].iat[i], F["low"][t].iat[i], F["close"][t].iat[i])


def equity_of(s: dict, F: dict, i: int, core_close: float | None) -> tuple[float, float, float]:
    core = s["core_shares"] * (core_close or 0.0)
    sat = 0.0
    for p in s["positions"]:
        c = F["close"][p["ticker"]].iat[i]
        sat += p["shares"] * (c if pd.notna(c) else p["entry"])
    return s["cash"] + core + sat, core, sat


def step(s: dict, F: dict, i: int, candidates: list[dict], market: dict, sectors: dict,
         earnings: dict, exits: dict | None = None, core_close: float | None = None,
         core_open: float | None = None) -> None:
    """Bitta savdo kuni. Tartib: (1) kechagi buyurtmalar ochilishda to'ldiriladi,
    (2) ochiq pozitsiyalar stop/maqsad/vaqt/kuzatuvdan chiqish bo'yicha yopiladi,
    (3) kapital va cho'qqidan pasayish hisoblanadi, (4) ertangi buyurtmalar tuziladi."""
    p = s["params"]
    day = F["index"][i]
    ds = day.date().isoformat()
    if s["started"] is None:
        s["started"] = ds
        if p["core_pct"] > 0 and core_close:
            amt = p["start_equity"] * p["core_pct"]
            sh = math.floor(amt / core_close * 1000) / 1000
            s["core_shares"] = sh
            s["cash"] -= sh * core_close + commission(sh)
    # (1) to'ldirish
    still = []
    for o in s["pending"]:
        t = o["ticker"]
        op = F["open"][t].iat[i]
        if pd.isna(op):
            continue
        fill = op * (1 + T["slippage"])
        if fill <= o["stop"] or fill >= o["target"]:
            s["log"].append({"d": ds, "t": t, "e": "bekor", "why": "ochilish narxi stop/maqsaddan o'tib ketdi"})
            continue
        cost = o["shares"] * fill + commission(o["shares"])
        if cost > s["cash"]:
            s["log"].append({"d": ds, "t": t, "e": "bekor", "why": "naqd yetmadi"})
            continue
        s["cash"] -= cost
        s["positions"].append({**o, "entry": fill, "entry_date": ds, "R": fill - o["stop"], "days": 0})
    s["pending"] = still
    # (2) yopish
    keep = []
    for pos in s["positions"]:
        t = pos["ticker"]
        o_, h, l, c = _bar(F, t, i)
        if pd.isna(c):
            keep.append(pos)
            continue
        pos["days"] += 1 if pos["entry_date"] != ds else 0
        px, why = None, None
        if l <= pos["stop"]:
            px = min(o_, pos["stop"]) if o_ < pos["stop"] else pos["stop"]
            px *= 1 - T["stop_slippage"]
            why = "stop"
        elif h >= pos["target"] and pos["entry_date"] != ds:
            px = max(o_, pos["target"]) if o_ > pos["target"] else pos["target"]
            why = "maqsad"
        elif pos["days"] >= T["max_hold_days"]:
            px, why = c, "vaqt chegarasi"
        elif exits and t in exits:
            px, why = c, "kuzatuvdan chiqdi: " + exits[t]
        if px is None:
            keep.append(pos)
            continue
        px *= 1 - T["slippage"]
        proceeds = pos["shares"] * px - commission(pos["shares"])
        s["cash"] += proceeds
        pnl = proceeds - pos["shares"] * pos["entry"] - commission(pos["shares"])
        r_mult = pnl / (pos["shares"] * pos["R"]) if pos["R"] > 0 else 0.0
        s["trades"].append({"ticker": t, "kind": pos["kind"], "entry_date": pos["entry_date"], "entry": pos["entry"],
                            "exit_date": ds, "exit": px, "shares": pos["shares"], "stop": pos["stop"],
                            "target": pos["target"], "r": round(r_mult, 3), "pnl": round(pnl, 2), "why": why,
                            "days": pos["days"], "sector": pos.get("sector"), "flags": pos.get("flags", {})})
    s["positions"] = keep
    # (3) kapital
    eq, core, sat = equity_of(s, F, i, core_close)
    s["peak"] = max(s["peak"], eq)
    dd = eq / s["peak"] - 1
    s["equity"].append([ds, round(eq, 2), round(core, 2), round(sat, 2), round(s["cash"], 2)])
    # (4) yangi buyurtmalar
    brake = 1.0
    status = "normal"
    if dd <= p["dd_stop_buys"]:
        status = "to'xtatilgan"
    elif dd <= p["dd_half_risk"]:
        brake, status = 0.5, "yarim risk"
    s["protection"] = {"dd": round(dd, 4), "status": status, "market_ok": market.get("allow_buys", True),
                       "risk_mult": market.get("risk_mult", 1.0) * brake}
    if status == "to'xtatilgan" or not market.get("allow_buys", True):
        return
    held = [x["ticker"] for x in s["positions"]]
    open_risk = sum(x["shares"] * max(x["entry"] - x["stop"], 0) for x in s["positions"])
    sat_equity = eq - core
    reserve = sat_equity * p["satellite_cash_min"]
    avail = s["cash"] - reserve
    for cnd in sorted(candidates, key=lambda x: -(x.get("score") or 0)):
        t = cnd["ticker"]
        if len(held) >= p["max_positions"]:
            break
        if t in held:
            continue
        sec = sectors.get(t, "")
        if sum(1 for h_ in held if sectors.get(h_, "") == sec) >= p["max_per_sector"]:
            continue
        if earnings_soon(earnings.get(t), day, T["earnings_block_days"]):
            continue
        if not corr_cluster_ok(F, i, t, held, p["max_per_cluster"], p["cluster_corr"]):
            continue
        c = F["close"][t].iat[i]
        R = c - cnd["stop"]
        if not (R > 0) or pd.isna(c):
            continue
        risk_d = eq * p["risk_per_trade"] * s["protection"]["risk_mult"]
        if open_risk + risk_d > eq * p["max_open_risk"]:
            break
        sh = math.floor(risk_d / R)
        sh = min(sh, math.floor(eq * p["max_position_pct"] / c))
        cost = sh * c * (1 + T["slippage"]) + commission(sh)
        if sh <= 0 or cost > avail:
            continue
        avail -= cost
        open_risk += sh * R
        held.append(t)
        s["pending"].append({"ticker": t, "kind": cnd["kind"], "stop": cnd["stop"], "target": cnd["target"],
                             "shares": sh, "planned": ds, "sector": sec, "flags": cnd.get("flags", {})})


def stats(trades: list[dict], equity: list[list]) -> dict:
    """Natija ko'rsatkichlari (1:3 maqolasidagi ro'yxat)."""
    n = len(trades)
    out = {"trades": n}
    if equity:
        e = pd.Series([x[1] for x in equity])
        out["max_dd"] = float((e / e.cummax() - 1).min())
        out["ret"] = float(e.iloc[-1] / e.iloc[0] - 1)
    if not n:
        return out
    r = pd.Series([t["r"] for t in trades])
    wins, losses = r[r > 0], r[r <= 0]
    streak = cur = 0
    for x in r:
        cur = cur + 1 if x <= 0 else 0
        streak = max(streak, cur)
    out.update(winrate=float((r > 0).mean()), avg_win=float(wins.mean()) if len(wins) else 0.0,
               avg_loss=float(losses.mean()) if len(losses) else 0.0, expectancy=float(r.mean()),
               profit_factor=float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else None,
               max_losing_streak=int(streak), avg_days=float(pd.Series([t["days"] for t in trades]).mean()))
    return out


# ── Strategiyalar musobaqasi: oylik teng ulushli portfellar ──────────────────
def comp_new(name: str) -> dict:
    return {"name": name, "cash": C.COMPETITION["start_equity"], "holdings": {}, "equity": [],
            "last_rebalance": None, "picks": [], "note": ""}


def comp_step(s: dict, day: pd.Timestamp, close: dict, picks: list[str] | None, yearly: bool = False) -> None:
    """picks berilsa va yangi oy (yoki yil) boshlangan bo'lsa — qayta taqsimlanadi (yopilish narxida)."""
    ds = day.date().isoformat()
    lr = s["last_rebalance"]
    due = lr is None or (ds[:4] != lr[:4] if yearly else ds[:7] != lr[:7])
    if picks is not None and due:
        val = s["cash"] + sum(sh * close.get(t, 0) for t, sh in s["holdings"].items())
        for t, sh in s["holdings"].items():           # hammasini sotish
            s["cash"] += sh * close.get(t, 0) * (1 - T["slippage"]) - commission(sh)
        s["holdings"] = {}
        picks = [t for t in picks if close.get(t)][:C.COMPETITION["top_n"]]
        if picks:
            each = s["cash"] / len(picks)
            for t in picks:
                px = close[t] * (1 + T["slippage"])
                fee = max(T["commission_min"], T["commission_per_share"] * each / px)
                sh = math.floor((each - fee) / px * 1000) / 1000
                cost = sh * close[t] * (1 + T["slippage"]) + commission(sh)
                if sh > 0 and cost <= s["cash"]:
                    s["cash"] -= cost
                    s["holdings"][t] = sh
        s["last_rebalance"], s["picks"] = ds, picks
        s["note"] = "" if picks else "Bu oy mezonlarga mos aksiya topilmadi — naqd turibdi"
        _ = val
    eq = s["cash"] + sum(sh * close.get(t, 0) for t, sh in s["holdings"].items())
    if s["equity"] and s["equity"][-1][0] == ds:
        s["equity"][-1] = [ds, round(eq, 2)]
    else:
        s["equity"].append([ds, round(eq, 2)])
