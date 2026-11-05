"""Maydonga qarab ichki bufer testi (sun'iy konturlar). python tests/test_bufer.py"""
import os, sys, tempfile, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import fenologiya.muhit  # noqa: F401
import numpy as np, geopandas as gpd, pyogrio
from shapely.geometry import box
from fenologiya import sozlama as S

spec = importlib.util.spec_from_file_location("m01", os.path.join(ROOT, "scripts", "01_geom_tayyorlash.py"))
m01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m01)
cfg = S.yuklash()["ichki_bufer"]

# 0.3 ga, 1 ga, 5 ga, ingichka 5 ga (10 m x 5 km)
g = gpd.GeoDataFrame({"uniqueid": list("abcd"), "viloyat": "v", "tuman": "T", "turi": "x", "mavsum": "Birlamchi ekin", "maydon": 0.0},
                     geometry=[box(0, 0, 55, 55), box(0, 0, 100, 100), box(0, 0, 224, 224), box(0, 0, 10, 5000)], crs=S.CRS)
d = tempfile.mkdtemp(); src = os.path.join(d, "s.gpkg")
pyogrio.write_dataframe(g.to_crs(4326), src, layer="ekin_yerlar")
r = m01.tayyorla(src, "T", cfg, os.path.join(d, "o.gpkg"))
got = dict(zip(r.uniqueid, r.bufer_m.astype(int)))
assert got == {"a": 0, "b": 5, "c": 10, "d": 0}, got
assert np.all(r.geometry.area.values >= cfg["min_qolgan_ulush"] * g.geometry.area.values - 1e-6)
print("test_bufer: OK", got)
