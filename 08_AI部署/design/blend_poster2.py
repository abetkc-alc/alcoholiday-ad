# design部：ポスターなじませ仕上げ 第2版（2026-10-06 社長指摘「貼った画像に見える」への対策）
# blend_poster.py より強く「同じカメラで撮った」質感に寄せる。絵柄の形は変えない（明るさ・色・ぼけ・ざらつき・影だけ）。
#
# 使い方: python blend_poster2.py 貼り直した画像.png Codexの元画像.png 出力.png "左上 右上 右下 左下" [色味の強さ 0〜1、標準0.4]
#   貼り直した画像：paste_poster.py の出力（原画が額に入っている）
#   Codexの元画像：Codex が出した写真（ポスター部分に部屋の光のむら・ランプの映り込みが描かれている。これを借りる）
#
# やること
#  1) 壁の明るさと色を「場所ごと」に調べ（額のまわりの壁から平面で近似）、紙の白を「同じ場所の壁より少し明るい程度」に落とす
#     → ランプ側が明るく遠い側が暗い、なだらかなむらが自然に付く
#  2) Codex の写真のポスター部分の「大きな明るさのむら」（ランプの映り込み・ガラスの反射）を借りて重ねる
#  3) 黒を少し浮かせ、鮮やかさ・コントラストを写真なみに落とす
#  4) 額のふちが紙に落とす細い影（上と光と反対側を濃く）
#  5) 写真と同じくらいのぼけ・ざらつき（壁のざらつきを測って同じ量を足す）
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

src, codex_p, dst, pts_s = sys.argv[1:5]
tint_k = float(sys.argv[5]) if len(sys.argv) > 5 else 0.4
pts = [tuple(float(v) for v in p.split(",")) for p in pts_s.split()]

im = Image.open(src).convert("RGB")
W, H = im.size
a = np.asarray(im).astype(np.float32) / 255.0
cx_img = np.asarray(Image.open(codex_p).convert("RGB")).astype(np.float32) / 255.0
LUMW = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def poly_mask(points, grow=0.0):
    cx = sum(p[0] for p in points) / 4
    cy = sum(p[1] for p in points) / 4
    pp = [(cx + (x - cx) * (1 + grow), cy + (y - cy) * (1 + grow)) for x, y in points]
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(pp, fill=255)
    return np.asarray(m).astype(np.float32) / 255.0


inner = poly_mask(pts)
pw = max(pts[1][0] - pts[0][0], pts[2][0] - pts[3][0])
ph = max(pts[3][1] - pts[0][1], pts[2][1] - pts[1][1])
gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)

# ---- 1) 壁の明るさ・色を場所ごとに（額の外の帯で平面近似。R,G,B それぞれ）
ring = np.clip(poly_mask(pts, 0.35) - poly_mask(pts, 0.12), 0, 1)
ys, xs = np.nonzero(ring > 0.5)
L = a[ys, xs] @ LUMW
lo, hi = np.percentile(L, 20), np.percentile(L, 80)
k = (L > lo) & (L < hi)
ys, xs = ys[k], xs[k]
A = np.stack([np.ones_like(xs, dtype=np.float32), xs / W, ys / H], 1)
wall = np.zeros((H, W, 3), np.float32)
for c in range(3):
    coef, *_ = np.linalg.lstsq(A, a[ys, xs, c], rcond=None)
    wall[..., c] = coef[0] + coef[1] * gx / W + coef[2] * gy / H
wall = np.clip(wall, 0.02, 1)
wall_L = wall @ LUMW

# 紙の白：同じ場所の壁の 1.10 倍の明るさ。色は壁の光の色を tint_k だけ乗せる（強くすると商品の色が変わる）
paper_L = np.clip(wall_L * 1.10, 0, 0.95)
wall_hue = wall / np.maximum(wall_L[..., None], 1e-4)
hue = 1 + (wall_hue - 1) * tint_k
target_white = paper_L[..., None] * hue

# ---- 2) Codex のポスター部分の大きなむら（映り込み）を借りる
def masked_blur(img, m, r):
    num = np.asarray(Image.fromarray(np.clip(img * m * 255, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))).astype(np.float32)
    den = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))).astype(np.float32)
    return num / np.maximum(den, 1e-3)


r_big = max(4.0, pw * 0.12)
cL = cx_img @ LUMW
cL_blur = masked_blur(cL, inner, r_big)
med = np.median(cL_blur[inner > 0.5])
shade = np.clip(cL_blur / max(med, 1e-4), 0.8, 1.2)
# 自分の絵柄の大きなむら（手・グラスの位置の違い）を打ち消すため、原画側でも同じぼかしをとって割る
aL = a @ LUMW
aL_blur = masked_blur(aL, inner, r_big)
amed = np.median(aL_blur[inner > 0.5])
own = np.clip(aL_blur / max(amed, 1e-4), 0.8, 1.2)
shade = np.clip(shade / own, 0.85, 1.15)
shade = 1 + (shade - 1) * 0.7

# 紙の白（原画の白 ≒ 1.0）を target_white に合わせる
b = a * target_white * shade[..., None]

# ---- 3) 黒を浮かせ、鮮やかさ・コントラストを落とす
black = wall * 0.16
b = black + b * (1 - 0.16 * 1.0)
bl = b @ LUMW
b = bl[..., None] + (b - bl[..., None]) * 0.85

# ガラスのごく弱い映り込み（斜めの柔らかい帯）
x0, y0 = pts[0]
t = ((gx - x0) / max(pw, 1) * 0.8 + (gy - y0) / max(ph, 1) * 0.6)
band = np.exp(-((t - 0.5) ** 2) / 0.03) * 0.025
b = b + band[..., None] * wall_hue * 0.9

# ---- 4) 額のふちが紙に落とす影（数px、柔らかく）
def dist_to_line(p, q):
    (x1, y1), (x2, y2) = p, q
    n = np.hypot(x2 - x1, y2 - y1)
    return np.abs((y2 - y1) * gx - (x2 - x1) * gy + x2 * y1 - y2 * x1) / n


sw = max(2.5, pw / 90)
# 光の来る側（壁の明るい側）は影が薄い
left_brighter = wall_L[int(pts[0][1] + ph / 2), int(pts[0][0])] > wall_L[int(pts[1][1] + ph / 2), int(pts[1][0])]
side_l, side_r = (0.10, 0.22) if left_brighter else (0.22, 0.10)
sh = (0.30 * np.exp(-dist_to_line(pts[0], pts[1]) / sw)
      + side_l * np.exp(-dist_to_line(pts[3], pts[0]) / sw)
      + side_r * np.exp(-dist_to_line(pts[1], pts[2]) / sw)
      + 0.06 * np.exp(-dist_to_line(pts[2], pts[3]) / sw))
b = b * (1 - np.clip(sh, 0, 0.4))[..., None]
b = np.clip(b, 0, 1)

# ---- 5) ぼけ・ざらつきを写真に合わせる
out = Image.fromarray((b * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(0.6, pw / 700)))
o = np.asarray(out).astype(np.float32) / 255.0
# 壁のざらつき量を測る（細かい揺れの標準偏差）
wl = a @ LUMW
hp = wl - np.asarray(Image.fromarray((wl * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255.0
noise_sd = float(np.clip(np.std(hp[ys, xs]), 0.004, 0.02))
rng = np.random.default_rng(7)
n = rng.normal(0, noise_sd, (H, W)).astype(np.float32)
n = np.asarray(Image.fromarray(np.clip((n + 0.5) * 255, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5))).astype(np.float32) / 255.0 - 0.5
o = o + n[..., None] * 1.3

m = np.asarray(Image.fromarray((inner * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32)[..., None] / 255.0
res = a * (1 - m) + np.clip(o, 0, 1) * m
Image.fromarray((np.clip(res, 0, 1) * 255).astype(np.uint8)).save(dst)
print("DONE", dst, "noise", round(noise_sd, 4))
