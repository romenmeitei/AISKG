# Test status — AISKG Framework v3.1.1

**Local validation date:** 18 August 2026  
**Python used locally:** 3.13.5  
**CI target:** Python 3.12

## Completed validation

- Source compilation: **passed**.
- Editable package build/install: **passed**.
- Non-integration pytest suite: **23 passed, 1 deselected**.
- Frozen integration assertion body: **1 passed**; all 285 scientific assertions passed.
- Direct frozen core execution: **passed**.
- Frozen core reproducibility audit: **285/285 PASS**.
- Core release run-directory verification: **passed**.
- Independent corrected-analysis verifier: **passed**.
- Corrected additional-analysis data checksums: **30/30 passed**.
- Corrected executed benchmark notebook: **13/13 code cells executed, 0 errors**.
- Self-contained v3.1.1 notebook clean-directory smoke test: **passed**.
- Self-contained notebook execution: **7/7 code cells executed, 0 errors**.
- Self-contained notebook output checksums: **34 entries**.
- Locked seed/bootstrap/clean-output tests: **passed**.
- Frozen-input tamper-rejection test: **passed**.
- Two-run byte-determinism test: **passed**.
- Notebook schema/error scan: **passed**.
- ZIP integrity scan: **passed**.
- Credential-pattern scan: **passed; no matching credentials detected**.

## Deterministic artifact identity

Two independent clean replays generated the same hashes:

- Complete corrected result archive: `aa5205189f79c34efdb77482bfda8cdf6ff4e084dc3c45f50fc598e520b28c17`.
- Pathway workbook: `c255e9e9068bd56d3c7caf40df139af55777385999e66f99d776d43bb6bd06a8`.
- Benchmark workbook: `8dc01dfac1708ef2bb00779ed6fe4ed9ba0ebdb87713066feb7cb620d9b69ade`.

## Reproducibility products verified

- `AISKG_Framework_v3.0.0_Release.zip` from the unchanged frozen core.
- `AISKG_v3.1.1_additional_analyses_reproduced.zip` from the corrected replay.
- `AISKG_Framework_v3_1_1_Complete_Reproducibility.ipynb` as the self-contained reviewer-facing route.
- Exact corrected executed benchmark notebook and corrected source-output archive as provenance records.

## Hosted checks remaining

The repository owner must confirm the included GitHub Actions workflow after pushing the release branch and should run the Colab notebook from the public repository. Those hosted checks require access to the owner's GitHub and Google accounts and are not represented as completed here.
