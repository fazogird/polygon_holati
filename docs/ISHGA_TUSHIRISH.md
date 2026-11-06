# Ishga tushirish yo'riqnomasi (runbook)

Boshidan oxirigacha: muhit → 01–03 (indeks vaqt qatori) → 04 (fenologiya) → tekshirish → git.
Har bir bandda **nega** shunday qilinishi qavs ichida yoki qaror raqami bilan ko'rsatilgan.

---

## 0. Bir martalik tayyorgarlik

1. **Muhit** (`fenologiya`, qaror 0005):
   ```
   conda env create -f env\environment.yml
   ```
2. **Terminal** — uch yo'ldan biri (VS Code PowerShell da `conda` "не распознано" chiqsa):
   - eng oson: `python` o'rniga **`.\run.bat`** (muhitni o'zi topadi, activate shart emas);
   - doimiy: `& "$env:LOCALAPPDATA\miniconda3\Scripts\conda.exe" init powershell`, terminalni qayta ochish
     (kerak bo'lsa `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`);
   - VS Code: `Ctrl+Shift+P` → *Python: Select Interpreter* → `fenologiya`.
3. **Kirish fayli**: `config\sozlamalar.yaml` → `kirish_konturlar` (birlamchi_ikkilamchi natijasi, `uniqueid` bilan).
4. **Tekshiruvlar** (bir necha soniya, hammasi `OK` bo'lishi kerak):
   ```
   .\run.bat tests\test_indeks.py
   .\run.bat tests\test_bufer.py
   .\run.bat tests\test_fen.py
   ```

---

## 1. Rejalashtirish

```
.\run.bat pipeline.py royxat
```
Har tuman: kontur soni, 01/02/03 holati, taxminiy vaqt.

**Taxmin haqida muhim** (2026-11-05 tajribasi): `royxat` taxmini Jomboy (51 kun) asosida. Ko'p tumanlar
Sentinel-2 ning **ikki orbitasi chegarasida** — ularda 80–105 kun bor va vaqt **1.2–1.8 baravar ko'p** bo'ladi.
Aniq taxmin uchun tumanlar bo'yicha kunlar soni kerak (02 dan keyin `data\oraliq\sahnalar_*.json`).

| Viloyat (fevral–oktyabr 2026) | Tuman | O'rtacha kun | Taxminiy vaqt (1 jarayon) |
|---|---|---|---|
| Farg'ona | 20 | 87 | ~5–9 soat |
| Sirdaryo | 14 | 91 | ~5–8 soat |
| Samarqand | 18 | 79 | ~20–25 soat |
| Qashqadaryo | 18 | 92 | ~30–35 soat |

Eng uzoq tumanlar: Nurobod, Qamashi (~5 soat), Muborak, Qo'shrabot, Ko'kdala (~3 soat) — tog'li, dalalari siyrak,
lekin to'rtburchagi katta (keyinchalik "faqat dala atrofini o'qish" bilan optimallashtirish mumkin).

---

## 2. 01–03: indeks vaqt qatori (asosiy, uzoq run)

**Kompyuter uxlab qolmasin**: `powercfg /change standby-timeout-ac 0` (yoki Параметры → Питание → Никогда).
**VS Code ni yopmang** (terminal yopilsa run to'xtaydi; ekranni Win+L bilan qulflash mumkin).

### Parallel: har viloyat alohida terminalda
VS Code terminal panelida **+** bilan yangi terminal, har biriga bitta buyruq:
```
.\run.bat pipeline.py indeks --viloyat "Qashqadaryo viloyati" --ishchi 4
.\run.bat pipeline.py indeks --viloyat "Samarqand viloyati"   --ishchi 4
.\run.bat pipeline.py indeks --viloyat "Farg'ona viloyati"    --ishchi 6
.\run.bat pipeline.py indeks --viloyat "Sirdaryo viloyati"    --ishchi 6
```
Katta viloyatlar uchun **ikkinchi terminal** — tumanlarni **oxiridan** boshlaydi va o'rtada uchrashadi:
```
.\run.bat pipeline.py indeks --viloyat "Qashqadaryo viloyati" --ishchi 4 --teskari
.\run.bat pipeline.py indeks --viloyat "Samarqand viloyati"   --ishchi 4 --teskari
```
- Boshqa jarayon ishlayotgan tuman o'tkazib yuboriladi (qulf fayli `logs\qulf_*.lock` yoki `logs\holat.csv` dagi
  "01/02 ok, 03 hali yo'q" belgisi). Uchrashuv nuqtasida eng ko'pi bilan bitta tuman ikki marta hisoblanishi mumkin —
  natija bir xil, zarar yo'q.
- **Nega parallel ishlaydi**: cheklov internet tezligi emas (tarmoq 1 Gbit/s, 4 jarayon jami ~84 Mbit/s ishlatdi),
  protsessor deyarli bo'sh — har o'qish so'rovining kechikishi asosiy vaqt. Xotira: kichik tumanda jarayon ~0.6 GB;
  eng katta tumanlarda (Nurobod, Qamashi) ~8–12 GB gacha — shuning uchun katta viloyatlarga `--ishchi 4`.

### Davom ettirish (to'xtab qolsa)
Xuddi shu buyruqni qayta bering — natija fayli bor qadamlar o'tkaziladi. Bir tuman xato bersa, pipeline keyingisiga
o'tadi; oxirida **XULOSA** jadvali. Bitta tumanni qaytadan: `--tuman "X tumani" --qayta`.

### Kuzatish (run davomida)
- Terminalda: `[3/18] … tuman`, `  40/97 kun | 1650 s`.
- Jurnallar: `logs\pipeline_<viloyat>[_teskari]_<vaqt>.log`, umumiy holat: `logs\holat.csv`
  (har qadam: vaqt, tuman, qadam, ok/XATO, soniya).
- Holat jadvali: `.\run.bat pipeline.py royxat`.

---

## 3. 04: fenologiya (tez)
```
.\run.bat pipeline.py fenologiya --hammasi
```
Tuman boshiga bir necha soniya; faqat 03 tayyor tumanlar. Natija: `data\natija\fenologiya_<tuman>.parquet`
(qaror 0010). Parametrlar: `config\sozlamalar.yaml` → `fenologiya:`.

## 4. Tekshirish grafiklari
```
.\run.bat scripts\03b_grafik.py --tuman "Qamashi tumani"
.\run.bat scripts\03b_grafik.py --tuman "Jomboy tumani" --uniqueid <id1> <id2>
```
`data\natija\grafik_*.png`: nuqtalar — NDVI, qizil chiziq — silliq NDVI, pastdagi qizil tasma — topilgan faol
oraliq, sarlavhada NDVI bo'yicha suv oylari va `yorliq_mos`.

---

## 5. Git (ikki repozitoriy, qaror 0009)
```
git add -A
git commit -m "..."
git push origin master          # ishxona GitLab: dalaga_index_run (master himoyalangan — force ishlatilmaydi)
git push github master:main     # shaxsiy GitHub: polygon_holati
```
`data\`, `logs\` gitga kirmaydi (`.gitignore`). GitLab "rejected" desa: avval `git pull origin master`
(yoki birinchi marta — boshlang'ich commit bilan `git merge origin/master --allow-unrelated-histories`).

---

## 6. Uchragan muammolar va yechimlari

| Belgisi | Sababi | Yechim |
|---|---|---|
| `conda` "не распознано" (VS Code PowerShell) | conda PowerShell uchun `init` qilinmagan | `.\run.bat` yoki 0-band, 2-punkt |
| Python `0xc06d007f` bilan jim qulaydi (exit 127) | muhit activate qilinmagan → boshqa BLAS/LAPACK DLL | `src\fenologiya\muhit.py` buni o'zi tuzatadi (qaror 0005); yangi skriptlarda birinchi import qilinsin |
| NDVI ±100 000 kabi qiymatlar | c1 da qaytish = DN·0.0001 − 0.1, qorong'i pikselda maxraj ~0 | piksel niqobi (qaror 0007) |
| Kichik konturlar yo'qolardi | hammasiga 10 m bufer | maydonga qarab bufer (qaror 0004) |
| `Guliston` va `Guliston tumani` fayllari ustma-ust | fayl nomidan "tumani" olib tashlanardi | to'liq nomdan fayl nomi (qaror 0009) |
| Vaqt taxmini 1.5–2× kam chiqdi | ikki orbita chegarasidagi tumanlarda 2× ko'p kun | 1-banddagi jadval; parallel/teskari terminallar |
| `UserWarning: Could not parse bucket/account`, `NotGeoreferencedWarning` | kutubxona ogohlantirishlari | zararsiz; pipeline jurnalida yashiriladi |
| GitLab push rad etildi | himoyalangan `master` + boshlang'ich commit | birlashtirib, force'siz push (5-band) |
| Terminal bir joyda soatlab yangi qator chiqarmaydi, Ctrl+C ishlamaydi | tasodifiy qotish (javobsiz tarmoq so'rovi) | terminalni o'ldirish → `Remove-Item logs\qulf_<tuman>.lock` → o'sha buyruqni qayta berish |
| `Ignoring read failure ... Could not resolve host` ko'p marta | ishxona DNS uzilishi | qiymat buzilmaydi, lekin kunlar yo'qoladi; DNS tiklangach tumanni `--tuman "X" --qayta` bilan qaytadan. Bir-ikkita alohida xato — e'tiborsiz |
| `--qayta` bersa ham "boshqa jarayon ishlayapti — o'tkazildi" | o'ldirilgan jarayonning `holat.csv` dagi izi (eski versiya) | 2026-11-06 da tuzatilgan: `--qayta` endi bu belgiga qaramaydi |
| O'ldirilgandan keyin tuman "qulflangan — o'tkazildi" | qulf fayli qolgan | `Remove-Item logs\qulf_<tuman>.lock` |
| Eski terminal qulflarni bilmaydi (kod yangilanishidan oldin boshlangan) | jarayon kodni boshlanishida yuklaydi | u boshqa terminal ishlayotgan tumanga yetganda o'ldirish (natija bir xil, faqat vaqt behuda) |
| Run vaqtida kodni o'zgartirish xavfi | pipeline har tuman uchun 01–03 ni **qaytadan** ishga tushiradi | run davomida `scripts\01–03` va `src\fenologiya\{muhit,sozlama,indeks}.py` ga tegilmaydi |
