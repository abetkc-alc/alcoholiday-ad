# editing部：Tシャツのアップ（closeup-kling3-v5.mp4）のプリントの文字崩れを直す（2026-10-03）
# Kling は布をほとんど動かさない指示でも、0.8秒あたりから FRUIT の F・R が斜めに崩れた。
# このカットはカメラ固定で、胸は呼吸でわずかに上下するだけ。そこで、文字が崩れていない最初のコマの
# プリント部分（布ごと）を、各コマの胸の位置（上下左右のずれを探して追いかける）に重ねる。
# 背景の光・髪・手など、プリント以外はその素材のまま。元の素材は残し、-fix.mp4 の別名で保存する。
# 使い方: python fix_closeup_print.py 入力.mp4 出力.mp4 [使う長さ秒]
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
dur = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 720, 1280, 24

raw = subprocess.run([FF, "-loglevel", "error", "-t", str(dur), "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     capture_output=True, check=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
print("frames", len(frames))


def yellow(f):
    a = f.astype(np.float32) / 255
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    gr = G / np.maximum(R, 1e-4)
    bg = B / np.maximum(G, 1e-4)
    return np.clip((np.minimum(R, G) - B - 0.06) / 0.18, 0, 1) * ((gr > 0.8) & (gr < 1.2) & (bg < 0.55))


ref = frames[0]
ya = yellow(ref)
# 背景の電球・肌を拾わないよう、胸のあたり（画面の中央）だけで探す
win = np.zeros_like(ya)
win[150:1050, 120:640] = 1
ys, xs = np.nonzero((ya * win) > 0.5)
# プリント全体を囲む四角（少し余白）
m = 34
y0, y1 = max(ys.min() - m, 0), min(ys.max() + m, H)
x0, x1 = max(xs.min() - m, 0), min(xs.max() + m, W)
print("print box", x0, y0, x1, y1)
ref_y = ya[y0:y1, x0:x1]

# 四角のふちをぼかしたマスク（ふち20px で素材となじませる）
mask = Image.new("L", (W, H), 0)
mask.paste(255, (x0 + 10, y0 + 10, x1 - 10, y1 - 10))
mask = np.asarray(mask.filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255

R = 70
shifts = []
for i, f in enumerate(frames):
    cy = yellow(f)
    # 最初のコマのプリントが、このコマでどれだけずれたかを探す（上下±70px・左右±15px。±14px では足りず二重に残った）
    best, bd = 1e18, (0, 0)
    for dy in range(-R, R + 1, 2):
        for dx in range(-15, 16, 1):
            yy0, xx0 = y0 + dy, x0 + dx
            if yy0 < 0 or xx0 < 0 or yy0 + ref_y.shape[0] > H or xx0 + ref_y.shape[1] > W:
                continue
            d = np.abs(cy[yy0:yy0 + ref_y.shape[0], xx0:xx0 + ref_y.shape[1]] - ref_y).sum()
            if d < best:
                best, bd = d, (dx, dy)
    shifts.append(bd)
shifts = np.array(shifts, np.float32)
# 測ったずれはコマごとにばらつく（そのまま使うとプリントがガタガタ揺れる）→ 時間の2次式でなめらかにする
t = np.arange(len(frames)) / FPS
sx = np.polyval(np.polyfit(t, shifts[:, 0], 2), t)
sy = np.polyval(np.polyfit(t, shifts[:, 1], 2), t)
for i in range(0, len(frames), 6):
    print(f"{t[i]:.2f}s measured dx={shifts[i, 0]:.0f} dy={shifts[i, 1]:.0f}  smooth dx={sx[i]:.1f} dy={sy[i]:.1f}")

refp = Image.fromarray(ref)
maskp = Image.fromarray((mask * 255).astype(np.uint8))
out = []
for i, f in enumerate(frames):
    # 小数のずれも、なめらかに動かす（画像の平行移動）
    tr = (1, 0, -sx[i], 0, 1, -sy[i])
    shifted = np.asarray(refp.transform((W, H), Image.AFFINE, tr, resample=Image.BILINEAR)).astype(np.float32)
    mk = (np.asarray(maskp.transform((W, H), Image.AFFINE, tr, resample=Image.BILINEAR)).astype(np.float32) / 255)[..., None]
    # 明るさの変化（呼吸・光のゆらぎ）は、四角のまわりの明るさの比で合わせる
    ring = (mk[..., 0] > 0.02) & (mk[..., 0] < 0.5)
    gain = (f[ring].astype(np.float32).mean(0) + 1) / (shifted[ring].mean(0) + 1)
    comp = f.astype(np.float32) * (1 - mk) + np.clip(shifted * gain, 0, 255) * mk
    out.append(np.clip(comp, 0, 255).astype(np.uint8))

p = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                      "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
p.stdin.write(np.stack(out).tobytes())
p.stdin.close()
p.wait()
print("DONE", dst)
