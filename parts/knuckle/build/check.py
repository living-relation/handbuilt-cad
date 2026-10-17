import sys, json, time; sys.path.insert(0, "/workspace/hbwork")
from hb_common import *
name = sys.argv[1]; part_dir = sys.argv[2]; args = [a for a in sys.argv[1:] if not a.startswith("--")]; run = args[2] if len(args) > 2 else name
s = load_scan_hb(run, part_dir)
st, d, w = fit_stats(s, f"{name}.stl"); print(json.dumps(st))
json.dump(st, open(f"{name}_fit.json", "w"), indent=1)
for l in far_clusters(s, d, w, thresh=1.0, top=15): print(l)
if "--render" in sys.argv:
    print(compare_renders(s, f"{name}.stl", "renders", name))
