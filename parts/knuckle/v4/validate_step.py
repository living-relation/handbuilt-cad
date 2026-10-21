import time; t=time.time()
from build123d import import_step
import os
s=import_step(os.path.join(os.path.dirname(os.path.abspath(__file__)), "knuckle.step"))
print("opened", "%.0fs"%(time.time()-t)); print("valid", s.is_valid, "solids", len(s.solids()), "faces", len(s.faces()), "volume %.0f"%s.volume)
bb=s.bounding_box(); print("bbox", bb.min, bb.max, "%.0fs"%(time.time()-t))
