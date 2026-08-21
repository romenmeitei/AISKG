"""Verification helpers for packaged AISKG source repositories."""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe manifest path: {value!r}")
    return path


def _read_manifest(path: Path) -> dict[str, tuple[int, str]]:
    rows: dict[str, tuple[int, str]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["path", "bytes", "sha256"]:
            raise ValueError(f"Unexpected PACKAGE_MANIFEST.csv columns: {reader.fieldnames}")
        for row in reader:
            rel = _safe_relative_path(row["path"]).as_posix()
            if rel in rows:
                raise ValueError(f"Duplicate manifest path: {rel}")
            digest = row["sha256"].lower()
            if not _SHA256_RE.fullmatch(digest):
                raise ValueError(f"Invalid manifest SHA-256 for {rel}")
            size = int(row["bytes"])
            if size < 0:
                raise ValueError(f"Invalid byte count for {rel}")
            rows[rel] = (size, digest)
    if not rows:
        raise ValueError("PACKAGE_MANIFEST.csv contains no files")
    return rows


def _read_checksums(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            digest, rel = raw.split("  ", 1)
        except ValueError as exc:
            raise ValueError(f"Malformed SHA256SUMS.txt line {line_number}") from exc
        rel = _safe_relative_path(rel).as_posix()
        digest = digest.lower()
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError(f"Invalid SHA-256 on line {line_number}")
        if rel in rows:
            raise ValueError(f"Duplicate checksum path: {rel}")
        rows[rel] = digest
    if not rows:
        raise ValueError("SHA256SUMS.txt contains no files")
    return rows


def verify_source_repository(root: str | Path) -> int:
    """Verify every path listed in both packaged source-integrity files."""
    repository = Path(root).resolve()
    manifest_path = repository / "PACKAGE_MANIFEST.csv"
    checksum_path = repository / "SHA256SUMS.txt"
    if not manifest_path.exists() or not checksum_path.exists():
        missing = [p.name for p in (manifest_path, checksum_path) if not p.exists()]
        raise FileNotFoundError(
            f"Missing packaged verification file(s): {', '.join(missing)}. "
            "Run scripts/build_source_release.py first."
        )

    manifest = _read_manifest(manifest_path)
    checksums = _read_checksums(checksum_path)
    if set(manifest) != set(checksums):
        only_manifest = sorted(set(manifest) - set(checksums))
        only_checksums = sorted(set(checksums) - set(manifest))
        raise ValueError(
            "Manifest/checksum path mismatch: "
            f"only_manifest={only_manifest[:5]}, only_checksums={only_checksums[:5]}"
        )

    for rel in sorted(manifest):
        expected_size, expected_digest = manifest[rel]
        if checksums[rel] != expected_digest:
            raise ValueError(f"Manifest/checksum digest disagreement: {rel}")
        target = repository / rel
        if not target.is_file():
            raise FileNotFoundError(f"MISSING: {rel}")
        if target.stat().st_size != expected_size:
            raise ValueError(f"SIZE MISMATCH: {rel}")
        observed = sha256(target)
        if observed != expected_digest:
            raise ValueError(f"SHA256 MISMATCH: {rel}")
    return len(manifest)
