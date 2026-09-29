"""2-qadam mantiqining testlari (internetsiz, sun'iy ma'lumotda)."""
import numpy as np
import pandas as pd
import pytest

from src.checks import quality_report
from src.prices import _split, to_4h
from src.universe import load_snapshot, parse_holdings

TZ = "America/New_York"


def hourly_day(day: str, close_at: str = "16:00", base: float = 100.0) -> pd.DataFrame:
    """Bir kunlik yfinance uslubidagi 60m shamlar: 09:30, 10:30, ... (oxirgisi yarim soat)."""
    starts = pd.date_range(f"{day} 09:30", f"{day} {close_at}", freq="60min", tz=TZ, inclusive="left")
    n = len(starts)
    o = base + np.arange(n)
    return pd.DataFrame(
        {"open": o, "high": o + 2, "low": o - 1, "close": o + 1, "volume": np.full(n, 1000)},
        index=starts,
    )


def test_regular_day_gives_two_bars():
    b = to_4h(hourly_day("2026-09-15"))
    assert list(b.index.strftime("%H:%M")) == ["09:30", "13:30"]
    first, second = b.iloc[0], b.iloc[1]
    assert first["n_1h"] == 4 and second["n_1h"] == 3          # 09:30–12:30 va 13:30–15:30
    assert first["open"] == 100 and first["close"] == 104      # birinchi open, oxirgi close
    assert first["high"] == 105 and first["low"] == 99
    assert first["volume"] == 4000 and second["volume"] == 3000
    assert second["end"].strftime("%H:%M") == "16:00"


def test_half_day_gives_one_bar():
    b = to_4h(hourly_day("2026-11-27", close_at="13:00"))      # Shukrona kunidan keyingi qisqa kun
    assert len(b) == 1 and b.iloc[0]["n_1h"] == 4


def test_dst_change_keeps_session_times():
    df = pd.concat([hourly_day("2026-10-30"), hourly_day("2026-11-02")])  # yozgi vaqt tugashi oralig'i
    b = to_4h(df)
    assert list(b.index.strftime("%H:%M")) == ["09:30", "13:30"] * 2


def test_unfinished_bar_is_dropped():
    df = hourly_day("2026-09-15")
    now = pd.Timestamp("2026-09-15 15:00", tz=TZ)              # ikkinchi sham hali yopilmagan
    b = to_4h(df.loc[:now], now=now)
    assert len(b) == 1 and b.index[0].strftime("%H:%M") == "09:30"


def test_premarket_rows_ignored():
    df = hourly_day("2026-09-15")
    extra = pd.DataFrame({"open": [1], "high": [1], "low": [1], "close": [1], "volume": [1]},
                         index=pd.DatetimeIndex([pd.Timestamp("2026-09-15 08:30", tz=TZ)]))
    b = to_4h(pd.concat([extra, df]))
    assert b.iloc[0]["open"] == 100


def test_split_multiindex_and_daily_dates():
    idx = pd.DatetimeIndex(["2026-09-14", "2026-09-15"])
    cols = pd.MultiIndex.from_product([["QQQ", "SPY"], ["Open", "High", "Low", "Close", "Volume"]])
    raw = pd.DataFrame(np.ones((2, 10)), index=idx, columns=cols)
    out = _split(raw, ["QQQ", "SPY", "XXX"], intraday=False)
    assert set(out) == {"QQQ", "SPY"}
    assert out["QQQ"].index[0] == pd.Timestamp("2026-09-14") and out["QQQ"].index.tz is None
    assert list(out["QQQ"].columns) == ["open", "high", "low", "close", "volume"]


SAMPLE_CSV = """Date,Account,StockTicker,SecurityName,CUSIP,Shares,Price,MarketValue,Weightings,NetAssets,SharesOutstanding,CreationUnits
09/29/2026,SPUS,NVDA,NVIDIA Corp,67066G104,"2,018,738.00",228.86,"462,008,378.68",14.13,3268804950,54750000,2190
09/29/2026,SPUS,AAPL,Apple Inc,037833100,"1,217,423.00",338.40,"411,975,943.20",12.60,3268804950,54750000,2190
09/29/2026,SPUS,Cash&Other,Cash & Other,Cash&Other,"6,739,995.00",1.00,"6,739,994.58",0.21,3268804950,54750000,2190
09/29/2026,SPUS,003654100CVR,ABIOMED INC,003654100CVR,405.00,0.00,0.00,0.00,3268804950,54750000,2190
09/29/2026,SPUS,2602335D,TPG Inc,BBG01Y2F01K3,"14,708.00",0.00,0.00,0.00,3268804950,54750000,2190
09/29/2026,SPUS,BRK.B,Example Class B,000000000,1.00,1.00,1.00,0.01,3268804950,54750000,2190
09/29/2026,SPUS,A,Agilent Technologies Inc,00846U101,"24,286.00",175.21,"4,255,150.06",0.13,3268804950,54750000,2190
"""


def test_parse_holdings_filters_non_stocks():
    df = parse_holdings(SAMPLE_CSV)
    assert list(df["ticker"]) == ["NVDA", "AAPL", "A", "BRK.B"]
    assert df.loc[df["ticker"] == "BRK.B", "yf_ticker"].item() == "BRK-B"
    assert df["weight"].iloc[0] == pytest.approx(14.13)


def test_snapshot_loads():
    df, name = load_snapshot()
    assert len(df) >= 200 and df["ticker"].is_unique and "NVDA" in set(df["ticker"])


def test_quality_report_flags_gaps_and_jumps():
    days = pd.bdate_range("2025-01-02", periods=250)
    ref = pd.concat([hourly_day(d.date().isoformat()) for d in days])
    ref4 = to_4h(ref)
    stock4 = ref4.drop(ref4.index[10:30]).copy()               # 20 ta sham yo'q
    stock4.iloc[-1, stock4.columns.get_loc("close")] *= 2       # keskin sakrash
    q = quality_report({"QQQ": ref4, "TEST": stock4}).set_index("ticker")
    assert q.loc["QQQ", "status"] == "ok"
    assert q.loc["TEST", "missing"] == 20
    assert "keskin sakrash" in q.loc["TEST", "status"]
