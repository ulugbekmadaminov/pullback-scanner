"""Ma'lumot qatlami: SPUS ro'yxati, kunlik narxlar, hisobot sanalari, dividendlar.

Tarmoq bilan ishlaydigan hamma narsa shu faylda — qolgan modullar faqat DataFrame bilan ishlaydi
(shuning uchun ularni internetsiz, demo ma'lumotda sinash mumkin).
"""
from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

import pandas as pd

from . import config as C

TICKER_RE = re.compile(r"^[A-Z]{1,5}(?:[.\-][A-Z])?$")
COLS = ["open", "high", "low", "close", "volume"]


# ── Aksiyalar ro'yxati ────────────────────────────────────────────────────────
def _col(df: pd.DataFrame, *names: str) -> str | None:
    norm = {re.sub(r"[^a-z]", "", c.lower()): c for c in df.columns}
    return next((norm[n] for n in names if n in norm), None)


def parse_holdings(text: str) -> pd.DataFrame:
    """Fondning rasmiy CSV matnidan toza ro'yxat: ticker, name, weight, yf."""
    df = pd.read_csv(io.StringIO(text))
    t = _col(df, "stockticker", "ticker", "symbol")
    if t is None:
        raise ValueError(f"Ticker ustuni topilmadi: {list(df.columns)}")
    n, w = _col(df, "securityname", "name"), _col(df, "weightings", "weight")
    out = pd.DataFrame({"ticker": df[t].astype(str).str.strip().str.upper()})
    out["name"] = df[n].astype(str).str.strip() if n else ""
    out["weight"] = pd.to_numeric(df[w].astype(str).str.replace(",", "").str.replace("%", ""),
                                  errors="coerce") if w else float("nan")
    out = out[out["ticker"].map(lambda x: bool(TICKER_RE.match(x))) & ~(out["weight"] <= 0)]
    out["yf"] = out["ticker"].str.replace(".", "-", regex=False)
    return out.drop_duplicates("ticker").sort_values("weight", ascending=False).reset_index(drop=True)


def load_snapshot() -> tuple[pd.DataFrame, str]:
    files = sorted((C.ROOT / "engine").glob("spus_snapshot_*.txt")) + sorted((C.ROOT / "universe").glob("spus_snapshot_*.txt"))
    path = max(files, key=lambda p: p.name)
    words = [w for ln in path.read_text().splitlines() if not ln.startswith("#") for w in ln.split()]
    df = pd.DataFrame({"ticker": [w for w in dict.fromkeys(words) if TICKER_RE.match(w)]})
    df["name"], df["weight"] = "", float("nan")
    df["yf"] = df["ticker"].str.replace(".", "-", regex=False)
    return df, path.name


def fetch_universe() -> tuple[pd.DataFrame, str]:
    import requests
    for attempt in range(3):
        try:
            r = requests.get(C.SPUS_CSV_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            df = parse_holdings(r.text)
            if len(df) >= 100:
                return df, "sp-funds.com CSV"
        except Exception as e:  # noqa: BLE001
            print(f"[ogohlantirish] SPUS CSV: {e}")
            time.sleep(3 * (attempt + 1))
    df, name = load_snapshot()
    return df, f"zaxira: {name}"


# ── Narxlar ───────────────────────────────────────────────────────────────────
def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=str.lower)
    df = df[[c for c in COLS if c in df.columns]].dropna(subset=["open", "high", "low", "close"])
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_convert(C.TZ).tz_localize(None)
    df.index = idx.normalize()
    df.index.name = "date"
    df = df.sort_index()
    return df[~df.index.duplicated(keep="last")].astype(float)


def download_daily(tickers: list[str], years: int = C.DAILY_YEARS, batch: int = 40, period: str | None = None) -> dict[str, pd.DataFrame]:
    """yfinance'dan split/dividendga moslangan kunlik shamlar. Yuklanmaganlar natijada bo'lmaydi."""
    import yfinance as yf
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), batch):
        part = tickers[i:i + batch]
        for attempt in range(3):
            try:
                raw = yf.download(part, period=period or f"{years}y", interval="1d", auto_adjust=True,
                                  group_by="ticker", threads=True, progress=False)
                if isinstance(raw.columns, pd.MultiIndex):
                    lv = set(raw.columns.get_level_values(0))
                    for t in part:
                        if t in lv and not raw[t].dropna(how="all").empty:
                            out[t] = _normalize(raw[t].dropna(how="all"))
                elif len(part) == 1 and not raw.empty:
                    out[part[0]] = _normalize(raw)
                break
            except Exception as e:  # noqa: BLE001
                print(f"[qayta urinish {attempt + 1}] {part[0]}…: {e}")
                time.sleep(5 * (attempt + 1))
        time.sleep(1)
    return out


def drop_unfinished(df: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Bozor hali yopilmagan bo'lsa (Nyu-York vaqti 16:15 dan oldin), bugungi chala shamni olib tashlaydi.
    Skaner qo'lda kun o'rtasida ishga tushirilsa ham faqat yopilgan kunlar tahlil qilinadi."""
    now = now if now is not None else pd.Timestamp.now(tz=C.TZ)
    if df.empty or df.index[-1] < now.tz_localize(None).normalize():
        return df
    if now.hour * 60 + now.minute < 16 * 60 + 15:
        return df.iloc[:-1]
    return df


def load_cached_prices(tickers: list[str], years: int = C.DAILY_YEARS) -> dict[str, pd.DataFrame]:
    """Keshdagi parquet'ni o'qiydi va faqat yetishmagan oxirgi kunlarni yuklaydi."""
    C.CACHE.mkdir(parents=True, exist_ok=True)
    path = C.CACHE / "daily.parquet"
    have: dict[str, pd.DataFrame] = {}
    if path.exists():
        big = pd.read_parquet(path)
        for t, g in big.groupby("ticker"):
            have[t] = g.drop(columns="ticker")
    # Har ishda keshdagi hamma aksiyaning oxirgi oyi qayta yuklanadi: yangi kunlar qo'shiladi,
    # oxirgi shamlar (masalan, kecha yopilmagan sham) to'g'risi bilan almashtiriladi.
    fresh_full = [t for t in tickers if t not in have]
    fresh_tail = [t for t in tickers if t in have]
    got = download_daily(fresh_full, years) if fresh_full else {}
    if fresh_tail:
        tail = download_daily(fresh_tail, period="1mo")
        for t, df in tail.items():
            # split bo'lsa eski tarix moslashtirilmagan bo'ladi → to'liq qayta yuklaymiz
            old = have[t]
            common = old.index.intersection(df.index)
            # taqqoslash oyning birinchi umumiy kunida: oxirgi kun chala sham bo'lishi mumkin
            if len(common) and abs(old.loc[common[0], "close"] / df.loc[common[0], "close"] - 1) > 0.02:
                got.update(download_daily([t], years))
            else:
                got[t] = pd.concat([old[old.index < df.index[0]], df])
    have.update(got)
    have = {t: drop_unfinished(df) for t, df in have.items()}
    frames = [df.assign(ticker=t) for t, df in have.items()]
    if frames:
        pd.concat(frames).to_parquet(path)
    return {t: have[t] for t in tickers if t in have}


# ── Hisobot sanalari va dividendlar ───────────────────────────────────────────
def fetch_earnings_and_dividends(tickers: list[str], pause: float = 0.25) -> tuple[dict, dict]:
    import yfinance as yf
    earn, divs = {}, {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            ed = tk.get_earnings_dates(limit=16)
            if ed is not None and not ed.empty:
                idx = pd.DatetimeIndex(ed.index)
                idx = idx.tz_convert(C.TZ) if idx.tz is not None else idx
                earn[t] = sorted({d.date().isoformat() for d in idx})
            d = tk.dividends
            if d is not None and not d.empty:
                di = pd.DatetimeIndex(d.index)
                di = di.tz_convert(C.TZ).tz_localize(None) if di.tz is not None else di
                divs[t] = {k.date().isoformat(): float(v) for k, v in zip(di, d.values)}
        except Exception as e:  # noqa: BLE001
            print(f"[ogohlantirish] {t} hisobot/dividend: {e}")
        time.sleep(pause)
    return earn, divs


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(clean(obj), ensure_ascii=False, separators=(",", ":"), default=_jsonable,
                              allow_nan=False))
    tmp.replace(path)


def clean(o):
    """NaN/inf → None (JSON standartida NaN yo'q), numpy turlari → oddiy Python turlari."""
    import math
    import numpy as np
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not math.isfinite(float(o)) else round(float(o), 6)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def _jsonable(o):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else round(float(o), 6)
    if isinstance(o, (pd.Timestamp,)):
        return o.date().isoformat()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))
