# Fusion add-ins (HB Export, HB BOM)

Two Python add-ins for Autodesk Fusion. Both run inside Fusion only; nothing here runs on its own.

| Add-in | Button | What it does |
|---|---|---|
| `HBExport/` | **HB Export** (Utilities > Add-Ins panel) | A checkbox per file type: STEP, F3D, STL, 3MF, IGES, SAT, and DXF of a selected sketch or flat face. Pick a folder once; it is remembered. Files are named after the design (Fusion's ` v12` suffix dropped), so each export **overwrites in place**. Optional: pick one component to export just that. |
| `HBBom/` | **HB BOM** (same panel) | Counts every component (pieces per part), fills part number / description / material / vendor / vendor part number / notes from a `build.json`, shows a table you can edit by hand, writes the fields back on **Apply + export**, then saves `<design>_BOM.csv`, `<design>_BOM.xlsx` and `<design>_BOM_report.txt` (anything blocked or still empty) in the folder you pick. |

## What Fusion lets a script write (checked on a non-commercial plan, Fusion 2705.1.11, 2026-10-29)
- Writable: component name, **part number**, **description**, **material** (component and body), body/occurrence **appearance**, and **attributes** on design, component and occurrence.
- Not available: custom BOM properties (the only property group is General: Part Name, Part Number, Description; there is no way to add one). So vendor, vendor part number and notes are stored as attributes in the group `handbuiltcad` and come back in the CSV/Excel.
- Export: STEP, F3D, STL, 3MF, sketch DXF work. **IGES and SAT are blocked by the plan** ("the user is restricted"); the add-in still offers them and reports them as blocked.
- Linked (external) components are read-only here; the report lists them.

## Install (once per PC)
1. In Fusion: **Utilities > Add-Ins > Scripts and Add-Ins** (Shift+S), **Add-Ins** tab.
2. Click the green **+** and pick the folder `tools/fusion_addins/HBExport` in your handbuilt-cad clone. Do the same for `tools/fusion_addins/HBBom`.
3. Select each one, click **Run**, and tick **Run on Startup**.
4. The buttons appear in **Utilities > Add-Ins** (and in the toolbar's Add-Ins panel).

Keep the folders inside the clone: both add-ins load the shared `hbcad_fusion_common/` folder next to them, so copying one folder elsewhere will not work. Updating the clone (`git pull --ff-only`) updates the add-ins; restart them from the dialog (Stop, Run).

Settings (last folder, checked types, last build.json) live in `%APPDATA%\HandbuiltCAD\fusion-addins\`.

## build.json for HB BOM
Any of these shapes work. Parts match by component name or part number (not case-sensitive):
```json
{"parts": [{"name": "Hinge leaf", "part_number": "FC5-712", "description": "Door hinge leaf",
            "material": "Aluminum 6061", "vendor": "McMaster", "vendor_pn": "1234A56", "notes": ""}]}
```
also `{"bom": [...]}`, a plain list, or `{"Hinge leaf": {"pn": "FC5-712", ...}}`. Accepted aliases: `pn`, `desc`, `mat`, `supplier`, `mcmaster`, `note`. Filling never replaces what you already typed unless **build.json overwrites filled cells** is ticked; Fusion's own defaults (part number = component name, the design's default material) count as empty. A material must match a name in your material libraries exactly, or the report lists it as blocked.

## Tests
- Pure logic (no Fusion): `$CAD_PY -m pytest -q tests/test_fusion_addins.py`.

Fusion work uses Autodesk's official, Autodesk-hosted MCP servers (nothing to install): Fusion Compute MCP `https://developer.api.autodesk.com/da/v3/mcp/fusion` (preferred, headless cloud Fusion, so local Fusion isn't interrupted); Fusion Data MCP `https://developer.api.autodesk.com/fusion/mcp`; Fusion Desktop MCP is built into Fusion (Preferences > General > API, local `http://127.0.0.1:27182/mcp`). Docs: https://help.autodesk.com/view/ADSKMCP/ENU/
