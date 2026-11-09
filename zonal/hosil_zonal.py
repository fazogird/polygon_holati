"""Hosildorlik rasterlarini ekin konturlariga yozish (zonal mean).

Har bir konturga bitta ustun (`hosil`, s/ga) yoziladi: kontur ichidagi
piksellarning o'rtachasi. Bug'doy konturiga faqat bug'doy rasteri,
paxta konturiga faqat paxta rasteri; boshqa ekinlarda ustun bo'sh qoladi.

Qaysi piksellar olinadi: markazi kontur ichida bo'lgan piksellar
(all_touched=False). Nodata (255) va 0 olinmaydi.

Ishga tushirish (loyiha ildizidan):
    .\\run.bat zonal\\hosil_zonal.py
    .\\run.bat zonal\\hosil_zonal.py --config zonal\\hosil.yaml
    .\\run.bat zonal\\hosil_zonal.py --kirish A.gpkg --chiqish B.gpkg
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import rasterio
import yaml
from rasterio.features import geometry_mask
from rasterio.windows import Window

BU_PAPKA = Path(__file__).resolve().parent
BLOK = 4096  # bir martada o'qiladigan raster bo'lagi (piksel), ~12 km


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def zonal_mean(geoms, src: rasterio.io.DatasetReader) -> np.ndarray:
    """Har bir geometriya uchun ichidagi valid piksellar o'rtachasi (yo'q bo'lsa NaN).

    `geoms` raster CRS ida bo'lishi kerak (GeoSeries). Konturlar bbox markazi
    bo'yicha BLOK x BLOK katakchalarga guruhlanadi, har katak uchun raster bir
    marta o'qiladi — tarmoq diskidan o'qish shu bilan tejaladi.
    """
    n = len(geoms)
    natija = np.full(n, np.nan, dtype="float64")
    if n == 0:
        return natija

    T = src.transform
    nodata = src.nodata
    b = geoms.bounds.to_numpy()  # minx, miny, maxx, maxy
    cx = (b[:, 0] + b[:, 2]) / 2
    cy = (b[:, 1] + b[:, 3]) / 2
    kat_col = np.floor((cx - T.c) / T.a / BLOK).astype(np.int64)
    kat_row = np.floor((cy - T.f) / T.e / BLOK).astype(np.int64)
    katak = pd.Series(np.arange(n)).groupby([kat_row, kat_col])

    toliq = Window(0, 0, src.width, src.height)
    geom_arr = geoms.to_numpy()
    for _, idx in katak:
        idx = idx.to_numpy()
        bb = b[idx]
        # katakdagi hamma konturlarni qoplaydigan oyna (piksel)
        c0 = math.floor((bb[:, 0].min() - T.c) / T.a)
        c1 = math.ceil((bb[:, 2].max() - T.c) / T.a)
        r0 = math.floor((bb[:, 3].max() - T.f) / T.e)
        r1 = math.ceil((bb[:, 1].min() - T.f) / T.e)
        try:
            win = Window(c0, r0, c1 - c0, r1 - r0).intersection(toliq)
        except rasterio.errors.WindowError:
            continue  # katak butunlay raster tashqarisida
        arr = src.read(1, window=win)
        wT = src.window_transform(win)
        wc0, wr0 = int(win.col_off), int(win.row_off)

        for i in idx:
            g = geom_arr[i]
            if g is None or g.is_empty:
                continue
            minx, miny, maxx, maxy = b[i]
            pc0 = max(math.floor((minx - T.c) / T.a) - wc0, 0)
            pc1 = min(math.ceil((maxx - T.c) / T.a) - wc0, arr.shape[1])
            pr0 = max(math.floor((maxy - T.f) / T.e) - wr0, 0)
            pr1 = min(math.ceil((miny - T.f) / T.e) - wr0, arr.shape[0])
            if pc1 <= pc0 or pr1 <= pr0:
                continue
            sub = arr[pr0:pr1, pc0:pc1]
            subT = wT * rasterio.Affine.translation(pc0, pr0)
            ichida = geometry_mask([g], out_shape=sub.shape, transform=subT,
                                   invert=True, all_touched=False)
            v = sub[ichida]
            if nodata is not None:
                v = v[v != nodata]
            v = v[v != 0]
            if v.size:
                natija[i] = float(v.mean())
    return natija


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Hosildorlik rasterlarini konturlarga yozish (zonal mean)")
    ap.add_argument("--config", default=str(BU_PAPKA / "hosil.yaml"), help="sozlama fayli (yaml)")
    ap.add_argument("--kirish", help="kirish gpkg (configdagini almashtiradi)")
    ap.add_argument("--chiqish", help="natija gpkg (configdagini almashtiradi)")
    ap.add_argument("--ustiga-yoz", action="store_true", help="natija fayli bor bo'lsa ham ustiga yozish")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load(Path(a.config).read_text(encoding="utf-8"))
    kirish = Path(a.kirish or cfg["kirish"])
    chiqish = Path(a.chiqish or cfg["chiqish"])
    qatlam = cfg.get("qatlam") or pyogrio.list_layers(kirish)[0, 0]
    ekin_ust = cfg.get("ekin_ustuni", "turi")
    vil_ust = cfg.get("viloyat_ustuni", "viloyat")
    nat_ust = cfg.get("natija_ustuni", "hosil")
    maydon_ust = cfg.get("maydon_ustuni", "maydon")
    yaxlit = int(cfg.get("yaxlitlash", 2))
    rasterlar: dict = cfg["rasterlar"] or {}

    if not kirish.exists():
        sys.exit(f"Kirish fayli topilmadi: {kirish}")
    if kirish.resolve() == chiqish.resolve():
        sys.exit("Chiqish fayli kirish bilan bir xil bo'lmasin.")
    if chiqish.exists() and not a.ustiga_yoz:
        sys.exit(f"Natija fayli allaqachon bor: {chiqish}\n  Ustiga yozish uchun --ustiga-yoz qo'shing.")
    for ekin, vils in rasterlar.items():
        for vil, rp in (vils or {}).items():
            if not Path(rp).exists():
                sys.exit(f"Raster topilmadi [{ekin} / {vil}]: {rp}")

    log(f"O'qilmoqda: {kirish} (qatlam: {qatlam})")
    gdf = pyogrio.read_dataframe(kirish, layer=qatlam)
    log(f"  {len(gdf):,} kontur, CRS {gdf.crs}")
    if nat_ust in gdf.columns:
        log(f"  Diqqat: '{nat_ust}' ustuni bor edi — qayta hisoblanadi.")

    ekinlar = set(gdf[ekin_ust].dropna().unique())
    viloyatlar = set(gdf[vil_ust].dropna().unique())
    for ekin, vils in rasterlar.items():
        if ekin not in ekinlar:
            log(f"  Diqqat: '{ekin}' ekini '{ekin_ust}' ustunida yo'q — o'tkazib yuboriladi.")
        for vil in (vils or {}):
            if vil not in viloyatlar:
                log(f"  Diqqat: '{vil}' '{vil_ust}' ustunida yo'q — o'tkazib yuboriladi.")

    hosil = np.full(len(gdf), np.nan, dtype="float64")
    hisobot = []
    for ekin, vils in rasterlar.items():
        for vil, rp in (vils or {}).items():
            tanla = np.flatnonzero((gdf[ekin_ust] == ekin).to_numpy() & (gdf[vil_ust] == vil).to_numpy())
            if tanla.size == 0:
                continue
            t0 = time.time()
            with rasterio.open(rp) as src:
                geoms = gdf.geometry.iloc[tanla].to_crs(src.crs)
                qiymat = zonal_mean(geoms, src)
            hosil[tanla] = qiymat
            yozildi = int(np.isfinite(qiymat).sum())
            # vazn: maydon ustuni (ga); bo'lmasa geometriya maydoni (raster CRS, metr)
            if maydon_ust in gdf.columns:
                maydon = gdf[maydon_ust].iloc[tanla].to_numpy(dtype="float64")
            else:
                maydon = geoms.area.to_numpy() / 1e4
            ok = np.isfinite(qiymat) & np.isfinite(maydon) & (maydon > 0)
            hisobot.append({
                "ekin": ekin, "viloyat": vil, "kontur": int(tanla.size), "yozildi": yozildi,
                "bosh_qoldi": int(tanla.size - yozildi),
                "maydon_ga": round(float(np.nansum(maydon[ok])), 1),
                # viloyat hosildorligi: katta kontur ko'proq vazn oladi
                "hosil_maydon_vaznli": round(float(np.average(qiymat[ok], weights=maydon[ok])), 2)
                if ok.any() else None,
                # konturlarning oddiy o'rtachasi: kichik va katta kontur teng
                "hosil_oddiy_ortacha": round(float(np.nanmean(qiymat)), 2) if yozildi else None,
                "hosil_min": round(float(np.nanmin(qiymat)), 2) if yozildi else None,
                "hosil_max": round(float(np.nanmax(qiymat)), 2) if yozildi else None,
                "raster": rp,
            })
            log(f"  {ekin:8s} | {vil:22s} | {tanla.size:6,} kontur, {yozildi:6,} yozildi | "
                f"{time.time() - t0:5.0f} s")

    # float64: float32 da 42.87 -> 42.869998... bo'lib ko'rinadi
    gdf[nat_ust] = np.round(hosil, yaxlit)

    chiqish.parent.mkdir(parents=True, exist_ok=True)
    if chiqish.exists():
        chiqish.unlink()
    log(f"Yozilmoqda: {chiqish}")
    pyogrio.write_dataframe(gdf, chiqish, layer=qatlam, driver="GPKG")

    hdf = pd.DataFrame(hisobot)
    hp = chiqish.with_name(chiqish.stem + "_hosil_hisobot.csv")
    hdf.to_csv(hp, index=False, encoding="utf-8-sig")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(hdf.drop(columns="raster").to_string(index=False))
    log(f"Tayyor. Hisobot: {hp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
