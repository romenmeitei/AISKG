# AISKG external benchmark public result subset

This directory contains metrics, aggregate audits, figures, locked thresholds, and system prediction rows from the BioRED/BioREDirect external relation benchmark.

It intentionally excludes BioRED/BioREDirect text, gold candidate rows, official model weights, NCBI source code, `test_candidates_*.csv`, `error_analysis.csv`, and PubTator files. The repository notebook retrieves official third-party assets at runtime and verifies their hashes.

All systems used gold entity mentions and normalized identifiers. The external endpoint is relation classification, not end-to-end NER plus RE. `AISKGRuleTransfer` and `AISKGConstrainedTransfer` are transfer adapters rather than the unchanged mushroom-domain extractor. Sentence-local evaluation is primary; full-document evaluation is a cross-sentence stress test. The BC8 test set is locked against further tuning.
