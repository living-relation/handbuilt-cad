"""Sample part: a simple L-bracket, to show the toolkit workflow.
Every size is a named number. Change one, run again, get a new STEP.

    ../../.venv/bin/python bracket.py
"""
from build123d import *  # chamfer, fillet, etc.

# ---- sizes (mm) -------------------------------------------------------------
BASE_L, BASE_W, THICK = 60.0, 40.0, 6.0     # base plate
UPRIGHT_H = 45.0                            # height of the upright (from the bottom)
BOLT_D = 6.6                                # M6 clearance holes in the base
BOLT_PITCH = 24.0                           # distance between the two base holes
BOLT_X = 38.0                               # base holes' distance from the upright face side
TOP_HOLE_D = 8.5                            # M8 clearance hole in the upright
TOP_HOLE_Z = 30.0                           # height of the upright hole
INSIDE_R = 6.5                              # inside corner: 1.3× the 5 mm tool in cnc_spec.json
EDGE_LEN = 1.0                              # modeled 45° outside chamfer (not auto-applied)
# ------------------------------------------------------------------------------

with BuildPart() as p:
    Box(BASE_L, BASE_W, THICK, align=(Align.MIN, Align.CENTER, Align.MIN))          # base, x 0..60
    Box(THICK, BASE_W, UPRIGHT_H, align=(Align.MIN, Align.CENTER, Align.MIN))       # upright at x 0..6
    inside = p.edges().filter_by(Axis.Y).filter_by_position(Axis.X, THICK - 0.01, THICK + 0.01) \
                      .filter_by_position(Axis.Z, THICK - 0.01, THICK + 0.01)
    fillet(inside, INSIDE_R)                  # pocket/profile radius, not a later inside-edge fillet pass
    with Locations((BOLT_X, -BOLT_PITCH / 2, 0), (BOLT_X, BOLT_PITCH / 2, 0)):
        Cylinder(BOLT_D / 2, THICK, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    with Locations(Location((0, 0, TOP_HOLE_Z), (0, 90, 0))):
        Cylinder(TOP_HOLE_D / 2, THICK * 2, mode=Mode.SUBTRACT)
    outer = p.edges().filter_by(Axis.Z).group_by(Axis.X)[-1]                        # far end corners
    chamfer(outer, EDGE_LEN)                   # modeled 45° edge break; drawing will dimension this

part = p.part
export_step(part, "bracket.step")
mass = part.volume * 2.70e-6   # aluminium 2.70 g/cm3 -> kg
print(f"bracket: volume {part.volume/1000:.2f} cm3, mass {mass*1000:.0f} g (aluminium); wrote bracket.step")
