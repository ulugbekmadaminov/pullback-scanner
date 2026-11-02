"""Qatlamli ball (0–100) va har bir ball uchun "nega?" izohlari + 9-modul strategiya skrinlari.

Tamoyil: qora quti yo'q. Har bir qatlam o'z tekshiruvlari ro'yxatini qaytaradi
(✓/✗ + matn), umumiy ball — qatlamlarning teng og'irlikli o'rtachasi.
Fundamental ko'rsatkichlar mutlaq chegara emas, SEKTOR ICHIDAGI o'rin bilan baholanadi.
"""
from __future__ import annotations

import math

import pandas as pd

from . import config as C

WEIGHTS = {
    "mid": {"trend": 1, "strength": 1, "growth": 1, "quality": 1},
    "long": {"quality": 1, "growth": 1, "value": 1, "trend": 1, "dividend": 1},
}


def _f(x) -> float:
    try:
        x = float(x)
        return x if math.isfinite(x) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _pct(x: float) -> str:
    return "—" if not math.isfinite(x) else f"{x * 100:.1f}%"


def _layer(checks: list[tuple[bool | None, str]]) -> dict:
    known = [c for c in checks if c[0] is not None]
    score = round(100 * sum(1 for c in known if c[0]) / len(known)) if known else None
    return {"score": score, "checks": [{"ok": c[0], "t": c[1]} for c in checks]}


def layers(t: str, F: dict, i: int, fund: dict, spct: dict, halal_member: bool) -> dict:
    d = F["ind"][t]
    row = d.loc[F["index"][i]] if F["index"][i] in d.index else d.iloc[-1]
    c, s50, s150, s200 = row["close"], row["sma50"], row["sma150"], row["sma200"]
    st = row["stage"]
    rs, fh = F["rs_pct"][t].iat[i], F["from_high"][t].iat[i]
    m = fund or {}
    sp = spct or {}
    L = {}
    L["trend"] = _layer([
        (st == 2 if pd.notna(st) else None, f"Weinstein bosqichi: {int(st) if pd.notna(st) else '—'} (2 — o'sish bosqichi)"),
        (bool(c > s50 > s150 > s200) if pd.notna(s200) else None,
         f"Narx {c:.2f} > SMA50 {s50:.2f} > SMA150 {s150:.2f} > SMA200 {s200:.2f}"),
        (bool(F["ema200_untouched"][t].iat[i]), "Oxirgi 1 oyda narx EMA200 ga tegmagan"),
        (bool(c > row["sma40w"]) if pd.notna(row["sma40w"]) else None, f"Haftalik 40 haftalik o'rtacha ({row['sma40w']:.2f}) ustida"),
    ])
    L["strength"] = _layer([
        (bool(rs >= C.WATCH_MID_ENTRY["rs_pct_min"]) if pd.notna(rs) else None,
         f"Nisbiy kuch: SPUS aksiyalarining {rs:.0f}% idan kuchli" if pd.notna(rs) else "Nisbiy kuch: ma'lumot yetarli emas"),
        (bool(fh <= 0.10) if pd.notna(fh) else None, f"52 haftalik cho'qqidan {fh * 100:.1f}% pastda (≤10% kuchli)" if pd.notna(fh) else "—"),
        (bool(F["sector_top"][t].iat[i]), "Sektori SPY'ga nisbatan kuchli yarmida"),
        (bool(F["ep"][t].iat[i]), "Yaqinda katalizator: hisobot/yangilikdan keyingi katta hajmli gap (EP)"),
    ])
    pio = _f(m.get("piotroski"))
    L["quality"] = _layer([
        (pio >= 6 if math.isfinite(pio) else None, f"Piotroski F-score: {int(pio) if math.isfinite(pio) else '—'}/9 (≥6 yaxshi)"),
        (_f(sp.get("roe")) >= 50 if math.isfinite(_f(sp.get("roe"))) else None, f"ROE {_pct(_f(m.get('roe')))} — sektorida {_f(sp.get('roe')):.0f}-foizlik"),
        (_f(sp.get("net_margin")) >= 50 if math.isfinite(_f(sp.get("net_margin"))) else None, f"Sof marja {_pct(_f(m.get('net_margin')))} — sektorida {_f(sp.get('net_margin')):.0f}-foizlik"),
        (_f(m.get("fcf_ttm", m.get("fcf_margin"))) > 0 if math.isfinite(_f(m.get("fcf_ttm", m.get("fcf_margin")))) else None, f"Erkin pul oqimi musbat (FCF marja {_pct(_f(m.get('fcf_margin')))})"),
        (_f(m.get("de")) <= 1 if math.isfinite(_f(m.get("de"))) else None, f"Qarz/kapital (D/E) {_f(m.get('de')):.2f} (≤1)"),
        (_f(m.get("current_ratio")) >= 1 if math.isfinite(_f(m.get("current_ratio"))) else None, f"Joriy nisbat {_f(m.get('current_ratio')):.2f} (≥1)"),
    ])
    L["growth"] = _layer([
        (_f(m.get("rev_q")) > .10 if math.isfinite(_f(m.get("rev_q"))) else None, f"Daromad o'sishi (chorak, yillik taqqoslash): {_pct(_f(m.get('rev_q')))}"),
        (_f(m.get("eps_q")) > .10 if math.isfinite(_f(m.get("eps_q"))) else None, f"EPS o'sishi (chorak): {_pct(_f(m.get('eps_q')))}"),
        (_f(m.get("rev_3y")) > .10 if math.isfinite(_f(m.get("rev_3y"))) else None, f"Daromad o'sishi (3 yillik o'rtacha): {_pct(_f(m.get('rev_3y')))}"),
        (_f(m.get("eps_3y")) > .10 if math.isfinite(_f(m.get("eps_3y"))) else None, f"EPS o'sishi (3 yillik o'rtacha): {_pct(_f(m.get('eps_3y')))}"),
    ])
    ig, e3 = _f(m.get("implied_growth")), _f(m.get("eps_3y"))
    L["value"] = _layer([
        (_f(sp.get("pe")) <= 50 if math.isfinite(_f(sp.get("pe"))) else None, f"P/E {_f(m.get('pe')):.1f} — sektorining arzonroq yarmida bo'lishi kerak"),
        (_f(sp.get("pfcf")) <= 50 if math.isfinite(_f(sp.get("pfcf"))) else None, f"P/FCF {_f(m.get('pfcf')):.1f} — sektorining arzonroq yarmida bo'lishi kerak"),
        (ig <= e3 if math.isfinite(ig) and math.isfinite(e3) else None,
         f"Teskari DCF: narx yiliga {_pct(ig)} FCF o'sishini hisobga olgan; oxirgi 3 yillik EPS o'sishi {_pct(e3)}"),
    ])
    dy, yrs = _f(m.get("div_yield")), int(m.get("div_years_up") or 0)
    L["dividend"] = _layer([
        (dy >= .02 if math.isfinite(dy) else None, f"Dividend daromadi {_pct(dy)} (≥2%)"),
        (yrs >= 10, f"Dividend {yrs} yil uzluksiz oshirilgan" + (" — Qirol" if yrs >= 50 else " — Aristokrat" if yrs >= 25 else "")),
        (_f(m.get("payout")) < .6 if math.isfinite(_f(m.get("payout"))) else None, f"To'lov ulushi (payout) {_pct(_f(m.get('payout')))} (<60%)"),
    ])
    halal2 = m.get("halal_ok")
    L["halal"] = {"ok": bool(halal_member) and halal2 is not False, "checks": [
        {"ok": bool(halal_member), "t": "SPUS (S&P 500 Shariah, AAOIFI) tarkibida"},
        {"ok": halal2, "t": f"Qarz / 24 oylik o'rtacha kapitallashuv {_pct(_f(m.get('halal_debt')))} (<30%)"},
        {"ok": None if not math.isfinite(_f(m.get("halal_cash"))) else _f(m.get("halal_cash")) < .3,
         "t": f"Foizli aktivlar / kapitallashuv {_pct(_f(m.get('halal_cash')))} (<30%)"},
        {"ok": None if not math.isfinite(_f(m.get("halal_income"))) else _f(m.get("halal_income")) < .05,
         "t": f"Foiz daromadi / jami daromad {_pct(_f(m.get('halal_income')))} (<5%)"},
        {"ok": None, "t": "Real savdodan oldin Hyssa'da tekshiring"},
    ]}
    return L


def total(L: dict, profile: str) -> float | None:
    w = WEIGHTS[profile]
    vals = [(L[k]["score"], wt) for k, wt in w.items() if L[k]["score"] is not None]
    if not vals:
        return None
    return round(sum(v * wt for v, wt in vals) / sum(wt for _, wt in vals), 1)


# ── 9-modul strategiyalari: skrin qoidalari ──────────────────────────────────
def _ge(x, th):
    x = _f(x)
    return math.isfinite(x) and x >= th


def _le(x, th):
    x = _f(x)
    return math.isfinite(x) and x <= th


def screen(name: str, m: dict, tech: dict) -> bool:
    """m — fundamental ko'rsatkichlar, tech — {'trend_ok','rs_pct','from_high'}."""
    S = C.STRATEGIES.get(name, {})
    trend_ok = tech.get("trend_ok", False)
    if name == "stable_growth":
        return all(_ge(m.get(k), S[k]) for k in ("rev_q", "rev_y", "rev_3y", "eps_q", "eps_y", "eps_3y", "roe")) and _ge(m.get("mcap"), S["mcap"])
    if name == "hyper_growth":
        return all(_ge(m.get(k), S[k]) for k in ("rev_q", "rev_y", "rev_3y", "gross_margin", "current_ratio")) \
            and _le(m.get("de"), S["de"]) and _ge(m.get("mcap"), S["mcap"])
    if name == "canslim":
        return _ge(m.get("eps_q"), S["eps_q"]) and _ge(m.get("eps_3y"), S["eps_3y"]) \
            and _ge(tech.get("rs_pct"), S["rs_pct"]) and _le(tech.get("from_high"), S["from_high"]) and tech.get("market_ok", True)
    if name == "up_value":
        ok = _le(m.get("pb"), S["pb"]) and _le(m.get("pe"), S["pe"]) and _le(m.get("peg"), S["peg"]) \
            and _ge(m.get("eps_3y"), S["eps_5y"]) and _ge(m.get("roe"), S["roe"]) \
            and _ge(m.get("current_ratio"), S["current_ratio"]) and _le(m.get("de"), S["de"]) and _ge(m.get("piotroski"), S["piotroski"])
        return ok and (trend_ok or not C.VALUE_TREND_FILTER)
    if name == "quality_dcf":
        ig, e3 = _f(m.get("implied_growth")), _f(m.get("eps_3y"))
        ok = _le(m.get("pb"), S["pb"]) and _le(m.get("pe"), S["pe"]) and _ge(m.get("roe"), S["roe"]) \
            and _ge(m.get("current_ratio"), S["current_ratio"]) and _ge(m.get("piotroski"), S["piotroski"]) \
            and math.isfinite(ig) and math.isfinite(e3) and ig < e3
        return ok and (trend_ok or not C.VALUE_TREND_FILTER)
    if name == "healthy_cash":
        return _ge(m.get("div_yield"), S["yield"]) and _ge(m.get("div_growth"), S["div_growth"]) \
            and _le(m.get("payout"), S["payout"]) and _ge(m.get("eps_3y"), S["eps_3y"]) and _ge(m.get("fcf_3y"), S["fcf_3y"]) \
            and _ge(m.get("fcf_margin"), S["fcf_margin"]) and _ge(m.get("current_ratio"), S["current_ratio"]) and _ge(m.get("mcap"), S["mcap"])
    if name == "aristocrats":
        return int(m.get("div_years_up") or 0) >= S["years_min"] and _le(m.get("payout"), 0.8)
    return False


STRATEGY_INFO = {
    "stable_growth": ("Barqaror o'sish (Stable)", "Daromad va EPS chorak, yil, 3 yilda >10%, ROE >10%, >$10 mlrd"),
    "hyper_growth": ("Tez o'sish (Hyper)", "Daromad >30%, yalpi marja >50%, D/E <0.5, >$2 mlrd"),
    "canslim": ("CANSLIM", "EPS chorak va 3 yil >25%, nisbiy kuch ≥80, cho'qqiga yaqin, bozor ijobiy"),
    "up_value": ("UP-Value (+trend)", "P/E <15, P/B <2, PEG <2, ROE >5%, D/E <0.5, Piotroski ≥5, narx SMA200 ustida"),
    "quality_dcf": ("UP-DCF (+trend)", "P/E <25, Piotroski ≥5, teskari DCF o'sishi tarixiy o'sishdan past, narx SMA200 ustida"),
    "healthy_cash": ("Dividend: Healthy cash", "Yield >2%, payout <50%, EPS/FCF o'sishi >5%, FCF marja >5%"),
    "aristocrats": ("Dividend Aristokratlari", "Dividend ≥25 yil uzluksiz oshirilgan, payout <80%"),
    "dogs_of_dow": ("Dogs of the Dow (halol)", "Dow 30 ichidan halol va eng yuqori dividendli 10 ta, yilda bir marta"),
    "long_watch": ("Uzoq muddat kuzatuvi", "Uzoq muddat kuzatuv ro'yxatidagi aksiyalar, teng ulush"),
    "signals": ("Faol signallar (yo'ldosh)", "Pullback va breakout signallari, depozit himoyasi qoidalari bilan"),
    "SPUS": ("SPUS (taqqoslash)", "Halol indeksni oddiy sotib olib ushlab turish"),
}
