from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Mention:
    """A PubTator entity mention linked to one normalized concept identifier."""

    doc_id: str
    start: int
    end: int
    text: str
    entity_type: str
    entity_id: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid mention offsets: {self.start}, {self.end}")


@dataclass(frozen=True)
class Relation:
    """A document-level relation. ``subject`` is optional BioREDirect directionality."""

    doc_id: str
    label: str
    arg1: str
    arg2: str
    novelty: str | None = None
    subject: str | None = None
    score: float | None = None

    def unordered_pair(self) -> tuple[str, str]:
        return tuple(sorted((self.arg1, self.arg2)))


@dataclass
class Document:
    doc_id: str
    title: str = ""
    abstract: str = ""
    mentions: list[Mention] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        if self.title and self.abstract:
            return f"{self.title}\n{self.abstract}"
        return self.title or self.abstract

    def concept_ids(self) -> list[str]:
        return sorted({m.entity_id for m in self.mentions if m.entity_id and m.entity_id != "-"})

    def mentions_for(self, entity_id: str) -> list[Mention]:
        return sorted(
            (m for m in self.mentions if m.entity_id == entity_id),
            key=lambda m: (m.start, m.end, m.text),
        )

    def entity_type_for(self, entity_id: str) -> str | None:
        types = [m.entity_type for m in self.mentions if m.entity_id == entity_id]
        if not types:
            return None
        # Prefer the modal type and use lexical order as a deterministic tie-break.
        counts: dict[str, int] = {}
        for value in types:
            counts[value] = counts.get(value, 0) + 1
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


@dataclass(frozen=True)
class CandidateExample:
    doc_id: str
    id1: str
    id2: str
    type1: str
    type2: str
    context: str
    same_sentence: bool
    char_distance: int
    label: str
    direction: str
    subject: str | None = None

    @property
    def pair_key(self) -> tuple[str, str]:
        return tuple(sorted((self.id1, self.id2)))

    @property
    def type_pair(self) -> tuple[str, str]:
        return tuple(sorted((self.type1, self.type2)))


@dataclass(frozen=True)
class Prediction:
    doc_id: str
    id1: str
    id2: str
    label: str
    subject: str | None = None
    score: float | None = None
    system: str = ""
    mode: str = ""

    @property
    def pair_key(self) -> tuple[str, str]:
        return tuple(sorted((self.id1, self.id2)))


def flatten_relations(documents: Iterable[Document]) -> list[Relation]:
    return [relation for document in documents for relation in document.relations]
