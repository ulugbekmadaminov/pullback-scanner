// UI yordamchilari. Ma'lumot DOM'ga faqat textContent orqali tushadi (XSS himoyasi).

type Child = Node | string | number | null | undefined | false | Child[];
type Attrs = Record<string, unknown> & { class?: string; on?: Record<string, (e: Event) => void> };

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, attrs?: Attrs | null, ...kids: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === undefined || v === null || v === false) continue;
      if (k === "on") for (const [ev, fn] of Object.entries(v as Record<string, EventListener>)) el.addEventListener(ev, fn);
      else if (k === "class") el.className = String(v);
      else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
      else if (k in el && typeof v !== "string") (el as any)[k] = v;
      else el.setAttribute(k, v === true ? "" : String(v));
    }
  }
  append(el, kids);
  return el;
}

export function append(el: Node, kids: Child[]): void {
  for (const k of kids) {
    if (k === null || k === undefined || k === false) continue;
    if (Array.isArray(k)) append(el, k);
    else el.appendChild(k instanceof Node ? k : document.createTextNode(String(k)));
  }
}

export function svg(path: string, size = 20): SVGSVGElement {
  const ns = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(ns, "svg");
  s.setAttribute("viewBox", "0 0 24 24");
  s.setAttribute("width", String(size));
  s.setAttribute("height", String(size));
  s.setAttribute("aria-hidden", "true");
  s.setAttribute("fill", "none");
  s.setAttribute("stroke", "currentColor");
  s.setAttribute("stroke-width", "1.8");
  s.setAttribute("stroke-linecap", "round");
  s.setAttribute("stroke-linejoin", "round");
  for (const d of path.split("|")) {
    const p = document.createElementNS(ns, "path");
    p.setAttribute("d", d);
    s.appendChild(p);
  }
  return s;
}

export const ICON = {
  market: "M3 12h4l3-8 4 16 3-8h4",
  list: "M8 6h13|M8 12h13|M8 18h13|M3 6h.01|M3 12h.01|M3 18h.01",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z|M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  wallet: "M3 7h15a3 3 0 0 1 3 3v7a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3z|M3 7l11-4 2 4|M16 13h2",
  more: "M5 12h.01|M12 12h.01|M19 12h.01",
  trophy: "M8 4h8v5a4 4 0 0 1-8 0z|M8 6H5a3 3 0 0 0 3 4|M16 6h3a3 3 0 0 1-3 4|M12 13v4|M9 20h6",
  book: "M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z|M4 19V5",
  flask: "M9 3h6|M10 3v6L5 18a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3",
  gear: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z|M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
  back: "M15 18l-6-6 6-6",
  check: "M5 12l5 5L20 7",
  cross: "M6 6l12 12|M18 6L6 18",
  dot: "M12 12h.01",
  plus: "M12 5v14|M5 12h14",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z|M21 21l-4.3-4.3",
  sync: "M21 12a9 9 0 0 1-15 6.7L3 16|M3 12a9 9 0 0 1 15-6.7L21 8|M21 3v5h-5|M3 21v-5h5",
  shield: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
  bulb: "M9 18h6|M10 21h4|M12 3a6 6 0 0 0-4 10.5c.8.8 1 1.5 1 2.5h6c0-1 .2-1.7 1-2.5A6 6 0 0 0 12 3z",
};

// ── formatlash ──
const nf2 = new Intl.NumberFormat("uz-UZ", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nf0 = new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 });
export const num = (x: number | null | undefined, d = 2) =>
  x === null || x === undefined || !isFinite(x) ? "—" : d === 0 ? nf0.format(x) : d === 2 ? nf2.format(x) : x.toFixed(d);
export const usd = (x: number | null | undefined) => (x === null || x === undefined || !isFinite(x) ? "—" : "$" + nf2.format(x));
export const pct = (x: number | null | undefined, d = 1, sign = false) =>
  x === null || x === undefined || !isFinite(x) ? "—" : (sign && x > 0 ? "+" : "") + (x * 100).toFixed(d) + "%";
export const rr = (x: number | null | undefined) => (x === null || x === undefined || !isFinite(x) ? "—" : (x > 0 ? "+" : "") + x.toFixed(2) + "R");
export const tone = (x: number | null | undefined) => (x === null || x === undefined || !isFinite(x) || x === 0 ? "" : x > 0 ? "up" : "down");

const MONTHS = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"];
export function dateUz(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);   // lokal sana: vaqt mintaqasi siljimasligi uchun
  return `${d}-${MONTHS[m - 1]} ${y}`;
}
export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ── holatlar ──
export function skeleton(lines = 4): HTMLElement {
  return h("div", { class: "skeleton", "aria-busy": "true", "aria-label": "Yuklanmoqda" },
    Array.from({ length: lines }, (_, i) => h("div", { class: "sk-line", style: { width: `${92 - i * 11}%` } })));
}

export function empty(icon: string, text: string, action?: { label: string; onClick: () => void }): HTMLElement {
  return h("div", { class: "empty" }, svg(icon, 36), h("p", null, text),
    action ? h("button", { class: "btn", on: { click: action.onClick } }, action.label) : null);
}

export function errorBox(text: string, retry?: () => void): HTMLElement {
  return h("div", { class: "error-box", role: "alert" }, h("p", null, text),
    retry ? h("button", { class: "btn", on: { click: retry } }, "Qayta urinish") : null);
}

// ── toast (undo bilan) ──
export function toast(text: string, undo?: () => void, ms = 4500): void {
  document.querySelector(".toast")?.remove();
  const t = h("div", { class: "toast", role: "status" }, h("span", null, text),
    undo ? h("button", { class: "toast-btn", on: { click: () => { undo(); t.remove(); } } }, "Bekor qilish") : null);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), ms);
}

// ── modal (ESC va tashqariga bosish yopadi, ostidagi sahifa skroll bo'lmaydi) ──
export function modal(title: string, body: Node, actions: { label: string; primary?: boolean; onClick: () => boolean | void | Promise<boolean | void> }[]): () => void {
  const prev = document.activeElement as HTMLElement | null;
  const close = () => { wrap.remove(); document.body.classList.remove("no-scroll"); document.removeEventListener("keydown", onKey); prev?.focus(); };
  const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
  const box = h("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": title },
    h("h2", null, title), body,
    h("div", { class: "modal-actions" }, actions.map((a) =>
      h("button", { class: a.primary ? "btn primary" : "btn", on: { click: async () => { if ((await a.onClick()) !== false) close(); } } }, a.label))));
  const wrap = h("div", { class: "modal-wrap", on: { click: (e) => { if (e.target === wrap) close(); } } }, box);
  document.body.appendChild(wrap);
  document.body.classList.add("no-scroll");
  document.addEventListener("keydown", onKey);
  (box.querySelector("input,select,button") as HTMLElement | null)?.focus();
  return close;
}

export function field(label: string, input: HTMLElement, hint?: string): HTMLElement {
  return h("label", { class: "field" }, h("span", null, label), input, hint ? h("small", null, hint) : null);
}

export function numInput(value: number | string, attrs: Attrs = {}): HTMLInputElement {
  return h("input", { type: "text", inputmode: "decimal", value: String(value), autocomplete: "off", ...attrs });
}

export function parseNum(s: string): number {
  return Number(String(s).replace(/\s/g, "").replace(",", "."));
}

export function checks(list: { ok: boolean | null; t: string }[]): HTMLElement {
  return h("ul", { class: "checks" }, list.map((c) =>
    h("li", { class: c.ok === true ? "ok" : c.ok === false ? "no" : "na" },
      h("span", { class: "mark", "aria-label": c.ok === true ? "bajarildi" : c.ok === false ? "bajarilmadi" : "ma'lumot" },
        svg(c.ok === true ? ICON.check : c.ok === false ? ICON.cross : ICON.dot, 14)),
      h("span", null, c.t))));
}

export function bar(score: number | null, label: string): HTMLElement {
  return h("div", { class: "lbar", title: `${label}: ${score ?? "—"}` },
    h("span", { class: "lbar-l" }, label),
    h("span", { class: "lbar-track" }, h("span", { class: "lbar-fill", style: { width: `${score ?? 0}%` } })),
    h("span", { class: "lbar-v" }, score === null ? "—" : String(score)));
}

export function debounce<T extends (...a: any[]) => void>(fn: T, ms = 250): T {
  let id: number | undefined;
  return ((...a: any[]) => { clearTimeout(id); id = window.setTimeout(() => fn(...a), ms); }) as T;
}
