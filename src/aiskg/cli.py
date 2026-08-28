"""Command-line interface for AISKG."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import AISKGConfig
from .pipeline import run_pipeline
from .reproducibility import verify_run
from .additional_analyses import run_replay
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

    additional = subparsers.add_parser(
        "additional-analyses",
        help="Replay the corrected v3.1.2 pathway validation and three-system benchmark",
    )
    additional.add_argument("--data-root", default="data/frozen/additional_analyses_v3.1.2")
    additional.add_argument("--output-root", default="outputs/additional-analyses-v3.1.2")

    external = subparsers.add_parser(
        "external-re-benchmark",
        help="Run the BioRED/BioREDirect external relation benchmark",
    )
    external.add_argument("--work-dir", default=".aiskg_work/external-re")
    external.add_argument("--output-dir", default="outputs/external-re-benchmark-v1.0.0")
    external.add_argument("--public-output-dir", default="outputs/external-re-benchmark-public-v1.0.0")
    external.add_argument("--config", default="configs/external_re/benchmark_config.json")
    external.add_argument("--rules", default="ontology/external_re/biored_trigger_rules.json")
    external.add_argument("--run-bioredirect", action="store_true")
    external.add_argument("--skip-bioredirect", action="store_true")
    external.add_argument("--no-download", action="store_true")
    external.add_argument("--force-download", action="store_true")
    external.add_argument("--train-pubtator")
    external.add_argument("--dev-pubtator")
    external.add_argument("--test-pubtator")
    external.add_argument("--bioredirect-predictions")
    external.add_argument("--split-scheme", choices=["bioredirect_bc8_official", "biored_classic"], default="bioredirect_bc8_official")
    external.add_argument("--bioredirect-revision", default="main")
    external.add_argument("--batch-size", type=int, default=8)
    external.add_argument("--cuda-device", default="0")
    external.add_argument("--bootstrap-iterations", type=int, default=5000)
    external.add_argument("--seed", type=int, default=20260826)
    external.add_argument("--modes", nargs="+", choices=["sentence_local", "full_document"], default=["sentence_local", "full_document"])
    external.add_argument("--clean", action="store_true")

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
    if args.command == "additional-analyses":
        result = run_replay(
            args.data_root,
            args.output_root,
        )
        print(
            json.dumps(
                {
                    "output_root": str(result.output_root),
                    "output_archive": str(result.output_archive),
                    "manifest": str(result.manifest),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "external-re-benchmark":
        from aiskg_external_re.cli import run_benchmark
        from aiskg_external_re.public_export import export_public_results
        import argparse as _argparse
        external_args = _argparse.Namespace(
            package_root=str(Path.cwd()), config=args.config, rules=args.rules,
            work_dir=args.work_dir, output_dir=args.output_dir,
            public_output_dir=args.public_output_dir,
            train_pubtator=args.train_pubtator, dev_pubtator=args.dev_pubtator,
            test_pubtator=args.test_pubtator, bioredirect_predictions=args.bioredirect_predictions,
            run_bioredirect=args.run_bioredirect, skip_bioredirect=args.skip_bioredirect,
            no_download=args.no_download, force_download=args.force_download,
            split_scheme=args.split_scheme, bioredirect_revision=args.bioredirect_revision,
            batch_size=args.batch_size, cuda_device=args.cuda_device,
            bootstrap_iterations=args.bootstrap_iterations, seed=args.seed,
            modes=args.modes, clean=args.clean,
        )
        archive = run_benchmark(external_args)
        public_archive = export_public_results(args.output_dir, args.public_output_dir, framework_version="3.2.0")
        print(json.dumps({"full_result_archive": str(archive), "public_result_archive": str(public_archive)}, indent=2))
        return 0
    if args.command == "list-variants":
        config = AISKGConfig.load(args.config)
        for variant in config.variants():
            print(f"{variant['name']}: {variant['label']}")
        return 0
    raise AssertionError("unreachable")
