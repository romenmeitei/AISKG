# GitHub upload and release guide

The intended repository is:

```text
https://github.com/romenmeitei/AISKG_Framework
```

## 1. Create the repository

On GitHub, select **New repository**, use the name `AISKG_Framework`, choose **Public**, and do not initialize it with a README, license, or `.gitignore` because these files are already included.

## 2. Extract the release package

Extract `AISKG_Framework_v3.0.0_GITHUB_READY.zip`. Upload the contents of the extracted folder, not the ZIP as one file.

## 3. Push with Git on Windows PowerShell

```powershell
cd "C:\path\to\AISKG_Framework_v3.0.0_GITHUB_READY"
git init
git branch -M main
git add -A
git commit -m "AISKG unified reproducibility framework v3.0.0"
git remote add origin https://github.com/romenmeitei/AISKG_Framework.git
git push -u origin main
```

When GitHub requests authentication, use the browser sign-in flow or a personal access token; account passwords are not accepted for Git operations.

## 4. Confirm GitHub Actions

Open **Actions → AISKG continuous integration**. The workflow must pass:

- repository import and unit tests;
- complete frozen pipeline;
- 285/285 expected checks;
- run-directory verification;
- release ZIP artifact upload.

## 5. Run the Colab notebook

Use the badge in `README.md` or the URL in `docs/COLAB_RUN_GUIDE.md`. Select **Runtime → Run all** and confirm `SUCCESS`.

## 6. Create the release

Create a GitHub release with:

```text
Tag: v3.0.0
Title: AISKG Framework v3.0.0
Target: the green main-branch commit
```

Attach the locally executed `AISKG_Framework_v3.0.0_Release.zip` as a release asset. Include the release notes from `RELEASE_NOTES_v3.0.0.md`.

## 7. Obtain a permanent DOI

Connect the repository to Zenodo, enable the repository, and create a new GitHub release if required by the archival workflow. Add the DOI to `CITATION.cff` and the manuscript software reference.

## 8. Keep historical repositories

Do not delete AISKG Section 1 or Section 2. Add a notice to each README that development has moved to the unified framework and retain their versioned releases for provenance.
