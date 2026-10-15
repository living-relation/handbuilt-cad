# MeshLab / pymeshlab — verified commands

Everything here was read out of the **installed** pymeshlab (2025.7) with
`pymeshlab.print_filter_parameter_list(<name>)`, not copied from docs or
tutorials. `tests/test_recipes.py` re-runs these and fails if a name drifts.

> API note: in 2025.7 the introspection helpers are **module-level**
> (`pymeshlab.print_filter_parameter_list`). `MeshSet.print_filter_parameter_list`
> does not exist, and `pymeshlab.__version__` is not defined either.

## Repair chain (order matters)

Duplicates first — non-manifold repair reports false positives on doubled
vertices.

```python
ms = pymeshlab.MeshSet(); ms.load_new_mesh("scan.stl")
ms.apply_filter("meshing_remove_duplicate_vertices")
ms.apply_filter("meshing_remove_duplicate_faces")
ms.apply_filter("meshing_remove_unreferenced_vertices")
ms.apply_filter("meshing_repair_non_manifold_edges")
ms.apply_filter("meshing_repair_non_manifold_vertices")
```

## Screened Poisson — seals holes, produces a watertight manifold

Needs per-vertex normals; a raw STL carries none.

```python
ms.apply_filter("compute_normal_per_vertex")
ms.apply_filter("generate_surface_reconstruction_screened_poisson",
                depth=10, preclean=True, samplespernode=1.5)
ms.set_current_mesh(ms.mesh_number() - 1)   # Poisson writes a NEW layer
```

Real parameter names (defaults shown):
`visiblelayer=False, depth=8, fulldepth=5, cgdepth=0, scale=1.1,
samplespernode=1.5, pointweight=4, iters=8, confidence=False,
preclean=False, threads=12`

`depth` is the octree resolution and the main quality knob. 8 (the default)
under-resolves scan detail; **10** matches typical structured-light density.
Above 11 it starts fitting sensor noise and memory runs away.

**Measured cost:** 3.16 M faces → watertight at depth 10 in ~64 s.

## Quadric decimation — keep it, but keep `planarquadric=True`

```python
ms.apply_filter("meshing_decimation_quadric_edge_collapse",
                targetfacenum=200_000, preserveboundary=True,
                preservenormal=True, preservetopology=True,
                planarquadric=True, autoclean=True)
```

Real parameter names (defaults shown):
`targetfacenum=6, targetperc=0, qualitythr=0.3, preserveboundary=False,
boundaryweight=1, preservenormal=False, preservetopology=False,
optimalplacement=True, planarquadric=False, planarweight=0.001,
qualityweight=False, autoclean=True, selected=False`

`planarquadric` defaults to **False**, which is wrong for mechanical parts:
plain quadric collapse preferentially eats flat regions, bowing the very
faces we later fit planes to.

## What this chain does NOT fix

Poisson **cannot invent occluded geometry**. On a scan with 17 % contiguous
occlusion it bridges the gaps smoothly, leaving up to ~6 mm local error at
those patches and a −6 % volume error, while unoccluded regions stay at
~0.17 mm. Fit primitives to the observed inliers and extrapolate
analytically — never trust the reconstructed surface inside an occlusion.
