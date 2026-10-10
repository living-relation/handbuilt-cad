import os
from common import *
import sys, trimesh.intersections as TI
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
s = load_scan()
AX = {"x": (1, 2, 0), "y": (0, 2, 1), "z": (0, 1, 2)}
def one(axis, L, path, lims=None, step=5):
    a, b, k = AX[axis]; nrm = np.zeros(3); nrm[k] = 1; o = np.zeros(3); o[k] = L
    segs = TI.mesh_plane(s, plane_normal=nrm, plane_origin=o)
    lo, hi = s.bounds
    if lims is None: lims = (lo[a]-2, hi[a]+2, lo[b]-2, hi[b]+2)
    W = (lims[1]-lims[0]); H = (lims[3]-lims[2]); sc = 12/max(W, H)
    fig, ax = plt.subplots(figsize=(W*sc+0.8, H*sc+0.6))
    if len(segs): ax.add_collection(LineCollection(segs[:, :, [a, b]], colors="k", linewidths=0.8))
    ax.set_xlim(lims[0], lims[1]); ax.set_ylim(lims[2], lims[3]); ax.set_aspect("equal")
    ax.set_xticks(np.arange(np.ceil(lims[0]/step)*step, lims[1], step)); ax.set_yticks(np.arange(np.ceil(lims[2]/step)*step, lims[3], step))
    ax.grid(True, lw=0.3); ax.tick_params(labelsize=7); ax.set_title(f"{axis}={L}  ({'xyz'[a]} across, {'xyz'[b]} up)")
    plt.tight_layout(); plt.savefig(path, dpi=80); plt.close()
out = os.environ.get("PEDAL_WORK_DIR", os.path.join(os.path.expanduser("~"), "agent-tools", "pedal-parametric")) + r"\work_s_"
for spec in sys.argv[1:]:
    ax, L = spec[0], float(spec[1:]); one(ax, L, out + spec + ".png")
