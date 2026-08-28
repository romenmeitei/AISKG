from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from .candidates import RELATION_LABELS
from .models import CandidateExample, Prediction


NONE_LABEL = "None"


def type_pair_key(example: CandidateExample) -> str:
    return "||".join(sorted((example.type1, example.type2)))


def _micro_f1_labels(gold: Sequence[str], pred: Sequence[str]) -> float:
    tp = sum(g == p and g != NONE_LABEL for g, p in zip(gold, pred))
    fp = sum(p != NONE_LABEL and p != g for g, p in zip(gold, pred))
    fn = sum(g != NONE_LABEL and p != g for g, p in zip(gold, pred))
    return 0.0 if 2 * tp + fp + fn == 0 else (2 * tp) / (2 * tp + fp + fn)


@dataclass
class DirectionMajorityModel:
    by_relation_typepair: dict[tuple[str, str], str]
    by_relation: dict[str, str]

    @classmethod
    def fit(cls, examples: Iterable[CandidateExample]) -> "DirectionMajorityModel":
        grouped: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        relation_grouped: dict[str, Counter[str]] = defaultdict(Counter)
        for example in examples:
            if example.label == NONE_LABEL:
                continue
            grouped[(example.label, type_pair_key(example))][example.direction] += 1
            relation_grouped[example.label][example.direction] += 1

        def select(counter: Counter[str]) -> str:
            if not counter:
                return "No_Direct"
            return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]

        return cls(
            by_relation_typepair={key: select(value) for key, value in grouped.items()},
            by_relation={key: select(value) for key, value in relation_grouped.items()},
        )

    def predict(self, example: CandidateExample, label: str) -> tuple[str, str | None]:
        direction = self.by_relation_typepair.get(
            (label, type_pair_key(example)),
            self.by_relation.get(label, "No_Direct"),
        )
        if direction == "Left_to_Right":
            return direction, example.id1
        if direction == "Right_to_Left":
            return direction, example.id2
        return "No_Direct", None


class TypePairMajority:
    """Leakage-controlled type-pair baseline trained only on the training split."""

    def __init__(self) -> None:
        self.positive_label: dict[str, str] = {}
        self.positive_rate: dict[str, float] = {}
        self.threshold: float = 0.5
        self.direction_model: DirectionMajorityModel | None = None

    def fit(self, examples: Sequence[CandidateExample]) -> "TypePairMajority":
        counts: dict[str, Counter[str]] = defaultdict(Counter)
        for example in examples:
            counts[type_pair_key(example)][example.label] += 1
        for pair, counter in counts.items():
            total = sum(counter.values())
            positives = [(label, count) for label, count in counter.items() if label != NONE_LABEL]
            if not positives or total == 0:
                continue
            label, count = sorted(positives, key=lambda x: (-x[1], x[0]))[0]
            self.positive_label[pair] = label
            self.positive_rate[pair] = count / total
        self.direction_model = DirectionMajorityModel.fit(examples)
        return self

    def _predict_labels(self, examples: Sequence[CandidateExample], threshold: float) -> list[str]:
        result: list[str] = []
        for example in examples:
            pair = type_pair_key(example)
            label = self.positive_label.get(pair, NONE_LABEL)
            rate = self.positive_rate.get(pair, 0.0)
            result.append(label if label != NONE_LABEL and rate >= threshold else NONE_LABEL)
        return result

    def tune(self, dev_examples: Sequence[CandidateExample]) -> float:
        best = (-1.0, 1.0)
        for threshold in np.linspace(0.01, 0.80, 80):
            labels = self._predict_labels(dev_examples, float(threshold))
            score = _micro_f1_labels([e.label for e in dev_examples], labels)
            candidate = (score, -float(threshold))
            if candidate > best:
                best = candidate
                self.threshold = float(threshold)
        return self.threshold

    def predict(self, examples: Sequence[CandidateExample], *, system: str, mode: str) -> list[Prediction]:
        labels = self._predict_labels(examples, self.threshold)
        output: list[Prediction] = []
        assert self.direction_model is not None
        for example, label in zip(examples, labels):
            if label == NONE_LABEL:
                continue
            _, subject = self.direction_model.predict(example, label)
            output.append(
                Prediction(
                    doc_id=example.doc_id,
                    id1=example.id1,
                    id2=example.id2,
                    label=label,
                    subject=subject,
                    score=self.positive_rate.get(type_pair_key(example), 0.0),
                    system=system,
                    mode=mode,
                )
            )
        return output


class RuleTransferAdapter:
    """Transparent AISKG-style trigger and ontology constraint transfer layer."""

    def __init__(self, rules: dict[str, list[str]]) -> None:
        self.rules = {
            label: [re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns]
            for label, patterns in rules.items()
        }
        self.allowed_by_pair: dict[str, set[str]] = defaultdict(set)
        self.prior: dict[tuple[str, str], float] = {}
        self.threshold: float = 1.0
        self.direction_model: DirectionMajorityModel | None = None

    @classmethod
    def from_json(cls, path: str | Path) -> "RuleTransferAdapter":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(payload["relation_patterns"])

    def fit(self, examples: Sequence[CandidateExample]) -> "RuleTransferAdapter":
        counts: dict[str, Counter[str]] = defaultdict(Counter)
        for example in examples:
            counts[type_pair_key(example)][example.label] += 1
        for pair, counter in counts.items():
            positive_labels = sorted(label for label in counter if label != NONE_LABEL)
            self.allowed_by_pair[pair].update(positive_labels)
            total_positive = sum(counter[label] for label in positive_labels)
            denominator = total_positive + 0.5 * max(1, len(positive_labels))
            for label in positive_labels:
                self.prior[(pair, label)] = (counter[label] + 0.5) / denominator
        self.direction_model = DirectionMajorityModel.fit(examples)
        return self

    def _score(self, example: CandidateExample, label: str) -> float:
        pair = type_pair_key(example)
        prior = self.prior.get((pair, label), 1e-6)
        score = math.log(prior + 1e-9)
        context = example.context
        hits = sum(1 for pattern in self.rules.get(label, []) if pattern.search(context))
        score += 2.25 * hits
        if example.same_sentence:
            score += 0.35
        if example.char_distance <= 80:
            score += 0.25
        elif example.char_distance > 250:
            score -= 0.20
        return score

    def _predict_labels(self, examples: Sequence[CandidateExample], threshold: float) -> tuple[list[str], list[float]]:
        labels: list[str] = []
        scores: list[float] = []
        for example in examples:
            pair = type_pair_key(example)
            allowed = sorted(self.allowed_by_pair.get(pair, set()))
            if not allowed:
                labels.append(NONE_LABEL)
                scores.append(float("-inf"))
                continue
            ranked = sorted(
                ((self._score(example, label), label) for label in allowed),
                key=lambda item: (-item[0], item[1]),
            )
            score, label = ranked[0]
            labels.append(label if score >= threshold else NONE_LABEL)
            scores.append(score)
        return labels, scores

    def tune(self, dev_examples: Sequence[CandidateExample]) -> float:
        observed_scores: list[float] = []
        _, scores = self._predict_labels(dev_examples, threshold=-1e9)
        observed_scores.extend(score for score in scores if np.isfinite(score))
        if not observed_scores:
            self.threshold = 1e9
            return self.threshold
        quantiles = np.quantile(observed_scores, np.linspace(0.02, 0.98, 97))
        candidates = sorted(set(float(v) for v in quantiles))
        best_score = -1.0
        best_threshold = candidates[-1]
        gold = [e.label for e in dev_examples]
        for threshold in candidates:
            labels, _ = self._predict_labels(dev_examples, threshold)
            score = _micro_f1_labels(gold, labels)
            if score > best_score or (score == best_score and threshold > best_threshold):
                best_score = score
                best_threshold = threshold
        self.threshold = best_threshold
        return self.threshold

    def predict(self, examples: Sequence[CandidateExample], *, system: str, mode: str) -> list[Prediction]:
        labels, scores = self._predict_labels(examples, self.threshold)
        assert self.direction_model is not None
        output: list[Prediction] = []
        for example, label, score in zip(examples, labels, scores):
            if label == NONE_LABEL:
                continue
            _, subject = self.direction_model.predict(example, label)
            # Logistic transformation gives a bounded ranking score; it is not a
            # calibrated probability and is explicitly labelled as such in outputs.
            bounded = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, score))))
            output.append(
                Prediction(
                    doc_id=example.doc_id,
                    id1=example.id1,
                    id2=example.id2,
                    label=label,
                    subject=subject,
                    score=bounded,
                    system=system,
                    mode=mode,
                )
            )
        return output


class ConstrainedTextClassifier:
    """TF-IDF/linear transfer model with AISKG-style type constraints.

    This model uses gold BioRED entities, training-split labels, a development-only
    decision threshold, and masks relation labels not observed for an entity-type pair
    in training. It is a new external transfer adapter, not the unchanged v3.1.2
    mushroom-domain extractor.
    """

    def __init__(self, *, seed: int = 20260826, max_features: int = 80000) -> None:
        self.seed = seed
        self.max_features = max_features
        self.vectorizer = None
        self.classifier = None
        self.classes_: list[str] = []
        self.allowed_by_pair: dict[str, set[str]] = defaultdict(set)
        self.threshold: float = 0.5
        self.direction_model: DirectionMajorityModel | None = None

    def _downsample(self, examples: Sequence[CandidateExample], max_negative_ratio: int = 6) -> list[CandidateExample]:
        positives = [e for e in examples if e.label != NONE_LABEL]
        negatives = [e for e in examples if e.label == NONE_LABEL]
        if not positives:
            raise ValueError("The training split contains no positive BioRED relations")
        max_negatives = max_negative_ratio * len(positives)
        if len(negatives) <= max_negatives:
            return list(examples)
        rng = np.random.default_rng(self.seed)
        indices = np.sort(rng.choice(len(negatives), size=max_negatives, replace=False))
        sampled = [negatives[int(i)] for i in indices]
        return sorted(positives + sampled, key=lambda e: (e.doc_id, e.id1, e.id2))

    def fit(self, examples: Sequence[CandidateExample]) -> "ConstrainedTextClassifier":
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import SGDClassifier

        for example in examples:
            if example.label != NONE_LABEL:
                self.allowed_by_pair[type_pair_key(example)].add(example.label)
        training = self._downsample(examples)
        texts = [e.context for e in training]
        labels = [e.label for e in training]
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.995,
            max_features=self.max_features,
            sublinear_tf=True,
            strip_accents="unicode",
            token_pattern=r"(?u)\b[\w\-\[\]:/]+\b",
        )
        matrix = self.vectorizer.fit_transform(texts)
        self.classifier = SGDClassifier(
            loss="log_loss",
            penalty="elasticnet",
            alpha=1e-5,
            l1_ratio=0.05,
            class_weight="balanced",
            max_iter=2500,
            tol=1e-4,
            random_state=self.seed,
            average=True,
        )
        self.classifier.fit(matrix, labels)
        self.classes_ = [str(value) for value in self.classifier.classes_]
        self.direction_model = DirectionMajorityModel.fit(examples)
        return self

    def _masked_probabilities(self, examples: Sequence[CandidateExample]) -> np.ndarray:
        if self.vectorizer is None or self.classifier is None:
            raise RuntimeError("Model must be fitted before prediction")
        matrix = self.vectorizer.transform([e.context for e in examples])
        probabilities = np.asarray(self.classifier.predict_proba(matrix), dtype=float)
        class_to_index = {label: index for index, label in enumerate(self.classes_)}
        for row_index, example in enumerate(examples):
            allowed = set(self.allowed_by_pair.get(type_pair_key(example), set())) | {NONE_LABEL}
            for label, column_index in class_to_index.items():
                if label not in allowed:
                    probabilities[row_index, column_index] = 0.0
            total = probabilities[row_index].sum()
            if total <= 0:
                if NONE_LABEL in class_to_index:
                    probabilities[row_index, class_to_index[NONE_LABEL]] = 1.0
                else:
                    probabilities[row_index] = 1.0 / probabilities.shape[1]
            else:
                probabilities[row_index] /= total
        return probabilities

    def _predict_labels(self, examples: Sequence[CandidateExample], threshold: float) -> tuple[list[str], list[float]]:
        if not examples:
            return [], []
        probabilities = self._masked_probabilities(examples)
        class_to_index = {label: index for index, label in enumerate(self.classes_)}
        positive_indices = [index for label, index in class_to_index.items() if label != NONE_LABEL]
        output: list[str] = []
        scores: list[float] = []
        for row in probabilities:
            if not positive_indices:
                output.append(NONE_LABEL)
                scores.append(0.0)
                continue
            best_index = max(positive_indices, key=lambda idx: (row[idx], self.classes_[idx]))
            best_label = self.classes_[best_index]
            best_score = float(row[best_index])
            none_score = float(row[class_to_index[NONE_LABEL]]) if NONE_LABEL in class_to_index else 0.0
            if best_score >= threshold and best_score >= none_score:
                output.append(best_label)
            else:
                output.append(NONE_LABEL)
            scores.append(best_score)
        return output, scores

    def tune(self, dev_examples: Sequence[CandidateExample]) -> float:
        gold = [e.label for e in dev_examples]
        best_score = -1.0
        best_threshold = 0.5
        for threshold in np.linspace(0.05, 0.95, 91):
            labels, _ = self._predict_labels(dev_examples, float(threshold))
            score = _micro_f1_labels(gold, labels)
            if score > best_score or (score == best_score and threshold > best_threshold):
                best_score = score
                best_threshold = float(threshold)
        self.threshold = best_threshold
        return self.threshold

    def predict(self, examples: Sequence[CandidateExample], *, system: str, mode: str) -> list[Prediction]:
        labels, scores = self._predict_labels(examples, self.threshold)
        assert self.direction_model is not None
        output: list[Prediction] = []
        for example, label, score in zip(examples, labels, scores):
            if label == NONE_LABEL:
                continue
            _, subject = self.direction_model.predict(example, label)
            output.append(
                Prediction(
                    doc_id=example.doc_id,
                    id1=example.id1,
                    id2=example.id2,
                    label=label,
                    subject=subject,
                    score=score,
                    system=system,
                    mode=mode,
                )
            )
        return output


def save_thresholds(path: str | Path, payload: dict[str, float | int | str]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
