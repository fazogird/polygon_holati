"""Spektral indekslar va piksel yaroqliligi.

Sentinel-2 c1 (Earth Search): qaytish = DN * 0.0001 - 0.1. Qorong'i piksellarda (suv, soya) qaytish 0 ga yaqin
yoki manfiy bo'ladi -> NDVI maxraji ~0 -> juda katta qiymatlar. Shuning uchun qaytishi (0, 1.5] dan tashqari
yoki maxraji juda kichik piksellar yaroqsiz deb olinadi; indekslar o'z chegarasiga qirqiladi.
"""
import numpy as np

REFL_MAX = 1.5
MIN_MAXRAJ = 0.02


def indekslar(red, nir, swir, scl, scl_toza):
    """-> (yaroqli_niqob, {"ndvi","evi2","ndmi"}) — massivlar float32, qaytish birligida."""
    ok = np.isin(scl, scl_toza)
    for b in (red, nir, swir):
        ok &= (b > 0) & (b <= REFL_MAX)
    s1, s2 = nir + red, nir + swir
    ok &= (s1 > MIN_MAXRAJ) & (s2 > MIN_MAXRAJ)
    with np.errstate(divide="ignore", invalid="ignore"):
        ind = {"ndvi": np.clip((nir - red) / s1, -1, 1),
               "evi2": np.clip(2.5 * (nir - red) / (nir + 2.4 * red + 1.0), -1, 2.5),
               "ndmi": np.clip((nir - swir) / s2, -1, 1)}
    for v in ind.values():
        ok &= np.isfinite(v)
    return ok, {k: v.astype("float32") for k, v in ind.items()}
