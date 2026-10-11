# ALCOHOLIDAY：Obsidian のノートどうしを自動でリンクする（2026-10-10 社長の指示）
#
#   ・新しい日誌・インボックスのメモ・BAR広告の申し込み・01〜05 のノートに、関係するノートへのリンクをつける
#   ・一覧のノート（06_日誌・00_インボックス・AI部署 仕事一覧・案件一覧）をつくり直す
#   ・つなぎ方のきまりは 08_AI部署/自動リンクのきまり.md（社長が言葉を書き足せる）
#
# ノートの一番下の「%% 自動リンク … %%」の行から下だけを書きかえる。上の本文にはさわらない。
# 書いている途中のノートにはさわらない（最後に保存してから15分たつまで待つ）。
#
# 使い方：python 08_AI部署/data/auto_link.py         … タスク スケジューラーから10分ごと
#         python 08_AI部署/data/auto_link.py --now   … 15分待たずに、全部すぐ処理する
import json
import pathlib
import re
import sys
import time
import traceback
from datetime import datetime

V = pathlib.Path(__file__).resolve().parents[2]          # AIアルコホリディ（Vault）
AI = V / "08_AI部署"
CASES = V / "09_広告事業" / "案件"
RULES = AI / "自動リンクのきまり.md"
LOGF = AI / "data" / "自動リンクの記録.txt"
MARK = "%% 自動リンク（この行から下はプログラムが書きかえます） %%"
IDLE = 0 if "--now" in sys.argv else 15 * 60
SKIP_DIRS = {"成果物", "完成", "node_modules", "素材", "動画"}
# 本文の名前でつながない（ありふれた名前・機械が読み書きするノート）
NO_TITLE = {"CLAUDE", "台本", "依頼メモ", "直しの依頼", "投稿結果", "案件一覧", "design", "scripts", "editing",
            "自動リンクのきまり", "プロフィール"}
# 自動リンクの欄をつけないノート（プログラムが読む・書き足すノート）
NO_BLOCK = {"CLAUDE", "自動制作ログ", "禁止表現リスト", "広告事業", "自動リンクのきまり", "直しから学んだこと"}
STATUS = {"new": "受付", "dispatched": "各部署へ指示済み", "working": "制作中", "review": "確認待ち",
          "video_requested": "動画づくり依頼", "finish_requested": "仕上げ依頼", "done": "完成", "posted": "投稿済み"}
GOODS = {"wine": "ワイン", "whisky": "ウイスキー", "beer": "ビール", "sake": "日本酒", "sparkling": "スパークリング"}
CASE_ID = re.compile(r"(?:ALC|BAR|TEST)-\d{8}-\d{2,4}")   # 受付番号（2026-10-10 から ALC-。前の案件は BAR-）
JOB_ID = re.compile(r"(?<![\d-])20\d\d-\d\d-\d\d-\d\d(?![\d-])")
DATE = re.compile(r"^20\d\d-\d\d-\d\d$")


def notes():
    out = []
    for p in V.rglob("*.md"):
        rel = p.relative_to(V).parts
        if any(x.startswith(".") for x in rel) or SKIP_DIRS & set(rel[:-1]):
            continue
        out.append(p)
    return out


def key(p):
    """リンクに書く名前（拡張子なしの Vault からの位置）"""
    return p.relative_to(V).with_suffix("").as_posix()


def read(p):
    b = p.read_bytes()
    return b.decode("utf-8-sig", errors="replace").replace("\r\n", "\n")


def base_text(p):
    return read(p).split(MARK)[0]


def idle(p):
    return time.time() - p.stat().st_mtime >= IDLE


def write_bytes_if_changed(p, data):
    if p.exists() and p.read_bytes() == data:
        return False
    p.write_bytes(data)
    return True


def set_block(p, lines):
    """ノートの一番下の自動リンク欄を lines にする。本文（上の部分）はバイト単位でそのまま残す"""
    if not idle(p):
        return
    raw = p.read_bytes()
    eol = b"\r\n" if raw.count(b"\r\n") * 2 > raw.count(b"\n") else b"\n"
    m = MARK.encode("utf-8")
    body = raw.split(m)[0].rstrip(b"\r\n \t")
    if not lines:
        new = body + eol if m in raw else raw
    else:
        new = body + eol + eol + m + eol + eol.join(s.encode("utf-8") for s in lines) + eol
    if write_bytes_if_changed(p, new):
        print("リンク：", key(p))


def write_note(p, text):
    """一覧ノート（全部プログラムがつくる）を書く。行の終わりは今のファイルに合わせる"""
    eol = "\n"
    if p.exists():
        raw = p.read_bytes()
        eol = "\r\n" if raw.count(b"\r\n") * 2 > raw.count(b"\n") else "\n"
    if write_bytes_if_changed(p, text.replace("\n", eol).encode("utf-8")):
        print("一覧：", key(p))


def load_rules():
    rules = []
    for line in read(RULES).splitlines():
        m = re.match(r"^\s*-\s*(.+?)\s*(?:→|->)\s*\[\[([^\]|#]+)", line)
        if m:
            words = [w.strip() for w in re.split(r"[、,，／/]", m.group(1)) if w.strip()]
            rules.append((words, m.group(2).strip()))
    return rules


class Vault:
    def __init__(self):
        self.all = notes()
        self.by_stem = {}
        for p in self.all:
            self.by_stem.setdefault(p.stem, []).append(p)
        self.rules = load_rules()
        self.titles = sorted((s for s, ps in self.by_stem.items() if len(ps) == 1 and len(s) >= 4 and s not in NO_TITLE
                              and not DATE.match(s) and not any(x in ps[0].parts for x in ("案件",))), key=len, reverse=True)
        self.diaries = sorted((p for p in (V / "06_日誌").rglob("*.md") if DATE.match(p.stem)), key=lambda p: p.stem)
        self.inbox = sorted((p for p in (V / "00_インボックス").rglob("*.md") if DATE.match(p.stem)), key=lambda p: p.stem)
        self.texts = {p: base_text(p) for p in self.diaries + self.inbox}

    def exists(self, target):
        target = target.split("#")[0]
        return target in self.by_stem or (V / (target + ".md")).exists()

    def link(self, target, label=None):
        return f"[[{target}|{label}]]" if label else f"[[{target}]]"

    def related(self, p, text):
        """本文から、つなぐ先を見つける（もう本文でつないでいる先は除く）"""
        found = []
        own = {p.stem, key(p)}

        def add(target, label=None):
            if target in own or not self.exists(target) or f"[[{target}" in text:
                return
            s = self.link(target, label)
            if s not in found:
                found.append(s)

        for cid in dict.fromkeys(CASE_ID.findall(text)):
            add(f"09_広告事業/案件/{cid}/依頼メモ", cid)
        for jid in dict.fromkeys(JOB_ID.findall(text)):
            if (AI / "design" / "成果物" / jid).exists() or (AI / "scripts" / "成果物" / jid).exists():
                add(f"AI部署 仕事一覧#{jid}", f"仕事 {jid}")
        plain = re.sub(r"\[\[[^\]]*\]\]", "", text).lower()
        for t in self.titles:
            if t.lower() in plain:
                add(t)
        n = len(found)
        for words, target in self.rules:
            if any(w.lower() in plain for w in words) and len(found) < n + 6:   # 言葉でつなぐのは6つまで（多すぎると見にくい）
                add(target)
        return found


def first_line(text):
    for line in text.splitlines():
        s = line.strip().lstrip("#").strip()
        if s and not s.startswith("[[") and not DATE.match(s) and not re.match(r"^\d\d:\d\d", s) and s != "---":
            return s[:40]
    return ""


def do_diaries(v):
    ds = v.diaries
    inbox = {p.stem: p for p in v.inbox}
    for i, p in enumerate(ds):
        text = v.texts[p]
        rel = []
        if "[[06_日誌]]" not in text:
            rel.append("[[06_日誌]]")
        if p.stem in inbox:
            rel.append(v.link(key(inbox[p.stem]), "この日のメモ"))
        rel += v.related(p, text)
        nav = []
        if i:
            nav.append("← " + v.link(key(ds[i - 1]), ds[i - 1].stem[5:]))
        if i < len(ds) - 1:
            nav.append(v.link(key(ds[i + 1]), ds[i + 1].stem[5:]) + " →")
        lines = (["関連：" + "／".join(rel)] if rel else []) + ["前後の日誌：" + "　".join(nav)]
        set_block(p, lines)


def do_inbox(v):
    diaries = {p.stem: p for p in v.diaries}
    for p in v.inbox:
        text = v.texts[p]
        rel = []
        if "[[00_インボックス]]" not in text:
            rel.append("[[00_インボックス]]")
        if p.stem in diaries:
            rel.append(v.link(key(diaries[p.stem]), "この日の日誌"))
        rel += v.related(p, text)
        set_block(p, ["関連：" + "／".join(rel)] if rel else [])


def do_indexes(v):
    # 06_日誌：月ごとの一覧
    months = {}
    for p in v.diaries:
        months.setdefault(p.stem[:7], []).append(p)
    lines = ["## 日誌の一覧（自動）"]
    for m in sorted(months, reverse=True):
        lines.append(f"### {m[:4]}年{int(m[5:])}月")
        lines.append("／".join(v.link(key(p), p.stem[5:]) for p in months[m]))
    lines.append("")
    lines.append("関連：[[ALCOHOLIDAY 事業計画]]")
    set_block(V / "06_日誌" / "06_日誌.md", lines)
    # 00_インボックス：メモの一覧（最初の一言つき）
    lines = ["## メモの一覧（自動）"]
    for p in reversed(v.inbox):
        lines.append(f"- {v.link(key(p), p.stem)}：{first_line(v.texts[p].split(chr(10), 1)[-1])}")
    lines.append("")
    lines.append("関連：[[ALCOHOLIDAY 事業計画]]")
    set_block(V / "00_インボックス" / "00_インボックス.md", lines)


def do_cases(v):
    if not CASES.exists():
        return
    rows = []
    for d in sorted((x for x in CASES.iterdir() if x.is_dir() and (x / "依頼メモ.md").exists()), reverse=True):
        try:
            o = json.loads((d / "order.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            o = {}
        base = f"09_広告事業/案件/{d.name}"
        rows.append(f"- {v.link(base + '/依頼メモ', d.name)}　{o.get('店名', '')}（受付 {o.get('受付日時', '')}）")
        others = sorted((p for p in d.glob("*.md") if p.name != "依頼メモ.md"), key=lambda p: (p.stem.startswith("直し"), p.stem))
        lines = []
        if others:
            lines.append("この案件のノート：" + "／".join(v.link(f"{base}/{p.stem}", p.stem) for p in others))
        days = [p for p in v.diaries if d.name in v.texts[p]]
        if days:
            lines.append("出てくる日誌：" + "／".join(v.link(key(p), p.stem) for p in days))
        lines.append("一覧：[[09_広告事業/案件/案件一覧|案件一覧]]／[[広告事業]]")
        set_block(d / "依頼メモ.md", lines)
    write_note(CASES / "案件一覧.md",
               "# 案件一覧\n\n[[広告事業]] の申し込みごとのノート（新しい順・自動でつくる一覧。このフォルダは GitHub に送らない）。"
               "自動でつくった記録は [[自動制作ログ]]、直しから学んだことは [[直しから学んだこと]]。\n\n" + "\n".join(rows) + "\n")


def do_jobs(v):
    """AI部署 仕事一覧（board.json と成果物のフォルダからつくる）"""
    try:
        orders = json.loads((AI / "data" / "board.json").read_text(encoding="utf-8")).get("orders", [])
    except (OSError, ValueError):
        return
    out = ["---", "tags: [AI部署, 仕事一覧]", "---", "", "# AI部署 仕事一覧", "",
           "[[ai-alcoholiday]]（KAYO）が受けた指示ごとに、各部署の成果物ノートをまとめたページ（新しい順・自動でつくる一覧）。",
           "指示の中身と状態は `08_AI部署/data/board.json`（管理ページで見る）。直しから学んだことは各部署のノート（[[design]]／[[scripts]]／[[editing]]）の「直しから学んだこと」。", ""]
    for o in sorted(orders, key=lambda o: o.get("id", ""), reverse=True):
        jid = o.get("id", "")
        goods = "・".join(GOODS.get(x, x) for x in (o.get("products") or [o.get("product")]) if x)
        img = " ".join(o.get("image", "").split())
        title = (goods + "｜" if goods else "") + (img[:45] + "…" if len(img) > 45 else img)
        out += [f"## {jid}", f"**{title}**", f"- 状態：{STATUS.get(o.get('status'), o.get('status', ''))}"]
        for dep, name in (("design", "写真の指示文"), ("scripts", "台本")):
            fs = sorted((AI / dep / "成果物" / jid).glob("*.md"))
            if fs:
                out.append(f"- {name}（[[{dep}]]）：" + "／".join(v.link(key(p), p.stem) for p in fs))
        if (AI / "editing" / "成果物" / jid).exists():
            out.append(f"- 動画（[[editing]]）：`08_AI部署/editing/成果物/{jid}/`")
        if (AI / "完成" / jid).exists():
            fs = sorted((AI / "完成" / jid).glob("*.md"))
            out.append("- 投稿用セット：`08_AI部署/完成/" + jid + "/`" + ("　" + "／".join(v.link(key(p), p.stem) for p in fs) if fs else ""))
        notes_ = [p for p in v.all if p.parent.name in ("04_動画生成", "03_SNS投稿", "02_商品") and jid in base_text(p)]
        if notes_:
            out.append("- 記録：" + "／".join(v.link(p.stem) for p in notes_))
        days = [p for p in v.diaries if jid in v.texts[p]]
        if days:
            out.append("- 出てくる日誌：" + "／".join(v.link(key(p), p.stem) for p in days))
        out.append("")
    out.append("関連：[[04_動画生成]]／[[03_SNS投稿]]／[[02_商品]]")
    write_note(AI / "AI部署 仕事一覧.md", "\n".join(out) + "\n")


def do_folders(v):
    """01〜05 のフォルダのノート：本文に出てくるノートへつなぐ（フォルダの表紙ノートにも）"""
    for folder in ("01_ブランド", "02_商品", "03_SNS投稿", "04_動画生成", "05_売上・数字"):
        for p in (V / folder).rglob("*.md"):
            if p.stem in NO_BLOCK or SKIP_DIRS & set(p.relative_to(V).parts[:-1]):
                continue
            text = base_text(p)
            rel = v.related(p, text)
            if p.stem != folder and f"[[{folder}]]" not in text:
                rel.insert(0, f"[[{folder}]]")
            set_block(p, ["関連（自動）：" + "／".join(rel)] if rel else [])


def main():
    v = Vault()
    for step in (do_diaries, do_inbox, do_indexes, do_cases, do_jobs, do_folders):
        try:
            step(v)
        except Exception:
            with LOGF.open("a", encoding="utf-8") as f:
                f.write(f"{datetime.now():%Y-%m-%d %H:%M} {step.__name__} でエラー\n{traceback.format_exc()}\n")
            traceback.print_exc()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
