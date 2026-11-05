# 0010 — Fenologiya: faol davr va NDVI bo'yicha suv oylari

**Sana:** 2026-11-05 · **Holat:** qabul qilingan (Jomboy grafiklarida tekshirilgan)

## Kontekst
Jomboy NDVI grafiklari qat'iy oylar (Birlamchi 3–5, Ikkilamchi 6–10, Mavsumiy 3–10) ko'p dalada haqiqatga mos
emasligini ko'rsatdi (bug'doy fevraldan yashil va iyunda o'riladi; ba'zi "Ikkilamchi"/"Boshqa" konturlar faqat
may–iyulda faol). Maqsad: ET hisobiga har kontur uchun **dalaning o'zidan** suv oylarini berish (ekin turi aniqlanmaydi).

## Usul (`src/fenologiya/fen.py`, `scripts/04_fenologiya.py`, sozlamalar `fenologiya:`)
1. Toza kuzatuvlar: dalaning ≥ 50% i toza bo'lgan sanalar.
2. Ikkala qo'shnisidan 0.15 dan ko'p past yakka nuqtalar (bulut qoldig'i) olib tashlanadi.
3. Kunlik chiziqli interpolyatsiya + 15 kunlik surilma o'rtacha.
4. Faol yadro: NDVI ≥ max(0.30, asos + 0.35 × (cho'qqi − asos)); 15 kundan qisqa pasayishlar (beda o'rimi)
   birlashtiriladi, 20 kundan qisqa yadrolar tashlanadi; cho'qqi − asos < 0.15 — dala yil bo'yi faol emas.
5. **Sikl chegarasi o'z amplitudasidan**: chap/o'ng eng past nuqtadan cho'qqigacha masofaning 20% iga yetgan joy
   (TIMESAT uslubi). Butun yil amplitudasi ishlatilganda ikkinchi (pastroq) ekin kech boshlanardi, bog' esa erta
   tugardi — tuzatildi. Davr boshida/oxirida NDVI ≥ 0.40 bo'lsa (kuzgi bug'doy), faollik davr chegarasidan.
6. **Sikl → mavsum**:
   - 2+ sikl: birinchisi Birlamchi kontur uchun, oxirgisi Ikkilamchi kontur uchun;
   - 1 qisqa sikl: cho'qqi 20-iyungacha → Birlamchi, keyin → Ikkilamchi (boshqa mavsumdagi kontur "faol emas");
   - 1 uzun sikl (≥ 150 kun, paxta/bog'): 20-iyunda bo'linadi;
   - Mavsumiy kontur: birinchi sikl boshidan oxirgi sikl oxirigacha.
   Shu tufayli bir joydagi Birlamchi va Ikkilamchi konturlar suvni **ikki marta sanamaydi**.
7. `suv_boshi_ndvi` / `suv_oxiri_ndvi` = faol oraliq boshi/oxiri oyi (`oldingi_sugorish_kun` bilan boshi oldinga
   surilishi mumkin — ekishdan oldingi sug'orish; hozir 0, ET jamoasi bilan kelishiladi).
8. `yorliq_mos`: faol oraliqning ≥ 60% i qat'iy oynaga tushsa `mos`, aks holda `farqli`; faol bo'lmasa `faol_emas`.
   `ishonch`: kuzatuv ≥ 25 va oraliq ichida ≥ 3 → yuqori; ≥ 15 → o'rta; aks holda past.

## Jomboy natijasi (15 296 kontur, 9 s)
| mavsum | mos | farqli | faol_emas |
|---|---|---|---|
| Birlamchi | 3 323 | 859 | 801 |
| Ikkilamchi | 4 935 | 9 | 456 |
| Mavsumiy | 4 770 | 1 | 29 |

Eng ko'p uchraydigan NDVI oylari: Birlamchi 2–6, Ikkilamchi 8–10 / 7–10, Mavsumiy 3–10 / 2–10.

## Tekshiruv
`tests/test_fen.py` (sun'iy qatorlar) va `scripts/03b_grafik.py` (qizil chiziq — silliq NDVI, pastdagi tasma —
topilgan faol oraliq).

## Ochiq
- `oldingi_sugorish_kun` qiymati (NDVI ekishdan 2–4 hafta keyin ko'tariladi).
- Chegara parametrlari boshqa tumanlarda (tog'li, sholi) grafiklar bilan tekshiriladi.
