# AISKG v3.1.2 frozen additional analyses

This directory contains the complete public manuscript-facing inputs for deterministic replay of the expanded pathway validation and corrected three-system benchmark.

## Pathway validation

The `pathway/` directory now includes the three completed, metadata-sanitized reviewer workbooks. The release independently:

1. reads all 115 Expert A and 115 Expert B pathway rows;
2. recomputes agreement for seven dimensions from 805 paired ratings;
3. identifies 22 direct disagreements and 84 cases containing Borderline/Uncertain ratings;
4. verifies the exact 92-case union requiring third-expert adjudication;
5. checks each adjudication against the originating labels, comments, path text, and template;
6. reconstructs all 805 final binary labels; and
7. confirms exact identity with the previously released final-label table before calculating pathway statistics.

The scientific endpoint remains 23/95 (24.2%) before refinement and 26/52 (50.0%) after outcome-aware refinement, with an absolute improvement of 25.8 percentage points and an overlap-aware bootstrap 95% CI of 14.4–37.5 percentage points.

## Corrected benchmark

The `benchmark/` directory preserves the corrected v3.1.1 three-system item-level outputs and statistical reference tables. PubTator3 relations remain **not evaluable** because no usable relation objects were returned; they are never scored as zero. The structured-LLM item-level replay is exact, while a future live model rerun is not claimed bit-for-bit identical because the source execution recorded mutable revision `main`.

## Locked contract

The manuscript-facing replay accepts only seed `20260817`, 10,000 overlap-aware pathway bootstrap replicates, 5,000 sentence-cluster benchmark bootstrap replicates, verified frozen inputs, and a clean output directory. Generated XLSX and ZIP artifacts use normalized metadata and timestamps.

Use `SHA256SUMS.txt` to verify every frozen file.
