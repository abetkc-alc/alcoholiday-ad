#!/bin/bash
# 使い方: run-codex.sh <商品> <角度番号> [セット名] [版] [追加の注意]
#   例) run-codex.sh wine 1               → wine-friday-prompt.md から wine-friday-angle1-v1.png
#   例) run-codex.sh wine 1 friday-v2     → wine-friday-v2-prompt.md から wine-friday-v2-angle1-v1.png
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/d23520d1e41bfb24/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-09-27-01"
ORIG="C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL"
p=$1; a=$2; set=${3:-friday}; v=${4:-1}; extra=$5
out="$p-$set-angle$a-v$v.png"
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
imgs=(-i "$ORIG/$p.jpg")
ref=""
if [ "$a" != "1" ]; then imgs+=(-i "$DIR/${REF:-$p-$set-angle1-v1.png}"); ref="2枚目の添付画像は角度1の完成画像（同じ部屋の見本）です。"; fi
prompt="このフォルダにある $p-$set-prompt.md を読み、「共通プロンプト」と「角度$a」の指示を合わせて、画像生成で縦9:16の写真を1枚生成し、$out としてこのフォルダに保存してください。1枚目の添付画像はポスター原画（$p.jpg）で、絵柄・文字を一切描き直さずに、部屋に本当に飾られているように自然になじませてください。$ref 既に同名ファイルがある場合は上書きせず、その旨を報告してください。$extra"
# 指示文は標準入力で渡す（-i は複数の画像を受け取るため、後ろに書いた指示文まで画像扱いされてしまう）
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s workspace-write -C "$DIR" "${imgs[@]}" 2>&1 | tail -15
[ -f "$DIR/$out" ] && echo "DONE $out" || echo "FAILED $out"
