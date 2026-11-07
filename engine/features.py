"""Kesma (barcha aksiyalar bo'yicha) belgilar: sana × ticker jadvallari.

Bir xil jadvallar ham kundalik skanerda (oxirgi qator), ham backtestda (butun tarix)
ishlatiladi — shunda ikkalasi aynan bir xil qoidaga bo'ysunadi.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .indicators import add_all


def build(prices: dict[str, pd.DataFrame], tickers: list[str], sectors: dict[str, str]) -> dict:
    ind = {t: add_all(prices[t]) for t in tickers if t in prices and len(prices[t]) > 260}
    idx = prices[C.REGIME["index"]].index if C.REGIME["index"] in prices else next(iter(ind.values())).index

    def mat(col: str) -> pd.DataFrame:
        return pd.DataFrame({t: d[col] for t, d in ind.items()}).reindex(idx)

    F: dict = {"ind": ind, "index": idx}
    for col in ("close", "open", "high", "low", "volume", "stage", "sma150", "sma40w", "ema200", "dvol20",
                "hi252", "atr", "rs_raw"):
        F[col] = mat(col)
    F["rs_pct"] = F["rs_raw"].rank(axis=1, pct=True) * 100
    F["from_high"] = 1 - F["close"] / F["hi252"]
    below150 = (F["close"] < F["sma150"]).astype(float)
    F["below150_streak"] = below150.rolling(C.WATCH_MID_EXIT["stage_break_days"]).sum()
    n = C.WATCH_MID_ENTRY["ema200_untouched_days"]
    F["ema200_untouched"] = (F["low"] > F["ema200"]).astype(float).rolling(n).sum() >= n
    F["liquid"] = (F["close"] >= C.MIN_PRICE) & (F["dvol20"] >= C.MIN_DOLLAR_VOL)

    # Sektor kuchi: sektor ETF'ining SPY ga nisbatan 21/63 kunlik kuchi, kun bo'yicha reyting
    spy = prices.get("SPY")
    rel = {}
    for etf in C.SECTOR_ETFS:
        if etf in prices and spy is not None:
            e, s = prices[etf]["close"].reindex(idx), spy["close"].reindex(idx)
            rel[etf] = 0.4 * (e.pct_change(21) - s.pct_change(21)) + 0.6 * (e.pct_change(63) - s.pct_change(63))
    rel_df = pd.DataFrame(rel)
    half = (rel_df.notna().sum(axis=1) + 1) // 2
    top = rel_df.rank(axis=1, ascending=False).le(half, axis=0)
    F["sector_top"] = pd.DataFrame({t: top[C.SECTOR_TO_ETF[sectors[t]]] if C.SECTOR_TO_ETF.get(sectors.get(t, "")) in top
                                    else pd.Series(True, index=idx) for t in ind}).reindex(idx).fillna(False)

    # Episodic Pivot: gap ≥5% va hajm ≥2× o'rtacha; keyin narx gap kuni tubidan pastga tushmagan
    gap = F["open"] / F["close"].shift(1) - 1
    vol50 = F["volume"].rolling(50, min_periods=20).mean()
    ep_day = (gap >= C.EP["gap_min"]) & (F["volume"] >= C.EP["vol_mult"] * vol50.shift(1))
    ep_low = F["low"].where(ep_day).ffill(limit=C.EP["lookback"])
    F["ep"] = ep_low.notna() & (F["close"] > ep_low)
    F["gap"] = gap
    return F


def mid_base_mask(F: dict) -> pd.DataFrame:
    """Asosiy yo'l: bosqich 2, kuchli, cho'qqiga yaqin, kuchli sektorda."""
    e = C.WATCH_MID_ENTRY
    base = (F["stage"] == 2) & (F["rs_pct"] >= e["rs_pct_min"]) & (F["from_high"] <= e["from_high_max"]) \
        & F["ema200_untouched"] & F["liquid"]
    if e["sector_top_half"]:
        base &= F["sector_top"]
    return base


def mid_entry_mask(F: dict) -> pd.DataFrame:
    base = mid_base_mask(F)
    # EP (katalizator) yo'li ham chiqish qoidalarini buzmasligi kerak — aks holda aksiya bugun kirib,
    # ertaga "nisbiy kuch < 40" yoki "cho'qqidan > 35%" bilan chiqib ketadi (kirdi-chiqdi).
    x = C.WATCH_MID_EXIT
    ep_ok = F["ep"] & F["liquid"] & (F["close"] > F["sma150"]) \
        & (F["rs_pct"] >= x["rs_pct_below"]) & (F["from_high"] <= x["from_high_over"])
    return base | ep_ok


def mid_exit_reason(F: dict, i: int, t: str) -> str | None:
    """Kuzatuvdan chiqish sababi (bo'lmasa None). Kirish va chiqish chegaralari orasida
    ataylab oraliq bor (gisterezis) — aksiya har kuni kirib-chiqib turmasligi uchun."""
    x = C.WATCH_MID_EXIT
    rs, fh = F["rs_pct"][t].iat[i], F["from_high"][t].iat[i]
    if F["below150_streak"][t].iat[i] >= x["stage_break_days"]:
        return f"Trend buzildi: {x['stage_break_days']} kun SMA150 ostida yopildi"
    if pd.notna(rs) and rs < x["rs_pct_below"]:
        return f"Nisbiy kuch {rs:.0f} foizlikka tushdi (<{x['rs_pct_below']})"
    if pd.notna(fh) and fh > x["from_high_over"]:
        return f"52 haftalik cho'qqidan {fh * 100:.0f}% pastda (>{x['from_high_over'] * 100:.0f}%)"
    g = F["gap"][t].iat[i]
    if pd.notna(g) and g <= x["earnings_gap_down"]:
        return f"Keskin gap pastga: {g * 100:.1f}%"
    return None


def corr_cluster_ok(F: dict, i: int, cand: str, holdings: list[str], limit: int, thr: float) -> bool:
    """Tema/korrelyatsiya chegarasi: 60 kunlik daromadlar korrelyatsiyasi ≥thr bo'lgan
    pozitsiyalar soni limitdan oshmasin (ARK saboqi: turli sektor ≠ turli tikish)."""
    if not holdings:
        return True
    r = F["close"].iloc[max(0, i - 60):i + 1].pct_change().iloc[1:]
    if cand not in r:
        return True
    c = r[[h for h in holdings if h in r] + [cand]].corr()[cand].drop(cand)
    return int((c >= thr).sum()) < limit


def earnings_soon(earn: list[str] | None, day: pd.Timestamp, n: int) -> bool:
    if not earn:
        return False
    end = day + pd.offsets.BDay(n)
    return any(day < pd.Timestamp(e) <= end for e in earn)
