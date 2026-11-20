#!/bin/bash
# 使い方: run-codex3-edit.sh <土台の画像> <直しの見出しの一部> <出力名> — sake-holiday3-prompt.md の「## 直し：…」の文を使い、土台の画像の一部だけを直す（2026-10-10-02 の run-codex-edit.sh と同じ方法）
CODEX="C:/Users/abetk/AppData/Local/OpenAI/Codex/bin/9691020b546a15b2/codex.exe"
DIR="C:/Users/abetk/Desktop/AIアルコホリディ/08_AI部署/design/成果物/2026-10-10-01"
GEN="C:/Users/abetk/.codex/generated_images"
base=$1; head=$2; out=$3
[ -f "$DIR/$out" ] && { echo "SKIP $out (already exists)"; exit 0; }
text=$(tr -d "" < "$DIR/sake-holiday3-prompt.md" | awk -v h="$head" '/^## /{f=(index($0,h)>0);next} f')
[ -z "$text" ] && { echo "見出しが見つかりません: $head"; exit 1; }
prompt="ファイルの読み書きはせず、画像生成（画像の編集）だけを1回行ってください。1枚目の添付画像を土台に、次の指示の部分だけを直した縦9:16の写真を1枚つくってください。直す所以外（部屋・カメラ・ポスター・料理・人の服）は1枚目とまったく同じにしてください。人の顔は絶対に写さないでください。

$text"
mark=$(mktemp); sleep 1
printf '%s' "$prompt" | "$CODEX" exec --skip-git-repo-check -s read-only -C "$DIR" -i "$DIR/$base" 2>&1 | tail -3
new=$(find "$GEN" -name '*.png' -newer "$mark" -printf '%T@ %p
' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
rm -f "$mark"
[ -n "$new" ] && cp -n "$new" "$DIR/$out" && echo "DONE $out (from $new)" || echo "FAILED $out"
