"""Deterministic filesystem, hashing, logging, and archive utilities."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Iterable

import numpy as np

FIXED_ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def set_global_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def extract_zip(archive: Path, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as handle:
        handle.extractall(destination)
    return destination


def find_file_root(root: Path, marker: str) -> Path:
    matches = sorted(root.rglob(marker))
    if not matches:
        raise FileNotFoundError(f"Could not locate {marker!r} below {root}")
    if len(matches) > 1:
        # Prefer data/ for Section 2 bundles and the archive root for Section 1.
        data_matches = [path for path in matches if path.parent.name == "data"]
        target = data_matches[0] if data_matches else matches[0]
    else:
        target = matches[0]
    return target.parent


def iter_release_files(root: Path, exclude: Iterable[str] = ()) -> list[Path]:
    excluded = set(exclude)
    result: list[Path] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel in excluded:
            continue
        result.append(path)
    return result


def deterministic_zip(source: Path, archive: Path, exclude: Iterable[str] = ()) -> Path:
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()
    already_compressed = {".zip", ".xlsx", ".png", ".jpg", ".jpeg", ".pdf", ".gz", ".bz2", ".xz"}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as handle:
        for path in iter_release_files(source, exclude=exclude):
            rel = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(rel, date_time=FIXED_ZIP_TIMESTAMP)
            compress_type = zipfile.ZIP_STORED if path.suffix.lower() in already_compressed else zipfile.ZIP_DEFLATED
            info.compress_type = compress_type
            info.external_attr = 0o644 << 16
            handle.writestr(info, path.read_bytes(), compress_type=compress_type, compresslevel=6 if compress_type == zipfile.ZIP_DEFLATED else None)
    return archive


def write_manifest(root: Path, path: Path, exclude: Iterable[str] = ()) -> None:
    rows = []
    for file_path in iter_release_files(root, exclude=exclude):
        rel = file_path.relative_to(root).as_posix()
        rows.append({"path": rel, "bytes": file_path.stat().st_size, "sha256": sha256_file(file_path)})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "bytes", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_sha256s(root: Path, path: Path, exclude: Iterable[str] = ()) -> None:
    lines = []
    for file_path in iter_release_files(root, exclude=exclude):
        rel = file_path.relative_to(root).as_posix()
        lines.append(f"{sha256_file(file_path)}  {rel}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def package_version(distribution: str) -> str:
    try:
        return importlib_metadata.version(distribution)
    except importlib_metadata.PackageNotFoundError:
        return "not-installed"


def git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unavailable"


def environment_metadata(root: Path) -> dict[str, Any]:
    packages = [
        "numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "networkx",
        "matplotlib", "openpyxl", "XlsxWriter", "PyYAML", "tabulate",
    ]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "git_commit": git_commit(root),
        "packages": {name: package_version(name) for name in packages},
    }
