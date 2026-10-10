"""Quick strength check of a STEP part with Gmsh + CalculiX (linear static, one load case).

Hold one side still, push on another side, get the peak stress and safety factor.

    $SIM_VENV/bin/python tools/quick_fea.py part.step --fix x:min --load x:max --force 0,0,-500 \
        --E 69000 --nu 0.33 --yield 276 --size 2

  --fix / --load   which nodes:  AXIS:min, AXIS:max, or AXIS:VALUE   (nodes within --tol mm of that plane)
  --force          total force in newtons, X,Y,Z, spread evenly over the load nodes
  --E --nu --yield material in MPa (defaults: 6061-T6 aluminium)
  --size           mesh size in mm (smaller = slower, more accurate)
Writes <part>_fea/ with the CalculiX deck, results, summary.json and result.vtu (open in ParaView).
This is a first check, not a certification. Real parts need proper load cases and a safety margin.
"""
import argparse, json, os, re, shutil, subprocess, sys
import numpy as np, gmsh

ap = argparse.ArgumentParser()
ap.add_argument("step"); ap.add_argument("--fix", required=True); ap.add_argument("--load", required=True)
ap.add_argument("--force", required=True); ap.add_argument("--E", type=float, default=69000.0)
ap.add_argument("--nu", type=float, default=0.33); ap.add_argument("--yield", dest="sy", type=float, default=276.0)
ap.add_argument("--size", type=float, default=2.0); ap.add_argument("--tol", type=float, default=0.05)
a = ap.parse_args()
if not shutil.which("ccx"): sys.exit("CalculiX (ccx) not found - run: bash setup.sh")

out = os.path.splitext(os.path.abspath(a.step))[0] + "_fea"; os.makedirs(out, exist_ok=True)
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.occ.importShapes(os.path.abspath(a.step)); gmsh.model.occ.synchronize()
gmsh.option.setNumber("Mesh.MeshSizeMax", a.size); gmsh.option.setNumber("Mesh.MeshSizeMin", a.size / 4)
gmsh.option.setNumber("Mesh.ElementOrder", 2); gmsh.option.setNumber("Mesh.HighOrderOptimize", 1)
gmsh.model.mesh.generate(3)
tags, xyz, _ = gmsh.model.mesh.getNodes(); xyz = xyz.reshape(-1, 3)
et, etags, enodes = gmsh.model.mesh.getElements(3)
k = list(et).index(11)  # 10-node tet
tets = np.asarray(enodes[k], dtype=np.int64).reshape(-1, 10)[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
gmsh.finalize()
idx = {int(t): i for i, t in enumerate(tags)}
used = np.unique(tets); pts = xyz[[idx[int(t)] for t in used]]; ids = used

def pick(spec):
    axis, where = spec.split(":"); c = "xyz".index(axis.lower()); col = pts[:, c]
    v = col.min() if where == "min" else col.max() if where == "max" else float(where)
    sel = ids[np.abs(col - v) <= a.tol]
    if len(sel) == 0: sys.exit(f"no nodes found for {spec} (try a bigger --tol)")
    return sel
fix, load = pick(a.fix), pick(a.load)
F = np.array([float(v) for v in a.force.split(",")])

name = "job"; inp = os.path.join(out, name + ".inp")
with open(inp, "w") as f:
    f.write("*NODE\n"); [f.write(f"{int(i)},{p[0]:.6f},{p[1]:.6f},{p[2]:.6f}\n") for i, p in zip(ids, pts)]
    f.write("*ELEMENT,TYPE=C3D10,ELSET=EALL\n"); [f.write(f"{n+1}," + ",".join(str(int(x)) for x in e) + "\n") for n, e in enumerate(tets)]
    for nm, s in (("FIX", fix), ("LOAD", load), ("ALLN", ids)):
        f.write(f"*NSET,NSET={nm}\n"); [f.write(f"{int(i)},\n") for i in s]
    f.write(f"*MATERIAL,NAME=M\n*ELASTIC\n{a.E},{a.nu}\n*SOLID SECTION,ELSET=EALL,MATERIAL=M\n")
    f.write("*STEP\n*STATIC\n*BOUNDARY\nFIX,1,3,0\n*CLOAD\n")
    for d in range(3):
        if F[d]: f.write(f"LOAD,{d+1},{F[d]/len(load):.8g}\n")
    f.write("*NODE PRINT,NSET=ALLN\nU\n*EL PRINT,ELSET=EALL\nS\n*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n")
r = subprocess.run(["ccx", "-i", name], cwd=out, capture_output=True, text=True)
open(os.path.join(out, "ccx.log"), "w").write(r.stdout + r.stderr)
dat = open(os.path.join(out, name + ".dat")).read()
def table(block, ncol, first):
    rows = []
    for l in block.splitlines()[1:]:          # first line is the header
        t = l.split()
        if len(t) == ncol:
            try: rows.append([float(x) for x in t[first:]])
            except ValueError: pass
    return np.array(rows)
U = table(dat.split("stresses")[0].split("displacements")[1], 4, 1)
S = table(dat.split("stresses")[1], 8, 2)
sx, sy, sz, txy, txz, tyz = S.T
vm = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (txy ** 2 + txz ** 2 + tyz ** 2))
p99 = float(np.percentile(vm, 99.9))
res = dict(part=os.path.basename(a.step), nodes=len(ids), elements=len(tets), fix_nodes=len(fix), load_nodes=len(load),
           force_N=F.tolist(), max_displacement_mm=float(np.linalg.norm(U, axis=1).max()),
           peak_von_mises_MPa=float(vm.max()), von_mises_99_9pct_MPa=p99, yield_MPa=a.sy,
           safety_factor=a.sy / float(vm.max()), safety_factor_99_9pct=a.sy / p99)
json.dump(res, open(os.path.join(out, "summary.json"), "w"), indent=1)
try:
    import meshio
    pos = {int(i): n for n, i in enumerate(ids)}
    meshio.write(os.path.join(out, "result.vtu"), meshio.Mesh(pts, [("tetra10", np.vectorize(pos.get)(tets[:, [0,1,2,3,4,5,6,7,9,8]]))],
                 point_data={"U": U}))
except Exception as e: print("(vtu not written:", e, ")")
print(f"nodes {len(ids)}, elements {len(tets)}; fixed {len(fix)} nodes, loaded {len(load)} nodes")
print(f"max displacement {res['max_displacement_mm']:.4f} mm")
print(f"peak stress {vm.max():.1f} MPa (99.9% {p99:.1f})  ->  safety factor {res['safety_factor']:.2f} vs yield {a.sy} MPa")
print("results in", out)
