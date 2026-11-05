# 0004 — Ichki bufer kontur maydoniga qarab

**Sana:** 2026-11-05 · **Holat:** qabul qilingan (dastlabki "hammasiga 10 m" o'rniga)

## Kontekst
Kontur chetidagi piksellarga qo'shni dala, yo'l yoki ariq aralashadi, shuning uchun hisob kontur ichidan olinadi.
Hammasiga bir xil 10 m bufer berilganda kichik konturlar yo'qolib qoladi (Jomboyda 844 ta).

## Qaror (`config/sozlamalar.yaml` → `ichki_bufer`)
| Kontur maydoni | Bufer |
|---|---|
| < 0.5 ga | 0 (asl geometriya) |
| 0.5 – 2 ga | 5 m |
| ≥ 2 ga | 10 m |

Qo'shimcha shart: bufer konturning **kamida 50%** ini va **kamida 300 m²** (~3 ta 10 m piksel) ni qoldirishi kerak;
aks holda keyingi kichikroq bufer, oxiri — bufersiz. Ishlatilgan bufer `bufer_m` ustunida.

## Tekshiruv
`tests/test_bufer.py`: 0.3 ga → 0 m, 1 ga → 5 m, 5 ga → 10 m, ingichka 10 m × 5 km kontur → 0 m.
