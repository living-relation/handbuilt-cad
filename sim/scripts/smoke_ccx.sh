#!/bin/bash
D=/home/daniel/projects/handbuilt-models/sim-tools/smoke/ccx
mkdir -p $D && cd $D
$HOME/simvenv/bin/python /home/daniel/projects/handbuilt-models/sim-tools/scripts/gen_ccx.py $D
ccx -i beam > beam_ccx.log 2>&1; echo "beam ccx exit $?"
ccx -i heat > heat_ccx.log 2>&1; echo "heat ccx exit $?"
python3 - <<'EOF'
import re
t=open('beam.dat').read().split('displacements')[1]
uz=[float(l.split()[3]) for l in t.strip().splitlines() if len(l.split())==4]
mx=max(abs(u) for u in uz); avg=sum(uz)/len(uz)
hc=open('beam_handcalc.txt').read()
tim=float(re.findall(r'= ([0-9.]+)', hc)[1]); eb=float(re.findall(r'= ([0-9.]+)', hc)[0])
s=f"Cantilever: ccx tip max |Uz| = {mx:.5f} mm, mean {abs(avg):.5f} mm\nHand calc: E-B {eb:.5f} mm, Timoshenko {tim:.5f} mm\nError vs Timoshenko: {100*(mx-tim)/tim:+.2f} %\n"
t=open('heat.dat').read().split('temperatures')[1]
T={int(l.split()[0]):float(l.split()[1]) for l in t.strip().splitlines() if len(l.split())==2}
import math
# nodes ordered i fastest, nx=10 -> node at x=25 is i=5 in first row: id 6
s+=f"Heat block: T(x=0)={T[1]:.2f}, T(x=25)={T[6]:.2f} (exact 60.00), T(x=50)={T[11]:.2f}\n"
open('RESULT.txt','w').write(s); print(s)
EOF