// Supabase sinxronizatsiyasi (ixtiyoriy). Kalitlar build paytida VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY
// orqali beriladi; bo'lmasa ilova faqat qurilmada ishlaydi. Ziddiyat qoidasi: `rev` kattasi yutadi,
// yutqazgan nusxa yo'qolmaydi — "zaxira" sifatida qurilmada saqlanadi.

import type { SupabaseClient } from "@supabase/supabase-js";
import { get, migrate, replace } from "./store";
import { debounce, toast } from "./ui";

const URL_ = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
export const configured = Boolean(URL_ && KEY);

let client: SupabaseClient | null = null;
export type SyncState = "o'chiq" | "kirilmagan" | "sinxron" | "yuborilmoqda" | "offline" | "xato";
let status: SyncState = configured ? "kirilmagan" : "o'chiq";
let email: string | null = null;
const listeners = new Set<() => void>();
const set = (s: SyncState) => { status = s; listeners.forEach((l) => l()); };

export const syncStatus = () => ({ status, email });
export const onSync = (fn: () => void) => { listeners.add(fn); return () => listeners.delete(fn); };

async function sb(): Promise<SupabaseClient | null> {
  if (!configured) return null;
  if (!client) {
    const { createClient } = await import("@supabase/supabase-js");
    client = createClient(URL_!, KEY!, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } });
    client.auth.onAuthStateChange((_e, session) => {
      email = session?.user?.email ?? null;
      if (session) pull().catch(() => {}); else set("kirilmagan");
    });
  }
  return client;
}

export async function start(): Promise<void> {
  const c = await sb();
  if (!c) return;
  const { data } = await c.auth.getSession();
  email = data.session?.user?.email ?? null;
  if (data.session) await pull().catch(() => set("xato"));
  window.addEventListener("online", () => { if (email) push().catch(() => {}); });
}

export async function signIn(addr: string): Promise<void> {
  const c = await sb();
  if (!c) throw new Error("Supabase sozlanmagan");
  const { error } = await c.auth.signInWithOtp({ email: addr, options: { emailRedirectTo: location.href.split("#")[0], shouldCreateUser: false } });
  if (error) throw new Error(error.message);
}

export async function signOut(): Promise<void> {
  const c = await sb();
  await c?.auth.signOut();
  email = null;
  set("kirilmagan");
}

async function pull(): Promise<void> {
  const c = await sb();
  if (!c || !email) return;
  if (!navigator.onLine) return set("offline");
  const { data: u } = await c.auth.getUser();
  if (!u.user) return set("kirilmagan");
  const { data, error } = await c.from("user_state").select("rev,data").eq("user_id", u.user.id).maybeSingle();
  if (error) { set("xato"); throw error; }
  const local = get();
  if (data && data.rev > local.rev) {
    localStorage.setItem("saralash.backup", JSON.stringify(local));     // yutqazgan nusxa saqlanadi
    await replace({ ...migrate(data.data), rev: data.rev });
    toast("Bulutdagi yangiroq ma'lumot yuklandi");
    set("sinxron");
  } else if (!data || data.rev < local.rev) {
    await push();
  } else set("sinxron");
}

export async function push(): Promise<void> {
  const c = await sb();
  if (!c || !email) return;
  if (!navigator.onLine) return set("offline");
  set("yuborilmoqda");
  const { data: u } = await c.auth.getUser();
  if (!u.user) return set("kirilmagan");
  const s = get();
  const { error } = await c.from("user_state").upsert({ user_id: u.user.id, rev: s.rev, data: s });
  if (error) {
    if (error.code === "40001" || /conflict/.test(error.message)) { await pull(); return; }
    set("xato");
    toast("Bulutga yuborilmadi: " + error.message);
    return;
  }
  set("sinxron");
}

export const schedulePush = debounce(() => { push().catch(() => set("xato")); }, 1200);
