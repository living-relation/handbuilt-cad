import os
from common import *
import trimesh.intersections as TI
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
s = load_scan()
def secplot(normal, levels, path, ax_idx, labels):
    n = len(levels); cols = 4; rows = (n + cols - 1)//cols
    fig, axs = plt.subplots(rows, cols, figsize=(cols*5, rows*5.5))
    for ax, L in zip(axs.ravel(), levels):
        o = np.zeros(3); o[np.argmax(np.abs(normal))] = L
        segs = TI.mesh_plane(s, plane_normal=normal, plane_origin=o)
        if len(segs): ax.add_collection(LineCollection(segs[:, :, list(ax_idx)], colors="k", linewidths=0.6))
        ax.set_title(f"{labels[2]}={L}"); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
        ax.set_xlim(s.bounds[0][ax_idx[0]]-2, s.bounds[1][ax_idx[0]]+2); ax.set_ylim(s.bounds[0][ax_idx[1]]-2, s.bounds[1][ax_idx[1]]+2)
        ax.set_xticks(np.arange(np.floor(s.bounds[0][ax_idx[0]]/10)*10, s.bounds[1][ax_idx[0]]+3, 10))
        ax.set_yticks(np.arange(np.floor(s.bounds[0][ax_idx[1]]/10)*10, s.bounds[1][ax_idx[1]]+3, 10))
        ax.tick_params(labelsize=7)
    plt.tight_layout(); plt.savefig(path, dpi=70); plt.close()
out = os.environ.get("PEDAL_WORK_DIR", os.path.join(os.path.expanduser("~"), "agent-tools", "pedal-parametric")) + r"\work_"
secplot([0,0,1], [-2, 3, 8, 14, 16.5, 18, 22, 30, 40, 48, 51.2, 53, 56, 60, 64, 67], out+"secz.png", (0,1), "xyz")
secplot([1,0,0], [-38, -32, -25, -15, -5, 5, 15, 25, 32, 34, 36.5, 38.5], out+"secx.png", (1,2), "yzx")
secplot([0,1,0], [-88, -80, -70, -60, -50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 45, 50], out+"secy.png", (0,2), "xzy")
