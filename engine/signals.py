"""Kirish signallari (kunlik grafik): PULLBACK (Uplift qo'llanmasi, 8 qoida) va BREAKOUT (Breakout1).

Har bir tekshiruv izohli qaytadi — ilovadagi "nega?" bo'limi shu matnlardan chiziladi.
Signal kun YOPILISHIDA tekshiriladi, kirish — keyingi kun ochilishida.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import config as C


def _candle(o, h, l, c, po, pc, ph) -> str | None:
    rng = h - l
    body = abs(c - o)
    if rng <= 0:
        return None
    lower = min(o, c) - l
    upper = h - max(o, c)
    if body > 0 and lower >= 2 * body and upper <= body and c >= l + rng * 2 / 3:
        return "bolg'a"
    if pc < po and c > o and o <= pc and c >= po:
        return "yutuvchi sham"
    if c > ph:
        return "oldingi cho'qqi ustida yopilish"
    return None


class SwingTracker:
    """Swing nuqtalarini kunma-kun quradi: pivot faqat o'ngdagi N sham yopilgach qo'shiladi."""

    def __init__(self, h: np.ndarray, l: np.ndarray, atr: np.ndarray, n: int, min_atr: float):
        self.h, self.l, self.atr, self.n, self.min_atr = h, l, atr, n, min_atr
        self.pts: list[tuple[int, str, float]] = []

    def _add(self, p: tuple[int, str, float]) -> None:
        pts = self.pts
        if pts and pts[-1][1] == p[1]:
            better = p[2] > pts[-1][2] if p[1] == "H" else p[2] < pts[-1][2]
            if better:
                pts[-1] = p
            return
        if pts:
            a = self.atr[p[0]]
            if math.isfinite(a) and abs(p[2] - pts[-1][2]) < self.min_atr * a:
                return
        pts.append(p)

    def step(self, t: int) -> None:
        i, n = t - self.n, self.n
        if i < n:
            return
        h, l = self.h, self.l
        cand = []
        # chapdagidan qat'iy baland, o'ngdagidan past emas (tekis cho'qqida birinchisi olinadi)
        if h[i] > h[i - n:i].max() and h[i] >= h[i + 1:t + 1].max():
            cand.append((i, "H", float(h[i])))
        if l[i] < l[i - n:i].min() and l[i] <= l[i + 1:t + 1].min():
            cand.append((i, "L", float(l[i])))
        for p in cand:
            self._add(p)


def _pullback_at(t: int, a: dict, sw: list, cfg: dict) -> dict:
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    e20, e50, atr = a["ema20"], a["ema50"], a["atr"]
    checks: list[dict] = []

    def add(key: str, ok: bool, text: str):
        checks.append({"k": key, "ok": bool(ok), "t": text})

    at = atr[t]
    add("trend", c[t] > e20[t] and c[t] > e50[t] and e20[t] > e50[t],
        f"Trend: yopilish {c[t]:.2f}, EMA20 {e20[t]:.2f}, EMA50 {e50[t]:.2f} (yopilish ikkalasidan, EMA20 EMA50 dan yuqori bo'lishi kerak)")
    hs = [k for k, p in enumerate(sw) if p[1] == "H" and p[0] < t]
    res = {"ok": False, "checks": checks}
    if not hs or hs[-1] < 3 or not math.isfinite(at):
        add("zinapoya", False, "Zinapoya: yetarli swing nuqtalari yo'q")
        return res
    j = hs[-1]
    H1, L1, H2, L2 = sw[j], sw[j - 1], sw[j - 2], sw[j - 3]
    if not (L1[1] == "L" and H2[1] == "H" and L2[1] == "L"):
        add("zinapoya", False, "Zinapoya: swing ketma-ketligi buzilgan")
        return res
    add("zinapoya", H1[2] > H2[2] and L1[2] > L2[2],
        f"Zinapoya: cho'qqilar {H2[2]:.2f} → {H1[2]:.2f}, tublar {L2[2]:.2f} → {L1[2]:.2f} (ikkalasi ham ko'tarilishi kerak)")
    seg_l = l[H1[0] + 1:t + 1]
    if len(seg_l) == 0:
        return res
    p_rel = int(np.argmin(seg_l))
    P, p_bar = float(seg_l[p_rel]), H1[0] + 1 + p_rel
    impulse = H1[2] - L1[2]
    depth = (H1[2] - P) / impulse if impulse > 0 else float("nan")
    bars = t - H1[0]
    add("impuls", impulse >= cfg["impulse_min_atr"] * at,
        f"Impuls: {impulse:.2f} = {impulse / at:.1f} ATR (kamida {cfg['impulse_min_atr']:.0f} ATR)")
    add("chuqurlik", cfg["depth_min"] <= depth <= cfg["depth_max"],
        f"Pullback chuqurligi {depth * 100:.0f}% (Fibonacci 38.2–61.8% oralig'ida bo'lishi kerak)")
    add("vaqt", cfg["bars_after_high_min"] <= bars <= cfg["bars_after_high_max"],
        f"Cho'qqidan keyin {bars} kun o'tgan (2–15)")
    held = P > L1[2] and bool((c[H1[0]:t + 1] > L1[2]).all())
    add("tub_saqlangan", held, f"Oldingi tub {L1[2]:.2f}: pullback tubi {P:.2f} undan yuqorida bo'lishi kerak")
    zone = cfg["zone_atr"] * at
    factors = []
    old_res = [p for p in sw[:j] if p[1] == "H" and p[2] < H1[2] and abs(p[2] - P) <= zone]
    if old_res:
        factors.append(f"eski qarshilik {old_res[-1][2]:.2f} endi tayanch")
    if abs(e20[p_bar] - P) <= zone:
        factors.append(f"EMA20 ({e20[p_bar]:.2f})")
    if L1[0] != L2[0]:
        slope = (L1[2] - L2[2]) / (L1[0] - L2[0])
        tl = L1[2] + slope * (p_bar - L1[0])
        if abs(tl - P) <= zone:
            factors.append(f"trend chizig'i ({tl:.2f})")
    add("zona", len(factors) >= cfg["zone_min_factors"],
        f"Zona {P:.2f} atrofida {len(factors)} omil kesishgan: " + (", ".join(factors) or "yo'q") + " (kamida 2)")
    pat = _candle(o[t], h[t], l[t], c[t], o[t - 1], c[t - 1], h[t - 1]) if t > 0 else None
    in_zone = l[t] <= P + zone
    add("signal", pat is not None and in_zone,
        f"Tasdiq shami: {pat or 'yo`q'}" + ("" if in_zone else " (sham zonadan uzoq)"))
    stop = P - cfg["stop_atr_buffer"] * at
    entry = c[t]
    R = entry - stop
    target = H1[2]
    rr = (target - entry) / R if R > 0 else float("nan")
    add("rr", R > 0 and rr >= cfg["min_rr"] and cfg["r_atr_min"] <= R / at <= cfg["r_atr_max"],
        f"Reja: kirish ~{entry:.2f}, stop {stop:.2f}, maqsad {target:.2f} → 1:{rr:.1f} (kamida 1:2)")
    res.update(ok=all(x["ok"] for x in checks), stop=stop, target=target, entry=entry, rr=rr,
               zone=[P - zone, P + zone], swings={"H1": H1, "L1": L1, "H2": H2, "L2": L2, "P": (p_bar, "P", P)},
               factors=factors, pattern=pat, depth=depth)
    return res


def _breakout_at(t: int, a: dict, cfg: dict) -> dict:
    c, h, l, v = a["close"], a["high"], a["low"], a["volume"]
    e, atr, vol50 = a[f"ema{cfg['ema']}"], a["atr"], a["vol50"]
    checks: list[dict] = []

    def add(key, ok, text):
        checks.append({"k": key, "ok": bool(ok), "t": text})

    n = cfg["high_lookback"]
    at = atr[t]
    res = {"ok": False, "checks": checks}
    if t < 252 or not math.isfinite(at):
        return res
    prev_hi = h[t - n:t].max()
    add("ema", c[t] > e[t], f"Yopilish {c[t]:.2f}, EMA{cfg['ema']} {e[t]:.2f} (ustida bo'lishi kerak)")
    add("yangi_cho'qqi", c[t] >= prev_hi, f"1 oylik cho'qqi {prev_hi:.2f}, yopilish {c[t]:.2f} (yangilanishi kerak)")
    hi252, hi126 = a["hi252"][t], a["hi126"][t]
    d252, d126 = 1 - c[t] / hi252, 1 - c[t] / hi126
    near = d252 <= cfg["near_high_pct"] or d126 <= cfg["near_high_pct"]
    add("yuqori_daraja", near, f"52 haftalik cho'qqidan {d252 * 100:.1f}%, 6 oylikdan {d126 * 100:.1f}% pastda (≤3%)")
    vm = v[t] / vol50[t] if vol50[t] else float("nan")
    add("hajm", vm >= cfg["vol_mult"], f"Hajm o'rtachadan {vm:.1f}× (kamida {cfg['vol_mult']}×)")
    lo = l[t - cfg["stop_lookback"] + 1:t + 1].min() - cfg["stop_atr_buffer"] * at
    R = min(max(c[t] - lo, cfg["r_atr_min"] * at), cfg["r_atr_max"] * at)
    stop = c[t] - R
    target = c[t] + cfg["target_r"] * R
    add("reja", True, f"Reja: kirish ~{c[t]:.2f}, stop {stop:.2f}, maqsad {target:.2f} (1:{cfg['target_r']:.0f})")
    res.update(ok=all(x["ok"] for x in checks), stop=stop, target=target, entry=c[t],
               rr=cfg["target_r"], near52=d252 <= cfg["near_high_pct"])
    return res


def _arrays(d: pd.DataFrame) -> dict:
    return {k: d[k].to_numpy(dtype=float) for k in d.columns if d[k].dtype != object}


def scan(d: pd.DataFrame, start: int = 260) -> pd.DataFrame:
    """Butun tarix bo'ylab signal kunlari (backtest uchun). d — indicators.add_all() natijasi."""
    a = _arrays(d)
    st = SwingTracker(a["high"], a["low"], a["atr"], C.PIVOT_N, C.PIVOT_MIN_ATR)
    rows = []
    for t in range(len(d)):
        st.step(t)
        if t < start:
            continue
        pb = _pullback_at(t, a, st.pts, C.PULLBACK)
        if pb["ok"]:
            rows.append({"t": t, "date": d.index[t], "kind": "pullback", "stop": pb["stop"], "target": pb["target"],
                         "factors": len(pb["factors"])})
        bo = _breakout_at(t, a, C.BREAKOUT)
        if bo["ok"]:
            rows.append({"t": t, "date": d.index[t], "kind": "breakout", "stop": bo["stop"], "target": bo["target"],
                         "factors": 0})
    return pd.DataFrame(rows)


def explain_last(d: pd.DataFrame) -> dict:
    """Oxirgi kun uchun ikkala kirish turining to'liq tekshiruvi (karta uchun)."""
    a = _arrays(d)
    st = SwingTracker(a["high"], a["low"], a["atr"], C.PIVOT_N, C.PIVOT_MIN_ATR)
    for t in range(len(d)):
        st.step(t)
    t = len(d) - 1
    pb = _pullback_at(t, a, st.pts, C.PULLBACK)
    bo = _breakout_at(t, a, C.BREAKOUT)
    idx = d.index

    def sw(p):
        return {"date": idx[p[0]].date().isoformat(), "price": round(p[2], 4)}
    if "swings" in pb:
        pb["swings"] = {k: sw(v) for k, v in pb["swings"].items()}
    recent = [{"date": idx[p[0]].date().isoformat(), "type": p[1], "price": round(p[2], 4)}
              for p in st.pts if p[0] >= len(d) - 160]
    return {"pullback": pb, "breakout": bo, "swings": recent}
