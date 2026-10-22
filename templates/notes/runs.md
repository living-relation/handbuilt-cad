# @JOB@ / runs

Owner: handbuilt-cad layout (setup.sh, tools/folder_notes.py). Agent note.

- Working outputs only, one folder per run (`<YYYYMMDD-HHMM>/`): meshes, solver files, iteration STEPs, topology `.npz`, renders, interim JSON, logs. All regenerable from `../src`.
- Cleanup rule: once a run is published (publish-to-models) or superseded, delete its regenerable outputs. Keep only results that are costly to regenerate, moved to `../../_archive/@JOB@/`. Logs and caches are deleted.
