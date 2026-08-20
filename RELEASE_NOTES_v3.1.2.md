# AISKG v3.1.2 — complete reviewer-level reproducibility release

Released: 18 August 2026

## Purpose

v3.1.2 supersedes v3.1.1 because the completed Expert A, Expert B, and third-expert pathway-validation workbooks became available after the earlier release. It closes the remaining reviewer-level reproducibility gap while preserving all manuscript-facing scientific estimates.

## Added

- Three public metadata-sanitized completed reviewer workbooks.
- Direct OOXML replay and validation of 805 paired ratings across seven dimensions.
- Independent raw agreement, Cohen’s kappa, and Gwet’s AC1 recalculation.
- Exact verification of 22 direct disagreements, 84 nondefinitive-rating cases, and all 92 required adjudications.
- Source-to-adjudication checks for labels, comments, pathway text, and pathway template.
- Reconstruction of all 805 final labels before endpoint analysis.
- `reviewer_rating_matrix_long.csv`, `third_expert_adjudication_audit.csv`, `interrater_agreement_recomputed.csv`, `REVIEWER_WORKBOOK_QC.json`, and a reconstructed final-label table.
- Expanded deterministic pathway workbook with agreement, QC, adjudication, rating-matrix, endpoint, and final-label sheets.
- Updated self-contained Colab notebook, verifier, tamper tests, GitHub Actions, documentation, and manuscript-output mapping.

## Privacy and provenance

The untouched uploads contained document properties with a personal account address. Public copies were imported/exported with `artifact_tool`, verified cell-for-cell for values and formulas, stripped of `docProps`, and rewritten with fixed ZIP timestamps. The untouched files are excluded from the public repository and retained only in the separate private provenance archive.

## Transparent source exceptions

Expert A contains two complete-pathway values (`XPV-0052`, `XPV-0074`) that differ from the deterministic component roll-up. The source cells are preserved rather than silently modified. Both are present in the third-expert workbook and are adjudicated `No`.

## Scientific results

The reviewer reconstruction matches the v3.1.1 public final-label table exactly. Therefore the principal results are unchanged:

- pathway correctness: 23/95 before refinement and 26/52 after outcome-aware refinement;
- absolute improvement: 25.8 percentage points, bootstrap 95% CI 14.4–37.5;
- common-schema strict entity micro-F1: AISKG 0.904, PubTator3 0.501, Structured LLM 0.503;
- directed strict relation micro-F1: AISKG 0.651, Structured LLM 0.009;
- PubTator relation status: not evaluable because no usable relation objects were returned.

The structured-LLM source run still records mutable revision `main`; archived predictions and statistics reproduce exactly, but a future live inference run is not claimed bit-for-bit identical.
