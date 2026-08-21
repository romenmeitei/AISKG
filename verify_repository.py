#!/usr/bin/env python3
"""Verify the packaged source manifest and its independent SHA-256 list."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aiskg.reproducibility.source_verifier import verify_source_repository


def main() -> int:
    try:
        checked = verify_source_repository(ROOT)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Repository verification PASSED ({checked} files; manifest and SHA256SUMS agree)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
