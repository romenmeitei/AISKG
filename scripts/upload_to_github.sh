#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_URL="${1:-https://github.com/romenmeitei/AISKG.git}"
RELEASE_BRANCH="${2:-release/v3.1.2}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python verify_repository.py

if [[ ! -d .git ]]; then
  cat >&2 <<'MSG'
Safety stop: this upload helper must be run inside an existing clone of
https://github.com/romenmeitei/AISKG after the verified v3.1.2 files have
been copied into that clone. It will not initialise or overwrite main.
See docs/GITHUB_UPLOAD_GUIDE.md.
MSG
  exit 2
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPOSITORY_URL"
else
  git remote add origin "$REPOSITORY_URL"
fi

git fetch origin --prune
current_branch="$(git branch --show-current)"
if [[ "$current_branch" != "$RELEASE_BRANCH" ]]; then
  if git show-ref --verify --quiet "refs/heads/$RELEASE_BRANCH"; then
    git switch "$RELEASE_BRANCH"
  else
    git switch -c "$RELEASE_BRANCH"
  fi
fi

git add -A
if git diff --cached --quiet; then
  echo "No staged changes; nothing to commit."
else
  git commit -m "Release AISKG v3.1.2 corrected manuscript reproducibility package"
fi

git push -u origin "$RELEASE_BRANCH"
echo "Release branch uploaded: $RELEASE_BRANCH"
echo "Open a pull request to main and merge only after GitHub Actions passes."
