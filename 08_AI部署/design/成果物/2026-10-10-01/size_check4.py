# v4 セットのポスターの大きさ確認図：左＝土台の写真に3つの切り抜き枠、右＝3枚を土台と同じ縮尺に戻して並べる（ポスターが同じ大きさに見えればそろっている）
from PIL import Image, ImageDraw, ImageFont
F = ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc', 26)
base = Image.open('sake-holiday4-angle1-v5.png').convert('RGB')
crops = {'①': (160, 44, 678, 1.388), '②': (250, 64, 458, 2.0546), '③': (262, 52, 350, 2.6886)}
files = {'①': 'sake-holiday4-angle1-v7-blend.png', '②': 'sake-holiday4-angle2-v2-blend.png', '③': 'sake-holiday4-angle3-v1-blend.png'}
inner = {'①': 449.3, '②': 666.1, '③': 871.3}  # 紙（額の内側）の高さ px（frame_edges_sat.py）
col = {'①': (230, 40, 40), '②': (30, 120, 230), '③': (20, 160, 60)}
W = Image.new('RGB', (941 + 20 + 3 * (700 + 20), 1672 + 120), 'white')
d = ImageDraw.Draw(W)
W.paste(base, (0, 100)); d.text((10, 20), '土台の写真（v5）と3つの切り抜き枠', font=F, fill=(0, 0, 0))
for k, (x, y, w, z) in crops.items():
    h = w * 1672 / 941
    d.rectangle([x, 100 + y, x + w, 100 + y + h], outline=col[k], width=5)
    d.text((x + 8, 100 + y + h - 40), k, font=F, fill=col[k])
ox = 961
for k, (x, y, w, z) in crops.items():
    im = Image.open(files[k]).convert('RGB')
    s = im.resize((round(941 / z), round(1672 / z)), Image.LANCZOS)
    W.paste(s, (ox, 100 + round(y))); d.rectangle([ox, 100 + y, ox + s.width, 100 + y + s.height], outline=col[k], width=4)
    d.text((ox, 20), f'{k} 縮尺を戻すと 紙の高さ {inner[k] / z:.1f}px', font=F, fill=col[k])
    ox += 720
W.save('sake-holiday4-size-check.png'); print('saved')
for k, (x, y, w, z) in crops.items(): print(k, f'紙の高さ {inner[k]:.1f}px ／ 拡大 {z:.3f} ＝ 土台で {inner[k]/z:.1f}px ＝ 障子 {inner[k]/z/147.5:.2f} マス')
