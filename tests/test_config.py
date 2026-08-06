from __future__ import annotations

import math

from aiskg.config import AISKGConfig


def test_configuration_is_complete(repository_root):
    config = AISKGConfig.load(repository_root / "config.yaml")
    assert config.get("project.version") == "3.0.0"
    assert len(config.variants()) == 9
    assert config.variants()[0]["name"] == "FULL_FRAMEWORK"


def test_research_representation_weights_sum_to_one(repository_root):
    config = AISKGConfig.load(repository_root / "config.yaml")
    total = sum(float(value) for value in config.get("research_representation.weights").values())
    assert math.isclose(total, 1.0, abs_tol=1e-12)


def test_all_configured_inputs_exist(repository_root):
    config = AISKGConfig.load(repository_root / "config.yaml")
    for key in [
        "paths.section1_input_bundle",
        "paths.section2_input_bundle",
        "paths.ablation_frozen_bundle",
        "paths.ablation_expected_results",
        "paths.ontology_aliases",
        "paths.relation_rules",
    ]:
        assert config.path_value(key).exists(), key
