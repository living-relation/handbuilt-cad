"""Generic SAE AN / JIC 37-degree male flare fitting end with a real helical UNF thread (build123d).

    from an_fitting import AN, male_an_leg
    leg, L = male_an_leg(AN[10], lead=0.5)        # solid of revolution + thread along local +Z, s = 0 .. L (nose face)

    .venv/bin/python tools/an_fitting.py --size 10 -o an10.step --stl   # standalone bored fitting end + validity check
    .venv/bin/python tools/an_fitting.py --size 6 --no-bore             # outer solid only; exit 1 if not one valid solid
    .venv/bin/python tools/an_fitting.py --selfcheck                    # build -6 and -10, MEASURE them, compare to STD; exit 1 on any miss

The leg is the OUTER solid only (no bore), so the caller can fuse it to a body and then cut one bore through everything
(use bore_d = STD bore A, or keep a bigger body bore and taper down to A just behind the nose).
Layout along s (nose face at s = L):
    body (lead, body_d) -> shoulder at s = L - J (30 deg ramp if the body is smaller than the relief, square face with an
    R root radius if it is bigger) -> relief land F x Q, ending in an R root radius up to the thread minor -> thread core
    with a swept 60 deg UNF ridge -> 45 deg start chamfer from the minor down to the cone major C, starting at B from the
    nose -> short land at C -> 37 deg cone down to the nose diameter D -> nose face.

Thread ends (why no feather edges): the ridge is swept with blunt, full-profile ends. The back end stops on the full core
0.25 mm past the relief radius; the front end is cut only by the 45 deg start chamfer.

All flare-end numbers come from STD below (MS33656 / AS4395 / ISO 8434-2), threads from ASME B1.1 UNF-2A. Dimensions in mm.
"""
import math
from build123d import *

IN = 25.4
MS, AS, ISO = "MS33656J", "AS4395B", "ISO 8434-2:2007"
B11 = "ASME B1.1 UNF-2A (amesweb / steelmasters UNF tables)"

def _r(lo_in=None, hi_in=None, lo=None, hi=None):
    """(lo, hi) in mm from inch or mm limits."""
    return (lo if lo is not None else lo_in * IN, hi if hi is not None else hi_in * IN)

# Doc with all sources and links: Sidekick, "37 deg AN/JIC male flare fitting end: -6 and -10 dimensions" (2026-10-11).
# STD[size][key] = (design value mm, (lo, hi) mm, source). Design value = middle of the range that satisfies BOTH
# MS33656/AS4395 and ISO 8434-2 where they differ (see the doc notes); lo/hi = that common range (what --selfcheck checks).
STD = {
    10: dict(
        tpi=(14, (14, 14), B11 + " 7/8-14"),
        major_d=(0.8707 * IN, _r(0.8631, 0.8734), B11 + ": major .8631-.8734 (model sized for mid pitch dia)"),
        pitch_d=(0.8243 * IN, _r(0.8216, 0.8270), B11 + ": pitch dia .8216-.8270"),
        minor_d=(0.7856 * IN, (0.0, 0.7884 * IN), B11 + ": UNR minor max .7884 (= major - 1.19078 P)"),
        J=(19.25, _r(lo=18.90, hi=19.63), MS + " Table I col J .758 +-.015 (= " + AS + " Table 1B col J); " + ISO + " Table 7 col i1 19.3 +-0.4"),
        D=(13.69, _r(lo=13.62, hi=13.77), MS + " Table I col D .539 +-.003; " + ISO + " Table 7 col d2 13.7 +-0.08"),
        C=(19.42, _r(lo=19.35, hi=19.48), MS + " Table I col C .767 +0/-.005; " + ISO + " Table 7 col d4 19.5 +-0.15"),
        cone_deg=(37.0, (36.5, 37.5), ISO + " Fig. 4: 37 deg +-30'; " + MS + " note 3 (angles +-1/2 deg)"),
        B=(6.97, _r(lo=6.80, hi=7.14), MS + " Table I col B .266 +.015/-0; " + ISO + " Table 7 col i2 7.0 +-0.2"),
        F=(19.60, _r(lo=19.56, hi=19.65), MS + " Table I col F .773 +.002/-.003; " + ISO + " Table 7 col d3 19.5 +-0.15 (overlap 19.56-19.65)"),
        Q=(2.91, _r(lo=2.72, hi=3.10), MS + " Table I col Q (= " + AS + " Table 1B col M) .107 +.015/-0; " + ISO + " Table 7 col f 3.1 +-0.4"),
        A=(12.29, _r(lo=12.19, hi=12.40), MS + " Table I col A .484 +-.004; " + ISO + " Table 7 col d1 12.3 +-0.2"),
        chamfer_deg=(45.0, (40.0, 50.0), MS + " sheet 1: 45 deg +-5; " + ISO + " Fig. 4"),
        root_r=(0.5, _r(lo=0.41, hi=0.79), MS + " sheet 1: R .016-.031; " + ISO + " Fig. 4: R0.5"),
        shoulder_d=(28.02, _r(lo=27.76, hi=28.27), AS + " Table 1B col L 1.103 +-.010 (MS K 1.111); only used by --selfcheck"),
    ),
    6: dict(
        tpi=(18, (18, 18), B11 + " 9/16-18"),
        major_d=(0.5588 * IN, _r(0.5524, 0.5611), B11 + ": major .5524-.5611 (model sized for mid pitch dia)"),
        pitch_d=(0.52275 * IN, _r(0.5205, 0.5250), B11 + ": pitch dia .5205-.5250"),
        minor_d=(0.4927 * IN, (0.0, 0.4950 * IN), B11 + ": UNR minor max .4950 (= major - 1.19078 P)"),
        J=(14.12, _r(lo=13.74, hi=14.50), MS + " Table I col J .556 +-.015 (= " + AS + " Table 1B col J); " + ISO + " Table 7 col i1 14.1 +-0.4"),
        D=(8.08, _r(lo=8.02, hi=8.15), MS + " Table I col D .318 +-.003; " + ISO + " Table 7 col d2 8.1 +-0.08"),
        C=(12.03, _r(lo=11.96, hi=12.09), MS + " Table I col C .476 +0/-.005; " + ISO + " Table 7 col d4 12.1 +-0.15"),
        cone_deg=(37.0, (36.5, 37.5), ISO + " Fig. 4: 37 deg +-30'; " + MS + " note 3 (angles +-1/2 deg)"),
        B=(5.20, _r(lo=5.03, hi=5.40), MS + " Table I col B .198 +.015/-0; " + ISO + " Table 7 col i2 5.2 +-0.2"),
        F=(12.20, _r(lo=12.14, hi=12.25), MS + " Table I col F .481 +.002/-.003; " + ISO + " Table 7 col d3 12.1 +-0.15 (overlap 12.14-12.25)"),
        Q=(2.30, _r(lo=2.11, hi=2.49), MS + " Table I col Q (= " + AS + " Table 1B col M) .083 +.015/-0; " + ISO + " Table 7 col f 2.5 +-0.4"),
        A=(7.54, _r(lo=7.44, hi=7.65), MS + " Table I col A .297 +-.004; " + ISO + " Table 7 col d1 7.5 +-0.2"),
        chamfer_deg=(45.0, (40.0, 50.0), MS + " sheet 1: 45 deg +-5; " + ISO + " Fig. 4"),
        root_r=(0.5, _r(lo=0.41, hi=0.79), MS + " sheet 1: R .016-.031; " + ISO + " Fig. 4: R0.5"),
        shoulder_d=(20.12, _r(lo=19.87, hi=20.37), AS + " Table 1B col L .792 +-.010 (MS K .799); only used by --selfcheck"),
    ),
}

def _spec(size, body_d, nose_chamfer):
    T = {k: v[0] for k, v in STD[size].items()}; P = IN / T["tpi"]
    return dict(size=size, pitch=P, major_d=T["major_d"], minor_d=T["minor_d"], relief_d=T["F"], relief_w=T["Q"],
                nose_d=T["D"], cone_d=T["C"], flare_deg=T["cone_deg"], J=T["J"], B=T["B"], root_r=T["root_r"],
                chamfer_deg=T["chamfer_deg"], bore_d=T["A"], thread_len=T["J"] - T["Q"], body_d=body_d,
                crest_w=P / 8, nose_chamfer=nose_chamfer)

# body_d = plain body before the shoulder (tube OD of the PCV pipes for -10; = relief for the -6 tee branch).
# nose_chamfer: break on the bore edge at the nose, kept to about a quarter of the (D - A) / 2 nose face.
AN = {10: _spec(10, body_d=16.4, nose_chamfer=0.15), 6: _spec(6, body_d=STD[6]["F"][0], nose_chamfer=0.07)}

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

def _profile(S, lead, rB):
    """Closed (r, s) outline of the leg core as build123d edges in the XZ plane (x = radius, z = s)."""
    rR, rMin, rN, rC, R = S["relief_d"] / 2, S["minor_d"] / 2, S["nose_d"] / 2, S["cone_d"] / 2, S["root_r"]
    tc = math.tan(math.radians(S["chamfer_deg"]))
    ramp = (rR - rB) / math.tan(math.radians(30)) if rB < rR else 0.0   # body smaller than relief: 30 deg ramp up
    s_sh = lead + ramp; L = s_sh + S["J"]                                # shoulder at L - J
    s_core = s_sh + S["relief_w"]                                        # relief radius meets the minor here
    hR = rMin - rR; aR = math.sqrt(R * R - (R - hR) ** 2)                # axial run of the R root radius (relief -> minor)
    s_B = L - S["B"]; s_cone = L - (rC - rN) / math.tan(math.radians(S["flare_deg"]))
    s_fc = s_B - (rMin - rC) / tc                                        # chamfer meets the minor
    P = lambda r, s: Vector(r, 0, s)
    E = [Line(P(0, 0), P(rB, 0))]
    if rB > rR + R:                                                      # square shoulder face + R root radius
        E += [Line(P(rB, 0), P(rB, s_sh)), Line(P(rB, s_sh), P(rR + R, s_sh)),
              ThreePointArc(P(rR + R, s_sh), P(rR + R - R * math.sin(math.pi / 4), s_sh + R - R * math.cos(math.pi / 4)), P(rR, s_sh + R))]
        cur = P(rR, s_sh + R)
    else:
        if lead > 1e-6: E.append(Line(P(rB, 0), P(rB, lead)))
        if ramp > 1e-6: E.append(Line(P(rB, lead), P(rR, s_sh)))
        cur = P(rR, s_sh)
    a0 = P(rR, s_core - aR)
    E.append(Line(cur, a0))
    um = (aR / 2); mid = P(rR + R - math.sqrt(R * R - um * um), s_core - aR + um)
    E.append(ThreePointArc(a0, mid, P(rMin, s_core)))
    E += [Line(P(rMin, s_core), P(rMin, s_fc)), Line(P(rMin, s_fc), P(rC, s_B)), Line(P(rC, s_B), P(rC, s_cone)),
          Line(P(rC, s_cone), P(rN, L)), Line(P(rN, L), P(0, L)), Line(P(0, L), P(0, 0))]
    return E, dict(L=L, s_sh=s_sh, s_core=s_core, s_B=s_B, s_cone=s_cone)

def male_an_leg(S, lead=0.5, body_d=None):
    """Outer solid of a male AN end on local +Z. Returns (solid, L) with the nose face at s = L."""
    rB = (body_d or S["body_d"]) / 2; rMaj, rC = S["major_d"] / 2, S["cone_d"] / 2
    E, s = _profile(S, lead, rB); L = s["L"]
    base = revolve(Face(Wire(E)), axis=Axis.Z)
    big = rMaj + 0.3; tc = math.tan(math.radians(S["chamfer_deg"]))
    env = revolve(Plane.XZ * Polygon((0, s["s_core"]), (big, s["s_core"]), (big, s["s_B"] - (big - rC) / tc), (rC, s["s_B"]),
                                     (0, s["s_B"]), align=None), axis=Axis.Z)
    # OCC booleans on swept helices are touchy: try a few equivalent ways and keep the first clean single solid
    for overlap in (0.1, 0.15, 0.2, 0.07):
        _, w_root = thread_ridge(S, 0, S["pitch"], overlap)
        z_start = s["s_core"] + w_root / 2 + 0.25                 # blunt back end fully on the core
        ridge, _ = thread_ridge(S, z_start, (s["s_B"] - z_start) + S["pitch"], overlap)
        r = ridge & env
        for fuse in (lambda: base + r, lambda: base.fuse(*r.solids()), lambda: base.fuse(*r.solids()).clean()):
            try: leg = fuse()
            except Exception: continue
            if (len(leg.solids()) == 1 and leg.is_valid and abs(leg.bounding_box().size.X - max(S["major_d"], 2 * rB)) < 0.05
                    and leg.volume > base.volume + 0.5 * r.volume):
                return leg, L
    raise RuntimeError("thread fuse failed for every variant")

def nose_bore_chamfer(part, nose_center, bore_d, length=0.15):
    """Light chamfer on the bore edge at the flare nose (safe no-op if the edge isn't found)."""
    try:
        en = [e for e in part.edges().filter_by(GeomType.CIRCLE)
              if (e.arc_center - nose_center).length < 1e-3 and abs(e.radius - bore_d / 2) < 1e-3]
        return chamfer(en, length=length) if en else part
    except Exception as ex:
        print("nose bore chamfer skipped:", ex); return part

def male_an_fitting(size, lead=3.0, body_d=None, bore=True):
    """Standalone male AN end: male_an_leg plus (optionally) the through bore A. Returns (part, L)."""
    S = AN[size]
    leg, L = male_an_leg(S, lead=lead, body_d=body_d)
    if bore:
        leg = leg - Pos(0, 0, -1) * Cylinder(S["bore_d"] / 2, L + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        leg = nose_bore_chamfer(leg, Vector(0, 0, L), S["bore_d"], S["nose_chamfer"])
    return leg, L

# ------------------------------------------------------------------ measure + selfcheck
def measure_fitting(part, dz=0.01, n_ang=36):
    """Measure a male flare end on +Z (nose face = top) from its MESH, not from parameters. Returns dict of mm / deg."""
    import os, tempfile, numpy as np, trimesh
    fd, tmp = tempfile.mkstemp(suffix=".stl"); os.close(fd)
    export_stl(part, tmp, tolerance=0.003, angular_tolerance=0.05); m = trimesh.load(tmp); os.remove(tmp)
    zlo, zhi = m.bounds[0][2], m.bounds[1][2]; R0 = float(np.abs(m.bounds[:, :2]).max()) + 5
    zs = np.arange(zlo + dz, zhi - dz / 2, dz); th = np.arange(n_ang) * 2 * np.pi / n_ang
    Z, TH = np.meshgrid(zs, th, indexing="ij"); c, s = np.cos(TH).ravel(), np.sin(TH).ravel()
    o = np.c_[R0 * c, R0 * s, Z.ravel()]; d = np.c_[-c, -s, np.zeros_like(c)]
    r = np.full(len(o), np.nan)
    for i in range(0, len(o), 2000):
        loc, ir, _ = m.ray.intersects_location(o[i:i + 2000], d[i:i + 2000], multiple_hits=False)
        r[i + ir] = np.hypot(loc[:, 0], loc[:, 1])
    r = r.reshape(len(zs), n_ang); rmin, rmax = np.nanmin(r, 1), np.nanmax(r, 1)
    bo = np.c_[np.zeros(len(zs)), np.zeros(len(zs)), zs]; bl, bi, _ = m.ray.intersects_location(bo, np.tile([1.0, 0, 0], (len(zs), 1)), multiple_hits=False)
    bore = np.full(len(zs), np.nan); bore[bi] = np.hypot(bl[:, 0], bl[:, 1])
    slope = np.gradient(rmin, dz)
    def run(i, ok, step, seek=0):                              # contiguous indices from i while ok(j) (first skip up to seek)
        for _ in range(seek):
            if not (0 <= i < len(zs)) or ok(i): break
            i += step
        out = []
        while 0 <= i < len(zs) and ok(i): out.append(i); i += step
        return out
    res = {}
    top = len(zs) - 2
    cone = run(top, lambda j: -0.95 < slope[j] < -0.55, -1)[2:-2]            # 37 deg: dr/dz = -0.754
    b, a = np.polyfit(zs[cone], rmin[cone], 1)
    res["cone_deg"] = math.degrees(math.atan(-b)); res["D"] = 2 * (a + b * zhi)
    land = run(cone[-1] - 1, lambda j: abs(slope[j]) < 0.05, -1, seek=40)
    land = land[1:-1] if len(land) > 4 else land
    res["C"] = 2 * float(np.median(rmin[land])) if land else float("nan")
    zB = zs[land[-1]] if land else zs[cone[-1]]
    res["B"] = zhi - zB
    ch = run((land[-1] if land else cone[-1]) - 1, lambda j: -1.4 < slope[j] < -0.6, -1, seek=40)[2:-2]
    if len(ch) >= 3:
        b2, _ = np.polyfit(zs[ch], rmin[ch], 1); res["chamfer_deg"] = math.degrees(math.atan(-b2))
    gap = rmax - rmin; thr = np.where(gap > 0.6 * np.nanmax(gap))[0]
    full = thr[(zs[thr] > zs[thr].min() + 0.6) & (zs[thr] < (zs[ch].min() if len(ch) else zB) - 0.6)]
    res["major_d"] = 2 * float(np.percentile(rmax[full], 99)); res["minor_d"] = 2 * float(np.median(rmin[full]))
    res["pitch_d"] = 2 * float(np.median(r[full].ravel()))     # half the samples above the pitch line: width there = P/2
    gaps = []                                                   # ridge-to-ridge spacing along z at every angle
    for k in range(n_ang):
        hi = r[full, k] > (res["major_d"] + res["minor_d"]) / 4; e = np.where(np.diff(hi.astype(int)) == 1)[0]
        if len(e) >= 3: gaps.append((zs[full][e[-1]] - zs[full][e[0]]) / (len(e) - 1))
    res["pitch"] = float(np.median(gaps)) if gaps else float("nan")
    res["tpi"] = IN / res["pitch"] if res["pitch"] == res["pitch"] else float("nan")
    # relief: lowest core radius behind the thread
    below = np.arange(0, thr.min()); ib = below[np.argmin(rmin[below])]; rF = rmin[ib]; res["F"] = 2 * float(rF)
    floor = run(ib, lambda j: abs(rmin[j] - rF) < 0.01, -1) + run(ib, lambda j: abs(rmin[j] - rF) < 0.01, 1)
    f_lo, f_hi = zs[min(floor)], zs[max(floor)]
    face = [j for j in range(min(floor) - 1, max(min(floor) - 80, 0), -1) if rmin[j] > rF + 0.45]
    z_sh = zs[face[0]] if face and f_lo - zs[face[0]] <= 0.65 else f_lo
    res["J"] = zhi - z_sh
    rminor = res["minor_d"] / 2; core = run(max(floor) + 1, lambda j: rmin[j] < rminor - 0.003, 1)
    z_core = zs[core[-1] + 1] if core else f_hi
    res["Q"] = z_core - z_sh
    def arc_r(idx):                                             # circle tangent to the floor through the points: R
        if len(idx) < 4: return float("nan")
        z = zs[idx]; u = rmin[idx] - rF
        A = np.c_[2 * z, -np.ones_like(z), 2 * u]; sol = np.linalg.lstsq(A, z * z + u * u, rcond=None)[0]; return float(sol[2])
    res["root_r"] = arc_r([j for j in core if rmin[j] > rF + 0.005])
    if face and f_lo - zs[face[0]] <= 0.65:
        res["root_r_shoulder"] = arc_r([j for j in range(face[0] + 1, min(floor)) if rF + 0.005 < rmin[j] < rF + 0.45])
    mid = (zs > z_sh + 1) & (zs < zhi - 1); res["A"] = 2 * float(np.nanmedian(bore[mid]))
    res["L"] = float(zhi - zlo)
    return res

CHECK_KEYS = ["J", "D", "C", "cone_deg", "B", "F", "Q", "A", "chamfer_deg", "root_r", "major_d", "pitch_d", "minor_d", "tpi"]

def selfcheck(sizes=(10, 6), slack=0.02, verbose=True):
    """Build each size as a standard-style fitting (shoulder face at AS4395 L), measure it, compare to STD. Returns (ok, rows)."""
    rows, ok = [], True
    for size in sizes:
        part, L = male_an_fitting(size, lead=3.0, body_d=STD[size]["shoulder_d"][0], bore=True)
        meas = measure_fitting(part)
        for k in CHECK_KEYS:
            nom, (lo, hi), src = STD[size][k]; v = meas.get(k, float("nan"))
            sl = 0.25 if k.endswith("_deg") else (0.08 if k == "root_r" else 0.02 if k == "tpi" else slack)
            good = v == v and lo - sl <= v <= hi + sl
            ok &= good; rows.append(dict(size=size, dim=k, standard=round(nom, 3), lo=round(lo, 3), hi=round(hi, 3),
                                         measured=round(v, 3), ok=bool(good), source=src))
        if verbose:
            print(f"-{size}: " + ", ".join(f"{k} {meas[k]:.3f}" for k in ("L", "root_r_shoulder") if k in meas))
    if verbose:
        print(f"{'size':>4} {'dim':<12} {'measured':>9} {'range':>17}  result  source")
        for r_ in rows:
            print(f"{-r_['size']:>4} {r_['dim']:<12} {r_['measured']:>9.3f} {r_['lo']:>8.3f}-{r_['hi']:<8.3f} "
                  f"{'ok  ' if r_['ok'] else 'FAIL'}    {r_['source']}")
        print("SELFCHECK PASS: all dimensions inside the standard ranges" if ok else "SELFCHECK FAIL: see FAIL rows above")
    return ok, rows

def main(argv=None):
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="Build a male SAE AN / JIC 37 deg flare fitting end with a real UNF thread "
                                 "and check it is one valid solid. Writes STEP (and STL with --stl).")
    ap.add_argument("--size", type=int, choices=sorted(AN), default=10, help="AN dash size (default 10)")
    ap.add_argument("--lead", type=float, default=3.0, help="plain body length before the shoulder, mm (default 3)")
    ap.add_argument("--body-d", type=float, default=None, help="plain body diameter, mm (default from the size table)")
    ap.add_argument("--no-bore", action="store_true", help="outer solid only (to fuse onto your own body)")
    ap.add_argument("-o", "--out", default=None, help="output STEP path (default an<size>_male.step)")
    ap.add_argument("--stl", action="store_true", help="also write an STL next to the STEP")
    ap.add_argument("--selfcheck", action="store_true", help="build -6 and -10, measure the geometry, compare with STD "
                    "(MS33656 / AS4395 / ISO 8434-2 / ASME B1.1); exit 1 if anything is out of range")
    ap.add_argument("--json", default=None, help="with --selfcheck: also write the rows to this JSON file")
    a = ap.parse_args(argv)
    if a.selfcheck:
        ok, rows = selfcheck()
        if a.json: json.dump(rows, open(a.json, "w"), indent=1)
        return 0 if ok else 1
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
