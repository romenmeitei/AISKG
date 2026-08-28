# AISKG external BioRED/BioREDirect benchmark v1.0.0

## Purpose

AISKG v3.2.0 adds an independent biomedical relation-extraction experiment to distinguish in-domain mushroom-toxicology performance from cross-domain portability. The analysis follows the released BioREDirect BC8 split and compares a leakage-controlled type-pair baseline, a transparent AISKG rule-transfer adapter, an AISKG constrained text-transfer adapter, and the official pretrained BioREDirect model.

## Reporting boundary

All systems receive gold entity mentions and normalized identifiers. The endpoint is relation classification, not end-to-end entity recognition plus relation extraction. `AISKGRuleTransfer` and `AISKGConstrainedTransfer` are new transfer adapters; they are not the unchanged v3.1.2 mushroom extractor. Sentence-local evaluation is primary and full-document evaluation is a cross-sentence stress test. The BC8 test results have been examined and the test split is locked against further tuning.

## Fixed design

- Train/development/test documents: 500/100/400, with no overlap.
- Seed: 20260826.
- Bootstrap iterations: 5,000 at the document level.
- Threshold selection: development only.
- BioREDirect resolved commit: `fc090435fa8198187ab5145da26d8abf01000131`.
- Official dataset SHA-256: `29aa0b2060f9d3dc66d9452412e741158f69fb06021c7e326174cb3f1a1c4a85`.
- Official model SHA-256: `f7c85ab60e9d61f3d06c682e432ac0a16ba56844a6389ec2941b23d567d9be00`.

## Headline results

| Scope | TypePairMajority | AISKGRuleTransfer | AISKGConstrainedTransfer | BioREDirect |
|---|---:|---:|---:|---:|
| Sentence-local relation F1 | 0.311 | 0.275 | **0.386** | **0.617** |
| Full-document relation F1 | 0.199 | 0.184 | **0.362** | **0.568** |

The constrained adapter exceeded the majority baseline by +0.074 F1 (95% bootstrap CI +0.046 to +0.102) in the primary sentence-local analysis and +0.163 (+0.137 to +0.189) in the full-document stress test. BioREDirect exceeded the constrained adapter by +0.232 (+0.200 to +0.264) and +0.206 (+0.178 to +0.234), respectively.

## Public data policy

The repository publishes metrics, aggregate audits, locked thresholds, figures, sanitized provenance, and prediction rows that contain identifiers and model outputs but no source text. It does not redistribute BioRED/BioREDirect corpus text, gold candidate rows, official model weights, official NCBI source code, `test_candidates_*.csv`, `error_analysis.csv`, or PubTator representations. The notebook retrieves official assets at runtime and verifies their hashes.

## Execution

Offline software check:

```bash
python scripts/run_external_re_smoke.py
```

Full GPU-backed run:

```bash
aiskg external-re-benchmark \
  --run-bioredirect \
  --clean
```

The repository-native Colab notebook is `notebooks/additional_analyses/AISKG_External_RE_Benchmark_Colab_v1_1.ipynb`.
