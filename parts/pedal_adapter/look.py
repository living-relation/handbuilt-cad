import os
from common import *
s = load_scan()
out = os.environ.get("PEDAL_WORK_DIR", os.path.join(os.path.expanduser("~"), "agent-tools", "pedal-parametric")) + r"\work_"
for v in ["iso","iso2","isob","isob2","top","bottom","front","back","right","left"]:
    render([(s, None)], out + "v_" + v + ".png", views=(v,), size=(1000, 900))
