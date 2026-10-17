"""Interface / fitment check: lists the round holes and bosses in a STEP file and (optionally)
compares them with a spec file of where they must be.

    .venv/bin/python tools/features.py part.step                 # list holes
    .venv/bin/python tools/features.py part.step --spec spec.json  # check against spec, exit 1 on fail

spec.json:  {"tolerance_mm": 0.05,
             "holes": [{"name": "bolt A", "x": 10, "y": 20, "z": 0, "d": 6.6, "axis": "z"}, ...]}
"""
import argparse, json, sys
from build123d import import_step, GeomType

def holes(shape):
    out = []
    for f in shape.faces():
        if f.geom_type != GeomType.CYLINDER: continue
        ax = f.axis_of_rotation if hasattr(f, "axis_of_rotation") else None
        r = f.radius
        c = f.center()
        d = ax.direction if ax else None
        name = "?"
        if d is not None:
            v = [abs(d.X), abs(d.Y), abs(d.Z)]; name = "xyz"[v.index(max(v))]
        p = ax.position if ax else c
        out.append(dict(d=round(2 * r, 3), axis=name, x=round(p.X, 3), y=round(p.Y, 3), z=round(p.Z, 3), cx=c.X, cy=c.Y, cz=c.Z))
    # merge split faces of the same cylinder
    uniq = []
    for h in out:
        if not any(abs(h["d"] - u["d"]) < 1e-3 and h["axis"] == u["axis"] and
                   all(abs(h[k] - u[k]) < 1e-3 for k in "xyz" if k != h["axis"]) for u in uniq): uniq.append(h)
    return uniq

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("step"); ap.add_argument("--spec"); a = ap.parse_args()
    shp = import_step(a.step); hs = holes(shp)
    bb = shp.bounding_box()
    print(f"{a.step}: size {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm, volume {shp.volume/1000:.2f} cm3")
    print(f"{len(hs)} cylindrical features (holes/bosses):")
    for h in hs: print(f"  dia {h['d']:8.3f}  axis {h['axis']}  at x {h['x']:8.3f} y {h['y']:8.3f} z {h['z']:8.3f}")
    if not a.spec: return
    spec = json.load(open(a.spec)); tol = spec.get("tolerance_mm", 0.05); fails = 0
    print("\nCheck against", a.spec, f"(tolerance {tol} mm):")
    for s in spec["holes"]:
        ax = s.get("axis", "z")
        m = [h for h in hs if h["axis"] == ax and abs(h["d"] - s["d"]) <= tol and
             all(abs(h[k] - s[k]) <= tol for k in "xyz" if k != ax)]
        print(f"  {'PASS' if m else 'FAIL'}  {s['name']}: dia {s['d']} at ({s['x']}, {s['y']}, {s['z']}) axis {ax}")
        fails += not m
    print("ALL PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)

if __name__ == "__main__": main()
