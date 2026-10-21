"""Final images for the owner: shaded model next to the plain grey scan, same camera."""
import numpy as np, trimesh
from common import load_scan, render
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.image as mpimg
s = load_scan(); m = trimesh.load("pedal_adapter.stl")
c = s.bounds.mean(0); r = np.linalg.norm(s.vertices - c, axis=1).max()
D = os.environ.get("PEDAL_WORK_DIR", os.path.join(os.path.expanduser("~"), "agent-tools", "pedal-parametric"))
render([(m, (0.62, 0.70, 0.82))], D + r"\pedal_model_iso.png", views=("iso",), size=(1100, 950), titles=["New model (clean solid)"], center=c, radius=r * 0.8)
names = {"iso": "front-right, from above", "iso2": "back-left, from above", "isob": "front-right, from below", "isob2": "back-left, from below"}
for i, (v, label) in enumerate(names.items(), 1):
    a = D + r"\_tmp_model.png"; b = D + r"\_tmp_scan.png"
    render([(m, (0.62, 0.70, 0.82))], a, views=(v,), size=(800, 700), titles=["New model"], center=c, radius=r * 0.8)
    render([(s, (0.72, 0.72, 0.72))], b, views=(v,), size=(800, 700), titles=["Scan"], center=c, radius=r * 0.8)
    fig, ax = plt.subplots(1, 2, figsize=(16, 7.2))
    for k, f in enumerate((a, b)): ax[k].imshow(mpimg.imread(f)); ax[k].axis("off")
    fig.suptitle(f"Pedal adapter - {label}", fontsize=16); plt.tight_layout()
    plt.savefig(D + rf"\pedal_compare_{i}_{v}.png", dpi=90); plt.close()
import os; os.remove(D + r"\_tmp_model.png"); os.remove(D + r"\_tmp_scan.png")
print("done")
