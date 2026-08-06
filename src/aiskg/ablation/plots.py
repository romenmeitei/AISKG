"""Publication-oriented ablation figures."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from ..config import AISKGConfig


def _labels(summary: pd.DataFrame) -> list[str]:
    return summary["label"].astype(str).tolist()


def _save(fig: plt.Figure, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def create_ablation_figures(summary: pd.DataFrame, output_dir: Path, config: AISKGConfig) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dpi = int(config.get("visualization.dpi"))
    labels = _labels(summary)
    x = np.arange(len(summary))
    paths: list[Path] = []

    # Performance comparison
    fig, ax = plt.subplots(figsize=(12, 6))
    width = 0.25
    ax.bar(x - width, summary["entity_f1"], width, label="Entity F1")
    ax.bar(x, summary["relation_f1"], width, label="Relation F1")
    ax.bar(x + width, summary["exact_triple_accuracy"], width, label="Exact triple accuracy")
    ax.set_ylim(0, 1.05); ax.set_ylabel("Score"); ax.set_title("Ablation performance comparison")
    ax.set_xticks(x, labels, rotation=45, ha="right"); ax.legend()
    path = output_dir / "performance.png"; _save(fig, path, dpi); paths.append(path)

    # Topology
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(x, summary["nodes"], marker="o", label="Nodes")
    ax.plot(x, summary["edges"], marker="s", label="Edges")
    ax.set_ylabel("Count"); ax.set_title("Graph topology across ablations")
    ax.set_xticks(x, labels, rotation=45, ha="right"); ax.legend()
    path = output_dir / "topology.png"; _save(fig, path, dpi); paths.append(path)

    # Precision/F1
    fig, ax = plt.subplots(figsize=(12, 6))
    columns = ["entity_precision", "entity_f1", "relation_precision", "relation_f1"]
    offsets = np.linspace(-0.3, 0.3, len(columns)); width = 0.18
    for offset, column in zip(offsets, columns):
        ax.bar(x + offset, summary[column], width, label=column.replace("_", " ").title())
    ax.set_ylim(0, 1.05); ax.set_ylabel("Score"); ax.set_title("Precision and F1 comparison")
    ax.set_xticks(x, labels, rotation=45, ha="right"); ax.legend(ncol=2)
    path = output_dir / "precision_f1.png"; _save(fig, path, dpi); paths.append(path)

    # Modularity
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x, summary["modularity"])
    ax.set_ylabel("Louvain modularity"); ax.set_title("Community modularity by ablation")
    ax.set_xticks(x, labels, rotation=45, ha="right")
    path = output_dir / "modularity.png"; _save(fig, path, dpi); paths.append(path)

    # Pathway count
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x, summary["pathway_count"])
    ax.set_ylabel("Pathway count"); ax.set_title("Reconstructed pathways by ablation")
    ax.set_xticks(x, labels, rotation=45, ha="right")
    path = output_dir / "pathway_count.png"; _save(fig, path, dpi); paths.append(path)

    # Radar chart
    radar_metrics = list(config.get("visualization.radar_metrics"))
    normalized = summary[radar_metrics].astype(float).copy()
    for column in radar_metrics:
        low, high = normalized[column].min(), normalized[column].max()
        normalized[column] = 1.0 if high == low else (normalized[column] - low) / (high - low)
    angles = np.linspace(0, 2 * np.pi, len(radar_metrics), endpoint=False).tolist(); angles += angles[:1]
    fig = plt.figure(figsize=(10, 8)); ax = fig.add_subplot(111, polar=True)
    for idx, row in normalized.iterrows():
        values = row.tolist(); values += values[:1]
        ax.plot(angles, values, linewidth=1.2, label=labels[idx])
    ax.set_xticks(angles[:-1], [m.replace("_", " ") for m in radar_metrics]); ax.set_ylim(0, 1)
    ax.set_title("Normalized ablation radar chart"); ax.legend(loc="upper left", bbox_to_anchor=(1.05, 1.0), fontsize=7)
    path = output_dir / "radar.png"; _save(fig, path, dpi); paths.append(path)

    # Heatmap
    heat_metrics = ["entity_f1", "relation_f1", "exact_triple_accuracy", "nodes", "edges", "modularity", "pathway_count", "monte_carlo_robustness"]
    matrix = summary[heat_metrics].astype(float).copy()
    for column in heat_metrics:
        low, high = matrix[column].min(), matrix[column].max()
        matrix[column] = 1.0 if high == low else (matrix[column] - low) / (high - low)
    fig, ax = plt.subplots(figsize=(12, 7))
    image = ax.imshow(matrix.to_numpy(), aspect="auto")
    ax.set_xticks(np.arange(len(heat_metrics)), [m.replace("_", " ") for m in heat_metrics], rotation=45, ha="right")
    ax.set_yticks(np.arange(len(labels)), labels)
    fig.colorbar(image, ax=ax, label="Normalized value"); ax.set_title("Ablation metric heatmap")
    path = output_dir / "heatmap.png"; _save(fig, path, dpi); paths.append(path)
    return paths


def create_ablation_pdf(summary: pd.DataFrame, path: Path, config: AISKGConfig) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = _labels(summary)
    with PdfPages(path) as pdf:
        fig, ax = plt.subplots(figsize=(11.69, 8.27)); ax.axis("off")
        ax.text(0.02, 0.95, "AISKG Framework v3.0.0 — Ablation Summary", fontsize=18, weight="bold", va="top")
        ax.text(0.02, 0.88, "All configurations use the same frozen corpus and preserve the published manuscript outputs.", fontsize=11, va="top")
        cols = ["label", "entity_f1", "relation_f1", "exact_triple_accuracy", "nodes", "edges", "modularity", "pathway_count"]
        table_df = summary[cols].copy()
        for col in ["entity_f1", "relation_f1", "exact_triple_accuracy", "modularity"]:
            table_df[col] = table_df[col].map(lambda x: f"{float(x):.3f}")
        table = ax.table(cellText=table_df.values, colLabels=table_df.columns, loc="center", cellLoc="center")
        table.auto_set_font_size(False); table.set_fontsize(7); table.scale(1, 1.4)
        pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)

        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        x = np.arange(len(summary)); width = 0.25
        ax.bar(x - width, summary["entity_f1"], width, label="Entity F1")
        ax.bar(x, summary["relation_f1"], width, label="Relation F1")
        ax.bar(x + width, summary["exact_triple_accuracy"], width, label="Exact triple accuracy")
        ax.set_ylim(0, 1.05); ax.set_xticks(x, labels, rotation=45, ha="right"); ax.legend(); ax.set_title("Performance comparison")
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)
    return path
