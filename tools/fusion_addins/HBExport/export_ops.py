"""Fusion-side export work. Separate from the UI so it can be driven from a script or test."""
import os
import adsk.core
import adsk.fusion

from . import export_core as core


def _plan_msg(e):
    s = str(e)
    if 'restricted' in s:
        return 'blocked by your Fusion plan (' + s.splitlines()[0] + ')'
    return s.splitlines()[0] if s else repr(e)


def dxf_from(entity, path):
    """Write a DXF from a sketch, or from a planar face via a temporary projected sketch."""
    sk = adsk.fusion.Sketch.cast(entity)
    if sk:
        return sk.saveAsDXF(path)
    face = adsk.fusion.BRepFace.cast(entity)
    if not face:
        raise ValueError('select a sketch or a flat face for DXF')
    if not isinstance(face.geometry, adsk.core.Plane):
        raise ValueError('the selected face is not flat')
    comp = face.body.parentComponent
    if face.assemblyContext:
        face = face.nativeObject
    tmp = comp.sketches.add(face)
    try:
        tmp.project(face)
        return tmp.saveAsDXF(path)
    finally:
        tmp.deleteMe()


def export(design, keys, folder, base, comp=None, occ=None, dxf_entity=None):
    """Export the chosen formats. comp/occ default to the root. Returns {key: (ok, path_or_error)}."""
    em = design.exportManager
    comp = comp or design.rootComponent
    mesh_target = occ or comp
    paths = core.target_paths(folder, base, keys)
    os.makedirs(folder, exist_ok=True)
    results = {}
    for k, p in paths.items():
        try:
            if k == 'dxf':
                if dxf_entity is None:
                    raise ValueError('no face or sketch selected')
                ok = dxf_from(dxf_entity, p)
            else:
                if k == 'step':
                    opt = em.createSTEPExportOptions(p, comp)
                elif k == 'iges':
                    opt = em.createIGESExportOptions(p, comp)
                elif k == 'sat':
                    opt = em.createSATExportOptions(p, comp)
                elif k == 'f3d':
                    opt = em.createFusionArchiveExportOptions(p, comp)
                elif k == 'stl':
                    opt = em.createSTLExportOptions(mesh_target, p)
                elif k == '3mf':
                    opt = em.createC3MFExportOptions(mesh_target, p)
                ok = em.execute(opt)
            results[k] = (bool(ok) and os.path.exists(p), p if ok else 'export returned False')
        except Exception as e:  # report every failure, never stop the batch
            results[k] = (False, _plan_msg(e))
    return results
