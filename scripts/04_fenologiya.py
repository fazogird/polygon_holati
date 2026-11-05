"""
04: Fenologiya — har kontur uchun o'z mavsumidagi faol davr va NDVI bo'yicha suv oylari (qaror 0010).

Kirish: data/kirish/konturlar_<tuman>.gpkg, data/oraliq/qator_<tuman>.parquet (03 natijasi)
Chiqish:
  data/natija/fenologiya_<tuman>.parquet — har kontur bitta qator:
    uniqueid, viloyat, tuman, turi, mavsum, maydon,
    faol (1/0: shu mavsumda dala ekilganmi), boshi_sana, oxiri_sana, faol_kun, chuqqi_sana, chuqqi_ndvi,
    suv_boshi_ndvi, suv_oxiri_ndvi (oy), suv_boshi_qatiy, suv_oxiri_qatiy (hozirgi qoida),
    yorliq_mos (mos / farqli / faol_emas), sikl_soni, sikllar (matn), asos_ndvi, boshi_chegarada,
    kuzatuv, oraliqdagi_kuzatuv, ishonch (yuqori / orta / past)
  data/oraliq/silliq_<tuman>.parquet — silliq NDVI har 5 kunda (grafik va Tableau uchun)

python scripts/04_fenologiya.py --tuman "Jomboy tumani"
"""
import os, sys, time, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
import numpy as np, pandas as pd, pyogrio
from fenologiya import sozlama as S
from fenologiya import fen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuman", required=True)
    a = ap.parse_args()
    s = S.yuklash(); cfg = s["fenologiya"]; sl = S.slug(a.tuman); t0 = time.time()
    k = pyogrio.read_dataframe(S.yol("data", "kirish", f"konturlar_{sl}.gpkg"), layer="konturlar", read_geometry=False)
    q = pd.read_parquet(S.yol("data", "oraliq", f"qator_{sl}.parquet"))
    ids = k.uniqueid.values
    Sm, kuz, kunlar, O = fen.kunlik_matritsa(q, ids, s["davr"]["boshi"], s["davr"]["oxiri"], cfg)
    yil = kunlar[0].year
    rows = []
    for i, r in enumerate(k.itertuples(index=False)):
        cyc, asos, _ = fen.sikllar(Sm[i], cfg)
        oral = fen.mavsum_oraliq(cyc, r.mavsum, kunlar, cfg)
        d = dict(uniqueid=r.uniqueid, kuzatuv=int(kuz[i]), sikl_soni=len(cyc), asos_ndvi=round(asos, 3) if asos == asos else None,
                 sikllar="; ".join(f"{kunlar[b]:%m-%d}..{kunlar[e]:%m-%d}" for b, e, _, _ in cyc))
        qo = cfg["qatiy_oyna"].get(r.mavsum)
        d["suv_boshi_qatiy"], d["suv_oxiri_qatiy"] = (qo if qo else (None, None))
        if oral is None:
            d.update(faol=0, yorliq_mos="faol_emas" if r.mavsum in cfg["qatiy_oyna"] else None, oraliqdagi_kuzatuv=0)
        else:
            b, e, p = oral
            sb = max(0, b - int(cfg["oldingi_sugorish_kun"]))
            d.update(faol=1, boshi_sana=kunlar[b], oxiri_sana=kunlar[e], faol_kun=e - b + 1, chuqqi_sana=kunlar[p],
                     chuqqi_ndvi=round(float(Sm[i, p]), 3), suv_boshi_ndvi=kunlar[sb].month, suv_oxiri_ndvi=kunlar[e].month,
                     boshi_chegarada=int(b == 0), oraliqdagi_kuzatuv=int(O[i, b:e + 1].sum()))
            if qo:
                w0, w1 = pd.Timestamp(yil, qo[0], 1), pd.Timestamp(yil, qo[1], 1) + pd.offsets.MonthEnd(0)
                ov = (min(kunlar[e], w1) - max(kunlar[b], w0)).days + 1
                d["yorliq_mos"] = "mos" if ov / (e - b + 1) >= 0.6 else "farqli"
        n_in = d["oraliqdagi_kuzatuv"]
        d["ishonch"] = "yuqori" if kuz[i] >= 25 and (d["faol"] == 0 or n_in >= 3) else ("orta" if kuz[i] >= 15 else "past")
        rows.append(d)
    R = k[["uniqueid", "viloyat", "tuman", "turi", "mavsum", "maydon"]].merge(pd.DataFrame(rows), on="uniqueid")
    os.makedirs(S.yol("data", "natija"), exist_ok=True)
    out = S.yol("data", "natija", f"fenologiya_{sl}.parquet"); R.to_parquet(out, index=False)
    # silliq qator har 5 kunda (grafik / Tableau)
    j = np.arange(0, len(kunlar), 5)
    L = pd.DataFrame({"uniqueid": np.repeat(ids, len(j)), "sana": np.tile(kunlar[j], len(ids)),
                      "ndvi_silliq": Sm[:, j].ravel().round(4)}).dropna()
    L.to_parquet(S.yol("data", "oraliq", f"silliq_{sl}.parquet"), index=False)
    # xulosa
    m = R[R.mavsum.isin(cfg["qatiy_oyna"].keys())]
    print(f"{a.tuman}: {len(R)} kontur | {time.time() - t0:.0f} s -> {out}")
    print(pd.crosstab(m.mavsum, m.yorliq_mos, margins=True).to_string())
    print("ishonch:", R.ishonch.value_counts().to_dict())
    f = m[m.faol == 1]
    print("NDVI bo'yicha suv oylari (faol konturlar, mavsum bo'yicha eng ko'p uchraydigan):")
    print(f.groupby("mavsum").apply(lambda x: (x.suv_boshi_ndvi.astype(int).astype(str) + "-" + x.suv_oxiri_ndvi.astype(int).astype(str))
                                    .value_counts().head(4).to_dict()).to_string())


if __name__ == "__main__":
    main()
