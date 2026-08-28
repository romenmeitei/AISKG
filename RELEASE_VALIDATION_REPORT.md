# AISKG v3.2.0 release validation report

**Validation date:** 2026-08-28  
**Release status:** generated for independent verification before GitHub upload

## Release scope

AISKG v3.2.0 preserves the deterministic v3.0.0 core and complete v3.1.2 reviewer/in-domain benchmark replay. It adds the BioRED/BioREDirect external relation-classification package, a repository-native Colab notebook, public-safe frozen outputs, offline smoke tests, CI checks and a tagged-release workflow.

## Frozen external result

- All external quality gates: PASS.
- Train/development/test documents: 500/100/400; overlap: 0.
- Gold entities supplied to every external system.
- Development-only threshold selection; no test tuning.
- Primary sentence-local F1: AISKG constrained 0.386; BioREDirect 0.617.
- Full-document F1: AISKG constrained 0.362; BioREDirect 0.568.
- BC8 test set: locked against further tuning.

## Public-release hygiene

The public data and reference ZIP exclude third-party text, gold candidate rows, `error_analysis.csv`, PubTator representations, official source code and model weights. The complete author-side result archive is identified by hash only.

Run `python scripts/verify_v3_2_0_release.py` and `python scripts/run_external_re_smoke.py` for the independent checks.
