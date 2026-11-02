import * as api from "../api";
import { lineChart } from "../chart";
import { checks, dateUz, empty, errorBox, h, ICON, num, pct, rr, skeleton, svg, tone, usd } from "../ui";

const FLAG_NAMES: Record<string, string> = { kind: "Signal turi", rejim: "Bozor rejimi", vix: "VIX", sektor_kuchli: "Sektor kuchli yarmida", ep: "Katalizator (EP)", rs: "Nisbiy kuch" };
const VAL_NAMES: Record<string, string> = { green: "yashil", yellow: "sariq", red: "qizil", True: "ha", False: "yo'q", pullback: "pullback", breakout: "breakout" };
const WHY_NAMES: Record<string, string> = { stop: "Stop", maqsad: "Maqsad", "vaqt chegarasi": "40 kun o'tdi" };

export default async function (root: HTMLElement) {
  root.append(h("div", { class: "page" }, skeleton(8)));
  let p: api.Portfolio, L: api.Learn;
  try { [p, L] = await Promise.all([api.portfolio(), api.learn()]); } catch (e) {
    root.replaceChildren(errorBox("Virtual portfel yuklanmadi: " + (e as Error).message, () => location.reload()));
    return;
  }
  const last = p.equity[p.equity.length - 1];
  const first = p.equity[0];
  const start = p.params.start_equity;
  // SPUS'ga to'liq qo'yilgan bo'lsa: yadro qiymati / yadro aksiyalari = SPUS narxi
  const spusPx = p.equity.map((e) => (p.core_shares ? e[2] / p.core_shares : null));
  const spusOnly: [string, number][] = spusPx[0] ? p.equity.map((e, i) => [e[0], start * (spusPx[i]! / spusPx[0]!)]) : [];
  const total: [string, number][] = p.equity.map((e) => [e[0], e[1]]);
  const ret = last ? last[1] / start - 1 : null;
  const spusRet = spusOnly.length ? spusOnly[spusOnly.length - 1][1] / start - 1 : null;
  const st = p.stats;
  const prot = p.protection;
  const chartEl = h("div", { class: "chart" });

  const alloc = last ? [["Yadro (SPUS)", last[2], "a-core"], ["Faol pozitsiyalar", last[3], "a-sat"], ["Naqd", last[4], "a-cash"]] as [string, number, string][] : [];
  const statusText: Record<string, string> = { normal: "Normal", "yarim risk": "Yarim risk (pasayish −5% dan oshdi)", "to'xtatilgan": "Yangi xaridlar to'xtatilgan (pasayish −10% dan oshdi)" };
  const errNames: Record<string, string> = { stop_gap: "Stop ostidan gap bilan ochildi (−1.25R dan yomon)", time_exit_loss: "40 kunda maqsadga yetmay zarar bilan yopildi", watch_exit: "Kuzatuv qoidasi buzilib chiqildi" };

  root.replaceChildren(h("div", { class: "page" },
    h("header", { class: "page-head" }, h("h1", null, "Virtual portfel"),
      h("p", { class: "dim" }, `Dastur qoidalar bo'yicha o'zi sotib oladi va sotadi — real pul emas. Boshlangan: ${dateUz(p.started)}, boshlang'ich kapital ${usd(start)}.`)),
    first ? h("section", { class: "hero-stats" },
      h("div", { class: "hs-main" }, h("small", null, "Kapital"), h("b", null, usd(last[1])), h("span", { class: tone(ret) }, pct(ret, 1, true), " boshidan")),
      h("div", null, h("small", null, "Faqat SPUS bo'lganda"), h("b", null, spusOnly.length ? usd(spusOnly[spusOnly.length - 1][1]) : "—"), h("span", { class: tone(spusRet) }, pct(spusRet, 1, true))),
      h("div", null, h("small", null, "Eng katta pasayish"), h("b", { class: "down" }, pct(st.max_dd ?? null, 1))),
      h("div", null, h("small", null, "Himoya"), h("b", { class: prot.status === "normal" ? "" : "caution" }, statusText[prot.status || "normal"] || prot.status))) : null,
    !first ? empty(ICON.wallet, "Portfel birinchi skaner ishidan keyin boshlanadi.") : h("section", { class: "panel" },
      h("h2", null, "Portfel va SPUS"), chartEl,
      h("div", { class: "legend" }, h("span", { class: "lg lg-brand" }, "Portfel (yadro + faol)"), h("span", { class: "lg lg-dim" }, "Faqat SPUS")),
      alloc.length ? h("div", { class: "alloc", role: "img", "aria-label": alloc.map(([l, v]) => `${l}: ${usd(v)}`).join(", ") },
        alloc.map(([l, v, c]) => h("span", { class: c, style: { flexGrow: String(Math.max(v, 0)) }, title: `${l}: ${usd(v)}` }))) : null,
      h("div", { class: "alloc-legend" }, alloc.map(([l, v, c]) => h("span", null, h("i", { class: c }), `${l} ${usd(v)}`)))),
    h("div", { class: "grid2" },
      h("section", { class: "panel" }, h("h2", null, `Ochiq pozitsiyalar (${p.positions.length})`),
        p.positions.length ? h("div", { class: "table-wrap" }, h("table", null,
          h("thead", null, h("tr", null, h("th", null, "Aksiya"), h("th", { class: "r" }, "Kirish"), h("th", { class: "r" }, "Hozir"), h("th", { class: "r" }, "Stop"), h("th", { class: "r" }, "Maqsad"), h("th", { class: "r" }, "R"))),
          h("tbody", null, p.positions.map((x) => h("tr", null,
            h("td", null, h("a", { href: `#/aksiya/${encodeURIComponent(x.ticker)}` }, x.ticker), h("small", { class: "dim" }, ` ${api.KIND_NAMES[x.kind] || x.kind}, ${x.days} kun`)),
            h("td", { class: "r" }, num(x.entry)), h("td", { class: "r" }, num(x.price)), h("td", { class: "r down" }, num(x.stop)), h("td", { class: "r up" }, num(x.target)),
            h("td", { class: "r " + tone(x.r_now) }, rr(x.r_now)))))))
          : h("p", { class: "dim" }, "Ochiq pozitsiya yo'q — faol qism naqdda."),
        p.pending.length ? [h("h3", null, "Ertangi buyurtmalar (ochilish narxida)"),
          checks(p.pending.map((o) => ({ ok: null, t: `${o.ticker}: ${o.shares} ta, ${api.KIND_NAMES[o.kind] || o.kind}, stop ${num(o.stop)}, maqsad ${num(o.target)}` })))] : null),
      h("section", { class: "panel" }, h("h2", null, "Natija ko'rsatkichlari"),
        h("dl", { class: "kv" },
          h("dt", null, "Yopilgan savdolar"), h("dd", null, String(st.trades ?? 0)),
          h("dt", null, "Yutuq foizi"), h("dd", null, pct(st.winrate ?? null, 0)),
          h("dt", null, "O'rtacha yutuq / zarar"), h("dd", null, `${rr(st.avg_win ?? null)} / ${rr(st.avg_loss ?? null)}`),
          h("dt", null, "Kutilma (bir savdoga)"), h("dd", { class: tone(st.expectancy ?? null) }, rr(st.expectancy ?? null)),
          h("dt", null, "Profit faktor"), h("dd", null, num(st.profit_factor ?? null)),
          h("dt", null, "Ketma-ket zararlar (eng ko'p)"), h("dd", null, String(st.max_losing_streak ?? "—")),
          h("dt", null, "O'rtacha ushlab turish"), h("dd", null, st.avg_days ? `${Math.round(st.avg_days)} kun` : "—")),
        h("p", { class: "dim small" }, "Kutilma musbat va kamida 100 ta savdo bo'lmaguncha, natija tasodif bo'lishi mumkin."))),
    h("section", { class: "panel" }, h("h2", null, "O'rganish"),
      h("p", { class: "dim small" }, "Dastur qoidalarni o'zi o'zgartirmaydi. Farq yetarli savdoda tasdiqlansa, taklif chiqadi — qabul qilish sizning qaroringiz."),
      L.proposals.length ? h("div", { class: "proposals" }, L.proposals.map((x) => h("p", { class: "proposal" }, svg(ICON.bulb, 18), h("span", null, x.text))))
        : h("p", null, `Hozircha taklif yo'q: har bir guruhda kamida 30 ta savdo kerak (hozir jami ${L.n}).`),
      Object.keys(L.errors).length ? [h("h3", null, "Xatolar hisobi"), h("dl", { class: "kv" }, Object.entries(L.errors).flatMap(([k, v]) => [h("dt", null, errNames[k] || k), h("dd", null, String(v))]))] : null,
      L.groups.length ? [h("h3", null, "Belgilar bo'yicha natija"), h("div", { class: "table-wrap" }, h("table", null,
        h("thead", null, h("tr", null, h("th", null, "Kirish paytidagi holat"), h("th", { class: "r" }, "Savdolar"), h("th", { class: "r" }, "Yutuq"), h("th", { class: "r" }, "Kutilma"))),
        h("tbody", null, L.groups.map((g) => h("tr", null, h("td", null, `${FLAG_NAMES[g.flag] || g.flag}: ${VAL_NAMES[g.value] || g.value}`),
          h("td", { class: "r" + (g.n < 30 ? " dim" : "") }, String(g.n)), h("td", { class: "r" }, pct(g.win, 0)), h("td", { class: "r " + tone(g.exp) }, rr(g.exp)))))))] : null),
    h("section", { class: "panel" }, h("h2", null, "Oxirgi savdolar"),
      p.trades.length ? h("div", { class: "table-wrap" }, h("table", null,
        h("thead", null, h("tr", null, h("th", null, "Aksiya"), h("th", null, "Kirdi"), h("th", null, "Chiqdi"), h("th", null, "Sabab"), h("th", { class: "r" }, "Foyda"), h("th", { class: "r" }, "R"))),
        h("tbody", null, [...p.trades].reverse().slice(0, 60).map((x) => h("tr", null,
          h("td", null, h("a", { href: `#/aksiya/${encodeURIComponent(x.ticker)}` }, x.ticker)),
          h("td", null, dateUz(x.entry_date)), h("td", null, dateUz(x.exit_date)),
          h("td", { class: "small" }, WHY_NAMES[x.why] || x.why),
          h("td", { class: "r " + tone(x.pnl) }, usd(x.pnl)), h("td", { class: "r " + tone(x.r) }, rr(x.r)))))))
        : h("p", { class: "dim" }, "Hali yopilgan savdo yo'q."),
      p.log.length ? [h("h3", null, "Bekor qilingan buyurtmalar"), checks(p.log.slice(-10).reverse().map((l) => ({ ok: false, t: `${dateUz(l.d)}, ${l.t}: ${l.why}` })))] : null)));
  if (!first) return;
  const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const chart = lineChart(chartEl, [
    { name: "Portfel", color: css("--brand"), data: total },
    { name: "SPUS", color: css("--text-dim"), data: spusOnly, dashed: true }]);
  return () => chart.remove();
}
