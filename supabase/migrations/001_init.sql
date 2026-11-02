-- Aksiya tahlili — Supabase sxemasi (v2.0.0)
-- Ishga tushirish: Supabase → SQL Editor → shu faylni to'liq qo'yib, Run.

-- 1) Dvigatel natijalari: har kuni bitta qatordan (summary, scores, watchlist, portfolio, learn).
--    Yozish faqat service role kaliti bilan (GitHub Actions sirlari). O'qish — faqat tizimga kirgan foydalanuvchi.
create table if not exists public.engine_snapshots (
  day        date        not null,
  kind       text        not null check (kind in ('summary','scores','watchlist','portfolio','learn')),
  data       jsonb       not null,
  created_at timestamptz not null default now(),
  primary key (day, kind)
);
alter table public.engine_snapshots enable row level security;
drop policy if exists "snapshots_read_authenticated" on public.engine_snapshots;
create policy "snapshots_read_authenticated" on public.engine_snapshots
  for select to authenticated using (true);
-- insert/update siyosati yo'q: anon va authenticated yoza olmaydi; service role RLS'ni chetlab o'tadi.

-- 2) Foydalanuvchining shaxsiy ma'lumoti: real pozitsiyalar, jurnal, sozlamalar, tozalash yozuvlari.
--    Bitta hujjat (jsonb) + versiya: ilova local-first, ziddiyatda yangiroq `rev` yutadi.
create table if not exists public.user_state (
  user_id    uuid        primary key references auth.users (id) on delete cascade,
  rev        bigint      not null default 0,
  data       jsonb       not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table public.user_state enable row level security;
drop policy if exists "user_state_owner_select" on public.user_state;
drop policy if exists "user_state_owner_insert" on public.user_state;
drop policy if exists "user_state_owner_update" on public.user_state;
drop policy if exists "user_state_owner_delete" on public.user_state;
create policy "user_state_owner_select" on public.user_state for select to authenticated using (auth.uid() = user_id);
create policy "user_state_owner_insert" on public.user_state for insert to authenticated with check (auth.uid() = user_id);
create policy "user_state_owner_update" on public.user_state for update to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "user_state_owner_delete" on public.user_state for delete to authenticated using (auth.uid() = user_id);

-- 3) Eski yozuv ustiga yozib yuborishdan himoya: rev faqat oshishi mumkin.
create or replace function public.user_state_guard() returns trigger language plpgsql as $$
begin
  if new.rev <= old.rev then
    raise exception 'conflict: server rev % >= client rev %', old.rev, new.rev using errcode = '40001';
  end if;
  new.updated_at := now();
  return new;
end $$;
drop trigger if exists user_state_guard on public.user_state;
create trigger user_state_guard before update on public.user_state
  for each row execute function public.user_state_guard();

-- 4) Ro'yxatdan o'tishni yopish tavsiya etiladi: Authentication → Providers → Email →
--    "Allow new users to sign up" ni O'CHIRING va o'zingizni Users bo'limidan qo'lda qo'shing.
