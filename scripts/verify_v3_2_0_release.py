#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import py_compile
import re
import sys
import zipfile
from pathlib import Path

import nbformat
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "3.2.0"
DATA = ROOT / "data" / "frozen" / "external_re_benchmark_v1.0.0"
ARCHIVE = ROOT / "reference_outputs" / "external_re_benchmark_v1.0.0" / "AISKG_External_RE_Benchmark_Public_Results_v1_0_0.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums() -> int:
    declared = {}
    for line in (DATA / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        declared[rel] = digest
        path = DATA / rel
        if not path.is_file() or sha256(path) != digest:
            raise AssertionError(f"Frozen external result checksum failure: {rel}")
    actual = {p.relative_to(DATA).as_posix() for p in DATA.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"}
    if set(declared) != actual:
        raise AssertionError(f"Frozen result manifest coverage mismatch: {sorted(set(declared) ^ actual)}")
    return len(declared)


def main() -> int:
    if (ROOT / "VERSION").read_text().strip() != RELEASE:
        raise AssertionError("VERSION is not 3.2.0")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'version = "3.2.0"' not in pyproject or "aiskg-external-re" not in pyproject:
        raise AssertionError("pyproject v3.2.0 external entry points are missing")
    if not DATA.is_dir() or not ARCHIVE.is_file():
        raise AssertionError("External benchmark public reference output is missing")
    entries = verify_checksums()

    forbidden = []
    for path in DATA.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("test_candidates_") or path.suffix == ".pubtator" or path.name == "error_analysis.csv":
            forbidden.append(path.name)
    if forbidden:
        raise AssertionError(f"Third-party text/gold artifacts leaked into public data: {forbidden}")
    with zipfile.ZipFile(ARCHIVE) as handle:
        names = {Path(name).name for name in handle.namelist() if not name.endswith("/")}
        leaked = sorted(name for name in names if name.startswith("test_candidates_") or name.endswith(".pubtator") or name == "error_analysis.csv")
        if leaked:
            raise AssertionError(f"Public reference ZIP leak: {leaked}")
        if handle.testzip() is not None:
            raise AssertionError("Public reference ZIP is corrupt")

    public_manifest = json.loads((DATA / "run_manifest_public.json").read_text(encoding="utf-8"))
    manifest_text = json.dumps(public_manifest)
    if "/content/" in manifest_text or "\\\\content\\\\" in manifest_text:
        raise AssertionError("Public manifest contains runtime absolute paths")
    gates = json.loads((DATA / "QUALITY_GATES.json").read_text(encoding="utf-8"))
    expected_gates = {
        "status": "PASS",
        "no_document_overlap": True,
        "threshold_tuned_on_development_only": True,
        "test_tuning_performed": False,
        "gold_entities_used_for_all_external_systems": True,
        "bioredirect_completed": True,
    }
    for key, value in expected_gates.items():
        if gates.get(key) != value:
            raise AssertionError((key, gates.get(key), value))

    metrics = pd.read_csv(DATA / "system_metrics.csv")
    expected = {
        ("sentence_local", "relation_type", "TypePairMajority"): 0.3113915010117843,
        ("sentence_local", "relation_type", "AISKGRuleTransfer"): 0.2747795635044712,
        ("sentence_local", "relation_type", "AISKGConstrainedTransfer"): 0.3857047809143617,
        ("sentence_local", "relation_type", "BioREDirect"): 0.6173139158576052,
        ("full_document", "relation_type", "TypePairMajority"): 0.198917229446894,
        ("full_document", "relation_type", "AISKGRuleTransfer"): 0.1837964621950027,
        ("full_document", "relation_type", "AISKGConstrainedTransfer"): 0.3624171662985169,
        ("full_document", "relation_type", "BioREDirect"): 0.5684279084914109,
    }
    indexed = metrics.set_index(["mode", "evaluation", "system"])
    for key, value in expected.items():
        observed = float(indexed.loc[key, "f1"])
        if not math.isclose(observed, value, rel_tol=0, abs_tol=1e-12):
            raise AssertionError((key, observed, value))
    candidate = pd.read_csv(DATA / "candidate_split_audit.csv")
    test = candidate[candidate.split.eq("test")].set_index("mode")
    if int(test.loc["sentence_local", "candidates"]) != 12726 or int(test.loc["full_document", "candidates"]) != 28734:
        raise AssertionError("External test candidate counts differ")

    prediction_files = sorted(DATA.glob("predictions_*.csv"))
    if len(prediction_files) != 8:
        raise AssertionError(f"Expected eight system prediction tables, found {len(prediction_files)}")
    forbidden_columns = {"text", "title", "abstract", "context", "gold_relation", "gold_direction"}
    for path in prediction_files:
        frame = pd.read_csv(path, nrows=3)
        if forbidden_columns & set(frame.columns):
            raise AssertionError(f"Text/gold columns in public prediction table: {path.name}")

    notebook = nbformat.read(ROOT / "notebooks" / "additional_analyses" / "AISKG_External_RE_Benchmark_Colab_v1_1.ipynb", as_version=4)
    nbformat.validate(notebook)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if len(code_cells) < 8:
        raise AssertionError("External notebook is unexpectedly short")
    notebook_text = "\n".join(cell.source for cell in notebook.cells)
    for marker in ["v3.2.0", "gold entity", "BC8", "public-output-dir", "run_external_re_smoke.py"]:
        if marker.lower() not in notebook_text.lower():
            raise AssertionError(f"Notebook missing marker: {marker}")

    for path in sorted((ROOT / "src" / "aiskg_external_re").glob("*.py")):
        py_compile.compile(str(path), doraise=True)
    if (ROOT / "src" / "aiskg_external_re" / "__init__.py").read_text().find('__version__ = "1.0.0"') < 0:
        raise AssertionError("External package version mismatch")

    provenance = json.loads((DATA / "source_provenance.json").read_text())
    if provenance["private_full_result_archive"]["public_repository_included"] is not False:
        raise AssertionError("Private full result redistribution boundary missing")

    credential_pattern = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})")
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".csv"}:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if credential_pattern.search(text):
                raise AssertionError(f"Credential-like pattern detected: {path.relative_to(ROOT)}")

    print(json.dumps({
        "release": RELEASE,
        "status": "PASS",
        "frozen_public_checksum_entries": entries,
        "prediction_tables": len(prediction_files),
        "external_notebook_code_cells": len(code_cells),
        "sentence_local_f1": {"AISKGConstrainedTransfer": expected[("sentence_local", "relation_type", "AISKGConstrainedTransfer")], "BioREDirect": expected[("sentence_local", "relation_type", "BioREDirect")]},
        "full_document_f1": {"AISKGConstrainedTransfer": expected[("full_document", "relation_type", "AISKGConstrainedTransfer")], "BioREDirect": expected[("full_document", "relation_type", "BioREDirect")]},
        "public_third_party_text": "EXCLUDED",
        "bc8_test_tuning": "LOCKED_NO_FURTHER_TUNING",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
