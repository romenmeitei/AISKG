#!/usr/bin/env python3
"""Repository-level one-command AISKG runner."""
from __future__ import annotations

import argparse
import json

from aiskg import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the unified AISKG Framework")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--run-id")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    result = run_pipeline(
        args.config,
        run_id=args.run_id,
        clean=True if args.clean else None,
        verbose=not args.quiet,
    )
    print(json.dumps({
        "run_dir": str(result["run_dir"]),
        "release_zip": str(result["release_zip"]),
        "release_archive": str(result["release_archive"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
