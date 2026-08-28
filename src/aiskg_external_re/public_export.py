from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Sequence

PUBLIC_FIXED_FILES = {
    "system_metrics.csv",
    "per_relation_metrics.csv",
    "paired_comparisons.csv",
    "candidate_split_audit.csv",
    "locked_development_thresholds.json",
    "QUALITY_GATES.json",
    "figure_external_relation_f1.png",
    "figure_per_relation_recall_full_document.png",
    "COPY_READY_METHODS.md",
    "COPY_READY_RESULTS_DRAFT.md",
    "SUCCESS.txt",
}
FORBIDDEN_PATTERNS = ("test_candidates_", ".pubtator")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sanitized_manifest(source: dict, source_dir: Path, framework_version: str) -> dict:
    assets = source.get("official_assets", {})
    inputs = source.get("input_hashes", {})
    environment = source.get("environment", {})
    bioredirect = source.get("bioredirect_status", {})
    rules = source.get("rules_file", {})
    return {
        "analysis_name": source.get("analysis_name"),
        "framework_version": framework_version,
        "external_benchmark_package_version": source.get("package_version", "1.0.0"),
        "seed": source.get("seed"),
        "bootstrap_iterations": source.get("bootstrap_iterations"),
        "modes": source.get("modes"),
        "split_scheme": source.get("split_scheme"),
        "input_hashes": {
            key: {
                "logical_name": Path(str(value.get("path", key))).name,
                "sha256": value.get("sha256"),
            }
            for key, value in inputs.items()
        },
        "split_qc": source.get("split_qc"),
        "official_assets": {
            "bioredirect_repository": assets.get("bioredirect_repository"),
            "bioredirect_commit": assets.get("bioredirect_commit"),
            "bioredirect_revision_requested": assets.get("bioredirect_revision_requested"),
            "dataset_url": assets.get("dataset_url"),
            "dataset_sha256": assets.get("dataset_sha256"),
            "model_url": assets.get("model_url"),
            "model_sha256": assets.get("model_sha256"),
        },
        "bioredirect_status": {
            "requested": bioredirect.get("requested"),
            "completed": bioredirect.get("completed"),
            "prediction_filename": Path(str(bioredirect.get("prediction_path", ""))).name or None,
            "prediction_sha256": bioredirect.get("prediction_sha256"),
        },
        "rules_file": {
            "filename": Path(str(rules.get("path", "biored_trigger_rules.json"))).name,
            "sha256": rules.get("sha256"),
        },
        "reporting_boundaries": source.get("reporting_boundaries"),
        "environment": {
            key: environment.get(key)
            for key in ["python", "platform", "machine", "processor", "packages", "torch"]
            if key in environment
        },
        "quality_gates": source.get("quality_gates"),
        "public_release": {
            "third_party_text_redistributed": False,
            "gold_annotation_rows_redistributed": False,
            "prediction_rows_redistributed": True,
            "excluded_patterns": list(FORBIDDEN_PATTERNS),
            "source_full_result_zip_sha256": _sha256(source_dir.with_suffix(".zip"))
            if source_dir.with_suffix(".zip").is_file()
            else None,
        },
    }


def _deterministic_zip(source_dir: Path, output_zip: Path) -> None:
    fixed = (2026, 8, 28, 0, 0, 0)
    output_zip.unlink(missing_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source_dir).as_posix()
            info = zipfile.ZipInfo(relative, fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def export_public_results(
    source_dir: str | Path,
    public_dir: str | Path,
    *,
    framework_version: str = "3.2.0",
) -> Path:
    source = Path(source_dir).resolve()
    destination = Path(public_dir).resolve()
    if not (source / "QUALITY_GATES.json").is_file():
        raise FileNotFoundError(source / "QUALITY_GATES.json")
    quality = json.loads((source / "QUALITY_GATES.json").read_text(encoding="utf-8"))
    if quality.get("status") != "PASS":
        raise ValueError("Only a PASS external benchmark run can be exported publicly.")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    selected = set(PUBLIC_FIXED_FILES)
    selected.update(path.name for path in source.glob("predictions_*.csv"))
    missing = sorted(name for name in PUBLIC_FIXED_FILES if not (source / name).is_file())
    if missing:
        raise FileNotFoundError(f"Missing public result file(s): {missing}")
    for name in sorted(selected):
        candidate = source / name
        if candidate.is_file():
            shutil.copy2(candidate, destination / name)

    full_manifest = json.loads((source / "run_manifest.json").read_text(encoding="utf-8"))
    _write_json(destination / "run_manifest_public.json", _sanitized_manifest(full_manifest, source, framework_version))
    (destination / "PUBLIC_RELEASE_README.md").write_text(
        "# AISKG external benchmark public result subset\n\n"
        "This directory contains metrics, aggregate audits, figures, locked thresholds, and system prediction rows from the BioRED/BioREDirect external relation benchmark.\n\n"
        "It intentionally excludes BioRED/BioREDirect text, gold candidate rows, official model weights, NCBI source code, `test_candidates_*.csv`, `error_analysis.csv`, and PubTator files. The repository notebook retrieves official third-party assets at runtime and verifies their hashes.\n\n"
        "All systems used gold entity mentions and normalized identifiers. The external endpoint is relation classification, not end-to-end NER plus RE. `AISKGRuleTransfer` and `AISKGConstrainedTransfer` are transfer adapters rather than the unchanged mushroom-domain extractor. Sentence-local evaluation is primary; full-document evaluation is a cross-sentence stress test. The BC8 test set is locked against further tuning.\n",
        encoding="utf-8",
    )
    (destination / "THIRD_PARTY_DATA_NOTICE.md").write_text(
        "# Third-party data notice\n\n"
        "BioRED/BioREDirect corpora, gold annotations, official source code, and model weights are not redistributed here. They remain governed by their source licences and terms. The live notebook downloads them from official NCBI locations and records the resolved source commit and SHA-256 hashes.\n",
        encoding="utf-8",
    )

    checksum_lines=[]
    for path in sorted(destination.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            checksum_lines.append(f"{_sha256(path)}  {path.relative_to(destination).as_posix()}")
    (destination / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    output_zip = destination.parent / f"{destination.name}.zip"
    _deterministic_zip(destination, output_zip)
    return output_zip


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a public-safe AISKG external benchmark result subset.")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--public-dir", required=True)
    parser.add_argument("--framework-version", default="3.2.0")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    archive = export_public_results(
        args.source_dir,
        args.public_dir,
        framework_version=args.framework_version,
    )
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
