import sys,json,itertools
from build123d import *
from OCP.TDocStd import TDocStd_Document
P=''
A=dict(a.split('=') for a in sys.argv[2:])

k=sys.argv[1]
a=import_step(A[k])
# get labels by walking
S=[]
def walk(n,path=''):
    lab=getattr(n,'label','') or ''
    kids=list(getattr(n,'children',[]) or [])
    if kids:
        for c in kids: walk(c,path+'/'+lab)
    else:
        for s in n.solids(): S.append((path+'/'+lab,s))
walk(a)
if len(S)!=len(a.solids()): S=[(f's{i}',s) for i,s in enumerate(a.solids())]
out=[]
bb=[s.bounding_box() for _,s in S]
for i,j in itertools.combinations(range(len(S)),2):
    A_,B_=bb[i],bb[j]
    if A_.min.X>B_.max.X or B_.min.X>A_.max.X or A_.min.Y>B_.max.Y or B_.min.Y>A_.max.Y or A_.min.Z>B_.max.Z or B_.min.Z>A_.max.Z: continue
    try:
        x=S[i][1].intersect(S[j][1]); xs=x.solids() if x else []
    except Exception as e: out.append(dict(a=S[i][0],b=S[j][0],err=str(e))); continue
    v=sum(s.volume for s in xs)
    if v>0.01:
        c=Compound(list(xs)).bounding_box()
        out.append(dict(a=S[i][0],b=S[j][0],vol=round(v,2),bbmin=[round(t,2) for t in (c.min.X,c.min.Y,c.min.Z)],bbmax=[round(t,2) for t in (c.max.X,c.max.Y,c.max.Z)]))
json.dump(dict(n=len(S),labels=[(l,round(s.volume,1)) for l,s in S],hits=out),open(f'logs/intf_{k}.json','w'),indent=1)
print(k,len(S),len(out))
for o in out: print(o)
