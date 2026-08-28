from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import zipfile
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd


FIXED_ZIP_TIMESTAMP = (2026, 8, 26, 0, 0, 0)


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: str | Path, payload: object) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def write_table(path: str | Path, frame: pd.DataFrame) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def environment_manifest() -> dict[str, object]:
    payload: dict[str, object] = {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cwd": os.getcwd(),
    }
    try:
        import numpy as np
        import pandas as pd
        import scipy
        import sklearn

        payload["packages"] = {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        }
    except Exception as exc:
        payload["package_version_error"] = repr(exc)
    try:
        import torch

        payload["torch"] = {
            "version": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_version": torch.version.cuda,
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
    except Exception as exc:
        payload["torch_error"] = repr(exc)
    return payload


def plot_system_f1(metrics: pd.DataFrame, output_path: str | Path) -> Path | None:
    relation = metrics[metrics["evaluation"] == "relation_type"].copy()
    if relation.empty:
        return None
    relation["label"] = relation["system"].astype(str) + "\n" + relation["mode"].astype(str)
    relation = relation.sort_values(["mode", "f1", "system"], ascending=[True, False, True])
    x = list(range(len(relation)))
    y = relation["f1"].to_numpy(float)
    low = y - relation["f1_ci_low"].to_numpy(float)
    high = relation["f1_ci_high"].to_numpy(float) - y

    fig, ax = plt.subplots(figsize=(max(8.0, len(relation) * 1.15), 5.6))
    ax.bar(x, y)
    ax.errorbar(x, y, yerr=[low, high], fmt="none", capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(relation["label"], rotation=35, ha="right")
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("Micro-F1")
    ax.set_title("External BioRED/BioREDirect relation-extraction benchmark")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_per_relation_recall(per_label: pd.DataFrame, output_path: str | Path, *, mode: str = "full_document") -> Path | None:
    subset = per_label[(per_label["mode"] == mode) & (per_label["gold_n"] > 0)].copy()
    if subset.empty:
        return None
    pivot = subset.pivot_table(index="relation", columns="system", values="recall", aggfunc="first").fillna(0.0)
    ax = pivot.plot(kind="bar", figsize=(11, 6))
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("Recall")
    ax.set_xlabel("BioRED relation class")
    ax.set_title(f"Per-class recall ({mode.replace('_', ' ')})")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="System", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig = ax.get_figure()
    fig.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def write_methods_snippet(path: str | Path, *, manifest: dict[str, object]) -> Path:
    asset = manifest.get("official_assets", {}) if isinstance(manifest.get("official_assets"), dict) else {}
    commit = asset.get("bioredirect_commit", "[resolved commit in run manifest]")
    split_scheme = manifest.get("split_scheme", "bioredirect_bc8_official")
    if split_scheme == "bioredirect_bc8_official":
        split_text = (
            "Following the official BioREDirect experiment, the released train and development "
            "partitions were combined for fitting, the original BioRED test partition was used "
            "only for development-stage threshold selection, and the independent BC8 test "
            "partition was used once for final evaluation."
        )
    else:
        split_text = (
            "The classic BioRED training, development and test partitions were retained without "
            "document overlap. Because the released BioREDirect model may have used the classic "
            "test partition during model development, this scheme must be reported as a secondary "
            "analysis rather than an untouched external test of that comparator."
        )
    text = f"""# Copy-ready Methods text — external relation-extraction validation

An external relation-extraction evaluation was conducted using the independently developed BioRED/BioREDirect corpus. {split_text} Gold entity mentions and normalized concept identifiers were supplied to every evaluated system so that the experiment isolated relation classification and directionality rather than conflating named-entity recognition with relation extraction. Two AISKG-derived transfer systems were prespecified: a transparent ontology/type-constrained trigger adapter and a TF–IDF linear classifier whose candidate universe was restricted to BioRED-supported entity-type pairs. A training-only type-pair majority model served as a leakage-controlled baseline. Model parameters were fitted on the training split, the positive-decision threshold was selected on the development split, and the final test split was evaluated only after these settings were locked.

Two scopes were analysed. The sentence-local analysis retained candidate pairs with at least one co-sentential mention pair and was treated as the closest architectural match to the sentence-level AISKG v3.1.2 extractor. The full-document analysis retained all eligible concept pairs and was treated as a cross-sentence stress test. The official BioREDirect pretrained model was executed from source commit `{commit}` using its released model and dataset files; resolved source revision, download URLs, SHA-256 checksums, runtime versions and inference logs were archived. Relation-type micro-precision, recall and F1 were calculated from exact normalized concept-pair and relation-label matches. Relation-plus-direction F1 was additionally calculated for gold relations carrying a BioREDirect Subject annotation. Uncertainty was estimated by document-level bootstrap resampling, and paired system comparisons used bootstrap F1 differences and exact McNemar tests on document-level exact correctness with Holm adjustment. No external test labels were used to develop aliases, trigger rules, type constraints, features or thresholds.

Reporting boundary: the AISKG external transfer systems are new domain-transfer adapters and are not the unchanged mushroom-poisoning v3.1.2 extractor. Their results must therefore be reported as external portability analyses rather than as a replacement for the frozen in-domain 150-sentence benchmark.
"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _format_metric(row: pd.Series) -> str:
    return (
        f"precision {row['precision']:.3f}, recall {row['recall']:.3f}, "
        f"F1 {row['f1']:.3f} (95% bootstrap CI {row['f1_ci_low']:.3f}–{row['f1_ci_high']:.3f}; "
        f"TP={int(row['tp'])}, FP={int(row['fp'])}, FN={int(row['fn'])})"
    )


def write_results_template(path: str | Path, metrics: pd.DataFrame, comparisons: pd.DataFrame) -> Path:
    lines = [
        "# Copy-ready Results draft — verify journal wording before use",
        "",
        "The external evaluation used gold BioRED/BioREDirect entity annotations and therefore measures relation extraction rather than end-to-end entity-plus-relation performance.",
        "",
    ]
    for mode in ["sentence_local", "full_document"]:
        subset = metrics[(metrics["mode"] == mode) & (metrics["evaluation"] == "relation_type")]
        if subset.empty:
            continue
        lines.append(f"## {mode.replace('_', ' ').title()}")
        for _, row in subset.sort_values("system").iterrows():
            lines.append(f"- **{row['system']}**: {_format_metric(row)}.")
        lines.append("")
        direction = metrics[(metrics["mode"] == mode) & (metrics["evaluation"] == "relation_plus_direction")]
        if not direction.empty:
            lines.append("Direction-aware exact relation results:")
            for _, row in direction.sort_values("system").iterrows():
                lines.append(f"- **{row['system']}**: {_format_metric(row)}.")
            lines.append("")
    if not comparisons.empty:
        lines.extend(["## Paired comparisons", ""])
        for _, row in comparisons.iterrows():
            lines.append(
                f"- {row['mode']}: {row['system_a']} minus {row['system_b']} F1 difference "
                f"{row['f1_difference_a_minus_b']:.3f} (95% bootstrap CI "
                f"{row['difference_ci_low']:.3f}–{row['difference_ci_high']:.3f}); "
                f"Holm-adjusted exact McNemar P={row.get('holm_adjusted_p', float('nan')):.4g}."
            )
    lines.extend(
        [
            "",
            "## Mandatory interpretation boundary",
            "",
            "These external results use gold entity annotations and a new AISKG-derived transfer adapter. They do not demonstrate end-to-end cross-domain entity recognition, and they must not be described as performance of the unchanged mushroom-domain v3.1.2 extractor.",
            "",
        ]
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_sha256s(root: str | Path, output_path: str | Path | None = None) -> Path:
    root = Path(root)
    output_path = Path(output_path) if output_path else root / "SHA256SUMS.txt"
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p != output_path):
        lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def deterministic_zip(source_dir: str | Path, zip_path: str | Path) -> Path:
    source_dir = Path(source_dir)
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in source_dir.rglob("*") if p.is_file()):
            relative = path.relative_to(source_dir).as_posix()
            info = zipfile.ZipInfo(relative, date_time=FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return zip_path
