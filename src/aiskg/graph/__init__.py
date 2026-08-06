"""Graph stage public API."""
from ..stages import run_stage

def run(config_path: str = "config.yaml", run_id: str | None = None):
    return run_stage("graph", config_path, run_id)

__all__ = ["run"]
