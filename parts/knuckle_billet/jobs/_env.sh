# sourced by the job scripts: cd into the run folder and load the sim tools
R=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "${KB_RUN:?set KB_RUN to the run folder}" || exit 1
source "$R/sim/wsl-env.sh" >/dev/null 2>&1 || source ~/simvenv/bin/activate
