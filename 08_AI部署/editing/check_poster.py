# editing部：Higgsfield の動画でポスターが動いていないか（大きさ・位置が変わっていないか）を数字で確かめる
# 2026-09-27 に、動画の中でポスターの絵が5秒で約3%小さくなっていた（社長に「縮小している」と指摘された）ため必須にした
#
# 使い方: python check_poster.py 動画.mp4 x0 y0 x1 y1 [調べる秒をカンマ区切り。標準 2.5,4.9]
#   x0..y1: ポスター（額の内側）の範囲。画面に対する割合 0〜1。人や物がかぶらないよう、ポスターの内側に絞る
# しくみ: 最初のコマのポスター部分を基準に、中ほど・終わりのコマを「何倍に拡大・何pxずらすと一番よく重なるか」を探す。
#   色や線の判定を使わないので、なじませ仕上げで色を落ち着かせた画像でも、ランプの光や人の髪に惑わされない
#   （2026-09-27：色で測る方法・黒い線で測る方法は、どちらもランプや髪を拾って数字がぶれたため、この方法にした）
# 判定: 大きさの変化 1%以下、ずれ 3px以下なら OK
import io
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image

video = sys.argv[1]
x0f, y0f, x1f, y1f = (float(v) for v in sys.argv[2:6])
ff = imageio_ffmpeg.get_ffmpeg_exe()


def frame(t):
    out = subprocess.run([ff, "-loglevel", "error", "-ss", str(t), "-i", video, "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(out)).convert("L")


ref_img = frame(0.05)
W, H = ref_img.size
box = (int(x0f * W), int(y0f * H), int(x1f * W), int(y1f * H))
cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
bw, bh = box[2] - box[0], box[3] - box[1]
ref = np.asarray(ref_img.crop(box)).astype(np.float32)
# 端の影響を避けるため内側だけで比べる
m = 8
ref_c = ref[m:-m, m:-m]


def best_match(img):
    best = (1e18, 1.0, 0, 0)
    for s in np.arange(0.95, 1.0501, 0.005):
        # s倍に拡大したときに基準と同じ範囲になる切り出し
        w2, h2 = bw / s, bh / s
        crop = img.crop((cx - w2 / 2, cy - h2 / 2, cx + w2 / 2, cy + h2 / 2)).resize((bw, bh), Image.BILINEAR)
        a = np.asarray(crop).astype(np.float32)
        for dx in range(-6, 7, 2):
            for dy in range(-6, 7, 2):
                sub = a[m + dy:bh - m + dy, m + dx:bw - m + dx]
                if sub.shape != ref_c.shape:
                    continue
                err = float(np.mean(np.abs(sub - ref_c)))
                if err < best[0]:
                    best = (err, float(s), dx, dy)
    return best


worst_s, worst_d = 0.0, 0
TIMES = [float(v) for v in sys.argv[6].split(",")] if len(sys.argv) > 6 else [2.5, 4.9]
for t in TIMES:
    err, s, dx, dy = best_match(frame(t))
    print(f"t={t}: 一番よく重なるのは 大きさ{s * 100:.1f}% ・ずれ({dx},{dy})px ・残りの差{err:.1f}")
    worst_s = max(worst_s, abs(s - 1))
    worst_d = max(worst_d, abs(dx), abs(dy))
print(f"大きさの変化 最大 {worst_s * 100:.1f}% / ずれ 最大 {worst_d}px")
print("OK" if worst_s <= 0.01 and worst_d <= 3 else "NG (poster moved)")
