from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from aiskg import run_pipeline
from aiskg.reproducibility import verify_run


@pytest.mark.integration
def test_complete_frozen_pipeline(repository_root, tmp_path):
    payload = yaml.safe_load((repository_root / "configs" / "ci.yaml").read_text(encoding="utf-8"))
    payload["paths"]["output_root"] = str(tmp_path / "outputs")
    payload["paths"]["work_root"] = str(tmp_path / "work")
    for key in ["section1_input_bundle", "section2_input_bundle", "ablation_frozen_bundle", "ablation_expected_results"]:
        path = Path(payload["paths"][key])
        payload["paths"][key] = str((repository_root / path).resolve())
    config_path = tmp_path / "integration.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    result = run_pipeline(config_path, run_id="integration", clean=True, verbose=False)
    assert result["release_zip"] == result["release_archive"]
    assert result["release_zip"].exists()
    assert len(result["audit"]) == 285
    assert set(result["audit"]["status"]) == {"PASS"}
    verification = verify_run(result["run_dir"])
    assert verification["files_checked"] > 100
