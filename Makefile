.PHONY: install test integration run verify verify-v312 verify-v320 external-smoke external-run source-release

install:
	python -m pip install -e .[dev,external-re] --no-build-isolation

test:
	pytest -q -m "not integration"

integration:
	pytest -q -m integration

run:
	python run_pipeline.py --config configs/manuscript_frozen.yaml --run-id publication-v3 --clean

verify:
	aiskg verify --run-dir outputs/publication-v3

verify-v312:
	python scripts/verify_v3_1_2_release.py

verify-v320:
	python scripts/verify_v3_2_0_release.py

external-smoke:
	python scripts/run_external_re_smoke.py

external-run:
	aiskg external-re-benchmark --run-bioredirect --clean

source-release:
	python scripts/build_source_release.py
