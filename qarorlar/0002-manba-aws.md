# 0002 — Asosiy manba: AWS Earth Search

**Sana:** 2026-11-05 · **Holat:** qabul qilingan

## Kontekst
Ikki bepul STAC manba: AWS Earth Search (Element84) va Microsoft Planetary Computer. ET loyihasi AWS ga ko'chmoqda.

## Sinov (`scripts/00_test_tezlik.py`, ishxona PC, Jomboy bo'lagi ~6 mln piksel, 3 oy)
| | AWS | Planetary Computer |
|---|---|---|
| STAC qidiruv | ~1 s | ~1.6 s |
| 10 m kanal | **5–7.5 s** | 11–16.5 s |
| 20 m kanal | 0.8–1.9 s | 0.4–0.5 s |

Ikkalasi ham bir xil sahnalarni topdi; ma'lumotning asosiy hajmi 10 m kanallar → AWS ~2× tez.

## Qaror
Asosiy manba `aws`: `https://earth-search.aws.element84.com/v1`, to'plam **`sentinel-2-c1-l2a`**
(qayta ishlangan, bir xil offset bilan). Kod manbadan mustaqil: `config/sozlamalar.yaml` → `manba: aws | pc`.

## Oqibat
- ET loyihasi bilan bir joyda (AWS us-west-2) ishlatilsa — eng tez va trafik bepul.
- `sentinel-2-c1-l2a` da qaytish = DN × 0.0001 − 0.1 (masshtab/offset STAC metadatasidan o'qiladi).
