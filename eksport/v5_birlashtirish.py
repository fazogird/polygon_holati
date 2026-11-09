"""v4 konturlariga fermer ma'lumoti va oylik NDVI ni `uniqueid` bo'yicha qo'shish -> v5.

Manbalar (hammasi faqat o'qiladi):
  asos   — ekin_yerlar_qisqa_v4.gpkg   : oxirgi konturlar (season, suv oylari, hosil)
  toliq  — ekin_yerlar_yakuniy.gpkg    : to'liq atributlar (fermer, kadastr, region kodi ...)
  oraliq — data/oraliq/qator_<tuman>.parquet : Sentinel-2 NDVI vaqt qatori (03 qadam)

Natija: asosdagi hamma narsa (geometriya ham) + fermer ustunlari + NDVI ustunlari:
  full_name, tax_number — fermer nomi va STIR (toliqdagi f_name, f_inn — nomi o'zgartirib)
  ndvi_02 .. ndvi_10    — oy bo'yicha o'rtacha NDVI (faqat toza kunlar: dalaning >= min_toza_ulush
                          qismi toza; sozlamalar.yaml dagi 04 qadam bilan bir xil). Kuzatuv bo'lmagan oy — bo'sh.
Ustun nomlari 10 belgidan oshmaydi (shp ga ajratganda qisqarmaydi).

Ishga tushirish (loyiha ildizidan):
    .\\run.bat eksport\\v5_birlashtirish.py
    .\\run.bat eksport\\v5_birlashtirish.py --tuman "Jomboy tumani" --chiqish D:\\temp\\test_v5.gpkg
Keyin shp: .\\run.bat eksport\\viloyat_shp.py D:\\...\\ekin_yerlar_qisqa_v5.gpkg
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fenologiya import muhit  # noqa: F401,E402  (GDAL_DATA/PROJ va DLL yo'llari, numpy dan oldin)

import argparse  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyogrio  # noqa: E402

from fenologiya import sozlama  # noqa: E402

NATIJA = Path("D:/Tasks/bir_ikki_lamchi/natija")
ASOS = NATIJA / "ekin_yerlar_qisqa_v4.gpkg"
TOLIQ = NATIJA / "ekin_yerlar_yakuniy.gpkg"
CHIQISH = NATIJA / "ekin_yerlar_qisqa_v5.gpkg"
ORALIQ = Path(sozlama.yol("data", "oraliq"))
KALIT = "uniqueid"

# toliq fayldan olinadigan ustunlar: {toliqdagi nomi: v5 dagi nomi}. Boshqa ustun kerak bo'lsa shu yerga qo'shing.
FERMER_USTUNLAR = {
    "f_name": "full_name",
    "f_inn": "tax_number",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def ndvi_oylik(fayllar: list[Path], idlar: set, oylar: list[int], min_toza: float) -> pd.DataFrame:
    """qator_*.parquet lardan uniqueid bo'yicha oylik o'rtacha NDVI (faqat toza kunlar)."""
    qismlar = []
    for f in fayllar:
        q = pd.read_parquet(f, columns=[KALIT, "sana", "ndvi", "toza_piksel", "jami_piksel"])
        q = q[q[KALIT].isin(idlar)]
        if q.empty:
            continue
        q = q[(q.toza_piksel / q.jami_piksel >= min_toza) & q.ndvi.notna()]
        q = q[q.sana.dt.month.isin(oylar)]
        jad = q.pivot_table(index=KALIT, columns=q.sana.dt.month, values="ndvi", aggfunc="mean")
        jad = jad.reindex(columns=oylar)
        jad.columns = [f"ndvi_{m:02d}" for m in oylar]
        jad["_n"] = q.groupby(KALIT).size()  # faqat takrorni hal qilish uchun, natijaga yozilmaydi
        qismlar.append(jad)
    if not qismlar:
        return pd.DataFrame(columns=[f"ndvi_{m:02d}" for m in oylar])
    nd = pd.concat(qismlar)
    # bitta kontur ikki tuman faylida bo'lsa (masalan shahar/tuman chegarasi) — kuzatuvi ko'pi olinadi
    dub = nd.index.duplicated(keep=False)
    if dub.any():
        log(f"  Diqqat: {nd.index[dub].nunique()} kontur bir nechta qator faylida — kuzatuvi ko'pi olindi")
        nd = nd.sort_values("_n", ascending=False)
        nd = nd[~nd.index.duplicated(keep="first")]
    return nd.drop(columns="_n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="v4 + fermer (yakuniy) + oylik NDVI (oraliq) -> v5")
    ap.add_argument("--asos", default=str(ASOS), help="oxirgi konturlar gpkg (standart: v4)")
    ap.add_argument("--toliq", default=str(TOLIQ), help="to'liq atributli gpkg (fermer ma'lumoti)")
    ap.add_argument("--oraliq", default=str(ORALIQ), help="qator_<tuman>.parquet papkasi")
    ap.add_argument("--chiqish", default=str(CHIQISH), help="natija gpkg (standart: ..._v5.gpkg)")
    ap.add_argument("--tuman", action="append",
                    help="faqat shu tuman(lar) — test uchun; bir necha marta berish mumkin")
    ap.add_argument("--ustiga-yoz", action="store_true", help="natija fayli bor bo'lsa ham ustiga yozish")
    a = ap.parse_args(argv)

    asos, toliq, oraliq, chiqish = Path(a.asos), Path(a.toliq), Path(a.oraliq), Path(a.chiqish)
    for p in (asos, toliq, oraliq):
        if not p.exists():
            sys.exit(f"Topilmadi: {p}")
    if chiqish.resolve() in (asos.resolve(), toliq.resolve()):
        sys.exit("Chiqish fayli kirish fayllaridan biri bilan bir xil bo'lmasin.")
    if chiqish.exists() and not a.ustiga_yoz:
        sys.exit(f"Natija fayli allaqachon bor: {chiqish}\n  Ustiga yozish uchun --ustiga-yoz qo'shing.")

    cfg = sozlama.yuklash()
    min_toza = float(cfg["fenologiya"]["min_toza_ulush"])
    oy0 = pd.Timestamp(cfg["davr"]["boshi"]).month
    oy1 = pd.Timestamp(cfg["davr"]["oxiri"]).month
    oylar = list(range(oy0, oy1 + 1))

    # --- 1. asos (geometriya bilan)
    qatlam = pyogrio.list_layers(asos)[0, 0]
    where = None
    if a.tuman:
        where = "tuman IN (" + ", ".join("'" + t.replace("'", "''") + "'" for t in a.tuman) + ")"
    log(f"Asos: {asos} (qatlam {qatlam}{', ' + where if where else ''})")
    gdf = pyogrio.read_dataframe(asos, layer=qatlam, where=where)
    log(f"  {len(gdf):,} kontur, CRS {gdf.crs}")
    if gdf.empty:
        sys.exit("Asosda kontur yo'q (tuman nomini tekshiring).")
    if gdf[KALIT].isna().any() or gdf[KALIT].duplicated().any():
        sys.exit(f"Asosda {KALIT} bo'sh yoki takror — birlashtirib bo'lmaydi.")

    # --- 2. toliq: fermer ustunlari
    t_qatlam = "ekin_yerlar" if "ekin_yerlar" in pyogrio.list_layers(toliq)[:, 0] else pyogrio.list_layers(toliq)[0, 0]
    t_ustunlar = list(pyogrio.read_info(toliq, layer=t_qatlam)["fields"])
    olish = dict(FERMER_USTUNLAR)
    yoq = [c for c in olish if c not in t_ustunlar]
    if yoq:
        sys.exit(f"Toliq faylda bu ustunlar yo'q: {yoq}")
    bor = [yangi for yangi in olish.values() if yangi in gdf.columns]
    if bor:
        sys.exit(f"Asosda bu ustunlar allaqachon bor: {bor}")
    log(f"Toliq: {toliq} (qatlam {t_qatlam}) -> " + ", ".join(f"{e} -> {y}" for e, y in olish.items()))
    tdf = pyogrio.read_dataframe(toliq, layer=t_qatlam, columns=[KALIT] + list(olish),
                                 read_geometry=False, where=where).rename(columns=olish)
    if tdf[KALIT].duplicated().any():
        sys.exit(f"Toliq faylda {KALIT} takror — qaysi qatorni olishni bilib bo'lmaydi.")
    n0 = len(gdf)
    gdf = gdf.merge(tdf, on=KALIT, how="left", validate="one_to_one", indicator="_t")
    assert len(gdf) == n0
    t_yoq = int((gdf._t == "left_only").sum())
    gdf = gdf.drop(columns="_t")
    log(f"  toliqda topildi: {n0 - t_yoq:,} / {n0:,}" + (f"  (topilmadi: {t_yoq:,})" if t_yoq else ""))

    # --- 3. NDVI
    fayllar = sorted(oraliq.glob("qator_*.parquet"))
    if a.tuman:
        sluglar = {sozlama.slug(t) for t in a.tuman}
        fayllar = [f for f in fayllar if f.stem.removeprefix("qator_") in sluglar] or fayllar
    log(f"NDVI: {len(fayllar)} qator fayli, oylar {oylar[0]}-{oylar[-1]}, toza ulush >= {min_toza}")
    t0 = time.time()
    nd = ndvi_oylik(fayllar, set(gdf[KALIT]), oylar, min_toza)
    log(f"  {len(nd):,} kontur uchun NDVI ({time.time() - t0:.0f} s)")
    gdf = gdf.merge(nd, left_on=KALIT, right_index=True, how="left", validate="one_to_one")
    assert len(gdf) == n0
    ndvi_ust = list(nd.columns)
    gdf[ndvi_ust] = gdf[ndvi_ust].astype("float64").round(3)

    # --- 4. yozish
    chiqish.parent.mkdir(parents=True, exist_ok=True)
    if chiqish.exists():
        chiqish.unlink()
    log(f"Yozilmoqda: {chiqish}")
    pyogrio.write_dataframe(gdf, chiqish, layer=qatlam, driver="GPKG")

    # --- 5. hisobot
    vil = "viloyat" if "viloyat" in gdf.columns else None
    h = gdf.assign(ndvi_bor=gdf[ndvi_ust].notna().any(axis=1),
                   fermer_bor=gdf["full_name"].notna() if "full_name" in gdf.columns else False)
    h = h.groupby(vil or (lambda _: "jami")).agg(kontur=(KALIT, "size"), ndvi_bor=("ndvi_bor", "sum"),
                                                 fermer_bor=("fermer_bor", "sum"))
    h["ndvi_yoq"] = h.kontur - h.ndvi_bor
    with pd.option_context("display.width", 200):
        print(h.to_string())
    oy_bosh = {c: int(gdf[c].isna().sum()) for c in ndvi_ust}
    log(f"Oy bo'yicha NDVI bo'sh (toza kun yo'q) konturlar: {oy_bosh}")
    log(f"Tayyor: {len(gdf):,} kontur, {len(gdf.columns) - 1} ustun -> {chiqish}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
