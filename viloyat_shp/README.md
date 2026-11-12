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
| `HISOBOT` | Excel hisobot; `None` — `CHIQISH` yonida `<nomi>_hisobot.xlsx` |
| `USTUNLAR` | `ID → kontur_raq`, `LVL_0_name → real_name`, `LVL_1_name → real_n1`, `LVL_2_name → real_n2` |
| `FERMER_BIZDA` / `FERMER_MANBADA` | `full_name` faqat bo'sh joyda `fermer_nom` dan to'ldiriladi |
| `MIN_ULUSH` | moslik chegarasi (standart 0.5) |
| `ULUSH_USTUNI` | moslik ulushi ustuni (`mos_ulush`), kerak bo'lmasa `None` |

```bash
.\run.bat viloyat_shp\atribut_otkazish.py
```

### Mos ekin yerga mos ma'lumot qanday o'tkaziladi

Ikki faylda umumiy kalit ustun yo'q. Proyeksiyalari ham har xil: bizniki EPSG:3857,
manbaniki UTM 42N (EPSG:32642). Shuning uchun konturlar joylashuvi bo'yicha (fazoviy) moslanadi.

**Muammo:** bizdagi bitta katta dala manbada ko'pincha 3–6 ta kichik konturga bo'lingan, lekin
ularning nomenklaturasi (`ID`, `LVL_*`) bir xil — nomenklatura bitta dala ichida o'zgarmaydi.
Eng katta bitta manba konturini olsak, har bir bo'lak dalaning 50% idan kam bo'lib, dala
bo'sh qolardi (masalan 0.38 + 0.21 + 0.16 + 0.13 + 0.07 + 0.06 = 1.0).

1. **Guruhlab moslash.** O'tkaziladigan qiymatlari bir xil manba konturlari bitta guruh
   hisoblanadi. Har bir bizning konturimiz uchun har bir guruhning birlashgan kesishmasi
   hisoblanadi va eng katta ulushli guruh olinadi. Hisob metrda, UTM da qilinadi.
   - **Nomenklatura:** `ID + LVL_0_name + LVL_1_name + LVL_2_name` to'rttasi birga bitta
     guruhdan olinadi — ID bir bo'lakdan, LVL boshqasidan aralashib ketmaydi.
   - **Fermer nomi:** alohida, `fermer_nom` qiymati bo'yicha guruhlanadi (bitta nomenklatura
     ichida fermer har xil bo'lishi mumkin). Faqat bo'sh `full_name` to'ldiriladi.
   - Bir-birini qoplagan manba konturlari ikki marta sanalmaydi (birlashma olinadi).
2. **Xavfsizlik chegarasi.** Guruh kesishmasi bizning kontur maydonining kamida 50% ini
   egallashi shart (`MIN_ULUSH = 0.5`). Kam bo'lsa, hech narsa o'tkazilmaydi va katak bo'sh
   qoladi. Bu boshqa konturning ma'lumoti adashib tushmasligi uchun. Eng yaqin konturni olish
   ishlatilmaydi.
3. **Teng nomzodlar.** Ikki guruh teng bo'lsa, natija har safar bir xil chiqadi: manbadagi
   qator tartibi bo'yicha birinchisi olinadi. Deyarli teng (2-guruh ≥ 90% × 1-guruh) konturlar
   hisobotning "Shubhali" varag'ida.
4. **`mos_ulush` ustuni.** Har bir konturga nomenklatura guruhining ulushi (0–1) yoziladi.
   QGIS/ArcGIS da `mos_ulush < 0.9` ni filtrlab, chegaradagi joylarni ko'rib chiqish mumkin.
   Kerak bo'lmasa `ULUSH_USTUNI = None` qiling.
5. **O'zgarmaslik tekshiruvi.** Manba faqat o'qiladi. Skript boshida va oxirida MANBA va KIRISH
   fayllarining xeshini solishtiradi — ikkalasi o'zgarmasligi shart. Natijaning geometriyasi,
   CRS i va konturlar soni kirish bilan bir xilligi ham tekshiriladi.

Natijaning geometriyasi, CRS i va qator tartibi kirish bilan bir xil qoladi.

### Excel hisobot

Har ishga tushirishda `HISOBOT` ga yoziladi (Excel da ochiq bo'lsa yozilmaydi — yopib qayta ishga tushiring):

| Varaq | Nima bor |
|---|---|
| **Umumiy** | fayllar; CRS lar (KIRISH, MANBA, moslash qaysi CRS da hisoblandi, CHIQISH); ekin yerlar soni va maydoni (ga) — KIRISH va CHIQISH da; ma'lumot o'tgan / bo'sh qolganlar soni va maydoni; tekshiruv natijalari |
| **Ustunlar** | qaysi ustundan qaysi ustunga: avval bo'sh edi, to'ldirildi, bo'sh qoldi, avvaldan bor (o'zgarmadi), foizlar |
| **Moslik** | moslik ulushi oraliqlari (≥ 0.99, 0.90–0.99, …, kesishma yo'q) bo'yicha konturlar soni; nechtasi bir nechta manba bo'lagidan yig'ilgan |
| **Tumanlar** | har tuman: kontur soni va maydoni, mos topilgan / bo'sh qolgan soni va maydoni, `full_name` to'ldirilishi |
| **Bo'sh qolganlar** | ma'lumot o'tmagan konturlar ro'yxati (FID, unique_id, tuman, maydon, sabab) |
| **Shubhali** | ikki guruh deyarli teng ulushda bo'lgan konturlar (nomenklatura va fermer nomi alohida): **Farqli ustunlar** (qaysi ustun ikki guruhda har xil, masalan `kontur_raq` yoki `kontur_raq, real_n2`), olingan va 2-guruh qiymatlari yonma-yon. "Umumiy" da farqli ustunlar bo'yicha soni |

### Shubhali dala nimani bildiradi

Bizning dala manbadagi ikki dalaning o'rtasida yotsa va ikkala guruh ulushi deyarli teng bo'lsa
(masalan 0.501 / 0.499), skript kattasini oladi va dalani "Shubhali" ga yozadi. "Farqli ustunlar"
qaysi qiymat aniq emasligini ko'rsatadi:

- **faqat `kontur_raq`** — `real_name`, `real_n1`, `real_n2` ikkala guruhda bir xil, ular aniq;
  faqat qaysi kontur raqami yozilgani ikkilanadi (dala ikki manba konturini teng bo'lib turadi).
- **`kontur_raq` + `real_*`** — nomenklatura darajasi ham har xil: shularni xaritada ko'rib chiqing.

Farg'ona misoli (2026-11-12): 22 nomenklatura shubhalisidan 16 tasi faqat `kontur_raq`,
3 tasi `kontur_raq, real_n2`, 3 tasi `kontur_raq, real_n1, real_n2`; `real_name` farqi yo'q.

### Misol: Sirdaryo viloyati (2026-11-09)

Sozlamalar:

```python
KIRISH  = r"D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v5_viloyatlar_shp\sirdaryo_viloyati.shp"
MANBA   = r"D:\Tasks\level_otkazish\LVL_6ekin\LVL_6ekin.shp"
CHIQISH = r"D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v6_viloyatlar_shp\sirdaryo_viloyati.shp"
```

Natija (guruhlab moslash):

| Ko'rsatkich | Qiymat |
|---|---|
| Jami kontur (KIRISH = CHIQISH) | 42 876 |
| Ekin yerlar maydoni (KIRISH = CHIQISH, `maydon` ustuni) | 367 834.02 ga |
| CRS: KIRISH / MANBA / moslash / CHIQISH | EPSG:3857 / EPSG:32642 / EPSG:32642 / EPSG:3857 |
| Ma'lumot o'tdi (`mos_ulush` ≥ 0.5) | 42 679 (366 808.86 ga) |
| — shundan 1 ta manba konturidan | 38 816 |
| — shundan bir nechta manba bo'lagidan yig'ilgan | 3 863 |
| — shundan `mos_ulush` ≥ 0.99 | 42 211 |
| Bo'sh qoldi | 197 — 1 025.15 ga (152 tasi hech qaysi manba konturiga tegmaydi, 45 tasi deyarli tegmaydi) |
| `full_name` bo'sh edi | 26 040 |
| — `fermer_nom` dan to'ldi | 20 336 |
| — bo'sh qoldi (manbada ham fermer nomi yo'q yoki ulush < 0.5) | 5 704 |
| `full_name` da bor qiymatlar | 16 836 — o'zgarmadi |
| Shubhali (deyarli teng 2 guruh) | nomenklatura 14, `fermer_nom` 17 |

**Avvalgi usul (eng katta bitta manba konturi) bilan solishtirish:**

| | Avvalgi usul | Guruhlab |
|---|---|---|
| Ma'lumot o'tgan kontur | 42 523 | 42 679 (+156) |
| Bo'sh qolgan | 353 (3 608.85 ga) | 197 (1 025.15 ga) |
| `full_name` to'ldirildi | 20 264 | 20 336 (+72) |
| Avval o'tgan qiymatlardan o'zgargani | — | 0 |

- Avvalgi usulda to'ldirilgan qiymatlarning birortasi o'zgarmadi — faqat bo'sh qolganlar to'ldi;
  boshqa ustunlar ham aynan bir xil.
- **Mustaqil tekshiruv (avvalgi usul):** har bir kontur ichidan nuqta olinib, u qaysi manba
  konturiga tushishi alohida usul bilan topildi. 41 068 ta konturdan 41 067 tasida qiymatlar
  aynan mos keldi; 1 tasida nuqta manba konturi chegarasiga tushib qoldi.
- Bo'sh qolgan 152 ta kontur eng yaqin manba konturidan o'rtacha (mediana) 79 m uzoqda, ko'pi
  Shirin shahrida — manbada u hudud yo'q.
