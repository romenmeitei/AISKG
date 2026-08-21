#!/usr/bin/env python3
"""Independent release verifier for AISKG v3.1.2."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import nbformat
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiskg.additional_analyses import run_replay
from aiskg.additional_analyses.reviewer_validation import (
    RATING_COLUMNS,
    replay_reviewer_validation,
    validate_public_workbook_container,
)

RELEASE = "3.1.2"
DATA_REL = Path("data/frozen/additional_analyses_v3.1.2")
CORRECTED_FILES = {
    "AISKG_three_system_benchmark_corrected.xlsx",
    "aiskg_entities.csv",
    "aiskg_relations.csv",
    "entity_class_coverage.csv",
    "figure_common_schema_entity_f1.png",
    "figure_entity_class_recall.png",
    "llm_entities.csv",
    "llm_relations.csv",
    "llm_validation_log.csv",
    "manuscript_ready_results.txt",
    "mcnemar_holm_tests.csv",
    "normalized_gold_entities.csv",
    "normalized_gold_relations.csv",
    "paired_bootstrap_differences.csv",
    "pubtator_entities.csv",
    "pubtator_relations.csv",
    "run_manifest.json",
    "system_metrics.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_data_checksums(data_root: Path) -> int:
    checksum_file = data_root / "SHA256SUMS.txt"
    lines = [line for line in checksum_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    declared: set[str] = set()
    for line in lines:
        expected, relative = line.split("  ", 1)
        declared.add(relative)
        path = data_root / relative
        if not path.is_file():
            raise AssertionError(f"Missing frozen additional-analysis file: {relative}")
        if sha256(path) != expected:
            raise AssertionError(f"SHA-256 mismatch for {relative}")
    actual = {
        path.relative_to(data_root).as_posix()
        for path in data_root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    }
    if declared != actual:
        raise AssertionError(f"Frozen-data manifest coverage mismatch: {sorted(declared ^ actual)}")
    return len(lines)


def verify_reviewer_workbooks(data_root: Path, provenance: dict) -> dict[str, object]:
    workbook_root = data_root / "pathway/reviewer_workbooks"
    mapping = {
        "expert_A_public": workbook_root / "Expert_A_completed_public.xlsx",
        "expert_B_public": workbook_root / "Expert_B_completed_public.xlsx",
        "third_expert_public": workbook_root / "Third_Expert_completed_public.xlsx",
    }
    for key, path in mapping.items():
        expected = provenance["reviewer_workbooks"][key]["sha256"]
        if sha256(path) != expected:
            raise AssertionError(f"Public reviewer workbook hash mismatch: {path.name}")
        validate_public_workbook_container(path)
    replay = replay_reviewer_validation(mapping["expert_A_public"], mapping["expert_B_public"], mapping["third_expert_public"])
    expected_agreement = pd.read_csv(data_root / "pathway/pathway_interrater_agreement_expected.csv")
    pd.testing.assert_frame_equal(replay.agreement, expected_agreement, check_exact=False, rtol=0, atol=1e-12)
    expected_qc = json.loads((data_root / "pathway/pathway_expected_reviewer_qc.json").read_text(encoding="utf-8"))
    observed_qc = {key: replay.qc[key] for key in expected_qc}
    if observed_qc != expected_qc:
        raise AssertionError("Reviewer QC mismatch.")
    frozen = pd.read_csv(data_root / "pathway/pathway_validation_final_labels_public.csv", dtype={"validation_id": str})
    reconstructed = replay.reconstructed_ratings.set_index("validation_id")
    for dimension in RATING_COLUMNS:
        for suffix in ["", "_source", "_binary"]:
            column = dimension + suffix
            observed = frozen["validation_id"].map(reconstructed[column])
            if suffix == "_binary":
                if not observed.astype(int).equals(frozen[column].astype(int)):
                    raise AssertionError(f"Reconstructed binary labels differ in {column}.")
            elif not observed.astype(str).equals(frozen[column].astype(str)):
                raise AssertionError(f"Reconstructed labels differ in {column}.")
    exceptions = replay.qc["complete_pathway_rollup_inconsistencies"]
    expected_exceptions = ["XPV-0052", "XPV-0074"]
    if [row["validation_id"] for row in exceptions["Expert A"]] != expected_exceptions or exceptions["Expert B"]:
        raise AssertionError("Source roll-up exception disclosure mismatch.")
    return {
        "reviewer_pairs": replay.qc["total_A_B_rating_pairs"],
        "direct_disagreements": replay.qc["direct_A_B_disagreements"],
        "adjudications": replay.qc["required_third_expert_adjudications"],
        "agreement_dimensions": len(replay.agreement),
        "final_labels_reconstructed": len(replay.rating_matrix_long),
    }


def verify_corrected_archive(repository: Path, data_root: Path, provenance: dict) -> None:
    archive = repository / "reference_outputs/additional_analyses_v3.1.2/AISKG_three_system_benchmark_corrected_outputs.zip"
    expected_archive_sha = provenance["corrected_benchmark_analysis"]["source_output_archive_sha256"]
    if sha256(archive) != expected_archive_sha:
        raise AssertionError("Corrected source output archive hash does not match provenance.")
    with zipfile.ZipFile(archive) as handle:
        names = {Path(name).name for name in handle.namelist() if not name.endswith("/")}
        if names != CORRECTED_FILES:
            raise AssertionError(f"Corrected archive file set mismatch: {sorted(names ^ CORRECTED_FILES)}")
        for filename in CORRECTED_FILES:
            if hashlib.sha256(handle.read(filename)).digest() != hashlib.sha256(
                (data_root / "benchmark" / filename).read_bytes()
            ).digest():
                raise AssertionError(f"Public corrected benchmark file differs from source archive: {filename}")


def verify_executed_notebook(repository: Path, provenance: dict) -> dict[str, int]:
    path = repository / "notebooks/additional_analyses/AISKG_PubTator3_Structured_LLM_Benchmark_Corrected_Executed_Reference.ipynb"
    if sha256(path) != provenance["corrected_benchmark_analysis"]["source_notebook_sha256"]:
        raise AssertionError("Corrected executed notebook hash mismatch.")
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if len(code_cells) != 13 or sum(cell.execution_count is not None for cell in code_cells) != 13:
        raise AssertionError("Corrected executed notebook is not fully executed (expected 13/13 code cells).")
    for cell in code_cells:
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                raise AssertionError("Corrected executed notebook contains an error output.")
    return {"code_cells": 13, "executed_code_cells": 13}


def verify_master_notebook(repository: Path) -> dict[str, int]:
    path = repository / "notebooks/AISKG_Framework_v3_1_2_Complete_Reproducibility.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    text = "\n".join(cell.source for cell in notebook.cells)
    for required in ["3.1.2", "805", "92", "interrater_agreement_recomputed.csv", "Third_Expert_completed_public.xlsx"]:
        if required not in text:
            raise AssertionError(f"Master notebook is missing required reviewer-level marker: {required}")
    if len(notebook.cells) != 11 or len(code_cells) != 7:
        raise AssertionError("Unexpected master notebook structure.")
    for cell in code_cells:
        if cell.get("outputs"):
            raise AssertionError("Distributed master notebook must not contain stale outputs.")
    return {"cells": 11, "code_cells": 7}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(ROOT))
    args = parser.parse_args()
    repository = Path(args.repo_root).resolve()
    data_root = repository / DATA_REL
    if (repository / "VERSION").read_text(encoding="utf-8").strip() != RELEASE:
        raise AssertionError("VERSION does not identify v3.1.2.")
    if not data_root.is_dir():
        raise AssertionError(f"Missing data directory: {data_root}")
    provenance = json.loads((data_root / "source_upload_sha256.json").read_text(encoding="utf-8"))
    if provenance.get("release_version") != RELEASE:
        raise AssertionError("Source provenance release version mismatch.")
    checksum_entries = verify_data_checksums(data_root)
    reviewer_status = verify_reviewer_workbooks(data_root, provenance)
    verify_corrected_archive(repository, data_root, provenance)
    corrected_notebook = verify_executed_notebook(repository, provenance)
    master_notebook = verify_master_notebook(repository)

    forbidden_names = {
        "benchmark_historical_failed_run_metrics_DO_NOT_REPORT.csv",
        "benchmark_historical_failed_run_paired_tests_DO_NOT_REPORT.csv",
        "benchmark_historical_failed_run_mcnemar_DO_NOT_REPORT.csv",
        "benchmark_failed_llm_validation_log.csv",
        "Expert_A_completed.xlsx",
        "Expert_B_completed.xlsx",
        "Third_Expert_completed.xlsx",
    }
    leaked = sorted(forbidden_names & {path.name for path in repository.rglob("*") if path.is_file()})
    if leaked:
        raise AssertionError(f"Private or superseded files leaked into the public release: {leaked}")

    with tempfile.TemporaryDirectory(prefix="aiskg-v3.1.2-verify-") as temporary:
        result = run_replay(data_root, Path(temporary) / "outputs")
        metrics = pd.read_csv(result.benchmark_metrics)
        pathway = pd.read_csv(result.pathway_summary)
        entity = metrics[(metrics.task == "entity") & (metrics.schema == "COMMON_146") & (metrics.criterion == "strict")].set_index("system")
        relation = metrics[(metrics.task == "relation") & (metrics.criterion == "directed_strict")].set_index("system")
        expected_entity = {"AISKG": 0.9038031319910514, "PubTator3": 0.5007235890014472, "StructuredLLM": 0.5026178010471204}
        for system, expected in expected_entity.items():
            if not math.isclose(float(entity.loc[system, "f1"]), expected, rel_tol=0, abs_tol=1e-12):
                raise AssertionError(f"Corrected entity F1 mismatch for {system}.")
        if tuple(relation.loc["AISKG", ["tp", "fp", "fn"]].astype(int)) != (27, 0, 29):
            raise AssertionError("AISKG relation counts mismatch.")
        if "PubTator3" in relation.index:
            raise AssertionError("PubTator relation performance was improperly scored.")
        primary = pathway[pathway.endpoint.eq("complete_pathway_correct")].set_index("system")
        if tuple(primary.loc["PRE_REFINEMENT", ["correct", "n"]].astype(int)) != (23, 95):
            raise AssertionError("Pre-refinement pathway result mismatch.")
        if tuple(primary.loc["OUTCOME_AWARE_REFINED", ["correct", "n"]].astype(int)) != (26, 52):
            raise AssertionError("Refined pathway result mismatch.")
        qc = json.loads((result.output_root / "pathway_validation/REVIEWER_WORKBOOK_QC.json").read_text())
        if qc["total_A_B_rating_pairs"] != 805 or qc["required_third_expert_adjudications"] != 92:
            raise AssertionError("Replay reviewer counts mismatch.")
        manifest = json.loads(result.manifest.read_text())
        if manifest["benchmark"]["llm_model_revision_is_immutable_commit"]:
            raise AssertionError("Mutable model revision limitation was not preserved.")
        if not result.success_marker.exists() or not result.output_archive.exists():
            raise AssertionError("Replay did not create required release artifacts.")

    print(json.dumps({
        "release": RELEASE,
        "status": "PASS",
        "data_checksum_entries": checksum_entries,
        "reviewer_validation": reviewer_status,
        "corrected_notebook": corrected_notebook,
        "master_notebook": master_notebook,
        "pathway_primary_endpoint": {"pre": "23/95", "refined": "26/52"},
        "corrected_entity_f1": expected_entity,
        "corrected_aiskg_relation": {"tp": 27, "fp": 0, "fn": 29, "f1": 0.6506024096385542},
        "pubtator_relation_status": "NOT_EVALUABLE_NO_RELATION_OBJECTS",
        "llm_live_weight_replay": "NOT_BITWISE_GUARANTEED_SOURCE_REVISION_MAIN",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
