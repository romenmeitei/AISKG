# AISKG Framework

[![CI](https://github.com/romenmeitei/AISKG_Framework/actions/workflows/ci.yml/badge.svg)](https://github.com/romenmeitei/AISKG_Framework/actions/workflows/ci.yml)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/romenmeitei/AISKG_Framework/blob/main/notebooks/AISKG_Framework_v3_Complete_Pipeline.ipynb)

**AISKG Framework v3.0.0** is a unified, deterministic implementation of the AI-assisted ontology-guided semantic knowledge-graph workflow developed for biomedical literature mining. It merges the former AISKG Section 1 and Section 2 releases into one modular Python project while preserving their frozen manuscript outputs.

## Scope

The framework provides:

- PubMed, Scopus, and Web of Science retrieval code;
- metadata harmonization and hierarchical deduplication;
- sentence segmentation, SentenceTransformer embeddings, UMAP, HDBSCAN, and BERTopic;
- ontology-guided entity and relation extraction;
- canonical normalization and semantic quality control;
- outcome-aware graph refinement;
- graph, community, temporal, and pathway analyses;
- expert validation and biomedical NLP benchmarking;
- co-occurrence and research-representation analyses;
- HHI/Shannon and Monte Carlo robustness analyses;
- nine deterministic component ablations;
- expected-result verification, SHA-256 audits, manifests, and release ZIP generation.

The default `manuscript_snapshot` profile is the authoritative exact-reproduction route. The historical Section 1 and Section 2 engines are retained under `src/aiskg/legacy/` and are never overwritten.

## One-command execution

```bash
python -m pip install -e . --no-build-isolation
python run_pipeline.py --config configs/manuscript_frozen.yaml --run-id publication-v3 --clean
```

Successful execution creates:

```text
outputs/publication-v3/
├── PIPELINE_SUCCESS.txt
├── RELEASE_MANIFEST.csv
├── RUN_METADATA.json
├── SHA256SUMS.txt
├── AISKG_Framework_v3.0.0_Release.zip
└── outputs/
    ├── legacy/section1/
    ├── legacy/section2/
    ├── extensions/ablation/
    └── reproducibility_audit.csv
```

The final audit contains **285 checks**:

- 22 Section 1 → Section 2 bridge checks;
- 109 frozen Section 2 expected-result checks;
- 153 ablation checks;
- 1 complete-pipeline success check.

## Google Colab

Open `notebooks/AISKG_Framework_v3_Complete_Pipeline.ipynb` using the badge above and select **Runtime → Run all**. The notebook clones the repository, installs it, executes the complete frozen pipeline, verifies the release, displays the ablation summary, and downloads the release ZIP.

## CLI

```bash
aiskg run --config config.yaml --run-id publication-v3 --clean
aiskg stage graph --config config.yaml
aiskg ablation --config config.yaml --run-id ablation-v3
aiskg list-variants --config config.yaml
aiskg verify --run-dir outputs/publication-v3
```

## Python API

```python
from aiskg import run_pipeline

result = run_pipeline(
    config_path="configs/manuscript_frozen.yaml",
    run_id="publication-v3",
    clean=True,
)
print(result["release_zip"])
```

Both `release_zip` and the backward-compatible `release_archive` API keys are returned.

## Ablation variants

1. Full framework
2. Without canonical normalization
3. Without ontology type constraints
4. Without semantic quality filters
5. Without outcome-aware refinement
6. Support ≥1
7. Support ≥2
8. Support ≥3
9. Support ≥5

Each variant exports metrics, relations, aggregated edges, GraphML, pathway edges, pathway GraphML, and research-priority rankings. Aggregate outputs include CSV, XLSX, JSON, Markdown, PDF, and seven publication-oriented figures.

## Repository organization

```text
AISKG_Framework/
├── configs/                  # Execution profiles
├── data/frozen/              # Versioned frozen input bundles
├── data/reference/           # Ablation checkpoints and executed reference release
├── ontology/                 # Human-readable ontology assets
├── notebooks/                # Google Colab workflow
├── src/aiskg/                # Modular Python package
├── tests/                    # Unit and integration tests
├── docs/                     # Architecture and reproducibility documentation
├── manuscript/               # Result and software-citation mappings
├── config.yaml               # Central scientific configuration
├── run_pipeline.py           # One-command runner
└── pyproject.toml
```

## Frozen versus live operation

### Frozen manuscript profile

Uses checksummed corpus, extraction, validation, and ablation inputs. It does not rely on current API contents or model downloads and is intended to reproduce the reported results.

### Live refresh

The upstream compatibility engine contains current retrieval, embedding, BERTopic, and extraction functions. A live refresh requires API credentials and an explicit human topic-curation step; it is not expected to reproduce the historical record counts because databases and indexing evolve.

## Testing

```bash
pytest -q -m "not integration"
pytest -q -m integration
```

The GitHub Actions workflow runs unit tests, the complete frozen pipeline, output verification, and artifact upload.

## Reproducibility and data rights

The software is MIT licensed. Original repository documentation and code are copyright © 2026 Lourembam Romen Meitei, subject to institutional and contractual rights. Third-party bibliographic metadata and abstracts remain subject to publisher, author, database-provider, and institutional terms; see `THIRD_PARTY_DATA_NOTICE.md`.

## Historical repositories

- AISKG Section 1: <https://github.com/romenmeitei/AISKG_01_Framework>
- AISKG Section 2: <https://github.com/romenmeitei/AISKG_02_Framework>

These repositories remain provenance records. New development should occur in this unified repository.

## Citation

Use the metadata in `CITATION.cff`. After creating the GitHub `v3.0.0` release, archive it with Zenodo or another DOI-issuing service and update the software citation with the permanent DOI.
