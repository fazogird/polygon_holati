# 0007 — Piksel niqobi

**Sana:** 2026-11-05 · **Holat:** qabul qilingan

## Kontekst
Jomboy iyun sinovida NDVI o'rtachalari mantiqiy chiqdi (bug'doy o'rilgan 0.28, bog' 0.62, makka 0.47), lekin
ayrim konturlarda NDVI −58 161 va +167 204 kabi qiymatlar chiqdi. Sabab: c1 da qaytish = DN × 0.0001 − 0.1,
qorong'i piksellarda (suv, soya) qaytish ~0 yoki manfiy → NDVI maxraji ~0.

## Qaror (`src/fenologiya/indeks.py`)
Piksel yaroqli, agar:
- SCL sinfi `scl_toza` da: 4 vegetatsiya, 5 ochiq tuproq, 6 suv, 7 aniqlanmagan (bulut, soya, qor — yo'q);
- qizil, NIR, SWIR qaytishi (0, 1.5] oralig'ida;
- NDVI va NDMI maxraji > 0.02.

Indekslar qirqiladi: NDVI, NDMI ∈ [−1, 1], EVI2 ∈ [−1, 2.5].

## Tekshiruv
`tests/test_indeks.py` — qorong'i, manfiy, bulut va > 1.5 piksellar yaroqsiz deb topiladi.
