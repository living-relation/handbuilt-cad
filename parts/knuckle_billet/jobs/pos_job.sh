#!/bin/bash
# pos_job.sh <final> <pos> <cases>
source "$(dirname "$0")/_env.sh"; F=$1; P=$2; C=$3; S=${F}_${P}
cp -n iter/${F}_mesh.npz iter/${S}_mesh.npz
POS=$P CASES=$C ZP=-77 python fea_iter.py iter $S > iter/${S}_deck.log 2>&1 && (cd iter && OMP_NUM_THREADS=5 ccx -i $S > ${S}_ccx.log 2>&1) && CASES=$C python post_iter.py iter $S > iter/${S}_post.log 2>&1 && python sum17.py iter $S >> sum.log 2>&1 && rm -f iter/$S.frd && echo DONE $S || echo FAIL $S
