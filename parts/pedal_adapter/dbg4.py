from build123d import *
import pedal_adapter as pa, collections
p = pa.build()
c = collections.Counter(f.geom_type for f in p.faces()); print(c, len(p.faces()))
