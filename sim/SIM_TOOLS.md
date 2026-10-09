# Simulation tools

Strength (FEA), heat and CFD tools. The solvers run in WSL (Ubuntu 26.04), and FreeCAD on Windows is the front end. Everything was installed on Oct 9 2026 and passed a smoke test (see `smoke/`).

## What's installed

| Tool | Use | Version | Where | Smoke test |
|---|---|---|---|---|
| CalculiX `ccx` | Static strength, thermal FEA | 2.21 (apt `calculix-ccx`) | WSL `/usr/bin/ccx` | Cantilever 100x10x10 mm steel, 100 N: tip 0.1902 mm vs 0.1920 mm hand calc (Timoshenko), -0.9 %. Steady heat block: mid-point 60.00 C, exact 60.00 C. `smoke/ccx/RESULT.txt` |
| Elmer FEM | Heat and multiphysics | 26.2.1 (built from official ElmerCSC source; no Ubuntu 26.04 package or PPA exists yet) | WSL `/opt/elmer`, `ElmerSolver` / `ElmerGrid` in `/usr/local/bin` | Al block with heat generation: Tmax 38.734 C vs 38.713 C exact, +0.05 %. `smoke/elmer/` |
| OpenFOAM | CFD | OpenFOAM 14 (openfoam.org apt repo, package `openfoam14` 20261008) | WSL `/opt/openfoam14` | Lid-driven cavity tutorial ran to the end; residuals Ux 1 -> 3e-5, p 1 -> 4e-6. `smoke/openfoam/` |
| Gmsh | Meshing | 4.14.0 (apt) in WSL; 4.15.2 Python module in the venv | WSL `/usr/bin/gmsh` | Meshed `pcv_adapter.step`: 4114 nodes, 13295 tets. `smoke/gmsh/` |
| ParaView | Post-processing, `pvpython` | 6.0.1 (apt) | WSL `/usr/bin/paraview`, `pvpython` | Rendered the beam result to `smoke/paraview/beam_displacement_x50.png` (headless with `xvfb-run`) |
| Python venv | meshio 5.3.5, gmsh 4.15.2, pygmsh 7.1.17, numpy 2.5.3, matplotlib 3.11.2, vtk 9.7.1, ccx2paraview 3.2.0 | Python 3.14 | WSL `/home/daniel/simvenv` | Used by the smoke tests |
| FreeCAD | CAD and FEM front end | 1.1.4 portable (official 7z, SHA256 checked) | `sim-tools\FreeCAD`, start with `sim-tools\FreeCAD.bat` | FEM workbench imports OK (`smoke/freecad_check_result.txt`) |

## How to run

Inside WSL, load everything first:

```bash
source /mnt/c/projects/active/handbuilt-models/sim-tools/wsl-env.sh   # OpenFOAM env + simvenv + $SIM
```

- **CalculiX:** `ccx -i job` (reads `job.inp`, writes `job.frd` / `job.dat`). Convert for ParaView with `ccx2paraview job.frd vtu`.
- **Elmer:** `ElmerGrid 14 2 mesh.msh -autoclean` (Gmsh msh2 file to Elmer mesh), then `ElmerSolver case.sif`. The heat example is `smoke/elmer/case.sif`.
- **OpenFOAM:** copy a tutorial from `$FOAM_TUTORIALS`, then `blockMesh` and `foamRun`, and `foamToVTK` for ParaView. Run cases in the Linux home (for example `~/sim-runs/...`) and copy the results out, because `/mnt/c` is slow for OpenFOAM's many small files.
- **Gmsh:** `gmsh part.step -3 -clmax 1.5 -o part.msh`.
- **ParaView:** `paraview` opens the GUI in WSL. For scripts, use `xvfb-run -a pvpython script.py` (example: `smoke/paraview/shot.py`).
- The scripts that ran every smoke test are in `scripts/` (`smoke_ccx.sh`, `smoke_elmer.sh`, `smoke_openfoam.sh`, `smoke_gmsh_pv.sh`).

## FreeCAD on Windows with the WSL solvers

FreeCAD 1.1.4 comes with its own Windows `ccx.exe` and `gmsh.exe` in `FreeCAD\bin`, so FEM works out of the box. To use the WSL CalculiX instead:

1. Open FreeCAD (`sim-tools\FreeCAD.bat`).
2. Go to Edit > Preferences > FEM > CalculiX, untick "Use built-in path", and set the binary to `C:\projects\active\handbuilt-models\sim-tools\ccx_wsl.bat`.
3. The wrapper runs `wsl ccx` in FreeCAD's working folder and uses all CPU threads. `gmsh_wsl.bat` does the same for Gmsh and converts Windows file paths.

FreeCAD's Elmer and OpenFOAM (CfdOF add-on) links expect Windows builds. For those, set up the case in FreeCAD, export it, and run it in WSL.

## Known quirk

`ccx2paraview` 3.2.0 crashes on stress results with numpy 2.x (it sorts complex eigenvalues). Displacement and temperature convert fine. For stress, load the `.frd` in FreeCAD, or convert a copy with only `*NODE FILE` output.

## Disk used

- WSL root went from 5.4 GB to about 9.1 GB used. That's 385 apt packages (about 2.6 GB including OpenFOAM), Elmer at 37 MB plus a 64 MB source tarball, and the venv at about 0.9 GB.
- Windows: FreeCAD 2.2 GB unpacked, plus the 0.4 GB download in `downloads\` (safe to delete).

## Uninstall / rollback

- WSL: `wsl -d Ubuntu -u root -- bash /mnt/c/projects/active/handbuilt-models/sim-tools/rollback/uninstall_wsl_sim_tools.sh` (add `--dry-run` to preview). It purges only the packages this install added, removes the OpenFOAM apt source, `/opt/elmer`, `/opt/src`, `~/simvenv` and `~/sim-runs`, and then compares against `rollback/wsl-packages-before.txt`.
- Windows: `powershell -File rollback\uninstall_windows_sim_tools.ps1` deletes the portable FreeCAD, the download and the wrappers. Nothing was installed system-wide, and no registry or PATH changes were made.
- Package lists: `rollback/wsl-packages-before.txt` (rebuilt from `/var/log/dpkg.log`, 544 packages), `wsl-packages-added.txt` (385), `wsl-manual-added.txt`, and `etc-apt-before/` (copy of `/etc/apt` before the change).
- Three packages that were already installed got minor security updates from Ubuntu (curl, libcurl4t64, libevent-core). The uninstall leaves those alone.