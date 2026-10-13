---
部署: ai-alcoholiday（統括）
管理者: KAYO
部下: "[[design]]／[[scripts]]／[[editing]]"
管理ページ: 08_AI部署/管理ページ.html
データ: 08_AI部署/data/board.json
tags: [AI部署, 統括]
---

# ai-alcoholiday（統括・管理者 KAYO）

## 結論

- 社長（あなた）は**管理ページ**からポスター動画のイメージを指示する
- 管理者 **KAYO** がそれを読み、design・scripts・editing の3部署に仕事を振り分ける
- 各部署の成果物は**管理ページ**に並ぶ。社長が見て選ぶ
- 選ばれたものを KAYO が **SNS投稿用に仕上げる**（投稿の前に社長がもう一度確認する）

## 組織図

```
社長（あなた）
  │  管理ページから指示・選択
  ▼
ai-alcoholiday ─ 管理者 KAYO（Claude Code）
  ├─ design  ：部屋に飾った写真をつくる（Codex）        → [[design]]
  ├─ scripts ：構成・画面の文字・投稿文をつくる          → [[scripts]]
  └─ editing ：Higgsfieldで動画化・1本に組み立てる       → [[editing]]
```

## 仕事の流れ

| 段階 | だれが | 何をする | 管理ページの表示 |
|---|---|---|---|
| 1 | 社長 | 管理ページで「新しい指示」を書いて保存 | 受付 |
| 2 | 社長 | Claude Code に「**KAYO、新しい指示を確認して**」と話しかける | |
| 3 | KAYO | 指示を読み、各部署への指示文を書いて登録 | 各部署へ指示済み |
| 4 | design | 部屋の写真を2〜3案（Codex） | 制作中 |
| 5 | scripts | 構成・文字・投稿文を2〜3案 | 制作中 |
| 6 | 社長 | 動画に使う写真（角度）を順番に選び、台本を1つ選ぶ | 確認待ち |
| 7 | editing | 選ばれた写真と台本で動画をつくる（Higgsfield＋ffmpeg） | 制作中 |
| 8 | 社長 | 動画を選び「SNS用に仕上げて」を押す → KAYOに「**KAYO、仕上げて**」 | 仕上げ依頼 |
| 9 | KAYO | 投稿用セット（動画・表紙・投稿文）を `完成/` に作る | 完成 |
| 10 | 社長 | 最終確認してSNSに投稿 | 投稿済み |

※ 写真を選ぶ前に動画まで作るとお金がむだになるため、**動画化（Higgsfield）は社長が写真を選んでから**行う。

---

## 管理ページと Claude Code のつながり

- `data/kayo_watch.py` が `board.json` を2秒ごとに見張り、「新しい指示」「仕上げ依頼」を見つけると Claude Code に知らせる
- Claude Code の Monitor で `python -u data/kayo_watch.py` を起動しておく（Monitor は最長30分で切れるので、切れたら起動し直す）
- 社長に「KAYO、見張りを始めて」と言われたら起動する。Claude Code を閉じている間は届かない（その場合は話しかけて確認する）

## KAYO（Claude Code）の作業手順

社長に「KAYO、新しい指示を確認して」と言われたら：

1. `08_AI部署/data/board.json` を読む。`status` が `new` の指示を探す
2. 各部署のノート（[[design]]／[[scripts]]／[[editing]]）を読み、ノウハウに沿った部署への指示文を書く
3. `board.json` のその指示の `kayo` 欄に、部署ごとの指示文を書き込み、`status` を `dispatched` にする
4. design と scripts の仕事を実行する（部署ごとにサブエージェント `design`／`scripts` に任せてよい）
5. できたものを `deliverables` に登録し、`status` を `review` にする
6. 社長に「管理ページで確認してください」と伝える

社長が写真・台本・音楽を選んで管理ページの「**動画をつくる**」を押したら（`status` が `video_requested`。`videoRequest` に写真・台本・音楽（`music`＝曲のファイル名、`musicPath`＝曲の場所）・承認した費用の目安が入る）：

7. editing の仕事を実行する。ボタンを押す時に費用の目安（1本約0.18ドル×枚数。2026-10-03 に0.12→0.18へ変更）を社長が承認済み。実際の見積もりが目安を大きく超える場合（1本0.25ドル超など）だけ、止めて社長に確認する
8. 動画を `deliverables.editing` に登録し、`status` を `review` に戻す

社長に「KAYO、仕上げて」と言われたら（`status` が `finish_requested`）：

9. 選ばれた動画・台本で投稿用セットを `08_AI部署/完成/<指示番号>/` に作る（[[editing]] の「3. SNS投稿用に仕上げる」）
10. `final` 欄にファイルを登録し、`status` を `done` にする

### 社長から直しが来たとき（2026-10-10 社長の指示）

1. `board.json` のその指示の `log` に「直し：（社長の言葉）」を書く
2. 担当の部署で直す（新しいファイルは v2・v3 と別名）
3. 直しから**次にも活かせること**を、担当部署のノート（[[design]]／[[scripts]]／[[editing]]）の「直しから学んだこと（社長の直し）」に1行で書き足す（日付・指示番号・社長の言葉 → 次からどうするか）
4. 新しい指示を受けたら、部署への指示文を書く前に、3部署の「直しから学んだこと」を**必ず読んで**指示文に入れる
5. BAR広告のお客さんの直しは、プログラム（`tools/fix_learn.py`）が自動で [[直しから学んだこと]] に書き足す（KAYO が手で直したときも、学びがあればそこへ書く）

### 守ること

- ファイルは削除しない・上書きしない（新しいものは別名で保存）
- SNS に勝手に投稿しない
- お金がかかる作業は先に社長に確認する
- 管理ページも `board.json` を書き換えるので、**書き込む直前に必ず読み直し**、他の指示を消さないようにする

---

## board.json の形（データの書き方）

```json
{
  "orders": [
    {
      "id": "2026-09-27-01",
      "createdAt": "2026-09-27T10:00:00+09:00",
      "products": ["wine", "whisky"],
      "image": "社長が書いたポスターのイメージ",
      "note": "社長の補足メモ",
      "status": "new",
      "kayo": { "summary": "", "design": "", "scripts": "", "editing": "" },
      "deliverables": {
        "design":  [{ "id": "d1", "title": "ワイン 案A 雨の窓辺", "files": ["design/成果物/2026-09-27-01/wine-rain-angle1-v1.png", "design/成果物/2026-09-27-01/wine-rain-angle2-v1.png", "…angle3〜5"], "memo": "" }],
        "scripts": [{ "id": "s1", "title": "案A", "text": "台本の本文（構成表・画面の文字・投稿文）", "memo": "" }],
        "editing": [{ "id": "e1", "title": "v1", "files": ["editing/成果物/2026-09-27-01/wine-rain-v1.mp4"], "memo": "" }]
      },
      "selected": { "design": null, "designFiles": [], "scripts": null, "editing": null },
      "final": { "files": [], "memo": "" },
      "log": [{ "at": "2026-09-27T10:00:00+09:00", "by": "社長", "text": "指示を受付" }]
    }
  ]
}
```

- `products`：選ばれた商品の一覧（複数あり）。`wine`／`whisky`／`beer`／`sake`／`sparkling`。古い指示は `product`（1つだけ）の場合がある
- 商品が複数のときは、商品ごとに design・scripts・editing の成果物をつくり、`title` に商品名を入れて区別する（例：「ワイン 案A」）
- `status`：`new`（受付）→ `dispatched`（各部署へ指示済み）→ `working`（制作中）→ `review`（確認待ち）→ `video_requested`（動画づくり依頼）→ `working` → `review` → `finish_requested`（仕上げ依頼）→ `done`（完成）→ `posted`（投稿済み）。社長が「没」にした指示は `dropped`（管理ページに出さない。ファイルと記録は消さずに残す。2026-10-11〜）
- ファイルの場所は `08_AI部署` から見た位置で書く（管理ページがそこから画像・動画を読む）
- `log` には、だれが何をしたかを1行ずつ足していく
- design の成果物は「部屋の案」1つにつき1件。`files` にアングル違いの写真を angle1 から順に全部入れる
- `selected.designFiles`：社長が「動画に使う」を押した写真（**押した順＝動画でつなぐ順**）。editing はこれを使う
- `selected.music`／`selected.musicPath`：社長が選んだ音楽（2026-10-03〜）。曲の置き場所は `C:\Users\abetk\Desktop\ALCOHOLIDAY\音声\backmusic\`。管理ページの「音楽フォルダを選ぶ」でこのフォルダを読み、試し聞きして1曲選ぶ（音楽を選ばないと「動画をつくる」は押せない）

## フォルダ構成

```
08_AI部署/
  ai-alcoholiday.md   … このノート（KAYO）
  管理ページ.html      … 社長が使う画面
  data/board.json     … 指示と成果物の一覧
  design/  design.md ＋ 成果物/
  scripts/ scripts.md ＋ 成果物/
  editing/ editing.md ＋ 成果物/
  完成/               … SNS投稿用セット
```

## 管理ページの使い方（社長向け）

1. `管理ページ.html` をダブルクリックして開く（**Chrome か Edge** で開く）
2. 初回だけ「フォルダを選ぶ」を押し、`08_AI部署` フォルダを選んで「許可」する
3. 「新しい指示」に商品とポスターのイメージを書いて「KAYOに指示を出す」
4. Claude Code に「KAYO、新しい指示を確認して」と話しかける
5. 成果物がそろったら管理ページで見比べ、「これを選ぶ」を押す
6. 動画を選んだら「SNS用に仕上げて」を押し、Claude Code に「KAYO、仕上げて」と話しかける

> [!info] 広告事業（BARのおすすめ紹介）
> KAYO は広告事業も担当する。手順は [[広告事業]]（`09_広告事業/広告事業.md`）。

関連：[[ALCOHOLIDAY 事業計画]]／[[04_動画生成]]／[[03_SNS投稿]]／[[AI部署 仕事一覧]]
