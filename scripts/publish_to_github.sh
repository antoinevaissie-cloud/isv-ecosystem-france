#!/usr/bin/env bash
set -euo pipefail

# Publish this project to a new GitHub repository and enable GitHub Pages (docs/).

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: GitHub CLI (gh) is not installed. Install: https://cli.github.com/" >&2
  exit 1
fi

REPO_ARG="${1:-}"
if [ -z "$REPO_ARG" ]; then
  read -r -p "Repository name (e.g., my-repo or owner/my-repo): " REPO_ARG
fi

VISIBILITY="${VISIBILITY:-public}" # or private
if [ "$VISIBILITY" != "public" ] && [ "$VISIBILITY" != "private" ]; then
  echo "VISIBILITY must be 'public' or 'private' (got: $VISIBILITY)" >&2
  exit 1
fi

echo "[1/6] Building data JSON…"
if [ -f scripts/extract_isv_profiles.py ]; then
  python3 scripts/extract_isv_profiles.py
else
  echo "Warning: scripts/extract_isv_profiles.py not found, skipping data build"
fi

echo "[2/6] Syncing web/ to docs/…"
mkdir -p docs
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete web/ docs/
else
  rm -rf docs/*
  cp -R web/* docs/
fi

echo "[3/6] Initializing git repo (if needed)…"
if [ ! -d .git ]; then
  git init
fi
git add -A
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  echo "Repo already has commits; creating a new one for changes (if any)."
  if ! git diff --cached --quiet; then
    git commit -m "Update: add docs/ static site for GitHub Pages"
  else
    echo "No changes to commit."
  fi
else
  git commit -m "Initial: ISV ecosystem site and extractor"
fi
git branch -M main

echo "[4/6] Creating GitHub repo and pushing…"
gh repo create "$REPO_ARG" --source=. --remote=origin --push -y --"$VISIBILITY"

REPO_FULL=$(gh repo view --json nameWithOwner -q .nameWithOwner)
DEFAULT_BRANCH=$(git symbolic-ref --short HEAD || echo main)

echo "[5/6] Enabling GitHub Pages from /docs on $DEFAULT_BRANCH…"
set +e
gh api --method POST "repos/$REPO_FULL/pages" \
  -H "Accept: application/vnd.github+json" \
  -f source[branch]="$DEFAULT_BRANCH" \
  -f source[path]="/docs"
POST_STATUS=$?
if [ $POST_STATUS -ne 0 ]; then
  gh api --method PUT "repos/$REPO_FULL/pages" \
    -H "Accept: application/vnd.github+json" \
    -f source[branch]="$DEFAULT_BRANCH" \
    -f source[path]="/docs"
fi
set -e

echo "[6/6] Fetching site URL…"
SITE_URL=$(gh api "repos/$REPO_FULL/pages" -q .html_url 2>/dev/null || true)
if [ -n "$SITE_URL" ] && [ "$SITE_URL" != "null" ]; then
  echo "Deployed: $SITE_URL"
else
  OWNER=$(gh repo view --json owner -q .owner.login)
  NAME=$(basename "$(git rev-parse --show-toplevel)")
  echo "Deployed. Expected URL: https://$OWNER.github.io/$NAME/"
  echo "If it doesn’t load immediately, wait ~60s and retry."
fi

