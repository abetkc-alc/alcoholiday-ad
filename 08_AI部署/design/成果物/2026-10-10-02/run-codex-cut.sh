#!/bin/bash
# 使い方: run-codex-cut.sh <アップ|乾杯前> <出力名>
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/9691020b546a15b2/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-10-02"
cut=$1; out=$2
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
prompt="このフォルダにある tshirt1966-A-prompt.md を読み、「共通」と「カット「$cut」」の指示を合わせて、画像生成で縦9:16の写真を1枚生成し、$out としてこのフォルダに保存してください。1枚目の添付画像は同じ女性の完成写真（顔・髪・服・場所の見本）、2枚目は商品のTシャツ（プリントの正解。下のamazonの文字や価格は不要）です。既に同名ファイルがある場合は上書きせず、その旨を報告してください。"
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s workspace-write -C "$DIR" -i "$DIR/tshirt1966-A-base.png" -i "$DIR/Tshirt_1966_BL.png" 2>&1 | tail -6
[ -f "$DIR/$out" ] && echo "DONE $out" || echo "FAILED $out"
