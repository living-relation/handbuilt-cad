# Generic (pvpython): plain-grey parallel close-up of one region.
# Usage: pvpython tools/render_closeup.py part.stl out.png "title" fx,fy,fz dx,dy,dz ux,uy,uz half_height_mm
from paraview.simple import *
import sys
stl, out, title = sys.argv[1:4]; f, d, u = [[float(t) for t in a.split(',')] for a in sys.argv[4:7]]; hh = float(sys.argv[7])
v = CreateRenderView(); v.ViewSize = [1000, 1000]; v.Background = [1, 1, 1]; v.OrientationAxesVisibility = 1
try: v.UseColorPaletteForBackground = 0
except Exception: pass
s = Show(STLReader(FileNames=[stl]), v); s.AmbientColor = s.DiffuseColor = [0.72, 0.74, 0.77]; s.Specular = 0.3
t = Show(Text(Text=title), v); t.Color = [0, 0, 0]; t.FontSize = 13
v.CameraParallelProjection = 1; v.CameraFocalPoint = f; v.CameraPosition = [f[i] + 500 * d[i] for i in range(3)]; v.CameraViewUp = u; v.CameraParallelScale = hh
SaveScreenshot(out, v, ImageResolution=[1000, 1000])
