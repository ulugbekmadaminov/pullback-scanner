import * as api from "../api";
import { lineChart } from "../chart";
import { checks, dateUz, empty, h, ICON, num, pct, rr, skeleton, tone } from "../ui";

const VARIANT: Record<string, string> = {
  signal: "Faqat signal", "signal+rejim": "Signal + bozor rejimi",
  "signal+kuzatuv": "Signal + kuzatuv ro'yxati", "signal+rejim+kuzatuv": "Signal + rejim + kuzatuv (to'liq tizim)",
};
const VERDICT: Record<string, [string, string]> = {
  davom: ["Davom etish mumkin", "up"], "to'xtash": ["Qoida isbotlanmadi", "down"], noaniq: ["Savdolar yetarli emas", "caution"],
};

export default async function (root: HTMLElement) {
  root.append(h("div", { class: "page" }, skeleton(8)));
  let b: api.Backtest;
  try { b = await api.backtest(); } catch {
    root.replaceChildren(h("div", { class: "page" },
      h("header", { class: "page-head" }, h("h1", null, "Backtest")),
      empty(ICON.flask, "Backtest hali ishga tushirilmagan. GitHub'da Actions bo'limida \"Backtest\" ishini qo'lda ishga tushiring — natija keyingi kunlik yangilanishda shu yerda chiqadi.")));
    return;
  }
  const charts: ReturnType<typeof lineChart>[] = [];
  const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const kinds = [...new Set(b.variants.map((v) => v.kind))];

  const variantEl = (v: api.Backtest["variants"][number]) => {
    const [vt, vc] = VERDICT[v.verdict] || [v.verdict, ""];
    const te = v.signal_test, tr = v.signal_train;
    const el = h("div", { class: "chart chart-sm" });
    queueMicrotask(() => charts.push(lineChart(el, [{ name: "Portfel", color: css("--brand"), data: v.equity }], 180)));
    return h("section", { class: "panel bt" },
      h("div", { class: "bt-head" }, h("h3", null, VARIANT[v.variant] || v.variant), h("span", { class: `verdict-chip ${vc}` }, vt)),
      h("div", { class: "table-wrap" }, h("table", null,
        h("thead", null, h("tr", null, h("th", null, ""), h("th", { class: "r" }, "Signallar"), h("th", { class: "r" }, "Yutuq"), h("th", { class: "r" }, "Kutilma"), h("th", { class: "r" }, "Profit faktor"))),
        h("tbody", null,
          h("tr", null, h("td", null, "Sozlash qismi (70%)"), h("td", { class: "r" }, String(tr.n ?? 0)), h("td", { class: "r" }, pct(tr.winrate, 0)), h("td", { class: "r " + tone(tr.expectancy) }, rr(tr.expectancy)), h("td", { class: "r" }, num(tr.profit_factor))),
          h("tr", null, h("td", null, h("b", null, "Tekshiruv qismi (30%)")), h("td", { class: "r" }, String(te.n ?? 0)), h("td", { class: "r" }, pct(te.winrate, 0)), h("td", { class: "r " + tone(te.expectancy) }, h("b", null, rr(te.expectancy))), h("td", { class: "r" }, num(te.profit_factor))),
          h("tr", null, h("td", null, `Tasodifiy kirish (${v.random.runs} marta)`), h("td", null), h("td", null), h("td", { class: "r " + tone(v.random.mean) }, rr(v.random.mean)), h("td", { class: "r dim" }, v.random.percentile !== null ? `${Math.round(v.random.percentile)}-foizlik` : ""))))),
      checks(v.checks.map((c) => ({ ok: c.ok, t: c.t }))),
      h("p", { class: "dim small" }, `Portfel darajasida: daromad ${pct(v.portfolio.ret, 1, true)}, maksimal pasayish ${pct(v.portfolio.max_dd, 1)}, ${v.portfolio.trades ?? 0} ta savdo.`),
      el);
  };

  root.replaceChildren(h("div", { class: "page" },
    h("header", { class: "page-head" }, h("h1", null, "Backtest"),
      h("p", { class: "dim" }, `Davr: ${dateUz(b.period[0])} – ${dateUz(b.period[1])}. ${b.universe} ta aksiya. Sozlash va tekshiruv ${dateUz(b.split_date)} da bo'lingan. Xarajat va sirpanish hisobga olingan.`)),
    b.demo ? h("div", { class: "note warn" }, h("p", null, "Bu DEMO ma'lumotdagi backtest — sun'iy narxlar, xulosa chiqarib bo'lmaydi.")) : null,
    h("div", { class: "note" }, h("p", null, "Qoida tasdiqlanishi uchun tekshiruv qismida hamma shart bajarilishi kerak: kamida 100 savdo, kutilma ≥ +0.10R, profit faktor ≥ 1.2, tasodifiy kirishlardan yuqori 5% da, pasayish ≤ 20%. ", b.survivorship_note, ".")),
    kinds.map((k) => [h("h2", null, api.KIND_NAMES[k] || k), h("div", { class: "grid2" }, b.variants.filter((v) => v.kind === k).map(variantEl))])));
  return () => charts.forEach((c) => c.remove());
}
