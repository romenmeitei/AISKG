param(
    [string]$RepositoryUrl = "https://github.com/romenmeitei/AISKG.git",
    [string]$ReleaseBranch = "release/v3.1.2"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python verify_repository.py
if ($LASTEXITCODE -ne 0) { throw "Repository verification failed" }

if (-not (Test-Path ".git")) {
    throw @"
Safety stop: this upload helper must be run inside an existing clone of
https://github.com/romenmeitei/AISKG after the verified v3.1.2 files have
been copied into that clone. It will not initialise or overwrite main.
See docs/GITHUB_UPLOAD_GUIDE.md.
"@
}

$remote = git remote get-url origin 2>$null
if (-not $remote) {
    git remote add origin $RepositoryUrl
} elseif ($remote -ne $RepositoryUrl) {
    git remote set-url origin $RepositoryUrl
}

git fetch origin --prune
$currentBranch = (git branch --show-current).Trim()
if ($currentBranch -ne $ReleaseBranch) {
    git show-ref --verify --quiet "refs/heads/$ReleaseBranch"
    if ($LASTEXITCODE -eq 0) {
        git switch $ReleaseBranch
    } else {
        git switch -c $ReleaseBranch
    }
}

git add -A
$staged = git diff --cached --name-only
if ($staged) {
    git commit -m "Release AISKG v3.1.2 corrected manuscript reproducibility package"
} else {
    Write-Host "No staged changes; nothing to commit."
}

git push -u origin $ReleaseBranch
Write-Host "Release branch uploaded: $ReleaseBranch"
Write-Host "Open a pull request to main and merge only after GitHub Actions passes."
