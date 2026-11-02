import * as api from "../api";
import * as store from "../store";
import * as sync from "../sync";
import { dateUz, field, h, ICON, modal, numInput, parseNum, svg, toast, todayIso } from "../ui";

declare const __APP_VERSION__: string;

const SYNC_TEXT: Record<sync.SyncState, string> = {
  "o'chiq": "Bulut ulanmagan — ma'lumot faqat shu qurilmada.",
  kirilmagan: "Bulut sozlangan, lekin kirilmagan.",
  sinxron: "Sinxronlangan.",
  yuborilmoqda: "Yuborilmoqda…",
  offline: "Internet yo'q — ulanganda yuboriladi.",
  xato: "Sinxronda xato. Keyinroq qayta uriniladi.",
};

export function applyMode(mode: string) {
  try { localStorage.setItem("saralash.mode", mode); } catch { /* */ }
  const m = mode === "auto" ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : mode;
  document.documentElement.dataset.mode = m;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", m === "dark" ? "#0F1426" : "#2536A8");
}

export default async function (root: HTMLElement) {
  const s = store.get().settings;
  const dep = numInput(s.deposit), mon = numInput(s.monthly), core = numInput(s.core_pct), risk = numInput(s.risk_pct);
  let mode = "auto";
  try { mode = localStorage.getItem("saralash.mode") || "auto"; } catch { /* */ }

  async function save() {
    const d = parseNum(dep.value), m = parseNum(mon.value), c = parseNum(core.value), r = parseNum(risk.value);
    if (!(d > 0)) return toast("Depozit musbat son bo'lishi kerak");
    if (!(m >= 0)) return toast("Oylik qo'shimcha 0 yoki undan katta bo'lishi kerak");
    if (!(c >= 0 && c <= 100)) return toast("Yadro ulushi 0–100% oralig'ida");
    if (!(r > 0 && r <= 2)) return toast("Savdo riski 0–2% oralig'ida — 2% dan katta risk depozitni xavf ostiga qo'yadi");
    if (await store.update((x) => { x.settings.deposit = d; x.settings.monthly = m; x.settings.core_pct = c; x.settings.risk_pct = r; })) toast("Saqlandi");
  }

  const modeSeg = h("div", { class: "seg", role: "group", "aria-label": "Mavzu" },
    ([["auto", "Tizim bo'yicha"], ["light", "Yorug'"], ["dark", "Qorong'i"]] as const).map(([v, l]) =>
      h("button", { class: "seg-b", "aria-pressed": String(mode === v), on: { click: (e) => {
        applyMode(v);
        (e.currentTarget as HTMLElement).parentElement!.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget)));
        window.dispatchEvent(new HashChangeEvent("hashchange"));   // grafiklar yangi ranglar bilan qayta chiziladi
      } } }, l)));

  const syncBox = h("div");
  function drawSync() {
    const st = sync.syncStatus();
    if (!sync.configured) {
      syncBox.replaceChildren(h("p", { class: "dim small" }, SYNC_TEXT["o'chiq"], " Ikkinchi qurilmada ishlatish uchun README'dagi Supabase bo'limini bajaring yoki zaxira faylidan foydalaning."));
      return;
    }
    if (!st.email) {
      const em = h("input", { type: "email", autocomplete: "email", placeholder: "email@misol.uz" });
      syncBox.replaceChildren(h("p", { class: "small" }, SYNC_TEXT[st.status]), field("Email", em, "Kirish havolasi shu emailga yuboriladi. Faqat oldindan qo'shilgan foydalanuvchi kira oladi."),
        h("button", { class: "btn", on: { click: async () => {
          if (!/^\S+@\S+\.\S+$/.test(em.value.trim())) return toast("Email noto'g'ri");
          try { await sync.signIn(em.value.trim()); toast("Havola yuborildi — pochtangizni oching"); } catch (e) { toast("Yuborilmadi: " + (e as Error).message); }
        } } }, "Kirish havolasini yuborish"));
      return;
    }
    syncBox.replaceChildren(h("p", { class: "small" }, svg(ICON.sync, 14), ` ${st.email}: ${SYNC_TEXT[st.status]}`),
      h("div", { class: "row-btns" },
        h("button", { class: "btn", on: { click: () => sync.push().catch(() => {}) } }, "Hozir sinxronlash"),
        h("button", { class: "btn ghost", on: { click: () => sync.signOut() } }, "Chiqish")));
  }
  const unSync = sync.onSync(drawSync);
  drawSync();

  function exportFile() {
    const url = URL.createObjectURL(store.exportJson());
    const a = h("a", { href: url, download: `saralash-zaxira-${todayIso()}.json` });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    toast("Zaxira fayli yuklab olindi");
  }
  const fileIn = h("input", { type: "file", accept: "application/json,.json", hidden: true, on: { change: async () => {
    const f = fileIn.files?.[0]; fileIn.value = "";
    if (!f) return;
    if (f.size > 5_000_000) return toast("Fayl juda katta");
    const text = await f.text();
    modal("Zaxiradan tiklash", h("p", null, "Joriy jurnal va sozlamalar fayldagisi bilan almashtiriladi. Avval hozirgi holatni zaxiralab qo'yish tavsiya etiladi."), [
      { label: "Bekor qilish", onClick: () => {} },
      { label: "Tiklash", primary: true, onClick: async () => {
        try { await store.importJson(text); toast("Tiklandi"); window.dispatchEvent(new HashChangeEvent("hashchange")); }
        catch (e) { toast((e as Error).message); return false; }
      } }]);
  } } });

  const about = h("dl", { class: "kv" });
  api.meta().then((m) => about.append(
    h("dt", null, "Ma'lumot sanasi"), h("dd", null, dateUz(m.date) + (m.demo ? " (DEMO)" : "")),
    h("dt", null, "Qoidalar versiyasi"), h("dd", null, m.rules_version),
    h("dt", null, "Aksiyalar ro'yxati"), h("dd", null, `${m.universe} ta, ${m.universe_source}`),
    h("dt", null, "Fundamental qamrov"), h("dd", null, `${m.fund_coverage} ta`))).catch(() => {});

  root.append(h("div", { class: "page narrow" },
    h("header", { class: "page-head" }, h("h1", null, "Sozlamalar")),
    h("section", { class: "panel" }, h("h2", null, "Pul va risk"),
      h("div", { class: "form" },
        field("Investitsiya depoziti, $", dep, "Pozitsiya hajmi shundan hisoblanadi"),
        field("Har oylik qo'shimcha, $", mon),
        field("Yadro (SPUS) ulushi, %", core, "Qolgani faol qism. Standart 60%"),
        field("Bir savdo riski, % depozitdan", risk, "Stopga tegsa yo'qotiladigan qism. Standart 0.75%")),
      h("button", { class: "btn primary", on: { click: save } }, "Saqlash")),
    h("section", { class: "panel" }, h("h2", null, "Ko'rinish"), modeSeg),
    h("section", { class: "panel" }, h("h2", null, "Bulut sinxroni"), syncBox),
    h("section", { class: "panel" }, h("h2", null, "Zaxira"),
      h("p", { class: "dim small" }, "Jurnal va sozlamalar JSON fayl sifatida. Telefon almashtirganda yoki brauzer tozalanganda kerak bo'ladi."),
      h("div", { class: "row-btns" },
        h("button", { class: "btn", on: { click: exportFile } }, "Zaxira faylini olish"),
        h("button", { class: "btn", on: { click: () => fileIn.click() } }, "Fayldan tiklash")), fileIn),
    h("section", { class: "panel" }, h("h2", null, "Ilova haqida"), about,
      h("p", { class: "dim small" }, `Saralash v${__APP_VERSION__}. Bu investitsiya maslahati emas: dastur qoidalarni ko'rsatadi va sinaydi, qarorni siz qabul qilasiz. Real savdodan oldin halollikni Hyssa'da tekshiring.`),
      h("button", { class: "btn ghost", on: { click: () => store.update((x) => { x.settings.onboarded = false; }).then(() => location.reload()) } }, "Tanishuvni qayta ko'rsatish"))));
  return () => { unSync(); };
}
