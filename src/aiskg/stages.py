"""Independent stage execution helpers.

In the frozen publication profile, upstream stages are intentionally replayed
as one checksummed Section 1 group and downstream stages as one checksummed
Section 2 group.  The grouping preserves exact historical outputs while each
public module remains independently executable through this stage interface.
"""
from __future__ import annotations

import copy
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .config import AISKGConfig
from .pipeline import run_pipeline

UPSTREAM_STAGES = {"retrieval", "preprocessing", "embedding", "topic_model", "extraction"}
DOWNSTREAM_STAGES = {"graph", "pathway", "benchmarking", "validation", "representation", "visualization"}


def run_stage(stage: str, config_path: str | Path = "config.yaml", run_id: str | None = None) -> dict[str, Any]:
    stage = stage.strip().lower()
    if stage not in UPSTREAM_STAGES | DOWNSTREAM_STAGES | {"ablation", "full"}:
        raise ValueError(f"Unknown stage: {stage}")
    config = AISKGConfig.load(config_path)
    payload = copy.deepcopy(config.data)

    if stage == "full":
        return run_pipeline(config_path, run_id=run_id)
    payload["stages"]["section1_snapshot"] = stage in UPSTREAM_STAGES
    payload["stages"]["section2_snapshot"] = stage in DOWNSTREAM_STAGES
    payload["stages"]["ablation"] = stage == "ablation"
    payload["project"]["run_id"] = run_id or f"stage-{stage}"

    temp_dir = config.repository_root / ".aiskg_work" / "stage_configs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{stage}.yaml"
    temp_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    try:
        return run_pipeline(temp_path, run_id=payload["project"]["run_id"])
    finally:
        temp_path.unlink(missing_ok=True)
