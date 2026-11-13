"""Bitta viloyat shp iga to'liq atributli shp dan ma'lumot o'tkazish (fazoviy moslash bilan).

Nima qiladi:
  1. KIRISH (bizning viloyat shp) va MANBA (to'liq atributli shp) o'qiladi.
     MANBA hech qachon o'zgartirilmaydi — skript oxirida fayllar xeshi qayta tekshiriladi.
  2. Guruhlab moslash. MANBA da bitta dala ko'pincha bir nechta kichik konturga bo'lingan,
     lekin ularning nomenklaturasi (ID, LVL_*) bir xil. Shuning uchun o'tkaziladigan qiymatlari
     bir xil MANBA konturlari bitta guruh deb olinadi va har bir guruhning bizning kontur bilan
     birlashgan kesishmasi hisoblanadi. Eng katta ulushli guruh olinadi; ulush (kesishma /
     bizning kontur maydoni) MIN_ULUSH dan kam bo'lsa — hech narsa o'tkazilmaydi.
  3. USTUNLAR (ID -> kontur_raq, ...) birga, bitta guruhdan olinadi — qiymatlar aralashmaydi.
  4. FERMER_BIZDA (full_name) faqat bo'sh joyda to'ldiriladi; fermer nomi alohida,
     FERMER_MANBADA (fermer_nom) qiymati bo'yicha guruhlab moslanadi. Bor qiymat o'zgarmaydi.
  5. Natija CHIQISH ga yoziladi. Geometriya, CRS, qator tartibi va boshqa ustunlar o'zgarmaydi.
  6. Hisobot Excel ga yoziladi (HISOBOT): nima qancha to'ldi / bo'sh qoldi, qaysi ustundan
     qaysi ustunga, qaysi CRS lar ishlatildi, tumanlar kesimi, bo'sh qolgan va shubhali konturlar.

Ishga tushirish (loyiha ildizidan), avval pastdagi KIRISH / MANBA / CHIQISH ni to'g'rilang:
    .\\run.bat viloyat_shp\\atribut_otkazish.py
"""

from __future__ import annotations

# =====================================================================================
#  FOYDALANUVCHI SOZLAMALARI — har bir viloyat uchun shu yerni o'zgartiring
# =====================================================================================

# Ma'lumot qabul qiladigan shp (bizning viloyat fayli). O'zgarmaydi.
KIRISH = r"D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v5_viloyatlar_shp\fargona_viloyati.shp"

# Ma'lumot olinadigan to'liq atributli shp. O'zgarmaydi (faqat o'qiladi).
MANBA = r"D:\Tasks\level_otkazish\far_ekinyer\Far_ekin2025\Far_ekin2025\Fargona_ekin2025.shp"

# Natija shp (yangi fayl; KIRISH yoki MANBA bilan bir xil bo'lishi mumkin emas).
CHIQISH = r"D:\Tasks\bir_ikki_lamchi\natija\ekin_yerlar_qisqa_v6_viloyatlar_shp\fargona_viloyati_v2.shp"

# Excel hisobot. None — CHIQISH yonida "<chiqish nomi>_hisobot.xlsx".
HISOBOT = None

# MANBA dan olinadigan ustunlar: {manbadagi nomi: bizdagi yangi nomi} (shp: 10 belgigacha).
# USTUNLAR = {
#     "ID": "kontur_raq",
#     "LVL_0_name": "real_name",
#     "LVL_1_name": "real_n1",
#     "LVL_2_name": "real_n2",
# }

# version 2
USTUNLAR = {
    "kontur_raq": "kontur_raq",
    "real_name": "real_name",
    "real_n1": "real_n1",
    "real_n2": "real_n2",
}

# Fermer nomi: bizdagi bo'sh FERMER_BIZDA katakchalari MANBA dagi FERMER_MANBADA dan to'ldiriladi.
# To'ldirmaslik uchun ikkalasini ham None qiling.
FERMER_BIZDA = "full_name"
FERMER_MANBADA = "full_name"

# Moslik chegarasi: kesishma / bizning kontur maydoni. 0.5 = kontur kamida yarmi bilan
# manba konturi ichida bo'lishi shart. Kattaroq qiymat — xavfsizroq, lekin kamroq to'ladi.
MIN_ULUSH = 0.5

# Har bir konturga moslik ulushini (0..1) yozish uchun ustun nomi; kerak bo'lmasa None.
ULUSH_USTUNI = "mos_ulush"

# CHIQISH (va hisobot) allaqachon bor bo'lsa ustiga yozilsinmi.
USTIGA_YOZ = False

# =====================================================================================

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fenologiya import muhit  # noqa: F401,E402  (GDAL_DATA/PROJ va DLL yo'llari, numpy dan oldin)

import hashlib  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyogrio  # noqa: E402
import shapely  # noqa: E402

SHP_QOSHIMCHA = (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix", ".sbn", ".sbx")
TENG_NOMZOD = 0.9  # ikkinchi nomzod ulushi >= 0.9 * birinchi bo'lsa — "deyarli teng"


def log(msg: str) -> None:
    satr = f"[{time.strftime('%H:%M:%S')}] {msg}"
    kod = getattr(sys.stdout, "encoding", None) or "utf-8"
    # Windows konsoli (cp1251 va h.k.) chiqara olmaydigan belgilar "?" bo'ladi — skript to'xtamaydi
    print(satr.encode(kod, errors="replace").decode(kod, errors="replace"), flush=True)


def shp_xesh(asos: Path) -> dict[str, str]:
    """shp ning hamma yon fayllari xeshi — fayl o'zgarmaganini tekshirish uchun."""
    out = {}
    for q in SHP_QOSHIMCHA:
        p = asos.with_suffix(q)
        if p.exists():
            out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def shp_ochir(asos: Path) -> None:
    for q in SHP_QOSHIMCHA:
        p = asos.with_suffix(q)
        if p.exists():
            p.unlink()


def bosh(s: pd.Series) -> pd.Series:
    """None / NaN / faqat bo'shliq — bo'sh hisoblanadi."""
    return s.isna() | s.astype(str).str.strip().eq("")


def crs_matn(crs) -> str:
    """EPSG:3857 (WGS 84 / Pseudo-Mercator) ko'rinishida."""
    if crs is None:
        return "yo'q"
    return f"{crs.to_string()} ({crs.name})"


class Kesishmalar:
    """Bizning konturlar va MANBA konturlari orasidagi hamma kesishmalar (bir marta hisoblanadi).

    Ikkala geometriya bir CRS da (metrik) bo'lishi kerak.
    """

    def __init__(self, biz_geom: np.ndarray, manba_geom: np.ndarray):
        self.b = shapely.make_valid(biz_geom)
        self.m = shapely.make_valid(manba_geom)
        bi, mi = shapely.STRtree(self.m).query(self.b, predicate="intersects")
        a = shapely.area(shapely.intersection(self.b[bi], self.m[mi]))
        juft = pd.DataFrame({"bi": bi, "mi": mi, "a": a})
        self.juft = juft[juft.a > 0].reset_index(drop=True)
        self.bmay = shapely.area(self.b)

    def guruhlab(self, kalit: pd.DataFrame) -> pd.DataFrame:
        """`kalit` ustunlari qiymati bir xil MANBA konturlarini guruhlab moslash.

        Har bir (bizning kontur, guruh) uchun kesishma — guruh konturlari birlashmasi bilan
        (bir-birini qoplagan manba konturlari ikki marta sanalmaydi). Natija (biz qatori bo'yicha):
          m_qator  — eng katta ulushli guruhning vakili (guruhdagi eng kichik manba qatori; -1: yo'q)
          ulush    — shu guruh kesishmasi / bizning kontur maydoni
          bolak    — shu guruhdan nechta manba konturi bizning konturga tegadi
          m_qator2, ulush2 — ikkinchi guruh (-1 / 0: yo'q)
        Teng ulushda kichik manba qatorli guruh olinadi (natija har safar bir xil).
        """
        kod = pd.factorize(kalit.fillna("").astype(str).agg("\x1f".join, axis=1))[0]
        j = self.juft.assign(g=kod[self.juft.mi.values])
        gr = j.groupby(["bi", "g"], sort=False).agg(a=("a", "sum"), mi=("mi", "min"), bolak=("mi", "size"))
        # bir guruhdan bir nechta bo'lak bo'lsa — birlashma bilan aniq kesishma
        kop = gr.index[gr.bolak.values > 1]
        if len(kop):
            mlar = j.set_index(["bi", "g"]).mi.groupby(level=[0, 1]).agg(list)
            gr.loc[kop, "a"] = [
                shapely.area(shapely.intersection(self.b[bi], shapely.union_all(self.m[mlar.loc[(bi, g)]])))
                for bi, g in kop
            ]
        gr = gr.reset_index()
        gr["ulush"] = np.minimum(gr.a.values / self.bmay[gr.bi.values], 1.0)
        gr = gr.sort_values(["bi", "ulush", "mi"], ascending=[True, False, True], kind="mergesort")
        gr["r"] = gr.groupby("bi").cumcount()

        n = len(self.b)
        out = pd.DataFrame({"m_qator": -1, "ulush": 0.0, "bolak": 0, "m_qator2": -1, "ulush2": 0.0},
                           index=range(n))
        r0, r1 = gr[gr.r == 0], gr[gr.r == 1]
        out.loc[r0.bi.values, ["m_qator", "ulush", "bolak"]] = r0[["mi", "ulush", "bolak"]].values
        out.loc[r1.bi.values, ["m_qator2", "ulush2"]] = r1[["mi", "ulush"]].values
        return out.astype({"m_qator": int, "bolak": int, "m_qator2": int})


def foiz(qism: float, jami: float) -> float:
    return round(qism / jami, 4) if jami else 0.0


def excel_yoz(yol: Path, varaqlar: dict[str, pd.DataFrame], foiz_ustunlar: set[str]) -> None:
    """Varaqlarni Excel ga yozish: qalin sarlavha, ustun kengligi, muzlatilgan birinchi qator."""
    from openpyxl.styles import Alignment, Font, PatternFill

    sarlavha_fon = PatternFill("solid", fgColor="DDEBF7")
    with pd.ExcelWriter(yol, engine="openpyxl") as w:
        for nom, df in varaqlar.items():
            df.to_excel(w, sheet_name=nom, index=False)
            ws = w.sheets[nom]
            for c in ws[1]:
                c.font = Font(bold=True)
                c.fill = sarlavha_fon
                c.alignment = Alignment(wrap_text=True, vertical="center")
            ws.freeze_panes = "A2"
            for j, ustun in enumerate(df.columns, start=1):
                harf = ws.cell(row=1, column=j).column_letter
                uz = max([len(str(ustun))] + [len(str(v)) for v in df[ustun].head(500)])
                ws.column_dimensions[harf].width = min(max(uz + 2, 10), 70)
                if ustun in foiz_ustunlar:
                    for qator in ws.iter_rows(min_row=2, min_col=j, max_col=j):
                        qator[0].number_format = "0.0%"


def main() -> int:
    boshlanish = time.strftime("%Y-%m-%d %H:%M:%S")
    kirish, manba_yol, chiqish = Path(KIRISH), Path(MANBA), Path(CHIQISH)
    hisobot = Path(HISOBOT) if HISOBOT else chiqish.with_name(f"{chiqish.stem}_hisobot.xlsx")
    for p in (kirish, manba_yol):
        if not p.exists():
            sys.exit(f"Fayl topilmadi: {p}")
    rez = {p.resolve() for p in (kirish, manba_yol)}
    if chiqish.resolve() in rez:
        sys.exit("CHIQISH KIRISH yoki MANBA bilan bir xil bo'lmasin — natija alohida faylga yoziladi.")
    for p in (chiqish, hisobot):
        if p.exists() and not USTIGA_YOZ:
            sys.exit(f"Natija allaqachon bor: {p}\n  Ustiga yozish uchun USTIGA_YOZ = True qiling.")
    if hisobot.suffix.lower() != ".xlsx":
        sys.exit(f"HISOBOT .xlsx bo'lsin: {hisobot}")
    if not 0 < MIN_ULUSH <= 1:
        sys.exit(f"MIN_ULUSH 0 dan katta, 1 dan kichik yoki teng bo'lsin: {MIN_ULUSH}")
    fermer = bool(FERMER_BIZDA and FERMER_MANBADA)

    yangi = list(USTUNLAR.values()) + ([ULUSH_USTUNI] if ULUSH_USTUNI else [])
    uzun = [c for c in yangi if len(c) > 10]
    if uzun:
        sys.exit(f"shp ustun nomi 10 belgidan oshmasin: {uzun}")

    xesh_manba, xesh_kirish = shp_xesh(manba_yol), shp_xesh(kirish)

    # ---- o'qish -------------------------------------------------------------------
    m_info = pyogrio.read_info(manba_yol)
    m_maydon = list(m_info["fields"])
    kerak = list(USTUNLAR) + ([FERMER_MANBADA] if fermer else [])
    yoq = [c for c in kerak if c not in m_maydon]
    if yoq:
        sys.exit(f"MANBA da ustun yo'q: {yoq}\n  Bor ustunlar: {m_maydon}")
    m_vil = ["viloyat"] if "viloyat" in m_maydon else []
    manba = pyogrio.read_dataframe(manba_yol, columns=list(dict.fromkeys(kerak + m_vil)))
    log(f"MANBA:  {manba_yol}  ({len(manba)} kontur, {manba.crs})")

    biz = pyogrio.read_dataframe(kirish)
    log(f"KIRISH: {kirish}  ({len(biz)} kontur, {biz.crs})")
    if fermer and FERMER_BIZDA not in biz.columns:
        sys.exit(f"KIRISH da '{FERMER_BIZDA}' ustuni yo'q. Bor ustunlar: {list(biz.columns)}")
    oldin_bor = [c for c in yangi if c in biz.columns]
    if oldin_bor:
        log(f"Diqqat: KIRISH da bu ustunlar allaqachon bor, qayta yoziladi: {oldin_bor}")
    if biz.crs is None or manba.crs is None:
        sys.exit("KIRISH yoki MANBA da CRS (.prj) yo'q — moslab bo'lmaydi.")

    vil_biz = sorted(biz["viloyat"].dropna().unique()) if "viloyat" in biz.columns else []
    vil_manba = sorted(manba["viloyat"].dropna().unique()) if m_vil else []
    if vil_biz or vil_manba:
        log(f"Viloyat: KIRISH {vil_biz}, MANBA {vil_manba}")

    # ---- guruhlab fazoviy moslash (metrik CRS da: MANBA metrik bo'lsa uniki, aks holda UTM) ----
    t0 = time.time()
    hisob_crs = manba.crs if manba.crs.is_projected else biz.estimate_utm_crs()
    kes = Kesishmalar(biz.geometry.to_crs(hisob_crs).values, manba.geometry.to_crs(hisob_crs).values)
    mos = kes.guruhlab(manba[list(USTUNLAR)])
    mos.index = biz.index
    n = len(biz)
    kesishma_yoq = mos.m_qator < 0
    qabul = ~kesishma_yoq & (mos.ulush >= MIN_ULUSH)
    ulush_past = ~kesishma_yoq & ~qabul
    kop_bolak = qabul & (mos.bolak > 1)
    log(f"Moslash ({hisob_crs.to_string()}, guruhlab, {time.time() - t0:.0f} s): "
        f"{int(qabul.sum())} / {n} kontur mos topildi (ulush >= {MIN_ULUSH})")
    log(f"  shundan bir nechta manba bo'lagidan yig'ilgan: {int(kop_bolak.sum())}")
    log(f"  kesishmasi yo'q: {int(kesishma_yoq.sum())};  kesishma bor, lekin ulush < {MIN_ULUSH}: "
        f"{int(ulush_past.sum())} -> bo'sh qoldirildi")
    u = mos.ulush
    oraliq = [
        ("≥ 0.99 (deyarli to'liq ichida)", qabul & (u >= 0.99), "o'tkazildi"),
        ("0.90 – 0.99", qabul & (u >= 0.9) & (u < 0.99), "o'tkazildi"),
        (f"{MIN_ULUSH:.2f} – 0.90", qabul & (u < 0.9), "o'tkazildi (chegarada, ko'rib chiqish mumkin)"),
        (f"0 – {MIN_ULUSH:.2f} (chegaradan past)", ulush_past, "o'tkazilmadi, bo'sh qoldi"),
        ("kesishma yo'q (0)", kesishma_yoq, "o'tkazilmadi, bo'sh qoldi"),
    ]
    log(f"  ulush: >=0.99 {int(oraliq[0][1].sum())}, 0.9-0.99 {int(oraliq[1][1].sum())}, "
        f"{MIN_ULUSH}-0.9 {int(oraliq[2][1].sum())}")

    # Shubhali: ikkinchi guruh ham deyarli teng ulushda (guruhlar qiymati har doim farqli).
    sh_nom = qabul & (mos.m_qator2 >= 0) & (mos.ulush2 >= TENG_NOMZOD * mos.ulush)
    log(f"  deyarli teng 2 guruh (nomenklatura): {int(sh_nom.sum())} -> eng katta ulushli olindi")

    # ---- o'tkazish ------------------------------------------------------------------
    natija = biz.copy()
    olinadi = manba.drop(columns="geometry").reset_index(drop=True)

    def manbadan(ustun: str, qator: np.ndarray) -> pd.Series:
        return pd.Series(np.where(qator >= 0, olinadi[ustun].reindex(qator).values, None),
                         index=natija.index, dtype=object)

    idx = mos.m_qator.where(qabul, -1).values
    ustun_hisobi = []
    for eski, nom in USTUNLAR.items():
        qiymat = manbadan(eski, idx)
        natija[nom] = qiymat.where(~bosh(qiymat), None)
        toldi = int(natija[nom].notna().sum())
        log(f"  {eski} -> {nom}: {toldi} kontur to'ldi")
        ustun_hisobi.append({
            "Manbadagi ustun (MANBA)": eski,
            "Bizdagi ustun (natija)": nom,
            "Qanday o'tkazildi": "yangi ustun; ID+LVL bir xil manba konturlari guruhlab moslandi"
                                 + (" (eski qiymati almashtirildi)" if nom in oldin_bor else ""),
            "Jami kontur": n,
            "Avval bo'sh edi": n,
            "To'ldirildi": toldi,
            "Bo'sh qoldi": n - toldi,
            "Avvaldan bor, o'zgarmadi": 0,
            "To'ldirildi, %": foiz(toldi, n),
            "Bo'sh qoldi, %": foiz(n - toldi, n),
        })

    fermer_toldi = pd.Series(False, index=natija.index)
    fermer_bosh_edi = pd.Series(False, index=natija.index)
    sh_fer = pd.Series(False, index=natija.index)
    fmos = None
    if fermer:
        fmos = kes.guruhlab(manba[[FERMER_MANBADA]])
        fmos.index = biz.index
        f_qabul = (fmos.m_qator >= 0) & (fmos.ulush >= MIN_ULUSH)
        f_manba = manbadan(FERMER_MANBADA, fmos.m_qator.where(f_qabul, -1).values)
        fermer_bosh_edi = bosh(natija[FERMER_BIZDA])
        fermer_toldi = fermer_bosh_edi & ~bosh(f_manba)
        natija[FERMER_BIZDA] = natija[FERMER_BIZDA].astype(object)
        natija.loc[fermer_toldi, FERMER_BIZDA] = f_manba[fermer_toldi]
        sh_fer = fermer_toldi & (fmos.m_qator2 >= 0) & (fmos.ulush2 >= TENG_NOMZOD * fmos.ulush)
        bosh_edi, toldi = int(fermer_bosh_edi.sum()), int(fermer_toldi.sum())
        log(f"  {FERMER_MANBADA} -> {FERMER_BIZDA}: {bosh_edi} bo'sh edi, {toldi} to'ldirildi, "
            f"{bosh_edi - toldi} bo'sh qoldi (bor {n - bosh_edi} qiymat o'zgarmadi); "
            f"deyarli teng 2 guruh: {int(sh_fer.sum())}")
        ustun_hisobi.append({
            "Manbadagi ustun (MANBA)": FERMER_MANBADA,
            "Bizdagi ustun (natija)": FERMER_BIZDA,
            "Qanday o'tkazildi": "faqat bo'sh kataklar; fermer_nom bir xil manba konturlari guruhlab "
                                 "moslandi; bor qiymat o'zgarmadi",
            "Jami kontur": n,
            "Avval bo'sh edi": bosh_edi,
            "To'ldirildi": toldi,
            "Bo'sh qoldi": bosh_edi - toldi,
            "Avvaldan bor, o'zgarmadi": n - bosh_edi,
            "To'ldirildi, %": foiz(toldi, bosh_edi),
            "Bo'sh qoldi, %": foiz(bosh_edi - toldi, bosh_edi),
        })

    if ULUSH_USTUNI:
        natija[ULUSH_USTUNI] = mos.ulush.round(3).values

    # ustun tartibi: bizning ustunlar, keyin yangilari, oxirida geometriya
    asl = [c for c in biz.columns if c != "geometry" and c not in yangi]
    natija = natija[asl + yangi + ["geometry"]]

    # ---- yozish ---------------------------------------------------------------------
    chiqish.parent.mkdir(parents=True, exist_ok=True)
    shp_ochir(chiqish)
    pyogrio.write_dataframe(natija, chiqish, driver="ESRI Shapefile", encoding="UTF-8")
    log(f"Yozildi: {chiqish}")

    # ---- tekshiruv ------------------------------------------------------------------
    manba_ok = shp_xesh(manba_yol) == xesh_manba
    kirish_ok = shp_xesh(kirish) == xesh_kirish
    qayta = pyogrio.read_dataframe(chiqish)
    soni_ok = len(qayta) == n
    geom_ok = soni_ok and bool(shapely.equals(qayta.geometry.values, biz.geometry.values).all())
    crs_ok = qayta.crs == biz.crs
    for ok, matn in [(manba_ok, "MANBA fayllari o'zgargan!"), (kirish_ok, "KIRISH fayllari o'zgargan!"),
                     (soni_ok, f"natijada {len(qayta)} kontur, kirishda {n}"),
                     (geom_ok, "natija geometriyasi kirishdan farq qiladi"),
                     (crs_ok, f"natija CRS i {qayta.crs}, kirishda {biz.crs}")]:
        if not ok:
            log(f"XATO: {matn}")
    xato = not (manba_ok and kirish_ok and soni_ok and geom_ok and crs_ok)
    if not xato:
        log("Tekshiruv: MANBA va KIRISH o'zgarmagan; kontur soni, geometriya va CRS bir xil.")

    # ---- Excel hisobot ----------------------------------------------------------------
    def ha(ok: bool) -> str:
        return "Ha ✔" if ok else "YO'Q ✘"

    # Maydon (ga): "maydon" ustuni bo'lsa — undan; har doim geometriyadan ham (hisob CRS ida).
    biz_ga = biz.geometry.to_crs(hisob_crs).area.values / 1e4
    qayta_ga = qayta.geometry.to_crs(hisob_crs).area.values / 1e4
    may = biz["maydon"].astype(float).values if "maydon" in biz.columns else biz_ga
    may_q = qayta["maydon"].astype(float).values if "maydon" in qayta.columns else qayta_ga
    may_izoh = "'maydon' ustunidan" if "maydon" in biz.columns else "geometriyadan hisoblangan"

    def ga(x) -> float:
        return round(float(np.nansum(x)), 2)

    def farqli_ustunlar(m_df: pd.DataFrame, maska: pd.Series, ust: list[str], nomlar: dict) -> np.ndarray:
        """Olingan va 2-guruh qiymatlari farq qiladigan ustunlar (bizdagi nomlari bilan), masalan
        "kontur_raq" yoki "kontur_raq, real_n2"."""
        if m_df is None or not maska.any():
            return np.array([], dtype=object)
        v1 = olinadi.iloc[m_df.loc[maska, "m_qator"].values][ust].fillna("").astype(str).values
        v2 = olinadi.iloc[m_df.loc[maska, "m_qator2"].values][ust].fillna("").astype(str).values
        return np.array([", ".join(nomlar.get(c, c) for c, f in zip(ust, qator) if f)
                         for qator in (v1 != v2)], dtype=object)

    nom_farq = farqli_ustunlar(mos, sh_nom, list(USTUNLAR), USTUNLAR)
    fer_farq = farqli_ustunlar(fmos, sh_fer, [FERMER_MANBADA], {FERMER_MANBADA: FERMER_BIZDA}) if fermer else None
    nom_farq_soni = pd.Series(nom_farq, dtype=object).value_counts()

    umumiy = pd.DataFrame([
        ("Sana", boshlanish, ""),
        ("— FAYLLAR —", "", ""),
        ("KIRISH (ma'lumot qabul qilgan fayl)", str(kirish), "o'zgarmadi, faqat o'qildi"),
        ("MANBA (ma'lumot olingan fayl)", str(manba_yol), "o'zgarmadi, faqat o'qildi"),
        ("CHIQISH (natija fayl)", str(chiqish), "yangi fayl"),
        ("— CRS (KOORDINATA TIZIMI) —", "", ""),
        ("KIRISH CRS i", crs_matn(biz.crs), ""),
        ("MANBA CRS i", crs_matn(manba.crs), ""),
        ("Moslash qaysi CRS da hisoblandi", crs_matn(hisob_crs),
         "ikkala fayl vaqtincha shu CRS ga o'tkazildi: kesishma maydoni metrda to'g'ri hisoblanadi"),
        ("CHIQISH CRS i", crs_matn(qayta.crs), "KIRISH bilan bir xil — geometriya qayta proyeksiyalanmadi"),
        ("— EKIN YERLAR: AVVAL (KIRISH) VA KEYIN (CHIQISH) —", "", ""),
        ("Ekin yerlar soni — KIRISH", n, ""),
        ("Ekin yerlar soni — CHIQISH (yangi saqlangan)", len(qayta), "bir xil bo'lishi shart"),
        ("Ekin yerlar maydoni, ga — KIRISH", ga(may), may_izoh),
        ("Ekin yerlar maydoni, ga — CHIQISH (yangi saqlangan)", ga(may_q), may_izoh),
        ("Geometriya maydoni, ga — KIRISH", ga(biz_ga), f"poligonlardan, {hisob_crs.to_string()} da"),
        ("Geometriya maydoni, ga — CHIQISH", ga(qayta_ga), f"poligonlardan, {hisob_crs.to_string()} da"),
        ("Ma'lumot o'tgan ekin yerlar: soni", int(qabul.sum()), f"{foiz(int(qabul.sum()), n):.1%}"),
        ("Ma'lumot o'tgan ekin yerlar: maydoni, ga", ga(may[qabul.values]),
         f"{foiz(ga(may[qabul.values]), ga(may)):.1%}"),
        ("Bo'sh qolgan ekin yerlar: soni", int((~qabul).sum()), f"{foiz(int((~qabul).sum()), n):.1%}"),
        ("Bo'sh qolgan ekin yerlar: maydoni, ga", ga(may[~qabul.values]),
         f"{foiz(ga(may[~qabul.values]), ga(may)):.1%}"),
        ("MANBA konturlari soni", len(manba), ""),
        ("Viloyat (KIRISH)", ", ".join(vil_biz), ""),
        ("Viloyat (MANBA)", ", ".join(vil_manba), ""),
        ("— MOSLASH (GURUHLAB) —", "", ""),
        ("Usul", "o'tkaziladigan qiymatlari bir xil MANBA konturlari bitta guruh",
         "bizning kontur manbada bir nechta bo'lakka bo'lingan bo'lsa ham, bo'laklar ulushi qo'shiladi"),
        ("Moslik chegarasi (MIN_ULUSH)", MIN_ULUSH,
         "guruh kesishmasi / bizning kontur maydoni shundan kam bo'lsa — hech narsa o'tkazilmaydi"),
        ("Mos manba guruhi topildi", int(qabul.sum()), f"{foiz(int(qabul.sum()), n):.1%}"),
        ("   shundan: 1 ta manba konturidan", int((qabul & (mos.bolak == 1)).sum()), ""),
        ("   shundan: bir nechta manba bo'lagidan yig'ilgan", int(kop_bolak.sum()), ""),
        ("Bo'sh qoldi — jami", int((~qabul).sum()), f"{foiz(int((~qabul).sum()), n):.1%}"),
        ("   shundan: hech qaysi manba konturiga tegmaydi", int(kesishma_yoq.sum()), ""),
        (f"   shundan: kesishma bor, lekin ulush < {MIN_ULUSH}", int(ulush_past.sum()), ""),
        ("Deyarli teng 2 guruh — nomenklatura (shubhali)", int(sh_nom.sum()),
         f"ikkinchi guruh ulushi ≥ {TENG_NOMZOD:.0%} × birinchi; eng kattasi olindi; 'Shubhali' varag'ida"),
    ] + [
        (f"   farqli ustunlar: {k}", int(v), "faqat shu ustun(lar) ikki guruhda har xil, qolganlari bir xil")
        for k, v in nom_farq_soni.items()
    ] + ([
        (f"Deyarli teng 2 guruh — {FERMER_MANBADA} (shubhali)", int(sh_fer.sum()),
         f"faqat {FERMER_BIZDA} to'ldirilgan konturlar; 'Shubhali' varag'ida"),
    ] if fermer else []) + [
        ("— TEKSHIRUV —", "", ""),
        ("MANBA o'zgarmadi (fayl xeshi bir xil)", ha(manba_ok), ""),
        ("KIRISH o'zgarmadi (fayl xeshi bir xil)", ha(kirish_ok), ""),
        ("Natijada kontur soni bir xil", ha(soni_ok), ""),
        ("Natijada geometriya bir xil", ha(geom_ok), ""),
        ("Natijada CRS bir xil", ha(crs_ok), ""),
    ], columns=["Ko'rsatkich", "Qiymat", "Izoh"])

    ustunlar_df = pd.DataFrame(ustun_hisobi)

    moslik_df = pd.DataFrame([{
        "Moslik ulushi (guruh kesishmasi / kontur maydoni)": o[0],
        "Konturlar soni": int(o[1].sum()),
        "Ulushi, %": foiz(int(o[1].sum()), n),
        "Shundan bir nechta bo'lakdan yig'ilgan": int((o[1] & (mos.bolak > 1)).sum()),
        "Natija": o[2],
    } for o in oraliq] + [{
        "Moslik ulushi (guruh kesishmasi / kontur maydoni)": "JAMI", "Konturlar soni": n, "Ulushi, %": 1.0,
        "Shundan bir nechta bo'lakdan yig'ilgan": int((mos.bolak > 1).sum()), "Natija": "",
    }])

    varaqlar = {"Umumiy": umumiy, "Ustunlar": ustunlar_df, "Moslik": moslik_df}

    if "tuman" in biz.columns:
        t = pd.DataFrame({"Tuman": biz["tuman"].fillna("(bo'sh)").values,
                          "jami": 1, "mos": qabul.values, "bosh": (~qabul).values,
                          "may": np.nan_to_num(may), "may_mos": np.where(qabul.values, np.nan_to_num(may), 0.0),
                          "f_bosh": fermer_bosh_edi.values, "f_toldi": fermer_toldi.values})
        g = t.groupby("Tuman").sum(numeric_only=True)
        g.loc["JAMI"] = g.sum()
        tum = pd.DataFrame({
            "Tuman": g.index,
            "Jami kontur": g.jami.values,
            "Jami maydon, ga": g["may"].round(2).values,
            "Mos topildi (ma'lumot o'tdi)": g.mos.values,
            "Mos topilgan maydon, ga": g.may_mos.round(2).values,
            "Bo'sh qoldi": g.bosh.values,
            "Bo'sh qolgan maydon, ga": (g["may"] - g.may_mos).round(2).values,
            "Mos topildi, %": (g.mos / g.jami).round(4).values,
        })
        if fermer:
            tum[f"{FERMER_BIZDA}: bo'sh edi"] = g.f_bosh.values
            tum[f"{FERMER_BIZDA}: to'ldirildi"] = g.f_toldi.values
            tum[f"{FERMER_BIZDA}: bo'sh qoldi"] = (g.f_bosh - g.f_toldi).values
        varaqlar["Tumanlar"] = tum

    def kontur_jadval(maska: pd.Series) -> pd.DataFrame:
        d = pd.DataFrame({"FID (qator, 0 dan)": np.flatnonzero(maska.values)})
        for c in ("unique_id", "tuman", "maydon", "crop"):
            if c in biz.columns:
                d[c] = biz.loc[maska, c].values
        return d

    bosh_df = kontur_jadval(~qabul)
    bosh_df["Moslik ulushi"] = mos.loc[~qabul, "ulush"].round(3).values
    bosh_df["Sabab"] = np.where(kesishma_yoq[~qabul].values, "hech qaysi manba konturiga tegmaydi",
                                f"eng katta guruh ulushi {MIN_ULUSH} dan kam")
    varaqlar["Bo'sh qolganlar"] = bosh_df

    def qiymat_matn(qatorlar: np.ndarray, ustunlar: list[str]) -> np.ndarray:
        return olinadi.iloc[qatorlar][ustunlar].fillna("").astype(str).agg(" / ".join, axis=1).values

    shubhali = []
    for tur, maska, m_df, ust, farq in [
        ("nomenklatura (" + " / ".join(USTUNLAR) + ")", sh_nom, mos, list(USTUNLAR), nom_farq),
        (FERMER_MANBADA, sh_fer, fmos, [FERMER_MANBADA], fer_farq),
    ]:
        if m_df is None or not maska.any():
            continue
        d = kontur_jadval(maska)
        d.insert(0, "Tur", tur)
        d.insert(1, "Farqli ustunlar", farq)
        d["Ulush (olindi)"] = m_df.loc[maska, "ulush"].round(3).values
        d["Ulush (2-guruh)"] = m_df.loc[maska, "ulush2"].round(3).values
        d["Olingan qiymat"] = qiymat_matn(m_df.loc[maska, "m_qator"].values, ust)
        d["2-guruh qiymati"] = qiymat_matn(m_df.loc[maska, "m_qator2"].values, ust)
        shubhali.append(d)
    varaqlar["Shubhali"] = (pd.concat(shubhali, ignore_index=True) if shubhali
                            else pd.DataFrame({"Tur": [], "Izoh": []}))

    foiz_ustunlar = {"To'ldirildi, %", "Bo'sh qoldi, %", "Ulushi, %", "Mos topildi, %"}
    try:
        hisobot.parent.mkdir(parents=True, exist_ok=True)
        excel_yoz(hisobot, varaqlar, foiz_ustunlar)
        log(f"Hisobot: {hisobot}")
    except PermissionError:
        log(f"XATO: hisobotni yozib bo'lmadi (Excel da ochiq bo'lishi mumkin): {hisobot}")
        xato = True
    return 1 if xato else 0


if __name__ == "__main__":
    sys.exit(main())
