# Aksiya tahlili dasturi (sobiq "Pullback skaner") — loyiha hisoboti

Sana: 2026-11-02 · Holat: MVP (0–5 bosqichlar) qurildi va DEMO ma'lumotda sinaldi; real ishga tushirish foydalanuvchi tomonida
Yangi chatda ishni davom ettirish uchun: shu faylni birinchi xabarga qo'shing.

---

## 1. Maqsad va foydalanuvchi

**Foydalanuvchi:** Ulugbek, shaxsiy foydalanish uchun (keyinchalik boshqalarga ochish mumkin).

**Maqsad:** sotib olishga yaraydigan halol AQSh aksiyalarini saralaydigan, o'rganilgan barcha
kuchli g'oyalarni birlashtirgan va vaqt o'tishi bilan o'z natijalaridan o'rganib boradigan
tahlil dasturi. Pullback — endi faqat bitta kirish usuli.

**Asosiy talablar:**
- Ikki profil: **o'rta muddat** (2 hafta – 6 oy) va **uzoq muddat** (1 yil+). Har pozitsiya
  kirishda profilga bog'lanadi va profili o'zgartirilmaydi.
- **Kundalik saralangan ro'yxat** + **aksiya bo'yicha chuqur tahlil kartasi**.
- **Kuzatuv ro'yxati:** qoidalarga mos kelsa avtomatik kiradi, qoida buzilsa chiqadi va
  **tarixga** yoziladi (sana, sabab, natija). Tarixni orqaga qaytib o'zgartirib bo'lmaydi.
- **Virtual portfel:** dastur o'zi "sotib oladi", ushlab turadi, sotadi, natijani o'lchaydi.
- **Depozitni himoyalash:** aksiya zarari oddiy holat, depozit zarari chegaralangan bo'lishi shart.
- **O'z xatolaridan o'rganish:** dastur o'zgarish **taklif qiladi**, Ulugbek tasdiqlaydi,
  yangi versiya eskisi bilan parallel sinaladi. Avtomatik o'z-o'zini o'zgartirish yo'q.

---

## 2. Arxitektura — B varianti (tanlangan)

```
pullback-scanner/            (GitHub: ulugbekmadaminov/pullback-scanner, public)
├── engine/     Python: ma'lumot, indikatorlar, strategiyalar, backtest, portfel
├── app/        Vite + TypeScript PWA (modullarga bo'lingan, local-first)
├── supabase/   jadvallar sxemasi, RLS qoidalari, migratsiyalar
├── docs/       qoidalar hujjati, LOYIHA-HISOBOTI.md
└── .github/workflows/   har kungi skaner (bozor yopilgach)
```

- **Dvigatel:** GitHub Actions'da har kuni ishlaydi. Natijalar Supabase'ga yoziladi,
  kunlik JSON nusxasi Git'da ham saqlanadi (o'zgarmas audit izi).
- **Baza:** Supabase (Postgres), login + RLS ("faqat o'z qatorini ko'radi").
  Service role kaliti faqat Actions sirlarida, front-endda faqat anon kalit.
- **Ilova:** Vite + TypeScript, local-first (IndexedDB + fonda sinxronizatsiya).
  Grafiklar: TradingView Lightweight Charts (loyiha ichida, CDN emas).
  Matnlar boshidanoq I18N tuzilmasida, hozircha faqat o'zbekcha.
- **Ma'lumot manbalari:** yfinance (narx, fundamental, hisobot sanalari),
  sp-funds.com (SPUS tarkibi CSV), SEC N-PORT (SPUS'ning choraklik tarixiy tarkibi —
  omon qolganlar xatosiga qarshi, yuklanishi hali tekshirilmagan).

**Taxminiy Supabase jadvallari (qoralama, tasdiqlanmagan):**
`universe`, `daily_scores`, `signals`, `watchlist`, `watchlist_history`,
`paper_portfolios`, `paper_trades`, `positions` (shaxsiy), `journal`, `settings`,
`strategy_versions`, `market_panel`.

---

## 3. Qilingan ishlar

**1-qadam — qoidalar spetsifikatsiyasi (Claude Doc):**
https://claude.ai/code/artifact/6178e8c4-f83c-4d59-b917-00288b4b7cb6
"Pullback skaner — 1-qadam: qoidalar spetsifikatsiyasi": 8 qoida (trend, zinapoya, pullback
chuqurligi, zona kesishmasi, tasdiq shami, hajm, stop/target, Nasdaq rejimi), savdoni
boshqarish, portfel chegaralari, backtest metodologiyasi, qaror mezonlari. Muzlatilgan.

**2-qadam — ma'lumot yig'ish (GitHub):**
- Kod: `config.py`, `src/universe.py`, `src/prices.py`, `src/checks.py`, `run_fetch.py`,
  `tests/test_data.py` (9 test), workflow `2-qadam — ma'lumot yig'ish`.
- Natija: SPUS 215 aksiya + QQQ, SPY; 4H shamlar 2024-10-01 – 2026-09-30 (~993 sham/aksiya),
  QQQ/SPY 10 yillik kunlik, hisobot sanalari, sektorlar, sifat hisoboti.
- **Muzlatilgan: commit 0848e31.**
- Sifat tekshiruvi: 23 ta "keskin sakrash"ning hammasi real voqealar (hisobotlar,
  2025-01-27 DeepSeek kuni, 2025-04 tarif qulashi). Tozalanmaydi.
- Qisqa tarixli: FDXF, P, Q.

**Muhim:** `.github` papkasi brauzerdan yuklanmaydi — workflow sahifada qo'lda yaratilgan.

**MVP v2 (2026-11-02) — "Saralash":**
- `engine/` (Python): ma'lumot (yfinance, SPUS CSV, kesh), indikatorlar, bozor paneli, fundamental
  (TTM, Piotroski, teskari DCF, halollik formulasi, dividend), pullback + breakout signallari,
  ball qatlamlari, kuzatuv (o'rta/uzoq, o'zgarmas tarix), virtual portfel (yadro + faol, himoya
  qavatlari), strategiyalar musobaqasi, backtest (70/30, tasodifiy kirish, 4 variant), o'rganish.
  22 ta test o'tadi.
- `app/` (Vite + TypeScript PWA): Bozor (hukm + rejim lentasi), Ro'yxat, Aksiya kartasi (grafikda
  reja, ✓/✗ izohlar, fundamental, halollik, tozalash), Kuzatuv (+ tarix), Virtual portfel (+ o'rganish),
  Musobaqa, Jurnalim (real savdolar, R, intizom, tozalash), Backtest, Sozlamalar (risk, mavzu,
  bulut sinxroni, zaxira). Offline ishlaydi, yorug'/qorong'i, telefon va kompyuter.
- `supabase/migrations/001_init.sql`: `engine_snapshots` + `user_state` (RLS, rev himoyasi).
  Taxminiy ko'p jadvalli sxema o'rniga ikkita jadval tanlandi: dvigatel holati Git'da, shaxsiy
  ma'lumot bitta versiyalangan hujjatda.
- Qoidalar hujjati: `docs/QOIDALAR-v2.md` (v2.0.0).
- Demo natija: kod to'g'ri ishlaydi; demo backtest raqamlari ma'nosiz (sun'iy narx).

---

## 4. Qulflangan qarorlar

**Ish tartibi**
- "bajar"/"boshla"siz kod ham, fayl ham yaratilmaydi. Har qarorda variant + tavsiya, qarorni
  Ulugbek qabul qiladi.

**Tamoyillar**
- Qora quti yo'q: har bir ball uchun "nega?" ko'rinadi.
- G'oyaning og'irligi mashhurlik bilan emas, **dalil** bilan belgilanadi. Ishlamagan
  g'oya "ma'lumot uchun" maqomiga tushadi (sababi hujjatda).
- Maqomlar: **Qoida** · **Sinovda** · **Ma'lumot uchun** · **Olinmadi**.
- Qoidalar test boshlanishidan oldin muzlatiladi; o'zgarish faqat yangi versiya sifatida.
- O'zini aldamaslik: 70/30 bo'linish, tasodifiy kirish bilan taqqoslash, variantlar jurnali,
  xarajatlar konservativ ($0.005/aksiya, min $1, har tomonda 0.05% slippage).

**Halollik**
- Asosiy ro'yxat: SPUS tarkibi (S&P 500 Shariah, AAOIFI), avtomatik.
- Ikkinchi tekshiruv: Uplift 4-modul formulasi — taqiqlangan moliyalashtirish va taqiqlangan
  aktivlar / 24 oylik o'rtacha bozor kapitallashuvi < 30%, foiz xarajati / daromad < 5%.
- Real savdodan oldin Hyssa'da tekshiriladi (chek-list 1-band).
- Joiz emas va hech qachon taklif qilinmaydi: CFD, fyuchers, optsion, short, imtiyozli aksiya,
  oddiy obligatsiya, foizli pul bozori. Naqd foizsiz, obligatsiya o'rnida sukuk.
- Dividend va daromad tozalash (purification): jurnal formulasi —
  (choraklik taqiqlangan daromad ÷ jami aksiyalar) × egalik × (kunlar ÷ 90).

**Portfel va depozit himoyasi**
- **Core-satellite:** yadro — keng halol indeks (SPUS), yo'ldosh — faol strategiyalar.
  Nisbat: **60% / 40%** (v2.0.0 standarti, Sozlamalarda o'zgartiriladi).
- Har qanday strategiya SPUS'ni ushlab turishdan yaxshi bo'lishi shart, aks holda puli yadroga.
- Himoya qavatlari: savdo riski 0.5–1%; umumiy ochiq risk ≤ 5%; pozitsiya ≤ 15%;
  depozitning 70–80% i ishlatiladi; sektor va **tema/korrelyatsiya** chegarasi;
  rejim "qizil" yoki VIX yuqori → yangi xarid yo'q; drawdown tormozi (−5% → risk yarmi,
  −10% → xarid to'xtaydi); hisobotga ≤ 5 kun qolsa kirilmaydi.
- **Stop bozor tuzilmasi va ATR bo'yicha**, target'dan hisoblanmaydi (Pro Calculator xatosi).
- Pulni kiritish: yadroga oylik summa darhol; katta summa — gibrid (yarmi darhol, qolgani
  3–6 oyda); yo'ldosh pozitsiya bo'lib-bo'lib olinishi backtestda sinaladi.
- 0-qatlam: investitsiya zaxira fondi (6 oy) va qimmat qarzlardan keyin.

**Profillar va chiqish**
- O'rta: chiqish narx asosida (stop, target, trend buzilishi, vaqt chegarasi).
- Uzoq: chiqish sabab asosida (fundamental yomonlashuv, halollik yo'qolishi, haftalik Stage 4).
  Tor stop yo'q.

**Grafik taymfreymi:** o'rta va uzoq uchun kunlik/haftalik (10+ yil tarix).
4H ma'lumot keyinchalik aniq kirish vaqti moduli uchun.

---

## 5. Materiallar inventari (nima olindi)

| Manba | Olingan | Maqom |
| --- | --- | --- |
| Uplift pullback qo'llanmasi | 8 qoida, stop/target, chek-list | Qoida |
| "1:3 — bu edge emas" | Kutilma, edge'ni isbotlash | Tamoyil |
| Nasdaq tayanchlari posti | Bozor rejimi filtri | Qoida (2 variantda sinov) |
| Sektor skaneri (rasm) | Stage, ETF'ga nisbatan kuch, 52H cho'qqi, EP, sektor reytingi | Qoida |
| DCF postlari | Teskari DCF, sezgirlik | Ma'lumot uchun |
| Aziz Halikov: TA tanqidi | Data-snooping himoyasi, momentum asosi | Tamoyil |
| Aziz Halikov: portfel | Diversifikatsiya, Sharpe, beta; xato: alpha, oltin | Qoida (qisman) |
| Indeks va sektor panellari | Risk ishtahasi (davriy/himoya), IWM/SPY | Qoida |
| 10 g'oya natijasi (rasm) | Shaffof hisobot formati; xatolar: breakeven, HOLD 0% | Format |
| Birinchi aksiya qo'llanmasi | Fundamental qatlam; RSI va 5% stop tuzatildi | Qoida |
| Islomiy fintex (Faraz Adam) | Robo-maslahatchi shariat shartlari, skrining | Qoida |
| Atamalar lug'ati | Ilova ichidagi "?" izohlari | Format |
| Moliyaviy maqsadlar checklisti | 0-qatlam, DCA sozlamasi | Qoida |
| ARK Big Ideas 2021 | Tema ≠ signal; tema/korrelyatsiya diversifikatsiyasi | Qoida |
| Pattern Trainer | Faqat grafikda savdo rejasini chizish | Format |
| Akhliddin kanali | Formulalar, Breakout1, "EMA200 ga 1 oy tegmagan", 70–80%/15% | Qoida |
| Golden Cross | — | Ma'lumot uchun |
| Psixologik daraja | — | Sinovda |
| Treyding jurnal | Tozalash formulasi; 4 xato tuzatildi | Qoida |
| 6–7 modul checklist | To'liq baholash tuzilmasi, sektorga nisbatan | Qoida |
| 4-modul halollik | 24 oylik formula | Qoida |
| 8-modul portfel | Teglar, risk profili | Qoida |
| 3-modul buxgalteriya | TTM ishlatish | Qoida |
| 9-modul strategiyalar | Graham, UP-Value, Piotroski, UP-DCF, Baffet, Stable, Hyper, CANSLIM, Small cap, Healthy cash, Dogs of the Dow, Kings/Aristocrats | Strategiyalar musobaqasi |
| Graham "ovoz berish / tarozi" | Profil og'irliklari, VIX | Qoida (VIX sinovda) |
| 1926–2019 grafigi | Core-satellite | Qoida |
| Buy&Hold / Lump / DCA / Hybrid | Pul kiritish usullari | Qoida |

Asosiy tuzatishlar: mutlaq chegaralar o'rniga sektor ichidagi o'rin; qiymat strategiyalariga
trend filtri (AAP qiymat tuzog'i saboqi); ROE chegarasi 15%; sifat baholari ballga
aralashtirilmaydi; har bir nomzodning natijasi tarixda yoziladi.

---

## 6. Ma'lum muammolar va cheklovlar

- **Omon qolganlar xatosi:** bugungi SPUS ro'yxati o'tmishga qo'llanadi. Yechim: SEC N-PORT
  orqali choraklik tarkib (tekshirilmagan).
- **Fundamental ma'lumot o'sha kuni ma'lum bo'lganidek emas** (bepul manbada yo'q) →
  fundamental strategiyalar backtest emas, **virtual portfel musobaqasi** bilan tekshiriladi.
  Istisno: Dogs of the Dow va Kings/Aristocrats (narx + dividend tarixi yetarli).
- yfinance norasmiy manba: bo'shliqlar bo'lishi mumkin, sifat hisoboti majburiy.
- Supabase bepul tarifi cheklovlari (uzoq ishlatilmasa to'xtatilishi) — qarorgacha tekshiriladi.
- Small cap: SPUS'da yo'q, alohida halol manba kerak → 2-bosqich.
- MA (Mastercard) halolligi manbalarda turlicha — tekshiriladi.
- Suhbat chegarasi: oldingi chat rasm chegarasiga yetdi; ish yangi chatda davom etadi.

---

## 7. Bosqichlar holati

0–5 bosqichlar **bajarildi** (2026-11-02). Keyingisi — real ma'lumotda birinchi ishga tushirish,
1–2 hafta kuzatish va backtest natijasini birga ko'rib chiqish. Keyingi versiyaga qolganlar:
4H aniq kirish moduli, small cap, SEC N-PORT tarixiy tarkib, I18N (ingliz/rus).

Dastlabki reja (tarix uchun):

0. **v2 qoidalar hujjati:** barcha qatlamlar, kuzatuvga kirish/chiqish chegaralari,
   depozit himoyasi raqamlari, strategiyalar ro'yxati, Supabase sxemasi.
   Qaror kerak: core/satellite nisbati, depozit va oylik summa, risk profili,
   VIX chegarasi, kuzatuv chegaralari (nisbiy kuch %, cho'qqidan masofa).
1. **Ma'lumot quvuri v2:** 10+ yillik kunlik narx (SPUS, sektor ETF'lari, QQQ/SPY/IWM, VIX),
   fundamental hisobotlar, dividend tarixi, har kungi avtomatik yangilanish.
2. **Tahlil dvigateli:** bozor paneli, trend/nisbiy kuch, Piotroski, fundamental (sektorga
   nisbatan), halollik ikkinchi tekshiruvi, pullback va breakout signallari, testlar.
3. **Kuzatuv ro'yxati va tarix** (Supabase).
4. **Virtual portfel:** yadro + yo'ldosh, himoya qavatlari, strategiyalar musobaqasi.
5. **PWA ilova:** bozor paneli, kundalik ro'yxat, aksiya kartasi (grafikda savdo rejasi,
   "nega?" izohlari), kuzatuv, tarix, portfel, sozlamalar.

Backtest hisobotlari, xatolardan o'rganish, jurnal va tozalash moduli ham MVP'ga kiritildi.

---

## 8. Ishga tushirish qadamlari

To'liq yo'riqnoma — repozitoriydagi `README.md`. Qisqasi:
1. ZIP'ni repozitoriyga yuklash; eski `config.py`, `run_fetch.py`, `src/`, `tests/test_data.py`,
   `.github/workflows/fetch-data.yml` ni o'chirish.
2. `.github/workflows/daily.yml` va `backtest.yml` ni "Create new file" bilan yaratish.
3. Settings → Actions → Read and write; Settings → Pages → Source: GitHub Actions.
4. Actions → Kundalik skaner → Run workflow; keyin Backtest → Run workflow.
5. (Ixtiyoriy) Supabase: SQL, ro'yxatdan o'tishni o'chirish, o'zini qo'shish, 3 ta secret.
