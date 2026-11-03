"""3本の Higgsfield 動画（2→1、1→3、3→4）を、つなぎ目が見えない1本のワンカットにする。

- 前の動画の最後と次の動画の最初は同じ写真なので、つなぎ目を 0.2 秒だけ重ねて溶かし、わずかな色や位置のずれを目立たなくする
- 仕上がり：縦 1080×1920、30コマ/秒、H.264、音なし
使い方：python join_oneshot.py [版の名前 v1]
"""
import os
import subprocess
import sys

import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CLIPS = ["oneshot-a-2to1.mp4", "oneshot-b-1to3.mp4", "oneshot-c-3to4.mp4"]
XF = 0.2  # つなぎ目を重ねる秒数


def duration(path):
    out = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True, encoding="utf-8", errors="ignore").stderr
    h, m, s = out.split("Duration: ")[1].split(",")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def main():
    ver = sys.argv[1] if len(sys.argv) > 1 else "v1"
    paths = [os.path.join(HERE, c) for c in CLIPS]
    durs = [duration(p) for p in paths]
    args = [FFMPEG, "-y"]
    for p in paths:
        args += ["-i", p]
    f = []
    for i in range(len(paths)):
        f.append(f"[{i}:v]scale=1080:1920:flags=lanczos,fps=30,setsar=1,format=yuv420p,settb=AVTB[v{i}]")
    last = "v0"
    offset = 0.0
    for i in range(1, len(paths)):
        offset += durs[i - 1] - XF
        f.append(f"[{last}][v{i}]xfade=transition=fade:duration={XF}:offset={offset:.3f}[x{i}]")
        last = f"x{i}"
    out = os.path.join(HERE, f"ワンカット-ポスターの店-{ver}.mp4")
    args += ["-filter_complex", ";".join(f), "-map", f"[{last}]", "-c:v", "libx264", "-crf", "17",
             "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    subprocess.run(args, check=True)
    print("DONE", out, f"{sum(durs) - XF * (len(paths) - 1):.2f}秒")


if __name__ == "__main__":
    main()
