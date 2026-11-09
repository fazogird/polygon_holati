"""Bitta viloyat shp iga to'liq atributli shp dan ma'lumot o'tkazish (fazoviy moslash bilan).

Nima qiladi:
  1. KIRISH (bizning viloyat shp) va MANBA (to'liq atributli shp) o'qiladi.
     MANBA hech qachon o'zgartirilmaydi — skript oxirida fayllar xeshi qayta tekshiriladi.
  2. Har bir KIRISH konturi uchun MANBA dagi eng ko'p ustma-ust tushgan kontur topiladi
     (kesishma maydoni bo'yicha). Kesishma bizning kontur maydonining MIN_ULUSH qismidan
     kam bo'lsa — mos kontur yo'q deb hisoblanadi va hech narsa o'tkazilmaydi.
  3. USTUNLAR dagi ustunlar yangi nom bilan qo'shiladi (ID -> kontur_raq, ...).
  4. FERMER_BIZDA (full_name) faqat bo'sh bo'lgan joyda FERMER_MANBADA (fermer_nom) dan
     to'ldiriladi; bor qiymat o'zgarmaydi.
  5. Natija CHIQISH ga yoziladi. Geometriya, CRS, qator tartibi va boshqa ustunlar o'zgarmaydi.

Ishga tushirish (loyiha ildizidan), avval pastdagi KIRISH / MANBA / CHIQISH ni to'g'rilang:
    .\\run.bat viloyat_shp\\atribut_otkazish.py
"""

from __future__ import annotations

# =====================================================================================
#  FOYDALANUVCHI SOZLAMALARI — har bir viloyat uchun shu yerni o'zgartiring
# =====================================================================================

# Ma'lumot qabul qiladigan shp (bizning viloyat fayli). O'zgarmaydi.
KIRISH = r"D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v5_viloyatlar_shp\sirdaryo_viloyati.shp"

# Ma'lumot olinadigan to'liq atributli shp. O'zgarmaydi (faqat o'qiladi).
MANBA = r"D:\Tasks\level_otkazish\LVL_6ekin\LVL_6ekin.shp"

# Natija shp (yangi fayl; KIRISH yoki MANBA bilan bir xil bo'lishi mumkin emas).
CHIQISH = r"D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v6_viloyatlar_shp\sirdaryo_viloyati.shp"

# MANBA dan olinadigan ustunlar: {manbadagi nomi: bizdagi yangi nomi} (shp: 10 belgigacha).
USTUNLAR = {
    "ID": "kontur_raq",
    "LVL_0_name": "real_name",
    "LVL_1_name": "real_n1",
    "LVL_2_name": "real_n2",
}

# Fermer nomi: bizdagi bo'sh FERMER_BIZDA katakchalari MANBA dagi FERMER_MANBADA dan to'ldiriladi.
# To'ldirmaslik uchun ikkalasini ham None qiling.
FERMER_BIZDA = "full_name"
FERMER_MANBADA = "fermer_nom"

# Moslik chegarasi: kesishma / bizning kontur maydoni. 0.5 = kontur kamida yarmi bilan
# manba konturi ichida bo'lishi shart. Kattaroq qiymat — xavfsizroq, lekin kamroq to'ladi.
MIN_ULUSH = 0.5

# Har bir konturga moslik ulushini (0..1) yozish uchun ustun nomi; kerak bo'lmasa None.
ULUSH_USTUNI = "mos_ulush"

# CHIQISH allaqachon bor bo'lsa ustiga yozilsinmi.
USTIGA_YOZ = False

# =====================================================================================

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fenologiya import muhit  # noqa: F401,E402  (GDAL_DATA/PROJ va DLL yo'llari, numpy dan oldin)

import hashlib  # noqa: E402
import time  # noqa: E402

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyogrio  # noqa: E402
import shapely  # noqa: E402

SHP_QOSHIMCHA = (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix", ".sbn", ".sbx")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def shp_xesh(asos: Path) -> dict[str, str]:
    """shp ning hamma yon fayllari xeshi — fayl o'zgarmaganini tekshirish uchun."""
    out = {}
    for q in SHP_QOSHIMCHA:
        p = asos.with_suffix(q)
        if p.exists():
            out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def shp_ochir(asos: Path) -> None:
    for q in SHP_QOSHIMCHA:
        p = asos.with_suffix(q)
        if p.exists():
            p.unlink()


def bosh(s: pd.Series) -> pd.Series:
    """None / NaN / faqat bo'shliq — bo'sh hisoblanadi."""
    return s.isna() | s.astype(str).str.strip().eq("")


def moslash(biz: gpd.GeoSeries, manba: gpd.GeoSeries) -> pd.DataFrame:
    """Har bir `biz` konturi uchun eng katta kesishmali `manba` konturini topish.

    Ikkalasi bir CRS da (metrik) bo'lishi kerak. Natija (biz indeksi bo'yicha):
      m_qator  — manba qator raqami (-1: kesishma yo'q)
      ulush    — eng katta kesishma / biz kontur maydoni
      ulush2   — ikkinchi eng katta kesishma ulushi (0: yo'q)
      m_qator2 — ikkinchi manba qatori (-1: yo'q)
    """
    b = shapely.make_valid(biz.values)
    m = shapely.make_valid(manba.values)
    tree = shapely.STRtree(m)
    bi, mi = tree.query(b, predicate="intersects")
    a = shapely.area(shapely.intersection(b[bi], m[mi]))
    juft = pd.DataFrame({"bi": bi, "mi": mi, "a": a})
    juft = juft[juft.a > 0]
    # eng katta kesishma birinchi; teng bo'lsa — manba qator tartibi (barqaror, takrorlanadigan)
    juft = juft.sort_values(["bi", "a", "mi"], ascending=[True, False, True], kind="mergesort")
    juft["r"] = juft.groupby("bi").cumcount()
    bmay = shapely.area(b)

    n = len(b)
    out = pd.DataFrame({"m_qator": -1, "ulush": 0.0, "m_qator2": -1, "ulush2": 0.0}, index=range(n))
    r0 = juft[juft.r == 0]
    out.loc[r0.bi.values, "m_qator"] = r0.mi.values
    out.loc[r0.bi.values, "ulush"] = r0.a.values / bmay[r0.bi.values]
    r1 = juft[juft.r == 1]
    out.loc[r1.bi.values, "m_qator2"] = r1.mi.values
    out.loc[r1.bi.values, "ulush2"] = r1.a.values / bmay[r1.bi.values]
    out.index = biz.index
    return out


def main() -> int:
    kirish, manba_yol, chiqish = Path(KIRISH), Path(MANBA), Path(CHIQISH)
    for p in (kirish, manba_yol):
        if not p.exists():
            sys.exit(f"Fayl topilmadi: {p}")
    rez = {p.resolve() for p in (kirish, manba_yol)}
    if chiqish.resolve() in rez:
        sys.exit("CHIQISH KIRISH yoki MANBA bilan bir xil bo'lmasin — natija alohida faylga yoziladi.")
    if chiqish.exists() and not USTIGA_YOZ:
        sys.exit(f"Natija allaqachon bor: {chiqish}\n  Ustiga yozish uchun USTIGA_YOZ = True qiling.")
    if not 0 < MIN_ULUSH <= 1:
        sys.exit(f"MIN_ULUSH 0 dan katta, 1 dan kichik yoki teng bo'lsin: {MIN_ULUSH}")
    fermer = bool(FERMER_BIZDA and FERMER_MANBADA)

    yangi = list(USTUNLAR.values()) + ([ULUSH_USTUNI] if ULUSH_USTUNI else [])
    uzun = [c for c in yangi if len(c) > 10]
    if uzun:
        sys.exit(f"shp ustun nomi 10 belgidan oshmasin: {uzun}")

    xesh_manba, xesh_kirish = shp_xesh(manba_yol), shp_xesh(kirish)

    # ---- o'qish -------------------------------------------------------------------
    m_info = pyogrio.read_info(manba_yol)
    m_maydon = list(m_info["fields"])
    kerak = list(USTUNLAR) + ([FERMER_MANBADA] if fermer else [])
    yoq = [c for c in kerak if c not in m_maydon]
    if yoq:
        sys.exit(f"MANBA da ustun yo'q: {yoq}\n  Bor ustunlar: {m_maydon}")
    m_vil = ["viloyat"] if "viloyat" in m_maydon else []
    manba = pyogrio.read_dataframe(manba_yol, columns=list(dict.fromkeys(kerak + m_vil)))
    log(f"MANBA:  {manba_yol}  ({len(manba)} kontur, {manba.crs})")

    biz = pyogrio.read_dataframe(kirish)
    log(f"KIRISH: {kirish}  ({len(biz)} kontur, {biz.crs})")
    if fermer and FERMER_BIZDA not in biz.columns:
        sys.exit(f"KIRISH da '{FERMER_BIZDA}' ustuni yo'q. Bor ustunlar: {list(biz.columns)}")
    bor = [c for c in yangi if c in biz.columns]
    if bor:
        log(f"Diqqat: KIRISH da bu ustunlar allaqachon bor, qayta yoziladi: {bor}")
    if biz.crs is None or manba.crs is None:
        sys.exit("KIRISH yoki MANBA da CRS (.prj) yo'q — moslab bo'lmaydi.")

    if m_vil and "viloyat" in biz.columns:
        log(f"Viloyat: KIRISH {sorted(biz['viloyat'].dropna().unique())}, "
            f"MANBA {sorted(manba['viloyat'].dropna().unique())}")

    # ---- fazoviy moslash (metrik CRS da: MANBA metrik bo'lsa uniki, aks holda UTM) -----
    t0 = time.time()
    hisob_crs = manba.crs if manba.crs.is_projected else biz.estimate_utm_crs()
    mos = moslash(biz.geometry.to_crs(hisob_crs), manba.geometry.to_crs(hisob_crs))
    qabul = (mos.m_qator >= 0) & (mos.ulush >= MIN_ULUSH)
    log(f"Moslash ({hisob_crs.to_string()}, {time.time() - t0:.0f} s): "
        f"{int(qabul.sum())} / {len(biz)} kontur mos topildi (ulush >= {MIN_ULUSH})")
    hech = int((mos.m_qator < 0).sum())
    past = int(((mos.m_qator >= 0) & ~qabul).sum())
    log(f"  kesishmasi yo'q: {hech};  kesishma bor, lekin ulush < {MIN_ULUSH}: {past} -> bo'sh qoldirildi")
    q = mos.loc[qabul, "ulush"]
    if len(q):
        log(f"  ulush: >=0.99 {int((q >= 0.99).sum())}, 0.9-0.99 {int(((q >= 0.9) & (q < 0.99)).sum())}, "
            f"{MIN_ULUSH}-0.9 {int((q < 0.9).sum())}")

    # Shubhali: ikkinchi nomzod ham deyarli teng (>= 0.9 * birinchi) va o'tkaziladigan qiymatlari boshqa.
    tekshir = list(USTUNLAR) + ([FERMER_MANBADA] if fermer else [])
    sh = qabul & (mos.m_qator2 >= 0) & (mos.ulush2 >= 0.9 * mos.ulush)
    if sh.any():
        v1 = manba.iloc[mos.loc[sh, "m_qator"].values][tekshir].fillna("").reset_index(drop=True)
        v2 = manba.iloc[mos.loc[sh, "m_qator2"].values][tekshir].fillna("").reset_index(drop=True)
        farq = int((v1 != v2).any(axis=1).sum())
        log(f"  deyarli teng 2 nomzod: {int(sh.sum())} (qiymatlari bir xil: {int(sh.sum()) - farq}, "
            f"farqli: {farq} -> eng katta kesishmali olindi)")

    # ---- o'tkazish ------------------------------------------------------------------
    natija = biz.copy()
    idx = mos.m_qator.where(qabul, -1).values
    olinadi = manba.drop(columns="geometry").reset_index(drop=True)
    for eski, nom in USTUNLAR.items():
        qiymat = pd.Series(np.where(idx >= 0, olinadi[eski].reindex(idx).values, None),
                           index=natija.index, dtype=object)
        natija[nom] = qiymat.where(~bosh(qiymat), None)
        log(f"  {eski} -> {nom}: {int(natija[nom].notna().sum())} kontur to'ldi")

    if fermer:
        f_manba = pd.Series(np.where(idx >= 0, olinadi[FERMER_MANBADA].reindex(idx).values, None),
                            index=natija.index, dtype=object)
        bizda_bosh = bosh(natija[FERMER_BIZDA])
        toldir = bizda_bosh & ~bosh(f_manba)
        natija[FERMER_BIZDA] = natija[FERMER_BIZDA].astype(object)
        natija.loc[toldir, FERMER_BIZDA] = f_manba[toldir]
        log(f"  {FERMER_MANBADA} -> {FERMER_BIZDA}: {int(bizda_bosh.sum())} bo'sh edi, "
            f"{int(toldir.sum())} to'ldirildi, {int((bizda_bosh & ~toldir).sum())} bo'sh qoldi "
            f"(bor {int((~bizda_bosh).sum())} qiymat o'zgarmadi)")

    if ULUSH_USTUNI:
        natija[ULUSH_USTUNI] = mos.ulush.round(3).values

    # ustun tartibi: bizning ustunlar, keyin yangilari, oxirida geometriya
    asl = [c for c in biz.columns if c != "geometry" and c not in yangi]
    natija = natija[asl + yangi + ["geometry"]]

    # ---- yozish ---------------------------------------------------------------------
    chiqish.parent.mkdir(parents=True, exist_ok=True)
    shp_ochir(chiqish)
    pyogrio.write_dataframe(natija, chiqish, driver="ESRI Shapefile", encoding="UTF-8")
    log(f"Yozildi: {chiqish}")

    # ---- tekshiruv ------------------------------------------------------------------
    xato = False
    if shp_xesh(manba_yol) != xesh_manba:
        log("XATO: MANBA fayllari o'zgargan!")
        xato = True
    if shp_xesh(kirish) != xesh_kirish:
        log("XATO: KIRISH fayllari o'zgargan!")
        xato = True
    qayta = pyogrio.read_dataframe(chiqish)
    if len(qayta) != len(biz):
        log(f"XATO: natijada {len(qayta)} kontur, kirishda {len(biz)}")
        xato = True
    elif not shapely.equals(qayta.geometry.values, biz.geometry.values).all():
        log("XATO: natija geometriyasi kirishdan farq qiladi")
        xato = True
    else:
        log("Tekshiruv: MANBA va KIRISH o'zgarmagan; kontur soni va geometriya bir xil.")
    return 1 if xato else 0


if __name__ == "__main__":
    sys.exit(main())
