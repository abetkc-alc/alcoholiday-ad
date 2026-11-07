# ALCニュース（ショート動画作成の別バージョン・試作 2026-11-07）
#   視聴者が投稿した動画1本＋「いつ・どこで・だれが・なにを・どうした・状況（300字）」から、
#   キー局の報道番組そっくりの縦型ニュース（20秒以内）をつくる。中身はくだらないのに、見た目と話し方は大まじめ＝シュールな笑い
#
#   流れ（縦1080×1920・30コマ/秒）：
#     A キャスター「ALCニュースです。」＋ニュースの要約。右のモニター（グリーンバック）に投稿動画
#     B 投稿動画を全画面（Bロール）。種類で変える
#         明るいニュース（bright）：動画の音そのまま＋テロップ＋字幕
#         困ったニュース（trouble）：顔にモザイク＋声を変える＋テロップ＋字幕＋「映像と音声を加工しています」
#         情報（info）　　　　　　　：動画の音は小さく、キャスターの声で要約を伝える＋テロップ＋字幕
#     C キャスターにもどり、明るく楽しい一言で終わる（「ご視聴ありがとうございました。」は 2026-11-07 にやめた）
#     D ALCOHOLIDAY のブランドボード＋「お酒との時間をもっと楽しく」の声（2026-11-07 タケシさんの指示。この分だけ20秒より長くなる）
#   ・キャスター「大舞 剛（おおまい つよし）」は笑わない。語尾は推測・伝聞（〜とのことです／〜とみられます）
#   ・テロップの字は報道番組で使われるUDゴシック系（BIZ UDPゴシック）
#   ・キャスターの映像：still＝写真のまま（無料・確認用）／lipsync＝Higgsfield の Seedance 2.5 で声に口を合わせる（お金がかかる）
#
# 使い方: python tools/alc_news.py 案件/<番号>/依頼.json [--caster still|lipsync] [--max-usd 3.5]
#   依頼.json：{"kind": "bright|trouble|info", "when": "", "where": "", "who": "", "what": "", "how": "", "situation": "", "video": "動画のファイル名"}
import argparse
import base64
import datetime
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
NEWS = HERE.parent                                   # 09_広告事業/ALCニュース
sys.path.insert(0, str(NEWS.parent / "tools"))
import narrate  # noqa: E402  Google の読み上げ・wav のそろえ方を借りる

FFMPEG = narrate.FFMPEG
W, H, FPS, SR = 1080, 1920, 30, 48000
LOGO = NEWS / "素材" / "logo-alcnews.png"
STUDIO = NEWS / "素材" / "キャスター" / "caster-studio-v2.png"   # v2（2026-11-07）：やさしい顔（笑顔ではない）
YUNET = NEWS / "素材" / "face_detection_yunet_2023mar.onnx"
FONT = r"C:\Windows\Fonts\BIZ-UDGothicB.ttc"         # BIZ UDPゴシック（報道のテロップに多いUDゴシック系）
FONT_IDX = 1
VOICE = "ja-JP-Chirp3-HD-Charon"                      # キャスターの声（声見本/ の中から選ぶ）
RATE = 1.12                                           # 一定のはやさで、はっきり
CASTER = "大舞 剛"
CASTER_EN = "Omai Tsuyoshi"    # 名前の英語表記
KINDS = {"bright": "明るいニュース", "trouble": "困ったニュース", "info": "情報"}

MAX_TOTAL = 20.0    # ニュースの部分（A〜C）の長さの上限。最後のブランドボード（D）はこの外
STING = 0.55        # はじまりの音のあと、キャスターが話しはじめるまで
A_TAIL = 0.45       # 要約を言い終えてからBロールまで
C_HEAD = 0.35       # キャスターにもどってから話しはじめるまで
C_TAIL = 0.9        # 最後の一言のあと
ENDING_IMG = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\画像\商品画像\ORIGINAL\JPG_ending_title.jpg")   # ブランドボード
ENDING_WAV = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\音声\お酒との時間をもっと楽しく.wav")
E_HEAD, E_TAIL, E_FADE = 0.3, 0.9, 0.3   # ブランドボードが出てから声まで／声のあと／キャスターからの切りかえ（秒）
B_MIN = 5.0         # Bロールの最短

RED = (200, 16, 30, 255)
DARK_RED = (150, 8, 18, 255)
YELLOW = (255, 222, 40, 255)
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)


def log(*a):
    print(*a, flush=True)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("ffmpeg でエラー：" + r.stderr[-800:])
    return r


def media_len(path):
    err = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def font(size):
    return ImageFont.truetype(FONT, size, index=FONT_IDX)


# ---------------------------------------------------------------- 1. 投稿動画をそろえる・書き起こす
def prepare_source(src, work):
    """投稿動画を 1080×1920・30コマ の mp4 と、48kHz の音（wav）にそろえる（縦横の回転も直す）。長いものは最初の60秒だけ"""
    mp4, wav = work / "src.mp4", work / "src.wav"
    if not mp4.exists():
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-t", "60",
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p",
             "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-an", str(mp4)])
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-t", "60", "-vn",
             "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
    return mp4, wav


def transcribe(wav, work):
    """投稿動画の話し声を、秒数つきで書き起こす（Gemini）"""
    out = work / "書き起こし.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    mp3 = work / "src_voice.mp3"
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-ac", "1", "-ar", "16000", "-b:a", "48k", str(mp3)])
    key = narrate.envfile.get("GEMINI_API_KEY")
    model = narrate.envfile.get("GEMINI_MODEL") or "gemini-flash-latest"
    prompt = ("この音声の話し声を、聞こえたとおり日本語で書き起こしてください。"
              "文ごとに開始・終了の秒数（小数1けた）をつけ、"
              '{"segments":[{"start":0.0,"end":1.8,"text":"…"}]} の JSON だけを返してください。話し声がなければ segments は空。')
    body = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(mp3.read_bytes()).decode()}},
                                    {"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    # 混んでいる（503）ときや、2分たっても返事がないときは、少し待って、ほかの種類の Gemini でもためす
    # （2026-11-07 に5分返事がなく、そのまま止まったことがある）
    r = None
    for m in [model, model, "gemini-3.8-flash", "gemini-flash-lite-latest", model, "gemini-3.8-flash"]:
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                              headers={"x-goog-api-key": key}, timeout=120, json=body)
            if r.status_code not in (429, 500, 503):
                break
            log(f"Gemini（{m}）が混んでいるので、もう一度")
        except requests.RequestException as e:
            log(f"Gemini（{m}）から返事がないので、もう一度（{type(e).__name__}）")
        time.sleep(8)
    if r is None:
        raise RuntimeError("Gemini から何度ためしても返事がありませんでした")
    if r.status_code != 200:
        raise RuntimeError("Gemini の書き起こしでエラー：" + r.text[:300])
    text = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
    segs = json.loads(re.search(r"\{.*\}", text, re.S).group(0)).get("segments", [])
    out.write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
    return segs


# ---------------------------------------------------------------- 2. 台本（Claude）
def make_prompt(order, segs, src_len, feedback=""):
    kind = order["kind"]
    tr = "\n".join(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in segs) or "（話し声なし）"
    vo_rule = ('"vo": Bロールの映像にかぶせて、キャスターの声で伝える要約（28字以内・ニュース原稿の文体・語尾は伝聞か推測）,'
               if kind == "info" else '"vo": "",')
    subs_rule = ('"subs": [] （情報のときは空）,' if kind == "info" else
                 '"subs": Bロールの範囲の中の、投稿者の話し声の字幕。[{"start": 元の動画の秒, "end": 秒, "text": "18字以内"}]。'
                 "書き起こしの言葉をそのまま使い、えー・あのー などは消してよい。話し声がなければ空,")
    return f"""あなたは、キー局の報道番組そっくりの縦型ショート動画「ALCニュース」の台本係です。
視聴者が投稿した、くだらない出来事を、本物の報道番組と同じまじめさで伝えることで、シュールな笑いをつくります。

## 決まり
- キャスターは「{CASTER}（おおまい つよし）」。決して笑わない、冗談を言わない、一定の調子で淡々と読む報道キャスター
- 原稿は本物のニュース原稿の文体（「けさ」「〜で」「男性が」など）。くだけた言葉・悪口・ネットスラング・「笑」「ｗ」は使わない
- 文の語尾は、推測か伝聞の形にする（「〜とのことです」「〜ということです」「〜とみられます」「〜した模様です」「〜と話しているということです」）
- 投稿の言葉が乱暴でも、報道の言葉に言いかえる（例：「マジでやばい」→「周囲には緊張が走った模様です」）
- 人の見た目をばかにする言葉は、そのまま書かず、事実だけを淡々と（例：「髪は整えられていなかったとみられます」）
- 数字・時刻は短く。「ALC」は書いてよい（読みは自動で直す）
- ニュースの部分は20秒以内なので、字数を必ず守る
- **締めの一言は、辛辣でシュール**（2026-11-07 タケシさんの指示）。キャスターは笑わず淡々と、ニュースの口調のまま、本人や出来事にちくっと刺さる冷静なツッコミを入れる。見た人が思わず吹き出す一言にする。ただし人の見た目・年齢・体をばかにする悪口や、ひどい言葉は使わない（行動や言ったことに対してだけ辛辣に）

## 投稿の内容
- ニュースの種類：{KINDS[kind]}
- いつ：{order.get('when', '')}
- どこで：{order.get('where', '')}
- だれが：{order.get('who', '')}
- なにを：{order.get('what', '')}
- どうした：{order.get('how', '')}
- 状況：{order.get('situation', '')}

## 投稿動画（{src_len:.1f}秒）の話し声の書き起こし
{tr}

## 返すもの（JSON だけ。説明・前置きはいらない）
{{
 "headline": 画面の上の「速報」のとなりに出す見出し（10字以内・体言止め）,
 "panel_title": モニターに大きく出す言葉（6字以内。四字熟語ふうの大げさな言葉がよい）,
 "panel_sub": その下の小さい説明（11字以内）,
 "open": キャスターの最初の原稿。必ず「ALCニュースです。」で始め、そのあと要約を1文（全部で38字以内）,
 "broll_start": Bロールに使う、元の動画のはじまりの秒,
 "broll_end": 終わりの秒（長さは5〜8秒。いちばん内容が伝わる・いちばんシュールな部分。{src_len:.1f}秒をこえない）,
 "broll_telop": Bロールの上に出すテロップ（13字以内・報道ふう。例：「“きょうの予定”を熱弁」）,
 {subs_rule}
 {vo_rule}
 "close_line": 最後にキャスターがまじめな顔で言う、辛辣でシュールな一言（16字以内。淡々とした報道の口調で、ちくっと刺す。例：「新曲の反響は、まだ確認されていません。」「予定の大半は、未定とのことです。」「本人以外の評価は不明です。」）
}}
{feedback}"""


def ask_claude(prompt):
    """claude -p で答えをもらい、その中の JSON を取り出す（bar_auto.py と同じ）"""
    for _ in range(2):
        r = subprocess.run(["claude", "-p", "--output-format", "text"], input=prompt, capture_output=True,
                           text=True, encoding="utf-8", timeout=600, cwd=str(NEWS))
        if r.returncode != 0:
            raise RuntimeError("Claude が答えませんでした：" + (r.stderr or r.stdout)[:300])
        m = re.search(r"\{.*\}", r.stdout, re.S)
        if m:
            return json.loads(m.group(0))
        prompt += "\n\n## もう一度\nこれは自動の処理で、質問に答える人はいません。必ず JSON だけを返してください。"
    raise RuntimeError("Claude の答えに JSON がありません：" + r.stdout[:300])


# ---------------------------------------------------------------- 3. キャスターの声
def speak(text, out):
    """キャスターの声で読み上げて out（.wav）に保存。秒数を返す"""
    out = pathlib.Path(out)
    # 同じ文・同じ声なら前の声を使う（作り直しで口の動きの動画とずれないように）
    memo, sig = out.with_suffix(".txt"), f"{VOICE}|{RATE}|{text}"
    if out.exists() and memo.exists() and memo.read_text(encoding="utf-8") == sig:
        return narrate.duration(out)
    say = text.replace("ALC", "エーエルシー").replace("ＡＬＣ", "エーエルシー")
    raw = out.with_suffix(".raw.wav")
    r = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize",
                      params={"key": narrate.env("GOOGLE_TTS_KEY")}, timeout=60,
                      json={"input": {"text": say}, "voice": {"languageCode": "ja-JP", "name": VOICE},
                            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": SR, "speakingRate": RATE}})
    if r.status_code != 200:
        raise RuntimeError("Google の読み上げでエラー：" + r.text[:300])
    raw.write_bytes(base64.b64decode(r.json()["audioContent"]))
    narrate.to_wav(raw, out)
    memo.write_text(sig, encoding="utf-8")
    return narrate.duration(out)


# ---------------------------------------------------------------- 4. 文字（テロップ・字幕）
def cards(text, per_line=15, lines=2):
    """字幕を「1画面ぶん（per_line 字×lines 行）」に分ける。句点で区切り、長ければ読点で区切る"""
    text = text.strip()
    sents = [s for s in re.split(r"(?<=[。！？])", text) if s.strip()]
    out = []
    for s in sents:
        s = s.strip()
        while len(s) > per_line * lines:
            cut = max((m.end() for m in re.finditer("、", s[:per_line * lines])), default=per_line * lines)
            out.append(s[:cut])
            s = s[cut:]
        if s:
            out.append(s)
    res = []
    for c in out:
        c = c.rstrip("。")
        if len(c) > per_line:
            # 2行に分ける場所：読点か、助詞（は・が・を・に・で・と・も・て）のあと。まん中に近い所
            lo, hi = max(1, len(c) - per_line), min(per_line, len(c) - 1)
            cands = [i + 1 for i, ch in enumerate(c[:-1]) if lo <= i + 1 <= hi and (ch == "、" or (ch in "はがをにでともて" and c[i + 1] not in "っゃゅょぁぃぅぇぉー"))]
            cands = [i for i in cands if c[i - 1] == "、"] or cands
            if cands:
                cut = min(cands, key=lambda i: abs(i - len(c) / 2))
                c = c[:cut] + "\n" + c[cut:]
            else:   # 助詞がない：言葉の途中（「シンガーソングライ／ター」など）で切らずに折り返し、入りきらない分は次の字幕へ（2026-11-07）
                res.extend(wrap_words(c, per_line, lines))
                continue
        res.append(c)
    return res


def wrap_words(c, per_line, lines):
    """言葉のまとまり（カタカナ・漢字の続き）を切らずに per_line 字で折り返し、lines 行ずつの字幕にする"""
    kind = lambda ch: "k" if re.match(r"[ァ-ヶー]", ch) else "h" if re.match(r"[一-龥々]", ch) else "o"   # noqa: E731
    ok = {i for i in range(1, len(c)) if c[i - 1] in "、はがをにでともて" or kind(c[i - 1]) != kind(c[i]) and kind(c[i]) != "o"}
    rows, s = [], 0
    while s < len(c):
        if len(c) - s <= per_line:
            rows.append(c[s:])
            break
        cut = max((i for i in ok if s < i <= s + per_line), default=s + per_line)
        rows.append(c[s:cut])
        s = cut
    return ["\n".join(rows[i:i + lines]) for i in range(0, len(rows), lines)]


def time_cards(text, t0, dur):
    """読み上げの長さ dur を、字数で分けて字幕の時間を決める"""
    cs = cards(text)
    n = sum(len(c.replace("\n", "")) for c in cs) or 1
    res, t = [], t0
    for c in cs:
        d = dur * len(c.replace("\n", "")) / n
        res.append((t, t + d, c))
        t += d
    return res


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def fit_font(text, size, max_w, min_size=30):
    while size > min_size and font(size).getlength(text) > max_w:
        size -= 2
    return font(size)


def header(headline):
    """画面上の帯（2026-11-07 タケシさんの直し「わかりやすく」）
    1段目：番組ロゴ／2段目：「速報」と白い見出しを横いっぱいに大きく
    SNS の画面の上の部分（アカウント名など）にかからないよう、上から110px あける"""
    im = layer()
    d = ImageDraw.Draw(im)
    x0, x1 = 36, W - 36
    # 1段目：番組ロゴ（素材/make_logo.py でつくる）。時刻は出さない（2026-11-07 タケシさんの指示）
    im.alpha_composite(Image.open(LOGO).convert("RGBA"), (x0, 104))
    # 2段目：速報＋見出し
    t2, b2 = 200, 290
    d.rectangle([x0, t2, x0 + 150, b2], fill=RED)
    d.text((x0 + 75, (t2 + b2) // 2), "速報", font=font(58), fill=WHITE, anchor="mm")
    d.rectangle([x0 + 150, t2, x1, b2], fill=WHITE)
    d.rectangle([x0 + 150, b2 - 6, x1, b2], fill=RED)
    fh = fit_font(headline, 64, x1 - x0 - 150 - 48)
    d.text((x0 + 150 + 24, (t2 + b2) // 2 - 3), headline, font=fh, fill=BLACK, anchor="lm")
    return im


def viewer_label(x, y):
    """「視聴者投稿」の小さなラベル"""
    im = layer()
    d = ImageDraw.Draw(im)
    f = font(34)
    w = int(f.getlength("視聴者投稿")) + 32
    d.rectangle([x, y, x + w, y + 52], fill=(0, 0, 0, 165))
    d.text((x + 16, y + 26), "視聴者投稿", font=f, fill=WHITE, anchor="lm")
    return im


def panel_title(box, title, sub):
    """モニターの右上：上に赤い札（小さな白い言葉）、その下に大きな白い字（黒いふちと影）
    （2026-11-07 タケシさんの直し：白い板・紺の板の形をやめた）"""
    im = layer()
    d = ImageDraw.Draw(im)
    x0, y0, x1, _ = box
    right = x1 - 34
    top = y0 + 36
    if sub:
        fs = fit_font(sub, 46, x1 - x0 - 120)
        sw = int(fs.getlength(sub))
        d.rectangle([right - sw - 44, top, right, top + 66], fill=RED)
        d.text((right - 22, top + 33), sub, font=fs, fill=WHITE, anchor="rm")
        top += 66 + 10
    ft = fit_font(title, 112, x1 - x0 - 80)
    sh = layer()
    ImageDraw.Draw(sh).text((right + 6, top + 6), title, font=ft, fill=(0, 0, 0, 170), anchor="ra",
                            stroke_width=12, stroke_fill=(0, 0, 0, 170))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d.text((right, top), title, font=ft, fill=WHITE, anchor="ra", stroke_width=10, stroke_fill=(12, 16, 28, 255))
    return im


def nameplate():
    im = layer()
    d = ImageDraw.Draw(im)
    x, y, h = 78, 1530, 116
    f1, f2, f3 = font(36), font(58), font(28)
    w = int(f1.getlength("キャスター")) + int(max(f2.getlength(CASTER), f3.getlength(CASTER_EN))) + 80
    d.rectangle([x, y, x + w, y + h], fill=(255, 255, 255, 240))
    d.rectangle([x, y, x + 14, y + h], fill=RED)
    d.text((x + 34, y + 46), "キャスター", font=f1, fill=(40, 40, 40, 255), anchor="lm")
    ncx = (x + 50 + f1.getlength("キャスター") + x + w - 30) / 2   # 漢字と英語は、まん中をそろえる（2026-11-07 タケシさんの直し）
    d.text((ncx, y + 44), CASTER, font=f2, fill=BLACK, anchor="mm")
    d.text((ncx, y + 94), CASTER_EN, font=f3, fill=(70, 70, 70, 255), anchor="mm")   # 英語表記（2026-11-07 タケシさんの指示）
    return im


def caster_sub(text):
    """キャスターの字幕：下の黒い帯に白い字（2行目は黄色）。帯なし・机を黒くするのはやめて、この形に戻した（2026-11-07 タケシさんの指示）"""
    im = layer()
    d = ImageDraw.Draw(im)
    d.rectangle([0, 1668, W, H], fill=(12, 12, 14, 225))
    lines = text.split("\n")
    f = font(66)
    y = 1668 + (H - 1668) // 2 - (len(lines) - 1) * 44
    for i, ln in enumerate(lines):
        d.text((W // 2, y + i * 88), ln, font=f, fill=WHITE if i == 0 else YELLOW, anchor="mm")
    return im


def broll_sub(text):
    """Bロールの字幕：投稿者の声は黄色い字に黒いふち（報道のインタビュー字幕）"""
    im = layer()
    d = ImageDraw.Draw(im)
    lines = text.split("\n")
    f = font(68)
    y = 1690 - (len(lines) - 1) * 90
    for i, ln in enumerate(lines):
        d.text((W // 2, y + i * 90), ln, font=f, fill=YELLOW, anchor="mm", stroke_width=7, stroke_fill=(0, 0, 0, 255))
    return im


def broll_telop(text, kind):
    """Bロールの上のテロップ（白い箱に赤い線）と「視聴者投稿」、困ったニュースは「加工しています」"""
    im = layer()
    d = ImageDraw.Draw(im)
    f = fit_font(text, 64, W - 160)
    w = int(f.getlength(text)) + 70
    x, y, h = 40, 1420, 96
    d.rectangle([x, y, x + w, y + h], fill=(255, 255, 255, 240))
    d.rectangle([x, y, x + 14, y + h], fill=RED)
    d.text((x + 40, y + h // 2), text, font=f, fill=BLACK, anchor="lm")
    im.alpha_composite(viewer_label(W - 236, 314))
    if kind == "trouble":
        n = "※映像と音声を一部加工しています"
        d.text((W - 40, 380), n, font=font(32), fill=WHITE, anchor="ra", stroke_width=3, stroke_fill=(0, 0, 0, 200))
    return im


# ---------------------------------------------------------------- 5. 映像（キャスター・モニター・モザイク）
def studio_layer():
    """スタジオの写真を 1080×1920 にし、グリーンバックをすけさせる。モニターの四角（x0,y0,x1,y1）も返す"""
    im = Image.open(STUDIO).convert("RGB").resize((W, H), Image.LANCZOS)
    a = np.asarray(im).astype(np.int16)
    alpha, box = key_alpha(a)
    rgb = despill(a, alpha)
    return np.dstack([rgb, alpha]).astype(np.uint8), box


def key_alpha(a):
    """緑の度合いから、すけ具合（0＝すける〜255）を決める"""
    a = a.astype(np.float32)   # int16 のままだと掛け算があふれる
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    gx = g - np.maximum(r, b)
    alpha = np.clip(255 - (gx - 50) * 255 / 60, 0, 255)
    alpha[g < 90] = 255
    ys, xs = np.where(alpha < 20)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(xs) else None
    return alpha.astype(np.uint8), box


def despill(a, alpha, margin=10):
    """髪や肩のふちに残る緑みを消す"""
    rgb = a.copy()
    edge = alpha < 250
    mx = np.maximum(rgb[..., 0], rgb[..., 2])
    rgb[..., 1] = np.where(edge, np.minimum(rgb[..., 1], mx + margin), rgb[..., 1])
    return np.clip(rgb, 0, 255).astype(np.uint8)


class Reader:
    """ffmpeg で動画をコマごとに読む（start 秒から n コマ。w×h にする）"""
    def __init__(self, path, start, n, size=(W, H)):
        self.w, self.h = size
        self.p = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(path),
                                   "-frames:v", str(n), "-vf", f"scale={self.w}:{self.h},fps={FPS}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = None

    def __next__(self):
        buf = self.p.stdout.read(self.w * self.h * 3)
        if len(buf) == self.w * self.h * 3:
            self.last = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
        return self.last

    def close(self):
        self.p.kill()


class Mosaic:
    """顔を見つけてモザイク（YuNet）。見失ったら少しのあいだ前の場所をかくす"""
    def __init__(self):
        # OpenCV は日本語の入った場所のファイルを読めないので、英字だけの一時フォルダに写してから読む
        tmp = pathlib.Path(tempfile.gettempdir()) / "alc_news_yunet.onnx"
        if not tmp.exists() or tmp.stat().st_size != YUNET.stat().st_size:
            shutil.copyfile(YUNET, tmp)
        self.det = cv2.FaceDetectorYN.create(str(tmp), "", (W // 2, H // 2), 0.6)
        self.box, self.miss = None, 99

    def __call__(self, f):
        small = cv2.cvtColor(cv2.resize(f, (W // 2, H // 2)), cv2.COLOR_RGB2BGR)
        _, faces = self.det.detect(small)
        if faces is not None and len(faces):
            x, y, w, h = (faces[np.argmax(faces[:, 2] * faces[:, 3])][:4] * 2).tolist()
            cx, cy, s = x + w / 2, y + h / 2, max(w, h)
            nb = np.array([cx - s * 0.62, cy - s * 0.78, cx + s * 0.62, cy + s * 0.68])
            self.box = nb if self.box is None or self.miss > 8 else self.box * 0.6 + nb * 0.4
            self.miss = 0
        else:
            self.miss += 1
        if self.box is None or self.miss > 20:
            return f
        x0, y0, x1, y1 = [int(v) for v in self.box]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 - x0 < 10 or y1 - y0 < 10:
            return f
        out = f.copy()
        roi = out[y0:y1, x0:x1]
        cell = max(18, (x1 - x0) // 11)
        sm = cv2.resize(roi, (max(1, (x1 - x0) // cell), max(1, (y1 - y0) // cell)), interpolation=cv2.INTER_AREA)
        out[y0:y1, x0:x1] = cv2.resize(sm, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
        return out


def cover(f, w, h):
    """動画のコマを w×h の四角いっぱいに（はみ出たぶんは切る）"""
    fh, fw = f.shape[:2]
    s = max(w / fw, h / fh)
    r = cv2.resize(f, (math.ceil(fw * s), math.ceil(fh * s)), interpolation=cv2.INTER_AREA)
    y = (r.shape[0] - h) // 2
    x = (r.shape[1] - w) // 2
    return r[y:y + h, x:x + w]


def blend(base, over):
    """RGB の base に RGBA の over を重ねる"""
    a = over[..., 3:4].astype(np.float32) / 255
    return (base.astype(np.float32) * (1 - a) + over[..., :3].astype(np.float32) * a).astype(np.uint8)


# ---------------------------------------------------------------- 6. キャスターの口を声に合わせる（Higgsfield・お金がかかる）
LIP_BOX = (0, 700, 820, 1520)        # Seedance にわたす写真（1080×1920 のうち、キャスターの顔と胸）
LIP_MODEL = "bytedance/seedance-2.5/reference-to-video"
STUDIO_EMPTY = NEWS / "素材" / "キャスター" / "studio-empty-v1.png"   # キャスターを消した空のスタジオ（Codex）
# 元の写真（caster-studio-v2・1080×1920 にしたとき）のキャスター：頭のてっぺん・頭のまん中・机の上の線（2026-11-07 はかった）
STILL_DESK = 1717                              # 元の写真の机の上のふち（口の動画はここから下を使わない）
EYE_MID, EYE_DIST = (342.5, 994.2), 110.7      # 口の動画のキャスターを置く、おおよその両目のまん中と幅（画面上）。くわしくは輪郭で合わせる
LIP_RES = "480p"   # 安いほう。11秒で約2.3ドル（720p は約5.1ドルで顔がくっきり）。2026-11-07 タケシさんの指示で 720p → 480p に戻した


def hf_key():
    k = narrate.envfile.get("HF_KEY")
    if not k:
        raise RuntimeError(".env に HF_KEY がありません")
    return {"Authorization": f"Key {k}"}


def hf_upload(path, ctype):
    up = requests.post("https://api.higgsfield.ai/files/generate-upload-url", headers=hf_key(), json={"content_type": ctype}, timeout=60).json()
    requests.put(up["upload_url"], headers={k: str(v) for k, v in (up.get("upload_headers") or {}).items()},
                 data=pathlib.Path(path).read_bytes(), timeout=300).raise_for_status()
    return up["public_url"]


def eyes(img):
    """顔を見つけて、右目・左目の位置（画素）を返す（YuNet）。見つからなければ None"""
    tmp = pathlib.Path(tempfile.gettempdir()) / "alc_news_yunet.onnx"
    if not tmp.exists() or tmp.stat().st_size != YUNET.stat().st_size:
        shutil.copyfile(YUNET, tmp)
    h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(str(tmp), "", (w, h), 0.6)
    _, faces = det.detect(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    if faces is None or not len(faces):
        return None
    f = faces[np.argmax(faces[:, 2] * faces[:, 3])]
    return np.array(f[4:6]), np.array(f[6:8])


def lip_fit(lip, box):
    """口の動画のキャスターを、写真のまま（still）の版のキャスターとぴったり同じ大きさ・位置に置く倍率と置き場所を決める
    1. 両目の幅と位置で、おおよその大きさと場所を出す
    2. モニター（緑）の中に写る写真のキャスターの形（頭と肩の輪郭）に、口の動画のキャスターの形がいちばん重なる大きさと場所を探す
    （2026-11-07 タケシさんの直し「写真のキャスターのサイズに」。Seedance のキャスターは頭が大きめで体が細めなので、目だけで合わせると
      体が小さく見えた。その前は頭のてっぺん〜机で合わせていたが、720p では後ろの壁の横線を机とまちがえた）"""
    m = re.search(r"(\d{3,4})x(\d{3,4})", subprocess.run([FFMPEG, "-hide_banner", "-i", str(lip)], capture_output=True,
                                                         text=True, encoding="utf-8", errors="replace").stderr)
    gw, gh = int(m[1]), int(m[2])
    found, masks = [], []
    for t in (0.0, 1.0, 2.0, 3.0, 4.0):   # まばたきなどでぶれないよう、何コマかの中ほどの値をとる
        p = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", str(lip), "-frames:v", "1",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
        if len(p.stdout) >= gw * gh * 3:
            f = np.frombuffer(p.stdout[:gw * gh * 3], np.uint8).reshape(gh, gw, 3)
            masks.append(key_alpha(f.astype(np.int16))[0] > 127)
            e = eyes(f)
            if e:
                found.append(np.r_[e[0], e[1]])
    if not found:
        raise RuntimeError("口の動画の中に、キャスターの顔（目の位置）を見つけられませんでした")
    le = np.median(found, 0)
    s0 = float(EYE_DIST / np.linalg.norm(le[2:] - le[:2]))
    # 写真のキャスターの形（モニターの中だけ。キャスター＝+1、緑＝−1）と、口の動画のキャスターの形（1/4 の大きさで探す）
    D = 4
    bx0, by0, bx1, by1 = box
    still = np.asarray(Image.open(STUDIO).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.int16)
    sa = key_alpha(still[by0:by1, bx0:bx1])[0][::D, ::D]
    target = np.where(sa > 127, 1.0, -1.0).astype(np.float32)
    lm = (np.mean(masks, 0) > 0.5).astype(np.float32)
    lm[int(gh * 0.9):] = 0                               # 生成された机のあたりは使わない
    th, tw = target.shape
    best = None
    for scale in np.arange(s0 * 0.8, s0 * 1.25, 0.005):
        n = max(8, round(gw * scale / D))
        ls = cv2.resize(lm, (n, n), interpolation=cv2.INTER_AREA)
        pad = np.zeros((th + 2 * n, tw + 2 * n), np.float32)
        pad[n:n + th, n:n + tw] = target
        r = cv2.matchTemplate(pad, ls, cv2.TM_CCORR)    # 重なったキャスターの面積 − 緑にはみ出した面積
        yy, xx = np.unravel_index(np.argmax(r), r.shape)
        if best is None or r[yy, xx] > best[0]:
            best = (r[yy, xx], float(scale), (xx - n) * D + bx0, (yy - n) * D + by0)
    _, scale, x, y = best
    return {"scale": scale, "size": round(gw * scale), "x": int(x), "y": int(y), "desk": STILL_DESK - int(y)}


def voice_feats(path, hop=0.02):
    """声の「音色の並び」（0.02秒ごと）と、音の大きさ（0＝いちばん大きい〜−1＝静か）"""
    sr = 8000
    raw = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32)
    n = int(sr * hop)
    win = n * 2
    x = np.pad(x, (win // 2, win // 2))
    fr = np.lib.stride_tricks.sliding_window_view(x, win)[::n] * np.hanning(win)
    sp = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    mel = lambda h: 2595 * np.log10(1 + h / 700)   # noqa: E731
    m, e = mel(np.fft.rfftfreq(win, 1 / sr)), np.linspace(mel(80), mel(3800), 26)
    fb = np.array([np.clip(np.minimum((m - e[i]) / (e[i + 1] - e[i]), (e[i + 2] - m) / (e[i + 2] - e[i + 1])), 0, None)
                   for i in range(24)])
    lm = np.log(sp @ fb.T + 1e-3)
    loud = lm.mean(1)
    loud = np.clip((loud - loud.max()) / (loud.max() - np.percentile(loud, 5) + 1e-9), -1, 0)
    shape = lm - lm.mean(1, keepdims=True)
    shape /= np.linalg.norm(shape, axis=1, keepdims=True) + 1e-9
    return shape, loud


def lip_timeline(lip, voice_wav, hop=0.02, pen=0.15):
    """口の動画は、渡した声の文と文の間を勝手にのばして読み直す（2026-11-07 に 0.4〜2秒ずれた）
    → 両方の声の音色の並びを端から端まで照らし合わせ（DTW）、「こちらの声の時刻 → 口の動画の時刻」の表をつくる
    （声の区間を順に対応させるやり方は、口の動画で区間がつながると使えなかった）"""
    (A, la), (B, lb) = voice_feats(voice_wav, hop), voice_feats(lip, hop)
    D = (1 - A @ B.T) * 0.5 + np.abs(la[:, None] - lb[None, :])
    n, m = D.shape
    C = np.full((n + 1, m + 1), np.inf)
    C[0, 0] = 0
    P = np.zeros((n + 1, m + 1), np.int8)    # 0＝ななめ／1＝こちらだけ進む／2＝口の動画だけ進む（1と2は少し損にする）
    for i in range(1, n + 1):
        diag, up = C[i - 1, :-1] + D[i - 1], C[i - 1, 1:] + D[i - 1] + pen
        best, bp = np.minimum(diag, up), np.where(diag <= up, 0, 1)
        prev = np.inf
        for j in range(m):
            h = prev + D[i - 1, j] + pen
            if h < best[j]:
                C[i, j + 1], P[i, j + 1] = h, 2
            else:
                C[i, j + 1], P[i, j + 1] = best[j], bp[j]
            prev = C[i, j + 1]
    i, j, mp = n, m, np.zeros(n)
    while i > 0 and j > 0:
        mp[i - 1] = max(mp[i - 1], j - 1)
        k = P[i, j]
        i, j = (i - 1, j - 1) if k == 0 else (i - 1, j) if k == 1 else (i, j - 1)
    mp = np.maximum.accumulate(np.convolve(np.pad(mp, 2, mode="edge"), np.ones(5) / 5, "valid")) * hop   # 0.1秒でならす
    rx = np.arange(n) * hop
    log(f"口の動画の時刻を声に合わせる（いちばん大きいずれ {(mp - rx).max():+.2f}秒）")
    return lambda t: float(np.interp(t, rx, mp) if t <= rx[-1] else mp[-1] + t - rx[-1])


def lipsync(work, voice_wav, max_usd):
    """キャスターの顔と胸の部分を、声（voice_wav）に口を合わせた動画にする。できた mp4 の場所を返す"""
    out = work / "caster_lipsync.mp4"
    if out.exists():
        return out
    x0, y0, x1, y1 = LIP_BOX
    crop = work / "caster_crop.png"
    Image.open(STUDIO).convert("RGB").resize((W, H), Image.LANCZOS).crop(LIP_BOX).save(crop)
    dur = math.ceil(narrate.duration(voice_wav))
    req = {"prompt": ("@image1 is the exact first frame. A Japanese male TV news anchor in a navy suit sits at the news desk and reads the news "
                      "in Japanese exactly as in @audio1, with precise lip sync to every syllable. He keeps the same calm, gentle, kind "
                      "expression as in @image1 and never smiles. Only his lips, jaw and a natural slow blink move; head almost still, "
                      "shoulders and body still. The camera is completely locked off: no zoom, no pan, no movement. The bright green screen "
                      "behind him stays flat pure green. Same person, same face, same hair, same suit in every frame. "
                      "Avoid: smiling, laughing, head turning, hand movement, camera movement, text, captions, subtitles, watermark."),
           "image_urls": [hf_upload(crop, "image/png")],
           "audio_urls": [hf_upload(voice_wav, "audio/wav")],
           "duration": dur, "resolution": LIP_RES, "aspect_ratio": "1:1"}
    est = requests.post(f"https://api.higgsfield.ai/estimate/{LIP_MODEL}", headers=hf_key(), json=req, timeout=60).json()
    usd = float(est.get("usd") or 0)
    if not usd:   # Seedance は金額でなく計算式だけを返す → 式のとおりに自分で計算する（1:1 の画素数は 16:9 と同じくらい）
        side = {"480p": 640, "720p": 960, "1080p": 1440}[LIP_RES]
        usd = math.ceil(side * side * dur * 24 / 1024) * (0.0234 if LIP_RES == "1080p" else 0.0214) / 1000
    log(f"Higgsfield の見積もり：{usd:.2f}ドル（{LIP_RES}・{dur}秒。上限 {max_usd}ドル）")
    if not usd or usd > max_usd:
        raise RuntimeError(f"見積もりが上限をこえたか、出ませんでした：{est}")
    sub = requests.post(f"https://api.higgsfield.ai/{LIP_MODEL}", headers=hf_key(), json=req, timeout=120).json()
    rid = sub.get("request_id")
    if not rid:
        raise RuntimeError(f"Higgsfield が受け付けませんでした：{sub}")
    (work / "lipsync-request.json").write_text(json.dumps({"request_id": rid, "usd": usd, "input": req}, ensure_ascii=False, indent=1), encoding="utf-8")
    url = sub.get("status_url") or f"https://api.higgsfield.ai/requests/{rid}/status"
    for _ in range(120):
        time.sleep(10)
        st = requests.get(url, headers=hf_key(), timeout=60).json()
        if st.get("status") in ("failed", "nsfw", "canceled"):
            if "balance" in str(st.get("error", "")):
                (work / "lipsync-request.json").rename(work / "lipsync-request-残高不足.json")
                raise RuntimeError("Higgsfield の残高が足りません（お金はかかっていません）。チャージしてから、同じ依頼をもう一度つくってください")
            raise RuntimeError(f"Higgsfield の生成が止まりました：{st}")
        if st.get("status") == "completed":
            out.write_bytes(requests.get(st["video"]["url"], timeout=300).content)
            return out
    raise RuntimeError(f"Higgsfield が20分たっても終わりません。request_id={rid}（二重にお金がかかるので、作り直す前に確かめる）")


# ---------------------------------------------------------------- 7. 音
def read_wav(path):
    with wave.open(str(path)) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return a.reshape(-1, w.getnchannels())[:, :2] if w.getnchannels() > 1 else np.repeat(a[:, None], 2, 1)


def write_wav(path, a):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


def sting(sec=1.6):
    """はじまりの「ポーン」という報道番組ふうの音（その場でつくる）"""
    t = np.arange(int(sec * SR)) / SR
    out = np.zeros_like(t)
    for st, hz, amp in ((0.0, 1318.5, 0.22), (0.0, 659.3, 0.16), (0.11, 1975.5, 0.12)):
        tt = np.clip(t - st, 0, None)
        out += amp * np.sin(2 * np.pi * hz * tt) * np.exp(-tt * 3.2) * (t >= st)
    out *= np.minimum(1, t / 0.005)
    return np.repeat(out[:, None], 2, 1).astype(np.float32)


def put(mix, clip, at, vol=1.0):
    i = int(at * SR)
    n = min(len(clip), len(mix) - i)
    if n > 0:
        mix[i:i + n] += clip[:n] * vol


def fade(a, sec=0.06):
    n = min(int(sec * SR), len(a) // 2)
    if n:
        ramp = np.linspace(0, 1, n)[:, None]
        a[:n] *= ramp
        a[-n:] *= ramp[::-1]
    return a


# ---------------------------------------------------------------- 8. 組み立て
def build(order_path, caster_mode="still", max_usd=3.5):
    order_path = pathlib.Path(order_path).resolve()
    work = order_path.parent
    order = json.loads(order_path.read_text(encoding="utf-8"))
    kind = order.get("kind", "bright")
    if kind not in KINDS:
        raise SystemExit("kind は bright / trouble / info のどれか")
    src = work / order["video"]
    log(f"■ ALCニュース：{KINDS[kind]}・キャスター {caster_mode}")

    mp4, swav = prepare_source(src, work)
    src_len = media_len(mp4)
    segs = transcribe(swav, work)
    log(f"書き起こし：{len(segs)}文")

    # 台本と声（長すぎたら1回だけ短くしてもらう）
    feedback = ""
    for attempt in range(3):
        sp = work / "台本.json"
        if attempt == 0 and sp.exists():
            spec = json.loads(sp.read_text(encoding="utf-8"))
        else:
            spec = ask_claude(make_prompt(order, segs, src_len, feedback))
            sp.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        close_text = spec["close_line"].rstrip("。") + "。"
        d_open = speak(spec["open"], work / "voice_open.wav")
        d_close = speak(close_text, work / "voice_close.wav")
        d_vo = speak(spec["vo"], work / "voice_vo.wav") if kind == "info" and spec.get("vo") else 0
        LA = STING + d_open + A_TAIL
        LC = C_HEAD + d_close + C_TAIL
        room = MAX_TOTAL - LA - LC
        if room >= max(B_MIN, d_vo + 0.8):
            break
        feedback = (f"\n\n## 直し\n前の台本は長すぎました（最初の原稿 {d_open:.1f}秒・最後 {d_close:.1f}秒"
                    + (f"・Bロールの要約 {d_vo:.1f}秒" if d_vo else "") + "）。全体20秒に入るよう、どれも2〜3割短くしてください。")
        log("長すぎるので短くしてもらう")
    else:
        raise RuntimeError("台本が20秒に入りませんでした")

    bs = max(0.0, min(float(spec["broll_start"]), src_len - B_MIN))
    be = min(float(spec["broll_end"]), src_len)
    LB = round(min(max(be - bs, B_MIN, d_vo + 0.8), room, src_len - bs), 2)
    news = LA + LB + LC
    end_wav = work / "ending.wav"                      # ブランドボードの声（この動画の音の形にそろえる）
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(ENDING_WAV), "-ar", str(SR), "-ac", "2", str(end_wav)])
    LE = E_HEAD + media_len(end_wav) + E_TAIL
    total = news + LE
    log(f"長さ：キャスター {LA:.1f}秒 ＋ Bロール {LB:.1f}秒（元の {bs:.1f}〜{bs + LB:.1f}秒）＋ 締め {LC:.1f}秒 ＋ ブランドボード {LE:.1f}秒 ＝ {total:.1f}秒")

    # 音
    mix = np.zeros((int(total * SR) + SR, 2), np.float32)
    put(mix, sting(), 0, 0.9)
    put(mix, read_wav(work / "voice_open.wav"), STING)
    src_a = read_wav(swav)
    seg = src_a[int(bs * SR):int((bs + LB) * SR)].copy()
    if kind == "trouble":   # 声を変える（低く・はやさは同じ）
        tmp_in, tmp_out = work / "b_in.wav", work / "b_voice.wav"
        write_wav(tmp_in, seg)
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp_in),
             "-af", f"asetrate={SR}*0.78,aresample={SR},atempo=1.282,highpass=f=120,lowpass=f=6000", str(tmp_out)])
        seg = read_wav(tmp_out)
    peak = float(np.abs(seg).max() or 1)
    seg = fade(seg * min(4.0, 0.7 / peak))
    put(mix, seg, LA, 0.14 if kind == "info" else 1.0)
    if d_vo:
        put(mix, read_wav(work / "voice_vo.wav"), LA + 0.4)
    put(mix, read_wav(work / "voice_close.wav"), LA + LB + C_HEAD)
    put(mix, read_wav(end_wav), news + E_HEAD)
    mix = mix[:int(total * SR)]
    write_wav(work / "mix.wav", mix)

    # 字幕の時間
    subs_a = time_cards(spec["open"], STING, d_open)
    subs_c = time_cards(close_text, LA + LB + C_HEAD, d_close)
    if kind == "info":
        subs_b = [(a, b, c, "caster") for a, b, c in time_cards(spec["vo"], LA + 0.4, d_vo)]
    else:
        subs_b = []
        for s in spec.get("subs") or []:
            a, b = float(s["start"]) - bs + LA, float(s["end"]) - bs + LA
            a, b = max(a, LA), min(b, LA + LB)
            if b - a > 0.3:
                for i, c in enumerate(cards(s["text"], 14, 2)):   # 長い字幕は分けて順に出す
                    n = len(cards(s["text"], 14, 2))
                    subs_b.append((a + (b - a) * i / n, a + (b - a) * (i + 1) / n, c, "speaker"))

    # 重ねる絵
    caster, box = studio_layer()
    px0, py0, px1, py1 = box
    pw, ph = px1 - px0, py1 - py0
    hd = header(spec["headline"])
    static_ac = layer()
    static_ac.alpha_composite(panel_title(box, spec["panel_title"], spec.get("panel_sub", "")))
    vw = int(font(34).getlength("視聴者投稿")) + 32
    static_ac.alpha_composite(viewer_label(px1 - vw - 28, py1 - 52 - 28))   # モニターの右下の隅（2026-11-07 タケシさんの直し）
    static_ac.alpha_composite(nameplate())
    static_ac.alpha_composite(hd)
    static_ac = np.asarray(static_ac)
    static_b = layer()
    static_b.alpha_composite(broll_telop(spec["broll_telop"], kind))
    static_b.alpha_composite(hd)
    static_b = np.asarray(static_b)
    sub_imgs = {}

    def sub_at(t, lst, style):
        for a, b, c, *st in lst:
            if a <= t < b:
                k = (c, st[0] if st else style)
                if k not in sub_imgs:
                    sub_imgs[k] = np.asarray(broll_sub(c) if k[1] == "speaker" else caster_sub(c))
                return sub_imgs[k]
        return None

    # キャスターの動く映像（lipsync のとき）：A と C の声を1本にして、口を合わせた動画をつくる
    lip_reader = None
    if caster_mode == "lipsync":
        voice_all = np.zeros((int((LA + LC) * SR) + SR, 2), np.float32)
        put(voice_all, read_wav(work / "voice_open.wav"), STING)
        put(voice_all, read_wav(work / "voice_close.wav"), LA + C_HEAD)
        vpath = work / "voice_caster.wav"
        write_wav(vpath, voice_all[:int(math.ceil(LA + LC) * SR)])
        lip = lipsync(work, vpath, max_usd)
        # Seedance は渡した写真の構図を守らず、緑の背景の前に小さめのキャスターをつくる（2026-11-07）
        # → 緑を抜いてキャスターだけにし、元の写真と同じ大きさ・位置に合わせて、空のスタジオの上に重ねる
        fit = lip_fit(lip, box)
        log(f"口の動画を {fit['scale']:.2f}倍にして ({fit['x']}, {fit['y']}) に置く")
        lip_time = lip_timeline(lip, vpath)
        lip_reader = Reader(lip, 0, int(media_len(lip) * FPS) + 2, (fit["size"], fit["size"]))
        lip_pos = {"k": -1, "frame": None}
        empty = np.asarray(Image.open(STUDIO_EMPTY).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.int16)
        ea, _ = key_alpha(empty)
        empty_layer = np.dstack([despill(empty, ea), ea]).astype(np.uint8)
        desk_layer = empty_layer.copy()                 # 手前の机（キャスターより前に置く）
        desk_layer[:STILL_DESK, :, 3] = 0
    base_caster = caster[..., :3]
    mosaic = Mosaic() if kind == "trouble" else None

    nA, nB, nC = round(LA * FPS), round(LB * FPS), round(LC * FPS)
    nE = round(LE * FPS)
    n_all = nA + nB + nC + nE
    board = np.asarray(Image.open(ENDING_IMG).convert("RGB").resize((W, H), Image.LANCZOS))
    last = None                                      # キャスターの最後のコマ（ブランドボードへ少しずつ切りかえる）
    out = work / "ALCニュース.mp4"
    enc = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-i", str(work / "mix.wav"),
                            "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                            "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
                            "-movflags", "+faststart", "-shortest", str(out)], stdin=subprocess.PIPE)
    # モニターに映す範囲：A は Bロールの少し前から、C は Bロールの終わりから（なければ同じ所）
    panel_a = Reader(mp4, max(0.0, bs - LA) if bs >= 2 else bs, nA)
    r_b = Reader(mp4, bs, nB)
    c_start = bs + LB if bs + LB + LC <= src_len else max(0.0, src_len - LC)
    panel_c = Reader(mp4, c_start, nC)

    def caster_frame(t_caster, panel):
        """スタジオ（キャスター）の後ろのモニターに、投稿動画をはめこむ。t_caster ＝ キャスターの声の上での時刻"""
        bg = np.zeros((H, W, 3), np.uint8)
        bg[py0:py1, px0:px1] = cover(panel, pw, ph)
        if lip_reader is None:
            return blend(bg, caster)
        want = round(lip_time(t_caster) * FPS)          # 声に合う口のコマまで読み進める（時刻は先へしか進まない）
        while lip_pos["k"] < want or lip_pos["frame"] is None:
            lip_pos["frame"] = next(lip_reader)
            lip_pos["k"] += 1
        frame = lip_pos["frame"].astype(np.int16)
        la, _ = key_alpha(frame)
        la = cv2.GaussianBlur(cv2.erode(la, np.ones((5, 5), np.uint8)), (5, 5), 0)   # 髪・肩のふちの緑を残さない
        la[fit["desk"]:] = 0                              # 生成された机から下は使わない
        layer_c = np.zeros((H, W, 4), np.uint8)          # キャスターだけの層（1080×1920 の中に置く）
        x, y, n = fit["x"], fit["y"], fit["size"]
        sx0, sy0 = max(0, -x), max(0, -y)
        dx0, dy0 = max(0, x), max(0, y)
        w_, h_ = min(n - sx0, W - dx0), min(n - sy0, H - dy0)
        layer_c[dy0:dy0 + h_, dx0:dx0 + w_, :3] = despill(frame, np.zeros_like(la), 0)[sy0:sy0 + h_, sx0:sx0 + w_]   # 緑の背景の照り返し（髪の緑み）を全体から取る
        layer_c[dy0:dy0 + h_, dx0:dx0 + w_, 3] = la[sy0:sy0 + h_, sx0:sx0 + w_]
        return blend(blend(blend(bg, empty_layer), layer_c), desk_layer)

    try:
        for i in range(n_all):
            t = i / FPS
            if i < nA:
                f = next(panel_a)
                f = mosaic(f) if mosaic else f
                fr = caster_frame(t, f)
                fr = blend(fr, static_ac)
                s = sub_at(t, [(a, b, c) for a, b, c in subs_a], "caster")
            elif i < nA + nB:
                f = next(r_b)
                fr = mosaic(f) if mosaic else f
                fr = blend(fr, static_b)
                s = sub_at(t, subs_b, "speaker")
            elif i < nA + nB + nC:
                f = next(panel_c)
                f = mosaic(f) if mosaic else f
                fr = caster_frame(t - nB / FPS, f)         # 口の動画の中では、C は A のすぐあと
                fr = blend(fr, static_ac)
                s = sub_at(t, [(a, b, c) for a, b, c in subs_c], "caster")
            else:                                           # D ブランドボード
                k = min(1.0, (i - nA - nB - nC + 1) / (E_FADE * FPS))
                fr = board if k >= 1 or last is None else (last * (1 - k) + board * k).astype(np.uint8)
                s = None
            if s is not None:
                fr = blend(fr, s)
            if i < nA + nB + nC:
                last = fr
            enc.stdin.write(fr.tobytes())
            if i % 60 == 0:
                log(f"組み立て {i}/{n_all}")
    finally:
        enc.stdin.close()
        enc.wait()
        for r in (panel_a, r_b, panel_c, lip_reader):
            if r:
                r.close()
    log(f"できました：{out}（{media_len(out):.1f}秒）")
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("order")
    ap.add_argument("--caster", choices=["still", "lipsync"], default="still")
    ap.add_argument("--max-usd", type=float, default=3.5)
    a = ap.parse_args()
    build(a.order, a.caster, a.max_usd)
