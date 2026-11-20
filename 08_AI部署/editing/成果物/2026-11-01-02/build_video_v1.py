# ALCOHOLIDAY editing部：指示 2026-11-01-02 ワイン・ビール・スパークリング（23歳それぞれの部屋）動画 v1
#   2026-11-01-01/build_video_v2.py（日本酒・字幕は最初の1つだけ）をコピーし、種類を選べるようにした
#   - 写真：Codex が作った <種類>-angle-01〜03-a2-420x592-v4.png（引き → 中くらい → アップ）
#   - 字幕は「NO ○○, NO LIFE.」1つだけ（2026-11-01 社長の直し）
#   - 曲は種類ごとに変える（2026-11-01 社長指示）
# 使い方: python build_video_v1.py 種類(wine/beer/sparkling) v1
import pathlib
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PRODUCT = sys.argv[1]
VER = sys.argv[2] if len(sys.argv) > 2 else "v1"
HERE = pathlib.Path(__file__).parent
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
BGM_DIR = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\音声\backmusic")

# 種類ごとの設定：最初の字幕・曲・曲の始める位置（秒）・各実写の使用秒数・使う素材（直した版があればそちら）
CONF = {
    # 引き：2.5秒ごろから部屋全体が暗くなり3.8秒でパッと明るくなる → 2.4秒まで（社長：お金をかけず短く使う）
    # 中くらい：4.5秒からポスターがずれる → 4.3秒まで／アップ：カメラが寄った → fix_up_zoom.py line で止めた版。4.0秒まで
    "wine": dict(hook="NO WINE, NO LIFE.", music="BOSANOVA.mp3", bgm_start=1.0,
                 lens=[2.4, 4.3, 4.0], clips={"up": "wine-room-up-kling-v1-fix2.mp4"}),
    "beer": dict(hook="NO BEER, NO LIFE.", music="pop.mp3", bgm_start=172.0,   # 172秒から一段盛り上がる
                 lens=[4.5, 4.5, 4.5]),
    # 引き：2秒すぎからポスターの絵が崩れる → 1.5秒まで（社長：お金をかけず短く使う）
    # 中くらい：4.5秒から画面全体が変わる → 4.3秒まで／アップ：カメラが寄った → fix_up_zoom.py で止めた版
    "sparkling": dict(hook="NO SPARKLING WINE, NO LIFE.", music="You_and_Me.mp3", bgm_start=13.0,   # 13秒から一段盛り上がる
                      lens=[1.5, 4.3, 4.5], clips={"up": "sparkling-room-up-kling-v1-fix.mp4"}),
}[PRODUCT]
CLIPS = [HERE / CONF.get("clips", {}).get(k, f"{PRODUCT}-room-{k}-kling-v1.mp4") for k in ("hiki", "naka", "up")]
SIZE_IMG = SHARED / "product-assets" / f"{PRODUCT}-size.png"
MUSIC = BGM_DIR / CONF["music"]
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
OUT = HERE / f"{PRODUCT}-room-{VER}.mp4"

LENS = CONF["lens"]   # 各実写の使用秒数（素材は約5.04秒。Kling は最後の0.5秒でポスターが縮みやすい）
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

    norm = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p"
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
           "-i", str(CLIPS[0]), "-i", str(CLIPS[1]), "-i", str(CLIPS[2]),
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
