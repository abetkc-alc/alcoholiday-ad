# ALCOHOLIDAY editing部：指示 2026-11-01-02 ワイン・ビール・スパークリング 動画 v2（静止画だけ）
#   2026-11-01 社長の直し「Higgsfield で何かを動かすのはやめて、静止画を使って動画を作成する」
#   （v1 の Kling 素材：草が異常に伸びる・アップでポスターの大きさが変わる・机の上に意味不明な煙）
#   - Codex の写真3枚（引き → 中くらい → アップ）を各4.5秒、黒フェード0.4秒でつなぐ。ズーム・動きは付けない（ポスターを動かさないルール）
#   - 字幕は「NO ○○, NO LIFE.」1つだけ／曲は種類ごと／最後はサイズ比較 → 締め画像＋ナレーション
# 使い方: python build_video_v2.py 種類(wine/beer/sparkling) v2
import pathlib
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PRODUCT = sys.argv[1]
VER = sys.argv[2] if len(sys.argv) > 2 else "v2"
HERE = pathlib.Path(__file__).parent
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
BGM_DIR = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\音声\backmusic")

# 種類ごとの設定：最初の字幕・曲・曲の始める位置（秒）
CONF = {
    "wine": dict(hook="NO WINE, NO LIFE.", music="BOSANOVA.mp3", bgm_start=1.0),
    "beer": dict(hook="NO BEER, NO LIFE.", music="pop.mp3", bgm_start=172.0),   # 172秒から一段盛り上がる
    "sparkling": dict(hook="NO SPARKLING WINE, NO LIFE.", music="You_and_Me.mp3", bgm_start=13.0),   # 13秒から一段盛り上がる
}[PRODUCT]
# 静止画（Codex の写真を 9:16 に左右だけ切ったもの）。引き → 中くらい → アップ。ズーム・動きは付けない
CLIPS = [HERE / "src" / f"{PRODUCT}-room-angle{i}-916.png" for i in (1, 2, 3)]
SIZE_IMG = SHARED / "product-assets" / f"{PRODUCT}-size.png"
MUSIC = BGM_DIR / CONF["music"]
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
OUT = HERE / f"{PRODUCT}-room-{VER}.mp4"

LENS = [4.5, 4.5, 4.5]   # 各写真を見せる秒数
FADE = 0.4       # 実写の間の黒フェード
T2 = LENS[0] - FADE              # 2本目が見え始める時刻
T3 = T2 + LENS[1] - FADE         # 3本目
MAIN = T3 + LENS[2]

# 字幕は最初の「NO ○○, NO LIFE.」だけ（2026-11-01 社長の直し）
SUBS = [(CONF["hook"], 0.3, 2.0)]
SUB_SIZE = 58
SUB_Y = 1560      # 字幕の上端（画面下の方。SNSの操作ボタンに隠れにくい高さ）
SUB_COLOR = (255, 255, 255, 255)

SIZE_DUR = 1.5
NARR_LEN = 4.17
BRAND_DUR = NARR_LEN + 0.5 - SIZE_DUR
BGM_START = CONF["bgm_start"]


def subtitle_png(text, path):
    """映画の字幕風：白文字＋細い縁取り＋うっすらした影。1行で横幅900px以内。"""
    f = ImageFont.truetype(FONT, SUB_SIZE)
    base = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    w = d.textlength(text, font=f)
    if w > 900:
        raise SystemExit(f"字幕が長すぎて1行に収まりません: {text}")
    x = (1080 - w) / 2
    shadow = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((x + 2, SUB_Y + 3), text, font=f, fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    base = Image.alpha_composite(base, shadow)
    ImageDraw.Draw(base).text((x, SUB_Y), text, font=f, fill=SUB_COLOR,
                              stroke_width=2, stroke_fill=(20, 20, 20, 200))
    base.save(path)


def main():
    if OUT.exists():
        raise SystemExit(f"すでにあります（上書きしません）: {OUT.name}")
    for p in CLIPS + [SIZE_IMG, MUSIC, BRAND, NARR]:
        if not p.exists():
            raise SystemExit(f"素材が見つかりません: {p}")
    work = HERE / f"work-{VER}"
    work.mkdir(exist_ok=True)
    subs = []
    for i, (t, _, _) in enumerate(SUBS, 1):
        p = work / f"sub-{i}.png"
        subtitle_png(t, p)
        subs.append(p)

    norm = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,fps=30,format=yuv420p"
    fc = [f"[{i}:v]trim=duration={LENS[i]},setpts=PTS-STARTPTS,{norm}[a{i}]" for i in range(3)]
    fc += [f"[a0][a1]xfade=transition=fadeblack:duration={FADE}:offset={T2}[x1]",
           f"[x1][a2]xfade=transition=fadeblack:duration={FADE}:offset={T3},format=yuv420p[f0]"]
    last = "f0"
    for i, (_, s, e) in enumerate(SUBS):
        idx = 7 + i
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={s}:d=0.25:alpha=1,fade=t=out:st={e - 0.25}:d=0.25:alpha=1[s{i}]")
        fc.append(f"[{last}][s{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
        last = f"m{i + 1}"
    fc += [
        f"[3:v]scale=1080:1920,fps=30,format=yuv420p,trim=duration={SIZE_DUR},setpts=PTS-STARTPTS[vs]",
        f"[5:v]scale=1080:1920:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
        f"[{last}]trim=duration={MAIN},setpts=PTS-STARTPTS,format=yuv420p[vm]",
        "[vm][vs][vb]concat=n=3:v=1:a=0,format=yuv420p[outv]",
        f"[4:a]atrim=start=0:end={MAIN},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=0.15,afade=t=out:st={MAIN - 1.0}:d=1.0,volume=0.55,aformat=sample_rates=44100:channel_layouts=stereo[bgm]",
        f"[6:a]atrim=0:{SIZE_DUR + BRAND_DUR},asetpts=PTS-STARTPTS,volume=1.6,apad=whole_dur={SIZE_DUR + BRAND_DUR},aresample=44100,aformat=sample_rates=44100:channel_layouts=stereo[narr]",
        "[bgm][narr]concat=n=2:v=0:a=1[outa]",
    ]
    total = MAIN + SIZE_DUR + BRAND_DUR
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-loop", "1", "-framerate", "30", "-t", str(LENS[0]), "-i", str(CLIPS[0]),
           "-loop", "1", "-framerate", "30", "-t", str(LENS[1]), "-i", str(CLIPS[1]),
           "-loop", "1", "-framerate", "30", "-t", str(LENS[2]), "-i", str(CLIPS[2]),
           "-loop", "1", "-framerate", "30", "-t", str(SIZE_DUR), "-i", str(SIZE_IMG),
           "-ss", str(BGM_START), "-i", str(MUSIC),   # 曲の途中へ直接飛ぶ
           "-loop", "1", "-framerate", "30", "-t", str(BRAND_DUR), "-i", str(BRAND),
           "-i", str(NARR)]
    for p in subs:
        cmd += ["-loop", "1", "-framerate", "30", "-t", str(MAIN), "-i", str(p)]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "21", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"DONE {OUT.name}  length {total:.2f}s")


if __name__ == "__main__":
    main()
