#!/usr/bin/env python3
"""Repository wrapper for the AISKG v3.1.2 corrected additional analyses."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiskg.additional_analyses import run_replay


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output-root", default="outputs/additional-analyses-v3.1.2")
    args = parser.parse_args()

    repository = Path(args.repo_root).resolve()
    output = Path(args.output_root)
    if not output.is_absolute():
        output = repository / output
    result = run_replay(
        repository / "data/frozen/additional_analyses_v3.1.2",
        output,
    )
    print(
        json.dumps(
            {
                "release": "3.1.2",
                "status": "PASS",
                "output_root": str(result.output_root),
                "output_archive": str(result.output_archive),
                "success_marker": str(result.success_marker),
                "manifest": str(result.manifest),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
