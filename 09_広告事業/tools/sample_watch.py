# ALCOHOLIDAY 営業サンプル：TikTok からダウンロードした飲食店の動画を、自動で見本の動画にする（2026-11-03 タケシの指示）
#
#   タケシは TikTok で「動画をダウンロード」を押すだけ。あとは自動：
#   1. ダウンロードのフォルダを見回り、新しい TikTok の動画を見つけたら 営業サンプル/S-日付-連番/素材/source.mp4 に写す（元のファイルは消さない）
#   2. 動画から12枚の場面を切り出し、Claude が場面を見て店名を読み取り、ネットでお店の情報を調べ、
#      使う3か所（雰囲気・おすすめ商品・自由）・ナレーション・字幕と、お店に送る営業の文（下書き）をつくる
#   3. BAR広告と同じ組み立て（build_bar_ad.py・有料版の見た目）で、声と字幕の入った見本の動画にする
#   ※ 見本は社内用。お店の許可なく投稿しない。営業の文は送る前にタケシが確かめて、手で送る
#
# 使い方（09_広告事業 フォルダで）
#   python tools/sample_watch.py          … ダウンロードのフォルダを見回る（タスク スケジューラーから5分ごと）
#   python tools/sample_watch.py <動画>   … その動画を1本、見本にする（試し）
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import bar_auto  # noqa: E402  台本の決まり・禁止の言葉・音楽の一覧を同じものにする
import build_bar_ad  # noqa: E402

HERE = TOOLS.parent                                  # 09_広告事業
ROOT = HERE / "営業サンプル"
LOG = ROOT / "営業サンプルの記録.md"
SEEN = ROOT / ".見た動画.json"
LOCK = ROOT / ".制作中"
DOWNLOADS = pathlib.Path.home() / "Downloads"
FRAMES = 12          # Claude に見せる場面の数
SEG = 5.0            # 1か所の長さの目安（秒）
FFMPEG = build_bar_ad.FFMPEG


def log(msg):
    line = f"- {datetime.now():%Y-%m-%d %H:%M} {msg}"
    print(line)
    with LOG.open("a", encoding="utf-8") as f:
        if f.tell() == 0:
            f.write("# 営業サンプルの記録\n\nTikTok からダウンロードした動画を、自動で見本の動画にした記録（tools/sample_watch.py）\n\n")
        f.write(line + "\n")


def is_tiktok(p):
    """TikTok の動画か：名前が19けたの数字（動画の番号）か、動画の中の印に TikTok のしるし（vid: など）がある"""
    if re.search(r"\d{19}", p.stem):
        return True
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return bool(re.search(r"vid:|tiktok|bytedance", r.stderr, re.I))


def new_videos():
    """ダウンロードのフォルダの、まだ見ていない TikTok の動画（書き込みが終わったものだけ）"""
    first = not SEEN.exists()
    seen = set(json.loads(SEEN.read_text(encoding="utf-8"))) if not first else set()
    found = []
    for p in sorted(DOWNLOADS.glob("*.mp4"), key=lambda x: x.stat().st_mtime):
        key = f"{p.name}|{p.stat().st_size}"
        if key in seen:
            continue
        if first:                    # はじめての見回りでは、前からあった動画は見本にしない（印だけつける）
            seen.add(key)
            continue
        if time.time() - p.stat().st_mtime < 20:   # まだダウンロード中かもしれない
            continue
        seen.add(key)
        if is_tiktok(p):
            found.append(p)
    SEEN.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=1), encoding="utf-8")
    return found


def new_case():
    day = datetime.now().strftime("%Y%m%d")
    n = 1
    while (ROOT / f"S-{day}-{n:02d}").exists():
        n += 1
    d = ROOT / f"S-{day}-{n:02d}"
    (d / "素材").mkdir(parents=True)
    return d


def cut_frames(src, d, dur):
    """場面を切り出す（ファイル名に何秒目かを入れる）"""
    fd = d / "場面"
    fd.mkdir(exist_ok=True)
    out = []
    for i in range(FRAMES):
        t = round(dur * (i + 0.5) / FRAMES, 1)
        f = fd / f"{i + 1:02d}_{t:05.1f}秒.jpg"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", str(t), "-i", str(src), "-frames:v", "1",
                        "-vf", "scale=480:-2", "-q:v", "4", str(f)], check=True)
        out.append(f)
    return out


def ask(prompt, d):
    """claude -p で答えをもらう。場面の画像を見る・ネットで調べるのは許す"""
    for _ in range(2):
        r = subprocess.run(["claude", "-p", "--output-format", "text", "--allowedTools", "Read,WebSearch,WebFetch"],
                           input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(d))
        if r.returncode != 0:
            raise RuntimeError("Claude が答えませんでした：" + (r.stderr or r.stdout)[:300])
        m = re.search(r"\{.*\}", r.stdout, re.S)
        if m:
            return json.loads(m.group(0))
        prompt += "\n\n## もう一度\n前の答えに JSON がありませんでした。これは自動の処理で、質問に答える人はいません。必ず JSON だけを返してください。"
    raise RuntimeError("Claude の答えに JSON がありません：" + r.stdout[:300])


def make_prompt(frames, dur, feedback=""):
    budget = bar_auto.narr_budget(SEG)
    names = "\n".join(f"- 場面/{f.name}" for f in frames)
    return f"""あなたは ALCOHOLIDAY の KAYO（scripts 部）です。飲食店に「お店の紹介動画づくり」を営業するための、見本の動画の台本をつくります。
材料は、TikTok に公開されている、ある飲食店の動画（長さ {dur:.1f}秒）です。見本は社内用で、お店に見せるだけです。

## すること
1. 下の場面の画像を Read ですべて見る（ファイル名の数字は、動画の何秒目か）
2. 画面の文字・看板・メニューなどから、**店名**を読み取る。店名がわかったら WebSearch で調べ、
   住所・最寄り駅からの道のり・営業時間・名物の商品と価格を確かめる（公式サイト・食べログ・ぐるなび・ホットペッパーなど）
3. 動画の中から、見本に使う3か所（各{SEG:.0f}秒くらい）の使い始めの秒をえらぶ
   - 1か所目：お店の雰囲気（店内・外観・乾杯など）　2か所目：おすすめ商品のアップ　3か所目：自由（別の料理・お酒など）
   - 3か所はなるべく重ならないように。使い始めは 0〜{max(0.0, dur - SEG):.1f}秒のあいだ
4. ナレーション・字幕と、お店に送る営業の文（下書き）をつくる

## 場面の画像
{names}

{bar_auto.rules()}

## 返す JSON の形（説明の文は不要。JSON だけ）
{{
  "shop": "店名（わからなければ \\"\\"）",
  "shop_kana": "店名の読み（ひらがな）",
  "found": "店名を何から読み取り、どこで調べたか（1〜2文。調べた URL も）",
  "starts": [1か所目の使い始めの秒, 2か所目, 3か所目],
  "clips": [
    {{"narr": "1か所目のナレーション（{budget}文字くらいまで）", "subs": ["字幕1行目", "字幕2行目", "字幕3行目"]}},
    {{"narr": "2か所目…", "subs": ["…"]}},
    {{"narr": "3か所目…", "subs": ["…"]}}
  ],
  "voice": "A（明るい女性）・B（大人の女性）・C（落ち着いた女性）・D（男性）からお店に合う1つ",
  "product": "画面に出す商品名（40文字まで）",
  "price": "画面に出す価格（調べてわからなければ \\"\\"）",
  "area": "画面に出す場所（例：東京都豊島区・池袋駅西口から徒歩1分）",
  "hours": "画面に出す営業時間（短く。わからなければ \\"\\"）",
  "music": "背景の音楽のファイル名（下の一覧から店の雰囲気に合う1つ）",
  "dm": "お店に送る営業の文（下書き）"
}}

## 背景の音楽（ファイル名：札・感じ）
{bar_auto.music_list()}

## 気をつけること
- 画像・調べたことにないことは足さない。わからないことは "" にする（作り話をしない）
- 店名がどうしてもわからないときは shop を "" にし、ナレーションは料理とお店の雰囲気の紹介にする（店名を言わない）
- ナレーションは、声に出して自然に流れる文にし、{budget}文字の8〜10割を使う。読点「、」で息つぎを入れる。字幕はナレーションを1行15文字までに分けたもの（3行まで）
- ナレーションで店名は読まない（読みまちがいを防ぐため。店名は画面の文字に出る）
- 言い回しは明るく。卑猥・差別・乱暴な言葉、上の禁止表現リストの言葉は使わない
- 営業の文（dm）：ALCOHOLIDAY（アルコホリディ）から、そのお店へ。ていねいで短く（250文字くらい）。
  「お店の動画を見て、紹介動画の見本を1本つくってみた」「よければ見てほしい」「毎月お店の SNS 用の動画をおつくりするサービスをしている」ことを伝え、押しつけない。
  最後に「今後のご連絡が不要でしたら、お手数ですがその旨お知らせください。」と、https://www.alcoholiday.org/ を入れる
{feedback}"""


def make_sample(src):
    d = new_case()
    shutil.copy2(src, d / "素材" / "source.mp4")
    (d / "元の動画.txt").write_text(f"{src}\n", encoding="utf-8")
    info = build_bar_ad.probe(d / "素材" / "source.mp4")
    dur = info["dur"]
    if dur < 8:
        raise RuntimeError(f"動画が短すぎます（{dur:.1f}秒。8秒以上の動画にしてください）")
    frames = cut_frames(d / "素材" / "source.mp4", d, dur)
    feedback = ""
    for attempt in (1, 2, 3):
        a = ask(make_prompt(frames, dur, feedback), d)
        starts = [round(max(0.0, min(float(s), dur - 3.2)), 2) for s in (a.get("starts") or [0, dur / 3, dur * 2 / 3])[:3]]
        voice = a.get("voice") if a.get("voice") in ("A", "B", "C", "D") else "A"
        music = a.get("music") or ""
        music = (bar_auto.MUSIC_DIR / music).as_posix() if music and (bar_auto.MUSIC_DIR / music).is_file() else ""
        n = 1
        while (d / "動画" / f"sample-v{n}.mp4").exists():
            n += 1
        spec = {
            "out": f"動画/sample-v{n}.mp4", "voice": voice,
            "clips": [{"file": "素材/source.mp4", "start": s, "narr": c["narr"], "subs": c["subs"]}
                      for s, c in zip(starts, a["clips"])],
            "product": a.get("product", ""), "price": a.get("price", ""), "shop": a.get("shop") or "（店名不明）",
            "area": a.get("area", ""), "hours": a.get("hours", ""),
            "music": music, "music_ss": 0, "limited": False,
            "date": datetime.now().strftime("%Y-%m-%d"), "plan": "paid",
        }
        spec["clips"][1]["show"] = "product"
        spec["clips"][2]["show"] = "shop"
        bad = bar_auto.find_banned({"clips": a["clips"], "product": spec["product"], "captions": {"dm": a.get("dm", "")}})
        if bad:
            feedback = "\n## 前の答えの直すところ（必ず直す）\n- " + "\n- ".join(bad)
            log(f"{d.name} 禁止の言葉があるのでつくり直し（{attempt}回目）：{' / '.join(bad)}")
            continue
        spec_path = d / f"制作-v{n}.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        r = subprocess.run([sys.executable, str(TOOLS / "build_bar_ad.py"), str(spec_path)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(HERE), env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if r.returncode != 0:
            msg = ((r.stderr or r.stdout).strip().splitlines() or ["?"])[-1]
            feedback = f"\n## 前の答えの直すところ（必ず直す）\n- 動画を組み立てられませんでした：{msg}。ナレーションを短くするか、使い始めの秒を前にしてください"
            log(f"{d.name} 動画の組み立てに失敗したのでつくり直し（{attempt}回目）：{msg}")
            continue
        (d / "営業の文（下書き）.md").write_text(
            f"# 営業の文（下書き）\n\n> 送る前に必ず読んで直す。送るのは手で（1日10〜20件まで）。\n\n"
            f"- 店名：{a.get('shop') or '不明'}（{a.get('shop_kana', '')}）\n- 調べ方：{a.get('found', '')}\n"
            f"- 見本の動画：動画/sample-v{n}.mp4\n\n---\n\n{a.get('dm', '')}\n", encoding="utf-8")
        (d / f"台本-v{n}.md").write_text(
            f"# 台本（見本 {datetime.now():%Y-%m-%d %H:%M}）\n\n声：{voice}　音楽：{pathlib.Path(music).name if music else 'なし'}\n\n"
            "| か所 | 使い始め | ナレーション | 字幕 |\n|---|---|---|---|\n"
            + "".join(f"| {i} | {c['start']}秒 | {c['narr']} | {' / '.join(c['subs'])} |\n" for i, c in enumerate(spec["clips"], 1)),
            encoding="utf-8")
        log(f"{d.name} {a.get('shop') or '店名不明'}：見本の動画 sample-v{n}.mp4 と営業の文（下書き）をつくった（元：{src.name}）")
        return d
    raise RuntimeError("3回つくり直してもうまくいきませんでした")


def main():
    ROOT.mkdir(exist_ok=True)
    if len(sys.argv) == 2:
        make_sample(pathlib.Path(sys.argv[1]).resolve())
        return
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 3600:
        return                                      # 前の見回りがまだ動いている
    LOCK.write_text(datetime.now().isoformat(), encoding="utf-8")
    try:
        for p in new_videos():
            try:
                make_sample(p)
            except Exception as e:  # noqa: BLE001  1本失敗しても次へ
                log(f"{p.name} 見本にできませんでした：{e}")
                traceback.print_exc()
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
