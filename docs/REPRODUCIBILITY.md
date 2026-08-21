# Reproducibility

## Additional analyses v3.1.2

```bash
python -m pip install -e ".[dev]" --no-build-isolation
python scripts/reproduce_additional_analyses_v3_1_2.py
```

The equivalent self-contained route is `notebooks/AISKG_Framework_v3_1_2_Complete_Reproducibility.ipynb`.

The replay verifies all files under `data/frozen/additional_analyses_v3.1.2/`, including metadata-sanitized completed Expert A, Expert B, and third-expert workbooks. It recomputes seven agreement tables, validates the exact 92-case adjudication set, reconstructs all 805 final ratings, and only then calculates pathway statistics. The benchmark module replays the corrected item-level gold and predictions.

Locked parameters are seed `20260817`, 10,000 pathway bootstraps, 5,000 benchmark bootstraps, and `clean=True`. Input tampering, altered parameters, and stale-output mode cause failure.

## Frozen v3.0.0 core

```bash
python run_pipeline.py --config configs/manuscript_frozen.yaml --run-id publication-v3 --clean
```

This route reproduces the original frozen core and evaluates 285 expected-result assertions.

## Independent checks

```bash
python verify_repository.py
pytest -q -m "not integration"
python scripts/verify_v3_1_2_release.py
python scripts/execute_v3_1_2_notebook_smoke.py
```

The structured-LLM archived predictions replay exactly, but future live inference is not bitwise guaranteed because the source run recorded model revision `main`. PubTator relations are not evaluable.
