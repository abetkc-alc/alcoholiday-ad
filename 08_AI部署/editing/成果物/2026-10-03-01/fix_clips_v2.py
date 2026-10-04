# editing部 2026-10-03-01：Higgsfield 素材に出た「湯気」（中アップ）と「鳥」（引き・窓の外）を消す
# しくみ：本来まったく動かない部分（棚の上の壁／窓の空）だけを、最初のコマ（湯気・鳥がまだ出ていない）の絵で覆う。ふちは12pxぼかす
# v2：中アップの湯気だけ、覆う範囲を泡のふちまで広げてやり直し（*-fix-v2.mp4）
import io, pathlib, subprocess
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter
HERE = pathlib.Path(__file__).parent
FF = imageio_ffmpeg.get_ffmpeg_exe()
JOBS = [("beer-autumn-naka-kling-v1", (495, 740, 692, 1064))]   # v2：泡のふちまで広げた（v1 で細い湯気が残ったため）
for name, box in JOBS:
    src = HERE / f"{name}.mp4"; out = HERE / f"{name}-fix-v2.mp4"
    if out.exists():
        print("skip", out.name); continue
    png = subprocess.run([FF, "-loglevel", "error", "-ss", "0", "-i", str(src), "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    f0 = Image.open(io.BytesIO(png)).convert("RGBA")
    mask = Image.new("L", f0.size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(4))
    f0.putalpha(mask)
    patch = HERE / "check" / f"{name}-patch-v2.png"
    f0.save(patch)
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", str(src), "-loop", "1", "-i", str(patch),
                    "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1,format=yuv420p",
                    "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-an", str(out)], check=True)
    print("DONE", out.name)
