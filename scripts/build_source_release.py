#!/usr/bin/env python3
"""Create the clean, deterministic AISKG v3.1.2 GitHub source package."""
from __future__ import annotations

import fnmatch
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiskg.reproducibility.packaging import build_source_manifests
from aiskg.utils import deterministic_zip

PACKAGE_NAME = "AISKG_v3.1.2_GITHUB_READY_COMPLETE"
_REQUIRED_STAGED_FILES = {
    "data/frozen/additional_analyses_v3.1.2/SHA256SUMS.txt",
    "data/frozen/additional_analyses_v3.1.2/source_upload_sha256.json",
    "notebooks/AISKG_Framework_v3_1_2_Complete_Reproducibility.ipynb",
    "scripts/verify_v3_1_2_release.py",
    "verify_repository.py",
}


def clean_generated_paths(root: Path) -> None:
    for path in [root / "outputs", root / ".aiskg_work", root / ".pytest_cache", root / ".ruff_cache"]:
        shutil.rmtree(path, ignore_errors=True)
    for path in root.rglob("__pycache__"):
        shutil.rmtree(path, ignore_errors=True)
    for path in root.glob("*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)
    for path in (root / "src").glob("*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)


def _copytree_ignore(directory: str, names: list[str]) -> set[str]:
    """Ignore generated material without removing nested scientific manifests."""
    current = Path(directory).resolve()
    ignored: set[str] = set()
    ignored_directory_names = {
        ".git",
        ".github-cache",
        "outputs",
        ".aiskg_work",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
    }
    for name in names:
        if name in ignored_directory_names:
            ignored.add(name)
        elif fnmatch.fnmatch(name, "*.pyc") or fnmatch.fnmatch(name, "*.pyo") or fnmatch.fnmatch(name, "*.egg-info"):
            ignored.add(name)
    # Only the repository-root source-integrity files are regenerated. A nested
    # SHA256SUMS.txt is scientific input provenance and must be preserved.
    if current == ROOT.resolve():
        ignored.update({"PACKAGE_MANIFEST.csv", "SHA256SUMS.txt"})
    return ignored


def _assert_required_staged_files(staged_root: Path) -> None:
    missing = sorted(rel for rel in _REQUIRED_STAGED_FILES if not (staged_root / rel).is_file())
    if missing:
        raise FileNotFoundError(f"Source staging omitted required reproducibility file(s): {missing}")


def main() -> int:
    root = ROOT
    clean_generated_paths(root)
    for generated in [root / "PACKAGE_MANIFEST.csv", root / "SHA256SUMS.txt"]:
        generated.unlink(missing_ok=True)

    archive = root.parent / f"{PACKAGE_NAME}.zip"
    archive.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="aiskg-v3.1.2-source-", dir=root.parent) as temporary:
        staging_parent = Path(temporary)
        staged_root = staging_parent / PACKAGE_NAME
        shutil.copytree(root, staged_root, ignore=_copytree_ignore)
        _assert_required_staged_files(staged_root)
        manifest, checksums = build_source_manifests(staged_root)
        shutil.copy2(manifest, root / manifest.name)
        shutil.copy2(checksums, root / checksums.name)
        deterministic_zip(staging_parent, archive)

    print(f"Manifest: {root / 'PACKAGE_MANIFEST.csv'}")
    print(f"Checksums: {root / 'SHA256SUMS.txt'}")
    print(f"Source archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
