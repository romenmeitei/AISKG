from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .models import Document, Mention, Prediction, Relation


RELATION_ALIASES = {
    "binding": "Bind",
    "bind": "Bind",
    "association": "Association",
    "comparison": "Comparison",
    "conversion": "Conversion",
    "cotreatment": "Cotreatment",
    "co_treatment": "Cotreatment",
    "druginteraction": "Drug_Interaction",
    "drug_interaction": "Drug_Interaction",
    "negativecorrelation": "Negative_Correlation",
    "negative_correlation": "Negative_Correlation",
    "positivecorrelation": "Positive_Correlation",
    "positive_correlation": "Positive_Correlation",
    "none": "None",
}

ENTITY_TYPE_ALIASES = {
    "chemical": "ChemicalEntity",
    "chemicalentity": "ChemicalEntity",
    "disease": "DiseaseOrPhenotypicFeature",
    "diseaseorphentypicfeature": "DiseaseOrPhenotypicFeature",
    "diseaseorphenotypicfeature": "DiseaseOrPhenotypicFeature",
    "gene": "GeneOrGeneProduct",
    "geneorgeneproduct": "GeneOrGeneProduct",
    "sequencevariant": "SequenceVariant",
    "organismtaxon": "OrganismTaxon",
    "cellline": "CellLine",
}


def normalize_relation_label(value: str | None) -> str:
    if value is None:
        return "None"
    raw = str(value).split("|", 1)[0].strip()
    key = re.sub(r"[^a-z0-9_]", "", raw.lower().replace("-", "_"))
    return RELATION_ALIASES.get(key, raw)


def normalize_entity_type(value: str) -> str:
    raw = re.sub(r"\s*\(.*?\)\s*$", "", str(value)).strip()
    key = re.sub(r"[^a-z0-9]", "", raw.lower())
    return ENTITY_TYPE_ALIASES.get(key, raw)


def _split_ids(raw: str) -> list[str]:
    values: list[str] = []
    for item in re.split(r"[,;]", raw):
        item = item.strip().strip("*")
        if not item or item == "-":
            continue
        values.append(item)
    return values or ([raw.strip()] if raw.strip() and raw.strip() != "-" else [])


def _as_float_from_pipe(value: str | None) -> float | None:
    if value is None or "|" not in value:
        return None
    tail = value.rsplit("|", 1)[-1]
    try:
        return float(tail)
    except ValueError:
        return None


def parse_pubtator(path: str | Path, *, strict: bool = True) -> list[Document]:
    """Parse BioRED/BioREDirect PubTator text.

    Supported relation records include the canonical BioRED form::

        PMID<TAB>Relation<TAB>ID1<TAB>ID2<TAB>Novelty

    and BioREDirect direction records::

        PMID<TAB>ID1<TAB>ID2<TAB>Subject:ID1

    Scores appended with ``|score`` are retained when present.
    """

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    documents: list[Document] = []
    current: Document | None = None
    pending_relations: list[Relation] = []
    direction_by_pair: dict[tuple[str, str], str] = {}
    unparsed: list[tuple[int, str]] = []

    def ensure_document(doc_id: str) -> Document:
        nonlocal current
        if current is None:
            current = Document(doc_id=doc_id)
        elif current.doc_id != doc_id:
            # PubTator normally separates documents with a blank line. Be permissive
            # when a producer omits it, but flush the prior document deterministically.
            flush()
            current = Document(doc_id=doc_id)
        return current

    def flush() -> None:
        nonlocal current, pending_relations, direction_by_pair
        if current is None:
            return
        enriched: list[Relation] = []
        for relation in pending_relations:
            pair = tuple(sorted((relation.arg1, relation.arg2)))
            subject = direction_by_pair.get(pair)
            enriched.append(
                Relation(
                    doc_id=relation.doc_id,
                    label=relation.label,
                    arg1=relation.arg1,
                    arg2=relation.arg2,
                    novelty=relation.novelty,
                    subject=subject,
                    score=relation.score,
                )
            )
        current.relations.extend(enriched)
        if current.title or current.abstract or current.mentions or current.relations:
            documents.append(current)
        current = None
        pending_relations = []
        direction_by_pair = {}

    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\r\n")
            if not line.strip():
                flush()
                continue

            text_match = re.match(r"^([^|]+)\|([ta])\|(.*)$", line)
            if text_match:
                doc_id, section, text = text_match.groups()
                document = ensure_document(doc_id)
                if section == "t":
                    document.title = text
                else:
                    document.abstract = text
                continue

            columns = line.split("\t")
            if len(columns) < 4:
                unparsed.append((line_number, line))
                continue

            doc_id = columns[0].strip()
            document = ensure_document(doc_id)

            # Entity annotation: PMID, start, end, surface, type, normalized ID(s)
            if len(columns) >= 6 and columns[1].isdigit() and columns[2].isdigit():
                start, end = int(columns[1]), int(columns[2])
                surface = columns[3]
                entity_type = normalize_entity_type(columns[4])
                ids = _split_ids(columns[5])
                for entity_id in ids:
                    document.mentions.append(
                        Mention(
                            doc_id=doc_id,
                            start=start,
                            end=end,
                            text=surface,
                            entity_type=entity_type,
                            entity_id=entity_id,
                        )
                    )
                continue

            # BioREDirect direction record: PMID, ID1, ID2, Subject:ID
            if len(columns) == 4 and columns[3].split("|", 1)[0].startswith("Subject:"):
                id1, id2 = columns[1].strip(), columns[2].strip()
                subject = columns[3].split("|", 1)[0].split(":", 1)[1].strip()
                if id1 != "-" and id2 != "-" and subject:
                    direction_by_pair[tuple(sorted((id1, id2)))] = subject
                continue

            # Standard relation record. Scores may be embedded after |.
            if len(columns) in {4, 5} or (len(columns) > 5 and not columns[1].isdigit()):
                relation_label = normalize_relation_label(columns[1])
                arg1, arg2 = columns[2].strip(), columns[3].strip()
                if arg1 == "-" or arg2 == "-":
                    continue
                novelty = columns[4].split("|", 1)[0].strip() if len(columns) >= 5 else None
                pending_relations.append(
                    Relation(
                        doc_id=doc_id,
                        label=relation_label,
                        arg1=arg1,
                        arg2=arg2,
                        novelty=novelty,
                        score=_as_float_from_pipe(columns[1]),
                    )
                )
                continue

            unparsed.append((line_number, line))

    flush()

    if strict and unparsed:
        preview = "\n".join(f"line {n}: {line[:180]}" for n, line in unparsed[:10])
        raise ValueError(
            f"Could not parse {len(unparsed)} PubTator records from {path}. "
            f"First records:\n{preview}"
        )

    seen: set[str] = set()
    for document in documents:
        if document.doc_id in seen:
            raise ValueError(f"Duplicate PubTator document block: {document.doc_id}")
        seen.add(document.doc_id)
    return documents


def write_predictions_pubtator(
    source_pubtator: str | Path,
    predictions: Iterable[Prediction],
    output_path: str | Path,
) -> Path:
    """Copy text/entities from a source file and append predictions per document."""

    source_pubtator = Path(source_pubtator)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    by_doc: dict[str, list[Prediction]] = defaultdict(list)
    for prediction in predictions:
        if prediction.label != "None":
            by_doc[prediction.doc_id].append(prediction)

    documents = parse_pubtator(source_pubtator, strict=False)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for document in documents:
            if document.title:
                handle.write(f"{document.doc_id}|t|{document.title}\n")
            if document.abstract:
                handle.write(f"{document.doc_id}|a|{document.abstract}\n")
            # Preserve one row per mention-concept pair. This is valid PubTator input
            # for downstream audit and avoids silently merging normalized IDs.
            for mention in sorted(document.mentions, key=lambda x: (x.start, x.end, x.entity_id)):
                handle.write(
                    "\t".join(
                        [
                            document.doc_id,
                            str(mention.start),
                            str(mention.end),
                            mention.text,
                            mention.entity_type,
                            mention.entity_id,
                        ]
                    )
                    + "\n"
                )
            for prediction in sorted(
                by_doc.get(document.doc_id, []),
                key=lambda x: (x.id1, x.id2, x.label),
            ):
                relation_field = prediction.label
                if prediction.score is not None:
                    relation_field += f"|{prediction.score:.8f}"
                handle.write(
                    f"{document.doc_id}\t{relation_field}\t{prediction.id1}\t{prediction.id2}\tPredicted\n"
                )
                if prediction.subject:
                    score = prediction.score if prediction.score is not None else 1.0
                    handle.write(
                        f"{document.doc_id}\t{prediction.id1}\t{prediction.id2}"
                        f"\tSubject:{prediction.subject}|{score:.8f}\n"
                    )
            handle.write("\n")
    return output_path


def predictions_to_csv(predictions: Iterable[Prediction], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["doc_id", "id1", "id2", "relation", "subject", "score", "system", "mode"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in predictions:
            writer.writerow(
                {
                    "doc_id": item.doc_id,
                    "id1": item.id1,
                    "id2": item.id2,
                    "relation": item.label,
                    "subject": item.subject or "",
                    "score": "" if item.score is None else f"{item.score:.10g}",
                    "system": item.system,
                    "mode": item.mode,
                }
            )
    return path
