# AISKG v3.1.2 public release checklist

- [ ] Extract `AISKG_v3.1.2_GITHUB_READY_COMPLETE.zip` into a clean directory.
- [ ] Confirm `VERSION`, `pyproject.toml`, and `CITATION.cff` identify v3.1.2.
- [ ] Run `python verify_repository.py`.
- [ ] Run `pytest -q -m "not integration"`.
- [ ] Run `python scripts/verify_v3_1_2_release.py`.
- [ ] Run `python scripts/execute_v3_1_2_notebook_smoke.py`.
- [ ] Confirm 805 paired ratings and 92 adjudications are reported.
- [ ] Confirm `XPV-0052` and `XPV-0074` are disclosed as Expert A roll-up exceptions and adjudicated `No`.
- [ ] Confirm PubTator relations are reported as not evaluable, not zero.
- [ ] Confirm no untouched `Expert_A_completed.xlsx`, `Expert_B_completed.xlsx`, or `Third_Expert_completed.xlsx` is present.
- [ ] Keep `AISKG_v3.1.2_PRIVATE_SOURCE_PROVENANCE.zip` private.
- [ ] Create branch `release/v3.1.2`, push it, and open a pull request.
- [ ] Merge only after GitHub Actions passes.
- [ ] Create annotated tag `v3.1.2` and publish `RELEASE_NOTES_v3.1.2.md`.
- [ ] Mint a new version-specific archive/DOI and update citation metadata without relabelling an earlier DOI.
