import * as api from "../api";
import { stockChart } from "../chart";
import * as store from "../store";
import { checks, dateUz, errorBox, field, h, ICON, modal, num, numInput, parseNum, pct, skeleton, svg, toast, todayIso, tone, usd } from "../ui";

const FUND_ROWS: [string, string, (v: any) => string, string?][] = [
  ["rev_q", "Daromad o'sishi (chorak)", (v) => pct(v, 1, true)],
  ["rev_3y", "Daromad o'sishi (3 yil o'rtacha)", (v) => pct(v, 1, true), "rev_3y"],
  ["eps_q", "EPS o'sishi (chorak)", (v) => pct(v, 1, true)],
  ["eps_3y", "EPS o'sishi (3 yil o'rtacha)", (v) => pct(v, 1, true), "eps_3y"],
  ["gross_margin", "Yalpi marja", (v) => pct(v), "gross_margin"],
  ["op_margin", "Operatsion marja", (v) => pct(v), "op_margin"],
  ["net_margin", "Sof marja", (v) => pct(v), "net_margin"],
  ["roe", "ROE", (v) => pct(v), "roe"],
  ["fcf_margin", "Erkin pul oqimi marjasi", (v) => pct(v)],
  ["current_ratio", "Joriy nisbat", (v) => num(v)],
  ["quick_ratio", "Tez nisbat", (v) => num(v)],
  ["de", "Qarz / kapital (D/E)", (v) => num(v)],
  ["interest_cov", "Foizni qoplash", (v) => num(v, 1)],
  ["pe", "P/E", (v) => num(v, 1), "pe"],
  ["pb", "P/B", (v) => num(v, 1), "pb"],
  ["ps", "P/S", (v) => num(v, 1), "ps"],
  ["pfcf", "P/FCF", (v) => num(v, 1), "pfcf"],
  ["peg", "PEG", (v) => num(v)],
  ["div_yield", "Dividend daromadi", (v) => pct(v, 2)],
  ["div_years_up", "Dividend oshirilgan yillar", (v) => (v ? String(v) : "0")],
  ["insiders", "Insayderlar ulushi", (v) => pct(v)],
  ["institutions", "Institutlar ulushi", (v) => pct(v)],
];

export default async function (root: HTMLElement, ticker: string) {
  root.append(h("div", { class: "page" }, skeleton(10)));
  let c: api.Card;
  try { c = await api.card(ticker); } catch (e) {
    root.replaceChildren(errorBox(`${ticker} kartasi topilmadi: ${(e as Error).message}`, () => history.back()));
    return;
  }
  const r = c.row;
  const show = { ema20: true, ema50: true, sma150: false, sma200: true, zone: false };
  const chartEl = h("div", { class: "chart" });
  let chart = stockChart(chartEl, c, show);
  const redraw = () => { chart.remove(); chart = stockChart(chartEl, c, show); };
  const toggles = h("div", { class: "toggles" }, (Object.keys(show) as (keyof typeof show)[]).map((k) =>
    h("label", { class: "tog" }, h("input", { type: "checkbox", checked: show[k], on: { change: (e) => { show[k] = (e.target as HTMLInputElement).checked; redraw(); } } }),
      k === "zone" ? "Pullback zonasi" : k.toUpperCase())));
  const s = store.get().settings;
  const plan = c.plan;
  // Risk butun depozitdan, pozitsiya esa depozitning 15% idan oshmaydi (dvigateldagi qoida bilan bir xil)
  const myShares = plan && plan.entry > plan.stop ? Math.max(0, Math.min(Math.floor(s.deposit * (s.risk_pct / 100) / (plan.entry - plan.stop)),
    Math.floor(s.deposit * 0.15 / plan.entry))) : 0;
  const f = c.fund || {};
  const lay = (k: string) => c.layers[k];
  const layerOrder = r.watch_long && !r.watch_mid ? ["quality", "growth", "value", "dividend", "trend", "strength"] : ["trend", "strength", "growth", "quality", "value", "dividend"];
  const impure = Number(f.impure_per_share_q) || 0;

  function addPosition() {
    const qty = numInput(plan ? myShares : ""), entry = numInput(plan ? plan.entry.toFixed(2) : r.price?.toFixed(2) ?? "");
    const stop = numInput(plan ? plan.stop.toFixed(2) : ""), target = numInput(plan ? plan.target.toFixed(2) : "");
    const prof = h("select", null, h("option", { value: "mid", selected: !r.watch_long || !!r.watch_mid }, "O'rta muddat (2 hafta – 6 oy)"),
      h("option", { value: "long", selected: r.watch_long && !r.watch_mid }, "Uzoq muddat (1 yil+)"));
    const date = h("input", { type: "date", value: todayIso() });
    const note = h("input", { type: "text", maxlength: 200, placeholder: "Nega sotib oldim (ixtiyoriy)" });
    modal(`${r.t} — pozitsiya qo'shish`, h("div", { class: "form" },
      h("p", { class: "dim small" }, "Real xaridingizni qayd qiling. Profil kiritilgandan keyin o'zgarmaydi — bu \"2 haftaga olgandim, endi uzoq muddatli\" xatosidan saqlaydi."),
      field("Profil", prof), field("Aksiyalar soni", qty), field("Kirish narxi, $", entry), field("Stop, $", stop, "Bo'sh qoldirsangiz R hisoblanmaydi"),
      field("Maqsad, $", target), field("Sana", date), field("Izoh", note)), [
      { label: "Bekor qilish", onClick: () => {} },
      { label: "Qo'shish", primary: true, onClick: async () => {
        const q = parseNum(qty.value), e = parseNum(entry.value);
        const st = stop.value.trim() ? parseNum(stop.value) : null, tg = target.value.trim() ? parseNum(target.value) : null;
        if (!(q > 0) || !(e > 0)) { toast("Soni va narxni to'g'ri kiriting"); return false; }
        if (st !== null && !(st < e)) { toast("Stop kirish narxidan past bo'lishi kerak"); return false; }
        const ok = await store.update((x) => { x.positions.push({ id: crypto.randomUUID(), ticker: r.t, profile: prof.value as "mid" | "long",
          kind: plan?.kind || "qo'lda", qty: q, entry: e, date: date.value || todayIso(), stop: st, target: tg, note: note.value,
          followed_plan: null, exit: null, exit_date: null, exit_note: "", purified: 0 }); });
        if (ok) toast(`${r.t} jurnalga qo'shildi`);
      } }]);
  }

  root.replaceChildren(h("div", { class: "page card-page" },
    h("a", { class: "back", href: "#/royxat" }, svg(ICON.back, 18), "Ro'yxat"),
    h("header", { class: "card-head" },
      h("div", null,
        h("h1", null, r.t, h("span", { class: "c-name" }, r.name)),
        h("p", { class: "dim" }, [r.sector, f.industry].filter(Boolean).join(", "))),
      h("div", { class: "c-price" }, h("b", null, num(r.price)), h("span", { class: tone(r.r1d) }, pct(r.r1d, 2, true), " bugun"))),
    h("div", { class: "chips" },
      lay("halal")?.ok ? h("span", { class: "chip up" }, "Halol (SPUS + formula)") : h("span", { class: "chip down" }, "Halollik shubhali"),
      r.watch_mid === "tayyor" ? h("span", { class: "chip up" }, "Kirishga tayyor") : r.watch_mid ? h("span", { class: "chip" }, `O'rta kuzatuvda: ${dateUz(c.watch.mid?.entered)} dan`) : null,
      r.watch_long ? h("span", { class: "chip" }, `Uzoq kuzatuvda: ${dateUz(c.watch.long?.entered)} dan`) : null,
      r.tags.map((t) => h("span", { class: "chip quiet" }, t)),
      r.earn ? h("span", { class: "chip quiet" }, `Hisobot: ${dateUz(r.earn)}`) : null),
    plan ? h("section", { class: "plan" },
      h("h2", null, `Bugungi signal: ${api.KIND_NAMES[plan.kind]}`),
      h("div", { class: "plan-grid" },
        h("div", null, h("small", null, "Kirish (ertaga ochilishda)"), h("b", null, usd(plan.entry))),
        h("div", null, h("small", null, "Stop"), h("b", { class: "down" }, usd(plan.stop))),
        h("div", null, h("small", null, "Maqsad"), h("b", { class: "up" }, usd(plan.target))),
        h("div", null, h("small", null, "Foyda / risk"), h("b", null, plan.rr ? `1 : ${plan.rr.toFixed(1)}` : "—"))),
      h("p", null, `Depozitingiz ${usd(s.deposit)} va savdo riski ${s.risk_pct}% bo'yicha: `, h("b", null, `${myShares} ta aksiya`),
        ` (risk ${usd(myShares * (plan.entry - plan.stop))}, pozitsiya ${usd(myShares * plan.entry)}).`),
      h("p", { class: "dim small" }, "Hisobotga 5 kundan kam qolgan bo'lsa yoki bozor rejimi qizil bo'lsa, dastur kirmaydi. Real savdodan oldin Hyssa'da halollikni tekshiring."))
      : null,
    h("section", { class: "panel" }, chartEl, toggles,
      h("p", { class: "dim small" }, "Strelkalar — o'tgan signallar (P — pullback, B — breakout). Signal bo'lgan kuni kirish, stop va maqsad chiziqlari chiziladi.")),
    h("div", { class: "grid2" },
      h("section", { class: "panel" }, h("h2", null, "Ball nimadan iborat"),
        h("p", { class: "dim small" }, `O'rta muddat: ${r.mid ?? "—"} ball, uzoq muddat: ${r.long ?? "—"} ball. Har bir qatlam teng og'irlikda. Bosib ochsangiz, har bir tekshiruv ko'rinadi.`),
        layerOrder.map((k) => lay(k) && h("details", { class: "layer" },
          h("summary", null, h("span", null, api.LAYER_NAMES[k]), h("span", { class: "l-score" }, lay(k).score === null ? "ma'lumot yo'q" : `${lay(k).score}`)),
          checks(lay(k).checks)))),
      h("section", { class: "panel" }, h("h2", null, "Kirish tekshiruvlari"),
        h("details", { class: "layer", open: c.explain.pullback.ok },
          h("summary", null, h("span", null, "Pullback (8 qoida)"), h("span", { class: "l-score" }, c.explain.pullback.ok ? "signal bor" : "signal yo'q")),
          checks(c.explain.pullback.checks)),
        h("details", { class: "layer", open: c.explain.breakout.ok },
          h("summary", null, h("span", null, "Breakout"), h("span", { class: "l-score" }, c.explain.breakout.ok ? "signal bor" : "signal yo'q")),
          checks(c.explain.breakout.checks)),
        c.watch.mid ? h("p", { class: "small" }, h("b", null, "Kuzatuvga kirish sababi: "), c.watch.mid.reason) : null,
        c.watch.long ? h("p", { class: "small" }, h("b", null, "Uzoq kuzatuv sababi: "), c.watch.long.reason) : null)),
    h("div", { class: "grid2" },
      h("section", { class: "panel" }, h("h2", null, "Fundamental ko'rsatkichlar"),
        f.fetched ? h("p", { class: "dim small" }, `Oxirgi 12 oy (TTM). Yangilangan: ${dateUz(f.fetched)}. Foizlik — o'z sektori ichidagi o'rni.`)
          : h("p", { class: "dim small" }, "Fundamental ma'lumot hali yuklanmagan — skaner har kuni ~70 aksiyani yangilaydi."),
        h("div", { class: "table-wrap" }, h("table", { class: "fund" }, h("tbody", null, FUND_ROWS.map(([k, label, fmt, sp]) =>
          h("tr", null, h("td", null, label), h("td", { class: "r" }, fmt(f[k])), h("td", { class: "r dim" }, sp && c.spct[sp] != null ? `${Math.round(c.spct[sp]!)}-foizlik` : "")))))),
        f.implied_growth != null ? h("p", { class: "small" }, h("b", null, "Teskari DCF: "),
          `bugungi narx keyingi 5 yilda yiliga ${pct(f.implied_growth)} erkin pul oqimi o'sishini hisobga olgan (diskont 10%, terminal 3%). Bunga ishonasizmi? Bu — ma'lumot uchun, ballga ta'sir qilmaydi.`) : null),
      h("section", { class: "panel" }, h("h2", null, "Sifat va halollik"),
        f.piotroski_items?.length ? h("details", { class: "layer", open: true },
          h("summary", null, h("span", null, "Piotroski F-score"), h("span", { class: "l-score" }, `${f.piotroski}/9`)), checks(f.piotroski_items)) : null,
        h("details", { class: "layer", open: true }, h("summary", null, h("span", null, "Halollik (AAOIFI, Uplift 4-modul)")), checks(lay("halal").checks)),
        h("p", { class: "small" }, h("b", null, "Tozalash: "), impure > 0
          ? `har bir aksiyaga chorakda taxminan ${usd(impure)} nomaqbul (foiz) daromad. Ushlab turgan kunlaringizga mutanosib hisoblanadi — Jurnalim bo'limida.`
          : "nomaqbul daromad ma'lumoti yo'q yoki nolga yaqin."),
        c.earnings.length ? h("p", { class: "dim small" }, "Hisobot sanalari: " + c.earnings.slice(-4).map(dateUz).join(", ")) : null)),
    h("div", { class: "actions" }, h("button", { class: "btn primary", on: { click: addPosition } }, svg(ICON.plus, 18), "Mening jurnalimga qo'shish"))));
  return () => chart.remove();
}
