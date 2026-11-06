"""
04b: NDVI bo'yicha faol davri qat'iy oylarga mos kelmagan konturlar — ArcGIS va Excel uchun.

04 natijasi (`fenologiya_<tuman>.parquet`) + asl kontur geometriyasi (v1 to'liq versiyasidan, `uniqueid` bo'yicha).
Chiqish (data/natija/eksport/):
  mos_kelmagan_<teg>.gpkg  — qatlam `konturlar` (asl geometriya, EPSG:3857) — ArcGIS da `yorliq_mos` bo'yicha rang
  mos_kelmagan_<teg>.csv   — xuddi shu jadval (Excel, UTF-8)

python scripts/04b_mos_kelmaganlar.py --tuman "Jomboy tumani"
python scripts/04b_mos_kelmaganlar.py --viloyat "Samarqand viloyati"
python scripts/04b_mos_kelmaganlar.py --hammasi
  --holat farqli faol_emas     (standart: ikkalasi; `mos` ham qo'shilsa — hammasi)
"""
import os, sys, argparse, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
import pandas as pd, pyogrio, geopandas as gpd
from fenologiya import sozlama as S

USTUN = ["uniqueid", "viloyat", "tuman", "turi", "mavsum", "maydon", "yorliq_mos",
         "suv_boshi_qatiy", "suv_oxiri_qatiy", "suv_boshi_ndvi", "suv_oxiri_ndvi",
         "boshi_sana", "oxiri_sana", "faol_kun", "chuqqi_sana", "chuqqi_ndvi", "sikl_soni", "sikllar",
         "kuzatuv", "ishonch"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuman", nargs="*"); ap.add_argument("--viloyat"); ap.add_argument("--hammasi", action="store_true")
    ap.add_argument("--holat", nargs="*", default=["farqli", "faol_emas"])
    a = ap.parse_args()
    s = S.yuklash()
    fl = sorted(glob.glob(S.yol("data", "natija", "fenologiya_*.parquet")))
    if not fl:
        raise SystemExit("04 natijasi yo'q — avval: pipeline.py fenologiya")
    R = pd.concat([pd.read_parquet(f) for f in fl], ignore_index=True)
    if a.tuman:
        R = R[R.tuman.isin(a.tuman)]; teg = S.slug(a.tuman[0]) if len(a.tuman) == 1 else "tanlangan"
    elif a.viloyat:
        R = R[R.viloyat == a.viloyat]; teg = S.slug(a.viloyat)
    elif a.hammasi:
        teg = "hammasi"
    else:
        raise SystemExit("--tuman, --viloyat yoki --hammasi bering")
    if R.empty:
        raise SystemExit("Tanlangan tuman(lar) uchun 04 natijasi topilmadi")
    R = R[R.yorliq_mos.isin(a.holat)][USTUN]
    # asl geometriya (v1 to'liq versiyasi), tuman bo'yicha o'qiladi
    src = S.kirish_yoli(s); parts = []
    for tm in sorted(R.tuman.unique()):
        g = pyogrio.read_dataframe(src, layer="ekin_yerlar", columns=["uniqueid"], where="tuman = '{}'".format(tm.replace("'", "''")))
        parts.append(g[g.uniqueid.isin(R.uniqueid)])
    G = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=parts[0].crs)
    G = G.merge(R, on="uniqueid", how="inner")
    for c in ("boshi_sana", "oxiri_sana", "chuqqi_sana"):
        G[c] = pd.to_datetime(G[c]).dt.strftime("%Y-%m-%d")
    od = S.yol("data", "natija", "eksport"); os.makedirs(od, exist_ok=True)
    gp, cs = os.path.join(od, f"mos_kelmagan_{teg}.gpkg"), os.path.join(od, f"mos_kelmagan_{teg}.csv")
    if os.path.exists(gp):
        os.remove(gp)
    pyogrio.write_dataframe(G, gp, layer="konturlar", driver="GPKG", promote_to_multi=True)
    G.drop(columns="geometry").to_csv(cs, index=False, encoding="utf-8-sig")
    print(f"{len(G)} kontur (geometriyasi topilmagan: {len(R) - len(G)})")
    print(pd.crosstab([G.viloyat, G.mavsum], G.yorliq_mos, margins=True).to_string())
    f = G[G.yorliq_mos == "farqli"]
    if len(f):
        print("\n'farqli' — NDVI oylari (eng ko'p):")
        print((f.mavsum + " | qat'iy " + f.suv_boshi_qatiy.astype("Int64").astype(str) + "-" + f.suv_oxiri_qatiy.astype("Int64").astype(str)
               + " -> NDVI " + f.suv_boshi_ndvi.astype("Int64").astype(str) + "-" + f.suv_oxiri_ndvi.astype("Int64").astype(str))
              .value_counts().head(8).to_string())
    print(f"\n-> {gp}\n-> {cs}")


if __name__ == "__main__":
    main()
