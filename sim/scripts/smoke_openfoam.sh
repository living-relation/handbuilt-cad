#!/bin/bash
D=/home/daniel/projects/handbuilt-models/sim-tools/smoke/openfoam
mkdir -p $D
OFBASH=$(ls -d /opt/openfoam*/etc/bashrc | sort -V | tail -1)
source $OFBASH
echo "OpenFOAM: $WM_PROJECT $WM_PROJECT_VERSION ($OFBASH)"
# run in Linux home (fast FS), then copy results
W=$HOME/sim-runs/of-cavity; rm -rf $W; mkdir -p $W
CAV=$(find $FOAM_TUTORIALS -maxdepth 4 -type d -name cavity | grep -i incompressible | head -1)
echo "tutorial: $CAV"
cp -r $CAV/. $W/ 2>/dev/null; cd $W; [ -d cavity ] && cd cavity
blockMesh > log.blockMesh 2>&1; echo "blockMesh exit $?"
if command -v foamRun >/dev/null && [ -f system/controlDict ] && grep -q solver system/controlDict; then foamRun > log.solver 2>&1; else icoFoam > log.solver 2>&1; fi
echo "solver exit $?"
grep -E '^Time =' log.solver | tail -1
grep -E 'Solving for Ux|Solving for p' log.solver | tail -2
foamToVTK -latestTime > log.foamToVTK 2>&1; echo "foamToVTK exit $?"
tail -n 3 log.solver
cp log.* $D/; cp -r system $D/; ls -d [0-9]* | tail -1 | xargs -I{} cp -r {} $D/