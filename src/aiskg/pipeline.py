"""Unified deterministic AISKG pipeline orchestration."""
from __future__ import annotations

import gc
import json
import shutil
import time
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .ablation import run_ablation
from .config import AISKGConfig, require_paths
from .context import RunContext
from .legacy import section1_engine, section2_engine
from .logging_utils import build_logger
from .reproducibility.audit import assert_audit_passed, build_reproducibility_audit
from .utils import (
    deterministic_zip,
    environment_metadata,
    extract_zip,
    find_file_root,
    set_global_seed,
    sha256_file,
    write_json,
    write_manifest,
    write_sha256s,
)


def _prepare_context(config: AISKGConfig, run_id: str, clean: bool) -> RunContext:
    context = RunContext.create(config, run_id)
    if clean:
        shutil.rmtree(context.run_dir, ignore_errors=True)
        shutil.rmtree(context.work_dir, ignore_errors=True)
    context.run_dir.mkdir(parents=True, exist_ok=True)
    context.work_dir.mkdir(parents=True, exist_ok=True)
    context.log_file.parent.mkdir(parents=True, exist_ok=True)
    return context


def _configure_legacy_engines(config: AISKGConfig) -> None:
    seed = int(config.get("project.random_seed"))
    section1_engine.RANDOM_SEED = int(config.get("topic_model.umap.random_state"))
    section2_engine.RANDOM_SEED = seed
    section2_engine.BOOTSTRAP_ITERATIONS = int(config.get("validation.bootstrap_iterations"))
    section2_engine.TEMPORAL_RAREFACTION_ITERATIONS = int(config.get("graph.temporal_rarefaction_iterations"))
    section2_engine.COMPOSITE_SENSITIVITY_ITERATIONS = int(config.get("research_representation.monte_carlo_iterations"))


def _run_section1(context: RunContext, logger: Any) -> dict[str, Any]:
    bundle = context.config.path_value("paths.section1_input_bundle")
    logger.info("Section 1: extracting %s", bundle.name)
    extracted = extract_zip(bundle, context.work_dir / "section1_input")
    input_root = extracted if (extracted / "input_checksums.csv").exists() else find_file_root(extracted, "input_checksums.csv")
    context.legacy_section1_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Section 1: executing frozen literature-to-extraction pipeline")
    return section1_engine.run_snapshot_pipeline(input_root, context.legacy_section1_dir)


def _run_section2(context: RunContext, bridge_zip: Path | None, logger: Any) -> dict[str, Any]:
    bundle = bridge_zip if bridge_zip is not None else context.config.path_value("paths.section2_input_bundle")
    logger.info("Section 2: extracting %s", bundle.name)
    extracted = extract_zip(bundle, context.work_dir / "section2_input")
    input_root = find_file_root(extracted, "input_checksums.csv")
    context.legacy_section2_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Section 2: executing frozen post-extraction pipeline")
    raw = section2_engine.run_pipeline(input_root, context.legacy_section2_dir)
    result = {
        "archive": str(raw["archive"]),
        "expected_checks": int(len(raw["expected_results"])),
        "output_dir": str(context.legacy_section2_dir),
    }
    del raw
    gc.collect()
    return result


def _finalize_release(context: RunContext, audit: pd.DataFrame, started: float, logger: Any) -> Path:
    audit_path = context.run_dir / "outputs" / "reproducibility_audit.csv"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(audit_path, index=False)

    metadata = {
        "framework": context.config.get("project.name"),
        "version": context.config.get("project.version"),
        "run_id": context.run_id,
        "mode": context.config.get("project.mode"),
        "random_seed": context.config.get("project.random_seed"),
        "config_file": str(context.config.path.relative_to(context.config.repository_root)),
        "config_sha256": sha256_file(context.config.path),
        "elapsed_seconds": round(time.time() - started, 6),
        "audit_checks": int(len(audit)),
        "audit_passed": int((audit["status"] == "PASS").sum()),
        **environment_metadata(context.config.repository_root),
    }
    write_json(metadata, context.run_dir / "RUN_METADATA.json")
    (context.run_dir / "PIPELINE_SUCCESS.txt").write_text("SUCCESS\n", encoding="utf-8")

    manifest_path = context.run_dir / "RELEASE_MANIFEST.csv"
    checksum_path = context.run_dir / "SHA256SUMS.txt"
    archive_name = str(context.config.get("release.archive_name"))
    archive_path = context.run_dir / archive_name
    excluded = {archive_name, manifest_path.name, checksum_path.name}
    logger.info("Creating deterministic release archive: %s", archive_path)
    # No log messages are emitted after the manifest is computed; otherwise the
    # log file would change after its checksum had been recorded.
    write_manifest(context.run_dir, manifest_path, exclude=excluded)
    write_sha256s(context.run_dir, checksum_path, exclude=excluded)
    deterministic_zip(context.run_dir, archive_path, exclude={archive_name})
    return archive_path


def run_pipeline(
    config_path: str | Path = "config.yaml",
    *,
    run_id: str | None = None,
    clean: bool | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """Execute the unified frozen pipeline and additive ablation study.

    Returns both ``release_zip`` and the backward-compatible
    ``release_archive`` key.  The alias fixes the earlier v3 integration-test
    mismatch without changing any scientific output.
    """
    started = time.time()
    config = AISKGConfig.load(config_path)
    selected_run_id = run_id or str(config.get("project.run_id"))
    selected_clean = bool(config.get("project.clean_run")) if clean is None else bool(clean)
    context = _prepare_context(config, selected_run_id, selected_clean)
    logger = build_logger(context.log_file, verbose=verbose)

    require_paths(config, [
        "paths.section1_input_bundle",
        "paths.section2_input_bundle",
        "paths.ablation_frozen_bundle",
        "paths.ablation_expected_results",
    ])
    set_global_seed(int(config.get("project.random_seed")))
    _configure_legacy_engines(config)
    logger.info("Starting AISKG %s run %s", config.get("project.version"), selected_run_id)

    section1_result: dict[str, Any] | None = None
    section2_result: dict[str, Any] | None = None
    ablation_result: dict[str, Any] | None = None
    bridge_zip: Path | None = None

    if config.stage_enabled("section1_snapshot"):
        section1_result = _run_section1(context, logger)
        bridge_zip = Path(section1_result["bridge_zip"])

    if config.stage_enabled("section2_snapshot"):
        section2_result = _run_section2(context, bridge_zip, logger)

    if config.stage_enabled("ablation"):
        logger.info("Ablation: rebuilding nine frozen-corpus variants and comparison outputs")
        ablation_result = run_ablation(config, context.ablation_dir, context.work_dir / "ablation")

    audit = build_reproducibility_audit(
        context.legacy_section1_dir if section1_result else None,
        context.legacy_section2_dir if section2_result else None,
        ablation_result["audit"] if ablation_result else None,
    )
    expected_total = 285 if section1_result and section2_result and ablation_result else None
    assert_audit_passed(audit, expected_total=expected_total)
    archive = _finalize_release(context, audit, started, logger)

    return {
        "run_dir": context.run_dir,
        "release_zip": archive,
        "release_archive": archive,
        "section1": section1_result,
        "section2": section2_result,
        "ablation": ablation_result,
        "audit": audit,
    }
