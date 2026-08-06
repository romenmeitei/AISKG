#!/usr/bin/env python3
"""Verify the source-repository manifest and SHA-256 values."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parent
    manifest = root / "PACKAGE_MANIFEST.csv"
    if not manifest.exists():
        raise SystemExit("PACKAGE_MANIFEST.csv is missing. Run scripts/build_source_release.py first.")
    checked = 0
    with manifest.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            path = root / row["path"]
            if not path.exists():
                raise SystemExit(f"MISSING: {row['path']}")
            if path.stat().st_size != int(row["bytes"]):
                raise SystemExit(f"SIZE MISMATCH: {row['path']}")
            if sha256(path) != row["sha256"]:
                raise SystemExit(f"SHA256 MISMATCH: {row['path']}")
            checked += 1
    print(f"Repository verification PASSED ({checked} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
