"""Fenologiya: NDVI vaqt qatoridan dalaning faol sikllari va mavsum bo'yicha faollik oralig'i.

1. Toza kuzatuvlar (dalaning >= min_toza_ulush qismi toza).
2. Pastga sakragan yakka nuqtalar (bulut qoldig'i) olib tashlanadi.
3. Kunlik chiziqli interpolyatsiya + surilma o'rtacha (silliqlash_kun).
4. Asos (10-persentil) va cho'qqi; faol = NDVI >= max(faol_min_ndvi, asos + faol_nisbiy * (cho'qqi - asos)).
5. Faol oraliqlar -> sikllar (qisqa pasayishlar birlashtiriladi, qisqa sikllar tashlanadi).
6. Sikllar mavsumga: 2+ sikl -> birinchisi Birlamchi, oxirgisi Ikkilamchi; 1 sikl -> cho'qqi bo'linish sanasigacha
   Birlamchi, keyin Ikkilamchi; uzun sikl (>= uzun_sikl_kun) -> ikkala mavsum (bo'linish sanasida bo'linadi);
   Mavsumiy kontur -> barcha sikllar (birinchi boshidan oxirgi oxirigacha).
"""
import numpy as np, pandas as pd


def kunlik_matritsa(q, ids, boshi, oxiri, cfg):
    """q (uzun jadval) -> (kunlik silliq NDVI [len(ids), kunlar], kuzatuv soni, kunlar, kuzatuv niqobi [len(ids), kunlar])."""
    kunlar = pd.date_range(boshi, oxiri, freq="D")
    t0 = kunlar[0]; nd = len(kunlar)
    q = q[(q.toza_piksel / q.jami_piksel) >= cfg["min_toza_ulush"]]
    pos = pd.Series(np.arange(len(ids)), index=ids)
    q = q[q.uniqueid.isin(pos.index)]
    ri = pos.loc[q.uniqueid].values
    di = ((q.sana - t0).dt.days).values
    M = np.full((len(ids), nd), np.nan, dtype="float32")
    M[ri, di] = q.ndvi.values
    kuz = np.zeros(len(ids), dtype="int32")
    np.add.at(kuz, ri, 1)
    S = np.full_like(M, np.nan)
    x = np.arange(nd)
    for i in range(len(ids)):
        k = np.where(~np.isnan(M[i]))[0]
        if len(k) < 3:
            continue
        v = M[i, k].astype("float64")
        # pastga sakragan yakka nuqtalar (ikkala qo'shnidan past) — bulut qoldig'i
        if len(v) >= 3:
            d1, d2 = v[1:-1] - v[:-2], v[1:-1] - v[2:]
            bad = np.where((d1 < -cfg["pastga_sakrash"]) & (d2 < -cfg["pastga_sakrash"]))[0] + 1
            if len(bad):
                keep = np.ones(len(v), bool); keep[bad] = False
                k, v = k[keep], v[keep]
        S[i] = np.interp(x, k, v)
    w = int(cfg["silliqlash_kun"])
    if w > 1:
        pad = w // 2
        bosh = np.all(np.isnan(S), axis=1)               # kuzatuvi yetarli bo'lmagan qatorlar NaN qolsin
        P = np.pad(np.nan_to_num(S), ((0, 0), (pad, pad)), mode="edge")
        c = np.cumsum(np.insert(P, 0, 0, axis=1), axis=1)
        S = ((c[:, w:] - c[:, :-w]) / w)[:, : nd].astype("float32")
        S[bosh] = np.nan
    return S, kuz, kunlar, ~np.isnan(M)


def sikllar(s, cfg):
    """Bitta silliq qator -> [(boshi_idx, oxiri_idx, cho'qqi_idx, cho'qqi_ndvi)], asos, cho'qqi."""
    if np.all(np.isnan(s)):
        return [], np.nan, np.nan
    asos, peak = float(np.nanpercentile(s, 10)), float(np.nanmax(s))
    if peak - asos < cfg["min_amplituda"]:
        return [], asos, peak
    thr = max(cfg["faol_min_ndvi"], asos + cfg["faol_nisbiy"] * (peak - asos))
    a = np.nan_to_num(s, nan=-1) >= thr
    if not a.any():
        return [], asos, peak
    d = np.diff(np.concatenate([[0], a.astype(int), [0]]))
    st, en = list(np.where(d == 1)[0]), list(np.where(d == -1)[0] - 1)
    i = 0                                   # qisqa pasayishlarni birlashtirish
    while i < len(st) - 1:
        if st[i + 1] - en[i] - 1 <= cfg["birlashtirish_kun"]:
            en[i] = en.pop(i + 1); st.pop(i + 1)
        else:
            i += 1
    yadro = [(b, e) for b, e in zip(st, en) if e - b + 1 >= cfg["min_sikl_kun"]]
    peaks = [b + int(np.nanargmax(s[b:e + 1])) for b, e in yadro]
    # chegaralarni siklning O'Z amplitudasiga nisbatan aniqlash: chap/o'ng eng past nuqtadan cho'qqigacha
    # bo'lgan masofaning `chegara_ulush` (20%) iga yetgan joy (TIMESAT uslubi) — ikkinchi, pastroq ekin ham
    # to'g'ri boshlanadi, bog' kabi doim yashil dalalar ham to'liq qamraladi.
    r = float(cfg.get("chegara_ulush", 0.2)); n = len(s); out = []
    for j, ((b, e), p) in enumerate(zip(yadro, peaks)):
        l0 = peaks[j - 1] if j else 0
        r1 = peaks[j + 1] if j + 1 < len(peaks) else n - 1
        tl = l0 + int(np.nanargmin(s[l0:p + 1])); tr = p + int(np.nanargmin(s[p:r1 + 1]))
        lv, rv = s[tl] + r * (s[p] - s[tl]), s[tr] + r * (s[p] - s[tr])
        bb = tl + int(np.argmax(s[tl:p + 1] >= lv))
        ee = tr - int(np.argmax(s[p:tr + 1][::-1] >= rv))
        cf = float(cfg.get("chegarada_faol_ndvi", 0.40))   # davr boshida/oxirida allaqachon yashil (kuzgi bug'doy)
        if tl == 0 and s[0] >= cf:
            bb = 0
        if tr == n - 1 and s[-1] >= cf:
            ee = n - 1
        if out:
            bb = max(bb, out[-1][1] + 1)
        out.append((bb, ee, p, float(s[p])))
    return out, asos, peak


def mavsum_oraliq(cyc, mavsum, kunlar, cfg):
    """Konturning o'z mavsumi uchun faol oraliq (boshi_idx, oxiri_idx, cho'qqi_idx) yoki None (shu mavsumda faol emas)."""
    if not cyc or mavsum not in ("Birlamchi ekin", "Ikkilamchi ekin", "Mavsumiy ekin"):
        return None
    if mavsum == "Mavsumiy ekin":                     # butun faol davr
        top = max(cyc, key=lambda c: c[3])
        return cyc[0][0], cyc[-1][1], top[2]
    split = int((pd.Timestamp(f"{kunlar[0].year}-{cfg['mavsum_bolinishi']}") - kunlar[0]).days)
    if len(cyc) >= 2:                                 # birinchi sikl Birlamchi, oxirgisi Ikkilamchi
        c = cyc[0] if mavsum == "Birlamchi ekin" else cyc[-1]
        return c[0], c[1], c[2]
    b, e, p, _ = cyc[0]
    if e - b + 1 >= cfg["uzun_sikl_kun"]:            # uzun yagona sikl (paxta, bog'): bo'linish sanasida bo'linadi
        if mavsum == "Birlamchi ekin":
            return (b, min(e, split), min(p, split)) if b <= split else None
        return (max(b, split + 1), e, max(p, split + 1)) if e > split else None
    if (mavsum == "Birlamchi ekin") == (p <= split):  # qisqa yagona sikl: cho'qqisi qaysi mavsumda
        return b, e, p
    return None
