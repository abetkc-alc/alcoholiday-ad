#!/bin/bash
# 使い方: run-codex.sh <人物A|B|C> [版]
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/faa963e871dd422c/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-03-02"
who=$1; v=${2:-1}
out="tshirt1966-woman$who-v$v.png"
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
prompt="このフォルダにある tshirt1966-women-prompt.md を読み、「共通プロンプト」と「人物$who」の指示を合わせて、画像生成で縦9:16の写真を1枚生成し、$out としてこのフォルダに保存してください。添付画像は商品のTシャツ（Tshirt_1966_BL.png）です。女性はこのTシャツを着ており、プリントの文字と絵柄は一切描き直さずに正確に再現してください（下のamazonの文字や価格は不要）。既に同名ファイルがある場合は上書きせず、その旨を報告してください。"
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s workspace-write -C "$DIR" -i "$DIR/Tshirt_1966_BL.png" 2>&1 | tail -8
[ -f "$DIR/$out" ] && echo "DONE $out" || echo "FAILED $out"
