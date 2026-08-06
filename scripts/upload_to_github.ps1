param(
    [string]$RepositoryUrl = "https://github.com/romenmeitei/AISKG_Framework.git"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python verify_repository.py
if ($LASTEXITCODE -ne 0) { throw "Repository verification failed" }

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

git add -A
$changes = git status --porcelain
if ($changes) {
    git commit -m "AISKG unified reproducibility framework v3.0.0"
}

$remote = git remote get-url origin 2>$null
if (-not $remote) {
    git remote add origin $RepositoryUrl
} elseif ($remote -ne $RepositoryUrl) {
    git remote set-url origin $RepositoryUrl
}

git push -u origin main
Write-Host "Upload complete. Check GitHub Actions before creating tag v3.0.0."
