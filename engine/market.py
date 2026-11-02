"""Bozor paneli: rejim (Nasdaq tayanchlari + SMA200), risk ishtahasi, sektorlar reytingi, VIX."""
from __future__ import annotations

import math

import pandas as pd

from . import config as C
from .indicators import pivots, sma


def regime_series(qqq: pd.DataFrame) -> pd.DataFrame:
    """Har kun uchun rejim: green / yellow / red va sababi.

    Shart 1: yopilish > SMA200. Shart 2: oxirgi tasdiqlangan kunlik pivot tub ostida
    ketma-ket 2 kun yopilmagan. Ikkalasi bajarilsa — yashil, bittasi — sariq, hech biri — qizil.
    """
    r = C.REGIME
    c = qqq["close"]
    m = sma(c, r["sma"])
    _, pl = pivots(qqq, r["pivot_lr"])
    last_low = pl.ffill()
    below = (c < last_low).astype(int)
    broken = below.rolling(r["break_days"]).sum() >= r["break_days"]
    # buzilish yangi pivot tub paydo bo'lguncha amal qiladi
    new_pivot = pl.notna()
    state = []
    is_broken = False
    for b, n in zip(broken.values, new_pivot.values):
        if n:
            is_broken = False
        if b:
            is_broken = True
        state.append(is_broken)
    broken_state = pd.Series(state, index=c.index)
    above = c > m
    score = above.astype(int) + (~broken_state).astype(int)
    out = pd.DataFrame({"above_sma": above, "support_ok": ~broken_state, "support": last_low, "sma200": m})
    out["regime"] = score.map({2: "green", 1: "yellow", 0: "red"})
    out.loc[m.isna(), "regime"] = None
    return out


def _ret(df: pd.DataFrame | None, n: int) -> float:
    if df is None or len(df) <= n:
        return float("nan")
    return float(df["close"].iloc[-1] / df["close"].iloc[-1 - n] - 1)


def basket_ret(prices: dict, tickers: list[str], n: int) -> float:
    vals = [_ret(prices.get(t), n) for t in tickers]
    vals = [v for v in vals if math.isfinite(v)]
    return sum(vals) / len(vals) if vals else float("nan")


def sector_ranking(prices: dict) -> list[dict]:
    spy = prices.get("SPY")
    rows = []
    for etf, name in C.SECTOR_ETFS.items():
        df = prices.get(etf)
        if df is None:
            continue
        rel21 = _ret(df, 21) - _ret(spy, 21)
        rel63 = _ret(df, 63) - _ret(spy, 63)
        group = "himoya" if etf in C.DEFENSIVE else "sezuvchan" if etf in C.SENSITIVE else "davriy"
        rows.append({"etf": etf, "name": name, "group": group, "r1d": _ret(df, 1), "r21": _ret(df, 21),
                     "r63": _ret(df, 63), "rel21": rel21, "rel63": rel63,
                     "score": 0.4 * rel21 + 0.6 * rel63 if math.isfinite(rel21) and math.isfinite(rel63) else float("nan")})
    rows.sort(key=lambda x: -x["score"] if math.isfinite(x["score"]) else 1e9)
    for i, r in enumerate(rows):
        r["rank"] = i + 1
        r["top_half"] = i < (len(rows) + 1) // 2
    return rows


def panel(prices: dict) -> dict:
    """Bugungi bozor paneli. Qaror qoidalari (xarid to'xtatish va h.k.) shu yerda yig'iladi."""
    q = prices.get(C.REGIME["index"])
    reg = regime_series(q).iloc[-1] if q is not None and len(q) > 220 else None
    vix_df = prices.get("^VIX")
    vix = float(vix_df["close"].iloc[-1]) if vix_df is not None and len(vix_df) else float("nan")
    risk_on_63 = basket_ret(prices, C.SENSITIVE + C.CYCLICAL, 63) - basket_ret(prices, C.DEFENSIVE, 63)
    risk_on_21 = basket_ret(prices, C.SENSITIVE + C.CYCLICAL, 21) - basket_ret(prices, C.DEFENSIVE, 21)
    breadth_63 = _ret(prices.get("IWM"), 63) - _ret(prices.get("SPY"), 63)
    sectors = sector_ranking(prices)
    regime = reg["regime"] if reg is not None else None
    allow_buys, risk_mult, reasons = True, 1.0, []
    if regime == "red":
        allow_buys = False
        reasons.append("Nasdaq rejimi qizil: SMA200 ostida va tayanch buzilgan")
    elif regime == "yellow":
        risk_mult *= 0.5
        reasons.append("Nasdaq rejimi sariq: shartlardan biri buzilgan — risk yarmiga")
    if math.isfinite(vix) and vix >= C.VIX_HIGH:
        allow_buys = False
        reasons.append(f"VIX {vix:.1f} ≥ {C.VIX_HIGH:.0f}: qo'rquv yuqori — yangi xarid yo'q")
    elif math.isfinite(vix) and vix >= C.VIX_ELEVATED:
        risk_mult *= 0.5
        reasons.append(f"VIX {vix:.1f} ≥ {C.VIX_ELEVATED:.0f}: risk yarmiga")
    if math.isfinite(risk_on_63) and math.isfinite(risk_on_21) and risk_on_63 < 0 and risk_on_21 < 0:
        risk_mult *= 0.75
        reasons.append("Himoya sektorlari 1 va 3 oyda kuchliroq (risk-off) — risk 25% kamaydi")
    idx = []
    for t in ("SPY", "QQQ", "DIA", "IWM", C.CORE_TICKER):
        df = prices.get(t)
        if df is not None and len(df) > 1:
            idx.append({"ticker": t, "close": float(df["close"].iloc[-1]), "r1d": _ret(df, 1),
                        "r21": _ret(df, 21), "r63": _ret(df, 63)})
    return {
        "date": q.index[-1].date().isoformat() if q is not None else None,
        "regime": regime,
        "regime_detail": None if reg is None else {
            "above_sma200": bool(reg["above_sma"]), "support_ok": bool(reg["support_ok"]),
            "support": float(reg["support"]) if pd.notna(reg["support"]) else None,
            "sma200": float(reg["sma200"]) if pd.notna(reg["sma200"]) else None,
            "close": float(q["close"].iloc[-1])},
        "vix": vix, "risk_on_21": risk_on_21, "risk_on_63": risk_on_63, "breadth_63": breadth_63,
        "sectors": sectors, "indices": idx,
        "allow_buys": allow_buys, "risk_mult": risk_mult, "reasons": reasons,
    }
