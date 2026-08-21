# GitHub upload and release guide — AISKG v3.1.2

The target repository is:

```text
https://github.com/romenmeitei/AISKG
```

This package is a complete repository tree, not a patch. Use a release branch and pull request; do not push the ZIP itself or overwrite `main` directly.

## 1. Extract and verify the source package

Extract `AISKG_v3.1.2_GITHUB_READY_COMPLETE.zip` to a separate directory, then run:

```bash
cd AISKG_v3.1.2_GITHUB_READY_COMPLETE
python -m pip install -e ".[dev]" --no-build-isolation
python verify_repository.py
pytest -q -m "not integration"
python scripts/verify_v3_1_2_release.py
python scripts/execute_v3_1_2_notebook_smoke.py
```

The complete frozen integration test is optional locally because it is also executed in GitHub Actions:

```bash
pytest -q -m integration
```

## 2. Create a fresh clone and release branch

Create the clone beside—not inside—the extracted package:

```bash
git clone https://github.com/romenmeitei/AISKG.git AISKG-v3.1.2-upload
cd AISKG-v3.1.2-upload
git switch -c release/v3.1.2
```

## 3. Copy the verified repository tree into the clone

### Linux or macOS

Run from the parent directory containing both folders:

```bash
rsync -a --delete \
  --exclude='.git/' \
  --exclude='outputs/' \
  --exclude='.aiskg_work/' \
  --exclude='.pytest_cache/' \
  AISKG_v3.1.2_GITHUB_READY_COMPLETE/ AISKG-v3.1.2-upload/
```

### Windows PowerShell

Run from the parent directory containing both folders. `robocopy` success codes 0–7 are normal:

```powershell
$source = (Resolve-Path ".\AISKG_v3.1.2_GITHUB_READY_COMPLETE").Path
$target = (Resolve-Path ".\AISKG-v3.1.2-upload").Path
robocopy $source $target /MIR /XD ".git" "outputs" ".aiskg_work" ".pytest_cache"
if ($LASTEXITCODE -gt 7) { throw "robocopy failed with code $LASTEXITCODE" }
Set-Location $target
```

## 4. Reverify inside the clone

```bash
python -m pip install -e ".[dev]" --no-build-isolation
python verify_repository.py
pytest -q -m "not integration"
python scripts/verify_v3_1_2_release.py
python scripts/execute_v3_1_2_notebook_smoke.py
```

## 5. Commit and push the release branch

Manual route:

```bash
git status
git add -A
git commit -m "Release AISKG v3.1.2 corrected manuscript reproducibility package"
git push -u origin release/v3.1.2
```

The safe helper scripts may be used instead after the package is inside the clone:

```bash
bash scripts/upload_to_github.sh
```

or:

```powershell
.\scripts\upload_to_github.ps1
```

Both helpers refuse a non-Git directory and push only `release/v3.1.2`.

## 6. Open and merge a pull request

Open a pull request from `release/v3.1.2` to `main`. Confirm that GitHub Actions passes:

- source-manifest verification;
- non-integration tests;
- corrected additional-analysis verification;
- clean-directory master-notebook execution;
- complete frozen core pipeline and 285/285 expected-result assertions; and
- generation of both core and corrected-analysis archives.

Merge only after the workflow is green.

## 7. Run the public Colab notebook

Open the Colab badge in `README.md`, choose **Runtime → Run all**, and confirm creation of:

- `ADDITIONAL_ANALYSES_SUCCESS.txt`;
- `COMBINED_REPRODUCIBILITY_MANIFEST.json`;
- `SHA256SUMS.txt`; and
- `AISKG_v3.1.2_additional_analyses_reproduced.zip`.

## 8. Create the tagged GitHub release

After merging:

```bash
git switch main
git pull origin main
git tag -a v3.1.2 -m "AISKG v3.1.2 corrected manuscript reproducibility release"
git push origin v3.1.2
```

Use `RELEASE_NOTES_v3.1.2.md` as the release description. The included tagged-release workflow builds and attaches the frozen core archive and corrected additional-analysis archive.

## 9. Archive a new Zenodo version

Create a new Zenodo version for tag `v3.1.2`. Add the newly minted version DOI to `CITATION.cff`, the software citation, and the manuscript. The prior DOI `10.5281/zenodo.21817891` remains the archived base-release DOI until Zenodo confirms the new version record.

## 10. Do not publish superseded artifacts

Do not upload the unpublished v3.1.0 draft, failed-run benchmark tables/logs, old empty-output files, or any result that represents missing PubTator relation objects as F1 = 0.
