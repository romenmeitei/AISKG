from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .candidates import candidate_universe
from .io_pubtator import normalize_relation_label
from .models import CandidateExample, Document, Prediction


NONE_LABEL = "None"


def gold_from_examples(examples: Iterable[CandidateExample], *, system: str = "Gold", mode: str = "") -> list[Prediction]:
    result: list[Prediction] = []
    for example in examples:
        if example.label == NONE_LABEL:
            continue
        result.append(
            Prediction(
                doc_id=example.doc_id,
                id1=example.id1,
                id2=example.id2,
                label=normalize_relation_label(example.label),
                subject=example.subject,
                score=1.0,
                system=system,
                mode=mode,
            )
        )
    return result


def predictions_from_documents(
    documents: Iterable[Document],
    examples: Sequence[CandidateExample],
    *,
    system: str,
    mode: str,
) -> list[Prediction]:
    universe = candidate_universe(examples)
    result: list[Prediction] = []
    for document in documents:
        for relation in document.relations:
            pair = tuple(sorted((relation.arg1, relation.arg2)))
            if (document.doc_id, *pair) not in universe:
                continue
            result.append(
                Prediction(
                    doc_id=document.doc_id,
                    id1=relation.arg1,
                    id2=relation.arg2,
                    label=normalize_relation_label(relation.label),
                    subject=relation.subject,
                    score=relation.score,
                    system=system,
                    mode=mode,
                )
            )
    return result


def _relation_key(item: Prediction) -> tuple[str, str, str, str]:
    id1, id2 = sorted((item.id1, item.id2))
    return item.doc_id, id1, id2, normalize_relation_label(item.label)


def _direction_key(item: Prediction) -> tuple[str, str, str, str, str]:
    doc_id, id1, id2, label = _relation_key(item)
    return doc_id, id1, id2, label, item.subject or "MISSING_SUBJECT"


def _deduplicate(items: Iterable[Prediction], *, directional: bool = False) -> dict[tuple, Prediction]:
    key_fn = _direction_key if directional else _relation_key
    result: dict[tuple, Prediction] = {}
    for item in items:
        if normalize_relation_label(item.label) == NONE_LABEL:
            continue
        key = key_fn(item)
        previous = result.get(key)
        if previous is None or (item.score or -math.inf) > (previous.score or -math.inf):
            result[key] = item
    return result


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def relation_counts(
    gold: Iterable[Prediction],
    predicted: Iterable[Prediction],
    *,
    directional: bool = False,
) -> tuple[int, int, int, set[tuple], set[tuple], set[tuple]]:
    gold_map = _deduplicate(gold, directional=directional)
    pred_map = _deduplicate(predicted, directional=directional)
    gold_keys, pred_keys = set(gold_map), set(pred_map)
    tp_keys = gold_keys & pred_keys
    fp_keys = pred_keys - gold_keys
    fn_keys = gold_keys - pred_keys
    return len(tp_keys), len(fp_keys), len(fn_keys), tp_keys, fp_keys, fn_keys


def metric_row(
    gold: Sequence[Prediction],
    predicted: Sequence[Prediction],
    *,
    system: str,
    mode: str,
    directional: bool = False,
) -> dict[str, object]:
    tp, fp, fn, _, _, _ = relation_counts(gold, predicted, directional=directional)
    precision, recall, f1 = precision_recall_f1(tp, fp, fn)
    return {
        "mode": mode,
        "evaluation": "relation_plus_direction" if directional else "relation_type",
        "system": system,
        "gold_n": len(_deduplicate(gold, directional=directional)),
        "predicted_n": len(_deduplicate(predicted, directional=directional)),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _counts_by_doc(
    gold: Sequence[Prediction],
    predicted: Sequence[Prediction],
    *,
    directional: bool,
) -> tuple[list[str], np.ndarray]:
    gold_map = _deduplicate(gold, directional=directional)
    pred_map = _deduplicate(predicted, directional=directional)
    doc_ids = sorted({key[0] for key in gold_map} | {key[0] for key in pred_map})
    rows = []
    for doc_id in doc_ids:
        g = {key for key in gold_map if key[0] == doc_id}
        p = {key for key in pred_map if key[0] == doc_id}
        rows.append((len(g & p), len(p - g), len(g - p)))
    return doc_ids, np.asarray(rows, dtype=int)


def bootstrap_f1_ci(
    gold: Sequence[Prediction],
    predicted: Sequence[Prediction],
    *,
    iterations: int,
    seed: int,
    directional: bool = False,
) -> tuple[float, float]:
    _, counts = _counts_by_doc(gold, predicted, directional=directional)
    if len(counts) == 0 or iterations <= 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    values = np.empty(iterations, dtype=float)
    for i in range(iterations):
        indices = rng.integers(0, len(counts), size=len(counts))
        tp, fp, fn = counts[indices].sum(axis=0)
        values[i] = precision_recall_f1(int(tp), int(fp), int(fn))[2]
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def paired_bootstrap_difference(
    gold: Sequence[Prediction],
    pred_a: Sequence[Prediction],
    pred_b: Sequence[Prediction],
    *,
    iterations: int,
    seed: int,
    directional: bool = False,
) -> dict[str, float]:
    docs_a, counts_a = _counts_by_doc(gold, pred_a, directional=directional)
    docs_b, counts_b = _counts_by_doc(gold, pred_b, directional=directional)
    all_docs = sorted(set(docs_a) | set(docs_b))
    map_a = {doc: counts_a[i] for i, doc in enumerate(docs_a)}
    map_b = {doc: counts_b[i] for i, doc in enumerate(docs_b)}
    array_a = np.asarray([map_a.get(doc, np.zeros(3, dtype=int)) for doc in all_docs], dtype=int)
    array_b = np.asarray([map_b.get(doc, np.zeros(3, dtype=int)) for doc in all_docs], dtype=int)
    if not all_docs:
        return {"difference": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}

    def score(array: np.ndarray) -> float:
        tp, fp, fn = array.sum(axis=0)
        return precision_recall_f1(int(tp), int(fp), int(fn))[2]

    observed = score(array_a) - score(array_b)
    rng = np.random.default_rng(seed)
    values = np.empty(iterations, dtype=float)
    for i in range(iterations):
        indices = rng.integers(0, len(all_docs), size=len(all_docs))
        values[i] = score(array_a[indices]) - score(array_b[indices])
    return {
        "difference": float(observed),
        "ci_low": float(np.quantile(values, 0.025)),
        "ci_high": float(np.quantile(values, 0.975)),
    }


def document_exactness(
    gold: Sequence[Prediction],
    predicted: Sequence[Prediction],
    *,
    directional: bool = False,
) -> dict[str, bool]:
    gold_map = _deduplicate(gold, directional=directional)
    pred_map = _deduplicate(predicted, directional=directional)
    docs = sorted({key[0] for key in gold_map} | {key[0] for key in pred_map})
    result: dict[str, bool] = {}
    for doc in docs:
        g = {key for key in gold_map if key[0] == doc}
        p = {key for key in pred_map if key[0] == doc}
        result[doc] = g == p
    return result


def exact_mcnemar(
    gold: Sequence[Prediction],
    pred_a: Sequence[Prediction],
    pred_b: Sequence[Prediction],
    *,
    directional: bool = False,
) -> dict[str, object]:
    exact_a = document_exactness(gold, pred_a, directional=directional)
    exact_b = document_exactness(gold, pred_b, directional=directional)
    docs = sorted(set(exact_a) | set(exact_b))
    both_correct = sum(exact_a.get(doc, False) and exact_b.get(doc, False) for doc in docs)
    a_only = sum(exact_a.get(doc, False) and not exact_b.get(doc, False) for doc in docs)
    b_only = sum(not exact_a.get(doc, False) and exact_b.get(doc, False) for doc in docs)
    both_wrong = len(docs) - both_correct - a_only - b_only
    discordant = a_only + b_only
    p_value = float(binomtest(min(a_only, b_only), discordant, 0.5, alternative="two-sided").pvalue) if discordant else 1.0
    return {
        "documents": len(docs),
        "both_exact": both_correct,
        "a_only_exact": a_only,
        "b_only_exact": b_only,
        "neither_exact": both_wrong,
        "exact_mcnemar_p": p_value,
    }


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [1.0] * n
    running = 0.0
    for rank, index in enumerate(order):
        value = min(1.0, (n - rank) * float(p_values[index]))
        running = max(running, value)
        adjusted[index] = running
    return adjusted


def per_relation_metrics(
    gold: Sequence[Prediction],
    predicted: Sequence[Prediction],
    *,
    system: str,
    mode: str,
) -> pd.DataFrame:
    labels = sorted({normalize_relation_label(item.label) for item in gold} | {normalize_relation_label(item.label) for item in predicted})
    rows: list[dict[str, object]] = []
    for label in labels:
        gold_label = [item for item in gold if normalize_relation_label(item.label) == label]
        pred_label = [item for item in predicted if normalize_relation_label(item.label) == label]
        tp, fp, fn, _, _, _ = relation_counts(gold_label, pred_label)
        precision, recall, f1 = precision_recall_f1(tp, fp, fn)
        rows.append(
            {
                "mode": mode,
                "system": system,
                "relation": label,
                "gold_n": len(_deduplicate(gold_label)),
                "predicted_n": len(_deduplicate(pred_label)),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    return pd.DataFrame(rows)


def direction_subset(gold: Sequence[Prediction], predicted: Sequence[Prediction]) -> tuple[list[Prediction], list[Prediction]]:
    """Restrict direction evaluation to gold relations with an annotated subject."""

    evaluable_pairs = {
        _relation_key(item)[:3]
        for item in gold
        if item.subject is not None and item.subject in {item.id1, item.id2}
    }
    gold_subset = [
        item for item in gold
        if _relation_key(item)[:3] in evaluable_pairs and item.subject
    ]
    pred_subset = [
        item for item in predicted
        if _relation_key(item)[:3] in evaluable_pairs
    ]
    return gold_subset, pred_subset


def error_table(
    gold: Sequence[Prediction],
    predicted: Sequence[Prediction],
    *,
    system: str,
    mode: str,
) -> pd.DataFrame:
    gold_map = _deduplicate(gold)
    pred_map = _deduplicate(predicted)
    rows: list[dict[str, object]] = []
    for key in sorted(set(gold_map) - set(pred_map)):
        item = gold_map[key]
        rows.append(
            {
                "mode": mode,
                "system": system,
                "error": "false_negative",
                "doc_id": item.doc_id,
                "id1": min(item.id1, item.id2),
                "id2": max(item.id1, item.id2),
                "gold_relation": item.label,
                "predicted_relation": "None",
                "gold_subject": item.subject or "",
                "predicted_subject": "",
            }
        )
    for key in sorted(set(pred_map) - set(gold_map)):
        item = pred_map[key]
        pair = (key[0], key[1], key[2])
        competing = [value for gkey, value in gold_map.items() if gkey[:3] == pair]
        rows.append(
            {
                "mode": mode,
                "system": system,
                "error": "wrong_label" if competing else "false_positive",
                "doc_id": item.doc_id,
                "id1": min(item.id1, item.id2),
                "id2": max(item.id1, item.id2),
                "gold_relation": ";".join(sorted({x.label for x in competing})) if competing else "None",
                "predicted_relation": item.label,
                "gold_subject": ";".join(sorted({x.subject or "" for x in competing})) if competing else "",
                "predicted_subject": item.subject or "",
            }
        )
    return pd.DataFrame(rows)


def metrics_with_ci(
    gold: Sequence[Prediction],
    predictions_by_system: dict[str, Sequence[Prediction]],
    *,
    mode: str,
    iterations: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict[str, object]] = []
    per_label_frames: list[pd.DataFrame] = []
    error_frames: list[pd.DataFrame] = []

    for offset, (system, predicted) in enumerate(predictions_by_system.items()):
        row = metric_row(gold, predicted, system=system, mode=mode)
        low, high = bootstrap_f1_ci(gold, predicted, iterations=iterations, seed=seed + offset)
        row["f1_ci_low"] = low
        row["f1_ci_high"] = high
        metric_rows.append(row)
        per_label_frames.append(per_relation_metrics(gold, predicted, system=system, mode=mode))
        error_frames.append(error_table(gold, predicted, system=system, mode=mode))

        direction_gold, direction_pred = direction_subset(gold, predicted)
        if direction_gold:
            drow = metric_row(
                direction_gold,
                direction_pred,
                system=system,
                mode=mode,
                directional=True,
            )
            dlow, dhigh = bootstrap_f1_ci(
                direction_gold,
                direction_pred,
                iterations=iterations,
                seed=seed + 1000 + offset,
                directional=True,
            )
            drow["f1_ci_low"] = dlow
            drow["f1_ci_high"] = dhigh
            metric_rows.append(drow)

    comparisons: list[dict[str, object]] = []
    systems = list(predictions_by_system)
    for i, system_a in enumerate(systems):
        for j in range(i + 1, len(systems)):
            system_b = systems[j]
            pred_a = predictions_by_system[system_a]
            pred_b = predictions_by_system[system_b]
            diff = paired_bootstrap_difference(
                gold,
                pred_a,
                pred_b,
                iterations=iterations,
                seed=seed + 10000 + i * 100 + j,
            )
            test = exact_mcnemar(gold, pred_a, pred_b)
            comparisons.append(
                {
                    "mode": mode,
                    "evaluation": "relation_type",
                    "system_a": system_a,
                    "system_b": system_b,
                    "f1_difference_a_minus_b": diff["difference"],
                    "difference_ci_low": diff["ci_low"],
                    "difference_ci_high": diff["ci_high"],
                    **test,
                }
            )

    if comparisons:
        adjusted = holm_adjust([float(row["exact_mcnemar_p"]) for row in comparisons])
        for row, value in zip(comparisons, adjusted):
            row["holm_adjusted_p"] = value

    metrics = pd.DataFrame(metric_rows)
    per_label = pd.concat(per_label_frames, ignore_index=True) if per_label_frames else pd.DataFrame()
    errors = pd.concat(error_frames, ignore_index=True) if error_frames else pd.DataFrame()
    comparison_df = pd.DataFrame(comparisons)
    return metrics, per_label, comparison_df, errors
