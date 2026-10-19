import math, numpy as np, textwrap
from build123d import *
from scipy.spatial import cKDTree
from dwg import *
from dwg import _tw, write_checks
from part import text_rect, Occ

def load_children(path):
    s=import_step(path); out={}
    for c in s.children:
        out.setdefault(c.label,[]).extend(c.solids())
    return out

def shapes_bb(shs):
    c=Compound(list(shs)); return c.bounding_box()

def sample_pts3d(shs,n_per_edge=6,maxe=3000,step=None,maxpts=4000):
    """points on the edges of shs. step=None: n_per_edge per edge (legacy); step=mm: spaced along each edge
    (dense, so a short visible edge of a part is still found), capped near maxpts per call."""
    pts=[]
    if step:
        out=[_edge_samples(s,step,maxpts) for s in shs]
        out=[o for o in out if len(o)]
        return np.vstack(out) if out else np.zeros((0,3))
    for s in shs:
        es=s.edges()
        st=max(1,len(es)//maxe)
        for e in es[::st]:
            try:
                for t in np.linspace(0,1,n_per_edge): pts.append(tuple(e.position_at(t)))
            except Exception: pass
    return np.array(pts) if pts else np.zeros((0,3))

_SAMPLES={}    # id(shape) -> (shape, step, points): edge samples are reused across views and sheets
_MOVED={}      # id(moved copy) -> (moved copy, original shape, offset vector), from exploded_shapes

def _edge_samples(s,step,maxpts):
    """points every ~step mm along every edge of one shape (OCCT, no Python per-parameter calls); cached."""
    mv=_MOVED.get(id(s))
    if mv is not None and mv[0] is s: return _edge_samples(mv[1],step,maxpts)+np.asarray(mv[2],float)
    hit=_SAMPLES.get(id(s))
    if hit is not None and hit[0] is s and hit[1]==step: return hit[2]
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_AbscissaPoint
    es=s.edges(); ad=[]
    for e in es:
        try: c=BRepAdaptor_Curve(e.wrapped); ad.append((c,GCPnts_AbscissaPoint.Length_s(c)))
        except Exception: pass
    L=sum(l for _,l in ad) or 1.0; st=max(step,L/maxpts); pts=[]
    for c,l in ad:
        n=max(3,int(l/st)+1); f,g=c.FirstParameter(),c.LastParameter()
        for t in np.linspace(f,g,n):
            p=c.Value(t); pts.append((p.X(),p.Y(),p.Z()))
    P=np.array(pts) if pts else np.zeros((0,3))
    _SAMPLES[id(s)]=(s,step,P)
    return P

class Occluder:
    """Ray test against the solids drawn in a view: is a 3D point hidden behind something, seen along -cam?"""
    def __init__(s,shapes):
        from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
        s.I=IntCurvesFace_ShapeIntersector(); s.I.Load(Compound(list(shapes)).wrapped,1e-4)
    def hidden(s,p,cam,eps=0.08):
        from OCP.gp import gp_Lin, gp_Pnt, gp_Dir
        c=np.asarray(cam,float); c=c/np.linalg.norm(c); q=np.asarray(p,float)+c*eps
        s.I.Perform(gp_Lin(gp_Pnt(*q),gp_Dir(*c)),0.0,1e9)
        return bool(s.I.IsDone() and s.I.NbPnt()>0)

# balloon rules (DRAWING-RULES 24-28): a balloon only where its part is clearly visible, on a point of that part
BAL_MIN_PTS=4        # visible, own, unoccluded edge points a part needs before it is ballooned in a view
BAL_MIN_SPAN=1.2     # ... spread over at least this much of the page (mm): a part that shows as a speck is not "clearly visible"
TIP_MIN_SEP=4.0      # leader tips at least this far apart on the page (mm), else they are "crowded"
BAL_GAP=2.0          # clear space between two balloon circles (mm)

def visible_candidates(view,item_shs,tree,others=None,occl=None,maxray=80):
    """page points on edges of item_shs that are drawn (on a visible HLR line), belong to this item (no other part's
    edge projects there) and are not hidden behind another solid (ray test). [] when the part is not clearly visible."""
    P=sample_pts3d(item_shs,step=0.4)
    if len(P)==0: return np.zeros((0,2))
    uv=np.c_[P@view.r,P@view.u]
    d,_=tree.query(uv); m=d<0.08
    P,uv=P[m],uv[m]
    if len(uv)<BAL_MIN_PTS: return np.zeros((0,2))
    if others is not None and len(others):
        ot=cKDTree(others); span=max(np.ptp(uv[:,0]),np.ptp(uv[:,1]),1.0)
        do,_=ot.query(uv); own=do>max(0.6,0.03*span)
        P,uv=P[own],uv[own]
    if occl is not None and len(P):
        idx=np.arange(len(P))
        if len(idx)>maxray: idx=np.random.default_rng(0).choice(idx,maxray,replace=False)
        ok=np.array([not occl.hidden(P[i],view.c) for i in idx],bool)
        P,uv=P[idx[ok]],uv[idx[ok]]
    if len(uv)<BAL_MIN_PTS: return np.zeros((0,2))
    pg=np.array([view.uv2pg(q) for q in uv])
    if max(np.ptp(pg[:,0]),np.ptp(pg[:,1]))<BAL_MIN_SPAN: return np.zeros((0,2))
    return pg

def choose_anchors(cands,min_sep=TIP_MIN_SEP):
    """one leader tip per item from its candidate points: near the middle of the part's visible edges, spread apart
    from the tips already chosen so leaders do not bunch on one spot. cands: {key: Nx2 page points}."""
    chosen={}
    for k in sorted(cands,key=lambda k:len(cands[k])):
        c=cands[k]; med=c[np.argmin(np.linalg.norm(c-c.mean(0),axis=1))]
        if chosen:
            O=np.array(list(chosen.values()))
            dmin=np.min(np.linalg.norm(c[:,None,:]-O[None,:,:],axis=2),axis=1)
            score=np.minimum(dmin,2*min_sep)-0.15*np.linalg.norm(c-med,axis=1)
            chosen[k]=c[int(np.argmax(score))]
        else: chosen[k]=med
    return chosen

def anchor_for(view,item_shs,tree,ctr_pg=None,others=None,occl=None):
    c=visible_candidates(view,item_shs,tree,others,occl)
    if not len(c): return None
    return choose_anchors({0:c})[0]

def vis_tree(view):
    pts=[]
    for p in list(view.vis)+list(getattr(view,'tan',[])):
        for a,b in zip(p[:-1],p[1:]):
            L=np.linalg.norm(b-a); n=max(2,int(L/0.05)+1)
            pts.append(np.linspace(a,b,n))
    return cKDTree(np.vstack(pts))

def balloon(sh,c,num,anchor,r=4.0,note=None,side=None,th=2.2):
    """balloon with the item number, leader to anchor, optional note (circuit / device it serves) beside the balloon."""
    c=np.asarray(c,float); a=np.asarray(anchor,float)
    d=a-c; L=np.linalg.norm(d)
    if num is not None:
        sh.circle(c,r,'tb',n=48); sh.txt(c[0],c[1],str(num),h=3.2,bold=True)
        if L>r: sh.line(c+d/L*r,a,'dim')
    else:
        sh.line(c,a,'dim')
    sh.circle(a,0.5,'tb',n=12); sh.tri([a+[0.55,0],a+[-0.3,0.48],a+[-0.3,-0.48]])
    if note:
        right=(side!='left') if side else (c[0]>=a[0])
        x=c[0]+((r+1.2) if num is not None else 0.8)*(1 if right else -1)
        sh.txt(x,c[1],note,h=th,ha='left' if right else 'right',va='center',bg=True)

def place_balloons(sh,view,anchors,occ,margin=12,r=4.0,bounds=None,log=None,notes=None):
    """anchors: list of (num, page_pt). Balloons on a ring round the view bbox, pushed apart so no two touch;
    a second ring takes the overflow when one ring is too short. Returns [(num, center, anchor)]."""
    if not anchors: return []
    x0,y0,x1,y1=view.bbox(); x0-=margin;y0-=margin;x1+=margin;y1+=margin
    if bounds:
        x0=max(x0,bounds[0]+r+1);y0=max(y0,bounds[1]+r+1);x1=min(x1,bounds[2]-r-1);y1=min(y1,bounds[3]-r-1)
    gap=2*r+BAL_GAP
    def ring(x0,y0,x1,y1,anch):
        cx,cy=(x0+x1)/2,(y0+y1)/2
        W=x1-x0;H=y1-y0;per=2*(W+H)
        def to_ring(p):
            dx,dy=p[0]-cx,p[1]-cy
            if abs(dx)<1e-9 and abs(dy)<1e-9: dx=1
            t=min((W/2)/abs(dx) if dx else 1e9,(H/2)/abs(dy) if dy else 1e9)
            q=(cx+dx*t,cy+dy*t)
            if abs(q[1]-y0)<1e-6: return q[0]-x0
            if abs(q[0]-x1)<1e-6: return W+(q[1]-y0)
            if abs(q[1]-y1)<1e-6: return W+H+(x1-q[0])
            return 2*W+H+(y1-q[1])
        def from_ring(s):
            s%=per
            if s<W: return (x0+s,y0)
            s-=W
            if s<H: return (x1,y0+s)
            s-=H
            if s<W: return (x1-s,y1)
            s-=W; return (x0,y1-s)
        ids=list(range(len(anch))); S=np.array([to_ring(a) for _,a in anch],float); n=len(S)
        g=gap*1.45    # perimeter spacing over the chord: across a corner two balloons are only 1/sqrt(2) of it apart
        for _ in range(3000):    # spread along the ring; re-sorted every pass so pushed balloons never pass each other
            o=np.argsort(S); S=S[o]; ids=[ids[k] for k in o]; moved=False
            for k in range(n if n>1 else 0):
                j=(k+1)%n; d=(S[j]-S[k])%per
                if d<g-1e-6: push=(g-d)/2+0.01; S[k]-=push; S[j]+=push; moved=True
            S%=per
            if not moved: break
        return [(anch[ids[k]][0],np.array(from_ring(S[k])),anch[ids[k]][1]) for k in range(n)], per
    def overlaps(out):
        C=np.array([c for _,c,_ in out]);
        if len(C)<2: return False
        D=np.linalg.norm(C[:,None]-C[None],axis=2)+np.eye(len(C))*1e9
        return D.min()<2*r+0.5
    cx,cy=(x0+x1)/2,(y0+y1)/2
    srt=sorted(anchors,key=lambda a:math.atan2(a[1][1]-cy,a[1][0]-cx))
    per0=2*((x1-x0)+(y1-y0)); tiers=max(1,math.ceil(len(anchors)*gap*1.45/per0))
    def tier_rect(t):     # nested rings grow outward but never leave the bounds (a step cell, a view's own area)
        g2=gap+1.0; q=[x0-t*g2,y0-t*g2,x1+t*g2,y1+t*g2]
        if bounds: q=[max(q[0],bounds[0]+r+1),max(q[1],bounds[1]+r+1),min(q[2],bounds[2]-r-1),min(q[3],bounds[3]-r-1)]
        return q
    while True:   # one ring, or as many nested rings as it takes for no two balloons to touch
        out=[]
        for t in range(tiers):
            o,_=ring(*tier_rect(t),srt[t::tiers]); out+=o
        if not overlaps(out) or tiers>=8: break
        tiers+=1
    for num,c,a in out:
        note=(notes or {}).get(num)
        balloon(sh,c,num,a,r,note=note)
        sh.rects.append((c[0]-r,c[1]-r,c[0]+r,c[1]+r))
    if log is not None: log.add(out,r)
    return out

def column_labels(sh,view,entries,area,r=4.0,log=None,th=2.2,col_w=112):
    """Label-view layout: every entry gets a balloon (item number) or a boxed wire label in a column left or right of
    the view, sorted top to bottom so leaders do not cross, text outward. entries: dicts num / anchor / text / box."""
    x0,y0,x1,y1=area; vx0,vy0,vx1,vy1=view.bbox()
    # split at the mean of the tips, not the view centre, so each column takes the parts on its own side
    cx=float(np.mean([e['anchor'][0] for e in entries])) if entries else (vx0+vx1)/2
    cols={'left':[e for e in entries if e['anchor'][0]<cx],'right':[e for e in entries if e['anchor'][0]>=cx]}
    placed=[]
    nc=max(12,int((col_w-22)/(th*0.82)))
    for es_ in cols.values():
        for e in es_: e['text']=textwrap.fill(e['text'],nc) if e.get('text') else e.get('text')
    for side,es in cols.items():
        if not es: continue
        es=sorted(es,key=lambda e:-e['anchor'][1])
        pitch=[max(2*r+BAL_GAP if e.get('num') is not None else 0,(e['text'].count('\n')+1)*th*1.6+1.6) for e in es]
        ys=[]; y=None; pp=None
        for e,p in zip(es,pitch):   # 1-D: each at its anchor height, pushed down below the one above (half of each one's height)
            want=e['anchor'][1]; y=want if y is None else min(want,y-(p+pp)/2); ys.append(y); pp=p
        lo=y0+r+2
        if ys and ys[-1]<lo:        # ran off the bottom: shift up, then squeeze to fit
            sh_=lo-ys[-1]; ys=[v+sh_ for v in ys]
        hi=y1-r-2
        if ys and ys[0]>hi:
            k=(hi-lo)/max(ys[0]-ys[-1],1e-6); ys=[lo+(v-ys[-1])*k for v in ys]
        bx=(vx0-14 if side=='left' else vx1+14)
        for e,y in zip(es,ys):
            c=np.array([bx,y]); a=np.asarray(e['anchor'],float)
            if e.get('num') is None:   # wire label: boxed text, leader to the connection point
                t=e['text']; w=_tw(t,th)+2; h=(t.count('\n')+1)*th*1.6+1.0
                bx0=c[0]-w if side=='left' else c[0]; sh.pl([(bx0,y-h/2),(bx0+w,y-h/2),(bx0+w,y+h/2),(bx0,y+h/2)],'thin',closed=True)
                sh.txt(bx0+1,y,t,h=th,ha='left',va='center')
                sh.line((c[0],y),a,'dim'); sh.circle(a,0.5,'tb',n=12); sh.tri([a+[0.55,0],a+[-0.3,0.48],a+[-0.3,-0.48]])
                sh.rects.append((bx0,y-h/2,bx0+w,y+h/2))
                placed.append((None,c,a))
            else:
                balloon(sh,c,e['num'],a,r,note=e.get('text'),side=side,th=th)
                sh.rects.append((c[0]-r,c[1]-r,c[0]+r,c[1]+r)); placed.append((e['num'],c,a))
    if log is not None:
        log.add([p for p in placed if p[0] is not None],r)
        log.cur['labels']=log.cur.get('labels',0)+sum(1 for p in placed if p[0] is None)
    return placed

class BalloonLog:
    """what the balloon rules found on one drawing; written to <pdf>.checks.json."""
    def __init__(s): s.views=[]; s.ballooned=set(); s.hidden={}; s.cur=None
    def view(s,name): s.cur=dict(view=name,placed=0,overlaps=0,crowded=0,crossings=0,hidden=[]); s.views.append(s.cur)
    def add(s,out,r):
        v=s.cur; v['placed']+=len(out)
        C=[np.asarray(c) for _,c,_ in out]; A=[np.asarray(a) for _,_,a in out]
        for i in range(len(out)):
            if out[i][0] is not None: s.ballooned.add(out[i][0])
            for j in range(i+1,len(out)):
                if np.linalg.norm(C[i]-C[j])<2*r+0.5: v['overlaps']+=1
                if np.linalg.norm(A[i]-A[j])<TIP_MIN_SEP*0.6: v['crowded']+=1
                if _cross(C[i],A[i],C[j],A[j]): v['crossings']+=1
    def miss(s,key): s.cur['hidden'].append(key)

def _cross(p1,p2,p3,p4):
    def o(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    return o(p1,p2,p3)*o(p1,p2,p4)<0 and o(p3,p4,p1)*o(p3,p4,p2)<0

def bom_table(sh,items,x1,ytop,colw=(9,9,44,80,40),h=2.0,title='BILL OF MATERIALS'):
    """draws BOM growing down from ytop, right edge x1. returns bottom y"""
    heads=['ITEM','QTY','PART NUMBER','DESCRIPTION','MATERIAL / SPEC']
    W=sum(colw); x0=x1-W; rh=h*2.1
    rows=[]
    for it in items:
        desc=it['desc'];
        if not it.get('shapes'): desc=desc+' (NOT SHOWN)' if not it.get('shown') else desc
        rows.append([str(it['item']),str(it['qty']),it.get('pn',''),desc,it.get('mat','')])
    y=ytop
    sh.pl([(x0,y),(x1,y),(x1,y-rh*1.2),(x0,y-rh*1.2)],'tb',closed=True)
    xs=np.cumsum([x0]+list(colw))
    for i,hd in enumerate(heads): sh.txt((xs[i]+xs[i+1])/2,y-rh*0.6,hd,h=h,bold=True)
    y-=rh*1.2
    for r in rows:
        wrapped=[textwrap.wrap(str(c),max(3,int(colw[i]/(h*0.80))))or[''] for i,c in enumerate(r)]
        nl=max(len(w) for w in wrapped); hh=rh*(1+0.75*(nl-1))
        sh.pl([(x0,y),(x1,y),(x1,y-hh),(x0,y-hh)],'thin',closed=True)
        for i,w in enumerate(wrapped):
            t='\n'.join(w)
            if i<2: sh.txt((xs[i]+xs[i+1])/2,y-hh/2,t,h=h)
            else: sh.txt(xs[i]+1,y-hh/2,t,h=h,ha='left')
        y-=hh
    for xx in xs[1:-1]: sh.line((xx,ytop),(xx,y),'thin')
    sh.pl([(x0,ytop),(x1,ytop),(x1,y),(x0,y)],'tb',closed=True)
    sh.rects.append((x0,y,x1,ytop))
    return y

def explode_lines(sh,view,pairs):
    """dotted assembly lines: where each moved part came from to where it is drawn."""
    for a,b in pairs:
        pa=view.P(a); pb=view.P(b)
        if np.linalg.norm(pb-pa)>3: sh.line(pa,pb,'expl')

def exploded_shapes(items,st,ctx=()):
    """shapes of one exploded view: st = dict(base=[items left in place], move=[(item, (dx,dy,dz))],
    custom=[(item, shape, vec)], ctx=bool). Returns (shapes, [(item, moved shape)], dotted line pairs)."""
    base=[s for i in st.get('base',[]) for s in (byno(items,i).get('shapes') or [])]
    moving=[]; pairs=[]
    for i,s,vec in st.get('custom',[]):
        m=s.moved(Location(Vector(*vec))); moving.append((i,m)); _MOVED[id(m)]=(m,s,vec)
        c0=np.array(tuple(s.center())); pairs.append((c0,c0+np.array(vec)))
    for i,vec in st.get('move',[]):
        for s in (byno(items,i).get('shapes') or []):
            m=s.moved(Location(Vector(*vec))); moving.append((i,m)); _MOVED[id(m)]=(m,s,vec)
            c0=np.array(tuple(s.center())); pairs.append((c0,c0+np.array(vec)))
    shs=base+[m for _,m in moving]+(list(ctx) if st.get('ctx') else [])
    return shs,moving,pairs

def balloon_view(sh,v,shapes_by_key,log,margin=9,bounds=None,notes=None,am=6,drawn=None):
    """balloon every key of shapes_by_key that is clearly visible in view v; the rest are logged as hidden.
    drawn = the solids drawn in the view (for the ray test)."""
    tree=vis_tree(v); keys=[k for k in shapes_by_key if shapes_by_key[k]]
    UV={}
    for k in keys:
        P=sample_pts3d(shapes_by_key[k][:am],step=0.6); UV[k]=np.c_[P@v.r,P@v.u] if len(P) else np.zeros((0,2))
    occl=Occluder(drawn) if drawn else None
    cands={}
    for k in keys:
        oth=[UV[j] for j in keys if j!=k and len(UV[j])]
        c=visible_candidates(v,shapes_by_key[k][:am],tree,np.vstack(oth) if oth else None,occl)
        if len(c): cands[k]=c
        else: log.miss(k)
    anc=choose_anchors(cands)
    return place_balloons(sh,v,[(k,anc[k]) for k in keys if k in anc],None,margin=margin,bounds=bounds,log=log,notes=notes)

def _iso_selection(spec,items,which):
    """items ballooned in one sheet-1 trimetric. which: 'assembled' | 'open' | 'exploded'.
    spec['iso_balloons'][which] (a list) wins; else in the assembled view only the primary parts (item 'primary': True)
    when any are marked (DRAWING-RULES 26), else the lid / cover items of open_hide (legacy split)."""
    ov=(spec.get('iso_balloons') or {}).get(which)
    live=[it for it in items if it.get('shapes') and not it.get('hide_in_asm') and not it.get('no_balloon')]
    if ov is not None: return [it for it in live if it['item'] in ov]
    hid=set(spec.get('open_hide') or [])
    if which=='assembled':
        prim=[it for it in live if it.get('primary')]
        if prim: return prim
        if hid and spec.get('balloon_split',True): return [it for it in live if it['item'] in hid]
        return live
    if which=='open': return [it for it in live if it['item'] not in hid]
    return live

def _label_entries(v,items,lv,drawn,log):
    """entries for column_labels: one balloon + note per labelled instance (fuse, relay ...), one boxed label per
    harness wire connection point. Hidden ones are logged, never drawn."""
    tree=vis_tree(v); occl=Occluder(drawn); ents=[]
    for lab in lv.get('labels',[]):
        it=byno(items,lab['item']); shs=it.get('shapes') or []
        if 'index' in lab: inst=[shs[lab['index']]] if lab['index']<len(shs) else []
        elif 'at' in lab:
            at=np.asarray(lab['at'],float)
            inst=sorted(shs,key=lambda s:np.linalg.norm(np.array(tuple(s.center()))-at))[:1]
        else: inst=shs[:1]
        key=f"{lab['item']}:{lab.get('index',lab.get('at',0))}"
        c=visible_candidates(v,inst,tree,None,occl) if inst else np.zeros((0,2))
        if not len(c): log.miss(key); continue
        ents.append(dict(num=lab['item'],anchor=choose_anchors({0:c})[0],text=lab['text'],key=key))
    for w in lv.get('wires',[]):
        p=np.asarray(w['at'],float); key='wire:'+w['text']
        if w.get('item') is not None:   # anchored on the part at that point (the terminal / lug / plug the wire lands in)
            shs=byno(items,w['item']).get('shapes') or []
            inst=sorted(shs,key=lambda s:np.linalg.norm(np.array(tuple(s.center()))-p))[:1]
            c=visible_candidates(v,inst,tree,None,occl) if inst else np.zeros((0,2))
            if not len(c): log.miss(key); continue
            pg=c[np.argmin(np.linalg.norm(c-v.P(p),axis=1))]
        else:
            pg=v.P(p)
            if occl.hidden(p,v.c): log.miss(key); continue
        ents.append(dict(num=None,anchor=pg,text=w['text'],key=key))
    # spread tips that land on the same spot
    for i in range(len(ents)):
        for j in range(i):
            if np.linalg.norm(ents[i]['anchor']-ents[j]['anchor'])<0.3: ents[i]['anchor']=ents[i]['anchor']+np.array([0.0,0.8])
    return ents

def stage_sheet_count(groups):
    return sum(-(-len(g)//4) for g in groups)

def add_stage_sheets(sheets,items,groups,ctx,info,nsheets,log,iso='iso',notes=None):
    """one sheet per group of exploded install steps (2 x n cells), balloons on the parts that move in each step (and the base
    parts not ballooned yet), dotted lines from each part to its place. notes: {item: text} printed beside its balloon."""
    chunks=[]     # at most 4 steps (2 x 2) on a sheet, so each step view is big enough to read
    for stages in groups:
        for k in range(0,len(stages),4): chunks.append(stages[k:k+4])
    for stages in chunks:
        sh=Sheet()
        n=len(stages); cols=2 if n>1 else 1; rows=math.ceil(n/cols)
        gx0,gy0,gx1,gy1=14,66,PW-14,PH-14
        cw=(gx1-gx0)/cols; ch=(gy1-gy0)/rows
        _done=set()
        for k,st in enumerate(stages):
            r_=k//cols; c_=k%cols
            # bottom row reserved for title block area on right: shrink cells in lowest row
            cx0=gx0+c_*cw; cy1=gy1-r_*ch; cx1=cx0+cw; cy0=cy1-ch
            if r_==rows-1 and c_==cols-1 and cols>1: cy0=max(cy0,66)
            shs,moving,pairs=exploded_shapes(items,st,ctx)
            if not shs: continue
            v=View(Compound(shs),st.get('view',iso),1.0)
            title_h=12
            sc=min((cw-40)/(v.umax-v.umin),(ch-30-title_h)/(v.vmax-v.vmin))
            v.scale=sc; v.w=(v.umax-v.umin)*sc; v.h=(v.vmax-v.vmin)*sc
            v.place((cx0+cx1)/2,(cy0+cy1)/2-4)
            v.draw(sh)
            explode_lines(sh,v,pairs)
            mv_ids=list(dict.fromkeys([x for x,_ in st.get('move',[])]+[x for x,_,_ in st.get('custom',[])]))
            bb_=st.get('balloon_base',[b for b in st.get('base',[]) if b not in _done])
            ids=[i for i in dict.fromkeys(mv_ids+bb_) if not byno(items,i).get('no_balloon')]
            sbk={i:([m for j,m in moving if j==i] or (byno(items,i).get('shapes') or []))[:6] for i in ids}
            log.view(f"STEP {st['no']}")
            out=balloon_view(sh,v,sbk,log,margin=9,bounds=(cx0+2,cy0+2,cx1-2,cy1-title_h),drawn=shs,notes=notes)
            _done.update(i for i,_,_ in out)
            sh.txt((cx0+cx1)/2,cy1-2,f"STEP {st['no']}: {st['title']}",h=3.2,bold=True,va='top')
            sh.txt((cx0+cx1)/2,cy1-7.5,st.get('subtitle',"EXPLODED TRIMETRIC (NOT TO SCALE)"),h=2.4,va='top')
            if st.get('note'): sh.txt(cx0+4,cy0+4,st['note'],h=2.4,ha='left',va='bottom')
        frame(sh,dict(info,scale='AS SHOWN'),len(sheets)+1,nsheets)
        sheets.append(sh)

def make_assembly(spec,out_pdf,png_prefix=None):
    items=spec['items']
    allsh=[s for it in items for s in (it.get('shapes') or []) if not it.get('hide_in_asm')]
    ctx=spec.get('context',[])  # shapes drawn but not in BOM (phantom-ish)
    comp=Compound(allsh+ctx)
    bb=comp.bounding_box()
    sheets=[]; log=BalloonLog()
    lviews=spec.get('label_views',[])
    nsheets=1+len(lviews)+stage_sheet_count(spec.get('stage_sheets',[]))
    info=dict(title=spec['title'],pn=spec['pn'],material='SEE BOM',source=spec.get('source',''),project=spec.get('project'),drawn=spec.get('drawn'))
    if spec.get('tol'): info['tol']=spec['tol']
    # ---- sheet 1
    revrows,rev,_=resolve_revlog(spec,spec.get('file'))
    info.update(rev=rev or '-',revlog=revrows,drawn=spec['_drawn'])
    sh=Sheet(); occ=Occ(); occ.rects=sh.rects
    rlr=revlog_rect(revrows)      # rev log top right; BOM starts below it
    ybot=bom_table(sh,items,PW-10,rlr[1]-3,colw=spec.get('bom_cols',(9,9,44,80,40)),h=spec.get('bom_h',2.0))
    bom_x0=PW-10-sum(spec.get('bom_cols',(9,9,44,80,40)))
    # views region
    bx0=bom_x0-6
    V={n:View(comp,n,1.0,name=n) for n in ['front','top','right']}
    iso=View(comp,spec.get('iso','iso'),1.0)
    isos=[('TRIMETRIC VIEW',iso,'assembled',list(allsh+ctx),None)]
    if spec.get('open_hide'):
        hid=set(spec['open_hide'])
        osh=[s for it in items if it['item'] not in hid and not it.get('hide_in_asm') for s in (it.get('shapes') or [])]+list(ctx)
        isos.append((spec.get('open_label','TRIMETRIC - LID REMOVED'),View(Compound(osh),spec.get('iso','iso'),1.0),'open',osh,None))
    if spec.get('exploded'):      # an exploded trimetric on sheet 1: hidden parts pulled out, dotted assembly lines
        ex=dict(spec['exploded']); ex.setdefault('base',[it['item'] for it in items if it.get('shapes') and it['item'] not in {i for i,_ in ex.get('move',[])}])
        esh,emov,epairs=exploded_shapes(items,ex,ctx)
        isos.append((ex.get('label','EXPLODED VIEW'),View(Compound(esh),ex.get('view',spec.get('iso','iso')),1.0),'exploded',esh,(ex,emov,epairs)))
    Wf=V['front'].w;Hf=V['front'].h;Ht=V['top'].h;Wr=V['right'].w
    gx=gy=24
    def fit_iso(vs,box):
        # place len(vs) iso views side by side (or stacked) in box, return scale
        x0,y0,x1,y1=box; n=len(vs); best=None
        for horiz in (True,False):
            cw=(x1-x0)/(n if horiz else 1); chh=(y1-y0)/(1 if horiz else n)
            sc=min(min((cw-24)/(v.umax-v.umin),(chh-28)/(v.vmax-v.vmin)) for v in vs)
            if best is None or sc>best[0]: best=(sc,horiz)
        return best
    cands=[]
    ivs=[x[1] for x in isos]
    # L1: ortho left column region A, isos right below BOM
    for frac in np.linspace(0.3,0.75,10):
        xa=14+(PW-28)*frac
        A=(14,70,min(xa,bx0),PH-14); B=(xa,70,PW-14,ybot-4)
        if B[3]-B[1]<60 or A[2]-A[0]<60: continue
        s=min((A[2]-A[0]-gx-26)/(Wf+Wr),(A[3]-A[1]-gy-36)/(Hf+Ht))
        fi=fit_iso(ivs,B)
        if s<=0 or fi[0]<=0: continue
        cands.append((min(fi[0],np.sqrt(pick_scale(s)*1.4*fi[0])),'L1',A,B,s,fi))
    # L2: isos on top-left, ortho bottom-left (for tall BOMs)
    for frac in np.linspace(0.35,0.65,7):
        ya=70+(PH-84)*frac
        A=(14,70,bx0,ya); B=(14,ya,bx0,PH-14)
        s=min((A[2]-A[0]-gx-26)/(Wf+Wr),(A[3]-A[1]-gy-36)/(Hf+Ht))
        fi=fit_iso(ivs,B)
        if s<=0 or fi[0]<=0: continue
        cands.append((min(fi[0],np.sqrt(pick_scale(s)*1.4*fi[0])),'L2',A,B,s,fi))
    _,lay,A,B,s,(si,horiz)=max(cands,key=lambda c:c[0])
    s=spec.get('scale',pick_scale(s))
    rx0,ry0,rx1,ry1=A
    for v in V.values(): v.scale=s; v.w=(v.umax-v.umin)*s; v.h=(v.vmax-v.vmin)*s
    tw=V['front'].w+gx+V['right'].w; th=V['front'].h+gy+V['top'].h
    ox=A[0]+14+(A[2]-A[0]-14-tw)/2; oy=A[1]+24+(A[3]-A[1]-24-th)/2
    V['front'].place(ox+V['front'].w/2,oy+V['front'].h/2)
    V['top'].place(ox+V['front'].w/2,oy+V['front'].h+gy+V['top'].h/2)
    V['right'].place(ox+V['front'].w+gx+V['right'].w/2,oy+V['front'].h/2)
    for v in V.values(): v.draw(sh); occ.add(v.bbox())
    n=len(isos); am=spec.get('anchor_max',6)
    for k,(lbl,v,which,drawn,exd) in enumerate(isos):
        if horiz: cw=(B[2]-B[0])/n; cell=(B[0]+k*cw,B[1],B[0]+(k+1)*cw,B[3])
        else: chh=(B[3]-B[1])/n; cell=(B[0],B[3]-(k+1)*chh,B[2],B[3]-k*chh)
        v.scale=si*0.92; v.w=(v.umax-v.umin)*v.scale; v.h=(v.vmax-v.vmin)*v.scale
        v.place((cell[0]+cell[2])/2,(cell[1]+cell[3])/2+5)
        v.draw(sh); occ.add(v.bbox())
        sh.txt(v.cx,cell[1]+8,lbl,h=3.2,bold=True,va='top')
        log.view(lbl)
        if exd:
            ex,emov,epairs=exd; explode_lines(sh,v,epairs)
            sel=_iso_selection(spec,items,'exploded')
            want=set(ex.get('balloon',[i for i,_ in ex.get('move',[])]+[i for i,_,_ in ex.get('custom',[])]))
            sbk={it['item']:([m for j,m in emov if j==it['item']] or it['shapes']) for it in sel if it['item'] in want}
        else:
            sel=_iso_selection(spec,items,which)
            sbk={it['item']:it['shapes'] for it in sel}
        balloon_view(sh,v,sbk,log,margin=9,bounds=(cell[0]+1,cell[1]+10,cell[2]-1,cell[3]-1),am=am,drawn=drawn)
    # overall reference dims
    fv=V['front']; x0_,y0_,x1_,y1_=fv.bbox()
    dim_lin(sh,(x0_,y0_),(x1_,y0_),'h',y0_-9,f"({fmt(bb.size.X,1)})")
    dim_lin(sh,(x0_,y0_),(x0_,y1_),'v',x0_-9,f"({fmt(bb.size.Z,1)})")
    rv=V['right']; x0_,y0_,x1_,y1_=rv.bbox()
    dim_lin(sh,(x0_,y0_),(x1_,y0_),'h',y0_-9,f"({fmt(bb.size.Y,1)})")
    sh.txt(fv.cx+ (V['right'].cx-fv.cx)/2,fv.bbox()[1]-17,f"FRONT / TOP / RIGHT VIEWS  SCALE {scale_str(s)}",h=3.0,bold=True,va='top')
    if spec.get('notes'): notes_block(sh,14,ry0-2,spec['notes'],h=2.2,width=130)
    info1=dict(info,scale=scale_str(s))
    frame(sh,info1,1,nsheets)
    sheets.append(sh)
    # ---- label sheets: one view, every fuse / relay ballooned with the circuit it serves, every harness wire
    #      connection point labelled with the harness drawing's wire-end label (DRAWING-RULES 27, 28)
    for li,lv in enumerate(lviews):
        sh=Sheet()
        hide=set(lv.get('hide',[]))
        lsh=[s for it in items if it['item'] not in hide and not it.get('hide_in_asm') for s in (it.get('shapes') or [])]+list(ctx)
        v=View(Compound(lsh),lv.get('view','top'),1.0)
        colw=lv.get('col_w',112); area=(14+colw,66,PW-14-colw,PH-24)
        sc=min((area[2]-area[0]-28)/(v.umax-v.umin),(area[3]-area[1]-16)/(v.vmax-v.vmin))
        sc=lv.get('scale') or pick_scale(sc)
        v.scale=sc; v.w=(v.umax-v.umin)*sc; v.h=(v.vmax-v.vmin)*sc
        v.place((area[0]+area[2])/2,(area[1]+area[3])/2)
        v.draw(sh)
        log.view(f"LABELS {li+1}")
        ents=_label_entries(v,items,lv,lsh,log)
        column_labels(sh,v,ents,(14,66,PW-14,PH-16),log=log,th=lv.get('text_h',2.2),col_w=colw)
        sh.txt(PW/2,PH-14,lv.get('title','FUSE, RELAY AND WIRE LABELS'),h=3.6,bold=True,va='top')
        sh.txt(PW/2,PH-20,f"{lv.get('view','top').upper()} VIEW  SCALE {scale_str(sc)}",h=2.6,va='top')
        frame(sh,dict(info,scale=scale_str(sc)),len(sheets)+1,nsheets)
        sheets.append(sh)
    add_stage_sheets(sheets,items,spec.get('stage_sheets',[]),ctx,info,nsheets,log,iso=spec.get('iso','iso'),notes=spec.get('stage_notes'))
    render(sheets,out_pdf,None,png_prefix)
    want=[it['item'] for it in items if it.get('shapes') and not it.get('hide_in_asm') and not it.get('no_balloon')]
    nb=[i for i in want if i not in log.ballooned]
    return write_checks(out_pdf,spec['pn'],log,spec.get('notes'),info.get('tol'),dict(not_ballooned=nb))

def byno(items,i):
    for it in items:
        if it['item']==i: return it
    raise KeyError(i)
