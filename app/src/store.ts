// Shaxsiy ma'lumot: local-first (IndexedDB). Supabase ulangan bo'lsa fonda sinxronlanadi.
// Hech qachon jimgina yo'qolmaydi: har bir yozish xatosi foydalanuvchiga ko'rsatiladi.

import { toast, todayIso } from "./ui";

export const SCHEMA = 1;

export interface Position {
  id: string; ticker: string; profile: "mid" | "long"; kind: string; qty: number; entry: number; date: string;
  stop: number | null; target: number | null; note: string; followed_plan: boolean | null;
  exit: number | null; exit_date: string | null; exit_note: string; purified: number;
}
export interface Settings {
  deposit: number; monthly: number; core_pct: number; risk_pct: number; onboarded: boolean;
}
export interface UserState { schema: number; rev: number; updated: string; settings: Settings; positions: Position[] }

export const DEFAULTS: Settings = { deposit: 10000, monthly: 0, core_pct: 60, risk_pct: 0.75, onboarded: false };

const DB = "saralash";
const STORE = "kv";
let state: UserState = { schema: SCHEMA, rev: 0, updated: "", settings: { ...DEFAULTS }, positions: [] };
const listeners = new Set<() => void>();

function idb(): Promise<IDBDatabase> {
  return new Promise((res, rej) => {
    const r = indexedDB.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(STORE);
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });
}

async function idbGet<T>(key: string): Promise<T | undefined> {
  const db = await idb();
  return new Promise((res, rej) => {
    const q = db.transaction(STORE).objectStore(STORE).get(key);
    q.onsuccess = () => res(q.result as T);
    q.onerror = () => rej(q.error);
  });
}

async function idbPut(key: string, val: unknown): Promise<void> {
  const db = await idb();
  return new Promise((res, rej) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(val, key);
    tx.oncomplete = () => res();
    tx.onerror = () => rej(tx.error);
    tx.onabort = () => rej(tx.error);
  });
}

export function migrate(raw: any): UserState {
  // Kelajakdagi sxema o'zgarishlari shu yerda: eski versiyadan yangisiga
  if (!raw || typeof raw !== "object") throw new Error("Fayl tuzilishi noto'g'ri");
  const s: UserState = {
    schema: SCHEMA, rev: Number(raw.rev) || 0, updated: String(raw.updated || ""),
    settings: { ...DEFAULTS, ...(raw.settings || {}) },
    positions: Array.isArray(raw.positions) ? raw.positions.map(validPos) : [],
  };
  if (Number(raw.schema) > SCHEMA) throw new Error("Fayl ilovaning yangiroq versiyasidan — ilovani yangilang");
  return s;
}

function validPos(p: any): Position {
  if (!p || typeof p.ticker !== "string" || !isFinite(Number(p.qty)) || !isFinite(Number(p.entry))) throw new Error("Pozitsiya yozuvi buzilgan");
  return {
    id: String(p.id || crypto.randomUUID()), ticker: p.ticker.toUpperCase().slice(0, 10), profile: p.profile === "long" ? "long" : "mid",
    kind: String(p.kind || "qo'lda"), qty: Number(p.qty), entry: Number(p.entry), date: String(p.date || todayIso()),
    stop: p.stop === null || p.stop === undefined ? null : Number(p.stop), target: p.target === null || p.target === undefined ? null : Number(p.target),
    note: String(p.note || ""), followed_plan: p.followed_plan ?? null, exit: p.exit === null || p.exit === undefined ? null : Number(p.exit),
    exit_date: p.exit_date ?? null, exit_note: String(p.exit_note || ""), purified: Number(p.purified) || 0,
  };
}

export async function init(): Promise<void> {
  try {
    const s = await idbGet<UserState>("state");
    if (s) state = migrate(s);
  } catch (e) {
    toast("Shaxsiy ma'lumotni o'qib bo'lmadi: " + (e as Error).message);
  }
}

export const get = (): UserState => state;
export const subscribe = (fn: () => void) => { listeners.add(fn); return () => listeners.delete(fn); };

export async function update(fn: (s: UserState) => void, opts: { silentSync?: boolean } = {}): Promise<boolean> {
  const prev = structuredClone(state);
  fn(state);
  state.rev += 1;
  state.updated = new Date().toISOString();
  try {
    await idbPut("state", state);
  } catch (e) {
    state = prev;
    const quota = (e as DOMException)?.name === "QuotaExceededError";
    toast(quota ? "Qurilma xotirasi to'lgan — saqlanmadi" : "Saqlanmadi: " + (e as Error).message);
    return false;
  }
  listeners.forEach((l) => l());
  if (!opts.silentSync) import("./sync").then((m) => m.schedulePush()).catch(() => {});
  return true;
}

export async function replace(next: UserState): Promise<void> {
  state = next;
  await idbPut("state", state);
  listeners.forEach((l) => l());
}

export function exportJson(): Blob {
  return new Blob([JSON.stringify({ app: "saralash", ...state }, null, 2)], { type: "application/json" });
}

export async function importJson(text: string): Promise<void> {
  let raw: any;
  try { raw = JSON.parse(text); } catch { throw new Error("Bu JSON fayl emas"); }
  if (raw.app !== "saralash") throw new Error("Bu Saralash zaxira fayli emas");
  const next = migrate(raw);                       // buzuq fayl mavjud ma'lumotga tegmaydi
  next.rev = Math.max(next.rev, state.rev) + 1;
  await replace(next);
  import("./sync").then((m) => m.schedulePush()).catch(() => {});
}

// ── hisob-kitoblar ──
export function closedStats(ps: Position[]) {
  const closed = ps.filter((p) => p.exit !== null);
  const rs = closed.map((p) => (p.stop !== null && p.entry > p.stop ? (p.exit! - p.entry) / (p.entry - p.stop) : null)).filter((x): x is number => x !== null);
  const pnl = closed.reduce((a, p) => a + (p.exit! - p.entry) * p.qty, 0);
  const wins = rs.filter((r) => r > 0);
  const followed = closed.filter((p) => p.followed_plan !== null);
  return {
    n: closed.length, nR: rs.length, pnl, winrate: rs.length ? wins.length / rs.length : null,
    expectancy: rs.length ? rs.reduce((a, b) => a + b, 0) / rs.length : null,
    plan_rate: followed.length ? followed.filter((p) => p.followed_plan).length / followed.length : null,
  };
}

/** Uplift jurnal formulasi: (choraklik nomaqbul daromad / aksiya) × egalik × (kunlar ÷ 90). */
export function purification(p: Position, impurePerShareQ: number, today = todayIso()): number {
  const end = p.exit_date || today;
  const days = Math.max(0, (Date.parse(end) - Date.parse(p.date)) / 86400000);
  return Math.max(0, impurePerShareQ * p.qty * (days / 90));
}
