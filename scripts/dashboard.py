"""
Dashboard — tuman xaritasi (konturlar) + kontur bo'yicha NDVI / EVI2 / NDMI vaqt qatori.

Ishga tushirish (alohida `fenologiya_viz` muhiti — pipeline muhitiga tegmaydi):
    .\\dashboard.bat
Brauzerda http://localhost:8501 ochiladi.

- Tuman tanlanadi -> xaritada konturlar (rang: sana bo'yicha indeks, maksimal NDVI, ekin turi, fenologiya ...).
- Konturni bosish -> o'ngda uning vaqt qatori (nuqta shaffofligi = dalaning toza ulushi, bulutli kunlar kulrang x),
  04 natijasi bo'lsa silliq NDVI va topilgan faol oraliq.
- "Solishtirish" rejimida bir nechta konturni ustma-ust ko'rish mumkin.

Parquet fayllarni DuckDB o'qiydi: xotiraga faqat kerakli ustun / sana / kontur olinadi, shuning uchun millionlab
qatorda ham tez ishlaydi (Excel'dagi 1 048 576 qator chegarasi yo'q).
Ma'lumot kompyuterdan chiqmaydi: server faqat localhost'da, Streamlit telemetriyasi o'chiq (.streamlit/config.toml).
Fon xarita plitkalari internetdan yuklanadi — ular faqat xarita oynasi koordinatasini so'raydi, kontur emas.
"""
import os, sys, glob, re, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401  (numpy dan oldin: DLL / GDAL_DATA)
import numpy as np, pandas as pd, duckdb, pyogrio
import pydeck as pdk
from pydeck.bindings.json_tools import default_serialize
import plotly.graph_objects as go
import streamlit as st
from fenologiya import sozlama as S

CFG = S.yuklash()
FEN = CFG["fenologiya"]
MIN_UL = float(FEN["min_toza_ulush"])
YIL = CFG["davr"]["boshi"][:4]
MAX_SOL = 8                                    # solishtirishda eng ko'p kontur

# ----------------------------------------------------------------------------------------------- ranglar
RDYLGN = ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee08b", "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850", "#006837"]
VIRIDIS = ["#440154", "#482878", "#3e4989", "#31688e", "#26828e", "#1f9e89", "#35b779", "#6ece58", "#b5de2b", "#fde725"]
TOIFA = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#76B7B2", "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F",
         "#1F77B4", "#8C564B", "#17BECF"]
QATIY_RANG = {"Birlamchi ekin": "#59A14F", "Ikkilamchi ekin": "#F28E2B", "Mavsumiy ekin": "#4E79A7",
              "mos": "#59A14F", "farqli": "#F28E2B", "faol_emas": "#9a9a9a",
              "yuqori": "#59A14F", "orta": "#EDC948", "past": "#E15759"}
INDEKS_RANG = {"ndvi": "#1a9850", "evi2": "#2F5597", "ndmi": "#8E44AD"}
KULRANG = [190, 190, 190, 110]


class IxchamDeck(pdk.Deck):
    """pydeck JSON ni indent=2 bilan yozadi — 15 ming kontur ~17 MB bo'ladi; ixcham JSON ~3 baravar kichik."""

    def to_json(self):
        return json.dumps(self, sort_keys=True, default=default_serialize, separators=(",", ":"))


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def uzluksiz_rang(v, vmin, vmax, palitra, alfa=210):
    """Qiymatlar -> [[r,g,b,a], ...]; NaN -> kulrang."""
    v = np.asarray(v, dtype="float64")
    t = np.nan_to_num(np.clip((v - vmin) / (vmax - vmin), 0, 1))
    st_ = np.linspace(0, 1, len(palitra)); p = np.array([_rgb(c) for c in palitra], dtype="float64")
    rgb = np.stack([np.interp(t, st_, p[:, i]) for i in range(3)], axis=1).round().astype(int)
    out = np.concatenate([rgb, np.full((len(v), 1), alfa)], axis=1).tolist()
    for i in np.where(np.isnan(v))[0]:
        out[i] = KULRANG
    return out


def toifa_rang(s):
    """Kategoriya -> rang (ko'pdan kamga; yarlig'i ma'lum bo'lsa o'z rangi). Qaytaradi: ranglar, legenda {nom: hex}."""
    s = s.fillna("—").astype(str)
    tartib = s.value_counts().index.tolist()
    leg, j = {}, 0
    for t in tartib:
        if t in QATIY_RANG:
            leg[t] = QATIY_RANG[t]
        elif t == "—":
            leg[t] = "#bebebe"
        else:
            leg[t] = TOIFA[j % len(TOIFA)] if j < len(TOIFA) else "#7f7f7f"; j += 1
    m = {k: _rgb(c) + [210] for k, c in leg.items()}
    return [m[x] for x in s], leg


# ----------------------------------------------------------------------------------------------- ma'lumot
def _pq(p):
    return "'" + p.replace("\\", "/").replace("'", "''") + "'"


def sql(q):
    con = duckdb.connect()
    try:
        return con.execute(q).df()
    finally:
        con.close()


def qator_yoli(sl):
    return S.yol("data", "oraliq", f"qator_{sl}.parquet")


def fen_yoli(sl):
    return S.yol("data", "natija", f"fenologiya_{sl}.parquet")


def silliq_yoli(sl):
    return S.yol("data", "oraliq", f"silliq_{sl}.parquet")


def _id_toza(ids):
    return [i for i in ids if re.fullmatch(r"[0-9A-Za-z_\-]+", str(i))]


@st.cache_data(show_spinner=False)
def tumanlar():
    rows = []
    for f in sorted(glob.glob(S.yol("data", "oraliq", "qator_*.parquet"))):
        sl = os.path.basename(f)[len("qator_"):-len(".parquet")]
        g = S.yol("data", "kirish", f"konturlar_{sl}.gpkg")
        if not os.path.exists(g):
            continue
        try:
            a = pyogrio.read_dataframe(g, layer="konturlar", read_geometry=False, max_features=1,
                                       columns=["viloyat", "tuman"])
            vil, tum = str(a.viloyat.iloc[0]), str(a.tuman.iloc[0])
        except Exception:
            vil, tum = "?", sl
        rows.append(dict(slug=sl, viloyat=vil, tuman=tum))
    return pd.DataFrame(rows, columns=["slug", "viloyat", "tuman"])


@st.cache_data(show_spinner="Konturlar o'qilmoqda…", max_entries=6)
def konturlar(sl):
    """Atributlar, xarita uchun poligonlar (lon/lat, soddalashtirilgan) va boshlang'ich ko'rinish."""
    k = pyogrio.read_dataframe(S.yol("data", "kirish", f"konturlar_{sl}.gpkg"), layer="konturlar",
                               columns=["uniqueid", "turi", "mavsum", "maydon"])
    k = k[k.geometry.notna() & ~k.geometry.is_empty]
    k["geometry"] = k.geometry.simplify(1.5)                 # UTM, metr — ko'rinishga ta'sir qilmaydi, hajm kamayadi
    g = k.to_crs(4326)
    uid, poly = [], []
    for u, geom in zip(g.uniqueid.values, g.geometry.values):
        parts = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for p in parts:
            rings = [p.exterior, *p.interiors]
            poly.append([np.round(np.asarray(r.coords)[:, :2], 5).tolist() for r in rings])   # ~1 m
            uid.append(u)
    c = g.geometry.representative_point()
    attrs = pd.DataFrame({"uniqueid": g.uniqueid.values, "turi": g.turi.values, "mavsum": g.mavsum.values,
                          "maydon": g.maydon.values, "lon": c.x.values, "lat": c.y.values})
    x0, y0, x1, y1 = g.total_bounds
    lat = (y0 + y1) / 2
    span = max(x1 - x0, (y1 - y0) / max(math.cos(math.radians(lat)), 0.2), 1e-4)
    view = dict(longitude=(x0 + x1) / 2, latitude=lat, zoom=float(np.clip(math.log2(560 * 360 / (512 * span)), 5, 16)))
    return attrs, pd.DataFrame({"uniqueid": uid, "polygon": poly}), view


@st.cache_data(show_spinner="Kontur statistikasi (DuckDB)…", max_entries=6)
def kontur_stat(sl):
    toza = f"toza_piksel >= {MIN_UL} * jami_piksel"
    return sql(f"""
        SELECT uniqueid,
               count(*) FILTER (WHERE {toza})                 AS kuzatuv,
               count(*)                                       AS jami_kun,
               max(ndvi) FILTER (WHERE {toza})                AS max_ndvi,
               arg_max(sana, ndvi) FILTER (WHERE {toza})      AS max_sana,
               median(ndvi) FILTER (WHERE {toza})             AS median_ndvi
        FROM read_parquet({_pq(qator_yoli(sl))}) GROUP BY uniqueid""")


@st.cache_data(show_spinner=False, max_entries=6)
def fenologiya(sl):
    p = fen_yoli(sl)
    return pd.read_parquet(p) if os.path.exists(p) else None


@st.cache_data(show_spinner=False, max_entries=6)
def sanalar(sl):
    return sql(f"""
        SELECT sana, count(*) AS n, avg(toza_piksel::DOUBLE / nullif(jami_piksel, 0)) AS ulush
        FROM read_parquet({_pq(qator_yoli(sl))}) GROUP BY sana ORDER BY sana""")


@st.cache_data(show_spinner=False, max_entries=64)
def sana_qiymat(sl, sana, indeks):
    return sql(f"""
        SELECT uniqueid, {indeks} AS qiymat, toza_piksel::DOUBLE / nullif(jami_piksel, 0) AS ulush
        FROM read_parquet({_pq(qator_yoli(sl))}) WHERE sana = TIMESTAMP '{pd.Timestamp(sana):%Y-%m-%d %H:%M:%S}'""")


@st.cache_data(show_spinner=False, max_entries=256)
def qator(sl, ids):
    ids = _id_toza(ids)
    if not ids:
        return pd.DataFrame()
    q = ", ".join(f"'{i}'" for i in ids)
    d = sql(f"""SELECT * FROM read_parquet({_pq(qator_yoli(sl))}) WHERE uniqueid IN ({q}) ORDER BY uniqueid, sana""")
    d["ulush"] = (d.toza_piksel / d.jami_piksel.replace(0, np.nan)).clip(0, 1)
    return d


@st.cache_data(show_spinner=False, max_entries=256)
def silliq(sl, ids):
    p, ids = silliq_yoli(sl), _id_toza(ids)
    if not os.path.exists(p) or not ids:
        return None
    q = ", ".join(f"'{i}'" for i in ids)
    return sql(f"SELECT * FROM read_parquet({_pq(p)}) WHERE uniqueid IN ({q}) ORDER BY uniqueid, sana")


@st.cache_data(show_spinner="Tuman bo'yicha o'rtacha egri chiziqlar…", max_entries=24)
def guruh_egri(sl, guruh, indeks, attrs):
    con = duckdb.connect()
    try:
        con.register("k", attrs[["uniqueid", guruh]].rename(columns={guruh: "guruh"}))
        return con.execute(f"""
            SELECT k.guruh, q.sana, median(q.{indeks}) AS qiymat, count(*) AS n
            FROM read_parquet({_pq(qator_yoli(sl))}) q JOIN k USING (uniqueid)
            WHERE q.toza_piksel >= {MIN_UL} * q.jami_piksel
            GROUP BY ALL ORDER BY q.sana""").df()
    finally:
        con.close()


@st.cache_data(show_spinner="Barcha tumanlar ro'yxati…")
def umumiy_jadval(t):
    import pyarrow.parquet as pq
    rows = []
    for r in t.itertuples():
        d = dict(viloyat=r.viloyat, tuman=r.tuman)
        try:
            d["kontur"] = pyogrio.read_info(S.yol("data", "kirish", f"konturlar_{r.slug}.gpkg"),
                                            layer="konturlar")["features"]
        except Exception:
            d["kontur"] = None
        try:
            d["yozuv"] = pq.ParquetFile(qator_yoli(r.slug)).metadata.num_rows
        except Exception:
            d["yozuv"] = None
        d["yozuv/kontur"] = round(d["yozuv"] / d["kontur"], 1) if d["yozuv"] and d["kontur"] else None
        f = fen_yoli(r.slug)
        d["fenologiya"] = os.path.exists(f)
        if d["fenologiya"]:
            try:
                vc = pd.read_parquet(f, columns=["yorliq_mos"]).yorliq_mos.value_counts()
                for c in ("mos", "farqli", "faol_emas"):
                    d[c] = int(vc.get(c, 0))
            except Exception:
                pass
        rows.append(d)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------- yordamchi
def legenda_uzluksiz(nom, vmin, vmax, palitra, fmt="{:.2f}"):
    g = ", ".join(palitra)
    st.markdown(
        f"<div style='font-size:12px;margin:2px 0 6px'>{nom}"
        f"<div style='height:10px;border-radius:3px;background:linear-gradient(to right,{g});margin:3px 0'></div>"
        f"<div style='display:flex;justify-content:space-between'><span>{fmt.format(vmin)}</span>"
        f"<span>{fmt.format(vmax)}</span></div><span style='opacity:.7'>kulrang — ma'lumot yo'q / bulutli</span></div>",
        unsafe_allow_html=True)


def legenda_toifa(leg, n_max=14):
    items = list(leg.items())[:n_max]
    html = "".join(f"<span style='display:inline-flex;align-items:center;margin:0 10px 4px 0'>"
                   f"<span style='width:11px;height:11px;border-radius:2px;background:{c};margin-right:4px'></span>{k}</span>"
                   for k, c in items)
    if len(leg) > n_max:
        html += f"<span style='opacity:.7'>… yana {len(leg) - n_max}</span>"
    st.markdown(f"<div style='font-size:12px;line-height:1.5'>{html}</div>", unsafe_allow_html=True)


def oy_kun(x):
    return "—" if pd.isna(x) else pd.Timestamp(x).strftime("%d.%m")


def baza_xarita(nom):
    if nom == "Sun'iy yo'ldosh (Esri)":
        return {"version": 8,
                "sources": {"esri": {"type": "raster", "tileSize": 256, "maxzoom": 18,
                                     "tiles": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
                                     "attribution": "Tiles © Esri"}},
                "layers": [{"id": "esri", "type": "raster", "source": "esri"}]}
    return {"Yorug'": pdk.map_styles.CARTO_LIGHT, "Qorong'i": pdk.map_styles.CARTO_DARK}.get(nom)


def tanlovga_qosh(uid, solishtir):
    t = st.session_state.setdefault("tanlangan", [])
    if solishtir:
        if uid not in t:
            t.append(uid)
            del t[:-MAX_SOL]
    else:
        t[:] = [uid]


# ----------------------------------------------------------------------------------------------- grafik
def vaqt_qatori_grafigi(sl, ids, indekslar, attrs, fen, bulutli_korsat):
    q = qator(sl, tuple(ids))
    sil = silliq(sl, tuple(ids)) if "ndvi" in indekslar else None
    fig = go.Figure()
    fig.add_vrect(x0=f"{YIL}-03-01", x1=f"{YIL}-06-01", fillcolor="#E3F1E5", line_width=0, layer="below", opacity=0.6)
    fig.add_vrect(x0=f"{YIL}-06-01", x1=f"{YIL}-11-01", fillcolor="#FBE5D6", line_width=0, layer="below", opacity=0.6)
    kop = len(ids) > 1
    chiziq = {"ndvi": "solid", "evi2": "dash", "ndmi": "dot"}
    for j, uid in enumerate(ids):
        d = q[q.uniqueid == uid]
        if d.empty:
            continue
        a = attrs.loc[attrs.uniqueid == uid]
        nom = f"{a.turi.iloc[0]} · {uid[:6]}" if len(a) else uid[:8]
        rang_k = TOIFA[j % len(TOIFA)]
        toza, bulut = d[d.ulush >= MIN_UL], d[d.ulush < MIN_UL]
        for ind in indekslar:
            rang = rang_k if kop else INDEKS_RANG[ind]
            sil_bor = ind == "ndvi" and sil is not None and (sil.uniqueid == uid).any()
            fig.add_trace(go.Scatter(
                x=toza.sana, y=toza[ind], mode="lines+markers" if not sil_bor else "markers",
                name=f"{ind.upper()} — {nom}" if kop else ind.upper(), legendgroup=f"{uid}{ind}",
                line=dict(color=rang, width=1.3, dash=chiziq[ind]),
                marker=dict(size=7, color=rang, opacity=None,
                            line=dict(width=0)),
                customdata=np.stack([toza.ulush * 100, toza.toza_piksel, toza.jami_piksel], axis=1),
                hovertemplate=f"<b>{ind.upper()}</b> %{{y:.3f}}<br>%{{x|%d.%m.%Y}}<br>toza: %{{customdata[0]:.0f}}%"
                              f" (%{{customdata[1]}}/%{{customdata[2]}} piksel)<extra>{nom}</extra>"))
            if bulutli_korsat and len(bulut):
                fig.add_trace(go.Scatter(
                    x=bulut.sana, y=bulut[ind], mode="markers", showlegend=False, legendgroup=f"{uid}{ind}",
                    marker=dict(symbol="x-thin", size=7, line=dict(width=1.5, color="#9a9a9a")),
                    customdata=bulut.ulush * 100,
                    hovertemplate=f"<b>{ind.upper()}</b> %{{y:.3f}} — bulutli<br>%{{x|%d.%m.%Y}}<br>"
                                  f"toza: %{{customdata:.0f}}%<extra>{nom}</extra>"))
            if sil_bor:
                s = sil[sil.uniqueid == uid]
                fig.add_trace(go.Scatter(x=s.sana, y=s.ndvi_silliq, mode="lines", legendgroup=f"{uid}{ind}",
                                         name=f"silliq NDVI — {nom}" if kop else "silliq NDVI",
                                         line=dict(color=rang if kop else "#C00000", width=2.4),
                                         hovertemplate="silliq %{y:.3f}<br>%{x|%d.%m}<extra></extra>"))
        if fen is not None:                                   # 04: faol oraliq — pastda tasma
            f = fen[fen.uniqueid == uid]
            if len(f) and f.faol.iloc[0] == 1 and pd.notna(f.boshi_sana.iloc[0]):
                y0 = -0.16 - 0.035 * j
                fig.add_shape(type="rect", x0=f.boshi_sana.iloc[0], x1=f.oxiri_sana.iloc[0], y0=y0, y1=y0 + 0.025,
                              fillcolor=rang_k if kop else "#C00000", line_width=0, opacity=0.9)
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=30, b=10), hovermode="closest",
                      legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)),
                      yaxis=dict(range=[-0.2 - 0.035 * max(len(ids) - 1, 0), 1.0], title=None, gridcolor="#e5e5e5"),
                      xaxis=dict(range=[CFG["davr"]["boshi"], CFG["davr"]["oxiri"]], tickformat="%d.%m",
                                 gridcolor="#e5e5e5"),
                      plot_bgcolor="white")
    return fig, q


def kontur_kartochka(uid, attrs, stat, fen):
    a = attrs[attrs.uniqueid == uid]
    s = stat[stat.uniqueid == uid]
    if a.empty:
        st.warning(f"{uid} bu tumanda topilmadi"); return
    a = a.iloc[0]
    st.markdown(f"**{a.turi}** · {a.mavsum} · {a.maydon:.2f} ga  \n<span style='font-size:12px;opacity:.7'>{uid}</span>",
                unsafe_allow_html=True)
    c = st.columns(3)
    if len(s):
        s = s.iloc[0]
        c[0].metric("Toza kuzatuv", f"{int(s.kuzatuv)} / {int(s.jami_kun)}")
        c[1].metric("Maks. NDVI", "—" if pd.isna(s.max_ndvi) else f"{s.max_ndvi:.2f}", oy_kun(s.max_sana),
                    delta_color="off", delta_arrow="off")
        c[2].metric("Median NDVI", "—" if pd.isna(s.median_ndvi) else f"{s.median_ndvi:.2f}")
    if fen is not None:
        f = fen[fen.uniqueid == uid]
        if len(f):
            f = f.iloc[0]
            if f.faol == 1:
                suv = f"{int(f.suv_boshi_ndvi)}–{int(f.suv_oxiri_ndvi)}" if pd.notna(f.suv_boshi_ndvi) else "—"
                qat = f"{int(f.suv_boshi_qatiy)}–{int(f.suv_oxiri_qatiy)}" if pd.notna(f.suv_boshi_qatiy) else "—"
                c = st.columns(3)
                c[0].metric("Faol oraliq", f"{oy_kun(f.boshi_sana)}–{oy_kun(f.oxiri_sana)}", f"{f.faol_kun:.0f} kun",
                            delta_color="off", delta_arrow="off")
                c[1].metric("Suv oylari (NDVI)", suv, f"qat'iy: {qat}", delta_color="off", delta_arrow="off")
                c[2].metric("Yorliq", f.yorliq_mos, f"ishonch: {f.ishonch}", delta_color="off", delta_arrow="off")
            else:
                st.info(f"Bu mavsumda faol emas (yorliq: {f.yorliq_mos}, ishonch: {f.ishonch})")
            st.caption(f"Sikllar: {f.sikllar or '—'} · cho'qqi {oy_kun(f.chuqqi_sana)} "
                       f"(NDVI {f.chuqqi_ndvi:.2f}) · asos NDVI {f.asos_ndvi:.2f}")


# ----------------------------------------------------------------------------------------------- sahifa
st.set_page_config(page_title="Ekin fenologiyasi", page_icon="🌾", layout="wide")
st.markdown("<style>.block-container{padding-top:1.2rem;padding-bottom:1rem} "
            "[data-testid='stMetricValue']{font-size:1.15rem}</style>", unsafe_allow_html=True)

T = tumanlar()
if T.empty:
    st.error("data/oraliq/qator_*.parquet (va mos data/kirish/konturlar_*.gpkg) topilmadi."); st.stop()

with st.sidebar:
    st.header("🌾 Ekin fenologiyasi")
    qp = T[T.slug == st.query_params.get("tuman", "")]           # ?tuman=jomboy_tumani — havola bilan ochish
    vils = sorted(T.viloyat.unique())
    vil = st.selectbox("Viloyat", vils, index=vils.index(qp.viloyat.iloc[0]) if len(qp) else 0)
    tt = T[T.viloyat == vil].sort_values("tuman")
    tl = tt.tuman.tolist()
    tuman = st.selectbox("Tuman", tl, index=tl.index(qp.tuman.iloc[0]) if len(qp) and qp.tuman.iloc[0] in tl else 0)
    sl = tt.loc[tt.tuman == tuman, "slug"].iloc[0]
    st.query_params["tuman"] = sl
    if st.button("↻ Fayllarni qayta o'qish", help="Pipeline yangi tuman yozgan bo'lsa"):
        st.cache_data.clear(); st.rerun()

try:
    attrs, poly, view0 = konturlar(sl)
    stat = kontur_stat(sl)
    sana_df = sanalar(sl)
except Exception as e:                                         # fayl hali yozilayotgan bo'lishi mumkin
    st.error(f"{tuman}: o'qib bo'lmadi — {e}"); st.stop()
fen = fenologiya(sl)
attrs = attrs.merge(stat, on="uniqueid", how="left")
if fen is not None:
    attrs = attrs.merge(fen[["uniqueid", "yorliq_mos", "ishonch", "faol_kun", "sikl_soni", "chuqqi_sana"]],
                        on="uniqueid", how="left")

if st.session_state.get("_tuman") != sl:                       # tuman almashdi — tanlov tozalanadi
    st.session_state.update(_tuman=sl, tanlangan=[], _oxirgi=None, _view=None)

with st.sidebar:
    st.subheader("Xarita rangi")
    rejimlar = ["Indeks — tanlangan sana", "Maksimal NDVI", "Toza kuzatuvlar soni", "Ekin turi", "Mavsum"]
    if fen is not None:
        rejimlar += ["Yorliq mosligi (04)", "Faol kunlar (04)", "Sikl soni (04)", "Cho'qqi oyi (04)", "Ishonch (04)"]
    rejim = st.selectbox("Rang", rejimlar, label_visibility="collapsed")
    indeks, sana = "ndvi", None
    if rejim.startswith("Indeks"):
        indeks = st.radio("Indeks", ["ndvi", "evi2", "ndmi"], horizontal=True, format_func=str.upper)
        opts = sana_df.sana.tolist()
        ul = dict(zip(sana_df.sana, sana_df.ulush))
        yoz = sana_df[sana_df.sana.dt.month.between(5, 8)]               # boshlang'ich: yozdagi eng toza kun
        yoz = yoz if len(yoz) else sana_df
        eng_toza = yoz.loc[yoz.ulush.idxmax(), "sana"] if len(yoz) else None
        sana = st.select_slider("Sana", options=opts, value=eng_toza, key=f"sana_{sl}",
                                format_func=lambda x: f"{pd.Timestamp(x):%d.%m} · toza {ul[x] * 100:.0f}%")
    st.subheader("Filtr")
    turlar = attrs.turi.value_counts().index.tolist()
    f_turi = st.multiselect("Ekin turi", turlar, placeholder="hammasi")
    f_mavsum = st.multiselect("Mavsum", sorted(attrs.mavsum.dropna().unique()), placeholder="hammasi")
    f_yorliq = (st.multiselect("Yorliq mosligi (04)", ["mos", "farqli", "faol_emas"], placeholder="hammasi")
                if fen is not None else [])
    mmax = float(np.ceil(attrs.maydon.max() or 1))
    f_maydon = st.slider("Maydon, ga", 0.0, mmax, (0.0, mmax), step=0.1)
    st.subheader("Xarita")
    baza = st.selectbox("Fon", ["Yorug'", "Sun'iy yo'ldosh (Esri)", "Qorong'i"], label_visibility="collapsed")
    shaffof = st.slider("Kontur shaffofligi", 0.1, 1.0, 0.8, 0.05)

# --- filtr
m = attrs.maydon.between(*f_maydon)
if f_turi:
    m &= attrs.turi.isin(f_turi)
if f_mavsum:
    m &= attrs.mavsum.isin(f_mavsum)
if f_yorliq:
    m &= attrs.yorliq_mos.isin(f_yorliq)
A = attrs[m].copy()

# --- rang
alfa = int(255 * shaffof)
leg_toifa, leg_uz = None, None
if rejim.startswith("Indeks"):
    v = sana_qiymat(sl, sana, indeks)
    A = A.merge(v, on="uniqueid", how="left")
    val = A.qiymat.where(A.ulush >= MIN_UL)
    vmin, vmax = (-0.2, 0.6) if indeks == "ndmi" else (0.0, 0.9)
    A["rang"] = uzluksiz_rang(val, vmin, vmax, RDYLGN, alfa)
    A["izoh"] = [f"{indeks.upper()} {pd.Timestamp(sana):%d.%m}: " + ("—" if pd.isna(q) else f"{q:.2f}")
                 + ("" if pd.isna(u) else f" (toza {u * 100:.0f}%)") for q, u in zip(A.qiymat, A.ulush)]
    leg_uz = (f"{indeks.upper()}, {pd.Timestamp(sana):%d.%m.%Y}", vmin, vmax, RDYLGN, "{:.1f}")
elif rejim == "Maksimal NDVI":
    A["rang"] = uzluksiz_rang(A.max_ndvi, 0.1, 0.95, RDYLGN, alfa)
    A["izoh"] = [f"maks NDVI {x:.2f} ({oy_kun(s)})" if pd.notna(x) else "maks NDVI —" for x, s in zip(A.max_ndvi, A.max_sana)]
    leg_uz = ("Maksimal NDVI (toza kunlar)", 0.1, 0.95, RDYLGN, "{:.1f}")
elif rejim == "Toza kuzatuvlar soni":
    top = float(max(A.kuzatuv.max() or 1, 1))
    A["rang"] = uzluksiz_rang(A.kuzatuv, 0, top, VIRIDIS, alfa)
    A["izoh"] = [f"toza kuzatuv: {int(k) if pd.notna(k) else 0}" for k in A.kuzatuv]
    leg_uz = ("Toza kuzatuvlar soni", 0, top, VIRIDIS, "{:.0f}")
elif rejim == "Faol kunlar (04)":
    A["rang"] = uzluksiz_rang(A.faol_kun.where(A.faol_kun > 0), 0, 270, VIRIDIS, alfa)
    A["izoh"] = [f"faol: {k:.0f} kun" if pd.notna(k) else "faol emas" for k in A.faol_kun]
    leg_uz = ("Faol kunlar", 0, 270, VIRIDIS, "{:.0f}")
else:
    col = {"Ekin turi": "turi", "Mavsum": "mavsum", "Yorliq mosligi (04)": "yorliq_mos", "Sikl soni (04)": "sikl_soni",
           "Cho'qqi oyi (04)": "chuqqi_sana", "Ishonch (04)": "ishonch"}[rejim]
    s = A[col]
    if col == "chuqqi_sana":
        s = s.dt.month.map(lambda x: f"{int(x):02d}-oy", na_action="ignore")
    elif col == "sikl_soni":
        s = s.map(lambda x: f"{int(x)} sikl", na_action="ignore")
    rr, leg_toifa = toifa_rang(s)
    A["rang"] = [r[:3] + [alfa] for r in rr]
    A["izoh"] = s.fillna("—").astype(str)
    if col in ("chuqqi_sana", "sikl_soni"):
        leg_toifa = dict(sorted(leg_toifa.items()))

A["maydon_t"] = A.maydon.round(2)
D = poly.merge(A[["uniqueid", "turi", "mavsum", "maydon_t", "rang", "izoh"]], on="uniqueid", how="inner")

# ----------------------------------------------------------------------------------------------- sahifa tanasi
tab1, tab2, tab3 = st.tabs(["🗺️ Xarita va kontur", "📈 Tuman bo'yicha", "📋 Barcha tumanlar"])

with tab1:
    chap, ong = st.columns([1.25, 1], gap="medium")
    with chap:
        top = st.columns([1.2, 1.4, 1])
        top[0].markdown(f"**{tuman}** — {len(A):,} / {len(attrs):,} kontur".replace(",", " "))
        izla = top[1].text_input("uniqueid", placeholder="uniqueid bo'yicha qidirish", label_visibility="collapsed")
        solishtir = top[2].toggle("Solishtirish", help=f"Bosilgan konturlar qo'shilib boradi (eng ko'p {MAX_SOL})")
        if izla and izla.strip() != st.session_state.get("_izla"):
            st.session_state["_izla"] = izla.strip()
            hit = attrs[attrs.uniqueid.str.startswith(izla.strip())]
            if len(hit):
                h = hit.iloc[0]
                tanlovga_qosh(h.uniqueid, solishtir)
                st.session_state["_view"] = dict(longitude=float(h.lon), latitude=float(h.lat), zoom=15.5)
            else:
                st.warning("Bunday uniqueid topilmadi")

        # xaritadagi bosish: vidjet holati chizishdan OLDIN o'qiladi — qo'shimcha qayta ishga tushirish shart emas
        try:
            objs = st.session_state[f"xarita_{sl}"]["selection"]["objects"].get("konturlar", [])
        except Exception:
            objs = []
        uid = objs[0].get("uniqueid") if objs else None
        if uid and uid != st.session_state.get("_oxirgi"):
            st.session_state["_oxirgi"] = uid
            tanlovga_qosh(uid, solishtir)

        tanl = st.session_state.get("tanlangan", [])
        vs = st.session_state.get("_view") or view0
        sel = poly[poly.uniqueid.isin(tanl)]
        layers = [pdk.Layer("PolygonLayer", data=D, id="konturlar", get_polygon="polygon", get_fill_color="rang",
                            get_line_color=[40, 40, 40, 90], line_width_min_pixels=0.4, stroked=True, filled=True,
                            pickable=True, auto_highlight=True, highlight_color=[255, 255, 255, 120])]
        if len(sel):
            layers.append(pdk.Layer("PolygonLayer", data=sel, id="tanlangan", get_polygon="polygon", filled=False,
                                    stroked=True, get_line_color=[0, 229, 255, 255], line_width_min_pixels=3))
        deck = IxchamDeck(layers=layers, map_style=baza_xarita(baza),
                        initial_view_state=pdk.ViewState(**vs, pitch=0, bearing=0),
                        tooltip={"html": "<b>{turi}</b><br/>{mavsum} · {maydon_t} ga<br/>{izoh}",
                                 "style": {"fontSize": "12px", "padding": "6px 8px"}})
        st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object", key=f"xarita_{sl}", height=600)
        if leg_uz:
            legenda_uzluksiz(*leg_uz)
        if leg_toifa:
            legenda_toifa(leg_toifa)

    with ong:
        tanl = st.session_state.get("tanlangan", [])
        if not tanl:
            st.info("Xaritada konturni bosing (yoki uniqueid bo'yicha qidiring) — shu yerda uning NDVI / EVI2 / NDMI "
                    "vaqt qatori chiqadi.")
            st.caption(f"Tumanda {len(sana_df)} ta Sentinel-2 kuni, {len(attrs):,} kontur. ".replace(",", " ") +
                       ("04 fenologiya natijasi bor." if fen is not None else "04 fenologiya hali hisoblanmagan."))
        else:
            c = st.columns([2, 1])
            indekslar = c[0].multiselect("Indekslar", ["ndvi", "evi2", "ndmi"], default=["ndvi"],
                                         format_func=str.upper, label_visibility="collapsed")
            bulutli = c[1].checkbox("Bulutli kunlar", value=True, help=f"toza ulush < {MIN_UL:.0%} — kulrang x")
            if len(tanl) == 1:
                kontur_kartochka(tanl[0], attrs, stat, fen)
            else:
                cc = st.columns([3, 1])
                cc[0].caption(f"{len(tanl)} kontur solishtirilmoqda")
                if cc[1].button("Tozalash"):
                    st.session_state["tanlangan"] = []; st.rerun()
            if indekslar:
                fig, q = vaqt_qatori_grafigi(sl, tanl, indekslar, attrs, fen, bulutli)
                st.plotly_chart(fig, config={"displaylogo": False})
                st.caption("Fon: yashil — Birlamchi (3–5), sariq — Ikkilamchi (6–10). Nuqta — toza kun "
                           f"(dalaning ≥{MIN_UL:.0%} i bulutsiz), x — bulutli. "
                           + ("Qizil chiziq — silliq NDVI, pastdagi tasma — 04 topgan faol oraliq."
                              if fen is not None else ""))
                st.download_button("⬇ CSV (tanlangan konturlar)", q.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"qator_{sl}_{len(tanl)}_kontur.csv", mime="text/csv")
            if len(tanl) > 1:
                with st.expander("Tanlangan konturlar"):
                    for u in tanl:
                        kontur_kartochka(u, attrs, stat, fen); st.divider()

with tab2:
    c = st.columns([1, 1, 2])
    guruhlar = {"Ekin turi": "turi", "Mavsum": "mavsum"}
    if fen is not None:
        guruhlar["Yorliq mosligi (04)"] = "yorliq_mos"
    gnom = c[0].selectbox("Guruh", list(guruhlar))
    gind = c[1].selectbox("Indeks ", ["ndvi", "evi2", "ndmi"], format_func=str.upper)
    g = guruhlar[gnom]
    soni = A[g].value_counts()
    eng = c[2].multiselect("Guruhlar", soni.index.tolist(), default=soni.index[:6].tolist(),
                           help="Filtrlangan konturlar bo'yicha (chap paneldagi filtr amal qiladi)")
    if eng:
        ge = guruh_egri(sl, g, gind, A[A[g].isin(eng)][["uniqueid", g]].reset_index(drop=True))
        fig = go.Figure()
        fig.add_vrect(x0=f"{YIL}-03-01", x1=f"{YIL}-06-01", fillcolor="#E3F1E5", line_width=0, layer="below", opacity=0.6)
        fig.add_vrect(x0=f"{YIL}-06-01", x1=f"{YIL}-11-01", fillcolor="#FBE5D6", line_width=0, layer="below", opacity=0.6)
        _, leg = toifa_rang(A[g])
        for gr in eng:
            d = ge[(ge.guruh == gr) & (ge.n >= 10)]
            d = d.assign(s=d.qiymat.rolling(3, center=True, min_periods=1).median())
            fig.add_trace(go.Scatter(x=d.sana, y=d.s, mode="lines", name=f"{gr} ({soni.get(gr, 0)})",
                                     line=dict(color=leg.get(str(gr), "#7f7f7f"), width=2.2), customdata=d.n,
                                     hovertemplate=f"{gr}<br>%{{x|%d.%m}}: %{{y:.3f}}<br>%{{customdata}} kontur<extra></extra>"))
        fig.update_layout(height=480, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="white",
                          legend=dict(orientation="h", y=-0.12), yaxis=dict(gridcolor="#e5e5e5", title=f"median {gind.upper()}"),
                          xaxis=dict(range=[CFG["davr"]["boshi"], CFG["davr"]["oxiri"]], tickformat="%d.%m", gridcolor="#e5e5e5"))
        st.plotly_chart(fig, config={"displaylogo": False})
        st.caption("Har sana uchun guruhdagi toza konturlar indeksining medianasi (3 nuqtali surilma median); "
                   "10 tadan kam kontur bo'lgan sanalar tashlab ketilgan.")
    c = st.columns(2)
    with c[0]:
        st.markdown("**Kontur soni va maydoni**")
        jad = A.groupby(g).agg(kontur=("uniqueid", "size"), maydon_ga=("maydon", "sum"),
                               median_toza_kuzatuv=("kuzatuv", "median"), median_maks_ndvi=("max_ndvi", "median"))
        st.dataframe(jad.sort_values("kontur", ascending=False).round(2))
    with c[1]:
        if fen is not None:
            st.markdown("**04: mavsum × yorliq mosligi**")
            st.dataframe(pd.crosstab(A.mavsum, A.yorliq_mos, margins=True, margins_name="jami"))
        st.markdown("**Sentinel-2 kunlari (tuman bo'yicha toza ulush)**")
        fb = go.Figure(go.Bar(x=sana_df.sana, y=sana_df.ulush * 100, marker_color="#4E79A7",
                              hovertemplate="%{x|%d.%m.%Y}: %{y:.0f}%<extra></extra>"))
        fb.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white",
                         yaxis=dict(range=[0, 100], title="toza %", gridcolor="#e5e5e5"), xaxis=dict(tickformat="%d.%m"))
        st.plotly_chart(fb, config={"displaylogo": False})

with tab3:
    st.caption("Diskdagi fayllar bo'yicha: kontur soni (gpkg), indeks yozuvlari (qator parquet), 04 natijasi bor-yo'qligi.")
    U = umumiy_jadval(T)
    st.dataframe(U, hide_index=True, height=560)
    cc = st.columns(4)
    cc[0].metric("Tuman", len(U))
    cc[1].metric("Kontur", f"{int(U.kontur.fillna(0).sum()):,}".replace(",", " "))
    cc[2].metric("Indeks yozuvlari", f"{int(U.yozuv.fillna(0).sum()):,}".replace(",", " "))
    cc[3].metric("04 fenologiya", f"{int(U.fenologiya.sum())} / {len(U)}")
