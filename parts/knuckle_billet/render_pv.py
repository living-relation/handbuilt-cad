# pvpython: von Mises renders of each case (two views), clipped colour range so the field is readable
from paraview.simple import *
import json, sys
D = '/workspace/knuckle_billet/baseline'
R = json.load(open(D + '/results.json'))
for case, r in R['cases'].items():
    src = XMLUnstructuredGridReader(FileName=[f'{D}/v4b_{case}.vtu'])
    warp = WarpByVector(Input=src); warp.Vectors = ['POINTS', 'U_mm']; warp.ScaleFactor = 20.0
    for view_name, pos, up in (('iso', [420, -380, 520], [0, -1, 0]), ('back', [-380, -300, -420], [0, -1, 0])):
        v = CreateRenderView(); v.ViewSize = [1400, 1000]; v.Background = [1, 1, 1]; v.OrientationAxesVisibility = 1
        try: v.UseColorPaletteForBackground = 0
        except Exception: pass
        d = Show(warp, v); ColorBy(d, ('POINTS', 'vonMises_MPa'))
        lut = GetColorTransferFunction('vonMises_MPa'); lut.ApplyPreset('Jet', True)
        top = max(r['vm_max'], 1.0); lut.RescaleTransferFunction(0.0, top)
        bar = GetScalarBar(lut, v); bar.Title = 'von Mises MPa'; bar.ComponentTitle = ''; bar.TitleColor = [0,0,0]; bar.LabelColor = [0,0,0]
        d.SetScalarBarVisibility(v, True)
        t = Text(Text=f"v4b baseline - {case}: max {r['vm_max']:.0f} MPa (excl. 3 mm at supports), deflection x20"); td = Show(t, v); td.Color = [0,0,0]; td.FontSize = 14
        v.CameraPosition = pos; v.CameraFocalPoint = [-15, -5, 75]; v.CameraViewUp = up; v.ResetCamera(); v.CameraParallelProjection = 0
        cam = GetActiveCamera(); cam.Zoom(1.15)
        SaveScreenshot(f'{D}/render_{case}_{view_name}.png', v, ImageResolution=[1400, 1000])
        Delete(t); Delete(v)
print('renders done')
