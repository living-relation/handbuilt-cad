#!/bin/sh
# Pre-commit guard: blocks part/model files, archives, files over 1 MB, and .env files.
# Personal home paths are reported as warnings (blocking when .guard-strict exists).
# Exceptions: one path per line in .guard-allow (exact path match).
set -u
MAX=1048576
fail=0; warn=0
allow() { [ -f .guard-allow ] && grep -qxF "$1" .guard-allow; }
git diff --cached --name-only --diff-filter=ACMR -z | tr '\0' '\n' > "${TMPDIR:-/tmp}/guard.$$"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if allow "$f"; then continue; fi
  lc=$(printf '%s' "$f" | tr 'A-Z' 'a-z')
  case "$lc" in
    *.step|*.stp|*.stl|*.3mf|*.f3d|*.fcstd|*.ply|*.obj|*.iges|*.igs|*.brep|*.glb|*.zip|*.7z|*.npz|*.npy|*.frd|*.vtu)
      echo "guard: BLOCK part/model/archive file: $f"; fail=1; continue;;
  esac
  base=$(basename "$lc")
  case "$base" in
    .env|.env.*) case "$base" in .env.example|.env.template) ;; *) echo "guard: BLOCK env file: $f"; fail=1; continue;; esac;;
  esac
  size=$(git cat-file -s ":$f" 2>/dev/null || echo 0)
  if [ "$size" -gt "$MAX" ]; then echo "guard: BLOCK file over 1 MB ($size bytes): $f"; fail=1; continue; fi
  if git show ":$f" 2>/dev/null | grep -qE '/home/[a-z][a-z0-9_-]*/|C:[\\/]+Users[\\/]+[A-Za-z]'; then
    echo "guard: WARN personal home path in: $f"; warn=$((warn+1))
  fi
done < "${TMPDIR:-/tmp}/guard.$$"
rm -f "${TMPDIR:-/tmp}/guard.$$"
if [ "$warn" -gt 0 ] && [ -f .guard-strict ]; then echo "guard: BLOCK $warn file(s) with home paths (.guard-strict is on)"; fail=1; fi
[ "$warn" -gt 0 ] && echo "guard: $warn file(s) with home paths (warning only; see docs/PRE-PUBLIC-CHECKLIST.md or CONTRIBUTING)"
exit $fail
