# design部：ポスターを部屋になじませる仕上げ
# Codex の写真ではポスターだけが「別の光で撮った画像を貼った」ように見える（明るすぎ・鮮やかすぎ・くっきりしすぎ・光のむらが無い）。
# そこで、額の内側（紙の部分）だけを、まわりの壁の光に合わせて整える。絵柄の形は一切変えない（色と明るさ・質感だけ）。
#
# 使い方: python blend_poster.py 入力.png 出力.png "x1,y1 x2,y2 x3,y3 x4,y4"  [強さ 0〜1、標準 1]
#   4点は額の「内側」の角（左上・右上・右下・左下の順、元画像のピクセル座標）
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

src, dst, pts_s = sys.argv[1], sys.argv[2], sys.argv[3]
strength = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
pts = [tuple(float(v) for v in p.split(",")) for p in pts_s.split()]

im = Image.open(src).convert("RGB")
W, H = im.size
a = np.asarray(im).astype(np.float32) / 255.0


def poly_mask(points, grow=0.0):
    cx = sum(p[0] for p in points) / 4
    cy = sum(p[1] for p in points) / 4
    pp = [(cx + (x - cx) * (1 + grow), cy + (y - cy) * (1 + grow)) for x, y in points]
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(pp, fill=255)
    return np.asarray(m).astype(np.float32) / 255.0


inner = poly_mask(pts)
# 壁のサンプル：額の外側の帯（額の木部を避けるため少し離す）
ring = np.clip(poly_mask(pts, 0.32) - poly_mask(pts, 0.14), 0, 1)

lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
ys, xs = np.nonzero(ring > 0.5)
# 明るすぎ・暗すぎる物（ランプ・植物）を外して、壁らしい画素だけ使う
L = lum[ys, xs]
lo, hi = np.percentile(L, 15), np.percentile(L, 85)
keep = (L > lo) & (L < hi)
ys, xs, L = ys[keep], xs[keep], L[keep]
# 壁の明るさを「平面」で近似 → 光のむら（ランプ側が明るい）を再現する
A = np.stack([np.ones_like(xs, dtype=np.float32), xs / W, ys / H], 1)
coef, *_ = np.linalg.lstsq(A, L, rcond=None)
gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
wall_L = coef[0] + coef[1] * gx / W + coef[2] * gy / H
wall_rgb = a[ys, xs].mean(0)
wall_tint = wall_rgb / max(wall_rgb.mean(), 1e-4)  # 部屋の光の色（暖色など）

# ポスター側の今の明るさ（紙の白の明るさ）
pys, pxs = np.nonzero(inner > 0.5)
paper_white = np.percentile(lum[pys, pxs], 97)

# 1) 光のむら：壁の明るさの変化をそのままポスターにも掛ける
#    白い紙は、同じ光を受けた壁より少し明るい程度（壁の1.35倍・上限あり）
target_white = np.clip(wall_L * 1.35, 0, 0.93)
gain = target_white / max(paper_white, 1e-4)
b = a * gain[..., None]
# 2) 部屋の光の色を少し乗せる
#    壁の色そのもの（緑の壁など）を強く乗せると商品の色が変わってしまう（2026-09-27 ワインの黄色が緑がかった）
#    → 壁の色は15%だけ。あとはランプの暖かい光の色を一定量乗せる
warm = np.array([1.03, 1.0, 0.93], dtype=np.float32)
b = b * ((0.85 + 0.15 * wall_tint) * warm)[None, None, :]
# 3) 鮮やかさ・コントラストを少し落とす（印刷の紙はテレビ画面のように鮮やかには光らない）
bl = b @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
b = bl[..., None] + (b - bl[..., None]) * 0.82
mean = (b * inner[..., None]).sum((0, 1)) / inner.sum()
b = mean + (b - mean) * 0.9
# 4) 額のガラスのうっすらした映り込み（斜めの柔らかい光の帯）
x0, y0 = pts[0]
x1, y1 = pts[2]
t = ((gx - x0) / max(x1 - x0, 1) * 0.8 + (gy - y0) / max(y1 - y0, 1) * 0.6)
band = np.exp(-((t - 0.55) ** 2) / 0.02) * 0.035
b = b + band[..., None] * np.array([1.0, 0.98, 0.94])
b = np.clip(b, 0, 1)

out = Image.fromarray((b * 255).astype(np.uint8))
# 5) 写真らしい柔らかさとざらつき
out = out.filter(ImageFilter.GaussianBlur(0.6))
o = np.asarray(out).astype(np.float32) / 255.0
rng = np.random.default_rng(1)
o = o + rng.normal(0, 0.012, o.shape).astype(np.float32)

# 額の内側だけ入れ替える（ふちを1〜2px ぼかしてなじませる）
m = np.asarray(Image.fromarray((inner * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255.0
m = (m * strength)[..., None]
res = a * (1 - m) + np.clip(o, 0, 1) * m
Image.fromarray((np.clip(res, 0, 1) * 255).astype(np.uint8)).save(dst)
print("DONE", dst)
