"""Fenologiya testi: sun'iy NDVI qatorlar (bug'doy + ikkinchi ekin, bitta kech ekin, bog', bo'sh dala).
python tests/test_fen.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
import numpy as np, pandas as pd
from fenologiya import sozlama as S, fen

cfg = S.yuklash()["fenologiya"]
kunlar = pd.date_range("2026-02-01", "2026-10-31", freq="D"); n = len(kunlar)
t = np.arange(n)
day = lambda m, d: int((pd.Timestamp(2026, m, d) - kunlar[0]).days)
g = lambda c, w, h: h * np.exp(-0.5 * ((t - c) / w) ** 2)

qatorlar = {
    "ikki_sikl": 0.1 + g(day(4, 20), 35, 0.8) + g(day(8, 25), 20, 0.55),      # bug'doy + mosh
    "kech_bitta": 0.1 + g(day(6, 10), 18, 0.65),                               # may-iyul ekin
    "bog": 0.4 + g(day(5, 15), 70, 0.35),                                      # doim yashil
    "bosh": 0.1 + 0.02 * np.sin(t / 9),                                        # bo'sh dala
}
oy = lambda i: kunlar[i].month
natija = {}
for nom, s in qatorlar.items():
    cyc, _, _ = fen.sikllar(s.astype("float32"), cfg)
    natija[nom] = {m: fen.mavsum_oraliq(cyc, m, kunlar, cfg) for m in ("Birlamchi ekin", "Ikkilamchi ekin", "Mavsumiy ekin")}
    natija[nom]["n"] = len(cyc)

r = natija["ikki_sikl"]
assert r["n"] == 2
assert oy(r["Birlamchi ekin"][0]) in (2, 3) and oy(r["Birlamchi ekin"][1]) in (6, 7), r
assert oy(r["Ikkilamchi ekin"][0]) in (7, 8) and oy(r["Ikkilamchi ekin"][1]) in (9, 10), r
r = natija["kech_bitta"]
assert r["n"] == 1 and r["Birlamchi ekin"] is not None and r["Ikkilamchi ekin"] is None        # cho'qqi 10-iyun < 20-iyun
assert oy(r["Birlamchi ekin"][0]) == 5 and oy(r["Birlamchi ekin"][1]) == 7, r
r = natija["bog"]
assert r["Mavsumiy ekin"] is not None and oy(r["Mavsumiy ekin"][1]) >= 9, r
assert natija["bosh"]["n"] == 0 and natija["bosh"]["Mavsumiy ekin"] is None
print("test_fen: OK", {k: {m[:4]: (None if v is None else f"{oy(v[0])}-{oy(v[1])}") for m, v in d.items() if m != "n"}
                       for k, d in natija.items()})
