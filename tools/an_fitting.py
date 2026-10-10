"""Generic SAE AN / JIC 37-degree male flare fitting end with a real helical UNF thread (build123d).

    from an_fitting import AN, male_an_leg
    leg, L = male_an_leg(AN[10], lead=0.5)        # solid of revolution + thread along local +Z, s = 0 .. L (nose face)

    .venv/bin/python tools/an_fitting.py --size 10 -o an10.step --stl   # standalone bored fitting end + validity check
    .venv/bin/python tools/an_fitting.py --size 6 --no-bore             # outer solid only; exit 1 if not one valid solid

The leg is the OUTER solid only (no bore), so the caller can fuse it to a body and then cut one bore through everything.
Layout along s: plain body (lead, diameter body_d) -> 30 deg step to the relief land (relief_d x relief_w, below the thread
minor so the thread runs out cleanly) -> thread core at the minor diameter with a swept 60 deg UNF ridge -> 45 deg chamfer
-> 37 deg flare cone -> nose face.

Thread ends (why no feather edges): the ridge is swept with blunt, full-profile ends. The back end stops on the full-diameter
core at least 0.25 mm past the relief, and the front end is cut only by the 45 deg start chamfer. Earlier models trimmed the
back end with a 45 deg run-out cone, and that left a paper-thin tail of thread on top of the relief.

Dimensions in mm. Sources: thread ASME B1.1 UNF-2A (major max, UNR minor max); flare end SAE AS4395 / MS33656 (see AN dict).
"""
import math
from build123d import *

IN = 25.4

def _spec(tpi, major_in, minor_in, relief_in, nose_in, cone_in, thread_len_in, bore, body_d, relief_w):
    P = IN / tpi
    return dict(pitch=P, major_d=major_in * IN, minor_d=minor_in * IN, relief_d=relief_in * IN, nose_d=nose_in * IN,
                cone_d=cone_in * IN, thread_len=thread_len_in * IN, bore_d=bore, body_d=body_d, relief_w=relief_w,
                flare_deg=37.0, crest_w=P / 8)

# -10: 7/8-14 UNF-2A (major .8731, UNR minor .7874), AS4395 size 10 relief F .773, nose .641, cone .727, thread .625
#      (the values pcv_an10 v2 uses). Bore 13.0 matches the PCV stock bore (AS4395 A .480-.488).
# -6:  9/16-18 UNF-2A (major .5611, UNR minor .4944 = pitch-dia max .5250 - 0.55 P, same relation as the -10 table values),
#      AS4395 size 06 relief F .481, bore A .293-.301 in -> 7.5 mm. Nose / cone / thread length scaled from the -10 values
#      by the F ratio (.481/.773) and the AS4395 J ratio (.556/.758). Check them against a real -6 fitting before machining.
AN = {
    10: _spec(14, 0.8731, 0.7874, 0.773, 0.641, 0.727, 0.625, bore=13.0, body_d=16.4, relief_w=1.8),
    6:  _spec(18, 0.5611, 0.4944, 0.481, 0.641 * 0.481 / 0.773, 0.727 * 0.481 / 0.773, 0.625 * 0.556 / 0.758,
              bore=7.5, body_d=0.481 * IN, relief_w=1.5),
}

def thread_ridge(S, z0, length, overlap=0.1):
    """Right-hand helical 60 deg ridge (flat crest P/8), swept along a helix on local Z, starting at z0. Blunt profile ends."""
    P, h = S["pitch"], (S["major_d"] - S["minor_d"]) / 2
    rr = S["minor_d"] / 2 - overlap                               # a little into the core so the fuse is solid
    w_root = S["crest_w"] + 2 * (h + overlap) * math.tan(math.radians(30))
    prof = Plane.XZ * Polygon((rr, -w_root / 2), (S["major_d"] / 2, -S["crest_w"] / 2), (S["major_d"] / 2, S["crest_w"] / 2),
                              (rr, w_root / 2), align=None)
    hx = Helix(P, length, rr)
    hx = Wire([hx]) if not isinstance(hx, Wire) else hx
    sp = hx.position_at(0)
    prof = Rot(0, 0, math.degrees(math.atan2(sp.Y, sp.X))) * prof
    return Pos(0, 0, z0) * sweep(prof, path=hx, is_frenet=True), w_root

def male_an_leg(S, lead=0.5, body_d=None):
    """Outer solid of a male AN end on local +Z. Returns (solid, L) with the nose face at s = L."""
    rB = (body_d or S["body_d"]) / 2; rR, rMin, rMaj = S["relief_d"] / 2, S["minor_d"] / 2, S["major_d"] / 2
    rN, rC = S["nose_d"] / 2, S["cone_d"] / 2
    cone_ax = (rC - rN) / math.tan(math.radians(S["flare_deg"]))
    ramp = abs(rR - rB) / math.tan(math.radians(30))                # 30 deg step body -> relief (either way)
    s_rel = lead + ramp; s_thr = s_rel + S["relief_w"]; L = s_thr + S["thread_len"]
    s_cone = L - cone_ax; s_fc = s_cone - (rMin - rC)               # 45 deg chamfer from the minor down to the cone
    pts = [(0, 0), (rB, 0)]
    if lead > 1e-6: pts.append((rB, lead))
    if ramp > 1e-6: pts.append((rR, s_rel))
    pts += [(rR, s_thr), (rMin, s_thr), (rMin, s_fc), (rC, s_cone), (rN, L), (0, L)]
    base = revolve(Plane.XZ * Polygon(*pts, align=None), axis=Axis.Z)
    # ridge: blunt start fully on the core, front cut by the 45 deg start chamfer envelope
    big = rMaj + 0.3
    env = revolve(Plane.XZ * Polygon((0, s_thr), (big, s_thr), (big, s_cone - (big - rC)), (rC, s_cone), (0, s_cone),
                                     align=None), axis=Axis.Z)
    # OCC booleans on swept helices are touchy: try a few equivalent ways and keep the first clean single solid
    for overlap in (0.1, 0.15, 0.2, 0.07):
        _, w_root = thread_ridge(S, 0, S["pitch"], overlap)
        z_start = s_thr + w_root / 2 + 0.25                       # blunt back end fully on the core, 0.25 past the relief
        ridge, _ = thread_ridge(S, z_start, (s_cone - z_start) + S["pitch"], overlap)
        r = ridge & env
        for fuse in (lambda: base + r, lambda: base.fuse(*r.solids()), lambda: base.fuse(*r.solids()).clean()):
            try: leg = fuse()
            except Exception: continue
            if (len(leg.solids()) == 1 and leg.is_valid and abs(leg.bounding_box().size.X - S["major_d"]) < 0.05
                    and leg.volume > base.volume + 0.5 * r.volume):
                return leg, L
    raise RuntimeError("thread fuse failed for every variant")

def nose_bore_chamfer(part, nose_center, bore_d, length=0.3):
    """Light chamfer on the bore edge at the flare nose (safe no-op if the edge isn't found)."""
    try:
        en = [e for e in part.edges().filter_by(GeomType.CIRCLE)
              if (e.arc_center - nose_center).length < 1e-3 and abs(e.radius - bore_d / 2) < 1e-3]
        return chamfer(en, length=length) if en else part
    except Exception as ex:
        print("nose bore chamfer skipped:", ex); return part


def male_an_fitting(size, lead=3.0, body_d=None, bore=True):
    """Standalone male AN end: male_an_leg plus (optionally) the through bore. Returns (part, L)."""
    S = AN[size]
    leg, L = male_an_leg(S, lead=lead, body_d=body_d)
    if bore:
        leg = leg - Pos(0, 0, -1) * Cylinder(S["bore_d"] / 2, L + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        leg = nose_bore_chamfer(leg, Vector(0, 0, L), S["bore_d"])
    return leg, L


def main(argv=None):
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="Build a male SAE AN / JIC 37 deg flare fitting end with a real UNF thread "
                                 "and check it is one valid solid. Writes STEP (and STL with --stl).")
    ap.add_argument("--size", type=int, choices=sorted(AN), default=10, help="AN dash size (default 10)")
    ap.add_argument("--lead", type=float, default=3.0, help="plain body length before the relief, mm (default 3)")
    ap.add_argument("--body-d", type=float, default=None, help="plain body diameter, mm (default from the size table)")
    ap.add_argument("--no-bore", action="store_true", help="outer solid only (to fuse onto your own body)")
    ap.add_argument("-o", "--out", default=None, help="output STEP path (default an<size>_male.step)")
    ap.add_argument("--stl", action="store_true", help="also write an STL next to the STEP")
    a = ap.parse_args(argv)
    S = AN[a.size]
    part, L = male_an_fitting(a.size, lead=a.lead, body_d=a.body_d, bore=not a.no_bore)
    out = a.out or f"an{a.size}_male.step"
    export_step(part, out)
    if a.stl:
        export_stl(part, out.rsplit(".", 1)[0] + ".stl")
    back = import_step(out)
    bb = part.bounding_box().size
    rep = dict(size=a.size, length_mm=round(L, 3), major_d_mm=round(bb.X, 3), pitch_mm=round(S["pitch"], 4),
               volume_mm3=round(part.volume, 1), solids=len(part.solids()), valid=bool(part.is_valid),
               reimport_solids=len(back.solids()), reimport_valid=bool(back.is_valid), step=out)
    print(json.dumps(rep))
    ok = rep["solids"] == 1 and rep["valid"] and rep["reimport_solids"] == 1 and rep["reimport_valid"]
    print("PASS: one valid solid" if ok else "FAIL: not one valid solid")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
