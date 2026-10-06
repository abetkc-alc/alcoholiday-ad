#!/bin/bash
# 使い方: run-codex.sh <角度番号> [版] [見本画像名] [追加の注意]
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/8aaf1547b825b104/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-06-01"
ORIG="C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL"
a=$1; v=${2:-1}; ref_img=${3:-whisky-soccer-angle1-v1.png}; extra=$4
out="whisky-soccer-angle$a-v$v.png"
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
imgs=(-i "$ORIG/whisky.jpg")
ref=""
if [ "$a" != "1" ]; then imgs+=(-i "$DIR/$ref_img"); ref="2枚目の添付画像は角度1の完成画像（同じ部屋の見本）です。"; fi
prompt="このフォルダにある whisky-soccer-prompt.md を読み、「共通プロンプト」と「角度$a」の指示を合わせて、画像生成で縦9:16の写真を1枚生成し、$out としてこのフォルダに保存してください。1枚目の添付画像はポスター原画（whisky.jpg）で、絵柄・文字を一切描き直さずに、部屋に本当に飾られているように自然になじませてください。$ref 既に同名ファイルがある場合は上書きせず、その旨を報告してください。$extra"
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s workspace-write -C "$DIR" "${imgs[@]}" 2>&1 | tail -15
[ -f "$DIR/$out" ] && echo "DONE $out" || echo "FAILED $out"
