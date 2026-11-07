# ALCニュース：番組ロゴをつくる
#   2026-11-07 タケシさんの指示：見本（白い四角3つに赤い字＋「NEWS」）の形で、NEWS をカタカナの「ニュース」に
#   赤い札の上に、白い四角に赤い「A」「L」「C」、その右に白い「ニュース」
#   AI に描かせると字がくずれるので、字の形（フォント）から組み立てる
#   使い方: python 素材/make_logo.py → 素材/logo-alcnews.png（高さ 92px。2倍で描いて縮める）
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
S = 2                      # 2倍の大きさで描いてから縮める（ふちをなめらかに）
H = 92 * S
RED, WHITE = (196, 22, 28), (255, 255, 255, 255)
F_BLOCK = ImageFont.truetype(r"C:\Windows\Fonts\GILB____.TTF", 64 * S)                  # Gill Sans MT Bold
F_NEWS = ImageFont.truetype(r"C:\Windows\Fonts\BIZ-UDGothicB.ttc", 50 * S, index=1)     # テロップと同じ BIZ UDPゴシックの太字（2026-11-07 タケシさんの指示）
PAD = 12 * S               # 札のふちの余白
BOX = H - PAD * 2          # 白い四角の大きさ
GAP = 7 * S                # 四角どうしのすきま
SHEAR = 0.2                # イタリック（右へかたむける。2026-11-07 タケシさんの指示）


def plate(w):
    """赤い札（上が少し明るく、下が少し暗い）"""
    y = np.linspace(1.12, 0.86, H)[:, None, None]
    a = np.clip(np.array(RED, float)[None, None, :] * y, 0, 255).repeat(w, 1)
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


def main():
    wn = int(F_NEWS.getlength("ニュース"))
    slant = int(SHEAR * BOX)
    total = PAD + (BOX + GAP) * 3 + 10 * S + wn + PAD + 4 * S + slant
    im = plate(total)
    fg = Image.new("RGBA", (total, H), (0, 0, 0, 0))   # 四角と字をまとめて描き、あとでかたむける
    d = ImageDraw.Draw(fg)
    x = PAD
    for ch in "ALC":
        d.rectangle([x, PAD, x + BOX - 1, PAD + BOX - 1], fill=WHITE)
        d.text((x + BOX / 2, PAD + BOX / 2 + 3 * S), ch, font=F_BLOCK, fill=RED, anchor="mm")
        x += BOX + GAP
    d.text((x + 10 * S, H // 2 + 2 * S), "ニュース", font=F_NEWS, fill=WHITE, anchor="lm")
    fg = fg.transform(fg.size, Image.AFFINE, (1, SHEAR, -SHEAR * H / 2 - slant / 2, 0, 1, 0), Image.BICUBIC)
    im.alpha_composite(fg)
    im = im.resize((total // S, H // S), Image.LANCZOS)
    out = HERE / "logo-alcnews.png"
    im.save(out)
    print(out, im.size)


if __name__ == "__main__":
    main()
