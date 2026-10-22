#!/usr/bin/env bash
# Runs the whole workflow on the sample bracket. From the repo root:  bash examples/bracket/run_all.sh
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"
R="$(cd ../.. && pwd)"; PY="$R/.venv/bin/python"; SIMPY="${SIM_VENV:-$HOME/simvenv}/bin/python"
echo "== 1. build the model";              "$PY" bracket.py
echo "== 2. interface check (holes)";       "$PY" "$R/tools/features.py" bracket.step --spec spec.json
echo "== 3. CNC check (setups, corners, walls)"; "$PY" "$R/tools/cnc_check.py" bracket.step --spec cnc_spec.json --strict
echo "== 4. six-view sheet";                "$PY" "$R/tools/views.py" bracket.step --six --name "Sample bracket" -o bracket_views.png
echo "== 5. interactive viewer";            "$PY" "$R/tools/viewer.py" bracket.step -o bracket_viewer.html
# FEA demo only: in a real job, run FEA only after the owner approves the geometry (unless they ask for early tests).
echo "== 6. strength check (500 N push on the top of the upright, base bottom held)"
# quick_fea refuses to write inside a git repo, so the results go outside it (override with FEA_OUT).
FEA_OUT="${FEA_OUT:-$(mktemp -d)/bracket_fea}"
"$SIMPY" "$R/tools/quick_fea.py" bracket.step --fix z:min --load z:max --force 500,0,0 --yield 276 --size 2.5 --out "$FEA_OUT"
echo "== done. Look at bracket_views.png and bracket_cnc.txt, open bracket_viewer.html, read $FEA_OUT/summary.json and MACHINING.md"
