from common import *
s = load_scan(); s.fix_normals() if False else None
P = s.vertices; N = s.vertex_normals
def circ(xy):
    A = np.c_[2*xy, np.ones(len(xy))]; b = (xy**2).sum(1); c = np.linalg.lstsq(A, b, rcond=None)[0]
    return c[:2], np.sqrt(c[2] + c[:2] @ c[:2])
print("bounds", s.bounds.round(2))
# studs: points below housing bottom near given centres
for c0 in [(21,-63), (7,34), (-32,16)]:
    m = (np.hypot(P[:,0]-c0[0], P[:,1]-c0[1]) < 7) & (P[:,2] < 17.0) & (P[:,2] > 12)
    q = P[m]; zmin = q[:,2].min()
    side = q[(q[:,2] > zmin+0.5) & (q[:,2] < 16.6) & (np.abs(N[m][:,2]) < 0.5)]
    cc, r = circ(side[:,:2]) if len(side) > 20 else ((np.nan,np.nan), np.nan)
    print("stud", c0, "n", len(q), "zmin %.2f" % zmin, "ctr", np.round(cc,2), "d %.2f" % (2*r), "nside", len(side))
# gear region
m = (np.hypot(P[:,0]-13, P[:,1]+33) < 23) & (P[:,2] < 17.0)
q = P[m]; print("gear zmin %.2f" % q[:,2].min(), "pct z", np.percentile(q[:,2],[1,5,25,50]).round(2))
for zz in [16.8, 16.4, 15.5, 14, 12.5, 11.5]:
    qq = q[np.abs(q[:,2]-zz) < 0.25]
    if len(qq) > 20:
        r = np.hypot(qq[:,0]-13, qq[:,1]+33); print("  z", zz, "n", len(qq), "r pct", np.percentile(r,[5,50,95,100]).round(2))
# gear disc circle from side points between 16.5 and 17
qq = q[(q[:,2] > 16.0) & (q[:,2] < 16.9) & (np.hypot(q[:,0]-13, q[:,1]+33) > 15)]
if len(qq) > 30: cc, r = circ(qq[:,:2]); print("disc ctr", cc.round(2), "d %.2f" % (2*r), len(qq))
# ear
m = (P[:,0] > 29) & (P[:,2] < 16.5) & (P[:,1] > -15) & (P[:,1] < 30)
q = P[m]; print("ear x", np.percentile(q[:,0],[1,99]).round(2), "y", np.percentile(q[:,1],[0.5,99.5]).round(2), "z", q[:,2].min().round(2))
# connector
m = (P[:,1] > 37) & (P[:,0] < -8)
q = P[m]; print("conn n", len(q), "z", np.percentile(q[:,2],[0.5,99.5]).round(2), "x", q[:,0].min().round(2), q[:,0].max().round(2), "y max", q[:,1].max().round(2))
xy = q[:,:2] - q[:,:2].mean(0); w, V = np.linalg.eigh(np.cov(xy.T)); print(" pca axes", V.round(3), w.round(1), "mean", q[:,:2].mean(0).round(2))
for zz in [20, 23, 26, 29, 32]:
    qq = q[np.abs(q[:,2]-zz) < 0.3]
    if len(qq): u = qq[:,:2] @ np.array([0.426,0.905]); v = qq[:,:2] @ np.array([0.905,-0.426]); print("  z", zz, "along", np.round([u.min(),u.max()],2), "across", np.round([v.min(), v.max()],2))
# lid dome
m = (np.hypot(P[:,0]-13, P[:,1]+33) < 4) & (P[:,2] > 51)
q = P[m]; print("lid dome zmax %.2f" % q[:,2].max(), "n", len(q))
for rr in [0.5,1,1.5,2,2.5,3,3.5]:
    qq = q[np.abs(np.hypot(q[:,0]-13, q[:,1]+33)-rr) < 0.25]; print("  r", rr, "z %.2f" % np.median(qq[:,2]) if len(qq) else "")
# top levels histogram for upward normals
up = N[:,2] > 0.97; z = P[up,2]; h, e = np.histogram(z, bins=np.arange(10, 70, 0.25)); idx = np.argsort(h)[::-1][:12]; print("up z peaks", sorted([(round(e[i],2), int(h[i])) for i in idx]))
dn = N[:,2] < -0.97; z = P[dn,2]; h, e = np.histogram(z, bins=np.arange(-5, 70, 0.25)); idx = np.argsort(h)[::-1][:12]; print("down z peaks", sorted([(round(e[i],2), int(h[i])) for i in idx]))
xp = N[:,0] > 0.97; x = P[xp,0]; h, e = np.histogram(x, bins=np.arange(-45, 45, 0.25)); idx = np.argsort(h)[::-1][:10]; print("+x peaks", sorted([(round(e[i],2), int(h[i])) for i in idx]))
xn = N[:,0] < -0.97; x = P[xn,0]; h, e = np.histogram(x, bins=np.arange(-45, 45, 0.25)); idx = np.argsort(h)[::-1][:10]; print("-x peaks", sorted([(round(e[i],2), int(h[i])) for i in idx]))
