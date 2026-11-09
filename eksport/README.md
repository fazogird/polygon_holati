# eksport — gpkg ni viloyatlar bo'yicha shapefile larga ajratish

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
- `--viloyat-ustuni`, `--qatlam` — ustun/qatlam nomi boshqacha bo'lsa.

Oxirida yozilgan konturlar soni kirishdagi bilan solishtiriladi.
Shp cheklovlari: ustun nomi 10 belgigacha, fayl 2 GB gacha — skript ikkalasini ham ogohlantiradi.
