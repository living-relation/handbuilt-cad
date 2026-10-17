import math, numpy as np, copy
from collections import defaultdict
from build123d import *
from shapely.geometry import LineString as SLine, Polygon as SPoly, Point as SPoint, box as sbox
from dwg import *
from dwg import _tw
import feat

TAP={2.5:('M3x0.5',0.5),3.3:('M4x0.7',0.7),4.2:('M5x0.8',0.8),5.0:('M6x1.0',1.0),6.8:('M8x1.25',1.25),8.5:('M10x1.5',1.5),10.2:('M12x1.75',1.75)}
VIEW_FOR_AXIS={'Z':'top','X':'right','Y':'front'}

class Occ:
    def __init__(s): s.rects=[]
    def free(s,r,pad=1.0):
        for q in s.rects:
            if r[0]<q[2]+pad and r[2]>q[0]-pad and r[1]<q[3]+pad and r[3]>q[1]-pad: return False
        return True
    def add(s,r): s.rects.append(r)

def text_rect(x,y,t,h,ha,va):
    w=_tw(t,h); n=t.count('\n')+1; H=n*h*1.6
    x0={'left':x,'right':x-w,'center':x-w/2}[ha]; y0={'bottom':y,'top':y-H,'center':y-H/2}[va]
    return (x0,y0,x0+w,y0+H)

def hole_callouts(solid,process,spec):
    holes,radii,_=feat.analyze(solid)
    tmap=spec.get('threads',{})
    groups=defaultdict(list)
    for h in holes:
        ks=sorted(h['segs']); r0=ks[0]; d0=2*r0
        t0,t1=h['segs'][r0]
        ax=h['axis']
        # entry side
        if h['through']:
            big=[k for k in ks[1:]]
            if big:
                bt=h['segs'][big[0]]; entry_hi = abs(bt[1]-h['hi'])<abs(bt[0]-h['lo'])
            else:
                cs=[c for c in h['cones'] if c[1]-c[0]>0.4]
                entry_hi = (not cs) or abs(cs[0][1]-h['hi'])<abs(cs[0][0]-h['lo'])
        else:
            entry_hi=h['open_hi']
        key=None; lines=[]
        dk=round(d0,1)
        thr=None; tapd=d0
        for td,(tn,p) in TAP.items():
            if abs(d0-td)<0.08 and any(abs(td-k)<0.08 for k in tmap): thr=(tn,p); tapd=td
        for k,vv in tmap.items():
            if abs(d0-k)<0.08 and isinstance(vv,tuple): thr=vv; tapd=k
        ov=tmap.get(dk)
        if ov=='plain': thr=None
        elif isinstance(ov,tuple): thr=ov
        if process!='machined' and ov is None: thr=None
        entry=h['hi'] if entry_hi else h['lo']
        # depth of smallest bore from entry
        far = t0 if entry_hi else t1
        depth=abs(entry-far)
        cb=None; fcb=None
        for k2 in ks[1:]:
            a,b=h['segs'][k2]
            touches_entry = abs((b if entry_hi else a)-entry)<0.05
            if touches_entry and cb is None: cb=(2*k2,b-a)
            elif not touches_entry and fcb is None: fcb=(2*k2,b-a)
        csk=None
        for (a,b,half) in h['cones']:
            at_entry = abs((b if entry_hi else a)-entry)<0.05
            if at_entry and math.degrees(half)<50 and (b-a)>0.3:
                rr=r0 if not cb else cb[0]/2
                csk=(2*(rr+(b-a)*math.tan(half)),2*math.degrees(half))
        if cb and not h['through']:
            # depth measured from entry for the small bore
            pass
        if thr:
            tn,p=thr; tdep=spec.get('thread_depth',{}).get(dk)
            if h['through'] or (cb and abs(depth-cb[1])>0 and h['through']): lines.append(f"{tn}-6H THRU")
            else:
                if tdep is None: tdep=max(round((depth-3*p)*2)/2, p*3)
                lines.append(f"⌀{fmt(tapd,2)} ↧{fmt(depth,1)}"); lines.append(f"{tn}-6H ↧{fmt(tdep,1)}")
        else:
            lines.append(f"⌀{fmt(d0,2)} " + ("THRU" if h['through'] else f"↧{fmt(depth,1)}"))
        if cb: lines.append(f"⌴ ⌀{fmt(cb[0],2)} ↧{fmt(cb[1],1)}")
        if fcb: lines.append(f"⌴ ⌀{fmt(fcb[0],2)} ↧{fmt(fcb[1],1)} FAR SIDE")
        if csk: lines.append(f"⌵ ⌀{fmt(csk[0],1)} X {fmt(csk[1],0)}°")
        bn=spec.get('boss_note',{}).get(dk)
        if bn and not h['through'] and depth<7: lines.append(bn)
        txt='\n'.join(lines)
        ovt=spec.get('hole_text',{}).get((ax,dk))
        if ovt=='skip': continue
        if ovt: txt=ovt
        center=h['base']+entry*h['d']
        side = '' if entry_hi else ' FAR SIDE'
        groups[(ax,txt+('' if (entry_hi or h['through']) else '\n(FROM '+{'Z':'BOTTOM','X':'-X SIDE','Y':'-Y SIDE'}[ax]+')'))].append(dict(c=center,r=r0,rmax=max(ks) if not csk else csk[0]/2,entry_hi=entry_hi))
    rgroups=defaultdict(list)
    for r in radii:
        rr=min(r['segs']); 
        if rr<0.6: continue
        a,b=r['segs'][rr]
        rgroups[(r['axis'],round(rr,2))].append(dict(base=r['base'],t=b,face=r))
    return groups,rgroups

def place_leaders(sh,occ,pending,ymin=66):
    from shapely.geometry import box as B, LineString as L
    for (v,tip,t,right,dirv) in pending:
        best=None
        R=[B(*q) for q in occ.rects]
        for dx in range(8,150,5):
            for dy in range(-100,101,4):
                for rr in (True,False):
                    tx=tip[0]+(dx if rr else -dx); ty=tip[1]+dy
                    r=text_rect(tx+(1 if rr else -1),ty,t,TH,'left' if rr else 'right','center')
                    if r[0]<12 or r[2]>PW-12 or r[3]>PH-12 or r[1]<ymin: continue
                    cost=math.hypot(dx,dy)+(0 if rr==right else 10)+abs(dy)*0.2
                    if best and cost>=best[0]: continue
                    rb=B(r[0]-1.5,r[1]-1.5,r[2]+1.5,r[3]+1.5)
                    ov=sum(1 for q in R if q.intersects(rb))
                    seg=L([tip,(tx-(4 if rr else -4),ty)])
                    cr=sum(1 for q,qq in zip(R,occ.rects) if not (qq[0]<=tip[0]<=qq[2] and qq[1]<=tip[1]<=qq[3]) and (qq[2]-qq[0])<200 and seg.intersects(q))
                    cost+=ov*1000+cr*150
                    if best is None or cost<best[0]: best=(cost,tx,ty,r)
        occ.add(best[3]); leader(sh,tip,best[1:3],t)

def seg_hits(a,b,rects):
    from shapely.geometry import LineString, box
    L=LineString([a,b])
    for r in rects:
        if (r[2]-r[0])>150: continue
        if L.intersects(box(*r)): 
            # ignore the view bbox containing the tip
            if r[0]<=a[0]<=r[2] and r[1]<=a[1]<=r[3]: continue
            return True
    return False

def lin_val(view,p1,p2,orient):
    q1=view.uv(p1); q2=view.uv(p2)
    return abs(q1[0]-q2[0]) if orient=='h' else abs(q1[1]-q2[1])

def auto_align_angle(solid,min_share=0.25):
    """Z rotation (deg, in (-45,45]) that squares the part's dominant vertical flat faces to the X/Y views.
    0 when already square (existing axis-aligned parts are untouched). A part modelled in a rotated frame
    (e.g. the fuel hanger strut plane) otherwise gets oblique views: no true circles, no hole callouts, no center marks."""
    from collections import defaultdict
    w=defaultdict(float); tot=0.0
    for f in solid.faces():
        if f.geom_type!=GeomType.PLANE: continue
        n=f.normal_at(); 
        if abs(n.Z)>1e-3: continue
        a=f.area; tot+=a
        th=math.degrees(math.atan2(n.Y,n.X))%90.0
        w[round(th,2)%90.0]+=a
    if not w or tot<=0: return 0.0
    th,best=max(w.items(),key=lambda kv:kv[1])
    if best<min_share*tot: return 0.0
    rot=-th if th<=45 else 90-th
    if abs(rot)<0.02: return 0.0
    # keep the longer plan size along X after squaring
    t=solid.rotate(Axis.Z,rot); bb=t.bounding_box()
    if bb.size.Y>bb.size.X*1.05: rot+=90 if rot<=0 else -90
    return round(rot,3)

def make_part(spec,out_pdf,out_dxf=None,png_prefix=None):
    shp=import_step(spec['file'])
    sols=shp.solids()
    solid=sols[spec.get('solid_index',0)] if spec.get('single',True) else shp
    if spec.get('move_to_origin',False) or True:
        bb=solid.bounding_box(); off=Vector(-(bb.min.X+bb.max.X)/2,-(bb.min.Y+bb.max.Y)/2,-bb.min.Z)
        if 'offset' in spec: off=Vector(*spec['offset'])
        solid=solid.moved(Location(off))
    spec['_off']=off
    if 'rotate' not in spec and spec.get('auto_align',True):
        ang=auto_align_angle(solid)
        if ang:
            solid=solid.rotate(Axis.Z,ang); bb=solid.bounding_box()
            solid=solid.moved(Location(Vector(-(bb.min.X+bb.max.X)/2,-(bb.min.Y+bb.max.Y)/2,-bb.min.Z)))
            print(f"auto-align: {spec.get('pn')} rotated {ang:+.3f} deg about Z so its main faces and holes square to the views")
        spec['_auto_align']=ang
    if 'rotate' in spec:
        for ax,ang in spec['rotate']:
            solid=solid.rotate({'X':Axis.X,'Y':Axis.Y,'Z':Axis.Z}[ax],ang)
        bb=solid.bounding_box(); solid=solid.moved(Location(Vector(-(bb.min.X+bb.max.X)/2,-(bb.min.Y+bb.max.Y)/2,-bb.min.Z)))
    proc=spec['process']
    revrows,rev,revsrc=resolve_revlog(spec,spec['file'])   # model drives the letter; drawing must match
    rlr=revlog_rect(len(revrows))
    hidden=False  # RULE 2026-10-17: never show hidden lines; spec 'hidden' ignored
    bb=solid.bounding_box()
    W,D,H=bb.size.X,bb.size.Y,bb.size.Z
    names=spec.get('views',['front','top','right'])
    V={}
    for n in names:
        if n=='section':
            continue
        V[n]=View(solid,n,1.0,hidden=hidden and n in spec.get('hidden_views',['front','top','right']),name=n)
    sec=spec.get('section')
    if sec:
        V[sec['slot']]=section_view(solid,sec['slot'],sec['origin'],1.0,'section')
    V['iso']=View(solid,spec.get('iso','iso'),1.0)
    slot_right='right'
    Wf=V['front'].w; Hf=V['front'].h; Ht=V['top'].h; Wr=V[slot_right].w
    gx=spec.get('gx',42); gy=spec.get('gy',36)
    areaW=spec.get('areaW',280); areaH=spec.get('areaH',178)   # 280: keeps views left of the rev log
    smax=min((areaW-gx-30)/(Wf+Wr),(areaH-gy-22)/(Hf+Ht))
    s=spec.get('scale') or pick_scale(smax)
    for v in V.values(): v.scale=s; v.w=(v.umax-v.umin)*s; v.h=(v.vmax-v.vmin)*s
    # placement
    totW=Wf*s+gx+Wr*s; totH=Hf*s+gy+Ht*s
    x0=22+(areaW-totW)/2+8; y0=spec.get('area_y0',86)+(areaH-totH)/2
    fx=x0+Wf*s/2; fy=y0+Hf*s/2
    V['front'].place(fx,fy)
    V['top'].place(fx,y0+Hf*s+gy+Ht*s/2)
    V[slot_right].place(x0+Wf*s+gx+Wr*s/2,fy)
    # iso in top-right box
    iso=V['iso']; isb=(318,150,418,min(262,rlr[1]-6))   # below the rev log
    isc=min(s*2,(isb[2]-isb[0])/(iso.umax-iso.umin),(isb[3]-isb[1]-10)/(iso.vmax-iso.vmin))
    isc=max([q for q in [3,2,1.5,1.25,1,0.8,0.75,0.6,0.5,0.4,0.3,0.25,0.2,0.15,0.1] if q<=isc+1e-9] or [0.1]); iso.scale=isc; iso.w=(iso.umax-iso.umin)*isc; iso.h=(iso.vmax-iso.vmin)*isc
    iso.place((isb[0]+isb[2])/2,(isb[1]+isb[3])/2+4)
    sh=Sheet(); occ=Occ(); occ.rects=sh.rects
    for k,v in V.items(): occ.add(v.bbox())
    occ.add(rlr)
    labels={'front':'FRONT','top':'TOP','right':'RIGHT'}
    if sec: labels[sec['slot']]=f"SECTION {sec['label']}"
    secslot=sec['slot'] if sec else None
    for k,v in V.items():
        if k=='iso': v.draw(sh); sh.txt(v.cx,v.cy-v.h/2-4,f"TRIMETRIC VIEW  (SCALE {scale_str(isc)})",h=2.8,va='top',bold=True); continue
        v.lab_off=spec.get('lab_off',{}).get(k,22 if k=='front' else 8)
        v.draw(sh,None)
    # section cutting line on top view
    if sec:
        tv=V['top']; o=np.array(sec['origin'],float); c,r,u=basis(*VIEWDIR[sec['slot']])
        if abs(c[0])>0.9:
            a=tv.P(o+[0,-D/2-6,0]); b=tv.P(o+[0,D/2+6,0]); a[0]=b[0]=tv.P(o)[0]
            a[1]=tv.bbox()[1]-6; b[1]=tv.bbox()[3]+6
        else:
            a=tv.P(o); b=a.copy(); a[0]=tv.bbox()[0]-6; b[0]=tv.bbox()[2]+6; a[1]=b[1]=tv.P(o)[1]
        sh.line(a,b,'cut')
        dirp=-np.array([c@tv.r,c@tv.u]); dirp/=np.linalg.norm(dirp)
        for p in (a,b):
            sh.line(p,p+dirp*8,'thin'); sh.arrow(p+dirp*8,p,L=3.5,W=1.4)
            sh.txt(*(p+dirp*12),sec['label'][0],h=4.5,bold=True)
    dims=[]
    tiers=defaultdict(int)
    def side_pos(view,side,tier=None):
        x0,y0,x1,y1=view.bbox()
        key=(id(view),side)
        if tier is None: tiers[key]+=1; tier=tiers[key]
        else: tiers[key]=max(tiers[key],tier)
        d=9+8*(tier-1)
        return {'below':y0-d,'above':y1+d,'left':x0-d,'right':x1+d}[side]
    paren=lambda t:(f"({t})" if proc=='printed' or proc=='purchased' else t)
    # overall dims
    if spec.get('overall',True):
        fv=V['front']; x0_,y0_,x1_,y1_=fv.bbox()
        dim_lin(sh,(x0_,y0_),(x1_,y0_),'h',side_pos(fv,'below'),paren(fmt(W,2)))
        dim_lin(sh,(x0_,y0_),(x0_,y1_),'v',side_pos(fv,'left'),paren(fmt(H,2)))
        rv=V.get('right')
        x0_,y0_,x1_,y1_=rv.bbox()
        dim_lin(sh,(x0_,y0_),(x1_,y0_),'h',side_pos(rv,'below'),paren(fmt(D,2)))
    # manual dims
    for d in spec.get('dims',[]):
        kind=d[0]
        if kind=='lin':
            _,vn,p1,p2,orient,side=d[:6]; o=d[6] if len(d)>6 else {}
            v=V[vn]; a=v.P(p1); b=v.P(p2)
            t=o.get('text') or fmt(lin_val(v,p1,p2,orient),2)
            if proc!='machined' and not o.get('text'): t=f"({t})"
            dim_lin(sh,a,b,orient,side_pos(v,side,o.get('tier')),t+o.get('suffix',''))
        elif kind=='note':
            _,vn,p,text,dx,dy=d; v=V[vn]; tip=v.P(p)
            leader(sh,tip,tip+np.array([dx,dy]),text)
        elif kind=='text':
            _,x,y,text=d[:4]; sh.txt(x,y,text,h=d[4] if len(d)>4 else TH,ha='left',va='top')
    # holes
    groups,rgroups=hole_callouts(solid,proc,spec)
    ordpts=defaultdict(list); pending=[]; marked=defaultdict(list)
    callout_n=0
    gl=sorted(groups.items(),key=lambda kv:(kv[0][0],-kv[1][0]['r']))
    if proc!='machined':
        gl=[g for g in gl if g[1][0]['r']*2>=spec.get('min_hole',2.5)]
        gl=sorted(gl,key=lambda kv:-len(kv[1]))[:spec.get('max_hole_groups',4)]
    for (ax,txt),inst in gl:
        vn=VIEW_FOR_AXIS[ax]
        if spec.get('hole_view',{}).get(ax): vn=spec['hole_view'][ax]
        if vn not in V: continue
        v=V[vn]
        for i in inst:
            centermark(sh,v.P(i['c']),i['rmax']*v.scale); marked[vn].append(v.P(i['c']))
            ordpts[vn].append(i['c'])
        # choose instance farthest from view center toward right/up
        cpg=np.array([v.cx,v.cy])
        pick=max(inst,key=lambda i:(v.P(i['c'])-cpg)@np.array([1,0.6])+0.001*np.linalg.norm(v.P(i['c'])-cpg))
        pc=v.P(pick['c']); rr=pick['rmax']*v.scale
        dirv=pc-cpg; 
        if np.linalg.norm(dirv)<1e-6: dirv=np.array([1,1.])
        dirv=dirv/np.linalg.norm(dirv)
        ang=math.atan2(dirv[1],dirv[0]); ang=math.radians(45 if dirv[0]>=0 else 135) if abs(dirv[1])<0.95 else ang
        tip=pc+rr*np.array([math.cos(ang),math.sin(ang)])
        n=len(inst); t=txt+(f"  ({n}X)" if n>1 else '')
        import re
        if n>1 and re.match(r'^\d+X ',txt): t=txt
        elif n>1:
            first,rest=t.split('\n')[0],t.split('\n')[1:]
            t='\n'.join([f"{n}X "+first.replace(f"  ({n}X)",'')]+[l.replace(f"  ({n}X)",'') for l in rest])
        if proc!='machined': t=t
        right = dirv[0]>=0
        pending.append((v,tip,t,right,dirv))
    # center marks for every visible hole / arc the feature finder missed (exact B-rep circles, any part orientation)
    if spec.get('center_marks',True):
        for vn,v in V.items():
            if vn=='iso' or vn==secslot: continue
            for pc,rp,kind in circle_marks(solid,v,spec.get('arc_mark_min_sweep',150.0)):
                if any(np.linalg.norm(pc-q)<0.5 for q in marked[vn]): continue
                centermark(sh,pc,rp,arc=(kind=='arc')); marked[vn].append(pc)
    # ordinate hole locations
    if spec.get('ordinates',proc=='machined'):
        for vn,pts in ordpts.items():
            v=V[vn]; x0_,y0_,x1_,y1_=v.bbox()
            uvs=np.array([v.uv(p) for p in pts]); 
            ux=sorted(set(np.round(uvs[:,0],2))); uy=sorted(set(np.round(uvs[:,1],2)))
            datum=np.array([v.umin,v.vmin])
            if spec.get('datum_center'): datum=np.array([(v.umin+v.umax)/2,(v.vmin+v.vmax)/2])
            ax_side=spec.get('ord_x_side',{}).get(vn,'above'); ay_side=spec.get('ord_y_side',{}).get(vn,'left')
            atx=side_pos(v,ax_side); aty=side_pos(v,ay_side)
            # x ordinates
            P=[];vals=[]
            for x in [datum[0]]+ux:
                ys=[q for q in uvs if abs(q[0]-x)<0.01]
                yref=(max(q[1] for q in ys) if ax_side=='above' else min(q[1] for q in ys)) if ys else (v.vmax if ax_side=='above' else v.vmin)
                if not ys: yref=v.vmax if ax_side=='above' else v.vmin
                P.append(v.uv2pg([x,yref])); vals.append(x-datum[0])
            # dedupe
            seen=set();PP=[];VV=[]
            for p,val in zip(P,vals):
                if round(val,2) in seen: continue
                seen.add(round(val,2)); PP.append(p); VV.append(val)
            ordinate(sh,PP,'x',None,atx,VV)
            occ.add((x0_,min(y1_,atx-4),x1_,atx+16) if ax_side=='above' else (x0_,atx-16,x1_,max(y0_,atx+4)))
            P=[];vals=[]
            for y in [datum[1]]+uy:
                xs=[q for q in uvs if abs(q[1]-y)<0.01]
                xref=(min(q[0] for q in xs) if ay_side=='left' else max(q[0] for q in xs)) if xs else (v.umin if ay_side=='left' else v.umax)
                P.append(v.uv2pg([xref,y])); vals.append(y-datum[1])
            seen=set();PP=[];VV=[]
            for p,val in zip(P,vals):
                if round(val,2) in seen: continue
                seen.add(round(val,2)); PP.append(p); VV.append(val)
            ordinate(sh,PP,'y',None,aty,VV)
            occ.add((aty-14,y0_,min(x0_,aty+3),y1_) if ay_side=='left' else (max(x1_,aty-3),y0_,aty+14,y1_))
    # radii
    for (ax,rr),inst in sorted(rgroups.items()):
        if spec.get('radii') is False or proc!='machined': break
        if rr in spec.get('skip_radii',[]): continue
        vn=VIEW_FOR_AXIS[ax]
        if vn not in V: continue
        v=V[vn]; cpg=np.array([v.cx,v.cy])
        # only those that appear as arcs on the visible outline near; pick the one farthest from center
        def arcpt(i):
            b=i['base']+i['t']*feat.AX[ax]
            pc=v.P(b); dd=pc-cpg; dd=dd/ (np.linalg.norm(dd)+1e-9)
            return pc+dd*rr*v.scale, pc
        pick=max(inst,key=lambda i:(arcpt(i)[0]-cpg)@np.array([-1,1.0]))
        def vis_tip(i):
            """leader tip on a visible part of the arc, or None if the arc isn't drawn in this view."""
            t0,pc0=arcpt(i)
            if on_visible(v,t0): return t0
            dd=t0-pc0; a0=math.atan2(dd[1],dd[0])
            for k in sorted(range(36),key=lambda k:min(k,36-k)):
                a=a0+k*math.pi/18; q=pc0+rr*v.scale*np.array([math.cos(a),math.sin(a)])
                if on_visible(v,q): return q
            return None
        cand=[(i,vis_tip(i)) for i in inst]; cand=[(i,t) for i,t in cand if t is not None]
        if not cand: continue              # radius not visible in this view: no leader to a hidden feature
        pick,tip=max(cand,key=lambda it:(it[1]-cpg)@np.array([-1,1.0]))
        pc=arcpt(pick)[1]
        ovt=spec.get('radius_text',{}).get(rr)
        if ovt=='skip': continue
        n=len(inst); t=(ovt or f"R{fmt(rr,2)}")+(f" ({n}X)" if n>1 else '')
        if proc!='machined': t=f"({t})" if False else t
        x0_,y0_,x1_,y1_=v.bbox()
        right=tip[0]>v.cx
        pending.append((v,tip,t,right,None))
    # place leaders
    place_leaders(sh,occ,pending)
    # view labels
    for k,v in V.items():
        if k=='iso': continue
        lbl=labels.get(k,k.upper())
        if k==secslot or spec.get('label_views'):
            sh.txt(v.cx,side_pos(v,'below',tiers[(id(v),'below')]+1)+2,lbl,h=3.5,bold=True,va='top')
    info=dict(title=spec['title'],pn=spec['pn'],material=spec['material'],scale=scale_str(s),source=spec.get('source',''),rev=rev or '-',revlog=revrows)
    frame(sh,info,1,1)
    nb=overlap_warnings(sh,rlr)
    if nb: print(f"WARNING: {nb} view/dim lines run into the rev log table on {spec['pn']}")
    for k,v in V.items():
        st=getattr(v,'stats',{})
        if st.get('planar_facets',0)>=50:
            print(f"WARNING: {spec['pn']} {k} view: {st['planar_facets']} facet edges between near-coplanar flat faces - "
                  "the model is polygonised (faceted outline); rebuild those curves as true arcs. Facet lines were filtered from the view.")
    spec['_revlog_src']=revsrc; spec['_view_stats']={k:getattr(v,'stats',{}) for k,v in V.items()}
    notes=list(spec.get('notes',[]))
    notes_block(sh,14,72,notes,h=2.3,width=128)
    for dt in spec.get('details',[]):
        draw_detail(sh,V[dt['parent']],dt)
    render([sh],out_pdf,out_dxf,png_prefix)
    return s

def _detail_body(sh,pv,dt,px,py):
    c=np.asarray(dt['center'],float); R=dt['radius']; sc=dt['scale']; lab=dt['label']
    cu=pv.uv(c); circ=SPoint(cu).buffer(R,64)
    T=lambda q:(px+(q[0]-cu[0])*sc,py+(q[1]-cu[1])*sc)
    for loops in pv.hatches:
        try: poly=SPoly(loops[0],loops[1:]).buffer(0).intersection(circ)
        except Exception: continue
        polys=[poly] if poly.geom_type=='Polygon' else [g for g in getattr(poly,'geoms',[]) if g.geom_type=='Polygon']
        for g in polys:
            if g.is_empty: continue
            sh.hatch([[T(q) for q in g.exterior.coords]]+[[T(q) for q in i.coords] for i in g.interiors])
    for p in pv.vis:
        if len(p)<2: continue
        ls=SLine(p).intersection(circ)
        geoms=[ls] if ls.geom_type=='LineString' else list(getattr(ls,'geoms',[]))
        for g in geoms:
            if g.geom_type=='LineString' and len(g.coords)>1: sh.pl([T(q) for q in g.coords],'vis')
    sh.circle((px,py),R*sc,'thin')
    sh.txt(px,py-R*sc-3,f"DETAIL {lab}\nSCALE {scale_str(sc)}",h=3.5,bold=True,va='top')
    for d in dt.get('dims',[]):
        _,p1,p2,orient,off,text=d
        a=np.array(T(pv.uv(p1))); b=np.array(T(pv.uv(p2)))
        at=(min(a[1],b[1])-off if off<0 else max(a[1],b[1])+off) if orient=='h' else (min(a[0],b[0])-abs(off) if off<0 else max(a[0],b[0])+off)
        dim_lin(sh,a,b,orient,at,text)

def _obstacles(sh):
    from shapely.geometry import box as sbox
    G=[]
    for it in sh.items:
        if it[0]=='pl' and len(it[1])>1:
            p=it[1]; G.append(SLine(np.vstack([p,p[:1]]) if it[3] else p))
        elif it[0]=='ha':
            try: G.append(SPoly(it[1][0]).buffer(0))
            except Exception: pass
        elif it[0]=='tri': G.append(SPoly(it[1]))
    for r in sh.rects: G.append(sbox(*r))
    return G

def draw_detail(sh,pv,dt):
    from shapely.strtree import STRtree
    from shapely.geometry import box as sbox
    from dwg import PW,PH
    dt=dict(dt); R0=dt['radius']; Rd0=R0*dt['scale']
    dt['radius']=max(R0,dt.get('min_pg_r',5.0)/pv.scale)
    if dt['radius']*dt['scale']>max(Rd0,22):
        tgt=max(Rd0,22)/dt['radius']; dt['scale']=max([x for x in STD_SCALES if x<=tgt] or [min(STD_SCALES)])
    R=dt['radius']; sc=dt['scale']; lab=dt['label']
    cu=pv.uv(np.asarray(dt['center'],float)); cpg=np.asarray(pv.uv2pg(cu),float); Rp=R*pv.scale
    G=_obstacles(sh); tree=STRtree(G)
    def hit(g,buf=0.0):
        gg=g.buffer(buf) if buf else g
        return any(G[k].intersects(gg) for k in tree.query(gg))
    tmp=Sheet(); _detail_body(tmp,pv,dt,0.0,0.0)
    P=np.vstack([it[1] for it in tmp.items if it[0]=='pl']+[np.array([[r[0],r[1]],[r[2],r[3]]]) for r in tmp.rects])
    fx0,fy0=P.min(0); fx1,fy1=P.max(0); Rd=R*sc
    FP=[]
    for px in np.arange(16,PW-16,3.0):
        for py in np.arange(16,PH-16,3.0):
            fp=(px+fx0-2,py+fy0-2,px+fx1+2,py+fy1+2)
            if fp[0]<13 or fp[1]<13 or fp[2]>PW-13 or fp[3]>PH-13: continue
            if SPoint(cpg).buffer(Rp+2).intersects(sbox(*fp)): continue
            if not hit(sbox(*fp)): FP.append(np.array([px,py]))
    # first-leg options: straight from circle (via=None) or a dogleg through a clear point
    legs=[]
    for ang in np.linspace(0,2*np.pi,48,endpoint=False):
        u=np.array([np.cos(ang),np.sin(ang)]); a=cpg+u*(Rp+0.3)
        for L in np.arange(6,90,3):
            if hit(SLine([cpg+u*(Rp+1.2),a+u*L]),1.5): break
            legs.append((a,a+u*L,L))
    best=None
    for c in FP:
        d=c-cpg; Ld=np.linalg.norm(d); u=d/Ld
        if Ld>Rp+Rd+8:
            a=cpg+u*(Rp+0.3); b=c-u*(Rd+0.3)
            if (best is None or Ld<best[0]) and not hit(SLine([cpg+u*(Rp+1.2),c-u*(Rd+1.0)]),1.5):
                best=(Ld,c,[a,b])
    if best is None:
        for c in FP:
            for a,v,L in legs:
                d=c-v; Ld=np.linalg.norm(d)
                if Ld<Rd+6: continue
                cost=L+Ld+15
                if best is not None and cost>=best[0]: continue
                u=d/Ld
                if hit(SLine([v,c-u*(Rd+1.0)]),1.5): continue
                best=(cost,c,[a,v,c-u*(Rd+0.3)])
    if best is None:
        # 3-segment fallback: circle -> v1 -> v2 (axis-aligned) -> detail
        legs2=[]
        for a,v,L in legs[::2]:
            for w in ([1,0],[-1,0],[0,1],[0,-1]):
                w=np.array(w,float)
                for L2 in np.arange(6,150,6):
                    if hit(SLine([v,v+w*L2]),1.5): break
                    legs2.append((a,v,v+w*L2,L+L2))
        FPs=sorted(FP,key=lambda c:np.linalg.norm(c-cpg))[:600]
        for c in FPs:
            for a,v,v2,L in legs2:
                d=c-v2; Ld=np.linalg.norm(d)
                if Ld<Rd+6: continue
                cost=L+Ld+30
                if best is not None and cost>=best[0]: continue
                u=d/Ld
                if hit(SLine([v2,c-u*(Rd+1.0)]),1.5): continue
                best=(cost,c,[a,v,v2,c-u*(Rd+0.3)])
    if best is None:
        raise RuntimeError(f"no clear spot for detail {lab}")
    _,c,path=best; px,py=c; u=(path[1]-path[0]); u=u/np.linalg.norm(u)
    sh.circle(cpg,Rp,'detail')
    sh.pl(path,'thin')
    # label on the parent circle, away from leader and geometry
    G2=_obstacles(sh); tree2=STRtree(G2); bestl=None
    for ang in np.linspace(0,2*np.pi,24,endpoint=False):
        v=np.array([np.cos(ang),np.sin(ang)])
        if v@u>0.5: continue
        q=cpg+v*(Rp+3.2)
        bx=sbox(q[0]-2.2,q[1]-2.7,q[0]+2.2,q[1]+2.7)
        n=sum(G2[k].intersects(bx) for k in tree2.query(bx))
        sc_=n*100-(v@np.array([0.6,0.8]))
        if bestl is None or sc_<bestl[0]: bestl=(sc_,q)
    sh.txt(*bestl[1],lab,h=4.5,bold=True)
    _detail_body(sh,pv,dt,px,py)
    dt['_placed']=(px,py)
