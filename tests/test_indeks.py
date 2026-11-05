"""Indeks va niqob testi (sun'iy ma'lumot). python tests/test_indeks.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
import numpy as np
from fenologiya.indeks import indekslar

red = np.array([0.05, 0.10, 0.001, -0.02, 0.05, 0.05], dtype="float32")
nir = np.array([0.40, 0.12, 0.002, 0.01, 0.40, 2.00], dtype="float32")
sw = np.array([0.20, 0.15, 0.002, 0.01, 0.20, 0.20], dtype="float32")
scl = np.array([4, 5, 4, 6, 9, 4])          # 9 = bulut
ok, ind = indekslar(red, nir, sw, scl, [4, 5, 6, 7])

assert ok.tolist() == [True, True, False, False, False, False], ok   # qorong'i, manfiy, bulut, >1.5 — yaroqsiz
assert abs(ind["ndvi"][0] - (0.35 / 0.45)) < 1e-6
assert np.all(np.abs(ind["ndvi"]) <= 1) and np.all(np.abs(ind["ndmi"]) <= 1)
assert np.all((ind["evi2"] >= -1) & (ind["evi2"] <= 2.5))
print("test_indeks: OK", {k: np.round(v[:2], 3).tolist() for k, v in ind.items()})
