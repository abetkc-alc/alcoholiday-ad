# editing部：人物が動く素材のTシャツのプリント崩れを直す（2026-10-10-02）
# 2026-10-03-02 の fix_closeup_print.py（上下左右のずれだけ）を、体が揺れる・前に乗り出す動きにも使えるよう広げたもの。
# - 最初のコマ（文字が崩れていない）のプリントを、各コマの胸の位置・傾き・大きさ（アフィン変換）に合わせて重ねる
# - 動きは黄色いプリントの形どうしを重ね合わせて測る（OpenCV の findTransformECC）。測った値は前後のコマでならしてなめらかにする
# - 手や腕（肌の色）がプリントの四角にかかったコマでは、肌の部分には重ねない（手・腕は素材のまま）
# 元の素材は残し、-fix.mp4 などの別名で保存する。
# 使い方: python fix_print_track.py 入力.mp4 出力.mp4 [使い始め秒] [使う長さ秒] [ref=基準コマ番号]
import subprocess
import sys

import cv2
import imageio_ffmpeg
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
ss = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
dur = float(sys.argv[4]) if len(sys.argv) > 4 else 5.1
REF = int(sys.argv[5]) if len(sys.argv) > 5 else 0
FF = imageio_ffmpeg.get_ffmpeg_exe()

probe = subprocess.run([FF, "-i", src], capture_output=True, text=True, encoding="utf-8", errors="ignore").stderr
import re
W, H = map(int, re.search(r"Video:.*?, (\d{3,4})x(\d{3,4})", probe).groups())
FPS = float(re.search(r"([\d.]+) fps", probe).group(1))
raw = subprocess.run([FF, "-loglevel", "error", "-ss", str(ss), "-t", str(dur), "-i", src,
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
n = len(frames)
print("frames", n, W, H, FPS)


def yellow(f):
    a = f.astype(np.float32) / 255
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    gr = G / np.maximum(R, 1e-4)
    bg = B / np.maximum(G, 1e-4)
    return (np.clip((np.minimum(R, G) - B - 0.06) / 0.18, 0, 1) * ((gr > 0.8) & (gr < 1.2) & (bg < 0.55))).astype(np.float32)


def skin(f):
    hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = ((h <= 17) | (h >= 170)) & (s > 40) & (s < 200) & (v > 90)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.dilate(m, np.ones((9, 9), np.uint8))
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 3)


ref = frames[REF]
ya = yellow(ref)
win = np.zeros_like(ya)
win[int(H * 0.30):int(H * 0.95), int(W * 0.15):int(W * 0.85)] = 1
ys, xs = np.nonzero((ya * win) > 0.5)
m = int(W * 0.035)
y0, y1 = max(ys.min() - m, 0), min(ys.max() + m, H)
x0, x1 = max(xs.min() - m, 0), min(xs.max() + m, W)
print("print box", x0, y0, x1, y1)

box = np.zeros((H, W), np.float32)
e = int(W * 0.012)
box[y0 + e:y1 - e, x0 + e:x1 - e] = 1
box = cv2.GaussianBlur(box, (0, 0), e)
ecc_mask = np.zeros((H, W), np.uint8)
pad = int(W * 0.08)
ecc_mask[max(y0 - pad, 0):y1 + pad, max(x0 - pad, 0):x1 + pad] = 255

tmpl = cv2.GaussianBlur(ya * win, (0, 0), 2)
warps = []
Wp = np.eye(2, 3, dtype=np.float32)
crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
order = list(range(REF, n)) + list(range(REF - 1, -1, -1))
res = {}
for i in order:
    if i == REF - 1:
        Wp = res[REF].copy()
    cur = cv2.GaussianBlur(yellow(frames[i]) * (1 - skin(frames[i])), (0, 0), 2)
    try:
        _, Wp = cv2.findTransformECC(tmpl, cur, Wp, cv2.MOTION_AFFINE, crit, ecc_mask, 5)
    except cv2.error:
        print("ECC failed at", i)
    res[i] = Wp.copy()
warps = np.stack([res[i] for i in range(n)])

# 前後のコマでならす（測った値のばらつきで、プリントが細かく揺れないように）
k = 7
pad_w = np.concatenate([warps[:1].repeat(k // 2, 0), warps, warps[-1:].repeat(k // 2, 0)])
smooth = np.stack([pad_w[i:i + k].mean(0) for i in range(n)])
for i in range(0, n, max(1, int(FPS // 2))):
    a = smooth[i]
    print(f"{i / FPS:.2f}s  scale={np.sqrt(abs(np.linalg.det(a[:, :2]))):.3f} dx={a[0, 2]:.1f} dy={a[1, 2]:.1f}")

out = []
for i, f in enumerate(frames):
    A = smooth[i]
    wr = cv2.warpAffine(ref, A, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
    mk = cv2.warpAffine(box, A, (W, H), flags=cv2.INTER_LINEAR)
    # 手・腕（肌の色）は、今のコマの方を残す
    mk = mk * (1 - skin(f))
    ring = (mk > 0.02) & (mk < 0.5)
    gain = (f[ring].astype(np.float32).mean(0) + 1) / (wr[ring].mean(0) + 1) if ring.any() else 1.0
    mk3 = mk[..., None]
    comp = f.astype(np.float32) * (1 - mk3) + np.clip(wr * gain, 0, 255) * mk3
    out.append(np.clip(comp, 0, 255).astype(np.uint8))

p = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                      "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
p.stdin.write(np.stack(out).tobytes())
p.stdin.close()
p.wait()
print("DONE", dst)
