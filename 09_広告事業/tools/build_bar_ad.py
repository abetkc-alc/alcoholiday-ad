# ALCOHOLIDAY 広告事業：BARのおすすめ紹介動画の組み立て（お客さんが撮った動画3本版）
#   流れ（縦1080×1920・約13〜16秒＋締め4.4秒）：
#     ① 動画1（お店の雰囲気）＋ナレーション＋字幕
#     ② 動画2（おすすめ商品）＋ナレーション＋字幕＋商品名・価格
#     ③ 動画3（自由）＋ナレーション＋字幕＋店名・場所・営業時間・お酒の注意書き
#     ④ ALCOHOLIDAY の締め画像＋ナレーション「お酒との時間をもっと楽しく」（無料版だけ）
#   ・無料版と有料版（2026-10-10 社長の指示。制作.json の "plan"：free／paid。書いていなければ無料版）
#       無料版：①〜③のあいだ、画面の上下に ALCOHOLIDAY のロゴを透かしで出す（商品名・店名は上の透かしの分だけ下げる）＋④の締め
#       有料版（2026-10-11 社長の指示で変更）：透かし・④の締め・金色の線はなし。最後に、商品の動画（動画2）の終わりの3.5秒を足し、
#               映像が見えるように少し暗くして、商品名・価格と、上下のまん中に「紹介したお店・商品の詳細はキャプションから。」、
#               下に小さく「Designed by」と ALCOHOLIDAY のロゴ
#   ・ナレーションは案内役（A＝ローズ／B＝ラフィ／C＝アイラ）の声で AI が読む（tools/narrate.py）
#   ・各動画の長さは「ナレーションの長さ＋少しの間」。足りないときは止める（静止・ループ・逆再生で伸ばさない）
#   ・お客さんの動画の音は使わない（音楽＋ナレーション）。左上に「PR」を出し続ける
#   ・音楽は、制作.json の "music" が空なら入れない（申し込みページの「音楽なし」。2026-10-11）
#   ・動画1のあいだ、右上に投稿日（制作.json の "date"：2026-10-05 の形）を出す
#   ・横向きの動画は、ぼかした同じ映像を背景にして、切らずに真ん中に置く。iPhone の HDR 動画は色を直す
#
# 使い方: python tools/build_bar_ad.py 案件/<受付番号>/制作.json
#   制作.json の例は 09_広告事業/広告事業.md の「動画の型」を見る。ファイルの場所は 制作.json のあるフォルダから見た位置
import json
import pathlib
import re
import subprocess
import sys

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import narrate  # noqa: E402

SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
# 締め画像は BAR広告専用（アマゾンの案内を外し「紹介したお店の詳細はキャプションから。」を大きく・赤枠と赤文字で目立たせたもの）。
# 元の ending-title.jpg は ALCOHOLIDAY 自身の動画用なので変えない
BRAND = pathlib.Path(__file__).resolve().parent.parent / "素材" / "ending-bar-v5.jpg"   # v5＝「紹介したお店・商品の詳細はキャプションから。」（2026-10-10 社長の指示。v4 は「お店の詳細」）
LOGO = pathlib.Path(__file__).resolve().parent.parent / "素材" / "ブランドロゴ.png"   # 黒文字・背景なし（元：Desktop/ALCOHOLIDAY/画像/商品画像/ブランドロゴ.png）。白くして使う
WM_W, WM_ALPHA = 380, 0.55          # 無料版の透かし：幅と濃さ（2026-10-10 社長の指示で 240→380 に大きく）
WM_TOP, WM_BOTTOM = 165, 1638       # 透かしの上の位置（PR と日付の下）と下の位置（字幕の下・注意書きの上）
FREE_SHIFT = 140                    # 無料版は上の透かしの分、商品名・店名を下げる
END_SEC = 3.5                       # 有料版の締め（商品の動画＋文字）の長さ（2026-10-11 2秒→3.5秒）
END_TEXT = "紹介したお店・商品の詳細は\nキャプションから。"
END_SIGN = "Designed by"   # このあとに ALCOHOLIDAY のロゴ
NARR_END = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
NARR_END_LEN = 4.17
BRAND_DUR = 4.4
FONT_B = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FONT_H = r"C:\Windows\Fonts\SourceHanSansJP-Heavy.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920
GOLD = (241, 196, 107, 255)
NOTICE = "お酒は20歳になってから。飲酒運転は法律で禁止されています。"
LIMITED = "数量に限りがありますので、品切れの際は予めご了承ください。"   # 数量限定の商品のとき（制作.json の "limited": true）

LEAD = 0.35         # 動画が始まってから声が出るまで
TAIL = 0.55         # 声が終わってから次の動画まで
MIN_CLIP = 3.0      # 1本の最短
TARGET_CLIP = 4.5   # 動画が足りていれば、この長さまで使う（声が長ければ声に合わせる）
MUSIC_VOL = 0.13    # 声の後ろの音楽
VOICE_VOL = 1.25


def font(size, heavy=False):
    p = FONT_H if heavy and pathlib.Path(FONT_H).exists() else FONT_B
    return ImageFont.truetype(p, size)


NO_HEAD = "）」』】、。，．！？ー〜…・)]!?,."   # 行の頭に来てはいけない文字


def wrap(d, text, f, maxw):
    """横幅に収まるように折り返す。数字・英字のかたまり（200円 など）は切らず、空白があればそこで改行する"""
    units = re.findall(r"\s+|[0-9A-Za-z.,%:]+円?|.", text)
    lines, cur = [], ""
    for u in units:
        if u.isspace():
            if cur:
                cur += " "
            continue
        if d.textlength(cur + u, font=f) > maxw and cur.strip() and u[0] not in NO_HEAD:
            # 行の中に空白があれば、最後の空白で改行する（言葉の途中で切らない）
            sp = cur.rstrip().rfind(" ")
            if sp > 0 and d.textlength(cur[sp + 1:] + u, font=f) <= maxw:
                lines.append(cur[:sp].rstrip())
                cur = cur[sp + 1:] + u
            else:
                lines.append(cur.rstrip())
                cur = u
        else:
            cur += u
    return lines + ([cur.strip()] if cur.strip() else [])


def split_lines(d, text, f, maxw=940):
    # 長いときは「 や （ の前で改行する（名前やかっこを途中で切らない）。改行は \n でも指定できる
    parts = re.sub(r"([「（(])", "\n\\1", text).lstrip("\n").split("\n") if d.textlength(text, font=f) > maxw else text.split("\n")
    return [ln for p in parts for ln in wrap(d, p.strip(), f, maxw)]


def text_center(d, y, text, f, fill, maxw=940, gap=1.25, stroke=0):
    lines = split_lines(d, text, f, maxw)
    for line in lines:
        w = d.textlength(line, font=f)
        d.text(((W - w) / 2, y), line, font=f, fill=fill, stroke_width=stroke, stroke_fill=(15, 12, 10, 220))
        y += int(f.size * gap)
    return y


def subtitle_png(text, path, y=1540, size=60):
    f = font(size)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    w = d.textlength(text, font=f)
    if w > 960:
        raise SystemExit(f"字幕が長すぎて1行に収まりません（15文字くらいまでに）: {text}")
    x = (W - w) / 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((x + 2, y + 3), text, font=f, fill=(0, 0, 0, 190))
    base = Image.alpha_composite(base, shadow.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(base).text((x, y), text, font=f, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(20, 20, 20, 220))
    base.save(path)


def pr_badge(path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((48, 96, 148, 150), radius=10, fill=(20, 16, 12, 170), outline=(255, 255, 255, 230), width=2)
    f = font(32)
    w = d.textlength("PR", font=f)
    d.text((98 - w / 2, 100), "PR", font=f, fill=(255, 255, 255, 255))
    im.save(path)


def white_logo(width, alpha):
    """ロゴを白くして、指定の幅と濃さにする"""
    lg = Image.open(LOGO).convert("RGBA")
    im = Image.new("RGBA", lg.size, (255, 255, 255, 0))
    im.putalpha(lg.getchannel("A").point(lambda v: int(v * alpha)))
    return im.resize((width, round(lg.height * width / lg.width)), Image.LANCZOS)


def paste_logo(im, logo, x, y, shadow=90):
    """明るい映像の上でも見えるように、うすい影をつけて置く"""
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", logo.size, (0, 0, 0, shadow)), (x + 2, y + 3), logo)
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    im.alpha_composite(logo, (x, y))


def watermark(im):
    """無料版：画面の上下のまん中に、ALCOHOLIDAY のロゴを透かしで置く"""
    lg = white_logo(WM_W, WM_ALPHA)
    for y in (WM_TOP, WM_BOTTOM):
        paste_logo(im, lg, (W - lg.width) // 2, y, shadow=60)


def end_png(path, product, price, limited=False):
    """有料版の締め：映像が透けて見えるくらいに暗くし、上下のまん中に案内の文字、その上に商品名と価格、
    下に小さく「Designed by」と ALCOHOLIDAY のロゴ（線は入れない）。数量限定の商品なら、価格の下に LIMITED の文も入れる"""
    im = Image.new("RGBA", (W, H), (10, 8, 6, 120))
    d = ImageDraw.Draw(im)
    white, edge = (255, 255, 255, 255), (15, 12, 10, 230)
    # 案内の文字：文字のかたまりの上下のまん中を、画面の上下のまん中（960）に合わせる
    f = font(66, heavy=True)
    lines, step = END_TEXT.split("\n"), int(66 * 1.4)
    box = d.textbbox((0, 0), lines[0], font=f)
    block = step * (len(lines) - 1) + (box[3] - box[1])
    y = H / 2 - block / 2 - box[1]
    top = y + box[1]
    for line in lines:
        b = d.textbbox((0, 0), line, font=f)
        d.text(((W - (b[2] - b[0])) / 2 - b[0], y), line, font=f, fill=white, stroke_width=3, stroke_fill=edge)
        y += step
    # 商品名と価格：案内の文字の上に、下からそろえて置く
    fp = next((font(sz, heavy=True) for sz in (60, 52, 46) if len(split_lines(d, product, font(sz, heavy=True))) <= 2), font(46, heavy=True))
    pl = split_lines(d, product, fp)
    fpr = font(46)
    fl = font(30)
    hl = len(split_lines(d, LIMITED, fl, 980)) * int(fl.size * 1.25) + 10 if limited else 0
    hp = len(pl) * int(fp.size * 1.25) + (int(fpr.size * 1.25) + 8 if price else 0) + hl
    yy = top - 110 - hp
    yy = text_center(d, yy, product, fp, white, stroke=2)
    if price:
        yy = text_center(d, yy + 8, price, fpr, GOLD, stroke=2)
    if limited:
        text_center(d, yy + 10, LIMITED, fl, (255, 255, 255, 240), maxw=980, stroke=2)
    # 下：「Designed by」＋ロゴ（1行に並べる）
    fs = font(32)
    lg = white_logo(230, 0.95)
    sw = d.textlength(END_SIGN, font=fs)
    gap = 16
    x = (W - (sw + gap + lg.width)) / 2
    cy = 1790
    sb = d.textbbox((0, 0), END_SIGN, font=fs)
    d.text((x, cy - (sb[1] + sb[3]) / 2), END_SIGN, font=fs, fill=(255, 255, 255, 235), stroke_width=2, stroke_fill=(15, 12, 10, 200))
    paste_logo(im, lg, int(x + sw + gap), int(cy - lg.height / 2))
    im.save(path)


WEEK = "月火水木金土日"


def date_chip(path, date):
    """投稿日を、PR と同じ高さの右上に文字だけで出す（例：2026年10月5日（日））"""
    import datetime
    dt = datetime.date.fromisoformat(str(date)[:10])
    text = f"{dt.year}年{dt.month}月{dt.day}日（{WEEK[dt.weekday()]}）"
    im = Image.open(path).convert("RGBA")
    d = ImageDraw.Draw(im)
    # 枠や塗りはつけず、文字だけ（字幕と同じ影と縁どりで、明るい映像の上でも読めるようにする）
    f = font(46)
    w = d.textlength(text, font=f)
    x, y = W - 48 - w, 92
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((x + 2, y + 3), text, font=f, fill=(0, 0, 0, 190))
    im = Image.alpha_composite(im, shadow.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(im).text((x, y), text, font=f, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(20, 20, 20, 220))
    im.save(path)


def soft_shadow(im):
    """文字のうしろにだけ、うすい影をつける（画面の上下を黒くしない。2026-10-16 社長の指示で上下の黒いグラデーションをやめた）"""
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: min(255, int(v * 0.8)))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 255))
    sh.putalpha(a)
    return Image.alpha_composite(sh, im)


def product_overlay(product, price, path, limited=False, top=210, line=True):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = top
    if line:
        d.line((440, y, 640, y), fill=GOLD, width=3)
    # 商品名が長いときは、2行に収まるまで文字を小さくする（64 → 56 → 50）
    f = next((font(sz, heavy=True) for sz in (64, 56, 50) if len(split_lines(d, product, font(sz, heavy=True))) <= 2), font(50, heavy=True))
    y = text_center(d, y + 26, product, f, (255, 255, 255, 255), stroke=3)
    if price:
        y = text_center(d, y + 8, price, font(46), GOLD, stroke=3)
    if limited:
        text_center(d, y + 10, LIMITED, font(30), (255, 255, 255, 240), maxw=980, stroke=2)
    soft_shadow(im).save(path)


def shop_overlay(shop, area, hours, path, top=210, line=True):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = top
    if line:
        d.line((440, y, 640, y), fill=GOLD, width=3)
    y = text_center(d, y + 26, shop, font(68, heavy=True), (255, 255, 255, 255), stroke=3)
    for t in (area, hours):
        if t:
            y = text_center(d, y + 4, t, font(38), (240, 230, 215, 255), stroke=3)
    text_center(d, 1810, NOTICE, font(27), (225, 215, 200, 240), maxw=1000, stroke=2)
    soft_shadow(im).save(path)


def plain_overlay(path):
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(path)


def probe(path):
    """長さ・縦横・回転・HDR かどうかを調べる（ffmpeg の表示から読む）"""
    err = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if not m:
        raise SystemExit(f"動画を読めません: {path}")
    dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    v = re.search(r"Stream #.*Video:.*?(\d{2,5})x(\d{2,5})", err)
    w, h = int(v[1]), int(v[2])
    rot = re.search(r"rotation of (-?[\d.]+)", err)
    if rot and abs(abs(float(rot[1])) - 90) < 1:
        w, h = h, w
    hdr = bool(re.search(r"arib-std-b67|smpte2084", err))
    return {"dur": dur, "w": w, "h": h, "hdr": hdr}


def video_filter(idx, info, dur, label):
    tone = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p," if info["hdr"] else "")
    head = f"[{idx}:v]{tone}fps=30,trim=duration={dur},setpts=PTS-STARTPTS"
    if info["h"] / info["w"] >= 1.3:   # 縦の動画：画面いっぱい
        return [f"{head},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,format=yuv420p[{label}]"]
    # 横・正方形の動画：切らずに真ん中へ。背景は同じ映像をぼかして暗く
    return [
        f"{head},split[{label}a][{label}b]",
        f"[{label}a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3,eq=brightness=-0.12,setsar=1[{label}bg]",
        f"[{label}b]scale={W}:-2:flags=lanczos,setsar=1[{label}fg]",
        f"[{label}bg][{label}fg]overlay=0:(H-h)/2,format=yuv420p[{label}]",
    ]


def main():
    spec_path = pathlib.Path(sys.argv[1]).resolve()
    S = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    rel = lambda p: (base / p) if not pathlib.Path(p).is_absolute() else pathlib.Path(p)
    out = rel(S["out"])
    if out.exists():
        raise SystemExit(f"すでにあります（上書きしません）: {out}")
    clips = S["clips"]
    paid = S.get("plan", "free") == "paid"
    if S.get("plan", "free") not in ("free", "paid"):
        raise SystemExit(f"plan は free か paid です: {S.get('plan')}")
    for p in [rel(c["file"]) for c in clips] + ([rel(S["music"])] if S.get("music") else []) + [LOGO] + ([] if paid else [BRAND, NARR_END]):
        if not p.exists():
            raise SystemExit(f"素材が見つかりません: {p}")
    if BRAND_DUR < NARR_END_LEN + 0.1:
        raise SystemExit("締めが短すぎます")
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / f"work-{out.stem}"
    work.mkdir(exist_ok=True)

    # 1) ナレーションをつくり、各動画の長さを決める
    voice = S.get("voice", "A")
    t, plan = 0.0, []
    for i, c in enumerate(clips, 1):
        wav = work / f"narr-{i}.wav"
        nd = narrate.synth(voice, c["narr"], wav)
        info = probe(rel(c["file"]))
        start = c.get("start", 0.0)
        need = max(MIN_CLIP, LEAD + nd + TAIL)
        dur = round(c.get("dur") or max(need, min(TARGET_CLIP, info["dur"] - start - 0.1)), 2)
        if start + dur > info["dur"] - 0.05:
            raise SystemExit(f"動画{i}が足りません：{dur:.2f}秒必要・使えるのは {info['dur'] - start:.2f}秒（{c['file']}）。"
                             "ナレーションを短くするか start を前にする")
        plan.append({"c": c, "wav": wav, "nd": nd, "dur": dur, "start": start, "info": info, "t0": t})
        print(f"動画{i}：{c['file']} {start:.1f}秒から {dur:.2f}秒（声 {nd:.2f}秒{'・HDR' if info['hdr'] else ''}"
              f"{'・横' if info['h'] / info['w'] < 1.3 else ''}）")
        t += dur
    body = t
    total = body + (END_SEC if paid else BRAND_DUR)
    if paid:   # 締めに使う商品の動画（show が product の動画。なければ2本目）の、終わりの END_SEC 秒
        pc = next((p for p in plan if p["c"].get("show") == "product"), plan[min(1, len(plan) - 1)])
        end_clip = {"file": rel(pc["c"]["file"]), "info": pc["info"], "start": round(max(0.0, pc["info"]["dur"] - END_SEC - 0.1), 2)}
        if pc["info"]["dur"] < END_SEC + 0.1:
            raise SystemExit(f"締めに使う商品の動画が短すぎます（{END_SEC}秒必要）: {pc['c']['file']}")

    # 2) 文字の画像
    pr = work / "pr.png"
    pr_badge(pr)
    if not paid:   # 無料版：PR といっしょに、上下の透かしを動画①〜③のあいだずっと出す
        im = Image.open(pr).convert("RGBA")
        watermark(im)
        im.save(pr)
    endcard = work / "end.png"
    if paid:
        end_png(endcard, S["product"], S.get("price", ""), S.get("limited", False))
    top = 210 + (0 if paid else FREE_SHIFT)
    overlays, subs = [], []
    for i, p in enumerate(plan, 1):
        ov = work / f"overlay-{i}.png"
        show = p["c"].get("show")
        if show == "product":
            product_overlay(S["product"], S.get("price", ""), ov, S.get("limited", False), top=top, line=not paid)
        elif show == "shop":
            shop_overlay(S["shop"], S.get("area", ""), S.get("hours", ""), ov, top=top, line=not paid)
        else:
            plain_overlay(ov)
        if i == 1 and S.get("date"):
            date_chip(ov, S["date"])
        overlays.append(ov)
        # 字幕：声の長さを文字数で分けて順に出す
        lines = p["c"].get("subs") or [p["c"]["narr"]]
        n = sum(len(x) for x in lines)
        s0 = p["t0"] + LEAD
        for j, text in enumerate(lines, 1):
            e0 = s0 + p["nd"] * len(text) / n
            img = work / f"sub-{i}-{j}.png"
            subtitle_png(text, img)
            subs.append((img, round(s0, 2), round(min(e0 + (0.25 if j == len(lines) else 0), p["t0"] + p["dur"] - 0.05), 2)))
            s0 = e0

    # 3) ffmpeg で組み立て
    #   入力：0〜2 動画／3〜5 文字（動画ごと）／6 PR（無料版は透かしつき）／7 締め画像（有料版は締めの文字）
    #         ／8 締めナレーション（無料版だけ）／曲／声3つ／字幕／締めの商品の動画（有料版だけ）
    n = len(plan)
    I_OV, I_PR, I_BRAND = n, 2 * n, 2 * n + 1
    I_NEND = None if paid else 2 * n + 2
    I_MUSIC = 2 * n + (2 if paid else 3)
    I_VOICE, I_SUB = I_MUSIC + 1, I_MUSIC + 1 + n
    I_ENDV = I_SUB + len(subs)
    fc = []
    for i, p in enumerate(plan):
        fc += video_filter(i, p["info"], p["dur"], f"c{i}")
        fc.append(f"[{I_OV + i}:v]format=rgba,fade=t=in:st=0:d=0.25:alpha=1[o{i}]")
        fc.append(f"[c{i}][o{i}]overlay=0:0:shortest=1[v{i}]")
    if paid:   # 締めの商品の動画を後ろにつなぐ
        fc += video_filter(I_ENDV, end_clip["info"], END_SEC, "ce")
    vs = "".join(f"[v{i}]" for i in range(n)) + ("[ce]" if paid else "")
    fc.append(vs + f"concat=n={n + (1 if paid else 0)}:v=1:a=0,format=yuv420p[m0]")
    vlen = total if paid else body
    last = "m0"
    for k, (_, s, e) in enumerate(subs):
        fc.append(f"[{I_SUB + k}:v]format=rgba,fade=t=in:st={s}:d=0.12:alpha=1,fade=t=out:st={e - 0.12}:d=0.12:alpha=1[s{k}]")
        fc.append(f"[{last}][s{k}]overlay=0:0:enable='between(t,{s},{e})'[m{k + 1}]")
        last = f"m{k + 1}"
    fc.append(f"[{last}][{I_PR}:v]overlay=0:0:shortest=1,trim=duration={vlen},setpts=PTS-STARTPTS[vm]")
    if paid:   # 最後の END_SEC 秒：商品の動画の上に締めの文字
        c0 = round(body, 2)
        fc += [
            f"[{I_BRAND}:v]format=rgba,fade=t=in:st={c0}:d=0.3:alpha=1[cr]",
            f"[vm][cr]overlay=0:0:enable='gte(t,{c0})',format=yuv420p[outv]",
        ]
    else:
        fc += [
            f"[{I_BRAND}:v]scale={W}:{H}:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,setsar=1,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
            "[vm][vb]concat=n=2:v=1:a=0,format=yuv420p[outv]",
        ]
    for i, p in enumerate(plan):
        ms = int((p["t0"] + LEAD) * 1000)
        fc.append(f"[{I_VOICE + i}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={VOICE_VOL},adelay=delays={ms}:all=1[nv{i}]")
    fc += [
        f"[{I_MUSIC}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{vlen},asetpts=PTS-STARTPTS,"
        f"volume={S.get('music_vol', MUSIC_VOL)},afade=t=in:st=0:d=0.3,afade=t=out:st={vlen - 1.0}:d=1.0[bgm]",
        "[bgm]" + "".join(f"[nv{i}]" for i in range(n)) + f"amix=inputs={n + 1}:duration=first:normalize=0,atrim=0:{vlen}"
        + ("[outa]" if paid else "[mixbody]"),
    ]
    if not paid:
        fc += [
            f"[{I_NEND}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{BRAND_DUR},asetpts=PTS-STARTPTS,volume=1.6,apad=whole_dur={BRAND_DUR}[narr]",
            "[mixbody][narr]concat=n=2:v=0:a=1[outa]",
        ]
    img = lambda p, d: ["-loop", "1", "-framerate", "30", "-t", str(d), "-i", str(p)]
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y"]
    for p in plan:
        cmd += ["-ss", str(p["start"]), "-t", str(p["dur"] + 0.2), "-i", str(rel(p["c"]["file"]))]
    for p, ov in zip(plan, overlays):
        cmd += img(ov, p["dur"])
    cmd += img(pr, vlen) + (img(endcard, vlen) if paid else img(BRAND, BRAND_DUR) + ["-i", str(NARR_END)])
    if S.get("music"):
        cmd += ["-ss", str(S.get("music_ss", 0)), "-t", str(vlen + 0.5), "-i", str(rel(S["music"]))]
    else:   # 音楽なし：無音を音楽のかわりに入れる
        cmd += ["-f", "lavfi", "-t", str(vlen + 0.5), "-i", "anullsrc=r=48000:cl=stereo"]
    for p in plan:
        cmd += ["-i", str(p["wav"])]
    for pth, _, _ in subs:
        cmd += img(pth, vlen)
    if paid:
        cmd += ["-ss", str(end_clip["start"]), "-t", str(END_SEC + 0.2), "-i", str(end_clip["file"])]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", str(work / "assembled.mp4")]
    subprocess.run(cmd, check=True)
    # iPhone の縦動画には「回転」の印が付いていて、そのまま引き継ぐと横向きで再生される。
    # 映像はもう縦にしてあるので、印だけを「回転なし」にして保存し直す（画質は変わらない）
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-display_rotation", "0",
                    "-i", str(work / "assembled.mp4"), "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    print(f"DONE {out}  {'有料版' if paid else '無料版'} {total:.2f}秒（" + " + ".join(f"動画{i + 1} {p['dur']}" for i, p in enumerate(plan))
          + (f" + 締め（商品の動画）{END_SEC}）" if paid else f" + 締め {BRAND_DUR}）")
          + f"・声：{narrate.NAMES.get(voice.upper(), voice)}（{narrate.engine()}）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
