# AIアルコホリディ フォルダの .env（APIキーなどの秘密の設定）を読む
# .env は GitHub に送らない（.gitignore 済み）。名前の一覧は .env.example
# 値は os.environ には入れない（claude -p などほかのプログラムに勝手に渡さないため）
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]   # AIアルコホリディ
_cache = None


def load():
    global _cache
    if _cache is None:
        _cache = {}
        p = ROOT / ".env"
        if p.exists():
            for line in p.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v:
                    _cache[k.strip()] = v
    return _cache


def get(name):
    return load().get(name)
