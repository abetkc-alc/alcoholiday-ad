# Claude から Gemini（Google）に動画を見てもらう入口（2026-11-03）
#   ・インスタなどの動画ファイルを Gemini にわたし、映像と音声をまとめて分析してもらう
#   ・インスタの URL はそのまま見られないので、動画は手元に保存してからわたす
#   ・再生数・いいね数などの数字は Gemini には見えない。必要なら --insights で文字としてわたす
#   ・キーは .env の GEMINI_API_KEY（Google AI Studio で作る）。値は画面に出さない
#   ・分析のあと、わたした動画は Gemini 側から消す
#
# 使い方:
#   python 08_AI部署/data/gemini.py 動画.mp4                       （インスタ動画の分析・はじめから用意した質問）
#   python 08_AI部署/data/gemini.py A.mp4 B.mp4 --insights "Aは再生1.2万・Bは800"   （何本か比べる）
#   python 08_AI部署/data/gemini.py 動画.mp4 "最初の3秒だけ見て、直すところを3つ"   （自分で質問する）
#   --out ノート.md：結果をノートに残す（つけなければ 03_SNS投稿/動画分析/日付_動画名.md）
#   --model：Gemini の種類（はじめは .env の GEMINI_MODEL か gemini-flash-latest）
#   --check：キーが使えるかだけ確かめる
import argparse
import datetime
import mimetypes
import pathlib
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]   # AIアルコホリディ
sys.path.insert(0, str(ROOT / "09_広告事業" / "tools"))
import envfile  # noqa: E402

API = "https://generativelanguage.googleapis.com"
OUT_DIR = ROOT / "03_SNS投稿" / "動画分析"

DEFAULT_PROMPT = """あなたは Instagram のリール動画にくわしい担当者です。
わたした動画を、映像と音声の両方を見て、日本語で分析してください。
お酒の雑貨ブランド ALCOHOLIDAY（アルコホリディ）が、自分たちの投稿づくりの参考にします。
むずかしい言葉は使わず、高齢の人にもわかる書き方にしてください。

次の見出しで書いてください。
## ひとことで
## 最初の3秒（目を引けているか・何で引いているか）
## 流れ（何秒に何が起きるか、短い表で）
## 画面の文字・字幕（読みやすさ・量・出る長さ）
## 声と音楽（テンポ・映像との合い方）
## 最後まで見てもらえそうか（やめそうな場面とその理由）
## まねしたいところ
## 直したほうがいいところ
## ALCOHOLIDAY で使うなら（具体的な案を3つ）
"""

COMPARE_NOTE = """
動画が何本かあるときは、わたした順に「動画1」「動画2」…と呼び、
最後に「## くらべて分かったこと」の見出しで、伸びた動画とそうでない動画の違いを書いてください。
"""


def key():
    k = envfile.get("GEMINI_API_KEY")
    if not k:
        raise SystemExit("Gemini のキーがありません。.env の GEMINI_API_KEY= のあとに、Google AI Studio で作ったキーを貼ってください")
    return k


def check(k):
    r = requests.get(f"{API}/v1beta/models", headers={"x-goog-api-key": k}, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"キーが使えません（{r.status_code}）：{r.text[:300]}")
    names = [m["name"].split("/", 1)[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    print("キーは使えます。動画を見られる Gemini の例：")
    for n in [n for n in names if n.startswith("gemini")][:15]:
        print("  " + n)


def upload(k, path):
    """動画を Gemini にわたし、見られる状態になるまで待つ"""
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "video/mp4"
    r = requests.post(f"{API}/upload/v1beta/files", headers={
        "x-goog-api-key": k,
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(len(data)),
        "X-Goog-Upload-Header-Content-Type": mime,
    }, json={"file": {"display_name": path.stem}}, timeout=60)
    r.raise_for_status()
    url = r.headers["x-goog-upload-url"]
    r = requests.post(url, headers={
        "X-Goog-Upload-Offset": "0",
        "X-Goog-Upload-Command": "upload, finalize",
    }, data=data, timeout=600)
    r.raise_for_status()
    f = r.json()["file"]
    for _ in range(120):   # 長くて10分
        if f.get("state") == "ACTIVE":
            return f
        if f.get("state") == "FAILED":
            raise SystemExit(f"Gemini が動画を読めませんでした：{path.name}")
        time.sleep(5)
        f = requests.get(f"{API}/v1beta/{f['name']}", headers={"x-goog-api-key": k}, timeout=30).json()
    raise SystemExit(f"動画の準備が10分たっても終わりませんでした：{path.name}")


def delete(k, f):
    try:
        requests.delete(f"{API}/v1beta/{f['name']}", headers={"x-goog-api-key": k}, timeout=30)
    except requests.RequestException:
        pass   # 消せなくても Gemini 側で2日後に自動で消える


def main():
    ap = argparse.ArgumentParser(description="Gemini に動画を見てもらう")
    ap.add_argument("items", nargs="*", help="動画ファイル（いくつでも）。最後に動画でない文字を書けば、それが質問になる")
    ap.add_argument("--prompt-file", help="質問を書いたファイル")
    ap.add_argument("--insights", help="再生数・いいね数などの数字（文字でわたす）")
    ap.add_argument("--model", help="Gemini の種類")
    ap.add_argument("--out", help="結果を残すノート")
    ap.add_argument("--check", action="store_true", help="キーが使えるかだけ確かめる")
    a = ap.parse_args()

    k = key()
    if a.check:
        check(k)
        return

    videos, words = [], []
    for it in a.items:
        p = pathlib.Path(it)
        (videos if p.is_file() else words).append(p if p.is_file() else it)
    if not videos:
        raise SystemExit("動画ファイルが見つかりません（場所と名前を確かめてください）")
    if a.prompt_file:
        prompt = pathlib.Path(a.prompt_file).read_text(encoding="utf-8")
    elif words:
        prompt = " ".join(words)
    else:
        prompt = DEFAULT_PROMPT + (COMPARE_NOTE if len(videos) > 1 else "")
    if a.insights:
        prompt += f"\n\n数字（インスタのインサイトなど）：\n{a.insights}\n"
    model = a.model or envfile.get("GEMINI_MODEL") or "gemini-flash-latest"

    files = []
    try:
        parts = []
        for i, v in enumerate(videos, 1):
            print(f"動画をわたしています：{v.name}", flush=True)
            f = upload(k, v)
            files.append(f)
            if len(videos) > 1:
                parts.append({"text": f"動画{i}：{v.name}"})
            parts.append({"file_data": {"mime_type": f.get("mimeType", "video/mp4"), "file_uri": f["uri"]}})
        parts.append({"text": prompt})
        print(f"Gemini（{model}）が見ています…", flush=True)
        for wait in (20, 40, 60, 90, 0):   # 混んでいる（503）・使いすぎ（429）ときは少し待ってやり直す
            r = requests.post(f"{API}/v1beta/models/{model}:generateContent",
                              headers={"x-goog-api-key": k},
                              json={"contents": [{"role": "user", "parts": parts}]}, timeout=900)
            if r.status_code not in (429, 503) or not wait:
                break
            print(f"Gemini が混んでいます。{wait}秒待ってやり直します", flush=True)
            time.sleep(wait)
        if r.status_code != 200:
            raise SystemExit(f"Gemini からエラー（{r.status_code}）：{r.text[:500]}")
        cands = r.json().get("candidates") or []
        reply = "".join(p.get("text", "") for c in cands[:1] for p in c.get("content", {}).get("parts", [])).strip()
        if not reply:
            raise SystemExit(f"Gemini の返事が空でした：{r.text[:500]}")
    finally:
        for f in files:
            delete(k, f)

    today = datetime.date.today().isoformat()
    out = pathlib.Path(a.out) if a.out else OUT_DIR / f"{today}_{videos[0].stem}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    head = (f"---\ndate: {today}\ntool: Gemini（{model}）\nvideos:\n"
            + "".join(f"  - \"{v.name}\"\n" for v in videos) + "---\n\n"
            + f"# 動画分析：{'・'.join(v.stem for v in videos)}\n\n")
    if a.insights:
        head += f"> 数字：{a.insights}\n\n"
    out.write_text(head + reply + "\n", encoding="utf-8")
    print(reply)
    print(f"\n保存しました：{out}")


if __name__ == "__main__":
    main()
