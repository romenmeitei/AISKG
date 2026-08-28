from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "frozen" / "external_re_benchmark_v1.0.0"


def test_external_quality_gates_and_metrics() -> None:
    gates = json.loads((DATA / "QUALITY_GATES.json").read_text())
    assert gates["status"] == "PASS"
    assert gates["no_document_overlap"] is True
    assert gates["test_tuning_performed"] is False
    metrics = pd.read_csv(DATA / "system_metrics.csv")
    primary = metrics[(metrics["mode"] == "sentence_local") & (metrics["evaluation"] == "relation_type")].set_index("system")
    assert abs(float(primary.loc["AISKGConstrainedTransfer", "f1"]) - 0.3857047809143617) < 1e-12
    assert abs(float(primary.loc["BioREDirect", "f1"]) - 0.6173139158576052) < 1e-12


def test_public_frozen_results_exclude_text_and_gold_candidates() -> None:
    names = {p.name for p in DATA.rglob("*") if p.is_file()}
    assert not any(name.startswith("test_candidates_") for name in names)
    assert not any(name.endswith(".pubtator") for name in names)
    assert "error_analysis.csv" not in names
    for path in DATA.glob("predictions_*.csv"):
        columns = set(pd.read_csv(path, nrows=1).columns)
        assert not ({"text", "abstract", "context", "gold_relation", "gold_direction"} & columns)


def test_external_adapter_source_and_configuration_present() -> None:
    assert (ROOT / "src" / "aiskg_external_re" / "cli.py").is_file()
    assert (ROOT / "configs" / "external_re" / "benchmark_config.json").is_file()
    assert (ROOT / "ontology" / "external_re" / "biored_trigger_rules.json").is_file()
    assert (ROOT / "notebooks" / "additional_analyses" / "AISKG_External_RE_Benchmark_Colab_v1_1.ipynb").is_file()
