# ALCニュース：キャスターの声の見本をつくる（Google の男性の声）
import base64, pathlib, sys
import requests
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools"))
import narrate  # noqa: E402

TEXT = "ALCニュースです。けさ、東京・池袋で、自称スーパースターの男性が、きょうの予定を熱く語り始めたということです。"
VOICES = ["ja-JP-Chirp3-HD-Charon", "ja-JP-Chirp3-HD-Schedar", "ja-JP-Chirp3-HD-Iapetus", "ja-JP-Chirp3-HD-Rasalgethi", "ja-JP-Neural2-C", "ja-JP-Neural2-D"]
here = pathlib.Path(__file__).resolve().parent
for v in VOICES:
    out = here / f"{v}.wav"
    if out.exists():
        continue
    r = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize", params={"key": narrate.env("GOOGLE_TTS_KEY")}, timeout=60,
                      json={"input": {"text": TEXT.replace("ALC", "エーエルシー")}, "voice": {"languageCode": "ja-JP", "name": v},
                            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 48000}})
    if r.status_code != 200:
        print(v, "エラー", r.text[:200]); continue
    raw = out.with_suffix(".raw.wav"); raw.write_bytes(base64.b64decode(r.json()["audioContent"]))
    narrate.to_wav(raw, out); raw.unlink()
    print(v, f"{narrate.duration(out):.2f}秒")
