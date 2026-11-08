"""受付ページ（ad.alcoholiday.org）の共有画像 og.jpg をつくる（2026-11-08 検索・SNS 対策）。

画像は GitHub に送らない決まりなので、google/photos.html に入っている写真（CC0）の1枚目
「バーのカウンターに並ぶ2杯のカクテル」を、Amplify が置くときに取り出して使う。
Python の標準の部品だけで動く。

使い方：python3 og_image.py <photos.html> <出す場所/og.jpg>
"""
import base64
import re
import sys

src, out = sys.argv[1], sys.argv[2]
text = open(src, encoding='utf-8').read()
m = re.search(r'"src": "data:image/jpeg;base64,([A-Za-z0-9+/=]+)"', text)
if not m:
    sys.exit('photos.html に写真が見つかりません')
with open(out, 'wb') as f:
    f.write(base64.b64decode(m.group(1)))
print('og.jpg をつくりました:', out)
