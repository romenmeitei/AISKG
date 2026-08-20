# AISKG v3.1.2 additional analyses

The v3.1.2 replay has two independent modules: complete reviewer-level pathway validation and the corrected held-out three-system benchmark.

## Pathway reviewer replay

The public inputs are three sanitized completed XLSX workbooks. The replay validates workbook hashes/container metadata, cached source values, formula coverage, row identity, static source fields, allowed labels, adjudication eligibility, source comments, rationales, and final binary decisions.

A third-expert row is required whenever Expert A and Expert B disagree or either source rating is Borderline/Uncertain. This produces 22 direct disagreements, 84 nondefinitive cases, and a 92-key union. The third workbook contains exactly those 92 unique keys—no missing, duplicate, or extra adjudications.

Final ratings are assigned from definitive A/B consensus for 713 rating pairs and from third-expert adjudication for 92 rating pairs. The reconstructed 805 labels and sources are then compared with the frozen public final-label table. Endpoint analysis proceeds only if every value matches.

## Pathway statistics

System proportions use Wilson 95% confidence intervals. The primary difference uses 10,000 unique-path bootstrap samples while preserving overlapping system membership. The historical pool consists of shared plus removed pathways; the refined pool consists of shared plus added pathways.

## Corrected benchmark

The benchmark uses the frozen 150-sentence held-out corpus. Entity scoring is one-to-one within sentence/type. The common PubTator-compatible comparison contains 146 PMID-eligible sentences. Relation scoring uses normalized directed triples. Sentence-cluster bootstrap confidence intervals and paired differences use 5,000 replicates; exact McNemar tests use Holm adjustment.

PubTator returned no usable relation objects and is therefore not evaluable for relation extraction. The structured-LLM validation rejects ungrounded/invalid items before scoring.
