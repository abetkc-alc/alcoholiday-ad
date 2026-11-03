# design部：額の内側の4隅を自動で出す（白木の額・明るい壁用。2026-10-10）
# 使い方: python frame_edges_sat.py 画像.png "x0,y0,x1,y1(おおよその内側の箱)" [探す幅px 標準15]
# frame_edges.py は「暗い額→明るい紙」の明るさで探すので、白木（明るい木）の額だと外れる。
# こちらは「色の濃さ（あざやかさ＝最大−最小）」で探す：木の額はオレンジで濃く、紙（白・灰色）はうすい。
# 外から内へ見て、あざやかさが一番大きく下がる所を額の内側の線とする。resid（ずれ）が±1px を超える辺は手で確かめる
import sys, numpy as np
from PIL import Image
a=np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float)
s=a.max(2)-a.min(2)
x0,y0,x1,y1=[int(v) for v in sys.argv[2].split(',')]
m=int(sys.argv[3]) if len(sys.argv)>3 else 15
def trans(prof):
    d=np.diff(prof); i=int(np.argmin(d))
    # 下がり方の前後で重み付けして小数点の位置を出す
    if 0<i<len(d)-1:
        y1_,y2_,y3_=d[i-1],d[i],d[i+1]; den=y1_-2*y2_+y3_
        off=0.5*(y1_-y3_)/den if den!=0 else 0
    else: off=0
    return i+0.5+off
top=[];bot=[];lef=[];rig=[]
xs=np.linspace(x0+(x1-x0)*0.1,x1-(x1-x0)*0.1,15).astype(int)
ys=np.linspace(y0+(y1-y0)*0.1,y1-(y1-y0)*0.1,15).astype(int)
for x in xs:
    top.append((x,y0-m+trans(s[y0-m:y0+m,x])))
    bot.append((x,y1+m-1-trans(s[y1-m:y1+m,x][::-1])))
for y in ys:
    lef.append((x0-m+trans(s[y,x0-m:x0+m]),y))
    rig.append((x1+m-1-trans(s[y,x1-m:x1+m][::-1]),y))
def fit(pts,horiz):
    P=np.array(pts)
    if horiz: k,b=np.polyfit(P[:,0],P[:,1],1); return ('h',k,b,P)
    k,b=np.polyfit(P[:,1],P[:,0],1); return ('v',k,b,P)
T,B,L,R=fit(top,1),fit(bot,1),fit(lef,0),fit(rig,0)
for n,f in zip('TBLR',(T,B,L,R)):
    res=f[3][:,1]-(f[1]*f[3][:,0]+f[2]) if f[0]=='h' else f[3][:,0]-(f[1]*f[3][:,1]+f[2])
    print(n,'resid',np.round(res,1))
def inter(h,v):
    kh,bh=h[1],h[2]; kv,bv=v[1],v[2]
    y=(kh*bv+bh)/(1-kh*kv); x=kv*y+bv; return x,y
c=[inter(T,L),inter(T,R),inter(B,R),inter(B,L)]
print(' '.join(f'{x:.1f},{y:.1f}' for x,y in c))
