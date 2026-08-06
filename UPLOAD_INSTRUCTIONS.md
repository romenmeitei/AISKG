# Upload instructions

Use the detailed instructions in `docs/GITHUB_UPLOAD_GUIDE.md`.

For Windows PowerShell, after creating the empty GitHub repository:

```powershell
cd "C:\path\to\AISKG_Framework_v3.0.0_GITHUB_READY"
python verify_repository.py
powershell -ExecutionPolicy Bypass -File .\scripts\upload_to_github.ps1
```

For Linux/macOS:

```bash
cd /path/to/AISKG_Framework_v3.0.0_GITHUB_READY
python verify_repository.py
./scripts/upload_to_github.sh
```

Do not upload the source ZIP as a single GitHub file. Extract it and commit the directory contents so the Colab notebook and GitHub Actions can access the files at their expected paths.
