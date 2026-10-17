import math, numpy as np, textwrap
from build123d import *
from scipy.spatial import cKDTree
from dwg import *
from dwg import _tw
from part import text_rect, Occ

def load_children(path):
    s=import_step(path); out={}
    for c in s.children:
        out.setdefault(c.label,[]).extend(c.solids())
    return out

def shapes_bb(shs):
    c=Compound(list(shs)); return c.bounding_box()

def sample_pts3d(shs,n_per_edge=6,maxe=3000):
    pts=[]
    for s in shs:
        es=s.edges()
        step=max(1,len(es)//maxe)
        for e in es[::step]:
            try:
                for t in np.linspace(0,1,n_per_edge): pts.append(tuple(e.position_at(t)))
            except Exception: pass
    return np.array(pts) if pts else np.zeros((0,3))

SHEET_DONE={}
def anchor_for(view,item_shs,tree,ctr_pg=None,others=None):
    P=sample_pts3d(item_shs)
    if len(P)==0: return None
    uv=np.c_[P@view.r,P@view.u]
    d,_=tree.query(uv)
    ok=uv[d<0.08]
    if len(ok)<3: return None
    if others is not None and len(others):
        ot=cKDTree(others); span=max(np.ptp(ok[:,0]),np.ptp(ok[:,1]),1.0)
        do,_=ot.query(ok); own=ok[do>max(0.6,0.03*span)]
        if len(own)>=3: ok=own
    cen=uv.mean(0)
    # prefer visible point near the item's own centroid, slightly biased outward
    k=np.argmin(np.linalg.norm(ok-cen,axis=1))
    return view.uv2pg(ok[k])

def vis_tree(view):
    pts=[]
    for p in view.vis:
        for a,b in zip(p[:-1],p[1:]):
            L=np.linalg.norm(b-a); n=max(2,int(L/0.05)+1)
            pts.append(np.linspace(a,b,n))
    return cKDTree(np.vstack(pts))

def balloon(sh,c,num,anchor,r=4.0):
    c=np.asarray(c,float); a=np.asarray(anchor,float)
    d=a-c; L=np.linalg.norm(d)
    sh.circle(c,r,'tb',n=48); sh.txt(c[0],c[1],str(num),h=3.2,bold=True)
    if L>r: sh.line(c+d/L*r,a,'dim')
    sh.circle(a,0.5,'tb',n=12); sh.tri([a+[0.55,0],a+[-0.3,0.48],a+[-0.3,-0.48]])

def place_balloons(sh,view,anchors,occ,margin=12,r=4.0,bounds=None):
    """anchors: list of (num, page_pt). Put balloons on ring around view bbox."""
    if not anchors: return
    x0,y0,x1,y1=view.bbox(); x0-=margin;y0-=margin;x1+=margin;y1+=margin
    if bounds:
        x0=max(x0,bounds[0]+r+1);y0=max(y0,bounds[1]+r+1);x1=min(x1,bounds[2]-r-1);y1=min(y1,bounds[3]-r-1)
    cx,cy=(x0+x1)/2,(y0+y1)/2
    W=x1-x0;H=y1-y0;per=2*(W+H)
    def to_ring(p):
        dx,dy=p[0]-cx,p[1]-cy
        if abs(dx)<1e-9 and abs(dy)<1e-9: dx=1
        t=min((W/2)/abs(dx) if dx else 1e9,(H/2)/abs(dy) if dy else 1e9)
        q=(cx+dx*t,cy+dy*t)
        # perimeter param starting bottom-left going CCW
        if abs(q[1]-y0)<1e-6: s=q[0]-x0
        elif abs(q[0]-x1)<1e-6: s=W+(q[1]-y0)
        elif abs(q[1]-y1)<1e-6: s=W+H+(x1-q[0])
        else: s=2*W+H+(y1-q[1])
        return s
    def from_ring(s):
        s%=per
        if s<W: return (x0+s,y0)
        s-=W
        if s<H: return (x1,y0+s)
        s-=H
        if s<W: return (x1-s,y1)
        s-=W; return (x0,y1-s)
    S=[to_ring(a) for _,a in anchors]
    order=np.argsort(S); S=np.array(S)[order]
    gap=2*r+2.5
    n=len(S)
    if n*gap>per: gap=per/n
    for it in range(200):
        moved=False
        for i in range(n):
            j=(i+1)%n
            d=(S[j]-S[i])%per
            if n>1 and d<gap:
                push=(gap-d)/2+0.01; S[i]-=push; S[j]+=push; moved=True
        if not moved: break
    for k,i in enumerate(order):
        num,a=anchors[i]; c=from_ring(S[k])
        balloon(sh,c,num,a,r)

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
    for a,b in pairs:
        pa=view.P(a); pb=view.P(b)
        if np.linalg.norm(pb-pa)>3: sh.line(pa,pb,'expl')

def make_assembly(spec,out_pdf,png_prefix=None):
    items=spec['items']
    allsh=[s for it in items for s in (it.get('shapes') or []) if not it.get('hide_in_asm')]
    ctx=spec.get('context',[])  # shapes drawn but not in BOM (phantom-ish)
    comp=Compound(allsh+ctx)
    bb=comp.bounding_box()
    sheets=[]
    nsheets=1+len(spec.get('stage_sheets',[]))
    info=dict(title=spec['title'],pn=spec['pn'],material='SEE BOM',source=spec.get('source',''),project=spec.get('project'),drawn=spec.get('drawn'))
    # ---- sheet 1
    revrows,rev,_=resolve_revlog(spec,spec.get('file'))
    info.update(rev=rev or '-',revlog=revrows)
    sh=Sheet(); occ=Occ(); occ.rects=sh.rects
    rlr=revlog_rect(revrows)      # rev log top right; BOM starts below it
    ybot=bom_table(sh,items,PW-10,rlr[1]-3,colw=spec.get('bom_cols',(9,9,44,80,40)),h=spec.get('bom_h',2.0))
    bom_x0=PW-10-sum(spec.get('bom_cols',(9,9,44,80,40)))
    # views region
    bx0=bom_x0-6
    V={n:View(comp,n,1.0,name=n) for n in ['front','top','right']}
    iso=View(comp,spec.get('iso','iso'),1.0)
    isos=[('TRIMETRIC VIEW',iso,None)]
    if spec.get('open_hide'):
        hid=set(spec['open_hide'])
        osh=[s for it in items if it['item'] not in hid and not it.get('hide_in_asm') for s in (it.get('shapes') or [])]+list(ctx)
        isos.append((spec.get('open_label','TRIMETRIC - LID REMOVED'),View(Compound(osh),spec.get('iso','iso'),1.0),hid))
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
    # L1: ortho left column region A, isos right below BOM
    for frac in np.linspace(0.3,0.75,10):
        xa=14+(PW-28)*frac
        A=(14,70,min(xa,bx0),PH-14); B=(xa,70,PW-14,ybot-4)
        if B[3]-B[1]<60 or A[2]-A[0]<60: continue
        s=min((A[2]-A[0]-gx-26)/(Wf+Wr),(A[3]-A[1]-gy-36)/(Hf+Ht))
        fi=fit_iso([v for _,v,_ in isos],B)
        if s<=0 or fi[0]<=0: continue
        cands.append((min(fi[0],np.sqrt(pick_scale(s)*1.4*fi[0])),'L1',A,B,s,fi))
    # L2: isos on top-left, ortho bottom-left (for tall BOMs)
    for frac in np.linspace(0.35,0.65,7):
        ya=70+(PH-84)*frac
        A=(14,70,bx0,ya); B=(14,ya,bx0,PH-14)
        s=min((A[2]-A[0]-gx-26)/(Wf+Wr),(A[3]-A[1]-gy-36)/(Hf+Ht))
        fi=fit_iso([v for _,v,_ in isos],B)
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
    n=len(isos)
    for k,(lbl,v,hid) in enumerate(isos):
        if horiz: cw=(B[2]-B[0])/n; cell=(B[0]+k*cw,B[1],B[0]+(k+1)*cw,B[3])
        else: chh=(B[3]-B[1])/n; cell=(B[0],B[3]-(k+1)*chh,B[2],B[3]-k*chh)
        v.scale=si*0.92; v.w=(v.umax-v.umin)*v.scale; v.h=(v.vmax-v.vmin)*v.scale
        v.place((cell[0]+cell[2])/2,(cell[1]+cell[3])/2+5)
        v.draw(sh); occ.add(v.bbox())
        sh.txt(v.cx,cell[1]+8,lbl,h=3.2,bold=True,va='top')
        tree=vis_tree(v); anchors=[]; sel=[]
        for it in items:
            if not it.get('shapes') or it.get('hide_in_asm'): continue
            if hid and it['item'] in hid: continue
            if hid is None and spec.get('open_hide') and it['item'] not in spec['open_hide'] and spec.get('balloon_split',True): continue
            sel.append(it)
        am=spec.get('anchor_max',6); UV={}
        for it in sel:
            P=sample_pts3d(it['shapes'][:am]); UV[it['item']]=np.c_[P@v.r,P@v.u] if len(P) else np.zeros((0,2))
        for it in sel:
            oth=[UV[j] for j in UV if j!=it['item'] and len(UV[j])]
            a=anchor_for(v,it['shapes'][:am],tree,others=np.vstack(oth) if oth else None)
            if a is not None: anchors.append((it['item'],a))
        place_balloons(sh,v,anchors,occ,margin=9,bounds=(cell[0]+1,cell[1]+10,cell[2]-1,cell[3]-1))
    # overall reference dims
    fv=V['front']; x0_,y0_,x1_,y1_=fv.bbox()
    dim_lin(sh,(x0_,y0_),(x1_,y0_),'h',y0_-9,f"({fmt(bb.size.X,1)})")
    dim_lin(sh,(x0_,y0_),(x0_,y1_),'v',x0_-9,f"({fmt(bb.size.Z,1)})")
    rv=V['right']; x0_,y0_,x1_,y1_=rv.bbox()
    dim_lin(sh,(x0_,y0_),(x1_,y0_),'h',y0_-9,f"({fmt(bb.size.Y,1)})")
    sh.txt(fv.cx+ (V['right'].cx-fv.cx)/2,fv.bbox()[1]-17,f"FRONT / TOP / RIGHT VIEWS  SCALE {scale_str(s)}",h=3.0,bold=True,va='top')
    if spec.get('notes'): notes_block(sh,14,66 if False else ry0-2,spec['notes'],h=2.2,width=130)
    info1=dict(info,scale=scale_str(s))
    frame(sh,info1,1,nsheets)
    sheets.append(sh)
    # ---- stage sheets
    for si_,stages in enumerate(spec.get('stage_sheets',[])):
        sh=Sheet()
        n=len(stages); cols=2 if n>1 else 1; rows=math.ceil(n/cols)
        gx0,gy0,gx1,gy1=14,66,PW-14,PH-14
        cw=(gx1-gx0)/cols; ch=(gy1-gy0)/rows
        for k,st in enumerate(stages):
            r_=k//cols; c_=k%cols
            # bottom row reserved for title block area on right: shrink cells in lowest row
            cx0=gx0+c_*cw; cy1=gy1-r_*ch; cx1=cx0+cw; cy0=cy1-ch
            if r_==rows-1 and c_==cols-1 and cols>1: cy0=max(cy0,66)
            base=[s for i in st['base'] for s in (byno(items,i).get('shapes') or [])]
            moving=[]; pairs=[]
            for i,s,vec in st.get('custom',[]):
                m=s.moved(Location(Vector(*vec))); moving.append((i,m))
                c0=np.array(tuple(s.center())); pairs.append((c0,c0+np.array(vec)))
            for i,vec in st['move']:
                it=byno(items,i)
                for s in (it.get('shapes') or []):
                    m=s.moved(Location(Vector(*vec))); moving.append((i,m))
                    c0=np.array(tuple(s.center())); pairs.append((c0,c0+np.array(vec)))
            shs=base+[m for _,m in moving]+(list(ctx) if st.get('ctx') else [])
            if not shs: continue
            v=View(Compound(shs),st.get('view',spec.get('iso','iso')),1.0)
            title_h=12
            sc=min((cw-40)/(v.umax-v.umin),(ch-30-title_h)/(v.vmax-v.vmin))
            v.scale=sc; v.w=(v.umax-v.umin)*sc; v.h=(v.vmax-v.vmin)*sc
            v.place((cx0+cx1)/2,(cy0+cy1)/2-4)
            v.draw(sh); 
            explode_lines(sh,v,pairs)
            tree=vis_tree(v)
            anchors=[]
            _done=SHEET_DONE.setdefault(id(sh),set())
            mv_ids=list(dict.fromkeys([x for x,_ in st['move']]+[x for x,_,_ in st.get('custom',[])]))
            bb=st.get('balloon_base',[b for b in st['base'] if b not in _done])
            ids=list(dict.fromkeys(mv_ids+bb))
            def _shs(i):
                it=byno(items,i)
                return ([m for j,m in moving if j==i] or (it.get('shapes') or []))[:6]
            uvs={}
            for i in ids:
                P=sample_pts3d(_shs(i)) if _shs(i) else np.zeros((0,3))
                uvs[i]=np.c_[P@v.r,P@v.u] if len(P) else np.zeros((0,2))
            for i in ids:
                if not len(uvs[i]): continue
                oth=[uvs[j] for j in ids if j!=i and len(uvs[j])]
                a=anchor_for(v,_shs(i),tree,others=np.vstack(oth) if oth else None)
                if a is not None: anchors.append((i,a)); _done.add(i)
            place_balloons(sh,v,anchors,None,margin=9,bounds=(cx0+2,cy0+2,cx1-2,cy1-title_h))
            sh.txt((cx0+cx1)/2,cy1-2,f"STEP {st['no']}: {st['title']}",h=3.2,bold=True,va='top')
            sh.txt((cx0+cx1)/2,cy1-7.5,"EXPLODED TRIMETRIC (NOT TO SCALE)",h=2.4,va='top')
            if st.get('note'): sh.txt(cx0+4,cy0+4,st['note'],h=2.4,ha='left',va='bottom')
        frame(sh,dict(info,scale='AS SHOWN'),si_+2,nsheets)
        sheets.append(sh)
    render(sheets,out_pdf,None,png_prefix)

def byno(items,i):
    for it in items:
        if it['item']==i: return it
    raise KeyError(i)
