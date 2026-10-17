from paraview.simple import *
import glob, os
REPO = os.environ.get('REPO') or os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
f = sorted(glob.glob(REPO + '/sim/smoke/ccx/beam_u*.vtu'))[-1]
r = XMLUnstructuredGridReader(FileName=[f])
w = WarpByVector(Input=r); w.Vectors = ['POINTS', 'U']; w.ScaleFactor = 50.0
v = GetActiveViewOrCreate('RenderView'); v.ViewSize = [1200, 600]
d = Show(w, v); ColorBy(d, ('POINTS', 'U', 'Magnitude')); d.SetScalarBarVisibility(v, True)
o = Show(r, v); o.SetRepresentationType('Wireframe'); o.Opacity = 0.3
v.CameraPosition = [50, -250, 60]; v.CameraFocalPoint = [50, 5, 0]; v.CameraViewUp = [0, 0, 1]; v.ResetCamera()
SaveScreenshot(REPO + '/sim/smoke/paraview/beam_displacement_x50.png', v, ImageResolution=[1200, 600])
print('screenshot saved from', f)
