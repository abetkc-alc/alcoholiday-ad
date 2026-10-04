# design部：額の内側の四隅を確かめるための拡大図をつくる（blend_poster.py に渡す座標を決める補助）
# 使い方: python corner_check.py 画像.png 出力.png "x1,y1 x2,y2 x3,y3 x4,y4"
# 各角の周り±40pxを3倍に拡大し、10pxごとに赤線、推定位置に青い十字を描く
import sys
from PIL import Image, ImageDraw
im = Image.open(sys.argv[1]).convert("RGB")
pts = [tuple(int(float(v)) for v in p.split(",")) for p in sys.argv[3].split()]
out = Image.new("RGB", (4 * 260, 260), "white")
for k, (x, y) in enumerate(pts):
    cr = im.crop((x - 40, y - 40, x + 40, y + 40)).resize((240, 240), Image.NEAREST)
    d = ImageDraw.Draw(cr)
    for g in range(0, 240, 30):
        d.line((g, 0, g, 240), fill=(255, 0, 0))
        d.line((0, g, 240, g), fill=(255, 0, 0))
    d.line((110, 120, 130, 120), fill=(0, 0, 255), width=2)
    d.line((120, 110, 120, 130), fill=(0, 0, 255), width=2)
    out.paste(cr, (k * 260, 0))
out.save(sys.argv[2])
