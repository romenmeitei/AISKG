# AISKG

[![CI](https://github.com/romenmeitei/AISKG/actions/workflows/ci.yml/badge.svg)](https://github.com/romenmeitei/AISKG/actions/workflows/ci.yml)
[![Open external benchmark in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/romenmeitei/AISKG/blob/main/notebooks/additional_analyses/AISKG_External_RE_Benchmark_Colab_v1_1.ipynb)
[![Open v3.1.2 replay in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/romenmeitei/AISKG/blob/main/notebooks/AISKG_Framework_v3_1_2_Complete_Reproducibility.ipynb)

**AISKG v3.2.0** is the external biomedical relation-benchmark release of the ontology-guided semantic knowledge-graph framework. It preserves the deterministic **v3.0.0 core** and the complete **v3.1.2 reviewer/in-domain benchmark replay**, and adds a new BioRED/BioREDirect cross-domain relation-classification experiment.

## What v3.2.0 adds

- an independently executed BioRED/BioREDirect benchmark using 500/100/400 train/development/test documents;
- a leakage-controlled type-pair majority baseline;
- a transparent AISKG rule-transfer adapter;
- an AISKG constrained TF-IDF transfer classifier;
- the official pretrained BioREDirect comparator at commit `fc090435fa8198187ab5145da26d8abf01000131`;
- sentence-local primary and full-document cross-sentence stress-test results;
- document-bootstrap confidence intervals and paired comparisons;
- repository-native CLI, tests and GPU Colab execution;
- public-safe frozen outputs and sanitized provenance; and
- CI/release verification without rerunning the live GPU model.

### External benchmark headline results

All systems received **gold entity mentions and normalized identifiers**. The endpoint is relation classification, not end-to-end NER plus RE.

| Scope | Type-pair majority | AISKG rule transfer | AISKG constrained transfer | BioREDirect |
|---|---:|---:|---:|---:|
| Sentence-local relation F1 | 0.311 | 0.275 | **0.386** | **0.617** |
| Full-document relation F1 | 0.199 | 0.184 | **0.362** | **0.568** |

The constrained adapter improved over the majority baseline but remained below the specialist BioREDirect model. The AISKG external systems are transfer adapters, not the unchanged mushroom-domain v3.1.2 extractor. The examined BC8 test split is locked against further tuning.

### Public-release boundary

This repository does not redistribute BioRED/BioREDirect text, official gold candidate rows, NCBI source code or model weights. It publishes metrics, aggregate audits, thresholds, figures, sanitized provenance and system prediction rows without source text. The Colab notebook downloads official assets at runtime and records their hashes.

## Install and verify

```bash
python -m pip install -e ".[dev,external-re]" --no-build-isolation
python verify_repository.py
pytest -q -m "not integration"
python scripts/verify_v3_1_2_release.py
python scripts/verify_v3_2_0_release.py
python scripts/run_external_re_smoke.py
```

## Run the external benchmark

The full official comparison requires a GPU and network access:

```bash
aiskg external-re-benchmark --run-bioredirect --clean
```

This creates an author-side complete result archive and a separate public-safe result archive. The repository-native Colab notebook provides the recommended execution route.

## Frozen external reference outputs

Public-safe frozen outputs are stored under:

```text
data/frozen/external_re_benchmark_v1.0.0/
reference_outputs/external_re_benchmark_v1.0.0/
```

See `docs/EXTERNAL_BIORED_BIOREDIRECT_BENCHMARK_v1.0.0.md` and `manuscript/EXTERNAL_RE_BENCHMARK_RESULT_MAPPING_v3.2.0.md`.

## Preserved v3.1.2 reviewer and in-domain replay

The pathway replay now independently performs the full reviewer workflow before calculating any endpoint:

- reads 115 Expert A and 115 Expert B pathway records;
- verifies 805 paired ratings across seven dimensions;
- recomputes raw agreement, Cohen’s kappa, and Gwet’s AC1;
- identifies 22 direct A–B disagreements and 84 cases containing a Borderline or Uncertain source rating;
- verifies the exact 92-case union requiring third-expert adjudication;
- checks each adjudication against the source labels, comments, pathway text, and template;
- reconstructs all 805 final binary labels; and
- confirms exact identity with the previously released final-label table.

The three public XLSX files are cell-for-cell content-equivalent to the submitted workbooks. They were imported/exported with `artifact_tool`, stripped of document properties containing a personal account address, and normalized to fixed ZIP timestamps. Untouched originals are intentionally excluded from public GitHub and retained only in the author-side private provenance archive.

## Manuscript-facing results

### Expanded pathway validation

| Outcome | Result |
|---|---:|
| Pre-refinement complete-pathway correctness | **23/95 (24.2%)** |
| Outcome-aware refined correctness | **26/52 (50.0%)** |
| Absolute difference | **25.8 percentage points** |
| Overlap-aware bootstrap 95% CI | **14.4–37.5 percentage points** |
| Unique blinded review units | **115** |
| Shared / removed / added pathways | **32 / 63 / 20** |

Complete-pathway pre-adjudication agreement was 95.7%; Cohen’s kappa was 0.930 and Gwet’s AC1 was 0.937. Two submitted Expert A complete-pathway cells (`XPV-0052` and `XPV-0074`) differ from their deterministic component roll-up. The submitted source values are preserved, both cases are disclosed in QC output, and both are resolved to `No` by third-expert adjudication.

### Corrected held-out benchmark

On the 146-sentence common PubTator-compatible entity subset, strict micro-F1 was **0.904** for AISKG, **0.501** for PubTator 3.0, and **0.503** for the structured LLM. On all 150 sentences, directed strict relation micro-F1 was **0.651** for AISKG and **0.009** for the structured LLM.

PubTator returned no usable relation objects, so its relation performance is **not evaluable** and must not be reported as F1 = 0. The structured-LLM archive contains parseable JSON for 150/150 sentences and rejects 131 ungrounded or invalid proposed items before scoring. The source run recorded model revision `main`; item-level results replay exactly, but a future live model call is not claimed bit-for-bit identical.

## One-command additional-analysis replay

```bash
python -m pip install -e ".[dev]" --no-build-isolation
aiskg additional-analyses \
  --data-root data/frozen/additional_analyses_v3.1.2 \
  --output-root outputs/additional-analyses-v3.1.2
```

Equivalent repository commands:

```bash
python scripts/reproduce_additional_analyses_v3_1_2.py
python scripts/verify_v3_1_2_release.py
python scripts/execute_v3_1_2_notebook_smoke.py
```

The replay is locked to seed `20260817`, 10,000 overlap-aware pathway bootstrap replicates, 5,000 sentence-cluster benchmark bootstrap replicates, verified frozen-input hashes, and clean-output execution. Altered parameters, stale-output mode, or a single-byte change to any frozen workbook/table are rejected.

Successful execution creates:

```text
outputs/additional-analyses-v3.1.2/
├── ADDITIONAL_ANALYSES_SUCCESS.txt
├── COMBINED_REPRODUCIBILITY_MANIFEST.json
├── PUBLICATION_REPORTING_STATUS.md
├── SHA256SUMS.txt
├── pathway_validation/
│   ├── interrater_agreement_recomputed.csv
│   ├── reviewer_rating_matrix_long.csv
│   ├── third_expert_adjudication_audit.csv
│   ├── pathway_validation_final_labels_reconstructed.csv
│   ├── REVIEWER_WORKBOOK_QC.json
│   └── AISKG_Expanded_Pathway_Validation_Results_v3.1.2.xlsx
└── benchmark/
    ├── system_metrics.csv
    └── AISKG_three_system_benchmark_reproduced_v3.1.2.xlsx
```

A deterministic sibling archive, `outputs/AISKG_v3.1.2_additional_analyses_reproduced.zip`, is generated.

## Self-contained Google Colab notebook

Open `notebooks/AISKG_Framework_v3_1_2_Complete_Reproducibility.ipynb` and select **Runtime → Run all**. The notebook embeds all public v3.1.2 additional-analysis inputs and the replay runtime. No network, PubTator API, GPU, or live language-model call is required for manuscript reproduction.

The exact corrected external benchmark execution is retained separately as provenance at `notebooks/additional_analyses/AISKG_PubTator3_Structured_LLM_Benchmark_Corrected_Executed_Reference.ipynb`.

## Frozen v3.0.0 core pipeline

The original manuscript-snapshot workflow remains unchanged and verifies 285 expected-result assertions:

```bash
python run_pipeline.py --config configs/manuscript_frozen.yaml --run-id publication-v3 --clean
```

It covers retrieval, harmonization, deduplication, segmentation, embeddings, topic modelling, ontology-guided extraction, graph construction, pathway reconstruction, benchmarking, representation analyses, ablations, Monte Carlo checks, and deterministic packaging.

## Repository structure

```text
AISKG/
├── configs/                         # Frozen and live profiles
├── data/frozen/                     # Core bundles and v3.1.2 public replay inputs
├── data/reference/                  # Frozen core reference bundles
├── docs/                            # Architecture, methods, validation, and release guidance
├── expected/                        # Frozen expected-result specifications
├── manuscript/                      # Claim-to-output and availability text
├── notebooks/                       # Self-contained and executed reference notebooks
├── reference_outputs/               # Corrected source archive and reference outputs
├── scripts/                         # Replay, verification, notebook, packaging, upload helpers
├── src/aiskg/                       # Modular Python package
└── tests/                           # Unit, release, tamper, and integration tests
```

## Validation before upload

```bash
python -m pip install -e ".[dev]" --no-build-isolation
python verify_repository.py
pytest -q -m "not integration"
python scripts/verify_v3_1_2_release.py
python scripts/execute_v3_1_2_notebook_smoke.py
```

The full frozen core can also be tested with `pytest -q -m integration`.

## Citation and licence

Use `CITATION.cff` for the v3.1.2 software citation. Create a new version-specific repository archive/DOI after publishing tag `v3.1.2`; do not relabel a DOI belonging to an earlier archived version.

Source code is MIT licensed. Public data and frozen outputs are governed by `DATA_LICENSE.md`, `THIRD_PARTY_DATA_NOTICE.md`, and source-specific notices.

