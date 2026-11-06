# 0011 — Vizualizatsiya: Streamlit + DuckDB + pydeck dashboard (lokal, bepul)

**Sana:** 2026-11-06 · **Holat:** qabul qilingan

## Kontekst
Indeks qatorlari tumanlar bo'yicha parquet'da (`qator_<tuman>.parquet`, 70 tuman, ~32 mln qator). Bitta konturni
Excel'da (QGIS orqali eksport) ko'rish mumkin, lekin minglab kontur bilan Excel qotadi (1 048 576 qator chegarasi,
hamma narsa xotiraga). Tableau pullik. Kerak: tuman xaritasida konturni bosib uning vaqt qatorini ko'rish,
tuman bo'yicha umumiy manzara, 04 natijasini (faol oraliq, yorliq mosligi) tekshirish.

## Qaror
`scripts/dashboard.py` — **Streamlit** ilovasi, ishga tushirish `dashboard.bat` (http://localhost:8501).
- **DuckDB** parquet'ni to'g'ridan-to'g'ri so'raydi: xotiraga faqat kerakli ustun / sana / kontur olinadi
  (kontur bosish ~1 s, tuman almashtirish birinchi marta ~6 s, keyin kesh).
- **pydeck (deck.gl)** — konturlar GPU'da chiziladi (tuman boshiga 12–23 ming poligon), bosish → tanlov.
- **plotly** — vaqt qatori (toza / bulutli nuqtalar, silliq NDVI, 04 faol oraliq tasmasi).
- Alohida **`fenologiya_viz`** muhiti (`env/environment_viz.yml`): pipeline ishlab turgan `fenologiya` muhitiga
  paket o'rnatish ishlayotgan jarayonlarning DLL'larini almashtirib yuborishi mumkin edi.
- Qaror 0001 ga mos: server faqat `localhost`'da, Streamlit telemetriyasi o'chiq (`.streamlit/config.toml`).
  Fon xarita plitkalari (Carto / Esri) internetdan keladi — ular faqat xarita oynasi koordinatasini so'raydi.

## Ko'rib chiqilgan muqobillar
- **Apache Superset / Metabase** — bepul BI (Tableau'ga yaqin), lekin Docker/server kerak, kontur xaritasi va
  "bosib vaqt qatori" oqimi zaif. Ko'p foydalanuvchili tashkiliy dashboard kerak bo'lsa — keyingi bosqich.
- **Kepler.gl** — millionlab poligonni tez chizadi, lekin bitta kontur vaqt qatori yo'q.
- **QGIS + Data Plotly** — parquet'ni ochadi, lekin katta hajmda sekin, jamoaga tarqatish noqulay.

## Texnik eslatmalar
- pydeck JSON'ni `indent=2` bilan yozadi — Jomboy (15 ming kontur) 17 MB bo'lardi; `IxchamDeck` ixcham JSON
  yozadi (~6 MB), koordinatalar 5 xona (~1 m), geometriya 1.5 m ga soddalashtiriladi.
- Xarita tanlovi chizishdan oldin `st.session_state` dan o'qiladi — bosishda ikkinchi qayta ishga tushirish yo'q.
- `?tuman=<slug>` havolasi tumanni to'g'ridan-to'g'ri ochadi.

## Ochiq
- Tarmoqda boshqa xodimlarga ochish (`--server.address 0.0.0.0`) — qaror 0001 bo'yicha alohida kelishiladi.
- 30 mingdan ortiq konturli tumanlarda brauzer yuklamasi — kerak bo'lsa MVT/GeoParquet plitkalariga o'tish.
