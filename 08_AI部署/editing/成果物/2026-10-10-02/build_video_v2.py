# ALCOHOLIDAY editing部：Tシャツ「1966 ISLAY WAS FRUIT」宣伝動画（案内役A／2026-10-10-02）v2
#   v2（2026-10-10 社長の直し）：「落ち着いた動画に」「動画が進むにつれて前回の動画と顔が同じになる → 元画像に忠実に」
#     「乾杯するときは画像が二重で違和感 → 訂正」
#   → ①③を、動きの小さい・やさしい声の素材に作り直した（①は A.png、③は A.png の腕だけグラスを持たせた写真から）
#   → プリントの直しは、文字のところだけ重ねる fix_print_track_v2.py に（v1 は布ごとの四角を重ね、袖・腕が二重に見えた）
#   ②アップは v1 と同じ素材（顔が出ない・グラスがゆっくり回るだけで落ち着いている）
#   以下は v1 の説明
#   2026-10-10 社長指示：案内役Aの女性で、2026-10-03-02（build_video_v3.py）と同じスタイル。前回より少し動きのある動画。話し方は明るく朗らか。
#   流れ：①明るく話しかける（冒頭に白いデザインを重ねる・声・字幕）→ ②Tシャツのアップ（グラスの氷が回る・カモメの声）
#         → ③満面の笑顔で乾杯（声「かんぱい！」）→ 商品画像 → 締め画像＋ナレーション（合計15秒）
#   - ①③は体が動くのでプリントの文字が崩れた → 最初のコマのプリントを、体の動き（ずれ・傾き・大きさ）に合わせて重ねて直した -fix.mp4 を使う（fix_print_track.py）
#     声は元の素材から取る（-fix.mp4 は映像だけ）
#   - 字幕は①の声の文字起こし（faster-whisper）の時刻に合わせてある。③の「かんぱい！」は字幕なし（前回「わかったら、乾杯。」の字幕は外す指示だったため）
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
SOUND = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\音声")
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TITLE = ORIG / "PNG_1966_ISLAY_BLUE.png"
PRODUCT = HERE / "Tshirt_1966_BL-fixed.png"   # 価格表示を INCLUDING TAX に直した画像（2026-10-03-02 v7 と同じ）
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
GULL = SOUND / "アップしたもの" / "カモメ 5.mp3"
MUSIC = SOUND / "backmusic" / "2_23_AM.mp3"
TALK_AUDIO = HERE / "a-talk-kling3-sound-v2.mp4"
CHEERS_AUDIO = HERE / "cheers-kling3-sound-v2.mp4"
OUT = HERE / f"tshirt1966-A-sns-{VER}.mp4"

# (素材, 使い始め秒, 使う長さ)
CLIPS = [(HERE / "a-talk-kling3-sound-v2-fix.mp4", 0.0, 4.7),   # ①話す（落ち着いた版。0.54秒から話し始め、4.6秒で話し終わる）
         (HERE / "closeup-kling3-v1-fix.mp4", 0.4, 1.8),        # ②アップ（グラスの氷が回る。2.5秒から6の形が変わったので前半だけ・プリントも重ねて直した版）
         (HERE / "cheers-kling3-sound-v2-fix.mp4", 0.6, 2.7)]   # ③乾杯（落ち着いた版。グラスを少し上げ、1.6〜2.2秒で「乾杯。」、そのあとやさしい笑顔）

TITLE_SHOW = 0.75
TITLE_FADE = 0.3
TITLE_COLOR = (255, 255, 255)
PRODUCT_DUR = 1.5
T1 = 0.0
T2 = T1 + CLIPS[0][2]
T3 = T2 + CLIPS[1][2]
MAIN = T3 + CLIPS[2][2]
BRAND_DUR = 15.0 - MAIN - PRODUCT_DUR
NARR_LEN = 4.17

MUSIC_SS = 12.0
MUSIC_LOW = 0.10     # ①の声の間
MUSIC_HIGH = 0.5     # アップ以降
MUSIC_DUCK = 0.22    # ③の「かんぱい！」の間
GULL_VOL = 0.9
CHEERS_VOICE = (T3 + 1.5 - CLIPS[2][1], T3 + 2.4 - CLIPS[2][1])  # 「かんぱい！」の完成動画での時刻


def at(t):
    return T1 + t - CLIPS[0][1]


SUBS = [("ねえ、この意味わかる？", TITLE_SHOW + TITLE_FADE, at(2.35)),
        ("シングルモルト好きなら、", at(2.45), at(3.78)),
        ("わかるよね。", at(3.78), T2 - 0.05)]
SUB_SIZE = 58
SUB_Y = 1560


def subtitle_png(text, path):
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
    for p in [TITLE, PRODUCT, BRAND, NARR, GULL, MUSIC, TALK_AUDIO, CHEERS_AUDIO] + [c[0] for c in CLIPS]:
        if not p.exists():
            raise SystemExit(f"素材が見つかりません: {p}")
    if BRAND_DUR < NARR_LEN + 0.1:
        raise SystemExit(f"締めが短すぎてナレーションが切れます: {BRAND_DUR:.2f}s")
    work = HERE / f"work-{VER}"
    work.mkdir(exist_ok=True)
    title = work / "title-overlay.png"
    im = Image.open(TITLE).convert("RGBA")
    im = Image.merge("RGBA", (*Image.new("RGB", im.size, TITLE_COLOR).split(), im.getchannel("A")))
    im.save(title)
    subs = []
    for i, (t, _, _) in enumerate(SUBS, 1):
        p = work / f"sub-{i}.png"
        subtitle_png(t, p)
        subs.append(p)

    # 入力の番号：0 デザイン／1〜3 素材／4 締め画像／5 ナレーション／6 無音／7 商品画像／8 カモメ／9 曲／10 ①の声／11 ③の声／12〜 字幕
    norm = "scale=1080:1920:flags=lanczos,fps=30,format=yuv420p,setsar=1"
    fc = []
    for i, (_, ss, dur) in enumerate(CLIPS):
        fc.append(f"[{i + 1}:v]trim=start={ss}:duration={dur},setpts=PTS-STARTPTS,{norm}[c{i}]")
    fc.append("[c0][c1][c2]concat=n=3:v=1:a=0,format=yuv420p[m0]")
    tend = TITLE_SHOW + TITLE_FADE
    fc.append(f"[0:v]format=rgba,fade=t=out:st={TITLE_SHOW}:d={TITLE_FADE}:alpha=1[ti]")
    fc.append(f"[m0][ti]overlay=0:0:enable='between(t,0,{tend})'[mt]")
    last = "mt"
    for i, (_, s, e) in enumerate(SUBS):
        fc.append(f"[{12 + i}:v]format=rgba,fade=t=in:st={s}:d=0.15:alpha=1,fade=t=out:st={e - 0.15}:d=0.15:alpha=1[s{i}]")
        fc.append(f"[{last}][s{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
        last = f"m{i + 1}"
    body = MAIN + PRODUCT_DUR
    c3ss, c3d = CLIPS[2][1], CLIPS[2][2]
    d1, d2 = CHEERS_VOICE
    fc += [
        f"[{last}]trim=duration={MAIN},setpts=PTS-STARTPTS[vm]",
        f"[7:v]scale=1080:1920,fps=30,format=yuv420p,setsar=1,trim=duration={PRODUCT_DUR},setpts=PTS-STARTPTS[vp]",
        f"[4:v]scale=1080:1920:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,setsar=1,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
        "[vm][vp][vb]concat=n=3:v=1:a=0,format=yuv420p[outv]",
        # 声の線：①の声 → アップの間は無音 → ③の声（かんぱい！と氷の音）→ 商品画像の間は無音
        f"[10:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=start={CLIPS[0][1]}:duration={CLIPS[0][2]},asetpts=PTS-STARTPTS,"
        f"afade=t=out:st={CLIPS[0][2] - 0.08}:d=0.08,volume=1.4[voice1]",
        f"[6:a]atrim=0:{CLIPS[1][2]},asetpts=PTS-STARTPTS[sil1]",
        f"[11:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=start={c3ss}:duration={c3d},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=0.05,afade=t=out:st={c3d - 0.15}:d=0.15,volume=1.4[voice3]",
        f"[6:a]atrim=0:{PRODUCT_DUR},asetpts=PTS-STARTPTS[sil2]",
        "[voice1][sil1][voice3][sil2]concat=n=4:v=0:a=1[vline]",
        f"[8:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={GULL_VOL},"
        f"afade=t=out:st=1.4:d=0.6,adelay={int(T2 * 1000)}|{int(T2 * 1000)},apad,atrim=0:{body}[gull]",
        # 曲：①の声の間は小さく、アップから大きく、「かんぱい！」の間は少し下げ、締めの前に消す
        f"[9:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{body},asetpts=PTS-STARTPTS,"
        f"volume='if(lt(t,{T2 - 0.15}),{MUSIC_LOW},if(lt(t,{T2 + 0.25}),{MUSIC_LOW}+({MUSIC_HIGH}-{MUSIC_LOW})*(t-{T2 - 0.15})/0.4,"
        f"if(between(t,{d1},{d2}),{MUSIC_DUCK},{MUSIC_HIGH})))':eval=frame,"
        f"afade=t=in:st=0:d=0.3,afade=t=out:st={body - 1.0}:d=1.0[bgm]",
        "[vline][gull][bgm]amix=inputs=3:duration=first:normalize=0[mixbody]",
        f"[5:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{BRAND_DUR},asetpts=PTS-STARTPTS,volume=1.6,apad=whole_dur={BRAND_DUR}[narr]",
        "[mixbody][narr]concat=n=2:v=0:a=1[outa]",
    ]
    total = MAIN + PRODUCT_DUR + BRAND_DUR
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-loop", "1", "-framerate", "30", "-t", str(tend), "-i", str(title)]
    for p, _, _ in CLIPS:
        cmd += ["-i", str(p)]
    cmd += ["-loop", "1", "-framerate", "30", "-t", str(BRAND_DUR), "-i", str(BRAND),
            "-i", str(NARR),
            "-f", "lavfi", "-t", "15", "-i", "anullsrc=r=48000:cl=stereo",
            "-loop", "1", "-framerate", "30", "-t", str(PRODUCT_DUR), "-i", str(PRODUCT),
            "-i", str(GULL),
            "-ss", str(MUSIC_SS), "-t", str(body + 0.5), "-i", str(MUSIC),
            "-i", str(TALK_AUDIO), "-i", str(CHEERS_AUDIO)]
    for p in subs:
        cmd += ["-loop", "1", "-framerate", "30", "-t", str(total), "-i", str(p)]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"DONE {OUT.name}  length {total:.2f}s  (main {MAIN:.2f}s + product {PRODUCT_DUR:.2f}s + brand {BRAND_DUR:.2f}s)")


if __name__ == "__main__":
    main()
