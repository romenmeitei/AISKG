# Test status — AISKG Framework v3.1.2

**Status:** PASS  
**Validated:** 18 August 2026

## Final checks

| Check | Result |
|---|---:|
| Python compilation (`src/`, `scripts/`, `tests/`) | PASS |
| Pytest excluding integration | 28 passed; 1 deselected |
| Frozen core integration | PASS |
| Frozen core expected-result audit | 285/285 PASS |
| Generated core files verified | 208 |
| Independent v3.1.2 verifier | PASS |
| Frozen additional-analysis input hashes | 35/35 PASS |
| Reviewer pairs | 805 |
| Direct A/B disagreements | 22 |
| Required third-expert adjudications | 92/92 |
| Reconstructed final labels | 805/805 match |
| Corrected benchmark source notebook | 13/13 code cells executed |
| Self-contained master notebook | 7/7 code cells executed |
| Master-notebook output checksums | 44 |
| Source manifest / SHA list | 174 / 174 agree |
| Direct public text privacy/credential scan | 153 files; 0 hits |
| Private original reviewer workbooks in public package | 0 |
| Private reviewer document-property address hits | 0 |
| Published bibliographic e-mail occurrences in historical frozen/reference archives | 3,557; disclosed third-party metadata |
| Failed-run `DO_NOT_REPORT` artifacts | 0 |

## Deterministic artifacts

Two fresh replays generated identical bytes for:

- combined additional-analysis archive: `5246bf827bec44b9eccfe284761426c29d771241ec94e0943199e0184a565690`;
- pathway Excel workbook: `9e21c1499155c10397fabcbee8c1ac29f8c9d0a3b626f9476da4473d13c71df1`;
- benchmark Excel workbook: `34cb44fec595bc4e826db8b5a050c5deea37c039648c8cd0edee6606ff655350`;
- recomputed agreement CSV: `0496acf371ad77175c1cd83a6a1ae9f7ec246f7f229ea8e02c4ce41287b6fccf`;
- reviewer QC JSON: `489822c947282262fe418c6c49c8672b51063f1191d0393262e1563e8888c8e2`; and
- reconstructed final-label CSV: `725b201ba1cf04bd65cfbd733724f7fcc4d88828335474c51a7e8eb4ceee8ac7`.

## Required release commands

```bash
python -m pip install -e ".[dev]" --no-build-isolation
python verify_repository.py
pytest -q -m "not integration"
python scripts/verify_v3_1_2_release.py
python scripts/execute_v3_1_2_notebook_smoke.py
pytest -q -m integration
```

The public package must report PubTator3 relation extraction as **not evaluable**, retain the structured-LLM revision `main` limitation, and exclude the untouched reviewer uploads.
