#!/bin/bash
# 使い方: run-codex2.sh <角度番号> [版] [見本画像名] [追加の注意]（v2 セット：sake-holiday2-prompt.md を使う。角度1も前回の角度1を「同じ部屋の見本」として渡す）
# Codex の新しい版は日本語の場所の読み書きでエラーになるので、指示を本文に入れ、画像は ~/.codex/generated_images からコピーする（2026-10-10-02 の方法）
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/9691020b546a15b2/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-10-01"
ORIG="C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL"
GEN="C:/Users/abetk/.codex/generated_images"
a=$1; v=${2:-1}; ref_img=${3:-sake-holiday2-angle1-v1.png}; extra=$4
out="sake-holiday2-angle$a-v$v.png"
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
common=$(tr -d "\r" < "$DIR/sake-holiday2-prompt.md" | awk '/^## 共通/{f=1;next} /^## /{f=0} f')
angle=$(tr -d "\r" < "$DIR/sake-holiday2-prompt.md" | awk -v h="角度$a" '/^## /{f=(index($0,h)>0);next} f')
imgs=(-i "$ORIG/sake.png")
ref=""
if [ "$a" != "1" ]; then imgs+=(-i "$DIR/$ref_img"); ref="2枚目の添付画像は角度1の完成画像（同じ部屋・同じ光・同じ料理と人の服の見本）です。"
else imgs+=(-i "$DIR/sake-holiday-angle1-v1-blend.png"); ref="2枚目の添付画像は前回の同じ部屋の写真（部屋・家具・料理・人の服の見本）です。ただし前回の写真の、壁の木もれ日・葉の影・斜めの光の帯と、窓のすぐ外の木はまねせず、やわらかく一様な光にしてください。人の手は器を置いた落ち着いた状態にしてください。"; fi
prompt="ファイルの読み書きはせず、画像生成だけを1回行ってください。次の指示どおりの縦9:16の写真を1枚生成してください。1枚目の添付画像はポスター原画（sake.png）で、絵柄・文字を一切描き直さずに、部屋に本当に飾られているように自然になじませてください。$ref 人の顔は絶対に写さないでください。$extra

【共通】
$common

【このアングルの指示】
$angle"
mark=$(mktemp); sleep 1
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s read-only -C "$DIR" "${imgs[@]}" 2>&1 | tail -4
new=$(find "$GEN" -name '*.png' -newer "$mark" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
rm -f "$mark"
[ -n "$new" ] && cp -n "$new" "$DIR/$out" && echo "DONE $out (from $new)" || echo "FAILED $out"
