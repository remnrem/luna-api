#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKOUT="${ROOT}/.luna-base-check"

rm -rf "${CHECKOUT}"
git clone https://github.com/remnrem/luna-base.git "${CHECKOUT}"

echo "luna-base remote: $(git -C "${CHECKOUT}" remote get-url origin)"
echo "luna-base branch: $(git -C "${CHECKOUT}" symbolic-ref --short HEAD)"
echo "luna-base revision: $(git -C "${CHECKOUT}" rev-parse HEAD)"
git -C "${CHECKOUT}" log -1 --format='luna-base commit: %h %cI %s'

if ! git -C "${CHECKOUT}" grep -n write_db HEAD -- lunapi/lunapi.h lunapi/lunapi.cpp; then
  echo "ERROR: fetched luna-base does not contain write_db()" >&2
  exit 1
fi

echo "OK: fetched luna-base contains write_db() declaration and implementation"
