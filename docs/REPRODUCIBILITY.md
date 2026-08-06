# Reproducibility model

## Level 1: exact manuscript reproduction

`configs/manuscript_frozen.yaml` starts from frozen, checksummed inputs and reproduces the reported Section 1 and Section 2 outputs. This is the authoritative route for the manuscript.

## Level 2: additive ablation reproduction

The nine ablation states use the same frozen corpus. Versioned per-variant checkpoints are independently audited and converted into publication tables, graphs, figures, JSON, XLSX, Markdown, and PDF outputs. The 153 manuscript-facing ablation checks cover 17 metrics for nine variants.

## Level 3: live refresh

Live PubMed, Scopus, and Web of Science retrieval is available in the upstream compatibility engine. It requires credentials, current service availability, model downloads, and expert topic curation. Live results will differ from the frozen snapshot as databases evolve.

## Deterministic controls

- Python random seed and NumPy seed;
- fixed Louvain seeds;
- fixed bootstrap and Monte Carlo iteration counts;
- SHA-256 input verification;
- formula-free expert workbooks;
- sample-manifest verification;
- expected numerical results;
- fixed ZIP member timestamps;
- versioned configuration snapshots;
- source and output manifests.

## Verification

```bash
aiskg verify --run-dir outputs/publication-v3
```

A valid run must contain `PIPELINE_SUCCESS.txt`, a complete manifest, matching file sizes, and matching SHA-256 hashes.
