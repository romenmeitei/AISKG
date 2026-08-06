# Migration from AISKG Sections 1 and 2

The unified framework preserves both earlier engines:

- Section 1 → `src/aiskg/legacy/section1_engine.py`
- Section 2 v2.1.1 → `src/aiskg/legacy/section2_engine.py`

Frozen inputs are retained under `data/frozen/`. The complete run first executes Section 1, uses its validated bridge ZIP directly as Section 2 input, executes Section 2, and then adds ablation and unified auditing.

The old repositories should remain public as provenance releases. New issues, features, and corrections should target `AISKG_Framework`.
