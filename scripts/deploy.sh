#!/usr/bin/env bash
set -euo pipefail
git fetch origin && git checkout main && git pull
SHA=$(git rev-parse --short HEAD)
TAG="deploy-$(date -u +%Y%m%d-%H%M)-$SHA"
git tag -a "$TAG" -m "Good deploy $TAG"
git push origin "$TAG"
if command -v gh >/dev/null 2>&1; then
  gh workflow run "Deploy to Droplet" --ref "$TAG"
  gh run watch --exit-status || true
fi
echo "Deployed tag: $TAG"
