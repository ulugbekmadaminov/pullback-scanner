# Pullback skaner — 2-qadam: ma'lumot yig'ish

Bu repozitoriy backtest uchun ma'lumot yig'adi: SPUS tarkibidagi ~215 halol aksiya
va QQQ, SPY uchun oxirgi ~2 yillik 4H shamlar, kunlik benchmarklar, hisobot sanalari
va sifat tekshiruvi. Qoidalar: "Pullback skaner — 1-qadam: qoidalar spetsifikatsiyasi".

## Bir martalik sozlash (10 daqiqa)

1. github.com da yangi **public** repozitoriy oching, masalan `pullback-scanner`.
   Public bo'lishi kerak: unda faqat ochiq narx ma'lumoti bo'ladi, shaxsiy narsa yo'q,
   va Claude natijani to'g'ridan-to'g'ri o'qiy oladi.
2. **Add file → Upload files** orqali shu ZIP ichidagi barcha fayl va papkalarni yuklang
   (`.github` papkasi ham kirishi shart). **Commit changes** bosing.
3. **Settings → Actions → General → Workflow permissions** da
   **Read and write permissions** ni tanlab, **Save** bosing.

## Ishga tushirish

1. **Actions** bo'limi → chapda **"2-qadam — ma'lumot yig'ish"** → **Run workflow**.
2. 20–40 daqiqa kuting. Yashil ✓ chiqsa, `data/` papkasi repozitoriyda paydo bo'ladi.
3. Repozitoriy havolasini Claude'ga yuboring.

Qizil ✗ chiqsa, uning sahifasidagi xabarni skrinshot qilib yuboring.

## Muhim: ma'lumot muzlatiladi

Backtest bitta, o'zgarmas ma'lumot to'plamida o'tkaziladi. Shuning uchun workflow'ni
**faqat bir marta** ishga tushiring. Qayta ishga tushirilsa, sozlash (70%) va tekshiruv
(30%) qismlari chegarasi siljiydi va natijani solishtirib bo'lmay qoladi.

## Natija tarkibi (`data/`)

| Fayl | Nima |
| --- | --- |
| `universe.csv` | Aksiyalar ro'yxati, sektor va sanoat bilan |
| `4h/<TICKER>.parquet` | 4H shamlar: 09:30–13:30 va 13:30–16:00 (ET) |
| `1d/QQQ.parquet`, `1d/SPY.parquet` | 10 yillik kunlik shamlar (bozor rejimi uchun) |
| `earnings.json` | Hisobot sanalari (`null` — yuklanmadi) |
| `quality.csv` | Har aksiya uchun: bo'shliqlar, keskin sakrashlar, OHLC xatolari |
| `manifest.json` | Qachon, qaysi manbadan, qaysi versiyalar bilan yig'ilgani |

## Ma'lum cheklovlar

- Ro'yxat bugungi SPUS tarkibi; 2 yil oldin u boshqacha bo'lgan (natija biroz optimistik).
- yfinance bepul, norasmiy manba: ba'zan bo'shliq bo'ladi, `quality.csv` ularni ko'rsatadi.
- Yangi birjaga chiqqan aksiyalarda tarix qisqa (`qisqa tarix` belgisi).

## Mahalliy ishga tushirish (ixtiyoriy)

```bash
pip install -r requirements.txt
python -m pytest -q
python run_fetch.py
```
