"""Upstream literature-to-semantic-extraction reproducibility pipeline.

This module is the canonical first-stage workflow for the mushroom-poisoning
semantic knowledge graph study. It has two operating modes:

1. MANUSCRIPT_SNAPSHOT (default): deterministic replay of the frozen,
   deduplicated corpus, frozen BERTopic assignments, expert topic curation,
   ontology-guided entity extraction, relation extraction, and edge
   aggregation. This mode reproduces the exact manuscript-facing files used by
   the separate post-extraction analysis pipeline.

2. LIVE_REFRESH (optional): fresh PubMed/Scopus/Web of Science retrieval,
   harmonization, deduplication, BERTopic fitting, expert-curation template
   generation, and refreshed semantic extraction. Live database results are
   expected to change over time and require API credentials and a human
   curation pass; they are not expected to reproduce the frozen manuscript
   counts byte-for-byte.

The default snapshot mode deliberately avoids live services, model downloads,
and non-deterministic topic retraining. It uses a frozen entity-bearing
sentence-boundary manifest from the original extraction environment so that
sentence-level entity and relation outputs remain stable across spaCy model
updates.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import platform
import re
import shutil
import sys
import time
import warnings
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PIPELINE_NAME = "Mushroom KG upstream literature-to-extraction pipeline"
PIPELINE_VERSION = "1.0.0"
DEFAULT_MODE = "MANUSCRIPT_SNAPSHOT"
FIXED_ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
RANDOM_SEED = 42

KEY_POST_EXTRACTION_FILES = [
    "01_document_sentence_entities.csv",
    "03_full_corpus_with_final_themes.csv",
    "04_explicit_sentence_relations.csv",
    "06_explicit_edges_aggregated.csv",
]

REFERENCE_FILES = [
    "03_full_corpus_with_final_themes.csv",
    "04_included_corpus_final_themes_only.csv",
    "05_final_theme_counts.csv",
    "06_final_theme_temporal_trends_long.csv",
    "07_final_theme_temporal_trends_wide.csv",
    "09_final_theme_relative_contribution.csv",
    "01_document_sentence_entities.csv",
    "04_explicit_sentence_relations.csv",
    "06_explicit_edges_aggregated.csv",
    "13_entity_year_counts.csv",
    "14_relation_year_counts.csv",
]

EXPECTED_SNAPSHOT_RESULTS = {
    "full_corpus_records": 2687,
    "included_records": 1868,
    "curated_themes": 9,
    "topic_ids_reviewed": 56,
    "entity_mentions": 8292,
    "unique_entities": 92,
    "documents_with_entities": 1521,
    "explicit_relation_instances": 1324,
    "aggregated_semantic_edges": 183,
    "support_ge_2_edges": 86,
    "support_ge_2_active_nodes": 40,
    "source_pubmed_records": 1095,
    "source_scopus_records": 1592,
    "year_start": 2000,
    "year_end": 2025,
}


# ---------------------------------------------------------------------------
# General utilities
# ---------------------------------------------------------------------------

def package_version(distribution: str) -> str:
    try:
        return importlib_metadata.version(distribution)
    except importlib_metadata.PackageNotFoundError:
        return "not-installed"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_title(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = text.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return re.sub(r"\s+", "", text)


def extract_year(value: Any) -> Optional[int]:
    if value is None or pd.isna(value):
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group()) if match else None


def safe_join(values: Iterable[Any]) -> str:
    cleaned = [clean_text(value) for value in values if clean_text(value)]
    return "; ".join(sorted(set(cleaned)))


def make_document_id(row: pd.Series) -> str:
    pmid = str(row.get("pmid_clean", "")).strip()
    doi = str(row.get("doi_clean", "")).strip()
    eid = str(row.get("eid", "")).strip()
    if pmid and pmid.lower() not in {"nan", "none", ""}:
        return f"PMID_{re.sub(r'[^0-9A-Za-z._-]', '', pmid)}"
    if doi and doi.lower() not in {"nan", "none", ""}:
        return "DOI_" + re.sub(r"[^0-9A-Za-z._-]", "_", doi)
    if eid and eid.lower() not in {"nan", "none", ""}:
        return "EID_" + re.sub(r"[^0-9A-Za-z._-]", "_", eid)
    index = int(getattr(row, "name", 0))
    return f"DOC_{index:06d}"


def ensure_directories(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def deterministic_zip(source_dir: Path, zip_path: Path, arc_prefix: str = "") -> None:
    """Create a deterministic ZIP with stable timestamps and sorted entries."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in source_dir.rglob("*") if p.is_file()):
            relative = path.relative_to(source_dir).as_posix()
            arcname = f"{arc_prefix.rstrip('/')}/{relative}" if arc_prefix else relative
            info = zipfile.ZipInfo(arcname, date_time=FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def write_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def normalized_dataframe_digest(df: pd.DataFrame) -> str:
    """Hash dataframe content independent of CSV line endings."""
    normalized = df.copy()
    for column in normalized.columns:
        normalized[column] = normalized[column].map(lambda value: "<NA>" if pd.isna(value) else str(value))
    payload = normalized.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return sha256_bytes(payload)


def compare_dataframes_exact(generated: Path, reference: Path) -> Dict[str, Any]:
    generated_bytes = generated.read_bytes()
    reference_bytes = reference.read_bytes()
    result: Dict[str, Any] = {
        "file": generated.name,
        "generated_sha256": sha256_bytes(generated_bytes),
        "reference_sha256": sha256_bytes(reference_bytes),
        "byte_identical": generated_bytes == reference_bytes,
        "generated_bytes": len(generated_bytes),
        "reference_bytes": len(reference_bytes),
    }
    if generated.suffix.lower() == ".csv" and reference.suffix.lower() == ".csv":
        left = pd.read_csv(generated, low_memory=False)
        right = pd.read_csv(reference, low_memory=False)
        result["generated_rows"] = len(left)
        result["reference_rows"] = len(right)
        result["generated_columns"] = len(left.columns)
        result["reference_columns"] = len(right.columns)
        same_columns = left.columns.tolist() == right.columns.tolist()
        result["same_columns"] = same_columns
        if same_columns and left.shape == right.shape:
            all_equal = True
            mismatches = 0
            for column in left.columns:
                a = left[column].fillna("<NA>").astype(str).reset_index(drop=True)
                b = right[column].fillna("<NA>").astype(str).reset_index(drop=True)
                n = int((a != b).sum())
                mismatches += n
                if n:
                    all_equal = False
            result["cell_identical"] = all_equal
            result["cell_mismatches"] = mismatches
        else:
            result["cell_identical"] = False
            result["cell_mismatches"] = None
    result["status"] = "PASS" if result.get("byte_identical") else (
        "PASS_CONTENT" if result.get("cell_identical") else "FAIL"
    )
    return result


def verify_input_checksums(input_root: Path) -> pd.DataFrame:
    manifest_path = input_root / "input_checksums.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing checksum manifest: {manifest_path}")
    manifest = pd.read_csv(manifest_path)
    rows: List[Dict[str, Any]] = []
    for entry in manifest.itertuples(index=False):
        relative = str(entry.file)
        path = input_root / relative
        if not path.exists():
            raise FileNotFoundError(f"Required input file is missing: {relative}")
        actual_hash = sha256_file(path)
        actual_bytes = path.stat().st_size
        expected_hash = str(entry.sha256)
        expected_bytes = int(entry.bytes)
        status = "PASS" if actual_hash == expected_hash and actual_bytes == expected_bytes else "FAIL"
        rows.append({
            "file": relative,
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
            "expected_bytes": expected_bytes,
            "actual_bytes": actual_bytes,
            "status": status,
        })
        if status != "PASS":
            raise ValueError(f"Checksum or size mismatch for {relative}")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Expert topic consolidation
# ---------------------------------------------------------------------------

def assign_final_theme(row: pd.Series) -> str:
    """Reproduce the manuscript's expert-guided theme consolidation rules."""
    label = str(row.get("expert_label", "")).lower()
    decision = str(row.get("include_exclude", "")).upper()

    if decision == "EXCLUDE":
        return "Excluded / non-core topic"

    if "amanita" in label or "amatoxin" in label or "amanitin" in label:
        if "liver" in label or "hepato" in label or "failure" in label:
            return "Amatoxin-induced hepatotoxicity and liver failure"
        return "Amanita poisoning and amatoxin intoxication"

    if "liver" in label or "hepatic" in label or "hepatotoxic" in label:
        return "Amatoxin-induced hepatotoxicity and liver failure"
    if "clinical" in label or "management" in label or "emergency" in label or "supportive" in label:
        return "Clinical poisoning management and supportive care"
    if "diagnosis" in label or "diagnostic" in label:
        return "Diagnosis, biomarkers, and clinical recognition"
    if "toxin detection" in label or "analytical" in label or "lc-ms" in label or "mass spectrometry" in label:
        return "Toxin detection and analytical toxicology"
    if "taxonomy" in label or "identification" in label or "species" in label or "barcoding" in label:
        return "Poisonous mushroom identification and taxonomy"
    if "epidemiology" in label or "outbreak" in label or "surveillance" in label:
        return "Epidemiology, outbreaks, and surveillance"
    if "renal" in label or "kidney" in label or "nephro" in label or "orellanine" in label or "cortinarius" in label:
        return "Renal and extrahepatic toxicity"
    if "neurolog" in label or "muscimol" in label or "ibotenic" in label or "muscarine" in label:
        return "Neurotoxic and cholinergic mushroom poisoning"
    if "ai" in label or "machine" in label or "deep learning" in label or "computational" in label or "image" in label:
        return "AI-assisted mushroom identification and computational classification"
    if "public health" in label or "prevention" in label or "awareness" in label:
        return "Public health prevention and risk communication"
    if "experimental" in label or "animal" in label or "model" in label:
        return "Experimental toxicology and translational models"
    if "therapy" in label or "treatment" in label or "n-acetylcysteine" in label or "silibinin" in label:
        return "Therapeutic strategies and antidotal interventions"
    if decision == "PARTIAL":
        return "Partially relevant mushroom-toxicology topic"
    return "Other mushroom-poisoning research themes"


def build_topic_summary(expert_df: pd.DataFrame) -> pd.DataFrame:
    required = {"topic_id", "top_words", "expert_label", "include_exclude", "comment"}
    missing = required - set(expert_df.columns)
    if missing:
        raise ValueError(f"Annotated expert topic file is missing columns: {sorted(missing)}")
    summary = (
        expert_df.groupby("topic_id")
        .agg({
            "top_words": "first",
            "expert_label": "first",
            "include_exclude": "first",
            "comment": "first",
        })
        .reset_index()
    )
    summary["topic_id"] = summary["topic_id"].astype(int)
    # All representative documents for a topic must carry identical decisions.
    for column in ["expert_label", "include_exclude", "comment"]:
        counts = expert_df.groupby("topic_id")[column].nunique(dropna=False)
        if (counts > 1).any():
            bad = counts[counts > 1].index.tolist()
            raise ValueError(f"Inconsistent {column} values within topic IDs: {bad}")
    summary["final_theme"] = summary.apply(assign_final_theme, axis=1)
    return summary


def run_theme_consolidation(
    corpus_path: Path,
    expert_path: Path,
    tables_dir: Path,
    figures_dir: Optional[Path] = None,
) -> Dict[str, pd.DataFrame]:
    """Apply expert topic curation and generate the frozen thematic outputs."""
    corpus = pd.read_csv(corpus_path, low_memory=False)
    expert = pd.read_csv(expert_path, low_memory=False)
    corpus.columns = corpus.columns.str.strip()
    expert.columns = expert.columns.str.strip()

    if "topic_refined" in corpus.columns:
        topic_col = "topic_refined"
    elif "topic_initial" in corpus.columns:
        topic_col = "topic_initial"
    else:
        raise ValueError("Corpus must contain topic_refined or topic_initial.")

    corpus[topic_col] = corpus[topic_col].astype(int)
    summary = build_topic_summary(expert)

    topic_ids = set(corpus[topic_col].dropna().astype(int).unique())
    reviewed_ids = set(summary["topic_id"].astype(int))
    missing_reviews = sorted(topic_ids - reviewed_ids)
    # BERTopic may retain the outlier label -1 after reduction. Treat only this
    # special label as an excluded, non-core topic so that a live refresh does
    # not fail merely because no representative-topic row exists for outliers.
    if missing_reviews == [-1]:
        outlier_row = pd.DataFrame([{
            "topic_id": -1,
            "top_words": "",
            "expert_label": "BERTopic outliers / unassigned records",
            "include_exclude": "EXCLUDE",
            "comment": "Automatically excluded outlier topic in live refresh.",
            "final_theme": "Excluded / non-core topic",
        }])
        summary = pd.concat([summary, outlier_row], ignore_index=True)
        reviewed_ids.add(-1)
        missing_reviews = []
    if missing_reviews:
        raise ValueError(f"Topic IDs lack expert review: {missing_reviews}")

    theme_map = dict(zip(summary["topic_id"], summary["final_theme"]))
    decision_map = dict(zip(summary["topic_id"], summary["include_exclude"]))
    label_map = dict(zip(summary["topic_id"], summary["expert_label"]))

    full = corpus.copy()
    full["expert_label"] = full[topic_col].map(label_map)
    full["include_exclude"] = full[topic_col].map(decision_map)
    full["final_theme"] = full[topic_col].map(theme_map)
    full["final_theme"] = full["final_theme"].fillna("Unmapped topic")
    full["include_exclude"] = full["include_exclude"].fillna("UNMAPPED")

    included = full[
        full["include_exclude"].astype(str).str.upper().isin(["INCLUDE", "PARTIAL"])
    ].copy()
    included = included[included["final_theme"] != "Excluded / non-core topic"].copy()

    theme_counts = included["final_theme"].value_counts().reset_index()
    theme_counts.columns = ["final_theme", "count"]
    theme_counts["percent"] = (theme_counts["count"] / theme_counts["count"].sum() * 100).round(2)

    included["year"] = pd.to_numeric(included["year"], errors="coerce")
    included = included.dropna(subset=["year"])
    included["year"] = included["year"].astype(int)
    trend_long = included.groupby(["year", "final_theme"]).size().reset_index(name="count")
    trend_wide = trend_long.pivot(index="year", columns="final_theme", values="count").fillna(0)
    trend_smooth = trend_wide[theme_counts.head(6)["final_theme"].tolist()].rolling(
        window=3, center=True, min_periods=1
    ).mean()
    trend_pct = trend_wide.div(trend_wide.sum(axis=1), axis=0).fillna(0) * 100

    from scipy.stats import linregress

    trend_stats: List[Dict[str, Any]] = []
    growth_rows: List[Dict[str, Any]] = []
    for theme in trend_wide.columns:
        x = trend_wide.index.to_numpy(dtype=float)
        y = trend_wide[theme].to_numpy(dtype=float)
        if len(x) >= 3 and np.sum(y) > 0:
            slope, intercept, r_value, p_value, std_err = linregress(x, y)
            r_squared = r_value ** 2
        else:
            slope = intercept = r_squared = p_value = std_err = np.nan
        trend_stats.append({
            "final_theme": theme,
            "slope_publications_per_year": slope,
            "r_squared": r_squared,
            "p_value": p_value,
            "std_err": std_err,
        })
        start_year = int(trend_wide.index.min())
        end_year = int(trend_wide.index.max())
        start_count = trend_wide.loc[start_year, theme]
        end_count = trend_wide.loc[end_year, theme]
        growth_rows.append({
            "final_theme": theme,
            "start_year": start_year,
            "end_year": end_year,
            "start_count": start_count,
            "end_count": end_count,
            "growth_percent": ((end_count - start_count) / max(start_count, 1)) * 100,
        })

    trend_stats_df = pd.DataFrame(trend_stats).sort_values("p_value")
    growth_df = pd.DataFrame(growth_rows).sort_values("growth_percent", ascending=False)
    p = theme_counts["percent"] / 100
    diversity = pd.DataFrame({
        "metric": ["Shannon diversity index of final expert-curated themes"],
        "value": [-float(np.sum(p * np.log(p)))],
    })
    excluded = summary[summary["include_exclude"].astype(str).str.upper() == "EXCLUDE"].copy()
    decisions = summary["include_exclude"].fillna("UNMAPPED").value_counts().reset_index()
    decisions.columns = ["decision", "count"]

    mapping_table = (
        summary.groupby("final_theme")
        .agg({
            "topic_id": lambda x: ", ".join(map(str, sorted(x))),
            "expert_label": lambda x: "; ".join(sorted(set(map(str, x)))),
            "include_exclude": "first",
            "top_words": lambda x: " | ".join(list(map(str, x))[:3]),
        })
        .reset_index()
    )
    mapping_table.columns = [
        "final_theme",
        "bertopic_topic_ids",
        "expert_interpretations",
        "curation_status",
        "representative_top_words",
    ]

    summary_publication = (
        theme_counts.merge(trend_stats_df, on="final_theme", how="left")
        .merge(growth_df[["final_theme", "growth_percent"]], on="final_theme", how="left")
    )

    ensure_directories(tables_dir)
    outputs = {
        "01_topic_level_expert_curation_summary.csv": summary.drop(columns=["final_theme"]),
        "02_final_theme_mapping_table.csv": summary,
        "03_full_corpus_with_final_themes.csv": full,
        "04_included_corpus_final_themes_only.csv": included,
        "05_final_theme_counts.csv": theme_counts,
        "06_final_theme_temporal_trends_long.csv": trend_long,
        "07_final_theme_temporal_trends_wide.csv": trend_wide.reset_index(),
        "08_smoothed_final_theme_trends.csv": trend_smooth.reset_index(),
        "09_final_theme_relative_contribution.csv": trend_pct.reset_index(),
        "10_final_theme_regression_statistics.csv": trend_stats_df,
        "11_final_theme_growth_rates.csv": growth_df,
        "12_final_theme_shannon_diversity.csv": diversity,
        "13_excluded_topic_summary.csv": excluded,
        "14_topic_inclusion_exclusion_counts.csv": decisions,
        "15_manuscript_final_theme_mapping_table.csv": mapping_table,
        "16_publication_ready_final_theme_summary.csv": summary_publication,
    }
    for filename, frame in outputs.items():
        frame.to_csv(tables_dir / filename, index=False)

    if figures_dir is not None:
        ensure_directories(figures_dir)
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12, 7))
        plt.bar(theme_counts["final_theme"], theme_counts["count"])
        plt.ylabel("Number of publications")
        plt.xlabel("Final expert-curated theme")
        plt.title("Distribution of expert-curated mushroom-poisoning themes")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(figures_dir / "01_final_theme_distribution.png", dpi=300)
        plt.close()

        plt.figure(figsize=(14, 8))
        for column in trend_wide.columns:
            plt.plot(trend_wide.index, trend_wide[column], linewidth=1.8, label=column)
        plt.xlabel("Year")
        plt.ylabel("Number of publications")
        plt.title("Temporal evolution of expert-curated themes")
        plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
        plt.tight_layout()
        plt.savefig(figures_dir / "02_final_theme_temporal_trends.png", dpi=300)
        plt.close()

    return {
        "topic_summary": summary,
        "full": full,
        "included": included,
        "theme_counts": theme_counts,
        "trend_long": trend_long,
        "trend_wide": trend_wide,
    }


# ---------------------------------------------------------------------------
# Ontology-guided entity and relation extraction
# ---------------------------------------------------------------------------

def load_ontology_aliases(path: Path) -> Dict[str, Dict[str, List[str]]]:
    aliases = pd.read_csv(path, low_memory=False)
    required = {"entity_type", "canonical_entity", "alias"}
    missing = required - set(aliases.columns)
    if missing:
        raise ValueError(f"Ontology alias file is missing columns: {sorted(missing)}")
    lexicon: Dict[str, Dict[str, List[str]]] = {}
    for row in aliases.itertuples(index=False):
        lexicon.setdefault(str(row.entity_type), {}).setdefault(str(row.canonical_entity), []).append(str(row.alias))
    for entity_type in lexicon:
        for canonical in lexicon[entity_type]:
            lexicon[entity_type][canonical] = list(dict.fromkeys(lexicon[entity_type][canonical]))
    return lexicon


def load_relation_rules(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rules: List[Dict[str, Any]] = []
    for rule in raw:
        rules.append({
            "source_types": set(rule["source_types"]),
            "target_types": set(rule["target_types"]),
            "relation": str(rule["relation"]),
            "patterns": [str(pattern) for pattern in rule["patterns"]],
        })
    return rules


def construct_stage4_corpus(corpus: pd.DataFrame) -> pd.DataFrame:
    required = [
        "title", "abstract", "year", "journal", "authors", "affiliations",
        "keywords", "text_for_nlp", "topic_initial", "topic_refined", "final_topic",
    ]
    missing = [column for column in required if column not in corpus.columns]
    if missing:
        raise ValueError(f"Corpus is missing extraction columns: {missing}")
    frame = corpus.copy()
    frame["document_id"] = frame.apply(make_document_id, axis=1)
    if frame["document_id"].duplicated().any():
        duplicates = frame.loc[frame["document_id"].duplicated(False), "document_id"].tolist()[:10]
        raise ValueError(f"Document IDs are not unique: {duplicates}")
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    for column in ["title", "abstract", "keywords", "text_for_nlp", "affiliations"]:
        frame[column] = frame[column].fillna("").astype(str)
    frame["stage4_text"] = (
        frame["title"].str.strip() + ". " +
        frame["abstract"].str.strip() + ". " +
        frame["keywords"].str.strip()
    ).str.replace(r"\s+", " ", regex=True).str.strip()
    frame["has_usable_text"] = frame["stage4_text"].str.len().ge(40)
    return frame


def create_phrase_matcher(lexicon: Mapping[str, Mapping[str, Sequence[str]]]):
    import spacy
    from spacy.matcher import PhraseMatcher

    nlp = spacy.blank("en")
    nlp.max_length = 3_000_000
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    lookup: Dict[int, Tuple[str, str]] = {}
    for entity_type, canonical_map in lexicon.items():
        for canonical, aliases in canonical_map.items():
            match_name = f"{entity_type}::{canonical}"
            patterns = [nlp.make_doc(alias) for alias in sorted(set(aliases), key=len, reverse=True)]
            matcher.add(match_name, patterns)
            lookup[nlp.vocab.strings[match_name]] = (entity_type, canonical)
    return nlp, matcher, lookup


def extract_entities_from_frozen_sentence_manifest(
    corpus: pd.DataFrame,
    sentence_manifest: pd.DataFrame,
    lexicon: Mapping[str, Mapping[str, Sequence[str]]],
) -> pd.DataFrame:
    """Replay the original entity extraction with frozen sentence boundaries.

    The manifest contains the sentence boundaries in which at least one ontology
    term was detected in the original extraction environment. The terms are
    rematched from the ontology here; entity rows themselves are not copied.
    """
    required_manifest = {
        "sentence_sequence", "document_id", "sentence_id", "sentence_text", "sentence_char_start"
    }
    missing = required_manifest - set(sentence_manifest.columns)
    if missing:
        raise ValueError(f"Sentence manifest is missing columns: {sorted(missing)}")

    stage4 = construct_stage4_corpus(corpus)
    metadata = stage4.set_index("document_id").to_dict("index")
    if not set(sentence_manifest["document_id"]).issubset(metadata):
        absent = sorted(set(sentence_manifest["document_id"]) - set(metadata))[:10]
        raise ValueError(f"Sentence manifest references unknown documents: {absent}")

    nlp, matcher, lookup = create_phrase_matcher(lexicon)
    negation_cues = {
        "no", "not", "without", "absence", "absent", "neither", "nor",
        "unlikely", "excluded", "negative",
    }
    full_doc_cache: Dict[str, Any] = {}

    def full_document_negation(document_id: str, char_start: int, window: int = 5) -> bool:
        if document_id not in full_doc_cache:
            full_doc_cache[document_id] = nlp.make_doc(metadata[document_id]["stage4_text"])
        document = full_doc_cache[document_id]
        start_token: Optional[int] = None
        for token in document:
            if token.idx <= char_start < token.idx + len(token):
                start_token = token.i
                break
        if start_token is None:
            for token in document:
                if token.idx >= char_start:
                    start_token = token.i
                    break
        if start_token is None:
            return False
        preceding = [token.lower_ for token in document[max(0, start_token - window):start_token]]
        return any(cue in preceding for cue in negation_cues)

    rows: List[Dict[str, Any]] = []
    sentence_manifest = sentence_manifest.sort_values("sentence_sequence")
    for record in sentence_manifest.itertuples(index=False):
        document_id = str(record.document_id)
        sentence_text = str(record.sentence_text)
        sentence_start = int(record.sentence_char_start)
        source_text = metadata[document_id]["stage4_text"]
        if source_text[sentence_start:sentence_start + len(sentence_text)] != sentence_text:
            raise ValueError(
                f"Sentence manifest no longer aligns with {document_id}, sentence {record.sentence_id}."
            )
        sentence_doc = nlp.make_doc(sentence_text)
        seen: set = set()
        for match_id, start, end in matcher(sentence_doc):
            entity_type, canonical = lookup[match_id]
            span = sentence_doc[start:end]
            key = (start, end, entity_type, canonical)
            if key in seen:
                continue
            seen.add(key)
            char_start = sentence_start + span.start_char
            char_end = sentence_start + span.end_char
            meta = metadata[document_id]
            rows.append({
                "document_id": document_id,
                "sentence_id": record.sentence_id,
                "sentence_text": sentence_text,
                "entity_type": entity_type,
                "canonical_entity": canonical,
                "matched_text": span.text,
                "char_start": char_start,
                "char_end": char_end,
                "negated": full_document_negation(document_id, char_start),
                "extraction_method": "curated_phrase_matcher",
                "year": meta.get("year"),
                "final_topic": meta.get("final_topic"),
                "title": meta.get("title"),
                "source": meta.get("source"),
            })
    return pd.DataFrame(rows)


def sentence_segment_live(text: str):
    import spacy
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return [sentence.text.strip() for sentence in nlp(text).sents if sentence.text.strip()]


def extract_entities_live(
    corpus: pd.DataFrame,
    lexicon: Mapping[str, Mapping[str, Sequence[str]]],
) -> pd.DataFrame:
    """Full refreshed extraction using a deterministic rule-based sentencizer."""
    import spacy
    from spacy.matcher import PhraseMatcher

    stage4 = construct_stage4_corpus(corpus)
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    nlp.max_length = 3_000_000
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    lookup: Dict[int, Tuple[str, str]] = {}
    for entity_type, canonical_map in lexicon.items():
        for canonical, aliases in canonical_map.items():
            name = f"{entity_type}::{canonical}"
            matcher.add(name, [nlp.make_doc(alias) for alias in sorted(set(aliases), key=len, reverse=True)])
            lookup[nlp.vocab.strings[name]] = (entity_type, canonical)
    negation_cues = {
        "no", "not", "without", "absence", "absent", "neither", "nor",
        "unlikely", "excluded", "negative",
    }
    rows: List[Dict[str, Any]] = []
    for record in stage4.loc[stage4["has_usable_text"]].itertuples(index=False):
        doc = nlp(record.stage4_text)
        sentence_index: Dict[int, int] = {}
        for index, sentence in enumerate(doc.sents):
            for token in sentence:
                sentence_index[token.i] = index
        seen: set = set()
        for match_id, start, end in matcher(doc):
            entity_type, canonical = lookup[match_id]
            span = doc[start:end]
            key = (start, end, entity_type, canonical)
            if key in seen:
                continue
            seen.add(key)
            preceding = [token.lower_ for token in doc[max(0, start - 5):start]]
            rows.append({
                "document_id": record.document_id,
                "sentence_id": sentence_index.get(start, -1),
                "sentence_text": span.sent.text.strip(),
                "entity_type": entity_type,
                "canonical_entity": canonical,
                "matched_text": span.text,
                "char_start": span.start_char,
                "char_end": span.end_char,
                "negated": any(cue in preceding for cue in negation_cues),
                "extraction_method": "curated_phrase_matcher_live_sentencizer",
                "year": record.year,
                "final_topic": record.final_topic,
                "title": record.title,
                "source": record.source,
            })
    return pd.DataFrame(rows)


def text_between(sentence_text: str, first_text: str, second_text: str) -> str:
    sentence = sentence_text.lower()
    first = first_text.lower()
    second = second_text.lower()
    first_index = sentence.find(first)
    second_index = sentence.find(second)
    if first_index == -1 or second_index == -1:
        return sentence
    if first_index <= second_index:
        return sentence[first_index + len(first):second_index]
    return sentence[second_index + len(second):first_index]


def relation_from_pair(
    entity_1: Mapping[str, Any],
    entity_2: Mapping[str, Any],
    sentence: str,
    relation_rules: Sequence[Mapping[str, Any]],
) -> Optional[Dict[str, Any]]:
    candidates: List[Tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]] = []
    for rule in relation_rules:
        if entity_1["entity_type"] in rule["source_types"] and entity_2["entity_type"] in rule["target_types"]:
            candidates.append((entity_1, entity_2, rule))
        if entity_2["entity_type"] in rule["source_types"] and entity_1["entity_type"] in rule["target_types"]:
            candidates.append((entity_2, entity_1, rule))

    for source, target, rule in candidates:
        between = text_between(sentence, str(source["matched_text"]), str(target["matched_text"]))
        full = sentence.lower()
        for pattern in rule["patterns"]:
            between_match = re.search(pattern, between, flags=re.I)
            full_match = re.search(pattern, full, flags=re.I)
            if between_match or full_match:
                return {
                    "source_entity": source["canonical_entity"],
                    "source_type": source["entity_type"],
                    "relation": rule["relation"],
                    "target_entity": target["canonical_entity"],
                    "target_type": target["entity_type"],
                    "trigger_pattern": pattern,
                    "relation_class": "explicit_rule",
                    "confidence": 0.80 if between_match else 0.65,
                }
    return None


def extract_relations(
    entities: pd.DataFrame,
    relation_rules: Sequence[Mapping[str, Any]],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    positive = entities.loc[~entities["negated"].astype(bool)].copy()
    relation_rows: List[Dict[str, Any]] = []
    cooccurrence_rows: List[Dict[str, Any]] = []

    group_columns = ["document_id", "sentence_id", "sentence_text"]
    for (document_id, sentence_id, sentence), group in positive.groupby(group_columns, dropna=False):
        mentions = (
            group[["entity_type", "canonical_entity", "matched_text", "year", "final_topic", "source"]]
            .drop_duplicates(["entity_type", "canonical_entity"])
            .to_dict("records")
        )
        if len(mentions) < 2:
            continue
        for entity_1, entity_2 in combinations(mentions, 2):
            if (
                entity_1["entity_type"] == entity_2["entity_type"] and
                entity_1["canonical_entity"] == entity_2["canonical_entity"]
            ):
                continue
            explicit = relation_from_pair(entity_1, entity_2, str(sentence), relation_rules)
            common = {
                "document_id": document_id,
                "sentence_id": sentence_id,
                "sentence_text": sentence,
                "year": entity_1.get("year"),
                "final_topic": entity_1.get("final_topic"),
                "source_database": entity_1.get("source"),
            }
            if explicit:
                relation_rows.append({**common, **explicit})
            else:
                pair = sorted(
                    [
                        (entity_1["canonical_entity"], entity_1["entity_type"]),
                        (entity_2["canonical_entity"], entity_2["entity_type"]),
                    ],
                    key=lambda value: (value[1], value[0]),
                )
                cooccurrence_rows.append({
                    **common,
                    "source_entity": pair[0][0],
                    "source_type": pair[0][1],
                    "relation": "CO_OCCURS_WITH",
                    "target_entity": pair[1][0],
                    "target_type": pair[1][1],
                    "trigger_pattern": "",
                    "relation_class": "sentence_cooccurrence",
                    "confidence": 0.35,
                })

    relations = pd.DataFrame(relation_rows).drop_duplicates()
    cooccurrences = pd.DataFrame(cooccurrence_rows).drop_duplicates()
    return relations, cooccurrences


def aggregate_edges(edge_df: pd.DataFrame) -> pd.DataFrame:
    if edge_df.empty:
        return pd.DataFrame()
    return (
        edge_df.groupby(
            [
                "source_entity", "source_type", "relation", "target_entity",
                "target_type", "relation_class",
            ],
            as_index=False,
        )
        .agg(
            support_sentences=("sentence_text", "size"),
            support_documents=("document_id", "nunique"),
            first_year=("year", "min"),
            latest_year=("year", "max"),
            mean_confidence=("confidence", "mean"),
            topics=("final_topic", lambda x: " | ".join(sorted(set(str(v) for v in x if pd.notna(v))))),
            source_databases=("source_database", lambda x: " | ".join(sorted(set(str(v) for v in x if pd.notna(v))))),
            provenance_document_ids=("document_id", lambda x: " | ".join(sorted(set(map(str, x))))),
        )
        .sort_values(["support_documents", "support_sentences"], ascending=False)
    )


def build_extraction_summaries(
    entities: pd.DataFrame,
    relations: pd.DataFrame,
    explicit_edges: pd.DataFrame,
    tables_dir: Path,
) -> Dict[str, pd.DataFrame]:
    positive = entities.loc[~entities["negated"].astype(bool)].copy()
    entity_summary = (
        positive.groupby(["entity_type", "canonical_entity"], as_index=False)
        .agg(
            mention_count=("canonical_entity", "size"),
            document_count=("document_id", "nunique"),
            first_year=("year", "min"),
            latest_year=("year", "max"),
            topic_count=("final_topic", "nunique"),
        )
        .sort_values(["entity_type", "document_count"], ascending=[True, False])
    )
    entity_document = positive[["document_id", "entity_type", "canonical_entity"]].drop_duplicates()
    entity_document["present"] = 1
    relation_summary = (
        explicit_edges.groupby("relation", as_index=False)
        .agg(
            unique_edges=("relation", "size"),
            supporting_documents=("support_documents", "sum"),
            supporting_sentences=("support_sentences", "sum"),
        )
        .sort_values("supporting_documents", ascending=False)
    )
    entity_year = (
        positive[["document_id", "year", "entity_type", "canonical_entity"]]
        .dropna(subset=["year"])
        .drop_duplicates()
        .groupby(["entity_type", "canonical_entity", "year"], as_index=False)
        .agg(publications=("document_id", "nunique"))
    )
    relation_year = (
        relations[[
            "document_id", "year", "source_entity", "source_type", "relation",
            "target_entity", "target_type",
        ]]
        .dropna(subset=["year"])
        .drop_duplicates()
        .groupby(
            ["source_entity", "source_type", "relation", "target_entity", "target_type", "year"],
            as_index=False,
        )
        .agg(publications=("document_id", "nunique"))
    )
    outputs = {
        "02_entity_summary.csv": entity_summary,
        "03_entity_document_matrix_long.csv": entity_document,
        "11_relation_type_summary.csv": relation_summary,
        "13_entity_year_counts.csv": entity_year,
        "14_relation_year_counts.csv": relation_year,
    }
    for filename, frame in outputs.items():
        frame.to_csv(tables_dir / filename, index=False)
    return outputs


# ---------------------------------------------------------------------------
# Snapshot pipeline and bridge to the post-extraction pipeline
# ---------------------------------------------------------------------------

def assemble_post_extraction_input_zip(
    generated_tables_dir: Path,
    bridge_static_dir: Path,
    destination_zip: Path,
) -> pd.DataFrame:
    """Assemble the complete Section 2 input bundle.

    Static validation/benchmark files are verified against their frozen hashes.
    The four upstream-generated CSV files are audited against their frozen
    references earlier in the pipeline, then their *actual* byte hashes are
    written into the Section 2 checksum manifest. This avoids false failures
    caused only by harmless CSV byte-format differences across compatible
    pandas/Python environments while preserving strict content checks.
    """
    staging = destination_zip.parent / "_bridge_staging"
    if staging.exists():
        shutil.rmtree(staging)
    data_dir = staging / "data"
    data_dir.mkdir(parents=True)

    for path in sorted(bridge_static_dir.iterdir()):
        if path.is_file():
            shutil.copy2(path, data_dir / path.name)
    for filename in KEY_POST_EXTRACTION_FILES:
        source = generated_tables_dir / filename
        if not source.exists():
            raise FileNotFoundError(f"Generated bridge file is missing: {filename}")
        shutil.copy2(source, data_dir / filename)

    checksum_path = data_dir / "input_checksums.csv"
    if not checksum_path.exists():
        raise FileNotFoundError("Bridge static files must include input_checksums.csv")
    checksum_manifest = pd.read_csv(checksum_path)
    audit_rows: List[Dict[str, Any]] = []
    for index, row in checksum_manifest.iterrows():
        filename = str(row["file"])
        path = data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Bridge input is missing: {filename}")
        actual_hash = sha256_file(path)
        actual_bytes = path.stat().st_size
        is_generated = filename in KEY_POST_EXTRACTION_FILES
        frozen_hash_match = actual_hash == str(row["sha256"])
        frozen_size_match = actual_bytes == int(row["bytes"])
        if not is_generated and not (frozen_hash_match and frozen_size_match):
            raise ValueError(f"Static bridge checksum mismatch for {filename}")
        checksum_manifest.loc[index, "sha256"] = actual_hash
        checksum_manifest.loc[index, "bytes"] = actual_bytes
        audit_rows.append({
            "file": filename,
            "source": "generated_upstream" if is_generated else "frozen_static",
            "sha256": actual_hash,
            "bytes": actual_bytes,
            "matches_frozen_manifest": bool(frozen_hash_match and frozen_size_match),
            "status": "PASS",
        })
    checksum_manifest.to_csv(checksum_path, index=False, lineterminator="\n")

    deterministic_zip(staging, destination_zip)
    audit = pd.DataFrame(audit_rows)
    shutil.rmtree(staging)
    return audit


def snapshot_summary(
    full: pd.DataFrame,
    included: pd.DataFrame,
    topic_summary: pd.DataFrame,
    entities: pd.DataFrame,
    relations: pd.DataFrame,
    edges: pd.DataFrame,
) -> Dict[str, Any]:
    filtered = edges[edges["support_documents"] >= 2]
    active_nodes = set(filtered["source_entity"]) | set(filtered["target_entity"])
    return {
        "full_corpus_records": len(full),
        "included_records": len(included),
        "curated_themes": int(included["final_theme"].nunique()),
        "topic_ids_reviewed": int(topic_summary["topic_id"].nunique()),
        "entity_mentions": len(entities),
        "unique_entities": int(entities["canonical_entity"].nunique()),
        "documents_with_entities": int(entities["document_id"].nunique()),
        "explicit_relation_instances": len(relations),
        "aggregated_semantic_edges": len(edges),
        "support_ge_2_edges": len(filtered),
        "support_ge_2_active_nodes": len(active_nodes),
        "source_pubmed_records": int((full["source"] == "PubMed").sum()),
        "source_scopus_records": int((full["source"] == "Scopus").sum()),
        "year_start": int(pd.to_numeric(full["year"], errors="coerce").min()),
        "year_end": int(pd.to_numeric(full["year"], errors="coerce").max()),
    }


def run_snapshot_pipeline(input_root: Path, output_root: Path) -> Dict[str, Any]:
    tables_dir = output_root / "tables"
    figures_dir = output_root / "figures"
    audits_dir = output_root / "audits"
    metadata_dir = output_root / "metadata"
    ensure_directories(tables_dir, figures_dir, audits_dir, metadata_dir)

    checksum_audit = verify_input_checksums(input_root)
    checksum_audit.to_csv(audits_dir / "01_input_checksum_audit.csv", index=False)

    frozen_dir = input_root / "data" / "frozen"
    ontology_dir = input_root / "data" / "ontology"
    reference_dir = input_root / "data" / "reference"
    bridge_static_dir = input_root / "data" / "bridge_static"

    theme_outputs = run_theme_consolidation(
        corpus_path=frozen_dir / "17_final_dataset_with_topics.csv",
        expert_path=frozen_dir / "16_topic_expert_review_template_annotated.csv",
        tables_dir=tables_dir,
        figures_dir=figures_dir,
    )

    corpus_with_topics = pd.read_csv(frozen_dir / "17_final_dataset_with_topics.csv", low_memory=False)
    sentence_manifest = pd.read_csv(frozen_dir / "frozen_entity_sentence_manifest.csv", low_memory=False)
    lexicon = load_ontology_aliases(ontology_dir / "ontology_entity_aliases.csv")
    relation_rules = load_relation_rules(ontology_dir / "relation_rules.json")

    entities = extract_entities_from_frozen_sentence_manifest(
        corpus=corpus_with_topics,
        sentence_manifest=sentence_manifest,
        lexicon=lexicon,
    )
    entities.to_csv(tables_dir / "01_document_sentence_entities.csv", index=False)

    relations, cooccurrences = extract_relations(entities, relation_rules)
    relations.to_csv(tables_dir / "04_explicit_sentence_relations.csv", index=False)
    cooccurrences.to_csv(tables_dir / "05_sentence_cooccurrences.csv", index=False)

    explicit_edges = aggregate_edges(relations)
    cooccurrence_edges = aggregate_edges(cooccurrences)
    explicit_edges.to_csv(tables_dir / "06_explicit_edges_aggregated.csv", index=False)
    cooccurrence_edges.to_csv(tables_dir / "07_cooccurrence_edges_aggregated.csv", index=False)
    build_extraction_summaries(entities, relations, explicit_edges, tables_dir)

    # Export transparent ontology and relation schema alongside outputs.
    shutil.copy2(ontology_dir / "ontology_entity_aliases.csv", metadata_dir / "ontology_entity_aliases.csv")
    shutil.copy2(ontology_dir / "relation_rules.json", metadata_dir / "relation_rules.json")
    shutil.copy2(input_root / "config" / "search_queries_and_parameters.json", metadata_dir / "search_queries_and_parameters.json")
    shutil.copy2(frozen_dir / "topic_expert_curation_summary.csv", metadata_dir / "topic_expert_curation_summary.csv")
    shutil.copy2(frozen_dir / "frozen_entity_sentence_manifest.csv", metadata_dir / "frozen_entity_sentence_manifest.csv")

    audit_rows: List[Dict[str, Any]] = []
    for filename in REFERENCE_FILES:
        generated = tables_dir / filename
        reference = reference_dir / filename
        if not generated.exists():
            raise FileNotFoundError(f"Expected generated file not found: {filename}")
        if not reference.exists():
            raise FileNotFoundError(f"Reference file not found: {filename}")
        audit_rows.append(compare_dataframes_exact(generated, reference))
    reference_audit = pd.DataFrame(audit_rows)
    reference_audit.to_csv(audits_dir / "02_reference_output_audit.csv", index=False)
    if (reference_audit["status"] == "FAIL").any():
        failures = reference_audit.loc[reference_audit["status"] == "FAIL", "file"].tolist()
        raise AssertionError(f"Generated outputs differ from frozen references: {failures}")

    summary = snapshot_summary(
        theme_outputs["full"],
        theme_outputs["included"],
        theme_outputs["topic_summary"],
        entities,
        relations,
        explicit_edges,
    )
    fixed_checks = []
    for metric, expected in EXPECTED_SNAPSHOT_RESULTS.items():
        actual = summary.get(metric)
        status = "PASS" if actual == expected else "FAIL"
        fixed_checks.append({"metric": metric, "expected": expected, "actual": actual, "status": status})
    fixed_checks_df = pd.DataFrame(fixed_checks)
    fixed_checks_df.to_csv(audits_dir / "03_fixed_result_checks.csv", index=False)
    if (fixed_checks_df["status"] != "PASS").any():
        bad = fixed_checks_df.loc[fixed_checks_df["status"] != "PASS", "metric"].tolist()
        raise AssertionError(f"Fixed snapshot checks failed: {bad}")

    bridge_zip = output_root / "Mushroom_KG_Reproducibility_Inputs_v2_from_upstream.zip"
    bridge_audit = assemble_post_extraction_input_zip(tables_dir, bridge_static_dir, bridge_zip)
    bridge_audit.to_csv(audits_dir / "04_post_extraction_bridge_audit.csv", index=False)

    run_manifest = {
        "pipeline_name": PIPELINE_NAME,
        "pipeline_version": PIPELINE_VERSION,
        "mode": "MANUSCRIPT_SNAPSHOT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            "pandas": package_version("pandas"),
            "numpy": package_version("numpy"),
            "spacy": package_version("spacy"),
            "scipy": package_version("scipy"),
            "matplotlib": package_version("matplotlib"),
        },
        "summary": summary,
        "reference_files_passed": int((reference_audit["status"].isin(["PASS", "PASS_CONTENT"])).sum()),
        "reference_files_total": len(reference_audit),
        "fixed_checks_passed": int((fixed_checks_df["status"] == "PASS").sum()),
        "fixed_checks_total": len(fixed_checks_df),
        "bridge_files_passed": int((bridge_audit["status"] == "PASS").sum()),
        "bridge_files_total": len(bridge_audit),
        "post_extraction_bridge_zip": bridge_zip.name,
    }
    write_json(run_manifest, output_root / "00_run_manifest.json")

    report_lines = [
        "# Upstream reproducibility report",
        "",
        f"- Pipeline: {PIPELINE_NAME} v{PIPELINE_VERSION}",
        "- Mode: MANUSCRIPT_SNAPSHOT",
        f"- Input checksum checks: {len(checksum_audit)}/{len(checksum_audit)} passed",
        f"- Frozen reference outputs: {run_manifest['reference_files_passed']}/{run_manifest['reference_files_total']} passed",
        f"- Fixed numerical checks: {run_manifest['fixed_checks_passed']}/{run_manifest['fixed_checks_total']} passed",
        f"- Section 2 bridge-file checks: {run_manifest['bridge_files_passed']}/{run_manifest['bridge_files_total']} passed",
        "",
        "## Snapshot summary",
        "",
    ]
    report_lines.extend(f"- {key}: {value}" for key, value in summary.items())
    report_lines.extend([
        "",
        "## Bridge to Section 2",
        "",
        f"Use `{bridge_zip.name}` as the input ZIP for the canonical post-extraction notebook.",
        "The bridge retains the original checksum manifest and is verified before creation.",
        "",
        "## Interpretation",
        "",
        "This exact rerun starts from the frozen deduplicated corpus and frozen BERTopic topic assignments.",
        "Fresh bibliographic retrieval and BERTopic refitting are available in LIVE_REFRESH mode, but require API credentials and a new expert-curation pass and are not expected to reproduce the historical snapshot exactly.",
    ])
    write_text("\n".join(report_lines) + "\n", output_root / "UPSTREAM_REPRODUCIBILITY_REPORT.md")
    write_text("SUCCESS\n", output_root / "PIPELINE_SUCCESS.txt")

    # Package all output files except the output archive itself.
    output_archive = output_root.parent / "Mushroom_KG_Upstream_Reproducibility_Outputs.zip"
    deterministic_zip(output_root, output_archive)
    return {
        "summary": summary,
        "output_archive": str(output_archive),
        "bridge_zip": str(bridge_zip),
        "run_manifest": run_manifest,
    }


# ---------------------------------------------------------------------------
# Optional live retrieval, deduplication, BERTopic, and refreshed extraction
# ---------------------------------------------------------------------------

@dataclass
class LiveConfig:
    year_start: int = 2000
    year_end: int = 2025
    pubmed_batch_size: int = 200
    scopus_batch_size: int = 25
    scopus_max_records: int = 5000
    scopus_abstract_limit: int = 1000
    wos_max_records: int = 300
    wos_page_size: int = 50
    title_similarity_threshold: int = 96
    require_abstract_for_nlp: bool = False
    random_seed: int = 42
    min_cluster_size: int = 15
    min_samples: int = 5
    umap_n_neighbors: int = 15
    umap_n_components: int = 5
    umap_min_dist: float = 0.0

    @property
    def pubmed_query(self) -> str:
        return f'''(
  "mushroom poisoning"[Title/Abstract]
  OR "mushroom intoxication"[Title/Abstract]
  OR "poisonous mushroom"[Title/Abstract]
  OR mycetism[Title/Abstract]
  OR amatoxin[Title/Abstract]
  OR amanitin[Title/Abstract]
  OR "mushroom toxin"[Title/Abstract]
  OR "Amanita poisoning"[Title/Abstract]
)
AND ("{self.year_start}/01/01"[Date - Publication] : "{self.year_end}/12/31"[Date - Publication])
AND english[Language]'''

    @property
    def scopus_query(self) -> str:
        return (
            'TITLE-ABS-KEY("mushroom poisoning" OR "mushroom intoxication" OR '
            '"poisonous mushroom" OR mycetism OR amatoxin OR amanitin OR '
            '"mushroom toxin" OR "Amanita poisoning") '
            f'AND PUBYEAR > {self.year_start - 1} AND PUBYEAR < {self.year_end + 1}'
        )

    @property
    def wos_query(self) -> str:
        return (
            'TS=("mushroom poisoning" OR "mushroom intoxication" OR '
            '"poisonous mushroom" OR mycetism OR amatoxin OR amanitin '
            'OR "mushroom toxin" OR "Amanita poisoning")'
        )


def empty_literature_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "source", "pmid", "doi", "eid", "title", "abstract", "year",
        "journal", "authors", "affiliations", "keywords", "language",
        "document_type",
    ])


def request_with_retries(
    method: str,
    url: str,
    *,
    attempts: int = 5,
    backoff: float = 1.0,
    retry_statuses: Sequence[int] = (429, 500, 502, 503, 504),
    **kwargs: Any,
):
    import requests

    last_error: Optional[Exception] = None
    for attempt in range(attempts):
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code not in retry_statuses:
                return response
            wait = backoff * (2 ** attempt)
            retry_after = response.headers.get("Retry-After")
            if retry_after and str(retry_after).isdigit():
                wait = max(wait, float(retry_after))
            time.sleep(wait)
        except Exception as exc:
            last_error = exc
            time.sleep(backoff * (2 ** attempt))
    if last_error:
        raise last_error
    return response


def parse_pubmed_article(article: Mapping[str, Any]) -> Dict[str, Any]:
    medline = article.get("MedlineCitation", {})
    pmid = str(medline.get("PMID", ""))
    art = medline.get("Article", {})
    title = clean_text(art.get("ArticleTitle", ""))
    abstract_parts: List[str] = []
    abstract = art.get("Abstract", {})
    if "AbstractText" in abstract:
        for part in abstract["AbstractText"]:
            abstract_parts.append(clean_text(part))
    journal = art.get("Journal", {})
    publication_date = ""
    try:
        values = journal.get("JournalIssue", {}).get("PubDate", {}).values()
        publication_date = " ".join(str(value) for value in values)
    except Exception:
        publication_date = ""
    doi = ""
    for identifier in article.get("PubmedData", {}).get("ArticleIdList", []):
        if str(getattr(identifier, "attributes", {}).get("IdType", "")).lower() == "doi":
            doi = normalize_doi(str(identifier))
    authors: List[str] = []
    affiliations: List[str] = []
    for author in art.get("AuthorList", []):
        name = clean_text(f"{author.get('ForeName', '')} {author.get('LastName', '')}")
        if name:
            authors.append(name)
        for affiliation in author.get("AffiliationInfo", []):
            affiliations.append(clean_text(affiliation.get("Affiliation", "")))
    keywords: List[str] = []
    for keyword_list in medline.get("KeywordList", []):
        keywords.extend(clean_text(str(keyword)) for keyword in keyword_list)
    return {
        "source": "PubMed",
        "pmid": pmid,
        "doi": doi,
        "eid": "",
        "title": title,
        "abstract": clean_text(" ".join(abstract_parts)),
        "year": extract_year(publication_date),
        "journal": clean_text(journal.get("Title", "")),
        "authors": safe_join(authors),
        "affiliations": safe_join(affiliations),
        "keywords": safe_join(keywords),
        "language": "English",
        "document_type": "Journal Article",
    }


def fetch_pubmed_live(
    query: str,
    email: str,
    output_raw_dir: Path,
    batch_size: int = 200,
    api_key: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    from Bio import Entrez

    Entrez.email = email
    Entrez.tool = "mushroom_poisoning_semantic_kg"
    if api_key:
        Entrez.api_key = api_key
    search = Entrez.esearch(db="pubmed", term=query, retmax=100000, sort="pub date")
    search_result = Entrez.read(search)
    search.close()
    identifiers = list(search_result.get("IdList", []))
    write_json({"query": query, "ids": identifiers}, output_raw_dir / "pubmed_search_manifest.json")
    records: List[Dict[str, Any]] = []
    for start in range(0, len(identifiers), batch_size):
        batch = identifiers[start:start + batch_size]
        for attempt in range(5):
            try:
                handle = Entrez.efetch(db="pubmed", id=",".join(batch), retmode="xml")
                data = Entrez.read(handle)
                handle.close()
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(1.0 * (2 ** attempt))
        for article in data.get("PubmedArticle", []):
            records.append(parse_pubmed_article(article))
        time.sleep(0.34 if not api_key else 0.11)
    frame = pd.DataFrame(records) if records else empty_literature_dataframe()
    return frame, {"ids_retrieved": len(identifiers), "records_parsed": len(frame)}


def fetch_scopus_live(
    query: str,
    api_key: Optional[str],
    output_raw_dir: Path,
    max_records: int = 5000,
    batch_size: int = 25,
    abstract_limit: int = 1000,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if not api_key:
        return empty_literature_dataframe(), {"status": "SKIPPED_NO_API_KEY", "records": 0}
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    url = "https://api.elsevier.com/content/search/scopus"
    records: List[Dict[str, Any]] = []
    pages = 0
    total_reported = None
    for start in range(0, max_records, batch_size):
        response = request_with_retries(
            "GET", url, headers=headers,
            params={"query": query, "start": start, "count": batch_size, "view": "STANDARD"},
            timeout=60,
        )
        if response.status_code != 200:
            return pd.DataFrame(records) if records else empty_literature_dataframe(), {
                "status": f"HTTP_{response.status_code}", "records": len(records),
                "message": response.text[:500],
            }
        page = response.json()
        write_json(page, output_raw_dir / f"scopus_page_{pages + 1:04d}.json")
        pages += 1
        entries = page.get("search-results", {}).get("entry", [])
        if not entries:
            break
        for entry in entries:
            records.append({
                "source": "Scopus",
                "pmid": clean_text(entry.get("pubmed-id", "")),
                "doi": normalize_doi(entry.get("prism:doi", "")),
                "eid": clean_text(entry.get("eid", "")),
                "title": clean_text(entry.get("dc:title", "")),
                "abstract": clean_text(entry.get("dc:description", "")),
                "year": extract_year(entry.get("prism:coverDate", "")),
                "journal": clean_text(entry.get("prism:publicationName", "")),
                "authors": clean_text(entry.get("dc:creator", "")),
                "affiliations": "",
                "keywords": "",
                "language": "",
                "document_type": clean_text(entry.get("subtypeDescription", "")),
            })
        total_reported = int(page.get("search-results", {}).get("opensearch:totalResults", 0))
        if start + batch_size >= total_reported:
            break
        time.sleep(0.25)

    frame = pd.DataFrame(records) if records else empty_literature_dataframe()
    if not frame.empty and abstract_limit > 0:
        missing = frame["abstract"].fillna("").str.len() < 30
        for index in frame[missing].index[:abstract_limit]:
            eid = clean_text(frame.loc[index, "eid"])
            if not eid:
                continue
            response = request_with_retries(
                "GET",
                f"https://api.elsevier.com/content/abstract/eid/{eid}",
                headers=headers,
                timeout=60,
            )
            if response.status_code == 200:
                payload = response.json()
                core = payload.get("abstracts-retrieval-response", {}).get("coredata", {})
                abstract = clean_text(core.get("dc:description", ""))
                if abstract:
                    frame.loc[index, "abstract"] = abstract
            time.sleep(0.2)
    return frame, {
        "status": "OK",
        "records": len(frame),
        "pages": pages,
        "total_results_reported": total_reported,
    }


def fetch_wos_live(
    query: str,
    api_key: Optional[str],
    output_raw_dir: Path,
    max_records: int = 300,
    page_size: int = 50,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if not api_key:
        return empty_literature_dataframe(), {"status": "SKIPPED_NO_API_KEY", "records": 0}
    headers = {"X-ApiKey": api_key, "Accept": "application/json"}
    url = "https://api.clarivate.com/apis/wos-starter/v1/documents"
    records: List[Dict[str, Any]] = []
    pages = 0
    for first in range(1, max_records + 1, page_size):
        page_number = int((first - 1) / page_size) + 1
        response = request_with_retries(
            "GET", url, headers=headers,
            params={"q": query, "db": "WOS", "limit": page_size, "page": page_number},
            timeout=60,
        )
        if response.status_code != 200:
            return pd.DataFrame(records) if records else empty_literature_dataframe(), {
                "status": f"HTTP_{response.status_code}", "records": len(records),
                "message": response.text[:500],
            }
        page = response.json()
        write_json(page, output_raw_dir / f"wos_page_{page_number:04d}.json")
        pages += 1
        hits = page.get("hits", [])
        if not hits:
            break
        for hit in hits:
            names = hit.get("names", {})
            authors = []
            for author in names.get("authors", []):
                if isinstance(author, dict):
                    authors.append(clean_text(author.get("displayName", "")))
            source = hit.get("source", {})
            identifiers = hit.get("identifiers", {})
            keywords = hit.get("keywords", [])
            records.append({
                "source": "WoS_validation",
                "pmid": "",
                "doi": normalize_doi(identifiers.get("doi", "")),
                "eid": "",
                "title": clean_text(hit.get("title", "")),
                "abstract": clean_text(hit.get("abstract", "")),
                "year": extract_year(hit.get("sourcePublishYear", "")),
                "journal": clean_text(source.get("sourceTitle", "")),
                "authors": safe_join(authors),
                "affiliations": "",
                "keywords": safe_join(keywords) if isinstance(keywords, list) else "",
                "language": "",
                "document_type": clean_text(hit.get("documentType", "")),
            })
        time.sleep(0.4)
    frame = pd.DataFrame(records) if records else empty_literature_dataframe()
    return frame, {"status": "OK", "records": len(frame), "pages": pages}


def harmonize_and_deduplicate(
    pubmed: pd.DataFrame,
    scopus: pd.DataFrame,
    config: LiveConfig,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from rapidfuzz import fuzz

    columns = [
        "source", "pmid", "doi", "eid", "title", "abstract", "year",
        "journal", "authors", "affiliations", "keywords", "language",
        "document_type",
    ]
    frames = []
    for frame in [pubmed, scopus]:
        current = frame.copy()
        for column in columns:
            if column not in current.columns:
                current[column] = ""
        frames.append(current[columns])
    merged = pd.concat(frames, ignore_index=True)
    merged["title_clean"] = merged["title"].map(normalize_title)
    merged["doi_clean"] = merged["doi"].map(normalize_doi)
    merged["pmid_clean"] = merged["pmid"].fillna("").astype(str).str.strip()

    log: List[List[Any]] = []
    before = len(merged)
    mask = merged["doi_clean"] != ""
    merged = pd.concat([
        merged[mask].drop_duplicates("doi_clean", keep="first"),
        merged[~mask],
    ], ignore_index=True)
    log.append(["Removed duplicate DOI records", before - len(merged)])

    before = len(merged)
    mask = merged["pmid_clean"] != ""
    merged = pd.concat([
        merged[mask].drop_duplicates("pmid_clean", keep="first"),
        merged[~mask],
    ], ignore_index=True)
    log.append(["Removed duplicate PMID records", before - len(merged)])

    before = len(merged)
    merged = merged.drop_duplicates("title_clean", keep="first")
    log.append(["Removed exact title duplicates", before - len(merged)])

    before = len(merged)
    merged = merged.reset_index(drop=True)
    titles = merged["title_clean"].tolist()
    remove: set = set()
    for i, title_i in enumerate(titles):
        if i in remove or not title_i or len(title_i) < 20:
            continue
        for j in range(i + 1, len(titles)):
            if j in remove:
                continue
            title_j = titles[j]
            if not title_j or len(title_j) < 20:
                continue
            if fuzz.ratio(title_i, title_j) >= config.title_similarity_threshold:
                remove.add(j)
    merged = merged.drop(index=list(remove)).reset_index(drop=True)
    log.append(["Removed fuzzy title duplicates", before - len(merged)])
    dedup = merged.copy()

    filter_log: List[List[Any]] = []
    frame = dedup.copy()
    before = len(frame)
    frame = frame[frame["title"].fillna("").str.len() > 5]
    filter_log.append(["Removed records with missing/short title", before - len(frame)])
    before = len(frame)
    frame = frame[frame["year"].notna()]
    filter_log.append(["Removed records with missing year", before - len(frame)])
    before = len(frame)
    frame["year"] = frame["year"].astype(int)
    frame = frame[(frame["year"] >= config.year_start) & (frame["year"] <= config.year_end)]
    filter_log.append(["Removed records outside year range", before - len(frame)])
    if config.require_abstract_for_nlp:
        before = len(frame)
        frame = frame[frame["abstract"].fillna("").str.len() >= 30]
        filter_log.append(["Removed records without usable abstract", before - len(frame)])
    else:
        filter_log.append(["Abstract not mandatory for NLP corpus", 0])
    frame["text_for_nlp"] = (
        frame["title"].fillna("") + ". " +
        frame["abstract"].fillna("") + ". " +
        frame["keywords"].fillna("")
    ).map(clean_text)
    before = len(frame)
    frame = frame[frame["text_for_nlp"].str.len() >= 30]
    filter_log.append(["Removed records with insufficient combined NLP text", before - len(frame)])
    final = frame.reset_index(drop=True)
    return merged, dedup, final, pd.DataFrame(log, columns=["step", "records_removed"]).assign(stage="deduplication").pipe(
        lambda dedup_log: pd.concat([
            dedup_log,
            pd.DataFrame(filter_log, columns=["step", "records_removed"]).assign(stage="filtering"),
        ], ignore_index=True)
    )


def fit_bertopic_live(corpus: pd.DataFrame, output_dir: Path, config: LiveConfig) -> Dict[str, Any]:
    """Fit BERTopic and emit a template for mandatory expert curation."""
    try:
        from sentence_transformers import SentenceTransformer
        from bertopic import BERTopic
        from umap import UMAP
        from hdbscan import HDBSCAN
    except ImportError as exc:
        raise ImportError(
            "LIVE_REFRESH BERTopic mode requires sentence-transformers, bertopic, umap-learn, and hdbscan. "
            "Install requirements_live.txt in Colab."
        ) from exc

    texts = corpus["text_for_nlp"].astype(str).tolist()
    embedding_model = SentenceTransformer("all-mpnet-base-v2")
    umap_model = UMAP(
        n_neighbors=config.umap_n_neighbors,
        n_components=config.umap_n_components,
        min_dist=config.umap_min_dist,
        metric="cosine",
        random_state=config.random_seed,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=config.min_cluster_size,
        min_samples=config.min_samples,
        metric="euclidean",
        prediction_data=True,
    )
    model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        min_topic_size=config.min_cluster_size,
        calculate_probabilities=True,
        verbose=True,
    )
    topics, probabilities = model.fit_transform(texts)
    refined = model.reduce_outliers(texts, topics, strategy="embeddings")
    result = corpus.copy()
    result["topic_initial"] = topics
    result["topic_refined"] = refined
    result["final_topic"] = "UNREVIEWED"
    ensure_directories(output_dir)
    result.to_csv(output_dir / "17_live_dataset_with_topics_unreviewed.csv", index=False)
    model.get_topic_info().to_csv(output_dir / "12_live_topic_info.csv", index=False)

    rows: List[Dict[str, Any]] = []
    valid_topics = [topic for topic in model.get_topics().keys() if topic != -1 and model.get_topic(topic)]
    for topic in valid_topics:
        words = ", ".join(word for word, _ in model.get_topic(topic)[:10])
        documents = model.get_representative_docs(topic)
        if isinstance(documents, dict):
            documents = documents.get(topic, [])
        for rank, document in enumerate(list(documents)[:5], start=1):
            rows.append({
                "topic_id": topic,
                "top_words": words,
                "representative_doc_rank": rank,
                "representative_text": str(document)[:600],
                "expert_label": "",
                "include_exclude": "",
                "comment": "",
            })
    template = pd.DataFrame(rows)
    template.to_csv(output_dir / "16_live_topic_expert_review_template.csv", index=False)
    try:
        model.save(output_dir / "bertopic_model", serialization="safetensors", save_ctfidf=True)
    except Exception:
        pass
    return {
        "records": len(result),
        "valid_topics": len(valid_topics),
        "dataset": str(output_dir / "17_live_dataset_with_topics_unreviewed.csv"),
        "review_template": str(output_dir / "16_live_topic_expert_review_template.csv"),
    }


def run_live_refresh(
    output_root: Path,
    *,
    phase: str,
    config: LiveConfig,
    entrez_email: Optional[str],
    entrez_api_key: Optional[str],
    scopus_api_key: Optional[str],
    wos_api_key: Optional[str],
    annotated_topic_file: Optional[Path],
    ontology_aliases: Path,
    relation_rules_file: Path,
) -> Dict[str, Any]:
    """Run a fresh database-to-extraction workflow.

    phase='RETRIEVE_AND_MODEL' retrieves and fits BERTopic, then generates a
    human-review template. phase='APPLY_CURATION_AND_EXTRACT' requires the
    unreviewed live dataset and a completed expert review file in output_root.
    """
    phase = phase.upper()
    raw_dir = output_root / "raw_api_responses"
    tables_dir = output_root / "tables"
    figures_dir = output_root / "figures"
    ensure_directories(raw_dir, tables_dir, figures_dir)

    if phase == "RETRIEVE_AND_MODEL":
        if not entrez_email:
            raise ValueError("ENTREZ_EMAIL is required for live PubMed retrieval.")
        pubmed, pubmed_status = fetch_pubmed_live(
            config.pubmed_query, entrez_email, raw_dir,
            batch_size=config.pubmed_batch_size, api_key=entrez_api_key,
        )
        scopus, scopus_status = fetch_scopus_live(
            config.scopus_query, scopus_api_key, raw_dir,
            max_records=config.scopus_max_records,
            batch_size=config.scopus_batch_size,
            abstract_limit=config.scopus_abstract_limit,
        )
        wos, wos_status = fetch_wos_live(
            config.wos_query, wos_api_key, raw_dir,
            max_records=config.wos_max_records,
            page_size=config.wos_page_size,
        )
        pubmed.to_csv(tables_dir / "01_raw_pubmed.csv", index=False)
        scopus.to_csv(tables_dir / "02_raw_scopus.csv", index=False)
        wos.to_csv(tables_dir / "04_raw_wos_validation.csv", index=False)
        merged, deduplicated, final, logs = harmonize_and_deduplicate(pubmed, scopus, config)
        merged.to_csv(tables_dir / "05_merged_raw_pubmed_scopus.csv", index=False)
        deduplicated.to_csv(tables_dir / "06_deduplicated_records.csv", index=False)
        final.to_csv(tables_dir / "08_final_nlp_corpus.csv", index=False)
        logs.to_csv(tables_dir / "09_deduplication_and_filtering_log.csv", index=False)
        status = {
            "phase": phase,
            "retrieval_time_utc": datetime.now(timezone.utc).isoformat(),
            "configuration": asdict(config),
            "queries": {
                "pubmed": config.pubmed_query,
                "scopus": config.scopus_query,
                "wos": config.wos_query,
            },
            "pubmed": pubmed_status,
            "scopus": scopus_status,
            "wos": wos_status,
            "merged_records": len(merged),
            "deduplicated_records": len(deduplicated),
            "final_nlp_records": len(final),
        }
        write_json(status, output_root / "live_retrieval_manifest.json")
        topic_status = fit_bertopic_live(final, tables_dir, config)
        status["bertopic"] = topic_status
        write_json(status, output_root / "live_retrieval_and_model_manifest.json")
        write_text(
            "The live model stage completed. Domain experts must complete "
            "16_live_topic_expert_review_template.csv before applying curation and extraction.\n",
            output_root / "NEXT_STEP.txt",
        )
        return status

    if phase == "APPLY_CURATION_AND_EXTRACT":
        unreviewed = tables_dir / "17_live_dataset_with_topics_unreviewed.csv"
        if not unreviewed.exists():
            raise FileNotFoundError(
                "Run LIVE_REFRESH phase RETRIEVE_AND_MODEL first; the unreviewed topic dataset is missing."
            )
        if annotated_topic_file is None or not annotated_topic_file.exists():
            raise FileNotFoundError("A completed annotated topic-review CSV is required.")
        theme_outputs = run_theme_consolidation(unreviewed, annotated_topic_file, tables_dir, figures_dir)
        lexicon = load_ontology_aliases(ontology_aliases)
        rules = load_relation_rules(relation_rules_file)
        curated_corpus = theme_outputs["full"].copy()
        # The semantic-extraction tables historically use ``final_topic`` for
        # the expert-consolidated domain label. Preserve that schema in live
        # refreshes rather than carrying the temporary UNREVIEWED placeholder.
        curated_corpus["final_topic"] = curated_corpus["final_theme"]
        entities = extract_entities_live(curated_corpus, lexicon)
        relations, cooccurrences = extract_relations(entities, rules)
        edges = aggregate_edges(relations)
        entities.to_csv(tables_dir / "01_document_sentence_entities.csv", index=False)
        relations.to_csv(tables_dir / "04_explicit_sentence_relations.csv", index=False)
        cooccurrences.to_csv(tables_dir / "05_sentence_cooccurrences.csv", index=False)
        edges.to_csv(tables_dir / "06_explicit_edges_aggregated.csv", index=False)
        aggregate_edges(cooccurrences).to_csv(tables_dir / "07_cooccurrence_edges_aggregated.csv", index=False)
        build_extraction_summaries(entities, relations, edges, tables_dir)
        status = {
            "phase": phase,
            "full_corpus_records": len(theme_outputs["full"]),
            "included_records": len(theme_outputs["included"]),
            "entity_mentions": len(entities),
            "relation_instances": len(relations),
            "aggregated_edges": len(edges),
        }
        write_json(status, output_root / "live_curation_and_extraction_manifest.json")
        return status

    raise ValueError("phase must be RETRIEVE_AND_MODEL or APPLY_CURATION_AND_EXTRACT")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=PIPELINE_NAME)
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=["MANUSCRIPT_SNAPSHOT", "LIVE_REFRESH"])
    parser.add_argument("--input-dir", type=Path, help="Extracted upstream input directory")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--live-phase", default="RETRIEVE_AND_MODEL")
    parser.add_argument("--annotated-topic-file", type=Path)
    args = parser.parse_args(argv)

    if args.mode == "MANUSCRIPT_SNAPSHOT":
        if args.input_dir is None:
            parser.error("--input-dir is required in MANUSCRIPT_SNAPSHOT mode")
        result = run_snapshot_pipeline(args.input_dir, args.output_dir)
        print(json.dumps(result["run_manifest"], indent=2))
        return 0

    config = LiveConfig()
    input_dir = args.input_dir
    if input_dir is None:
        parser.error("--input-dir is required to locate ontology files in LIVE_REFRESH mode")
    result = run_live_refresh(
        args.output_dir,
        phase=args.live_phase,
        config=config,
        entrez_email=os.getenv("ENTREZ_EMAIL"),
        entrez_api_key=os.getenv("NCBI_API_KEY"),
        scopus_api_key=os.getenv("SCOPUS_API_KEY"),
        wos_api_key=os.getenv("WOS_API_KEY"),
        annotated_topic_file=args.annotated_topic_file,
        ontology_aliases=input_dir / "data" / "ontology" / "ontology_entity_aliases.csv",
        relation_rules_file=input_dir / "data" / "ontology" / "relation_rules.json",
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
