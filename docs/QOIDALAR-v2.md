# Qoidalar — v2.0.0

Barcha raqamlar `engine/config.py` da; bu hujjat ularning ma'nosini tushuntiradi. Qiymat o'zgarsa —
`RULES_VERSION` oshiriladi va pastdagi "O'zgarishlar jurnali"ga sana va sabab yoziladi.

Maqomlar: **Qoida** (qarorga ta'sir qiladi) · **Sinovda** (alohida o'lchanadi, qarorga ta'sir qilmaydi) ·
**Ma'lumot uchun** (ko'rsatiladi, ballga kirmaydi) · **Olinmadi**.

## 1. Aksiyalar ro'yxati (universe)
- SPUS ETF tarkibi (sp-funds.com CSV). Yuklanmasa — `universe/` dagi oxirgi nusxa.
- Likvidlik: narx ≥ $10, 20 kunlik o'rtacha savdo hajmi ≥ $20 mln.
- Halollik ikkinchi tekshiruvi (Uplift 4-modul, AAOIFI): qarz / 24 oylik o'rtacha kapitallashuv < 30%;
  naqd + qisqa muddatli investitsiyalar / kapitallashuv < 30%; foiz daromadi / jami daromad < 5%.
  Bajarilmasa — "Halollik shubhali" belgisi; kuzatuvdan chiqish sababi.
- Tozalash (purification): (choraklik nomaqbul daromad / aksiya) × egalik × (kunlar ÷ 90).

## 2. Bozor paneli — Qoida
| Holat | Shart | Ta'sir |
| --- | --- | --- |
| Yashil | QQQ > SMA200 va oxirgi kunlik pivot tub (5/5) buzilmagan | oddiy risk |
| Sariq | ikki shartdan biri buzilgan | risk 50% |
| Qizil | ikkalasi ham buzilgan | yangi xarid yo'q |
| VIX ≥ 22 | | risk 50% |
| VIX ≥ 30 | | yangi xarid yo'q |

Pivot tub "buzildi" = uning ostida ketma-ket 2 kun yopilish. Ma'lumot uchun: risk ishtahasi
(sezuvchan+davriy minus himoya sektorlari, 1 va 3 oy), IWM−SPY (3 oy), 11 sektor ETF reytingi
(0.4 × 1 oylik + 0.6 × 3 oylik SPY'ga nisbatan daromad).

## 3. Ball qatlamlari
Har bir qatlam 0–100 (bajarilgan tekshiruvlar ulushi; ma'lumot yo'q tekshiruv hisobga olinmaydi).
Qatlamlar teng og'irlikda.
- **O'rta profil:** Trend, Kuch, O'sish, Sifat.
- **Uzoq profil:** Sifat, O'sish, Qiymat, Trend, Dividend.

| Qatlam | Tekshiruvlar |
| --- | --- |
| Trend | Weinstein bosqichi 2; narx > SMA50 > SMA150 > SMA200; 40 haftalik o'rtacha ustida |
| Kuch | nisbiy kuch (IBD uslubi: 63/126/189/252 kun, 0.4/0.2/0.2/0.2) SPUS ichida; 52 haftalik cho'qqidan ≤10% |
| Sifat | Piotroski ≥ 6; ROE va sof marja sektorida yuqori yarmida; FCF > 0; D/E ≤ 1; joriy nisbat ≥ 1 |
| O'sish | daromad va EPS: chorak (yillik taqqoslash) va 3 yillik o'rtacha > 10% |
| Qiymat | P/E va P/FCF sektorining arzonroq yarmida; teskari DCF (ma'lumot uchun) |
| Dividend | daromad ≥ 2%; ≥ 10 yil uzluksiz oshirilgan (25+ Aristokrat, 50+ Qirol); payout < 60% |

Mutlaq chegaralar o'rniga **sektor ichidagi o'rin** ishlatiladi (6–7 modul saboqi). Teskari DCF:
diskont 10%, terminal o'sish 3%, 10 yil — ballga kirmaydi.

## 4. Kuzatuv ro'yxati — Qoida
**O'rta muddat (2 hafta – 6 oy) — kirish (hammasi):** bosqich 2; nisbiy kuch ≥ 70-foizlik;
52 haftalik cho'qqidan ≤ 25%; sektori kuchli yarmida; 21 kun EMA200 ga tegmagan; likvid.
*Yoki* Episodic Pivot: gap ≥ 5% va hajm ≥ 2× (20 kun ichida), narx gap tubidan va SMA150 dan yuqori.
**Chiqish (biri yetarli):** SMA150 ostida ketma-ket 3 kun; nisbiy kuch < 40; cho'qqidan > 35%;
hisobot gapi ≤ −7%; halollik yo'qoldi.

**Uzoq muddat (1 yil+) — kirish:** halol; Piotroski ≥ 6; ROE ≥ 15%; D/E ≤ 1; FCF > 0; narx 40 haftalik
o'rtachadan yuqori. **Chiqish:** Piotroski ≤ 3; FCF < 0; halollik yo'qoldi; narx 40 haftalik o'rtachadan 10% past.

Har bir kirish va chiqish sana, narx va sabab bilan `state/watch_history.jsonl` ga yoziladi va o'zgartirilmaydi.

## 5. Kirish signallari (kunlik) — Qoida
Faqat **o'rta kuzatuvdagi** aksiyalarda; kirish ertangi ochilish narxida.

**Pullback (Uplift qo'llanmasi, 8 qoida):** trend (EMA tartibi); zinapoya H1>H2, L1>L2 (swing filtri ≥1 ATR);
impuls ≥ 3 ATR; chuqurlik 38.2–61.8%; cho'qqidan keyin 2–15 sham; L1 saqlangan; zona — eski qarshilik /
EMA20 / trend chizig'idan kamida 2 tasi ±0.5 ATR ichida; tasdiq shami (bolg'a, yutuvchi yoki oldingi
cho'qqidan yuqori yopilish). Stop: pullback tubi − 0.25 ATR. Maqsad: H1. R/R ≥ 2, risk 0.75–3 ATR.

**Breakout (Akhliddin Breakout1):** narx > EMA100; 21 kunlik yangi cho'qqi; 52 haftalik yoki 6 oylik
cho'qqiga 3% ichida; hajm ≥ 1.5× 50 kunlik o'rtacha. Stop: 10 kunlik tub − 0.25 ATR (0.75–3 ATR
oralig'iga keltiriladi). Maqsad: 3R.

**Savdoni boshqarish:** stop, maqsad yoki 40 savdo kuni; kuzatuvdan chiqsa — yopiladi.
Hisobotga ≤ 5 savdo kuni qolsa kirilmaydi. Ochilish stopdan pastda bo'lsa — ochilish narxida chiqiladi.
Xarajatlar: $0.005/aksiya (min $1), har tomonda 0.05% sirpanish.

Ma'lumot uchun: Golden Cross. Sinovda: psixologik daraja. Olinmadi: pattern trainer.

## 6. Depozit himoyasi va portfel — Qoida
| Parametr | Qiymat |
| --- | --- |
| Yadro / faol qism | 60% SPUS / 40% |
| Bitta savdo riski | umumiy kapitalning 0.75% |
| Barcha ochiq stoplar birdan urilsa | ≤ 5% |
| Bitta pozitsiya | ≤ 15% |
| Pozitsiyalar soni | ≤ 8; sektor bo'yicha ≤ 2; korrelyatsiya klasteri (60 kun, ≥0.7) bo'yicha ≤ 2 |
| Faol qismda naqd | ≥ 20% |
| Cho'qqidan pasayish −5% | risk yarmiga |
| Cho'qqidan pasayish −10% | yangi xarid to'xtaydi |

## 7. Strategiyalar musobaqasi (9-modul) — Sinovda
Har biri alohida $10 000 virtual portfel; oy boshida mezonga mos eng yuqori 10 ta aksiya teng ulushda
(Dogs of the Dow — yilda bir marta). SPUS bilan taqqoslanadi. Fundamental strategiyalar tarixda
sinab bo'lmaydi — musobaqa birinchi real ishdan boshlanadi; xulosa ≥ 1 yildan keyin.
Stable growth, Hyper growth, CANSLIM, UP-Value (+trend), UP-DCF (+trend), Healthy cash,
Dividend Aristokratlari, Dogs of the Dow (DJIA ∩ SPUS), Uzoq kuzatuv, SPUS, Faol signallar.
Qiymat strategiyalariga trend filtri qo'shilgan (narx SMA200 ustida) — "qiymat tuzog'i" saboqi.

## 8. Backtest va qaror mezonlari
70% sozlash / 30% tekshiruv (vaqt bo'yicha). 300 marta tasodifiy kirish (bir xil ATR stop va R maqsad).
To'rt variant: faqat signal; + rejim; + kuzatuv; + rejim + kuzatuv.
**"Davom"** uchun tekshiruv qismida hammasi: ≥ 100 signal; kutilma ≥ +0.10R; profit faktor ≥ 1.2;
tasodifiy kirishlarning yuqori 5% ida; portfel pasayishi ≤ 20%; tekshiruv kutilmasi sozlashdagining ≥ yarmi.
Signal yetarli bo'lmasa — **"noaniq"**, aks holda **"to'xtash"**.

## 9. O'rganish
Har yopilgan savdo kirish paytidagi belgilar bilan yoziladi (signal turi, rejim, VIX, sektor kuchi, EP,
nisbiy kuch guruhi). Har guruhda ≥ 30 savdo bo'lib, kutilmadagi farq ≥ 0.20R bo'lsa — **taklif** chiqadi.
Dastur o'zi o'zgartirmaydi; taklif qabul qilinsa — yangi versiya, eski versiya bilan parallel sinaladi.

## O'zgarishlar jurnali
- **2.0.0 (2026-11-02)** — birinchi to'liq versiya: ikki profil, kuzatuv, pullback + breakout,
  depozit himoyasi, musobaqa, backtest, o'rganish. Standart qiymatlar Ulugbekning "nima to'g'ri bo'lsa
  shuni qil" ko'rsatmasi bilan tanlandi: yadro 60/40, risk 0.75%, VIX 22/30, kuzatuv chegaralari yuqoridagidek.
