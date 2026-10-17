"""Check one or more STEP files: solid count, validity, volume, bounding box.

Rule it enforces: a printed or machined part is ONE solid (no floating pieces).
An assembly STEP legitimately holds many solids; check each part file on its own.

Run (build123d venv):  python tools/check_step.py part1.step part2.step ...
Exit code 1 if any file has more than one solid or an invalid solid.
"""
import sys
from build123d import import_step


def main(paths):
    bad = 0
    for p in paths:
        shape = import_step(p)
        solids = list(shape.solids())
        vols = sorted((s.volume for s in solids), reverse=True)
        valid = all(s.is_valid for s in solids)
        bb = shape.bounding_box()
        flag = "OK " if len(solids) == 1 and valid else "BAD"
        if flag == "BAD":
            bad += 1
        print(f"{flag} {p}: solids={len(solids)} valid={valid} volume={shape.volume:.1f} mm3 "
              f"bbox={bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")
        if len(solids) > 1:
            print("    solid volumes (mm3):", ", ".join(f"{v:.1f}" for v in vols[:8]))
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
