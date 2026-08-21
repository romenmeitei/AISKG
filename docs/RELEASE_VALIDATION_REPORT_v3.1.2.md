# Release validation report — AISKG Framework v3.1.2

**Validation date:** 18 August 2026  
**Release status:** PASS — GitHub-ready public reproducibility package  
**Supersedes:** v3.1.1

## Release scope

AISKG v3.1.2 preserves the deterministic v3.0.0 frozen manuscript pipeline and the corrected three-system benchmark introduced in v3.1.1. It adds the completed Expert A, Expert B, and third-expert pathway-validation workbooks and closes the remaining reviewer-level reproducibility gap.

The public package contains metadata-sanitized, content-equivalent reviewer workbooks. Untouched source uploads are excluded because their document properties contained a personal account address; the originals are retained only in the separate private provenance archive.

## Reviewer-workbook audit

| Check | Result |
|---|---:|
| Expert A pathway rows | 115 |
| Expert B pathway rows | 115 |
| Rating dimensions | 7 |
| Paired A/B ratings | 805 |
| Direct A–B disagreements | 22 |
| Cases containing Borderline/Uncertain | 84 |
| Unique cases requiring third review | 92 |
| Third-expert rows supplied | 92 |
| Missing / duplicate / extra adjudications | 0 / 0 / 0 |
| Definitive A/B consensus ratings | 713 |
| Third-expert final labels | 88 No; 4 Yes |
| Reconstructed final ratings matching prior public table | 805/805 |

All 92 adjudication rows were matched to the originating validation ID, pathway text, pathway template, rating dimension, Expert A label/comment, and Expert B label/comment. Every final label was binary and every adjudicator rationale was nonblank.

### Independently recomputed agreement

| Dimension | Raw agreement | Cohen’s kappa | Gwet’s AC1 | Disagreements |
|---|---:|---:|---:|---:|
| Entities | 0.965 | 0.930 | 0.931 | 4 |
| Relations | 0.957 | 0.931 | 0.937 | 5 |
| Direction | 1.000 | 1.000 | 1.000 | 0 |
| Sequence | 1.000 | 1.000 | 1.000 | 0 |
| Terminal class | 0.991 | 0.983 | 0.983 | 1 |
| Evidence support | 0.939 | 0.908 | 0.909 | 7 |
| Complete pathway | 0.957 | 0.930 | 0.937 | 5 |

### Transparent source exceptions

Expert A contains two submitted `complete_pathway_correct` values, `XPV-0052` and `XPV-0074`, that differ from the deterministic roll-up of their six component ratings. The source cells were preserved rather than silently edited. Both cases were explicitly included in third-expert adjudication and resolved to `No`. Expert B contained no such roll-up exception.

## Workbook privacy and integrity

The three public workbooks were imported and exported with `artifact_tool`, checked against the uploaded sheets for values and formulas, stripped of OOXML document properties, and rewritten with fixed ZIP timestamps. Public hashes are:

| Public workbook | SHA-256 |
|---|---|
| `Expert_A_completed_public.xlsx` | `bf3dbf599fa7176fb6f54c5102da12276791f689885b92ea9f585b1471e9d447` |
| `Expert_B_completed_public.xlsx` | `849adf9dd1522ead303d0fa481591a70777bf03ef8cef33a096f95bf66dcad4e` |
| `Third_Expert_completed_public.xlsx` | `c86c0d4bfdc10b0713f7ded76331135bc806092a81a38794dc648308439751e5` |

The generated pathway and benchmark Excel workbooks were inspected with `artifact_tool`. Key ranges contained the expected values, no `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, or `#N/A` errors were found, and rendered previews confirmed readable headers, bounded columns, wrapped evidence fields, filters, freeze panes, and three-decimal statistical displays.

## Scientific replay results

### Expanded pathway validation

| Endpoint | Reproduced result |
|---|---:|
| Pre-refinement correctness | 23/95 (24.2%) |
| Outcome-aware refined correctness | 26/52 (50.0%) |
| Absolute difference | 25.8 percentage points |
| Overlap-aware bootstrap 95% CI | 14.4–37.5 percentage points |
| Unique blinded review units | 115 |
| Shared / removed / added | 32 / 63 / 20 |

### Corrected three-system benchmark

| Task/system | Reproduced result |
|---|---:|
| AISKG common-schema strict entity micro-F1 | 0.904 |
| PubTator3 common-schema strict entity micro-F1 | 0.501 |
| Structured LLM common-schema strict entity micro-F1 | 0.503 |
| AISKG directed strict relation micro-F1 | 0.651 (27 TP, 0 FP, 29 FN) |
| Structured LLM directed strict relation micro-F1 | 0.009 (1 TP, 157 FP, 55 FN) |
| PubTator3 relation extraction | Not evaluable—no usable relation objects |
| Structured-LLM valid JSON | 150/150 sentences |
| Rejected ungrounded/invalid LLM items | 131 |

The release prevents PubTator3 relation performance from being represented as F1 = 0. The corrected source execution recorded `Qwen/Qwen2.5-7B-Instruct` revision `main`; archived item-level predictions and statistics are reproducible, but a future live inference call is not claimed to use bit-identical weights.

## Executable validation

| Validation | Result |
|---|---:|
| Python source compilation | PASS |
| Non-integration pytest suite | 28 passed; 1 deselected |
| Frozen v3.0.0 core audit | 285/285 PASS |
| Core generated files independently verified | 208 |
| v3.1.2 frozen-input checksum entries | 35/35 PASS |
| Reviewer paired ratings replayed | 805 |
| Required adjudications verified | 92/92 |
| Corrected executed benchmark notebook | 13/13 code cells executed; no error output |
| Self-contained v3.1.2 notebook | 11 cells; 7/7 code cells executed |
| Notebook-produced checksum entries | 44 |
| Source repository manifest | 174 files; manifest and SHA list agree |
| Direct public text files scanned for e-mail/credential patterns | 153; no matches |
| Untouched reviewer workbooks in public tree | 0 |
| Private reviewer document-property address hits in public files/archives | 0 |
| Published bibliographic e-mail occurrences inside frozen/reference archives | 3,557; third-party source metadata disclosed in `THIRD_PARTY_DATA_NOTICE.md` |
| Superseded failed-run artifacts in public tree | 0 |

## Determinism checks

Two independent clean additional-analysis runs produced byte-identical outputs:

| Artifact | SHA-256 |
|---|---|
| `AISKG_v3.1.2_additional_analyses_reproduced.zip` | `5246bf827bec44b9eccfe284761426c29d771241ec94e0943199e0184a565690` |
| Pathway results workbook | `9e21c1499155c10397fabcbee8c1ac29f8c9d0a3b626f9476da4473d13c71df1` |
| Benchmark results workbook | `34cb44fec595bc4e826db8b5a050c5deea37c039648c8cd0edee6606ff655350` |
| Recomputed agreement CSV | `0496acf371ad77175c1cd83a6a1ae9f7ec246f7f229ea8e02c4ce41287b6fccf` |
| Reviewer QC JSON | `489822c947282262fe418c6c49c8672b51063f1191d0393262e1563e8888c8e2` |
| Reconstructed final-label CSV | `725b201ba1cf04bd65cfbd733724f7fcc4d88828335474c51a7e8eb4ceee8ac7` |

The self-contained notebook has SHA-256 `23472daad47f42373c5cc1f9c007f06565b5c54cf75d6f9b5febf35806f64b38`; its embedded payload hash is `ca3b345bb97ffe93e2fbf1d677330f86f243329e4a6db5f42c29cebcfd2ae2c9`.

## Reporting boundaries

1. The submitted reviewer values are reproduced exactly; the two disclosed Expert A roll-up exceptions are not corrected in-place and are resolved only through recorded third-expert decisions.
2. Sanitized public workbooks are content-equivalent but intentionally not byte-identical to the private originals.
3. PubTator3 relation extraction is not evaluable and must not be reported as zero performance.
4. Archived structured-LLM predictions are reproducible; future live inference is not bitwise guaranteed because the source run used mutable revision `main`.
5. Live literature retrieval, PubTator services, and other external APIs are not required for the frozen manuscript replay and may change independently.
6. A DOI belonging to an earlier release must not be relabelled as v3.1.2. Archive the `v3.1.2` tag as a new version.

## Final disposition

The v3.1.2 public repository is suitable for GitHub release and manuscript sharing. Use only the v3.1.2 package and tag; v3.1.1 remains a historical superseded release.
