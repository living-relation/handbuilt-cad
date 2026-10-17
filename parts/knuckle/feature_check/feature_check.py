"""Feature-accuracy check of knuckle v4: local cylinder/plane fits on the scan around each modelled feature."""
import sys, math, json
sys.path.insert(0, "/workspace/hbwork"); sys.path.insert(0, "/workspace/handbuilt/knuckle/v4")
import numpy as np
from scipy.optimize import least_squares
from hb_common import load_scan_hb
import knuckle as K

s = load_scan_hb("knuckle", "/workspace/hbwork/knuckle")
P = np.asarray(s.vertices); N = np.asarray(s.vertex_normals)

def unit(a): a = np.asarray(a, float); return a / np.linalg.norm(a)

def fit_cyl(c, a, d, t0, t1, band=1.2, inner=None):
    """Fit a cylinder to scan points near the model cylinder (radial band, axial range t0..t1 about c)."""
    c = np.asarray(c, float); a = unit(a); r = d / 2
    v = P - c; t = v @ a; rad = np.linalg.norm(v - np.outer(t, a), axis=1)
    m = (np.abs(rad - r) < band) & (t > t0) & (t < t1)
    # keep points whose normal is radial (rejects end faces / fillets)
    nr = (v - np.outer(t, a))[m] / np.maximum(rad[m, None], 1e-9)
    ok = np.abs((N[m] * nr).sum(1)) > 0.8
    Q = P[m][ok]
    if len(Q) < 30: return None
    def f(x):
        cc = x[:3]; aa = x[3:6] / np.linalg.norm(x[3:6]); w = Q - cc; tt = w @ aa
        return np.linalg.norm(w - np.outer(tt, aa), axis=1) - x[6]
    x = least_squares(f, np.r_[c, a, r], loss="soft_l1", f_scale=0.2).x
    cc = x[:3]; aa = unit(x[3:6]); aa = aa if aa @ a > 0 else -aa
    res = f(x)
    # position error: distance between the two axes at the model centre
    p_on = cc + aa * ((c - cc) @ aa)
    return dict(d=2 * abs(x[6]), pos=float(np.linalg.norm(p_on - c)), ang=math.degrees(math.acos(min(1, abs(aa @ a)))),
                rms=float(np.sqrt((res ** 2).mean())), n=len(Q))

def fit_plane(p0, nrm, half=30, band=1.5, radius=None, c=None):
    nrm = unit(nrm); v = P - np.asarray(p0); h = v @ nrm
    m = (np.abs(h) < band) & ((N @ nrm) > 0.9)
    if radius is not None:
        w = v - np.outer(h, nrm); m &= np.linalg.norm(w, axis=1) < radius
    Q = P[m]
    if len(Q) < 30: return None
    cq = Q.mean(0); u, sv, vt = np.linalg.svd(Q - cq); n2 = vt[2] * np.sign(vt[2] @ nrm)
    return dict(offset=float((cq - p0) @ nrm), ang=math.degrees(math.acos(min(1, abs(n2 @ nrm)))), n=len(Q))

rows = []
def add(name, model_d, r, kind="cyl"):
    if r is None: rows.append([name, model_d, None, None, None, None, None]); return
    rows.append([name, model_d, round(r["d"], 2), round(r["d"] - model_d, 2), round(r["pos"], 2), round(r["ang"], 2), round(r["rms"], 2)])

Z = (0, 0, 1)
# hub outside
add("Hub OD (bearing housing)", K.HUB_OD, fit_cyl((0, 0, 16), Z, K.HUB_OD, -8, 8))
add("Hub OD top (above flare)", K.HUB_OD_TOP, fit_cyl((0, 0, 36.5), Z, K.HUB_OD_TOP, -2.5, 2.5))
# bore steps
names = {0: "Bore bottom counterbore", 1: "Bore circlip groove", 2: "Bore bearing seat", 3: "Bore stop lip", 4: "Bore above lip", 5: "Bore top counterbore"}
for i, (z0, z1, d) in enumerate(K.BORE[:6]):
    zc = (max(z0, 0) + z1) / 2; h = (z1 - max(z0, 0)) / 2 - (0.4 if z1 - z0 < 5 else 1.0)
    add(f"{names[i]} (z {max(z0,0):.1f}-{z1:.1f})", d, fit_cyl((0, 0, zc), Z, d, -h, h, band=1.0))
# holes
for i, (x, y) in enumerate(K.FLANGE_HOLES):
    add(f"Flange bolt hole {i+1} ({x:.0f},{y:.0f})", K.FLANGE_HOLE_D, fit_cyl((x, y, 72), Z, K.FLANGE_HOLE_D, -6, 6, band=1.0))
for (x, y), d, (z0, z1) in K.EAR_HOLES:
    add(f"Ear hole ({x:.0f},{y:.0f})", d, fit_cyl((x, y, (z0 + z1) / 2), Z, d, -(z1 - z0) / 2, (z1 - z0) / 2, band=1.0))
xn = ["Side boss hole (X)", "Lower arm hole, outer (X) - shock/link mount", "Lower arm hole, inner (X) - shock/link mount"]
for nm, ((y, z), d, x0, x1) in zip(xn, K.X_HOLES):
    add(nm, d, fit_cyl(((x0 + x1) / 2, y, z), (1, 0, 0), d, -(x1 - x0) / 2, (x1 - x0) / 2, band=1.0))
for nm, e in K.EYES.items():
    L = e["length"]
    add(f"{nm} bore", e["bore"], fit_cyl(e["c"], e["axis"], e["bore"], -L / 2 + 1.5, L / 2 - 1.5, band=1.5))
    add(f"{nm} outside dia", e["od"], fit_cyl(e["c"], e["axis"], e["od"], -L / 2 + 1.5, L / 2 - 1.5, band=1.5))
# faces: eye ends, hub bottom
faces = []
for nm, e in K.EYES.items():
    a = unit(e["axis"]); c = np.asarray(e["c"]); L = e["length"]
    for sgn in (1, -1):
        r = fit_plane(c + sgn * a * L / 2, sgn * a, radius=e["od"] / 2 + 2)
        faces.append([f"{nm} end face ({'+' if sgn > 0 else '-'})", None if r is None else round(r["offset"], 2), None if r is None else round(r["ang"], 2)])
r = fit_plane(np.array([0, 0, 0.0]), (0, 0, -1), radius=47); faces.append(["Hub bottom face", round(r["offset"], 2), round(r["ang"], 2)])
json.dump({"cyl": rows, "faces": faces}, open("feature_check.json", "w"), indent=1)
hdr = "| feature | model mm | scan mm | size err | axis pos err mm | axis angle err deg | fit rms |"
print(hdr); print("|---|---|---|---|---|---|---|")
for r in rows: print("| " + " | ".join("-" if v is None else str(v) for v in r) + " |")
print("\n| face | offset scan vs model mm | angle err deg |\n|---|---|---|")
for f in faces: print("| " + " | ".join("-" if v is None else str(v) for v in f) + " |")
