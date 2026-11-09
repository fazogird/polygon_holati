# 0012 — Zona kalendari va suv oylari (v3)

**Sana:** 2026-11-06 … 2026-11-09 · **Holat:** qabul qilingan (foydalanuvchi bilan kelishilgan)

## Kontekst
04 natijasi (69 tuman) har kontur uchun NDVI faol davrini berdi, lekin oylar konturdan konturga juda farq qiladi.
ET hisobi uchun barqaror qoida kerak: viloyat / agroiqlim zonasi / ekin turi bo'yicha guruh oylari, so'ng ular
v1 konturlariga (`ekin_yerlar_qisqa.gpkg`) faqat `suv_boshi` / `suv_oxiri` ustunlari orqali yoziladi.

## Zona kalendari (`config/zonalar.yaml`, `scripts/04d_zona_kalendar.py`)
- Zonalar: Qashqadaryo G'arb / Sharq; Farg'ona G'arb / Sharq; Samarqand G'arb / Markaz / Tog'li; Sirdaryo bitta.
- Oy guruhga kiradi, agar o'sha oyda faol maydonning ≥ 50% i kamida 10 kun yashil bo'lsa.
- Zonalar orasida farq deyarli yo'q — viloyat darajasi yetarli; alohida faqat Samarqand Tog'li (bug'doy 3-5).

## Suv oylari qoidasi (`config/suv_oylari.yaml`, `src/fenologiya/suv.py`)
1. **Birlamchi** — hammasi **3-oydan** (ekish oldi sug'orish ham kiradi); tugashi ekin turi bo'yicha:
   Ozuqa 3-5, Qashqadaryo va Samarqand Tog'li bug'doyi 3-5, qolganlari 3-6.
2. **Ikkilamchi** (shu jumladan "aniqlanmagan" — bo'sh qolmaydi) — shu daladagi Birlamchi tugagan oydan keyin,
   **10-oygacha**: 3-5 → 6-10, 3-6 → 7-10. Bitta dalada bir oy ikki mavsumga yozilmaydi (ET ikki marta hisoblanmaydi).
3. **Mavsumiy** (Bog', Paxta, Boshqa, Beda ...) — **3-10**.
4. **Ozuqa yoki Bug'doy ustidagi Paxta** — Mavsumiy emas, **Ikkilamchi ekin** (`season` ham o'zgaradi), 5-10;
   ostidagi Birlamchi 3-4 (NDVI: ozuqa aprel boshida tugaydi, paxta iyunda ko'karadi). 463 kontur, 7 184 ga.
5. Bitta dala: ikki kontur kesishmasi ulardan birining maydonining ≥ 50% i; bir nechta bo'lsa — eng kattasi.

Natija (to'liq qisqa fayl): Birlamchi 3-4 / 3-5 / 3-6; Ikkilamchi 5-10 / 6-10 / 7-10; Mavsumiy 3-10.
8 yoki 9 bilan tugaydigan kontur yo'q.

## Faylga yozish
- Kirish GPKG nusxalanadi, nusxada SQL UPDATE: faqat `suv_boshi`, `suv_oxiri` (va 4-banddagi `season`).
  Geometriya, boshqa ustunlar, fid, `uniqueid` o'zgarmaydi — `suv.faqat_suv_farqi()` tekshiradi (sinovda 0).
- Chiqish asl fayl yonida: `ekin_yerlar_qisqa_v3_fenologiya.gpkg` (+ `_ozgarish.csv`, `_chegara_farqli.csv`).
- Ishga tushirish: `scripts/05_suv_oylari.py` yoki `notebooks/suv_oylari.ipynb`.

## Rad etilgan variantlar
- NDVI "faol emas" Ikkilamchi aniqlanmagan konturlarni suvsiz qoldirish (Qashqadaryoda 84%) — foydalanuvchi:
  ular Ikkilamchi, bo'sh emas.
- Ekin turi bo'yicha NDVI'ga aniq mos oylar (Boshqa 3-5, Bog' 3-9, Mosh 7-9 ...) — Mavsumiy hammasi 3-10,
  Ikkilamchi hammasi 10 gacha qilib soddalashtirildi.
- Paxta 5-10 (NDVI'dan) — butun ekin 3-10 qabul qilindi.

## Birlamchi ↔ Ikkilamchi chegarasi (v3, to'liq qisqa fayl)
Aynan bir xil 105 201 juft; deyarli bir xil (IoU ≥ 0.99) 3 609; chegarasi farq qiladi — Birlamchi 7 205 /
Ikkilamchi 11 030 kontur; jufti yo'q — 1 Ikkilamchi.
