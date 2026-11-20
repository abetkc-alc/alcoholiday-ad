#!/bin/bash
# 使い方: run-codex4-edit.sh <土台の画像> <直しの見出しの頭> <出力名> [poster]
#   sake-holiday4-prompt.md の「## 直し4：…」の文を使い、土台の画像を編集する（2026-10-10-02 の run-codex-edit.sh と同じ方法）
#   4つ目に poster と書くと、ポスター原画 sake.png も2枚目に添付する
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/9691020b546a15b2/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-10-01"
ORIG="C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL"
GEN="C:/Users/abetk/.codex/generated_images"
base=$1; head=$2; out=$3
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
text=$(tr -d "\r" < "$DIR/sake-holiday4-prompt.md" | awk -v h="## $head" '/^## /{f=(index($0,h)==1);next} f')
[ -z "$text" ] && { echo "見出しが見つかりません: $head"; exit 1; }
imgs=(-i "$DIR/$base"); add=""
[ "$4" = "poster" ] && { imgs+=(-i "$ORIG/sake.png"); add="2枚目の添付画像はポスター原画（sake.png）です。ポスターの絵柄・文字は描き直さず、この原画のとおりにしてください。"; }
prompt="ファイルの読み書きはせず、画像生成（画像の編集）だけを1回行ってください。1枚目の添付画像を土台に、次の指示どおりに直した縦9:16の写真を1枚つくってください。指示にない所は1枚目とまったく同じにしてください。$add 人の顔は絶対に写さないでください。

$text"
mark=$(mktemp); sleep 1
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s read-only -C "$DIR" "${imgs[@]}" 2>&1 | tail -3
new=$(find "$GEN" -name '*.png' -newer "$mark" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
rm -f "$mark"
[ -n "$new" ] && cp -n "$new" "$DIR/$out" && echo "DONE $out (from $new)" || echo "FAILED $out"
