"""Verification helpers for completed AISKG runs and source releases."""
from __future__ import annotations

import csv
from pathlib import Path

from ..utils import sha256_file


def verify_run(run_dir: str | Path) -> dict[str, int]:
    root = Path(run_dir).resolve()
    success = root / "PIPELINE_SUCCESS.txt"
    if not success.exists():
        raise FileNotFoundError(f"Success marker missing: {success}")
    manifest = root / "RELEASE_MANIFEST.csv"
    if not manifest.exists():
        raise FileNotFoundError(f"Release manifest missing: {manifest}")
    checked = 0
    with manifest.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            path = root / row["path"]
            if not path.exists():
                raise FileNotFoundError(f"Manifest file missing: {row['path']}")
            if int(row["bytes"]) != path.stat().st_size:
                raise AssertionError(f"Size mismatch: {row['path']}")
            if row["sha256"] != sha256_file(path):
                raise AssertionError(f"SHA-256 mismatch: {row['path']}")
            checked += 1
    return {"files_checked": checked, "success_markers": 1}
