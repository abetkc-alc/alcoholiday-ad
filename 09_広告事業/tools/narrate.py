# ALCOHOLIDAY BAR広告：ナレーション（AIの読み上げ音声）をつくる
#   案内役ごとに声を変える（A＝ローズ／B＝ラフィ／C＝アイラ／D＝アルビン（男性））
#   ・本番：Google の読み上げ（Cloud Text-to-Speech）。環境変数 GOOGLE_TTS_KEY があればこちらを使う
#   ・お試し：edge-tts（Microsoft の無料の声。3人とも別の声）
#
# 使い方（単体で試す）: python tools/narrate.py A "今夜は恵比寿のこのBARへ。" 出力.wav
import asyncio
import base64
import os
import pathlib
import re
import subprocess
import sys
import wave

import imageio_ffmpeg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import envfile  # noqa: E402  .env（APIキーなど）を読む

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
NAMES = {"A": "ローズ", "B": "ラフィ", "C": "アイラ", "D": "アルビン"}

# 本番の声（Google の Chirp3-HD）。2026-10-04 社長が聞き比べて決定
GOOGLE_VOICES = {
    "A": {"name": "ja-JP-Chirp3-HD-Sulafat", "rate": 1.05},   # ローズ（候補9）
    "B": {"name": "ja-JP-Chirp3-HD-Aoede", "rate": 1.0},      # ラフィ（候補5）
    "C": {"name": "ja-JP-Chirp3-HD-Despina", "rate": 0.97},   # アイラ（候補13）
    "D": {"name": "ja-JP-Chirp3-HD-Orus", "rate": 1.0},       # アルビン（男性・男性候補13）
}
# 読み方の直し（字幕はそのまま、声だけこの読み方にする）
READINGS = {
    "BAR": "バー", "Bar": "バー", "bar": "バー",   # 「ビーエーアール」と読まれるので「バー」に統一
    "徒歩": "とほ",                                # 「ポホ」と読み違える声があるため
}
# お試しの声（edge-tts）。3人とも別の人の声にする（2026-10-04 社長「全部同じ雰囲気」→ 変更）
#   日本語の女性は Nanami だけなので、B・C は日本語も話せる多言語の声を使う（聞き取りで発音を確認済み）
EDGE_VOICES = {
    "A": {"voice": "ja-JP-NanamiNeural", "rate": "+10%", "pitch": "+8Hz"},                # ローズ：明るく親しみやすい（高め・はきはき）
    "B": {"voice": "de-DE-SeraphinaMultilingualNeural", "rate": "+0%", "pitch": "-4Hz"},  # ラフィ：クールで大人っぽい（低め）
    "C": {"voice": "pt-BR-ThalitaMultilingualNeural", "rate": "-10%", "pitch": "+0Hz"},   # アイラ：ゆっくり落ち着いた
    "D": {"voice": "ja-JP-KeitaNeural", "rate": "+0%", "pitch": "+0Hz"},                  # アルビン：男性
}


def all_readings():
    """決まった読み方 ＋ お客さんの直しから学んだ読み方（直しから学んだこと.md の「読み方の辞書」）。長い言葉から先に置きかえる"""
    try:
        import fix_learn
        learned = fix_learn.readings()
    except Exception:   # noqa: BLE001  辞書が読めなくても、読み上げは止めない
        learned = {}
    return sorted({**learned, **READINGS}.items(), key=lambda kv: -len(kv[0]))


def env(name):
    v = envfile.get(name) or os.environ.get(name)   # まず .env、なければ環境変数
    if not v and sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v = winreg.QueryValueEx(k, name)[0]
        except OSError:
            v = None
    return v


def engine():
    return "google" if env("GOOGLE_TTS_KEY") else "edge"


def to_wav(src, dst):
    """48kHz・ステレオの wav にそろえ、前後の無音を切る"""
    trim = "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse"
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                    "-af", trim, "-ar", "48000", "-ac", "2", str(dst)], check=True)


def duration(wav_path):
    with wave.open(str(wav_path)) as w:
        return w.getnframes() / w.getframerate()


PAUSE = 0.4   # 文の中にスペースがあるとき、そこで置く「一拍」の長さ（秒）。2026-10-10 社長の指示


def synth(key, text, out):
    """text を案内役 key の声で読み上げて out（.wav）に保存。秒数を返す
    文の中にスペース（半角・全角）があれば、そこで区切って読み、あいだに一拍（PAUSE 秒）おく（2026-10-10 社長の指示）
    ただし英語の言葉どうしのあいだのスペース（「Single Malt」など。前も後ろも英字か数字）では区切らない"""
    key = key.upper()
    if key not in NAMES:
        raise SystemExit("声は A / B / C / D のどれか")
    out = pathlib.Path(out)
    # 読み方の直し（BAR→バー など）の前に区切る（英語どうしかどうかを、お客さんが書いたままの文字で見るため）
    parts = [p for p in re.split(r"(?<![A-Za-z0-9])\s+|\s+(?![A-Za-z0-9])", text.strip()) if p]
    for k, v in all_readings():
        parts = [p.replace(k, v) for p in parts]
    text = " ".join(parts)
    if len(parts) <= 1:
        synth_one(key, text.strip(), out)
        return duration(out)
    # 区切りごとに読み上げて、一拍の無音をはさんでつなぐ（どれも 48kHz・ステレオ・16bit）
    frames, params = [], None
    for i, part in enumerate(parts):
        piece = out.with_name(f"{out.stem}.part{i + 1}.wav")
        synth_one(key, part, piece)
        with wave.open(str(piece)) as w:
            params = params or w.getparams()
            if i:
                frames.append(b"\0" * int(PAUSE * w.getframerate()) * w.getsampwidth() * w.getnchannels())
            frames.append(w.readframes(w.getnframes()))
    with wave.open(str(out), "wb") as w:
        w.setparams(params)
        w.writeframes(b"".join(frames))
    return duration(out)


def synth_one(key, text, out):
    """区切りのない1つの文を読み上げて out（.wav）に保存する"""
    raw = out.with_suffix(".raw" + (".wav" if engine() == "google" else ".mp3"))
    if engine() == "google":
        import requests
        v = GOOGLE_VOICES[key]
        r = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize",
                          params={"key": env("GOOGLE_TTS_KEY")}, timeout=60,
                          json={"input": {"text": text},
                                "voice": {"languageCode": "ja-JP", "name": v["name"]},
                                "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 48000, "speakingRate": v["rate"]}})
        if r.status_code != 200:
            raise SystemExit("Google の読み上げでエラー：" + r.text[:300])
        raw.write_bytes(base64.b64decode(r.json()["audioContent"]))
    else:
        import edge_tts
        v = EDGE_VOICES[key]
        asyncio.run(edge_tts.Communicate(text, v["voice"], rate=v["rate"], pitch=v["pitch"]).save(str(raw)))
    to_wav(raw, out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 4:
        raise SystemExit("使い方: python tools/narrate.py <A|B|C|D> \"文\" 出力.wav")
    d = synth(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"{NAMES[sys.argv[1].upper()]}（{engine()}）{d:.2f}秒 → {sys.argv[3]}")
