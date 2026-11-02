import * as api from "../api";
import * as store from "../store";
import { append, dateUz, empty, field, h, ICON, modal, num, numInput, parseNum, pct, rr, svg, toast, todayIso, tone, usd } from "../ui";

export default async function (root: HTMLElement) {
  const byT = new Map<string, api.Row>();
  const impure = new Map<string, number>();
  try { (await api.scores()).forEach((r) => byT.set(r.t, r)); } catch { /* narxlarsiz ham jurnal ishlaydi */ }
  const body = h("div");

  async function loadImpure(ts: string[]) {
    await Promise.all(ts.filter((t) => !impure.has(t)).map((t) => api.card(t)
      .then((c) => impure.set(t, Number(c.fund?.impure_per_share_q) || 0)).catch(() => impure.set(t, 0))));
  }

  function rNow(p: store.Position, price: number | null): number | null {
    return p.stop !== null && p.entry > p.stop && price !== null ? (price - p.entry) / (p.entry - p.stop) : null;
  }

  function addNew() {
    const t = h("input", { type: "text", maxlength: 8, autocapitalize: "characters", placeholder: "Masalan, MSFT" });
    const prof = h("select", null, h("option", { value: "mid" }, "O'rta muddat (2 hafta – 6 oy)"), h("option", { value: "long" }, "Uzoq muddat (1 yil+)"));
    const qty = numInput(""), entry = numInput(""), stop = numInput(""), target = numInput("");
    const date = h("input", { type: "date", value: todayIso(), max: todayIso() });
    const note = h("input", { type: "text", maxlength: 200, placeholder: "Nega sotib oldim" });
    modal("Yangi pozitsiya", h("div", { class: "form" },
      field("Ticker", t), field("Profil", prof, "Keyin o'zgarmaydi"), field("Aksiyalar soni", qty), field("Kirish narxi, $", entry),
      field("Stop, $", stop, "Stopsiz pozitsiya R va intizom statistikasiga kirmaydi"), field("Maqsad, $", target), field("Sana", date), field("Izoh", note)), [
      { label: "Bekor qilish", onClick: () => {} },
      { label: "Qo'shish", primary: true, onClick: async () => {
        const tk = t.value.trim().toUpperCase(), q = parseNum(qty.value), e = parseNum(entry.value);
        const st = stop.value.trim() ? parseNum(stop.value) : null, tg = target.value.trim() ? parseNum(target.value) : null;
        if (!/^[A-Z][A-Z0-9.\-]{0,7}$/.test(tk)) { toast("Ticker noto'g'ri"); return false; }
        if (!(q > 0) || !(e > 0)) { toast("Soni va narxni to'g'ri kiriting"); return false; }
        if (st !== null && !(st > 0 && st < e)) { toast("Stop 0 dan katta va kirish narxidan past bo'lishi kerak"); return false; }
        if (tg !== null && !(tg > e)) { toast("Maqsad kirish narxidan yuqori bo'lishi kerak"); return false; }
        const ok = await store.update((s) => { s.positions.push({ id: crypto.randomUUID(), ticker: tk, profile: prof.value as "mid" | "long", kind: "qo'lda",
          qty: q, entry: e, date: date.value || todayIso(), stop: st, target: tg, note: note.value.trim(), followed_plan: null, exit: null, exit_date: null, exit_note: "", purified: 0 }); });
        if (ok) toast(`${tk} qo'shildi`);
      } }]);
  }

  function closePos(p: store.Position) {
    const px = numInput(byT.get(p.ticker)?.price?.toFixed(2) ?? "");
    const date = h("input", { type: "date", value: todayIso(), min: p.date, max: todayIso() });
    const plan = h("select", null, h("option", { value: "" }, "Belgilanmagan"), h("option", { value: "1" }, "Ha — reja bo'yicha chiqdim"), h("option", { value: "0" }, "Yo'q — rejadan chetga chiqdim"));
    const note = h("input", { type: "text", maxlength: 200, placeholder: "Nima o'rgandim" });
    modal(`${p.ticker} — sotish`, h("div", { class: "form" },
      field("Sotish narxi, $", px), field("Sana", date), field("Reja bo'yicha chiqdimmi?", plan, "Intizom statistikasi shundan hisoblanadi"), field("Izoh", note)), [
      { label: "Bekor qilish", onClick: () => {} },
      { label: "Sotildi deb belgilash", primary: true, onClick: async () => {
        const x = parseNum(px.value);
        if (!(x > 0)) { toast("Sotish narxini kiriting"); return false; }
        const ok = await store.update((s) => { const q = s.positions.find((y) => y.id === p.id); if (!q) return;
          q.exit = x; q.exit_date = date.value || todayIso(); q.exit_note = note.value.trim(); q.followed_plan = plan.value === "" ? null : plan.value === "1"; });
        if (ok) toast(`${p.ticker} sotildi deb belgilandi`);
      } }]);
  }

  async function remove(p: store.Position) {
    const snapshot = structuredClone(store.get().positions);
    const ok = await store.update((s) => { s.positions = s.positions.filter((y) => y.id !== p.id); });
    if (ok) toast(`${p.ticker} o'chirildi`, () => { store.update((s) => { s.positions = snapshot; }); });
  }

  async function markPurified(p: store.Position, amount: number) {
    await store.update((s) => { const q = s.positions.find((y) => y.id === p.id); if (q) q.purified = Math.round(amount * 100) / 100; });
    toast(`${p.ticker}: ${usd(amount)} tozalandi deb belgilandi`);
  }

  async function draw() {
    const ps = store.get().positions;
    const open = ps.filter((p) => p.exit === null).sort((a, b) => b.date.localeCompare(a.date));
    const closed = ps.filter((p) => p.exit !== null).sort((a, b) => (b.exit_date || "").localeCompare(a.exit_date || ""));
    await loadImpure([...new Set(ps.map((p) => p.ticker))]);
    const st = store.closedStats(ps);
    const s = store.get().settings;
    const openRisk = open.reduce((a, p) => a + (p.stop !== null ? Math.max(0, (p.entry - p.stop) * p.qty) : 0), 0);
    const owed = ps.reduce((a, p) => a + Math.max(0, store.purification(p, impure.get(p.ticker) || 0) - p.purified), 0);

    const posCard = (p: store.Position) => {
      const price = p.exit ?? byT.get(p.ticker)?.price ?? null;
      const r = p.exit !== null ? rNow(p, p.exit) : rNow(p, price);
      const ret = price !== null ? price / p.entry - 1 : null;
      const pur = store.purification(p, impure.get(p.ticker) || 0);
      const due = Math.max(0, pur - p.purified);
      const days = Math.round((Date.parse(p.exit_date || todayIso()) - Date.parse(p.date)) / 86400000);
      const row = byT.get(p.ticker);
      const warn = p.exit === null && p.stop !== null && price !== null && price <= p.stop;
      return h("article", { class: "jpos" + (warn ? " warn" : "") },
        h("div", { class: "j-top" },
          h("a", { href: `#/aksiya/${encodeURIComponent(p.ticker)}` }, h("strong", null, p.ticker)),
          h("span", { class: "chip quiet" }, p.profile === "mid" ? "O'rta" : "Uzoq"),
          p.followed_plan === true ? h("span", { class: "chip up" }, "Reja bo'yicha") : p.followed_plan === false ? h("span", { class: "chip down" }, "Rejadan chetga") : null,
          h("span", { class: "j-ret " + tone(ret) }, pct(ret, 1, true), r !== null ? ` (${rr(r)})` : "")),
        h("p", { class: "small" }, `${num(p.qty, 0)} ta × ${usd(p.entry)}, ${dateUz(p.date)}`,
          p.exit !== null ? `. Sotildi ${usd(p.exit)}, ${dateUz(p.exit_date)} (${days} kun)` : `. Hozir ${usd(price)}, ${days} kun`),
        h("p", { class: "small dim" }, `Stop ${usd(p.stop)}, maqsad ${usd(p.target)}`, p.note ? `. ${p.note}` : "", p.exit_note ? `. ${p.exit_note}` : ""),
        warn ? h("p", { class: "small down" }, "Narx stopdan past — reja bo'yicha sotish vaqti.") : null,
        p.exit === null && row && !row.watch_mid && !row.watch_long ? h("p", { class: "small caution" }, "Bu aksiya hozir kuzatuv ro'yxatidan tashqarida — sababini kartasida ko'ring.") : null,
        pur > 0 ? h("p", { class: "small" }, `Tozalash: ${usd(pur)}`, due > 0.005 ? `, to'lanmagan ${usd(due)}` : ", to'langan") : null,
        h("div", { class: "j-actions" },
          p.exit === null ? h("button", { class: "btn small", on: { click: () => closePos(p) } }, "Sotildi") : null,
          due > 0.005 ? h("button", { class: "btn small", on: { click: () => markPurified(p, pur) } }, "Tozalandi") : null,
          h("button", { class: "btn small ghost", on: { click: () => remove(p) } }, "O'chirish")));
    };

    body.replaceChildren();
    append(body, [
      h("section", { class: "hero-stats" },
        h("div", { class: "hs-main" }, h("small", null, "Yopilgan savdolar natijasi"), h("b", { class: tone(st.pnl) }, usd(st.pnl)), h("span", null, `${st.n} ta savdo`)),
        h("div", null, h("small", null, "Kutilma"), h("b", { class: tone(st.expectancy) }, rr(st.expectancy)), h("span", { class: "dim" }, `${st.nR} ta stopli savdo`)),
        h("div", null, h("small", null, "Yutuq foizi"), h("b", null, pct(st.winrate, 0))),
        h("div", null, h("small", null, "Rejaga amal qilish"), h("b", null, pct(st.plan_rate, 0)))),
      open.length ? h("p", { class: "small" + (openRisk > s.deposit * 0.05 ? " caution" : " dim") },
        `Ochiq risk: ${usd(openRisk)} — depozitning ${pct(openRisk / s.deposit, 1)}. Chegara 5%.`) : null,
      owed > 0.005 ? h("p", { class: "small" }, svg(ICON.shield, 14), ` Jami to'lanmagan tozalash: ${usd(owed)}`) : null,
      h("div", { class: "actions" }, h("button", { class: "btn primary", on: { click: addNew } }, svg(ICON.plus, 18), "Pozitsiya qo'shish")),
      h("h2", null, `Ochiq (${open.length})`),
      open.length ? h("div", { class: "wgrid" }, open.map(posCard)) : empty(ICON.book, "Ochiq pozitsiya yo'q. Aksiya kartasidan yoki shu yerdan qo'shing."),
      closed.length ? [h("h2", null, `Yopilgan (${closed.length})`), h("div", { class: "wgrid" }, closed.map(posCard))] : null]);
  }

  root.replaceChildren(h("div", { class: "page" },
    h("header", { class: "page-head" }, h("h1", null, "Jurnalim"),
      h("p", { class: "dim" }, "Real savdolaringiz. Faqat shu qurilmada saqlanadi; Sozlamalarda bulut sinxronini yoqish yoki zaxira faylini olish mumkin.")),
    body));
  await draw();
  return store.subscribe(() => { draw(); }) as () => void;
}
