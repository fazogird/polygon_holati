"""
00: Manbalar testi — AWS Earth Search va Microsoft Planetary Computer.
Har manba uchun: STAC qidiruv vaqti, sahna topildimi, Sentinel-2 qizil (10 m) va SCL (20 m) kanallaridan
hudud bo'lagini o'qish vaqti va tezligi. Kontur yuklanmaydi — faqat ochiq tasvir o'qiladi.

python scripts/00_test_tezlik.py [--bbox minlon minlat maxlon maxlat] [--oy 2026-06]
"""
import os, sys, time, json, argparse, datetime
import requests
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff",
                GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", VSI_CACHE="TRUE")
MANBALAR = {
    "aws": dict(stac="https://earth-search.aws.element84.com/v1", col="sentinel-2-c1-l2a", red="red", scl="scl", imzo=False),
    "pc": dict(stac="https://planetarycomputer.microsoft.com/api/stac/v1", col="sentinel-2-l2a", red="B04", scl="SCL", imzo=True),
}


def imzo_pc(col):
    r = requests.get(f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{col}", timeout=30)
    r.raise_for_status()
    return r.json()["token"]


def oqish(href, bbox):
    t = time.time()
    with rasterio.Env(**GDAL_ENV):
        with rasterio.open(href) as ds:
            b = transform_bounds("EPSG:4326", ds.crs, *bbox)
            T = ds.transform            # oddiy arifmetika (ba'zi muhitlarda rasterio.from_bounds numpy DLL xatosi beradi)
            c0, c1 = sorted([int((b[0] - T.c) / T.a), int((b[2] - T.c) / T.a)])
            r0, r1 = sorted([int((b[3] - T.f) / T.e), int((b[1] - T.f) / T.e)])
            c0, r0 = max(c0, 0), max(r0, 0); c1, r1 = min(c1, ds.width), min(r1, ds.height)
            w = rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)
            a = ds.read(1, window=w)
    dt = time.time() - t
    return dict(soniya=round(dt, 2), piksel=int(a.size), mpiks_s=round(a.size / dt / 1e6, 2), shakl=list(a.shape))


def test(nom, m, bbox, oy):
    r = dict(manba=nom)
    y, mo = map(int, oy.split("-"))
    end = (datetime.date(y + (mo == 12), mo % 12 + 1, 1) - datetime.timedelta(days=1)).isoformat()
    body = {"collections": [m["col"]], "bbox": bbox, "datetime": f"{oy}-01T00:00:00Z/{end}T23:59:59Z",
            "limit": 20, "query": {"eo:cloud_cover": {"lt": 20}}}
    try:
        t = time.time()
        res = requests.post(m["stac"] + "/search", json=body, timeout=60)
        res.raise_for_status()
        feats = res.json().get("features", [])
        r["stac_soniya"] = round(time.time() - t, 2)
        r["sahnalar_soni"] = len(feats)
        if not feats:
            r["xato"] = "sahna topilmadi"; return r
        it = min(feats, key=lambda f: f["properties"].get("eo:cloud_cover", 100))
        r["sahna"] = it["id"]; r["sana"] = it["properties"]["datetime"][:10]
        r["bulut_%"] = round(it["properties"].get("eo:cloud_cover", -1), 1)
        tok = imzo_pc(m["col"]) if m["imzo"] else None
        href = lambda k: it["assets"][k]["href"] + (("?" + tok) if tok else "")
        r["qizil_10m"] = oqish(href(m["red"]), bbox)
        r["scl_20m"] = oqish(href(m["scl"]), bbox)
    except Exception as e:
        r["xato"] = f"{type(e).__name__}: {str(e)[:200]}"
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", nargs=4, type=float, default=[66.95, 39.60, 67.25, 39.85])   # Jomboy atrofi
    ap.add_argument("--oy", default="2026-06")
    a = ap.parse_args()
    print(f"Hudud (bbox): {a.bbox} | oy: {a.oy}\n")
    natija = [test(n, m, a.bbox, a.oy) for n, m in MANBALAR.items()]
    for r in natija:
        print(f"=== {r['manba'].upper()} ===")
        for k, v in r.items():
            if k != "manba":
                print(f"  {k:14s}: {v}")
        print()
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    p = os.path.join(ROOT, "logs", f"test_tezlik_{datetime.datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(natija, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Jurnal:", p)


if __name__ == "__main__":
    main()
