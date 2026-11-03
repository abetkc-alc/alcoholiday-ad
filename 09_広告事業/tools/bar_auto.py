# ALCOHOLIDAY BAR広告：新しい申し込みを自動で動画にして、お客さんに「動画ができました」メールを送る
#
#   1. 受付台帳の「受付」の申し込みを取り込む（bar_sync.py pull と同じ）
#   2. KAYO（Claude）が台本（ナレーション・字幕）と、えらばれた SNS ごとの投稿文をつくる（claude -p）
#      投稿文の最後には「提供：アルコホリディ」と URL を、プログラムが必ず付ける（2026-10-10 社長の指示）
#   ※ 直しの依頼（「修正依頼」。1回まで）も同じように自動で直して、もう一度メールを送る（2026-10-04 社長の指示）
#      2026-10-31 タケシの指示：無料版は直しなし。有料版は、確認ページでお客さんが直した「ひらがなの読み方」で読み直す（make_reading_fix）
#   3. 動画を組み立てる（build_bar_ad.py。台帳の「プラン」が「有料」なら有料版、それ以外は無料版）
#   4. 投稿文の決まりを確かめて、お客さんに「動画ができました」メールを送る（bar_sync.py deliver と同じ）
#
# 使い方（09_広告事業 フォルダで）
#   python tools/bar_auto.py            … 新しい申し込みを全部処理する（Windows のタスク スケジューラーから数分ごとに動かす）
#   python tools/bar_auto.py <受付番号>  … その案件だけ、台本づくりからやり直す（取り込み済みのもの）
#   python tools/bar_auto.py <受付番号> fix "直しの依頼の文" … その案件の直しだけをする
#   python tools/bar_auto.py <受付番号> --dry … 動画までつくって、メールは送らない（試し）
#
# 2026-10-04 社長の指示：お客さんの申し込みから「動画ができました」メールまでを自動にする。
#   2026-10-10 から SNS への投稿はしない。お客さんが確認ページで動画を決めて、ダウンロードし、自分の SNS に載せる。
#   うまくいかなかった案件は「制作中」のまま残し、自動制作ログ.md と受付台帳の履歴に理由を書く（KAYO が手で仕上げる）
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import bar_sync  # noqa: E402
import build_bar_ad  # noqa: E402
import fix_learn  # noqa: E402  直しから学んだこと（2026-10-10）
import narrate  # noqa: E402  読み方の直し（有料版のひらがなをつくるとき）

HERE = TOOLS.parent                      # 09_広告事業
LOG = HERE / "自動制作ログ.md"
LOCK = HERE / "案件" / ".自動制作中"
MUSIC_DIR = pathlib.Path(r"C:\Users\abetk\Desktop\ALCOHOLIDAY\音声\backmusic")
# 申し込みページでお客さんがえらぶ音楽（2026-10-11 社長の指示）。"" は音楽なし
MUSIC_CHOICES = {"バンドサウンド": "BAND_SOUND.mp3", "ボサノバ": "BOSANOVA.mp3", "ジャズ": "JAZZ.mp3", "ポップ": "pop.mp3", "音楽なし": ""}
MUSIC_TAGS = HERE / "素材" / "音楽の札.json"   # 曲ごとの雰囲気の札（KAYO は曲を聞けないので、この札で選ぶ）
DEFAULT_VOICE = "A"
DRY = "--dry" in sys.argv          # 試し：動画までつくって、メールは送らない
if DRY:
    sys.argv.remove("--dry")


def log(msg):
    line = f"- {datetime.now():%Y-%m-%d %H:%M} {msg}"
    print(line)
    with LOG.open("a", encoding="utf-8") as f:
        if f.tell() == 0:
            f.write("# BAR広告 自動制作ログ\n\n[[広告事業]] の申し込みを自動で動画にした記録（tools/bar_auto.py）\n\n")
        f.write(line + "\n")


def rules():
    """広告事業.md の「台本のきまり」をそのまま Claude に渡す（＋直しから学んだこと.md の学び。2026-10-10 社長の指示）"""
    t = (HERE / "広告事業.md").read_text(encoding="utf-8")
    a = t.index("## 台本のきまり")
    b = (HERE / "禁止表現リスト.md").read_text(encoding="utf-8")
    b = b[:b.index("## 自動で見つける言葉")].strip()
    return (t[a:t.index("\n---", a)] + "\n\n" + b.replace("\n## ", "\n### ").replace("# 禁止表現リスト", "## 禁止表現リスト", 1)
            + fix_learn.lessons_for_prompt())


def banned_words():
    """禁止表現リスト.md の「自動で見つける言葉」（機械で探す言葉）"""
    t = (HERE / "禁止表現リスト.md").read_text(encoding="utf-8")
    t = t[t.index("## 自動で見つける言葉"):]
    t = t[t.index("```") + 3:]
    return [w.strip() for w in t[:t.index("```")].splitlines() if w.strip()]


def allowed_words():
    """禁止表現リスト.md の「機械で探すときに外す言葉」（タリスカーの中のリスカなど。2026-10-14）"""
    t = (HERE / "禁止表現リスト.md").read_text(encoding="utf-8")
    if "## 機械で探すときに外す言葉" not in t:
        return []
    t = t[t.index("## 機械で探すときに外す言葉"):]
    t = t[t.index("```") + 3:]
    return [w.strip() for w in t[:t.index("```")].splitlines() if w.strip()]


def find_shop_name(a, shop, kana):
    """ナレーションの店名が、お客さんの入れたカナになっているかを調べる（2026-10-31 タケシの指示：店名を読み上げてよい。
    前の「店名は読み上げない」（2026-10-17）はやめた）。字幕は正式名称のままでよいので調べない。カナのない前の申し込みは調べない"""
    flat = lambda s: "".join(str(s).split()).lower()
    name, kana = flat(shop), str(kana).strip()
    if not kana or len(name) < 2 or name == flat(kana):
        return []
    return [f"動画{i}のナレーションに店名が「{shop}」のまま書いてある。ナレーションでは店名を「{kana}」と書く（字幕は「{shop}」のままでよい）"
            for i, c in enumerate(a.get("clips", []), 1) if name in flat(c.get("narr", ""))]


def find_banned(a):
    """台本と投稿文から禁止の言葉を探す。見つかったら直すところのリストを返す"""
    texts = [("ナレーション・字幕", " ".join(str(c.get("narr", "")) + " " + " ".join(map(str, c.get("subs", []))) for c in a.get("clips", [])))]
    texts += [("画面の文字", " ".join(str(a.get(k, "")) for k in ("product", "price", "area", "hours")))]
    texts += [(f"投稿文（{k}）", str(v)) for k, v in (a.get("captions") or {}).items()]
    flat = lambda s: "".join(s.split()).lower()
    ok = [flat(w) for w in allowed_words()]
    probs = []
    for where, s in texts:
        s = flat(s)
        for w in ok:
            s = s.replace(w, "／")
        hit = [w for w in banned_words() if flat(w) in s]
        if hit:
            probs.append(f"{where}に禁止の言葉「{'」「'.join(hit)}」がある。違う言葉に置き換える（置き換えられなければ、その部分を削る）")
    return probs


def ask_claude(prompt):
    """claude -p で答えをもらい、その中の JSON を取り出す"""
    # 申し込みの中身が変わっていると、Claude が JSON のかわりに質問を返すことがある（2026-10-07）。
    # 答える人はいないので、念を押してもう1回だけ頼む
    for i in range(2):
        r = subprocess.run(["claude", "-p", "--output-format", "text"], input=prompt, capture_output=True,
                           text=True, encoding="utf-8", timeout=600, cwd=str(HERE))
        if r.returncode != 0:
            raise RuntimeError("Claude が答えませんでした：" + (r.stderr or r.stdout)[:300])
        m = re.search(r"\{.*\}", r.stdout, re.S)
        if m:
            return json.loads(m.group(0))
        prompt += ("\n\n## もう一度\n前の答えに JSON がありませんでした。これは自動の処理で、質問に答える人はいません。"
                   "確認や質問はせず、上の決まりに従って、必ず JSON だけを返してください。"
                   "宣伝に向かない言葉や心配な言葉は使わず、商品とお店の紹介として作ってください。")
    raise RuntimeError("Claude の答えに JSON がありません：" + r.stdout[:300])


NARR_CPS = 5.0    # 声が1秒に読む文字数（Google の声で、間やひらがなの読みがあると約4.5〜5文字。2026-10-16 試して決めた）
NARR_MAX = 45     # 1本のナレーションの上限（字幕15文字×3行）
NARR_MIN = 20


def narr_budget(dur):
    """動画の長さから、ナレーションの文字数の目安を決める（2026-10-16 社長「読み上げを多く」。前は一律20〜25文字）
    使えるのは「使い始め0.3秒・終わりの余り0.1秒・声の前後の間0.9秒」を引いた分"""
    return int(max(NARR_MIN, min(NARR_MAX, (dur - 1.3) * NARR_CPS)))


def make_prompt(order, clips, feedback=""):
    vids = json.loads(order.get("動画の説明") or "[]")
    # 2026-10-16 社長の指示：動画ごとの説明の欄はなくなった。「商品の説明」1つから、3本の動画のナレーションを分けてつくる
    #   （前の申し込みで動画ごとの説明があるときは、それも渡す）
    lines = [f"動画{v['no']}（{v['title']}・長さ {c['dur']:.1f}秒・ナレーションは{narr_budget(c['dur'])}文字くらいまで）"
             + (f"：お客さんの説明「{v['desc']}」" if str(v.get("desc") or "").strip() else "")
             for v, c in zip(vids, clips)]
    music = music_list()
    plats = bar_sync.platforms_of(order)
    return f"""あなたは ALCOHOLIDAY の KAYO（scripts 部）です。BAR のおすすめ商品を紹介する縦型動画の台本と SNS の投稿文をつくります。
動画と投稿文は、お店が自分の SNS アカウントに載せます（お店の立場で書く）。
ツールは使わず、下の決まりに従って、最後に JSON だけを返してください（説明の文は不要）。

{rules()}

## この申し込み
- 店名：{order['店名']}
- 店名の読み（カナ）：{order.get('店名カナ') or '（なし）'}
- 都道府県：{order['都道府県']}
- 住所：{order.get('住所', '')}
- 最寄り駅・エリア：{order.get('エリア', '')}
- 営業時間：{order.get('営業時間', '')}
- 電話：{order.get('電話', '')}
- お店の SNS：{order.get('店のSNS', '')}
- おすすめ商品：{order['商品名']}
- 商品の説明：{order.get('商品の説明', '')}
- 価格：{order.get('価格', '')}
- 数量限定：{order.get('数量限定', '')}
- 投稿文をつくる SNS：{','.join(plats)}
{chr(10).join('- ' + x for x in lines)}

## 返す JSON の形
{{
  "clips": [
    {{"narr": "動画1のナレーション（上の「ナレーションは〇文字くらいまで」の文字数）", "subs": ["字幕1行目", "字幕2行目", "字幕3行目"]}},
    {{"narr": "動画2…", "subs": ["…", "…", "…"]}},
    {{"narr": "動画3…", "subs": ["…", "…", "…"]}}
  ],
  "voice": "声の案内役（お客さんの指定が A/B/C/D ならそれ。おまかせなら店の雰囲気で A=ローズ（明るい女性）B=ラフィ（大人の女性）C=アイラ（落ち着いた女性）D=アルビン（男性）から選ぶ）",
  "product": "画面に出す商品名（40文字まで。お客さんの商品名をもとに整える）",
  "price": "画面に出す価格（例：600円（税込））",
  "area": "画面に出す場所（例：東京都豊島区・要町駅から徒歩3分）",
  "hours": "画面に出す営業時間（短く整える。例：18時〜翌2時（日曜定休））",
  "music": "背景の音楽のファイル名（お客さんがえらんだ曲を使うので、\"\" でよい。えらんでいない申し込みだけ、店の雰囲気に合う札の曲を下の「背景の音楽」から1つ）",
  "captions": {{{', '.join(f'"{p}": "…"' for p in plats)}}}
}}

## 背景の音楽（ファイル名：札・感じ）
{music}

## 気をつけること
- 卑猥な言葉・差別的な言葉・誹謗中傷・乱暴な言葉は一切使わない（お客さんが書いた言葉でも使わない。ナレーション・字幕・商品名・投稿文すべて）
- 上の「禁止表現リスト」の表現と、それに近い表現は使わない。お客さんの言葉にあったら、違う言葉に置き換える
- これは自動の処理で、質問に答える人はいない。確認や質問はせず、必ず JSON を返す。申し込みに宣伝に向かない言葉や心配な言葉があれば、それは使わず、商品とお店の紹介として作る
- **ナレーションは多めに**（2026-10-16 社長の指示）：動画ごとの「ナレーションは〇文字くらいまで」の8〜10割を使い、動画のあいだ声がとぎれないようにする。文字数をこえない。説明にないことは足さない
- **ナレーションは「商品の説明」の文から、3本に分けてつくる**（2026-10-16 社長の指示。お客さんは動画ごとの文を書かない）
  - 動画1（お店の雰囲気）：説明の中の、お店の場所・雰囲気の言葉。なければ場所でお店を紹介する
  - 動画2（おすすめ商品）：説明の中の、商品の味・素材・こだわり・飲み方の言葉と商品名
  - 動画3（自由）：説明の中の、マスターやお店の魅力の言葉、または商品をすすめる言葉で明るく締める
  - 3本で同じことをくり返さない。説明の言葉をなるべくそのまま使い、足りないときは商品名・場所を足す（決まり文句・説明にないほめ言葉は足さない）。長いときだけ、言いかえずに削って短くする
  - 動画ごとの「お客さんの説明」がある申し込み（前のページ）は、その言葉を優先する
- ナレーションは、声に出して自然に流れる文にする（体言止めを続けない・読点「、」で息つぎする所を入れる）。字幕（subs）はナレーションを1行15文字までに分けたもの（3行まで）
- お客さんの説明にスペース（半角・全角）があれば、ナレーション（narr）でも同じところにスペースを残す（読み上げでそこに一拍おくため）。スペースのないところに足さない
- 「今夜はここへ」「まずはここへ」「今夜はここで」や、それに似た言葉は使わない
- **言い回しは、原則としてすべて明るく**する（ナレーション・字幕・投稿文。前向きで楽しい感じに。2026-10-11 社長の指示）
- 投稿文の住所・営業時間・電話番号は、上の「この申し込み」の文字を**そのまま**入れる（自動で確かめるため。言い換えない）
- 投稿文は「投稿文をつくる SNS」の分だけつくる（{'・'.join(bar_sync.PLATFORM_NAMES[p] for p in plats)}）
- 投稿文の本文は「商品の説明」をもとに書く。説明にないことは足さない
- どの投稿文にも「#PR」「お酒は20歳になってから。飲酒運転は法律で禁止されています。」を必ず入れる
- 「提供：アルコホリディ」と URL は、プログラムが投稿文の最後に付けるので、書かない（X は、その分を残して本文を230までにする）
- 数量限定が「はい」なら、投稿文にも「数量限定」とわかる一言を入れる
{feedback}"""


def music_list():
    """使ってよい曲と、その札の一覧（札の表がなければ曲の名前だけ）"""
    try:
        tags = json.loads(MUSIC_TAGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tags = {}
    rows = []
    for p in sorted(MUSIC_DIR.glob("*.mp3")):
        t = tags.get(p.name, {})
        if t.get("use") is False:
            continue
        rows.append(f"- {p.name}：{'・'.join(t.get('札', []))}　{t.get('感じ', '')}")
    return "\n".join(rows)


def find_clips(d):
    files = []
    for no in (1, 2, 3):
        cand = sorted((d / "素材").glob(f"video{no}.*"))
        if not cand:
            raise RuntimeError(f"動画{no}が見つかりません")
        files.append(cand[-1])
    return [{"file": f, "dur": build_bar_ad.probe(f)["dur"]} for f in files]


def next_out(d):
    n = 1
    while (d / "動画" / f"bar-ad-v{n}.mp4").exists():
        n += 1
    return f"動画/bar-ad-v{n}.mp4"


def produce(oid, d, order, clips, ask, what, keep_voice):
    """Claude の答え（ask）から動画をつくり、決まりを確かめて届ける。うまくいかなければ理由を伝えて3回までつくり直す"""
    (d / "動画").mkdir(exist_ok=True)
    feedback = ""
    for attempt in (1, 2, 3):
        a = ask(feedback)
        if isinstance(a.get("changes"), list):   # 「直したところ」が箇条書きで返ってきたら1つの文にする
            a["changes"] = "／".join(map(str, a["changes"]))
        mine = order.get("案内役") if order.get("案内役") in bar_sync.GUIDE_NAMES else None
        voice = (mine if keep_voice and mine else None) or (a.get("voice") if a.get("voice") in bar_sync.GUIDE_NAMES else None) or mine or DEFAULT_VOICE
        # 音楽：新しい申し込みはお客さんがえらんだ曲（2026-10-11〜）。直しは Claude の答え（"" は音楽なし）
        chosen = MUSIC_CHOICES.get(order.get("音楽"))   # None＝えらんでいない（前の申し込み）
        name = a.get("music", "") or ""
        if keep_voice and chosen is not None:
            name = chosen
        elif name in ("", "なし", "音楽なし") and not keep_voice:
            name = ""
        elif not (MUSIC_DIR / name).is_file() or name not in music_list():
            name = chosen if chosen is not None else "かろやかな心で.mp3"
        music = (MUSIC_DIR / name).as_posix() if name else ""
        starts = a.get("starts") or []
        spec = {
            "out": next_out(d), "voice": voice,
            "clips": [{"file": f"素材/{c['file'].name}",
                       "start": clamp_start(starts[i] if i < len(starts) else None, c["dur"]),
                       "narr": x["narr"], "subs": x["subs"]} for i, (c, x) in enumerate(zip(clips, a["clips"]))],
            "product": a["product"], "price": a["price"], "shop": order["店名"], "area": a["area"], "hours": a["hours"],
            "music": music, "music_ss": 0, "limited": order.get("数量限定") == "はい",
            "date": datetime.now().strftime("%Y-%m-%d"),   # 動画1の右上に出す日付（つくった日）
            "plan": "paid" if order.get("プラン") == "有料" else "free",   # 無料版／有料版（2026-10-10 社長の指示）
        }
        spec["clips"][1]["show"] = "product"
        spec["clips"][2]["show"] = "shop"
        # えらばれた SNS の分だけにし、最後に「提供：アルコホリディ」と URL を付ける
        cap = {p: bar_sync.add_credit(a["captions"][p]) for p in bar_sync.platforms_of(order) if (a.get("captions") or {}).get(p)}
        a["captions"] = cap
        bad = find_banned(a)   # 禁止表現リスト.md の言葉（2026-10-07 社長の指示）
        probs = bad + find_shop_name(a, order["店名"], order.get("店名カナ", "")) + [p for p in bar_sync.check_captions(oid, cap) if not p.startswith("注意：")]
        if probs:
            feedback = "\n## 前の答えの直すところ（必ず直す）\n- " + "\n- ".join(probs)
            log(f"{oid} {'禁止の言葉があるので' if bad else '投稿文の決まりが足りないので'}つくり直し（{attempt}回目）：{' / '.join(probs)}")
            continue
        # ファイルは上書きしない：動画の番号（v1, v2…）ごとに別の名前で残す
        ver = pathlib.Path(spec["out"]).stem.replace("bar-ad-", "")
        spec_path, cap_path = d / f"制作-{ver}.json", d / f"投稿文-{ver}.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        cap_path.write_text(json.dumps(cap, ensure_ascii=False, indent=2), encoding="utf-8")
        # エラーの文が文字化けすると Claude が直し方をわからないので、utf-8 で出させる（2026-10-14）
        r = subprocess.run([sys.executable, str(TOOLS / "build_bar_ad.py"), str(spec_path)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(HERE),
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if r.returncode != 0:
            msg = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["?"]
            feedback = f"\n## 前の答えの直すところ（必ず直す）\n- 動画を組み立てられませんでした：{msg[0]}。ナレーションをもっと短くしてください"
            log(f"{oid} 動画の組み立てに失敗したのでつくり直し（{attempt}回目）：{msg[0]}")
            continue
        video = d / spec["out"]
        write_script_note(d / f"台本-{ver}.md", spec, cap, a.get("changes", ""))
        # 有料版：読み上げのひらがなを確認ページに出し、お客さんが読み方を直せるようにする（2026-10-31 タケシの指示）
        yomi = a.get("yomi") or (make_yomi([c["narr"] for c in spec["clips"]]) if spec["plan"] == "paid" else None)
        if yomi:
            (d / f"よみ-{ver}.json").write_text(json.dumps(yomi, ensure_ascii=False, indent=2), encoding="utf-8")
        if DRY:
            log(f"{oid} 試し（--dry）：{what}の動画 {video.name} をつくった。メールは送っていない")
            return
        bar_sync.deliver(oid, str(video), str(cap_path), yomi)
        bar_sync.call("update", id=oid, fields={}, log=f"自動制作：{what}の動画 {video.name} を届け、「動画ができました」メールを送った")
        log(f"{oid} {order['店名']}：{what}の動画 {video.name}（{'有料版' if spec['plan'] == 'paid' else '無料版'}・声：{bar_sync.GUIDE_NAMES[voice]}）を届け、「動画ができました」メールを送った"
            + (f"　直したところ：{a.get('changes')}" if a.get("changes") else ""))
        return
    raise RuntimeError("3回つくり直してもうまくいきませんでした")


def clamp_start(v, dur):
    """動画の使い始め（秒）。指定がなければ 0.3 秒。4.5秒ぶん残るようにする"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 0.3 if dur >= 5.0 else 0.0
    return round(max(0.0, min(v, dur - 3.0)), 2)


def make_case(oid):
    """新しい申し込み"""
    d = bar_sync.CASES / oid
    order = json.loads((d / "order.json").read_text(encoding="utf-8"))
    clips = find_clips(d)
    produce(oid, d, order, clips, lambda fb: ask_claude(make_prompt(order, clips, fb)), "新しい申し込み", True)


def latest(d):
    """いちばん新しい 制作-vN.json と、それに合う投稿文"""
    specs = sorted(d.glob("制作-v*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    sp = specs[-1] if specs else d / "制作.json"
    cp = d / sp.name.replace("制作", "投稿文")
    if not cp.exists():   # 手で直したときなど、同じ番号の投稿文がなければ、いちばん新しい投稿文を使う
        caps = sorted(d.glob("投稿文-v*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
        cp = caps[-1] if caps else d / "投稿文.json"
    return json.loads(sp.read_text(encoding="utf-8")), json.loads(cp.read_text(encoding="utf-8"))


def fix_prompt(order, clips, spec, cap, comment, feedback=""):
    now = {
        "clips": [{"narr": c["narr"], "subs": c["subs"]} for c in spec["clips"]],
        "starts": [c.get("start", 0) for c in spec["clips"]],
        "voice": spec.get("voice"), "product": spec.get("product"), "price": spec.get("price"),
        "area": spec.get("area"), "hours": spec.get("hours"), "music": pathlib.Path(spec.get("music", "")).name,
        # 「提供：アルコホリディ」と URL はプログラムが付け直すので、外して渡す
        "captions": {k: bar_sync.add_credit(v).replace("\n\n" + bar_sync.CREDIT, "") for k, v in cap.items()},
    }
    lens = "、".join(f"動画{i}は{c['dur']:.1f}秒" for i, c in enumerate(clips, 1))
    budgets = "、".join(f"動画{i}は{narr_budget(c['dur'])}文字まで" for i, c in enumerate(clips, 1))
    return f"""あなたは ALCOHOLIDAY の KAYO（scripts 部）です。お客さんから、動画の直しの依頼が届きました。
ツールは使わず、依頼に合わせて今の内容を直し、最後に JSON だけを返してください（説明の文は不要）。
言い回しは、原則としてすべて明るくします（前向きで楽しい感じに）。

## お客さんの直しの依頼
{comment}

## 今の内容（この形のまま、直すところだけ変えて返す）
{json.dumps(now, ensure_ascii=False, indent=2)}

## 直せること
- clips：動画1〜3のナレーション（narr。{budgets}）と字幕（subs。1行15文字まで・3行まで）。語尾や言い方、読み方
  - 語尾を下げたいときは、言い切りの形にして「。」で終える（例：「〜をどうぞ。」）。上げたいときは「！」
  - **読み間違いの直しは narr（声）だけをひらがなにする。subs（字幕）は漢字のまま**（例：narr「要町のいっけんや」、subs「要町の一軒家」）
- starts：動画1〜3の使い始め（秒）。{lens}。使い始めから4.5秒ぶん使う
- voice：声（A=ローズ（明るい女性）B=ラフィ（大人の女性）C=アイラ（落ち着いた女性）D=アルビン（男性））
- product・price・area・hours：画面に出す商品名・価格・場所・営業時間
- music：背景の音楽（下の一覧から。音楽なしにするときは ""）
- captions：SNS の投稿文（決まりは下のとおり。「提供：アルコホリディ」と URL はプログラムが最後に付けるので、書かない）
- お店の動画そのものの差し替え・撮り直しはできない。できない依頼は、できる範囲でいちばん近い直し方にする

## 返す JSON に足すもの
- "changes"：直したところを、お客さんにわかる短い日本語で（例：「最後のナレーションの語尾を下げました」）

{rules()}

## 背景の音楽（ファイル名：札・感じ）
{music_list()}

## この申し込みのお店の情報（投稿文の住所・営業時間・電話番号は、この文字をそのまま入れる）
- 店名：{order['店名']}
- 店名の読み（カナ）：{order.get('店名カナ') or '（なし）'}
- 住所：{order.get('住所', '')}
- 営業時間：{order.get('営業時間', '')}
- 電話：{order.get('電話', '')}
{feedback}"""


def make_fix(oid, comment):
    """直しの依頼（1回まで）"""
    d = bar_sync.CASES / oid
    order = json.loads((d / "order.json").read_text(encoding="utf-8"))
    clips = find_clips(d)
    spec, cap = latest(d)
    (d / "直しの依頼.md").open("a", encoding="utf-8").write(f"- {datetime.now():%Y-%m-%d %H:%M} {comment}\n")
    produce(oid, d, order, clips, lambda fb: ask_claude(fix_prompt(order, clips, spec, cap, comment, fb)), "直し", False)


YOMI_OK = re.compile(r"^[ぁ-んァ-ヶー・、。！？!?「」 　0-9０-９]*$")   # Code.gs の YOMI_RE と同じ


def make_yomi(narrs):
    """ナレーションを、声が読むとおりのひらがなにする（有料版の確認ページで見せる。2026-10-31 タケシの指示）
    読み方の直し（BAR→バー・お客さんの直しから学んだ読み方など）をしてから、Claude にひらがなにしてもらう"""
    texts = []
    for t in narrs:
        t = narrate.PERCENT_OFF.sub(r"\1%オフ", t)
        for k, v in narrate.all_readings():
            t = t.replace(k, v)
        texts.append(t)
    prompt = f"""次の3つの文は、動画のナレーション（AI の声が読み上げる文）です。
それぞれを、声に出して読むとおりに、すべてひらがなに書きかえてください。ツールは使わず、最後に JSON だけを返してください。

- 漢字・カタカナ・英字・数字・記号は、読み方のひらがなにする（例：「要町駅から徒歩3分」→「かなめちょうえきからとほさんぷん」、「BAR」→「ばー」、「20%オフ」→「にじゅっぱーせんとおふ」）
- のばす音は「ー」のまま、句読点（、。！？）はそのまま残す
- 元の文にあるスペースは、同じところに残す。スペースのないところに足さない
- 地名・店名・人の名前・お酒の名前は、いちばんふつうの読み方にする

{json.dumps(texts, ensure_ascii=False)}

## 返す JSON の形
{{"yomi": ["動画1のひらがな", "動画2のひらがな", "動画3のひらがな"]}}"""
    yomi = []
    for _ in range(2):
        yomi = [str(y).strip() for y in (ask_claude(prompt).get("yomi") or [])]
        bad = [i + 1 for i, y in enumerate(yomi) if not YOMI_OK.match(y)]
        if len(yomi) == len(narrs) and not bad:
            return yomi
        prompt += f"\n\n## もう一度\n前の答えは、ひらがな以外の文字が残っていたか、数が{len(narrs)}つではありませんでした（動画{bad}）。すべてひらがなにしてください。"
    if len(yomi) != len(narrs):
        raise RuntimeError("ナレーションのひらがなをつくれませんでした")
    log("注意：ナレーションのひらがなに、ひらがな以外の文字が残りました（そのまま確認ページに出す）")
    return yomi


def make_reading_fix(oid, row):
    """有料版の「読み方の直し」（1回まで。2026-10-31 タケシの指示）。Claude は使わず、
    お客さんが読み方を変えた動画だけ、ナレーションをお客さんのひらがなにして読み直す（字幕・投稿文・音楽・声は前のまま）"""
    d = bar_sync.CASES / oid
    order = json.loads((d / "order.json").read_text(encoding="utf-8"))
    clips = find_clips(d)
    spec, cap = latest(d)
    new = json.loads(row["よみの直し"])
    old = json.loads(row.get("よみ") or "[]")
    norm = lambda s: " ".join(str(s).split())
    if len(new) != len(spec["clips"]) or len(old) != len(new):
        raise RuntimeError("読み方の数が動画の数と合いません")
    changed = [i for i in range(len(new)) if norm(new[i]) != norm(old[i])]

    def spoken(i):
        """お客さんのひらがな。もとの文に「徒歩」などがあれば、その読み（とほ）を漢字にもどす（「と、ほ」と区切って読まないように）"""
        t = norm(new[i])
        for k, y in narrate.PRONOUNCE.items():
            if k in spec["clips"][i]["narr"]:
                t = t.replace(y, k, spec["clips"][i]["narr"].count(k))
        return t
    comment = row.get("お客さんのコメント") or "読み方の直し"
    (d / "直しの依頼.md").open("a", encoding="utf-8").write(f"- {datetime.now():%Y-%m-%d %H:%M} {comment}\n")
    a = {
        "clips": [{"narr": spoken(i) if i in changed else c["narr"], "subs": c["subs"]} for i, c in enumerate(spec["clips"])],
        "starts": [c.get("start", 0) for c in spec["clips"]],
        "voice": spec.get("voice"), "product": spec["product"], "price": spec["price"], "area": spec["area"], "hours": spec["hours"],
        "music": pathlib.Path(spec["music"]).name if spec.get("music") else "",
        "captions": {k: bar_sync.add_credit(v).replace("\n\n" + bar_sync.CREDIT, "") for k, v in cap.items()},
        "changes": "読み上げの読み方を直しました（" + "・".join(f"動画{i + 1}" for i in changed) + "）",
        "yomi": [norm(y) for y in new],
    }
    produce(oid, d, order, clips, lambda fb: json.loads(json.dumps(a)), "読み方の直し", False)


def write_script_note(path, spec, cap, changes=""):
    rows = "\n".join(f"| {i} | {c['narr']} | {' / '.join(c['subs'])} |" for i, c in enumerate(spec["clips"], 1))
    path.write_text(
        f"# 台本（自動制作 {datetime.now():%Y-%m-%d %H:%M}）\n\n声：{bar_sync.GUIDE_NAMES[spec['voice']]}　音楽：{pathlib.Path(spec['music']).name if spec.get('music') else 'なし'}\n\n"
        + (f"直したところ：{changes}\n\n" if changes else "") +
        f"| 動画 | ナレーション | 字幕 |\n|---|---|---|\n{rows}\n\n## 投稿文\n"
        + "".join(f"\n### {bar_sync.PLATFORM_NAMES.get(k, k)}\n\n{v}\n" for k, v in cap.items()),
        encoding="utf-8")


KEEP_SOURCE_DAYS = 30   # お客さんが送った動画（素材）を残す日数（2026-11-03 タケシの指示。Google 側は Code.gs の KEEP_SOURCE_DAYS）


def remove_old_sources():
    """受付から30日たった案件の、お客さんの動画（素材/）と、それから作った途中のファイル（動画/work-*）を消す。
    できあがった動画（動画/bar-ad-v*.mp4）・台本・投稿文は残す。消したら「.素材を消した」の印と自動制作ログに残す"""
    import shutil
    for d in sorted(bar_sync.CASES.iterdir()):
        order, mark = d / "order.json", d / ".素材を消した"
        if not d.is_dir() or not order.exists() or mark.exists():
            continue
        try:
            n = [int(x) for x in re.findall(r"\d+", json.loads(order.read_text(encoding="utf-8")).get("受付日時", ""))[:5]]
            at = datetime(*n)
        except (ValueError, TypeError):
            continue   # 受付日時が読めない案件はさわらない
        if (datetime.now() - at).days < KEEP_SOURCE_DAYS:
            continue
        files = [p for p in (d / "素材").glob("*") if p.is_file()]
        works = [p for p in (d / "動画").glob("work-*") if p.is_dir()]
        for p in files:
            p.unlink()
        for p in works:
            shutil.rmtree(p)
        mark.write_text(f"{datetime.now():%Y-%m-%d %H:%M} 素材 {len(files)}個・途中のフォルダ {len(works)}個を消した\n", encoding="utf-8")
        log(f"{d.name} 受付から{KEEP_SOURCE_DAYS}日たったので、素材の動画 {len(files)}個と途中のフォルダ {len(works)}個を消した")


def do_fixes():
    """「修正依頼」の案件を自動で直す。うまくいかなかったものは、同じ依頼では二度とためさない（KAYO が手で直す）"""
    for r in bar_sync.call("list", state="修正依頼"):
        oid, comment = r["id"], r.get("お客さんのコメント", "")
        d = bar_sync.CASES / oid
        mark = d / ".自動の直しができなかった"
        if not (d / "order.json").exists() or (mark.exists() and mark.read_text(encoding="utf-8") == comment):
            continue
        try:
            if r.get("よみの直し"):   # 有料版の読み方の直し（2026-10-31〜）
                make_reading_fix(oid, r)
            else:
                make_fix(oid, comment)
        except (Exception, SystemExit) as e:
            mark.write_text(comment, encoding="utf-8")
            log(f"{oid} 直しを自動でできませんでした（修正依頼のまま。KAYO が手で直す）：{e}")
            traceback.print_exc()
            try:
                bar_sync.call("update", id=oid, fields={}, log=f"直しを自動でできませんでした：{str(e)[:200]}")
            except (Exception, SystemExit):
                pass


def main():
    if len(sys.argv) == 2:
        make_case(sys.argv[1])
        return
    if len(sys.argv) == 4 and sys.argv[2] == "fix":
        make_fix(sys.argv[1], sys.argv[3])
        return
    # 前の処理がまだ動いていたら何もしない（1時間より古い印は消えたものとみなす）
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 3600:
        return
    LOCK.parent.mkdir(exist_ok=True)
    LOCK.write_text(datetime.now().isoformat(), encoding="utf-8")
    try:
        try:
            remove_old_sources()
        except Exception as e:
            log(f"古い素材を消すところでエラー：{e}")
        do_fixes()
        rows = bar_sync.call("list", state="受付")
        # 取り込んだあとに止まった案件（「制作中」で、動画がまだなく、自動でできなかった印もないもの）も仕上げる
        for r in bar_sync.call("list", state="制作中"):
            d = bar_sync.CASES / r["id"]
            if (d / "order.json").exists() and not list((d / "動画").glob("*.mp4")) and not (d / ".自動制作できなかった").exists():
                rows.append(r)
        if not rows:
            return
        try:
            if any(r["状態"] == "受付" for r in rows):
                bar_sync.pull()
        except (Exception, SystemExit) as e:
            log(f"取り込みでエラー：{e}")
        for r in rows:
            oid = r["id"]
            if not (bar_sync.CASES / oid / "order.json").exists():
                continue
            # 動画の受け取りが途中で止まった申し込みは、失敗にせず、次の回にもう一度受け取る
            if r["状態"] == "受付" and any(not list((bar_sync.CASES / oid / "素材").glob(f"video{n}.*")) for n in (1, 2, 3)):
                log(f"{oid} 動画の受け取りが途中で止まったので、次の回にやり直す")
                continue
            try:
                make_case(oid)
            except (Exception, SystemExit) as e:
                (bar_sync.CASES / oid / ".自動制作できなかった").write_text(str(e)[:500], encoding="utf-8")
                log(f"{oid} 自動制作できませんでした（制作中のまま。KAYO が手で仕上げる）：{e}")
                traceback.print_exc()
                try:
                    bar_sync.call("update", id=oid, fields={}, log=f"自動制作できませんでした：{str(e)[:200]}")
                except (Exception, SystemExit):
                    pass
    finally:
        LOCK.write_text("", encoding="utf-8")
        LOCK.replace(LOCK.with_name(".自動制作おわり"))


if __name__ == "__main__":
    main()
