"""Dvigatel testlari (internetsiz). Ishga tushirish: python -m pytest -q"""
import json
import math

import numpy as np
import pandas as pd
import pytest

from engine import config as C
from engine import portfolio as PF
from engine.data import clean, parse_holdings, write_json
from engine.fundamentals import compute_metrics, dividend_metrics, piotroski, reverse_dcf
from engine.indicators import add_all, atr, pivots
from engine.market import regime_series
from engine.signals import SwingTracker, _candle, explain_last, scan


def frame(close, spread=0.01, vol=1e6, start="2020-01-01"):
    c = np.asarray(close, dtype=float)
    idx = pd.bdate_range(start, periods=len(c))
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * (1 + spread), "low": np.minimum(o, c) * (1 - spread),
                         "close": c, "volume": np.full(len(c), vol)}, index=idx)


# ── indikatorlar ─────────────────────────────────────────────────────────────
def test_pivot_confirmed_only_after_n_bars():
    c = [10, 11, 12, 15, 12, 11, 10, 9, 10]
    df = frame(c, 0)
    df["high"], df["low"] = df["close"] + .1, df["close"] - .1
    ph, _ = pivots(df, 3)
    assert ph.notna().sum() == 1
    assert ph.index.get_loc(ph.first_valid_index()) == 3 + 3          # cho'qqi 3-kunda, tasdiq 6-kunda
    assert ph.dropna().iloc[0] == pytest.approx(15.1)


def test_no_lookahead_in_indicators():
    rng = np.random.default_rng(1)
    df = frame(100 * np.exp(np.cumsum(rng.normal(0, .01, 600))))
    full = add_all(df)
    cut = add_all(df.iloc[:400])
    for col in ("ema20", "sma150", "atr", "rsi", "hi252", "stage"):
        a, b = full[col].iloc[:400], cut[col]
        assert np.allclose(a.fillna(-1), b.fillna(-1)), col


def test_atr_positive():
    df = frame(np.linspace(10, 20, 100))
    assert (atr(df).dropna() > 0).all()


# ── signallar ────────────────────────────────────────────────────────────────
def test_candle_patterns():
    assert _candle(10, 10.2, 9.0, 10.1, 10.5, 10.3, 10.6) == "bolg'a"
    assert _candle(9.9, 10.6, 9.8, 10.5, 10.4, 10.0, 10.45) == "yutuvchi sham"
    assert _candle(10, 10.6, 9.95, 10.55, 10.1, 10.2, 10.4) == "oldingi cho'qqi ustida yopilish"
    assert _candle(10, 10.1, 9.9, 10.0, 10.0, 10.0, 10.2) is None


def test_swing_tracker_alternates_and_filters_noise():
    rng = np.random.default_rng(3)
    df = add_all(frame(100 * np.exp(np.cumsum(rng.normal(0.0005, .015, 500)))))
    st = SwingTracker(df["high"].values, df["low"].values, df["atr"].values, 3, 1.0)
    for t in range(len(df)):
        st.step(t)
    types = [p[1] for p in st.pts]
    assert all(a != b for a, b in zip(types, types[1:]))               # H va L navbatma-navbat
    assert len(st.pts) > 10


def test_scan_and_explain_shapes():
    rng = np.random.default_rng(5)
    df = add_all(frame(50 * np.exp(np.cumsum(rng.normal(0.0008, .015, 900))), vol=2e6))
    s = scan(df)
    assert set(s.columns) >= {"t", "date", "kind", "stop", "target"} if len(s) else True
    for r in s.itertuples():
        c = df["close"].iat[r.t]
        assert r.stop < c < r.target                                     # reja mantiqiy
    ex = explain_last(df)
    assert {"pullback", "breakout", "swings"} <= set(ex)
    assert all("t" in c and "ok" in c for c in ex["pullback"]["checks"])


# ── bozor rejimi ──────────────────────────────────────────────────────────────
def test_regime_red_after_crash_green_in_uptrend():
    wig = lambda n: 3 * np.sin(np.arange(n) / 3)  # noqa: E731 — pivotlar paydo bo'lishi uchun tebranish
    up = frame(np.linspace(100, 200, 400) + wig(400), 0.005)
    assert regime_series(up)["regime"].iloc[-1] == "green"
    crash = frame(np.r_[np.linspace(100, 200, 400), np.linspace(200, 120, 60)] + wig(460), 0.005)
    assert regime_series(crash)["regime"].iloc[-1] == "red"


# ── fundamental ──────────────────────────────────────────────────────────────
def _stmt(rows: dict, n=4):
    cols = pd.to_datetime([f"{2025 - k}-12-31" for k in range(n)])
    return pd.DataFrame(rows, index=cols).T


def test_piotroski_perfect_and_bad():
    inc = _stmt({"Net Income": [120, 100, 80, 60], "Total Revenue": [1000, 900, 800, 700], "Gross Profit": [500, 430, 380, 330]})
    bal = _stmt({"Total Assets": [1000, 1000, 950, 900], "Long Term Debt": [100, 150, 160, 170], "Current Assets": [400, 350, 300, 300],
                 "Current Liabilities": [200, 200, 200, 200], "Ordinary Shares Number": [100, 100, 101, 102]})
    cf = _stmt({"Operating Cash Flow": [150, 120, 90, 70]})
    score, items = piotroski(inc, bal, cf)
    assert score == 9 and len(items) == 9
    inc2 = _stmt({"Net Income": [-10, 100, 80, 60], "Total Revenue": [800, 900, 800, 700], "Gross Profit": [300, 430, 380, 330]})
    cf2 = _stmt({"Operating Cash Flow": [-20, 120, 90, 70]})
    bal2 = _stmt({"Total Assets": [1100, 1000, 950, 900], "Long Term Debt": [300, 150, 160, 170], "Current Assets": [300, 350, 300, 300],
                  "Current Liabilities": [250, 200, 200, 200], "Ordinary Shares Number": [120, 100, 101, 102]})
    assert piotroski(inc2, bal2, cf2)[0] == 0


def test_reverse_dcf_roundtrip():
    r, tg, fcf, g = .10, .03, 100.0, .12
    f, pv = fcf, 0.0
    for y in range(1, 11):
        f *= 1 + (g if y <= 5 else g / 2)
        pv += f / (1 + r) ** y
    ev = pv + f * (1 + tg) / (r - tg) / (1 + r) ** 10
    assert reverse_dcf(fcf, ev) == pytest.approx(g, abs=1e-4)
    assert math.isnan(reverse_dcf(-5, 1000))


def test_dividend_years_and_yield():
    divs = {f"{y}-03-01": 1.0 + 0.1 * (y - 1990) for y in range(1990, 2026)}
    m = dividend_metrics(divs, price=100, today=pd.Timestamp("2026-06-01").date())
    assert m["div_years_up"] == 2025 - 1990
    m2 = dividend_metrics({"2024-03-01": 2.0, "2025-03-01": 1.5}, 100, pd.Timestamp("2026-01-10").date())
    assert m2["div_years_up"] == 0


def test_compute_metrics_halal_and_ratios():
    q = pd.to_datetime(["2025-09-30", "2025-06-30", "2025-03-31", "2024-12-31", "2024-09-30"])
    qinc = pd.DataFrame({"Total Revenue": [130, 120, 110, 100, 100], "Net Income": [26, 24, 22, 20, 18],
                         "Gross Profit": [65, 60, 55, 50, 50], "Operating Income": [30, 28, 26, 24, 22],
                         "Diluted EPS": [1.3, 1.2, 1.1, 1.0, 1.0], "Interest Expense": [1, 1, 1, 1, 1],
                         "Interest Income": [2, 2, 2, 2, 2]}, index=q).T
    qbal = pd.DataFrame({"Total Assets": [1000] * 5, "Current Assets": [400] * 5, "Current Liabilities": [200] * 5,
                         "Stockholders Equity": [500] * 5, "Total Debt": [100] * 5,
                         "Cash Cash Equivalents And Short Term Investments": [150] * 5,
                         "Ordinary Shares Number": [100] * 5}, index=q).T
    qcf = pd.DataFrame({"Free Cash Flow": [20, 20, 20, 20, 20]}, index=q).T
    m = compute_metrics({"qinc": qinc, "qbal": qbal, "qcf": qcf}, price=20.0, avg_mcap_24m=2000.0)
    assert m["rev_ttm"] == 460 and m["rev_q"] == pytest.approx(0.30)
    assert m["roe"] == pytest.approx(92 / 500)
    assert m["halal_debt"] == pytest.approx(100 / 2000) and m["halal_ok"]
    assert m["halal_income"] == pytest.approx(8 / 460)
    assert m["pe"] == pytest.approx(20 / 4.6)
    m2 = compute_metrics({"qinc": qinc, "qbal": qbal.replace({100: 900}), "qcf": qcf}, 20.0, 2000.0)
    assert m2["halal_debt"] > .3 and not m2["halal_ok"]


# ── portfel va depozit himoyasi ──────────────────────────────────────────────
def _F(closes: dict, opens=None, lows=None, highs=None):
    idx = pd.bdate_range("2024-01-01", periods=len(next(iter(closes.values()))))
    c = pd.DataFrame(closes, index=idx)
    o = pd.DataFrame(opens, index=idx) if opens else c
    lo = pd.DataFrame(lows, index=idx) if lows else c * .99
    hi = pd.DataFrame(highs, index=idx) if highs else c * 1.01
    return {"index": idx, "close": c, "open": o, "low": lo, "high": hi}


def test_position_sizing_risk_and_caps():
    F = _F({"AAA": [100.0] * 5, "BBB": [50.0] * 5})
    s = PF.new_state({"core_pct": 0.0})
    cands = [{"ticker": "AAA", "kind": "pullback", "stop": 98.0, "target": 106.0, "score": 90}]
    PF.step(s, F, 0, cands, {"allow_buys": True, "risk_mult": 1.0}, {"AAA": "Tech"}, {})
    o = s["pending"][0]
    # risk 0.75% × 10 000 = 75$ / R 2$ = 37 aksiya, lekin pozitsiya ≤15% → 15 aksiya
    assert o["shares"] == 15


def test_stop_gap_fills_at_open_not_stop():
    F = _F({"AAA": [100, 100, 90, 90]}, opens={"AAA": [100, 100, 88, 90]}, lows={"AAA": [99, 99, 87, 89]})
    s = PF.new_state({"core_pct": 0.0, "max_position_pct": 1.0})
    PF.step(s, F, 0, [{"ticker": "AAA", "kind": "breakout", "stop": 95.0, "target": 115.0}], {"allow_buys": True}, {}, {})
    PF.step(s, F, 1, [], {"allow_buys": True}, {}, {})
    assert len(s["positions"]) == 1
    PF.step(s, F, 2, [], {"allow_buys": True}, {}, {})
    tr = s["trades"][0]
    assert tr["why"] == "stop" and tr["exit"] < 88.01 and tr["r"] < -2           # gap: zarar 1R dan katta


def test_market_red_blocks_buys_and_drawdown_brake():
    F = _F({"AAA": [100.0] * 3})
    s = PF.new_state({"core_pct": 0.0})
    c = [{"ticker": "AAA", "kind": "pullback", "stop": 98.0, "target": 106.0}]
    PF.step(s, F, 0, c, {"allow_buys": False}, {}, {})
    assert s["pending"] == []
    s2 = PF.new_state({"core_pct": 0.0})
    s2["peak"] = 12_000                                                  # cho'qqidan −16%
    PF.step(s2, F, 0, c, {"allow_buys": True}, {}, {})
    assert s2["pending"] == [] and s2["protection"]["status"] == "to'xtatilgan"


def test_sector_cap():
    F = _F({t: [100.0] * 2 for t in ("A1", "A2", "A3")})
    s = PF.new_state({"core_pct": 0.0, "max_per_cluster": 99})
    c = [{"ticker": t, "kind": "pullback", "stop": 99.0, "target": 103.0, "score": 90 - k} for k, t in enumerate(("A1", "A2", "A3"))]
    s["positions"] = [{"ticker": "A1", "kind": "x", "entry": 100, "stop": 95, "target": 103, "shares": 1, "R": 1,
                       "entry_date": "2024-01-01", "days": 0}]
    PF.step(s, F, 1, c, {"allow_buys": True}, {"A1": "Tech", "A2": "Tech", "A3": "Tech"}, {})
    assert [o["ticker"] for o in s["pending"]] == ["A2"]                  # sektorda ko'pi bilan 2 ta


def test_core_satellite_split():
    F = _F({"AAA": [100.0] * 2})
    s = PF.new_state()
    PF.step(s, F, 0, [], {"allow_buys": True}, {}, {}, core_close=50.0)
    assert s["core_shares"] * 50 == pytest.approx(6000, rel=1e-3)
    assert s["equity"][-1][1] == pytest.approx(10_000, abs=2)


def test_competition_monthly_rebalance():
    s = PF.comp_new("x")
    PF.comp_step(s, pd.Timestamp("2026-01-05"), {"A": 10, "B": 20}, ["A", "B"])
    assert set(s["holdings"]) == {"A", "B"}
    PF.comp_step(s, pd.Timestamp("2026-01-20"), {"A": 10, "B": 20, "C": 5}, ["C"])
    assert set(s["holdings"]) == {"A", "B"}                              # oy ichida qayta taqsimlanmaydi
    PF.comp_step(s, pd.Timestamp("2026-02-02"), {"A": 10, "B": 20, "C": 5}, ["C"])
    assert set(s["holdings"]) == {"C"}


def test_stats_expectancy():
    st = PF.stats([{"r": 2.0, "days": 3}, {"r": -1.0, "days": 2}, {"r": -1.0, "days": 1}], [["a", 100], ["b", 90], ["c", 95]])
    assert st["expectancy"] == pytest.approx(0) and st["max_losing_streak"] == 2 and st["max_dd"] == pytest.approx(-.1)


# ── ma'lumot yordamchilari ───────────────────────────────────────────────────
def test_clean_json_has_no_nan(tmp_path):
    p = tmp_path / "x.json"
    write_json(p, {"a": float("nan"), "b": [np.float64(1.5), np.int64(2)], "c": np.bool_(True)})
    assert json.loads(p.read_text()) == {"a": None, "b": [1.5, 2], "c": True}
    assert clean({"x": float("inf")}) == {"x": None}


def test_parse_holdings_filters_cash_and_codes():
    csv = ("Date,Account,StockTicker,SecurityName,Weightings\n"
           "1,SPUS,NVDA,NVIDIA,14.1\n1,SPUS,Cash&Other,Cash,0.2\n1,SPUS,003654100CVR,X,0\n1,SPUS,BRK.B,Y,0.1\n")
    df = parse_holdings(csv)
    assert list(df["ticker"]) == ["NVDA", "BRK.B"] and df["yf"].iloc[1] == "BRK-B"


def test_config_sane():
    p = C.PORTFOLIO
    assert abs(p["core_pct"] + p["satellite_pct"] - 1) < 1e-9
    assert 0 < p["risk_per_trade"] <= 0.01 and p["max_open_risk"] <= 0.05
    assert C.WATCH_MID_EXIT["rs_pct_below"] < C.WATCH_MID_ENTRY["rs_pct_min"]          # gisterezis
    assert C.WATCH_MID_EXIT["from_high_over"] > C.WATCH_MID_ENTRY["from_high_max"]


@pytest.mark.slow
def test_pipeline_demo_end_to_end(tmp_path):
    from engine import pipeline
    old = C.STATE
    try:
        out = tmp_path / "data"
        summary = pipeline.run(demo=True, publish_dir=out, warmup_days=40)
        for f in ("meta.json", "market.json", "scores.json", "watchlist.json", "portfolio.json", "competition.json", "learn.json"):
            json.loads((out / f).read_text())
        assert summary["date"] and len(list((out / "cards").glob("*.json"))) > 100
        meta = json.loads((out / "meta.json").read_text())
        assert meta["demo"] is True
    finally:
        C.STATE = old
