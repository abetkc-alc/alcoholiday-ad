# design部：額の内側の4隅を自動で出す。使い方: python frame_edges.py 画像.png "x0,y0,x1,y1(おおよその内側の箱)" [探す幅px 標準25]
# 各辺15か所で「暗い額→明るい紙」の切り替わりを探し、直線で当てはめて交点を出す。resid（ずれ）が±1px を超える辺は、日ざしの帯などで外れているので、明るさの数字で手で決める
# 額の内側の線を、列/行ごとの「暗い額→明るい紙」の切り替わりから求め、直線で当てはめて4隅を出す
import sys, numpy as np
from PIL import Image
a=np.asarray(Image.open(sys.argv[1]).convert('L')).astype(float)
x0,y0,x1,y1=[int(v) for v in sys.argv[2].split(',')]  # おおよその内側の箱
m=int(sys.argv[3]) if len(sys.argv)>3 else 25
def trans(prof, inward):
    # prof: 外から内へ。額(暗)から紙(明)へ最後に上がる所
    d=np.diff(prof); i=int(np.argmax(d)); return i+0.5
top=[];bot=[];lef=[];rig=[]
xs=np.linspace(x0+(x1-x0)*0.1,x1-(x1-x0)*0.1,15).astype(int)
ys=np.linspace(y0+(y1-y0)*0.1,y1-(y1-y0)*0.1,15).astype(int)
for x in xs:
    p=a[y0-m:y0+m,x]; top.append((x,y0-m+trans(p,1)))
    p=a[y1-m:y1+m,x][::-1]; bot.append((x,y1+m-1-trans(p,1)))
for y in ys:
    p=a[y,x0-m:x0+m]; lef.append((x0-m+trans(p,1),y))
    p=a[y,x1-m:x1+m][::-1]; rig.append((x1+m-1-trans(p,1),y))
def fit(pts,horiz):
    P=np.array(pts); 
    if horiz: k,b=np.polyfit(P[:,0],P[:,1],1); return ('h',k,b,P)
    k,b=np.polyfit(P[:,1],P[:,0],1); return ('v',k,b,P)
T,B,L,R=fit(top,1),fit(bot,1),fit(lef,0),fit(rig,0)
for n,f in zip('TBLR',(T,B,L,R)):
    res=f[3][:,1]-(f[1]*f[3][:,0]+f[2]) if f[0]=='h' else f[3][:,0]-(f[1]*f[3][:,1]+f[2])
    print(n, 'resid', np.round(res,1))
def inter(h,v):
    # y=kh x+bh ; x=kv y+bv
    kh,bh=h[1],h[2]; kv,bv=v[1],v[2]
    y=(kh*bv+bh)/(1-kh*kv); x=kv*y+bv; return x,y
c=[inter(T,L),inter(T,R),inter(B,R),inter(B,L)]
print(' '.join(f'{x:.1f},{y:.1f}' for x,y in c))
