# design部：Codex が描き直してしまったポスターを、元画像（原画）そのものに差し替える
# Codex はポスターを「描き直す」ことがあり、ロゴの文字が崩れたり絵柄が変わったりする（2026-10-06）。
# 部屋はそのまま使い、額の内側だけを原画を遠近に合わせて貼り直す。そのあと blend_poster.py で必ずなじませる。
#
# 使い方: python paste_poster.py 入力.png 原画.jpg 出力.png "左上 右上 右下 左下" ["紙の範囲 x0,y0,x1,y1"]
#   4点は額の「内側」の角（corner_check.py で調べる）
#   紙の範囲：原画の中の、紙（白いふち込み）の部分。ウイスキー whisky.jpg は 497,75,2521,2937
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

src, art_p, dst, pts_s = sys.argv[1:5]
box = tuple(int(v) for v in sys.argv[5].split(",")) if len(sys.argv) > 5 else None
pts = [tuple(float(v) for v in p.split(",")) for p in pts_s.split()]

room = Image.open(src).convert("RGB")
W, H = room.size
art = Image.open(art_p).convert("RGB")
if box:
    art = art.crop(box)

# 点々模様のちらつきを防ぐため、先に貼る大きさの2倍くらいまで縮める
qw = max(abs(pts[1][0] - pts[0][0]), abs(pts[2][0] - pts[3][0]))
qh = max(abs(pts[3][1] - pts[0][1]), abs(pts[2][1] - pts[1][1]))
sw = int(qw * 2)
sh = int(sw * art.height / art.width)
art = art.resize((sw, sh), Image.LANCZOS)


def coeffs(dst_pts, src_pts):
    # 出力の点 -> 原画の点 への射影変換の係数
    A, B = [], []
    for (x, y), (u, v) in zip(dst_pts, src_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


# ふちの外側を白で足しておく（足さないと、ふちに黒い点線が出る）
PAD = 6
padded = Image.new("RGB", (sw + 2 * PAD, sh + 2 * PAD), art.getpixel((2, 2)))
padded.paste(art, (PAD, PAD))
art = padded
src_pts = [(PAD, PAD), (sw + PAD, PAD), (sw + PAD, sh + PAD), (PAD, sh + PAD)]
warped = art.transform((W, H), Image.PERSPECTIVE, coeffs(pts, src_pts), Image.BICUBIC)

mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(mask).polygon(pts, fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(0.7))

out = room.copy()
out.paste(warped, (0, 0), mask)

# 額のふちが紙に落とす細い影（上と左を少し濃く）
o = np.asarray(out).astype(np.float32)
gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)


def dist_to_line(p, q):
    (x1, y1), (x2, y2) = p, q
    n = np.hypot(x2 - x1, y2 - y1)
    return np.abs((y2 - y1) * gx - (x2 - x1) * gy + x2 * y1 - y2 * x1) / n


k = max(2.0, qw / 120)  # 影の幅（px）
shade = (0.22 * np.exp(-dist_to_line(pts[0], pts[1]) / k)
         + 0.16 * np.exp(-dist_to_line(pts[3], pts[0]) / k)
         + 0.08 * np.exp(-dist_to_line(pts[1], pts[2]) / k)
         + 0.06 * np.exp(-dist_to_line(pts[2], pts[3]) / k))
m = np.asarray(mask).astype(np.float32) / 255.0
o = o * (1 - np.clip(shade, 0, 0.35) * m)[..., None]
Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)).save(dst)
print("DONE", dst)
