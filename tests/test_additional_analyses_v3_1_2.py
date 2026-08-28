from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import nbformat
import pandas as pd
import pytest

from aiskg.additional_analyses import run_replay
from aiskg.additional_analyses.reviewer_validation import RATING_COLUMNS, replay_reviewer_validation

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/frozen/additional_analyses_v3.1.2"
WORKBOOKS = DATA / "pathway/reviewer_workbooks"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reviewer_replay():
    return replay_reviewer_validation(
        WORKBOOKS / "Expert_A_completed_public.xlsx",
        WORKBOOKS / "Expert_B_completed_public.xlsx",
        WORKBOOKS / "Third_Expert_completed_public.xlsx",
    )


def test_release_version_and_correct_repository_url():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "3.2.0"
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "3.2.0"' in pyproject
    assert "https://github.com/romenmeitei/AISKG" in pyproject
    assert "AISKG_Framework/issues" not in pyproject


def test_public_reviewer_workbooks_are_sanitized_and_hash_locked():
    provenance = json.loads((DATA / "source_upload_sha256.json").read_text(encoding="utf-8"))
    mapping = {
        "expert_A_public": WORKBOOKS / "Expert_A_completed_public.xlsx",
        "expert_B_public": WORKBOOKS / "Expert_B_completed_public.xlsx",
        "third_expert_public": WORKBOOKS / "Third_Expert_completed_public.xlsx",
    }
    for key, path in mapping.items():
        assert digest(path) == provenance["reviewer_workbooks"][key]["sha256"]
        with zipfile.ZipFile(path) as archive:
            assert not any(name.startswith("docProps/") for name in archive.namelist())
            assert all(tuple(info.date_time) == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())


def test_reviewer_agreement_is_independently_recomputed():
    replay = reviewer_replay()
    expected = pd.read_csv(DATA / "pathway/pathway_interrater_agreement_expected.csv")
    pd.testing.assert_frame_equal(replay.agreement, expected, check_exact=False, rtol=0, atol=1e-12)
    assert len(replay.agreement) == 7
    complete = replay.agreement.set_index("dimension").loc["complete_pathway_correct"]
    assert complete["disagreements"] == 5
    assert abs(complete["gwet_ac1"] - 0.937074225055402) < 1e-12


def test_third_expert_coverage_and_final_label_reconstruction():
    replay = reviewer_replay()
    assert replay.qc["total_A_B_rating_pairs"] == 805
    assert replay.qc["direct_A_B_disagreements"] == 22
    assert replay.qc["nondefinitive_source_rating_cases"] == 84
    assert replay.qc["required_third_expert_adjudications"] == 92
    assert replay.qc["definitive_A_B_consensus_ratings"] == 713
    assert replay.qc["third_expert_final_label_counts"] == {"No": 88, "Yes": 4}
    assert len(replay.adjudication_audit) == 92
    assert replay.adjudication_audit["source_match_verified"].astype(bool).all()

    frozen = pd.read_csv(DATA / "pathway/pathway_validation_final_labels_public.csv", dtype={"validation_id": str})
    reconstructed = replay.reconstructed_ratings.set_index("validation_id")
    for dimension in RATING_COLUMNS:
        for suffix in ["", "_source", "_binary"]:
            column = dimension + suffix
            observed = frozen["validation_id"].map(reconstructed[column])
            if suffix == "_binary":
                assert observed.astype(int).equals(frozen[column].astype(int))
            else:
                assert observed.astype(str).equals(frozen[column].astype(str))


def test_submitted_rollup_exceptions_are_disclosed_and_adjudicated():
    replay = reviewer_replay()
    exceptions = replay.qc["complete_pathway_rollup_inconsistencies"]
    assert [row["validation_id"] for row in exceptions["Expert A"]] == ["XPV-0052", "XPV-0074"]
    assert all(row["recorded_complete_pathway_correct"] == "Yes" for row in exceptions["Expert A"])
    assert all(row["component_rollup"] == "No" for row in exceptions["Expert A"])
    assert exceptions["Expert B"] == []
    audit = replay.adjudication_audit.set_index(["validation_id", "rating_dimension"])
    for validation_id in ["XPV-0052", "XPV-0074"]:
        assert audit.loc[(validation_id, "complete_pathway_correct"), "adjudicated_label"] == "No"


def test_pathway_primary_endpoint_and_population():
    labels = pd.read_csv(DATA / "pathway/pathway_validation_final_labels_public.csv")
    assert len(labels) == 115 and labels["validation_id"].is_unique
    assert labels["membership"].value_counts().to_dict() == {
        "REMOVED_BY_REFINEMENT": 63,
        "SHARED": 32,
        "ADDED_BY_REFINEMENT": 20,
    }
    pre = labels[labels["membership"].isin(["SHARED", "REMOVED_BY_REFINEMENT"])]
    refined = labels[labels["membership"].isin(["SHARED", "ADDED_BY_REFINEMENT"])]
    assert (int(pre["complete_pathway_correct_binary"].sum()), len(pre)) == (23, 95)
    assert (int(refined["complete_pathway_correct_binary"].sum()), len(refined)) == (26, 52)


def test_corrected_benchmark_metrics_and_reporting_boundary():
    metrics = pd.read_csv(DATA / "benchmark/system_metrics.csv")
    common = metrics[(metrics.task == "entity") & (metrics.schema == "COMMON_146") & (metrics.criterion == "strict")].set_index("system")
    assert abs(common.loc["AISKG", "f1"] - 0.9038031319910514) < 1e-12
    assert abs(common.loc["PubTator3", "f1"] - 0.5007235890014472) < 1e-12
    assert abs(common.loc["StructuredLLM", "f1"] - 0.5026178010471204) < 1e-12
    relation = metrics[metrics.task.eq("relation")].set_index("system")
    assert tuple(relation.loc["AISKG", ["tp", "fp", "fn"]].astype(int)) == (27, 0, 29)
    assert abs(relation.loc["AISKG", "f1"] - 0.6506024096385542) < 1e-12
    assert "PubTator3" not in relation.index


def test_corrected_statistics_are_valid_and_llm_json_is_complete():
    paired = pd.read_csv(DATA / "benchmark/paired_bootstrap_differences.csv")
    tests = pd.read_csv(DATA / "benchmark/mcnemar_holm_tests.csv")
    validation = pd.read_csv(DATA / "benchmark/llm_validation_log.csv")
    assert paired["bootstrap_two_sided_p"].between(0, 1).all()
    assert tests["mcnemar_exact_p"].between(0, 1).all()
    assert tests["holm_p"].between(0, 1).all()
    assert len(validation) == 150 and validation["json_valid"].astype(bool).all()
    assert validation["rejected_items"].sum() == 131


def test_source_manifest_discloses_mutable_model_revision():
    manifest = json.loads((DATA / "benchmark/run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["commit"] == "0e9e0e979c98664c74d7f27e318a7a06aed4fa54"
    assert manifest["pubtator_sentence_coverage"] == 146
    assert manifest["pubtator_relation_status"] == "not_evaluable_no_relation_objects"
    assert manifest["llm_model_id"] == "Qwen/Qwen2.5-7B-Instruct"
    assert manifest["llm_model_revision"] == "main"


def test_private_and_superseded_files_are_absent():
    forbidden = {
        "benchmark_historical_failed_run_metrics_DO_NOT_REPORT.csv",
        "benchmark_historical_failed_run_paired_tests_DO_NOT_REPORT.csv",
        "benchmark_historical_failed_run_mcnemar_DO_NOT_REPORT.csv",
        "benchmark_failed_llm_validation_log.csv",
        "Expert_A_completed.xlsx",
        "Expert_B_completed.xlsx",
        "Third_Expert_completed.xlsx",
    }
    names = {path.name for path in ROOT.rglob("*") if path.is_file()}
    assert not (forbidden & names)


def test_self_contained_master_notebook_is_valid():
    path = ROOT / "notebooks/AISKG_Framework_v3_1_2_Complete_Reproducibility.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    assert len(notebook.cells) == 11
    assert len([cell for cell in notebook.cells if cell.cell_type == "code"]) == 7
    text = "\n".join(str(cell.source) for cell in notebook.cells)
    for marker in ["v3.1.2", "EMBEDDED_PAYLOAD_SHA256", "805", "92", "pubtator_relation_status"]:
        assert marker in text


def test_replay_archive_is_byte_deterministic(tmp_path):
    first = run_replay(DATA, tmp_path / "first" / "outputs")
    second = run_replay(DATA, tmp_path / "second" / "outputs")
    assert digest(first.output_archive) == digest(second.output_archive)
    assert digest(first.output_root / "pathway_validation/AISKG_Expanded_Pathway_Validation_Results_v3.1.2.xlsx") == digest(
        second.output_root / "pathway_validation/AISKG_Expanded_Pathway_Validation_Results_v3.1.2.xlsx"
    )
    assert digest(first.output_root / "benchmark/AISKG_three_system_benchmark_reproduced_v3.1.2.xlsx") == digest(
        second.output_root / "benchmark/AISKG_three_system_benchmark_reproduced_v3.1.2.xlsx"
    )
    assert digest(first.output_root / "pathway_validation/interrater_agreement_recomputed.csv") == digest(
        second.output_root / "pathway_validation/interrater_agreement_recomputed.csv"
    )


def test_manuscript_replay_rejects_unlocked_statistics(tmp_path):
    with pytest.raises(ValueError, match="locked to seed=20260817"):
        run_replay(DATA, tmp_path / "unlocked", seed=1)


def test_replay_rejects_tampered_reviewer_workbook(tmp_path):
    import shutil

    tampered = tmp_path / "data"
    shutil.copytree(DATA, tampered)
    target = tampered / "pathway/reviewer_workbooks/Expert_A_completed_public.xlsx"
    target.write_bytes(target.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="checksum mismatch"):
        run_replay(tampered, tmp_path / "outputs")


def test_replay_rejects_tampered_benchmark_input(tmp_path):
    import shutil

    tampered = tmp_path / "data"
    shutil.copytree(DATA, tampered)
    target = tampered / "benchmark/system_metrics.csv"
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        run_replay(tampered, tmp_path / "outputs")


def test_manuscript_replay_rejects_stale_output_mode(tmp_path):
    with pytest.raises(ValueError, match="requires clean=True"):
        run_replay(DATA, tmp_path / "outputs", clean=False)
