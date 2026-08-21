# Release validation report — AISKG Framework v3.1.1

**Validation date:** 18 August 2026  
**Release status:** PASS for public GitHub packaging and manuscript-sharing use, subject to the reporting boundaries below.

## Release scope

AISKG v3.1.1 is a complete source-repository release built from the validated v3.0.0 frozen framework. It supersedes the unpublished v3.1.0 draft and replaces the invalid external-system run with the corrected executed PubTator3/structured-LLM benchmark notebook and corrected item-level output archive supplied on 18 August 2026.

The release has two reproducibility layers:

1. the unchanged v3.0.0 manuscript-snapshot core, including the original Section 1, Section 2, ablation, and 285 expected-result assertions; and
2. the corrected v3.1.1 expanded pathway-validation and three-system benchmark replay.

## Corrected-source provenance

| Source artifact | SHA-256 |
|---|---|
| Corrected executed benchmark notebook | `920d222921cf81887b0b83b244cbc093e57cf6c6ffe66389eeeb03f116fdec20` |
| Corrected benchmark output archive | `109f7af0ac4281a970e6d084daa16a70d0231d599c603fe340f928daae1fa31d` |
| Expanded pathway-validation notebook | `ce0e1af18623991a5df51a668215556b1ce6ce93c0142873b6704df3e9485de9` |
| Expanded pathway-validation output archive | `913355edbe2da32835e3bdae39fafd2d7f3d62832a93cfa92b5ec70366ec262c` |
| Frozen v3.0.0 GitHub-ready base | `b51d8f0b17b9bad7b3b6ab2f01fb10ab132eae01d7fd8f315c375fc52d31d759` |

The exact corrected benchmark notebook and its original output ZIP are retained as provenance under `notebooks/additional_analyses/` and `reference_outputs/additional_analyses_v3.1.1/`. Superseded failed-run tables, logs, empty-output pseudo-scores, and the invalid p-value are excluded from the public repository.

The released `benchmark_sentences.csv` is byte-identical to `data/heldout_sentences.csv` in the frozen Section 2 input archive; both have SHA-256 `cc98cc7ee6e8b248d161b0be5754c9db96bf31fb7c21175a7985615a23cb2701`. The 27-relation AISKG strict projection also reproduces the locked normalization rule already present in the frozen Section 2 engine rather than introducing a post hoc rule.

## Validation results

### Source, package, and unit validation

| Check | Result |
|---|---:|
| Python source compilation | PASS |
| Editable package build/install | PASS |
| Non-integration pytest suite | **23 passed, 1 deselected** |
| Independent v3.1.1 verifier | PASS |
| Frozen additional-analysis checksum entries | **30/30** |
| Corrected benchmark reference notebook | **13/13 code cells executed; 0 errors** |
| Self-contained notebook | **7/7 code cells executed; 0 errors** |
| Self-contained notebook generated checksums | **34 entries** |
| Locked seed/bootstrap/clean-output enforcement | PASS |
| Tampered frozen-input rejection | PASS |
| Byte-deterministic replay test | PASS |
| Notebook schema/error scan | PASS |
| ZIP integrity checks | PASS |
| Credential-pattern scan | PASS; no matching credentials detected |

### Byte-deterministic replay

Two independent clean replays from the same verified frozen inputs produced identical artifacts:

| Artifact | SHA-256 in both runs |
|---|---|
| `AISKG_v3.1.1_additional_analyses_reproduced.zip` | `aa5205189f79c34efdb77482bfda8cdf6ff4e084dc3c45f50fc598e520b28c17` |
| Pathway result workbook | `c255e9e9068bd56d3c7caf40df139af55777385999e66f99d776d43bb6bd06a8` |
| Benchmark result workbook | `8dc01dfac1708ef2bb00779ed6fe4ed9ba0ebdb87713066feb7cb620d9b69ade` |

The replay normalizes OOXML and ZIP metadata, verifies the 30 frozen inputs before calculation, deletes any prior output directory, and locks the manuscript-facing parameters to seed `20260817`, 10,000 pathway bootstrap replicates, and 5,000 benchmark bootstrap replicates.

### Self-contained master notebook

`notebooks/AISKG_Framework_v3_1_1_Complete_Reproducibility.ipynb` was executed in a clean directory with no repository checkout and no network or model call. It restored and verified its embedded public payload, completed both corrected analyses, generated all reporting artifacts and success markers, and exited without a notebook error.

### Frozen core validation

A clean frozen-core execution completed successfully and generated `AISKG_Framework_v3.0.0_Release.zip`.

| Frozen-core audit category | Passed |
|---|---:|
| Section 1 → Section 2 bridge | 22/22 |
| Frozen Section 2 expected results | 109/109 |
| Ablation expected results | 153/153 |
| Complete-pipeline marker | 1/1 |
| **Total** | **285/285** |

The generated core run contained `PIPELINE_SUCCESS.txt`, 208 release-manifest/checksum entries, and passed the independent run-directory verifier. The frozen integration test body reported one passed test; the same core pipeline and run-directory verifier were also executed directly and both exited successfully.

## Corrected results independently reproduced

### Expanded pathway validation

- Pre-refinement complete-pathway correctness: **23/95 (24.2%)**.
- Outcome-aware refined complete-pathway correctness: **26/52 (50.0%)**.
- Absolute improvement: **25.8 percentage points**.
- Overlap-aware bootstrap 95% CI: **14.4–37.5 percentage points**.
- Unique blinded units: **115** (32 shared, 63 removed, 20 added).

### Common-schema strict entity benchmark

| System | TP | FP | FN | Micro-F1 | 95% CI |
|---|---:|---:|---:|---:|---:|
| AISKG | 202 | 15 | 28 | **0.904** | 0.871–0.934 |
| PubTator3 | 173 | 288 | 57 | **0.501** | 0.451–0.552 |
| Structured LLM | 144 | 199 | 86 | **0.503** | 0.443–0.563 |

### Directed strict relation benchmark

| System | TP | FP | FN | Micro-F1 | 95% CI |
|---|---:|---:|---:|---:|---:|
| AISKG | 27 | 0 | 29 | **0.651** | 0.400–0.804 |
| Structured LLM | 1 | 157 | 55 | **0.009** | 0.000–0.032 |

PubTator3 returned no usable relation objects and is correctly marked **not evaluable** for relation extraction rather than assigned F1 = 0. The corrected structured-LLM output contained parseable JSON for 150/150 sentences, with 131 invalid or ungrounded proposed items rejected before scoring.

## Reporting boundaries

1. **Reviewer-level pathway agreement:** the public release reproduces the 115 final de-identified labels and endpoint statistics. The completed Expert A, Expert B, and third-expert workbooks were not present in the supplied pathway archive, so raw reviewer agreement and adjudication rationales are not independently reconstructed.
2. **Structured-LLM live rerun:** the corrected execution recorded `Qwen/Qwen2.5-7B-Instruct` at requested revision `main`, not an immutable model-weight commit. Archived predictions and all derived statistics are exactly replayable; a future live inference call is not claimed to be bit-for-bit identical.
3. **Frozen versus live evidence:** the v3.0.0 manuscript-snapshot outputs remain the exact frozen core. Any new API retrieval, model download, or literature refresh must be reported as a dated live analysis.
4. **Zenodo DOI:** a DOI assigned to an earlier archived release must not be relabelled as the v3.1.1 version DOI. Add a v3.1.1 DOI only after the new GitHub tag has been archived.

## Owner actions after extraction

Run the verification commands in `UPLOAD_INSTRUCTIONS.md`, push the extracted repository contents to a `release/v3.1.1` branch, confirm the included GitHub Actions workflow, merge only after a green pull request, create tag `v3.1.1`, and then archive that tag as a new version.
