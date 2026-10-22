---
name: sim-stack
description: >-
  Use for any strength, heat, multiphysics or CFD check of an approved CAD
  part: a quick single linear-static check with tools/quick_fea.py, or a full
  study with the WSL simulation stack (Gmsh, CalculiX, Elmer, OpenFOAM,
  ParaView) in sim/SIM_TOOLS.md. Runs on the user's machine.
---
The project's own rules win over this skill. Versions, smoke tests and solver commands are in `sim/SIM_TOOLS.md`.

## When
- Only after the user approves the geometry (cnc-part-check passed), unless they ask for early tests to check the design or find risks.
- Pick the smallest path that answers the question:
  - **Quick check**: one part, one linear static load case, isotropic material. `tools/quick_fea.py`. A first look, not a sign-off.
  - **Full study**: several load cases, contact, assemblies, thermal, multiphysics or CFD. Gmsh + CalculiX / Elmer / OpenFOAM.
  - If a quick check lands close to the limit, or the load case doesn't fit it, say so and offer the full study.

## Where it runs
- WSL on the user's machine: `source sim/wsl-env.sh` from the repo root (OpenFOAM env, sim venv `$SIM_VENV`, `$SIM`; `sim/env.sh` on plain Linux). FreeCAD stays on Windows (`[paths] freecad_dir`; WSL wrappers `ccx_wsl.bat` / `gmsh_wsl.bat`).
- Run cases in the parts-home runs folder, `<parts_home>/<job>/runs/<stamp>/` (`tools/paths.py`; `[paths] parts_home` / `HBCAD_PARTS_HOME`, default `~/cad-parts`), on the Linux side, not `/mnt/c`. Never inside a git repo; never commit run output.
- The sim venv and system packages are shared and read-only for agents: no installs, upgrades or rollback scripts without the user's yes.

## Inputs (once per job, saved in SUMMARY.md)
- Load and boundary cases, material data, acceptance limit and safety factor. Look up material properties and bought-part ratings yourself from primary sources and cite them from the datasheet or the maker's own page (primary-source-spec-check); ask the user only for what no source settles (loads, limit, safety factor). Never assume a safety factor.

## Quick check
```bash
$SIM_VENV/bin/python tools/quick_fea.py part.step --job <job> --fix x:min --load x:max --force 0,0,-500 \
    --E 69000 --nu 0.33 --yield 276 --size 2
```
- `--fix` / `--load`: `AXIS:min`, `AXIS:max` or `AXIS:VALUE` (nodes within `--tol` mm of that plane). `--force`: total N as X,Y,Z spread over the load nodes.
- Material defaults are 6061-T6; always pass the real material.
- Output: `--job <job>` writes deck, results, `summary.json` and `result.vtu` to `<parts_home>/<job>/runs/<stamp>/`; `--out <dir>` (wins over `--job`) picks another folder. It refuses any folder inside a git repo.

## Full study
1. Mesh the approved STEP with Gmsh; record mesh size and element type.
2. Solve: CalculiX (static, thermal), Elmer (heat, multiphysics) or OpenFOAM (CFD). Check convergence (residuals).
3. Post-process in ParaView (`xvfb-run -a pvpython` for scripts).

## Both paths: before reporting
- Mesh check: refine the mesh and re-run; the reported peak must hold. A peak only at a sharp corner, fixed node or load node is a singularity, not a result; say so.
- Result images are smooth (no mesh lines unless the mesh is the point), and section views are capped (solid cut faces), never open shells.
- Report: path used and why, load case, fixed and loaded faces, material and source, solver and version, mesh, convergence, peak stress or temperature vs the limit, safety factor, max displacement, open risks. Tool in parentheses. Report and ask as cnc-part-check "Asking the user" says.

## Known issues
- `ccx2paraview` 3.2.0 crashes on stress with numpy 2.x. Load the `.frd` in FreeCAD, or convert a copy with only `*NODE FILE` output.
