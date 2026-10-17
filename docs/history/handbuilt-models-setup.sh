#!/usr/bin/env bash
# One-step setup for the handbuilt-models CAD toolkit (Linux or Windows WSL Ubuntu).
# Safe to re-run: anything already installed is detected and skipped.
#
#   bash setup.sh            Python venvs + CalculiX/Gmsh/ParaView (asks for sudo if something is missing)
#   bash setup.sh --python   Python venvs only (no sudo, no apt)
#   bash setup.sh --full     also OpenFOAM (CFD) and Elmer (heat/multiphysics, ~15 min build)
#   bash setup.sh --check    only report what is installed
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_VENV="${SIM_VENV:-$HOME/simvenv}"
MODE="${1:-default}"
export PATH="$HOME/.local/bin:$PATH"
G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; N=$'\e[0m'
ok(){ echo "${G}[ok]${N}   $*"; }; warn(){ echo "${Y}[skip]${N} $*"; }; bad(){ echo "${R}[fail]${N} $*"; }
have(){ command -v "$1" >/dev/null 2>&1; }

check(){
  echo; echo "== What is installed"
  if [ -x "$REPO/.venv/bin/python" ] && "$REPO/.venv/bin/python" -c "import build123d,trimesh" 2>/dev/null; then
    ok "model venv  $REPO/.venv  (build123d $("$REPO/.venv/bin/python" -c 'import build123d;print(build123d.__version__)'))"
  else bad "model venv  missing  -> bash setup.sh --python"; fi
  if [ -x "$SIM_VENV/bin/python" ] && "$SIM_VENV/bin/python" -c "import gmsh,meshio" 2>/dev/null; then ok "sim venv    $SIM_VENV  (gmsh $("$SIM_VENV/bin/python" -c 'import gmsh;print(gmsh.__version__)'))"
  else bad "sim venv    missing  -> bash setup.sh --python"; fi
  have ccx && ok "CalculiX    $(command -v ccx)" || bad "CalculiX    missing  -> bash setup.sh"
  have gmsh && ok "Gmsh        $(gmsh --version 2>&1 | head -1)" || warn "Gmsh app    missing (the Python gmsh in the sim venv is enough for the tools)"
  have pvpython && ok "ParaView    $(command -v pvpython)" || warn "ParaView    missing (optional, for fancy result pictures)"
  ls -d /opt/openfoam*/etc/bashrc >/dev/null 2>&1 && ok "OpenFOAM    $(ls -d /opt/openfoam* | sort -V | tail -1)" || warn "OpenFOAM    not installed (optional, bash setup.sh --full)"
  have ElmerSolver && ok "Elmer       $(command -v ElmerSolver)" || warn "Elmer       not installed (optional, bash setup.sh --full)"
  have ollama && ok "Ollama      $(command -v ollama)" || warn "Ollama      not found (optional local AI helper)"
}

python_part(){
  echo "== Python environments"
  have python3 || { bad "python3 not found. On Ubuntu: sudo apt install python3 python3-venv"; exit 1; }
  if ! have uv; then echo "installing uv (fast Python installer) into ~/.local/bin"; curl -LsSf https://astral.sh/uv/install.sh | sh || { bad "could not install uv"; exit 1; }; fi
  ok "uv $(uv --version | cut -d' ' -f2)"
  [ -x "$REPO/.venv/bin/python" ] || uv venv "$REPO/.venv" --python 3.13 || { bad "could not make .venv"; exit 1; }
  uv pip install --quiet --python "$REPO/.venv/bin/python" -r "$REPO/requirements.txt" && ok "model venv ready ($REPO/.venv)" || bad "model venv install failed"
  [ -x "$SIM_VENV/bin/python" ] || uv venv "$SIM_VENV" --python 3.13 || { bad "could not make $SIM_VENV"; exit 1; }
  REQ="$REPO/requirements-sim.txt"
  if [ "$(uname -m)" != "x86_64" ]; then grep -v -E '^pypardiso' "$REQ" > /tmp/hbm-req-sim.txt; REQ=/tmp/hbm-req-sim.txt; warn "pypardiso needs x86_64; skipped"; fi
  uv pip install --quiet --python "$SIM_VENV/bin/python" -r "$REQ" && ok "sim venv ready ($SIM_VENV)" || bad "sim venv install failed"
}

system_part(){
  echo "== Simulation programs (apt)"
  if ! have apt-get; then warn "not a Debian/Ubuntu system: install CalculiX (ccx), Gmsh and ParaView with your package manager"; return; fi
  PKGS=()
  have ccx || PKGS+=(calculix-ccx)
  have gmsh || PKGS+=(gmsh)
  have pvpython || PKGS+=(paraview)
  have xvfb-run || PKGS+=(xvfb)
  if [ ${#PKGS[@]} -eq 0 ]; then ok "CalculiX, Gmsh, ParaView, xvfb already installed"; else
    echo "installing: ${PKGS[*]} (needs your password)"
    sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${PKGS[@]}" && ok "installed ${PKGS[*]}" || bad "apt install failed"
  fi
  if [ "$MODE" = "--full" ]; then
    ls -d /opt/openfoam*/etc/bashrc >/dev/null 2>&1 && ok "OpenFOAM already installed" || sudo bash "$REPO/sim-tools/scripts/of.sh"
    have ElmerSolver && ok "Elmer already installed" || sudo bash "$REPO/sim-tools/scripts/elmer.sh"
  fi
}

case "$MODE" in
  --check) check ;;
  --python) python_part; check ;;
  default|--full) python_part; system_part; check ;;
  -h|--help) sed -n 2,9p "$0" ;;
  *) echo "unknown option $MODE"; sed -n 2,9p "$0"; exit 2 ;;
esac
echo; echo "Next: source sim-tools/env.sh   then try   bash examples/bracket/run_all.sh"
