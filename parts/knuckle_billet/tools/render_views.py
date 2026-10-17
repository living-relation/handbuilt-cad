# Generic (pvpython): 6 labelled orthographic plain-grey views + one sheet.
# Usage: pvpython tools/render_views.py <in.stl> <out_prefix> <title>
# Frame convention used for the knuckle: Z = hub axis (+Z inboard), -Y up, +X forward (RH part).
from paraview.simple import *
import sys
stl, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
src = STLReader(FileNames=[stl])
VIEWS = [('front', 'outboard face (looking +Z)', [0, 0, -1], [0, -1, 0]), ('back', 'inboard face (looking -Z)', [0, 0, 1], [0, -1, 0]),
         ('left', 'rear side (looking +X)', [-1, 0, 0], [0, -1, 0]), ('right', 'forward side (looking -X)', [1, 0, 0], [0, -1, 0]),
         ('top', 'top (looking down, +Y)', [0, -1, 0], [1, 0, 0]), ('bottom', 'bottom (looking up, -Y)', [0, 1, 0], [1, 0, 0])]
files = []
for name, desc, d, up in VIEWS:
    v = CreateRenderView(); v.ViewSize = [1000, 1000]; v.Background = [1, 1, 1]; v.OrientationAxesVisibility = 1
    try: v.UseColorPaletteForBackground = 0
    except Exception: pass
    s = Show(src, v); s.AmbientColor = s.DiffuseColor = [0.72, 0.74, 0.77]; s.Specular = 0.3
    t = Text(Text=f'{title} - {name.upper()}: {desc}'); td = Show(t, v); td.Color = [0, 0, 0]; td.FontSize = 13
    v.CameraParallelProjection = 1; v.CameraFocalPoint = [0, 0, 0]; v.CameraPosition = [1000 * c for c in d]; v.CameraViewUp = up
    v.ResetCamera(); GetActiveCamera().Zoom(1.05)
    f = f'{out}_{name}.png'; SaveScreenshot(f, v, ImageResolution=[1000, 1000]); files.append(f); Delete(t); Delete(v)
try:
    from PIL import Image
    ims = [Image.open(f).convert('RGB') for f in files]; W, H = ims[0].size
    sheet = Image.new('RGB', (3 * W, 2 * H), 'white')
    for i, im in enumerate(ims): sheet.paste(im, ((i % 3) * W, (i // 3) * H))
    sheet.save(f'{out}_sheet.png')
except Exception as ex: print('sheet: PIL missing in pvpython, run tools/sheet.py', ex)
