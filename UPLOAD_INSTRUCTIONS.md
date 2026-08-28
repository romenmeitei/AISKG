# Upload instructions — AISKG v3.2.0

This is a complete repository package, not an overlay-only archive. Read `docs/GITHUB_UPLOAD_GUIDE.md` before changing the public repository.

Verify locally:

```bash
python -m pip install -e ".[dev,external-re]" --no-build-isolation
python verify_repository.py
pytest -q -m "not integration"
python scripts/verify_v3_1_2_release.py
python scripts/execute_v3_1_2_notebook_smoke.py
python scripts/verify_v3_2_0_release.py
python scripts/run_external_re_smoke.py
```

Copy the verified tree into a fresh clone, use branch `release/v3.2.0`, and never overwrite `main` directly. The helpers in `scripts/upload_to_github.sh` and `.ps1` refuse to run outside a Git clone and push only the release branch.

Do not add the author-side full external result ZIP or any official BioRED/BioREDirect corpus/model asset to public GitHub.
