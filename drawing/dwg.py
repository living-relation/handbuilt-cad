"""SteveCAD 2D drawing engine: HLR views (build123d/OCCT) -> 11x17 ANSI B sheets -> PDF (+DXF)."""
import math, datetime, os, numpy as np
from build123d import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import ezdxf
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
_FONTS=[x for x in os.environ.get('STEVECAD_FONTS','').split(os.pathsep) if x]+['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/libreoffice/opens___.ttf']
for f in _FONTS:
    if not os.path.exists(f): continue  # missing fonts fall back to matplotlib's bundled DejaVu
    try: font_manager.fontManager.addfont(f)
    except Exception: pass
plt.rcParams['font.family']=['DejaVu Sans','DejaVu Sans Mono','OpenSymbol']
plt.rcParams['lines.scale_dashes']=False
plt.rcParams['hatch.linewidth']=0.35
plt.rcParams['pdf.fonttype']=42
PW,PH=431.8,279.4
MM2PT=72/25.4
STY={'vis':(0.50,None),'hid':(0.25,(3.0,1.5)),'ctr':(0.18,(8,1.5,1.5,1.5)),'thin':(0.18,None),
     'dim':(0.18,None),'border':(0.7,None),'tb':(0.35,None),'phantom':(0.25,(8,1.5,1.5,1.5,1.5,1.5)),
     'expl':(0.25,(2.0,1.5)),'cut':(0.6,(10,2,2,2)),'detail':(0.5,(7,1.8))}
DXF_LAYER={'vis':('VISIBLE','CONTINUOUS',7),'hid':('HIDDEN','HIDDEN',8),'ctr':('CENTER','CENTER',1),'thin':('THIN','CONTINUOUS',7),
     'dim':('DIM','CONTINUOUS',3),'border':('BORDER','CONTINUOUS',7),'tb':('TITLE','CONTINUOUS',7),'phantom':('PHANTOM','PHANTOM',6),
     'expl':('EXPLODE','DASHED',6),'cut':('CUTPLANE','DASHDOT',1),'detail':('DETAIL','DASHED',5)}
TH=3.0  # standard text height mm

class Sheet:
    def __init__(s): s.items=[]; s.rects=[]
    def pl(s,pts,sty='thin',closed=False): s.items.append(('pl',np.asarray(pts,float),sty,closed))
    def line(s,a,b,sty='thin'): s.pl([a,b],sty)
    def circle(s,c,r,sty='thin',n=72):
        t=np.linspace(0,2*np.pi,n+1); s.pl(np.c_[c[0]+r*np.cos(t),c[1]+r*np.sin(t)],sty)
    def txt(s,x,y,t,h=TH,ha='center',va='center',rot=0,bold=False,bg=False,layer='TEXT'):
        s.items.append(('tx',x,y,str(t),h,ha,va,rot,bold,bg,layer))
        t=str(t); w=_tw(t,h); n=t.count('\n')+1; H=n*h*1.6
        if rot==90: w,H=H,w
        x0={'left':x,'right':x-w,'center':x-w/2}[ha] if rot!=90 else ({'bottom':x-w,'top':x,'center':x-w/2}[va] if False else x-w/2)
        y0={'bottom':y,'top':y-H,'center':y-H/2}[va] if rot!=90 else ({'left':y,'right':y-H,'center':y-H/2}[ha] if False else (y if va=='bottom' else y-H))
        s.rects.append((x0,y0,x0+w,y0+H))
    def tri(s,pts): s.items.append(('tri',np.asarray(pts,float)))
    def hatch(s,loops,angle=45): s.items.append(('ha',[np.asarray(l,float) for l in loops],angle))
    def wipe(s,x0,y0,x1,y1): s.items.append(('wipe',x0,y0,x1,y1))
    def arrow(s,tip,frm,L=3.0,W=1.0):
        tip=np.asarray(tip,float); d=tip-np.asarray(frm,float); n=np.linalg.norm(d)
        if n<1e-9: return
        d/=n; p=np.array([-d[1],d[0]]); b=tip-d*L
        s.tri([tip,b+p*W/2,b-p*W/2])

def _tw(t,h):  # approx text width
    return max(len(l) for l in t.split('\n'))*h*0.82

def render(sheets,pdf_path,dxf_path=None,png_prefix=None):
    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(pdf_path) as pdf:
        for i,sh in enumerate(sheets):
            fig=plt.figure(figsize=(17,11)); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,PW); ax.set_ylim(0,PH); ax.axis('off')
            for it in sh.items:
                k=it[0]
                if k=='pl':
                    _,p,sty,cl=it; lw,da=STY[sty]
                    if cl: p=np.vstack([p,p[:1]])
                    ln,=ax.plot(p[:,0],p[:,1],color='k',lw=lw*MM2PT,solid_capstyle='round',solid_joinstyle='round',zorder=2 if sty=='vis' else 3)
                    if da: ln.set_dashes([d*MM2PT for d in da])
                elif k=='tri':
                    ax.fill(it[1][:,0],it[1][:,1],color='k',lw=0,zorder=4)
                elif k=='wipe':
                    _,x0,y0,x1,y1=it; ax.fill([x0,x1,x1,x0],[y0,y0,y1,y1],color='w',lw=0,zorder=3.5)
                elif k=='ha':
                    verts=[];codes=[]
                    for l in it[1]:
                        verts+=list(l)+[l[0]]; codes+=[Path.MOVETO]+[Path.LINETO]*(len(l)-1)+[Path.CLOSEPOLY]
                    ax.add_patch(PathPatch(Path(verts,codes),facecolor='none',edgecolor='k',lw=0,hatch='////',zorder=1))
                elif k=='tx':
                    _,x,y,t,h,ha,va,rot,b,bg,_l=it
                    t=t.replace('⌴','⊔').replace('⌵','∨')
                    kw=dict(bbox=dict(fc='w',ec='none',pad=0.6)) if bg else {}
                    ax.text(x,y,t,fontsize=h*MM2PT/0.72,ha=ha,va=va,rotation=rot,fontweight='bold' if b else 'normal',zorder=5,linespacing=1.25,**kw)
            pdf.savefig(fig)
            if png_prefix: fig.savefig(f"{png_prefix}_sh{i+1}.png",dpi=110)
            plt.close(fig)
    if dxf_path:
        doc=ezdxf.new('R2010',setup=True); doc.units=ezdxf.units.MM
        for sty,(nm,lt,col) in DXF_LAYER.items():
            if nm not in doc.layers: doc.layers.add(nm,color=col,linetype=lt if lt in doc.linetypes else 'CONTINUOUS')
        doc.layers.add('TEXT',color=7); doc.layers.add('HATCH',color=8)
        msp=doc.modelspace()
        for i,sh in enumerate(sheets):
            ox=i*(PW+50)
            for it in sh.items:
                k=it[0]
                if k=='pl':
                    _,p,sty,cl=it; msp.add_lwpolyline([(x+ox,y) for x,y in p],close=cl,dxfattribs={'layer':DXF_LAYER[sty][0]})
                elif k=='tri':
                    p=it[1]; msp.add_solid([(x+ox,y) for x,y in p],dxfattribs={'layer':'DIM'})
                elif k=='ha':
                    h=msp.add_hatch(dxfattribs={'layer':'HATCH'}); h.set_pattern_fill('ANSI31',scale=0.6)
                    for l in it[1]: h.paths.add_polyline_path([(x+ox,y) for x,y in l],is_closed=True)
                elif k=='tx':
                    _,x,y,t,hh,ha,va,rot,b,bg,_l=it
                    t=t.replace('⌀','%%c').replace('°','%%d').replace('±','%%p').replace('↧',' DP ').replace('⌴','CBORE ').replace('⌵','CSK ')
                    al={('left','center'):'MIDDLE_LEFT',('center','center'):'MIDDLE_CENTER',('right','center'):'MIDDLE_RIGHT',
                        ('left','bottom'):'BOTTOM_LEFT',('center','bottom'):'BOTTOM_CENTER',('right','bottom'):'BOTTOM_RIGHT',
                        ('left','top'):'TOP_LEFT',('center','top'):'TOP_CENTER',('right','top'):'TOP_RIGHT'}.get((ha,va),'MIDDLE_LEFT')
                    lines=t.split('\n'); n=len(lines)
                    for j,ln in enumerate(lines):
                        dy=(n-1-j)*hh*1.6 if va=='bottom' else (-j*hh*1.6 if va=='top' else ((n-1)/2-j)*hh*1.6)
                        e=msp.add_text(ln,dxfattribs={'height':hh*0.85,'layer':'TEXT','rotation':rot})
                        e.set_placement((x+ox-math.sin(math.radians(rot))*dy,y+math.cos(math.radians(rot))*dy),align=ezdxf.enums.TextEntityAlignment[al])
        doc.saveas(dxf_path)

# ---------------- projection ----------------
def basis(cam,up=(0,0,1)):
    c=np.asarray(cam,float); c/=np.linalg.norm(c); f=-c
    r=np.cross(f,up); r/=np.linalg.norm(r); u=np.cross(r,f)
    return c,r,u
VIEWDIR={'front':((0,-1,0),(0,0,1)),'top':((0,0,1),(0,1,0)),'right':((1,0,0),(0,0,1)),'left':((-1,0,0),(0,0,1)),
         'back':((0,1,0),(0,0,1)),'bottom':((0,0,-1),(0,-1,0)),'iso':((1,-1.55,1.15),(0,0,1)),'iso2':((-1,-1.55,1.15),(0,0,1))}

def edge_pts(e,defl=0.02):
    try:
        a=BRepAdaptor_Curve(e.wrapped); g=GCPnts_QuasiUniformDeflection(a,defl)
        if g.IsDone() and g.NbPoints()>1:
            return np.array([[g.Value(i).X(),g.Value(i).Y()] for i in range(1,g.NbPoints()+1)])
    except Exception: pass
    return np.array([[v.X,v.Y] for v in (e.position_at(t) for t in np.linspace(0,1,12))])

def project(shape,view,hidden=False,defl=0.02):
    cam,up=VIEWDIR[view] if isinstance(view,str) else view
    c,r,u=basis(cam,up)
    v,h=shape.project_to_viewport(tuple(c*5000),tuple(u),(0,0,0))
    vis=[edge_pts(e,defl) for e in v]
    hid=[edge_pts(e,defl) for e in h] if hidden else []
    return vis,hid,(c,r,u)

class View:
    """A placed view. world->uv via basis; uv->page via center & scale."""
    def __init__(s,shape,view,scale,hidden=False,name='',defl=None,section=None,polys=None):
        s.view=view; s.scale=scale; s.name=name; s.hatches=[]
        if polys is not None:  # precomputed
            s.vis,s.hid,(s.c,s.r,s.u)=polys
        else:
            s.vis,s.hid,(s.c,s.r,s.u)=project(shape,view,hidden,defl or 0.01/max(scale,0.2))
        allp=np.vstack(s.vis) if s.vis else np.zeros((1,2))
        s.umin,s.vmin=allp.min(0); s.umax,s.vmax=allp.max(0)
        s.w=(s.umax-s.umin)*scale; s.h=(s.vmax-s.vmin)*scale
        s.cx=s.cy=0
    def place(s,cx,cy): s.cx,s.cy=cx,cy; return s
    def uv(s,p): p=np.asarray(p,float); return np.array([p@s.r,p@s.u])
    def P(s,p):  # world 3D -> page
        q=s.uv(p); return s.uv2pg(q)
    def uv2pg(s,q): return np.array([s.cx+(q[0]-(s.umin+s.umax)/2)*s.scale, s.cy+(q[1]-(s.vmin+s.vmax)/2)*s.scale])
    def bbox(s): return (s.cx-s.w/2,s.cy-s.h/2,s.cx+s.w/2,s.cy+s.h/2)
    def draw(s,sh,label=None,label_scale=True):
        for p in s.hid: sh.pl([s.uv2pg(q) for q in p],'hid')
        for loops in s.hatches: sh.hatch([[s.uv2pg(q) for q in l] for l in loops])
        for p in s.vis: sh.pl([s.uv2pg(q) for q in p],'vis')
        if label:
            x0,y0,x1,y1=s.bbox()
            sh.txt(s.cx,y0-s.lab_off if hasattr(s,'lab_off') else y0-9,label+(f"\nSCALE {scale_str(s.scale)}" if label_scale else ''),h=3.5,va='top',bold=True)

def scale_str(s):
    if s>=1: return f"{s:g}:1"
    return f"1:{round(1/s,2):g}"
STD_SCALES=[10,8,5,4,3,2,1.5,1,2/3,0.5,0.4,1/3,0.25,0.2,0.1]
def pick_scale(maxs):
    for s in STD_SCALES:
        if s<=maxs+1e-9: return s
    return STD_SCALES[-1]

def section_view(solid,view,origin,scale,name):
    """cut solid with plane through origin normal to view cam dir; keep far side; hatch cut faces."""
    cam,up=VIEWDIR[view]; c,r,u=basis(cam,up)
    pl=Plane(origin=tuple(origin),z_dir=tuple(c))
    half=solid.split(pl,keep=Keep.BOTTOM)
    v=View(half,view,scale,name=name)
    o=np.asarray(origin,float); loops_all=[]
    for f in half.faces():
        if f.geom_type!=GeomType.PLANE: continue
        n=np.array(tuple(f.normal_at())); ctr=np.array(tuple(f.center()))
        if abs(abs(n@c)-1)<1e-4 and abs((ctr-o)@c)<1e-3:
            from shapely.geometry import Polygon as SP
            from shapely.ops import unary_union
            vs,tris=f.tessellate(0.02,0.2)
            uvp=[v.uv(np.array(tuple(p))) for p in vs]
            polys=[SP([uvp[a],uvp[b],uvp[c]]).buffer(1e-4) for a,b,c in tris]
            U=unary_union(polys).buffer(-1e-4)
            geoms=[U] if U.geom_type=='Polygon' else list(U.geoms)
            loops=[]
            for g in geoms:
                if g.is_empty: continue
                loops_all.append([np.array(g.exterior.coords)]+[np.array(i.coords) for i in g.interiors])
            continue
            loops_all.append(loops)
    v.hatches=loops_all
    return v

# ---------------- dimensions ----------------
def fmt(x,dec=1):
    s=f"{x:.{dec}f}"
    if dec>0: s=s.rstrip('0').rstrip('.') if '.' in s else s
    return s

def dim_lin(sh,p1,p2,orient,at,text,ext_gap=1.2,ext_over=2.0,h=TH):
    """p1,p2 page pts; orient 'h' measures x-dist with dim line at y=at; 'v' measures y-dist with dim line at x=at"""
    p1=np.asarray(p1,float); p2=np.asarray(p2,float)
    if orient=='h':
        a=np.array([p1[0],at]); b=np.array([p2[0],at])
        for p in (p1,p2):
            sgn=1 if at>p[1] else -1
            sh.line((p[0],p[1]+sgn*ext_gap),(p[0],at+sgn*ext_over),'dim')
    else:
        a=np.array([at,p1[1]]); b=np.array([at,p2[1]])
        for p in (p1,p2):
            sgn=1 if at>p[0] else -1
            sh.line((p[0]+sgn*ext_gap,p[1]),(at+sgn*ext_over,p[1]),'dim')
    L=np.linalg.norm(b-a); m=(a+b)/2; tw=_tw(text,h)
    sh.rects.append((min(a[0],b[0])-1,min(a[1],b[1])-1,max(a[0],b[0])+1,max(a[1],b[1])+1))
    inside = L>8.5
    if inside:
        sh.line(a,b,'dim'); sh.arrow(a,b); sh.arrow(b,a)
    else:
        d=(b-a)/max(L,1e-9)
        sh.line(a-d*7,b+d*7,'dim'); sh.arrow(a,a-d*3); sh.arrow(b,b+d*3)
    if orient=='h':
        if inside or True: sh.txt(m[0],m[1]+0.8,text,h=h,va='bottom')
    else:
        if L>tw*0+h*1.6+7:
            sh.txt(m[0],m[1],text,h=h,bg=True)
        else:
            sh.txt(m[0]+1.2,m[1]+L/2+5,text,h=h,ha='left',va='bottom')

def leader(sh,tip,txtpos,text,h=TH,dot=False,arrow=True):
    tip=np.asarray(tip,float); tp=np.asarray(txtpos,float)
    right = tp[0]>=tip[0]
    sh_end=tp+np.array([-3 if right else 3,0]) if False else tp
    knee=tp-np.array([4 if right else -4,0])
    sh.pl([tip,knee,tp],'dim')
    if arrow: sh.arrow(tip,knee)
    nl=text.count('\n')
    sh.txt(tp[0]+(1 if right else -1),tp[1],text,h=h,ha='left' if right else 'right',va='center')

def centermark(sh,c,r,ext=2.0):
    c=np.asarray(c,float); L=r+ext
    if r<1.2: L=2.5
    sh.line(c-[L,0],c+[L,0],'ctr'); sh.line(c-[0,L],c+[0,L],'ctr')

def ordinate(sh,pts,axis,base_pg,at,vals,h=2.8):
    """ordinate dims: pts page points, axis 'x' (vertical ext lines to y=at) or 'y'"""
    # base_pg: page coordinate of datum, vals: values
    order=np.argsort([p[0] if axis=='x' else p[1] for p in pts])
    last=-1e9
    for i in order:
        p=pts[i]; v=vals[i]
        if axis=='x':
            x=p[0]; pos=max(x,last+h*1.25); last=pos
            sgn=1 if at>p[1] else -1
            sh.pl([(x,p[1]+sgn*1.2),(x,at-sgn*3),(pos,at-sgn*0.5)],'dim')
            sh.txt(pos,at,fmt(v,2),h=h,rot=90,ha='center',va='bottom' if sgn>0 else 'top')
        else:
            y=p[1]; pos=max(y,last+h*1.25); last=pos
            sgn=1 if at>p[0] else -1
            sh.pl([(p[0]+sgn*1.2,y),(at-sgn*3,y),(at-sgn*0.5,pos)],'dim')
            sh.txt(at,pos,fmt(v,2),h=h,ha='left' if sgn>0 else 'right')

# ---------------- frame ----------------
def frame(sh,info,sheet_no,n_sheets,proj=True):
    m=10.0
    sh.pl([(m,m),(PW-m,m),(PW-m,PH-m),(m,PH-m)],'border',closed=True)
    sh.pl([(5,5),(PW-5,5),(PW-5,PH-5),(5,PH-5)],'thin',closed=True)
    # zones 8 x 4
    for i in range(1,8):
        x=m+i*(PW-2*m)/8; sh.line((x,5),(x,m),'thin'); sh.line((x,PH-5),(x,PH-m),'thin')
    for i in range(8):
        x=m+(i+.5)*(PW-2*m)/8; sh.txt(x,7.5,str(8-i),h=2.5); sh.txt(x,PH-7.5,str(8-i),h=2.5)
    for j in range(1,4):
        y=m+j*(PH-2*m)/4; sh.line((5,y),(m,y),'thin'); sh.line((PW-5,y),(PW-m,y),'thin')
    for j in range(4):
        y=m+(j+.5)*(PH-2*m)/4; L='ABCD'[j]; sh.txt(7.5,y,L,h=2.5); sh.txt(PW-7.5,y,L,h=2.5)
    # title block 178 x 52 at bottom right
    x1=PW-m; x0=x1-178; y0=m; y1=y0+52
    sh.pl([(x0,y0),(x1,y0),(x1,y1),(x0,y1)],'tb',closed=True)
    def box(a,b,c,d,label,val,vh=3.2,bold=False):
        sh.pl([(a,b),(c,b),(c,d),(a,d)],'thin',closed=True)
        sh.txt(a+1,d-1,label,h=1.8,ha='left',va='top')
        sh.txt((a+c)/2,(b+d)/2-1.2,val,h=vh,bold=bold)
    # rows
    box(x0,y1-10,x1,y1,'COMPANY / PROJECT',info.get('project','ST185 CELICA GT-FOUR  -  LINK ECU CONVERSION'),3.2,True)
    box(x0,y1-24,x1,y1-10,'TITLE',info['title'],4.6 if len(info['title'])<38 else 3.6,True)
    box(x0,y1-34,x0+90,y1-24,'PART / DWG NO.',info['pn'],3.2,True)
    box(x0+90,y1-34,x0+110,y1-24,'REV',info.get('rev','1'),3.6,True)
    box(x0+110,y1-34,x1,y1-24,'MATERIAL',info.get('material','-'),2.6 if len(info.get('material',''))>22 else 3.0)
    box(x0,y0+8,x0+30,y1-34,'SCALE',info.get('scale','-'),3.0)
    box(x0+30,y0+8,x0+52,y1-34,'UNITS','mm',3.0)
    box(x0+52,y0+8,x0+80,y1-34,'SIZE','B (11x17)',2.6)
    box(x0+80,y0+8,x0+108,y1-34,'SHEET',f"{sheet_no} OF {n_sheets}",3.0)
    box(x0+108,y0+8,x0+140,y1-34,'DATE',info.get('date',datetime.date.today().isoformat()),2.8)
    box(x0+140,y0+8,x1,y1-34,'DRAWN',"SteveCAD",3.0)
    box(x0,y0,x0+140,y0+8,'SOURCE',info.get('source',''),min(2.0,2.0*86/max(1,len(info.get('source','')))))
    # projection symbol (third angle)
    a,b=x0+140,y0
    sh.pl([(a,b),(x1,b),(x1,b+8),(a,b+8)],'thin',closed=True)
    cx,cy=a+11,b+4
    sh.pl([(cx-6,cy-2.2),(cx-1.5,cy-1.2),(cx-1.5,cy+1.2),(cx-6,cy+2.2)],'thin',closed=True)
    sh.line((cx-7,cy),(cx-0.5,cy),'ctr')
    sh.circle((cx+4,cy),2.2,'thin'); sh.circle((cx+4,cy),1.0,'thin')
    sh.txt(a+27,cy,"3RD ANGLE",h=1.8)
    # tolerance block left of title block
    tx0=x0-92; tx1=x0
    sh.pl([(tx0,y0),(tx1,y0),(tx1,y0+40),(tx0,y0+40)],'tb',closed=True)
    sh.txt(tx0+2,y0+38,"UNLESS OTHERWISE SPECIFIED:",h=2.2,ha='left',va='top',bold=True)
    tol=info.get('tol',"DIMENSIONS ARE IN MILLIMETERS\nTOLERANCES:\n  X     ±0.5      X.X  ±0.2\n  X.XX  ±0.05    ANGLES ±0.5°\nBREAK SHARP EDGES 0.2-0.4\nSURFACE FINISH Ra 3.2 µm\nINTERPRET PER ASME Y14.5-2018")
    sh.txt(tx0+2,y0+33.5,tol,h=2.2,ha='left',va='top')
    revs=info.get('revs')
    if revs:
        rh=4.0; ry1=y0+40+rh*(len(revs)+1); cols=[tx0,tx0+7,tx0+59,tx0+77,tx1]
        sh.pl([(tx0,y0+40),(tx1,y0+40),(tx1,ry1),(tx0,ry1)],'tb',closed=True)
        rows=[('REV','DESCRIPTION','DATE','BY')]+list(revs)
        for k,row in enumerate(rows):
            yt=ry1-k*rh
            if k: sh.line((tx0,yt),(tx1,yt),'thin')
            for c,(a,b) in enumerate(zip(cols[:-1],cols[1:])):
                if k==0 or c!=1: sh.txt((a+b)/2,yt-rh/2,row[c],h=1.8 if k==0 else 1.5,bold=(k==0))
                else: sh.txt(a+1,yt-rh/2,row[c],h=1.7,ha='left')
        for a in cols[1:-1]: sh.line((a,y0+40),(a,ry1),'thin')

def notes_block(sh,x,y,notes,h=2.6,title='NOTES:',width=136):
    import textwrap
    sh.txt(x,y,title,h=3.0,ha='left',va='top',bold=True)
    yy=y-5
    nc=int(width/(h*0.84))
    notes=[textwrap.fill(n.replace('\n',' '),nc,subsequent_indent='     ') for n in notes]
    for i,n in enumerate(notes,1):
        sh.txt(x,yy,f"{i}.  {n}",h=h,ha='left',va='top')
        yy-=h*1.6*(n.count('\n')+1)+1.0
    return yy
