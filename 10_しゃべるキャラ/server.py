# 古い iPad に映したキャラクターと話すための、パソコン側のプログラム
# パソコンで動かし、iPad の Safari から http://（パソコンのIP）:8765 を開く
# ChatGPT（OpenAI）のキーはパソコンの .env の OPENAI_API_KEY だけに置き、iPad には渡さない
import io
import json
import pathlib
import socket
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "09_広告事業" / "tools"))
import envfile  # noqa: E402

PORT = 8765
HISTORY_MAX = 20          # おぼえておく会話の数（多いほど料金が少し上がる）
AUDIO_KEEP = 10           # 声のファイルをいくつまで手元に残すか

lock = threading.Lock()
history = []              # [{"role": "user"/"assistant", "content": "..."}]
audio_store = {}          # id -> mp3 のバイト列


def settings():
    return json.loads((HERE / "設定.json").read_text(encoding="utf-8"))


def personality():
    return (HERE / "性格.txt").read_text(encoding="utf-8").strip()


def openai_post(path, body, timeout=60):
    key = envfile.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY が .env にありません")
    req = urllib.request.Request(
        "https://api.openai.com/v1/" + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def ask_chatgpt(text):
    s = settings()
    with lock:
        history.append({"role": "user", "content": text})
        del history[:-HISTORY_MAX]
        msgs = [{"role": "system", "content": personality()}] + list(history)
    data = json.loads(openai_post("chat/completions", {
        "model": s["chat_model"],
        "messages": msgs,
        "max_completion_tokens": 1500,
    }))
    reply = (data["choices"][0]["message"].get("content") or "").strip()
    if not reply:
        reply = "ごめんね、うまく言葉が出てこなかった。もう一回言ってくれる？"
    with lock:
        history.append({"role": "assistant", "content": reply})
        del history[:-HISTORY_MAX]
    return reply


def make_voice(text):
    s = settings()
    body = {"model": s["tts_model"], "voice": s["voice"], "input": text,
            "response_format": "mp3"}
    if s.get("voice_instructions"):
        body["instructions"] = s["voice_instructions"]
    try:
        mp3 = openai_post("audio/speech", body)
    except urllib.error.HTTPError as e:
        if e.code != 400 or "instructions" not in body:
            raise
        del body["instructions"]          # 声の指示に対応していないモデルのとき
        mp3 = openai_post("audio/speech", body)
    aid = uuid.uuid4().hex
    with lock:
        audio_store[aid] = mp3
        for old in list(audio_store)[:-AUDIO_KEEP]:
            del audio_store[old]
    return aid


def silence_wav():
    # iPad で音を鳴らせるようにするための、0.1秒の無音
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(struct.pack("<h", 0) * 2205)
    return buf.getvalue()


SILENCE = silence_wav()


def error_text(e):
    if isinstance(e, urllib.error.HTTPError):
        try:
            detail = json.loads(e.read().decode("utf-8"))["error"]["message"]
        except Exception:
            detail = ""
        return "OpenAI からエラー %s：%s" % (e.code, detail)
    return "%s：%s" % (type(e).__name__, e)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, obj):
        self.send(200, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                  "application/json; charset=utf-8")

    def send_media(self, data, ctype):
        # 古い iPad の Safari は「一部分だけください」(Range) と頼んでくるので、それに応える
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else 0
            end = int(b) if b else len(data) - 1
            end = min(end, len(data) - 1)
            self.send(206, data[start:end + 1], ctype, {
                "Accept-Ranges": "bytes",
                "Content-Range": "bytes %d-%d/%d" % (start, end, len(data))})
        else:
            self.send(200, data, ctype, {"Accept-Ranges": "bytes"})

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self.send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/silence.wav":
            self.send_media(SILENCE, "audio/wav")
        elif path.startswith("/audio/") and path.endswith(".mp3"):
            with lock:
                mp3 = audio_store.get(path[7:-4])
            if mp3 is None:
                self.send(404, b"", "text/plain")
            else:
                self.send_media(mp3, "audio/mpeg")
        elif path == "/api/config":
            self.send_json({"name": settings()["name"]})
        else:
            self.send(404, b"", "text/plain")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        req = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        if self.path == "/api/reset":
            with lock:
                history.clear()
            self.send_json({"ok": True})
            return
        if self.path != "/api/chat":
            self.send(404, b"", "text/plain")
            return
        text = (req.get("text") or "").strip()[:500]
        if not text:
            self.send_json({"reply": "", "audio": ""})
            return
        t0 = time.time()
        print("あなた：" + text)
        try:
            reply = ask_chatgpt(text)
        except Exception as e:
            msg = error_text(e)
            print("  ※ " + msg)
            self.send_json({"reply": "ごめんね、いまChatGPTとつながらないみたい。パソコンの画面を見てね。",
                            "audio": "", "error": msg})
            return
        print(settings()["name"] + "：" + reply)
        audio = ""
        try:
            audio = "/audio/%s.mp3" % make_voice(reply)
        except Exception as e:
            print("  ※ 声をつくれませんでした（" + error_text(e) + "）")
        print("  （%.1f秒）" % (time.time() - t0))
        self.send_json({"reply": reply, "audio": audio})


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "（わかりませんでした）"
    finally:
        s.close()


if __name__ == "__main__":
    if not envfile.get("OPENAI_API_KEY"):
        print("※ .env に OPENAI_API_KEY がまだありません。入れてから、もう一度起動してください。")
    print("")
    print("  iPad の Safari で、この住所を開いてください：")
    print("    http://%s:%d" % (lan_ip(), PORT))
    print("")
    print("  （この黒い画面を閉じると止まります）")
    print("")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
