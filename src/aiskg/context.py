"""Run-context objects used by the unified pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import AISKGConfig


@dataclass(frozen=True)
class RunContext:
    config: AISKGConfig
    run_id: str
    run_dir: Path
    work_dir: Path
    legacy_section1_dir: Path
    legacy_section2_dir: Path
    ablation_dir: Path
    log_file: Path

    @classmethod
    def create(cls, config: AISKGConfig, run_id: str) -> "RunContext":
        output_root = config.path_value("paths.output_root")
        work_root = config.path_value("paths.work_root")
        run_dir = output_root / run_id
        work_dir = work_root / run_id
        return cls(
            config=config,
            run_id=run_id,
            run_dir=run_dir,
            work_dir=work_dir,
            legacy_section1_dir=run_dir / "outputs" / "legacy" / "section1" / "outputs",
            legacy_section2_dir=run_dir / "outputs" / "legacy" / "section2" / "outputs",
            ablation_dir=run_dir / "outputs" / "extensions" / "ablation",
            log_file=run_dir / "logs" / "pipeline.log",
        )
