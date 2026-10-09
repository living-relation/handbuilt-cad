from common import *
s = load_scan()
out = r"C:\Users\danie\agent-tools\pedal-parametric\work_"
for v in ["iso","iso2","isob","isob2","top","bottom","front","back","right","left"]:
    render([(s, None)], out + "v_" + v + ".png", views=(v,), size=(1000, 900))
