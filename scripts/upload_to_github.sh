#!/usr/bin/env bash
set -euo pipefail
REPOSITORY_URL="${1:-https://github.com/romenmeitei/AISKG_Framework.git}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python verify_repository.py
if [[ ! -d .git ]]; then
  git init
  git branch -M main
fi

git add -A
if ! git diff --cached --quiet; then
  git commit -m "AISKG unified reproducibility framework v3.0.0"
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPOSITORY_URL"
else
  git remote add origin "$REPOSITORY_URL"
fi

git push -u origin main
echo "Upload complete. Check GitHub Actions before creating tag v3.0.0."
