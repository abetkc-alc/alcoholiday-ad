# ALCOHOLIDAY BAR広告：Google（受付台帳）とパソコン（KAYO）の受け渡し
#
# 使い方（09_広告事業 フォルダで）
#   python tools/bar_sync.py list [状態]            … 依頼の一覧（状態：受付／制作中／承認待ち／修正依頼／予約済み など）
#   python tools/bar_sync.py pull                   … 「受付」の依頼を 案件/<受付番号>/ に取り込み（動画3本は 素材/video1〜3）、状態を「制作中」にする
#   python tools/bar_sync.py local <依頼ファイル.json> … お試し版の受付ページで保存した依頼を 案件/ に取り込む（Google を通さない）
#   python tools/bar_sync.py fixes                  … 「修正依頼」の一覧とお客さんのコメント
#   python tools/bar_sync.py check <受付番号> <投稿文.json>  … 投稿文の決まり（#PR・提供・注意書き・住所・営業時間・電話・X の長さ）を確かめるだけ
#   python tools/bar_sync.py deliver <受付番号> <動画.mp4> <投稿文.json>
#                                                   … 動画と投稿文を届け、お客さんに承認のお願いメールを送る（社長の確認後に使う）
#   python tools/bar_sync.py voice <A|B|C|D> <見本.mp3> … 受付ページの「▶ 声を聞く」で流す声の見本を登録する（09_広告事業/声見本/）
#   python tools/bar_sync.py schedule <受付番号>     … Upload-Post への予約をやり直す（予約エラーのとき）
#   python tools/bar_sync.py set <受付番号> <状態>    … 状態を手で変える（例：キャンセル）
#   python tools/bar_sync.py info                   … 受付ページと受付台帳の場所
#
# 必要な設定（Windows のユーザー環境変数）
#   BAR_API_URL … Apps Script のウェブアプリの URL（https://script.google.com/macros/s/…/exec）
#   BAR_API_KEY … setup() を実行したときに出た API_KEY
#
# 決まり：ファイルは消さない・上書きしない。投稿は必ずお客さんの承認のあと（承認はお客さんが承認ページで押す）
import base64
import imageio_ffmpeg
import tempfile
import subprocess
import json
import os
import pathlib
import sys
import time

import requests

HERE = pathlib.Path(__file__).resolve().parent.parent        # 09_広告事業
CASES = HERE / "案件"
GUIDE_NAMES = {"A": "ローズ", "B": "ラフィ", "C": "アイラ", "D": "アルビン"}
EXT = {"video/quicktime": ".mov", "video/mp4": ".mp4", "video/webm": ".webm", "video/3gpp": ".3gp"}


def env(name):
    v = os.environ.get(name)
    if not v and sys.platform == "win32":
        import winreg   # 環境変数を設定したあと、開き直していない画面でも読めるように
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v = winreg.QueryValueEx(k, name)[0]
        except OSError:
            v = None
    if not v:
        sys.exit(f"{name} が設定されていません（09_広告事業/google/設置手順.md を見てください）")
    return v


def call(action, **kw):
    # 通信が一瞬切れたり、Google が一時的に「見つかりません（404）」や変な返事を返すことがあるので、5回までやり直す
    #   （2026-10-06 の申し込みで、大きい動画のかけらを受け取る途中に何度も起きた）
    for i in range(5):
        try:
            r = requests.post(env("BAR_API_URL"), json={"key": env("BAR_API_KEY"), "action": action, **kw}, timeout=600)
            r.raise_for_status()
            res = r.json()
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError, ValueError) as e:
            if i == 4:
                if isinstance(e, ValueError):
                    sys.exit("Google から思わぬ返事が来ました（URLやデプロイを確認）：\n" + r.text[:500])
                raise
            time.sleep(10 * (i + 1))
    if not res.get("ok"):
        sys.exit("Google 側でエラー：" + str(res.get("error")))
    return res["result"]


def show(rows):
    if not rows:
        print("（該当なし）")
    for r in rows:
        print(f"{r['id']}  [{r['状態']}]  {r.get('投稿日時') or '投稿は承認後'}  {r.get('SNS') or ''}  {r['店名']}（{r['都道府県']}）  {r['商品名']}  声:{GUIDE_NAMES.get(r['案内役'], 'おまかせ')}")


def unique(path):
    """同じ名前があれば -2, -3 … を付けて、上書きしない"""
    if not path.exists():
        return path
    n = 2
    while True:
        p = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not p.exists():
            return p
        n += 1


def pull():
    rows = call("list", state="受付")
    if not rows:
        print("新しい依頼はありません")
        return
    for r in rows:
        d = CASES / r["id"]
        (d / "素材").mkdir(parents=True, exist_ok=True)
        unique(d / "order.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        parts = call("sources", id=r["id"])
        for v in json.loads(r["動画の説明"] or "[]"):
            # 前の回で最後まで受け取れた動画は、受け取り直さない（同じ動画が何本もたまらないように）
            have = [p for p in (d / "素材").glob(f"video{v['no']}.*") if v.get("size") and p.stat().st_size == v["size"]]
            if have:
                continue
            mine = [x for x in parts if x["name"].startswith(f"v{v['no']}.part")]
            if len(mine) != v["parts"]:
                sys.exit(f"{r['id']} の動画{v['no']}のかけらが足りません（{len(mine)}/{v['parts']}）")
            data = b"".join(base64.b64decode(call("part", id=r["id"], fileId=x["fileId"])) for x in mine)
            save_video(d, v, data)
        note = d / "依頼メモ.md"
        if not note.exists():
            note.write_text(order_note(r), encoding="utf-8")
        call("update", id=r["id"], fields={"状態": "制作中"}, log="KAYO が受け取り、制作開始")
        print(f"取り込み：{d}")
        show([r])


def video_ext(v):
    return EXT.get(v.get("type", ""), pathlib.Path(v.get("name", "")).suffix.lower() or ".mp4")


def save_video(d, v, data):
    out = unique(d / "素材" / f"video{v['no']}{video_ext(v)}")
    out.write_bytes(data)
    print(f"  動画{v['no']}：{out.name}（{len(data) / 1e6:.1f}MB）")


def local(path):
    """お試し版で保存した依頼ファイル（動画も入っている）を 案件/ に取り込む"""
    o = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    slot = {"noon": "12:00", "evening": "17:00"}.get(o.get("slot"), "")
    infos = []
    for i, v in enumerate(o.get("videos", []), 1):
        infos.append({"no": i, "title": v.get("title", ""), "desc": v.get("desc", ""), "name": v.get("name", ""),
                      "type": v.get("type", ""), "size": v.get("size", 0), "sec": round(v.get("sec") or 0, 1),
                      "parts": len(v.get("chunks", []))})
    r = {"id": o["id"], "会員ID": o.get("memberEmail", "（お試し）"), "受付日時": o.get("受付日時", ""), "状態": "制作中（お試し）", "店名": o.get("shop", ""),
         "担当者": o.get("person", ""), "メール": o.get("email", ""), "電話": o.get("tel", ""),
         "都道府県": o.get("pref", ""), "住所": o.get("address", ""), "エリア": o.get("area", ""), "営業時間": o.get("hours", ""),
         "店のSNS": o.get("sns", ""), "商品名": o.get("product", ""), "商品の説明": o.get("desc", ""),
         "価格": o.get("price", ""), "数量限定": "はい" if o.get("limited") else "", "投稿日": o.get("date", ""), "時間帯": o.get("slot", ""),
         "案内役": o.get("guide", "おまかせ"), "要望": o.get("note", ""),
         "お客さんの投稿文": o.get("caption", ""),
         "動画の説明": json.dumps(infos, ensure_ascii=False), "投稿日時": f"{o.get('date', '')} {slot}"}
    d = CASES / r["id"]
    (d / "素材").mkdir(parents=True, exist_ok=True)
    unique(d / "order.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    for v, info in zip(o.get("videos", []), infos):
        save_video(d, info, b"".join(base64.b64decode(c) for c in v.get("chunks", [])))
    note = d / "依頼メモ.md"
    if not note.exists():
        note.write_text(order_note(r), encoding="utf-8")
    print(f"取り込み：{d}")


def full_address(r):
    """住所に都道府県が入っていれば、二重に付けない"""
    a = r.get('住所', '') or ''
    return a if a.startswith(r['都道府県']) else r['都道府県'] + a


def order_note(r):
    return f"""---
受付番号: {r['id']}
状態: 制作中
投稿する SNS: {r.get('SNS') or 'instagram,tiktok,x'}
tags: [広告事業, BAR広告]
---

# {r['店名']}｜{r['商品名']}

| 項目 | 内容 |
|---|---|
| 店名 | {r['店名']} |
| 住所 | {full_address(r)} |
| 最寄り駅 | {r['エリア']} |
| 営業時間 | {r['営業時間']} |
| お店のSNS | {r['店のSNS']} |
| 担当者 | {r['担当者']}（{r['メール']}／{r['電話']}） |
| おすすめ商品 | {r['商品名']}（{r['価格']}） |
| 数量限定 | {r.get('数量限定') or 'いいえ'}（はい なら 制作.json に "limited": true） |
| 投稿する SNS | {r.get('SNS') or 'instagram,tiktok,x'}（承認から2時間以内に投稿。時刻は承認のときに決まる） |
| ナレーションの声 | {r['案内役']}（{GUIDE_NAMES.get(r['案内役'], 'おまかせ')}） |

## 商品の説明（お客さんの文章）

{r['商品の説明']}

## お店で撮った動画と説明（お客さんの文章）

{videos_table(r)}

## SNS に載せる文（お客さんが書いた文。空なら KAYO が書く）

{captions_text(r)}

## ご要望

{r['要望'] or 'なし'}

## 制作の記録

- 動画：`素材/video1〜3`
- 台本・投稿文：（scripts）
- 動画：（editing）

関連：[[広告事業]]
"""


def videos_table(r):
    rows = ["| 動画 | 内容 | 長さ | お客さんの説明 |", "|---|---|---|---|"]
    for v in json.loads(r.get("動画の説明") or "[]"):
        rows.append(f"| {v['no']} | {v.get('title', '')} | {v.get('sec', 0)}秒 | {str(v.get('desc', '')).replace(chr(10), ' ')} |")
    return "\n".join(rows)


def captions_text(r):
    t = str(r.get("お客さんの投稿文") or "").strip()
    return t if t else "（空。KAYO が書く）"


NOTICE = "お酒は20歳になってから。飲酒運転は法律で禁止されています。"


def x_weight(text):
    """X の文字数の数え方（日本語などは2、英数字は1。合計280まで）"""
    return sum(1 if ord(ch) < 0x1100 else 2 for ch in text)


def check_captions(oid, cap):
    """投稿文の決まりを確かめる。問題のリストを返す（空なら OK）"""
    probs = []
    names = {"instagram": "Instagram", "tiktok": "TikTok", "x": "X"}
    for k, name in names.items():
        if not cap.get(k):
            probs.append(f"{name} の投稿文がありません")
    if probs:
        return probs
    order = CASES / oid / "order.json"
    r = json.loads(order.read_text(encoding="utf-8")) if order.exists() else {}
    # 空白をなくし、「～」「〜」「~」や全角・半角のちがいは同じとみなす
    norm = str.maketrans({"～": "〜", "~": "〜", "：": ":", "（": "(", "）": ")", "－": "-", "ー": "-", "‐": "-"})
    flat = lambda t: "".join(str(t).split()).translate(norm)
    digits = lambda t: "".join(ch for ch in str(t) if ch.isdigit())
    for k, name in names.items():
        t = cap[k]
        if "#PR" not in t:
            probs.append(f"{name}：「#PR」がない（広告の表示）")
        if "提供：" not in t:
            probs.append(f"{name}：「提供：店名」がない")
        if NOTICE not in t:
            probs.append(f"{name}：お酒の注意書きがない")
        if r.get("住所") and flat(r["住所"]) not in flat(t):
            probs.append(f"{name}：住所（{r['住所']}）がない")
        if r.get("営業時間") and flat(r["営業時間"]) not in flat(t):
            probs.append(f"{name}：営業時間（{r['営業時間']}）がない")
        if r.get("電話") and digits(r["電話"]) not in digits(t):
            probs.append(f"{name}：電話番号（{r['電話']}）がない")
    if not order.exists():
        probs.append(f"注意：{order} がないので、住所・営業時間・電話は確かめていません")
    w = x_weight(cap["x"])
    if w > 280:
        probs.append(f"X が長すぎます（{w}／280。日本語は1文字2と数える）")
    return probs


def deliver(oid, video, captions):
    video, captions = pathlib.Path(video), pathlib.Path(captions)
    cap = json.loads(captions.read_text(encoding="utf-8"))
    probs = [x for x in check_captions(oid, cap) if not x.startswith("注意：")]
    if probs:
        sys.exit("投稿文の決まりが守られていません：\n・" + "\n・".join(probs))
    size = video.stat().st_size / 1e6
    if size > 35:
        sys.exit(f"動画が大きすぎます（{size:.1f}MB）。35MB以下にしてください")
    # 承認ページで再生する確認用の小さい動画（幅540・軽く）もいっしょに届ける
    prev = pathlib.Path(tempfile.gettempdir()) / f"確認用_{oid}.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
                    "-vf", "scale=540:-2", "-c:v", "libx264", "-crf", "28", "-preset", "veryfast",
                    "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(prev)], check=True)
    res = call("deliver", id=oid, name=video.name, captions=cap,
               video=base64.b64encode(video.read_bytes()).decode(),
               preview=base64.b64encode(prev.read_bytes()).decode())
    print("届けました。お客さんに承認のお願いメールを送りました")
    print("承認ページ：", res["reviewUrl"])


def voice(key, mp3):
    key = key.upper()
    if key not in GUIDE_NAMES:
        sys.exit("声は A / B / C / D のどれか")
    data = pathlib.Path(mp3).read_bytes()
    if len(data) > 500_000:
        sys.exit("見本が大きすぎます（10秒以内・64kbps くらいの mp3 にする）")
    call("voice", guide=key, data=base64.b64encode(data).decode())
    print(f"{GUIDE_NAMES[key]} の声の見本を登録しました")


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__ or open(__file__, encoding="utf-8").read().split("import")[0])
        return
    cmd = a[0]
    if cmd == "list":
        show(call("list", state=a[1] if len(a) > 1 else None))
    elif cmd == "pull":
        pull()
    elif cmd == "local" and len(a) == 2:
        local(a[1])
    elif cmd == "fixes":
        for r in call("list", state="修正依頼"):
            show([r])
            print("   コメント：", r["お客さんのコメント"])
    elif cmd == "check" and len(a) == 3:
        probs = check_captions(a[1], json.loads(pathlib.Path(a[2]).read_text(encoding="utf-8")))
        print("OK：投稿文の決まりは守られています" if not probs else "直すところ：\n・" + "\n・".join(probs))
        x = json.loads(pathlib.Path(a[2]).read_text(encoding="utf-8")).get("x", "")
        print(f"X の長さ：{x_weight(x)}／280")
    elif cmd == "deliver" and len(a) == 4:
        deliver(a[1], a[2], a[3])
    elif cmd == "voice" and len(a) == 3:
        voice(a[1], a[2])
    elif cmd == "schedule" and len(a) == 2:
        print(call("schedule", id=a[1]))
    elif cmd == "set" and len(a) == 3:
        r = call("update", id=a[1], fields={"状態": a[2]}, log=f"KAYO が状態を「{a[2]}」に変更")
        show([r])
    elif cmd == "info":
        print(json.dumps(call("info"), ensure_ascii=False, indent=2))
    else:
        sys.exit("使い方がちがいます。python tools/bar_sync.py だけで実行すると説明が出ます")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
