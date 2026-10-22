# Overview

[← Home](../../README.md)

## What this is

A collection of parts rebuilt by hand from 3D scans, plus the tools used to check and improve them. The approach is deliberately "hand-built": instead of auto-converting a mesh to CAD, each part is measured from the scan (holes, bores, faces, angles), the numbers are rounded to sensible real values, and a short Python script (build123d) builds a clean solid from named dimensions. Change a number at the top of the script, run it again, get a new STEP.

On top of that, some parts get:

- **Strength checks (FEA):** Gmsh meshes the STEP, CalculiX solves load cases from each part LOADS.md (in its parts-home `src/`), ParaView/matplotlib render the results.
- **Topology optimisation:** density (SIMP) and stress-limited runs to see where material can go, then a rebuild as a machinable solid.
- **Machining plans:** setups, stock size, tools and tolerances (`MACHINING.md` in the billet knuckle part folder under `$MODELS_DIR`).

## The pieces and where they live

| Piece | Where | Notes |
|---|---|---|
| This repo (models, scripts, notes, docs) | PC → WSL Ubuntu `~/projects/handbuilt-cad`; GitHub `living-relation/handbuilt-cad` | The single source of truth for hand-built work |
| Fairsolid (scan cleanup / measuring helper) | `pipelines/fairsolid/` (older runs: the archived checkout, see `docs/FAIRSOLID.md`) | Part of this repo since 2026-10-17; the old GitHub repo was deleted on 2026-10-21 |
| Raw scans | Creality Scan folders on the PC, OneDrive, Google Drive | Not in git; listed in `scans/INDEX.md` |
| Simulation tools | WSL (CalculiX, Gmsh, Elmer, OpenFOAM, ParaView, `~/simvenv`) | Install script in `sim/scripts/` |
| FreeCAD | Windows `<freecad_dir>` (`[paths] freecad_dir`, default `<Projects>\_tools\FreeCAD`) | Optional front end |
| Older trials | the owner's scratch folders (outside this repo) | Historical; not needed to use this repo |
| Backups | git history | Repo work is backed up by git; the projects `_archive\` folder holds obsolete work only (owner's OK first) |
| Agent box | A Linux machine the AI agent works on | Some heavy runs happen there and results get copied back here |

## Current highlights

- **Rear knuckle (cast) v4** — the approved hand-built model of the scanned knuckle.
- **Billet knuckles** — five 7075 versions (best 2.33 kg, middle 2.40, full-arm 2.43, easy 2.46, two-piece 2.42 + bolts), all passing a 2× safety factor at fast-road slick-tyre loads.
- **Bezel v3**, **pedal adapter**, **PCV pipe** (stock and −10 AN angled 35°/45° versions), **catch-can reference surfaces**.

See the [Parts index](Parts.md) for numbers and files.
