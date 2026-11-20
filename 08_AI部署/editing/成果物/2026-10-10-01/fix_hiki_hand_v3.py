# editing部 2026-10-10-01（2回目）：引きの素材 v3 で、右のネルシャツの人の手が1秒すぎから大きく持ち上がり、
#   徳利の上で指を広げたまま浮いて不自然だった（指示は「少し動く程度」）
# お金をかけない直し方：手が動いた場所だけを、手が動く前のコマ（0.42秒・Kling のぼけ方がそろった後）の絵で全コマ覆う
#   覆う場所は「各コマと基準コマの差」の最大値で自動で決める（画面の右下だけ。左のニットの人の小さな動きは残す）
#   元の素材は残し、-fix.mp4 の別名で保存する
# 使い方: python fix_hiki_hand_v3.py 入力.mp4 出力.mp4 [マスクの確認画像.png]
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageFilter

ff = imageio_ffmpeg.get_ffmpeg_exe()
src, dst = sys.argv[1], sys.argv[2]
W, H = 720, 1280
REF = 10            # 基準コマ（0.42秒）
raw = subprocess.run([ff, "-loglevel", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     capture_output=True, check=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
ref = frames[REF].astype(np.float32)
refL = ref.mean(axis=2)

dmax = np.zeros((H, W), np.float32)
for f in frames:
    d = np.abs(f.astype(np.float32).mean(axis=2) - refL)
    d = np.asarray(Image.fromarray(d.astype(np.uint8)).filter(ImageFilter.BoxBlur(3)), np.float32)
    dmax = np.maximum(dmax, d)
m = (dmax > 18)
m[:, : int(W * 0.5)] = False          # 左半分（ニットの人）は覆わない
m[: int(H * 0.55), :] = False         # 上（壁・ポスター・障子）は覆わない
mask = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(8))
if len(sys.argv) > 3:
    mask.save(sys.argv[3])
mk = np.asarray(mask, np.float32)[..., None] / 255.0
ys, xs = np.nonzero(np.asarray(mask) > 10)
print(f"frames {len(frames)} / 覆った範囲 x {xs.min()}-{xs.max()} y {ys.min()}-{ys.max()} / 面積 {float((mk > 0.04).mean()) * 100:.1f}%")

out = (frames.astype(np.float32) * (1 - mk) + ref * mk).clip(0, 255).astype(np.uint8)
p = subprocess.Popen([ff, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                      "-r", "24", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", dst],
                     stdin=subprocess.PIPE)
p.stdin.write(out.tobytes())
p.stdin.close()
p.wait()
print("DONE", dst)
