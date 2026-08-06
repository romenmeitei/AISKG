from __future__ import annotations

import pandas as pd

from aiskg.ablation import run_ablation
from aiskg.config import AISKGConfig


def test_ablation_expected_results(repository_root, tmp_path):
    config = AISKGConfig.load(repository_root / "config.yaml")
    result = run_ablation(config, tmp_path / "ablation", tmp_path / "work")
    audit = result["audit"]
    assert len(audit) == 153
    assert set(audit["status"]) == {"PASS"}
    summary = result["summary"].set_index("variant")
    assert int(summary.loc["FULL_FRAMEWORK", "nodes"]) == 38
    assert int(summary.loc["FULL_FRAMEWORK", "edges"]) == 77
    assert int(summary.loc["WITHOUT_OUTCOME_AWARE_REFINEMENT", "edges"]) == 86
    assert int(summary.loc["SUPPORT_GE_5", "pathway_count"]) == 14
