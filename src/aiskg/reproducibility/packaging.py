"""Source-repository manifest and checksum generation."""
from __future__ import annotations

from pathlib import Path

from ..utils import write_manifest, write_sha256s


def build_source_manifests(repository_root: str | Path) -> tuple[Path, Path]:
    root = Path(repository_root).resolve()
    manifest = root / "PACKAGE_MANIFEST.csv"
    checksums = root / "SHA256SUMS.txt"
    exclude = {
        manifest.name,
        checksums.name,
        "AISKG_Framework_v3.0.0_GITHUB_READY.zip",
    }
    write_manifest(root, manifest, exclude=exclude)
    write_sha256s(root, checksums, exclude=exclude)
    return manifest, checksums
