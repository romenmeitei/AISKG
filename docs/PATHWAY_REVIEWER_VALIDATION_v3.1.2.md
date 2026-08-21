# Pathway reviewer validation audit — v3.1.2

## Input structure

- Expert A: 115 unique pathway rows, seven rating dimensions.
- Expert B: 115 matching pathway rows, seven rating dimensions.
- Third expert: 92 unique rating-dimension adjudication rows.
- Total paired A/B ratings: 805.

## Eligibility and coverage

A third-expert decision is required for any A–B disagreement or any source Borderline/Uncertain rating. The audit identifies 22 direct disagreements and 84 nondefinitive cases; their union contains 92 unique keys. The third-expert workbook contains exactly the same 92 keys.

## Agreement

| Dimension | Raw agreement | Cohen’s kappa | Gwet’s AC1 | Disagreements |
|---|---:|---:|---:|---:|
| Entities | 0.965 | 0.930 | 0.931 | 4 |
| Relations | 0.957 | 0.931 | 0.937 | 5 |
| Direction | 1.000 | 1.000 | 1.000 | 0 |
| Sequence | 1.000 | 1.000 | 1.000 | 0 |
| Terminal class | 0.991 | 0.983 | 0.983 | 1 |
| Evidence support | 0.939 | 0.908 | 0.909 | 7 |
| Complete pathway | 0.957 | 0.930 | 0.937 | 5 |

## Final adjudications

The third expert assigns 88 `No` and four `Yes` decisions. All labels are binary, all rationales are nonblank, and every source label/comment/path/template matches the originating workbook.

Two Expert A complete-pathway source cells (`XPV-0052`, `XPV-0074`) differ from component roll-up. Both are explicitly adjudicated `No`; no submitted source value is silently edited.
