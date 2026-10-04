#!/bin/bash
# 使い方: run-codex-v2.sh <A|C> → v1の顔はそのままでプリントだけなじませ / run-codex-v2.sh B → 新しい顔で作り直し
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/faa963e871dd422c/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-03-02"
who=$1; out="tshirt1966-woman$who-v2.png"
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
if [ "$who" = "B" ]; then
  imgs=(-i "$DIR/Tshirt_1966_BL.png")
  prompt="このフォルダにある tshirt1966-women-prompt.md を読み、「共通プロンプト」「プリントのなじませ」「人物B（v2・クールな印象に変更）」の指示を合わせて（古い「人物B」は使わない）、画像生成で縦9:16の写真を1枚生成し、$out としてこのフォルダに保存してください。添付画像は商品のTシャツです。女性はこのTシャツを着ており、プリントの文字と絵柄の形は変えず、布に刷り込まれたように自然になじませてください（下のamazonの文字や価格は不要）。既に同名ファイルがある場合は上書きせず、その旨を報告してください。"
else
  imgs=(-i "$DIR/tshirt1966-woman$who-v1.png" -i "$DIR/Tshirt_1966_BL.png")
  prompt="このフォルダにある tshirt1966-women-prompt.md の「プリントのなじませ」を読んでください。1枚目の添付画像（tshirt1966-woman$who-v1.png）をもとに、人物の顔・髪型・表情・ポーズ・背景・構図・色味はそのまま変えずに、Tシャツの胸のプリントだけを「プリントのなじませ」の指示どおり、布に刷り込まれたインクに見えるよう描き直した縦9:16の写真を画像生成で1枚つくり、$out としてこのフォルダに保存してください。2枚目の添付画像は商品のTシャツで、プリントの文字・カモメの形の正解です（つづりを変えない）。既に同名ファイルがある場合は上書きせず、その旨を報告してください。"
fi
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s workspace-write -C "$DIR" "${imgs[@]}" 2>&1 | tail -8
[ -f "$DIR/$out" ] && echo "DONE $out" || echo "FAILED $out"
