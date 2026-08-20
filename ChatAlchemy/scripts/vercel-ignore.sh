#!/usr/bin/env bash
set -u

# Vercel interprets exit 0 as "skip this build" and exit 1 as
# "continue with the deployment". Be deliberately conservative: if the
# previous successful deployment commit is unavailable in Vercel's shallow
# checkout, build instead of failing the deployment or skipping uncertain code.
if [ -z "${VERCEL_GIT_PREVIOUS_SHA:-}" ]; then
  exit 1
fi

if ! git cat-file -e "${VERCEL_GIT_PREVIOUS_SHA}^{commit}" 2>/dev/null; then
  exit 1
fi

if git diff --quiet "$VERCEL_GIT_PREVIOUS_SHA" HEAD -- \
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
  .vercel-research-preview-trigger; then
  # No release-relevant changes: skip the deployment.
  exit 0
fi

# Relevant changes (or a comparison error) should never block deployment.
exit 1
