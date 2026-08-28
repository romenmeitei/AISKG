#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_URL="${1:-https://github.com/romenmeitei/AISKG.git}"
RELEASE_BRANCH="${2:-release/v3.2.0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python verify_repository.py
python scripts/verify_v3_2_0_release.py

if [[ ! -d .git ]]; then
  cat >&2 <<'MSG'
Safety stop: run this helper only inside an existing AISKG Git clone after
copying the verified v3.2.0 repository tree. It never initializes or pushes
main directly. See docs/GITHUB_UPLOAD_GUIDE.md.
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
  git commit -m "Release AISKG v3.2.0 external biomedical relation benchmark"
fi

git push -u origin "$RELEASE_BRANCH"
echo "Release branch uploaded: $RELEASE_BRANCH"
echo "Open a pull request to main and merge only after GitHub Actions passes."
