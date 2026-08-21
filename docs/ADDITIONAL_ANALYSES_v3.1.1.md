# Corrected additional analyses — AISKG v3.1.1

## Authoritative replay

Run:

```bash
aiskg additional-analyses
```

or execute `notebooks/AISKG_Framework_v3_1_1_Complete_Reproducibility.ipynb`.

The replay reads only `data/frozen/additional_analyses_v3.1.1/`, verifies all 30 archived input checksums before calculation, regenerates figures and workbooks, writes a combined provenance manifest, and creates a byte-deterministic output ZIP.

The manuscript-facing contract is fixed to seed `20260817`, 10,000 overlap-aware pathway bootstrap replicates, 5,000 sentence-cluster benchmark bootstrap replicates, and clean-output execution. Alternate statistical parameters, tampered frozen inputs, and stale-output mode are rejected.

## Expanded pathway validation

The pathway analysis is a census of 95 pre-refinement pathway-plus-template items and 52 outcome-aware refined items, represented by 115 unique blinded units because 32 items occur in both pools. The public table includes final de-identified labels and source designation.

Complete-pathway correctness increased from 23/95 to 26/52. The overlap-aware absolute difference was 0.257895 with a 95% bootstrap interval of 0.143517 to 0.375286. Shared pathways were more likely to be correct than removed pathways (odds ratio 8.0; Fisher exact p = 7.179936×10⁻⁵).

The completed reviewer-level workbooks were not present in the supplied archive. Agreement coefficients are preserved as archived provenance, not independently recalculated evidence.

## Corrected benchmark

### Held-out corpus provenance

The released `benchmark/benchmark_sentences.csv` is byte-identical to `data/heldout_sentences.csv` in `AISKG_Section2_Inputs_v2.1.1.zip`. Both files have SHA-256 `cc98cc7ee6e8b248d161b0be5754c9db96bf31fb7c21175a7985615a23cb2701`.

### Populations

- Common PubTator-compatible entity comparison: 146 sentences and 230 gold entities.
- Full-domain AISKG/structured-LLM comparison: 150 sentences and 318 gold entities.
- Directed relation comparison: 150 sentences and 56 gold relations.

The four DOI/EID-only records excluded from the PubTator-compatible comparison are listed in `benchmark/run_manifest.json`.

### Scoring

Entity true positives are assigned one-to-one within each sentence and shared entity type. Strict matching requires identical character offsets; overlap matching requires non-empty span intersection. Relation scoring uses normalized directed `(source, relation, target)` triples.

The AISKG relation projection reproduces the locked Greek-letter and whitespace normalization implemented in `src/aiskg/legacy/section2_engine.py`. The frozen Section 2 benchmark context independently records the same 27 true positives, 0 false positives, and 29 false negatives; this is not a new post hoc filtering rule.

### Statistics

Confidence intervals use sentence-cluster bootstrap resampling. Paired F1 differences use shared bootstrap indices. Exact sentence-level correctness comparisons use exact McNemar tests with Holm adjustment. Every reported p-value is constrained to [0, 1].

### External-system boundary

PubTator produced entity annotations for the 146 eligible records but no usable relation objects. It is included in the entity comparison and marked **not evaluable** for relation extraction. The structured-LLM run produced parseable JSON for all 150 sentences after validation; 131 invalid or ungrounded proposed items were rejected before scoring.

The executed LLM run requested revision `main`. This does not invalidate the archived prediction-level benchmark, but it prevents a claim that future live inference will use exactly the same model weights.

## Byte-level determinism

Generated OOXML core properties and ZIP member timestamps are normalized. Two independent full replays produced the same hashes:

- corrected result archive: `aa5205189f79c34efdb77482bfda8cdf6ff4e084dc3c45f50fc598e520b28c17`;
- pathway workbook: `c255e9e9068bd56d3c7caf40df139af55777385999e66f99d776d43bb6bd06a8`;
- benchmark workbook: `8dc01dfac1708ef2bb00779ed6fe4ed9ba0ebdb87713066feb7cb620d9b69ade`.
