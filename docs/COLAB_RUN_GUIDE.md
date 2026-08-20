# Google Colab run guide — AISKG v3.1.2

1. Open `notebooks/AISKG_Framework_v3_1_2_Complete_Reproducibility.ipynb` from the README Colab badge.
2. Select **Runtime → Run all**.
3. Keep seed `20260817`, pathway bootstrap count `10000`, and benchmark bootstrap count `5000` unchanged for manuscript reproduction.
4. Leave `RUN_CORE_FROZEN_PIPELINE = False` unless the unchanged v3.0.0 core must also be rerun.
5. After completion, confirm the final cell reports 805 reviewer pairs, 92 adjudications, and status `PASS`.
6. Download `AISKG_v3.1.2_additional_analyses_reproduced.zip` when required.

The notebook is self-contained and requires no live PubTator or language-model call. It restores three public reviewer workbooks, validates all source/adjudication records, reconstructs final labels, reproduces pathway and benchmark results, and emits checksums. PubTator relation performance must remain reported as not evaluable.
