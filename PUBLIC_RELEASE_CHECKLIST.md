# AISKG v3.2.0 public release checklist

- [ ] Extract `AISKG_v3.2.0_GITHUB_READY_COMPLETE.zip` into a clean directory.
- [ ] Confirm `VERSION`, `pyproject.toml`, `src/aiskg/__init__.py`, and `CITATION.cff` identify v3.2.0.
- [ ] Run `python verify_repository.py`.
- [ ] Run `pytest -q -m "not integration"`.
- [ ] Run `python scripts/verify_v3_1_2_release.py`.
- [ ] Run `python scripts/execute_v3_1_2_notebook_smoke.py`.
- [ ] Run `python scripts/verify_v3_2_0_release.py`.
- [ ] Run `python scripts/run_external_re_smoke.py`.
- [ ] Confirm the public external result directory and ZIP contain no `test_candidates_*`, `error_analysis.csv`, `.pubtator`, official datasets, source checkout or model weights.
- [ ] Confirm all external quality gates report PASS and no test tuning.
- [ ] Confirm the BC8 test-lock warning is present.
- [ ] Confirm BioREDirect is reported as stronger than the AISKG adapters.
- [ ] Keep `AISKG_External_RE_Benchmark_Results_v1_0.zip` author-side; do not upload it to the public repository.
- [ ] Create branch `release/v3.2.0`, push it and open a pull request.
- [ ] Merge only after GitHub Actions passes.
- [ ] Create annotated tag `v3.2.0` and publish `RELEASE_NOTES_v3.2.0.md`.
- [ ] Mint a new version-specific archive/DOI and update `CITATION.cff` and the manuscript after Zenodo returns the DOI.
