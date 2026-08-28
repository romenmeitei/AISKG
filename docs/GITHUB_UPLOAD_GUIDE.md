# GitHub upload and release guide — AISKG v3.2.0

Target repository: `https://github.com/romenmeitei/AISKG`

The source ZIP is a complete repository tree. Do not commit the ZIP as one file and do not overwrite `main` directly.

## 1. Extract and verify

```bash
unzip AISKG_v3.2.0_GITHUB_READY_COMPLETE.zip
cd AISKG_v3.2.0_GITHUB_READY_COMPLETE
python -m pip install -e ".[dev,external-re]" --no-build-isolation
python verify_repository.py
pytest -q -m "not integration"
python scripts/verify_v3_1_2_release.py
python scripts/execute_v3_1_2_notebook_smoke.py
python scripts/verify_v3_2_0_release.py
python scripts/run_external_re_smoke.py
```

## 2. Create a fresh clone and branch

```bash
cd ..
git clone https://github.com/romenmeitei/AISKG.git AISKG-v3.2.0-upload
cd AISKG-v3.2.0-upload
git switch -c release/v3.2.0
cd ..
```

## 3. Copy the verified tree

Linux/macOS:

```bash
rsync -a --delete \
  --exclude='.git/' \
  --exclude='outputs/' \
  --exclude='.aiskg_work/' \
  --exclude='.pytest_cache/' \
  AISKG_v3.2.0_GITHUB_READY_COMPLETE/ AISKG-v3.2.0-upload/
```

Windows PowerShell:

```powershell
$source = (Resolve-Path ".\AISKG_v3.2.0_GITHUB_READY_COMPLETE").Path
$target = (Resolve-Path ".\AISKG-v3.2.0-upload").Path
robocopy $source $target /MIR /XD ".git" "outputs" ".aiskg_work" ".pytest_cache"
if ($LASTEXITCODE -gt 7) { throw "robocopy failed with code $LASTEXITCODE" }
Set-Location $target
```

## 4. Reverify inside the clone

Run the same six verification commands from step 1.

## 5. Commit and push

```bash
git status
git add -A
git commit -m "Release AISKG v3.2.0 external biomedical relation benchmark"
git push -u origin release/v3.2.0
```

Or run `bash scripts/upload_to_github.sh` / `.\scripts\upload_to_github.ps1` from inside the clone.

## 6. Open the pull request

```bash
gh pr create \
  --base main \
  --head release/v3.2.0 \
  --title "AISKG v3.2.0 external BioRED/BioREDirect benchmark" \
  --body-file RELEASE_NOTES_v3.2.0.md
```

Merge only after GitHub Actions is green. The workflow verifies the old release layers, the new external frozen result and public-export boundary, the offline external smoke test, and all 285 core checks.

## 7. Tag and release

```bash
git switch main
git pull origin main
git tag -a v3.2.0 -m "AISKG v3.2.0 external biomedical relation benchmark"
git push origin v3.2.0
```

The tagged workflow publishes the core archive, v3.1.2 replay archive, public-safe external result ZIP and repository-native Colab notebook. Use `RELEASE_NOTES_v3.2.0.md` as the release description.

## 8. Zenodo

Create a new Zenodo version for tag `v3.2.0`. Update `CITATION.cff`, the software reference and manuscript only after Zenodo assigns the new version DOI. Never relabel the v3.1.2 DOI.

## 9. Files that must remain private

Do not upload the full `AISKG_External_RE_Benchmark_Results_v1_0.zip`, text-bearing `test_candidates_*.csv`, `error_analysis.csv`, PubTator representations, official BioRED/BioREDirect datasets, official source checkout or model weights.
