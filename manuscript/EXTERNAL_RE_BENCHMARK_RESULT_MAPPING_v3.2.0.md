# Manuscript-to-output mapping: external BioRED/BioREDirect benchmark

| Manuscript claim | Frozen public output |
|---|---|
| 500/100/400 split, no overlap | `candidate_split_audit.csv`, `QUALITY_GATES.json`, `run_manifest_public.json` |
| Sentence-local AISKG constrained F1 0.386 | `system_metrics.csv` |
| Sentence-local BioREDirect F1 0.617 | `system_metrics.csv` |
| Full-document AISKG constrained F1 0.362 | `system_metrics.csv` |
| Full-document BioREDirect F1 0.568 | `system_metrics.csv` |
| Constrained minus majority +0.074 / +0.163 | `paired_comparisons.csv` |
| BioREDirect minus constrained +0.232 / +0.206 | `paired_comparisons.csv` |
| Relation-specific F1 | `per_relation_metrics.csv` |
| Development-only thresholds | `locked_development_thresholds.json` |
| Source commit and official asset hashes | `run_manifest_public.json` |
| All quality gates passed | `QUALITY_GATES.json`, `SUCCESS.txt` |

Reporting must state that gold entities were supplied; the AISKG systems are transfer adapters; sentence-local is primary; full-document is a stress test; BioREDirect was stronger; and BC8 is locked against further tuning.
