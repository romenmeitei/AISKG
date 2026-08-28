from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Sequence

import pandas as pd

from .adapter import ConstrainedTextClassifier, RuleTransferAdapter, TypePairMajority, save_thresholds
from .bioredirect import (
    prepare_official_assets,
    prepare_python311_environment,
    run_official_bioredirect_prediction,
    sha256_file,
)
from .candidates import build_candidate_examples
from .evaluation import (
    gold_from_examples,
    metrics_with_ci,
    predictions_from_documents,
)
from .io_pubtator import parse_pubtator, predictions_to_csv, write_predictions_pubtator
from .models import CandidateExample, Prediction
from .reporting import (
    deterministic_zip,
    environment_manifest,
    plot_per_relation_recall,
    plot_system_f1,
    write_json,
    write_methods_snippet,
    write_results_template,
    write_sha256s,
    write_table,
)


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _candidate_summary(split: str, mode: str, examples: Sequence[CandidateExample]) -> dict[str, object]:
    relation_counts = Counter(example.label for example in examples)
    direction_counts = Counter(example.direction for example in examples if example.label != "None")
    return {
        "split": split,
        "mode": mode,
        "candidates": len(examples),
        "positive_relations": sum(value for key, value in relation_counts.items() if key != "None"),
        "negative_candidates": relation_counts.get("None", 0),
        "same_sentence_candidates": sum(example.same_sentence for example in examples),
        "relation_distribution": dict(sorted(relation_counts.items())),
        "direction_distribution_among_positive": dict(sorted(direction_counts.items())),
        "documents": len({example.doc_id for example in examples}),
    }


def _write_test_candidates(examples: Sequence[CandidateExample], path: Path) -> None:
    rows = [
        {
            "doc_id": e.doc_id,
            "id1": e.id1,
            "id2": e.id2,
            "type1": e.type1,
            "type2": e.type2,
            "same_sentence": int(e.same_sentence),
            "char_distance": e.char_distance,
            "gold_relation": e.label,
            "gold_direction": e.direction,
            "gold_subject": e.subject or "",
            "context": e.context,
        }
        for e in examples
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def _validate_splits(train_docs, dev_docs, test_docs) -> dict[str, object]:
    train_ids = {doc.doc_id for doc in train_docs}
    dev_ids = {doc.doc_id for doc in dev_docs}
    test_ids = {doc.doc_id for doc in test_docs}
    overlaps = {
        "train_dev": sorted(train_ids & dev_ids),
        "train_test": sorted(train_ids & test_ids),
        "dev_test": sorted(dev_ids & test_ids),
    }
    if any(overlaps.values()):
        raise ValueError(f"Document leakage across BioRED splits: {overlaps}")
    return {
        "train_documents": len(train_ids),
        "dev_documents": len(dev_ids),
        "test_documents": len(test_ids),
        "document_overlap": {key: len(value) for key, value in overlaps.items()},
    }


def run_benchmark(args: argparse.Namespace) -> Path:
    package_root = Path(args.package_root).resolve()
    config = _load_json(args.config or package_root / "configs" / "external_re" / "benchmark_config.json")
    work_dir = Path(args.work_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    if args.clean and output_dir.exists():
        shutil.rmtree(output_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    seed = int(args.seed if args.seed is not None else config["global_seed"])
    bootstrap_iterations = int(
        args.bootstrap_iterations
        if args.bootstrap_iterations is not None
        else config["bootstrap_iterations"]
    )
    modes = args.modes or list(config["modes"])
    split_scheme = args.split_scheme or config.get("split_scheme", "bioredirect_bc8_official")
    invalid_modes = set(modes) - {"sentence_local", "full_document"}
    if invalid_modes:
        raise ValueError(f"Invalid modes: {sorted(invalid_modes)}")

    official_assets: dict[str, str] = {}
    train_path = Path(args.train_pubtator).resolve() if args.train_pubtator else None
    dev_path = Path(args.dev_pubtator).resolve() if args.dev_pubtator else None
    test_path = Path(args.test_pubtator).resolve() if args.test_pubtator else None

    if not (train_path and dev_path and test_path):
        if args.no_download:
            raise ValueError("Explicit train/dev/test files are required with --no-download")
        official_assets = prepare_official_assets(
            work_dir / "official",
            revision=args.bioredirect_revision or config.get("bioredirect_revision", "main"),
            force_download=args.force_download,
        )
        if split_scheme == "bioredirect_bc8_official":
            train_path = Path(official_assets["official_train_dev_pubtator"])
            dev_path = Path(official_assets["official_development_pubtator"])
            test_path = Path(official_assets["official_bc8_test_pubtator"])
        elif split_scheme == "biored_classic":
            train_path = Path(official_assets["classic_train_pubtator"])
            dev_path = Path(official_assets["classic_dev_pubtator"])
            test_path = Path(official_assets["classic_test_pubtator"])
        else:
            raise ValueError(f"Unknown split scheme: {split_scheme}")

    assert train_path and dev_path and test_path
    input_hashes = {
        "train_pubtator": {"path": str(train_path), "sha256": sha256_file(train_path)},
        "dev_pubtator": {"path": str(dev_path), "sha256": sha256_file(dev_path)},
        "test_pubtator": {"path": str(test_path), "sha256": sha256_file(test_path)},
    }

    print("Parsing BioRED/BioREDirect splits...", flush=True)
    train_docs = parse_pubtator(train_path, strict=True)
    dev_docs = parse_pubtator(dev_path, strict=True)
    test_docs = parse_pubtator(test_path, strict=True)
    split_qc = _validate_splits(train_docs, dev_docs, test_docs)

    run_bioredirect = bool(args.run_bioredirect)
    if args.skip_bioredirect:
        run_bioredirect = False
    if not args.run_bioredirect and not args.skip_bioredirect:
        run_bioredirect = bool(config.get("run_bioredirect", True))

    bioredirect_prediction_path: Path | None = (
        Path(args.bioredirect_predictions).resolve() if args.bioredirect_predictions else None
    )
    bioredirect_status: dict[str, object] = {
        "requested": run_bioredirect,
        "completed": False,
        "prediction_path": str(bioredirect_prediction_path) if bioredirect_prediction_path else None,
    }

    if run_bioredirect and bioredirect_prediction_path is None:
        if not official_assets:
            # The user provided data files but still requested the official comparator.
            official_assets = prepare_official_assets(
                work_dir / "official",
                revision=args.bioredirect_revision or config.get("bioredirect_revision", "main"),
                force_download=args.force_download,
            )
        repository_dir = Path(official_assets["bioredirect_repository"])
        # prepare_official_assets records the URL under this key; repository path is fixed.
        repository_dir = work_dir / "official" / "BioREDirect"
        model_dir = Path(official_assets["model_directory"])
        python_bin = prepare_python311_environment(
            work_dir / "official" / "bioredirect_py311",
            repository_dir,
        )
        bioredirect_prediction_path = run_official_bioredirect_prediction(
            repository_dir=repository_dir,
            python_bin=python_bin,
            model_dir=model_dir,
            test_pubtator=test_path,
            output_dir=work_dir / "official" / "prediction",
            batch_size=int(args.batch_size or config.get("bioredirect_batch_size", 8)),
            cuda_device=str(args.cuda_device or config.get("cuda_device", "0")),
        )
        bioredirect_status.update(
            {
                "completed": True,
                "prediction_path": str(bioredirect_prediction_path),
                "prediction_sha256": sha256_file(bioredirect_prediction_path),
            }
        )
    elif run_bioredirect and bioredirect_prediction_path is not None:
        if not bioredirect_prediction_path.exists():
            raise FileNotFoundError(bioredirect_prediction_path)
        bioredirect_status.update(
            {
                "completed": True,
                "prediction_sha256": sha256_file(bioredirect_prediction_path),
            }
        )

    bioredirect_docs = (
        parse_pubtator(bioredirect_prediction_path, strict=True)
        if bioredirect_prediction_path is not None
        else []
    )

    rules_path = Path(args.rules or package_root / "ontology" / "external_re" / "biored_trigger_rules.json")
    all_metrics: list[pd.DataFrame] = []
    all_per_label: list[pd.DataFrame] = []
    all_comparisons: list[pd.DataFrame] = []
    all_errors: list[pd.DataFrame] = []
    candidate_summaries: list[dict[str, object]] = []
    thresholds: dict[str, object] = {
        "seed": seed,
        "test_tuning_performed": False,
        "threshold_selection_split": "development",
        "modes": {},
    }

    for mode_index, mode in enumerate(modes):
        print(f"\n=== External benchmark mode: {mode} ===", flush=True)
        train_examples = build_candidate_examples(
            train_docs,
            mode=mode,
            max_context_chars=int(config.get("max_context_chars", 1800)),
        )
        dev_examples = build_candidate_examples(
            dev_docs,
            mode=mode,
            max_context_chars=int(config.get("max_context_chars", 1800)),
        )
        test_examples = build_candidate_examples(
            test_docs,
            mode=mode,
            max_context_chars=int(config.get("max_context_chars", 1800)),
        )
        if not train_examples or not dev_examples or not test_examples:
            raise RuntimeError(f"Empty candidate split in {mode}")
        if not any(example.label != "None" for example in train_examples):
            raise RuntimeError(f"No positive training relations in {mode}")
        if not any(example.label != "None" for example in test_examples):
            raise RuntimeError(f"No positive test relations in {mode}")

        for split, examples in [
            ("train", train_examples),
            ("development", dev_examples),
            ("test", test_examples),
        ]:
            candidate_summaries.append(_candidate_summary(split, mode, examples))
        _write_test_candidates(test_examples, output_dir / f"test_candidates_{mode}.csv")

        gold = gold_from_examples(test_examples, mode=mode)
        predictions: dict[str, Sequence[Prediction]] = {}
        mode_thresholds: dict[str, float] = {}

        if config.get("run_type_pair_majority", True):
            model = TypePairMajority().fit(train_examples)
            mode_thresholds["TypePairMajority"] = model.tune(dev_examples)
            predictions["TypePairMajority"] = model.predict(
                test_examples,
                system="TypePairMajority",
                mode=mode,
            )

        if config.get("run_rule_transfer", True):
            rule_model = RuleTransferAdapter.from_json(rules_path).fit(train_examples)
            mode_thresholds["AISKGRuleTransfer"] = rule_model.tune(dev_examples)
            predictions["AISKGRuleTransfer"] = rule_model.predict(
                test_examples,
                system="AISKGRuleTransfer",
                mode=mode,
            )

        if config.get("run_constrained_text_transfer", True):
            text_model = ConstrainedTextClassifier(seed=seed + mode_index).fit(train_examples)
            mode_thresholds["AISKGConstrainedTransfer"] = text_model.tune(dev_examples)
            predictions["AISKGConstrainedTransfer"] = text_model.predict(
                test_examples,
                system="AISKGConstrainedTransfer",
                mode=mode,
            )

        if bioredirect_docs:
            predictions["BioREDirect"] = predictions_from_documents(
                bioredirect_docs,
                test_examples,
                system="BioREDirect",
                mode=mode,
            )

        if len(predictions) < 2:
            raise RuntimeError("At least two evaluable systems are required")

        thresholds["modes"][mode] = mode_thresholds
        for system, system_predictions in predictions.items():
            predictions_to_csv(
                system_predictions,
                output_dir / f"predictions_{mode}_{system}.csv",
            )
            if system != "BioREDirect":
                write_predictions_pubtator(
                    test_path,
                    system_predictions,
                    output_dir / f"predictions_{mode}_{system}.pubtator",
                )

        metrics, per_label, comparisons, errors = metrics_with_ci(
            gold,
            dict(predictions),
            mode=mode,
            iterations=bootstrap_iterations,
            seed=seed + 5000 * mode_index,
        )
        all_metrics.append(metrics)
        all_per_label.append(per_label)
        all_comparisons.append(comparisons)
        all_errors.append(errors)

    metrics_df = pd.concat(all_metrics, ignore_index=True)
    per_label_df = pd.concat(all_per_label, ignore_index=True)
    comparisons_df = pd.concat(all_comparisons, ignore_index=True)
    errors_df = pd.concat(all_errors, ignore_index=True)
    candidate_df = pd.json_normalize(candidate_summaries)

    write_table(output_dir / "system_metrics.csv", metrics_df)
    write_table(output_dir / "per_relation_metrics.csv", per_label_df)
    write_table(output_dir / "paired_comparisons.csv", comparisons_df)
    write_table(output_dir / "error_analysis.csv", errors_df)
    write_table(output_dir / "candidate_split_audit.csv", candidate_df)
    save_thresholds(output_dir / "locked_development_thresholds.json", thresholds)

    plot_system_f1(metrics_df, output_dir / "figure_external_relation_f1.png")
    plot_per_relation_recall(
        per_label_df,
        output_dir / "figure_per_relation_recall_full_document.png",
        mode="full_document",
    )

    quality_gates = {
        "status": "PASS",
        "no_document_overlap": all(value == 0 for value in split_qc["document_overlap"].values()),
        "train_development_test_fixed": True,
        "threshold_tuned_on_development_only": True,
        "test_tuning_performed": False,
        "gold_entities_used_for_all_external_systems": True,
        "sentence_local_and_full_document_separated": set(modes) == {"sentence_local", "full_document"},
        "bioredirect_requested": run_bioredirect,
        "bioredirect_completed": bool(bioredirect_docs),
        "test_gold_relation_n_by_mode": {
            mode: int(
                metrics_df[
                    (metrics_df["mode"] == mode)
                    & (metrics_df["evaluation"] == "relation_type")
                ]["gold_n"].iloc[0]
            )
            for mode in modes
        },
    }
    if run_bioredirect and not bioredirect_docs:
        quality_gates["status"] = "PARTIAL"
        quality_gates["warning"] = "BioREDirect was requested but did not complete; do not report a BioREDirect comparison."
    write_json(output_dir / "QUALITY_GATES.json", quality_gates)

    manifest: dict[str, object] = {
        "analysis_name": "AISKG external BioRED/BioREDirect relation-extraction benchmark",
        "package_version": config.get("package_version", "1.0.0"),
        "seed": seed,
        "bootstrap_iterations": bootstrap_iterations,
        "modes": modes,
        "split_scheme": split_scheme,
        "input_hashes": input_hashes,
        "split_qc": split_qc,
        "official_assets": official_assets,
        "bioredirect_status": bioredirect_status,
        "rules_file": {"path": str(rules_path), "sha256": sha256_file(rules_path)},
        "reporting_boundaries": config.get("reporting_boundaries", {}),
        "environment": environment_manifest(),
        "quality_gates": quality_gates,
    }
    write_json(output_dir / "run_manifest.json", manifest)
    write_methods_snippet(output_dir / "COPY_READY_METHODS.md", manifest=manifest)
    write_results_template(
        output_dir / "COPY_READY_RESULTS_DRAFT.md",
        metrics_df,
        comparisons_df,
    )
    (output_dir / "SUCCESS.txt").write_text(
        "AISKG external relation-extraction benchmark completed.\n"
        f"Quality-gate status: {quality_gates['status']}\n"
        "Read QUALITY_GATES.json and the reporting boundaries before manuscript use.\n",
        encoding="utf-8",
    )
    write_sha256s(output_dir)
    zip_path = output_dir.parent / f"{output_dir.name}.zip"
    deterministic_zip(output_dir, zip_path)
    print(f"\nResults archive: {zip_path}", flush=True)
    return zip_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the AISKG external BioRED/BioREDirect relation-extraction benchmark."
    )
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--config")
    parser.add_argument("--rules")
    parser.add_argument("--train-pubtator")
    parser.add_argument("--dev-pubtator")
    parser.add_argument("--test-pubtator")
    parser.add_argument("--bioredirect-predictions")
    parser.add_argument("--run-bioredirect", action="store_true")
    parser.add_argument("--skip-bioredirect", action="store_true")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument(
        "--split-scheme",
        choices=["bioredirect_bc8_official", "biored_classic"],
        help="Default: official BioREDirect train+dev / original test-as-dev / BC8 held-out test.",
    )
    parser.add_argument("--bioredirect-revision")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--cuda-device")
    parser.add_argument("--bootstrap-iterations", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["sentence_local", "full_document"],
    )
    parser.add_argument("--public-output-dir", help="Write a public-safe result subset with no third-party text or gold annotations.")
    parser.add_argument("--clean", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        full_zip = run_benchmark(args)
        if args.public_output_dir:
            from .public_export import export_public_results
            public_zip = export_public_results(
                Path(args.output_dir), Path(args.public_output_dir), framework_version="3.2.0"
            )
            print(f"Public-safe result archive: {public_zip}")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
