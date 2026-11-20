# ALCニュース 試作の受付ページ（このパソコンの中だけで動く。ほかの人からは見えない）
#   起動: python tools/app.py  → ブラウザで http://127.0.0.1:8765 が開く
#   申し込むと 案件/<日時>/ に 依頼.json と動画を置き、alc_news.py で動画をつくる
import datetime
import email.parser
import email.policy
import html
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
JOBS = HERE.parent / "案件"
PORT = 8765
FIELDS = [("when", "① いつ", "例：11月7日午前9時ごろ"), ("where", "② どこで", "例：池袋界隈で"),
          ("who", "③ だれが", "例：自称スーパースター"), ("what", "④ なにを", "例：自分のきょうの予定を"),
          ("how", "⑤ どうした", "例：熱く語り始めた")]
KINDS = [("bright", "明るいニュース", "動画の音そのまま＋テロップ・字幕"),
         ("trouble", "困ったニュース", "顔にモザイク・声を変えて＋テロップ・字幕"),
         ("info", "情報", "キャスターが内容を要約して伝える")]

CSS = """
:root{--navy:#0c1a33;--red:#c8101e;--paper:#f4f5f7;--ink:#14171c;--line:#d5d9e0}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
font-family:"BIZ UDPGothic","BIZ UDPゴシック","Yu Gothic",sans-serif;line-height:1.6}
header{background:var(--navy);color:#fff;display:flex;align-items:stretch;height:64px}
header .logo{background:var(--red);padding:0 28px 0 20px;display:flex;align-items:center;font-size:26px;font-weight:700;
clip-path:polygon(0 0,100% 0,calc(100% - 18px) 100%,0 100%)}
header .sub{display:flex;align-items:center;padding:0 18px;font-size:15px;opacity:.85}
main{max-width:760px;margin:0 auto;padding:24px 16px 60px}
h2{font-size:19px;border-left:6px solid var(--red);padding-left:10px;margin:28px 0 12px}
.kinds{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.kinds label{background:#fff;border:2px solid var(--line);border-radius:6px;padding:12px;cursor:pointer;display:block}
.kinds input{margin-right:6px}.kinds small{display:block;color:#5a6270;font-size:13px;margin-top:4px}
.kinds label:has(input:checked){border-color:var(--red);box-shadow:0 0 0 2px rgba(200,16,30,.15)}
.f{margin:10px 0}.f label{display:block;font-weight:700;margin-bottom:4px}
input[type=text],textarea,select{width:100%;font:inherit;font-size:17px;padding:10px;border:1px solid var(--line);border-radius:6px;background:#fff}
textarea{height:150px}.count{text-align:right;font-size:13px;color:#5a6270}
button{background:var(--red);color:#fff;border:0;border-radius:6px;font:inherit;font-size:19px;font-weight:700;padding:14px 28px;cursor:pointer;width:100%;margin-top:22px}
.note{font-size:13px;color:#5a6270}.box{background:#fff;border:1px solid var(--line);border-radius:6px;padding:14px}
video{width:100%;max-width:400px;display:block;margin:0 auto;background:#000;border-radius:6px}
pre{white-space:pre-wrap;font-size:13px;background:#0e1420;color:#cfe;padding:12px;border-radius:6px;max-height:260px;overflow:auto}
.jobs a{display:block;padding:6px 0;color:var(--navy)}
@media(max-width:600px){.kinds{grid-template-columns:1fr}}
"""


def page(title, body):
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head><body>
<header><div class="logo">ALCニュース</div><div class="sub">試作（タケシさん専用・このパソコンの中だけ）</div></header>
<main>{body}</main></body></html>"""


def job_title(d):
    try:
        o = json.loads((d / "依頼.json").read_text(encoding="utf-8"))
        return f"{o.get('who', '')}{o.get('what', '')}{o.get('how', '')}"
    except Exception:   # noqa: BLE001
        return ""


def form():
    kinds = "".join(f'<label><input type="radio" name="kind" value="{k}" {"checked" if i == 0 else ""}>{n}<small>{s}</small></label>'
                    for i, (k, n, s) in enumerate(KINDS))
    fields = "".join(f'<div class="f"><label>{n}</label><input type="text" name="{k}" placeholder="{p}" required></div>' for k, n, p in FIELDS)
    jobs = sorted([d for d in JOBS.glob("*") if (d / "依頼.json").exists()], reverse=True)[:15]
    mark = {"done": "", "script_ok": "（台本の確認待ち）", "too_long": "（台本が長すぎ）", "script": "（台本づくり中）",
            "video": "（動画づくり中）", "error": "（失敗）"}
    past = "".join(f'<a href="/job/{d.name}">{d.name}　{html.escape(job_title(d))}{mark.get(state_of(d), "")}</a>' for d in jobs)
    return page("ALCニュース 試作", f"""
<form method="post" action="/new" enctype="multipart/form-data">
<h2>ニュースの種類</h2><div class="kinds">{kinds}</div>
<h2>内容</h2>{fields}
<div class="f"><label>⑥ 状況（300字まで）</label><textarea name="situation" maxlength="300" required
oninput="this.nextElementSibling.textContent=this.value.length+' / 300字'"></textarea><div class="count">0 / 300字</div></div>
<h2>投稿する動画</h2><div class="f"><input type="file" name="video" accept="video/*" required></div>
<h2>キャスターの映像</h2><div class="f">{caster_select("still")}
<p class="note">あとで台本を確かめる画面でも変えられます。</p></div>
<button>台本をつくる（まだ動画はつくりません）</button>
<p class="note">1〜2分で台本ができます。台本を確かめて・直してから「この台本で動画をつくる」を押します。</p>
</form>
<h2>これまでにつくったもの</h2><div class="box jobs">{past or "まだありません"}</div>""")


def caster_select(cur):
    opts = [("still", "写真のまま（無料・中身の確認用）"), ("lipsync", "声に合わせて口を動かす（Higgsfield・480p・1本 約2.3ドル）")]
    o = "".join(f'<option value="{k}" {"selected" if k == cur else ""}>{n}</option>' for k, n in opts)
    return (f'<select name="caster">{o}</select>'
            '<p class="note">口を動かすほうは、お金がかかります（約2.3ドル）。見積もりが3.5ドルをこえたら作らずに止まります。</p>')


def state_of(d):
    s = d / "状態.txt"
    if s.exists():
        return s.read_text(encoding="utf-8", errors="replace").strip() or "video"
    if (d / "完了").exists() and (d / "ALCニュース.mp4").exists():   # 2026-11-07 までの案件
        return "done"
    return "error" if (d / "失敗").exists() else "video"


def read_json(f, default):
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:   # noqa: BLE001
        return default


# 台本の欄（名前・見出し・字数の目安）
SCRIPT_FIELDS = [("headline", "画面の上の見出し（「速報」のとなり）", 10), ("panel_title", "モニターの大きな言葉", 6),
                 ("panel_sub", "その上の赤い札", 11), ("when_label", "画面に出す日時", 10), ("where_label", "画面に出す場所", 10),
                 ("open", "キャスターの最初の原稿（声と字幕）", 38), ("broll_telop", "投稿動画の上のテロップ", 13),
                 ("vo", "投稿動画にかぶせるキャスターの声（情報のとき）", 28), ("close_line", "キャスターの締めの一言（声と字幕）", 16)]


def script_page(jid, d):
    spec = read_json(d / "台本.json", {})
    order = read_json(d / "依頼.json", {})
    ln = read_json(d / "台本の長さ.json", {})
    warn = ""
    if state_of(d) == "too_long":
        logf = d / "制作ログ.txt"
        last = [x for x in logf.read_text(encoding="utf-8", errors="replace").splitlines() if "長すぎ" in x] if logf.exists() else []
        warn = f'<div class="box" style="border-color:var(--red);color:var(--red)">{html.escape(last[-1] if last else "台本が長すぎます。短くしてください")}</div>'
    rows = ""
    for k, n, lim in SCRIPT_FIELDS:
        if k == "vo" and order.get("kind") != "info":
            continue
        v = spec.get(k, "")
        tag = (f'<textarea name="{k}" style="height:80px">{html.escape(v)}</textarea>' if lim > 20 else
               f'<input type="text" name="{k}" value="{html.escape(v)}">')
        rows += f'<div class="f"><label>{n}<span class="note">（{lim}字くらいまで・いま{len(v)}字）</span></label>{tag}</div>'
    subs = spec.get("subs") or []
    if subs:
        rows += '<h2>投稿動画の字幕（投稿した人の声）</h2>'
        for i, s in enumerate(subs):
            rows += (f'<div class="f"><label>元の動画の {float(s.get("start", 0)):.1f}〜{float(s.get("end", 0)):.1f}秒</label>'
                     f'<input type="text" name="sub_{i}" value="{html.escape(s.get("text", ""))}"></div>')
    info = ""
    if ln:
        info = (f'<p class="note">ニュースの長さ：約{ln["news"]}秒（20秒まで）＋ブランドボード約5秒。'
                f'投稿動画は元の {ln["broll_start"]}秒から {ln["broll_len"]}秒ぶん使います。'
                '原稿を長くすると20秒をこえることがあります。こえたときは、ここに戻って短くするようお知らせします。</p>')
    return page("ALCニュース 台本の確認", f"""
<h2>受付番号 {html.escape(jid)}　台本の確認</h2>{warn}
<p>台本ができました。読んで、直したいところは書きかえてから「この台本で動画をつくる」を押してください。</p>{info}
<form method="post" action="/make/{jid}">{rows}
<h2>キャスターの映像</h2><div class="f">{caster_select(order.get("caster", "still"))}</div>
<button>この台本で動画をつくる</button></form>
<h2>台本をまるごとつくり直す</h2>
<form method="post" action="/redo/{jid}"><div class="f"><label>どう直してほしいか（なくてもよい）</label>
<textarea name="wish" style="height:80px" placeholder="例：締めの一言をもっと短く・見出しに「高校生」を入れる"></textarea></div>
<button style="background:#5a6270">台本をつくり直す（前の台本は 台本-旧.json として残す）</button></form>
<p><a href="/">← 新しいニュースをつくる</a></p>""")


def job_page(jid):
    d = JOBS / jid
    if state_of(d) in ("script_ok", "too_long"):
        return script_page(jid, d)
    return page("ALCニュース 制作中", f"""
<h2>受付番号 {html.escape(jid)}</h2>
<div id="v" class="box">つくっています…</div>
<h2>進みぐあい</h2><pre id="log"></pre>
<p><a href="/">← 新しいニュースをつくる</a></p>
<script>
const msg={{script:'台本をつくっています…（1〜2分）',video:'動画をつくっています…（2〜3分。口を動かすときは10分ほど）'}};
async function tick(){{
  const r=await fetch('/status/{jid}');const s=await r.json();
  document.getElementById('log').textContent=s.log;
  if(s.state==='script_ok'||s.state==='too_long'){{location.reload();return;}}
  if(s.done){{document.getElementById('v').innerHTML='<video src="/file/{jid}/ALCニュース.mp4?'+s.mtime+'" controls playsinline></video>'+
    '<p style="text-align:center"><a href="/file/{jid}/ALCニュース.mp4?dl=1">ダウンロード</a></p>';return;}}
  if(s.error){{document.getElementById('v').textContent='うまくいきませんでした。下の「進みぐあい」を Claude に見せてください。';return;}}
  document.getElementById('v').textContent=msg[s.state]||msg.video;
  setTimeout(tick,3000);
}}
tick();
</script>""")


def launch(d, args, first=False):
    """alc_news.py を別に動かす。落ちたときは 状態.txt を error に"""
    script = (f'"{sys.executable}" -X utf8 "{HERE / "alc_news.py"}" "{d / "依頼.json"}" {args} '
              f'{">" if first else ">>"} "{d / "制作ログ.txt"}" 2>&1 || echo error> "{d / "状態.txt"}"')
    (d / "状態.txt").write_text("script" if "--script-only" in args else "video", encoding="utf-8")
    subprocess.Popen(script, shell=True, cwd=str(HERE.parent))


class H(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        parts = [urllib.parse.unquote(p) for p in u.path.strip("/").split("/")]
        if u.path == "/":
            return self.send(200, form())
        if len(parts) == 2 and parts[0] == "job" and (JOBS / parts[1]).is_dir():
            return self.send(200, job_page(parts[1]))
        if len(parts) == 2 and parts[0] == "status" and (JOBS / parts[1]).is_dir():
            d = JOBS / parts[1]
            logf = d / "制作ログ.txt"
            log = logf.read_text(encoding="utf-8", errors="replace") if logf.exists() else ""
            log = "\n".join(ln for ln in log.splitlines() if not re.match(r"組み立て [1-9]", ln))
            mp4 = d / "ALCニュース.mp4"
            st = state_of(d)
            done = st == "done" and mp4.exists()
            return self.send(200, json.dumps({"log": log[-4000:], "done": done, "error": st == "error", "state": st,
                                              "mtime": int(mp4.stat().st_mtime) if done else 0}), "application/json")
        if len(parts) == 3 and parts[0] == "file" and parts[2] == "ALCニュース.mp4":
            f = JOBS / parts[1] / parts[2]
            if f.exists():
                return self.send_file(f, "dl=1" in u.query)
        self.send(404, "ありません")

    def send_file(self, f, download):
        data = f.read_bytes()
        extra = {"Accept-Ranges": "bytes"}
        if download:
            extra["Content-Disposition"] = "attachment; filename*=UTF-8''" + urllib.parse.quote(f"ALCニュース_{f.parent.name}.mp4")
        m = re.match(r"bytes=(\d+)-(\d*)", self.headers.get("Range", ""))
        if m:   # 動画の再生位置を動かせるように、一部だけ返す
            a = int(m[1])
            b = int(m[2]) if m[2] else len(data) - 1
            extra["Content-Range"] = f"bytes {a}-{b}/{len(data)}"
            return self.send(206, data[a:b + 1], "video/mp4", extra)
        self.send(200, data, "video/mp4", extra)

    def do_POST(self):
        parts = [urllib.parse.unquote(p) for p in self.path.strip("/").split("/")]
        if len(parts) == 2 and parts[0] in ("make", "redo") and (JOBS / parts[1]).is_dir():
            raw = self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
            vals = {k: v[0].strip() for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}
            return (self.make if parts[0] == "make" else self.redo)(parts[1], vals)
        if self.path != "/new":
            return self.send(404, "ありません")
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + raw)
        vals, video, vname = {}, None, ""
        for p in msg.iter_parts():
            name = p.get_param("name", header="content-disposition")
            if name == "video":
                video, vname = p.get_payload(decode=True), p.get_filename() or "video.mp4"
            else:
                b = p.get_payload(decode=True)
                try:
                    vals[name] = b.decode("utf-8").strip()
                except UnicodeDecodeError:   # 古いWindowsの道具から送ると Shift-JIS になる
                    vals[name] = b.decode("cp932", errors="replace").strip()
        jid = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        d = JOBS / jid
        d.mkdir(parents=True)
        ext = pathlib.Path(vname).suffix.lower() or ".mp4"
        (d / f"投稿動画{ext}").write_bytes(video)
        order = {k: vals.get(k, "") for k in ("kind", "when", "where", "who", "what", "how")}
        order["situation"] = vals.get("situation", "")[:300]
        order["video"] = f"投稿動画{ext}"
        order["caster"] = "lipsync" if vals.get("caster") == "lipsync" else "still"
        (d / "依頼.json").write_text(json.dumps(order, ensure_ascii=False, indent=1), encoding="utf-8")
        # まず台本だけ（2026-11-08 タケシさんの指示「動画生成の前に台本を教えて」）
        launch(d, "--script-only", first=True)
        self.send(303, "", extra={"Location": "/job/" + urllib.parse.quote(jid)})

    def make(self, jid, vals):
        """確かめた（直した）台本で動画をつくる"""
        d = JOBS / jid
        spec = read_json(d / "台本.json", {})
        for k, *_ in SCRIPT_FIELDS:
            if k in vals:
                spec[k] = vals[k]
        for i, s in enumerate(spec.get("subs") or []):
            if f"sub_{i}" in vals:
                s["text"] = vals[f"sub_{i}"]
        (d / "台本.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        order = read_json(d / "依頼.json", {})
        order["caster"] = "lipsync" if vals.get("caster") == "lipsync" else "still"
        (d / "依頼.json").write_text(json.dumps(order, ensure_ascii=False, indent=1), encoding="utf-8")
        launch(d, f"--confirmed --caster {order['caster']}")
        self.send(303, "", extra={"Location": "/job/" + urllib.parse.quote(jid)})

    def redo(self, jid, vals):
        """台本をまるごとつくり直す。前の台本は消さずに名前を変えて残す"""
        d = JOBS / jid
        sp = d / "台本.json"
        if sp.exists():
            n = 1
            while (d / f"台本-旧{n}.json").exists():
                n += 1
            sp.rename(d / f"台本-旧{n}.json")
        if vals.get("wish"):
            with open(d / "台本の直し.txt", "a", encoding="utf-8") as f:   # 前の希望も残して、ぜんぶ反映する
                f.write("- " + vals["wish"].replace("\n", " ") + "\n")
        launch(d, "--script-only")
        self.send(303, "", extra={"Location": "/job/" + urllib.parse.quote(jid)})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    JOBS.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)   # 127.0.0.1 ＝ このパソコンの中だけ
    print(f"ALCニュース 試作：http://127.0.0.1:{PORT}  （止めるときはこの画面を閉じる）")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    srv.serve_forever()
