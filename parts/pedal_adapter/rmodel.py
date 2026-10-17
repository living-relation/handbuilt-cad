import os
import trimesh, sys
from common import render
m = trimesh.load("pedal_adapter.stl")
out = os.environ.get("PEDAL_WORK_DIR", os.path.join(os.path.expanduser("~"), "agent-tools", "pedal-parametric")) + r"\work_m_"
for v in ["iso", "iso2", "isob", "isob2", "left", "bottom"]:
    render([(m, (0.62, 0.7, 0.82))], out + v + ".png", views=(v,), size=(900, 800))
