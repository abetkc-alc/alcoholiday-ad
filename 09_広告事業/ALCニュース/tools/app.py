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
    past = "".join(f'<a href="/job/{d.name}">{d.name}　{html.escape(job_title(d))}{"" if (d / "ALCニュース.mp4").exists() else "（未完成）"}</a>' for d in jobs)
    return page("ALCニュース 試作", f"""
<form method="post" action="/new" enctype="multipart/form-data">
<h2>ニュースの種類</h2><div class="kinds">{kinds}</div>
<h2>内容</h2>{fields}
<div class="f"><label>⑥ 状況（300字まで）</label><textarea name="situation" maxlength="300" required
oninput="this.nextElementSibling.textContent=this.value.length+' / 300字'"></textarea><div class="count">0 / 300字</div></div>
<h2>投稿する動画</h2><div class="f"><input type="file" name="video" accept="video/*" required></div>
<h2>キャスターの映像</h2><div class="f"><select name="caster">
<option value="still">写真のまま（無料・中身の確認用）</option>
<option value="lipsync">声に合わせて口を動かす（Higgsfield・480p・1本 約2.3ドル）</option></select>
<p class="note">口を動かすほうは、お金がかかります。見積もりが3.5ドルをこえたら作らずに止まります。</p></div>
<button>ニュースをつくる（ニュース20秒以内＋ブランドボード）</button>
</form>
<h2>これまでにつくったもの</h2><div class="box jobs">{past or "まだありません"}</div>""")


def job_page(jid):
    return page("ALCニュース 制作中", f"""
<h2>受付番号 {html.escape(jid)}</h2>
<div id="v" class="box">つくっています…（2〜3分。口を動かすときは10分ほど）</div>
<h2>進みぐあい</h2><pre id="log"></pre>
<p><a href="/">← 新しいニュースをつくる</a></p>
<script>
async function tick(){{
  const r=await fetch('/status/{jid}');const s=await r.json();
  document.getElementById('log').textContent=s.log;
  if(s.done){{document.getElementById('v').innerHTML='<video src="/file/{jid}/ALCニュース.mp4?'+s.mtime+'" controls playsinline></video>'+
    '<p style="text-align:center"><a href="/file/{jid}/ALCニュース.mp4?dl=1">ダウンロード</a></p>';return;}}
  if(s.error){{document.getElementById('v').textContent='うまくいきませんでした。下の「進みぐあい」を Claude に見せてください。';return;}}
  setTimeout(tick,3000);
}}
tick();
</script>""")


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
            done = (d / "完了").exists() and mp4.exists()
            return self.send(200, json.dumps({"log": log[-4000:], "done": done, "error": (d / "失敗").exists(),
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
        (d / "依頼.json").write_text(json.dumps(order, ensure_ascii=False, indent=1), encoding="utf-8")
        caster = "lipsync" if vals.get("caster") == "lipsync" else "still"
        # 動画づくりは別のプログラムで。終わったら「完了」、だめなら「失敗」の印を置く
        script = (f'"{sys.executable}" -X utf8 "{HERE / "alc_news.py"}" "{d / "依頼.json"}" --caster {caster} '
                  f'> "{d / "制作ログ.txt"}" 2>&1 && type nul > "{d / "完了"}" || type nul > "{d / "失敗"}"')
        subprocess.Popen(script, shell=True, cwd=str(HERE.parent))
        self.send(303, "", extra={"Location": f"/job/{jid}"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    JOBS.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)   # 127.0.0.1 ＝ このパソコンの中だけ
    print(f"ALCニュース 試作：http://127.0.0.1:{PORT}  （止めるときはこの画面を閉じる）")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    srv.serve_forever()
