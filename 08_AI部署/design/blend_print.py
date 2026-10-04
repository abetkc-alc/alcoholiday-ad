# design部：Tシャツのプリントを布になじませる仕上げ
# Codex の写真ではプリントが「平らなステッカーを貼った」ように見える（シワに沿わない・影がかからない・鮮やかすぎ）。
# そこで、プリントのまわりの布の明るさ（シワの影）を調べ、プリントにも同じ影をかけ、シワに沿って少しゆがませる。
# 文字・絵柄の形そのものは変えない（数ピクセルのゆがみと、色・明るさ・質感だけ）。
#
# 使い方: python blend_print.py 入力.png 出力.png [強さ 0〜1、標準 1]
#   プリント（黒い布の上の黄色）は自動で見つける
import sys

import numpy as np
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
strength = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255.0
H, W, _ = a.shape
R, G, B = a[..., 0], a[..., 1], a[..., 2]


def blur(x, s):
    # numpy だけのガウスぼかし（縦横に分けて掛ける）
    r = int(s * 3) + 1
    k = np.exp(-(np.arange(-r, r + 1) ** 2) / (2 * s * s))
    k /= k.sum()
    pad = np.pad(x, r, mode="edge")
    t = np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 1, pad)
    return np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 0, t)


def fill(val, w, s):
    # w の重みがある所だけの値で、まわりを埋めながらぼかす（プリントの下の布を推定する）
    return blur(val * w, s) / np.maximum(blur(w, s), 1e-4)


def sample(img, mx, my):
    # 少しずらした位置から色を拾う（なめらかな補間）
    hh, ww = img.shape[:2]
    x0 = np.clip(np.floor(mx).astype(int), 0, ww - 2)
    y0 = np.clip(np.floor(my).astype(int), 0, hh - 2)
    fx = np.clip(mx - x0, 0, 1)[..., None] if img.ndim == 3 else np.clip(mx - x0, 0, 1)
    fy = np.clip(my - y0, 0, 1)[..., None] if img.ndim == 3 else np.clip(my - y0, 0, 1)
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


# 1) プリントの場所：黄色（赤と緑が高く、青が低い）
alpha = np.clip((np.minimum(R, G) - B - 0.06) / 0.18, 0, 1)
# 背景のボトル（琥珀色）・電球・肌も暖色なので、色の比率で「プリントの黄色」だけを選ぶ
#   プリント：赤と緑がほぼ同じ・青がとても少ない／ボトルや肌：赤が強い（緑÷赤が小さい）・電球：白っぽい
gr = G / np.maximum(R, 1e-4)
bg = B / np.maximum(G, 1e-4)
yellow = (alpha > 0.6) & (gr > 0.82) & (gr < 1.15) & (bg < 0.5) & (G > 0.25)
# 黄色が一番集まっている場所（プリント）を中心に、そのまとまりだけを使う
# （縮小した格子で、黄色のあるマスを広げてつなげ、一番大きいかたまりを選ぶ）
cs = 16
gh, gw = H // cs, W // cs
cells = yellow[: gh * cs, : gw * cs].reshape(gh, cs, gw, cs).sum((1, 3)) >= 3
grown = cells.copy()
for _ in range(2):
    g2 = grown.copy()
    g2[1:] |= grown[:-1]; g2[:-1] |= grown[1:]; g2[:, 1:] |= grown[:, :-1]; g2[:, :-1] |= grown[:, 1:]
    grown = g2
lab = np.zeros((gh, gw), int)
best, best_n, n_lab = 0, 0, 0
for sy in range(gh):
    for sx in range(gw):
        if grown[sy, sx] and not lab[sy, sx]:
            n_lab += 1
            stack, cnt = [(sy, sx)], 0
            lab[sy, sx] = n_lab
            while stack:
                cy, cx = stack.pop()
                cnt += cells[cy, cx]
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < gh and 0 <= nx < gw and grown[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n_lab
                        stack.append((ny, nx))
            if cnt > best_n:
                best, best_n = n_lab, cnt
keep = np.kron(lab == best, np.ones((cs, cs), bool))
keep = np.pad(keep, ((0, H - keep.shape[0]), (0, W - keep.shape[1])))
strong = yellow & keep
ys, xs = np.nonzero(strong)
y_lo, y_hi = ys.min(), ys.max()
x_lo, x_hi = xs.min(), xs.max()
m = 14
y0b, y1b, x0b, x1b = max(y_lo - m, 0), min(y_hi + m, H), max(x_lo - m, 0), min(x_hi + m, W)
print("print box", x0b, x1b, y0b, y1b)
box = np.zeros((H, W), np.float32)
box[y0b:y1b, x0b:x1b] = 1
alpha *= box

# 計算は範囲のまわりだけで行う（速くするため）
pad = 60
Y0, Y1, X0, X1 = max(y0b - pad, 0), min(y1b + pad, H), max(x0b - pad, 0), min(x1b + pad, W)
ac = a[Y0:Y1, X0:X1]
al = alpha[Y0:Y1, X0:X1]
h, w = al.shape

# 2) 布（プリント以外）の明るさから、シワの影を推定する
cloth_w = (blur(al, 2.0) < 0.02).astype(np.float32)
lum = ac @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
shade_fine = fill(lum, cloth_w, 5.0)      # シワ
shade_wide = fill(lum, cloth_w, 30.0)     # 光のむら（大きな明暗）
ref = np.median(lum[cloth_w > 0.5])
S = (0.55 * shade_fine + 0.45 * shade_wide) / max(ref, 1e-4)
S = np.clip(S, 0.45, 1.6) ** 0.9

# 3) プリントの下の布の色（プリントを取り除いた布）
base = np.stack([fill(ac[..., c], cloth_w, 6.0) for c in range(3)], -1)
rng = np.random.default_rng(3)
base = base + (rng.normal(0, 0.008, base.shape) * cloth_w.mean()).astype(np.float32)

# 4) インクの色：今のプリントの色を取り出し、鮮やかさ・明るさを少し落とす
ink = np.stack([fill(ac[..., c], al, 1.2) for c in range(3)], -1)
il = ink @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
ink = il[..., None] + (ink - il[..., None]) * 0.85
ink = ink * 0.95

# 5) シワに沿ったゆがみ：明暗の傾きの方向に少しずらす（最大3px程度）
gy, gx = np.gradient(blur(S, 6.0))
gmax = max(np.percentile(np.hypot(gx, gy), 99), 1e-4)
dx, dy = gx / gmax * 2.5, gy / gmax * 2.5
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
al_w = sample(al, xx - dx, yy - dy)
ink_w = sample(ink, xx - dx, yy - dy)

# 6) シワの影をインクにもかける＋綿の織り目（細かいざらつき）とインクのかすれ
tex = blur(rng.normal(0, 1, (h, w)).astype(np.float32), 0.7)
tex = tex / max(tex.std(), 1e-4)
ink_w = ink_w * S[..., None] * (1 + 0.03 * tex[..., None])
al_w = np.clip(al_w * (0.97 + 0.03 * tex), 0, 1)
# くっきりしすぎる輪郭をほんの少しやわらげる
al_w = 0.7 * al_w + 0.3 * blur(al_w, 0.8)

comp = base * (1 - al_w[..., None]) + np.clip(ink_w, 0, 1) * al_w[..., None]
# 写真らしいざらつきを、まわりと同じくらい足す
comp = comp + rng.normal(0, 0.01, comp.shape).astype(np.float32)

# 7) プリントのまわりだけ入れ替える（ふちはなめらかに）
region = np.clip(blur((blur(np.maximum(al, al_w), 3.0) > 0.01).astype(np.float32), 3.0), 0, 1)
region = (region * strength)[..., None]
out = a.copy()
out[Y0:Y1, X0:X1] = ac * (1 - region) + np.clip(comp, 0, 1) * region
Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(dst)
print("DONE", dst)
