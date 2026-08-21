# Upload instructions — AISKG v3.1.2

## Verify the extracted package

```bash
cd AISKG_v3.1.2_GITHUB_READY_COMPLETE
python -m pip install -e ".[dev]" --no-build-isolation
python verify_repository.py
pytest -q -m "not integration"
python scripts/verify_v3_1_2_release.py
python scripts/execute_v3_1_2_notebook_smoke.py
```

The verifier must report 805 reviewer pairs, 22 direct disagreements, 92 adjudications, seven agreement dimensions, 23/95 and 26/52 pathway endpoints, and the corrected benchmark metrics.

## Upload through a release branch

Do not upload the ZIP as a single repository file and do not overwrite `main` directly.

```bash
git clone https://github.com/romenmeitei/AISKG.git AISKG-v3.1.2-upload
cd AISKG-v3.1.2-upload
git switch -c release/v3.1.2
```

Copy the contents of the extracted package into this clone while preserving `.git`, then run the verification commands again.

```bash
git add -A
git commit -m "Release AISKG v3.1.2 complete reviewer-level reproducibility package"
git push -u origin release/v3.1.2
```

After GitHub Actions passes, merge the pull request, update local `main`, and tag the merged commit:

```bash
git switch main
git pull origin main
git tag -a v3.1.2 -m "AISKG v3.1.2 complete reviewer-level reproducibility release"
git push origin v3.1.2
```

Create the GitHub release using `RELEASE_NOTES_v3.1.2.md`, then mint a new version-specific archive/DOI.

## Private files

Keep `AISKG_v3.1.2_PRIVATE_SOURCE_PROVENANCE.zip` outside the public repository. It contains untouched reviewer uploads and source provenance. The public repository already includes privacy-sanitized, content-equivalent reviewer workbooks.
