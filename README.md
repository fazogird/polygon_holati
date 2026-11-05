# polygon_holati

*(lokal papka: `ekin_fenologiya`)*

Har bir ekin konturi uchun **Sentinel-2 (10 m) indeks vaqt qatori** (NDVI, EVI2, NDMI) va undan
**mavsum bo'yicha faollik** (dala qachon tirik bo'lgan → `suv_boshi` / `suv_oxiri`) — ET (suv iste'moli)
hisobiga konturlarni mavsumlari ajratilgan holda tayyorlash uchun.

Ekin turi aniqlanmaydi — faqat dalaning o'z "ritmi" (fenologiyasi).
Kirish: `birlamchi_ikkilamchi` loyihasining natijasi (`uniqueid` bilan konturlar).

## Tamoyillar
- Konturlar **kompyuterdan chiqmaydi**: sun'iy yo'ldosh tasvirlari ochiq STAC/COG manbalardan oqim bilan o'qiladi,
  hisob lokal (yoki tashkilotning o'z AWS serverida).
- Manba konfiguratsiyada tanlanadi: `aws` (Earth Search, `sentinel-2-c1-l2a`) yoki `pc` (Planetary Computer).
- Natija `uniqueid` bo'yicha — asl konturlar bilan lokalda birlashtiriladi.

## Tuzilma
```
config/      sozlamalar.yaml — manba, sana oralig'i, indekslar, bulut chegarasi
src/fenologiya/  kutubxona: STAC qidiruv, o'qish, indekslar, zonal statistika, fenologiya
scripts/     pipeline qadamlari (00_ ... 0N_)
data/        kirish/ oraliq/ natija/   (gitga kirmaydi)
logs/        jurnallar                 (gitga kirmaydi)
tests/       testlar (test_indeks, test_bufer)
qarorlar/    qabul qilingan qarorlar va jarayon jurnali
docs/        hujjat va rasmlar
env/         conda muhit tavsifi
run.bat      fenologiya muhitida skript ishga tushirish (activate shart emas)
```

## Pipeline
| Qadam | Skript | Nima | Holat |
|---|---|---|---|
| 00 | `00_test_tezlik.py` | manbalar (AWS / PC) mavjudligi va o'qish tezligi | tayyor |
| 01 | `01_geom_tayyorlash.py` | konturlar → `uniqueid` + mavsum + geometriya (UTM 42N), ichki bufer **maydonga qarab** | tayyor |
| 02 | `02_stac_qidiruv.py` | davr bo'yicha Sentinel-2 sahnalari ro'yxati (bulut filtri) | tayyor |
| 03 | `03_indeks_qator.py` | har kontur × sana: NDVI, EVI2, NDMI, toza piksel soni | tayyor |
| 03b | `03b_grafik.py` | namunaviy konturlar NDVI grafiklari (tekshirish) | tayyor |
| 04 | `04_fenologiya.py` | silliqlash, faol sikllar, mavsum bo'yicha faol davr, `suv_boshi_ndvi`/`suv_oxiri_ndvi` | tayyor |
| 05 | `05_eksport.py` | ET jamoasi uchun jadval + Tableau uchun uzun format | keyingi |

Qarorlar va jarayon jurnali: **[qarorlar/](qarorlar/README.md)** · To'liq ishga tushirish yo'riqnomasi: **[docs/ISHGA_TUSHIRISH.md](docs/ISHGA_TUSHIRISH.md)**.

## Muhitni yoqish (uchta yo'l)

**A. Eng oson — `run.bat`** (conda sozlanmagan bo'lsa ham ishlaydi; VS Code PowerShell yoki cmd da):
```
cd D:\Tasks\ekin_fenologiya
.\run.bat scripts\01_geom_tayyorlash.py --tuman "Jomboy tumani"
```
Quyidagi buyruqlarda `python` o'rniga `.\run.bat` yozing.

**B. Doimiy — PowerShell uchun conda ni bir marta sozlash** (`conda` "не распознано" xatosi chiqsa):
```
& "$env:LOCALAPPDATA\miniconda3\Scripts\conda.exe" init powershell
```
Terminalni yopib qayta oching. "Выполнение сценариев отключено" xatosi chiqsa, bir marta:
```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Keyin `conda activate fenologiya` ishlaydi.

**C. VS Code** — `Ctrl+Shift+P` → *Python: Select Interpreter* → `fenologiya`; yangi ochilgan terminal muhitni o'zi yoqadi.

## Ko'p tuman: `pipeline.py` (tavsiya etiladi)

Har tuman uchun 01 → 02 → 03 ni ketma-ket bajaradi. **Davom ettiradi**: natija fayli bor qadam o'tkazib yuboriladi —
run to'xtasa (internet, kompyuter o'chsa), xuddi shu buyruqni qayta bering. Bir tuman xato bersa keyingisiga o'tadi,
oxirida xulosa chiqaradi. Jurnal: `logs\pipeline_*.log`, holat: `logs\holat.csv`.
```
.\run.bat pipeline.py royxat                                   # barcha tumanlar, holati, taxminiy vaqt
.\run.bat pipeline.py royxat --viloyat "Samarqand viloyati"
.\run.bat pipeline.py indeks --viloyat "Samarqand viloyati"    # butun viloyat
.\run.bat pipeline.py indeks --tuman "Urgut tumani" "Tayloq tumani"
.\run.bat pipeline.py indeks --hammasi                         # hamma tuman (bir necha o'n soat)
```
`--ishchi N` — parallel oqimlar (standart 6), `--qayta` — bor natijalarni ham qaytadan hisoblash.
Tavsiya: viloyatma-viloyat, kechasi yoki dam olish kunlari ishga tushiring. 4 viloyatni 4 ta terminalda parallel
ishlatish mumkin (katta viloyatlarga `--ishchi 4` — xotira uchun); kompyuter uxlab qolmasin.

**04 — fenologiya** (03 tayyor tumanlar uchun, tuman boshiga bir necha soniya):
```
.\run.bat pipeline.py fenologiya --hammasi
.\run.bat scripts\03b_grafik.py --tuman "Jomboy tumani"         # tekshirish grafiklari (silliq chiziq + faol oraliq)
```
Natija: `data\natija\fenologiya_<tuman>.parquet` — har kontur: `faol`, `boshi_sana`, `oxiri_sana`, `suv_boshi_ndvi`,
`suv_oxiri_ndvi`, `yorliq_mos`, `ishonch` va boshq. (qaror 0010).

## Ishga tushirish tartibi (bitta tuman, qadamma-qadam)

Muhit yoqilgan terminalda (yoki `python` o'rniga `.\run.bat`):
```
cd D:\Tasks\ekin_fenologiya
```
1. Tekshiruvlar (bir necha soniya):
```
python tests\test_indeks.py
python tests\test_bufer.py
```
2. Konturlarni tayyorlash (~30 s) → `data\kirish\konturlar_jomboy_tumani.gpkg`
```
python scripts\01_geom_tayyorlash.py --tuman "Jomboy tumani"
```
3. Sahnalarni qidirish (~5 s) → `data\oraliq\sahnalar_jomboy_tumani.json`
```
python scripts\02_stac_qidiruv.py --tuman "Jomboy tumani"
```
4. Indeks vaqt qatori (Jomboy, fevral–oktyabr: ~15 daqiqa) → `data\oraliq\qator_jomboy_tumani.parquet`
```
python scripts\03_indeks_qator.py --tuman "Jomboy tumani" --ishchi 6
```
Har qadam o'z oraliq faylini qaytadan yozadi. Davr, bulut chegarasi, bufer — `config\sozlamalar.yaml` da.
`--ishchi` — parallel o'qish oqimlari (internet sekin bo'lsa kamaytiring).
Bir nechta tuman: `01` ga `--tuman "A tumani" "B tumani"` yoki `--hammasi`; `02` va `03` har tuman uchun alohida.

## Manba tanlovi — tezlik testi (2026-11-05, ishxona PC, Jomboy bo'lagi ~6 mln piksel)

| | AWS Earth Search | Planetary Computer |
|---|---|---|
| STAC qidiruv | ~1 s | ~1.6 s |
| 10 m kanal (qizil) | **5–7.5 s** | 11–16.5 s |
| 20 m kanal (SCL) | 0.8–1.9 s | 0.4–0.5 s |

Ma'lumotning asosiy hajmi 10 m kanallar → **AWS ~2 baravar tez**; asosiy manba `aws`. Bitta oqim bilan o'lchangan,
parallel o'qishda tezlik oshadi. Jurnallar: `logs/test_tezlik_*.json`.

Eslatma: `gis_pro` muhitida numpy DLL nosozligi bor (matplotlib va `rasterio.windows.from_bounds` da
`0xc06d007f`) — shuning uchun bu loyiha alohida `fenologiya` muhitida ishlaydi.

## Muhit
```
conda env create -f env/environment.yml
conda activate fenologiya
```
