# AISKG v3.2.0 — external biomedical relation benchmark release

Released: 2026-08-28

AISKG v3.2.0 is an additive methodological release. It preserves the deterministic v3.0.0 core and complete v3.1.2 reviewer/in-domain benchmark replay, and adds a new independently executed BioRED/BioREDirect external relation-classification analysis.

## Added

- Repository-integrated `aiskg_external_re` package.
- `aiskg external-re-benchmark` and `aiskg-external-re` commands.
- Repository-native GPU Colab notebook.
- Offline synthetic end-to-end smoke test.
- Public-safe result exporter that excludes third-party text and gold candidate rows.
- Frozen public metrics, aggregate audits, thresholds, text-free predictions, figures and sanitized provenance.
- v3.2.0 independent verifier, tests, CI and tagged-release integration.
- Manuscript-to-output map and explicit reporting boundaries.

## External benchmark results

| Scope | AISKG constrained transfer | BioREDirect |
|---|---:|---:|
| Sentence-local relation F1 | 0.386 (95% CI 0.355-0.415) | 0.617 (0.593-0.641) |
| Full-document relation F1 | 0.362 (0.339-0.386) | 0.568 (0.545-0.591) |

The constrained adapter exceeded the type-pair majority baseline by +0.074 F1 in the sentence-local analysis and +0.163 in the full-document stress test. BioREDirect remained substantially stronger.

## Non-negotiable reporting boundaries

- Gold entity mentions and normalized IDs were supplied to all external systems.
- The external endpoint is relation classification, not end-to-end NER plus RE.
- The AISKG rule/constrained systems are transfer adapters, not the unchanged v3.1.2 extractor.
- Sentence-local is the primary portability endpoint; full-document is a cross-sentence stress test.
- The BC8 test set is locked against further tuning.
- BioRED/BioREDirect text, gold candidate rows, official code and model weights are not redistributed.

## Preserved results

The v3.0.0 core still passes 285/285 assertions. The v3.1.2 reviewer replay still reconstructs 805 final ratings and 92 adjudications; pathway correctness remains 23/95 before and 26/52 after outcome-aware refinement. The corrected in-domain benchmark remains unchanged.
