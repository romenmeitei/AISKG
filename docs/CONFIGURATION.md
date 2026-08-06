# Configuration reference

`config.yaml` is the central configuration. Profile files under `configs/` are complete, standalone configurations.

## Primary switches

- `stages.*`: enable or disable pipeline groups.
- `extraction.ontology_constraints`
- `extraction.canonical_normalization`
- `extraction.semantic_quality_filters`
- `extraction.outcome_aware_refinement`
- `graph.evidence_threshold`
- `graph.confidence_threshold`
- `embedding.model_name`
- `topic_model.enabled`
- `pathway.enabled`
- `benchmarking.enabled`
- `validation.*`
- `research_representation.monte_carlo_iterations`
- `ablation.variants`
- `reproducibility.*`

The loader rejects missing required keys and research-representation weights that do not sum to one. New modules never silently substitute scientific defaults. The frozen compatibility engines remain version-pinned to preserve published results.
