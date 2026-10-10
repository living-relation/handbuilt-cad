#!/bin/bash
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"; export REPO
B=$REPO
D=$B/sim-tools/smoke/gmsh; mkdir -p $D && cd $D
cp $B/pcv_adapter/pcv_adapter.step .
gmsh pcv_adapter.step -3 -format msh4 -clmax 1.5 -o pcv_adapter.msh > gmsh.log 2>&1; echo "gmsh exit $?"
$HOME/simvenv/bin/python - <<'EOF' | tee RESULT.txt
import meshio
m = meshio.read('pcv_adapter.msh')
print('gmsh meshed PCV adapter STEP:', len(m.points), 'nodes;', {c.type: len(c.data) for c in m.cells})
tet = [c for c in m.cells if c.type == 'tetra']
meshio.write('pcv_adapter_tets.vtu', meshio.Mesh(m.points, tet))
EOF
P=$B/sim-tools/smoke/paraview; mkdir -p $P && cd $B/sim-tools/smoke/ccx
sed '/^\*EL FILE/,+1d' beam.inp > beam_u.inp && ccx -i beam_u > beam_u_ccx.log 2>&1
$HOME/simvenv/bin/ccx2paraview beam_u.frd vtu > $P/ccx2paraview.log 2>&1; echo "ccx2paraview exit $?"
ls $B/sim-tools/smoke/ccx/*.vtu
cat > $P/shot.py <<'EOF'
from paraview.simple import *
import glob, os
f = sorted(glob.glob(os.environ['REPO'] + '/sim-tools/smoke/ccx/beam_u*.vtu'))[-1]
r = XMLUnstructuredGridReader(FileName=[f])
w = WarpByVector(Input=r); w.Vectors = ['POINTS', 'U']; w.ScaleFactor = 50.0
v = GetActiveViewOrCreate('RenderView'); v.ViewSize = [1200, 600]
d = Show(w, v); ColorBy(d, ('POINTS', 'U', 'Magnitude')); d.SetScalarBarVisibility(v, True)
o = Show(r, v); o.SetRepresentationType('Wireframe'); o.Opacity = 0.3
v.CameraPosition = [50, -250, 60]; v.CameraFocalPoint = [50, 5, 0]; v.CameraViewUp = [0, 0, 1]; v.ResetCamera()
SaveScreenshot(os.environ['REPO'] + '/sim-tools/smoke/paraview/beam_displacement_x50.png', v, ImageResolution=[1200, 600])
print('screenshot saved from', f)
EOF
cd $P; xvfb-run -a pvpython shot.py > pvpython.log 2>&1; echo "pvpython exit $?"; tail -3 pvpython.log
pvpython --version 2>/dev/null | head -1