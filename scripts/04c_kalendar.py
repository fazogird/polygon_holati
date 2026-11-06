"""
04c: NDVI asosidagi ekin kalendari — viloyat × ekin turi × mavsum kesimida (agronom bilan tekshirish uchun).

Har guruh: kontur soni, faol ulushi, faol davr boshi/oxiri (median va 25–75% oralig'i, kun.oy), NDVI bo'yicha eng
ko'p uchraydigan suv oylari, qat'iy oylar va mos / farqli / faol_emas ulushi. Faqat `ishonch = yuqori` konturlar.

Chiqish: data/natija/eksport/kalendar_<teg>.csv  (+ ekranda jadval)

python scripts/04c_kalendar.py --tuman "Jomboy tumani"
python scripts/04c_kalendar.py --hammasi            (viloyat kesimida)
  --min_kontur 30     guruhda kamida shuncha kontur bo'lsa ko'rsatiladi
"""
import os, sys, argparse, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
import numpy as np, pandas as pd
from fenologiya import sozlama as S


def kun_oy(doy, yil):
    return "—" if pd.isna(doy) else (pd.Timestamp(f"{yil}-01-01") + pd.Timedelta(days=int(round(doy)) - 1)).strftime("%d.%m")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuman", nargs="*"); ap.add_argument("--viloyat"); ap.add_argument("--hammasi", action="store_true")
    ap.add_argument("--min_kontur", type=int, default=30)
    a = ap.parse_args()
    s = S.yuklash(); yil = int(s["davr"]["boshi"][:4])
    R = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(S.yol("data", "natija", "fenologiya_*.parquet")))], ignore_index=True)
    if a.tuman:
        R = R[R.tuman.isin(a.tuman)]; teg = S.slug(a.tuman[0]) if len(a.tuman) == 1 else "tanlangan"
    elif a.viloyat:
        R = R[R.viloyat == a.viloyat]; teg = S.slug(a.viloyat)
    elif a.hammasi:
        teg = "hammasi"
    else:
        raise SystemExit("--tuman, --viloyat yoki --hammasi bering")
    R = R[R.mavsum.isin(["Birlamchi ekin", "Ikkilamchi ekin", "Mavsumiy ekin"]) & (R.ishonch == "yuqori")].copy()
    R["b"] = pd.to_datetime(R.boshi_sana).dt.day_of_year; R["e"] = pd.to_datetime(R.oxiri_sana).dt.day_of_year
    R["oylar"] = np.where(R.faol == 1, R.suv_boshi_ndvi.astype("Int64").astype(str) + "-" + R.suv_oxiri_ndvi.astype("Int64").astype(str), None)
    rows = []
    for (vil, tur, mav), g in R.groupby(["viloyat", "turi", "mavsum"]):
        if len(g) < a.min_kontur:
            continue
        f = g[g.faol == 1]
        q = lambda c, p: f[c].quantile(p) if len(f) else np.nan
        vc = g.yorliq_mos.value_counts(normalize=True)
        top = f.oylar.value_counts(normalize=True).head(2)
        qo = s["fenologiya"]["qatiy_oyna"][mav]
        rows.append({"viloyat": vil, "turi": tur, "mavsum": mav, "kontur": len(g),
                     "faol_%": round(100 * len(f) / len(g)),
                     "boshi_median": kun_oy(q("b", .5), yil), "boshi_25_75": f"{kun_oy(q('b', .25), yil)}–{kun_oy(q('b', .75), yil)}",
                     "oxiri_median": kun_oy(q("e", .5), yil), "oxiri_25_75": f"{kun_oy(q('e', .25), yil)}–{kun_oy(q('e', .75), yil)}",
                     "ndvi_oylar_kop": "; ".join(f"{k} ({v:.0%})" for k, v in top.items()),
                     "qatiy": f"{qo[0]}-{qo[1]}",
                     "mos_%": round(100 * vc.get("mos", 0)), "farqli_%": round(100 * vc.get("farqli", 0)),
                     "faol_emas_%": round(100 * vc.get("faol_emas", 0))})
    K = pd.DataFrame(rows).sort_values(["viloyat", "mavsum", "kontur"], ascending=[True, True, False])
    od = S.yol("data", "natija", "eksport"); os.makedirs(od, exist_ok=True)
    out = os.path.join(od, f"kalendar_{teg}.csv"); K.to_csv(out, index=False, encoding="utf-8-sig")
    with pd.option_context("display.width", 250, "display.max_rows", 300, "display.max_colwidth", 40):
        print(K.drop(columns="viloyat").to_string(index=False))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
