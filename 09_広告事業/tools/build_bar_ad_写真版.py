# ALCOHOLIDAY 広告事業：BARのおすすめ紹介動画の組み立て（editing部）
#   流れ（約15〜16秒・縦1080×1920）：
#     ① 案内役がカメラに話す（Kling 3.0・声あり）＋字幕
#     ② お客さんの商品写真（実物の写真。動かさない・ズームしない）＋商品名・価格
#     ③ 案内役が微笑む（Kling 3.0）＋お店の情報（店名・場所・営業時間）
#     ④ ALCOHOLIDAY の締め画像＋ナレーション「お酒との時間をもっと楽しく」（必ず入れる）
#   ・左上に「PR」を出し続ける（広告であることの表示）。③にお酒の注意書きを入れる
#   ・素材はループ・逆再生・長い静止で伸ばさない（各素材の一部を切り出して使うだけ）
#
# 使い方: python tools/build_bar_ad.py 案件/<受付番号>/制作.json
#   制作.json の例は 09_広告事業/広告事業.md の「動画の型」を見る。ファイルの場所は 制作.json のあるフォルダから見た位置
import json
import pathlib
import subprocess
import sys

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
NARR_LEN = 4.17
BRAND_DUR = 4.4
FONT_B = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FONT_H = r"C:\Windows\Fonts\SourceHanSansJP-Heavy.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920
GOLD = (241, 196, 107, 255)
NOTICE = "お酒は20歳になってから。飲酒運転は法律で禁止されています。"

MUSIC_LOW = 0.10    # 声の間
MUSIC_HIGH = 0.45   # 声のあと


def font(size, heavy=False):
    p = FONT_H if heavy and pathlib.Path(FONT_H).exists() else FONT_B
    return ImageFont.truetype(p, size)


def wrap(d, text, f, maxw):
    """日本語を1文字ずつ見て、横幅に収まるように折り返す"""
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=f) > maxw and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    return lines + ([cur] if cur else [])


def text_center(d, y, text, f, fill, maxw=940, gap=1.25, stroke=0):
    # 「」の前で改行（「季節のフルーツカクテル／「桃のベリーニ」」のように、名前を途中で切らない）。改行は \n でも指定できる
    parts = text.replace("「", "\n「").lstrip("\n").split("\n") if d.textlength(text, font=f) > maxw else text.split("\n")
    lines = [ln for p in parts for ln in wrap(d, p.strip(), f, maxw)]
    for line in lines:
        w = d.textlength(line, font=f)
        d.text(((W - w) / 2, y), line, font=f, fill=fill, stroke_width=stroke, stroke_fill=(15, 12, 10, 220))
        y += int(f.size * gap)
    return y


def subtitle_png(text, path, y=1560, size=58):
    f = font(size)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    w = d.textlength(text, font=f)
    if w > 900:
        raise SystemExit(f"字幕が長すぎて1行に収まりません（9文字前後に）: {text}")
    x = (W - w) / 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((x + 2, y + 3), text, font=f, fill=(0, 0, 0, 170))
    base = Image.alpha_composite(base, shadow.filter(ImageFilter.GaussianBlur(4)))
    ImageDraw.Draw(base).text((x, y), text, font=f, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(20, 20, 20, 200))
    base.save(path)


def pr_badge(path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((48, 96, 148, 150), radius=10, fill=(20, 16, 12, 170), outline=(255, 255, 255, 230), width=2)
    f = font(32)
    w = d.textlength("PR", font=f)
    d.text((98 - w / 2, 100), "PR", font=f, fill=(255, 255, 255, 255))
    im.save(path)


def photo_card(src, product, price, path):
    """お客さんの写真：背景は同じ写真をぼかして暗く、中央に写真そのもの（切らない・ゆがめない）"""
    ph = Image.open(src).convert("RGB")
    bg = ph.copy()
    r = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * r) + 1, int(bg.height * r) + 1), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    bg = bg.filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (10, 8, 6)), 0.55).convert("RGBA")
    box_w, box_h = 960, 1080
    s = min(box_w / ph.width, box_h / ph.height)
    fg = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS)
    x, y = (W - fg.width) // 2, 260 + (box_h - fg.height) // 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x + 8, y + 14, x + fg.width + 8, y + fg.height + 14), radius=18, fill=(0, 0, 0, 160))
    bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(18)))
    mask = Image.new("L", fg.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fg.width, fg.height), radius=18, fill=255)
    bg.paste(fg, (x, y), mask)
    d = ImageDraw.Draw(bg)
    yy = text_center(d, 1400, product, font(66, heavy=True), (255, 255, 255, 255), stroke=2)
    if price:
        text_center(d, yy + 14, price, font(46), GOLD, stroke=2)
    bg.convert("RGB").save(path, quality=95)


def shop_overlay(shop, area, hours, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = Image.new("L", (1, H), 0)
    for yy in range(H):
        grad.putpixel((0, yy), int(200 * max(0, min(1, (yy - 1080) / 360))))
    im.paste(Image.new("RGBA", (W, H), (10, 8, 6, 255)), (0, 0), grad.resize((W, H)))
    d = ImageDraw.Draw(im)
    y = 1330
    d.line((440, y, 640, y), fill=GOLD, width=3)
    y = text_center(d, y + 28, shop, font(70, heavy=True), (255, 255, 255, 255))
    for t in (area, hours):
        if t:
            y = text_center(d, y + 6, t, font(38), (235, 225, 210, 255))
    text_center(d, 1800, NOTICE, font(26), (210, 200, 185, 230), maxw=1000)
    im.save(path)


def main():
    spec_path = pathlib.Path(sys.argv[1]).resolve()
    S = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    rel = lambda p: (base / p) if not pathlib.Path(p).is_absolute() else pathlib.Path(p)
    out = rel(S["out"])
    if out.exists():
        raise SystemExit(f"すでにあります（上書きしません）: {out}")
    talk, smile = S["talk"], S["smile"]
    for p in [rel(talk["file"]), rel(smile["file"]), rel(S["photo"]), rel(S["music"]), BRAND, NARR]:
        if not p.exists():
            raise SystemExit(f"素材が見つかりません: {p}")
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / f"work-{out.stem}"
    work.mkdir(exist_ok=True)

    T_TALK, T_PHOTO, T_SMILE = talk["dur"], S.get("photo_dur", 3.0), smile["dur"]
    t2 = T_TALK
    t3 = t2 + T_PHOTO
    body = t3 + T_SMILE
    total = body + BRAND_DUR
    if BRAND_DUR < NARR_LEN + 0.1:
        raise SystemExit("締めが短すぎます")

    pr = work / "pr.png"
    pr_badge(pr)
    card = work / "photo-card.jpg"
    photo_card(rel(S["photo"]), S["product"], S.get("price", ""), card)
    shop = work / "shop.png"
    shop_overlay(S["shop"], S.get("area", ""), S.get("hours", ""), shop)
    subs = []
    for i, (t, s, e) in enumerate(S.get("subs", []), 1):
        p = work / f"sub-{i}.png"
        subtitle_png(t, p)
        subs.append((p, s - talk["start"], e - talk["start"]))

    # 入力：0 話す／1 微笑む／2 商品カード／3 店の情報／4 PR／5 締め画像／6 ナレーション／7 曲／8 無音／9〜 字幕
    norm = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps=30,format=yuv420p,setsar=1"
    fc = [
        f"[0:v]trim=start={talk['start']}:duration={T_TALK},setpts=PTS-STARTPTS,{norm}[v0]",
        f"[2:v]scale={W}:{H},fps=30,format=yuv420p,setsar=1,trim=duration={T_PHOTO},setpts=PTS-STARTPTS[v1]",
        f"[1:v]trim=start={smile['start']}:duration={T_SMILE},setpts=PTS-STARTPTS,{norm}[v2r]",
        f"[3:v]format=rgba,fade=t=in:st=0.15:d=0.3:alpha=1[shop]",
        "[v2r][shop]overlay=0:0:shortest=1[v2]",
        "[v0][v1][v2]concat=n=3:v=1:a=0,format=yuv420p[m0]",
    ]
    last = "m0"
    for i, (_, s, e) in enumerate(subs):
        fc.append(f"[{9 + i}:v]format=rgba,fade=t=in:st={s}:d=0.12:alpha=1,fade=t=out:st={e - 0.12}:d=0.12:alpha=1[s{i}]")
        fc.append(f"[{last}][s{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
        last = f"m{i + 1}"
    fc += [
        f"[{last}][4:v]overlay=0:0:shortest=1,trim=duration={body},setpts=PTS-STARTPTS[vm]",
        f"[5:v]scale={W}:{H}:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,setsar=1,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
        "[vm][vb]concat=n=2:v=1:a=0,format=yuv420p[outv]",
        f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=start={talk['start']}:duration={T_TALK},asetpts=PTS-STARTPTS,"
        f"afade=t=out:st={T_TALK - 0.08}:d=0.08,volume={S.get('voice_vol', 1.4)}[voice]",
        f"[8:a]atrim=0:{body - T_TALK},asetpts=PTS-STARTPTS[sil]",
        "[voice][sil]concat=n=2:v=0:a=1[vline]",
        f"[7:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{body},asetpts=PTS-STARTPTS,"
        f"volume='if(lt(t,{t2 - 0.15}),{MUSIC_LOW},if(lt(t,{t2 + 0.25}),{MUSIC_LOW}+({MUSIC_HIGH}-{MUSIC_LOW})*(t-{t2 - 0.15})/0.4,{MUSIC_HIGH}))':eval=frame,"
        f"afade=t=in:st=0:d=0.3,afade=t=out:st={body - 1.0}:d=1.0[bgm]",
        "[vline][bgm]amix=inputs=2:duration=first:normalize=0[mixbody]",
        f"[6:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{BRAND_DUR},asetpts=PTS-STARTPTS,volume=1.6,apad=whole_dur={BRAND_DUR}[narr]",
        "[mixbody][narr]concat=n=2:v=0:a=1[outa]",
    ]
    img = lambda p, t: ["-loop", "1", "-framerate", "30", "-t", str(t), "-i", str(p)]
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-i", str(rel(talk["file"])), "-i", str(rel(smile["file"]))]
    cmd += img(card, T_PHOTO) + img(shop, T_SMILE) + img(pr, body) + img(BRAND, BRAND_DUR)
    cmd += ["-i", str(NARR), "-ss", str(S.get("music_ss", 0)), "-t", str(body + 0.5), "-i", str(rel(S["music"])),
            "-f", "lavfi", "-t", "20", "-i", "anullsrc=r=48000:cl=stereo"]
    for p, _, _ in subs:
        cmd += img(p, body)
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print(f"DONE {out}  {total:.2f}s（話す {T_TALK} + 写真 {T_PHOTO} + 微笑む {T_SMILE} + 締め {BRAND_DUR}）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
