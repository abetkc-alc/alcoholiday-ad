# design部：ポスターなじませ仕上げ 第3版（2026-10-06 社長指摘「3枚とも、ポスターがまだ不自然」への対策）
#
# 考え方：Codex が描いたポスター（文字は崩れるが、部屋の光・色・むら・映り込みは自然）から
#        「紙の白」「背景のベージュ」「黒い線」が部屋の光でどんな色に写っているかを測り、
#        原画を貼った画像の色を、その写り方にそっくり合わせる。絵柄の形は原画のまま。
#
# 使い方: python blend_poster3.py 貼り直した画像.png Codexの元画像.png 出力.png "左上 右上 右下 左下" [映り込みの強さ 標準0.8]
#   貼り直した画像：paste_poster.py の出力
#   4点：額の内側の角（paste_poster.py と同じ値）
#
# 手順
#  1) Codex の白いふち（左右・上・下）の色を何十か所も測り、なめらかな面で近似 → 紙の白の明るさ・色のむら（ランプ側が明るい）
#  2) Codex のベージュ（絵の無い左上・上・左下）と黒い線の色を、白に対する割合で測る
#  3) 原画の各色（黒→ベージュ→白）を、測った割合へ折れ線で写す × 1) の白のむら
#  4) Codex と結果を大きくぼかして差をとり、映り込み・光の帯を足す
#  5) 額のふちが紙に落とす細い影、写真なみのぼけ・ざらつき
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

src, codex_p, dst, pts_s = sys.argv[1:5]
refl_k = float(sys.argv[5]) if len(sys.argv) > 5 else 0.8
pts = [tuple(float(v) for v in p.split(",")) for p in pts_s.split()]
TL, TR, BR, BL = [np.array(p) for p in pts]

im = Image.open(src).convert("RGB")
W, H = im.size
a = np.asarray(im).astype(np.float32) / 255.0
cdx = np.asarray(Image.open(codex_p).convert("RGB")).astype(np.float32) / 255.0
LUMW = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
pw = float(np.linalg.norm(TR - TL))
ph = float(np.linalg.norm(BL - TL))


def at(u, v):
    # 紙の上の位置（u=横 0〜1, v=縦 0〜1）→ 画像の座標（四隅の内挿）
    return (1 - u) * (1 - v) * TL + u * (1 - v) * TR + u * v * BR + (1 - u) * v * BL


def sample(img, u, v, r=1):
    x, y = at(u, v)
    x, y = int(round(x)), int(round(y))
    return np.median(img[y - r:y + r + 1, x - r:x + r + 1].reshape(-1, 3), 0)


# 原画（whisky.jpg）のレイアウト：ベージュの範囲は u 0.039〜0.955, v 0.029〜0.944
mu = 0.014  # 白いふちの真ん中あたり（額の影を避ける）
wpts = []
for t in np.linspace(0.08, 0.92, 12):
    wpts += [(mu, t), (1 - mu, t), (t, mu)]
for t in list(np.linspace(0.04, 0.22, 4)) + list(np.linspace(0.78, 0.96, 4)):
    wpts += [(t, 0.955), (t, 0.99)]
U = np.array([p[0] for p in wpts]); V = np.array([p[1] for p in wpts])
Cw = np.array([sample(cdx, u, v) for u, v in wpts])
# 外れ値（文字・影）を外す
Lw = Cw @ LUMW
keep = Lw > np.percentile(Lw, 15)
U, V, Cw = U[keep], V[keep], Cw[keep]
Aw = np.stack([np.ones_like(U), U, V, U * V, U ** 2, V ** 2], 1)
coefs = [np.linalg.lstsq(Aw, Cw[:, c], rcond=None)[0] for c in range(3)]

# 画像の各画素の (u,v) を求める（射影の逆変換）
def homography(src_pts, dst_pts):
    A = []
    for (x, y), (u, v) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A))
    return vt[-1].reshape(3, 3)


Hm = homography(pts, [(0, 0), (1, 0), (1, 1), (0, 1)])
gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
den = Hm[2, 0] * gx + Hm[2, 1] * gy + Hm[2, 2]
uu = (Hm[0, 0] * gx + Hm[0, 1] * gy + Hm[0, 2]) / den
vv = (Hm[1, 0] * gx + Hm[1, 1] * gy + Hm[1, 2]) / den
uc, vc = np.clip(uu, 0, 1), np.clip(vv, 0, 1)
basis = [np.ones_like(uc), uc, vc, uc * vc, uc ** 2, vc ** 2]
white = np.stack([sum(c * b for c, b in zip(co, basis)) for co in coefs], -1)
white = np.clip(white, 0.05, 1)

# ベージュと黒の写り方（白に対する割合）
bpts = [(u, v) for u in np.linspace(0.10, 0.90, 9) for v in (0.06, 0.10)] + \
       [(u, v) for u in np.linspace(0.10, 0.40, 4) for v in (0.86, 0.91)]


def ratio_at(img, plist, white_fn):
    r = []
    for u, v in plist:
        x, y = at(u, v)
        r.append(sample(img, u, v, 2) / np.maximum(white_fn[int(round(y)), int(round(x))], 1e-3))
    return np.median(np.array(r), 0)


r_beige_c = ratio_at(cdx, bpts, white)
# 原画側（貼った画像）の白・ベージュ（原画は白=1）
art_white = np.median(np.array([sample(a, u, v) for u, v in wpts]), 0)
r_beige_a = np.median(np.array([sample(a, u, v, 2) for u, v in bpts]), 0) / art_white
inner = Image.new("L", (W, H), 0)
ImageDraw.Draw(inner).polygon(pts, fill=255)
inner_m = np.asarray(inner.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255.0
core = np.asarray(inner.filter(ImageFilter.MinFilter(9))).astype(np.float32) / 255.0 > 0.5
cl = cdx @ LUMW
dark_c = np.percentile(cl[core], 1.5)
dark_px = cdx[core][np.abs(cl[core] - dark_c) < 0.03]
r_black_c = np.median(dark_px, 0) / np.median(white[core], 0)
r_black_a = np.array([0.0, 0.0, 0.0])
print("beige ratio codex", r_beige_c.round(3), "art", r_beige_a.round(3), "black", r_black_c.round(3))

# 原画の色（白で割った値）を、黒→ベージュ→白 の3点を通る折れ線で写す（チャンネルごと）
x = a / art_white
y = np.empty_like(x)
for c in range(3):
    xs = np.array([r_black_a[c], r_beige_a[c], 1.0])
    ys = np.array([r_black_c[c], r_beige_c[c], 1.0])
    xc = x[..., c]
    lo = ys[0] + (xc - xs[0]) * (ys[1] - ys[0]) / max(xs[1] - xs[0], 1e-3)
    hi = ys[1] + (xc - xs[1]) * (ys[2] - ys[1]) / max(xs[2] - xs[1], 1e-3)
    y[..., c] = np.where(xc < xs[1], lo, hi)
b = np.clip(y, 0, 1.05) * white

# 4) 映り込み・光の帯：Codex と結果を大きくぼかした差を足す
def masked_blur(img, m, r):
    out = []
    dm = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))).astype(np.float32)
    for c in range(3):
        num = np.asarray(Image.fromarray(np.clip(img[..., c] * m * 255, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))).astype(np.float32)
        out.append(num / np.maximum(dm, 1e-3))
    return np.stack(out, -1)


cm = core.astype(np.float32)
rb = max(3.0, pw * 0.06)
resid = masked_blur(cdx, cm, rb) - masked_blur(np.clip(b, 0, 1), cm, rb)
# 絵柄のずれによる差は打ち消し合うよう、さらに広くぼかしたものとの平均
resid2 = masked_blur(cdx, cm, rb * 2.5) - masked_blur(np.clip(b, 0, 1), cm, rb * 2.5)
resid = np.clip(0.4 * resid + 0.6 * resid2, -0.08, 0.08)
b = b + resid * refl_k

# ガラスのごく弱い映り込み：斜めの柔らかい光の帯＋ランプ側のぼんやりした明るみ
lamp_left = white[int(at(0.05, 0.5)[1]), int(at(0.05, 0.5)[0])].mean() > white[int(at(0.95, 0.5)[1]), int(at(0.95, 0.5)[0])].mean()
t = uc * 0.8 + vc * 0.6
sheen = np.exp(-((t - 0.55) ** 2) / 0.02) * 0.03
lu = 0.08 if lamp_left else 0.92
glow = np.exp(-(((uc - lu) / 0.18) ** 2 + ((vc - 0.40) / 0.22) ** 2)) * 0.045
b = b + (sheen + glow)[..., None] * (white / np.maximum(white.mean(-1, keepdims=True), 1e-3))

# 5) 額のふちの影
def dist_to_line(p, q):
    (x1, y1), (x2, y2) = p, q
    n = np.hypot(x2 - x1, y2 - y1)
    return np.abs((y2 - y1) * gx - (x2 - x1) * gy + x2 * y1 - y2 * x1) / n


sw = max(2.0, pw / 110)
left_bright = white[int(at(0.05, 0.5)[1]), int(at(0.05, 0.5)[0])].mean() > white[int(at(0.95, 0.5)[1]), int(at(0.95, 0.5)[0])].mean()
sl, sr = (0.10, 0.22) if left_bright else (0.22, 0.10)
sh = (0.28 * np.exp(-dist_to_line(pts[0], pts[1]) / sw)
      + sl * np.exp(-dist_to_line(pts[3], pts[0]) / sw)
      + sr * np.exp(-dist_to_line(pts[1], pts[2]) / sw)
      + 0.06 * np.exp(-dist_to_line(pts[2], pts[3]) / sw))
b = b * (1 - np.clip(sh, 0, 0.4))[..., None]
b = np.clip(b, 0, 1)

# ぼけ・ざらつき（Codex のポスター部分の細かい揺れに合わせる）
out = Image.fromarray((b * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(min(0.8, max(0.5, pw / 900))))
o = np.asarray(out).astype(np.float32) / 255.0
hp = cl - np.asarray(Image.fromarray((cl * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255.0
flat = core & (np.abs(cl - np.median(cl[core])) < 0.05)
noise_sd = float(np.clip(np.std(hp[flat]) if flat.sum() > 50 else 0.006, 0.003, 0.006))  # 強すぎると紙がざらざらに見える（上限0.006）
rng = np.random.default_rng(7)
n = rng.normal(0, noise_sd, (H, W)).astype(np.float32)
o = o + n[..., None]

res = a * (1 - inner_m[..., None]) + np.clip(o, 0, 1) * inner_m[..., None]
Image.fromarray((np.clip(res, 0, 1) * 255).astype(np.uint8)).save(dst)
print("DONE", dst, "noise", round(noise_sd, 4))
