"""Bo'sh qolgan ekin yerlarini qo'shni dalalardan to'ldirish (bufer 1 m -> 10 m, ierarxik).

atribut_otkazish.py dan keyin ishlatiladi: manbaga tegmagani uchun nomenklaturasi (real_name,
real_n1, real_n2, kontur_raq) bo'sh qolgan dalalarga yonidagi to'lgan dalalardan qiymat beradi.

Qoida:
  1. "Bo'sh dala" — USTUNLAR ning hammasi bo'sh. "To'lgan dala" — kamida bittasi bor.
  2. Bo'sh dalaga QADAM_M (1 m) bufer beriladi. Bufer to'lgan dalaga tegsa — shu qadamda
     to'xtaydi; tegmasa 2 m, 3 m, ... MAX_M (10 m) gacha oshiriladi.
  3. Ierarxik tanlash. USTUNLAR yirikdan maydaga tartiblangan (real_name -> real_n1 -> real_n2
     -> kontur_raq). Har daraja uchun tekkan qo'shnilar ichida eng ko'p takrorlangan qiymat va
     uning ulushi (soni bo'yicha) topiladi. Ulushi KELISHUV dan kam bo'lmagan eng chuqur
     darajagacha to'ldiriladi, undan maydaroq ustunlar bo'sh qoladi. Masalan qo'shnilar
     real_name/n1/n2 da kelishib, kontur_raq da kelishmasa — faqat real_name/n1/n2 to'ladi.
     Teng bo'lsa — bufer ichida maydoni kattarog'i, keyin eng yaqini.
  4. Faqat avvaldan to'lgan dalalar qo'shni bo'ladi: yangi to'ldirilgan dala boshqasiga
     manba bo'lmaydi (xato zanjir bo'lib tarqalmasligi uchun).
  5. Masofa haqiqiy metrda: hisob UTM da (KIRISH 3857 bo'lsa ham). Natija geometriyasi,
     CRS i, qator tartibi va boshqa ustunlar o'zgarmaydi. KIRISH o'zgarmaydi.
  6. Har dalaga qanday to'lgani yoziladi (toldi_usul, toldi_dar, qoshni_m, qoshni_n, qoshni_ul).
  7. Sinov (TEKSHIRUV_SONI): to'lgan, chetdagi dalalardan bir qismi bo'sh deb faraz qilinadi va
     shu qoida bilan topilgan qiymat haqiqiysi bilan solishtiriladi — aniqlik hisobotda.
  8. Hisobot Excel ga yoziladi (HISOBOT).

Ishga tushirish (loyiha ildizidan), avval pastdagi KIRISH / CHIQISH ni to'g'rilang:
    .\\run.bat viloyat_shp\\qoshnidan_toldirish.py
"""

from __future__ import annotations

# =====================================================================================
#  FOYDALANUVCHI SOZLAMALARI — har bir viloyat uchun shu yerni o'zgartiring
# =====================================================================================

# Bo'sh dalalari to'ldiriladigan shp (atribut_otkazish.py natijasi). O'zgarmaydi.
KIRISH = r"D:\Tasks\level_otkazish\qash_blok\qashqadaryo_viloyati_v2\qashqadaryo_viloyati_v2.shp"

# Natija shp (yangi fayl; KIRISH bilan bir xil bo'lishi mumkin emas).
CHIQISH = r"D:\Tasks\level_otkazish\qash_blok\qashqadaryo_viloyati_v2\qashqadaryo_viloyati_v3.shp"

# Excel hisobot. None — CHIQISH yonida "<chiqish nomi>_hisobot.xlsx".
HISOBOT = None

# Qo'shnidan to'ldiriladigan ustunlar — YIRIKDAN MAYDAGA tartibda (ierarxiya).
USTUNLAR = ["real_name", "real_n1", "real_n2", "kontur_raq"]

# Kelishuv chegarasi: daraja qiymati tekkan qo'shnilarning shu ulushida bo'lsa to'ldiriladi.
# 0.67 (standart) — ulush >= 0.67: 3/4, 4/5 o'tadi; 2/3 = 0.667 o'tmaydi (3 qo'shnida hammasi kelishsin).
# 1.0 — hamma qo'shni kelishsin; 0 — ierarxiyasiz (doim to'liq, eng ko'p takrorlangani).
KELISHUV = 0.67

# Bufer qadami va eng katta masofa (metr): 1, 2, 3, ... 10 m.
QADAM_M = 1
MAX_M = 10

# Sinov uchun nechta to'lgan (chetdagi) dala bo'sh deb faraz qilinadi; 0 — sinov yo'q.
TEKSHIRUV_SONI = 5000

# CHIQISH (va hisobot) allaqachon bor bo'lsa ustiga yozilsinmi.
USTIGA_YOZ = False

# =====================================================================================

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fenologiya import muhit  # noqa: F401,E402  (GDAL_DATA/PROJ va DLL yo'llari, numpy dan oldin)

import time  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyogrio  # noqa: E402
import shapely  # noqa: E402

from atribut_otkazish import crs_matn, excel_yoz, foiz, log, shp_ochir, shp_xesh  # noqa: E402

# Yangi ustunlar (shp: 10 belgigacha)
U_USUL = "toldi_usul"  # manba / qoshni (to'liq) / qoshni_qisman / kelishmadi / bosh
U_DAR = "toldi_dar"    # nechta ustun (daraja) to'ldi: 0..len(USTUNLAR)
U_MASOFA = "qoshni_m"  # qo'shni necha metrlik buferda topildi
U_SONI = "qoshni_n"    # shu buferga tekkan to'lgan qo'shnilar soni
U_ULUSH = "qoshni_ul"  # to'ldirilgan eng chuqur daraja qiymati qo'shnilarning qancha qismida
YANGI = [U_USUL, U_DAR, U_MASOFA, U_SONI, U_ULUSH]
AJR = "\x1f"


def qoshnilar(g: np.ndarray, maqsad: np.ndarray, qoshni: np.ndarray, prefiks: list[np.ndarray],
              ustma_ust_emas: bool = False) -> pd.DataFrame:
    """Har bir `maqsad` dala uchun ierarxik qiymat tanlash (g — metrik CRS dagi geometriyalar).

    prefiks[L-1] — har qator uchun USTUNLAR[:L] qiymatlari birlashmasi (L = 1..K).
    Bufer d metr qo'shniga tegadi <=> masofa <= d: masofa bir marta hisoblanadi, birinchi tekkan
    qadam = ceil(masofa / QADAM_M) * QADAM_M (kamida QADAM_M).
    Natija (maqsad qatori indeksi bo'yicha): dar (to'ldiriladigan daraja 0..K), qiymat (shu
    darajagacha), ulush (shu daraja), qadam, soni, xil (to'liq daraja nechta xil), tup_k va
    ulush_k (to'liq daraja eng ko'pi), tup2 (to'liq daraja 2-nomzodi), d_min.
    """
    K = len(prefiks)
    tree = shapely.STRtree(g[qoshni])
    ti, k = tree.query(g[maqsad], predicate="dwithin", distance=float(MAX_M))
    t, n = maqsad[ti], qoshni[k]
    ok = t != n
    t, n = t[ok], n[ok]
    if ustma_ust_emas and len(t):  # sinovda: boshqa mavsumdagi xuddi shu dala hisobga olinmaydi
        ov = shapely.area(shapely.intersection(g[t], g[n])) / np.maximum(shapely.area(g[t]), 1e-9)
        t, n = t[ov < 0.01], n[ov < 0.01]
    if not len(t):
        return pd.DataFrame(columns=["dar", "qiymat", "ulush", "qadam", "soni", "xil",
                                     "tup_k", "ulush_k", "tup2", "d_min"])
    d = shapely.distance(g[t], g[n])
    j = pd.DataFrame({"t": t, "n": n, "d": d})
    j["qadam"] = np.maximum(np.ceil(j.d / QADAM_M - 1e-9), 1).astype(int) * QADAM_M
    j = j[j.qadam <= MAX_M]
    j = j[j.qadam == j.groupby("t").qadam.transform("min")].copy()
    buf = shapely.buffer(g[j.t.values], j.qadam.values.astype(float), quad_segs=4)
    j["w"] = shapely.area(shapely.intersection(buf, g[j.n.values]))
    jami = j.groupby("t").size()
    idx = jami.index

    # har daraja: eng ko'p takrorlangan qiymat (teng: maydon, keyin masofa, keyin qator)
    top, ikk, xil = [], None, None
    for L in range(1, K + 1):
        j["key"] = prefiks[L - 1][j.n.values]
        a = (j.groupby(["t", "key"], sort=False)
             .agg(s=("n", "size"), w=("w", "sum"), d=("d", "min"), nmin=("n", "min")).reset_index())
        a = a.sort_values(["t", "s", "w", "d", "nmin"], ascending=[True, False, False, True, True],
                          kind="mergesort")
        a["r"] = a.groupby("t").cumcount()
        b = a[a.r == 0].set_index("t").reindex(idx)
        b["ulush"] = b.s / jami
        top.append(b)
        if L == K:
            ikk = a[a.r == 1].set_index("t").key.reindex(idx)
            xil = a.groupby("t").size().reindex(idx)

    # eng chuqur kelishilgan daraja (ulush yiriklashgan sari kamaymaydi)
    ulushlar = np.column_stack([b.ulush.values for b in top])
    otdi = ulushlar >= KELISHUV - 1e-9
    dar = np.where(otdi.any(axis=1), K - np.argmax(otdi[:, ::-1], axis=1), 0)
    kalitlar = np.column_stack([b.key.values for b in top])
    qiymat = np.array([kalitlar[i, dar[i] - 1] if dar[i] > 0 else "" for i in range(len(idx))], dtype=object)
    ulush = np.array([ulushlar[i, dar[i] - 1] if dar[i] > 0 else ulushlar[i, 0] for i in range(len(idx))])
    return pd.DataFrame({
        "dar": dar, "qiymat": qiymat, "ulush": np.round(ulush, 3),
        "qadam": j.groupby("t").qadam.first().reindex(idx).values,
        "soni": jami.values, "xil": xil.values,
        "tup_k": top[-1].key.values, "ulush_k": np.round(top[-1].ulush.values, 3),
        "tup2": ikk.values, "d_min": top[-1].d.values,
    }, index=idx)


def main() -> int:
    boshlanish = time.strftime("%Y-%m-%d %H:%M:%S")
    kirish, chiqish = Path(KIRISH), Path(CHIQISH)
    hisobot = Path(HISOBOT) if HISOBOT else chiqish.with_name(f"{chiqish.stem}_hisobot.xlsx")
    if not kirish.exists():
        sys.exit(f"Fayl topilmadi: {kirish}")
    if chiqish.resolve() == kirish.resolve():
        sys.exit("CHIQISH KIRISH bilan bir xil bo'lmasin — natija alohida faylga yoziladi.")
    for p in (chiqish, hisobot):
        if p.exists() and not USTIGA_YOZ:
            sys.exit(f"Natija allaqachon bor: {p}\n  Ustiga yozish uchun USTIGA_YOZ = True qiling.")
    if not (QADAM_M > 0 and MAX_M >= QADAM_M):
        sys.exit(f"QADAM_M > 0 va MAX_M >= QADAM_M bo'lsin: {QADAM_M}, {MAX_M}")
    if not 0 <= KELISHUV <= 1:
        sys.exit(f"KELISHUV 0 dan 1 gacha bo'lsin: {KELISHUV}")

    xesh_kirish = shp_xesh(kirish)
    biz = pyogrio.read_dataframe(kirish)
    yoq = [c for c in USTUNLAR if c not in biz.columns]
    if yoq:
        sys.exit(f"KIRISH da ustun yo'q: {yoq}\n  Bor ustunlar: {list(biz.columns)}")
    if biz.crs is None:
        sys.exit("KIRISH da CRS (.prj) yo'q.")
    n, K = len(biz), len(USTUNLAR)
    log(f"KIRISH: {kirish}  ({n} kontur, {biz.crs})")

    qiymat = biz[USTUNLAR].astype(object).where(biz[USTUNLAR].notna(), "").astype(str).apply(lambda s: s.str.strip())
    bosh_maska = (qiymat == "").all(axis=1).values
    tolgan_maska = ~bosh_maska
    prefiks = [qiymat[USTUNLAR[:L]].agg(AJR.join, axis=1).values for L in range(1, K + 1)]

    t0 = time.time()
    hisob_crs = biz.estimate_utm_crs()
    g = shapely.make_valid(biz.geometry.to_crs(hisob_crs).values)
    bi, fi = np.flatnonzero(bosh_maska), np.flatnonzero(tolgan_maska)
    log(f"Avval to'lgan: {len(fi)};  bo'sh: {len(bi)}  (hisob {hisob_crs.to_string()}, bufer {QADAM_M}..{MAX_M} m, "
        f"ierarxiya {' > '.join(USTUNLAR)}, kelishuv {KELISHUV})")
    tan = qoshnilar(g, bi, fi, prefiks)
    log(f"Qo'shni topildi: {len(tan)} / {len(bi)}  ({time.time() - t0:.0f} s)")

    # ---- natija -----------------------------------------------------------------------
    dar = np.zeros(n, int)
    dar[tan.index.values] = tan.dar.values
    toliq = dar == K
    qisman = (dar > 0) & (dar < K)
    toldi = dar > 0
    kelishmadi = np.zeros(n, bool)
    kelishmadi[tan.index.values[tan.dar.values == 0]] = True
    qoldi = bosh_maska & ~toldi
    yaqin_yoq = qoldi & ~kelishmadi

    natija = biz.copy()
    for c in USTUNLAR:
        natija[c] = natija[c].astype(object)
    for ix, dd, q in zip(tan.index.values, tan.dar.values, tan.qiymat.values):
        if dd > 0:
            vals = q.split(AJR)
            for i, c in enumerate(USTUNLAR):
                natija.iat[ix, natija.columns.get_loc(c)] = (vals[i] or None) if i < dd else None
    usul = np.where(tolgan_maska, "manba", "bosh").astype(object)  # object: matn qisqarib qolmasin
    usul[toliq & bosh_maska] = "qoshni"
    usul[qisman] = "qoshni_qisman"
    usul[kelishmadi] = "kelishmadi"
    natija[U_USUL] = usul
    natija[U_DAR] = np.where(tolgan_maska, K, dar)
    natija[U_MASOFA] = 0
    natija[U_SONI] = 0
    natija[U_ULUSH] = 0.0
    if len(tan):
        ix = natija.index[tan.index.values]
        natija.loc[ix, U_MASOFA] = tan.qadam.values.astype(int)
        natija.loc[ix, U_SONI] = tan.soni.values.astype(int)
        natija.loc[ix, U_ULUSH] = tan.ulush.values.astype(float)
    asl = [c for c in biz.columns if c != "geometry" and c not in YANGI]
    natija = natija[asl + YANGI + ["geometry"]]

    xil = np.zeros(n, bool)
    xil[tan.index.values[tan.xil.values > 1]] = True
    log(f"  to'liq to'ldirildi ({K} ustun): {int((toliq & bosh_maska).sum())};  qisman: {int(qisman.sum())}  "
        + ", ".join(f"{L} ustun {int((dar == L).sum())}" for L in range(1, K)))
    log(f"  qo'shnilar real_name da ham kelishmadi: {int(kelishmadi.sum())};  "
        f"{MAX_M} m ichida qo'shni yo'q: {int(yaqin_yoq.sum())}")
    if len(tan):
        log("  qadam (m): " + ", ".join(f"{int(k)}: {int(v)}" for k, v in tan.qadam.value_counts().sort_index().items()))

    # ---- sinov: chetdagi to'lgan dalalarni bo'sh deb faraz qilib solishtirish -----------
    sinov_df = None
    sinov_jami = None
    if TEKSHIRUV_SONI and len(bi) and len(fi) > 1:
        ts = time.time()
        a, _ = shapely.STRtree(g[bi]).query(g[fi], predicate="dwithin", distance=float(MAX_M))
        chet = np.unique(fi[a])
        sam = np.random.default_rng(0).choice(chet, size=min(TEKSHIRUV_SONI, len(chet)), replace=False)
        st = qoshnilar(g, sam, fi, prefiks, ustma_ust_emas=True)
        if len(st):
            haq = qiymat.values[st.index.values]
            sd = st.dar.values

            def baho(m: np.ndarray) -> dict:
                """m — sinovdagi dalalar maskasi: to'ldirilgan ustunlar qanchalik to'g'ri."""
                q = st.qiymat.values[m]
                h, dd = haq[m], sd[m]
                tol_soni = togri_soni = hammasi = 0
                ust_tol = np.zeros(K, int)
                ust_tog = np.zeros(K, int)
                for qi, hi, di in zip(q, h, dd):
                    v = qi.split(AJR) if di > 0 else []
                    ok = [v[i] == hi[i] for i in range(di)]
                    tol_soni += di
                    togri_soni += sum(ok)
                    hammasi += int(di > 0 and all(ok))
                    for i in range(di):
                        ust_tol[i] += 1
                        ust_tog[i] += int(ok[i])
                nt = int((dd > 0).sum())
                return {
                    "Sinovdagi dalalar": int(m.sum()),
                    "To'ldirildi (kamida 1 ustun)": nt,
                    f"To'liq ({K} ustun)": int((dd == K).sum()),
                    "Qisman": int(((dd > 0) & (dd < K)).sum()),
                    "Kelishmadi (bo'sh qoldi)": int((dd == 0).sum()),
                    "To'ldirilgan ustunlari hammasi to'g'ri, %": foiz(hammasi, nt),
                    "To'ldirilgan kataklardan to'g'ri, %": foiz(togri_soni, tol_soni),
                    **{f"{c} to'g'ri, %": foiz(int(ust_tog[i]), int(ust_tol[i])) for i, c in enumerate(USTUNLAR)},
                }

            rows = [{"Bufer, m": int(q), **baho(st.qadam.values == q)} for q in sorted(st.qadam.unique())]
            rows += [{"Bufer, m": "qo'shnilar bir xil qiymatli", **baho(st.xil.values == 1)},
                     {"Bufer, m": "qo'shnilar har xil qiymatli", **baho(st.xil.values > 1)},
                     {"Bufer, m": "JAMI", **baho(np.ones(len(st), bool))}]
            sinov_df = pd.DataFrame(rows)
            sinov_jami = {"sinov": len(sam), **rows[-1], "har_xil": rows[-2]}
            hk = "To'ldirilgan ustunlari hammasi to'g'ri, %"
            log(f"Sinov ({len(sam)} ta chetdagi to'lgan dala, {time.time() - ts:.0f} s): qo'shni topildi {len(st)}; "
                f"to'ldirilgan ustunlari hammasi to'g'ri {rows[-1][hk]:.1%}; "
                f"qo'shnilar har xil bo'lganda {rows[-2][hk]:.1%} ({rows[-2]['Sinovdagi dalalar']} ta)")

    # ---- yozish va tekshiruv ------------------------------------------------------------
    chiqish.parent.mkdir(parents=True, exist_ok=True)
    shp_ochir(chiqish)
    pyogrio.write_dataframe(natija, chiqish, driver="ESRI Shapefile", encoding="UTF-8")
    log(f"Yozildi: {chiqish}")
    kirish_ok = shp_xesh(kirish) == xesh_kirish
    qayta = pyogrio.read_dataframe(chiqish)
    soni_ok = len(qayta) == n
    geom_ok = soni_ok and bool(shapely.equals(qayta.geometry.values, biz.geometry.values).all())
    crs_ok = qayta.crs == biz.crs
    eski_ok = soni_ok and bool((qayta.loc[tolgan_maska, USTUNLAR].fillna("").astype(str).values
                                == biz.loc[tolgan_maska, USTUNLAR].fillna("").astype(str).values).all())
    for ok, matn in [(kirish_ok, "KIRISH fayllari o'zgargan!"), (soni_ok, "kontur soni farq qiladi"),
                     (geom_ok, "geometriya farq qiladi"), (crs_ok, "CRS farq qiladi"),
                     (eski_ok, "avval to'lgan qiymatlar o'zgargan")]:
        if not ok:
            log(f"XATO: {matn}")
    xato = not (kirish_ok and soni_ok and geom_ok and crs_ok and eski_ok)
    if not xato:
        log("Tekshiruv: KIRISH o'zgarmagan; soni, geometriya, CRS va avval to'lgan qiymatlar bir xil.")

    # ---- Excel hisobot ------------------------------------------------------------------
    def ha(ok: bool) -> str:
        return "Ha ✔" if ok else "YO'Q ✘"

    may = biz["maydon"].astype(float).values if "maydon" in biz.columns else shapely.area(g) / 1e4

    def ga(m: np.ndarray) -> float:
        return round(float(np.nansum(may[m])), 2)

    hamma = np.ones(n, bool)
    toliq_b = toliq & bosh_maska
    umumiy = [
        ("Sana", boshlanish, ""),
        ("— FAYLLAR —", "", ""),
        ("KIRISH", str(kirish), "o'zgarmadi, faqat o'qildi"),
        ("CHIQISH", str(chiqish), "yangi fayl"),
        ("— CRS —", "", ""),
        ("KIRISH CRS i", crs_matn(biz.crs), ""),
        ("Bufer qaysi CRS da hisoblandi", crs_matn(hisob_crs), "masofa haqiqiy metrda"),
        ("CHIQISH CRS i", crs_matn(qayta.crs), "KIRISH bilan bir xil"),
        ("— QOIDA —", "", ""),
        ("Ierarxiya (yirikdan maydaga)", " > ".join(USTUNLAR), "kelishilgan eng chuqur darajagacha to'ldiriladi"),
        ("Kelishuv chegarasi (KELISHUV)", KELISHUV,
         "daraja qiymati tekkan qo'shnilarning shu ulushida bo'lishi shart; 1.0 — hammasida"),
        ("Bufer", f"{QADAM_M} m dan {MAX_M} m gacha, {QADAM_M} m qadam",
         "birinchi to'lgan qo'shniga tekkan qadamda to'xtaydi"),
        ("Bir nechta qo'shni tegsa", "har darajada eng ko'p takrorlangan qiymat",
         "teng bo'lsa — bufer ichida maydoni kattasi, keyin eng yaqini"),
        ("Qo'shni bo'la oladi", "faqat avvaldan to'lgan dalalar", "yangi to'ldirilgan dala manba bo'lmaydi"),
        ("— EKIN YERLAR —", "", ""),
        ("Jami: soni", n, ""),
        ("Jami: maydoni, ga", ga(hamma), ""),
        ("Avvaldan to'lgan (manba): soni", int(tolgan_maska.sum()), f"{foiz(int(tolgan_maska.sum()), n):.1%}"),
        ("Avvaldan to'lgan (manba): maydoni, ga", ga(tolgan_maska), ""),
        ("Avval bo'sh: soni", int(bosh_maska.sum()), f"{foiz(int(bosh_maska.sum()), n):.1%}"),
        ("Avval bo'sh: maydoni, ga", ga(bosh_maska), ""),
        ("Qo'shnidan to'ldirildi — jami: soni", int(toldi.sum()), f"bo'shlarning {foiz(int(toldi.sum()), len(bi)):.1%}"),
        ("Qo'shnidan to'ldirildi — jami: maydoni, ga", ga(toldi), ""),
        (f"   to'liq ({K} ustun): soni", int(toliq_b.sum()), f"toldi_usul = qoshni; maydoni {ga(toliq_b)} ga"),
        ("   qisman: soni", int(qisman.sum()),
         f"toldi_usul = qoshni_qisman; maydaroq ustunlarda qo'shnilar kelishmadi; maydoni {ga(qisman)} ga"),
    ] + [
        (f"      {L} ustun ({', '.join(USTUNLAR[:L])})", int((dar == L).sum()), "") for L in range(1, K)
    ] + [
        ("Bo'sh qoldi — jami: soni", int(qoldi.sum()), f"maydoni {ga(qoldi)} ga"),
        (f"   {MAX_M} m ichida to'lgan qo'shni yo'q", int(yaqin_yoq.sum()), "toldi_usul = bosh"),
        (f"   qo'shnilar {USTUNLAR[0]} da ham kelishmadi", int(kelishmadi.sum()), "toldi_usul = kelishmadi"),
        ("Natijada to'lgan jami (kamida 1 ustun): soni", int((tolgan_maska | toldi).sum()),
         f"{foiz(int((tolgan_maska | toldi).sum()), n):.1%}"),
    ]
    foiz_qatorlar = set()
    if sinov_jami:
        hk = "To'ldirilgan ustunlari hammasi to'g'ri, %"
        umumiy += [
            ("— SINOV (ANIQLIK) —", "", ""),
            ("Sinovdagi to'lgan dalalar (chetdagi)", sinov_jami["sinov"],
             "yonida bo'sh dala bor to'lgan dalalar bo'sh deb faraz qilindi"),
            ("   to'ldirildi (kamida 1 ustun)", sinov_jami["To'ldirildi (kamida 1 ustun)"], ""),
            ("   to'ldirilgan ustunlari hammasi to'g'ri", sinov_jami[hk], "batafsil 'Sinov' varag'ida"),
            ("   qo'shnilar har xil bo'lganda to'g'ri", sinov_jami["har_xil"][hk],
             f"{sinov_jami['har_xil']['Sinovdagi dalalar']} ta dala"),
        ] + [(f"   {c} to'g'ri", sinov_jami[f"{c} to'g'ri, %"], "") for c in USTUNLAR]
        foiz_qatorlar = {"   to'ldirilgan ustunlari hammasi to'g'ri", "   qo'shnilar har xil bo'lganda to'g'ri"} | \
                        {f"   {c} to'g'ri" for c in USTUNLAR}
    umumiy += [
        ("— TEKSHIRUV —", "", ""),
        ("KIRISH o'zgarmadi (fayl xeshi bir xil)", ha(kirish_ok), ""),
        ("Kontur soni bir xil", ha(soni_ok), ""),
        ("Geometriya bir xil", ha(geom_ok), ""),
        ("CRS bir xil", ha(crs_ok), ""),
        ("Avval to'lgan qiymatlar o'zgarmadi", ha(eski_ok), ""),
    ]
    umumiy_df = pd.DataFrame(umumiy, columns=["Ko'rsatkich", "Qiymat", "Izoh"])

    qad_rows = []
    for q in sorted(tan.qadam.unique()) if len(tan) else []:
        m = tan.qadam.values == q
        ix = tan.index.values[m]
        qad_rows.append({"Bufer, m": int(q), "Qo'shni topildi": int(m.sum()),
                         f"To'liq ({K} ustun)": int((tan.dar.values[m] == K).sum()),
                         "Qisman": int(((tan.dar.values[m] > 0) & (tan.dar.values[m] < K)).sum()),
                         "Kelishmadi": int((tan.dar.values[m] == 0).sum()),
                         "Maydoni, ga": round(float(np.nansum(may[ix])), 2)})
    qad_df = pd.DataFrame(qad_rows)
    if sinov_df is not None and len(qad_df):
        s = sinov_df[sinov_df["Bufer, m"].apply(lambda x: isinstance(x, (int, np.integer)))]
        qad_df = qad_df.merge(s[["Bufer, m", "To'ldirilgan ustunlari hammasi to'g'ri, %"]].rename(
            columns={"To'ldirilgan ustunlari hammasi to'g'ri, %": "Sinovda to'g'ri, %"}), on="Bufer, m", how="left")

    varaqlar = {"Umumiy": umumiy_df, "Qadamlar": qad_df}

    if "tuman" in biz.columns:
        nm = np.nan_to_num(may)
        t = pd.DataFrame({"Tuman": biz["tuman"].fillna("(bo'sh)").values, "jami": 1, "may": nm,
                          "bosh": bosh_maska, "may_bosh": np.where(bosh_maska, nm, 0.0),
                          "toliq": toliq_b, "qisman": qisman, "may_toldi": np.where(toldi, nm, 0.0),
                          "qoldi": qoldi, "may_qoldi": np.where(qoldi, nm, 0.0)})
        gg = t.groupby("Tuman").sum(numeric_only=True)
        gg.loc["JAMI"] = gg.sum()
        varaqlar["Tumanlar"] = pd.DataFrame({
            "Tuman": gg.index, "Jami kontur": gg.jami.values, "Jami maydon, ga": gg["may"].round(2).values,
            "Avval bo'sh": gg.bosh.values, "Avval bo'sh maydon, ga": gg.may_bosh.round(2).values,
            "To'liq to'ldirildi": gg.toliq.values, "Qisman to'ldirildi": gg.qisman.values,
            "To'ldirilgan maydon, ga": gg.may_toldi.round(2).values,
            "Bo'sh qoldi": gg.qoldi.values, "Bo'sh qolgan maydon, ga": gg.may_qoldi.round(2).values,
        })

    def kontur_jadval(ix: np.ndarray) -> pd.DataFrame:
        d = pd.DataFrame({"FID (qator, 0 dan)": ix})
        for c in ("unique_id", "tuman", "maydon", "crop"):
            if c in biz.columns:
                d[c] = biz[c].values[ix]
        return d

    def matn(s) -> str:
        return s.replace(AJR, " / ") if isinstance(s, str) else ""

    if len(tan):
        td = kontur_jadval(tan.index.values)
        td["toldi_usul"] = usul[tan.index.values]
        td["To'ldirilgan ustunlar"] = [", ".join(USTUNLAR[:dd]) for dd in tan.dar.values]
        td["Bufer, m"] = tan.qadam.values.astype(int)
        td["Eng yaqin qo'shnigacha, m"] = np.round(tan.d_min.values.astype(float), 2)
        td["Tekkan qo'shnilar"] = tan.soni.values.astype(int)
        td["Qo'shnilar qiymati"] = np.where(tan.xil.values > 1, "har xil", "bir xil")
        td["Yozilgan qiymat"] = [matn(s) for s in tan.qiymat]
        td["Yozilgan qiymat ulushi"] = tan.ulush.values
        td[f"To'liq ({K} ustun) eng ko'pi"] = [matn(s) for s in tan.tup_k]
        td["To'liq eng ko'pi ulushi"] = tan.ulush_k.values
        td["To'liq 2-nomzod"] = [matn(s) for s in tan.tup2]
        varaqlar["To'ldirilganlar"] = td
    qd = kontur_jadval(np.flatnonzero(qoldi))
    qd["Sabab"] = np.where(kelishmadi[qoldi], f"qo'shnilar {USTUNLAR[0]} da ham kelishmadi",
                           f"{MAX_M} m ichida to'lgan qo'shni yo'q")
    varaqlar["Bo'sh qolganlar"] = qd
    if sinov_df is not None:
        varaqlar["Sinov"] = sinov_df

    foiz_ustunlar = {"Sinovda to'g'ri, %", "Yozilgan qiymat ulushi", "To'liq eng ko'pi ulushi",
                     "To'ldirilgan ustunlari hammasi to'g'ri, %", "To'ldirilgan kataklardan to'g'ri, %"} | \
                    {f"{c} to'g'ri, %" for c in USTUNLAR}
    try:
        hisobot.parent.mkdir(parents=True, exist_ok=True)
        excel_yoz(hisobot, varaqlar, foiz_ustunlar)
        from openpyxl import load_workbook  # Umumiy dagi sinov foizlari formati
        wb = load_workbook(hisobot)
        for r in wb["Umumiy"].iter_rows(min_row=2):
            if r[0].value in foiz_qatorlar:
                r[1].number_format = "0.0%"
        wb.save(hisobot)
        log(f"Hisobot: {hisobot}")
    except PermissionError:
        log(f"XATO: hisobotni yozib bo'lmadi (Excel da ochiq bo'lishi mumkin): {hisobot}")
        xato = True
    return 1 if xato else 0


if __name__ == "__main__":
    sys.exit(main())
