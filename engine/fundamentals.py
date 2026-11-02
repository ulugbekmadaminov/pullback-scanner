"""Fundamental ko'rsatkichlar: rentabellik, o'sish, moliyaviy sog'lomlik, baholash,
Piotroski F-score, halollik koeffitsiyentlari (Uplift 4-modul), teskari DCF, dividend tarixi.

Hisoblash qismi (compute_metrics) faqat jadvallar bilan ishlaydi — tarmoqsiz sinaladi.
Barcha nisbatlar kasr ko'rinishida (0.25 = 25%).
"""
from __future__ import annotations

import math
import time
from datetime import date

import numpy as np
import pandas as pd

from . import config as C


def _row(df: pd.DataFrame | None, *names: str) -> pd.Series | None:
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.index:
            s = pd.to_numeric(df.loc[n], errors="coerce")
            s = s[~s.index.duplicated()].sort_index(ascending=False)   # eng yangisi birinchi
            return s
    return None


def _v(s: pd.Series | None, i: int = 0) -> float:
    if s is None or len(s) <= i:
        return float("nan")
    x = s.iloc[i]
    return float(x) if pd.notna(x) else float("nan")


def _ttm(s: pd.Series | None) -> float:
    if s is None or len(s.dropna()) < 4:
        return float("nan")
    return float(s.dropna().iloc[:4].sum())


def _g(new: float, old: float) -> float:
    if not (math.isfinite(new) and math.isfinite(old)) or old <= 0:
        return float("nan")
    return new / old - 1


def _cagr(new: float, old: float, years: int) -> float:
    if not (math.isfinite(new) and math.isfinite(old)) or old <= 0 or new <= 0:
        return float("nan")
    return (new / old) ** (1 / years) - 1


def _div(a: float, b: float) -> float:
    return a / b if math.isfinite(a) and math.isfinite(b) and b != 0 else float("nan")


def piotroski(inc: pd.DataFrame, bal: pd.DataFrame, cf: pd.DataFrame) -> tuple[float, list[dict]]:
    """Piotroski F-score (0–9) oxirgi ikki yillik hisobotdan. Har bir band izohi bilan qaytadi."""
    ni, cfo = _row(inc, "Net Income", "Net Income Common Stockholders"), _row(cf, "Operating Cash Flow")
    ta, ltd = _row(bal, "Total Assets"), _row(bal, "Long Term Debt")
    ca, cl = _row(bal, "Current Assets"), _row(bal, "Current Liabilities")
    sh = _row(bal, "Ordinary Shares Number", "Share Issued")
    rev, gp = _row(inc, "Total Revenue"), _row(inc, "Gross Profit")
    if ni is None or ta is None or len(ta) < 2:
        return float("nan"), []
    roa0, roa1 = _div(_v(ni), _v(ta)), _div(_v(ni, 1), _v(ta, 1))
    items = [
        ("Sof foyda > 0", _v(ni) > 0),
        ("Operatsion pul oqimi > 0", _v(cfo) > 0),
        ("ROA yaxshilangan", roa0 > roa1),
        ("Operatsion pul oqimi > sof foyda", _v(cfo) > _v(ni)),
        ("Uzoq muddatli qarz / aktivlar kamaygan",
         _div(_v(ltd) if math.isfinite(_v(ltd)) else 0, _v(ta)) <= _div(_v(ltd, 1) if math.isfinite(_v(ltd, 1)) else 0, _v(ta, 1))),
        ("Joriy nisbat yaxshilangan", _div(_v(ca), _v(cl)) > _div(_v(ca, 1), _v(cl, 1))),
        ("Aksiyalar soni ko'paymagan", _v(sh) <= _v(sh, 1) * 1.005 if math.isfinite(_v(sh, 1)) else False),
        ("Yalpi marja yaxshilangan", _div(_v(gp), _v(rev)) > _div(_v(gp, 1), _v(rev, 1))),
        ("Aktivlar aylanmasi yaxshilangan", _div(_v(rev), _v(ta)) > _div(_v(rev, 1), _v(ta, 1))),
    ]
    out = [{"t": t, "ok": bool(ok)} for t, ok in items]
    return float(sum(1 for x in out if x["ok"])), out


def reverse_dcf(fcf: float, ev: float, r: float = C.DCF["discount"], tg: float = C.DCF["terminal_growth"],
                years: int = C.DCF["years"]) -> float:
    """Bugungi narx qanday yillik FCF o'sishini (1–5 yil g, 6–10 yil g/2) hisobga olgan?"""
    if not (math.isfinite(fcf) and math.isfinite(ev)) or fcf <= 0 or ev <= 0:
        return float("nan")

    def value(g: float) -> float:
        f, pv = fcf, 0.0
        for y in range(1, years + 1):
            f *= 1 + (g if y <= years // 2 else g / 2)
            pv += f / (1 + r) ** y
        tv = f * (1 + tg) / (r - tg)
        return pv + tv / (1 + r) ** years

    lo, hi = -0.5, 1.5
    if value(hi) < ev:
        return hi
    if value(lo) > ev:
        return lo
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if value(mid) < ev else (lo, mid)
    return (lo + hi) / 2


def dividend_metrics(divs: dict[str, float] | None, price: float, today: date | None = None) -> dict:
    """Dividend daromadi, o'sishi va uzluksiz oshirilgan yillar (Aristokrat/Qirol tegi)."""
    out = {"div_yield": 0.0, "div_growth": float("nan"), "div_years_up": 0, "div_ttm": 0.0}
    if not divs:
        return out
    s = pd.Series(divs)
    s.index = pd.to_datetime(s.index)
    today = today or date.today()
    ttm = s[s.index > pd.Timestamp(today) - pd.Timedelta(days=365)].sum()
    out["div_ttm"] = float(ttm)
    out["div_yield"] = _div(float(ttm), price) if price else 0.0
    yearly = s.groupby(s.index.year).sum()
    yearly = yearly[yearly.index < today.year]              # joriy (to'liq bo'lmagan) yil hisoblanmaydi
    if len(yearly) >= 2:
        out["div_growth"] = _g(float(yearly.iloc[-1]), float(yearly.iloc[-2]))
        n = 0
        vals = yearly.values
        for i in range(len(vals) - 1, 0, -1):
            if vals[i] > vals[i - 1] * 1.001:
                n += 1
            else:
                break
        out["div_years_up"] = n
    return out


def compute_metrics(st: dict, price: float, avg_mcap_24m: float, info: dict | None = None,
                    divs: dict | None = None, today: date | None = None) -> dict:
    """st: {'inc','qinc','bal','qbal','cf','qcf'} → bitta aksiya uchun ko'rsatkichlar lug'ati."""
    info = info or {}
    inc, qinc, bal, qbal, cf, qcf = (st.get(k) for k in ("inc", "qinc", "bal", "qbal", "cf", "qcf"))
    rev_a, rev_q = _row(inc, "Total Revenue"), _row(qinc, "Total Revenue")
    eps_a, eps_q = _row(inc, "Diluted EPS", "Basic EPS"), _row(qinc, "Diluted EPS", "Basic EPS")
    ni_a, ni_q = _row(inc, "Net Income", "Net Income Common Stockholders"), _row(qinc, "Net Income", "Net Income Common Stockholders")
    gp_q, op_q = _row(qinc, "Gross Profit"), _row(qinc, "Operating Income")
    gp_a, op_a = _row(inc, "Gross Profit"), _row(inc, "Operating Income")
    intexp_q, intinc_q = _row(qinc, "Interest Expense"), _row(qinc, "Interest Income")
    intexp_a, intinc_a = _row(inc, "Interest Expense"), _row(inc, "Interest Income")
    b = qbal if qbal is not None and not qbal.empty else bal
    ta, ca, cl = _row(b, "Total Assets"), _row(b, "Current Assets"), _row(b, "Current Liabilities")
    inv, eq = _row(b, "Inventory"), _row(b, "Stockholders Equity", "Common Stock Equity")
    debt = _row(b, "Total Debt")
    cash = _row(b, "Cash And Cash Equivalents")
    cash_sti = _row(b, "Cash Cash Equivalents And Short Term Investments")
    sti = _row(b, "Other Short Term Investments")
    shares = _row(b, "Ordinary Shares Number", "Share Issued")
    fcf_a, fcf_q = _row(cf, "Free Cash Flow"), _row(qcf, "Free Cash Flow")

    rev_ttm = _ttm(rev_q) if math.isfinite(_ttm(rev_q)) else _v(rev_a)
    ni_ttm = _ttm(ni_q) if math.isfinite(_ttm(ni_q)) else _v(ni_a)
    eps_ttm = _ttm(eps_q) if math.isfinite(_ttm(eps_q)) else _v(eps_a)
    fcf_ttm = _ttm(fcf_q) if math.isfinite(_ttm(fcf_q)) else _v(fcf_a)
    gp_ttm = _ttm(gp_q) if math.isfinite(_ttm(gp_q)) else _v(gp_a)
    op_ttm = _ttm(op_q) if math.isfinite(_ttm(op_q)) else _v(op_a)
    ie_ttm = _ttm(intexp_q) if math.isfinite(_ttm(intexp_q)) else _v(intexp_a)
    ii_ttm = _ttm(intinc_q) if math.isfinite(_ttm(intinc_q)) else _v(intinc_a)
    sh = _v(shares) if math.isfinite(_v(shares)) else float(info.get("sharesOutstanding") or float("nan"))
    mcap = price * sh if math.isfinite(sh) else float(info.get("marketCap") or float("nan"))
    tdebt = _v(debt) if math.isfinite(_v(debt)) else 0.0
    c_sti = _v(cash_sti) if math.isfinite(_v(cash_sti)) else (_v(cash) if math.isfinite(_v(cash)) else 0.0) + (_v(sti) if math.isfinite(_v(sti)) else 0.0)
    equity = _v(eq)

    m: dict = {}
    m["rev_ttm"], m["ni_ttm"], m["eps_ttm"], m["fcf_ttm"] = rev_ttm, ni_ttm, eps_ttm, fcf_ttm
    m["mcap"] = mcap
    m["rev_q"] = _g(_v(rev_q, 0), _v(rev_q, 4))
    m["eps_q"] = _g(_v(eps_q, 0), _v(eps_q, 4))
    m["rev_y"] = _g(_v(rev_a, 0), _v(rev_a, 1))
    m["eps_y"] = _g(_v(eps_a, 0), _v(eps_a, 1))
    n_a = len(rev_a.dropna()) if rev_a is not None else 0
    k = min(3, max(n_a - 1, 0))
    m["rev_3y"] = _cagr(_v(rev_a, 0), _v(rev_a, k), k) if k >= 2 else float("nan")
    m["eps_3y"] = _cagr(_v(eps_a, 0), _v(eps_a, k), k) if k >= 2 else float("nan")
    m["fcf_3y"] = _cagr(_v(fcf_a, 0), _v(fcf_a, k), k) if k >= 2 else float("nan")
    m["gross_margin"] = _div(gp_ttm, rev_ttm)
    m["op_margin"] = _div(op_ttm, rev_ttm)
    m["net_margin"] = _div(ni_ttm, rev_ttm)
    m["fcf_margin"] = _div(fcf_ttm, rev_ttm)
    m["roe"] = _div(ni_ttm, equity) if math.isfinite(equity) and equity > 0 else float("nan")
    m["roa"] = _div(ni_ttm, _v(ta))
    m["current_ratio"] = _div(_v(ca), _v(cl))
    m["quick_ratio"] = _div(_v(ca) - (_v(inv) if math.isfinite(_v(inv)) else 0), _v(cl))
    m["cash_ratio"] = _div(c_sti, _v(cl))
    m["de"] = _div(tdebt, equity) if math.isfinite(equity) and equity > 0 else float("nan")
    m["debt_assets"] = _div(tdebt, _v(ta))
    m["interest_cov"] = _div(op_ttm, abs(ie_ttm)) if math.isfinite(ie_ttm) and ie_ttm != 0 else float("nan")
    m["pe"] = _div(price, eps_ttm) if math.isfinite(eps_ttm) and eps_ttm > 0 else float("nan")
    m["pb"] = _div(mcap, equity) if math.isfinite(equity) and equity > 0 else float("nan")
    m["ps"] = _div(mcap, rev_ttm)
    m["pfcf"] = _div(mcap, fcf_ttm) if fcf_ttm > 0 else float("nan")
    g = m["eps_3y"]
    m["peg"] = _div(m["pe"], g * 100) if math.isfinite(g) and g > 0 else float("nan")
    m["piotroski"], m["piotroski_items"] = piotroski(inc, bal, cf)
    ev = mcap + tdebt - c_sti if math.isfinite(mcap) else float("nan")
    m["implied_growth"] = reverse_dcf(fcf_ttm, ev)
    # Halollik (Uplift 4-modul): 24 oylik o'rtacha bozor kapitallashuviga nisbatan
    base = avg_mcap_24m if math.isfinite(avg_mcap_24m) and avg_mcap_24m > 0 else mcap
    m["halal_debt"] = _div(tdebt, base)
    m["halal_cash"] = _div(c_sti, base)
    m["halal_income"] = _div(ii_ttm, rev_ttm) if math.isfinite(ii_ttm) else 0.0
    m["interest_exp_rev"] = _div(abs(ie_ttm), rev_ttm) if math.isfinite(ie_ttm) else 0.0
    m["halal_ok"] = bool(
        (not math.isfinite(m["halal_debt"]) or m["halal_debt"] < C.HALAL["debt_mcap_max"])
        and (not math.isfinite(m["halal_cash"]) or m["halal_cash"] < C.HALAL["cash_mcap_max"])
        and (not math.isfinite(m["halal_income"]) or m["halal_income"] < C.HALAL["interest_rev_max"]))
    # Tozalash uchun: so'nggi chorakdagi nomaqbul daromad (foiz daromadi) aksiya boshiga
    ii_last = _v(intinc_q) if math.isfinite(_v(intinc_q)) else _div(ii_ttm, 4)
    m["impure_per_share_q"] = _div(ii_last, sh) if math.isfinite(ii_last) and ii_last > 0 else 0.0
    m.update(dividend_metrics(divs, price, today))
    pr = info.get("payoutRatio")
    m["payout"] = float(pr) if isinstance(pr, (int, float)) else _div(m["div_ttm"], eps_ttm)
    m["insiders"] = float(info.get("heldPercentInsiders") or float("nan"))
    m["institutions"] = float(info.get("heldPercentInstitutions") or float("nan"))
    return m


def fetch_one(ticker: str, price: float, avg_mcap_24m: float, divs: dict | None) -> dict:
    import yfinance as yf
    tk = yf.Ticker(ticker)
    st = {}
    for k, attr in (("inc", "income_stmt"), ("qinc", "quarterly_income_stmt"), ("bal", "balance_sheet"),
                    ("qbal", "quarterly_balance_sheet"), ("cf", "cashflow"), ("qcf", "quarterly_cashflow")):
        try:
            st[k] = getattr(tk, attr)
        except Exception:  # noqa: BLE001
            st[k] = None
    try:
        info = tk.info or {}
    except Exception:  # noqa: BLE001
        info = {}
    m = compute_metrics(st, price, avg_mcap_24m, info, divs)
    m["sector"] = info.get("sector") or ""
    m["industry"] = info.get("industry") or ""
    m["name"] = info.get("shortName") or info.get("longName") or ticker
    m["fetched"] = date.today().isoformat()
    return m


def refresh(fund: dict, tickers: list[str], prices: dict[str, pd.DataFrame], divs: dict,
            max_per_run: int = 70, pause: float = 0.4) -> dict:
    """Eng eski yangilanganlardan boshlab ko'pi bilan `max_per_run` tasini yangilaydi
    (yuk kunlarga taqsimlanadi, yfinance cheklovlariga tushmaslik uchun)."""
    def age(t: str) -> int:
        f = fund.get(t, {}).get("fetched")
        return 9999 if not f else (date.today() - date.fromisoformat(f)).days
    due = sorted([t for t in tickers if age(t) >= C.FUNDAMENTALS_MAX_AGE_DAYS], key=age, reverse=True)[:max_per_run]
    for t in due:
        df = prices.get(t)
        if df is None or df.empty:
            continue
        price = float(df["close"].iloc[-1])
        try:
            sh_guess = fund.get(t, {}).get("mcap", float("nan")) / fund.get(t, {}).get("price", float("nan"))
        except Exception:  # noqa: BLE001
            sh_guess = float("nan")
        avg_px = float(df["close"].iloc[-504:].mean())
        m = fetch_one(t, price, float("nan"), divs.get(t))
        sh = m["mcap"] / price if math.isfinite(m.get("mcap", float("nan"))) and price else sh_guess
        if math.isfinite(sh):          # 24 oylik o'rtacha kapitallashuv bilan qayta hisoblash
            base = avg_px * sh
            m["halal_debt"] = m["halal_debt"] * (m["mcap"] / base) if math.isfinite(m["halal_debt"]) else m["halal_debt"]
            m["halal_cash"] = m["halal_cash"] * (m["mcap"] / base) if math.isfinite(m["halal_cash"]) else m["halal_cash"]
            m["halal_ok"] = bool((not math.isfinite(m["halal_debt"]) or m["halal_debt"] < C.HALAL["debt_mcap_max"])
                                 and (not math.isfinite(m["halal_cash"]) or m["halal_cash"] < C.HALAL["cash_mcap_max"])
                                 and (not math.isfinite(m["halal_income"]) or m["halal_income"] < C.HALAL["interest_rev_max"]))
        m["price"] = price
        fund[t] = m
        time.sleep(pause)
    return fund


def sector_percentiles(fund: dict, keys: list[str]) -> dict:
    """Har bir ko'rsatkich bo'yicha aksiyaning O'Z SEKTORI ichidagi foizlik o'rni (0–100).
    Mutlaq chegaralar o'rniga shu ishlatiladi (checklist tuzatishi)."""
    rows = [{"t": t, "sector": v.get("sector", ""), **{k: v.get(k) for k in keys}} for t, v in fund.items()]
    if not rows:
        return {}
    df = pd.DataFrame(rows).set_index("t")
    out: dict = {t: {} for t in df.index}
    for k in keys:
        col = pd.to_numeric(df[k], errors="coerce")
        pct = col.groupby(df["sector"]).rank(pct=True) * 100
        for t, v in pct.items():
            out[t][k] = None if pd.isna(v) else round(float(v), 1)
    return out
