"""Narx ma'lumoti: yfinance'dan 1 soatlik shamlar va ularni 4H ga yig'ish.

4H shamlar TradingView'dagidek: kuniga 2 ta, 09:30–13:30 va 13:30–16:00 (ET).
Faqat asosiy sessiya. Tugallanmagan sham saqlanmaydi.
"""
from __future__ import annotations

import time

import pandas as pd

from config import (
    BATCH_SIZE,
    SESSION_CLOSE_MIN,
    SESSION_OPEN_MIN,
    SPLIT_MIN,
    TZ,
)

COLS = ["open", "high", "low", "close", "volume"]


def _normalize(df: pd.DataFrame, intraday: bool = True) -> pd.DataFrame:
    """Ustun nomlari kichik harfda; vaqt: soatlik — ET vaqt zonasida, kunlik — oddiy sana."""
    df = df.rename(columns=str.lower)
    df = df[[c for c in COLS if c in df.columns]].dropna(subset=["open", "high", "low", "close"])
    idx = pd.DatetimeIndex(df.index)
    if intraday:
        idx = idx.tz_localize("UTC") if idx.tz is None else idx
        idx = idx.tz_convert(TZ)
    else:
        idx = (idx.tz_convert(TZ).tz_localize(None) if idx.tz is not None else idx).normalize()
    df.index = idx
    df.index.name = "start" if intraday else "date"
    df = df.sort_index()
    return df[~df.index.duplicated(keep="last")]


def _split(raw: pd.DataFrame, tickers: list[str], intraday: bool) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return out
    if isinstance(raw.columns, pd.MultiIndex):
        level0 = set(raw.columns.get_level_values(0))
        for t in tickers:
            if t in level0:
                df = raw[t].dropna(how="all")
                if not df.empty:
                    out[t] = _normalize(df, intraday)
    elif len(tickers) == 1:
        out[tickers[0]] = _normalize(raw.dropna(how="all"), intraday)
    return out


def download(tickers: list[str], interval: str, retries: int = 3, **kwargs) -> dict[str, pd.DataFrame]:
    """Tickerlarni guruhlab yuklaydi. Yuklanmaganlari natijada bo'lmaydi."""
    import yfinance as yf

    intraday = interval.endswith("m") or interval.endswith("h")
    result: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        for attempt in range(retries):
            try:
                raw = yf.download(
                    batch,
                    interval=interval,
                    auto_adjust=True,
                    prepost=False,
                    group_by="ticker",
                    threads=True,
                    progress=False,
                    **kwargs,
                )
                result.update(_split(raw, batch, intraday))
                break
            except Exception as e:  # noqa: BLE001
                print(f"[qayta urinish {attempt + 1}] {batch[0]}…: {e}")
                time.sleep(5 * (attempt + 1))
        time.sleep(1)
    return result


def to_4h(df1h: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """1 soatlik shamlarni 4H ga yig'adi.

    Natija indeksi — sham boshlanishi (09:30 yoki 13:30, ET). Ustunlar:
    open, high, low, close, volume, n_1h (nechta soatlik sham kirdi), end.
    `now` berilsa, tugashi undan keyin bo'lgan (hali yopilmagan) sham tashlanadi.
    """
    if df1h.empty:
        return pd.DataFrame(columns=COLS + ["n_1h", "end"])
    df = df1h.sort_index()
    minutes = df.index.hour * 60 + df.index.minute
    df = df[(minutes >= SESSION_OPEN_MIN) & (minutes < SESSION_CLOSE_MIN)]
    minutes = df.index.hour * 60 + df.index.minute
    block = (minutes >= SPLIT_MIN).astype(int)
    day = df.index.normalize()

    g = df.groupby([day, block])
    out = g.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        n_1h=("close", "size"),
    )
    days = out.index.get_level_values(0)
    blocks = out.index.get_level_values(1)
    start_min = pd.Index(blocks).map({0: SESSION_OPEN_MIN, 1: SPLIT_MIN})
    end_min = pd.Index(blocks).map({0: SPLIT_MIN, 1: SESSION_CLOSE_MIN})
    out.index = pd.DatetimeIndex(days + pd.to_timedelta(start_min, unit="min"), name="start")
    out["end"] = days + pd.to_timedelta(end_min, unit="min")
    if now is not None:
        out = out[out["end"] <= now.tz_convert(TZ)]
    return out
