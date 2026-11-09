"""
04d: Zona bo'yicha NDVI ekin kalendari — agronom bilan kelishish uchun (zonalar: config/zonalar.yaml).

Har zona × mavsum × ekin turi:
  kontur soni, maydon (ga), faol %, NDVI faol davr boshi / oxiri (median va 25–75%), NDVI bo'yicha eng ko'p
  uchraydigan oylar, HOZIRGI qat'iy oylar (asl faylda, masalan 3-5) va TAKLIF oylar, mos / farqli / faol_emas %.
Har zona × mavsum (barcha ekinlar) — xulosa qatori.

TAKLIF qoidasi (maydon bilan tortilgan): boshi = faol konturlar boshlanish sanasining 25-persentili oyi,
oxiri = tugash sanasining 75-persentili oyi — ya'ni maydonning ko'p qismining faol davrini qamraydi.
Boshlanish davr boshiga (1-fevral) to'g'ri kelsa "≤2" (ekin fevraldan oldin ham faol bo'lgan).
Faqat `ishonch = yuqori` konturlar.

Chiqish: data/natija/eksport/zona_kalendar.xlsx (Xulosa + har zona varag'i) — openpyxl bo'lmasa CSV lar.

python scripts/04d_zona_kalendar.py                    (barcha 04 natijalari)
python scripts/04d_zona_kalendar.py --min_kontur 20    (kichik guruhlarni ham ko'rsatish; standart 30)
"""
import os, sys, argparse, glob, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
import numpy as np, pandas as pd, yaml
from fenologiya import sozlama as S

MAVSUMLAR = ["Birlamchi ekin", "Ikkilamchi ekin", "Mavsumiy ekin"]
try:                                   # Windows konsoli (cp1251/cp866) "×", "≤" ni chiqara olsin
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def zonalar():
    with open(S.yol("config", "zonalar.yaml"), encoding="utf-8") as f:
        z = yaml.safe_load(f)
    return {(vil, tm): zona for vil, zz in z.items() for zona, tlar in zz.items() for tm in tlar}


def wq(x, w, p):
    """Maydon bilan tortilgan persentil."""
    x, w = np.asarray(x, float), np.asarray(w, float)
    m = ~np.isnan(x) & ~np.isnan(w)
    if not m.any():
        return np.nan
    i = np.argsort(x[m]); xs, ws = x[m][i], w[m][i]
    c = np.cumsum(ws) / ws.sum()
    return float(xs[np.searchsorted(c, p, side="left").clip(0, len(xs) - 1)])


def guruh(g, yil, d0, qatiy):
    f = g[g.faol == 1]
    sana = lambda doy: (pd.Timestamp(f"{yil}-01-01") + pd.Timedelta(days=int(round(doy)) - 1)) if doy == doy else None
    fmt = lambda doy: "—" if doy != doy else sana(doy).strftime("%d.%m")
    b25, b50, b75 = (wq(f.b, f.maydon, p) for p in (.25, .5, .75))
    e25, e50, e75 = (wq(f.e, f.maydon, p) for p in (.25, .5, .75))
    if len(f):
        tb = "≤2" if b25 <= d0 else str(sana(b25).month)
        taklif = f"{tb}-{sana(e75).month}"
    else:
        taklif = "—"
    vc = g.yorliq_mos.value_counts(normalize=True)
    top = f.oylar.value_counts(normalize=True).head(2)
    return {"kontur": len(g), "maydon_ga": round(g.maydon.sum()), "faol_%": round(100 * len(f) / len(g)) if len(g) else 0,
            "NDVI_boshi (median)": fmt(b50), "boshi 25–75%": f"{fmt(b25)}–{fmt(b75)}",
            "NDVI_oxiri (median)": fmt(e50), "oxiri 25–75%": f"{fmt(e25)}–{fmt(e75)}",
            "NDVI oylar (eng ko'p)": "; ".join(f"{k} ({v:.0%})" for k, v in top.items()),
            "hozirgi (asl fayl)": f"{qatiy[0]}-{qatiy[1]}", "TAKLIF": taklif,
            "mos_%": round(100 * vc.get("mos", 0)), "farqli_%": round(100 * vc.get("farqli", 0)),
            "faol_emas_%": round(100 * vc.get("faol_emas", 0))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min_kontur", type=int, default=30)
    a = ap.parse_args()
    s = S.yuklash(); yil = int(s["davr"]["boshi"][:4]); d0 = pd.Timestamp(s["davr"]["boshi"]).day_of_year
    qo = s["fenologiya"]["qatiy_oyna"]
    fl = sorted(glob.glob(S.yol("data", "natija", "fenologiya_*.parquet")))
    if not fl:
        raise SystemExit("04 natijasi yo'q — avval: pipeline.py fenologiya --hammasi")
    R = pd.concat([pd.read_parquet(f) for f in fl], ignore_index=True)
    Z = zonalar()
    R["zona"] = [Z.get((v, t), f"{v} — belgilanmagan") for v, t in zip(R.viloyat, R.tuman)]
    yoq = R.loc[R.zona.str.endswith("belgilanmagan"), ["viloyat", "tuman"]].drop_duplicates()
    if len(yoq):
        print("OGOHLANTIRISH: zonalar.yaml da yo'q tumanlar:", yoq.values.tolist())
    R = R[R.mavsum.isin(MAVSUMLAR) & (R.ishonch == "yuqori")].copy()
    R["b"] = pd.to_datetime(R.boshi_sana).dt.day_of_year; R["e"] = pd.to_datetime(R.oxiri_sana).dt.day_of_year
    R["oylar"] = np.where(R.faol == 1, R.suv_boshi_ndvi.astype("Int64").astype(str) + "-" + R.suv_oxiri_ndvi.astype("Int64").astype(str), None)
    print(f"04 natijasi: {R.tuman.nunique()} tuman, {len(R)} kontur (ishonch = yuqori)")

    xul, varaq = [], {}
    for zona, gz in R.groupby("zona"):
        rows = []
        for mav in MAVSUMLAR:
            gm = gz[gz.mavsum == mav]
            if gm.empty:
                continue
            r = {"mavsum": mav, "turi": "* BARCHA EKINLAR", **guruh(gm, yil, d0, qo[mav])}
            rows.append(r); xul.append({"zona": zona, "tumanlar": gz.tuman.nunique(), **r})
            for tur, gt in sorted(gm.groupby("turi"), key=lambda x: -x[1].maydon.sum()):
                if len(gt) >= a.min_kontur:
                    rows.append({"mavsum": mav, "turi": tur, **guruh(gt, yil, d0, qo[mav])})
        varaq[zona] = pd.DataFrame(rows)
    X = pd.DataFrame(xul)

    od = S.yol("data", "natija", "eksport"); os.makedirs(od, exist_ok=True)
    try:
        import openpyxl  # noqa: F401
        out = os.path.join(od, "zona_kalendar.xlsx")
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            X.to_excel(w, sheet_name="Xulosa", index=False)
            for zona, df in varaq.items():
                df.to_excel(w, sheet_name=re.sub(r"[\\/*?:\[\]']", "", zona)[:31], index=False)
            for ws in w.book.worksheets:
                ws.freeze_panes = "A2"
                for col in ws.columns:
                    ws.column_dimensions[col[0].column_letter].width = min(42, max(10, max(len(str(c.value or "")) for c in col) + 2))
        print(f"-> {out}")
    except ImportError:
        X.to_csv(os.path.join(od, "zona_kalendar_xulosa.csv"), index=False, encoding="utf-8-sig")
        for zona, df in varaq.items():
            df.to_csv(os.path.join(od, f"zona_kalendar_{S.slug(zona)}.csv"), index=False, encoding="utf-8-sig")
        print(f"-> {od}\\zona_kalendar_*.csv  (Excel uchun: conda install -n fenologiya -c conda-forge openpyxl)")
    with pd.option_context("display.width", 250, "display.max_rows", 200, "display.max_colwidth", 30):
        print("\nXULOSA (zona × mavsum, barcha ekinlar):")
        print(X[["zona", "mavsum", "kontur", "maydon_ga", "faol_%", "NDVI_boshi (median)", "NDVI_oxiri (median)",
                 "hozirgi (asl fayl)", "TAKLIF", "farqli_%", "faol_emas_%"]].to_string(index=False))


if __name__ == "__main__":
    main()
