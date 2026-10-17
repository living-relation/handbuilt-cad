# Extract + smooth the plate outline and corner windows from the scan (run once; writes bezel_outline.py)
import sys; sys.path.insert(0,'/workspace/hbwork')
import numpy as np, trimesh
from shapely.geometry import Polygon, box
from secpoly import secpolys
s=trimesh.load('/workspace/handbuilt/bezel/bezel_hb.ply')
g=secpolys(s,-1.2); G=sorted(getattr(g,'geoms',[g]),key=lambda q:-q.area); P=G[0]
outer=Polygon(P.exterior).intersection(box(24.5,-50,500,500)).buffer(3).buffer(-3)
def resample(poly,n):
    L=poly.exterior.length; return np.array([poly.exterior.interpolate(t).coords[0] for t in np.linspace(0,L,n,endpoint=False)])
def smooth(pts,keep):
    F=np.fft.rfft(pts[:,0]+1j*pts[:,1]) if False else None
    z=pts[:,0]+1j*pts[:,1]; Z=np.fft.fft(z); Z[keep:-keep]=0; z=np.fft.ifft(Z); return np.c_[z.real,z.imag]
out=resample(outer,400)
# keep the straight edge exactly straight: anything with x<26 -> x=24.5
out=smooth(out,40); out[out[:,0]<26.0,0]=25.5   # inside the back wall (x 24.5-27) so plate and wall overlap, no shared face
wins=[]
for h in P.interiors:
    q=Polygon(h)
    if 500<q.area<2000:
        q=q.buffer(-2).buffer(2).simplify(2.5)   # straight sides; corners filleted in CAD
        wins.append(np.round(np.asarray(q.exterior.coords)[:-1],2).tolist())
with open('bezel_outline.py','w') as f:
    f.write('OUTLINE = %r\nWINDOWS = %r\n'%(np.round(out[::4],2).tolist(),wins))
print(len(out[::4]),[len(w) for w in wins])
