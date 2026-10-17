"""Shared helpers: load the scan in the Fairsolid part frame, render with VTK offscreen."""
import json, numpy as np, trimesh
RUN = r"C:\projects\active\fairsolid\runs\pedal_adapter"

def load_scan():
    m = trimesh.load(RUN + r"\10_clean.ply", process=False)
    fr = json.load(open(RUN + r"\20_frame.json"))
    R = np.array(fr["rotation"]); o = np.array(fr["origin"])
    v = (np.asarray(m.vertices) - o) @ R.T          # rigid only, no scale
    return trimesh.Trimesh(v, np.asarray(m.faces), process=False)

def render(meshes, path, views=("iso",), size=(900, 700), titles=None, scalar=None, cmap_range=None, bar_title=None, center=None, radius=None):
    """meshes: list of (trimesh, rgb or None). scalar: per-vertex array for first mesh."""
    import vtk
    from vtk.util import numpy_support as ns
    W, H = size
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.SetSize(W * len(views), H)
    allpts = np.vstack([m.vertices for m, _ in meshes]); c = allpts.mean(0) if center is None else np.asarray(center, float); r = np.linalg.norm(allpts - c, axis=1).max() if radius is None else radius
    dirs = {"iso": (1, -1.2, 0.9), "iso2": (-1, 1.2, 0.9), "top": (0, 0, 1), "bottom": (0, 0, -1), "front": (0, -1, 0), "back": (0, 1, 0),
            "right": (1, 0, 0), "left": (-1, 0, 0), "isob": (1, -1.2, -0.9), "isob2": (-1, 1.2, -0.9)}
    for i, vname in enumerate(views):
        ren = vtk.vtkRenderer(); ren.SetViewport(i / len(views), 0, (i + 1) / len(views), 1); ren.SetBackground(1, 1, 1)
        for k, (m, rgb) in enumerate(meshes):
            pts = vtk.vtkPoints(); pts.SetData(ns.numpy_to_vtk(np.ascontiguousarray(m.vertices, dtype=float), deep=True))
            f = np.hstack([np.full((len(m.faces), 1), 3), m.faces]).astype(np.int64).ravel()
            cells = vtk.vtkCellArray(); cells.SetCells(len(m.faces), ns.numpy_to_vtkIdTypeArray(f, deep=True))
            pd = vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(cells)
            nm = vtk.vtkPolyDataNormals(); nm.SetInputData(pd); nm.SetFeatureAngle(35); nm.Update()
            mp = vtk.vtkPolyDataMapper(); mp.SetInputConnection(nm.GetOutputPort())
            act = vtk.vtkActor(); act.SetMapper(mp)
            if k == 0 and scalar is not None:
                arr = ns.numpy_to_vtk(np.ascontiguousarray(scalar, dtype=float), deep=True); pd.GetPointData().SetScalars(arr); nm.Update()
                lut = vtk.vtkLookupTable(); lut.SetHueRange(0.66, 0.0); lut.SetNumberOfColors(256); lut.Build()
                mp.SetLookupTable(lut); mp.SetScalarRange(*cmap_range); mp.ScalarVisibilityOn()
                if i == len(views) - 1:
                    sb = vtk.vtkScalarBarActor(); sb.SetLookupTable(lut); sb.SetTitle(bar_title or ""); sb.SetNumberOfLabels(5)
                    sb.GetTitleTextProperty().SetColor(0, 0, 0); sb.GetLabelTextProperty().SetColor(0, 0, 0)
                    sb.SetWidth(0.12); sb.SetHeight(0.6); sb.SetPosition(0.86, 0.2); ren.AddViewProp(sb)
            else:
                mp.ScalarVisibilityOff(); act.GetProperty().SetColor(*(rgb or (0.75, 0.78, 0.82)))
                if rgb is not None and len(rgb) == 4: act.GetProperty().SetColor(*rgb[:3]); act.GetProperty().SetOpacity(rgb[3])
            act.GetProperty().SetSpecular(0.2); ren.AddActor(act)
        d = np.array(dirs[vname], float); d /= np.linalg.norm(d)
        cam = ren.GetActiveCamera(); cam.SetFocalPoint(*c); cam.SetPosition(*(c + d * r * 4))
        cam.SetViewUp(*((0, 1, 0) if vname in ("top", "bottom") else (0, 0, 1))); cam.SetParallelProjection(1); cam.SetParallelScale(r * 1.05)
        ren.ResetCameraClippingRange()
        t = vtk.vtkTextActor(); t.SetInput((titles[i] if titles else vname)); t.GetTextProperty().SetColor(0, 0, 0); t.GetTextProperty().SetFontSize(20); t.SetPosition(10, H - 30); ren.AddViewProp(t)
        rw.AddRenderer(ren)
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(path); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()

