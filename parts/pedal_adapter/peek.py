import json, numpy as np
f = json.load(open(r"C:\projects\active\fairsolid\runs\pedal_adapter\30_fit.json"))
print(f["noise_floor_mm"], f["tolerance"]["value_mm"])
for a in sorted(f["areas"], key=lambda a: -a["area_mm2"]):
    fit = a.get("final") or a.get("fit") or {}
    if a["kind"] == "plane":
        n = np.round(fit["normal"], 3); print("P", a["id"], round(a["area_mm2"]), n.tolist(), "off", fit["offset_mm"])
    elif a["type"] in ("round",) or a["kind"] in ("hole","boss","fillet","cylinder"):
        print("R", a["id"], a["kind"], round(a["area_mm2"]), "axis", np.round(fit.get("axis",[0,0,0]),3).tolist(), "pt", np.round(fit.get("point_mm",[0,0,0]),2).tolist(), "d", fit.get("diameter_mm"), "L", fit.get("length_mm"), a.get("partial"))
