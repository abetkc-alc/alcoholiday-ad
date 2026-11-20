#!/bin/bash
# 使い方: run-codex-edit.sh <カット名> <出力名> — tshirt1966-A-base.png を土台に、指示どおり一部だけ直した画像を作る（Codex はファイル操作できないので、本文で指示し generated_images からコピー）
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/9691020b546a15b2/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-10-02"
GEN="C:/Users/abetk/.codex/generated_images"
cut=$1; out=$2
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
cutText=$(awk -v h="カット「$cut」" '/^## /{f=(index($0,h)>0);next} f' "$DIR/tshirt1966-A-prompt.md")
[ -z "$cutText" ] && { echo "カットが見つかりません: $cut"; exit 1; }
prompt="ファイルの読み書きはせず、画像生成（画像の編集）だけを1回行ってください。1枚目の添付画像（女性の完成写真）を土台に、次の指示の部分だけを直した縦9:16の写真を1枚つくってください。顔は1枚目と同じ人物のまま、少しも別人にしないでください。2枚目の添付画像は商品のTシャツ（プリントの正解）です。

$cutText"
mark=$(mktemp); sleep 1
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s read-only -C "$DIR" -i "$DIR/tshirt1966-A-base.png" -i "$DIR/Tshirt_1966_BL.png" 2>&1 | tail -3
new=$(find "$GEN" -name '*.png' -newer "$mark" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
rm -f "$mark"
[ -n "$new" ] && cp -n "$new" "$DIR/$out" && echo "DONE $out (from $new)" || echo "FAILED $out"
