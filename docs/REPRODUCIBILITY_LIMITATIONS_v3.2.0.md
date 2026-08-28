# AISKG v3.2.0 reproducibility and reporting limitations

1. The v3.0.0 frozen core and v3.1.2 reviewer/in-domain benchmark replay remain unchanged.
2. External BioRED/BioREDirect results use gold entities; they are not end-to-end NER plus RE.
3. The AISKG external systems are transfer adapters, not the unchanged mushroom-domain extractor.
4. The full-document result is a cross-sentence stress test; sentence-local is the primary portability endpoint.
5. The BC8 test set has been examined and must not be reused for model tuning.
6. BioREDirect source revision, dataset archive, model archive, and predictions are identified by commit/hash. Official third-party assets are not redistributed.
7. The public result subset excludes text-bearing candidates, PubTator files, and gold error rows; the author-side full source result archive is retained privately.
8. A future live download may fail or change availability even though recorded hashes define the executed experiment.
9. BioREDirect outperformed the AISKG transfer adapters; v3.2.0 does not claim state-of-the-art external relation extraction.
10. The external experiment does not isolate the causal effect of ontology constraints alone because an otherwise identical unconstrained text classifier was not included.
