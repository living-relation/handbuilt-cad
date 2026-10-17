#!/bin/sh
# Runs the pinned gitleaks on staged changes. Fails (never skips) if gitleaks is missing.
set -u
ROOT=$(git rev-parse --show-toplevel)
GL="$ROOT/.tools/gitleaks"; [ -x "$GL" ] || GL="$ROOT/.tools/gitleaks.exe"
[ -x "$GL" ] || GL=$(command -v gitleaks 2>/dev/null || true)
if [ -z "$GL" ] || [ ! -x "$GL" ]; then
  echo "gitleaks not found. Run setup.sh / setup.ps1 (installs the pinned gitleaks into .tools/)."; exit 1
fi
want=$(cat "$ROOT/.gitleaks-version")
have=$("$GL" version 2>/dev/null | tr -d 'v\r')
[ "$have" = "$want" ] || { echo "gitleaks $have found, $want pinned. Re-run setup."; exit 1; }
exec "$GL" git --pre-commit --staged --redact --no-banner -v "$ROOT"
