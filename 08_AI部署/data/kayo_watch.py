# KAYOの見張り役：管理ページが board.json に書いた「新しい指示」「仕上げ依頼」を見つけて1行ずつ知らせる。
# Claude Code の Monitor から起動して使う（python kayo_watch.py）。
import json
import pathlib
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")  # 日本語が文字化けしないように

BOARD = pathlib.Path(__file__).with_name("board.json")
WATCH = {"new": "新しい指示", "video_requested": "動画づくり依頼", "finish_requested": "仕上げ依頼"}

seen = set()
last_mtime = None
while True:
    try:
        mtime = BOARD.stat().st_mtime
        if mtime != last_mtime:
            last_mtime = mtime
            data = json.loads(BOARD.read_text(encoding="utf-8-sig"))
            for o in data.get("orders", []):
                key = (o.get("id"), o.get("status"))
                if o.get("status") in WATCH and key not in seen:
                    seen.add(key)
                    print(f"【{WATCH[o['status']]}】No.{o.get('id')} 商品={','.join(o.get('products') or [o.get('product') or '?'])} イメージ={o.get('image', '')[:60]}", flush=True)
    except (OSError, ValueError):
        pass  # 管理ページが書き込み中などで一時的に読めないときは次の回に読み直す
    time.sleep(2)
