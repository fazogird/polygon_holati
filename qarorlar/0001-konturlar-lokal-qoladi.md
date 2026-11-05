# 0001 — Konturlar tashqariga chiqmaydi

**Sana:** 2026-11-05 · **Holat:** qabul qilingan

## Kontekst
Har bir kontur uchun Sentinel-2 indeks vaqt qatori kerak. Google Earth Engine eng tez yo'l, lekin u konturlarni
yuklashni talab qiladi — tashkilot ma'lumotini (to'liq shp) GEE ga yuklab bo'lmaydi.

## Qaror
Sun'iy yo'ldosh tasvirlari ochiq bulut omborlaridan **STAC + COG** orqali **oqim bilan** o'qiladi (faqat kerakli
bo'laklar), hisob **lokal** (yoki tashkilotning o'z AWS serverida) bajariladi. Konturlar hech qayerga yuklanmaydi.
Natija `uniqueid` bo'yicha lokalda asl konturlar bilan birlashtiriladi.

## Ko'rib chiqilgan muqobillar
- GEE: tez, lekin geometriya yuklanadi — rad etildi.
- `uniqueid` + faqat geometriya faylini platformaga yuklash: mumkin, lekin geometriyaning o'zi ham ma'lumot — kerak emas,
  chunki lokal oqim usuli bunisiz ishlaydi.

## Oqibat
- Ruxsat talab qilinmaydi; ma'lumot nazorati to'liq tashkilotda.
- Hisob tezligi internet tezligiga bog'liq (AWS serverida ishlatilsa — ancha tez).
