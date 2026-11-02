import * as api from "../api";
import { bar, empty, errorBox, h, ICON, num, pct, skeleton, svg, tone } from "../ui";

type Filter = { profile: "mid" | "long"; only: "all" | "watch" | "signal"; sector: string; q: string };
const KEY = "saralash.listFilter";

function loadFilter(): Filter {
  try { return { profile: "mid", only: "all", sector: "", q: "", ...JSON.parse(localStorage.getItem(KEY) || "{}") }; }
  catch { return { profile: "mid", only: "all", sector: "", q: "" }; }
}

export function rowEl(r: api.Row, profile: "mid" | "long" = "mid"): HTMLElement {
  const layers = profile === "mid" ? ["trend", "strength", "growth", "quality"] : ["quality", "growth", "value", "trend", "dividend"];
  const score = profile === "mid" ? r.mid : r.long;
  return h("a", { class: "row", href: `#/aksiya/${encodeURIComponent(r.t)}` },
    h("div", { class: "row-main" },
      h("div", { class: "row-id" }, h("strong", null, r.t),
        r.signal ? h("span", { class: "chip brand" }, api.KIND_NAMES[r.signal] || r.signal) : null,
        r.watch_mid === "tayyor" ? h("span", { class: "chip up" }, "Kirishga tayyor") : r.watch_mid ? h("span", { class: "chip" }, "O'rta kuzatuv") : null,
        r.watch_long ? h("span", { class: "chip" }, "Uzoq kuzatuv") : null,
        r.tags.map((t) => h("span", { class: "chip quiet" }, t)),
        !r.halal ? h("span", { class: "chip down" }, "Halollik shubhali") : null),
      h("div", { class: "row-name" }, r.name, r.sector ? `, ${r.sector}` : "")),
    h("div", { class: "row-score", title: "Umumiy ball (0–100)" }, h("b", null, score === null ? "—" : Math.round(score)), h("small", null, "ball")),
    h("div", { class: "row-bars" }, layers.map((k) => bar(r.L[k] ?? null, api.LAYER_NAMES[k]))),
    h("div", { class: "row-px" }, h("span", null, num(r.price)), h("small", { class: tone(r.r21) }, pct(r.r21, 1, true), " 1 oy")));
}

export default async function (root: HTMLElement) {
  root.append(h("div", { class: "page" }, skeleton(8)));
  let rows: api.Row[];
  try { rows = await api.scores(); } catch (e) {
    root.replaceChildren(errorBox("Ro'yxat yuklanmadi: " + (e as Error).message, () => location.reload()));
    return;
  }
  const f = loadFilter();
  const sectors = [...new Set(rows.map((r) => r.sector).filter(Boolean))].sort();
  const list = h("div", { class: "rows" });
  const count = h("p", { class: "dim small" });
  const seg = (name: keyof Filter, opts: [string, string][]) => h("div", { class: "seg", role: "group" },
    opts.map(([v, label]) => h("button", { class: "seg-b", "aria-pressed": String(f[name] === v),
      on: { click: (e) => { (f as any)[name] = v; (e.currentTarget as HTMLElement).parentElement!.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget))); draw(); } } }, label)));
  const search = h("input", { type: "search", placeholder: "Ticker yoki nom", value: f.q, "aria-label": "Qidirish",
    on: { input: (e) => { f.q = (e.target as HTMLInputElement).value; draw(); } } });
  const sel = h("select", { "aria-label": "Sektor", on: { change: (e) => { f.sector = (e.target as HTMLSelectElement).value; draw(); } } },
    h("option", { value: "" }, "Barcha sektorlar"), sectors.map((s) => h("option", { value: s, selected: s === f.sector }, s)));

  function draw() {
    try { localStorage.setItem(KEY, JSON.stringify(f)); } catch { /* shaxsiy rejim */ }
    const q = f.q.trim().toUpperCase();
    let r = rows.filter((x) => (!f.sector || x.sector === f.sector) && (!q || x.t.includes(q) || x.name.toUpperCase().includes(q)));
    if (f.only === "watch") r = r.filter((x) => (f.profile === "mid" ? x.watch_mid : x.watch_long));
    if (f.only === "signal") r = r.filter((x) => x.signal);
    r = [...r].sort((a, b) => ((f.profile === "mid" ? b.mid : b.long) ?? -1) - ((f.profile === "mid" ? a.mid : a.long) ?? -1));
    count.textContent = `${r.length} ta aksiya`;
    list.replaceChildren(...(r.length ? r.slice(0, 300).map((x) => rowEl(x, f.profile)) :
      [empty(ICON.search, "Bu filtrlar bo'yicha aksiya topilmadi.", { label: "Filtrlarni tozalash", onClick: () => { f.only = "all"; f.sector = ""; f.q = ""; search.value = ""; sel.value = ""; draw(); } })]));
  }

  root.replaceChildren(h("div", { class: "page" },
    h("header", { class: "page-head" }, h("h1", null, "Saralangan ro'yxat"),
      h("p", { class: "dim" }, "SPUS (S&P 500 Shariah) aksiyalari umumiy ball bo'yicha. Har bir aksiyani oching — ball nimadan iboratligi ✓/✗ bilan ko'rinadi.")),
    h("div", { class: "filters" },
      seg("profile", [["mid", "O'rta muddat"], ["long", "Uzoq muddat"]]),
      seg("only", [["all", "Hammasi"], ["watch", "Kuzatuvda"], ["signal", "Bugun signal"]]),
      h("div", { class: "filter-row" }, h("span", { class: "search" }, svg(ICON.search, 16), search), sel)),
    count, list));
  draw();
}
