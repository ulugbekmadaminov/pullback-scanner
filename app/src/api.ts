// Dvigatel natijalari (data/*.json). Har bir fayl bir marta yuklanadi va xotirada saqlanadi.

export interface Check { ok: boolean | null; t: string; k?: string }
export interface Layer { score: number | null; checks: Check[] }
export interface Row {
  t: string; name: string; sector: string; price: number | null; r1d: number | null; r21: number | null;
  rs: number | null; fh: number | null; stage: number | null; mid: number | null; long: number | null;
  L: Record<string, number | null>; halal: boolean; liquid: boolean; signal: string | null;
  watch_mid: "tayyor" | "kuzatuvda" | null; watch_long: boolean; earn: string | null; tags: string[];
  last_signal: { date: string; kind: string } | null;
}
export interface Meta { date: string; generated: string; demo: boolean; rules_version: string; universe_source: string; universe: number; fund_coverage: number }
export interface Sector { etf: string; name: string; group: string; r1d: number; r21: number; r63: number; rel21: number; rel63: number; rank: number; top_half: boolean }
export interface Market {
  date: string; regime: "green" | "yellow" | "red" | null; vix: number | null; risk_on_21: number | null; risk_on_63: number | null;
  breadth_63: number | null; allow_buys: boolean; risk_mult: number; reasons: string[]; sectors: Sector[];
  indices: { ticker: string; close: number; r1d: number; r21: number; r63: number }[];
  regime_detail: { above_sma200: boolean; support_ok: boolean; support: number | null; sma200: number | null; close: number } | null;
  history: { t: string[]; c: number[]; sma200: (number | null)[]; regime: (string | null)[] };
}
export interface Card {
  t: string; row: Row; layers: Record<string, Layer & { ok?: boolean }>; plan: null | { kind: string; entry: number; stop: number; target: number; rr: number | null };
  explain: { pullback: { ok: boolean; checks: Check[]; zone?: [number, number]; stop?: number; target?: number; factors?: string[] };
             breakout: { ok: boolean; checks: Check[] }; swings: { date: string; type: string; price: number }[] };
  fund: Record<string, any>; spct: Record<string, number | null>;
  chart: { t: string[]; o: number[]; h: number[]; l: number[]; c: number[]; v: number[]; ema20: (number | null)[]; ema50: (number | null)[]; sma150: (number | null)[]; sma200: (number | null)[] };
  signals: { d: string; k: string }[]; watch: { mid: WatchItem | null; long: WatchItem | null }; earnings: string[];
}
export interface WatchItem { entered: string; price: number; reason: string }
export interface HistItem { ticker: string; profile: string; entered: string; exited: string; reason_in: string; reason_out: string; price_in: number; price_out: number | null; ret: number | null }
export interface Trade { ticker: string; kind: string; entry_date: string; entry: number; exit_date: string; exit: number; shares: number; stop: number; target: number; r: number; pnl: number; why: string; days: number; sector?: string; flags?: Record<string, unknown> }
export interface Portfolio {
  params: Record<string, number>; equity: [string, number, number, number, number][];
  positions: (Trade & { R: number; price: number | null; r_now: number | null })[]; pending: { ticker: string; kind: string; stop: number; target: number; shares: number; planned: string }[];
  trades: Trade[]; stats: Record<string, number | null>; protection: { dd?: number; status?: string; market_ok?: boolean; risk_mult?: number };
  core_shares: number; started: string | null; log: { d: string; t: string; e: string; why: string }[];
}
export interface Strategy { key: string; title: string; rule: string; equity: [string, number][]; holdings: string[]; note: string; candidates: number | null }
export interface Learn { n: number; errors: Record<string, number>; groups: { flag: string; value: string; n: number; exp: number; win: number }[]; proposals: { text: string; flag: string }[] }
export interface Backtest { generated: string; demo: boolean; period: [string, string]; split_date: string; universe: number; survivorship_note: string;
  variants: { variant: string; kind: string; signals: number; signal_test: Record<string, number>; signal_train: Record<string, number>;
    random: { runs: number; mean: number | null; p95: number | null; percentile: number | null }; portfolio: Record<string, number>;
    equity: [string, number][]; checks: { t: string; ok: boolean; v: number | null }[]; verdict: string }[] }

const cache = new Map<string, Promise<any>>();
const BASE = "./data/";

export class DataError extends Error {}

export function load<T>(name: string, fresh = false): Promise<T> {
  if (fresh) cache.delete(name);
  if (!cache.has(name)) {
    const p = fetch(BASE + name, { cache: "no-cache" }).then(async (r) => {
      if (!r.ok) throw new DataError(r.status === 404 ? `${name} topilmadi` : `${name}: ${r.status}`);
      return r.json();
    });
    p.catch(() => cache.delete(name));
    cache.set(name, p);
  }
  return cache.get(name)!;
}

export const meta = () => load<Meta>("meta.json");
export const market = () => load<Market>("market.json");
export const scores = () => load<Row[]>("scores.json");
export const card = (t: string) => load<Card>(`cards/${encodeURIComponent(t)}.json`);
export const watchlist = () => load<{ mid: Record<string, WatchItem>; long: Record<string, WatchItem>; history: HistItem[] }>("watchlist.json");
export const portfolio = () => load<Portfolio>("portfolio.json");
export const competition = () => load<{ strategies: Strategy[] }>("competition.json");
export const learn = () => load<Learn>("learn.json");
export const backtest = () => load<Backtest>("backtest.json");

export function refreshAll(): void { cache.clear(); }

export const LAYER_NAMES: Record<string, string> = {
  trend: "Trend", strength: "Kuch", quality: "Sifat", growth: "O'sish", value: "Qiymat", dividend: "Dividend", halal: "Halollik",
};
export const KIND_NAMES: Record<string, string> = { pullback: "Pullback", breakout: "Breakout" };
export const REGIME_NAMES: Record<string, string> = { green: "Yashil", yellow: "Sariq", red: "Qizil" };
