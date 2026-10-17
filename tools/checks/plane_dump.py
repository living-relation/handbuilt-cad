import sys,numpy as np
from build123d import *
from collections import defaultdict
s=import_step(sys.argv[1]).solids()[0]
lv=defaultdict(list)
for f in s.faces():
    if f.geom_type!=GeomType.PLANE: continue
    n=np.round(tuple(f.normal_at()),3); c=f.center()
    ax='XYZ'[int(np.argmax(abs(n)))]
    if abs(abs(n).max()-1)>1e-3: ax='oblique'
    bb=f.bounding_box()
    val={'X':c.X,'Y':c.Y,'Z':c.Z}.get(ax,0)
    lv[(ax,round(val,2))].append(f"n={n.tolist()} area={f.area:.0f} bb=({bb.min.X:.1f},{bb.min.Y:.1f},{bb.min.Z:.1f})-({bb.max.X:.1f},{bb.max.Y:.1f},{bb.max.Z:.1f})")
for k in sorted(lv):
    for x in lv[k]: print(k,x)
