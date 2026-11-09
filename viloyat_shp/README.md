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

### Moslash qanday ishlaydi

Ikki faylda umumiy kalit yo'q, shuning uchun fazoviy moslanadi: har bir bizning konturimiz
uchun manbadagi **eng katta maydon bilan ustma-ust tushgan** kontur olinadi. Kesishma bizning
kontur maydonining `MIN_ULUSH` qismidan kam bo'lsa — hech narsa o'tkazilmaydi (adashib boshqa
konturning ma'lumoti tushmasligi uchun). Hisob metrik CRS da (manbaniki, masalan UTM 42N);
natijaning geometriyasi, CRS i va qator tartibi kirish bilan bir xil qoladi.

Skript oxirida tekshiradi: MANBA va KIRISH fayllari xeshi o'zgarmagan, natijada kontur soni va
geometriya kirish bilan bir xil.

Sirdaryo (2026-11-09): 42 876 konturdan 42 523 tasi mos (41 056 tasi ≥ 99% manba konturi
ichida); 353 tasi bo'sh qoldi; `full_name` 26 040 bo'shdan 20 264 tasi to'ldirildi.
