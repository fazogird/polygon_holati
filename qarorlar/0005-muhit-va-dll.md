# 0005 — Alohida `fenologiya` muhiti; DLL yo'li

**Sana:** 2026-11-05 · **Holat:** qabul qilingan

## Kontekst
`gis_pro` va `aws_et` muhitlarida `numpy.linalg`, `rasterio.windows.from_bounds` va `matplotlib` Windows xatosi
`0xc06d007f` bilan qulagan. Sabab: muhitning `python.exe` si **`conda activate` qilinmasdan** chaqirilganda
`Library\bin` PATH da bo'lmaydi va boshqa joydagi mos kelmaydigan BLAS/LAPACK DLL yuklanadi.
Muhitlar buzilmagan — DLL papkalari PATH ga qo'shilganda hammasi ishladi.

## Qaror
1. Loyiha alohida **`fenologiya`** muhitida ishlaydi (`env/environment.yml`); boshqa muhitlarga tegilmaydi.
2. Har bir skript boshida `fenologiya.muhit` import qilinadi — u numpy dan oldin muhitning DLL papkalarini PATH ga
   qo'shadi va GDAL/PROJ yo'llarini o'rnatadi. Shunda `conda activate` qilingan-qilinmaganidan qat'i nazar ishlaydi.

## Oqibat
`birlamchi_ikkilamchi` loyihasining `.bat` fayllari ham python ni activate qilmasdan chaqiradi — u yerdagi skriptlar
bu funksiyalarni ishlatmagani uchun ta'sir qilmagan, lekin kelajakda shu tuzatishni u yerga ham qo'shish tavsiya etiladi.
