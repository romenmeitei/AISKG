from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from aiskg.reproducibility.source_verifier import verify_source_repository


def _write_verification_files(root: Path, files: dict[str, bytes]) -> None:
    rows = []
    checksum_lines = []
    for rel, payload in sorted(files.items()):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        rows.append({"path": rel, "bytes": len(payload), "sha256": digest})
        checksum_lines.append(f"{digest}  {rel}")
    with (root / "PACKAGE_MANIFEST.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)
    (root / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")


def test_repository_verifier_checks_manifest_and_checksum_list(tmp_path):
    _write_verification_files(tmp_path, {"README.md": b"release\n", "src/module.py": b"VALUE = 1\n"})
    assert verify_source_repository(tmp_path) == 2


def test_repository_verifier_rejects_tampering(tmp_path):
    _write_verification_files(tmp_path, {"README.md": b"release\n"})
    (tmp_path / "README.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="MISMATCH"):
        verify_source_repository(tmp_path)
