"""
03: Har kontur × sana uchun NDVI, EVI2, NDMI (Sentinel-2, 10 m, SCL bilan bulut/soya niqobi).

Usul: konturlar mavsum sinfi bo'yicha (Birlamchi / Ikkilamchi / Mavsumiy / boshqa) alohida yorliq-rastrlarga
o'tkaziladi (bir joyda B va I ustma-ust turgani uchun); har sana uchun tasvir bir marta o'qiladi va
np.bincount bilan barcha konturlar o'rtachasi bir yo'la hisoblanadi.

Chiqish: data/oraliq/qator_<tuman>.parquet — uniqueid, sana, ndvi, evi2, ndmi, toza_piksel, jami_piksel
         (faqat toza_piksel >= min_toza_piksel bo'lgan qatorlar)

python scripts/03_indeks_qator.py --tuman "Jomboy tumani" [--ishchi 6]
"""
import os, sys, time, argparse, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd, pyogrio, pystac
import odc.stac
from odc.geo.geobox import GeoBox
from rasterio.features import rasterize
from fenologiya import sozlama as S
from fenologiya.indeks import indekslar

SINF = {"Birlamchi ekin": 0, "Ikkilamchi ekin": 1, "Mavsumiy ekin": 2}


def yorliqlar(k, gb):
    """Har mavsum sinfi uchun yorliq rastri (0 = kontur yo'q, i+1 = k ning i-qatori)."""
    sinf = k.mavsum.map(SINF).fillna(3).astype(int).values
    labs = []
    for c in sorted(set(sinf)):
        idx = np.where(sinf == c)[0]
        lab = rasterize(((g, int(i) + 1) for g, i in zip(k.geometry.values[idx], idx)),
                        out_shape=gb.shape, transform=gb.affine, fill=0, dtype="int32")
        labs.append(lab)
    return labs


def bir_kun(items, gb, kan, labs, n, scl_toza, min_px):
    ds = odc.stac.load(items, bands=list(kan.values()), geobox=gb, groupby="solar_day", resampling="nearest",
                       chunks=None, fail_on_error=False)
    sc = {}
    for nom, a in kan.items():
        rb = items[0].assets[a].extra_fields.get("raster:bands", [{}])[0]
        sc[nom] = (rb.get("scale", 1e-4), rb.get("offset", 0.0))
    r = lambda nom: ds[kan[nom]].values[0].astype("float32") * sc[nom][0] + sc[nom][1]
    ok, ind = indekslar(r("qizil"), r("nir"), r("swir16"), ds[kan["scl"]].values[0], scl_toza)
    cnt = np.zeros(n + 1); sums = {k_: np.zeros(n + 1) for k_ in ind}
    for lab in labs:
        sel = ok & (lab > 0); l = lab[sel]
        cnt += np.bincount(l, minlength=n + 1)
        for k_, v in ind.items():
            sums[k_] += np.bincount(l, weights=v[sel].astype("float64"), minlength=n + 1)
    good = np.where(cnt >= min_px)[0]
    return good, cnt[good], {k_: (sums[k_][good] / cnt[good]).astype("float32") for k_ in ind}, float(ok.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuman", required=True)
    ap.add_argument("--ishchi", type=int, default=6)
    a = ap.parse_args()
    s = S.yuklash(); sl = S.slug(a.tuman)
    odc.stac.configure_rio(cloud_defaults=True, aws={"aws_unsigned": True})
    k = pyogrio.read_dataframe(S.yol("data", "kirish", f"konturlar_{sl}.gpkg"), layer="konturlar").reset_index(drop=True)
    n = len(k)
    ic = pystac.ItemCollection.from_file(S.yol("data", "oraliq", f"sahnalar_{sl}.json"))
    xmin, ymin, xmax, ymax = k.total_bounds
    gb = GeoBox.from_bbox((xmin - 20, ymin - 20, xmax + 20, ymax + 20), crs=S.CRS, resolution=10)
    t0 = time.time()
    labs = yorliqlar(k, gb)
    jami = np.zeros(n + 1)
    for lab in labs:
        jami += np.bincount(lab.ravel(), minlength=n + 1)
    print(f"{a.tuman}: {n} kontur, to'r {gb.shape[1]}x{gb.shape[0]} (10 m), yorliq rastrlari {len(labs)} ta "
          f"({time.time() - t0:.0f} s); pikselsiz kontur: {int((jami[1:] == 0).sum())}", flush=True)
    kunlar = collections.defaultdict(list)
    for it in ic:
        kunlar[it.datetime.date()].append(it)
    kan = s["manba_cfg"]["kanallar"]
    parts, sifat = [], {}
    with ThreadPoolExecutor(a.ishchi) as ex:
        futs = {ex.submit(bir_kun, its, gb, kan, labs, n, s["scl_toza"], s["min_toza_piksel"]): d for d, its in kunlar.items()}
        for j, f in enumerate(as_completed(futs), 1):
            d = futs[f]
            try:
                good, c, v, frac = f.result()
            except Exception as e:
                print(f"  {d}: XATO {type(e).__name__}: {str(e)[:120]}", flush=True); continue
            sifat[d] = frac
            if len(good):
                parts.append(pd.DataFrame({"i": good - 1, "sana": pd.Timestamp(d), "toza_piksel": c.astype("int32"), **v}))
            if j % 10 == 0 or j == len(futs):
                print(f"  {j}/{len(futs)} kun | {time.time() - t0:.0f} s", flush=True)
    q = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["i", "sana", "toza_piksel", "ndvi", "evi2", "ndmi"])
    q["uniqueid"] = k.uniqueid.values[q.i.values]
    q["jami_piksel"] = jami[1:][q.i.values].astype("int32")
    q = q.drop(columns="i")[["uniqueid", "sana", "ndvi", "evi2", "ndmi", "toza_piksel", "jami_piksel"]].sort_values(["uniqueid", "sana"])
    out = S.yol("data", "oraliq", f"qator_{sl}.parquet")
    q.to_parquet(out, index=False)
    sf = pd.Series(sifat).sort_index()
    print(f"Tayyor: {len(q)} qator, {q.uniqueid.nunique()} kontur, {len(sf)} kun, toza kunlar (>50% toza): {int((sf > 0.5).sum())}"
          f" | {time.time() - t0:.0f} s -> {out}")


if __name__ == "__main__":
    main()
