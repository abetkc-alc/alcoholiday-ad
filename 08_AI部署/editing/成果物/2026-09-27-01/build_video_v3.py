# ALCOHOLIDAY editing部：指示 2026-09-27-01 ワイン動画 v3（2026-09-27 社長指摘をすべて反映した版）
#   - 最初の文字は「NO WINE, NO LIFE.」（どの商品も NO ○○, NO LIFE. で始める）
#   - 文字は映画の字幕風（画面下・落ち着いた白文字・細い縁取り＋うっすら影）
#   - ポスターは一切動かさない：後からのズームはしない。最後はクローズアップ写真の実写をそのまま使う
#   - 最後は必ず締め画像＋ナレーション
# 使い方: python build_video_v3.py v3
import pathlib
import subprocess
import sys

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VER = sys.argv[1] if len(sys.argv) > 1 else "v3"
HERE = pathlib.Path(__file__).parent
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# 社長が選んだ順
CLIPS = [HERE / "wine-3shot-naka-kling-v1.mp4",   # 中ぐらいのアップ
         HERE / "wine-3shot-hiki-kling-v1.mp4",   # 引き
         HERE / "wine-3shot-up-kling-v1.mp4"]     # アップ（最後。ズームはしない）
SIZE_IMG = SHARED / "product-assets" / "wine-size.png"
MUSIC = SHARED / "music" / "alcoholiday-selected-2_23_AM.mp3"
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
OUT = HERE / f"wine-friday-sns-{VER}.mp4"

CLIP_LEN = 4.5   # 各実写の使用秒数（素材は約5秒。これより長くしない）
FADE = 0.4       # 実写の間の黒フェード
T2 = CLIP_LEN - FADE             # 2本目が見え始める時刻
T3 = 2 * CLIP_LEN - 2 * FADE     # 3本目
MAIN = 3 * CLIP_LEN - 2 * FADE

# 字幕（文字, 表示開始, 表示終了）
SUBS = [("NO WINE, NO LIFE.", 0.3, 2.2),
        ("金曜の夜、乾杯。", 2.4, T2 - 0.1),
        ("頑張った私に。", T2 + 0.4, T3 - 0.1),
        ("秋のはじまりに。", T3 + 0.5, MAIN - 0.2)]
SUB_SIZE = 58
SUB_Y = 1560      # 字幕の上端（画面下の方。SNSの操作ボタンに隠れにくい高さ）

SIZE_DUR = 1.5
NARR_LEN = 4.17
BRAND_DUR = NARR_LEN + 0.5 - SIZE_DUR
BGM_SILENCE = 0.7


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
    ImageDraw.Draw(base).text((x, SUB_Y), text, font=f, fill=(255, 255, 255, 255),
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
    fc = [f"[{i}:v]trim=duration={CLIP_LEN},setpts=PTS-STARTPTS,{norm}[a{i}]" for i in range(3)]
    fc += [f"[a0][a1]xfade=transition=fadeblack:duration={FADE}:offset={T2}[x1]",
           f"[x1][a2]xfade=transition=fadeblack:duration={FADE}:offset={T3},format=yuv420p[m0]"]
    last = "m0"
    for i, (_, s, e) in enumerate(SUBS):
        idx = 7 + i
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={s}:d=0.25:alpha=1,fade=t=out:st={e - 0.25}:d=0.25:alpha=1[s{i}]")
        fc.append(f"[{last}][s{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
        last = f"m{i + 1}"
    fc += [
        f"[3:v]scale=1080:1920,fps=30,format=yuv420p,trim=duration={SIZE_DUR},setpts=PTS-STARTPTS[vs]",
        f"[5:v]scale=1080:1920:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
        f"[{last}]trim=duration={MAIN},setpts=PTS-STARTPTS[vm]",
        "[vm][vs][vb]concat=n=3:v=1:a=0,format=yuv420p[outv]",
        f"[4:a]atrim=start={BGM_SILENCE}:end={BGM_SILENCE + MAIN},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=0.3,afade=t=out:st={MAIN - 1.0}:d=1.0,volume=0.55[bgm]",
        f"[6:a]atrim=0:{SIZE_DUR + BRAND_DUR},asetpts=PTS-STARTPTS,volume=1.6,apad=whole_dur={SIZE_DUR + BRAND_DUR}[narr]",
        "[bgm][narr]concat=n=2:v=0:a=1[outa]",
    ]
    total = MAIN + SIZE_DUR + BRAND_DUR
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-i", str(CLIPS[0]), "-i", str(CLIPS[1]), "-i", str(CLIPS[2]),
           "-loop", "1", "-framerate", "30", "-t", str(SIZE_DUR), "-i", str(SIZE_IMG),
           "-i", str(MUSIC),
           "-loop", "1", "-framerate", "30", "-t", str(BRAND_DUR), "-i", str(BRAND),
           "-i", str(NARR)]
    for p in subs:
        cmd += ["-loop", "1", "-framerate", "30", "-t", str(total), "-i", str(p)]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"DONE {OUT.name}  length {total:.2f}s")


if __name__ == "__main__":
    main()
