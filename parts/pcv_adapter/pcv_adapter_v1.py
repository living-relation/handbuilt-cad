"""PCV adapter tube - Audi 2016 2.0T (EA888 Gen3), PCV valve -> intake manifold.
Hand-built parametric model from scan Project_26060601 (Creality, rough). All mm.
Z = tube axis, z=0 at the "left" end (the one with the single O-ring groove).
"""
from build123d import *

# ---------------- parameters ----------------
LENGTH          = 53.0   # overall length, face to face
BORE_D          = 13.0   # straight-through bore
BORE_CHAMFER    = 0.8    # 45 deg chamfer at both bore mouths
MAIN_LAND_D     = 21.8   # full end OD (lands between/behind grooves), same at both ends
LEAD_LAND_D     = 21.0   # outermost lead-in land at each end (slightly smaller)
END_CHAMFER_AX  = 1.0    # outer lead-in chamfer at each end face: axial length
END_CHAMFER_RAD = 0.8    #   ... radial depth
NECK_D          = 16.4   # bottleneck OD
GROOVE_FLOOR_D  = 17.6   # O-ring groove root diameter (depth 2.1 from MAIN_LAND_D)
GROOVE_W        = 3.3    # O-ring groove width (suits 2.5 mm cross-section O-ring)
# groove centres measured from z=0 face
LEFT_GROOVE_Z   = 4.6
RIGHT_GROOVE_Z  = (LENGTH - 4.6, LENGTH - 11.25)   # outer, inner groove on right end
# left end body
LEFT_LAND_END_Z = 11.0   # main land stops, taper to neck begins
NECK_START_Z    = 19.2   # taper reaches neck
NECK_END_Z      = 34.1   # neck ends, ramp up toward right end
RIB_D           = 20.4   # shoulder rib ahead of the inner right groove
RIB_START_Z     = 38.6   # ramp reaches rib
TAPER_FILLET    = 2.0    # blend radius at neck/taper junctions
RIB_FILLET      = 0.8    # blend where the right ramp meets the rib
# ---------------------------------------------

def profile_pts():
    rB = BORE_D / 2; rM = MAIN_LAND_D / 2; rL = LEAD_LAND_D / 2
    rN = NECK_D / 2; rG = GROOVE_FLOOR_D / 2; rR = RIB_D / 2; h = GROOVE_W / 2
    g0 = LEFT_GROOVE_Z; g1, g2 = RIGHT_GROOVE_Z     # g1 outer (near right face), g2 inner
    p = [
        (rB + BORE_CHAMFER, 0),
        (rL - END_CHAMFER_RAD, 0),
        (rL, END_CHAMFER_AX),
        (rL, g0 - h), (rG, g0 - h), (rG, g0 + h), (rM, g0 + h),
        (rM, LEFT_LAND_END_Z),
        (rN, NECK_START_Z),
        (rN, NECK_END_Z),
        (rR, RIB_START_Z),
        (rR, g2 - h), (rG, g2 - h), (rG, g2 + h),
        (rM, g2 + h), (rM, g1 - h), (rG, g1 - h), (rG, g1 + h),
        (rL, g1 + h),
        (rL, LENGTH - END_CHAMFER_AX),
        (rL - END_CHAMFER_RAD, LENGTH),
        (rB + BORE_CHAMFER, LENGTH),
        (rB, LENGTH - BORE_CHAMFER),
        (rB, BORE_CHAMFER),
    ]
    return p

def build():
    pts = profile_pts()
    with BuildPart() as part:
        with BuildSketch(Plane.XZ) as sk:
            Polygon(*pts, align=None)
        revolve(axis=Axis.Z)
        # soft blends where the neck meets the tapers (real part is moulded, smooth S-curves)
        def ring(z):
            return [e for e in part.edges().filter_by(GeomType.CIRCLE)
                    if abs(e.position_at(0).Z - z) < 1e-3]
        fillet(ring(NECK_START_Z) + ring(NECK_END_Z) + ring(LEFT_LAND_END_Z), radius=TAPER_FILLET)
        fillet(ring(RIB_START_Z), radius=RIB_FILLET)
    return part.part

if __name__ == "__main__":
    import os
    out = os.path.dirname(os.path.abspath(__file__))
    p = build()
    print("valid:", p.is_valid, "volume mm3:", round(p.volume, 1))
    export_step(p, os.path.join(out, "pcv_adapter.step"))
    export_stl(p, os.path.join(out, "pcv_adapter.stl"), tolerance=0.01, angular_tolerance=0.1)
