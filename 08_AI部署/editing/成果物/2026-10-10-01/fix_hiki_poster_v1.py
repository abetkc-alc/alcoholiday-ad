# editing部 2026-10-10-01：引きの素材（乾杯）で、3.3秒ごろからポスターの絵（升と手）が小さく形を変えた（check_poster.py で 105%・NG）
# お金をかけない直し方：ポスター（額ごと）の四角だけを、最初のコマの絵で全コマ覆う（ふちを6pxぼかす）
#   ポスターのまわりは壁だけで、手・腕・お猪口は四角に入らない（いちばん高く上がる手でも y=500 前後、四角の下は y=400）
#   元の素材は残し、-fix.mp4 の別名で保存する
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageFilter

ff = imageio_ffmpeg.get_ffmpeg_exe()
src, dst = sys.argv[1], sys.argv[2]
W, H = 720, 1280
X0, Y0, X1, Y1 = 212, 60, 428, 402   # 額の外側より少し大きい四角（720x1280 のとき）
FEATHER = 6

raw = subprocess.run([ff, "-loglevel", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     capture_output=True, check=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
ref = frames[0].astype(np.float32)

mask = Image.new("L", (W, H), 0)
mask.paste(255, (X0 + FEATHER, Y0 + FEATHER, X1 - FEATHER, Y1 - FEATHER))
mask = np.asarray(mask.filter(ImageFilter.GaussianBlur(FEATHER / 2)), np.float32)[..., None] / 255.0

# 念のため：四角のふち（壁）に何かが入ってこないか、最初のコマとの差を数字で出す
ring = np.zeros((H, W), bool)
ring[Y0 - 10:Y1 + 10, X0 - 10:X1 + 10] = True
ring[Y0:Y1, X0:X1] = False
worst = max(float(np.abs(f.astype(np.float32) - ref)[ring].mean()) for f in frames)
print(f"frames {len(frames)} / 四角のまわりの壁の差 最大 {worst:.1f}（10以下なら何も入ってきていない）")

out = (frames.astype(np.float32) * (1 - mask) + ref * mask).clip(0, 255).astype(np.uint8)
p = subprocess.Popen([ff, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                      "-r", "24", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", dst],
                     stdin=subprocess.PIPE)
p.stdin.write(out.tobytes())
p.stdin.close()
p.wait()
print("DONE", dst)
