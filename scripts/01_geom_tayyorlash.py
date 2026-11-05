"""
01: Konturlarni tayyorlash — faqat kerakli ustunlar, UTM 42N, ichki bufer.

Kirish: birlamchi_ikkilamchi natijasi (to'liq versiya, `uniqueid` bilan).
Chiqish: data/kirish/konturlar_<tuman>.gpkg (qatlam `konturlar`):
  uniqueid, viloyat, tuman, turi, mavsum, maydon, bufer_m (ishlatilgan ichki bufer, 0 = asl geometriya)
  + geometriya (EPSG:32642). Bufer maydonga qarab — config `ichki_bufer` (qaror 0004).

python scripts/01_geom_tayyorlash.py --tuman "Jomboy tumani"      (yoki --hammasi)
"""
import os, sys, time, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401  (numpy dan oldin!)
import pyogrio, shapely, numpy as np
from fenologiya import sozlama as S

USTUN = ["uniqueid", "viloyat", "tuman", "turi", "mavsum", "maydon"]


def tayyorla(src, tuman, cfg, out):
    """Ichki bufer maydonga qarab: katta kontur -> kattaroq bufer, kichik -> bufersiz.
    Bufer konturning >= min_qolgan_ulush qismini va >= min_qolgan_m2 ni qoldirmasa, keyingi kichikroq bufer sinaladi."""
    q = tuman.replace("'", "''")
    g = pyogrio.read_dataframe(src, layer="ekin_yerlar", columns=USTUN, where=f"tuman = '{q}'")
    if g.empty:
        raise SystemExit(f"Tuman topilmadi: {tuman}")
    g = g.to_crs(S.CRS)
    geo = g.geometry.values
    area = shapely.area(geo)
    pog = sorted(cfg["pogonalar"], key=lambda p: p["min_ga"])
    reja = np.zeros(len(g))                                   # maydon bo'yicha rejalashtirilgan bufer
    for p in pog:
        reja[area / 1e4 >= p["min_ga"]] = p["bufer_m"]
    tanlangan = np.zeros(len(g)); natija = geo.copy()
    hal = np.zeros(len(g), dtype=bool)
    for b in sorted({p["bufer_m"] for p in pog if p["bufer_m"] > 0}, reverse=True):
        idx = np.where(~hal & (reja >= b))[0]
        if not len(idx):
            continue
        inner = shapely.buffer(geo[idx], -b, join_style="mitre")
        ia = shapely.area(inner)
        ok = ~shapely.is_empty(inner) & (ia >= cfg["min_qolgan_m2"]) & (ia >= cfg["min_qolgan_ulush"] * area[idx])
        natija[idx[ok]] = inner[ok]; tanlangan[idx[ok]] = b; hal[idx[ok]] = True
    g["bufer_m"] = tanlangan.astype("int16")
    g["geometry"] = natija
    pyogrio.write_dataframe(g, out, layer="konturlar", driver="GPKG", promote_to_multi=True)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuman", nargs="*")
    ap.add_argument("--hammasi", action="store_true")
    a = ap.parse_args()
    s = S.yuklash()
    src = S.kirish_yoli(s)
    tumanlar = sorted(pyogrio.read_dataframe(src, layer="ekin_yerlar", columns=["tuman"], read_geometry=False)
                      .tuman.dropna().unique()) if a.hammasi else (a.tuman or [])
    if not tumanlar:
        raise SystemExit("--tuman yoki --hammasi bering")
    os.makedirs(S.yol("data", "kirish"), exist_ok=True)
    for tm in tumanlar:
        t = time.time()
        out = S.yol("data", "kirish", f"konturlar_{S.slug(tm)}.gpkg")
        if os.path.exists(out):
            os.remove(out)                           # o'z oraliq faylimiz — qayta yaratiladi
        g = tayyorla(src, tm, s["ichki_bufer"], out)
        print(f"{tm}: {len(g)} kontur | bufer (m) -> soni: {g.bufer_m.value_counts().sort_index().to_dict()}"
              f" | mavsum: {g.mavsum.value_counts(dropna=False).to_dict()} | {time.time() - t:.0f} s -> {out}", flush=True)


if __name__ == "__main__":
    main()
