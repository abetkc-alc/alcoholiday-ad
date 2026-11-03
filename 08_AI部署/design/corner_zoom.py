# design部：4隅の周りを10倍に拡大し、推定点に十字を描く。使い方: python corner_zoom.py 画像.png 出力.png "左上 右上 右下 左下"
# 4隅の周りを8倍に拡大し、推定点に十字（cyan）
import sys
from PIL import Image, ImageDraw
im=Image.open(sys.argv[1]).convert('RGB'); pts=[tuple(float(v) for v in p.split(',')) for p in sys.argv[3].split()]
R=12;Z=10; out=Image.new('RGB',(4*(2*R*Z+10),2*R*Z),'white')
for k,(x,y) in enumerate(pts):
    cx,cy=int(x),int(y); cr=im.crop((cx-R,cy-R,cx+R,cy+R)).resize((2*R*Z,2*R*Z),Image.NEAREST); d=ImageDraw.Draw(cr)
    px=(x-(cx-R))*Z; py=(y-(cy-R))*Z
    d.line((px-30,py,px+30,py),fill=(0,255,255)); d.line((px,py-30,px,py+30),fill=(0,255,255))
    out.paste(cr,(k*(2*R*Z+10),0))
out.save(sys.argv[2])
