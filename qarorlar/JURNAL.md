# Jarayon jurnali

## 2026-11-05
- Loyiha papkasi `D:\Tasks\ekin_fenologiya` yaratildi (config, src, scripts, data, logs, tests, docs, env, qarorlar).
- **00 tezlik testi** (AWS va Planetary Computer, Jomboy, 2026-04/06/07): ikkalasi ishlaydi, AWS ~2× tez → qaror 0002.
- `gis_pro`/`aws_et` da DLL xatosi aniqlandi va sababi topildi → `fenologiya` muhiti va `muhit.py` → qaror 0005.
- **01** (Jomboy, eski 10 m bufer bilan): 15 296 kontur; 844 tasi bufer bilan yo'qolardi → qaror 0004 (maydonga qarab bufer).
- **02 + 03 sinovi** (Jomboy, faqat 2026-06): 12 sahna, 6 kun, plitkalar T42SUJ + T42TUK; 15 269 konturda qiymat,
  73 727 qator; vaqt ~270 s (~45 s/kun). NDVI medianlari mantiqiy; qorong'i piksellarda katta qiymatlar topildi →
  qaror 0007 (niqob), `tests/test_indeks.py`.
- Asosiy davr fevral–oktyabr 2026 → qaror 0003. Asosiy run'lar foydalanuvchi tomonidan → qaror 0008.

### Taxminiy vaqt (sinovdan)
~45 s/kun (6 parallel oqim, ishxona interneti). Fevral–oktyabr ≈ 50–55 toza kun → **Jomboy uchun ~40 daqiqa**.
70 tuman uchun ketma-ket bir necha soat → keyingi qadamda tezlashtirish (AWS serverida ishlatish yoki o'qishni
optimallashtirish) ko'rib chiqiladi.
