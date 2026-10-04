# Instagram連携メモ

[[03_SNS投稿]] の関連メモ。ClaudeCodeとInstagramをつなげるための作業記録。

## ①分析用の連携（投稿の反応を見る）※保留中

- 使うスクリプト：`fetch_instagram_posts.py`（ルートフォルダに設置済み）
- 2026-08-22：ログイン自体は成功したが、投稿データ取得時にエラー発生
  - 原因：Instagram側の仕様変更に、ツール（Instaloader）が対応できていない
  - さらにInstaloaderは2025年11月から更新停止しており、使用によるアカウント凍結リスクの報告もある
    （参考：[Issue #2656](https://github.com/instaloader/instaloader/issues/2656)、[Issue #2555](https://github.com/instaloader/instaloader/issues/2555)）
  - → リスクに見合わないため、この方法は保留。②の公式連携に一本化する
- 2026-08-22追記：実際にログイン後の投稿データ取得を試したが、エラーは直らなかった
  - 原因は**Instagram（Meta）側サーバーの不具合**と判明（「ig_business_category_subvertical」という項目が削除されたことによるサーバーエラー）
  - Instaloader側の問題ではなく、こちらで打てる対処法がない状態
- 状態：☐ 現状使用不可（Meta側の不具合待ち。②に切り替え推奨）

## ②自動投稿用の連携（動画を自動でアップする・分析もこちらに統合）

※①の代わりに、投稿の分析（いいね数・コメント数など）もこちらの公式の仕組みで行う。

Instagramへ公式に自動投稿するには、Meta（Facebook）が用意した「Instagramグラフ API（Content Publishing API）」という窓口を使う。あべさんご自身の操作が必要な準備が以下。

- ☐ Instagramアカウント（alcohol_iday）を「プロアカウント（ビジネス）」に切り替える
  - インスタアプリ → 設定 → アカウントの種類とツール → プロアカウントに切り替える
- ~~☐ Facebookページを1つ作る~~
  - 2026-08-22：Facebookアカウントが作れないため保留 → 下記の新方式を試す
  - ☐【新方式】Facebookページ不要の連携方法（2024年〜Metaが提供）を試す
    - 「Instagram API with Instagram Login」という仕組み。Facebookページとの連携が不要
    - ただし、開発者サイト（developers.facebook.com）への登録自体にFacebookアカウントが必要かどうかは未確認
    - → まず developers.facebook.com にアクセスし、登録にFacebookアカウントが必須か確認する
  - 2026-08-22：Facebookアカウント新規登録を試みたが、送信しても反応なし
    - 短時間に登録を試みるとFacebookが不審な動きとみなしブロックすることがあるため、24時間は操作せず様子を見る方針に
    - 再開目安：2026-08-23以降
    - 再開時：まずスマホのFacebookアプリからの登録を試す（パソコンより成功しやすい）
- ☐ Meta for Developers（developers.facebook.com）でアカウント登録し、「アプリ」を1つ作成する
  - アプリの種類は「ビジネス」を選ぶ
- ☐ 作成したアプリに「Instagram」の機能（プロダクト）を追加する
- ☐ アクセストークン（合言葉のようなもの）を発行する
  - これがあれば、プログラムから「代わりに投稿していいですよ」と証明できる
- ☐ InstagramビジネスアカウントID を控える

上記がそろったら、あべさんから「アクセストークンとアカウントIDが取れた」と教えてもらえれば、
それを使って「動画を確認してからワンクリックで投稿する」プログラムをこちらで作成する。

状態：☐ 未着手
