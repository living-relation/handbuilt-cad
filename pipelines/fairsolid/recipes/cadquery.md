# CadQuery / OCCT — verified behaviour

Verified against **cadquery 2.8.0** on Python 3.13.12 (Windows).

## The teardown crash — read this first

`import cadquery` works, does correct geometry, writes correct files, and then
**crashes at interpreter shutdown**. Observed both as segfault (exit 139) and
as heap corruption (exit 0xC0000374 / 3221226356), depending on how much OCCT
state exists.

```
$ python -c "import cadquery as cq; print(cq.Workplane().box(2,2,2).val().Volume())"
8.0
Segmentation fault          # exit 139 - but the 8.0 is correct
```

It is an OCCT static-destructor problem, not a logic error. Everything the
process was asked to do has already happened. The danger is that a
subprocess-based pipeline reads the exit code and discards a good result.

**Fix:** end the process with `os._exit(0)`, which skips C++ teardown.
`fairsolid.subproc.emit()` does this for every stage.

```python
print("RESULT:" + json.dumps(payload))
sys.stdout.flush(); sys.stderr.flush()
os._exit(0)
```

## Mesh to solid B-Rep

There is no one-call importer. Sew triangles, then wrap the shell in a solid —
sewing is what welds shared edges, and without it CAD imports a surface body
rather than a solid.

```python
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_Sewing, BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeSolid)
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopoDS import TopoDS

sew = BRepBuilderAPI_Sewing(tolerance)       # ~0.25x median edge length
for tri in mesh.faces:
    poly = BRepBuilderAPI_MakePolygon(p1, p2, p3, True)
    sew.Add(BRepBuilderAPI_MakeFace(poly.Wire()).Face())
sew.Perform()
exp = TopExp_Explorer(sew.SewedShape(), TopAbs_SHELL)
solid = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(exp.Current())).Solid()
```

Tolerance matters: too tight and edges fail to weld (surface body); too loose
and distinct features merge. Keying it to median edge length works across
scales.

**Cost:** 8,000 triangles → a valid solid, but **20.4 MB** of STEP. This is
the "triangle soup" problem. Prefer `s50_reconstruct`, which produces the same
part as 61 analytic faces in 238 kB.

## Export and re-import

```python
cq.exporters.export(result, "part.step")          # AP214 by default
shape = cq.importers.importStep("part.step")
shape.val().isValid()                              # sanity check
len(shape.solids().vals())                         # 1 == it is a solid body
[e for e in shape.edges().vals() if e.geomType() == "CIRCLE"]
```

`geomType()` returning `CIRCLE` is how you confirm a hole is a real analytic
circle and not a fine polygon.

## trimesh section coordinates — a trap

`Path3D.to_planar()` picks its **own arbitrary 2D basis** and returns the
mapping as a second value. Discarding it silently puts polygons in a local
frame:

```python
planar, _ = sec.to_planar()            # WRONG - polygons offset from world
```

On a real part this offset every slice ring by a constant 1.3 mm. It survives
every dimensional check, because a uniform translation preserves all sizes —
it only shows up as features no longer concentric with the origin.

```python
to_2D = np.eye(4); to_2D[2, 3] = -z    # cut is the Z=z plane
planar, _ = sec.to_planar(to_2D=to_2D) # RIGHT - 2D coords are world XY
```
