#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
cd "$ROOT/web/e2e"
if [ ! -d node_modules/@playwright/test ]; then
  pnpm install
  pnpm exec playwright install chromium
fi
node record-backup.mjs
