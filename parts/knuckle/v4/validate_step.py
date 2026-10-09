import time; t=time.time()
from build123d import import_step
s=import_step(r"C:\projects\_scratch\handbuilt\knuckle\v4\knuckle.step")
print("opened", "%.0fs"%(time.time()-t)); print("valid", s.is_valid, "solids", len(s.solids()), "faces", len(s.faces()), "volume %.0f"%s.volume)
bb=s.bounding_box(); print("bbox", bb.min, bb.max, "%.0fs"%(time.time()-t))
