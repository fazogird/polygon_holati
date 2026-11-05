"""
Barcha (yoki tanlangan) tumanlar uchun pipeline: 01 konturlar -> 02 sahnalar -> 03 indeks vaqt qatori.

- Tumanlar ketma-ket ishlanadi; har qadam alohida jarayonda (xotira tozalanadi).
- DAVOM ETTIRISH: natija fayli bor qadam o'tkazib yuboriladi — run to'xtasa, xuddi shu buyruqni qayta bering.
  Qaytadan hisoblash uchun: --qayta
- Bir tuman xato bersa, keyingisiga o'tiladi; oxirida jadval: qaysi tuman tayyor, qaysi xato.
- Jurnal: logs/pipeline_<sana>.log, holat: logs/holat.csv

Buyruqlar (muhit yoqilgan terminalda yoki python o'rniga .\\run.bat):
  python pipeline.py royxat [--viloyat "Samarqand viloyati"]          tumanlar, holati, taxminiy vaqt
  python pipeline.py indeks --tuman "Jomboy tumani" "Urgut tumani"
  python pipeline.py indeks --viloyat "Samarqand viloyati" [--ishchi 6]
  python pipeline.py indeks --hammasi
"""
import os, sys, csv, time, argparse, datetime, subprocess
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
import fenologiya.muhit  # noqa: F401
import pyogrio
from fenologiya import sozlama as S

SEK_PER_MPX = 96          # Jomboy o'lchovi: 9.76 mln piksel to'r, fevral–oktyabr, 6 oqim -> 934 s


def fayllar(sl):
    return {"01": S.yol("data", "kirish", f"konturlar_{sl}.gpkg"),
            "02": S.yol("data", "oraliq", f"sahnalar_{sl}.json"),
            "03": S.yol("data", "oraliq", f"qator_{sl}.parquet")}


def tumanlar(s, viloyat=None, tanlangan=None, olcham=False):
    src = S.kirish_yoli(s)
    t = pyogrio.read_dataframe(src, layer="ekin_yerlar", columns=["viloyat", "tuman"], read_geometry=olcham)
    if viloyat:
        t = t[t.viloyat == viloyat]
    if tanlangan:
        t = t[t.tuman.isin(tanlangan)]
    g = t.groupby(["viloyat", "tuman"])
    res = g.size().rename("kontur").reset_index()
    if olcham:
        tb = t.to_crs(S.CRS).groupby("tuman").geometry.apply(lambda x: x.total_bounds)
        res["mpx"] = res.tuman.map(lambda tm: (tb[tm][2] - tb[tm][0]) * (tb[tm][3] - tb[tm][1]) / 100 / 1e6)
    return res.sort_values(["viloyat", "tuman"]).reset_index(drop=True)


def royxat(a, s):
    r = tumanlar(s, a.viloyat, olcham=True)
    r["taxminiy_daq"] = (r.mpx * SEK_PER_MPX / 60).round(0).astype(int)
    for q in ("01", "02", "03"):
        r[q] = [("tayyor" if os.path.exists(fayllar(S.slug(tm))[q]) else "-") for tm in r.tuman]
    import pandas as pd
    with pd.option_context("display.max_rows", 200, "display.width", 200):
        print(r.drop(columns="mpx").to_string(index=False))
    qolgan = r[r["03"] != "tayyor"]
    print(f"\nJami {len(r)} tuman, {int(r.kontur.sum())} kontur | 03 tayyor: {int((r['03'] == 'tayyor').sum())}"
          f" | qolgan {len(qolgan)} tuman, taxminan {qolgan.taxminiy_daq.sum() / 60:.1f} soat (ishxona interneti)")


class Jurnal:
    def __init__(self, teg="tanlangan"):
        os.makedirs(S.yol("logs"), exist_ok=True)       # parallel run'lar aralashmasin: nomda viloyat
        self.f = open(S.yol("logs", f"pipeline_{teg}_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"), "a", encoding="utf-8")
    def __call__(self, m=""):
        print(m, flush=True); self.f.write(m + "\n"); self.f.flush()


def holat_yoz(tuman, qadam, holat, sek):
    p = S.yol("logs", "holat.csv"); yangi = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if yangi:
            w.writerow(["vaqt", "tuman", "qadam", "holat", "soniya"])
        w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), tuman, qadam, holat, round(sek)])


def qadam(log, nom, args):
    t = time.time()
    p = subprocess.Popen([sys.executable, os.path.join(ROOT, "scripts", nom)] + args, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    for line in p.stdout:
        line = line.rstrip()
        if any(x in line for x in ("GDAL_DATA", "gdalvrt", "Could not parse bucket", "warnings.warn", "NotGeoreferenced", "dest = _reproject")):
            continue
        log("    " + line)
    p.wait()
    return p.returncode == 0, time.time() - t


def indeks(a, s):
    r = tumanlar(s, a.viloyat, a.tuman if a.tuman else None)
    if not a.hammasi and not a.viloyat and not a.tuman:
        raise SystemExit("--tuman, --viloyat yoki --hammasi bering")
    if r.empty:
        raise SystemExit("Tuman topilmadi (nomini `python pipeline.py royxat` dan oling)")
    log = Jurnal(S.slug(a.viloyat) if a.viloyat else ("hammasi" if a.hammasi else "tanlangan")); t0 = time.time(); xulosa = []
    log(f"PIPELINE indeks — {len(r)} tuman — {datetime.datetime.now():%Y-%m-%d %H:%M} | davr {s['davr']['boshi']}..{s['davr']['oxiri']}")
    for i, row in r.iterrows():
        tm = row.tuman; sl = S.slug(tm); f = fayllar(sl); holat = "tayyor"
        log(f"\n[{i + 1}/{len(r)}] {row.viloyat} / {tm} ({row.kontur} kontur)")
        rejalar = [("01", "01_geom_tayyorlash.py", ["--tuman", tm]),
                   ("02", "02_stac_qidiruv.py", ["--tuman", tm]),
                   ("03", "03_indeks_qator.py", ["--tuman", tm, "--ishchi", str(a.ishchi)])]
        for q, sk, args in rejalar:
            if os.path.exists(f[q]) and not a.qayta:
                log(f"  {q}: bor, o'tkazildi"); continue
            log(f"  {q}: {sk}")
            ok, sek = qadam(log, sk, args)
            holat_yoz(tm, q, "ok" if ok else "XATO", sek)
            if not ok:
                holat = f"XATO ({q})"; log(f"  !!! {q} xato bilan tugadi — keyingi tumanga o'tiladi"); break
            log(f"  {q}: tayyor ({sek:.0f} s)")
        xulosa.append((tm, holat))
    log(f"\n=== XULOSA ({(time.time() - t0) / 60:.1f} daqiqa) ===")
    for tm, h in xulosa:
        log(f"  {h:12s} {tm}")
    xato = [tm for tm, h in xulosa if h != "tayyor"]
    log(f"Tayyor: {len(xulosa) - len(xato)} / {len(xulosa)}" + (f" | xato: {xato} — buyruqni qayta bering" if xato else ""))


def main():
    ap = argparse.ArgumentParser(description="ekin_fenologiya pipeline (README.md)")
    sub = ap.add_subparsers(dest="buyruq", required=True)
    r = sub.add_parser("royxat", help="tumanlar, holati va taxminiy vaqt")
    r.add_argument("--viloyat")
    i = sub.add_parser("indeks", help="01 -> 02 -> 03 tanlangan tumanlar uchun")
    i.add_argument("--tuman", nargs="*"); i.add_argument("--viloyat"); i.add_argument("--hammasi", action="store_true")
    i.add_argument("--ishchi", type=int, default=6); i.add_argument("--qayta", action="store_true")
    a = ap.parse_args(); s = S.yuklash()
    royxat(a, s) if a.buyruq == "royxat" else indeks(a, s)


if __name__ == "__main__":
    main()
