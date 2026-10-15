"""Regressions for the pedal adapter crash (found 2026-10-08).

Stage 50 died on the pedal adapter scan with no usable error: OCCT raised
BRepSweep_Translation on one run and corrupted the heap (exit 0xC0000374) on
another. The chain was:

  1. Stage 20 put Z=0 on the LARGEST downward face. On a stepped part that is
     a shelf part-way up - on the pedal adapter, 21 mm of the part hung below
     it.
  2. Stage 50 pinned the bottom layer to Z=0 regardless, while the top of that
     layer had snapped onto the same plane, leaving a zero-thickness layer.
  3. Extruding a zero-length prism is undefined in OCCT.

The test part reproduces that shape: a wide plate (the largest downward face)
sitting on a narrower boss that reaches 20 mm lower. Built from CAD, so the
true dimensions are known exactly; true size is asserted, never rescaled.
"""
from pathlib import Path

import numpy as np
import pytest
import trimesh

from fairsolid.geom import Frame, normalisation_for
from fairsolid.primitives import extract_planes, extract_cylinders, dedupe_cylinders, noise_floor
from fairsolid.stages import s20_frame
from fairsolid.stages.s50_reconstruct import (
    MIN_LAYER_MM, merge_thin_layers, reconstruct, snap_layers,
)

PLATE = 70.0       # plate is PLATE x PLATE x PLATE_T, top at z = BOSS_H + PLATE_T
PLATE_T = 8.0
BOSS_D = 30.0      # boss hangs below the plate, from z = 0 to z = BOSS_H
BOSS_H = 20.0
BORE_D = 12.0      # bore runs through both


@pytest.fixture(scope="module")
def stepped(tmp_path_factory):
    import cadquery as cq

    d = tmp_path_factory.mktemp("stepped")
    part = (cq.Workplane("XY").circle(BOSS_D / 2).extrude(BOSS_H)
            .faces(">Z").workplane().rect(PLATE, PLATE).extrude(PLATE_T)
            .faces(">Z").workplane().circle(BORE_D / 2).cutThruAll())
    volume = part.val().Volume()
    stl = d / "nominal.stl"
    cq.exporters.export(part, str(stl), tolerance=0.01, angularTolerance=0.1)

    # process=True merges the STL's duplicated vertices, so the mesh is
    # watertight and slices into closed sections, as stage 10's output is.
    mesh = trimesh.load(stl, force="mesh", process=True)
    assert mesh.is_watertight
    mesh = mesh.subdivide_to_size(max_edge=1.0)
    rng = np.random.default_rng(3)
    mesh.vertices = mesh.vertices + rng.normal(0, 0.03, mesh.vertices.shape)
    scan = d / "scan.ply"
    mesh.export(scan)
    assert mesh.is_watertight
    return d, scan, mesh, volume


def _write_frame(path: Path, mesh: trimesh.Trimesh, origin) -> Path:
    R = np.eye(3)
    aligned = np.asarray(mesh.vertices) - np.asarray(origin, dtype=float)
    centre, scale = normalisation_for(
        np.array([aligned.min(axis=0), aligned.max(axis=0)]))
    Frame(rotation=R.tolist(), origin=list(map(float, origin)), centre=centre,
          scale=scale, units="mm", notes=["test frame"]).save(path)
    return path


def test_base_is_lowest_downward_face_not_largest(stepped):
    """Z=0 must land on the boss bottom, not on the larger plate underside."""
    _, _, mesh, _ = stepped
    planes = extract_planes(mesh)
    cyls = dedupe_cylinders(extract_cylinders(
        mesh, [np.array([0.0, 0.0, 1.0])], max_rms=3 * noise_floor(planes)))
    origin, note = s20_frame._pick_origin(mesh, np.eye(3), cyls, planes)
    assert abs(origin[2] - 0.0) < 0.1, (origin, note)
    # And the part therefore sits on the XY plane instead of hanging through it.
    z = np.asarray(mesh.vertices)[:, 2] - origin[2]
    assert np.mean(z < -0.3) < 0.002, note


def test_reconstruct_survives_material_below_z0(stepped):
    """The exact pedal adapter condition: Z=0 on a shelf, part reaching below.

    Before the fix this layer stack contained a zero-thickness layer and
    stage 50 died inside OCCT. It must now build the whole part, at true size,
    without dropping the 20 mm that sits below Z=0.
    """
    d, scan, mesh, volume = stepped
    frame = _write_frame(d / "frame_shelf.json", mesh, [0.0, 0.0, BOSS_H])
    r = reconstruct(scan, frame, d / "shelf.step")
    bbox = sorted(r["bbox_mm"])
    assert bbox == pytest.approx(sorted([PLATE, PLATE, BOSS_H + PLATE_T]), abs=0.6)
    assert r["zmin"] == pytest.approx(-BOSS_H, abs=0.5)
    assert r["volume_mm3"] == pytest.approx(volume, rel=0.03)


def test_reconstruct_with_stage20_base_sits_on_xy(stepped):
    """With stage 20's own base pick the same part starts exactly at Z=0."""
    d, scan, mesh, volume = stepped
    planes = extract_planes(mesh)
    origin, _ = s20_frame._pick_origin(mesh, np.eye(3), [], planes)
    frame = _write_frame(d / "frame_base.json", mesh, origin)
    r = reconstruct(scan, frame, d / "base.step")
    assert abs(r["zmin"]) < 1e-6
    assert r["bbox_mm"][2] == pytest.approx(BOSS_H + PLATE_T, abs=0.5)
    assert r["volume_mm3"] == pytest.approx(volume, rel=0.03)


def test_snap_layers_never_yields_thin_layers():
    """The pedal adapter's own numbers: snapping collapsed layer 0 to 0 mm."""
    layers = [
        {"z0": -21.172, "z1": -0.25, "z_mid": 0.0, "area": 900.0},
        {"z0": -0.25, "z1": 33.9, "z_mid": 0.0, "area": 3000.0},
        {"z0": 33.9, "z1": 43.04, "z_mid": 0.0, "area": 1500.0},
        {"z0": 43.04, "z1": 50.924, "z_mid": 0.0, "area": 700.0},
    ]
    heights = [-17.198, -14.824, 0.0, 3.526, 13.633, 33.887]
    out = snap_layers([dict(l) for l in layers], heights, tol=2.0)
    assert all(l["z1"] - l["z0"] >= MIN_LAYER_MM for l in out), out
    # Material below Z=0 is kept, not pinned away.
    assert out[0]["z0"] == pytest.approx(-21.172)
    assert out[-1]["z1"] == pytest.approx(50.924)
    for lo, hi in zip(out[:-1], out[1:]):
        assert lo["z1"] == pytest.approx(hi["z0"])


def test_merge_thin_layers_keeps_the_stack_contiguous():
    layers = [
        {"z0": 0.0, "z1": 0.0},          # collapsed by snapping
        {"z0": 0.0, "z1": 10.0},
        {"z0": 10.0, "z1": 10.3},        # thinner than MIN_LAYER_MM
        {"z0": 10.3, "z1": 20.0},
    ]
    out = merge_thin_layers(layers)
    assert [(l["z0"], l["z1"]) for l in out] == [(0.0, 10.3), (10.3, 20.0)]
