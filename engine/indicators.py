"""Texnik o'lchovlar. Hech biri kelajakdagi shamni ko'rmaydi (pivotlar faqat tasdiqlangach)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()   # Wilder


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def pivots(df: pd.DataFrame, n: int = 3) -> tuple[pd.Series, pd.Series]:
    """Pivot cho'qqi/tub. Qiymat pivot shamida emas, TASDIQLANGAN kunida (n kun keyin) paydo bo'ladi.

    Natija: ikkita seriya — har kunda shu kungacha ma'lum bo'lgan pivot narxi (aks holda NaN),
    indeks — tasdiq kuni; 'bar' atributi o'rniga alohida pozitsiya ro'yxati qaytariladi.
    """
    h, l = df["high"].values, df["low"].values
    size = len(df)
    ph = np.full(size, np.nan)
    pl = np.full(size, np.nan)
    for i in range(n, size - n):
        if h[i] > h[i - n:i].max() and h[i] >= h[i + 1:i + n + 1].max():
            ph[i + n] = h[i]
        if l[i] < l[i - n:i].min() and l[i] <= l[i + 1:i + n + 1].min():
            pl[i + n] = l[i]
    return pd.Series(ph, index=df.index), pd.Series(pl, index=df.index)


def rs_score(close: pd.Series) -> pd.Series:
    """IBD uslubidagi og'irlikli daromad (63/126/189/252 kun)."""
    from .config import RS_WEIGHTS
    s = 0.0
    for n, w in RS_WEIGHTS.items():
        s = s + w * (close / close.shift(n) - 1)
    return s


def stage(close: pd.Series) -> pd.Series:
    """Weinstein bosqichi kunlik grafikda (30 haftalik ≈ 150 kunlik SMA).

    2 — narx SMA150 ustida va SMA150 o'smoqda; 4 — ostida va tushmoqda;
    1 — ostida, lekin SMA tekis/o'smoqda (asos); 3 — ustida, lekin SMA tekis/tushmoqda (cho'qqi).
    """
    m = sma(close, 150)
    slope = m - m.shift(20)
    above = close > m
    rising = slope > 0
    st = pd.Series(np.nan, index=close.index)
    st[above & rising] = 2
    st[above & ~rising] = 3
    st[~above & ~rising] = 4
    st[~above & rising] = 1
    st[m.isna()] = np.nan
    return st


def add_all(df: pd.DataFrame) -> pd.DataFrame:
    """Kunlik DataFrame'ga barcha ustunlarni qo'shadi (nusxa qaytaradi)."""
    from .config import ATR_N
    d = df.copy()
    c = d["close"]
    for n in (20, 50, 100, 200):
        d[f"ema{n}"] = ema(c, n)
    for n in (50, 150, 200):
        d[f"sma{n}"] = sma(c, n)
    d["atr"] = atr(d, ATR_N)
    d["rsi"] = rsi(c)
    d["vol50"] = d["volume"].rolling(50, min_periods=20).mean()
    d["dvol20"] = (c * d["volume"]).rolling(20, min_periods=10).mean()
    d["hi252"] = d["high"].rolling(252, min_periods=120).max()
    d["hi126"] = d["high"].rolling(126, min_periods=60).max()
    d["hi63"] = d["high"].rolling(63, min_periods=30).max()
    d["rs_raw"] = rs_score(c)
    d["stage"] = stage(c)
    w = c.resample("W-FRI").last()
    d["sma40w"] = sma(w, 40).reindex(d.index, method="ffill")
    return d
