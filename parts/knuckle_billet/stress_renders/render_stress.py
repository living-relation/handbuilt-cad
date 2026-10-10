# pvpython: von Mises renders for the 4 final billet knuckles, colour capped at SF-2 allowable (503/2 = 251 MPa, 7075-T651)
from paraview.simple import *
import json
B = '/workspace/knuckle_billet'; O = B + '/stress_renders'; CAP = 251.0; SY = 503.0
V = [('best', 'Best', 'fin_best', 2.33), ('middle', 'Middle', 'fin_M5', 2.40), ('full-arm', 'Full-arm', 'fa2', 2.43), ('easy', 'Easy', 'fin_easy', 2.46)]
CASES = [('corner', 'cornering 1.8 g'), ('brake', 'braking 1.7 g')]
out = {}
for key, lab, stem, kg in V:
    S = json.load(open(f'{B}/final/{key}/fea_summary.json'))
    for case, cdesc in CASES:
        pk, rb = S[case]['peak'], S[case]['robust']; sf = SY / rb
        src = XMLUnstructuredGridReader(FileName=[f'{B}/iter/{stem}_{case}.vtu'])
        warp = WarpByVector(Input=src); warp.Vectors = ['POINTS', 'U_mm']; warp.ScaleFactor = 20.0
        v = CreateRenderView(); v.ViewSize = [1400, 1000]; v.Background = [1, 1, 1]; v.OrientationAxesVisibility = 1
        try: v.UseColorPaletteForBackground = 0
        except Exception: pass
        d = Show(warp, v); ColorBy(d, ('POINTS', 'vonMises_MPa'))
        lut = GetColorTransferFunction('vonMises_MPa'); lut.ApplyPreset('Jet', True); lut.RescaleTransferFunction(0.0, CAP)
        try: lut.AutomaticRescaleRangeMode = 'Never'
        except Exception: pass
        bar = GetScalarBar(lut, v); bar.Title = 'von Mises MPa (red = 251 limit)'; bar.ComponentTitle = ''
        bar.TitleColor = [0, 0, 0]; bar.LabelColor = [0, 0, 0]; bar.RangeLabelFormat = '%.0f'; bar.TitleFontSize = 18; bar.LabelFontSize = 16
        bar.ScalarBarLength = 0.5
        d.SetScalarBarVisibility(v, True)
        t = Text(Text=f"{lab} {kg:.2f} kg, {cdesc}, peak {rb:.0f} MPa, SF {sf:.2f}\n7075-T651, colour capped at 251 MPa (SF 2), deflection x20; local spike {pk:.0f} MPa at a sharp corner"); td = Show(t, v); td.Color = [0, 0, 0]; td.FontSize = 18
        for vn, pos in (('iso', [420, -380, 520]), ('back', [-380, -300, -420])):
            v.CameraPosition = pos; v.CameraFocalPoint = [-15, -5, 75]; v.CameraViewUp = [0, -1, 0]; v.ResetCamera(); v.CameraParallelProjection = 0
            GetActiveCamera().Zoom(1.05)
            fn = f'{O}/{key}_{case}_{vn}.png'; SaveScreenshot(fn, v, ImageResolution=[1400, 1000])
        fn = f'{O}/{key}_{case}_iso.png'
        out[f'{key}_{case}'] = dict(file=fn, peak_local=round(pk, 1), robust=round(rb, 1), SF=round(sf, 2))
        Delete(t); Delete(v); Delete(warp); Delete(src)
json.dump(out, open(f'{O}/summary.json', 'w'), indent=1); print('done')
