#!/bin/bash
J=$(cd "$(dirname "$0")" && pwd); source "$J/_env.sh"
for F in middle best fullarm easy; do python mesh_step.py iter/$F.step iter/${F}_mesh.npz 3.5 > iter/${F}_mesh.log 2>&1 & done; wait
xargs -P 3 -L 1 bash "$J/pos_job.sh" < "$J/jobs17.txt"
echo ALLDONE
