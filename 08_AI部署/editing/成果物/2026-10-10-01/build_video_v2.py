# ALCOHOLIDAY editing部：指示 2026-10-10-01 日本酒・連休に同級生と昼飲み 動画 v1
#   見本：2026-10-06-01/build_video_v1.py をコピーして素材・字幕を差し替え、「古いフィルム映像」の質感を足した
#   - 台本：scripts/成果物/2026-10-10-01/台本-案B.md（字幕6つ。最初は「NO JAPANESE SAKE, NO LIFE.」）
#   - 写真の順（社長が選んだ順）：中ぐらい(angle2) → 引き(angle1) → アップ(angle3)。字幕は台本の順番のまま時間順に当てる
#   - ポスターは一切動かさない（後からのズーム・画面全体の揺れ・コマのガタつきなし）
#   - 古いフィルムの質感：粒子（毎コマ変わる細かいノイズ）・少し色あせた暖色・周りを少し暗く・ときどき淡い光もれ（画面のふちだけ）
#     字幕はフィルム加工のあとに重ねる（文字はくっきり読めるように）。締め画像は軽めにかけ、ロゴははっきり残す
#   - 黒フェードは前後の素材に重ねる（xfade）ので、2本目・3本目の字幕は台本の時刻より早まる（各場面の中の位置は台本どおり）
#   - 音楽は社長が選んだ「週末京都現実逃避.mp3」。曲の盛り上がり 172.05秒 から使い、締めの前に消す
#   - サイズ比較写真（sake-size.png）→ 最後は必ず締め画像＋ナレーション
# v2（2026-10-10）：v1 は光もれがほとんど見えず、粒子も控えめだったので、光もれを強く・大きく、粒子を少し強く。
#   粒子でファイルが大きくなる（v1 は約110MB）ので crf 17→21 にした
# 使い方: python build_video_v2.py v2
import pathlib
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VER = sys.argv[1] if len(sys.argv) > 1 else "v2"
HERE = pathlib.Path(__file__).parent
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# 社長が選んだ順
CLIPS = [HERE / "sake-holiday-naka-kling-v1.mp4",   # 中ぐらい（手前の手がお猪口を持ち上げる）
         HERE / "sake-holiday-hiki-kling-v1-fix.mp4",   # 引き（2人で乾杯。3.3秒〜ポスターの絵が変わったので最初のコマのポスターで覆った版）
         HERE / "sake-holiday-up-kling-v1.mp4"]     # アップ（木の葉の影・日ざしがゆれる。ズームはしない）
SIZE_IMG = SHARED / "product-assets" / "sake-size.png"
MUSIC = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\音声\backmusic\週末京都現実逃避.mp3")
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
OUT = HERE / f"sake-holiday-{VER}.mp4"

CLIP_LEN = 5.0   # 各実写の使用秒数（素材は約5.04秒。これより長くしない）
FADE = 0.4       # 実写の間の黒フェード
T2 = CLIP_LEN - FADE             # 2本目が見え始める時刻 4.6
T3 = 2 * CLIP_LEN - 2 * FADE     # 3本目 9.2
MAIN = 3 * CLIP_LEN - 2 * FADE   # 14.2

# 字幕（文字, 表示開始, 表示終了）— 台本 案B（各場面の中の位置は台本どおり、順番も台本どおり）
SUBS = [("NO JAPANESE SAKE, NO LIFE.", 0.3, 2.0),
        ("暇な同級生、来訪。", 2.3, T2 - 0.1),
        ("話は、いつもの話。", T2 + 0.4, T2 + 2.5),
        ("オチは、ない。", T2 + 2.7, T3 - 0.1),
        ("腐れ縁に、乾杯。", T3 + 0.3, T3 + 2.5),
        ("Amazonで販売中。", T3 + 2.7, MAIN - 0.2)]
SUB_SIZE = 58
SUB_Y = 1560      # 字幕の上端（画面下の方。SNSの操作ボタンに隠れにくい高さ）
SUB_COLOR = (250, 246, 236, 255)   # 古い映画の字幕のような、少しだけ温かい白

SIZE_DUR = 1.5
NARR_LEN = 4.17
BRAND_DUR = NARR_LEN + 0.5 - SIZE_DUR
BGM_START = 172.05   # 曲の盛り上がりが始まる位置（秒）

# 古いフィルムの質感（画面は一切動かさない。色・粒子・周りの暗さだけ）
FILM = ("eq=contrast=0.93:saturation=0.74:brightness=0.012:gamma=1.02,"
        "colorbalance=rs=0.05:gs=0.01:bs=-0.07:rm=0.04:gm=0.0:bm=-0.05:rh=0.03:gh=0.0:bh=-0.06,"
        "curves=all='0/0.055 0.5/0.52 1/0.95',"
        "vignette=angle=PI/4.6,"
        "noise=c0s=15:c0f=t+u:c1s=5:c1f=t+u:c2s=5:c2f=t+u")
FILM_LIGHT = ("eq=saturation=0.9:contrast=0.97,"
              "colorbalance=rh=0.025:bh=-0.04:rm=0.02:bm=-0.03,"
              "vignette=angle=PI/6,"
              "noise=c0s=6:c0f=t+u")
# 光もれ（場所, 出始め, 消える時刻）。ポスターに重ならない画面のふちに出す
LEAKS = [("left", 3.7, 5.3), ("right", 8.3, 9.9), ("leftlow", 12.6, 14.0)]


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


def leak_png(kind, path):
    """光もれ：画面のふちからにじむ淡いオレンジ〜赤の光（透明度つき）。"""
    W, H = 1080, 1920
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    if kind == "left":
        cx, cy, rx, ry, col = -60, 1250, 640, 950, (255, 140, 60)
    elif kind == "right":
        cx, cy, rx, ry, col = W + 60, 1350, 640, 1000, (255, 110, 50)
    else:
        cx, cy, rx, ry, col = -40, 1700, 720, 720, (255, 160, 80)
    dist = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    a = np.clip(1.0 - dist, 0, 1) ** 1.3 * 0.62
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = col
    rgba[..., 3] = (a * 255).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(path)


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
    leaks = []
    for i, (k, _, _) in enumerate(LEAKS, 1):
        p = work / f"leak-{i}.png"
        leak_png(k, p)
        leaks.append(p)

    norm = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p"
    fc = [f"[{i}:v]trim=duration={CLIP_LEN},setpts=PTS-STARTPTS,{norm}[a{i}]" for i in range(3)]
    fc += [f"[a0][a1]xfade=transition=fadeblack:duration={FADE}:offset={T2}[x1]",
           f"[x1][a2]xfade=transition=fadeblack:duration={FADE}:offset={T3},format=yuv420p,{FILM}[f0]"]
    last = "f0"
    n_sub = len(subs)
    leak_base = 7 + n_sub
    for i, (_, s, e) in enumerate(LEAKS):
        idx = leak_base + i
        mid = (s + e) / 2
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={s}:d={mid - s}:alpha=1,fade=t=out:st={mid}:d={e - mid}:alpha=1[l{i}]")
        fc.append(f"[{last}][l{i}]overlay=0:0:enable='between(t,{s},{e})'[f{i + 1}]")
        last = f"f{i + 1}"
    for i, (_, s, e) in enumerate(SUBS):
        idx = 7 + i
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={s}:d=0.25:alpha=1,fade=t=out:st={e - 0.25}:d=0.25:alpha=1[s{i}]")
        fc.append(f"[{last}][s{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
        last = f"m{i + 1}"
    fc += [
        f"[3:v]scale=1080:1920,fps=30,format=yuv420p,trim=duration={SIZE_DUR},setpts=PTS-STARTPTS,{FILM}[vs]",
        f"[5:v]scale=1080:1920:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS,{FILM_LIGHT}[vb]",
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
    for p in subs + leaks:
        cmd += ["-loop", "1", "-framerate", "30", "-t", str(MAIN), "-i", str(p)]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "21", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"DONE {OUT.name}  length {total:.2f}s")


if __name__ == "__main__":
    main()
