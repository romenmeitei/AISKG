from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable


BIOREDIRECT_REPOSITORY = "https://github.com/ncbi-nlp/BioREDirect.git"
BIOREDIRECT_DATASET_URL = "https://ftp.ncbi.nlm.nih.gov/pub/lu/BioREDirect/datasets.zip"
BIOREDIRECT_MODEL_URL = "https://ftp.ncbi.nlm.nih.gov/pub/lu/BioREDirect/bioredirect_biored_pt.zip"
BIOREX_BASE_MODEL_URL = "https://ftp.ncbi.nlm.nih.gov/pub/lu/BioREx/biorex_biolinkbert_pt.zip"
TORCH_INDEX_URL = "https://download.pytorch.org/whl/cu126"


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(
    command: Iterable[str],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    log_path: str | Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    command_list = [str(value) for value in command]
    print("+", " ".join(command_list), flush=True)
    merged_env = os.environ.copy()
    if env:
        merged_env.update({str(key): str(value) for key, value in env.items()})
    process = subprocess.run(
        command_list,
        cwd=None if cwd is None else str(cwd),
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if log_path is not None:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(process.stdout or "", encoding="utf-8")
    if process.stdout:
        tail = "\n".join(process.stdout.splitlines()[-80:])
        print(tail, flush=True)
    if check and process.returncode != 0:
        raise subprocess.CalledProcessError(
            process.returncode,
            command_list,
            output=process.stdout,
        )
    return process


def download_file(url: str, destination: str | Path, *, force: bool = False) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0 and not force:
        print(f"Using existing download: {destination}")
        return destination
    temporary = destination.with_suffix(destination.suffix + ".part")
    if temporary.exists():
        temporary.unlink()
    print(f"Downloading {url}\n  -> {destination}", flush=True)

    class Progress:
        def __init__(self) -> None:
            self.last_percent = -1

        def __call__(self, blocks: int, block_size: int, total_size: int) -> None:
            if total_size <= 0:
                return
            percent = min(100, int(blocks * block_size * 100 / total_size))
            if percent >= self.last_percent + 5:
                print(f"  {percent}%", flush=True)
                self.last_percent = percent

    urllib.request.urlretrieve(url, temporary, reporthook=Progress())
    temporary.replace(destination)
    return destination


def safe_extract_zip(archive: str | Path, destination: str | Path) -> Path:
    archive = Path(archive)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as handle:
        bad = handle.testzip()
        if bad is not None:
            raise zipfile.BadZipFile(f"Corrupt ZIP member: {bad}")
        root = destination.resolve()
        for member in handle.infolist():
            target = (destination / member.filename).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"Unsafe ZIP path: {member.filename}")
        handle.extractall(destination)
    return destination


def clone_bioredirect(
    destination: str | Path,
    *,
    revision: str = "main",
    force: bool = False,
) -> tuple[Path, str]:
    destination = Path(destination)
    if force and destination.exists():
        shutil.rmtree(destination)
    if not destination.exists():
        run_command(["git", "clone", BIOREDIRECT_REPOSITORY, str(destination)])
    run_command(["git", "fetch", "--all", "--tags"], cwd=destination)
    run_command(["git", "checkout", revision], cwd=destination)
    # When revision is a branch, make sure the run uses the current remote state.
    if revision in {"main", "master"}:
        run_command(["git", "pull", "--ff-only"], cwd=destination)
    commit = run_command(["git", "rev-parse", "HEAD"], cwd=destination).stdout.strip()
    if len(commit) != 40:
        raise RuntimeError(f"Could not resolve BioREDirect commit: {commit!r}")
    return destination, commit


def prepare_python311_environment(
    venv_dir: str | Path,
    repository_dir: str | Path,
    *,
    install_torch: bool = True,
) -> Path:
    """Create an isolated Python 3.11 environment with the official requirements."""

    venv_dir = Path(venv_dir)
    repository_dir = Path(repository_dir)
    if not shutil.which("uv"):
        run_command([sys.executable, "-m", "pip", "install", "-q", "uv"])
    if not venv_dir.exists():
        # uv downloads a managed Python 3.11 build if Colab does not provide one.
        run_command(["uv", "python", "install", "3.11"])
        run_command(["uv", "venv", "--python", "3.11", str(venv_dir)])
    python_bin = venv_dir / "bin" / "python"
    if not python_bin.exists():
        python_bin = venv_dir / "Scripts" / "python.exe"
    if not python_bin.exists():
        raise FileNotFoundError(f"Python executable missing from {venv_dir}")

    marker = venv_dir / ".bioredirect_requirements_installed"
    if not marker.exists():
        run_command(["uv", "pip", "install", "--python", str(python_bin), "--upgrade", "pip", "setuptools", "wheel"])
        if install_torch:
            torch_installed = False
            torch_errors: list[str] = []
            for index_url in [TORCH_INDEX_URL, "https://download.pytorch.org/whl/cu124", "https://download.pytorch.org/whl/cu121"]:
                process = run_command(
                    [
                        "uv",
                        "pip",
                        "install",
                        "--python",
                        str(python_bin),
                        "torch",
                        "torchvision",
                        "torchaudio",
                        "--index-url",
                        index_url,
                    ],
                    check=False,
                )
                if process.returncode == 0:
                    torch_installed = True
                    break
                torch_errors.append(f"{index_url}: {process.stdout[-1000:] if process.stdout else 'no output'}")
            if not torch_installed:
                # CPU/PyPI fallback keeps the workflow executable, although official
                # BioREDirect inference will be much slower without a CUDA wheel.
                process = run_command(
                    [
                        "uv",
                        "pip",
                        "install",
                        "--python",
                        str(python_bin),
                        "torch",
                        "torchvision",
                        "torchaudio",
                    ],
                    check=False,
                )
                if process.returncode != 0:
                    torch_errors.append(f"PyPI fallback: {process.stdout[-1000:] if process.stdout else 'no output'}")
                    raise RuntimeError("Unable to install PyTorch in the BioREDirect environment:\n" + "\n".join(torch_errors))
        run_command(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python_bin),
                "-r",
                str(repository_dir / "requirements.txt"),
            ]
        )
        marker.write_text("installed\n", encoding="utf-8")
    return python_bin


def discover_split_file(
    root: str | Path,
    split: str,
    *,
    require_bc8: bool = False,
    exclude_bc8: bool = False,
    require_train_dev: bool = False,
) -> Path:
    root = Path(root)
    candidates = []
    for path in root.rglob("*.pubtator"):
        name = path.name.lower()
        if "bioredirect" not in name and "biored" not in name:
            continue
        if split.lower() not in name:
            continue
        if require_bc8 and "bc8" not in name:
            continue
        if exclude_bc8 and "bc8" in name:
            continue
        if require_train_dev and not ("train_dev" in name or "train-and-dev" in name):
            continue
        if not require_train_dev and split.lower() == "train" and ("train_dev" in name or "train-and-dev" in name):
            continue
        candidates.append(path)
    if not candidates:
        qualifiers = {
            "require_bc8": require_bc8,
            "exclude_bc8": exclude_bc8,
            "require_train_dev": require_train_dev,
        }
        raise FileNotFoundError(
            f"No BioRED/BioREDirect {split} PubTator file found under {root}; {qualifiers}"
        )
    return sorted(candidates, key=lambda path: (len(str(path)), str(path)))[0]


def discover_model_directory(root: str | Path) -> Path:
    root = Path(root)
    candidates = sorted({path.parent for path in root.rglob("config.json")})
    for candidate in candidates:
        if "bioredirect" in candidate.name.lower() or "biored" in candidate.name.lower():
            return candidate
    if candidates:
        return candidates[0]
    raise FileNotFoundError(f"No Hugging Face model directory containing config.json under {root}")


def prepare_official_assets(
    work_dir: str | Path,
    *,
    revision: str = "main",
    force_download: bool = False,
) -> dict[str, str]:
    work_dir = Path(work_dir)
    downloads = work_dir / "downloads"
    repository, commit = clone_bioredirect(work_dir / "BioREDirect", revision=revision)

    dataset_zip = download_file(BIOREDIRECT_DATASET_URL, downloads / "bioredirect_datasets.zip", force=force_download)
    model_zip = download_file(BIOREDIRECT_MODEL_URL, downloads / "bioredirect_biored_pt.zip", force=force_download)

    dataset_root = work_dir / "official_dataset"
    model_root = work_dir / "official_model"
    if force_download or not dataset_root.exists() or not any(dataset_root.rglob("*.pubtator")):
        if dataset_root.exists():
            shutil.rmtree(dataset_root)
        safe_extract_zip(dataset_zip, dataset_root)
    if force_download or not model_root.exists() or not any(model_root.rglob("config.json")):
        if model_root.exists():
            shutil.rmtree(model_root)
        safe_extract_zip(model_zip, model_root)

    classic_train = discover_split_file(dataset_root, "train")
    classic_dev = discover_split_file(dataset_root, "dev")
    classic_test = discover_split_file(dataset_root, "test", exclude_bc8=True)
    official_train_dev = discover_split_file(
        dataset_root, "train", require_train_dev=True
    )
    official_bc8_test = discover_split_file(
        dataset_root, "test", require_bc8=True
    )
    model_dir = discover_model_directory(model_root)

    manifest = {
        "bioredirect_repository": BIOREDIRECT_REPOSITORY,
        "bioredirect_revision_requested": revision,
        "bioredirect_commit": commit,
        "dataset_url": BIOREDIRECT_DATASET_URL,
        "dataset_zip": str(dataset_zip),
        "dataset_sha256": sha256_file(dataset_zip),
        "model_url": BIOREDIRECT_MODEL_URL,
        "model_zip": str(model_zip),
        "model_sha256": sha256_file(model_zip),
        "classic_train_pubtator": str(classic_train),
        "classic_dev_pubtator": str(classic_dev),
        "classic_test_pubtator": str(classic_test),
        "official_train_dev_pubtator": str(official_train_dev),
        "official_development_pubtator": str(classic_test),
        "official_bc8_test_pubtator": str(official_bc8_test),
        "model_directory": str(model_dir),
    }
    manifest_path = work_dir / "official_assets_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def run_official_bioredirect_prediction(
    *,
    repository_dir: str | Path,
    python_bin: str | Path,
    model_dir: str | Path,
    test_pubtator: str | Path,
    output_dir: str | Path,
    batch_size: int = 8,
    cuda_device: str = "0",
) -> Path:
    repository_dir = Path(repository_dir)
    python_bin = Path(python_bin)
    model_dir = Path(model_dir)
    test_pubtator = Path(test_pubtator)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_test_pubtator = output_dir / "bioredirect_test.input.pubtator"
    source_text = test_pubtator.read_text(encoding="utf-8-sig", errors="replace").rstrip()
    normalized_test_pubtator.write_text(source_text + "\n\n", encoding="utf-8")
    test_tsv = output_dir / "bioredirect_test.tsv"
    pred_tsv = output_dir / "bioredirect_test.pred.tsv"
    pred_pubtator = output_dir / "bioredirect_test.pred.pubtator"
    env = {"CUDA_VISIBLE_DEVICES": cuda_device, "TOKENIZERS_PARALLELISM": "false"}

    run_command(
        [
            str(python_bin),
            "src/dataset_format_converter/convert_pubtator_2_tsv.py",
            "--in_pubtator_file",
            str(normalized_test_pubtator),
            "--out_tsv_file",
            str(test_tsv),
            "--in_bert_model",
            str(model_dir),
            "--task",
            "biored",
        ],
        cwd=repository_dir,
        env=env,
        log_path=output_dir / "01_convert_pubtator.log",
    )
    run_command(
        [
            str(python_bin),
            "src/run_exp.py",
            "--task_name",
            "biored",
            "--in_bioredirect_model",
            str(model_dir),
            "--in_test_tsv_file",
            str(test_tsv),
            "--out_pred_tsv_file",
            str(pred_tsv),
            "--batch_size",
            str(batch_size),
        ],
        cwd=repository_dir,
        env=env,
        log_path=output_dir / "02_model_inference.log",
    )
    run_command(
        [
            str(python_bin),
            "src/run_test_pred.py",
            "--to_pubtator3",
            "--in_test_pubtator_file",
            str(normalized_test_pubtator),
            "--in_test_tsv_file",
            str(test_tsv),
            "--in_pred_tsv_file",
            str(pred_tsv),
            "--out_pred_pubtator_file",
            str(pred_pubtator),
        ],
        cwd=repository_dir,
        env=env,
        log_path=output_dir / "03_convert_predictions.log",
    )
    if not pred_pubtator.exists() or pred_pubtator.stat().st_size == 0:
        raise RuntimeError("BioREDirect produced no PubTator prediction file")
    return pred_pubtator
