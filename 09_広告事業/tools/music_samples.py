# ALCOHOLIDAY 広告事業：申し込みページの「背景の音楽」の見本（▶ 聞く）をつくって、GAS の「声見本」フォルダに置く（2026-10-11）
#   曲の頭から SAMPLE_SEC 秒だけ・音を小さめのファイルにして送る（動画でも曲の頭から使うので、同じところを聞いてもらう）
#   曲の音源ファイルそのものはお客さんに渡さない（OpenTracks の決まり）。見本は短く切り、音質も落としたものだけ
# 使い方: python 09_広告事業/tools/music_samples.py
import base64
import subprocess
import sys
import tempfile
import pathlib

import imageio_ffmpeg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bar_auto  # noqa: E402
import bar_sync  # noqa: E402

SAMPLE_SEC = 12


def main():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as tmp:
        for name, file in bar_auto.MUSIC_CHOICES.items():
            if not file:
                continue   # 音楽なし
            out = pathlib.Path(tmp) / "s.mp3"
            subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-t", str(SAMPLE_SEC), "-i", str(bar_auto.MUSIC_DIR / file),
                            "-af", f"afade=t=in:d=0.3,afade=t=out:st={SAMPLE_SEC - 1.5}:d=1.5", "-ac", "1", "-b:a", "64k", str(out)], check=True)
            bar_sync.call("voice", guide="音楽_" + name, data=base64.b64encode(out.read_bytes()).decode())
            print(f"見本を置いた：音楽_{name}.mp3（{out.stat().st_size // 1024}KB）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
