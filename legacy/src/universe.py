"""Aksiyalar ro'yxati: SPUS ETF tarkibi (S&P 500 Shariah, AAOIFI).

Asosiy manba — fondning rasmiy CSV fayli. U yuklanmasa, universe/ dagi
eng so'nggi zaxira nusxa ishlatiladi va bu manifestda qayd etiladi.
"""
from __future__ import annotations

import io
import re
import time
from pathlib import Path

import pandas as pd
import requests

from config import SPUS_CSV_URL, UNIVERSE_DIR

# Oddiy aksiya tickeri: 1-5 harf, ixtiyoriy sinf qo'shimchasi (BRK.B).
# Naqd pul, CVR va raqamli ichki kodlar shu bilan chiqarib tashlanadi.
TICKER_RE = re.compile(r"^[A-Z]{1,5}(?:[.\-][A-Z])?$")


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    norm = {re.sub(r"[^a-z]", "", c.lower()): c for c in df.columns}
    for n in names:
        if n in norm:
            return norm[n]
    return None


def parse_holdings(text: str) -> pd.DataFrame:
    """Rasmiy CSV matnini toza ro'yxatga aylantiradi: ticker, name, weight, yf_ticker."""
    df = pd.read_csv(io.StringIO(text))
    tcol = _find_col(df, "stockticker", "ticker", "symbol")
    if tcol is None:
        raise ValueError(f"Ticker ustuni topilmadi: {list(df.columns)}")
    ncol = _find_col(df, "securityname", "name", "description")
    wcol = _find_col(df, "weightings", "weight", "weighting")

    out = pd.DataFrame({"ticker": df[tcol].astype(str).str.strip().str.upper()})
    out["name"] = df[ncol].astype(str).str.strip() if ncol else ""
    if wcol:
        out["weight"] = pd.to_numeric(
            df[wcol].astype(str).str.replace(",", "").str.replace("%", ""), errors="coerce"
        )
    else:
        out["weight"] = float("nan")

    ok = out["ticker"].map(lambda t: bool(TICKER_RE.match(t)))
    out = out[ok & ~(out["weight"] <= 0)]
    out["yf_ticker"] = out["ticker"].str.replace(".", "-", regex=False)
    return (
        out.drop_duplicates("ticker")
        .sort_values("weight", ascending=False, na_position="last")
        .reset_index(drop=True)
    )


def load_snapshot(directory: Path = UNIVERSE_DIR) -> tuple[pd.DataFrame, str]:
    """Eng so'nggi spus_snapshot_*.txt faylini o'qiydi."""
    files = sorted(directory.glob("spus_snapshot_*.txt"))
    if not files:
        raise FileNotFoundError("Zaxira ro'yxat topilmadi (universe/spus_snapshot_*.txt)")
    path = files[-1]
    words = [
        w for line in path.read_text().splitlines() if not line.startswith("#")
        for w in line.split()
    ]
    df = pd.DataFrame({"ticker": words})
    df = df[df["ticker"].map(lambda t: bool(TICKER_RE.match(t)))].drop_duplicates()
    df["name"] = ""
    df["weight"] = float("nan")
    df["yf_ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    return df.reset_index(drop=True), path.name


def fetch_universe(url: str = SPUS_CSV_URL, retries: int = 3) -> tuple[pd.DataFrame, str]:
    """(ro'yxat, manba nomi). Avval rasmiy CSV, bo'lmasa zaxira."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            df = parse_holdings(r.text)
            if len(df) < 100:  # SPUS'da ~200+ aksiya bo'lishi kerak
                raise ValueError(f"Juda kam ticker: {len(df)}")
            return df, "sp-funds.com CSV"
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    print(f"[ogohlantirish] Rasmiy CSV yuklanmadi ({last_err}); zaxira ishlatiladi")
    df, name = load_snapshot()
    return df, f"zaxira: {name}"


def add_sectors(df: pd.DataFrame, pause: float = 0.3) -> pd.DataFrame:
    """Har bir aksiyaga yfinance'dan sektor va sanoat qo'shadi (portfel chegarasi uchun)."""
    import yfinance as yf

    sectors, industries = [], []
    for t in df["yf_ticker"]:
        sector = industry = ""
        for attempt in range(3):
            try:
                info = yf.Ticker(t).info or {}
                sector = info.get("sector", "") or ""
                industry = info.get("industry", "") or ""
                break
            except Exception:  # noqa: BLE001
                time.sleep(2 * (attempt + 1))
        sectors.append(sector)
        industries.append(industry)
        time.sleep(pause)
    out = df.copy()
    out["sector"] = sectors
    out["industry"] = industries
    return out
