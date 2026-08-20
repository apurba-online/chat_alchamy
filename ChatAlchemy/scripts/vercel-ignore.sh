#!/usr/bin/env bash
set -e

if [ -z "${VERCEL_GIT_PREVIOUS_SHA:-}" ]; then
  exit 1
fi

git diff --quiet "$VERCEL_GIT_PREVIOUS_SHA" HEAD -- \
  src \
  api \
  backend/chatalchemy \
  backend/requirements.txt \
  public \
  package.json \
  package-lock.json \
  index.html \
  vite.config.ts \
  tsconfig.json \
  tsconfig.app.json \
  tsconfig.node.json \
  vercel.json \
  scripts/vercel-ignore.sh \
  .vercel-research-preview-trigger
