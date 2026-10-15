---
name: codex
description: Codex（OpenAI）に仕事をたのむ。社長が「Codex で〜」「Codex に〜」「Codex に見てもらって」と言ったとき、または design 部が Codex で画像をつくるときに使う。08_AI部署/data/codex.py から呼ぶ。
---

# Codex に仕事をたのむ（2026-10-16）

Claude から Codex を呼ぶときは、必ず `08_AI部署/data/codex.py` を使う。
codex.exe を直接さがして呼ばない。置き場所は更新で変わるが、このプログラムが毎回いちばん新しいものを見つける。

## 呼び方（Bash）

```bash
cd "C:/Users/abetk/Desktop/AIアルコホリディ"
# 相談・見直し（ファイルは書きかえさせない）
python 08_AI部署/data/codex.py "指示文" --readonly -C <見てほしいフォルダ>
# 画像づくり・ファイルをつくる仕事（-C のフォルダの中だけ書きかえてよい）
python 08_AI部署/data/codex.py --prompt-file <指示.md> -C <成果物フォルダ> -i <画像1> -i <画像2>
```

- 時間がかかる仕事（画像づくりは数分〜十数分）は Bash の `run_in_background` で動かし、終わりを待つ。`--timeout` のはじめは30分
- Codex の返事は「----- Codex の返事 -----」の下に出る。残したいときは `--out 返事.md`
- `-C` は、いちばんせまい作業フォルダにする（Vault 全体にしない）。書きかえてほしくないときは `--readonly`

## 指示文に必ず入れること

- 日本語で返事をすること
- 「既に同じ名前のファイルがあるときは上書きせず、そのことを報告する」
- 「ファイルを削除しない」
- `.env` や `07_アカウント管理` は読まない・中身を書かない

## 終わったら

- Codex の返事と、できたファイルを Claude が自分で確かめる（画像は Read で見る）。Codex の「できました」をそのまま信じない
- 社長には、結論から、やさしい言葉で伝える
- 画像づくりの細かい手順（なじませ仕上げなど）は `08_AI部署/design/design.md` に従う
