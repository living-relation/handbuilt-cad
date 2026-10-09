#!/bin/bash
# usage: run_iter.sh <stem> [smax]   (expects iter/<stem>.step)
set -e; cd /workspace/knuckle_billet; S=$1; M=${2:-3.5}
/workspace/kbvenv/bin/python mesh_step.py iter/$S.step iter/${S}_mesh.npz $M > iter/${S}_mesh.log 2>&1
/workspace/kbvenv/bin/python fea_iter.py iter $S > iter/${S}_deck.log 2>&1
(cd iter && OMP_NUM_THREADS=8 ccx -i $S > ${S}_ccx.log 2>&1)
/workspace/kbvenv/bin/python post_iter.py iter $S > iter/${S}_post.log 2>&1
echo DONE $S
