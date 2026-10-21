#!/bin/bash
# fea_run.sh <stem>   (needs iter/<stem>_mesh.npz in $KB_RUN; ZP env optional)
source "$(dirname "$0")/_env.sh"; S=$1
python fea_iter.py iter $S > iter/${S}_deck.log 2>&1 && (cd iter && OMP_NUM_THREADS=8 ccx -i $S > ${S}_ccx.log 2>&1) && python post_iter.py iter $S > iter/${S}_post.log 2>&1 && echo DONE $S || echo FAIL $S
