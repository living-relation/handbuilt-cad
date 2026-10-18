---
name: sim-stack
description: >-
  Use when running heat, multiphysics, CFD or full FEA jobs with the WSL
  simulation stack (CalculiX, Elmer, OpenFOAM, Gmsh, ParaView, FreeCAD front
  end) described in sim/SIM_TOOLS.md. Runs on the user's machine.
---
> Draft by Grok Bot (17/10/26). Owner: SteveCAD, who will refine it. Changes go through a PR he reviews.

The project's own rules win over this skill wherever they differ. `sim/SIM_TOOLS.md` has the versions, smoke tests and commands.

## When
No strength, heat or CFD runs until the user approves the geometry, unless they ask for early tests. For a single quick static check, use quick-fea.

## Where it runs
- Solvers run in WSL on the user's machine: `source sim/wsl-env.sh` from the repo root (OpenFOAM env, sim venv, `$SIM`). FreeCAD stays on Windows (`[paths] freecad_dir`); its WSL wrappers are `ccx_wsl.bat` / `gmsh_wsl.bat` in that folder.
- Run cases in the Linux home (e.g. `~/sim-runs/<job>`), not under `/mnt/c` (slow for OpenFOAM), then copy the results to the job's working folder. Never commit run output.
- The sim venv and system packages are shared: read-only for agents. Don't install, upgrade or run the rollback scripts without the user's yes.

## Steps
1. Ask once per job (save in SUMMARY.md): load or boundary cases, material data, the acceptance limit and safety factor. Never assume one.
2. Mesh with Gmsh from the approved STEP; record mesh size and element type.
3. Solve: CalculiX (static, thermal), Elmer (heat, multiphysics) or OpenFOAM (CFD). Check convergence (residuals) and do a mesh refinement check on the result you report.
4. Post-process in ParaView (`xvfb-run -a pvpython` for scripts). Section views of results are capped (solid cut faces), never open shells.
5. Report the case setup, solver and version, mesh, convergence, results vs the limit and the open risks. Walk the user through decisions one at a time.

## Known issues
- `ccx2paraview` 3.2.0 crashes on stress with numpy 2.x. Load the `.frd` in FreeCAD, or convert a copy with only `*NODE FILE` output.
