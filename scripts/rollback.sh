#!/usr/bin/env bash
set -euo pipefail
TAG="${1:-}"
if [ -z "$TAG" ]; then
  echo "Usage: $0 deploy-YYYYMMDD-HHMM-<sha>"; exit 1
fi
if command -v gh >/dev/null 2>&1; then
  gh workflow run Rollback -f tag="$TAG"
  gh run watch --exit-status || true
fi
echo "Rolled back to: $TAG"
