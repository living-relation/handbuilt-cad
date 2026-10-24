#!/usr/bin/env bash
# Check that the handbuilt-cad WSL/Linux install is complete. Run by setup.sh as its last step; agents can run it
# any time:  bash scripts/verify-install.sh [--no-sim]
# Exits 1 with a list of what is missing. Read-only: it installs and changes nothing.
set -uo pipefail
cd "$(dirname "$0")/.."
SIM=1; for a in "$@"; do case $a in --no-sim) SIM=0;; *) echo "unknown option $a"; exit 2;; esac; done
missing=()
ok() { echo "  ok: $1"; }
miss() { echo "  MISSING: $1"; missing+=("$1"); }

# What a fresh non-interactive login shell sees (this is how agents call WSL: wsl bash -lc '...').
login() { env -i HOME="$HOME" USER="${USER:-$(id -un)}" TERM=dumb bash -lc "$1" 2>/dev/null; }

echo "verify: env vars in a non-interactive 'bash -lc'"
for v in CAD_HOME CAD_PY MODELS_DIR HBCAD_PARTS_HOME SIM_VENV; do
  val=$(login "printf %s \"\${$v:-}\"")
  if [ -n "$val" ]; then ok "$v=$val"; else miss "env var $v (not set in bash -lc; re-run setup.sh, or source ~/.config/handbuilt-cad/env.sh from your login file)"; fi
done
CAD_PY_L=$(login 'printf %s "${CAD_PY:-}"'); SIM_VENV_L=$(login 'printf %s "${SIM_VENV:-}"')

echo "verify: tools"
if p=$(login 'command -v uv'); then ok "uv ($p)"; else miss "uv on PATH in bash -lc (setup puts it in ~/.local/bin)"; fi
py=${CAD_PY_L:-${CAD_PY:-}}
if [ -n "$py" ] && "$py" -c 'import build123d' 2>/dev/null; then ok "CAD venv python + build123d ($py)"; else miss "CAD venv python with build123d (${py:-CAD_PY unset})"; fi

if [ "$SIM" = 1 ]; then
  for t in ccx gmsh pvpython; do
    if p=$(login "command -v $t"); then ok "$t ($p)"; else miss "$t (apt: see apt-sim.txt)"; fi
  done
  sv=${SIM_VENV_L:-${SIM_VENV:-$HOME/simvenv}}
  if [ -x "$sv/bin/python" ] && "$sv/bin/python" -c 'import gmsh, meshio, numpy' 2>/dev/null; then ok "sim venv ($sv, $("$sv/bin/python" -V 2>&1))"
  else miss "sim venv $sv (default ~/simvenv; python with gmsh, meshio, numpy from requirements-sim.txt)"; fi
else
  echo "  skipped: ccx, gmsh, pvpython, sim venv (--no-sim)"
fi

if [ ${#missing[@]} -gt 0 ]; then
  echo "verify: FAILED, ${#missing[@]} missing:" >&2
  for m in "${missing[@]}"; do echo "  - $m" >&2; done
  exit 1
fi
echo "verify: all OK"
