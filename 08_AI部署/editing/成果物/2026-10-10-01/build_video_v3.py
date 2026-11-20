# ALCOHOLIDAY editing部：指示 2026-10-10-01 日本酒・連休に同級生と昼飲み 動画 v3（2回目の動画づくり）
#   build_video_v2.py をコピーし、素材だけ社長が作り直した写真（4回目）の動画に差し替えた。古いフィルムの質感（FILM）・字幕・光もれ・音楽は v2 と同じ
#   - 写真の順（社長が選んだ順）：引き(angle1-v7) → 乾杯の直前(angle2-v2) → アップ(angle3-v1)。台本 案B の場面の順と同じ
#   - 1回目への社長の直し「乾杯の動きが不自然。おちょこが長くなる・突然葉の影」→ 乾杯はお猪口がふれ合うだけ、葉の影なし
# 使い方: python build_video_v3.py v3
import pathlib
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VER = sys.argv[1] if len(sys.argv) > 1 else "v3"
HERE = pathlib.Path(__file__).parent
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# 社長が選んだ順（崩れた区間を直した版があればそちらを使う）
CLIP1 = "sake-holiday4-hiki-kling-v3-fix.mp4"   # 右の手が1秒すぎから大きく持ち上がり不自然 → 手の所を0.42秒のコマで覆った版（fix_hiki_hand_v3.py）
CLIP2 = "sake-holiday4-kanpai-kling-v3.mp4"   # 0.4〜3.33秒お猪口がふれ合い、3.38秒から離れ始める → 最初の3.4秒だけ使う
CLIP3 = "sake-holiday4-up-kling-v3.mp4"
CLIPS = [HERE / CLIP1,   # 引き（右のネルシャツの人の手が少し動く）
         HERE / CLIP2,   # 乾杯の直前（お猪口どうしがそっとふれ合う）
         HERE / CLIP3]   # アップ（壁とポスターだけ。光がごく弱く変わる）
SIZE_IMG = SHARED / "product-assets" / "sake-size.png"
MUSIC = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\音声\backmusic\週末京都現実逃避.mp3")
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
OUT = HERE / f"sake-holiday-{VER}.mp4"

LENS = [5.0, 3.4, 5.0]   # 各実写の使用秒数（素材は約5.04秒。乾杯は離れ始める前の3.4秒まで）
FADE = 0.4       # 実写の間の黒フェード
T2 = LENS[0] - FADE              # 2本目が見え始める時刻 4.6
T3 = T2 + LENS[1] - FADE         # 3本目 7.6
MAIN = T3 + LENS[2]              # 12.6

# 字幕（文字, 表示開始, 表示終了）— 台本 案B（各場面の中の位置は台本どおり、順番も台本どおり）
SUBS = [("NO JAPANESE SAKE, NO LIFE.", 0.3, 2.0),
        ("暇な同級生、来訪。", 2.3, T2 - 0.1),
        ("話は、いつもの話。", T2 + 0.2, T2 + 1.6),
        ("オチは、ない。", T2 + 1.75, T3 - 0.1),
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
LEAKS = [("left", 3.7, 5.3), ("right", 6.9, 8.5), ("leftlow", 11.0, 12.4)]


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
    fc = [f"[{i}:v]trim=duration={LENS[i]},setpts=PTS-STARTPTS,{norm}[a{i}]" for i in range(3)]
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
