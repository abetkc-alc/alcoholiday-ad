#!/bin/bash
# 使い方: run-codex-cut-v2.sh <アップ|乾杯前> <出力名>
# v2：Codex の新しい版は、このフォルダ（日本語の場所）のファイル読み書きでエラー（helper_unknown_error）になる。
#   → 指示（tshirt1966-A-prompt.md の「共通」＋カット）を本文に入れて渡し、できた画像は ~/.codex/generated_images からこのフォルダへコピーする。
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/9691020b546a15b2/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-10-02"
GEN="C:/Users/abetk/.codex/generated_images"
cut=$1; out=$2
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
common=$(tr -d "" < "$DIR/tshirt1966-A-prompt.md" | awk '/^## 共通/{f=1;next} /^## /{f=0} f')
cutText=$(tr -d "" < "$DIR/tshirt1966-A-prompt.md" | awk -v h="カット「$cut」" '/^## /{f=(index($0,h)>0);next} f')
[ -z "$cutText" ] && { echo "カットが見つかりません: $cut"; exit 1; }
prompt="ファイルの読み書きはせず、画像生成だけを1回行ってください。次の指示どおりの縦9:16の写真を1枚生成してください。1枚目の添付画像は同じ女性の完成写真（顔・髪・服・場所の見本。tshirt1966-A-base.png）、2枚目は商品のTシャツ（プリントの正解。下のamazonの文字や価格は不要）です。

【共通】
$common

【このカットの指示】
$cutText"
mark=$(mktemp); sleep 1
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s read-only -C "$DIR" -i "$DIR/tshirt1966-A-base.png" -i "$DIR/Tshirt_1966_BL.png" 2>&1 | tail -4
new=$(find "$GEN" -name '*.png' -newer "$mark" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
rm -f "$mark"
[ -n "$new" ] && cp -n "$new" "$DIR/$out" && echo "DONE $out (from $new)" || echo "FAILED $out"
