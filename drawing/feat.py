import math, numpy as np
from build123d import *
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Cone
from OCP.BRepTools import BRepTools

AX={'X':np.array([1.,0,0]),'Y':np.array([0,1.,0]),'Z':np.array([0,0,1.])}
def axname(d):
    for k,v in AX.items():
        if abs(abs(d@v)-1)<1e-4: return k
    return None

def cyl_faces(solid):
    out=[]
    for f in solid.faces():
        a=BRepAdaptor_Surface(f.wrapped)
        t=a.GetType()
        if t not in (GeomAbs_Cylinder,GeomAbs_Cone): continue
        if t==GeomAbs_Cylinder:
            c=a.Cylinder(); ax=c.Axis(); r=c.Radius(); half=None
        else:
            c=a.Cone(); ax=c.Axis(); r=c.RefRadius(); half=c.SemiAngle()
        loc=np.array([ax.Location().X(),ax.Location().Y(),ax.Location().Z()])
        d=np.array([ax.Direction().X(),ax.Direction().Y(),ax.Direction().Z()])
        n=axname(d)
        if n is None: continue
        d=AX[n]
        u0,u1,v0,v1=BRepTools.UVBounds_s(f.wrapped)
        bb=f.bounding_box()
        pts=np.array([[bb.min.X,bb.min.Y,bb.min.Z],[bb.max.X,bb.max.Y,bb.max.Z]])
        t0,t1=sorted(pts@d)
        # point on axis at t
        base=loc-(loc@d)*d
        try:
            pc=f.position_at(0.5,0.5); nn=np.array(tuple(f.normal_at(pc))); pc=np.array(tuple(pc))
            rad=pc-base-((pc-base)@d)*d if False else None
        except Exception: pc=None
        base0=loc-(loc@d)*d
        radial=(pc-base0)-((pc-base0)@d)*d
        concave=bool(nn@radial<0)
        out.append(dict(concave=concave,face=f,kind='cyl' if half is None else 'cone',r=r,axis=n,d=d,base=base,t0=t0,t1=t1,span=u1-u0,half=half,bb=bb))
    return out

def inside(solid,p):
    return solid.is_inside(Vector(*p),0.01)

def analyze(solid):
    cf=cyl_faces(solid)
    holes=[];radii=[];bosses=[]
    # cluster coaxial
    groups=[]
    for c in cf:
        for g in groups:
            if g[0]['axis']==c['axis'] and np.linalg.norm(g[0]['base']-c['base'])<0.01:
                g.append(c);break
        else: groups.append([c])
    # split convex cylinders out
    newg=[]
    for g in groups:
        cc=[c for c in g if c['kind']=='cone' or c['concave']]
        cv=[c for c in g if c['kind']=='cyl' and not c['concave']]
        if cc: newg.append(cc)
        for c in cv: newg.append([c])
    groups=newg
    for g in groups:
        full=[c for c in g]
        ang=sum(c['span'] for c in g if c['kind']=='cyl')
        cyls=[c for c in g if c['kind']=='cyl']
        if not cyls: continue
        mid=cyls[0]; tm=(mid['t0']+mid['t1'])/2
        concave = all(c['concave'] for c in cyls)
        # merge cylinders with same radius & overlapping t
        segs={}
        for c in cyls:
            k=round(c['r'],3); s=segs.setdefault(k,[c['t0'],c['t1'],0.0]); s[0]=min(s[0],c['t0']); s[1]=max(s[1],c['t1']); s[2]+=c['span']
        full_circle = all(v[2]>2*math.pi-0.05 for v in segs.values())
        cones=[c for c in g if c['kind']=='cone']
        rec=dict(axis=g[0]['axis'],d=g[0]['d'],base=g[0]['base'],segs={k:v[:2] for k,v in segs.items()},cones=[(c['t0'],c['t1'],c['half']) for c in cones],concave=concave,full=full_circle,span=max(v[2] for v in segs.values()))
        if full_circle and concave: holes.append(rec)
        elif full_circle: bosses.append(rec)
        else: radii.append(rec)
    # characterize holes
    for h in holes:
        d=h['d']; ks=sorted(h['segs'])  # radii ascending
        rmin=ks[0]; t0,t1=h['segs'][rmin]
        lo=min([v[0] for v in h['segs'].values()]+[c[0] for c in h['cones']]); hi=max([v[1] for v in h['segs'].values()]+[c[1] for c in h['cones']])
        perp=np.cross(d,[1,0,0] if abs(d[0])<0.9 else [0,1,0]); perp/=np.linalg.norm(perp)
        probe=0.35*rmin+0.1; off=perp*0.5*rmin
        open_lo = not inside(solid,h['base']+off+(lo-probe)*d)
        open_hi = not inside(solid,h['base']+off+(hi+probe)*d)
        h['open_lo']=open_lo; h['open_hi']=open_hi; h['lo']=lo; h['hi']=hi
        h['through']=open_lo and open_hi
        h['dia']=2*rmin; h['len']=t1-t0
    return holes,radii,bosses

if __name__=='__main__':
    import sys
    for f in sys.argv[1:]:
        s=import_step(f); sol=s.solids()[0]
        holes,radii,b=analyze(sol)
        print('==',f, 'bb',sol.bounding_box().min, sol.bounding_box().max)
        for h in sorted(holes,key=lambda h:(h['axis'],h['dia'])):
            print(f" HOLE {h['axis']} dia={h['dia']:.3f} segs={ {round(2*k,3):(round(v[0],2),round(v[1],2)) for k,v in h['segs'].items()} } cones={[(round(a,2),round(b,2),round(math.degrees(c),1)) for a,b,c in h['cones']]} thru={h['through']} lo/hi open={h['open_lo']},{h['open_hi']} base={np.round(h['base'],2)}")
        from collections import Counter
        print(' RADII',Counter((r['axis'],round(min(r['segs'])  ,2),r['concave']) for r in radii))
        print(' BOSS',[(bb['axis'],round(2*min(bb['segs']),2)) for bb in b])
