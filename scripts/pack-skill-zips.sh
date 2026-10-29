#!/usr/bin/env bash
# Optional: rebuild Claude-importable zips in skills/<name>.zip (CI does this on PRs).
# Usage: bash scripts/pack-skill-zips.sh [--no-check]
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${CAD_PY:-python3}" scripts/pack_skill_zips.py "$@"
