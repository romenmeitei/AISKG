#!/usr/bin/env python3
"""Execute the self-contained AISKG v3.1.2 notebook in a clean directory."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import nbformat
from nbclient import NotebookClient

NOTEBOOK = "AISKG_Framework_v3_1_2_Complete_Reproducibility.ipynb"
OUTPUT_DIR = "AISKG_v3.1.2_reproduction_outputs"
OUTPUT_ZIP = "AISKG_v3.1.2_additional_analyses_reproduced.zip"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--save-executed", default="")
    args = parser.parse_args()

    # Limit native numerical-library thread pools before launching the clean
    # kernel. This prevents intermittent resource contention on small CI/Colab
    # runners without changing any deterministic analysis result.
    for name in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
        os.environ.setdefault(name, "1")
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("PYTHONHASHSEED", "0")

    repository = Path(args.repo_root).resolve()
    source = repository / "notebooks" / NOTEBOOK
    if not source.exists():
        raise SystemExit(f"Notebook not found: {source}")

    with tempfile.TemporaryDirectory(prefix="aiskg-v3.1.2-notebook-") as temporary:
        workdir = Path(temporary)
        notebook_path = workdir / NOTEBOOK
        notebook_path.write_bytes(source.read_bytes())
        notebook = nbformat.read(notebook_path, as_version=4)
        nbformat.validate(notebook)
        client = NotebookClient(
            notebook,
            timeout=args.timeout,
            kernel_name="python3",
            resources={"metadata": {"path": str(workdir)}},
        )
        executed = client.execute()
        for index, cell in enumerate(executed.cells):
            if cell.cell_type != "code":
                continue
            for output in cell.get("outputs", []):
                if output.get("output_type") == "error":
                    raise RuntimeError(
                        f"Notebook cell {index} failed: {output.get('ename')}: {output.get('evalue')}"
                    )

        output_root = workdir / OUTPUT_DIR
        archive = workdir / OUTPUT_ZIP
        required = [
            output_root / "ADDITIONAL_ANALYSES_SUCCESS.txt",
            output_root / "COMBINED_REPRODUCIBILITY_MANIFEST.json",
            output_root / "SHA256SUMS.txt",
            output_root / "benchmark/system_metrics.csv",
            output_root / "pathway_validation/pathway_correctness_summary.csv",
            output_root / "pathway_validation/interrater_agreement_recomputed.csv",
            output_root / "pathway_validation/reviewer_rating_matrix_long.csv",
            output_root / "pathway_validation/third_expert_adjudication_audit.csv",
            output_root / "pathway_validation/REVIEWER_WORKBOOK_QC.json",
            output_root / "pathway_validation/pathway_validation_final_labels_reconstructed.csv",
            archive,
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise RuntimeError(f"Notebook completed without required outputs: {missing}")
        success = (output_root / "ADDITIONAL_ANALYSES_SUCCESS.txt").read_text(encoding="utf-8")
        if "completed successfully" not in success.casefold():
            raise RuntimeError("Success marker did not contain the expected statement.")
        qc = json.loads((output_root / "pathway_validation/REVIEWER_WORKBOOK_QC.json").read_text(encoding="utf-8"))
        if qc.get("total_A_B_rating_pairs") != 805 or qc.get("required_third_expert_adjudications") != 92:
            raise RuntimeError("Reviewer-level notebook replay did not reproduce 805 paired ratings and 92 adjudications.")
        if not qc.get("reviewer_level_replay_passed"):
            raise RuntimeError("Reviewer-level notebook replay did not pass.")
        if args.save_executed:
            destination = Path(args.save_executed).resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            nbformat.write(executed, destination)

        print(
            json.dumps(
                {
                    "release": "3.1.2",
                    "status": "PASS",
                    "notebook_cells": len(executed.cells),
                    "executed_code_cells": sum(
                        cell.cell_type == "code" and cell.execution_count is not None for cell in executed.cells
                    ),
                    "reviewer_pairs": qc["total_A_B_rating_pairs"],
                    "adjudications": qc["required_third_expert_adjudications"],
                    "checksum_entries": len(
                        (output_root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
                    ),
                    "result_archive_bytes": archive.stat().st_size,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
