# @JOB@ / runs

Owner: handbuilt-cad (https://github.com/living-relation/handbuilt-cad). Note written by `tools/folder_notes.py` (setup and publish-to-models), add-only.

Used by: handbuilt-cad's tools (`tools/paths.py` run_dir, `quick_fea.py --job`), which write working outputs here.
Deleting, moving or renaming this folder breaks those tools; clean up old runs by the rule below instead.

- Working outputs only, one folder per run (`<YYYYMMDD-HHMM>/`): meshes, solver files, iteration STEPs, topology `.npz`, renders, interim JSON, logs. All regenerable from `../src`.
- Cleanup rule: once a run is published (publish-to-models) or superseded, delete its regenerable outputs. Keep only results that are costly to regenerate, moved to `../../_archive/@JOB@/`. Logs and caches are deleted.
