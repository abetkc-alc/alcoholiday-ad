# editing部：指示 2026-11-01-01 アップの素材で、カメラが少しずつ引いてポスターが5秒で約3%小さくなった（check_poster.py で NG）
# お金をかけない直し方：check_poster.py と同じ測り方（拡大とずれを総当たり）で、0.2秒ごとにポスターの大きさ・位置を
#   最初のコマと比べて測り、なめらかにしてから各コマを拡大・ずらしてポスターを止める
#   （OpenCV の findTransformECC で測ったら、明るさの変化に引っぱられて半分ほどしか直らなかった）
# 使い方: python fix_up_zoom.py 入力.mp4 出力.mp4 x0 y0 x1 y1 [line]（ポスターの範囲・画面に対する割合。line＝折れ線でならす）
# 出力は映像だけ（この素材はもともと音なし）
import subprocess
import sys

import cv2
import imageio_ffmpeg
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
x0f, y0f, x1f, y1f = (float(v) for v in sys.argv[3:7])
ff = imageio_ffmpeg.get_ffmpeg_exe()

cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
h, w = frames[0].shape[:2]
box = (int(x0f * w), int(y0f * h), int(x1f * w), int(y1f * h))
bcx, bcy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
bw, bh = box[2] - box[0], box[3] - box[1]
gray = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames]
m = 10
ref_c = gray[0][box[1]:box[3], box[0]:box[2]][m:-m, m:-m]


def best_match(img):
    """そのコマを (bcx,bcy) を中心に s 倍し、dx,dy ずらすと最初のコマに一番重なる値。"""
    best = (1e18, 1.0, 0.0, 0.0)
    for s in np.arange(0.98, 1.0601, 0.0025):
        w2, h2 = bw / s, bh / s
        crop = cv2.getRectSubPix(img, (int(round(w2)), int(round(h2))), (bcx, bcy))
        a = cv2.resize(crop, (bw, bh), interpolation=cv2.INTER_LINEAR)
        for dx in range(-8, 9):
            for dy in range(-8, 9):
                sub = a[m + dy:bh - m + dy, m + dx:bw - m + dx]
                if sub.shape != ref_c.shape:
                    continue
                # 明るさの変化に引っぱられないよう、平均の明るさをそろえて比べる
                err = float(np.mean(np.abs((sub - sub.mean()) - (ref_c - ref_c.mean()))))
                if err < best[0]:
                    best = (err, float(s), float(dx), float(dy))
    return best


step = max(1, int(round(fps * 0.2)))
idx = list(range(0, len(frames), step)) + [len(frames) - 1]
meas = []
for i in idx:
    _, s, dx, dy = best_match(gray[i])
    meas.append((s, dx, dy))
    print(f"{i / fps:.2f}s: 大きさ {s * 100:.2f}% ずれ ({dx:+.0f},{dy:+.0f})")
meas = np.array(meas)
t = np.arange(len(frames))
if len(sys.argv) > 7 and sys.argv[7] == "line":
    # 寄り方が途中で止まる素材（2026-11-01-02 ワインのアップ：4秒で105%に達して止まる）は2次式が合わない
    #   → 測った値を前後1つずつと平均してから折れ線でつなぐ
    ma = np.array([meas[max(0, i - 1):i + 2].mean(axis=0) for i in range(len(meas))])
    smooth = np.stack([np.interp(t, idx, ma[:, k]) for k in range(3)], axis=1)
else:
    smooth = np.stack([np.polyval(np.polyfit(idx, meas[:, k], 2), t) for k in range(3)], axis=1)
smooth[:, 0] /= smooth[0, 0]   # 最初のコマはそのまま（1倍・ずれ0）
smooth[:, 1] -= smooth[0, 1]
smooth[:, 2] -= smooth[0, 2]

# 各コマ：ポスターの中心で s 倍 → 切り出しのずれ (dx,dy) の分だけ画像を逆に動かす
#   すべて拡大（s≥1）になるので、画面のふちに空きは出ない
proc = subprocess.Popen([ff, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "slow",
                         "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
for f, (s, dx, dy) in zip(frames, smooth):
    mtx = np.array([[s, 0, bcx - s * bcx - dx], [0, s, bcy - s * bcy - dy]], np.float32)
    out = cv2.warpAffine(f, mtx, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    proc.stdin.write(out.tobytes())
proc.stdin.close()
proc.wait()
print(f"DONE {dst}  最後のコマの拡大 {smooth[-1, 0]:.4f}")
