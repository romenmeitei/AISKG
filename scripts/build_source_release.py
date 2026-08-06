#!/usr/bin/env python3
"""Create the upload-ready source manifest, checksums, and source archive."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiskg.reproducibility.packaging import build_source_manifests
from aiskg.utils import deterministic_zip


def main() -> int:
    root = ROOT
    for path in [root / "outputs", root / ".aiskg_work", root / ".pytest_cache", root / ".ruff_cache"]:
        shutil.rmtree(path, ignore_errors=True)
    for path in root.rglob("__pycache__"):
        shutil.rmtree(path, ignore_errors=True)
    for path in root.glob("*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)
    for path in (root / "src").glob("*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)

    archive = root.parent / "AISKG_Framework_v3.0.0_GITHUB_READY.zip"
    manifest, checksums = build_source_manifests(root)
    deterministic_zip(root, archive, exclude={"AISKG_Framework_v3.0.0_GITHUB_READY.zip"})
    print(f"Manifest: {manifest}")
    print(f"Checksums: {checksums}")
    print(f"Source archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
