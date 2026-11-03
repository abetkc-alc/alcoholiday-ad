# タケシさんの自撮りトーク動画（IMG_0097.MOV・約2分）を、テロップ入りの18秒にまとめる（2026-11-03）
#   - 文字起こしと場面えらびは Gemini（03_SNS投稿/動画分析/2026-11-03_IMG_0097.md）。
#     Gemini の時刻はずれがあるので、切る場所は「声の間」（ffmpeg の silencedetect）に合わせた
#   - 話の部分 18.0秒 → 締め画像＋ナレーション（SNS 動画は必ず最後に入れる）
#   - できるもの：talk18-v1.mp4（18.0秒・締めなし）／talk18-end-v1.mp4（締めつき）
# 使い方: python build_talk18.py v1
import pathlib
import subprocess
import sys

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VER = sys.argv[1] if len(sys.argv) > 1 else "v1"
HERE = pathlib.Path(__file__).parent
SRC = pathlib.Path(r"C:\Users\abetk\Downloads\IMG_0097.MOV")
SHARED = pathlib.Path(r"C:\Users\abetk\Documents\Codex\2026-09-19\chatgpt-alcoholiday-sns-alcoholiday-instagram-x\outputs")
BRAND = SHARED / "ending-assets" / "ending-title.jpg"
NARR = SHARED / "ending-assets" / "お酒との時間をもっと楽しく.wav"
FONT = r"C:\Windows\Fonts\SourceHanSansJP-Bold.otf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = HERE / f"talk18-{VER}.mp4"
OUT_END = HERE / f"talk18-end-{VER}.mp4"

# 元の動画から使う区間（秒）。どれも声の間で切っている。合計 18.0秒
#   v2：v1 は「短い動画を」の前に「て」、うしろに「みんなが」が入り、「そういう」の「そう」が欠けた（Gemini で確認）。
#       0.01秒ごとの声の大きさで切る場所を直し、足りなくなった分に「当たり前だけど」を入れた
#   v3：「短い」の出だしが少し欠けたので、64.49 → 64.47 に
CUTS = [(45.90, 54.00),    # どうやったら月に100万円を稼ぎ出せるか…なかなかうまくいかないです
        (54.85, 55.95),    # 当たり前だけど
        (64.47, 66.45),    # 短い動画を作ることができたら
        (109.45, 116.27)]  # そういう人たちに使ってもらいたいようなサービスをやってみようと思ってます
MAIN = sum(e - s for s, e in CUTS)

HOOK = "月100万円への挑戦"
# テロップ（文字, 表示開始, 表示終了）— まとめた動画の中の時刻
SUBS = [("どうやったら\n月に100万円を稼ぎ出せるか", 0.10, 2.45),
        ("真剣に考えている\nつもりだけど…", 2.45, 6.65),
        ("なかなか\nうまくいかないです", 6.65, 8.10),
        ("当たり前だけど", 8.10, 9.20),
        ("短い動画を\n作ることができたら", 9.20, 11.16),
        ("そういう人たち（お店）に\n使ってもらいたいサービスを", 11.16, 15.30),
        ("やってみようと\n思ってます！", 15.30, MAIN)]
SUB_SIZE = 66
SUB_BOTTOM = 1600   # テロップの下端（SNS の操作ボタンに隠れにくい高さ）
HOOK_SIZE = 92
HOOK_Y = 230

NARR_LEN = 4.17
BRAND_DUR = NARR_LEN + 0.3


def draw_text(lines, size, y_top, path):
    """白い太字＋黒い縁取り＋うっすらした影。各行 940px 以内・中央ぞろえ。"""
    f = ImageFont.truetype(FONT, size)
    base = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    gap = int(size * 1.3)
    pos = []
    for i, t in enumerate(lines):
        w = ImageDraw.Draw(base).textlength(t, font=f)
        if w > 940:
            raise SystemExit(f"テロップが長すぎます: {t}")
        pos.append(((1080 - w) / 2, y_top + i * gap, t))
    sd = ImageDraw.Draw(shadow)
    for x, y, t in pos:
        sd.text((x + 3, y + 4), t, font=f, fill=(0, 0, 0, 180))
    base = Image.alpha_composite(base, shadow.filter(ImageFilter.GaussianBlur(5)))
    d = ImageDraw.Draw(base)
    for x, y, t in pos:
        d.text((x, y), t, font=f, fill=(255, 255, 255, 255), stroke_width=6, stroke_fill=(15, 15, 15, 255))
    base.save(path)


def run(cmd):
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y"] + cmd, check=True)


def main():
    for p in (OUT, OUT_END):
        if p.exists():
            raise SystemExit(f"すでにあります（上書きしません）: {p.name}")
    for p in (SRC, BRAND, NARR):
        if not p.exists():
            raise SystemExit(f"素材が見つかりません: {p}")
    work = HERE / f"work-{VER}"
    work.mkdir(exist_ok=True)

    pngs = []
    p = work / "hook.png"
    draw_text([HOOK], HOOK_SIZE, HOOK_Y, p)
    pngs.append((p, 0.0, MAIN))
    for i, (t, s, e) in enumerate(SUBS, 1):
        lines = t.split("\n")
        p = work / f"sub-{i}.png"
        draw_text(lines, SUB_SIZE, SUB_BOTTOM - int(SUB_SIZE * 1.3) * len(lines), p)
        pngs.append((p, s, e))

    # 区間を切り出してつなぐ（縦向きは ffmpeg が自動で直す）。音のつなぎ目は 0.04秒だけフェードしてプツッと鳴らないようにする
    norm = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p"
    fc, cat = [], ""
    for i, (s, e) in enumerate(CUTS):
        d = e - s
        fc.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,{norm}[v{i}]")
        fc.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={d - 0.04:.3f}:d=0.04[a{i}]")
        cat += f"[v{i}][a{i}]"
    fc.append(f"{cat}concat=n={len(CUTS)}:v=1:a=1[m0][outa]")
    last = "m0"
    for i, (_, s, e) in enumerate(pngs):
        fade = "" if i == 0 else f",fade=t=in:st={s}:d=0.12:alpha=1"
        fc.append(f"[{i + 1}:v]format=rgba{fade}[s{i}]")
        fc.append(f"[{last}][s{i}]overlay=0:0:enable='between(t,{s},{e})'[m{i + 1}]")
        last = f"m{i + 1}"
    fc.append(f"[{last}]format=yuv420p[outv]")
    cmd = ["-i", str(SRC)]
    for p, _, _ in pngs:
        cmd += ["-loop", "1", "-framerate", "30", "-t", f"{MAIN:.2f}", "-i", str(p)]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]", "-t", f"{MAIN:.2f}",
            "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(OUT)]
    run(cmd)
    print(f"DONE {OUT.name}  length {MAIN:.2f}s")

    # 締め画像＋ナレーションをつなぐ
    fc = [f"[1:v]scale=1080:1920:in_range=jpeg:out_range=tv,fps=30,format=yuv420p,trim=duration={BRAND_DUR},setpts=PTS-STARTPTS[vb]",
          f"[2:a]volume=1.6,aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={BRAND_DUR}[nb]",
          "[0:v][0:a][vb][nb]concat=n=2:v=1:a=1[outv][outa]"]
    run(["-i", str(OUT), "-loop", "1", "-framerate", "30", "-t", str(BRAND_DUR), "-i", str(BRAND), "-i", str(NARR),
         "-filter_complex", ";".join(fc), "-map", "[outv]", "-map", "[outa]",
         "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT_END)])
    print(f"DONE {OUT_END.name}  length {MAIN + BRAND_DUR:.2f}s")


if __name__ == "__main__":
    main()
