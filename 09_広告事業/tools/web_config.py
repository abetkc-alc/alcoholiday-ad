# AWS の受付ページ（09_広告事業/web/）をパソコンで試すための config.js をつくる（2026-10-11）
#   GAS の住所は .env の BAR_API_URL から読む（画面には出さない）。config.js は GitHub に送らない（.gitignore 済み）
#   本番（Amplify）では、Amplify の環境変数 ALC_API から、置くときに自動でつくる（amplify.yml）
#
# 使い方（09_広告事業 フォルダで）
#   python tools/web_config.py                 … web/config.js をつくる
#   python -m http.server 8080 -d web          … http://localhost:8080/ で受付ページを試せる
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import envfile  # noqa: E402

url = envfile.get("BAR_API_URL")
if not url:
    sys.exit(".env に BAR_API_URL がありません")
out = pathlib.Path(__file__).resolve().parent.parent / "web" / "config.js"
out.write_text("window.ALC_API = " + json.dumps(url) + ";\n", encoding="utf-8")
print("つくりました：", out)
