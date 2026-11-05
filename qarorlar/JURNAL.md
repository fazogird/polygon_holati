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

- Git: foydalanuvchi `origin` ni GitLab `dalaga_index_run` ga o'zgartirgan, push o'tmagan (GitLab boshlang'ich
  commit). Boshlang'ich commit birlashtirildi, force'siz push: GitLab `master` + GitHub `main` → qaror 0009.
- `pipeline.py` (ko'p tuman, davom ettirish) va `royxat` qo'shildi; fayl nomlari to'liq tuman nomidan (to'qnashuv
  tuzatildi), Jomboy fayllari qayta nomlandi. Samarqand: 18 tuman, qolgan 17 ~7 soat (taxmin).

- 18:00 — foydalanuvchi 4 viloyatni 4 ta VS Code terminalida parallel ishga tushirdi (Samarqand va Qashqadaryo
  `--ishchi 4`, Farg'ona va Sirdaryo `--ishchi 6`). Taxmin: tugashi ~3:30–6:30. RAM 64 GB (bo'sh ~29 GB).
- **04 fenologiya** yozildi va Jomboy'da sinaldi (9 s): faol sikllar, sikl chegarasi o'z amplitudasidan (20%),
  mavsumga biriktirish, NDVI suv oylari → qaror 0010. Birinchi variantda ikkinchi ekin kech boshlanardi va bog' erta
  tugardi — grafikda ko'rinib, tuzatildi. `tests/test_fen.py`, `pipeline.py fenologiya`, 03b ga silliq chiziq.
  Run vaqtida 01–03 va ular ishlatadigan modullarga tegilmadi.

- ~18:20 holat: 4 jarayon xatosiz; Beshariq tugadi (56 kun, 943 s). Xotira har jarayonda ~0.6 GB (23 GB bo'sh),
  tarmoq jami ~84 Mbit/s (karta 1 Gbit/s) → cheklov tarmoq emas, so'rov kechikishi.
  **Muhim topilma**: ko'p tumanlar ikki orbita chegarasida — 80–105 kun (Jomboy 51). Taxmin 1.2–1.8× kam chiqdi;
  qayta hisob: Farg'ona/Sirdaryo tunda tugaydi, Samarqand ~20–25 soat, Qashqadaryo ~30–35 soat.
  → `pipeline.py indeks --teskari` (ikkinchi terminal oxiridan boshlaydi) va band/qulf tekshiruvi qo'shildi
  (holat.csv dagi "01" son bo'lib o'qilish xatosi testda topilib tuzatildi).
- `docs/ISHGA_TUSHIRISH.md` — to'liq yo'riqnoma (muhit, parallel run, kuzatish, davom ettirish, 04, git, muammolar).

### Taxminiy vaqt (sinovdan)
~45 s/kun (6 parallel oqim, ishxona interneti). Fevral–oktyabr ≈ 50–55 toza kun → **Jomboy uchun ~40 daqiqa**.
70 tuman uchun ketma-ket bir necha soat → keyingi qadamda tezlashtirish (AWS serverida ishlatish yoki o'qishni
optimallashtirish) ko'rib chiqiladi.
