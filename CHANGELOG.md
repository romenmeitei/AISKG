# Changelog

## 3.2.0 — 2026-08-28

- Added an independent BioRED/BioREDirect external relation-classification benchmark under gold-entity conditions.
- Added AISKG rule-transfer and constrained text-transfer adapters, a leakage-controlled type-pair baseline and the official BioREDirect comparator.
- Added sentence-local primary and full-document stress-test evaluations, 5,000-document bootstrap intervals and paired comparisons.
- Integrated external code, configuration, smoke tests, a repository-native Colab notebook and public-safe result export.
- Published metrics, thresholds, aggregate audits, text-free predictions, figures and sanitized provenance while excluding third-party text, gold candidate rows, official code and model weights.
- Locked the examined BC8 test set against further tuning.
- Preserved the v3.0.0 core and v3.1.2 reviewer/in-domain benchmark replay unchanged.

## 3.1.2 — 2026-08-18

- Added public metadata-sanitized completed Expert A, Expert B, and third-expert workbooks.
- Added independent replay of 805 paired ratings, seven agreement tables, and all 92 required adjudications.
- Reconstructed all final labels and verified exact identity with v3.1.1; scientific estimates are unchanged.
- Disclosed and adjudicated two Expert A component-roll-up exceptions (`XPV-0052`, `XPV-0074`).
- Updated the self-contained notebook, verifier, tests, workflows, documentation, and deterministic package.
- Superseded v3.1.1 for public manuscript reproducibility.

## 3.1.1 — 2026-08-18

- Replaced the invalid draft external benchmark with the corrected executed PubTator3/structured-LLM analysis.
- Added transparent item-level corrected benchmark outputs and deterministic statistical replay.
- Added the expanded blinded pathway-validation replay.
- Added the `aiskg additional-analyses` CLI command, a self-contained master notebook, verification scripts, tests, provenance documents, and CI checks.
- Locked the corrected replay to verified inputs, fixed statistical parameters, and clean output generation.
- Normalized Excel/ZIP metadata and added a two-run byte-determinism test.
- Strengthened packaged-source verification by cross-checking `PACKAGE_MANIFEST.csv` and `SHA256SUMS.txt`.
- Excluded all superseded failed-run benchmark tables from the public release.
- Corrected repository URLs from `AISKG_Framework` to `AISKG`.
- Preserved the v3.0.0 frozen core workflow and expected outputs unchanged.

## 3.0.0 — 2026-08-05

- Unified the historical AISKG Section 1 and Section 2 workflows.
- Added a modular package and CLI.
- Added deterministic manuscript-snapshot execution and 285 expected-result checks.
- Added nine deterministic component ablations.
- Added source and output manifests, SHA-256 verification, notebooks, CI, and release packaging.
