"""Barcha qoidalar va chegaralar shu yerda. Bitta haqiqat manbai.

Har bir qiymat v2 qoidalar hujjatidagi qatorga mos keladi. Qiymat o'zgarsa —
RULES_VERSION oshiriladi va sababi docs/QOIDALAR-v2.md ga yoziladi
(o'tmishdagi natijalar qaysi versiyada olingani shu raqamdan bilinadi).
"""
from __future__ import annotations

from pathlib import Path

RULES_VERSION = "2.0.0"

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"                   # git'da saqlanadigan holat (audit izi)
CACHE = ROOT / ".cache"                  # vaqtinchalik narx keshi (git'ga kirmaydi)
PUBLIC = ROOT / "app" / "public" / "data"  # ilova o'qiydigan JSON
TZ = "America/New_York"

# ── Ma'lumot manbalari ────────────────────────────────────────────────────────
SPUS_CSV_URL = "https://www.sp-funds.com/wp-content/uploads/data/TidalFG_Holdings_SPUS.csv"
DAILY_YEARS = 12                          # SMA200 + 10 yillik backtest uchun
CHART_DAYS = 520                          # ilovadagi grafik uchun ~2 yil
FUNDAMENTALS_MAX_AGE_DAYS = 7             # fundamental ma'lumot haftada bir yangilanadi
MIN_PRICE = 10.0
MIN_DOLLAR_VOL = 20e6                     # 20 kunlik o'rtacha savdo hajmi, $

# Yadro (core) — keng halol indeks
CORE_TICKER = "SPUS"
BENCHMARKS = ["SPUS", "SPY", "QQQ", "IWM", "DIA", "^VIX"]

# Sektor ETF'lari va Morningstar guruhlari (2-rasm: himoya/sezuvchan/davriy)
SECTOR_ETFS = {
    "XLK": "Texnologiya", "XLV": "Sog'liqni saqlash", "XLP": "Birlamchi iste'mol",
    "XLU": "Kommunal", "XLE": "Energiya", "XLI": "Sanoat", "XLC": "Aloqa",
    "XLY": "Ikkilamchi iste'mol", "XLB": "Materiallar", "XLF": "Moliya", "XLRE": "Ko'chmas mulk",
}
DEFENSIVE = ["XLP", "XLV", "XLU"]
SENSITIVE = ["XLE", "XLI", "XLK", "XLC"]
CYCLICAL = ["XLY", "XLB", "XLF", "XLRE"]
# yfinance sektor nomi → sektor ETF
SECTOR_TO_ETF = {
    "Technology": "XLK", "Healthcare": "XLV", "Consumer Defensive": "XLP",
    "Utilities": "XLU", "Energy": "XLE", "Industrials": "XLI",
    "Communication Services": "XLC", "Consumer Cyclical": "XLY",
    "Basic Materials": "XLB", "Financial Services": "XLF", "Real Estate": "XLRE",
}
# Dow Jones 30 (2026 holati). Indeks tarkibi o'zgarsa shu ro'yxat yangilanadi.
DJIA = ["AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
        "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK",
        "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT"]

# ── Bozor paneli ──────────────────────────────────────────────────────────────
REGIME = {
    "index": "QQQ",
    "sma": 200,
    "pivot_lr": 5,          # kunlik pivot tub: chap va o'ngda 5 tadan sham
    "break_days": 2,        # pivot tub ostida ketma-ket 2 kun yopilish = buzilish
}
VIX_HIGH = 30.0             # undan yuqori — yangi xarid to'xtaydi
VIX_ELEVATED = 22.0         # undan yuqori — risk yarmiga tushadi

# ── Indikatorlar ──────────────────────────────────────────────────────────────
ATR_N = 14
PIVOT_N = 3                 # swing cho'qqi/tub: chap-o'ngda 3 sham
PIVOT_MIN_ATR = 1.0         # qo'shni cho'qqi-tub farqi kamida 1 ATR
RS_WEIGHTS = {63: 0.4, 126: 0.2, 189: 0.2, 252: 0.2}   # IBD uslubidagi nisbiy kuch

# ── Kuzatuv ro'yxati: O'RTA muddat (2 hafta – 6 oy) ────────────────────────────
WATCH_MID_ENTRY = {
    "rs_pct_min": 70,           # SPUS ichida nisbiy kuch foizlik o'rni
    "from_high_max": 0.25,      # 52 haftalik cho'qqidan ko'pi bilan 25% pastda
    "sector_top_half": True,    # sektori SPY'ga nisbatan kuchli yarmida
    "ema200_untouched_days": 21,  # Akhliddin PullBack1: 1 oy EMA200 ga tegmagan
}
WATCH_MID_EXIT = {
    "rs_pct_below": 40,
    "from_high_over": 0.35,
    "stage_break_days": 3,      # SMA150 ostida ketma-ket 3 kun
    "earnings_gap_down": -0.07,
}
EP = {"gap_min": 0.05, "vol_mult": 2.0, "lookback": 20}   # Episodic Pivot

# ── Kuzatuv ro'yxati: UZOQ muddat (1 yil+) ────────────────────────────────────
WATCH_LONG_ENTRY = {
    "piotroski_min": 6,
    "roe_min": 0.15,
    "de_max": 1.0,
    "fcf_positive": True,
    "above_sma200w": True,      # haftalik 40 haftalik o'rtacha ustida (Stage 4 emas)
}
WATCH_LONG_EXIT = {"piotroski_max": 3, "below_sma200w_pct": 0.10}

# ── Kirish signallari (kunlik) ────────────────────────────────────────────────
PULLBACK = {
    "depth_min": 0.382, "depth_max": 0.618,
    "impulse_min_atr": 3.0,
    "bars_after_high_min": 2, "bars_after_high_max": 15,
    "zone_atr": 0.5, "zone_min_factors": 2,
    "stop_atr_buffer": 0.25,
    "min_rr": 2.0, "r_atr_min": 0.75, "r_atr_max": 3.0,
}
BREAKOUT = {
    "ema": 100,
    "high_lookback": 21,        # 1 oylik cho'qqini yangilash
    "near_high_pct": 0.03,      # 3/6/12 oylik cho'qqiga 3% ichida
    "vol_mult": 1.5,
    "stop_lookback": 10,
    "stop_atr_buffer": 0.25,
    "target_r": 3.0,
    "r_atr_min": 0.75, "r_atr_max": 3.0,
}
TRADE = {
    "max_hold_days": 40,        # o'rta profil vaqt chegarasi
    "earnings_block_days": 5,   # hisobotga ≤5 savdo kuni qolsa kirilmaydi
    "commission_per_share": 0.005, "commission_min": 1.0,
    "slippage": 0.0005, "stop_slippage": 0.0005,
}

# ── Depozit himoyasi va portfel ──────────────────────────────────────────────
PORTFOLIO = {
    "start_equity": 10_000.0,
    "core_pct": 0.60,           # yadro (SPUS)
    "satellite_pct": 0.40,      # faol strategiyalar
    "risk_per_trade": 0.0075,   # umumiy kapitalning 0.75% i
    "max_open_risk": 0.05,      # barcha ochiq stoplar birdan urilsa ham ≤5%
    "max_position_pct": 0.15,   # bitta pozitsiya ≤ 15%
    "max_positions": 8,
    "max_per_sector": 2,
    "max_per_cluster": 2,       # korrelyatsiya klasteri (tema)
    "cluster_corr": 0.70,
    "satellite_cash_min": 0.20, # yo'ldosh qismining kamida 20% i naqd
    "dd_half_risk": -0.05,      # cho'qqidan −5% → risk yarmiga
    "dd_stop_buys": -0.10,      # cho'qqidan −10% → yangi xarid to'xtaydi
}

# ── Strategiyalar musobaqasi (9-modul) ───────────────────────────────────────
COMPETITION = {"rebalance": "monthly", "top_n": 10, "start_equity": 10_000.0}
STRATEGIES = {
    "stable_growth": {"rev_q": .10, "rev_y": .10, "rev_3y": .10, "eps_q": .10, "eps_y": .10,
                      "eps_3y": .10, "roe": .10, "mcap": 10e9},
    "hyper_growth": {"rev_q": .30, "rev_y": .30, "rev_3y": .30, "gross_margin": .50,
                     "current_ratio": 1.0, "de": 0.5, "mcap": 2e9},
    "canslim": {"eps_q": .25, "eps_3y": .25, "rs_pct": 80, "from_high": 0.15},
    "up_value": {"pb": 2.0, "pe": 15, "peg": 2.0, "eps_5y": 0.0, "roe": .05,
                 "current_ratio": 1.0, "de": 0.5, "piotroski": 5},
    "quality_dcf": {"pb": 4.0, "pe": 25, "roe": .05, "current_ratio": 1.0, "piotroski": 5},
    "healthy_cash": {"yield": .02, "div_growth": .02, "payout": .50, "eps_3y": .05,
                     "fcf_3y": .05, "fcf_margin": .05, "current_ratio": 1.0, "mcap": 2e9},
    "aristocrats": {"years_min": 25},
    "dogs_of_dow": {"n": 10},
    "pullback": {}, "breakout": {},
}
# Qiymat strategiyalariga trend filtri (AAP "qiymat tuzog'i" saboqi)
VALUE_TREND_FILTER = True

# Halollik (Uplift 4-modul, AAOIFI)
HALAL = {"debt_mcap_max": 0.30, "cash_mcap_max": 0.30, "interest_rev_max": 0.05}

# Teskari DCF
DCF = {"discount": 0.10, "terminal_growth": 0.03, "years": 10}

# Backtest
BACKTEST = {"split": 0.70, "random_runs": 300, "seed": 42,
            "decision": {"min_trades_test": 100, "min_expectancy_r": 0.10,
                         "min_profit_factor": 1.2, "random_pct": 95,
                         "max_dd": 0.20, "test_vs_train": 0.5}}

# O'rganish (xatolardan)
LEARN = {"min_trades": 30, "min_diff_r": 0.20}
