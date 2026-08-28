#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aiskg-external-re-smoke-") as temporary:
        tmp = Path(temporary)
        output = tmp / "full-results"
        public = tmp / "public-results"
        fixture = ROOT / "tests" / "fixtures" / "external_re"
        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_external_re_benchmark.py"),
            "--package-root", str(ROOT),
            "--work-dir", str(tmp / "work"),
            "--output-dir", str(output),
            "--config", str(ROOT / "configs" / "external_re" / "benchmark_config.json"),
            "--rules", str(ROOT / "ontology" / "external_re" / "biored_trigger_rules.json"),
            "--train-pubtator", str(fixture / "fixture_train.pubtator"),
            "--dev-pubtator", str(fixture / "fixture_dev.pubtator"),
            "--test-pubtator", str(fixture / "fixture_test.pubtator"),
            "--bioredirect-predictions", str(fixture / "fixture_test.pubtator"),
            "--run-bioredirect", "--no-download", "--bootstrap-iterations", "100", "--clean",
            "--public-output-dir", str(public),
        ]
        process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        print(process.stdout)
        if process.returncode:
            print(process.stderr, file=sys.stderr)
            return process.returncode
        gates = json.loads((output / "QUALITY_GATES.json").read_text(encoding="utf-8"))
        if gates.get("status") != "PASS":
            raise AssertionError(gates)
        metrics = pd.read_csv(output / "system_metrics.csv")
        expected = {"TypePairMajority", "AISKGRuleTransfer", "AISKGConstrainedTransfer", "BioREDirect"}
        if set(metrics.system) != expected or set(metrics["mode"]) != {"sentence_local", "full_document"}:
            raise AssertionError("Unexpected smoke metric coverage")
        comparator = metrics[(metrics.system == "BioREDirect") & (metrics.evaluation == "relation_type")]
        if len(comparator) != 2 or not (comparator.f1 == 1.0).all():
            raise AssertionError(comparator)
        forbidden = [p.name for p in public.rglob("*") if p.is_file() and (p.name.startswith("test_candidates_") or p.suffix == ".pubtator" or p.name == "error_analysis.csv")]
        if forbidden:
            raise AssertionError(f"Public exporter leaked forbidden files: {forbidden}")
        public_manifest = json.loads((public / "run_manifest_public.json").read_text(encoding="utf-8"))
        if "/content/" in json.dumps(public_manifest):
            raise AssertionError("Public manifest contains Colab absolute paths")
        if not output.with_suffix(".zip").is_file() or not public.with_suffix(".zip").is_file():
            raise AssertionError("Smoke archives missing")
    print("PASS: external relation benchmark offline smoke and public export")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
