import numpy as np, trimesh
from scipy.spatial import cKDTree
def fit_lite(scan, model_stl, n_model=1500000, n_scan=60000, seed=0):
    """Memory-light scan->model distance: KD-tree on a dense model surface sample, area-weighted scan sample."""
    m = trimesh.load(model_stl)
    Q, _ = trimesh.sample.sample_surface(m, n_model, seed=seed)
    P, _ = trimesh.sample.sample_surface(scan, n_scan, seed=seed)
    d, _ = cKDTree(Q).query(P, workers=2)
    pct = lambda q: round(float(np.percentile(d, q)), 3)
    return {"median_mm": pct(50), "p95_mm": pct(95), "max_mm": round(float(d.max()), 2),
            "within_0.5_pct": round(float((d <= 0.5).mean() * 100), 1), "within_1.0_pct": round(float((d <= 1.0).mean() * 100), 1)}, P, d
