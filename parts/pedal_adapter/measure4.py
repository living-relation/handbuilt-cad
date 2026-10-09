from common import *
s = load_scan(); P = s.vertices
def circ(xy):
    A = np.c_[2*xy, np.ones(len(xy))]; b = (xy**2).sum(1); c = np.linalg.lstsq(A, b, rcond=None)[0]
    return c[:2], np.sqrt(c[2] + c[:2] @ c[:2])
for c0 in [(21.2,-62.8), (7.7,34.5), (-31.8,16.3)]:
    m = (np.hypot(P[:,0]-c0[0], P[:,1]-c0[1]) < 8) & (P[:,2] < 17.0) & (P[:,2] > 12)
    q = P[m]
    # refine centre: points z<16.6
    cc, r = circ(q[q[:,2] < 16.7][:, :2]); 
    rr = np.hypot(q[:,0]-cc[0], q[:,1]-cc[1])
    prof = [(r0, round(float(np.median(q[np.abs(rr-r0)<0.3,2])),2)) for r0 in np.arange(0, 6.5, 0.5) if (np.abs(rr-r0)<0.3).sum() > 3]
    print("stud ctr", cc.round(2), "rfit(z<16.7) %.2f" % r, prof)
# spokes
m = (np.hypot(P[:,0]-13.2, P[:,1]+32.8) < 21) & (P[:,2] < 13.5)
q = P[m]; ang = np.degrees(np.arctan2(q[:,1]+32.8, q[:,0]-13.2)) % 360; r = np.hypot(q[:,0]-13.2, q[:,1]+32.8)
h, e = np.histogram(ang[r > 8], bins=72, range=(0,360)); print("spoke angle hist (5deg bins):", [(int(e[i]), int(h[i])) for i in range(72) if h[i] > 0.4*h.max()])
for a0 in range(0, 360, 45):
    pass
print("r pct of low pts", np.percentile(r,[1,10,50,90,99]).round(2), "z min", q[:,2].min().round(2))
# hub
m = (np.hypot(P[:,0]-13.2, P[:,1]+32.8) < 7) & (P[:,2] < 16.8)
q = P[m]; rr = np.hypot(q[:,0]-13.2, q[:,1]+32.8)
print("hub prof", [(r0, round(float(np.median(q[np.abs(rr-r0)<0.3,2])),2)) for r0 in np.arange(0, 7, 0.5) if (np.abs(rr-r0)<0.3).sum() > 3])
# C ring
m = (np.hypot(P[:,0]+20, P[:,1]+37) < 9) & (P[:,2] < 16.9)
q = P[m]; print("cring n", len(q), "zmin", q[:,2].min().round(2) if len(q) else None)
if len(q) > 30:
    cc, r = circ(q[:, :2]); rr = np.hypot(q[:,0]-cc[0], q[:,1]-cc[1]); a = np.degrees(np.arctan2(q[:,1]-cc[1], q[:,0]-cc[0])) % 360
    print(" ctr", cc.round(2), "r", round(r,2), "r pct", np.percentile(rr,[2,50,98]).round(2), "z pct", np.percentile(q[:,2],[2,50]).round(2))
    h, e = np.histogram(a, bins=24, range=(0,360)); print(" ang occupancy", h.tolist())
