"""PCV breather tube, Audi OE 06H103223A (EA888 2.0T), PCV valve -> intake manifold.
Hand-built parametric model from scan Project_26060601 (Creality, rough; one side filled in by the table)
plus listing photos (eBay 147535844352). All mm.
v3: ball-shaped flare (the owner, part in hand). v2: made symmetric. Both ends are identical (photos show an O-ring pair at each end); the end
geometry comes from the better-scanned end. Z = tube axis, z=0 at one end face.
"""
from build123d import *

# ---------------- parameters ----------------
LENGTH          = 53.0   # overall length, face to face
BORE_D          = 13.0   # straight-through bore
BORE_CHAMFER    = 0.8    # 45 deg chamfer at both bore mouths
MAIN_LAND_D     = 21.8   # end OD between/behind the grooves (same both ends)
LEAD_LAND_D     = 21.0   # outermost lead-in land at each end
END_CHAMFER_AX  = 1.0    # lead-in chamfer at each end face: axial length
END_CHAMFER_RAD = 0.8    #   ... radial depth
NECK_D          = 16.4   # bottleneck OD
GROOVE_FLOOR_D  = 17.6   # O-ring groove root diameter (2.1 deep below MAIN_LAND_D)
GROOVE_W        = 3.3    # O-ring groove width (2.5 mm cross-section O-ring, e.g. 17 x 2.5)
OUTER_GROOVE_Z  = 4.6    # outer groove centre, measured from each end face
INNER_GROOVE_Z  = 11.25  # inner groove centre, measured from each end face
BALL_D          = 20.4   # max OD of the ball-shaped flare behind the inner groove
NECK_START_Z    = 18.9   # ball flare reaches neck OD (from each end face)
NECK_FILLET     = 1.5    # blend where the ball meets the neck
# ---------------------------------------------

def _ball_center_z():
    """Sphere centred on the axis that passes through (BALL_D/2, z0) and (NECK_D/2, NECK_START_Z)."""
    z0 = INNER_GROOVE_Z + GROOVE_W / 2
    r1, r2, z1 = BALL_D / 2, NECK_D / 2, NECK_START_Z
    zc = (r2**2 + z1**2 - r1**2 - z0**2) / (2 * (z1 - z0))
    return z0, zc, (r1**2 + (z0 - zc)**2) ** 0.5

def end_edges(flip):
    """Outer profile for one end as edges in the XZ plane (x = radius). flip mirrors to the far end."""
    rM = MAIN_LAND_D / 2; rL = LEAD_LAND_D / 2; rN = NECK_D / 2
    rG = GROOVE_FLOOR_D / 2; rB1 = BALL_D / 2; h = GROOVE_W / 2
    o, i = OUTER_GROOVE_Z, INNER_GROOVE_Z
    z0, zc, R = _ball_center_z()
    Z = (lambda z: LENGTH - z) if flip else (lambda z: z)
    P = lambda r, z: (r, 0, Z(z))
    pts = [(rL - END_CHAMFER_RAD, 0), (rL, END_CHAMFER_AX), (rL, o - h), (rG, o - h), (rG, o + h),
           (rM, o + h), (rM, i - h), (rG, i - h), (rG, z0), (rB1, z0)]
    edges = [Line(P(*a), P(*b)) for a, b in zip(pts[:-1], pts[1:])]
    import math
    zm = z0 + 0.5 * (NECK_START_Z - z0)
    rm = (R**2 - (zm - zc)**2) ** 0.5
    edges.append(ThreePointArc(P(rB1, z0), P(rm, zm), P(rN, NECK_START_Z)))
    return edges

def build():
    rB = BORE_D / 2
    a = end_edges(False)
    b = [e.reversed() if hasattr(e, "reversed") else e for e in reversed(end_edges(True))]
    rN = NECK_D / 2
    P = lambda r, z: (r, 0, z)
    loop = ([Line(P(rB + BORE_CHAMFER, 0), P(LEAD_LAND_D / 2 - END_CHAMFER_RAD, 0))] + a +
            [Line(P(rN, NECK_START_Z), P(rN, LENGTH - NECK_START_Z))])
    b_edges = list(reversed(end_edges(True)))
    for e in b_edges:
        loop.append(Edge(e.wrapped.Reversed()))
    loop += [Line(P(LEAD_LAND_D / 2 - END_CHAMFER_RAD, LENGTH), P(rB + BORE_CHAMFER, LENGTH)),
             Line(P(rB + BORE_CHAMFER, LENGTH), P(rB, LENGTH - BORE_CHAMFER)),
             Line(P(rB, LENGTH - BORE_CHAMFER), P(rB, BORE_CHAMFER)),
             Line(P(rB, BORE_CHAMFER), P(rB + BORE_CHAMFER, 0))]
    face = Face(Wire(loop))
    part = revolve(face, axis=Axis.Z)
    try:
        ring = [e for e in part.edges().filter_by(GeomType.CIRCLE)
                if min(abs(e.position_at(0).Z - NECK_START_Z), abs(e.position_at(0).Z - (LENGTH - NECK_START_Z))) < 1e-3
                and abs(e.radius - NECK_D / 2) < 1e-3]
        part = fillet(ring, radius=NECK_FILLET)
    except Exception as ex:
        print("neck fillet skipped:", ex)
    return part

if __name__ == "__main__":
    import os
    out = os.path.dirname(os.path.abspath(__file__))
    p = build()
    print("valid:", p.is_valid, "volume mm3:", round(p.volume, 1))
    export_step(p, os.path.join(out, "pcv_adapter.step"))
    export_stl(p, os.path.join(out, "pcv_adapter.stl"), tolerance=0.01, angular_tolerance=0.1)
