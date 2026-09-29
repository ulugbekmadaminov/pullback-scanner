"""2-qadam: ma'lumot yig'ish.

Natija (data/ papkasida):
  universe.csv          — aksiyalar ro'yxati, sektori bilan
  4h/<TICKER>.parquet   — 4H shamlar (aksiyalar + QQQ, SPY)
  1d/QQQ.parquet, SPY   — kunlik shamlar (bozor rejimi uchun)
  earnings.json         — hisobot sanalari
  quality.csv           — har bir aksiya uchun sifat tekshiruvi
  manifest.json         — qachon, qaysi manbadan, qaysi versiyalar bilan yig'ilgan
"""
from __future__ import annotations

import json
import sys
from datetime import date

import pandas as pd

from config import BENCHMARKS, DAILY_PERIOD, DATA, INTRADAY_DAYS, UNIVERSE_DIR
from src.checks import fetch_earnings, quality_report
from src.prices import download, to_4h
from src.universe import add_sectors, fetch_universe


def main() -> int:
    import yfinance as yf

    now = pd.Timestamp.now(tz="UTC")
    (DATA / "4h").mkdir(parents=True, exist_ok=True)
    (DATA / "1d").mkdir(parents=True, exist_ok=True)

    # 1. Aksiyalar ro'yxati
    uni, source = fetch_universe()
    print(f"Ro'yxat: {len(uni)} aksiya ({source})")
    if source.startswith("sp-funds"):
        snap = UNIVERSE_DIR / f"spus_snapshot_{date.today().isoformat()}.txt"
        snap.write_text(
            f"# SPUS tarkibi, {date.today().isoformat()} (sp-funds.com)\n"
            + " ".join(uni["ticker"]) + "\n"
        )
    uni = add_sectors(uni)
    uni.to_csv(DATA / "universe.csv", index=False)

    # 2. Soatlik narxlar -> 4H
    tickers = list(uni["yf_ticker"]) + BENCHMARKS
    start = (now - pd.Timedelta(days=INTRADAY_DAYS)).date().isoformat()
    hourly = download(tickers, interval="60m", start=start)
    failed = sorted(set(tickers) - set(hourly))
    print(f"Soatlik: {len(hourly)} yuklandi, {len(failed)} yuklanmadi")

    bars4h: dict[str, pd.DataFrame] = {}
    for t, df in hourly.items():
        b = to_4h(df, now=now)
        if not b.empty:
            b.to_parquet(DATA / "4h" / f"{t}.parquet")
            bars4h[t] = b

    # 3. Kunlik benchmarklar (SMA 200 va pivot uchun)
    daily = download(BENCHMARKS, interval="1d", period=DAILY_PERIOD)
    for t, df in daily.items():
        df.to_parquet(DATA / "1d" / f"{t}.parquet")

    # 4. Hisobot sanalari
    earnings = fetch_earnings(list(uni["yf_ticker"]))
    (DATA / "earnings.json").write_text(json.dumps(earnings, indent=1, sort_keys=True))

    # 5. Sifat tekshiruvi
    q = quality_report(bars4h)
    q.to_csv(DATA / "quality.csv", index=False)
    flagged = q[q["status"] != "ok"]

    manifest = {
        "fetched_at_utc": now.isoformat(),
        "universe_source": source,
        "universe_count": int(len(uni)),
        "intraday_start": start,
        "loaded_4h": len(bars4h),
        "failed": failed,
        "earnings_missing": sorted(t for t, v in earnings.items() if v is None),
        "quality_flagged": flagged[["ticker", "status"]].to_dict("records"),
        "versions": {"yfinance": yf.__version__, "pandas": pd.__version__, "python": sys.version.split()[0]},
    }
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))

    print(f"Tayyor: {len(bars4h)} ta 4H fayl, sifat ogohlantirishi: {len(flagged)}")
    # Ko'p aksiya yuklanmasa — xato bilan tugaydi, shunda Actions buni qizil ko'rsatadi
    return 1 if len(failed) > 0.1 * len(tickers) else 0


if __name__ == "__main__":
    raise SystemExit(main())
