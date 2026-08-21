# AISKG v3.1.1 — corrected manuscript reproducibility release

Released: 18 August 2026

## Purpose

v3.1.1 supersedes the unpublished v3.1.0 draft package. The earlier draft incorporated an operationally invalid PubTator/structured-LLM benchmark run. This release replaces it with the corrected executed notebook and corrected item-level output archive supplied on 18 August 2026.

## Added

- Complete deterministic replay of the expanded blinded pathway validation.
- Corrected three-system held-out entity benchmark on 146 PMID-eligible sentences.
- Corrected AISKG versus structured-LLM directed relation benchmark on all 150 sentences.
- Exact corrected predictions, metrics, confidence intervals, paired bootstrap comparisons, McNemar-Holm tests, class coverage, figures, workbook, and run manifest.
- `aiskg additional-analyses` command and repository wrapper.
- Self-contained `AISKG_Framework_v3_1_1_Complete_Reproducibility.ipynb`.
- Exact corrected executed benchmark notebook and original corrected output archive as provenance references.
- Independent verifier, clean-directory notebook smoke test, pytest checks, input checksums, and GitHub Actions integration.
- Held-out sentence-corpus lineage to the frozen Section 2 input bundle.
- Explicit manuscript-to-output mapping and reporting-boundary documentation.

## Reproducibility hardening

- The replay verifies 30 frozen input checksums before analysis.
- Manuscript-facing execution is locked to seed `20260817`, 10,000 pathway bootstraps, 5,000 benchmark bootstraps, and clean output generation.
- Alternate parameters, tampered frozen inputs, and stale-output mode are rejected.
- Excel metadata and ZIP timestamps are normalized; two independent replays produced byte-identical workbooks and the same complete result archive.
- The corrected result archive has SHA-256 `aa5205189f79c34efdb77482bfda8cdf6ff4e084dc3c45f50fc598e520b28c17`.

## Corrected results

- Pathway correctness: 23/95 before refinement and 26/52 after outcome-aware refinement.
- Corrected common-schema strict entity micro-F1: AISKG 0.904, PubTator3 0.501, structured LLM 0.503.
- Corrected directed strict relation micro-F1: AISKG 0.651 and structured LLM 0.009.
- PubTator relation output: not evaluable because no usable relation objects were returned.
- Structured-LLM JSON validity: 150/150 sentences.

## Removed from the public release

- Failed-run PubTator/LLM metrics from the superseded draft.
- Empty-output values presented as scientific zero performance.
- The invalid two-sided bootstrap p-value greater than 1.
- Old failed-run validation logs and `DO_NOT_REPORT` tables.
- The misleading `--no-clean` route for the manuscript-facing replay.

## Reporting limitations

The pathway final labels are reproducible, but the raw completed reviewer workbooks were absent from the supplied archive. The corrected LLM execution recorded revision `main`; archived item-level outputs are exactly replayable, while a future live call is not claimed to use identical weights.

## Core compatibility

The v3.0.0 frozen manuscript-snapshot pipeline and its 285 expected-result checks are preserved unchanged. v3.1.1 is an additive corrected-analysis release.
