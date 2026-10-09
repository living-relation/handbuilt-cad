"""Pedal adapter - clean parametric model rebuilt from the 3D scan.

Coordinates are the Fairsolid part frame of runs/pedal_adapter (20_frame.json):
rigid rotation + translation of the scan only, scale 1.0, millimetres.
  +X  toward the flat side plates, +Y toward the connector, +Z up (lid side).
  Z = 0 is the frame's base reference; the housing underside is at Z = 17.2.

Every size below was measured from the scan (10_clean.ply, noise 0.09 mm)
and snapped: levels/lengths to 0.1 mm, diameters to 0.5 mm or a standard size,
angles to whole degrees. Scan texture is deliberately NOT followed.

The swept body (housing side walls, rounded left nose and the scoop roof)
comes from measured station profiles in pedal_sections.py, low-pass filtered
so they are smooth; every flat face is then cut by an exact plane below.
"""
from math import radians, sin, cos
from build123d import *
from pedal_sections import BODY_STATIONS

# ---------------------------------------------------------------- parameters
# Main levels (Z)
Z_BOTTOM      = 17.2   # housing underside, flat
Z_LID         = 50.7   # main lid top, flat
Z_PAD         = 52.0   # raised pad on the lid (motor circle + left pad)
Z_LEDGE       = 24.2   # underside of the right-hand ledge / scoop side wall
Z_PLATE_TOP   = 51.0   # top of the front side plate (sits 0.3 proud of lid)

# Side walls (X)
X_SIDE        = 38.3   # outer face of both side plates (front plate + scoop wall)
X_RECESS      = 35.5   # recessed housing wall between the two plates
Y_RECESS      = (-42.0, -9.0)   # recess runs between these Y values
X_PLATE_IN    = 30.5   # inner face of the front plate / ear

# Lid features
PAD_CENTER    = (13.2, -32.8)  # motor / gear axis (same axis top and bottom)
PAD_DIA       = 40.0           # round raised pad on the lid
PAD_LEFT      = [(-30.0, -3.5), (-12.0, -5.5), (-5.5, -21.0), (-8.5, -30.0),
                 (-23.0, -34.0), (-39.0, -22.0)]   # left raised pad outline (XY)
LID_STEP_Y_MIN = -44.0         # lid flats end here; scoop roof takes over
DOME_DIA      = 8.0            # small round boss on the lid at the motor axis
DOME_TOP      = 53.7
DOME_FILLET   = 0.8
DOME_HOLE_DIA = 2.5            # centre dimple
DOME_HOLE_DEPTH = 1.0

# Gear boss under the housing
GEAR_RING_DIA = 40.8           # round wall around the gear (also bounds the ledge)
GEAR_DISC_Z   = 16.4           # disc face just under the housing bottom
STAR_POINTS   = 8
STAR_TIP_R    = 16.5
STAR_ROOT_R   = 6.5
STAR_PHASE_DEG = 8.5           # angle of first spike from +X
STAR_BOTTOM_Z = 10.5
STAR_HUB_HOLE_DIA = 7.0
STAR_HUB_HOLE_TOP = 15.5

# Ledge under the scoop side wall (clean step, replaces the scanned "ramp")
X_LEDGE       = 28.5           # ledge wall for Y < about -46 (then follows the gear ring)
Y_LEDGE_END   = -19.0          # ledge stops here (front of the gear ring)

# Screw posts on the underside ("domed studs" -> clean round posts)
POST_CENTERS  = [(21.3, -62.7), (6.9, 34.2), (-32.1, 16.2)]
POST_DIA      = 9.0
POST_BOTTOM_Z = 15.4           # 1.8 mm proud of the underside
POST_FILLET   = 1.2
POST_HOLE_DIA = 3.5
POST_HOLE_DEPTH = 2.5
LOBE_DIA      = 9.5            # vertical round lobe around the front post
LOBE_CENTER   = (6.9, 34.5)

# Small ring on the underside
RING_CENTER   = (-19.5, -38.0)
RING_OD, RING_ID = 10.0, 7.0
RING_BOTTOM_Z = 15.4

# Left-side base flange step (straight part, between the left lobe and the nose)
LEFT_FLANGE_Y = (-6.0, 4.0)
LEFT_WALL_X   = -32.5          # upper left wall
LEFT_FLANGE_X = -35.0          # lower flange face
LEFT_STEP_Z   = (31.0, 33.5)   # 45 deg step from flange to wall

# Front end of the housing (plan outline, XY) - applies for Y > FRONT_Y0
FRONT_Y0      = 14.0
FRONT_OUTLINE = [(38.3, 14.0), (38.3, 22.8), (31.5, 23.0), (26.0, 28.5), (21.0, 30.3),
                 (11.0, 32.6), (-4.0, 33.1), (-8.0, 32.6), (-34.0, 20.5), (-38.5, 16.0),
                 (-45.0, 14.0)]                       # upper housing, 25 deg front face on the left
FLANGE_OFFSET = 2.2            # lower base flange stands out this far from the front face
FLANGE_TOP_Z  = 30.5           # flange runs from Z_BOTTOM up to here
FLANGE_X     = (-37.0, 24.0)   # flange runs between these X values
FLANGE_LOBE_DIA = 13.5         # flange wraps the front lobe

# Connector (rotated 25 deg from +Y toward -X)
CONN_ANGLE_DEG = 25.0
CONN_U        = (30.0, 56.0)   # along its axis, from the frame origin
CONN_V        = (-15.0, 11.0)  # across (26.0 wide)
SOCKET_V      = (-13.0, 8.0)   # socket opening in the end face (across)
SOCKET_Z      = (18.0, 23.5)
SOCKET_DEPTH  = 6.0            # how far the socket goes in from the end face
SOCKET_FILLET = 1.5
CONN_Z        = (14.0, 25.5)   # 11.5 tall
CONN_FILLET   = 2.0

# Ear (mounting tab under the front plate) and gusset
EAR_Y         = (-8.5, 23.5)   # front plate extent in Y
EAR_ARC_CENTER = (9.0, 7.4)    # (Y, Z) - concentric with the hole
EAR_ARC_R     = 11.0
EAR_HOLE_DIA  = 6.4            # M6 fine clearance (ISO 273)
GUSSET_X      = (30.5, 35.5)
GUSSET_TOP    = (-24.0, 24.2)  # (Y, Z) where the 45 deg gusset meets the ledge

# Pocket grid on the front side plate (in the X_SIDE face)
POCKET_Y      = [6.7 + (i - 1.5) * 7.25 for i in range(4)]   # 4 columns, 7.25 pitch
POCKET_Z      = [34.7 + (1.5 - j) * 7.5 for j in range(4)]   # 4 rows, 7.5 pitch
POCKET_SIZE   = 4.0            # square pockets with round corners
POCKET_CORNER = 1.0
POCKET_DEPTH  = 3.0            # scan only sees ~1.5-5 mm into these; 3.0 is a judgment call
POCKET_BIG    = (1, 1, 6.0)    # (column, row, diameter): one larger round hole
POCKET_SKIP   = [(3, 3)]       # no pocket here on the part

# Scan crop plane at the open scoop end (the scan stops here)
MOUTH_ORIGIN  = (9.85, -80.52, 33.76)
MOUTH_NORMAL  = (0.228, 0.936, 0.268)

BIG = 400.0
# ---------------------------------------------------------------- helpers

def box_between(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)

def cyl_z(cx, cy, d, z0, z1):
    return Pos(cx, cy, z0) * Cylinder(d / 2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))

def prism_xy(points, z0, z1):
    face = Face(Wire.make_polygon([Vector(x, y, z0) for x, y in points], close=True))
    return extrude(face, amount=z1 - z0, dir=(0, 0, 1))

def prism_yz(points_yz, x0, x1):
    pts = [Vector(x0, y, z) for y, z in points_yz]
    face = Face(Wire.make_polygon(pts, close=True))
    return extrude(face, amount=x1 - x0, dir=(1, 0, 0))

# ---------------------------------------------------------------- body
def station_wire(y, pts):
    # same (uniform) parameters on every station so the loft surface stays light
    n = len(pts)
    return Wire([Edge.make_spline([Vector(x, y, z) for x, z in pts], periodic=True,
                                  parameters=[i / n for i in range(n + 1)])])

def build():
    wires = [station_wire(y, p) for y, p in BODY_STATIONS]
    body = Solid.make_loft(wires)
    y_front = BODY_STATIONS[0][0]
    # straight extension of the first station toward the front end
    front = extrude(Face(wires[0]), amount=40.0, dir=(0, 1, 0))
    body = body.fuse(front, glue=True).clean()
    # plan trim of the front end
    from shapely.geometry import Polygon as SPoly, box as sbox
    keep2d = SPoly(FRONT_OUTLINE).union(sbox(-200, -200, 200, FRONT_Y0 + 0.5))
    keep = prism_xy(list(keep2d.exterior.coords)[:-1], -50, 120)
    body = body & keep
    # exact flats
    body = body & box_between(-BIG, X_SIDE, -BIG, BIG, Z_BOTTOM, BIG)
    body = body - box_between(-BIG, BIG, LID_STEP_Y_MIN, BIG, Z_LID, BIG)   # flat lid; pads are added back below
    body = body - box_between(X_RECESS, BIG, Y_RECESS[0], Y_RECESS[1], -BIG, BIG)
    ledge = box_between(X_LEDGE, BIG, -BIG, Y_LEDGE_END, -BIG, Z_LEDGE)
    ledge = ledge - cyl_z(*PAD_CENTER, GEAR_RING_DIA, -BIG, BIG)
    body = body - ledge
    # raised pads on the lid
    body = body + cyl_z(*PAD_CENTER, PAD_DIA, Z_LID - 0.5, Z_PAD) + prism_xy(PAD_LEFT, Z_LID - 0.5, Z_PAD)

    # left flange step
    lf = prism_yz([(0, 0)], 0, 1) if False else None
    pts = [Vector(-60, 0, LEFT_STEP_Z[0]), Vector(LEFT_FLANGE_X, 0, LEFT_STEP_Z[0]), Vector(LEFT_WALL_X, 0, LEFT_STEP_Z[1]),
           Vector(LEFT_WALL_X, 0, 90), Vector(-60, 0, 90)]
    lcut = extrude(Face(Wire.make_polygon([Vector(p.X, LEFT_FLANGE_Y[0], p.Z) for p in pts], close=True)), amount=LEFT_FLANGE_Y[1] - LEFT_FLANGE_Y[0], dir=(0, 1, 0))
    body = body - lcut
    # lower base flange on the front end
    from shapely.geometry import Polygon as SPoly, box as sbox
    fl = SPoly(FRONT_OUTLINE).buffer(FLANGE_OFFSET, join_style=2).intersection(sbox(FLANGE_X[0], FRONT_Y0, FLANGE_X[1], 80))
    flange = prism_xy(list(fl.exterior.coords)[:-1], Z_BOTTOM, FLANGE_TOP_Z)
    flange = flange + cyl_z(*LOBE_CENTER, FLANGE_LOBE_DIA, Z_BOTTOM, FLANGE_TOP_Z)
    body = body + flange
    # front lobe and posts
    body = body + cyl_z(*LOBE_CENTER, LOBE_DIA, Z_BOTTOM, Z_LID)
    for cx, cy in POST_CENTERS:
        post = cyl_z(cx, cy, POST_DIA, POST_BOTTOM_Z, Z_BOTTOM + 0.5)
        post = fillet(post.edges().sort_by(Axis.Z)[0], POST_FILLET)
        post = post - cyl_z(cx, cy, POST_HOLE_DIA, POST_BOTTOM_Z - 1, POST_BOTTOM_Z + POST_HOLE_DEPTH)
        body = body + post
    # lid dome
    dome = cyl_z(*PAD_CENTER, DOME_DIA, Z_PAD - 0.5, DOME_TOP)
    dome = fillet(dome.edges().sort_by(Axis.Z)[-1], DOME_FILLET)
    dome = dome - cyl_z(*PAD_CENTER, DOME_HOLE_DIA, DOME_TOP - DOME_HOLE_DEPTH, DOME_TOP + 1)
    body = body + dome
    # gear disc and star
    body = body + cyl_z(*PAD_CENTER, GEAR_RING_DIA, GEAR_DISC_Z, Z_BOTTOM + 0.5)
    star_pts = []
    for i in range(2 * STAR_POINTS):
        a = radians(STAR_PHASE_DEG + i * 180.0 / STAR_POINTS)
        r = STAR_TIP_R if i % 2 == 0 else STAR_ROOT_R
        star_pts.append((PAD_CENTER[0] + r * cos(a), PAD_CENTER[1] + r * sin(a)))
    star = prism_xy(star_pts, STAR_BOTTOM_Z, GEAR_DISC_Z + 0.2)
    star = star - cyl_z(*PAD_CENTER, STAR_HUB_HOLE_DIA, STAR_BOTTOM_Z - 1, STAR_HUB_HOLE_TOP)
    body = body + star
    # ring
    ring = cyl_z(*RING_CENTER, RING_OD, RING_BOTTOM_Z, Z_BOTTOM + 0.5) - cyl_z(*RING_CENTER, RING_ID, RING_BOTTOM_Z - 1, Z_BOTTOM + 1)
    body = body + ring
    # connector
    a = radians(CONN_ANGLE_DEG)
    u = Vector(-sin(a), cos(a), 0); v = Vector(cos(a), sin(a), 0)
    uc = (CONN_U[0] + CONN_U[1]) / 2; vc = (CONN_V[0] + CONN_V[1]) / 2
    c = u * uc + v * vc
    conn = Box(CONN_V[1] - CONN_V[0], CONN_U[1] - CONN_U[0], CONN_Z[1] - CONN_Z[0])
    conn = fillet(conn.edges().filter_by(Axis.Y), CONN_FILLET)
    sock = Box(SOCKET_V[1] - SOCKET_V[0], SOCKET_DEPTH * 2, SOCKET_Z[1] - SOCKET_Z[0])
    sock = fillet(sock.edges().filter_by(Axis.Y), SOCKET_FILLET)
    sock = Pos((SOCKET_V[0] + SOCKET_V[1]) / 2 - vc, (CONN_U[1] - CONN_U[0]) / 2, (SOCKET_Z[0] + SOCKET_Z[1]) / 2 - (CONN_Z[0] + CONN_Z[1]) / 2) * sock
    conn = conn - sock
    conn = Pos(c.X, c.Y, (CONN_Z[0] + CONN_Z[1]) / 2) * Rot(0, 0, CONN_ANGLE_DEG) * conn
    body = body + conn
    # ear plate with hole, and gusset
    ear_c = Pos(X_PLATE_IN, EAR_ARC_CENTER[0], EAR_ARC_CENTER[1]) * Rot(0, 90, 0) * Cylinder(EAR_ARC_R, X_SIDE - X_PLATE_IN, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ear_r = box_between(X_PLATE_IN, X_SIDE, EAR_Y[0], EAR_Y[1], EAR_ARC_CENTER[1], Z_PLATE_TOP)
    ear_link = prism_yz([(EAR_Y[0], 12.0), (EAR_ARC_CENTER[0] - EAR_ARC_R, EAR_ARC_CENTER[1]),
                         (EAR_ARC_CENTER[0] + EAR_ARC_R, EAR_ARC_CENTER[1]), (EAR_Y[1], 12.0),
                         (EAR_Y[1], Z_PLATE_TOP), (EAR_Y[0], Z_PLATE_TOP)], X_PLATE_IN, X_SIDE)
    ear = ear_c + ear_r + ear_link
    t = 0.7071
    gus = prism_yz([GUSSET_TOP, (EAR_Y[0], GUSSET_TOP[1]), (EAR_Y[0], 12.0),
                    (EAR_ARC_CENTER[0] - EAR_ARC_R * t, EAR_ARC_CENTER[1] - EAR_ARC_R * t)], GUSSET_X[0], GUSSET_X[1])
    body = body + ear + gus
    hole = Pos(X_PLATE_IN - 5, EAR_ARC_CENTER[0], EAR_ARC_CENTER[1]) * Rot(0, 90, 0) * Cylinder(EAR_HOLE_DIA / 2, X_SIDE - X_PLATE_IN + 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = body - hole
    # pocket grid on the front plate
    for i, py in enumerate(POCKET_Y):
        for j, pz in enumerate(POCKET_Z):
            if (i, j) in POCKET_SKIP: continue
            if (i, j) == POCKET_BIG[:2]:
                pk = Pos(X_SIDE - POCKET_DEPTH, py, pz) * Rot(0, 90, 0) * Cylinder(POCKET_BIG[2] / 2, POCKET_DEPTH + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
            else:
                pk = Box(POCKET_DEPTH + 1, POCKET_SIZE, POCKET_SIZE)
                pk = fillet(pk.edges().filter_by(Axis.X), POCKET_CORNER)
                pk = Pos(X_SIDE - POCKET_DEPTH + (POCKET_DEPTH + 1) / 2, py, pz) * pk
            body = body - pk
    # scan crop plane
    body = split(body, Plane(origin=MOUTH_ORIGIN, z_dir=MOUTH_NORMAL), keep=Keep.TOP)
    return body

if __name__ == "__main__":
    import time
    t0 = time.time()
    part = build()
    part = part.clean() if hasattr(part, "clean") else part
    print("valid", part.is_valid, "volume %.0f mm3" % part.volume, "bbox", part.bounding_box(), "%.1fs" % (time.time() - t0))
    export_step(part, "pedal_adapter.step")
    export_stl(part, "pedal_adapter.stl", tolerance=0.02, angular_tolerance=0.1)











