# AISKG v3.2.0 test status

The release must pass:

1. packaged-source manifest/checksum verification;
2. the existing non-integration unit test suite;
3. the complete v3.1.2 reviewer/in-domain benchmark verifier;
4. the v3.1.2 clean-directory replay notebook smoke test;
5. the v3.2.0 external frozen-result verifier;
6. the offline end-to-end external adapter/public-export smoke test; and
7. the frozen core CI profile with all 285 expected-result assertions.

The live BioREDirect GPU run is not repeated in standard CI. CI verifies the frozen public results, source commit/hash provenance, quality gates and an offline synthetic execution. The full official run remains available through the repository-native Colab notebook.
