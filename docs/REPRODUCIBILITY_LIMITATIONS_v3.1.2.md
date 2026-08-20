# Reproducibility boundaries — AISKG v3.1.2

## Exactly reproducible

- all public reviewer-workbook cached values and formulas;
- 805 paired A/B ratings and seven agreement tables;
- the exact 92-case adjudication set and all final decisions/rationales;
- reconstruction of all 805 final labels;
- pathway endpoint, mechanism, stratified, and bootstrap results;
- corrected item-level benchmark statistics, confidence intervals, paired tests, and figures;
- generated workbooks, checksums, manifests, and deterministic result ZIPs;
- the unchanged frozen v3.0.0 core manuscript snapshot.

## Privacy transformation

The public reviewer workbooks are content-equivalent sanitized copies, not byte-identical originals. Document properties containing a personal account address were removed and ZIP timestamps fixed. Original hashes and sanitized hashes are both recorded. The untouched files remain private.

## External-model limitation

The corrected structured-LLM source execution requested revision `main`, not an immutable commit SHA. Archived predictions and derived statistics replay exactly; future live model inference is not guaranteed to use identical weights.

## External-service limitation

Live bibliographic retrieval, PubTator calls, and third-party APIs may change over time. They are not required for the frozen manuscript replay. PubTator relation performance is not evaluable because the archived run returned no usable relation objects.
