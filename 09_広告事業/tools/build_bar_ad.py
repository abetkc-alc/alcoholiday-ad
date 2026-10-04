# ALCOHOLIDAY 広告事業：BARのおすすめ紹介動画の組み立て（お客さんが撮った動画3本版）
#   流れ（縦1080×1920・約13〜16秒＋締め4.4秒）：
#     ① 動画1（お店の雰囲気）＋ナレーション＋字幕
#     ② 動画2（おすすめ商品）＋ナレーション＋字幕＋商品名・価格
#     ③ 動画3（自由）＋ナレーション＋字幕＋店名・場所・営業時間・お酒の注意書き
#     ④ ALCOHOLIDAY の締め画像＋ナレーション「お酒との時間をもっと楽しく」（必ず入れる）
#   ・ナレーションは案内役（A＝ローズ／B＝ラフィ／C＝アイラ）の声で AI が読む（tools/narrate.py）
#   ・各動画の長さは「ナレーションの長さ＋少しの間」。足りないときは止める（静止・ループ・逆再生で伸ばさない）
#   ・お客さんの動画の音は使わない（音楽＋ナレーション）。左上に「PR」を出し続ける
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
BRAND = pathlib.Path(__file__).resolve().parent.parent / "素材" / "ending-bar-v3.jpg"
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


def top_shade(im, depth=640, alpha=190):
    grad = Image.new("L", (1, H), 0)
    for yy in range(H):
        grad.putpixel((0, yy), int(alpha * max(0, min(1, (depth - yy) / (depth * 0.55)))))
    im.paste(Image.new("RGBA", (W, H), (10, 8, 6, 255)), (0, 0), grad.resize((W, H)))


def bottom_shade(im, start=1380, alpha=150):
    grad = Image.new("L", (1, H), 0)
    for yy in range(H):
        grad.putpixel((0, yy), int(alpha * max(0, min(1, (yy - start) / 300))))
    im.paste(Image.new("RGBA", (W, H), (10, 8, 6, 255)), (0, 0), grad.resize((W, H)))


def product_overlay(product, price, path, limited=False):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    top_shade(im)
    d = ImageDraw.Draw(im)
    y = 210
    d.line((440, y, 640, y), fill=GOLD, width=3)
    # 商品名が長いときは、2行に収まるまで文字を小さくする（64 → 56 → 50）
    f = next((font(sz, heavy=True) for sz in (64, 56, 50) if len(split_lines(d, product, font(sz, heavy=True))) <= 2), font(50, heavy=True))
    y = text_center(d, y + 26, product, f, (255, 255, 255, 255), stroke=2)
    if price:
        y = text_center(d, y + 8, price, font(46), GOLD, stroke=2)
    if limited:
        text_center(d, y + 10, LIMITED, font(30), (255, 255, 255, 240), maxw=980, stroke=2)
    bottom_shade(im)
    im.save(path)


def shop_overlay(shop, area, hours, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    top_shade(im, depth=700)
    d = ImageDraw.Draw(im)
    y = 210
    d.line((440, y, 640, y), fill=GOLD, width=3)
    y = text_center(d, y + 26, shop, font(68, heavy=True), (255, 255, 255, 255), stroke=2)
    for t in (area, hours):
        if t:
            y = text_center(d, y + 4, t, font(38), (240, 230, 215, 255), stroke=2)
    bottom_shade(im)
    text_center(d, 1810, NOTICE, font(27), (225, 215, 200, 240), maxw=1000, stroke=1)
    im.save(path)


def plain_overlay(path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bottom_shade(im)
    im.save(path)


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
    for p in [rel(c["file"]) for c in clips] + [rel(S["music"]), BRAND, NARR_END]:
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
    total = body + BRAND_DUR

    # 2) 文字の画像
    pr = work / "pr.png"
    pr_badge(pr)
    overlays, subs = [], []
    for i, p in enumerate(plan, 1):
        ov = work / f"overlay-{i}.png"
        show = p["c"].get("show")
        if show == "product":
            product_overlay(S["product"], S.get("price", ""), ov, S.get("limited", False))
        elif show == "shop":
            shop_overlay(S["shop"], S.get("area", ""), S.get("hours", ""), ov)
        else:
            plain_overlay(ov)
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
    #   入力：0〜2 動画／3〜5 文字（動画ごと）／6 PR／7 締め画像／8 締めナレーション／9 曲／10〜12 声／13〜 字幕
    n = len(plan)
    I_OV, I_PR, I_BRAND, I_NEND, I_MUSIC, I_VOICE, I_SUB = n, 2 * n, 2 * n + 1, 2 * n + 2, 2 * n + 3, 2 * n + 4, 3 * n + 4
    fc = []
    for i, p in enumerate(plan):
        fc += video_filter(i, p["info"], p["dur"], f"c{i}")
        fc.append(f"[{I_OV + i}:v]format=rgba,fade=t=in:st=0:d=0.25:alpha=1[o{i}]")
        fc.append(f"[c{i}][o{i}]overlay=0:0:shortest=1[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,format=yuv420p[m0]")
    last = "m0"
    for k, (_, s, e) in enumerate(subs):
        fc.append(f"[{I_SUB + k}:v]format=rgba,fade=t=in:st={s}:d=0.12:alpha=1,fade=t=out:st={e - 0.12}:d=0.12:alpha=1[s{k}]")
        fc.append(f"[{last}][s{k}]overlay=0:0:enable='between(t,{s},{e})'[m{k + 1}]")
        last = f"m{k + 1}"
    fc += [
        f"[{last}][{I_PR}:v]overlay=0:0:shortest=1,trim=duration={body},setpts=PTS-STARTPTS[vm]",
        f"[{I_BRAND}:v]scale={W}:{H}:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,setsar=1,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
        "[vm][vb]concat=n=2:v=1:a=0,format=yuv420p[outv]",
    ]
    for i, p in enumerate(plan):
        ms = int((p["t0"] + LEAD) * 1000)
        fc.append(f"[{I_VOICE + i}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={VOICE_VOL},adelay=delays={ms}:all=1[nv{i}]")
    fc += [
        f"[{I_MUSIC}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{body},asetpts=PTS-STARTPTS,"
        f"volume={S.get('music_vol', MUSIC_VOL)},afade=t=in:st=0:d=0.3,afade=t=out:st={body - 1.0}:d=1.0[bgm]",
        "[bgm]" + "".join(f"[nv{i}]" for i in range(n)) + f"amix=inputs={n + 1}:duration=first:normalize=0,atrim=0:{body}[mixbody]",
        f"[{I_NEND}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{BRAND_DUR},asetpts=PTS-STARTPTS,volume=1.6,apad=whole_dur={BRAND_DUR}[narr]",
        "[mixbody][narr]concat=n=2:v=0:a=1[outa]",
    ]
    img = lambda p, d: ["-loop", "1", "-framerate", "30", "-t", str(d), "-i", str(p)]
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y"]
    for p in plan:
        cmd += ["-ss", str(p["start"]), "-t", str(p["dur"] + 0.2), "-i", str(rel(p["c"]["file"]))]
    for p, ov in zip(plan, overlays):
        cmd += img(ov, p["dur"])
    cmd += img(pr, body) + img(BRAND, BRAND_DUR)
    cmd += ["-i", str(NARR_END), "-ss", str(S.get("music_ss", 0)), "-t", str(body + 0.5), "-i", str(rel(S["music"]))]
    for p in plan:
        cmd += ["-i", str(p["wav"])]
    for pth, _, _ in subs:
        cmd += img(pth, body)
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
            "-r", "30", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", str(work / "assembled.mp4")]
    subprocess.run(cmd, check=True)
    # iPhone の縦動画には「回転」の印が付いていて、そのまま引き継ぐと横向きで再生される。
    # 映像はもう縦にしてあるので、印だけを「回転なし」にして保存し直す（画質は変わらない）
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-display_rotation", "0",
                    "-i", str(work / "assembled.mp4"), "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    print(f"DONE {out}  {total:.2f}秒（" + " + ".join(f"動画{i + 1} {p['dur']}" for i, p in enumerate(plan)) + f" + 締め {BRAND_DUR}）"
          f"・声：{narrate.NAMES.get(voice.upper(), voice)}（{narrate.engine()}）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
