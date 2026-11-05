"""
02: Sentinel-2 sahnalarini qidirish (STAC) — tuman hududi va davr bo'yicha, sahna buluti filtri bilan.
Chiqish: data/oraliq/sahnalar_<tuman>.json (STAC ItemCollection)

python scripts/02_stac_qidiruv.py --tuman "Jomboy tumani" [--boshi 2026-06-01 --oxiri 2026-06-30]
"""
import os, sys, time, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
import pyogrio, pandas as pd
from pystac_client import Client
from fenologiya import sozlama as S


def qidir(s, bbox, boshi, oxiri):
    m = s["manba_cfg"]
    cl = Client.open(m["stac"])
    if m.get("imzo"):
        import planetary_computer
        cl = Client.open(m["stac"], modifier=planetary_computer.sign_inplace)
    srch = cl.search(collections=[m["collection"]], bbox=bbox, datetime=f"{boshi}/{oxiri}",
                     query={"eo:cloud_cover": {"lt": s["bulut_max_foiz"]}})
    return srch.item_collection()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuman", required=True)
    ap.add_argument("--boshi"); ap.add_argument("--oxiri")
    a = ap.parse_args()
    s = S.yuklash()
    boshi, oxiri = a.boshi or s["davr"]["boshi"], a.oxiri or s["davr"]["oxiri"]
    k = pyogrio.read_dataframe(S.yol("data", "kirish", f"konturlar_{S.slug(a.tuman)}.gpkg"), layer="konturlar")
    bbox = list(k.to_crs(4326).total_bounds)
    t = time.time()
    ic = qidir(s, bbox, boshi, oxiri)
    out = S.yol("data", "oraliq", f"sahnalar_{S.slug(a.tuman)}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ic.save_object(out)
    d = pd.DataFrame([{"sana": it.datetime.date(), "plitka": it.properties.get("s2:mgrs_tile") or it.id.split("_")[1],
                       "bulut": it.properties.get("eo:cloud_cover")} for it in ic])
    print(f"{a.tuman}: {boshi}..{oxiri} | sahnalar {len(ic)} | kunlar {d.sana.nunique()} | plitkalar {sorted(d.plitka.unique())}"
          f" | {time.time() - t:.0f} s -> {out}")
    if len(d):
        print("oylar bo'yicha kunlar:", d.groupby(pd.to_datetime(d.sana).dt.strftime("%Y-%m")).sana.nunique().to_dict())


if __name__ == "__main__":
    main()
