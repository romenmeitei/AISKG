# Reproducibility limitations and reporting rules — AISKG v3.1.1

## Pathway human validation

The public release includes the 115 de-identified final-label records and all tables needed to reproduce the reported endpoint statistics. The source archive contained blank reviewer templates rather than the completed Expert A, Expert B, and third-expert workbooks. Do not state that the raw reviewer agreement matrix or adjudicator rationales were independently reconstructed from this repository.

## Corrected external benchmark

The corrected PubTator and structured-LLM item-level predictions are archived and fully sufficient to reproduce the reported metrics, confidence intervals, paired bootstrap differences, exact tests, and figures.

PubTator relation performance is not evaluable because the service returned no usable relation objects. Do not convert this operational absence into an F1 value of zero.

## Model revision

The corrected structured-LLM execution used `Qwen/Qwen2.5-7B-Instruct` with requested revision `main`. The exact resolved model-weight commit was not recorded. Therefore:

- the archived item-level predictions and derived statistics are exactly replayable;
- the executed notebook is valid provenance for the completed run;
- a future live model invocation is not guaranteed to reproduce identical tokens or predictions;
- a new live manuscript benchmark should pin an immutable model commit and archive raw responses.

## Frozen versus live workflows

The v3.0.0 `manuscript_snapshot` profile remains the exact frozen core route. API calls, model downloads, or refreshed literature retrievals are time-stamped live analyses and must be reported separately from frozen reproduction.
