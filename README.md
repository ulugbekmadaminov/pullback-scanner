# Saralash — halol AQSh aksiyalari tahlili

Shaxsiy tahlil dasturi: SPUS (S&P 500 Shariah) aksiyalarini har kuni qoidalar asosida saralaydi,
har bir ball uchun "nega?" ni ✓/✗ bilan ko'rsatadi, kuzatuv ro'yxatini o'zi yuritadi va qoidalarni
virtual portfelda sinab boradi. **Bu investitsiya maslahati emas.** Real savdodan oldin halollik Hyssa'da tekshiriladi.

```
engine/      Python dvigatel: ma'lumot, indikatorlar, signallar, ball, kuzatuv, portfel, backtest
app/         PWA ilova (Vite + TypeScript), telefon va kompyuterda ishlaydi, offline ham ochiladi
supabase/    ixtiyoriy bulut sinxroni uchun SQL (jadvallar + RLS)
state/       dvigatel holati — har kuni commit qilinadi (o'zgarmas audit izi)
docs/        QOIDALAR-v2.md (barcha qoidalar va raqamlar), LOYIHA-HISOBOTI.md, BACKTEST.md
github-workflows/  .github/workflows ga qo'lda ko'chiriladigan 2 ta workflow
legacy/      eski 2-qadam kodi (ma'lumot yig'ish), faqat tarix uchun
```

Har kuni ertalab, AQSh bozorining oldingi kuni yopilgach (04:30 UTC, seshanba–shanba) GitHub Actions: testlar → skaner → `state/` commit →
ilovani yig'ish → GitHub Pages'ga joylash. Ilova manzili: `https://<login>.github.io/<repo>/`.

## Bir martalik sozlash

### 1. Fayllarni yuklash
1. Repozitoriyda **Add file → Upload files** → ZIP ichidagi hamma narsani tashlang → **Commit changes**.
2. Eski 2-qadam fayllarini o'chiring (ular endi `legacy/` ichida): ildizdagi `config.py`, `run_fetch.py`,
   `src/` papkasi, `tests/test_data.py`, hamda `.github/workflows/fetch-data.yml`.
   `data/` papkasi (muzlatilgan 4H ma'lumot) qolishi mumkin.

### 2. Workflow'larni yaratish (brauzer `.github` papkasini yuklamaydi)
1. **Add file → Create new file**, nomi: `.github/workflows/daily.yml`.
   Ichiga `github-workflows/daily.yml` mazmunini to'liq ko'chiring → Commit.
2. Xuddi shunday `.github/workflows/backtest.yml` ← `github-workflows/backtest.yml`.

### 3. Ruxsatlar va Pages
1. **Settings → Actions → General → Workflow permissions → Read and write permissions → Save.**
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**

### 4. Birinchi ishga tushirish
1. **Actions → Kundalik skaner → Run workflow** (`demo` belgilanmagan). 20–40 daqiqa.
2. Yashil ✓ dan keyin ilova Pages manzilida ochiladi. Telefonda: brauzer menyusi → "Bosh ekranga qo'shish".
3. **Actions → Backtest → Run workflow** — 10 yillik tarixda pullback va breakout sinovi (1–2 soat).
   Natija keyingi kunlik ishdan so'ng ilovaning Backtest bo'limida va `docs/BACKTEST.md` da.

Birinchi kunlarda bilish kerak:
- Fundamental ma'lumot kuniga ~70 aksiyadan yangilanadi — 215 ta aksiya ~4 kunda to'liq qamraladi.
  Shungacha ba'zi kartalarda "ma'lumot yo'q" bo'ladi va ular uzoq kuzatuvga kirmaydi.
- Virtual portfel va strategiyalar musobaqasi **birinchi real ishdan** boshlanadi. Xulosa uchun kamida
  100 ta savdo / 1 yil kerak — ungacha faqat kuzating.
- Yangi narsani sinash kerak bo'lsa: Run workflow → `demo` ni belgilang (sun'iy ma'lumot, `state/` ga yozilmaydi).

### 5. Bulut sinxroni (ixtiyoriy — jurnalni ikki qurilmada ko'rish uchun)
Supabase'siz ham hammasi ishlaydi: jurnal shu qurilmada saqlanadi, Sozlamalar → Zaxira orqali faylga olinadi.
1. supabase.com → yangi loyiha (bepul). **SQL Editor** → `supabase/migrations/001_init.sql` ni to'liq qo'yib **Run**.
2. **Authentication → Sign In / Providers → Email**: "Allow new users to sign up" ni **o'chiring**.
   **Authentication → Users → Add user** → o'z emailingiz.
3. **Authentication → URL Configuration → Site URL**: ilovaning Pages manzili.
4. GitHub → **Settings → Secrets and variables → Actions → New repository secret**:
   `SUPABASE_URL` (Project URL), `SUPABASE_ANON_KEY` (anon/publishable key),
   `SUPABASE_SERVICE_KEY` (service_role key — **hech qayerga ko'chirmang**, faqat shu yerda).
5. Kundalik skanerni qayta ishga tushiring. Ilovada Sozlamalar → Bulut sinxroni → email → pochtadagi havola.

## Mahalliy ishga tushirish (ixtiyoriy)
```bash
pip install -r requirements.txt
python -m pytest -q                      # 22 test
python -m engine.pipeline --demo         # sun'iy ma'lumot bilan to'liq skaner
python run_backtest.py --demo --limit 60
cd app && npm ci && npm run dev          # http://localhost:5173
```

## Qoida o'zgartirish tartibi
Barcha raqamlar `engine/config.py` da. O'zgarish faqat yangi versiya sifatida: `RULES_VERSION` oshiriladi,
sababi `docs/QOIDALAR-v2.md` ga yoziladi, backtest qayta ishlatiladi. Dastur o'zi qoidani o'zgartirmaydi —
Portfel → O'rganish bo'limida faqat taklif chiqaradi.

## Ma'lum cheklovlar
- yfinance norasmiy bepul manba: ba'zan bo'shliq yoki kechikish bo'ladi.
- Ro'yxat bugungi SPUS tarkibi — tarixiy backtest biroz optimistik (omon qolganlar xatosi).
- Fundamental ma'lumotning o'tmishdagi holati yo'q, shuning uchun fundamental strategiyalar orqaga
  qarab emas, bugundan oldinga — virtual portfel musobaqasida sinaladi.
