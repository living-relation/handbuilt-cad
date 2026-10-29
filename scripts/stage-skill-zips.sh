#!/bin/sh
# Stage skill zips under skills/ via git pathspecs (no shell glob: empty set is fine),
# then refuse anything else in the index.
set -eu
cd "$(git rev-parse --show-toplevel)"
git ls-files --others --modified --deleted --exclude-standard -- 'skills/*.zip' |
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    git add -- "$f"
  done
extra=$(git diff --cached --name-only | grep -vE '^skills/[^/]+\.zip$' || true)
if [ -n "$extra" ]; then
  echo "refusing to commit non-zip paths: $extra" >&2
  exit 1
fi
