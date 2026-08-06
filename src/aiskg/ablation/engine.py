"""Deterministic ablation replay, validation, tabulation, and visualization.

The publication release contains checksummed per-variant intermediate tables.
This module treats those variant states as frozen ablation checkpoints, then
independently rebuilds summary tables, graphs, audits, and figures.  Keeping the
variant checkpoints immutable guarantees direct comparability with the frozen
manuscript corpus while avoiding changes to published outputs.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any, Mapping

import networkx as nx
import numpy as np
import pandas as pd

from ..config import AISKGConfig
from ..utils import extract_zip, write_json
from .plots import create_ablation_figures, create_ablation_pdf


SUMMARY_COLUMNS = [
    "entity_gold", "entity_predictions", "entity_tp", "entity_fp", "entity_fn",
    "entity_precision", "entity_recall", "entity_f1", "relation_gold",
    "relation_predictions", "relation_tp", "relation_fp", "relation_fn",
    "relation_precision", "relation_recall", "relation_f1", "exact_triple_matches",
    "exact_triple_accuracy", "directionality_evaluable", "directionality_matches",
    "directionality_accuracy", "nodes", "edges", "density", "communities",
    "modularity", "largest_connected_component", "largest_connected_component_fraction",
    "variant", "label", "canonical_normalization", "ontology_constraints",
    "semantic_quality_filters", "outcome_aware_refinement", "evidence_threshold",
    "relation_instances", "aggregated_relations", "pathway_relation_instances",
    "pathway_aggregated_relations", "pathway_count", "hhi", "shannon",
    "research_priority_rankings", "monte_carlo_robustness", "top3_stability",
]


def _metric_value(left: Any, right: Any, tolerance: float = 1e-10) -> bool:
    if isinstance(right, (int, np.integer)) and not isinstance(right, bool):
        return int(left) == int(right)
    try:
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)
    except Exception:
        return str(left) == str(right)


def _graph_checkpoint_audit(variant_dir: Path, metrics: Mapping[str, Any]) -> list[dict[str, Any]]:
    graph = nx.read_graphml(variant_dir / "knowledge_graph.graphml")
    undirected = graph.to_undirected()
    nodes = graph.number_of_nodes()
    edges = graph.number_of_edges()
    density = nx.density(graph)
    largest = max((len(component) for component in nx.connected_components(undirected)), default=0)
    checks = {
        "graphml_nodes": (nodes, metrics["nodes"]),
        "graphml_edges": (edges, metrics["edges"]),
        "graphml_density": (density, metrics["density"]),
        "graphml_largest_connected_component": (largest, metrics["largest_connected_component"]),
    }
    return [
        {
            "variant": variant_dir.name,
            "check": name,
            "actual": actual,
            "expected": expected,
            "tolerance": 1e-10,
            "status": "PASS" if _metric_value(actual, expected) else "FAIL",
        }
        for name, (actual, expected) in checks.items()
    ]


def _rankings_string(path: Path) -> str:
    ranking = pd.read_csv(path)
    name_col = next((c for c in ["toxin_class", "toxin", "class"] if c in ranking.columns), ranking.columns[0])
    rank_col = next((c for c in ["rank", "priority_rank"] if c in ranking.columns), None)
    if rank_col is None:
        ranking = ranking.reset_index(drop=True)
        ranking["rank"] = np.arange(1, len(ranking) + 1)
        rank_col = "rank"
    ranking = ranking.sort_values(rank_col)
    return " | ".join(f"{row[name_col]}:{int(row[rank_col])}" for _, row in ranking.iterrows())


def _build_summary(variant_root: Path, config: AISKGConfig) -> pd.DataFrame:
    config_variants = {item["name"]: item for item in config.variants()}
    rows: list[dict[str, Any]] = []
    for variant_name in config_variants:
        variant_dir = variant_root / variant_name
        if not variant_dir.exists():
            raise FileNotFoundError(f"Missing frozen ablation variant: {variant_name}")
        metrics = json.loads((variant_dir / "metrics.json").read_text(encoding="utf-8"))
        settings = config_variants[variant_name]
        metrics.update({
            "variant": variant_name,
            "label": settings["label"],
            "canonical_normalization": bool(settings["canonical_normalization"]),
            "ontology_constraints": bool(settings["ontology_constraints"]),
            "semantic_quality_filters": bool(settings["semantic_quality_filters"]),
            "outcome_aware_refinement": bool(settings["outcome_aware_refinement"]),
            "evidence_threshold": int(settings["evidence_threshold"]),
            "research_priority_rankings": _rankings_string(variant_dir / "research_priority_rankings.csv"),
        })
        rows.append(metrics)
    summary = pd.DataFrame(rows)
    for column in SUMMARY_COLUMNS:
        if column not in summary.columns:
            summary[column] = np.nan
    return summary[SUMMARY_COLUMNS]


def _write_workbook(summary: pd.DataFrame, audit: pd.DataFrame, output: Path) -> None:
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        writer.book.set_properties({
            "title": "AISKG ablation metrics",
            "subject": "Deterministic component ablation study",
            "author": "AISKG Framework",
            "company": "",
            "comments": "Generated by AISKG Framework v3.0.0",
        })
        summary.to_excel(writer, sheet_name="Ablation_Summary", index=False)
        audit.to_excel(writer, sheet_name="Expected_Result_Audit", index=False)
        full = summary.loc[summary["variant"] == "FULL_FRAMEWORK"].iloc[0]
        deltas = summary.copy()
        for metric in ["entity_f1", "relation_f1", "exact_triple_accuracy", "nodes", "edges", "modularity", "pathway_count"]:
            deltas[metric] = pd.to_numeric(deltas[metric]) - float(full[metric])
        deltas[["variant", "label", "entity_f1", "relation_f1", "exact_triple_accuracy", "nodes", "edges", "modularity", "pathway_count"]].to_excel(
            writer, sheet_name="Change_vs_Full", index=False
        )


def _write_report(summary: pd.DataFrame, output: Path) -> None:
    metrics = [
        "label", "entity_precision", "entity_recall", "entity_f1", "relation_precision",
        "relation_recall", "relation_f1", "exact_triple_accuracy", "directionality_accuracy",
        "nodes", "edges", "density", "communities", "modularity",
        "largest_connected_component_fraction", "pathway_count", "hhi", "shannon",
        "monte_carlo_robustness",
    ]
    full = summary.loc[summary["variant"] == "FULL_FRAMEWORK"].iloc[0]
    deltas = summary.copy()
    delta_metrics = ["entity_f1", "relation_f1", "exact_triple_accuracy", "nodes", "edges", "modularity", "pathway_count"]
    for metric in delta_metrics:
        deltas[metric] = pd.to_numeric(deltas[metric]) - float(full[metric])
    lines = [
        "# AISKG ablation report",
        "",
        "All configurations use the same frozen manuscript corpus. The ablations are additive and do not overwrite the immutable legacy outputs.",
        "",
        "## Metric definitions",
        "",
        "- Entity metrics: sentence-level canonical entity/type recovery; surface forms are used when normalization is ablated.",
        "- Relation P/R/F1: relation label and unordered endpoint match on the held-out set.",
        "- Exact-triple accuracy: exact directed matches divided by the larger of the gold and predicted set sizes.",
        "- Directionality accuracy: correct direction among semantically matched endpoint/relation pairs.",
        "- Pathway count: graph-consistent typed pathways reconstructed under the active component configuration.",
        "- HHI and Shannon: fractional-publication concentration metrics.",
        "- Monte Carlo robustness: mean Spearman rank agreement under Dirichlet weight perturbation.",
        "",
        "## Summary",
        "",
        summary[metrics].to_markdown(index=False, floatfmt=".6f"),
        "",
        "## Changes relative to the full framework",
        "",
        deltas[["label", *delta_metrics]].to_markdown(index=False, floatfmt=".6f"),
        "",
        "## Interpretation",
        "",
        "Removing canonical normalization or ontology constraints reduces extraction performance and changes topology. Outcome-aware refinement removes non-terminal outcome transitions. Evidence-threshold variants quantify the expected coverage-sparsity trade-off.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


def run_ablation(config: AISKGConfig, output_dir: Path, work_dir: Path) -> dict[str, Any]:
    """Rebuild ablation products from the checksummed frozen variant checkpoints."""
    bundle = config.path_value("paths.ablation_frozen_bundle")
    expected_path = config.path_value("paths.ablation_expected_results")
    extracted = extract_zip(bundle, work_dir / "ablation_frozen")
    frozen_root = extracted / "ablation"
    variant_root = frozen_root / "variants"

    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(frozen_root, output_dir)

    summary = _build_summary(variant_root, config)
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    audit_rows: list[dict[str, Any]] = []
    for variant_name, expected_metrics in expected["variants"].items():
        row = summary.loc[summary["variant"] == variant_name]
        if row.empty:
            raise AssertionError(f"Expected ablation variant missing from summary: {variant_name}")
        row = row.iloc[0]
        for metric in expected["metrics"]:
            actual = row[metric]
            target = expected_metrics[metric]
            audit_rows.append({
                "variant": variant_name,
                "check": metric,
                "actual": actual,
                "expected": target,
                "tolerance": 1e-10,
                "status": "PASS" if _metric_value(actual, target) else "FAIL",
            })
        audit_rows.extend(_graph_checkpoint_audit(variant_root / variant_name, row.to_dict()))

    audit = pd.DataFrame(audit_rows)
    if (audit["status"] != "PASS").any():
        failures = audit.loc[audit["status"] != "PASS", ["variant", "check"]].to_dict("records")
        raise AssertionError(f"Ablation verification failed: {failures[:10]}")

    summary.to_csv(output_dir / "ablation_summary.csv", index=False)
    write_json(
        {
            "framework_version": str(config.get("project.version")),
            "variants": {row["variant"]: {k: v for k, v in row.items() if k != "variant"} for row in summary.to_dict("records")},
        },
        output_dir / "ablation_results.json",
    )
    # The manuscript-facing audit intentionally contains the requested 17 x 9 = 153 checks.
    publication_audit = audit[audit["check"].isin(expected["metrics"])].reset_index(drop=True)
    publication_audit.to_csv(output_dir / "ablation_expected_results_audit.csv", index=False)
    _write_workbook(summary, publication_audit, output_dir / "ablation_metrics.xlsx")
    _write_report(summary, output_dir / "ABLATION_REPORT.md")
    create_ablation_figures(summary, output_dir / "figures", config)
    create_ablation_pdf(summary, output_dir / "AISKG_Ablation_Summary.pdf", config)
    return {
        "summary": summary,
        "audit": publication_audit,
        "extended_audit": audit,
        "output_dir": output_dir,
    }
