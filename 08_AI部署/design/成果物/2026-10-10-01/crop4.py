# v4 セット：土台の写真（sake-holiday4-angle1-v5.png）を「カメラが前に出た」ように切り抜いて 941x1672 に拡大する
# 同じ写真から切り抜くので、ポスターの実物の大きさ・掛ける高さ・人の座る位置は全角度で同じになる
# 使い方: python crop4.py 入力 出力 x0 y0 幅（高さは幅×16/9）
import sys
from PIL import Image, ImageFilter
src, out, x0, y0, w = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
h = w * 1672 / 941
im = Image.open(src).convert('RGB')
c = im.resize((941, 1672), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))
c = c.filter(ImageFilter.UnsharpMask(radius=1.2, percent=40, threshold=2))
c.save(out)
print(f'{out}: 切り抜き x {x0:.0f}-{x0+w:.0f} y {y0:.0f}-{y0+h:.0f}（拡大 {941/w:.2f}倍）')
