# zonal — hosildorlik rasterini konturlarga yozish

Qishloq xo'jaligidan kelgan hosildorlik rasterlari (piksel = s/ga) har bir kontur
uchun **bitta ustunga — `hosil`** — o'rtacha (mean) qilib yoziladi.

- Bug'doy konturiga faqat bug'doy rasteri, paxta konturiga faqat paxta rasteri.
- Boshqa ekinlarda `hosil` bo'sh (NULL) qoladi.
- Piksel olinadi: markazi kontur ichida bo'lsa. Nodata (255) va 0 olinmaydi.
- Kirish fayli o'zgarmaydi, natija yangi faylga yoziladi.

## Ishlatish

1. `zonal/hosil.yaml` ni oching va yo'llarni tekshiring:
   - `kirish` — oxirgi ekin fayli (gpkg),
   - `chiqish` — yangi fayl nomi,
   - `rasterlar` — ekin → viloyat → raster yo'li.
2. Loyiha ildizidan ishga tushiring:

```bash
.\run.bat zonal\hosil_zonal.py
```

Yo'llarni buyruqda ham berish mumkin (yaml dagini almashtiradi):

```bash
.\run.bat zonal\hosil_zonal.py --kirish D:\...\eski.gpkg --chiqish D:\...\yangi.gpkg
```

Natija fayli bor bo'lsa skript to'xtaydi; ustiga yozish uchun `--ustiga-yoz` qo'shing.

## Natija

- `<chiqish>.gpkg` — hamma eski ustunlar + `hosil` (s/ga, verguldan keyin 2 xona).
- `<chiqish>_hosil_hisobot.csv` — ekin × viloyat: kontur soni, nechtasiga yozildi,
  o'rtacha / min / max hosil.

Bo'sh qolgan bug'doy/paxta konturlari — raster qoplamaydigan joylar yoki
raster ichida faqat nodata bo'lgan konturlar.

## Yangi raster qo'shish

`hosil.yaml` dagi `rasterlar` bo'limiga qator qo'shing. Ekin nomi `turi`
ustunidagi qiymat bilan, viloyat nomi `viloyat` ustunidagi qiymat bilan aynan
bir xil bo'lishi kerak (masalan `"Bug'doy"`, `"Farg'ona viloyati"`).
