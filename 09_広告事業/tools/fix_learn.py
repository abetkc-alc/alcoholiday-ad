# ALCOHOLIDAY BAR広告：お客さんの「直しの依頼」から学んで、次の動画づくりに活かす（2026-10-10 社長の指示）
#
#   ・案件/<受付番号>/直しの依頼.md に新しい依頼があれば、直す前と直したあとの台本を見くらべて、
#     Claude に「ほかのお店にも活かせる学び」と「読み方の直し」をまとめてもらい、直しから学んだこと.md に書き足す
#   ・bar_auto.py は lessons_for_prompt() で学びを台本係に渡し、narrate.py は readings() で読み方の辞書を使う
#
# 使い方（09_広告事業 フォルダで）
#   python tools/fix_learn.py          … 新しい直しを全部学ぶ（タスク スケジューラーから10分ごと）
#   python tools/fix_learn.py --mark   … 今ある直しを「学んだ」ことにする（学ばずに印だけ）
import json
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timedelta

HERE = pathlib.Path(__file__).resolve().parent.parent      # 09_広告事業
NOTE = HERE / "直しから学んだこと.md"
CASES = HERE / "案件"
DONE = CASES / ".直しの学び済み.json"
RECORD = CASES / "直しの記録.md"
KANA = re.compile(r"^[ぁ-んァ-ヶー・ 　]+$")
ENTRY = re.compile(r"^- (\d{4}-\d\d-\d\d \d\d:\d\d) (.*)$")
WAIT = timedelta(hours=2)          # 直した台本ができないまま2時間たったら、あるものだけで学ぶ


def _note():
    try:
        return NOTE.read_text(encoding="utf-8").replace("\r\n", "\n")
    except OSError:
        return ""


def _section(t, title):
    i = t.find("## " + title)
    if i < 0:
        return ""
    j = t.find("\n## ", i + 1)
    return t[i:j if j >= 0 else len(t)]


def lessons():
    """「台本づくりの学び」の箇条書き"""
    return [x[2:].strip() for x in _section(_note(), "台本づくりの学び").splitlines() if x.startswith("- ")]


def readings():
    """読み方の辞書 {言葉: よみ}"""
    s = _section(_note(), "読み方の辞書")
    m = re.search(r"```\n(.*?)```", s, re.S)
    out = {}
    for line in (m.group(1) if m else "").splitlines():
        if "=" in line:
            k, v = (x.strip() for x in line.split("=", 1))
            if k and v:
                out[k] = v
    return out


def lessons_for_prompt():
    """台本係（Claude）に渡す文。学びがなければ空"""
    ls = lessons()[-30:]
    rd = readings()
    if not ls and not rd:
        return ""
    s = "\n\n## 前のお客さんの直しから学んだこと（必ず守る）\n" + "\n".join("- " + x for x in ls)
    if rd:
        s += "\n- 次の言葉は、声では自動でこの読み方になる（字幕は漢字のままでよい）：" + "、".join(f"{k}＝{v}" for k, v in rd.items())
    return s


def _scripts(d):
    """案件の台本ノート（つくった時刻つき）を古い順に"""
    out = []
    for p in d.glob("台本*.md"):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"自動制作 (\d{4}-\d\d-\d\d \d\d:\d\d)", t)
        at = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M") if m else datetime.fromtimestamp(p.stat().st_mtime)
        out.append((at, p, t))
    return sorted(out, key=lambda x: x[0])


def _ask(prompt):
    r = subprocess.run(["claude", "-p", "--output-format", "text"], input=prompt, capture_output=True,
                       text=True, encoding="utf-8", timeout=600, cwd=str(HERE))
    m = re.search(r"\{.*\}", r.stdout or "", re.S)
    if r.returncode != 0 or not m:
        raise RuntimeError("Claude が答えませんでした：" + (r.stderr or r.stdout or "")[:300])
    return json.loads(m.group(0))


def _prompt(comment, before, after):
    return f"""あなたは ALCOHOLIDAY の KAYO です。BAR の紹介動画に、お客さんから直しの依頼がありました。
直す前と直したあとの台本を見くらべて、**ほかのお店の動画をつくるときにも活かせる学び**をまとめてください。
ツールは使わず、最後に JSON だけを返してください。確認や質問はしない（自動の処理で、答える人はいない）。

## お客さんの直しの依頼
{comment}

## 直す前の台本
{before or "（なし）"}

## 直したあとの台本
{after or "（まだない）"}

## いまある学び（同じことは書かない）
{chr(10).join("- " + x for x in lessons()) or "（なし）"}

## いまある読み方の辞書（同じ言葉は書かない）
{"、".join(f"{k}={v}" for k, v in readings().items()) or "（なし）"}

## 返す JSON
{{
  "lesson": "次から台本をつくるときに守ること（1文・60文字くらいまで・やさしい日本語）。そのお店だけの好みや中身の話、いまある学びと同じなら空の文字",
  "readings": {{"読み間違えられた言葉（漢字など）": "正しいよみ（ひらがな）"}}
}}
- readings は、お客さんが「読み方・発音がちがう」と言った言葉だけ。ないときは {{}}
"""


def _add_to_note(lesson, rd, when, oid):
    t = NOTE.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in t else "\n"
    t = t.replace("\r\n", "\n")
    if lesson and lesson not in t:
        sec = _section(t, "台本づくりの学び")
        new = sec.rstrip("\n") + f"\n- {lesson}（{when[:10]} {oid} の直しから）\n\n"
        t = t.replace(sec, new, 1)
    add = [f"{k}={v}" for k, v in rd.items() if k not in readings()]
    if add:
        sec = _section(t, "読み方の辞書")
        i = sec.rfind("```")
        t = t.replace(sec, sec[:i] + "\n".join(add) + "\n" + sec[i:], 1)
    NOTE.write_bytes(t.replace("\n", eol).encode("utf-8"))


def _record(line):
    if not RECORD.exists():
        RECORD.write_text("# 直しの記録（BAR広告）\n\nお客さんの直しの依頼と、そこから学んだこと（このフォルダは GitHub に送らない）。"
                          "学びのまとめは [[直しから学んだこと]]。\n\n", encoding="utf-8")
    with RECORD.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main(mark_only=False):
    try:
        done = json.loads(DONE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        done = {}
    for f in sorted(CASES.glob("*/直しの依頼.md")):
        d, oid = f.parent, f.parent.name
        entries = [m.groups() for m in map(ENTRY.match, f.read_text(encoding="utf-8").splitlines()) if m]
        for n, (when, comment) in enumerate(entries):
            if n < done.get(oid, 0):
                continue
            if mark_only:
                done[oid] = n + 1
                continue
            at = datetime.strptime(when, "%Y-%m-%d %H:%M")
            sc = _scripts(d)
            before = [x for x in sc if x[0] <= at]
            after = [x for x in sc if x[0] >= at and "直したところ" in x[2]]
            if not after and datetime.now() - at < WAIT:
                break                       # まだ直している途中。次の回に
            try:
                a = _ask(_prompt(comment, before[-1][2] if before else "", after[0][2] if after else ""))
            except Exception as e:          # noqa: BLE001  Claude が答えないときは、次の回にもう一度
                print(f"{oid}：学べませんでした（次の回にもう一度）：{e}")
                break
            lesson = str(a.get("lesson") or "").strip()
            rd = {str(k).strip(): str(v).strip() for k, v in (a.get("readings") or {}).items()
                  if str(k).strip() and 0 < len(str(k).strip()) <= 20 and KANA.match(str(v).strip())}
            _add_to_note(lesson, rd, when, oid)
            _record(f"- {when} {oid} 依頼「{comment}」→ 学び：{lesson or 'なし'}"
                    + (f"／読み方：{'、'.join(f'{k}={v}' for k, v in rd.items())}" if rd else ""))
            print(f"{oid}：学び「{lesson or 'なし'}」 読み方 {rd or 'なし'}")
            done[oid] = n + 1
            DONE.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")
    DONE.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main("--mark" in sys.argv)
