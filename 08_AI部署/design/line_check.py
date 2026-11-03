# 写真のゆがみ確認用（2026-10-11）
# 使い方:
#   python line_check.py 入力.png 出力.png grid            … 50pxごとの目盛り線（座標を読むため）
#   python line_check.py 入力.png 出力.png lines "V:x1,y1,x2,y2 D:x1,y1,x2,y2 H:..."
#     V=縦の線（赤・画面の上下いっぱいまで延ばす。まっすぐ縦なら x1=x2）
#     D=奥へ向かう線（緑・画面いっぱいまで延ばす。1点に集まるかを見る）／H=横の線（青）
#     D の線どうしの交点（消失点）を計算して表示する
import sys
from PIL import Image, ImageDraw
src, out, mode = sys.argv[1], sys.argv[2], sys.argv[3]
im = Image.open(src).convert('RGB'); w, h = im.size
d = ImageDraw.Draw(im)
if mode == 'grid':
    for x in range(0, w, 50):
        d.line([(x, 0), (x, h)], fill=(255, 0, 0) if x % 100 == 0 else (255, 160, 160), width=1)
        if x % 100 == 0: d.text((x + 2, 2), str(x), fill=(255, 0, 0))
    for y in range(0, h, 50):
        d.line([(0, y), (w, y)], fill=(0, 0, 255) if y % 100 == 0 else (160, 160, 255), width=1)
        if y % 100 == 0: d.text((2, y + 2), str(y), fill=(0, 0, 255))
else:
    col = {'V': (255, 0, 0), 'D': (0, 200, 0), 'H': (0, 90, 255)}
    ds = []
    for item in sys.argv[4].split():
        k, c = item.split(':'); x1, y1, x2, y2 = map(float, c.split(','))
        if k == 'V':
            print(f'縦の線 x {x1:.0f}→{x2:.0f}（上下の差 {x2-x1:+.1f}px）')
        if abs(x2 - x1) < 1e-6:
            pts = [(x1, 0), (x1, h)]
        else:
            m = (y2 - y1) / (x2 - x1); b = y1 - m * x1
            pts = [(-w, b - m * w), (2 * w, b + 2 * m * w)]
        d.line(pts, fill=col[k], width=2)
        d.line([(x1, y1), (x2, y2)], fill=(255, 255, 0), width=3)
        if k == 'D': ds.append((x1, y1, x2, y2))
    vps = []
    for i in range(len(ds)):
        for j in range(i + 1, len(ds)):
            a, b = ds[i], ds[j]
            den = (a[0]-a[2])*(b[1]-b[3]) - (a[1]-a[3])*(b[0]-b[2])
            if abs(den) < 1e-9: continue
            t = ((a[0]-b[0])*(b[1]-b[3]) - (a[1]-b[1])*(b[0]-b[2])) / den
            vps.append((a[0] + t*(a[2]-a[0]), a[1] + t*(a[3]-a[1])))
    for (x, y) in vps:
        print(f'奥への線の交点 ({x:.0f}, {y:.0f})')
        d.ellipse([x-6, y-6, x+6, y+6], outline=(255, 0, 255), width=3)
im.save(out)
