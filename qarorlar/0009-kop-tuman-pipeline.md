# 0009 — Ko'p tuman uchun pipeline, fayl nomlari, repozitoriylar

**Sana:** 2026-11-05 · **Holat:** qabul qilingan

## Qaror
1. **`pipeline.py`** — tumanlarni ketma-ket ishlaydi (01 → 02 → 03), har qadam alohida jarayonda.
   Natija fayli bor qadam o'tkazib yuboriladi (**davom ettirish**); xato bergan tuman o'tkazilib, oxirida xulosa.
   Jurnal `logs/pipeline_*.log`, holat `logs/holat.csv`. `royxat` — tumanlar, holati, taxminiy vaqt.
2. **Fayl nomi tumanning to'liq nomidan** (`Jomboy tumani` → `jomboy_tumani`). Avvalgi usul "tumani" so'zini
   olib tashlardi va `Guliston` / `Guliston tumani`, `Shahrisabz` / `Shahrisabz tumani` bir xil nom olib, bir-birini
   ustidan yozardi. Jomboy natijalari qayta hisoblanmasdan yangi nomga o'tkazildi.
3. **Taxminiy vaqt** tuman to'rtburchagi (10 m piksel soni) bo'yicha: Jomboy o'lchovi ~96 s / mln piksel.
   Tog'li, dalalari siyrak tumanlar (Nurobod, Qo'shrabot) to'rtburchagi katta → sekin; keyin faqat dala atrofini
   o'qish bilan optimallashtirish mumkin.
4. **Repozitoriylar** — har o'zgarish ikkalasiga push qilinadi:
   - `origin` — ishxona GitLab: `gitlab.spacemc.uz/d.nozimov/dalaga_index_run` (`master`, himoyalangan — force'siz)
   - `github` — shaxsiy GitHub: `github.com/fazogird/polygon_holati` (`main`)
   ```
   git push origin master
   git push github master:main
   ```
