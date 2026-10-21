# knuckle_billet FEA job scripts (chunks 16-17)
Run from WSL. Each script works in a run folder (default `$KB_RUN`, e.g. a folder under your scratch dir) that holds `iter/<stem>.step`
(or `<stem>_mesh.npz`), `loads.json` and copies of this folder's `fea_iter.py`, `post_iter.py`, `mesh_step.py`, `sum17.py`.
They source the repo's `sim/wsl-env.sh` (ccx, gmsh) and fall back to `~/simvenv`.

- `fea_run.sh <stem>`: one deck -> ccx -> post run (chunk 16 middle-smooth `ms3`). Env `ZP` moves the tyre contact patch (chunk 16 `ms3w` used `ZP=-60`).
- `pos_job.sh <final> <pos> <cases>`: chunk 17 run at a suspension link position (`POS`= bump|mid|ride|droop), 9in ET-35 wheel (`ZP=-77`), then `sum17.py`.
- `pos_all.sh`: meshes the four finals and runs `jobs17.txt` 3 at a time (chunk 17 results: `../loads17_results.md`).
