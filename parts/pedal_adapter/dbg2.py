from build123d import *
import pedal_adapter as pa
from pedal_sections import BODY_STATIONS as S
w = [pa.station_wire(y, p) for y, p in S]
L = Solid.make_loft(w)
B = pa.box_between(-400, pa.X_SIDE, -400, 400, pa.Z_BOTTOM, 400)
print("loft", round(L.volume), "loft&clip", round((L & B).volume), "loft-clip", round((L - B).volume))
for i in range(0, len(S) - 1, 1):
    l = Solid.make_loft(w[i:i+2]); c = l & B
    print(S[i][0], round(l.volume), round(c.volume), round((l - B).volume), "BAD" if c.volume > l.volume + 1 else "")
