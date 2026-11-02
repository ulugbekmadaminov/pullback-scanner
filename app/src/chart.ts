// Grafiklar: TradingView Lightweight Charts (loyiha ichida, CDN emas).
import { ColorType, createChart, LineStyle, type IChartApi, type Time } from "lightweight-charts";
import type { Card } from "./api";

function css(v: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
}

function base(el: HTMLElement, height: number, fit = true): IChartApi {
  const chart = createChart(el, {
    height, autoSize: true,
    layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: css("--text-dim"), fontFamily: css("--font"), fontSize: 11 },
    grid: { vertLines: { visible: false }, horzLines: { color: css("--line") } },
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false, fixLeftEdge: true },
    crosshair: { horzLine: { labelBackgroundColor: css("--brand") }, vertLine: { labelBackgroundColor: css("--brand") } },
    handleScroll: { vertTouchDrag: false },
  });
  // Kenglik o'zgarsa (telefon burilishi) chiziqli grafiklar to'liq ko'rinadi; sham grafigida foydalanuvchi zoomi saqlanadi.
  // Grafik o'chirilganda kuzatuvchi ham uziladi — aks holda "Object is disposed" xatosi chiqadi.
  let ro: ResizeObserver | null = null;
  if (fit) { ro = new ResizeObserver(() => chart.timeScale().fitContent()); ro.observe(el); }
  const remove = chart.remove.bind(chart);
  chart.remove = () => { ro?.disconnect(); ro = null; remove(); };
  return chart;
}

export function stockChart(el: HTMLElement, c: Card, show: Record<string, boolean>): IChartApi {
  const ch = c.chart;
  const chart = base(el, el.clientWidth < 600 ? 300 : 420, false);
  const up = css("--up"), down = css("--down");
  const candles = chart.addCandlestickSeries({ upColor: up, downColor: down, borderVisible: false, wickUpColor: up, wickDownColor: down });
  candles.setData(ch.t.map((t, i) => ({ time: t as Time, open: ch.o[i], high: ch.h[i], low: ch.l[i], close: ch.c[i] })));
  const vol = chart.addHistogramSeries({ priceScaleId: "vol", priceFormat: { type: "volume" }, color: css("--line-strong") });
  chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
  vol.setData(ch.t.map((t, i) => ({ time: t as Time, value: ch.v[i] })));
  const lines: [keyof typeof ch, string, string][] = [["ema20", "--ma1", "EMA20"], ["ema50", "--ma2", "EMA50"], ["sma150", "--ma3", "SMA150"], ["sma200", "--ma4", "SMA200"]];
  for (const [k, color, title] of lines) {
    if (!show[k as string]) continue;
    const s = chart.addLineSeries({ color: css(color), lineWidth: 1, priceLineVisible: false, lastValueVisible: false, title });
    const arr = ch[k] as (number | null)[];
    s.setData(ch.t.flatMap((t, i) => (arr[i] === null ? [] : [{ time: t as Time, value: arr[i] as number }])));
  }
  // signal belgilari
  candles.setMarkers(c.signals.map((s) => ({
    time: s.d as Time, position: "belowBar" as const, color: s.k === "pullback" ? css("--brand") : css("--caution"),
    shape: "arrowUp" as const, text: s.k === "pullback" ? "P" : "B",
  })));
  // savdo rejasi: kirish, stop, maqsad; pullback zonasi
  const plan = c.plan;
  if (plan) {
    candles.createPriceLine({ price: plan.entry, color: css("--brand"), lineWidth: 1, lineStyle: LineStyle.Solid, title: "Kirish" });
    candles.createPriceLine({ price: plan.stop, color: down, lineWidth: 1, lineStyle: LineStyle.Dashed, title: "Stop" });
    candles.createPriceLine({ price: plan.target, color: up, lineWidth: 1, lineStyle: LineStyle.Dashed, title: "Maqsad" });
  }
  const z = c.explain.pullback.zone;
  if (z && (plan?.kind === "pullback" || show.zone)) {
    for (const p of z) candles.createPriceLine({ price: p, color: css("--caution"), lineWidth: 1, lineStyle: LineStyle.Dotted, title: "Zona" });
  }
  const n = ch.t.length;
  chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - 180), to: n + 3 });
  return chart;
}

export function lineChart(el: HTMLElement, series: { name: string; color: string; data: [string, number][]; dashed?: boolean }[], height = 260, pctMode = true): IChartApi {
  const chart = base(el, height);
  for (const s of series) {
    if (!s.data.length) continue;
    const first = s.data[0][1];
    const l = chart.addLineSeries({ color: s.color, lineWidth: 2, title: s.name, priceLineVisible: false,
      lineStyle: s.dashed ? LineStyle.Dashed : LineStyle.Solid,
      priceFormat: pctMode ? { type: "custom", formatter: (v: number) => (v > 0 ? "+" : "") + v.toFixed(1) + "%" } : undefined });
    l.setData(s.data.map(([t, v]) => ({ time: t as Time, value: pctMode ? (v / first - 1) * 100 : v })));
  }
  chart.timeScale().fitContent();
  return chart;
}

export function regimeChart(el: HTMLElement, m: { t: string[]; c: number[]; sma200: (number | null)[]; regime: (string | null)[] }): IChartApi {
  const chart = base(el, 220);
  const colors: Record<string, string> = { green: css("--up"), yellow: css("--caution"), red: css("--down") };
  const price = chart.addLineSeries({ color: css("--text"), lineWidth: 2, title: "QQQ", priceLineVisible: false });
  price.setData(m.t.map((t, i) => ({ time: t as Time, value: m.c[i], color: colors[m.regime[i] || ""] || css("--text-dim") })));
  const sma = chart.addLineSeries({ color: css("--text-dim"), lineWidth: 1, lineStyle: LineStyle.Dashed, title: "SMA200", priceLineVisible: false, lastValueVisible: false });
  sma.setData(m.t.flatMap((t, i) => (m.sma200[i] === null ? [] : [{ time: t as Time, value: m.sma200[i] as number }])));
  chart.timeScale().fitContent();
  return chart;
}
