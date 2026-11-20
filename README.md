# ALCOHOLIDAY（アルコホリディ）

**お酒との時間をもっと楽しく**

お酒をテーマにした雑貨（ポスター・Tシャツ・缶バッジなど）をつくって売っているブランドです。
このリポジトリは、ALCOHOLIDAY の仕事のノートと、AI で動画づくりなどを自動にするプログラムをまとめたものです。

## Web サイト・お店

| 名前 | アドレス | 内容 |
|---|---|---|
| ホームページ | https://www.alcoholiday.org/ | ブランドの紹介（Google サイト） |
| ショート動画作成の受付サイト | https://ad.alcoholiday.org/ | BAR・飲食店のおすすめ紹介動画の申し込み（AWS Amplify） |
| Amazon ストア | https://www.amazon.co.jp/stores/ALCOHOLIDAY/page/F79A1788-B8AA-4248-973D-17D360788C0C | 商品の販売 |
| Instagram | https://www.instagram.com/alcohol_iday/ | @alcohol_iday |

## 目標と売上をつくる流れ

- 毎月の売上：100万円
- SNS でお客さんを見つける → Amazon ストアで買ってもらう

## フォルダの中身

このフォルダ全体が Obsidian（ノートアプリ）の保管庫です。入口のノートは [ALCOHOLIDAY 事業計画.md](ALCOHOLIDAY%20事業計画.md)。

| フォルダ | 内容 |
|---|---|
| `00_インボックス` | とりあえずのメモ置き場 |
| `01_ブランド` | ブランドの方針・ホームページの記録 |
| `02_商品` | 商品ごとの情報 |
| `03_SNS投稿` | SNS 投稿の企画・記録・動画の分析 |
| `04_動画生成` | AI での動画づくりの記録 |
| `05_売上・数字` | 売上や目標の記録 |
| `06_日誌` | 毎日の作業の記録 |
| `08_AI部署` | AI の部署（design／scripts／editing／marketing）と、まとめ役 KAYO の手順 |
| `09_広告事業` | ショート動画作成サービス（受付サイト・自動制作のプログラム・ALCニュース） |
| `10_しゃべるキャラ` | 古い iPad で話すキャラ「ホリィ」 |

## 受付サイト（ad.alcoholiday.org）のしくみ

- ページの中身：`09_広告事業/google/`（Google Apps Script）
- 入口のページ：`09_広告事業/web/index.html`（AWS Amplify に置く。置き方は `amplify.yml`）
- GitHub の main に送ると、Amplify が自動で受付サイトを新しくします

## 送らないもの

- APIキーなどの秘密の設定（`.env`。名前の一覧だけ `.env.example`）
- 画像・動画・音声
- お客さんの案件（個人情報）、`07_アカウント管理`

くわしい作業のきまりは [CLAUDE.md](CLAUDE.md) にあります。
