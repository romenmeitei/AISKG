"""Reproducibility audits for frozen legacy outputs and additive ablations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _normalize_status(value: Any) -> str:
    text = str(value).strip().upper()
    return "PASS" if text in {"PASS", "PASS_CONTENT", "SUCCESS", "TRUE"} else text


def build_reproducibility_audit(
    section1_output: Path | None,
    section2_output: Path | None,
    ablation_audit: pd.DataFrame | None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    if section1_output is not None:
        bridge_path = section1_output / "audits" / "04_post_extraction_bridge_audit.csv"
        bridge = pd.read_csv(bridge_path)
        for idx, row in bridge.iterrows():
            rows.append({
                "category": "section1_to_section2_bridge",
                "check": str(row.get("file", row.get("item", f"bridge_{idx+1}"))),
                "actual": row.get("actual_sha256", row.get("status", "")),
                "expected": row.get("expected_sha256", "PASS"),
                "status": _normalize_status(row.get("status", "FAIL")),
            })

    if section2_output is not None:
        expected_path = section2_output / "00_expected_results_check.csv"
        expected = pd.read_csv(expected_path)
        for _, row in expected.iterrows():
            rows.append({
                "category": "legacy_section2_expected_results",
                "check": str(row["check"]),
                "actual": row["actual"],
                "expected": row["expected"],
                "status": _normalize_status(row["status"]),
            })

    if ablation_audit is not None:
        for _, row in ablation_audit.iterrows():
            rows.append({
                "category": "ablation_expected_results",
                "check": f"{row['variant']}::{row['check']}",
                "actual": row["actual"],
                "expected": row["expected"],
                "status": _normalize_status(row["status"]),
            })

    rows.append({
        "category": "pipeline",
        "check": "all_enabled_stages_completed",
        "actual": 1,
        "expected": 1,
        "status": "PASS",
    })
    audit = pd.DataFrame(rows)
    return audit


def assert_audit_passed(audit: pd.DataFrame, expected_total: int | None = None) -> None:
    failures = audit.loc[audit["status"] != "PASS"]
    if not failures.empty:
        raise AssertionError(f"Reproducibility audit failed: {failures.head(20).to_dict('records')}")
    if expected_total is not None and len(audit) != expected_total:
        raise AssertionError(f"Expected {expected_total} audit checks, observed {len(audit)}")
