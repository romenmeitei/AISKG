# Release validation report — AISKG Framework v3.0.0

## Scientific compatibility

The unified pipeline executed the frozen Section 1 engine, passed its reference and fixed-result checks, generated the validated bridge ZIP, and supplied that bridge directly to the frozen Section 2 v2.1.1 engine. The resulting manuscript-facing outputs remain under `outputs/legacy/`.

## Additive ablation layer

Nine ablation configurations were generated from the same frozen corpus. The release contains per-variant relations, aggregated edges, knowledge graphs, pathway graphs, research-priority rankings, metrics, figures, and reports. All 153 manuscript-facing ablation checks passed.

## Complete audit

| Audit category | Passed |
|---|---:|
| Section 1 → Section 2 bridge | 22/22 |
| Frozen Section 2 expected results | 109/109 |
| Ablation expected results | 153/153 |
| Complete-pipeline marker | 1/1 |
| **Total** | **285/285** |

## Automated tests

- 10 non-integration tests passed.
- 1 complete frozen integration test passed.
- Repository modules parsed and imported successfully.
- Deterministic ZIP unit test passed.
- Complete output-manifest verification passed.

## Notebook validation

`reference_outputs/AISKG_Framework_v3_Complete_Pipeline_Executed_Reference.ipynb` contains an executed reference run. It completed without cell errors and generated `AISKG_Framework_v3.0.0_Release.zip`.

## Remaining owner actions

1. Publish the package in the current `AISKG` GitHub repository (the original v3.0.0 draft used the working name `AISKG_Framework`).
2. Push the upload-ready source tree.
3. Confirm the GitHub Actions workflow is green on Python 3.12.
4. Open the public Colab badge and select Runtime → Run all.
5. Create GitHub release `v3.0.0` and attach the executed release ZIP.
6. Optionally archive the release in Zenodo and add the DOI to `CITATION.cff` and the manuscript.
