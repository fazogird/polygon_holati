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

- VS Code PowerShell da `conda` tanilmadi (conda PowerShell uchun `init` qilinmagan) → `run.bat` qo'shildi
  (muhitni o'zi topadi) va README ga uch yo'l yozildi (run.bat / `conda init powershell` / VS Code interpreter).
- Repozitoriy: https://github.com/fazogird/polygon_holati (`main`). Ma'lumotlar (`data/`, `logs/`) gitga kirmaydi.

- **03 to'liq run (foydalanuvchi, Jomboy, fevral–oktyabr):** 101 sahna, 51 kun, 15 287 / 15 296 konturda qiymat,
  636 081 qator, **934 s (~15.5 daq)**. NDVI −0.8…0.997 (niqob ishladi). Kontur boshiga median 41 toza kuzatuv;
  bahorda siyrak (mart–may oyiga ~2), yozda oyiga 5–9.
- **03b grafiklar** (9 namuna): usul ishlaydi; qat'iy oylar ko'p dalada mos emas —
  bug'doy fevraldan yashil, iyunda o'riladi; "Ikkilamchi" Kartoshka aslida may–iyulda faol; "Boshqa" (Mavsumiy)
  faqat may–iyunda faol; "Birlamchi aniqlanmagan" may–iyul. → 04 da faollik oralig'i dalaning o'z egri chizig'idan.

### Taxminiy vaqt (sinovdan)
~45 s/kun (6 parallel oqim, ishxona interneti). Fevral–oktyabr ≈ 50–55 toza kun → **Jomboy uchun ~40 daqiqa**.
70 tuman uchun ketma-ket bir necha soat → keyingi qadamda tezlashtirish (AWS serverida ishlatish yoki o'qishni
optimallashtirish) ko'rib chiqiladi.
