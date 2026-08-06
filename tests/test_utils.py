from __future__ import annotations

from pathlib import Path

from aiskg.utils import deterministic_zip, sha256_file


def test_deterministic_zip_is_byte_identical(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").write_text("alpha\n", encoding="utf-8")
    (source / "b.txt").write_text("beta\n", encoding="utf-8")
    first = deterministic_zip(source, tmp_path / "first.zip")
    second = deterministic_zip(source, tmp_path / "second.zip")
    assert sha256_file(first) == sha256_file(second)
