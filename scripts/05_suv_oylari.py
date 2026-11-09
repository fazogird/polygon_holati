"""
05: Konturlarga suv oylari — FAQAT suv_boshi / suv_oxiri (va Ozuqa/Bug'doy ustidagi Paxta uchun season) yangilanadi.

Geometriya, qolgan ustunlar, fid va uniqueid o'zgarmaydi: kirish GPKG nusxalanadi va nusxada SQL UPDATE qilinadi.
Asl faylga tegilmaydi. Qoidalar: config/suv_oylari.yaml; hisob: src/fenologiya/suv.py.
Shu ishni qadamma-qadam: notebooks/suv_oylari.ipynb

Kirish:  bitta GPKG (standart: ../bir_ikki_lamchi/natija/ekin_yerlar_qisqa.gpkg)
Chiqish: kirish yonida <nom>_<versiya>_fenologiya.gpkg va <nom>_<versiya>_fenologiya_ozgarish.csv

python scripts/05_suv_oylari.py                       (v3)
python scripts/05_suv_oylari.py --quruq               (faqat jadval, GPKG yozilmaydi)
python scripts/05_suv_oylari.py --kirish F.gpkg --versiya v4
"""
import os, sys, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
import pandas as pd
from fenologiya import suv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kirish", help="GPKG (standart: ../bir_ikki_lamchi/natija/ekin_yerlar_qisqa.gpkg)")
    ap.add_argument("--versiya", default="v3")
    ap.add_argument("--chiqish", help="chiqish papkasi (standart: kirish fayl papkasi)")
    ap.add_argument("--quruq", action="store_true", help="GPKG yozmasdan faqat jadval")
    a = ap.parse_args()
    kirish = os.path.abspath(a.kirish or suv.standart_kirish())
    od = a.chiqish or os.path.dirname(kirish); os.makedirs(od, exist_ok=True)
    nom = f"{os.path.splitext(os.path.basename(kirish))[0]}_{a.versiya}_fenologiya"

    cfg, zm = suv.sozlamalar()
    df, mc = suv.oqi(kirish)
    print(f"Kirish: {kirish} — {len(df)} kontur (mavsum ustuni: {mc})")
    for x in suv.nomlarni_tekshir(df, cfg, zm):
        print("OGOHLANTIRISH:", x)
    G = suv.geom_oqi(kirish, mc)
    df, _ = suv.hisobla(df, G, cfg, zm)

    T = suv.ozgarish_jadvali(df)
    out_csv = os.path.join(od, nom + "_ozgarish.csv"); T.to_csv(out_csv, index=False, encoding="utf-8-sig")
    d = df[df.mavsum.notna()]
    oy_ozg = (d.suv_boshi.fillna(-1) != d.b.fillna(-1)) | (d.suv_oxiri.fillna(-1) != d.o.fillna(-1))
    print(f"O'zgargan: oylar {oy_ozg.sum()}, mavsum {(d.mavsum != d.yangi_mavsum).sum()} / {len(d)} kontur; "
          f"mavsumsiz {df.mavsum.isna().sum()} — tegilmadi")
    with pd.option_context("display.width", 220, "display.max_rows", 400):
        print(d.assign(yangi=[suv.oy_matn(b, o) for b, o in zip(d.b, d.o)])
              .groupby(["yangi_mavsum", "yangi"]).agg(kontur=("uniqueid", "size"), maydon_ga=("maydon", "sum"))
              .round().astype(int).to_string())
    print(f"-> {out_csv}")
    if a.quruq:
        print("--quruq: GPKG yozilmadi"); return

    dst = os.path.join(od, nom + ".gpkg")
    h = suv.gpkg_yangila(kirish, dst, df, mc)
    print(f"-> {dst}  yangilangan qatorlar: {h}")
    print("Tekshiruv (suv/season dan boshqa farq qilgan qatorlar):", suv.faqat_suv_farqi(kirish, dst))


if __name__ == "__main__":
    main()
