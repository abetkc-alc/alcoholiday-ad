# 0.2秒ごとに、指定した四角（割合 x0,y0,x1,y1）を拡大して並べる。お猪口・手の伸び・ゆがみ・指の数を見る
# 使い方: python crops.py 動画.mp4 出力.png x0 y0 x1 y1 [倍率]
import subprocess, sys
import imageio_ffmpeg, numpy as np
from PIL import Image, ImageDraw
ff = imageio_ffmpeg.get_ffmpeg_exe()
v, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = (float(a) for a in sys.argv[3:7])
scale = float(sys.argv[7]) if len(sys.argv) > 7 else 1.5
raw = subprocess.run([ff, "-loglevel", "error", "-i", v, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
probe = subprocess.run([ff, "-i", v], capture_output=True, text=True, errors="ignore").stderr
import re
W, H = map(int, re.search(r"(\d{3,4})x(\d{3,4})", probe).groups())
fps = float(re.search(r"([\d.]+) fps", probe).group(1))
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
times = [round(i * 0.2, 2) for i in range(int(len(fr) / fps / 0.2) + 1)]
crops = []
for t in times:
    i = min(int(round(t * fps)), len(fr) - 1)
    c = Image.fromarray(fr[i]).crop(box)
    c = c.resize((int(c.width * scale), int(c.height * scale)))
    ImageDraw.Draw(c).text((4, 4), f"{t:.1f}s", fill=(255, 0, 0))
    crops.append(c)
cols = 6
cw, ch = crops[0].size
sheet = Image.new("RGB", (cw * cols, ch * ((len(crops) + cols - 1) // cols)), "white")
for k, c in enumerate(crops):
    sheet.paste(c, ((k % cols) * cw, (k // cols) * ch))
sheet.save(out)
print(W, H, fps, len(fr), "frames ->", out, sheet.size)
