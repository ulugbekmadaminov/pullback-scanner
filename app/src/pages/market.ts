import * as api from "../api";
import { regimeChart } from "../chart";
import { checks, dateUz, errorBox, h, num, pct, skeleton, tone } from "../ui";

function verdict(m: api.Market): { line: string; sub: string; cls: string } {
  if (!m.allow_buys) return { line: "Bugun yangi xarid yo'q", sub: "Depozit himoyasi ishlayapti — ochiq pozitsiyalar o'z rejasi bilan boshqariladi.", cls: "red" };
  if (m.risk_mult < 1) return { line: `Xarid mumkin, risk ${Math.round(m.risk_mult * 100)}% ga kamaytirilgan`, sub: "Bozor sharoiti to'liq qulay emas — pozitsiyalar kichikroq olinadi.", cls: "yellow" };
  return { line: "Bozor qulay — qoidalar bo'yicha xarid mumkin", sub: "Faqat kuzatuvdagi va signal bergan aksiyalar, oddiy risk bilan.", cls: "green" };
}

export default async function (root: HTMLElement) {
  root.append(h("div", { class: "page" }, skeleton(6)));
  let m: api.Market, meta: api.Meta;
  try {
    [m, meta] = await Promise.all([api.market(), api.meta()]);
  } catch (e) {
    root.replaceChildren(errorBox("Bozor ma'lumoti yuklanmadi: " + (e as Error).message + ". Skaner hali ishga tushmagan bo'lishi mumkin.", () => location.reload()));
    return;
  }
  const v = verdict(m);
  const tape = h("div", { class: "tape", role: "img", "aria-label": "Oxirgi bir yildagi Nasdaq rejimi: yashil, sariq yoki qizil kunlar" },
    m.history.regime.map((r, i) => h("span", { class: `t-${r || "none"}`, title: `${m.history.t[i]}: ${api.REGIME_NAMES[r || ""] || "—"}` })));
  const d = m.regime_detail;
  const chartEl = h("div", { class: "chart chart-sm" });
  const sectorsBy = (g: string) => m.sectors.filter((s) => s.group === g);
  const groupTitle: Record<string, string> = { himoya: "Himoya qiluvchi", sezuvchan: "Sezuvchan", davriy: "Davriy" };

  root.replaceChildren(h("div", { class: "page" },
    h("section", { class: `verdict v-${v.cls}` },
      h("p", { class: "v-date" }, `${dateUz(meta.date)} yopilishi bo'yicha`),
      h("h1", null, v.line),
      h("p", { class: "v-sub" }, v.sub),
      tape,
      h("div", { class: "tape-legend" }, h("span", null, "1 yil oldin"), h("span", null, "bugun"))),
    h("div", { class: "grid2" },
      h("section", { class: "panel" },
        h("h2", null, "Nega shunday?"),
        m.reasons.length ? checks(m.reasons.map((t) => ({ ok: false, t }))) : checks([{ ok: true, t: "Cheklov yo'q: rejim yashil, VIX me'yorida, risk ishtahasi ijobiy" }]),
        d ? checks([
          { ok: d.above_sma200, t: `Nasdaq (QQQ) ${num(d.close)} — 200 kunlik o'rtacha ${num(d.sma200)} ${d.above_sma200 ? "ustida" : "ostida"}` },
          { ok: d.support_ok, t: `Oxirgi tayanch ${num(d.support)} ${d.support_ok ? "saqlanmoqda" : "ostida ketma-ket 2 kun yopildi"}` },
        ]) : null),
      h("section", { class: "panel" },
        h("h2", null, "Kayfiyat"),
        h("dl", { class: "kv" },
          h("dt", null, "VIX (qo'rquv indeksi)"), h("dd", { class: (m.vix ?? 0) >= 22 ? "down" : "" }, num(m.vix, 1)),
          h("dt", null, "Risk ishtahasi, 1 oy"), h("dd", { class: tone(m.risk_on_21) }, pct(m.risk_on_21, 1, true)),
          h("dt", null, "Risk ishtahasi, 3 oy"), h("dd", { class: tone(m.risk_on_63) }, pct(m.risk_on_63, 1, true)),
          h("dt", null, "Kichik kompaniyalar (IWM−SPY), 3 oy"), h("dd", { class: tone(m.breadth_63) }, pct(m.breadth_63, 1, true))),
        h("p", { class: "dim small" }, "Risk ishtahasi — sezuvchan va davriy sektorlarning himoya sektorlaridan ustunligi. Manfiy bo'lsa, katta pul xavfdan qochmoqda."))),
    h("section", { class: "panel" }, h("h2", null, "Nasdaq va rejim"), chartEl,
      h("p", { class: "dim small" }, "Chiziq rangi o'sha kungi rejimni bildiradi. Uzuq chiziq — 200 kunlik o'rtacha.")),
    h("section", { class: "panel" },
      h("h2", null, "Indekslar"),
      h("div", { class: "table-wrap" }, h("table", null,
        h("thead", null, h("tr", null, h("th", null, "Indeks"), h("th", { class: "r" }, "Narx"), h("th", { class: "r" }, "Kun"), h("th", { class: "r" }, "1 oy"), h("th", { class: "r" }, "3 oy"))),
        h("tbody", null, m.indices.map((x) => h("tr", null, h("td", null, x.ticker), h("td", { class: "r" }, num(x.close)),
          h("td", { class: `r ${tone(x.r1d)}` }, pct(x.r1d, 2, true)), h("td", { class: `r ${tone(x.r21)}` }, pct(x.r21, 1, true)),
          h("td", { class: `r ${tone(x.r63)}` }, pct(x.r63, 1, true)))))))),
    h("section", { class: "panel" },
      h("h2", null, "Sektorlar: SPY'ga nisbatan kuch"),
      h("p", { class: "dim small" }, "Kuchli yarmidagi sektor aksiyalari kuzatuvga kirish shartidan biri. Moliya va ko'chmas mulk faqat bozor signali sifatida — ulardagi aksiyalarning ko'pi halol emas."),
      h("div", { class: "sector-groups" }, ["himoya", "sezuvchan", "davriy"].map((g) => h("div", { class: "sg" },
        h("h3", null, groupTitle[g]),
        sectorsBy(g).map((s) => h("div", { class: "sector" },
          h("span", { class: "rank" + (s.top_half ? " top" : "") }, String(s.rank)),
          h("span", { class: "s-name" }, s.name, h("small", null, s.etf)),
          h("span", { class: `s-v ${tone(s.rel21)}` }, pct(s.rel21, 1, true), h("small", null, "1 oy")),
          h("span", { class: `s-v ${tone(s.rel63)}` }, pct(s.rel63, 1, true), h("small", null, "3 oy"))))))))));
  const chart = regimeChart(chartEl, m.history);
  return () => chart.remove();
}
