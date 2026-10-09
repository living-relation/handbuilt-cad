from build123d import *
import pedal_adapter as pa, os
from pedal_sections import BODY_STATIONS as S
w = [pa.station_wire(y, p) for y, p in S]
L = Solid.make_loft(w); export_step(L, "_t_loft.step"); print("loft", os.path.getsize("_t_loft.step"), len(L.faces()))
e = w[0].edges()[0]; print("spline poles", e.wrapped and len(S[0][1]))
