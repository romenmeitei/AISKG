from __future__ import annotations

import ast
from pathlib import Path


def test_nonlegacy_python_files_parse(repository_root):
    for path in (repository_root / "src" / "aiskg").rglob("*.py"):
        if "legacy" in path.parts:
            continue
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_no_argparse_execution_at_import_in_colab_notebook(repository_root):
    text = (repository_root / "notebooks" / "AISKG_Framework_v3_Complete_Pipeline.ipynb").read_text(encoding="utf-8")
    assert "parser.parse_args()" not in text
