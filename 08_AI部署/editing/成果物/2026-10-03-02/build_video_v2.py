# ALCOHOLIDAY editing部：Tシャツ「1966 ISLAY WAS FRUIT」宣伝動画（2026-10-03-02）v2
#   v1（build_video_v1.py）からの変更（2026-10-03 社長指示）
#   - ①を声ありの素材（Kling 3.0 音声あり）に差し替え：セリフの音声
#   - ③は WAS FRUIT まで映る写真から作り直した、やわらかい笑顔に差し替え
#   - 「わかったら、乾杯。」の字幕はなし
#   - 締めの前に商品画像（Tshirt_1966_BL.png）を入れる
#   流れ：デザイン画像 → ①真顔で話す（声）→ ②Tシャツのアップ → ③やわらかい笑顔 → 商品画像 → 締め画像＋ナレーション（合計15秒）
#   - 字幕は①の声の文字起こし（faster-whisper）の時刻に合わせてある
#   - 素材はループ・逆再生・長い静止で伸ばさない（各素材の一部を切り出して使うだけ）
# 使い方: python build_video_v2.py v2
import pathlib
import subprocess
import sys

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VER = sys.argv[1] if len(sys.argv) > 1 else "v2"
HERE = pathlib.Path(__file__).parent
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
ORIG = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\画像\商品画像\ORIGINAL")
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TITLE = ORIG / "PNG_1966_ISLAY_BLUE.png"
PRODUCT = ORIG / "Tshirt_1966_BL.png"
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
OUT = HERE / f"tshirt1966-sns-{VER}.mp4"

TALK_SS = 0.5    # ①の使い始め（0.78秒から話し始めるので、その前の無言の見つめを少し残す）
SMILE_SS = 1.5   # ③の使い始め（2秒あたりから微笑み始めるので、笑顔が長く映るように）
# (素材, 使い始め秒, 使う長さ)
CLIPS = [(HERE / "b-talk-kling3-sound-v3.mp4", TALK_SS, 4.3),    # ①話す（声あり。4.70秒で話し終わる）
         (HERE / "closeup-kling3-v2.mp4", 0.0, 1.25),            # ②アップ（1.375秒から文字がゆがむので、その前まで）
         (HERE / "smile-kling3-v4.mp4", SMILE_SS, 2.65)]         # ③やわらかい笑顔

TITLE_DUR = 1.0
PRODUCT_DUR = 1.5
T1 = TITLE_DUR                       # ①の開始
T2 = T1 + CLIPS[0][2]                # ②の開始
T3 = T2 + CLIPS[1][2]                # ③の開始
MAIN = T3 + CLIPS[2][2]              # 本編（商品画像の前まで）の長さ
BRAND_DUR = 15.0 - MAIN - PRODUCT_DUR  # 締め（合計15秒にそろえる）
NARR_LEN = 4.17


def at(t):
    """①の素材の時刻 → 完成動画の時刻"""
    return T1 + t - TALK_SS


# 字幕（文字, 表示開始, 表示終了）— 声の文字起こしの時刻（素材の秒）に合わせる
SUBS = [("シングルモルトを", at(0.78), at(1.80)),
        ("知らないと、", at(1.80), at(2.45)),
        ("この意味は、", at(2.50), at(3.80)),
        ("わからない。", at(3.80), T2 - 0.05)]
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
    for p in [TITLE, PRODUCT, BRAND, NARR] + [c[0] for c in CLIPS]:
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

    # 入力の番号：0 デザイン画像／1〜3 素材／4 締め画像／5 ナレーション／6 無音／7 商品画像／8〜 字幕
    norm = "scale=1080:1920:flags=lanczos,fps=30,format=yuv420p,setsar=1"
    fc = [f"[0:v]scale=1080:1920,fps=30,format=yuv420p,setsar=1,trim=duration={TITLE_DUR},setpts=PTS-STARTPTS[t0]"]
    for i, (_, ss, dur) in enumerate(CLIPS):
        fc.append(f"[{i + 1}:v]trim=start={ss}:duration={dur},setpts=PTS-STARTPTS,{norm}[c{i}]")
    fc.append("[t0][c0][c1][c2]concat=n=4:v=1:a=0,format=yuv420p[m0]")
    last = "m0"
    for i, (_, s, e) in enumerate(SUBS):
        fc.append(f"[{8 + i}:v]format=rgba,fade=t=in:st={s}:d=0.15:alpha=1,fade=t=out:st={e - 0.15}:d=0.15:alpha=1[s{i}]")
        fc.append(f"[{last}][s{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
        last = f"m{i + 1}"
    rest = MAIN - T2 + PRODUCT_DUR   # ②③と商品画像の間（無音）
    fc += [
        f"[{last}]trim=duration={MAIN},setpts=PTS-STARTPTS[vm]",
        f"[7:v]scale=1080:1920,fps=30,format=yuv420p,setsar=1,trim=duration={PRODUCT_DUR},setpts=PTS-STARTPTS[vp]",
        f"[4:v]scale=1080:1920:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,setsar=1,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
        "[vm][vp][vb]concat=n=3:v=1:a=0,format=yuv420p[outv]",
        # 音：デザイン画像の間は無音 → ①の声（素材の音そのまま）→ ②③商品画像は無音 → 締めでナレーション
        # （anullsrc を filter の中で作ると終わりが来ず止まった → 長さを決めた入力 [6] を分けて使う）
        "[6:a]asplit=2[z1][z2]",
        f"[z1]atrim=0:{T1},asetpts=PTS-STARTPTS[sil1]",
        f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=start={TALK_SS}:duration={CLIPS[0][2]},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=0.05,afade=t=out:st={CLIPS[0][2] - 0.08}:d=0.08,volume=1.4[voice]",
        f"[z2]atrim=0:{rest},asetpts=PTS-STARTPTS[sil2]",
        f"[5:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{BRAND_DUR},asetpts=PTS-STARTPTS,volume=1.6,apad=whole_dur={BRAND_DUR}[narr]",
        "[sil1][voice][sil2][narr]concat=n=4:v=0:a=1[outa]",
    ]
    total = MAIN + PRODUCT_DUR + BRAND_DUR
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-loop", "1", "-framerate", "30", "-t", str(TITLE_DUR), "-i", str(title)]
    for p, _, _ in CLIPS:
        cmd += ["-i", str(p)]
    cmd += ["-loop", "1", "-framerate", "30", "-t", str(BRAND_DUR), "-i", str(BRAND),
            "-i", str(NARR),
            "-f", "lavfi", "-t", "15", "-i", "anullsrc=r=48000:cl=stereo",
            "-loop", "1", "-framerate", "30", "-t", str(PRODUCT_DUR), "-i", str(PRODUCT)]
    for p in subs:
        cmd += ["-loop", "1", "-framerate", "30", "-t", str(total), "-i", str(p)]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"DONE {OUT.name}  length {total:.2f}s  (main {MAIN:.2f}s + product {PRODUCT_DUR:.2f}s + brand {BRAND_DUR:.2f}s)")


if __name__ == "__main__":
    main()
