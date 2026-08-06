.PHONY: install test integration run verify source-release

install:
	python -m pip install -e .[dev] --no-build-isolation

test:
	pytest -q -m "not integration"

integration:
	pytest -q -m integration

run:
	python run_pipeline.py --config configs/manuscript_frozen.yaml --run-id publication-v3 --clean

verify:
	aiskg verify --run-dir outputs/publication-v3

source-release:
	python scripts/build_source_release.py
