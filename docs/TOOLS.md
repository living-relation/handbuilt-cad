# Tools index

| Tool | Path / source | Made / existing / modified | Pinned version | Used for |
|---|---|---|---|---|
| build123d | PyPI | existing | 0.13.0 | parametric build scripts |
| OCP (OpenCascade bindings, toolkit venv) | PyPI `cadquery-ocp-novtk` | existing | 8.0.1.1.0 | build123d kernel |
| CadQuery + OCP (fairsolid venv) | PyPI `cadquery`, `cadquery-ocp` | existing | 2.8.0 / 7.9.3.1.1 | scan pipeline (separate venv: the two OCP builds conflict) |
| numpy / scipy / trimesh / rtree / shapely | PyPI | existing | 2.5.3 / 1.18.1 / 5.1.1 / 1.4.1 / 2.2.0 | geometry and checks |
| open3d | PyPI | existing | 0.20.0 | point clouds / scans |
| pyvista / vtk | PyPI | existing | 0.49.0 / 9.7.1 | renders (offscreen in WSL) |
| ezdxf | PyPI | existing | 1.4.4 | DXF output |
| Python | uv-managed CPython | existing | 3.13.16 (`.python-version`) | toolkit venv |
| uv | astral-sh/uv release | existing | 0.13.0 | venv + lock |
| gitleaks | gitleaks/gitleaks release | existing | 8.30.1 (`.gitleaks-version`) | pre-commit secret scan |
| gmsh, CalculiX, ParaView, OCCT tools | Ubuntu apt (`apt-sim.txt`) | existing | see `apt-sim.txt` | optional sim tools |
| sim venv packages | PyPI (`requirements-sim.txt`) | existing | see file | optional meshing/FEA post (Python 3.14 venv) |
| FreeCAD | FreeCAD release | existing | 1.1.4 | headless FEM / edge breaks; its bundled Python is never imported by this repo |
| FreeCAD launcher wrappers | `sim/` (`*.bat`) | modified (our wrappers) | - | run ccx/gmsh in WSL from FreeCAD |
| tools/* | `tools/` | made | - | toolkit (`sketch_blend.py`, `chamfer_batch.py` ported from handbuilt-models 2026-10-17) |
| drawing engine (part/asm/dwg/feat/hw) + revs.py + templates | `drawing/` | made | - | 2D drawings from B-rep (no hidden lines, rev log), rev letters, revision register |
| model checks | `tools/checks/` | made | - | mesh, structural-only minimum wall (`check_printed_walls.py` + `wall_classes.py`, per-project config from `walls.example.toml`; `walls_any.py` detection only), round-trip, interference, edge breaks, hole fixes |
| FreeCAD smoke check | `sim/smoke/run_freecad_check.py` | made | - | FreeCAD FEM import check using `[paths] freecad_dir` from `local.toml` |
| renders | `tools/render/` | made | - | smooth-shaded renders, section plots |
| fairsolid | `pipelines/fairsolid/` | made | - | scan -> parametric STEP |
| sim scripts | `sim/` | made | - | meshing/FEA helpers and smoke tests |
| Fusion 360, Fusion MCP add-in, harness-design MCP, Blender MCP add-on | outside dependencies | existing | listed in the workstation pin file | not part of this repo |
