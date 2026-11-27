#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
node "$ROOT/scripts/demo/scan-external.mjs"
cd "$ROOT/web/e2e"
if [ ! -d node_modules/@playwright/test ]; then
  pnpm install
  pnpm exec playwright install chromium
fi
pnpm exec playwright test offline.spec.ts
