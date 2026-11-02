import "@fontsource-variable/onest";
import "./styles.css";
import * as api from "./api";
import * as store from "./store";
import * as sync from "./sync";
import { h, ICON, modal, svg, toast, field, numInput, parseNum } from "./ui";

declare const __APP_VERSION__: string;
export const APP_VERSION = __APP_VERSION__;

export type Page = (root: HTMLElement, arg: string) => void | (() => void) | Promise<void | (() => void)>;

const NAV: { id: string; label: string; icon: string; primary: boolean }[] = [
  { id: "bozor", label: "Bozor", icon: ICON.market, primary: true },
  { id: "royxat", label: "Ro'yxat", icon: ICON.list, primary: true },
  { id: "kuzatuv", label: "Kuzatuv", icon: ICON.eye, primary: true },
  { id: "portfel", label: "Portfel", icon: ICON.wallet, primary: true },
  { id: "musobaqa", label: "Musobaqa", icon: ICON.trophy, primary: false },
  { id: "jurnal", label: "Jurnalim", icon: ICON.book, primary: false },
  { id: "backtest", label: "Backtest", icon: ICON.flask, primary: false },
  { id: "sozlamalar", label: "Sozlamalar", icon: ICON.gear, primary: false },
];

const pages: Record<string, () => Promise<{ default: Page }>> = {
  bozor: () => import("./pages/market"),
  royxat: () => import("./pages/list"),
  aksiya: () => import("./pages/card"),
  kuzatuv: () => import("./pages/watch"),
  portfel: () => import("./pages/portfolio"),
  musobaqa: () => import("./pages/compete"),
  jurnal: () => import("./pages/journal"),
  backtest: () => import("./pages/backtest"),
  sozlamalar: () => import("./pages/settings"),
  koproq: () => import("./pages/more"),
};

let cleanup: void | (() => void);
const main = h("main", { id: "main", tabindex: "-1" });
const sideNav = h("nav", { class: "side", "aria-label": "Bo'limlar" });
const bottomNav = h("nav", { class: "bottom", "aria-label": "Bo'limlar" });
const demoBar = h("div", { class: "demo-bar", hidden: true });

function navLink(n: { id: string; label: string; icon: string }, cls: string) {
  return h("a", { href: `#/${n.id}`, class: cls, "data-id": n.id }, svg(n.icon, 20), h("span", null, n.label));
}

function shell() {
  const app = document.getElementById("app")!;
  sideNav.append(
    h("a", { href: "#/bozor", class: "brand", "aria-label": "Saralash — bosh sahifa" }, brandMark(), h("span", null, "Saralash")),
    ...NAV.map((n) => navLink(n, "side-link")),
    h("p", { class: "side-foot" }, `v${APP_VERSION}`),
  );
  bottomNav.append(...NAV.filter((n) => n.primary).map((n) => navLink(n, "tab")), navLink({ id: "koproq", label: "Ko'proq", icon: ICON.more }, "tab"));
  app.append(demoBar, h("div", { class: "layout" }, sideNav, main), bottomNav);
}

export function brandMark(size = 26): SVGSVGElement {
  const ns = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(ns, "svg");
  s.setAttribute("viewBox", "0 0 32 32");
  s.setAttribute("width", String(size));
  s.setAttribute("height", String(size));
  s.setAttribute("aria-hidden", "true");
  s.setAttribute("class", "mark-svg");
  // zinapoya: uchta ustun, bir xil asosda (y=27), har biri oldingisidan baland
  [[4, 19], [13, 12], [22, 5]].forEach(([x, y], k) => {
    const r = document.createElementNS(ns, "rect");
    r.setAttribute("x", String(x)); r.setAttribute("y", String(y)); r.setAttribute("width", "7");
    r.setAttribute("height", String(27 - y)); r.setAttribute("rx", "1.6");
    r.setAttribute("class", k === 2 ? "m-up" : "m-base");
    s.appendChild(r);
  });
  return s;
}

async function route() {
  const [, id = "bozor", arg = ""] = location.hash.split("/");
  const key = pages[id] ? id : "bozor";
  for (const a of document.querySelectorAll<HTMLAnchorElement>("nav a[data-id]")) {
    const active = a.dataset.id === key || (key === "aksiya" && a.dataset.id === "royxat") ||
      (!NAV.find((n) => n.id === key && n.primary) && a.dataset.id === "koproq" && !["aksiya"].includes(key) && a.classList.contains("tab"));
    a.toggleAttribute("aria-current", active);
  }
  if (typeof cleanup === "function") cleanup();
  main.replaceChildren();
  window.scrollTo(0, 0);
  try {
    const mod = await pages[key]();
    cleanup = await mod.default(main, decodeURIComponent(arg));
  } catch (e) {
    main.replaceChildren(h("div", { class: "error-box", role: "alert" },
      h("p", null, "Sahifani ochib bo'lmadi: " + (e as Error).message),
      h("button", { class: "btn", on: { click: () => route() } }, "Qayta urinish")));
  }
  main.focus({ preventScroll: true });
}

function onboarding() {
  const s = store.get().settings;
  const dep = numInput(s.deposit), mon = numInput(s.monthly);
  const body = h("div", { class: "stack" },
    h("p", null, "Saralash halol AQSh aksiyalarini qoidalar asosida saralaydi, nega tanlanganini ko'rsatadi va qoidalarni virtual portfelda sinab boradi."),
    h("p", { class: "dim" }, "Bu investitsiya maslahati emas. Har bir qarorni o'zingiz qabul qilasiz va real savdodan oldin halollikni Hyssa'da tekshirasiz."),
    field("Investitsiya depoziti, $", dep, "Pozitsiya hajmi shu summadan hisoblanadi. Faqat zaxira fondidan tashqari pul."),
    field("Har oylik qo'shimcha, $", mon, "Yadro (SPUS) qismiga har oy qo'shiladi."));
  modal("Xush kelibsiz", body, [
    { label: "Keyinroq", onClick: () => { store.update((st) => { st.settings.onboarded = true; }); } },
    { label: "Saqlash", primary: true, onClick: async () => {
      const d = parseNum(dep.value), m = parseNum(mon.value);
      if (!(d > 0) || !(m >= 0)) { toast("Summani raqam bilan kiriting"); return false; }
      await store.update((st) => { st.settings.deposit = d; st.settings.monthly = m; st.settings.onboarded = true; });
    } },
  ]);
}

function registerSW() {
  if (!("serviceWorker" in navigator) || import.meta.env.DEV) return;
  navigator.serviceWorker.register("./sw.js").then((reg) => {
    reg.addEventListener("updatefound", () => {
      const w = reg.installing;
      w?.addEventListener("statechange", () => {
        if (w.state === "installed" && navigator.serviceWorker.controller) {
          toast("Yangi versiya tayyor", () => { w.postMessage("skip-waiting"); }, 15000);
        }
      });
    });
  }).catch(() => {});
  let reloaded = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => { if (!reloaded) { reloaded = true; location.reload(); } });
}

async function boot() {
  shell();
  await store.init();
  window.addEventListener("hashchange", route);
  await route();
  api.meta().then((m) => {
    if (m.demo) {
      demoBar.hidden = false;
      demoBar.replaceChildren(h("strong", null, "DEMO ma'lumot."),
        " Narxlar sun'iy — natijalar haqiqiy bozorni aks ettirmaydi. Haqiqiy skaner GitHub Actions'da ishga tushgach yo'qoladi.");
    }
  }).catch(() => {});
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    let m = "auto";
    try { m = localStorage.getItem("saralash.mode") || "auto"; } catch { /* */ }
    if (m === "auto") import("./pages/settings").then((x) => { x.applyMode("auto"); route(); });
  });
  if (!store.get().settings.onboarded) onboarding();
  sync.start().catch(() => {});
  registerSW();
}

boot();
