import * as api from "../api";
import { dateUz, empty, errorBox, h, ICON, num, pct, skeleton, tone } from "../ui";

type Tab = "mid" | "long" | "tarix";
const KEY = "saralash.watchTab";

export default async function (root: HTMLElement) {
  root.append(h("div", { class: "page" }, skeleton(8)));
  let w: Awaited<ReturnType<typeof api.watchlist>>, rows: api.Row[];
  try { [w, rows] = await Promise.all([api.watchlist(), api.scores()]); } catch (e) {
    root.replaceChildren(errorBox("Kuzatuv ro'yxati yuklanmadi: " + (e as Error).message, () => location.reload()));
    return;
  }
  const byT = new Map(rows.map((r) => [r.t, r]));
  let tab: Tab = "mid";
  try { tab = (localStorage.getItem(KEY) as Tab) || "mid"; } catch { /* */ }
  const body = h("div");
  const tabs = h("div", { class: "seg", role: "tablist" });

  function item(t: string, it: api.WatchItem, profile: "mid" | "long") {
    const r = byT.get(t);
    const ret = r?.price && it.price ? r.price / it.price - 1 : null;
    const ready = profile === "mid" && r?.watch_mid === "tayyor";
    return h("a", { class: "witem" + (ready ? " ready" : ""), href: `#/aksiya/${encodeURIComponent(t)}` },
      h("div", { class: "w-top" },
        h("strong", null, t),
        r?.signal ? h("span", { class: "chip brand" }, `Bugun: ${api.KIND_NAMES[r.signal]}`) : ready ? h("span", { class: "chip up" }, "Kirishga tayyor") : null,
        h("span", { class: "w-ret " + tone(ret) }, pct(ret, 1, true))),
      h("p", { class: "w-name" }, r?.name || "", r?.sector ? `, ${r.sector}` : ""),
      h("p", { class: "w-reason" }, it.reason),
      h("p", { class: "dim small" }, `${dateUz(it.entered)} dan, ${num(it.price)} narxda. Ball: ${num((profile === "mid" ? r?.mid : r?.long) ?? null, 0)}`));
  }

  function draw() {
    try { localStorage.setItem(KEY, tab); } catch { /* */ }
    tabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
    if (tab === "tarix") {
      const hist = [...w.history].reverse();
      body.replaceChildren(hist.length ? h("div", { class: "table-wrap" }, h("table", { class: "hist" },
        h("thead", null, h("tr", null, h("th", null, "Aksiya"), h("th", null, "Muddat"), h("th", null, "Kirgan"), h("th", null, "Chiqqan"), h("th", { class: "r" }, "Natija"), h("th", null, "Chiqish sababi"))),
        h("tbody", null, hist.map((x) => h("tr", null,
          h("td", null, h("a", { href: `#/aksiya/${encodeURIComponent(x.ticker)}` }, x.ticker)),
          h("td", null, x.profile === "mid" ? "O'rta" : "Uzoq"),
          h("td", { title: x.reason_in }, dateUz(x.entered)), h("td", null, dateUz(x.exited)),
          h("td", { class: "r " + tone(x.ret) }, pct(x.ret, 1, true)),
          h("td", { class: "small" }, x.reason_out))))))
        : empty(ICON.eye, "Hali hech bir aksiya kuzatuvdan chiqmagan."));
      return;
    }
    const src = tab === "mid" ? w.mid : w.long;
    const list = Object.entries(src).sort((a, b) => {
      const ra = byT.get(a[0]), rb = byT.get(b[0]);
      const ka = (ra?.signal ? 2 : 0) + (ra?.watch_mid === "tayyor" ? 1 : 0), kb = (rb?.signal ? 2 : 0) + (rb?.watch_mid === "tayyor" ? 1 : 0);
      return kb - ka || b[1].entered.localeCompare(a[1].entered);
    });
    body.replaceChildren(
      h("p", { class: "dim" }, tab === "mid"
        ? "Bosqich 2 trendi, kuchli nisbiy kuch, cho'qqiga yaqin va kuchli sektorda. Kirish faqat pullback yoki breakout signali bilan."
        : "Sifatli biznes: Piotroski ≥ 6, ROE ≥ 15%, qarz me'yorida, erkin pul oqimi musbat, narx 40 haftalik o'rtachadan yuqori."),
      list.length ? h("div", { class: "wgrid" }, list.map(([t, it]) => item(t, it, tab as "mid" | "long")))
        : empty(ICON.eye, "Hozir shartlarga mos aksiya yo'q. Bu ham signal — bozor kuchsiz bo'lishi mumkin."));
  }

  const counts: Record<Tab, number> = { mid: Object.keys(w.mid).length, long: Object.keys(w.long).length, tarix: w.history.length };
  ([["mid", "O'rta"], ["long", "Uzoq"], ["tarix", "Tarix"]] as [Tab, string][]).forEach(([k, l]) =>
    tabs.append(h("button", { class: "seg-b", role: "tab", "data-tab": k, on: { click: () => { tab = k; draw(); } } }, l, h("small", null, ` ${counts[k]}`))));

  root.replaceChildren(h("div", { class: "page" },
    h("header", { class: "page-head" }, h("h1", null, "Kuzatuv"),
      h("p", { class: "dim" }, "Aksiya qoidaga mos kelganda kiradi va qoida buzilganda o'zi chiqadi. Har bir chiqish sababi bilan tarixda qoladi.")),
    tabs, body));
  draw();
}
