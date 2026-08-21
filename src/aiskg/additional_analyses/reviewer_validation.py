"""Reviewer-level replay for the AISKG v3.1.2 pathway validation.

The public release contains metadata-sanitized, content-equivalent copies of the
completed Expert A, Expert B, and third-expert workbooks.  This module reads the
OOXML containers directly, validates the complete adjudication trail, recomputes
agreement, and reconstructs every final binary label before pathway statistics
are calculated.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import posixpath
import re
from pathlib import Path
from typing import Any, Iterable, Mapping
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd

from ..utils import sha256_file

RATING_COLUMNS = [
    "entities_correct",
    "relations_correct",
    "direction_correct",
    "sequence_coherent",
    "terminal_class_correct",
    "all_edges_evidence_supported",
    "complete_pathway_correct",
]
COMPONENT_RATING_COLUMNS = RATING_COLUMNS[:-1]
STATIC_COLUMNS = [
    "validation_id",
    "path_text",
    "pathway_template",
    "relation_chain",
    "supporting_evidence",
]
ALLOWED_SOURCE_LABELS = {"Yes", "No", "Borderline", "Uncertain"}
FINAL_LABELS = {"Yes", "No"}
NONDEFINITIVE_LABELS = {"Borderline", "Uncertain"}
FIXED_PUBLIC_XLSX_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS = f"{{{_MAIN_NS}}}"
_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_CELL_REF_RE = re.compile(r"([A-Z]+)([0-9]+)")


@dataclass(frozen=True)
class ReviewerReplay:
    """Validated reviewer workbooks and all reconstructed outputs."""

    expert_a: pd.DataFrame
    expert_b: pd.DataFrame
    third_expert: pd.DataFrame
    agreement: pd.DataFrame
    rating_matrix_long: pd.DataFrame
    adjudication_audit: pd.DataFrame
    reconstructed_ratings: pd.DataFrame
    qc: dict[str, Any]


def _normalise_blank(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value)


def _normalise_label(value: Any) -> str:
    return _normalise_blank(value).strip()


def _column_index(reference: str) -> int:
    match = _CELL_REF_RE.fullmatch(reference)
    if not match:
        raise ValueError(f"Invalid OOXML cell reference: {reference}")
    number = 0
    for character in match.group(1):
        number = number * 26 + ord(character) - 64
    return number - 1


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    value_node = cell.find(_NS + "v")
    raw = None if value_node is None else value_node.text
    if cell_type == "s" and raw is not None:
        return shared_strings[int(raw)]
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.iter(_NS + "t"))
    if cell_type == "b":
        return raw == "1"
    if raw is None:
        return None
    if cell_type in {"str", "e", "d"}:
        return raw
    try:
        numeric = float(raw)
        return int(numeric) if numeric.is_integer() else numeric
    except ValueError:
        return raw


def _worksheet_target(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationship_map = {
        relationship.attrib["Id"]: relationship.attrib["Target"]
        for relationship in relationships.findall(_REL_NS + "Relationship")
    }
    sheets = workbook.find(_NS + "sheets")
    if sheets is None:
        raise ValueError("Workbook contains no worksheets.")
    for sheet in sheets:
        if sheet.attrib.get("name") != sheet_name:
            continue
        relation_id = sheet.attrib.get(f"{{{_DOC_REL_NS}}}id")
        if relation_id not in relationship_map:
            raise ValueError(f"Worksheet relationship is missing for {sheet_name!r}.")
        target = relationship_map[relation_id].replace("\\", "/")
        if target.startswith("/"):
            return target.lstrip("/")
        return posixpath.normpath(posixpath.join("xl", target))
    raise ValueError(f"Required worksheet {sheet_name!r} is absent.")


def read_cached_worksheet(path: str | Path, sheet_name: str) -> tuple[pd.DataFrame, set[str]]:
    """Read cached OOXML values and return formula-bearing cell references.

    Formula evaluation is intentionally not attempted.  The reviewer workbooks
    contain cached values written by the spreadsheet application; those values
    are the auditable source ratings used by the original analysis.
    """

    path = Path(path)
    with zipfile.ZipFile(path, "r") as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(text.text or "" for text in item.iter(_NS + "t"))
                for item in shared_root.findall(_NS + "si")
            ]
        target = _worksheet_target(archive, sheet_name)
        worksheet = ET.fromstring(archive.read(target))
        rows_by_number: dict[int, dict[int, Any]] = {}
        formulas: set[str] = set()
        for row in worksheet.iter(_NS + "row"):
            row_number = int(row.attrib.get("r", len(rows_by_number) + 1))
            cells: dict[int, Any] = {}
            for cell in row.findall(_NS + "c"):
                reference = cell.attrib.get("r")
                if not reference:
                    raise ValueError(f"Cell without a reference in {path.name}.")
                cells[_column_index(reference)] = _cell_value(cell, shared_strings)
                if cell.find(_NS + "f") is not None:
                    formulas.add(reference)
            rows_by_number[row_number] = cells

    if 1 not in rows_by_number:
        raise ValueError(f"Worksheet {sheet_name!r} in {path.name} lacks a header row.")
    header_cells = rows_by_number[1]
    width = max(header_cells) + 1
    headers = [_normalise_blank(header_cells.get(index)).strip() for index in range(width)]
    if not all(headers) or len(headers) != len(set(headers)):
        raise ValueError(f"Worksheet {sheet_name!r} has blank or duplicate headers.")
    records: list[dict[str, Any]] = []
    for row_number in sorted(number for number in rows_by_number if number > 1):
        row = rows_by_number[row_number]
        record = {header: row.get(index) for index, header in enumerate(headers)}
        if any(_normalise_blank(value) for value in record.values()):
            records.append(record)
    return pd.DataFrame(records, columns=headers), formulas


def validate_public_workbook_container(path: str | Path) -> dict[str, Any]:
    """Require privacy-sanitized, deterministic public XLSX metadata."""

    path = Path(path)
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        private_properties = [name for name in names if name.startswith("docProps/")]
        nonfixed_timestamps = [
            info.filename for info in archive.infolist() if tuple(info.date_time) != FIXED_PUBLIC_XLSX_TIMESTAMP
        ]
    if private_properties:
        raise ValueError(f"Public workbook {path.name} retains private document properties: {private_properties}")
    if nonfixed_timestamps:
        raise ValueError(f"Public workbook {path.name} has non-deterministic ZIP timestamps: {nonfixed_timestamps[:5]}")
    return {
        "filename": path.name,
        "sha256": sha256_file(path),
        "doc_properties_removed": True,
        "all_zip_timestamps_fixed": True,
        "zip_members": len(names),
    }


def _require_columns(frame: pd.DataFrame, required: Iterable[str], label: str) -> None:
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} is missing required columns: {sorted(missing)}")


def _component_rollup(row: Mapping[str, Any]) -> str:
    labels = [_normalise_label(row[column]) for column in COMPONENT_RATING_COLUMNS]
    if "No" in labels:
        return "No"
    if "Borderline" in labels:
        return "Borderline"
    if "Uncertain" in labels:
        return "Uncertain"
    return "Yes"


def _rollup_exceptions(frame: pd.DataFrame) -> list[dict[str, str]]:
    exceptions: list[dict[str, str]] = []
    for record in frame.to_dict(orient="records"):
        expected = _component_rollup(record)
        observed = _normalise_label(record["complete_pathway_correct"])
        if observed != expected:
            exceptions.append(
                {
                    "validation_id": _normalise_label(record["validation_id"]),
                    "recorded_complete_pathway_correct": observed,
                    "component_rollup": expected,
                }
            )
    return exceptions


def _validate_primary_reviewers(
    expert_a: pd.DataFrame,
    expert_b: pd.DataFrame,
    formulas_a: set[str],
    formulas_b: set[str],
) -> dict[str, Any]:
    required = [*STATIC_COLUMNS, *RATING_COLUMNS, "error_category", "reviewer_comments"]
    _require_columns(expert_a, required, "Expert A workbook")
    _require_columns(expert_b, required, "Expert B workbook")
    if len(expert_a) != 115 or len(expert_b) != 115:
        raise ValueError(f"Expected 115 reviewer rows each; observed A={len(expert_a)}, B={len(expert_b)}.")

    ids_a = expert_a["validation_id"].map(_normalise_label)
    ids_b = expert_b["validation_id"].map(_normalise_label)
    if ids_a.duplicated().any() or ids_b.duplicated().any():
        raise ValueError("Reviewer validation IDs must be unique.")
    if not ids_a.equals(ids_b):
        raise ValueError("Expert A and Expert B validation IDs or row order differ.")

    for column in STATIC_COLUMNS:
        left = expert_a[column].map(_normalise_blank)
        right = expert_b[column].map(_normalise_blank)
        if not left.equals(right):
            differing = ids_a[left.ne(right)].tolist()[:10]
            raise ValueError(f"Expert workbook source field {column!r} differs for {differing}.")
    for reviewer_name, frame in [("Expert A", expert_a), ("Expert B", expert_b)]:
        for column in RATING_COLUMNS:
            labels = set(frame[column].map(_normalise_label))
            if not labels <= ALLOWED_SOURCE_LABELS:
                raise ValueError(f"{reviewer_name} has invalid labels in {column}: {sorted(labels)}")

    exceptions_a = _rollup_exceptions(expert_a)
    exceptions_b = _rollup_exceptions(expert_b)
    formula_rows_a = sum(reference.startswith("L") for reference in formulas_a)
    formula_rows_b = sum(reference.startswith("L") for reference in formulas_b)
    if formula_rows_a + len(exceptions_a) != 115 or formula_rows_b + len(exceptions_b) != 115:
        raise ValueError(
            "The complete-pathway formula coverage does not reconcile with the disclosed source roll-up exceptions."
        )
    return {
        "unique_validation_ids": 115,
        "expert_A_complete_pathway_formula_cells": formula_rows_a,
        "expert_B_complete_pathway_formula_cells": formula_rows_b,
        "complete_pathway_rollup_inconsistencies": {
            "Expert A": exceptions_a,
            "Expert B": exceptions_b,
        },
    }


def _agreement_table(expert_a: pd.DataFrame, expert_b: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dimension in RATING_COLUMNS:
        labels_a = expert_a[dimension].map(_normalise_label).tolist()
        labels_b = expert_b[dimension].map(_normalise_label).tolist()
        n = len(labels_a)
        raw = sum(left == right for left, right in zip(labels_a, labels_b)) / n
        categories = sorted(set(labels_a) | set(labels_b))
        counts_a = Counter(labels_a)
        counts_b = Counter(labels_b)
        chance_kappa = sum((counts_a[label] / n) * (counts_b[label] / n) for label in categories)
        if math.isclose(chance_kappa, 1.0):
            kappa = 1.0 if math.isclose(raw, 1.0) else math.nan
        else:
            kappa = (raw - chance_kappa) / (1.0 - chance_kappa)
        if len(categories) <= 1:
            ac1 = 1.0
        else:
            pooled = {label: (counts_a[label] + counts_b[label]) / (2.0 * n) for label in categories}
            chance_ac1 = sum(probability * (1.0 - probability) for probability in pooled.values()) / (
                len(categories) - 1
            )
            ac1 = (raw - chance_ac1) / (1.0 - chance_ac1) if not math.isclose(chance_ac1, 1.0) else 1.0
        rows.append(
            {
                "dimension": dimension,
                "n": n,
                "raw_agreement": float(raw),
                "cohen_kappa": float(kappa),
                "gwet_ac1": float(ac1),
                "disagreements": int(sum(left != right for left, right in zip(labels_a, labels_b))),
            }
        )
    return pd.DataFrame(rows)


def _required_adjudications(
    expert_a: pd.DataFrame, expert_b: pd.DataFrame
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], set[tuple[str, str]]]:
    direct_disagreements: set[tuple[str, str]] = set()
    nondefinitive: set[tuple[str, str]] = set()
    for row_a, row_b in zip(expert_a.to_dict(orient="records"), expert_b.to_dict(orient="records")):
        validation_id = _normalise_label(row_a["validation_id"])
        for dimension in RATING_COLUMNS:
            label_a = _normalise_label(row_a[dimension])
            label_b = _normalise_label(row_b[dimension])
            key = (validation_id, dimension)
            if label_a != label_b:
                direct_disagreements.add(key)
            if label_a in NONDEFINITIVE_LABELS or label_b in NONDEFINITIVE_LABELS:
                nondefinitive.add(key)
    return direct_disagreements, nondefinitive, direct_disagreements | nondefinitive


def _validate_third_expert(
    expert_a: pd.DataFrame,
    expert_b: pd.DataFrame,
    third: pd.DataFrame,
    direct: set[tuple[str, str]],
    nondefinitive: set[tuple[str, str]],
    required: set[tuple[str, str]],
) -> tuple[pd.DataFrame, dict[tuple[str, str], dict[str, Any]]]:
    required_columns = [
        "validation_id",
        "path_text",
        "pathway_template",
        "reviewer_comments_A",
        "reviewer_comments_B",
        "rating_dimension",
        "adjudicated_label",
        "adjudicator_rationale",
        *[f"{dimension}_A" for dimension in RATING_COLUMNS],
        *[f"{dimension}_B" for dimension in RATING_COLUMNS],
    ]
    _require_columns(third, required_columns, "Third-expert workbook")
    if len(third) != len(required):
        raise ValueError(f"Expected {len(required)} third-expert rows; observed {len(third)}.")

    a_by_id = {
        _normalise_label(record["validation_id"]): record for record in expert_a.to_dict(orient="records")
    }
    b_by_id = {
        _normalise_label(record["validation_id"]): record for record in expert_b.to_dict(orient="records")
    }
    seen: set[tuple[str, str]] = set()
    audit_rows: list[dict[str, Any]] = []
    adjudications: dict[tuple[str, str], dict[str, Any]] = {}
    for row in third.to_dict(orient="records"):
        validation_id = _normalise_label(row["validation_id"])
        dimension = _normalise_label(row["rating_dimension"])
        key = (validation_id, dimension)
        if validation_id not in a_by_id or dimension not in RATING_COLUMNS:
            raise ValueError(f"Invalid third-expert key: {key}")
        if key in seen:
            raise ValueError(f"Duplicate third-expert key: {key}")
        seen.add(key)
        if key not in required:
            raise ValueError(f"Unexpected third-expert adjudication: {key}")
        source_a = a_by_id[validation_id]
        source_b = b_by_id[validation_id]
        if _normalise_blank(row["path_text"]) != _normalise_blank(source_a["path_text"]):
            raise ValueError(f"Third-expert path text does not match source workbooks for {key}.")
        if _normalise_blank(row["pathway_template"]) != _normalise_blank(source_a["pathway_template"]):
            raise ValueError(f"Third-expert template does not match source workbooks for {key}.")
        if _normalise_blank(row["reviewer_comments_A"]) != _normalise_blank(source_a["reviewer_comments"]):
            raise ValueError(f"Third-expert Expert A comments do not match source workbook for {key}.")
        if _normalise_blank(row["reviewer_comments_B"]) != _normalise_blank(source_b["reviewer_comments"]):
            raise ValueError(f"Third-expert Expert B comments do not match source workbook for {key}.")
        label_a = _normalise_label(row[f"{dimension}_A"])
        label_b = _normalise_label(row[f"{dimension}_B"])
        if label_a != _normalise_label(source_a[dimension]) or label_b != _normalise_label(source_b[dimension]):
            raise ValueError(f"Third-expert source ratings do not match primary workbooks for {key}.")
        for other_dimension in RATING_COLUMNS:
            if other_dimension == dimension:
                continue
            if _normalise_label(row[f"{other_dimension}_A"]) or _normalise_label(row[f"{other_dimension}_B"]):
                raise ValueError(f"Third-expert row {key} contains ratings in an unrelated dimension.")
        adjudicated = _normalise_label(row["adjudicated_label"])
        rationale = _normalise_blank(row["adjudicator_rationale"]).strip()
        if adjudicated not in FINAL_LABELS:
            raise ValueError(f"Third-expert final label must be Yes/No for {key}; observed {adjudicated!r}.")
        if not rationale:
            raise ValueError(f"Third-expert rationale is blank for {key}.")
        if key in direct and key in nondefinitive:
            reason = "A_B_DISAGREEMENT_AND_NONDEFINITIVE_SOURCE"
        elif key in direct:
            reason = "A_B_DISAGREEMENT"
        else:
            reason = "NONDEFINITIVE_SOURCE_RATING"
        audit = {
            "validation_id": validation_id,
            "path_text": _normalise_blank(source_a["path_text"]),
            "pathway_template": _normalise_blank(source_a["pathway_template"]),
            "rating_dimension": dimension,
            "expert_A_label": label_a,
            "expert_B_label": label_b,
            "expert_A_comment": _normalise_blank(source_a["reviewer_comments"]),
            "expert_B_comment": _normalise_blank(source_b["reviewer_comments"]),
            "adjudication_reason": reason,
            "adjudicated_label": adjudicated,
            "adjudicator_rationale": rationale,
            "final_binary": 1 if adjudicated == "Yes" else 0,
            "source_match_verified": True,
        }
        audit_rows.append(audit)
        adjudications[key] = audit

    missing = required - seen
    extra = seen - required
    if missing or extra:
        raise ValueError(f"Third-expert coverage mismatch; missing={sorted(missing)}, extra={sorted(extra)}")
    audit_frame = pd.DataFrame(audit_rows).sort_values(
        ["validation_id", "rating_dimension"], kind="stable"
    ).reset_index(drop=True)
    return audit_frame, adjudications


def replay_reviewer_validation(
    expert_a_path: str | Path,
    expert_b_path: str | Path,
    third_expert_path: str | Path,
) -> ReviewerReplay:
    """Validate the three public workbooks and reconstruct every final rating."""

    workbook_qc = {
        "Expert A": validate_public_workbook_container(expert_a_path),
        "Expert B": validate_public_workbook_container(expert_b_path),
        "Third expert": validate_public_workbook_container(third_expert_path),
    }
    expert_a, formulas_a = read_cached_worksheet(expert_a_path, "Pathways")
    expert_b, formulas_b = read_cached_worksheet(expert_b_path, "Pathways")
    third, formulas_third = read_cached_worksheet(third_expert_path, "Sheet1")
    if formulas_third:
        raise ValueError("The third-expert adjudication workbook must contain final values rather than formulas.")
    primary_qc = _validate_primary_reviewers(expert_a, expert_b, formulas_a, formulas_b)
    agreement = _agreement_table(expert_a, expert_b)
    direct, nondefinitive, required = _required_adjudications(expert_a, expert_b)
    adjudication_audit, adjudications = _validate_third_expert(
        expert_a, expert_b, third, direct, nondefinitive, required
    )

    rating_rows: list[dict[str, Any]] = []
    reconstructed_rows: list[dict[str, Any]] = []
    for source_a, source_b in zip(expert_a.to_dict(orient="records"), expert_b.to_dict(orient="records")):
        validation_id = _normalise_label(source_a["validation_id"])
        reconstructed: dict[str, Any] = {"validation_id": validation_id}
        for dimension in RATING_COLUMNS:
            label_a = _normalise_label(source_a[dimension])
            label_b = _normalise_label(source_b[dimension])
            key = (validation_id, dimension)
            if key in required:
                final_label = adjudications[key]["adjudicated_label"]
                final_source = "Third-expert adjudication"
            else:
                if label_a != label_b or label_a not in FINAL_LABELS:
                    raise ValueError(f"Unadjudicated non-consensus rating at {key}.")
                final_label = label_a
                final_source = "Expert agreement"
            final_binary = 1 if final_label == "Yes" else 0
            reconstructed[dimension] = final_label
            reconstructed[f"{dimension}_source"] = final_source
            reconstructed[f"{dimension}_binary"] = final_binary
            rating_rows.append(
                {
                    "validation_id": validation_id,
                    "path_text": _normalise_blank(source_a["path_text"]),
                    "pathway_template": _normalise_blank(source_a["pathway_template"]),
                    "rating_dimension": dimension,
                    "expert_A_label": label_a,
                    "expert_B_label": label_b,
                    "expert_A_comment": _normalise_blank(source_a["reviewer_comments"]),
                    "expert_B_comment": _normalise_blank(source_b["reviewer_comments"]),
                    "A_equals_B": label_a == label_b,
                    "A_definitive": label_a in FINAL_LABELS,
                    "B_definitive": label_b in FINAL_LABELS,
                    "requires_third_expert": key in required,
                    "final_label": final_label,
                    "final_source": final_source,
                    "final_binary": final_binary,
                }
            )
        reconstructed_rows.append(reconstructed)

    rating_matrix = pd.DataFrame(rating_rows)
    reconstructed = pd.DataFrame(reconstructed_rows)
    third_label_counts = Counter(adjudication_audit["adjudicated_label"].tolist())
    qc: dict[str, Any] = {
        "reviewer_level_replay_passed": True,
        "workbook_container_qc": workbook_qc,
        **primary_qc,
        "rating_dimensions": len(RATING_COLUMNS),
        "total_A_B_rating_pairs": len(rating_matrix),
        "direct_A_B_disagreements": len(direct),
        "nondefinitive_source_rating_cases": len(nondefinitive),
        "required_third_expert_adjudications": len(required),
        "definitive_A_B_consensus_ratings": len(rating_matrix) - len(required),
        "third_expert_final_ratings": len(adjudication_audit),
        "third_expert_final_label_counts": {
            label: int(third_label_counts.get(label, 0)) for label in sorted(FINAL_LABELS)
        },
        "third_expert_source_rows_match_primary_workbooks": True,
        "third_expert_exact_coverage_verified": True,
        "all_reconstructed_final_labels_binary": bool(
            rating_matrix["final_label"].isin(FINAL_LABELS).all()
        ),
    }
    return ReviewerReplay(
        expert_a=expert_a,
        expert_b=expert_b,
        third_expert=third,
        agreement=agreement,
        rating_matrix_long=rating_matrix,
        adjudication_audit=adjudication_audit,
        reconstructed_ratings=reconstructed,
        qc=qc,
    )
