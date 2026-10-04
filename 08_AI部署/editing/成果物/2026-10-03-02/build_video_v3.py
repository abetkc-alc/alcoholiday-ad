# ALCOHOLIDAY editing部：Tシャツ「1966 ISLAY WAS FRUIT」宣伝動画（2026-10-03-02）v3
#   v2（build_video_v2.py）からの変更（2026-10-03 社長指示）
#   - 最初のデザイン画像を透かして、背景（①の映像）が見えるように：白いもやを薄くかけた①の冒頭に、デザインを重ねてから消す
#   - Tシャツのアップを長く：布を動かさないアップ（closeup-kling3-v5）に差し替え
#   - アップに切り替わる瞬間に、カモメの声（カモメ 5.mp3）
#   - 音楽 2_23_AM.mp3：声の間は小さく、アップから大きく、締めの前に消す（締めはナレーションだけ）
#   流れ：①真顔で話す（冒頭にデザインを重ねる・声）→ ②アップ（カモメ）→ ③やわらかい笑顔 → 商品画像 → 締め画像＋ナレーション（合計15秒）
#   - 字幕は①の声の文字起こし（faster-whisper）の時刻に合わせてある
#   - 素材はループ・逆再生・長い静止で伸ばさない（各素材の一部を切り出して使うだけ）
# 使い方: python build_video_v3.py v3
import pathlib
import subprocess
import sys

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VER = sys.argv[1] if len(sys.argv) > 1 else "v3"
HERE = pathlib.Path(__file__).parent
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
ORIG = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\画像\商品画像\ORIGINAL")
SOUND = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\音声")
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TITLE = ORIG / "PNG_1966_ISLAY_BLUE.png"
PRODUCT = ORIG / "Tshirt_1966_BL.png"
# v7〜：価格表示のつづりを「INCLUDINT TAX」→「INCLUDING TAX」に直した画像（T を同じ書体 Bebas Neue の G に差し替え。元画像はそのまま）
PRODUCT = HERE / "Tshirt_1966_BL-fixed.png"
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
GULL = SOUND / "アップしたもの" / "カモメ 5.mp3"
MUSIC = SOUND / "backmusic" / "2_23_AM.mp3"
OUT = HERE / f"tshirt1966-sns-{VER}.mp4"

# (素材, 使い始め秒, 使う長さ)
CLIPS = [(HERE / "b-talk-kling3-sound-v3.mp4", 0.0, 4.8),   # ①話す（声あり。0.78秒から話し始め、4.70秒で話し終わる）
         (HERE / "closeup-kling3-v5-fix4.mp4", 0.0, 2.0),  # ②アップ（布を動かさない版。0.8秒から文字が崩れたので、最初のコマのプリントを重ねて直した版：fix_closeup_print.py）
         (HERE / "smile-kling3-v4.mp4", 1.6, 2.4)]          # ③やわらかい笑顔（2秒あたりから微笑む）

TITLE_SHOW = 0.75    # デザインをはっきり見せる時間
TITLE_FADE = 0.3     # そのあと消えていく時間
TITLE_COLOR = (255, 255, 255)  # デザインの色（v6 で社長指示「白（明るい色）に変える」。紺のままだと暗い背景に沈んだ）。None なら元の紺
VEIL = 0.0           # デザインの下にかける白いもやの濃さ（v3/v4 は0.55。v5 で社長指示「背景の白を消して重ねる」により0）
PRODUCT_DUR = 1.5
T1 = 0.0
T2 = T1 + CLIPS[0][2]                # ②の開始
T3 = T2 + CLIPS[1][2]                # ③の開始
MAIN = T3 + CLIPS[2][2]              # 本編（商品画像の前まで）の長さ
BRAND_DUR = 15.0 - MAIN - PRODUCT_DUR  # 締め（合計15秒にそろえる）
NARR_LEN = 4.17

MUSIC_SS = 12.0      # 曲が一段盛り上がる所から使う（1秒ごとの音の大きさで確認）
MUSIC_LOW = 0.10     # 声の間（声を邪魔しない大きさ。v3 の0.16では声と曲の差が小さかった）
MUSIC_HIGH = 0.5     # アップ以降
GULL_VOL = 0.9


def at(t):
    """①の素材の時刻 → 完成動画の時刻"""
    return T1 + t - CLIPS[0][1]


# 字幕（文字, 表示開始, 表示終了）— 声の文字起こしの時刻（素材の秒）に合わせる
# 最初の字幕は、デザインが消えてから出す
SUBS = [("シングルモルトを", TITLE_SHOW + TITLE_FADE, at(1.80)),
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
    for p in [TITLE, PRODUCT, BRAND, NARR, GULL, MUSIC] + [c[0] for c in CLIPS]:
        if not p.exists():
            raise SystemExit(f"素材が見つかりません: {p}")
    if BRAND_DUR < NARR_LEN + 0.1:
        raise SystemExit(f"締めが短すぎてナレーションが切れます: {BRAND_DUR:.2f}s")
    work = HERE / f"work-{VER}"
    work.mkdir(exist_ok=True)
    # 冒頭：白いもや（半透明）＋デザイン（背景は透明のまま）を1枚にして、①の映像の上に重ねる
    title = work / "title-overlay.png"
    im = Image.open(TITLE).convert("RGBA")
    if TITLE_COLOR:
        # 形（透明度）はそのまま、色だけ塗り替える
        im = Image.merge("RGBA", (*Image.new("RGB", im.size, TITLE_COLOR).split(), im.getchannel("A")))
    veil = Image.new("RGBA", im.size, (255, 255, 255, int(255 * VEIL)))
    Image.alpha_composite(veil, im).save(title)
    subs = []
    for i, (t, _, _) in enumerate(SUBS, 1):
        p = work / f"sub-{i}.png"
        subtitle_png(t, p)
        subs.append(p)

    # 入力の番号：0 デザイン（もや付き）／1〜3 素材／4 締め画像／5 ナレーション／6 無音／7 商品画像／8 カモメ／9 曲／10〜 字幕
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
        fc.append(f"[{10 + i}:v]format=rgba,fade=t=in:st={s}:d=0.15:alpha=1,fade=t=out:st={e - 0.15}:d=0.15:alpha=1[s{i}]")
        fc.append(f"[{last}][s{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
        last = f"m{i + 1}"
    rest = MAIN - T2 + PRODUCT_DUR   # ②③と商品画像の間
    body = MAIN + PRODUCT_DUR        # 締めの前まで
    fc += [
        f"[{last}]trim=duration={MAIN},setpts=PTS-STARTPTS[vm]",
        f"[7:v]scale=1080:1920,fps=30,format=yuv420p,setsar=1,trim=duration={PRODUCT_DUR},setpts=PTS-STARTPTS[vp]",
        f"[4:v]scale=1080:1920:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,setsar=1,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
        "[vm][vp][vb]concat=n=3:v=1:a=0,format=yuv420p[outv]",
        # 声の線：①の声 → 以降は無音（締めの前まで）
        f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=start={CLIPS[0][1]}:duration={CLIPS[0][2]},asetpts=PTS-STARTPTS,"
        f"afade=t=out:st={CLIPS[0][2] - 0.08}:d=0.08,volume=1.4[voice]",
        f"[6:a]atrim=0:{rest},asetpts=PTS-STARTPTS[sil]",
        "[voice][sil]concat=n=2:v=0:a=1[vline]",
        # カモメ：アップに切り替わる瞬間から
        f"[8:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={GULL_VOL},"
        f"afade=t=out:st=3.0:d=0.6,adelay={int(T2 * 1000)}|{int(T2 * 1000)},apad,atrim=0:{body}[gull]",
        # 曲：声の間は小さく、アップから大きく、締めの前に消す
        f"[9:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{body},asetpts=PTS-STARTPTS,"
        f"volume='if(lt(t,{T2 - 0.15}),{MUSIC_LOW},if(lt(t,{T2 + 0.25}),{MUSIC_LOW}+({MUSIC_HIGH}-{MUSIC_LOW})*(t-{T2 - 0.15})/0.4,{MUSIC_HIGH}))':eval=frame,"
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
            "-ss", str(MUSIC_SS), "-t", str(body + 0.5), "-i", str(MUSIC)]
    for p in subs:
        cmd += ["-loop", "1", "-framerate", "30", "-t", str(total), "-i", str(p)]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"DONE {OUT.name}  length {total:.2f}s  (main {MAIN:.2f}s + product {PRODUCT_DUR:.2f}s + brand {BRAND_DUR:.2f}s)")


if __name__ == "__main__":
    main()
