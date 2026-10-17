from build123d import *
import pedal_adapter as pa
from pedal_sections import BODY_STATIONS as S
from shapely.geometry import Polygon
for y, p in S:
    P = Polygon(p); print(y, "valid" if P.is_valid else "SELF-INTERSECTING", "ccw", P.exterior.is_ccw, "start", p[0])
w = [pa.station_wire(y, p) for y, p in S]
L = Solid.make_loft(w); print("loft valid", L.is_valid, "vol", L.volume)
