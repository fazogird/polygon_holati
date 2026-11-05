"""Conda muhitini 'activate' qilinmagan holda ham to'g'ri ishlatish.

Muhitning python.exe si to'g'ridan-to'g'ri chaqirilsa, `Library\\bin` PATH da bo'lmaydi va Windows boshqa joydagi
mos kelmaydigan BLAS/LAPACK DLL ni yuklaydi -> numpy.linalg, rasterio, matplotlib `0xc06d007f` bilan qulaydi.
Bu modul numpy dan OLDIN import qilinishi kerak.
"""
import os, sys

_p = sys.prefix
_dirs = [_p, os.path.join(_p, "Library", "mingw-w64", "bin"), os.path.join(_p, "Library", "usr", "bin"),
         os.path.join(_p, "Library", "bin"), os.path.join(_p, "Scripts"), os.path.join(_p, "bin")]
os.environ["PATH"] = os.pathsep.join([d for d in _dirs if os.path.isdir(d)] + [os.environ.get("PATH", "")])
for d in _dirs:
    if os.path.isdir(d) and hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(d)
        except OSError:
            pass
for var, sub in (("GDAL_DATA", "gdal"), ("PROJ_LIB", "proj"), ("PROJ_DATA", "proj")):
    d = os.path.join(_p, "Library", "share", sub)
    if os.path.isdir(d):
        os.environ[var] = d
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
