"""Command-line interface for AISKG."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import AISKGConfig
from .pipeline import run_pipeline
from .reproducibility import verify_run
from .stages import run_stage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aiskg", description="AISKG unified semantic knowledge-graph framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run the complete configured pipeline")
    run.add_argument("--config", default="config.yaml")
    run.add_argument("--run-id")
    run.add_argument("--clean", action="store_true")
    run.add_argument("--quiet", action="store_true")

    stage = subparsers.add_parser("stage", help="Run one independently executable stage group")
    stage.add_argument("name", choices=["retrieval", "preprocessing", "embedding", "topic_model", "extraction", "graph", "pathway", "benchmarking", "validation", "representation", "visualization", "ablation", "full"])
    stage.add_argument("--config", default="config.yaml")
    stage.add_argument("--run-id")

    ablation = subparsers.add_parser("ablation", help="Run only the additive ablation suite")
    ablation.add_argument("--config", default="config.yaml")
    ablation.add_argument("--run-id", default="ablation")

    verify = subparsers.add_parser("verify", help="Verify a completed output directory")
    verify.add_argument("--run-dir", required=True)

    variants = subparsers.add_parser("list-variants", help="List configured ablation variants")
    variants.add_argument("--config", default="config.yaml")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        result = run_pipeline(args.config, run_id=args.run_id, clean=True if args.clean else None, verbose=not args.quiet)
        print(json.dumps({"run_dir": str(result["run_dir"]), "release_zip": str(result["release_zip"])}, indent=2))
        return 0
    if args.command == "stage":
        result = run_stage(args.name, args.config, args.run_id)
        print(json.dumps({"run_dir": str(result["run_dir"]), "release_zip": str(result["release_zip"])}, indent=2))
        return 0
    if args.command == "ablation":
        result = run_stage("ablation", args.config, args.run_id)
        print(json.dumps({"run_dir": str(result["run_dir"]), "release_zip": str(result["release_zip"])}, indent=2))
        return 0
    if args.command == "verify":
        print(json.dumps(verify_run(args.run_dir), indent=2))
        return 0
    if args.command == "list-variants":
        config = AISKGConfig.load(args.config)
        for variant in config.variants():
            print(f"{variant['name']}: {variant['label']}")
        return 0
    raise AssertionError("unreachable")
