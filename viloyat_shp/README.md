# viloyat_shp

Viloyat shp fayllari bilan ishlash (har bir viloyat alohida). Bu papkadagi skriptlar
loyihaning boshqa modullariga (`src`, `scripts`, `eksport`, `zonal`) ta'sir qilmaydi.

## `atribut_otkazish.py` — to'liq atributli shp dan ma'lumot o'tkazish

Kirish/chiqish skript boshidagi **FOYDALANUVCHI SOZLAMALARI** blokida qo'lda yoziladi:

| O'zgaruvchi | Ma'nosi |
|---|---|
| `KIRISH` | ma'lumot qabul qiladigan viloyat shp (o'zgarmaydi) |
| `MANBA` | to'liq atributli shp (faqat o'qiladi, o'zgarmaydi) |
| `CHIQISH` | natija shp (yangi fayl) |
| `USTUNLAR` | `ID → kontur_raq`, `LVL_0_name → real_name`, `LVL_1_name → real_n1`, `LVL_2_name → real_n2` |
| `FERMER_BIZDA` / `FERMER_MANBADA` | `full_name` faqat bo'sh joyda `fermer_nom` dan to'ldiriladi |
| `MIN_ULUSH` | moslik chegarasi (standart 0.5) |
| `ULUSH_USTUNI` | moslik ulushi ustuni (`mos_ulush`), kerak bo'lmasa `None` |

```bash
.\run.bat viloyat_shp\atribut_otkazish.py
```

### Mos ekin yerga mos ma'lumot qanday o'tkaziladi

Ikki faylda umumiy kalit ustun yo'q. Proyeksiyalari ham har xil: bizniki EPSG:3857,
manbaniki UTM 42N (EPSG:32642). Shuning uchun konturlar joylashuvi bo'yicha (fazoviy) moslanadi:

1. **Eng katta ustma-ust tushish.** Har bir bizning konturimiz uchun manbadagi eng katta maydon
   bilan ustma-ust tushgan kontur olinadi. Hisob metrda, UTM da qilinadi.
2. **Xavfsizlik chegarasi.** Bu ustma-ust qism bizning kontur maydonining kamida 50% ini
   egallashi shart (`MIN_ULUSH = 0.5`). Kam bo'lsa, hech narsa o'tkazilmaydi va katak bo'sh
   qoladi. Bu boshqa konturning ma'lumoti adashib tushmasligi uchun.
3. **Teng nomzodlar.** Ikki nomzod teng bo'lsa, natija har safar bir xil chiqadi: manbadagi
   qator tartibi bo'yicha birinchisi olinadi.
4. **`mos_ulush` ustuni.** Har bir konturga moslik ulushi (0–1) yoziladi. QGIS/ArcGIS da
   `mos_ulush < 0.9` ni filtrlab, shubhali joylarni ko'rib chiqish mumkin. Kerak bo'lmasa
   `ULUSH_USTUNI = None` qiling.
5. **O'zgarmaslik tekshiruvi.** Manba faqat o'qiladi. Skript boshida va oxirida MANBA va KIRISH
   fayllarining xeshini solishtiradi — ikkalasi o'zgarmasligi shart. Natijaning geometriyasi va
   konturlar soni kirish bilan bir xilligi ham tekshiriladi.

Natijaning geometriyasi, CRS i va qator tartibi kirish bilan bir xil qoladi.

### Misol: Sirdaryo viloyati (2026-11-09)

Sozlamalar:

```python
KIRISH  = r"D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v5_viloyatlar_shp\sirdaryo_viloyati.shp"
MANBA   = r"D:\Tasks\level_otkazish\LVL_6ekin\LVL_6ekin.shp"
CHIQISH = r"D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v6_viloyatlar_shp\sirdaryo_viloyati.shp"
```

Natija:

| Ko'rsatkich | Qiymat |
|---|---|
| Jami kontur | 42 876 |
| Ma'lumot o'tdi (`mos_ulush` ≥ 0.5) | 42 523 |
| — shundan manba konturi ichida ≥ 99% | 41 056 |
| Bo'sh qoldi | 353 (152 tasi hech qaysi manba konturiga tegmaydi, 201 tasida ustma-ust qism 50% dan kam) |
| `full_name` bo'sh edi | 26 040 |
| — `fermer_nom` dan to'ldi | 20 264 |
| — bo'sh qoldi (manbada ham fermer nomi yo'q) | 5 776 |
| `full_name` da bor qiymatlar | 16 836 — o'zgarmadi |

- **Mustaqil tekshiruv:** har bir kontur ichidan nuqta olinib, u qaysi manba konturiga
  tushishi alohida usul bilan topildi. 41 068 ta konturdan 41 067 tasida qiymatlar aynan mos
  keldi; 1 tasida nuqta manba konturi chegarasiga tushib qoldi, nomuvofiqlik topilmadi.
- 36 ta konturda ikki manba konturi deyarli teng ulushda (masalan 0.55 / 0.45) va qiymatlari
  har xil — bular ikki manba konturi chegarasida yotadi; kattaroq ulushli konturning
  ma'lumoti berildi.
