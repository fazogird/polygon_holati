"""
03b: NDVI chiziqli grafiklari (tekshirish uchun) — tanlangan yoki namunaviy konturlar.

Nuqtalar: har sana NDVI (shaffofligi = dalaning toza ulushi). 04 natijasi bo'lsa: qizil chiziq — silliq NDVI,
pastdagi qizil tasma — kontur mavsumi uchun topilgan faol oraliq, sarlavhada NDVI bo'yicha suv oylari.
04 bo'lmasa: ko'k chiziq — 3 nuqtali surilma median.
Fon: Birlamchi oynasi (mart–may) yashil, Ikkilamchi oynasi (iyun–oktyabr) to'q sariq.

python scripts/03b_grafik.py --tuman "Jomboy tumani"                       (har ekin turidan 1 tadan namuna)
python scripts/03b_grafik.py --tuman "Jomboy tumani" --uniqueid ID1 ID2    (aniq konturlar)
Chiqish: data/natija/grafik_<tuman>_<vaqt>.png
"""
import os, sys, argparse, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fenologiya.muhit  # noqa: F401
import numpy as np, pandas as pd, pyogrio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fenologiya import sozlama as S

NAMUNA = ["Bug'doy", "Ikkilamchi ekin aniqlanmagan", "Mosh", "Makka", "Birlamchi ekin aniqlanmagan",
          "Kartoshka", "Bog'", "Beda", "Boshqa", "Paxta", "Loviya", "Sholi"]


def tanla(k, q, n_max=9, seed=1):
    obs = q[q.toza_piksel / q.jami_piksel >= 0.5].groupby("uniqueid").size()
    kk = k[k.uniqueid.isin(obs[obs >= 30].index) & (k.maydon >= 1)]
    out = []
    for t in NAMUNA:
        s = kk[kk.turi == t]
        if len(s):
            out.append(s.sample(1, random_state=seed).uniqueid.iloc[0])
        if len(out) >= n_max:
            break
    return out


def chiz(k, q, ids, yil, out, fen=None, sil=None, anonim=False):
    n = len(ids); cols = 3; rows = int(np.ceil(n / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(5.2 * cols, 3.2 * rows), dpi=130, squeeze=False, sharey=True)
    for ax in axs.ravel()[n:]:
        ax.axis("off")
    for ax, uid in zip(axs.ravel(), ids):
        r = k[k.uniqueid == uid].iloc[0]
        d = q[q.uniqueid == uid].sort_values("sana")
        ul = (d.toza_piksel / d.jami_piksel).clip(0, 1).values
        ax.axvspan(pd.Timestamp(f"{yil}-03-01"), pd.Timestamp(f"{yil}-05-31"), color="#E3F1E5", zorder=0)
        ax.axvspan(pd.Timestamp(f"{yil}-06-01"), pd.Timestamp(f"{yil}-10-31"), color="#FBE5D6", zorder=0)
        ax.scatter(d.sana, d.ndvi, s=14, c="#2F5597", alpha=np.clip(0.25 + 0.75 * ul, 0, 1), zorder=3)
        sarlavha2 = ""
        if sil is not None and fen is not None:          # 04 natijasi: silliq chiziq + topilgan faol oraliq
            ss = sil[sil.uniqueid == uid]
            ax.plot(ss.sana, ss.ndvi_silliq, color="#C00000", lw=1.6, zorder=4)
            f = fen[fen.uniqueid == uid]
            if len(f) and f.faol.iloc[0] == 1:
                ax.axvspan(f.boshi_sana.iloc[0], f.oxiri_sana.iloc[0], ymin=0, ymax=0.06, color="#C00000", zorder=5)
                sarlavha2 = f" | NDVI suv: {int(f.suv_boshi_ndvi.iloc[0])}-{int(f.suv_oxiri_ndvi.iloc[0])} ({f.yorliq_mos.iloc[0]})"
            elif len(f):
                sarlavha2 = " | shu mavsumda faol emas"
        else:
            ax.plot(d.sana, d.ndvi.rolling(3, center=True, min_periods=1).median(), color="#2F5597", lw=1.4, zorder=2)
        ax.set_ylim(-0.1, 1.0); ax.grid(alpha=0.3)
        idq = "" if anonim else f"{uid[:8]}…  "
        ax.set_title(f"{r.turi} | {r.mavsum} | {r.maydon:.1f} ga{sarlavha2}\n{idq}({len(d)} kuzatuv)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m"))
    fig.suptitle("NDVI (Sentinel-2, 10 m) — yashil fon: Birlamchi (3–5), sariq: Ikkilamchi (6–10)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, facecolor="white"); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuman", required=True)
    ap.add_argument("--uniqueid", nargs="*")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--anonim", action="store_true", help="kontur ID larsiz (README / ommaviy hujjat uchun)")
    ap.add_argument("--chiqish", help="chiqish fayli (standart: data/natija/grafik_<tuman>_<vaqt>.png)")
    a = ap.parse_args()
    sl = S.slug(a.tuman); s = S.yuklash()
    k = pyogrio.read_dataframe(S.yol("data", "kirish", f"konturlar_{sl}.gpkg"), layer="konturlar", read_geometry=False)
    q = pd.read_parquet(S.yol("data", "oraliq", f"qator_{sl}.parquet"))
    ids = a.uniqueid or tanla(k, q, seed=a.seed)
    out = a.chiqish or S.yol("data", "natija", f"grafik_{sl}_{datetime.datetime.now():%Y%m%d_%H%M%S}.png")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fp, sp = S.yol("data", "natija", f"fenologiya_{sl}.parquet"), S.yol("data", "oraliq", f"silliq_{sl}.parquet")
    fen = pd.read_parquet(fp) if os.path.exists(fp) else None
    sil = pd.read_parquet(sp) if os.path.exists(sp) else None
    chiz(k, q, ids, s["davr"]["boshi"][:4], out, fen, sil, anonim=a.anonim)
    print(f"{len(ids)} kontur" + ("" if a.anonim else f": {[(k.loc[k.uniqueid == i, 'turi'].iloc[0], i) for i in ids]}") + f"\n-> {out}")


if __name__ == "__main__":
    main()
