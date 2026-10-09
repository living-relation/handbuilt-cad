from common import *
import trimesh.intersections as TI
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
s = load_scan()
a = np.radians(25); u = np.array([-np.sin(a), np.cos(a), 0]); v = np.array([np.cos(a), np.sin(a), 0]); zz = np.array([0,0,1.])
fig, axs = plt.subplots(2, 3, figsize=(18, 10))
for ax, vv in zip(axs[0], [-10, -2.5, 6]):
    segs = TI.mesh_plane(s, plane_normal=v, plane_origin=v * vv)
    S = np.stack([segs @ u, segs @ zz], -1); ax.add_collection(LineCollection(S, colors="k", lw=0.7))
    ax.set_xlim(20, 60); ax.set_ylim(8, 40); ax.set_aspect("equal"); ax.grid(True, lw=0.3); ax.set_title(f"v={vv}: u across, z up"); ax.set_xticks(range(20, 61, 2)); ax.tick_params(labelsize=6)
for ax, uu in zip(axs[1], [40, 48, 54]):
    segs = TI.mesh_plane(s, plane_normal=u, plane_origin=u * uu)
    S = np.stack([segs @ v, segs @ zz], -1); ax.add_collection(LineCollection(S, colors="k", lw=0.7))
    ax.set_xlim(-25, 20); ax.set_ylim(8, 35); ax.set_aspect("equal"); ax.grid(True, lw=0.3); ax.set_title(f"u={uu}: v across, z up"); ax.set_xticks(range(-25, 21, 2)); ax.tick_params(labelsize=6)
plt.tight_layout(); plt.savefig(r"C:\Users\danie\agent-tools\pedal-parametric\work_conn.png", dpi=70)
