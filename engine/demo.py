"""Sun'iy (DEMO) ma'lumot: internetsiz sinov va ilova ko'rinishi uchun.

Natijalar haqiqiy bozorni aks ettirmaydi — ilova DEMO belgisini ko'rsatadi.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

SECTORS = list(C.SECTOR_TO_ETF.keys())


def _path(rng, n, mu, vol, start, market=None, beta=1.0):
    eps = rng.normal(0, vol, n)
    r = mu + eps + (beta * market if market is not None else 0)
    close = start * np.exp(np.cumsum(r))
    spread = np.abs(rng.normal(0, vol * 0.8, n)) + vol * 0.3
    open_ = close * np.exp(rng.normal(0, vol * 0.4, n))
    high = np.maximum(open_, close) * (1 + spread * rng.uniform(0.2, 1.0, n))
    low = np.minimum(open_, close) * (1 - spread * rng.uniform(0.2, 1.0, n))
    vol_ = rng.lognormal(14, 0.4, n) * (1 + 3 * np.abs(eps) / vol)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol_})


def make(tickers: list[str], years: int = 12, seed: int = 7) -> tuple[dict, dict, dict, dict]:
    rng = np.random.default_rng(seed)
    end = pd.Timestamp.today().normalize() - pd.offsets.BDay(1)
    idx = pd.bdate_range(end=end, periods=252 * years)
    n = len(idx)
    # bozor: bir necha rejim (o'sish, qulash, yon)
    regime_mu = np.zeros(n)
    k = 0
    while k < n:
        L = int(rng.integers(120, 500))
        regime_mu[k:k + L] = rng.choice([0.0008, 0.0005, -0.0012, 0.0001], p=[.45, .3, .1, .15])
        k += L
    market = regime_mu + rng.normal(0, 0.009, n)
    prices, fund, earn, divs = {}, {}, {}, {}

    def put(t, df):
        df.index = idx
        prices[t] = df

    put("SPY", _path(rng, n, 0, 0.002, 300, market, 1.0))
    put("SPUS", _path(rng, n, 0.00005, 0.003, 25, market, 1.05))
    put("QQQ", _path(rng, n, 0.0001, 0.003, 200, market, 1.25))
    put("DIA", _path(rng, n, 0, 0.003, 250, market, 0.85))
    put("IWM", _path(rng, n, -0.00005, 0.005, 150, market, 1.2))
    vix = 16 + 120 * pd.Series(-market).rolling(10, min_periods=1).mean().clip(lower=-0.05).to_numpy() * 10 + rng.normal(0, 1.2, n)
    vix = np.clip(vix, 10, 60)
    put("^VIX", pd.DataFrame({"open": vix, "high": vix * 1.04, "low": vix * 0.96, "close": vix, "volume": 0.0}))
    for etf in C.SECTOR_ETFS:
        put(etf, _path(rng, n, rng.normal(0, 0.0002), 0.004, 80, market, rng.uniform(0.6, 1.3)))
    for i, t in enumerate(tickers):
        sector = SECTORS[i % len(SECTORS)]
        mu = rng.normal(0.0001, 0.00025)
        put(t, _path(rng, n, mu, rng.uniform(0.011, 0.024), rng.uniform(20, 400), market, rng.uniform(0.6, 1.6)))
        q = pd.date_range(idx[0], idx[-1] + pd.Timedelta(days=60), freq="QS-JAN") + pd.Timedelta(days=int(rng.integers(20, 40)))
        earn[t] = [d.date().isoformat() for d in q]
        price = float(prices[t]["close"].iloc[-1])
        g = rng.normal(0.10, 0.12)
        fund[t] = {
            "name": f"Demo {t}", "sector": sector, "industry": sector, "price": price,
            "mcap": float(rng.lognormal(24.5, 1.0)), "rev_q": g + rng.normal(0, .05), "rev_y": g, "rev_3y": g * .9,
            "eps_q": g * 1.3 + rng.normal(0, .1), "eps_y": g * 1.2, "eps_3y": g * 1.1, "fcf_3y": g,
            "gross_margin": float(rng.uniform(.2, .8)), "op_margin": float(rng.uniform(.0, .35)),
            "net_margin": float(rng.uniform(-.05, .3)), "fcf_margin": float(rng.uniform(-.05, .3)),
            "roe": float(rng.uniform(-.05, .45)), "roa": float(rng.uniform(0, .2)),
            "current_ratio": float(rng.uniform(.7, 3.0)), "quick_ratio": float(rng.uniform(.5, 2.5)),
            "cash_ratio": float(rng.uniform(.1, 1.5)), "de": float(rng.uniform(0, 1.8)),
            "debt_assets": float(rng.uniform(0, .45)), "interest_cov": float(rng.uniform(1, 60)),
            "pe": float(rng.uniform(8, 60)), "pb": float(rng.uniform(1, 15)), "ps": float(rng.uniform(1, 15)),
            "pfcf": float(rng.uniform(8, 60)), "peg": float(rng.uniform(.5, 4)),
            "piotroski": float(rng.integers(2, 10)), "piotroski_items": [],
            "implied_growth": float(rng.uniform(-.05, .3)),
            "halal_debt": float(rng.uniform(0, .35)), "halal_cash": float(rng.uniform(0, .25)),
            "halal_income": float(rng.uniform(0, .04)), "interest_exp_rev": float(rng.uniform(0, .04)),
            "impure_per_share_q": float(rng.uniform(0, .3)),
            "div_yield": float(rng.choice([0, rng.uniform(.005, .045)])), "div_growth": float(rng.uniform(-.05, .12)),
            "div_years_up": int(rng.choice([0, 3, 12, 27, 52], p=[.4, .25, .2, .1, .05])),
            "payout": float(rng.uniform(.1, .8)), "insiders": float(rng.uniform(0, .2)),
            "institutions": float(rng.uniform(.4, .9)), "fetched": end.date().isoformat(),
        }
        fund[t]["halal_ok"] = fund[t]["halal_debt"] < .3 and fund[t]["halal_cash"] < .3
        if fund[t]["div_yield"] > 0:
            yrs = range(end.year - 30, end.year + 1)
            base = fund[t]["div_yield"] * price / 4 / (1.06 ** 30)
            divs[t] = {f"{y}-0{m}-15": base * (1.06 ** (y - end.year + 30)) for y in yrs for m in (2, 5, 8)}
    return prices, fund, earn, divs
