# 0006 — Zonal statistika: yorliq-rastr + bincount

**Sana:** 2026-11-05 · **Holat:** qabul qilingan

## Kontekst
Har sana uchun minglab konturning o'rtacha indeksini hisoblash kerak. Bir joyda Birlamchi va Ikkilamchi kontur
ustma-ust turadi (bir xil yer, ikki mavsum) — ularni bitta rastrga yozib bo'lmaydi.

## Qaror
- Hisob to'ri: **EPSG:32642 (UTM 42N), 10 m** — tuman chegarasi bo'yicha.
- Konturlar **mavsum sinfi** bo'yicha (Birlamchi / Ikkilamchi / Mavsumiy / boshqa) alohida yorliq-rastrlarga
  o'tkaziladi (bir sinf ichida konturlar ustma-ust tushmaydi).
- Har sana uchun tasvir **bir marta** o'qiladi (bir kundagi plitkalar birlashtiriladi — `groupby=solar_day`),
  indekslar hisoblanadi va `numpy.bincount` bilan barcha konturlarning yig'indisi va toza piksel soni bir yo'la olinadi.
- Kontur-sana yozuvi faqat `toza_piksel >= min_toza_piksel` (3) bo'lsa saqlanadi.

## Oqibat
Kontur soniga deyarli bog'liq emas (tez); `exactextract` kerak emas. Pikselning kontur ichiga tushishi markazi bo'yicha.
