#!/usr/bin/env python3
"""Build the self-contained AISKG v3.1.2 reviewer-facing notebook."""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path
import zipfile

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/AISKG_Framework_v3_1_2_Complete_Reproducibility.ipynb"
PAYLOAD_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def payload_bytes() -> bytes:
    paths: list[tuple[Path | None, str, bytes | None]] = []
    data_root = ROOT / "data/frozen/additional_analyses_v3.1.2"
    for path in sorted(item for item in data_root.rglob("*") if item.is_file()):
        relative = Path("data/frozen/additional_analyses_v3.1.2") / path.relative_to(data_root)
        paths.append((path, relative.as_posix(), None))
    for relative in [
        "src/aiskg/utils.py",
        "src/aiskg/additional_analyses/__init__.py",
        "src/aiskg/additional_analyses/replay.py",
        "src/aiskg/additional_analyses/reviewer_validation.py",
    ]:
        paths.append((ROOT / relative, relative, None))
    minimal_init = b'"""Self-contained AISKG v3.1.2 notebook runtime."""\n__version__ = "3.1.2"\n'
    paths.append((None, "src/aiskg/__init__.py", minimal_init))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, relative, literal in sorted(paths, key=lambda item: item[1]):
            payload = literal if literal is not None else source.read_bytes()
            info = zipfile.ZipInfo(relative, PAYLOAD_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def build() -> Path:
    payload = payload_bytes()
    payload_hash = hashlib.sha256(payload).hexdigest()
    payload_b64 = base64.b64encode(payload).decode("ascii")

    cells = [
        new_markdown_cell(
            """# AISKG Framework v3.1.2 — complete reviewer-level reproducibility notebook

This self-contained notebook embeds the complete public v3.1.2 pathway-validation inputs, including `Expert_A_completed_public.xlsx`, `Expert_B_completed_public.xlsx`, and `Third_Expert_completed_public.xlsx`, together with the corrected three-system benchmark item-level data and deterministic replay code.

**Default behaviour:** no network, API, or live model call is required. The notebook recomputes seven reviewer-agreement tables from 805 paired ratings, verifies all 92 required third-expert decisions, reconstructs every final pathway label, reproduces pathway and benchmark statistics, regenerates figures/workbooks, writes checksums, and creates a consolidated ZIP.

The exact corrected PubTator/structured-LLM execution remains preserved as an executed reference notebook. Its model revision was recorded as `main`, not an immutable commit; archived predictions replay exactly, but a future live model call is not claimed bit-for-bit identical."""
        ),
        new_code_cell(
            """#@title 1. Locked release configuration (do not change for manuscript reproduction)
from pathlib import Path

RELEASE_VERSION = "3.1.2"
BASE_FROZEN_RELEASE = "3.0.0"
AUDITED_COMMIT = "0e9e0e979c98664c74d7f27e318a7a06aed4fa54"
SEED = 20260817
PATHWAY_BOOTSTRAPS = 10_000
BENCHMARK_BOOTSTRAPS = 5_000
RUN_CORE_FROZEN_PIPELINE = False
AUTO_DOWNLOAD_RESULT_ZIP = False

START_DIR = Path.cwd().resolve()
EMBEDDED_ROOT = START_DIR / ".aiskg_v3_1_2_embedded"
OUTPUT_ROOT = START_DIR / f"AISKG_v{RELEASE_VERSION}_reproduction_outputs"
OUTPUT_ARCHIVE = START_DIR / f"AISKG_v{RELEASE_VERSION}_additional_analyses_reproduced.zip"
print({"release": RELEASE_VERSION, "offline_replay": True, "output_root": str(OUTPUT_ROOT)})"""
        ),
        new_code_cell(
            """#@title 2. Import deterministic runtime dependencies
import base64, hashlib, json, shutil, subprocess, sys, zipfile
import numpy as np
import pandas as pd
import scipy
import statsmodels
import matplotlib
import nbformat
print({"Python": sys.version.split()[0], "NumPy": np.__version__, "pandas": pd.__version__, "SciPy": scipy.__version__})"""
        ),
        new_code_cell(
            f'''#@title 3. Restore and verify the embedded public release payload
EMBEDDED_PAYLOAD_SHA256 = "{payload_hash}"
EMBEDDED_PAYLOAD_B64 = """{payload_b64}"""
payload = base64.b64decode(EMBEDDED_PAYLOAD_B64)
assert hashlib.sha256(payload).hexdigest() == EMBEDDED_PAYLOAD_SHA256
if EMBEDDED_ROOT.exists():
    shutil.rmtree(EMBEDDED_ROOT)
EMBEDDED_ROOT.mkdir(parents=True)
payload_path = EMBEDDED_ROOT / "payload.zip"
payload_path.write_bytes(payload)
with zipfile.ZipFile(payload_path) as archive:
    archive.extractall(EMBEDDED_ROOT)
sys.path.insert(0, str(EMBEDDED_ROOT / "src"))
DATA_ROOT = EMBEDDED_ROOT / "data/frozen/additional_analyses_v3.1.2"
assert DATA_ROOT.is_dir()
print({{"payload_sha256": EMBEDDED_PAYLOAD_SHA256, "embedded_files": sum(p.is_file() for p in EMBEDDED_ROOT.rglob("*"))}})'''
        ),
        new_markdown_cell(
            """## Optional frozen core execution

The v3.1.2 additional analyses are fully self-contained. The next cell is disabled by default and only reruns the unchanged v3.0.0 core snapshot from the audited Git commit."""
        ),
        new_code_cell(
            """#@title 4. Optional execution of the unchanged v3.0.0 frozen core pipeline
CORE_RUN_STATUS = {"requested": bool(RUN_CORE_FROZEN_PIPELINE), "status": "NOT_REQUESTED"}
if RUN_CORE_FROZEN_PIPELINE:
    core_root = START_DIR / "AISKG_core_audited_commit"
    if core_root.exists(): shutil.rmtree(core_root)
    subprocess.run(["git", "clone", "--quiet", "https://github.com/romenmeitei/AISKG.git", str(core_root)], check=True)
    subprocess.run(["git", "-C", str(core_root), "checkout", "--quiet", AUDITED_COMMIT], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", str(core_root), "--no-build-isolation"], check=True)
    subprocess.run([sys.executable, str(core_root / "run_pipeline.py"), "--config", str(core_root / "configs/manuscript_frozen.yaml"), "--run-id", "v3-1-2-core-audit", "--clean", "--quiet"], check=True, cwd=core_root)
    CORE_RUN_STATUS = {"requested": True, "status": "PASS", "core_release": str(core_root / "outputs/v3-1-2-core-audit/AISKG_Framework_v3.0.0_Release.zip")}
print(CORE_RUN_STATUS)"""
        ),
        new_markdown_cell("# Deterministic reviewer-level pathway and corrected benchmark replay"),
        new_code_cell(
            """#@title 5. Execute the complete frozen replay
from aiskg.additional_analyses import run_replay
result = run_replay(DATA_ROOT, OUTPUT_ROOT, seed=SEED, pathway_bootstraps=PATHWAY_BOOTSTRAPS, benchmark_bootstraps=BENCHMARK_BOOTSTRAPS, clean=True)
print({"output_root": str(result.output_root), "output_archive": str(result.output_archive), "manifest": str(result.manifest)})"""
        ),
        new_code_cell(
            """#@title 6. Assert reviewer-level and manuscript-facing results
pathway_summary = pd.read_csv(result.pathway_summary)
benchmark_metrics = pd.read_csv(result.benchmark_metrics)
agreement = pd.read_csv(OUTPUT_ROOT / "pathway_validation/interrater_agreement_recomputed.csv")
adjudication = pd.read_csv(OUTPUT_ROOT / "pathway_validation/third_expert_adjudication_audit.csv")
rating_matrix = pd.read_csv(OUTPUT_ROOT / "pathway_validation/reviewer_rating_matrix_long.csv")
reviewer_qc = json.loads((OUTPUT_ROOT / "pathway_validation/REVIEWER_WORKBOOK_QC.json").read_text())
manifest = json.loads(result.manifest.read_text())

primary = pathway_summary[pathway_summary.endpoint.eq("complete_pathway_correct")]
entity_common = benchmark_metrics[(benchmark_metrics.task == "entity") & (benchmark_metrics.schema == "COMMON_146") & (benchmark_metrics.criterion == "strict")]
relation_full = benchmark_metrics[(benchmark_metrics.task == "relation") & (benchmark_metrics.criterion == "directed_strict")]
assert len(rating_matrix) == 805
assert len(adjudication) == 92 and adjudication.source_match_verified.astype(bool).all()
assert len(agreement) == 7
assert reviewer_qc["direct_A_B_disagreements"] == 22
assert reviewer_qc["required_third_expert_adjudications"] == 92
assert reviewer_qc["third_expert_final_label_counts"] == {"No": 88, "Yes": 4}
assert tuple(primary[primary.system.eq("PRE_REFINEMENT")][["correct", "n"]].iloc[0].astype(int)) == (23, 95)
assert tuple(primary[primary.system.eq("OUTCOME_AWARE_REFINED")][["correct", "n"]].iloc[0].astype(int)) == (26, 52)
assert abs(float(entity_common[entity_common.system.eq("AISKG")].f1.iloc[0]) - 0.9038031319910514) < 1e-12
assert abs(float(entity_common[entity_common.system.eq("PubTator3")].f1.iloc[0]) - 0.5007235890014472) < 1e-12
assert abs(float(entity_common[entity_common.system.eq("StructuredLLM")].f1.iloc[0]) - 0.5026178010471204) < 1e-12
assert tuple(relation_full[relation_full.system.eq("AISKG")][["tp", "fp", "fn"]].iloc[0].astype(int)) == (27, 0, 29)
assert not relation_full.system.eq("PubTator3").any()
assert manifest["benchmark"]["structured_llm_json_valid_n"] == 150
assert manifest["benchmark"]["llm_model_revision_is_immutable_commit"] is False
assert result.success_marker.exists() and result.output_archive.exists()
print("Reviewer agreement"); display(agreement)
print("Pathway primary endpoint"); display(primary)
print("Corrected common-schema strict entity benchmark"); display(entity_common)
print("Corrected directed strict relation benchmark"); display(relation_full)"""
        ),
        new_code_cell(
            """#@title 7. Final integrity report and optional Colab download
checksum_entries = (OUTPUT_ROOT / "SHA256SUMS.txt").read_text().splitlines()
print({"status": "PASS", "release": RELEASE_VERSION, "reviewer_pairs": 805, "adjudications": 92, "output_files_with_checksums": len(checksum_entries), "result_archive_bytes": result.output_archive.stat().st_size, "pubtator_relation_status": manifest["benchmark"]["pubtator_relation_status"]})
if AUTO_DOWNLOAD_RESULT_ZIP:
    try:
        from google.colab import files
        files.download(str(result.output_archive))
    except ImportError:
        print("AUTO_DOWNLOAD_RESULT_ZIP is available only in Google Colab.")"""
        ),
        new_markdown_cell(
            """## Reporting boundary

The generated `PUBLICATION_REPORTING_STATUS.md` and `COMBINED_REPRODUCIBILITY_MANIFEST.json` are authoritative. Reviewer agreement, adjudication, final-label reconstruction, and downstream pathway estimates are now independently reproducible from the public sanitized workbooks. The untouched source workbooks remain private because their document metadata contained a personal account address. PubTator relation performance is **not evaluable**, not zero. The archived structured-LLM predictions reproduce the corrected statistics, while a future live inference requires an immutable model revision for weight-level reproducibility."""
        ),
    ]
    notebook = new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "colab": {"name": NOTEBOOK.name, "provenance": []},
        },
    )
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, NOTEBOOK)
    print(f"Built {NOTEBOOK}")
    print(f"Payload SHA-256: {payload_hash}")
    print(f"Cells: {len(cells)}; code cells: {sum(cell.cell_type == 'code' for cell in cells)}")
    return NOTEBOOK


if __name__ == "__main__":
    build()
