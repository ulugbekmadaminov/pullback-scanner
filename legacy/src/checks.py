"""Hisobot (earnings) sanalari va ma'lumot sifati tekshiruvi."""
from __future__ import annotations

import time

import pandas as pd

from config import TZ

MAX_BAR_MOVE = 0.25  # bitta 4H shamda ±25% dan katta o'zgarish shubhali


def fetch_earnings(tickers: list[str], limit: int = 16, pause: float = 0.3) -> dict[str, list[str] | None]:
    """Har bir aksiya uchun o'tgan va kelgusi hisobot sanalari (ET, YYYY-MM-DD).

    None — yuklab bo'lmadi (backtestda bu aksiya uchun filtr ishlamaydi va bu qayd etiladi).
    """
    import yfinance as yf

    out: dict[str, list[str] | None] = {}
    for t in tickers:
        dates = None
        for attempt in range(3):
            try:
                ed = yf.Ticker(t).get_earnings_dates(limit=limit)
                if ed is not None and not ed.empty:
                    idx = pd.DatetimeIndex(ed.index)
                    idx = idx.tz_localize("UTC") if idx.tz is None else idx
                    dates = sorted({d.date().isoformat() for d in idx.tz_convert(TZ)})
                break
            except Exception:  # noqa: BLE001
                time.sleep(2 * (attempt + 1))
        out[t] = dates
        time.sleep(pause)
    return out


def quality_report(bars4h: dict[str, pd.DataFrame], reference: str = "QQQ") -> pd.DataFrame:
    """Har bir aksiya uchun sifat ko'rsatkichlari.

    Mos yozuv (reference) sifatida QQQ sessiyalari olinadi: unda bor, aksiyada yo'q
    shamlar "yetishmayotgan" deb hisoblanadi (aksiya birjaga kirgan kundan boshlab).
    """
    ref = bars4h.get(reference)
    ref_index = ref.index if ref is not None else None
    ref_n1h = ref["n_1h"] if ref is not None else None
    rows = []
    for t, df in bars4h.items():
        if df.empty:
            rows.append({"ticker": t, "bars": 0, "status": "bo'sh"})
            continue
        missing = partial = 0
        if ref_index is not None:
            expected = ref_index[ref_index >= df.index[0]]
            missing = int(len(expected.difference(df.index)))
            common = df.index.intersection(ref_index)
            partial = int((df.loc[common, "n_1h"] < ref_n1h.loc[common]).sum())
        moves = df["close"].pct_change().abs()
        extreme = int((moves > MAX_BAR_MOVE).sum())
        zero_vol = int((df["volume"] <= 0).sum())
        bad_ohlc = int(((df["high"] < df[["open", "close"]].max(axis=1)) |
                        (df["low"] > df[["open", "close"]].min(axis=1))).sum())
        issues = []
        if len(df) < 400:
            issues.append("qisqa tarix")
        if ref_index is not None and missing > 0.02 * max(len(df), 1):
            issues.append("ko'p bo'shliq")
        if extreme:
            issues.append("keskin sakrash")
        if bad_ohlc:
            issues.append("OHLC xatosi")
        rows.append({
            "ticker": t,
            "first": df.index[0].date().isoformat(),
            "last": df.index[-1].date().isoformat(),
            "bars": len(df),
            "missing": missing,
            "partial": partial,
            "extreme_moves": extreme,
            "zero_volume": zero_vol,
            "bad_ohlc": bad_ohlc,
            "status": "ok" if not issues else "; ".join(issues),
        })
    return pd.DataFrame(rows).sort_values("ticker").reset_index(drop=True)
