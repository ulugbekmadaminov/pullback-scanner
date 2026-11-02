import * as api from "../api";
import { lineChart } from "../chart";
import { dateUz, empty, errorBox, h, ICON, pct, skeleton, tone, usd } from "../ui";

// Ajratib turadigan, rang ko'r odamlar uchun ham farqlanadigan ketma-ketlik (birinchisi — brend)
const PALETTE = ["--brand", "--up", "--caution", "--down", "--ma2", "--ma3", "--ma4", "--ma1"];

export default async function (root: HTMLElement) {
  root.append(h("div", { class: "page" }, skeleton(8)));
  let comp: { strategies: api.Strategy[] };
  try { comp = await api.competition(); } catch (e) {
    root.replaceChildren(errorBox("Musobaqa ma'lumoti yuklanmadi: " + (e as Error).message, () => location.reload()));
    return;
  }
  const ret = (s: api.Strategy) => (s.equity.length ? s.equity[s.equity.length - 1][1] / s.equity[0][1] - 1 : null);
  const list = [...comp.strategies].sort((a, b) => (ret(b) ?? -9) - (ret(a) ?? -9));
  const fundStrats = comp.strategies.filter((s) => s.key !== "signals");
  const since = fundStrats.reduce<string | null>((m, s) => (s.equity[0] && (!m || s.equity[0][0] > m) ? s.equity[0][0] : m), null);
  const days = Math.max(0, ...fundStrats.map((s) => s.equity.length));
  const spus = comp.strategies.find((s) => s.key === "SPUS");
  const chartEl = h("div", { class: "chart" });
  const selected = new Set(list.slice(0, 4).map((s) => s.key).concat(spus ? ["SPUS"] : []));
  const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  let chart: ReturnType<typeof lineChart> | null = null;

  function drawChart() {
    chart?.remove();
    // grafikda faqat umumiy boshlanish sanasidan keyingi qism — teng sharoitda taqqoslash uchun
    const ser = list.filter((s) => selected.has(s.key)).map((s, i) => ({
      name: s.title, color: s.key === "SPUS" ? css("--text-dim") : css(PALETTE[i % PALETTE.length]), dashed: s.key === "SPUS",
      data: s.equity.filter((e) => !since || e[0] >= since) }));
    chart = lineChart(chartEl, ser, 300);
  }

  const young = days < 21;
  root.replaceChildren(h("div", { class: "page" },
    h("header", { class: "page-head" }, h("h1", null, "Strategiyalar musobaqasi"),
      h("p", { class: "dim" }, "Har bir strategiya alohida virtual portfel: oy boshida mezonlarga mos eng yuqori 10 aksiya teng ulushda olinadi. Fundamental ma'lumot tarixda yo'qligi sababli ular orqaga qarab sinalmaydi — musobaqa bugundan oldinga boradi.")),
    young ? h("div", { class: "note" }, h("p", null, since ? `Musobaqa ${dateUz(since)} da boshlangan (${days} savdo kuni). ` : "", "Ishonchli xulosa uchun kamida 1 yil kerak — hozircha faqat kuzating.")) : null,
    days < 2 ? null : h("section", { class: "panel" }, chartEl,
      h("p", { class: "dim small" }, "Pastdagi ro'yxatda belgilang — grafikda qaysi strategiyalar ko'rinishini tanlaysiz. Uzuq chiziq — SPUS.")),
    list.length ? h("div", { class: "strats" }, list.map((s, i) => {
      const r = ret(s);
      const last = s.equity[s.equity.length - 1];
      const beat = spus && r !== null && ret(spus) !== null ? r - ret(spus)! : null;
      return h("section", { class: "strat" },
        h("label", { class: "s-head" },
          days < 2 ? null : h("input", { type: "checkbox", checked: selected.has(s.key), on: { change: (e) => { (e.target as HTMLInputElement).checked ? selected.add(s.key) : selected.delete(s.key); drawChart(); } } }),
          h("span", { class: "s-rank" }, String(i + 1)),
          h("strong", null, s.title),
          h("span", { class: "s-ret " + tone(r) }, pct(r, 1, true))),
        h("p", { class: "small" }, s.rule),
        h("p", { class: "dim small" }, last ? `Qiymat ${usd(last[1])}` : "", beat !== null && s.key !== "SPUS" ? `, SPUS'dan ${beat >= 0 ? "+" : ""}${(beat * 100).toFixed(1)} foiz punkt` : "",
          s.candidates !== null ? `. Bugun mezonga mos: ${s.candidates} ta` : ""),
        s.note ? h("p", { class: "small caution" }, s.note) : null,
        s.holdings.length ? h("div", { class: "chips" }, s.holdings.slice(0, 12).map((t) => t === "SPUS" ? h("span", { class: "chip quiet" }, t)
          : h("a", { class: "chip quiet", href: `#/aksiya/${encodeURIComponent(t)}` }, t))) : null);
    })) : empty(ICON.trophy, "Strategiyalar birinchi skaner ishidan keyin paydo bo'ladi.")));
  if (days >= 2) drawChart();
  return () => chart?.remove();
}
