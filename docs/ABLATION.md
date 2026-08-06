# Ablation study

All ablations use the same frozen corpus, gold annotations, graph evidence, and research-representation inputs.

## Configurations

- `FULL_FRAMEWORK`
- `WITHOUT_CANONICAL_NORMALIZATION`
- `WITHOUT_ONTOLOGY_TYPE_CONSTRAINTS`
- `WITHOUT_SEMANTIC_QUALITY_FILTERS`
- `WITHOUT_OUTCOME_AWARE_REFINEMENT`
- `SUPPORT_GE_1`
- `SUPPORT_GE_2`
- `SUPPORT_GE_3`
- `SUPPORT_GE_5`

## Metrics

Entity precision/recall/F1, relation precision/recall/F1, exact-triple accuracy, directionality accuracy, nodes, edges, density, communities, modularity, largest connected component, pathway count, fractional HHI, normalized Shannon entropy, research-priority rankings, and Monte Carlo ranking robustness.

## Output files

- `ablation_summary.csv`
- `ablation_metrics.xlsx`
- `ablation_results.json`
- `ABLATION_REPORT.md`
- `AISKG_Ablation_Summary.pdf`
- seven PNG comparison figures
- per-variant CSV and GraphML outputs

## Interpretation safeguard

Ablation results are additive. They do not replace the blinded expert-validation results or modify the frozen manuscript outputs.
