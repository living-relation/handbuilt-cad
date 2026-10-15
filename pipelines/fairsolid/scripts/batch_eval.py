"""Run the full pipeline over a set of real scans and tabulate what happened.

The point is not to make any single scan succeed. It is to find out, across
real parts rather than one synthetic fixture, where the pipeline delivers a
parametric solid, where it correctly falls back, and where it breaks.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

from fairsolid.pipeline import finish, prepare

# Scan paths come from FAIRSOLID_SCAN_DIR (default: ./scans), one file per part.
SCAN_DIR = Path(os.environ.get("FAIRSOLID_SCAN_DIR", "scans"))
SCANS = {
    "pedal_adapter": str(SCAN_DIR / "pedal_adapter.ply"),
    "fuel_pump":     str(SCAN_DIR / "fuel_pump.stl"),
    "bezel":         str(SCAN_DIR / "bezel.stl"),
    "oil_catch":     str(SCAN_DIR / "oil_catch.ply"),
    "dash_housing":  str(SCAN_DIR / "dash_housing.ply"),
}

rows = []
for name, path in SCANS.items():
    p = Path(path)
    row = {"name": name, "exists": p.exists()}
    if not p.exists():
        rows.append(row); print(f"{name}: MISSING"); continue
    try:
        st = prepare(p, Path("runs") / name)
        row["faces_in"] = st["ingest"]["faces"]
        row["extents"] = [round(x, 1) for x in st["ingest"]["extents"]]
        idl = st.get("idealize") or {}
        row["flatness_gain"] = round(idl.get("flatness_gain", 0) * 100, 1)
        row["noise_floor"] = round(st["frame"]["noise_floor"], 4)
        row["planes"] = st["frame"]["n_planes"]
        row["cylinders"] = st["frame"]["n_cylinders"]
        row["options"] = st["frame"]["n_options"]

        fin = finish(Path("runs") / name, choice=0, tol=0.5)
        dev = fin.get("deviation")
        row["verdict"] = dev["verdict"] if dev else "no-parametric"
        row["median_dev"] = round(dev["median_mm"], 3) if dev else None
        row["within_tol"] = round(dev["fraction_within_tol"] * 100, 1) if dev else None
        rec = fin.get("reconstruct") or {}
        row["layers"] = rec.get("n_layers")
        fac = fin.get("faceted") or {}
        row["faceted_valid"] = fac.get("is_valid")
        row["shells"] = fac.get("n_shells")
        row["delivered"] = Path(fin["primary"]).name
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        traceback.print_exc(limit=2)
    rows.append(row)
    print(json.dumps(row))

Path("work/batch_eval.json").write_text(json.dumps(rows, indent=2))
print("\nwrote work/batch_eval.json")
sys.stdout.flush()
