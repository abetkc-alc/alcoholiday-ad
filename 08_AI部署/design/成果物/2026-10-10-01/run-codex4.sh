#!/bin/bash
# 使い方: run-codex4.sh <角度番号> [版] [見本画像名] [追加の注意]（見出しを変えるときは SEC="見出しの一部" を前につける）
# v4 セット：sake-holiday4-prompt.md。ポスターの大きさ（A2・障子のマスで約2.7マス）と高さ、人の座る位置を全角度でそろえる版
# 角度1：原画＋3回目の角度1（部屋・人・座る位置の見本）／角度2・3：原画＋角度1の完成画像（これを土台に「カメラが前に出た」写真）
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/9691020b546a15b2/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-10-01"
ORIG="C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL"
GEN="C:/Users/abetk/.codex/generated_images"
a=$1; v=${2:-1}; ref_img=${3:-sake-holiday4-angle1-v1-blend.png}; extra=$4
out="sake-holiday4-angle$a-v$v.png"
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
common=$(tr -d "\r" < "$DIR/sake-holiday4-prompt.md" | awk '/^## 共通/{f=1;next} /^## /{f=0} f')
angle=$(tr -d "\r" < "$DIR/sake-holiday4-prompt.md" | awk -v h="## ${SEC:-角度$a：}" '/^## /{f=(index($0,h)==1);next} f')  # 見出しの頭で探す（v1 は「角度1」が角度2・3の見出しにも入っていて、3つ分の指示が混ざった）
if [ "$a" != "1" ]; then
  imgs=(-i "$DIR/$ref_img" -i "$ORIG/sake.png")
  ref="1枚目の添付画像は角度1の完成画像です。これを土台に、同じ部屋・同じ人・同じ座る位置・同じ服・同じ光のまま、カメラだけが前に出た写真にしてください。2枚目の添付画像はポスター原画（sake.png）で、絵柄・文字を一切描き直さないでください。ポスターの実物の大きさと壁の高さは1枚目と同じです（障子のマスと比べた大きさを変えない）。"
else
  imgs=(-i "$ORIG/sake.png" -i "$DIR/sake-holiday3-angle1-v3-blend.png")
  if [ -n "$NOREF" ]; then imgs=(-i "$ORIG/sake.png"); fi  # NOREF=1：前回の写真を渡さない（v2 は前回の構図をそのまままねして、カメラが遠いままだった）
  ref="1枚目の添付画像はポスター原画（sake.png）で、絵柄・文字を一切描き直さずに、部屋に本当に飾られているように自然になじませてください。2枚目の添付画像は前回の写真で、部屋・人の服・2人の座る位置・料理の見本です。ただし前回はカメラが遠く、ポスターが大きすぎて低すぎたので、その2点は本文の数字どおりに直してください。"
  [ -n "$NOREF" ] && ref="添付画像はポスター原画（sake.png）で、絵柄・文字を一切描き直さずに、部屋に本当に飾られているように自然になじませてください。"
fi
prompt="ファイルの読み書きはせず、画像生成だけを1回行ってください。次の指示どおりの縦9:16の写真を1枚生成してください。$ref 人の顔は絶対に写さないでください。$extra

【共通】
$common

【このアングルの指示】
$angle"
mark=$(mktemp); sleep 1
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s read-only -C "$DIR" "${imgs[@]}" 2>&1 | tail -4
new=$(find "$GEN" -name '*.png' -newer "$mark" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
rm -f "$mark"
[ -n "$new" ] && cp -n "$new" "$DIR/$out" && echo "DONE $out (from $new)" || echo "FAILED $out"
