#!/bin/bash
# Recreate the simulation setup on a fresh WSL Ubuntu (26.04).
# Usage: bash sim-tools/scripts/install_sim_tools_wsl.sh   (asks for sudo)
# The original step-by-step install scripts are next to this one (apt1.sh, elmer.sh, of.sh, simvenv.sh)
# and the rollback lists are in sim-tools/rollback/.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

echo "== apt: CalculiX, Gmsh, ParaView, build tools"
sudo apt-get update
sudo apt-get install -y calculix-ccx gmsh paraview xvfb build-essential cmake gfortran \
  libblas-dev liblapack-dev libopenmpi-dev curl git python3-venv

echo "== OpenFOAM 14 (openfoam.org repo)"
if [ ! -d /opt/openfoam14 ]; then bash "$REPO/sim-tools/scripts/of.sh"; fi

echo "== Elmer FEM (built from source into /opt/elmer)"
if ! command -v ElmerSolver >/dev/null; then bash "$REPO/sim-tools/scripts/elmer.sh"; fi

echo "== uv + simvenv (~/simvenv)"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
[ -x "$HOME/simvenv/bin/python" ] || uv venv "$HOME/simvenv" --python 3.14
uv pip install --python "$HOME/simvenv/bin/python" -r "$REPO/requirements-sim.txt"

echo "== build venv (.venv)"
[ -x "$REPO/.venv/bin/python" ] || uv venv "$REPO/.venv" --python 3.13
uv pip install --python "$REPO/.venv/bin/python" -r "$REPO/requirements.txt"

echo "== smoke tests"
bash "$REPO/sim-tools/scripts/smoke_ccx.sh" || echo "ccx smoke test failed"
echo "Done. Load tools with: source $REPO/sim-tools/wsl-env.sh"
