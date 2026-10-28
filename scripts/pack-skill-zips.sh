#!/usr/bin/env bash
# Rebuild Claude-importable zips in skills/<name>.zip (same bytes as pack-skill-zips.ps1).
# Usage: bash scripts/pack-skill-zips.sh [--no-check]
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${CAD_PY:-python3}" scripts/pack_skill_zips.py "$@"
