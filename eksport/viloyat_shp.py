"""Ekin yerlari gpkg faylini viloyatlar bo'yicha alohida shapefile larga ajratish.

Har bir viloyat (`viloyat` ustunidagi qiymat) o'z shp fayliga yoziladi:
    <kirish papkasi>/<kirish nomi>_viloyatlar_shp/fargona_viloyati.shp
                                                   qashqadaryo_viloyati.shp
                                                   samarqand_viloyati.shp
                                                   sirdaryo_viloyati.shp
Hamma ustunlar va CRS saqlanadi; ba'zi ustunlar shp da boshqa nom oladi (SHP_NOMLAR,
masalan uniqueid -> unique_id). Matn UTF-8 (.cpg fayli bilan) yoziladi.
Kirish fayli o'zgarmaydi.

Ishga tushirish (loyiha ildizidan):
    .\\run.bat eksport\\viloyat_shp.py D:\\...\\ekin_yerlar_qisqa_v5.gpkg
    .\\run.bat eksport\\viloyat_shp.py            (fayl yo'lini so'raydi)
    .\\run.bat eksport\\viloyat_shp.py A.gpkg --chiqish D:\\boshqa\\papka --ustiga-yoz
    .\\run.bat eksport\\viloyat_shp.py A.gpkg --nom tuman=district   (qo'shimcha / boshqa nom)
    .\\run.bat eksport\\viloyat_shp.py A.gpkg --nomlamasdan          (gpkg nomlari bilan)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fenologiya import muhit  # noqa: F401,E402  (GDAL_DATA/PROJ va DLL yo'llari, numpy dan oldin)

import argparse  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402

import pyogrio  # noqa: E402

SHP_QOSHIMCHA = (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix", ".sbn", ".sbx")
SHP_CHEGARA = 2 * 1024**3  # shapefile .shp/.dbf 2 GB dan oshmasligi kerak

# shp da ustun nomini o'zgartirish: {gpkg dagi nomi: shp dagi nomi} (10 belgigacha).
# gpkg da bo'lmagan ustun e'tiborsiz qoladi.
SHP_NOMLAR = {
    "uniqueid": "unique_id",
    "season": "mavsum",
    "turi": "crop",
    "hosil": "yield",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def fayl_nomi(viloyat: str) -> str:
    """"Farg'ona viloyati" -> "fargona_viloyati" (shp uchun xavfsiz ASCII nom)."""
    s = viloyat.strip().lower()
    s = re.sub(r"[ʻʼ‘’'`]", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "nomsiz"


def shp_ochir(asos: Path) -> None:
    for q in SHP_QOSHIMCHA:
        p = asos.with_suffix(q)
        if p.exists():
            p.unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="gpkg ni viloyatlar bo'yicha alohida shp larga ajratish")
    ap.add_argument("kirish", nargs="?", help="kirish gpkg (berilmasa so'raladi)")
    ap.add_argument("--chiqish", help="natija papkasi (standart: kirish yonida <nomi>_viloyatlar_shp)")
    ap.add_argument("--qatlam", help="gpkg qatlami (standart: birinchisi)")
    ap.add_argument("--viloyat-ustuni", default="viloyat", help="viloyat nomi qaysi ustunda")
    ap.add_argument("--ustiga-yoz", action="store_true", help="shp lar bor bo'lsa ham ustiga yozish")
    ap.add_argument("--nom", action="append", default=[], metavar="ESKI=YANGI",
                    help="shp da ustun nomini o'zgartirish (SHP_NOMLAR ga qo'shiladi); bir necha marta berish mumkin")
    ap.add_argument("--nomlamasdan", action="store_true", help="SHP_NOMLAR ishlatilmasin (faqat --nom)")
    a = ap.parse_args(argv)

    kirish_str = a.kirish or input("gpkg fayl yo'li: ").strip().strip('"')
    kirish = Path(kirish_str)
    if not kirish.exists():
        sys.exit(f"Kirish fayli topilmadi: {kirish}")
    qatlam = a.qatlam or pyogrio.list_layers(kirish)[0, 0]
    chiqish = Path(a.chiqish) if a.chiqish else kirish.parent / f"{kirish.stem}_viloyatlar_shp"
    vil_ust = a.viloyat_ustuni

    info = pyogrio.read_info(kirish, layer=qatlam)
    if vil_ust not in list(info["fields"]):
        sys.exit(f"'{vil_ust}' ustuni yo'q. Bor ustunlar: {list(info['fields'])}")
    maydonlar = list(info["fields"])
    nomlar_map = {} if a.nomlamasdan else dict(SHP_NOMLAR)
    for s in a.nom:
        if "=" not in s:
            sys.exit(f"--nom ESKI=YANGI ko'rinishida bo'lsin: {s}")
        eski, yangi = (x.strip() for x in s.split("=", 1))
        nomlar_map[eski] = yangi
    yoq = [e for e in nomlar_map if e not in maydonlar]
    if yoq:
        log(f"Diqqat: gpkg da yo'q, nomlanmaydi: {yoq}")
    nomlar_map = {e: y for e, y in nomlar_map.items() if e in maydonlar and e != y}
    shp_ustunlar = [nomlar_map.get(f, f) for f in maydonlar]
    takror = sorted({c for c in shp_ustunlar if [x.lower() for x in shp_ustunlar].count(c.lower()) > 1})
    if takror:
        sys.exit(f"Nomlashdan keyin ustun nomi takrorlanadi: {takror}  (nomlar: {nomlar_map})")
    if nomlar_map:
        log("shp da nomlanadi: " + ", ".join(f"{e} -> {y}" for e, y in nomlar_map.items()))
    uzun = [f for f in shp_ustunlar if len(f) > 10]
    if uzun:
        log(f"Diqqat: shp da ustun nomi 10 belgigacha qisqaradi: {uzun}")

    log(f"Kirish: {kirish}  (qatlam {qatlam}, {info['features']} kontur, {info['crs']})")
    vil = pyogrio.read_dataframe(kirish, layer=qatlam, columns=[vil_ust], read_geometry=False)[vil_ust]
    if vil.isna().any():
        log(f"Diqqat: {int(vil.isna().sum())} konturda viloyat bo'sh — ular hech qaysi shp ga tushmaydi")
    viloyatlar = sorted(vil.dropna().unique())
    log(f"Viloyatlar ({len(viloyatlar)}): {', '.join(viloyatlar)}")

    nomlar = {v: fayl_nomi(v) for v in viloyatlar}
    if len(set(nomlar.values())) != len(nomlar):
        sys.exit(f"Ikki viloyat bir xil fayl nomiga tushdi: {nomlar}")
    bor = [chiqish / f"{n}.shp" for n in nomlar.values() if (chiqish / f"{n}.shp").exists()]
    if bor and not a.ustiga_yoz:
        sys.exit(f"Natija shp lar allaqachon bor: {chiqish}\n  Ustiga yozish uchun --ustiga-yoz qo'shing.")
    chiqish.mkdir(parents=True, exist_ok=True)

    jami = 0
    for v in viloyatlar:
        t0 = time.time()
        v_sql = v.replace("'", "''")
        gdf = pyogrio.read_dataframe(kirish, layer=qatlam, where=f"\"{vil_ust}\" = '{v_sql}'")
        gdf = gdf.rename(columns=nomlar_map)
        asos = chiqish / f"{nomlar[v]}.shp"
        shp_ochir(asos)
        pyogrio.write_dataframe(gdf, asos, driver="ESRI Shapefile", encoding="UTF-8")
        hajm = max(asos.stat().st_size, asos.with_suffix(".dbf").stat().st_size)
        if hajm >= SHP_CHEGARA:
            log(f"  XATO: {asos.name} 2 GB dan katta — shp buzilgan bo'lishi mumkin, gpkg da qoldiring")
        maydon = f", {gdf['maydon'].sum():,.0f} ga" if "maydon" in gdf.columns else ""
        log(f"  {v}: {len(gdf)} kontur{maydon} -> {asos.name} ({hajm / 1024**2:,.0f} MB, {time.time() - t0:.0f} s)")
        jami += len(gdf)

    log(f"Tayyor: {jami} / {info['features']} kontur yozildi -> {chiqish}")
    if jami != info["features"] - int(vil.isna().sum()):
        log("Diqqat: yozilgan kontur soni kirishdagidan farq qiladi!")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
