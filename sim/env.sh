# Source this to load the toolkit:   source sim-tools/env.sh
# Works from any folder; finds the repo from this file's location.
export HBM="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SIM="$HBM"
export SIM_VENV="${SIM_VENV:-$HOME/simvenv}"
_of=$(ls -d /opt/openfoam*/etc/bashrc 2>/dev/null | sort -V | tail -1)
case $- in *u*) _hbm_u=1; set +u;; *) _hbm_u=;; esac   # OpenFOAM bashrc needs nounset off
[ -n "$_of" ] && source "$_of"
[ -n "$_hbm_u" ] && set -u
[ -f "$SIM_VENV/bin/activate" ] && source "$SIM_VENV/bin/activate"
alias hbm-py="$HBM/.venv/bin/python"
echo "toolkit loaded: HBM=$HBM  (models: \$HBM/.venv/bin/python, sim: $SIM_VENV)"
