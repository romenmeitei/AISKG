from __future__ import annotations

import argparse
import json
from pathlib import Path

from .replay import run_replay


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay AISKG v3.1.2 corrected additional analyses")
    parser.add_argument(
        "--data-root",
        default="data/frozen/additional_analyses_v3.1.2",
        help="Directory containing pathway/ and benchmark/",
    )
    parser.add_argument("--output-root", default="outputs/additional-analyses-v3.1.2")
    args = parser.parse_args()
    result = run_replay(
        Path(args.data_root),
        Path(args.output_root),
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "output_root": str(result.output_root),
                "output_archive": str(result.output_archive),
                "manifest": str(result.manifest),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
