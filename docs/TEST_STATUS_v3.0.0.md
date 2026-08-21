# Test status — AISKG Framework v3.0.0

## Completed local validation

- Python: 3.13.5
- Non-integration pytest suite: **10 passed**
- Full frozen integration test: **1 passed**
- Complete notebook-equivalent execution: **passed**
- Notebook cell errors: **0**
- Enabled ablation configurations: **9/9**
- Reproducibility audit: **285/285 passed**
- Output release ZIP: **generated and verified**
- Backward-compatible API keys: `release_zip` and `release_archive`

## CI target

The included GitHub Actions workflow runs on Python 3.12, the current Google Colab major/minor environment targeted by the project. It installs the project, runs unit tests, executes the complete frozen pipeline, verifies the generated manifest, asserts 285/285 checks, and uploads the release ZIP as an artifact.

## Hosted Colab status

The Colab notebook was executed from first cell to final cell with `nbclient` using its exact commands and repository files. Hosted Colab must be launched by the repository owner after upload because this environment cannot sign in to the owner's Google account.
