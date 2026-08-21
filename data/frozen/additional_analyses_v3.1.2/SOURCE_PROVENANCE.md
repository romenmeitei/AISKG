# Source provenance and release lineage

AISKG v3.1.2 supersedes v3.1.1 because the completed Expert A, Expert B, and third-expert pathway-validation workbooks became available after the earlier release. Their inclusion closes the only material pathway-validation reproducibility gap. The reconstructed final labels are exactly identical to v3.1.1, so all manuscript-facing pathway and benchmark estimates are unchanged.

The untouched workbook uploads are preserved only in the private provenance archive. Public GitHub copies were imported/exported with `artifact_tool`, verified cell-for-cell for values and formulas, stripped of document properties that contained a personal account address, and normalized to deterministic ZIP timestamps. Original and public-copy hashes are recorded in `source_upload_sha256.json`.

Reviewer replay covers 805 paired ratings across seven dimensions. It detects 22 direct A–B disagreements and 84 cases with a Borderline or Uncertain source rating; their union is exactly the 92 rows in the third-expert workbook. All 92 source labels, comments, pathway texts, templates, binary adjudications, and rationales are validated. Two Expert A complete-pathway cells (`XPV-0052`, `XPV-0074`) differ from their component roll-up and are transparently retained; both are resolved to `No` by third-expert adjudication.

The corrected benchmark remains linked to AISKG commit `0e9e0e979c98664c74d7f27e318a7a06aed4fa54`, seed `20260817`, and 5,000 sentence-cluster bootstrap replicates. `benchmark/benchmark_sentences.csv` is byte-identical to the held-out corpus in `AISKG_Section2_Inputs_v2.1.1.zip` (SHA-256 `cc98cc7ee6e8b248d161b0be5754c9db96bf31fb7c21175a7985615a23cb2701`). The corrected executed notebook is preserved under `notebooks/additional_analyses/`, and its original corrected output ZIP under `reference_outputs/additional_analyses_v3.1.2/`.

The superseded failed PubTator/LLM outputs and invalid statistical files remain excluded from the public release.
