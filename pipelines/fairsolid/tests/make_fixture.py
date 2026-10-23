"""Generate a known ground-truth part and a simulated scan of it.

Having exact nominal dimensions is what lets the test suite assert on
recovered SIZE, not just recovered shape - the scale invariant this whole
project turns on.
"""
import json, os, sys
from pathlib import Path

import numpy as np
import cadquery as cq
import trimesh

OUT = Path(__file__).parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

# Nominal geometry, in millimetres. Deliberately mechanical: flats to fit
# planes to, a boss and a bore to fit cylinders to.
NOMINAL = {
    "plate_x": 80.0, "plate_y": 50.0, "plate_z": 12.0,
    "bore_d": 16.0,
    "boss_d": 26.0, "boss_h": 10.0,
    "corner_hole_d": 6.0, "corner_inset": 8.0,
}

def build():
    n = NOMINAL
    part = cq.Workplane("XY").box(n["plate_x"], n["plate_y"], n["plate_z"])
    part = (part.faces(">Z").workplane()
                .circle(n["boss_d"] / 2).extrude(n["boss_h"]))
    part = (part.faces(">Z").workplane()
                .circle(n["bore_d"] / 2).cutThruAll())
    part = (part.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                .rect(n["plate_x"] - 2 * n["corner_inset"],
                      n["plate_y"] - 2 * n["corner_inset"], forConstruction=True)
                .vertices().circle(n["corner_hole_d"] / 2).cutThruAll())
    return part

part = build()
cq.exporters.export(part, str(OUT / "nominal.step"))
cq.exporters.export(part, str(OUT / "nominal.stl"),
                    tolerance=0.01, angularTolerance=0.1)
solid = part.val()
truth = dict(NOMINAL)
truth["volume"] = solid.Volume()
truth["bbox"] = list(solid.BoundingBox().DiagonalLength for _ in [0])[0]
(OUT / "nominal.json").write_text(json.dumps(truth, indent=2))
print("nominal volume mm^3:", round(solid.Volume(), 4))

# --- simulated scan: noise, arbitrary pose, missing patches -------------
mesh = trimesh.load(OUT / "nominal.stl", force="mesh", process=False)
rng = np.random.default_rng(7)

# Resample to a realistic scanner point spacing (~0.35 mm) before adding
# sensor noise. Subdividing to sub-0.1 mm facets and then adding 0.05 mm
# noise destroys the normal field in a way no real scanner does.
mesh = mesh.subdivide_to_size(max_edge=0.35)
mesh.vertices = mesh.vertices + rng.normal(0, 0.04, mesh.vertices.shape)

angle = np.deg2rad(37.0)
R = trimesh.transformations.rotation_matrix(angle, [0.37, 0.51, 0.77])
T = trimesh.transformations.translation_matrix([123.4, -56.7, 89.1])
mesh.apply_transform(T @ R)

# Occlusion: real scanners lose CONTIGUOUS patches (undercuts, deep bores,
# grazing angles), not scattered individual triangles. Knock out a handful
# of spherical regions instead.
centres_f = mesh.triangles_center
drop = np.zeros(len(mesh.faces), dtype=bool)
lo, hi = mesh.bounds
for _ in range(6):
    c = lo + rng.random(3) * (hi - lo)
    r = 0.10 * np.linalg.norm(hi - lo)
    drop |= np.linalg.norm(centres_f - c, axis=1) < r
mesh.update_faces(~drop)
mesh.remove_unreferenced_vertices()
print("occluded fraction: %.1f%%" % (100 * drop.mean()))

mesh.export(OUT / "scan.stl")
print("scan faces:", len(mesh.faces), "watertight:", mesh.is_watertight)
print("scan bounds:", np.round(mesh.bounds, 2).tolist())

sys.stdout.flush(); os._exit(0)
