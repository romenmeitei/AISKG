from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from .io_pubtator import normalize_relation_label
from .models import CandidateExample, Document, Mention, Relation


# Entity pairs used by the official BioREDirect converter for the BioRED task.
OFFICIAL_BIORED_ENTITY_PAIRS: frozenset[tuple[str, str]] = frozenset(
    tuple(sorted(pair))
    for pair in [
        ("ChemicalEntity", "ChemicalEntity"),
        ("ChemicalEntity", "DiseaseOrPhenotypicFeature"),
        ("ChemicalEntity", "GeneOrGeneProduct"),
        ("ChemicalEntity", "SequenceVariant"),
        ("DiseaseOrPhenotypicFeature", "GeneOrGeneProduct"),
        ("DiseaseOrPhenotypicFeature", "SequenceVariant"),
        ("GeneOrGeneProduct", "GeneOrGeneProduct"),
        ("SequenceVariant", "SequenceVariant"),
    ]
)

RELATION_LABELS = (
    "Association",
    "Bind",
    "Comparison",
    "Conversion",
    "Cotreatment",
    "Drug_Interaction",
    "Negative_Correlation",
    "Positive_Correlation",
)


@dataclass(frozen=True)
class SentenceSpan:
    start: int
    end: int
    text: str


def sentence_spans(text: str) -> list[SentenceSpan]:
    """Return deterministic offset-preserving sentence spans.

    PubTator concatenates title and abstract with one newline, which is treated as a
    hard boundary. Within each section, punctuation followed by likely sentence-start
    text defines a boundary. The implementation is intentionally dependency-free so
    the same offsets are obtained in Colab and local replay.
    """

    if not text:
        return []

    segments: list[tuple[int, int, str]] = []
    cursor = 0
    for match in re.finditer(r"\n+", text):
        if match.start() > cursor:
            segments.append((cursor, match.start(), text[cursor:match.start()]))
        cursor = match.end()
    if cursor < len(text):
        segments.append((cursor, len(text), text[cursor:]))

    spans: list[SentenceSpan] = []
    # Avoid splitting after common abbreviations and decimal points by requiring a
    # likely sentence-start token after whitespace.
    boundary = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\[])" )
    for base_start, _, segment in segments:
        local_cursor = 0
        for match in boundary.finditer(segment):
            local_end = match.start()
            if segment[local_cursor:local_end].strip():
                spans.append(
                    SentenceSpan(
                        base_start + local_cursor,
                        base_start + local_end,
                        segment[local_cursor:local_end],
                    )
                )
            local_cursor = match.end()
        if local_cursor < len(segment) and segment[local_cursor:].strip():
            spans.append(
                SentenceSpan(
                    base_start + local_cursor,
                    base_start + len(segment),
                    segment[local_cursor:],
                )
            )
    return spans or [SentenceSpan(0, len(text), text)]


def _span_index_for_mention(mention: Mention, spans: list[SentenceSpan]) -> int | None:
    for index, span in enumerate(spans):
        if span.start <= mention.start and mention.end <= span.end:
            return index
    # PubTator offsets can occasionally differ by one character around the title/
    # abstract separator. Use maximal overlap as a transparent fallback.
    best_index: int | None = None
    best_overlap = 0
    for index, span in enumerate(spans):
        overlap = max(0, min(mention.end, span.end) - max(mention.start, span.start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_index = index
    return best_index


def _closest_mentions(
    mentions1: list[Mention],
    mentions2: list[Mention],
    spans: list[SentenceSpan],
) -> tuple[Mention, Mention, bool, int, int, int]:
    best: tuple[tuple[int, int, int, int], Mention, Mention, bool, int, int] | None = None
    for m1 in mentions1:
        for m2 in mentions2:
            s1 = _span_index_for_mention(m1, spans)
            s2 = _span_index_for_mention(m2, spans)
            same = s1 is not None and s2 is not None and s1 == s2
            distance = max(0, max(m1.start, m2.start) - min(m1.end, m2.end))
            sentence_gap = 999 if s1 is None or s2 is None else abs(s1 - s2)
            key = (0 if same else 1, sentence_gap, distance, min(m1.start, m2.start))
            if best is None or key < best[0]:
                best = (key, m1, m2, same, s1 if s1 is not None else -1, s2 if s2 is not None else -1)
    if best is None:
        raise ValueError("Cannot select a mention pair from empty mention lists")
    _, m1, m2, same, s1, s2 = best
    distance = max(0, max(m1.start, m2.start) - min(m1.end, m2.end))
    return m1, m2, same, distance, s1, s2


def _insert_entity_markers(
    text: str,
    base_start: int,
    m1: Mention,
    m2: Mention,
) -> str:
    operations: list[tuple[int, str]] = []
    for mention, label in ((m1, "E1"), (m2, "E2")):
        local_start = max(0, mention.start - base_start)
        local_end = max(local_start, mention.end - base_start)
        local_end = min(local_end, len(text))
        local_start = min(local_start, local_end)
        operations.append((local_end, f"[/{label}]"))
        operations.append((local_start, f"[{label}:{mention.entity_type}]"))
    marked = text
    # Closing tags should be inserted before opening tags at an identical position.
    for position, token in sorted(operations, key=lambda x: (x[0], x[1].startswith("[/")), reverse=True):
        marked = marked[:position] + token + marked[position:]
    return " ".join(marked.split())


def _relation_by_pair(document: Document) -> dict[tuple[str, str], Relation]:
    grouped: dict[tuple[str, str], list[Relation]] = {}
    for relation in document.relations:
        key = tuple(sorted((relation.arg1, relation.arg2)))
        grouped.setdefault(key, []).append(relation)
    result: dict[tuple[str, str], Relation] = {}
    for key, relations in grouped.items():
        # BioRED normally has one relation label per concept pair. Preserve a
        # deterministic first label and expose multi-label conflicts in metadata/QC.
        result[key] = sorted(relations, key=lambda r: (normalize_relation_label(r.label), r.arg1, r.arg2))[0]
    return result


def _direction_target(relation: Relation | None, id1: str, id2: str) -> tuple[str, str | None]:
    if relation is None or not relation.subject:
        return "No_Direct", None
    if relation.subject == id1:
        return "Left_to_Right", id1
    if relation.subject == id2:
        return "Right_to_Left", id2
    return "No_Direct", None


def build_candidate_examples(
    documents: Iterable[Document],
    *,
    mode: str,
    max_context_chars: int = 1800,
    allowed_entity_pairs: frozenset[tuple[str, str]] = OFFICIAL_BIORED_ENTITY_PAIRS,
) -> list[CandidateExample]:
    """Generate gold-entity relation candidates.

    ``sentence_local`` includes only entity pairs with at least one co-sentential
    mention pair. ``full_document`` includes all official BioRED entity-type pairs and
    uses the shortest sentence span connecting their closest mentions.
    """

    if mode not in {"sentence_local", "full_document"}:
        raise ValueError("mode must be 'sentence_local' or 'full_document'")

    examples: list[CandidateExample] = []
    for document in documents:
        text = document.text
        spans = sentence_spans(text)
        relations = _relation_by_pair(document)
        concept_ids = document.concept_ids()
        for id1, id2 in combinations(concept_ids, 2):
            type1 = document.entity_type_for(id1)
            type2 = document.entity_type_for(id2)
            if not type1 or not type2:
                continue
            if tuple(sorted((type1, type2))) not in allowed_entity_pairs:
                continue
            mentions1 = document.mentions_for(id1)
            mentions2 = document.mentions_for(id2)
            if not mentions1 or not mentions2:
                continue
            m1, m2, same_sentence, distance, s1, s2 = _closest_mentions(mentions1, mentions2, spans)
            if mode == "sentence_local" and not same_sentence:
                continue

            if same_sentence and s1 >= 0:
                context_start = spans[s1].start
                context_end = spans[s1].end
            elif s1 >= 0 and s2 >= 0:
                lo, hi = sorted((s1, s2))
                context_start = spans[lo].start
                context_end = spans[hi].end
            else:
                context_start = max(0, min(m1.start, m2.start) - 400)
                context_end = min(len(text), max(m1.end, m2.end) + 400)

            if context_end - context_start > max_context_chars:
                midpoint = (min(m1.start, m2.start) + max(m1.end, m2.end)) // 2
                half = max_context_chars // 2
                context_start = max(0, midpoint - half)
                context_end = min(len(text), context_start + max_context_chars)
                context_start = max(0, context_end - max_context_chars)

            context = _insert_entity_markers(text[context_start:context_end], context_start, m1, m2)
            relation = relations.get(tuple(sorted((id1, id2))))
            label = normalize_relation_label(relation.label) if relation else "None"
            direction, subject = _direction_target(relation, id1, id2)
            distance_bin = (
                "OVERLAP" if distance == 0 else
                "D1_20" if distance <= 20 else
                "D21_80" if distance <= 80 else
                "D81_250" if distance <= 250 else
                "D251_PLUS"
            )
            metadata_prefix = (
                f"TYPEPAIR_{type1}__{type2} "
                f"SAME_SENTENCE_{int(same_sentence)} DISTANCE_{distance_bin} "
            )
            examples.append(
                CandidateExample(
                    doc_id=document.doc_id,
                    id1=id1,
                    id2=id2,
                    type1=type1,
                    type2=type2,
                    context=metadata_prefix + context,
                    same_sentence=same_sentence,
                    char_distance=distance,
                    label=label,
                    direction=direction,
                    subject=subject,
                )
            )
    return sorted(examples, key=lambda e: (e.doc_id, e.id1, e.id2))


def candidate_universe(examples: Iterable[CandidateExample]) -> set[tuple[str, str, str]]:
    return {(e.doc_id, *e.pair_key) for e in examples}
