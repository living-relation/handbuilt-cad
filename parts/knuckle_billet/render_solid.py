# pvpython: plain shaded grey renders of the solid (no stress colours), iso + back
from paraview.simple import *
import sys
stl, out, label = sys.argv[1], sys.argv[2], sys.argv[3]
src = STLReader(FileNames=[stl])
for name, pos in (('iso', [420, -380, 520]), ('back', [-380, -300, -420])):
    v = CreateRenderView(); v.ViewSize = [1400, 1000]; v.Background = [1, 1, 1]
    try: v.UseColorPaletteForBackground = 0
    except Exception: pass
    d = Show(src, v); d.AmbientColor = d.DiffuseColor = [0.72, 0.74, 0.77]; d.Specular = 0.35; d.SpecularPower = 40
    t = Text(Text=label); td = Show(t, v); td.Color = [0, 0, 0]; td.FontSize = 14
    v.CameraPosition = pos; v.CameraFocalPoint = [-15, -5, 75]; v.CameraViewUp = [0, -1, 0]; v.ResetCamera(); GetActiveCamera().Zoom(1.15)
    SaveScreenshot(f'{out}_{name}.png', v, ImageResolution=[1400, 1000]); Delete(t); Delete(v)
