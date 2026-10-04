# ALCOHOLIDAY editing部：指示 2026-09-27-01（ワイン 金曜の夜・台本A「ごほうび」）の組み立て
# 使い方: python build_video.py v1
# 構成: 角度4実写 → 黒フェード → 角度5実写 → 黒フェード → 角度2実写 → ポスターへズーム → ズーム静止
#       → サイズ比較写真 → 締め画像＋ナレーション（必須）
# ルール: ループ・逆再生・長い静止で尺を伸ばさない。既存ファイルは上書きしない。
import pathlib
import subprocess
import sys

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

VER = sys.argv[1] if len(sys.argv) > 1 else "v1"
HERE = pathlib.Path(__file__).parent
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
FONT = r"C:\Users\abetk\AppData\Local\CapCut\User Data\Cache\effect\6740439840254333443\92988aefce8a45c8fd7fe58a60fc72cc\特黑体-思源黑体1号.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

CLIPS = [HERE / "wine-friday-angle4-kling-v1.mp4",
         HERE / "wine-friday-angle5-kling-v1.mp4",
         HERE / "wine-friday-angle2-kling-v1.mp4"]
SIZE_IMG = SHARED / "product-assets" / "wine-size.png"
MUSIC = SHARED / "music" / "alcoholiday-selected-2_23_AM.mp3"
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
OUT = HERE / f"wine-friday-sns-{VER}.mp4"

# 画面の文字（台本A）と表示する時間（秒）
# （文字, 表示開始, 表示終了, 上からの位置px）。ポスターに寄る場面ではポスターの英語の一文と重ならない位置にする
CAPTIONS = [("金曜の夜、乾杯。", 0.5, 3.5, 1190),
            ("頑張った私に。", 4.1, 7.5, 1190),
            ("秋のはじまりに。", 11.6, 15.4, 1620)]

FADE = 0.4           # 角度の間の黒フェード
C1, C2, C3 = 4.0, 4.5, 4.5   # 各実写の使用秒数（素材は約5秒。これより長くしない）
ZOOM, HOLD = 2.4, 0.8        # 最後の実写のあとポスターへズーム → 静止
ZOOM_MAX = 1.25
ZOOM_X, ZOOM_Y = 0.50, 0.33  # 角度2の画面内でのポスター中心（横・縦の割合）
SIZE_DUR = 1.5
NARR_LEN = 4.17
BRAND_DUR = NARR_LEN + 0.5 - SIZE_DUR
BGM_SILENCE = 0.7

MAIN = C1 + C2 + (C3 + ZOOM + HOLD) - 2 * FADE


def caption_png(text, path, y=1190):
    """これまでの動画と同じ見た目：幅940px・80px・白文字＋濃い縁取り（標準は上から1190px）。"""
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 80)
    w = d.textlength(text, font=f)
    if w > 940:
        raise SystemExit(f"文字が長すぎて1行に収まりません: {text}")
    d.text(((1080 - w) / 2, y), text, font=f, fill="white", stroke_width=3, stroke_fill=(25, 20, 16, 210))
    im.save(path)


def main():
    if OUT.exists():
        raise SystemExit(f"すでにあります（上書きしません）: {OUT.name}")
    for p in CLIPS + [SIZE_IMG, MUSIC, BRAND, NARR]:
        if not p.exists():
            raise SystemExit(f"素材が見つかりません: {p}")
    work = HERE / f"work-{VER}"
    work.mkdir(exist_ok=True)
    caps = []
    for i, (t, _, _, y) in enumerate(CAPTIONS, 1):
        p = work / f"caption-{i}.png"
        caption_png(t, p, y)
        caps.append(p)

    norm = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p"
    c3_frames = int(C3 * 30)
    zoom_done = int((C3 + ZOOM) * 30)
    z = (f"if(lt(on\\,{c3_frames})\\,1\\,if(lt(on\\,{zoom_done})\\,"
         f"1+{ZOOM_MAX - 1}*sqrt((on-{c3_frames})/{int(ZOOM * 30)})\\,{ZOOM_MAX}))")
    zx = f"max(0\\,min(iw-iw/zoom\\,iw*{ZOOM_X}-(iw/zoom)/2))"
    zy = f"max(0\\,min(ih-ih/zoom\\,ih*{ZOOM_Y}-(ih/zoom)/2))"
    off1 = C1 - FADE
    off2 = C1 + C2 - 2 * FADE

    fc = [
        f"[0:v]trim=duration={C1},setpts=PTS-STARTPTS,{norm}[a1]",
        f"[1:v]trim=duration={C2},setpts=PTS-STARTPTS,{norm}[a2]",
        f"[2:v]trim=duration={C3},setpts=PTS-STARTPTS,{norm},tpad=stop_mode=clone:stop_duration={ZOOM + HOLD},"
        f"zoompan=z='{z}':x='{zx}':y='{zy}':d=1:s=1080x1920:fps=30,format=yuv420p[a3]",
        f"[a1][a2]xfade=transition=fadeblack:duration={FADE}:offset={off1}[x1]",
        f"[x1][a3]xfade=transition=fadeblack:duration={FADE}:offset={off2},format=yuv420p[m0]",
    ]
    last = "m0"
    for i, (_, s, e, _) in enumerate(CAPTIONS):
        idx = 7 + i
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={s}:d=0.2:alpha=1,fade=t=out:st={e - 0.2}:d=0.2:alpha=1[c{i}]")
        fc.append(f"[{last}][c{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
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
    cmd = [FFMPEG, "-hide_banner", "-y",
           "-i", str(CLIPS[0]), "-i", str(CLIPS[1]), "-i", str(CLIPS[2]),
           "-loop", "1", "-framerate", "30", "-t", str(SIZE_DUR), "-i", str(SIZE_IMG),
           "-i", str(MUSIC),
           "-loop", "1", "-framerate", "30", "-t", str(BRAND_DUR), "-i", str(BRAND),
           "-i", str(NARR)]
    for p in caps:
        cmd += ["-loop", "1", "-framerate", "30", "-t", str(total), "-i", str(p)]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"DONE {OUT.name}  予定の長さ {total:.2f}秒")


if __name__ == "__main__":
    main()
