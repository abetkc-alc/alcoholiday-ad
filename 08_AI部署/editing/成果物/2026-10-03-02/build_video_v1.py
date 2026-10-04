# ALCOHOLIDAY editing部：Tシャツ「1966 ISLAY WAS FRUIT」宣伝動画（2026-10-03-02）
#   見本：2026-10-03-01/build_video_v1.py（字幕版）をもとに、話しかける人物動画用に組み直し
#   - 社長指示：最初に PNG_1966_ISLAY_BLUE.png を入れる／締めを含めて15秒／声は後から付ける（本編は無音）
#   - 流れ：デザイン画像 → ①真顔で話す（シュール）→ ②Tシャツのアップ → ③笑顔（暖かい）→ 締め画像＋ナレーション
#   - 字幕は①の口の動き（素材の 0.6〜2.3秒 と 2.8〜4.5秒）に合わせてある
#   - 素材はループ・逆再生・長い静止で伸ばさない（各素材の一部を切り出して使うだけ）
# 使い方: python build_video_v1.py v1
import pathlib
import subprocess
import sys

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VER = sys.argv[1] if len(sys.argv) > 1 else "v1"
HERE = pathlib.Path(__file__).parent
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TITLE = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\画像\商品画像\ORIGINAL\PNG_1966_ISLAY_BLUE.png")
# (素材, 使い始め秒, 使う長さ)
CLIPS = [(HERE / "b-talk-kling3-v1.mp4", 0.0, 4.6),     # ①話す
         (HERE / "closeup-kling3-v2.mp4", 0.0, 1.25),   # ②Tシャツのアップ（1.375秒からすそを引く動きで文字がゆがむので、その前まで）
         (HERE / "smile-kling3-v2.mp4", 0.25, 3.3)]     # ③笑顔（3.75秒から文字が斜めになるので、その前まで）
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
OUT = HERE / f"tshirt1966-sns-{VER}.mp4"

TITLE_DUR = 1.4
T1 = TITLE_DUR                       # ①の開始
T2 = T1 + CLIPS[0][2]                # ②の開始
T3 = T2 + CLIPS[1][2]                # ③の開始
MAIN = T3 + CLIPS[2][2]              # 本編の長さ
BRAND_DUR = 15.0 - MAIN              # 締め（合計15秒にそろえる）
NARR_LEN = 4.17

# 字幕（文字, 表示開始, 表示終了）— 台本 案A
SUBS = [("シングルモルトを", T1 + 0.6, T1 + 1.5),
        ("知らないと、", T1 + 1.5, T1 + 2.4),
        ("この意味は、", T1 + 2.8, T1 + 3.6),
        ("わからない。", T1 + 3.6, T2 - 0.05),
        ("わかったら、乾杯。", T3 + 1.5, MAIN - 0.1)]
SUB_SIZE = 58
SUB_Y = 1560


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
    for p in [TITLE, BRAND, NARR] + [c[0] for c in CLIPS]:
        if not p.exists():
            raise SystemExit(f"素材が見つかりません: {p}")
    if BRAND_DUR < NARR_LEN + 0.1:
        raise SystemExit(f"締めが短すぎてナレーションが切れます: {BRAND_DUR:.2f}s")
    work = HERE / f"work-{VER}"
    work.mkdir(exist_ok=True)
    # 冒頭のデザイン画像は背景が透明なので、白地に重ねてから使う
    title = work / "title.png"
    im = Image.open(TITLE).convert("RGBA")
    Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im).convert("RGB").save(title)
    subs = []
    for i, (t, _, _) in enumerate(SUBS, 1):
        p = work / f"sub-{i}.png"
        subtitle_png(t, p)
        subs.append(p)

    norm = "scale=1080:1920:flags=lanczos,fps=30,format=yuv420p,setsar=1"
    fc = [f"[0:v]scale=1080:1920,fps=30,format=yuv420p,setsar=1,trim=duration={TITLE_DUR},setpts=PTS-STARTPTS[t0]"]
    for i, (_, ss, dur) in enumerate(CLIPS):
        fc.append(f"[{i + 1}:v]trim=start={ss}:duration={dur},setpts=PTS-STARTPTS,{norm}[c{i}]")
    fc.append("[t0][c0][c1][c2]concat=n=4:v=1:a=0,format=yuv420p[m0]")
    last = "m0"
    base_idx = 7
    for i, (_, s, e) in enumerate(SUBS):
        idx = base_idx + i
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={s}:d=0.15:alpha=1,fade=t=out:st={e - 0.15}:d=0.15:alpha=1[s{i}]")
        fc.append(f"[{last}][s{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
        last = f"m{i + 1}"
    fc += [
        f"[{last}]trim=duration={MAIN},setpts=PTS-STARTPTS[vm]",
        f"[4:v]scale=1080:1920:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,setsar=1,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
        "[vm][vb]concat=n=2:v=1:a=0,format=yuv420p[outv]",
        # 本編は無音（声・曲は後から付ける）。締めはナレーションのみ
        # （anullsrc を filter の中で作ると終わりが来ず、メモリを使い続けて止まった → 長さを決めた入力にする）
        f"[6:a]asetpts=PTS-STARTPTS[sil]",
        f"[5:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{BRAND_DUR},asetpts=PTS-STARTPTS,volume=1.6,apad=whole_dur={BRAND_DUR}[narr]",
        "[sil][narr]concat=n=2:v=0:a=1[outa]",
    ]
    total = MAIN + BRAND_DUR
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-loop", "1", "-framerate", "30", "-t", str(TITLE_DUR), "-i", str(title)]
    for p, _, _ in CLIPS:
        cmd += ["-i", str(p)]
    cmd += ["-loop", "1", "-framerate", "30", "-t", str(BRAND_DUR), "-i", str(BRAND),
            "-i", str(NARR),
            "-f", "lavfi", "-t", str(MAIN), "-i", "anullsrc=r=48000:cl=stereo"]
    for p in subs:
        cmd += ["-loop", "1", "-framerate", "30", "-t", str(total), "-i", str(p)]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"DONE {OUT.name}  length {total:.2f}s  (本編 {MAIN:.2f}s + 締め {BRAND_DUR:.2f}s)")


if __name__ == "__main__":
    main()
