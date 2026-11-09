"""
Suv ichish oylari (05) — konturlar GPKG ida FAQAT suv_boshi / suv_oxiri (va qayta belgilangan Paxta uchun mavsum)
ustunlari yangilanadi. Geometriya, boshqa ustunlar, fid, uniqueid o'zgarmaydi: kirish GPKG nusxalanadi va nusxada
SQL UPDATE qilinadi. Qoidalar: config/suv_oylari.yaml.

Ishlatish: scripts/05_suv_oylari.py yoki notebooks/suv_oylari.ipynb
"""
import os, shutil, sqlite3, datetime
import numpy as np, pandas as pd, yaml
from . import sozlama as S

MAVSUMLAR = ["Birlamchi ekin", "Ikkilamchi ekin", "Mavsumiy ekin"]


def yaml_oqi(*q):
    with open(S.yol(*q), encoding="utf-8") as f:
        return yaml.safe_load(f)


def sozlamalar():
    """(cfg, zona_map): suv_oylari.yaml va (viloyat, tuman) → zona."""
    cfg = yaml_oqi("config", "suv_oylari.yaml")
    zm = {(v, t): z for v, zz in yaml_oqi("config", "zonalar.yaml").items() for z, tl in zz.items() for t in tl}
    return cfg, zm


def standart_kirish():
    return os.path.join(os.path.dirname(S.kirish_yoli(S.yuklash())), "ekin_yerlar_qisqa.gpkg")


def oqi(gpkg):
    """Atributlar (geometriyasiz). Mavsum ustuni `mavsum` yoki `season` → df.mavsum. Qaytaradi (df, mc)."""
    c = sqlite3.connect(f"file:{gpkg}?mode=ro", uri=True)
    cols = {r[1] for r in c.execute('PRAGMA table_info("ekin_yerlar")')}
    mc = "mavsum" if "mavsum" in cols else "season"
    df = pd.read_sql(f'SELECT uniqueid, viloyat, tuman, turi, {mc} AS mavsum, maydon, suv_boshi, suv_oxiri '
                     f'FROM ekin_yerlar', c)
    c.close()
    return df, mc


def geom_oqi(gpkg, mc):
    """Mavsumli konturlar geometriyasi bilan (uniqueid, viloyat, turi, mavsum, geometry)."""
    import pyogrio
    G = pyogrio.read_dataframe(gpkg, layer="ekin_yerlar", columns=["uniqueid", "viloyat", "turi", mc],
                               where=f"{mc} IN ('Birlamchi ekin', 'Ikkilamchi ekin', 'Mavsumiy ekin')")
    return G.rename(columns={mc: "mavsum"})


def nomlarni_tekshir(df, cfg, zm):
    """yaml dagi ekin/zona nomi ma'lumotda yo'q bo'lsa — ogohlantirish matnlari ro'yxati."""
    bor = set(df.turi.dropna())
    nomlar = {t for blok in [cfg["hammasi"], *cfg.get("viloyat", {}).values(), *cfg.get("zona", {}).values()]
              for m in blok.values() for t in m if t != "_boshqa"}
    nomlar |= set((cfg.get("paxta_ikkilamchi") or {}).get("ostidagi", []))
    xab = []
    if nomlar - bor:
        xab.append(f"suv_oylari.yaml dagi ekin nomlari ma'lumotda yo'q: {sorted(nomlar - bor)}")
    if set(cfg.get("zona", {})) - set(zm.values()):
        xab.append(f"suv_oylari.yaml dagi zona zonalar.yaml da yo'q: {sorted(set(cfg['zona']) - set(zm.values()))}")
    return xab


def jadval_oylari(df, cfg, zm):
    """Har qator uchun jadvaldagi (boshi, oxiri): zona → viloyat → hammasi; ekin turi → _boshqa."""
    def top(blok, mav, tur):
        m = (blok or {}).get(mav) or {}
        return m.get(tur, m.get("_boshqa"))
    nat = {}
    for vil, tm, mav, tur in df[["viloyat", "tuman", "mavsum", "turi"]].drop_duplicates().itertuples(index=False):
        if not isinstance(mav, str):
            continue
        z = zm.get((vil, tm))
        v = (top(cfg.get("zona", {}).get(z), mav, tur) if z else None) \
            or top(cfg.get("viloyat", {}).get(vil), mav, tur) or top(cfg["hammasi"], mav, tur)
        if v is None:
            raise ValueError(f"suv_oylari.yaml da '{mav}' uchun qiymat yo'q (hammasi → _boshqa)")
        nat[(vil, tm, mav, tur)] = v
    k = list(zip(df.viloyat, df.tuman, df.mavsum, df.turi))
    b = np.array([nat.get(x, (np.nan, np.nan))[0] for x in k], float)
    o = np.array([nat.get(x, (np.nan, np.nan))[1] for x in k], float)
    return b, o


def juftlar(G, chap, ong):
    """chap va ong mavsum konturlarining kesishgan juftlari: kesishma (m2, 3857) va har ikkisining ulushi, IoU,
    geometriya aynan tengligi (shapely.equals)."""
    import geopandas as gpd, shapely
    A = G[G.mavsum.isin(chap)]; B = G[G.mavsum.isin(ong)]
    j = gpd.sjoin(A[["uniqueid", "mavsum", "turi", "geometry"]],
                  B[["uniqueid", "turi", "geometry"]].rename(columns={"uniqueid": "uid_b", "turi": "turi_b"}),
                  predicate="intersects")
    ga = j.geometry.values
    gb = B.set_index("uniqueid").geometry.loc[j.uid_b].values
    ki = shapely.area(shapely.intersection(ga, gb))
    sa, sb = shapely.area(ga), shapely.area(gb)
    return pd.DataFrame({"uniqueid": j.uniqueid.values, "mavsum": j.mavsum.values, "turi": j.turi.values,
                         "uid_b": j.uid_b.values, "turi_b": j.turi_b.values, "ki": ki,
                         "ulush_a": ki / sa, "ulush_b": ki / sb, "iou": ki / (sa + sb - ki),
                         "teng": shapely.equals(ga, gb)})


def birlamchi_boglash(G, min_ulush):
    """Har Ikkilamchi/Mavsumiy kontur uchun shu daladagi Birlamchi (eng katta kesishma). Bitta dala: kesishma
    konturlardan birining maydonining ≥ min_ulush qismi."""
    j = juftlar(G, ["Ikkilamchi ekin", "Mavsumiy ekin"], ["Birlamchi ekin"])
    j = j[(j.ulush_a >= min_ulush) | (j.ulush_b >= min_ulush)]
    return j.sort_values("ki", ascending=False).drop_duplicates("uniqueid").reset_index(drop=True)


def hisobla(df, G, cfg, zm, log=print):
    """df ga ustunlar qo'shadi: yangi_mavsum, b, o (yangi suv oylari). Qoidalar tartibi:
    1) Paxta (Mavsumiy) Ozuqa/Bug'doy ustida → Ikkilamchi ekin; ostidagi Birlamchi → paxta_ikkilamchi.birlamchi
    2) jadval: Birlamchi ekin turi bo'yicha, Ikkilamchi 7-10, Mavsumiy 3-10
    3) bitta dala: Ikkilamchi/Mavsumiy Birlamchi tugagan oydan keyin → ketma_ket.oxiri gacha"""
    df = df.copy()
    df["yangi_mavsum"] = df.mavsum
    kk = cfg.get("ketma_ket") or {}
    L = birlamchi_boglash(G, kk.get("min_ulush", 0.5))
    ix = pd.Series(df.index, index=df.uniqueid)

    pi = cfg.get("paxta_ikkilamchi")
    ub = []
    if pi:
        m = (L.mavsum == "Mavsumiy ekin") & (L.turi == "Paxta") & L.turi_b.isin(pi["ostidagi"])
        up, ub = L.uniqueid[m].unique(), L.uid_b[m].unique()
        df.loc[ix[up].values, "yangi_mavsum"] = "Ikkilamchi ekin"
        L.loc[m, "mavsum"] = "Ikkilamchi ekin"
        log(f"Paxta {list(pi['ostidagi'])} ustida → Ikkilamchi ekin: {len(up)} kontur "
            f"({df.maydon[ix[up].values].sum():,.0f} ga); ostidagi Birlamchi: {len(ub)} kontur")

    tmp = df.assign(mavsum=df.yangi_mavsum)
    df["b"], df["o"] = jadval_oylari(tmp, cfg, zm)
    if pi and len(ub):
        df.loc[ix[ub].values, ["b", "o"]] = pi["birlamchi"]

    if kk:
        bo = df.o.values[ix[L.uid_b].values]
        r = ix[L.uniqueid].values
        df.loc[r, "b"] = bo + 1
        df.loc[r, "o"] = kk.get("oxiri", 10)
        for mav, g in L.assign(b=bo + 1).groupby("mavsum"):
            log(f"{mav}: {len(g)} / {(df.yangi_mavsum == mav).sum()} kontur Birlamchidan keyin — boshi: "
                f"{g.b.astype(int).value_counts().sort_index().to_dict()}")
    return df, L


def oy_matn(b, o):
    return "—" if pd.isna(b) else f"{int(b)}-{int(o)}"


def ozgarish_jadvali(df):
    d = df[df.mavsum.notna()].copy()
    d["eski"] = [oy_matn(b, o) for b, o in zip(d.suv_boshi, d.suv_oxiri)]
    d["yangi"] = [oy_matn(b, o) for b, o in zip(d.b, d.o)]
    T = (d.groupby(["viloyat", "mavsum", "yangi_mavsum", "turi", "eski", "yangi"])
         .agg(kontur=("uniqueid", "size"), maydon_ga=("maydon", "sum")).reset_index())
    T["maydon_ga"] = T.maydon_ga.round().astype(int)
    return T.sort_values(["viloyat", "yangi_mavsum", "maydon_ga"], ascending=[True, True, False])


def gpkg_yangila(src, dst, df, mc):
    """src → dst nusxa; nusxada suv_boshi, suv_oxiri va (o'zgargan bo'lsa) mavsum ustuni yangilanadi."""
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("chiqish kirish bilan bir xil bo'lmasin")
    shutil.copy2(src, dst)
    c = sqlite3.connect(dst)
    # GPKG rtree triggerlari ST_* funksiyalarni nomlaydi; fid/geom o'zgarmagani uchun chaqirilmaydi,
    # lekin trigger tayyorlanishi uchun ro'yxatda bo'lishi kerak.
    for fn in ("ST_IsEmpty", "ST_MinX", "ST_MaxX", "ST_MinY", "ST_MaxY"):
        c.create_function(fn, 1, lambda g: None)
    d = df[df.mavsum.notna()]
    c.execute("CREATE TEMP TABLE yangi (uniqueid TEXT PRIMARY KEY, b INTEGER, o INTEGER, m TEXT)")
    c.executemany("INSERT INTO yangi VALUES (?,?,?,?)",
                  [(u, None if pd.isna(b) else int(b), None if pd.isna(o) else int(o), m)
                   for u, b, o, m in d[["uniqueid", "b", "o", "yangi_mavsum"]].itertuples(index=False)])
    hisob = {}
    for (tn,) in c.execute("SELECT table_name FROM gpkg_contents").fetchall():
        cols = {r[1] for r in c.execute(f'PRAGMA table_info("{tn}")')}
        if not {"uniqueid", "suv_boshi", "suv_oxiri"} <= cols:
            continue
        setm = f', "{mc}" = y.m' if mc in cols else ""
        cur = c.execute(f'UPDATE "{tn}" SET suv_boshi = y.b, suv_oxiri = y.o{setm} FROM yangi y '
                        f'WHERE "{tn}".uniqueid = y.uniqueid')
        hisob[tn] = cur.rowcount
        c.execute("UPDATE gpkg_contents SET last_change = ? WHERE table_name = ?",
                  (datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"), tn))
    c.commit(); c.close()
    return hisob


def faqat_suv_farqi(asl, yangi, ruxsat=("suv_boshi", "suv_oxiri", "season", "mavsum")):
    """Tekshiruv: asl va yangi GPKG da `ruxsat` dan boshqa ustun (geometriya ham) farq qiladigan qatorlar soni."""
    c = sqlite3.connect(f"file:{yangi}?mode=ro", uri=True)
    c.execute(f"ATTACH 'file:{asl}?mode=ro' AS a")
    nat = {}
    for (tn,) in c.execute("SELECT table_name FROM gpkg_contents").fetchall():
        cols = [r[1] for r in c.execute(f'PRAGMA table_info("{tn}")') if r[1] not in ruxsat]
        q = ",".join(f'"{x}"' for x in cols)
        nat[tn] = c.execute(f'SELECT count(*) FROM (SELECT {q} FROM "{tn}" EXCEPT SELECT {q} FROM a."{tn}")').fetchone()[0]
    c.close()
    return nat


def chegara_solishtir(G):
    """Birlamchi va Ikkilamchi konturlar chegarasi: har kontur uchun qarama-qarshi mavsumdagi eng mos juft (IoU).
    Toifa: 'aynan bir xil' (geometriya teng) / 'deyarli bir xil' (IoU ≥ 0.99) / 'farq qiladi' (bitta dalada,
    lekin chegara boshqa) / 'jufti yo'q' (≥50% kesishadigan qarama-qarshi kontur yo'q)."""
    j = juftlar(G, ["Birlamchi ekin"], ["Ikkilamchi ekin"])
    j = j[(j.ulush_a >= 0.5) | (j.ulush_b >= 0.5)]

    def toifa(t, i):
        return np.select([t, i >= 0.99, i > 0], ["aynan bir xil", "deyarli bir xil", "farq qiladi"], "jufti yo'q")

    natija = []
    for tomon, uid, mav in [("Birlamchi", "uniqueid", "Birlamchi ekin"), ("Ikkilamchi", "uid_b", "Ikkilamchi ekin")]:
        e = j.sort_values(["teng", "iou"], ascending=False).drop_duplicates(uid)
        jj = j.groupby(uid).size()
        K = G.loc[G.mavsum == mav, ["uniqueid", "viloyat", "turi"]].copy()
        m = e.set_index(uid)
        K["iou"] = K.uniqueid.map(m.iou).fillna(0).values
        K["teng"] = K.uniqueid.map(m.teng).fillna(False).astype(bool).values
        K["juft_soni"] = K.uniqueid.map(jj).fillna(0).astype(int).values
        K["toifa"] = toifa(K.teng.values, K.iou.values)
        K["tomon"] = tomon
        natija.append(K)
    return pd.concat(natija, ignore_index=True)
