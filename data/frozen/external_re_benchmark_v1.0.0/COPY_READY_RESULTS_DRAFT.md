# Copy-ready Results draft — verify journal wording before use

The external evaluation used gold BioRED/BioREDirect entity annotations and therefore measures relation extraction rather than end-to-end entity-plus-relation performance.

## Sentence Local
- **AISKGConstrainedTransfer**: precision 0.350, recall 0.430, F1 0.386 (95% bootstrap CI 0.355–0.415; TP=2029, FP=3769, FN=2694).
- **AISKGRuleTransfer**: precision 0.195, recall 0.465, F1 0.275 (95% bootstrap CI 0.249–0.302; TP=2197, FP=9071, FN=2526).
- **BioREDirect**: precision 0.591, recall 0.646, F1 0.617 (95% bootstrap CI 0.593–0.641; TP=3052, FP=2113, FN=1671).
- **TypePairMajority**: precision 0.356, recall 0.277, F1 0.311 (95% bootstrap CI 0.284–0.338; TP=1308, FP=2370, FN=3415).

Direction-aware exact relation results:
- **AISKGConstrainedTransfer**: precision 0.548, recall 0.427, F1 0.480 (95% bootstrap CI 0.447–0.513; TP=1596, FP=1315, FN=2141).
- **AISKGRuleTransfer**: precision 0.458, recall 0.413, F1 0.434 (95% bootstrap CI 0.402–0.468; TP=1545, FP=1831, FN=2192).
- **BioREDirect**: precision 0.676, recall 0.605, F1 0.639 (95% bootstrap CI 0.606–0.671; TP=2262, FP=1085, FN=1475).
- **TypePairMajority**: precision 0.532, recall 0.301, F1 0.384 (95% bootstrap CI 0.351–0.419; TP=1124, FP=989, FN=2613).

## Full Document
- **AISKGConstrainedTransfer**: precision 0.345, recall 0.382, F1 0.362 (95% bootstrap CI 0.339–0.386; TP=2297, FP=4361, FN=3721).
- **AISKGRuleTransfer**: precision 0.114, recall 0.469, F1 0.184 (95% bootstrap CI 0.167–0.201; TP=2821, FP=21858, FN=3197).
- **BioREDirect**: precision 0.557, recall 0.580, F1 0.568 (95% bootstrap CI 0.545–0.591; TP=3491, FP=2774, FN=2527).
- **TypePairMajority**: precision 0.150, recall 0.296, F1 0.199 (95% bootstrap CI 0.179–0.221; TP=1782, FP=10117, FN=4236).

Direction-aware exact relation results:
- **AISKGConstrainedTransfer**: precision 0.462, recall 0.308, F1 0.370 (95% bootstrap CI 0.343–0.395; TP=1411, FP=1645, FN=3166).
- **AISKGRuleTransfer**: precision 0.410, recall 0.383, F1 0.396 (95% bootstrap CI 0.366–0.427; TP=1753, FP=2525, FN=2824).
- **BioREDirect**: precision 0.688, recall 0.565, F1 0.620 (95% bootstrap CI 0.590–0.649; TP=2584, FP=1174, FN=1993).
- **TypePairMajority**: precision 0.459, recall 0.282, F1 0.349 (95% bootstrap CI 0.320–0.378; TP=1289, FP=1518, FN=3288).

## Paired comparisons

- sentence_local: TypePairMajority minus AISKGRuleTransfer F1 difference 0.037 (95% bootstrap CI 0.008–0.065); Holm-adjusted exact McNemar P=0.001099.
- sentence_local: TypePairMajority minus AISKGConstrainedTransfer F1 difference -0.074 (95% bootstrap CI -0.102–-0.046); Holm-adjusted exact McNemar P=0.1796.
- sentence_local: TypePairMajority minus BioREDirect F1 difference -0.306 (95% bootstrap CI -0.337–-0.274); Holm-adjusted exact McNemar P=0.001099.
- sentence_local: AISKGRuleTransfer minus AISKGConstrainedTransfer F1 difference -0.111 (95% bootstrap CI -0.137–-0.085); Holm-adjusted exact McNemar P=2.861e-05.
- sentence_local: AISKGRuleTransfer minus BioREDirect F1 difference -0.343 (95% bootstrap CI -0.377–-0.310); Holm-adjusted exact McNemar P=1.257e-08.
- sentence_local: AISKGConstrainedTransfer minus BioREDirect F1 difference -0.232 (95% bootstrap CI -0.264–-0.200); Holm-adjusted exact McNemar P=0.08555.
- full_document: TypePairMajority minus AISKGRuleTransfer F1 difference 0.015 (95% bootstrap CI 0.001–0.029); Holm-adjusted exact McNemar P=0.6562.
- full_document: TypePairMajority minus AISKGConstrainedTransfer F1 difference -0.163 (95% bootstrap CI -0.189–-0.137); Holm-adjusted exact McNemar P=1.
- full_document: TypePairMajority minus BioREDirect F1 difference -0.370 (95% bootstrap CI -0.399–-0.340); Holm-adjusted exact McNemar P=0.1235.
- full_document: AISKGRuleTransfer minus AISKGConstrainedTransfer F1 difference -0.179 (95% bootstrap CI -0.201–-0.157); Holm-adjusted exact McNemar P=1.
- full_document: AISKGRuleTransfer minus BioREDirect F1 difference -0.385 (95% bootstrap CI -0.413–-0.357); Holm-adjusted exact McNemar P=0.003113.
- full_document: AISKGConstrainedTransfer minus BioREDirect F1 difference -0.206 (95% bootstrap CI -0.234–-0.178); Holm-adjusted exact McNemar P=0.02213.

## Mandatory interpretation boundary

These external results use gold entity annotations and a new AISKG-derived transfer adapter. They do not demonstrate end-to-end cross-domain entity recognition, and they must not be described as performance of the unchanged mushroom-domain v3.1.2 extractor.
