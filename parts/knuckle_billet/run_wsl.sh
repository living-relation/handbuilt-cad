#!/bin/bash
# run the CalculiX loop for billet iterations inside WSL (detached), using ~/simvenv
cd ~/projects/handbuilt-cad/parts/knuckle_billet || exit 1
source ~/projects/handbuilt-cad/sim/wsl-env.sh > /dev/null 2>&1 || source ~/simvenv/bin/activate
echo "python=$(which python) ccx=$(which ccx)"; python -c 'import gmsh, numpy, meshio, scipy; print("mods ok", gmsh.__version__)' || exit 2
for S in "$@"; do
  python mesh_step.py iter/$S.step iter/${S}_mesh.npz 5.0 > iter/${S}_mesh.log 2>&1 && python fea_iter.py iter $S > iter/${S}_deck.log 2>&1 && \
  (cd iter && OMP_NUM_THREADS=8 ccx -i $S > ${S}_ccx.log 2>&1) && python post_iter.py iter $S > iter/${S}_post.log 2>&1 && echo "DONE $S" || echo "FAIL $S"
done
