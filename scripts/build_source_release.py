#!/usr/bin/env python3
"""Create the clean deterministic AISKG v3.2.0 GitHub source package."""
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

PACKAGE_NAME = "AISKG_v3.2.0_GITHUB_READY_COMPLETE"
_REQUIRED = {
    "data/frozen/additional_analyses_v3.1.2/SHA256SUMS.txt",
    "data/frozen/external_re_benchmark_v1.0.0/SHA256SUMS.txt",
    "reference_outputs/external_re_benchmark_v1.0.0/AISKG_External_RE_Benchmark_Public_Results_v1_0_0.zip",
    "notebooks/additional_analyses/AISKG_External_RE_Benchmark_Colab_v1_1.ipynb",
    "scripts/verify_v3_1_2_release.py",
    "scripts/verify_v3_2_0_release.py",
    "scripts/run_external_re_smoke.py",
    "verify_repository.py",
}


def clean(root: Path) -> None:
    for path in [root / "outputs", root / ".aiskg_work", root / ".pytest_cache", root / ".ruff_cache"]:
        shutil.rmtree(path, ignore_errors=True)
    for path in root.rglob("__pycache__"):
        shutil.rmtree(path, ignore_errors=True)
    for path in root.rglob("*.egg-info"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def ignore(directory: str, names: list[str]) -> set[str]:
    current = Path(directory).resolve()
    ignored=set()
    for name in names:
        if name in {".git", "outputs", ".aiskg_work", ".pytest_cache", ".ruff_cache", "__pycache__"}:
            ignored.add(name)
        elif fnmatch.fnmatch(name, "*.pyc") or fnmatch.fnmatch(name, "*.pyo") or fnmatch.fnmatch(name, "*.egg-info"):
            ignored.add(name)
    if current == ROOT.resolve():
        ignored.update({"PACKAGE_MANIFEST.csv", "SHA256SUMS.txt"})
    return ignored


def main() -> int:
    clean(ROOT)
    for name in ["PACKAGE_MANIFEST.csv", "SHA256SUMS.txt"]:
        (ROOT / name).unlink(missing_ok=True)
    archive = ROOT.parent / f"{PACKAGE_NAME}.zip"
    archive.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="aiskg-v3.2.0-source-", dir=ROOT.parent) as temporary:
        staging_parent=Path(temporary)
        staged=staging_parent / PACKAGE_NAME
        shutil.copytree(ROOT, staged, ignore=ignore)
        missing=sorted(rel for rel in _REQUIRED if not (staged / rel).is_file())
        if missing:
            raise FileNotFoundError(missing)
        manifest, sums=build_source_manifests(staged)
        shutil.copy2(manifest, ROOT / manifest.name)
        shutil.copy2(sums, ROOT / sums.name)
        deterministic_zip(staging_parent, archive)
    print(f"Manifest: {ROOT / 'PACKAGE_MANIFEST.csv'}")
    print(f"Checksums: {ROOT / 'SHA256SUMS.txt'}")
    print(f"Source archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
