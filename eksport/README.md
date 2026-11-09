# eksport

## 1. v5: v4 + fermer ma'lumoti + oylik NDVI (`v5_birlashtirish.py`)

`ekin_yerlar_qisqa_v4.gpkg` ga `uniqueid` bo'yicha qo'shiladi:

- `ekin_yerlar_yakuniy.gpkg` dan fermer ma'lumoti, nomi o'zgartirib: `f_name → full_name`,
  `f_inn → tax_number` (ro'yxat skript boshidagi `FERMER_USTUNLAR` da);
- `data/oraliq/qator_<tuman>.parquet` dan NDVI: `ndvi_02 … ndvi_10` (oy bo'yicha o'rtacha).
  Faqat toza kunlar (dalaning ≥ 50% i toza, 04 bilan bir xil); kuzatuv bo'lmagan oy — bo'sh.

v4 ustunlari va geometriyasi o'zgarmaydi. Natija: `D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v5.gpkg`.

```bash
.\run.bat eksport\v5_birlashtirish.py
.\run.bat eksport\v5_birlashtirish.py --tuman "Jomboy tumani" --chiqish D:\temp\test_v5.gpkg   (tez test)
```

Keyin v5 ni shp ga bo'lish (pastda):

```bash
.\run.bat eksport\viloyat_shp.py D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v5.gpkg
```

## 2. gpkg ni viloyatlar bo'yicha shapefile larga ajratish (`viloyat_shp.py`)

Ekin yerlari gpkg faylidagi konturlar `viloyat` ustuni bo'yicha ajratiladi va
har bir viloyat alohida shp fayliga yoziladi. Ustunlar, CRS va geometriya
o'zgarmaydi; matn UTF-8 (`.cpg` bilan), kirish fayli o'zgarmaydi.

## Ishlatish

Loyiha ildizidan, oxirgi gpkg faylini berib:

```bash
.\run.bat eksport\viloyat_shp.py D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v4.gpkg
```

Fayl berilmasa, skript yo'lni so'raydi.

Natija kirish fayli turgan papkada, `<fayl nomi>_viloyatlar_shp` papkasida:

```
ekin_yerlar_qisqa_v4_viloyatlar_shp/
  fargona_viloyati.shp      (+ .shx .dbf .prj .cpg)
  qashqadaryo_viloyati.shp
  samarqand_viloyati.shp
  sirdaryo_viloyati.shp
```

Qo'shimcha parametrlar:

- `--chiqish PAPKA` — boshqa papkaga yozish;
- `--ustiga-yoz` — shp lar bor bo'lsa ham qayta yozish (aks holda skript to'xtaydi);
- `--viloyat-ustuni`, `--qatlam` — ustun/qatlam nomi boshqacha bo'lsa;
- `--nom ESKI=YANGI` — shp da yana bir ustunni boshqa nom bilan yozish (bir necha marta berish mumkin);
- `--nomlamasdan` — standart nomlash ishlatilmasin, ustunlar gpkg dagi nomi bilan qoladi.

Standart nomlash (skript boshidagi `SHP_NOMLAR`; gpkg o'zgarmaydi, faqat shp da):

| gpkg | shp |
|---|---|
| `uniqueid` | `unique_id` |
| `season` | `mavsum` |
| `turi` | `crop` |
| `hosil` | `yield` |

Nomlashdan keyin ikki ustun bir xil nomga tushsa, skript to'xtaydi.

Oxirida yozilgan konturlar soni kirishdagi bilan solishtiriladi.
Shp cheklovlari: ustun nomi 10 belgigacha, fayl 2 GB gacha — skript ikkalasini ham ogohlantiradi.
