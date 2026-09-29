"""Loyiha sozlamalari. Qoidalar spetsifikatsiyasi v1 ga mos (1-bo'lim)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
UNIVERSE_DIR = ROOT / "universe"

# SPUS (SP Funds S&P 500 Sharia Industry Exclusions ETF) rasmiy tarkib fayli
SPUS_CSV_URL = "https://www.sp-funds.com/wp-content/uploads/data/TidalFG_Holdings_SPUS.csv"

BENCHMARKS = ["QQQ", "SPY"]          # bozor rejimi va taqqoslash
INTRADAY_DAYS = 729                   # yfinance 60m ma'lumot chegarasi ~730 kun
DAILY_PERIOD = "10y"                  # SMA 200 uchun yetarli kunlik tarix
BATCH_SIZE = 40                       # bir so'rovdagi tickerlar soni

TZ = "America/New_York"
SESSION_OPEN_MIN = 9 * 60 + 30        # 09:30
SPLIT_MIN = 13 * 60 + 30              # 13:30 — 4H shamlar chegarasi
SESSION_CLOSE_MIN = 16 * 60           # 16:00
