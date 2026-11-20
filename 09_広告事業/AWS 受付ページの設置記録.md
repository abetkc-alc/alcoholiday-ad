---
事業: ALCOHOLIDAY 広告事業（ショート動画作成）
作成: 2026-10-11
tags: [広告事業, AWS, Amplify]
---

# AWS 受付ページの設置記録

## 結論

- 受付サイトは **https://ad.alcoholiday.org/**（AWS Amplify）。GAS は裏方（台帳・メール・動画の受け渡し・自動制作）のまま
- これで、ホームページに埋め込んだときの**縦スクロールの2重**と、Google のページを直接開いたときの「**Google Apps Script のユーザーによって作成…**」のお知らせが、両方なくなった（2026-10-11 社長が確認「全部解決している！」）
- **AWS の無料プランは 2027年4月11日 まで**。1週間前（**2027-04-04**）に、GAS の1時間ごとの見回りから社長のメールにリマインドが届く（Code.gs の `OWNER_REMINDERS`）。続けるには、AWS の「プランをアップグレード」で有料プランへ（今の使い方なら月に数十円〜数百円ほどの見込み）

## なぜ AWS にしたか

| 方法 | スクロール | お知らせ | 結果 |
|---|---|---|---|
| Google サイトに埋め込む（〜2026-10-10） | 2重（窓の高さ1200・中身はトップ約4200／申し込み約10700） | 出ない（確認ページは出る） | 携帯で操作しにくい |
| Google のページを直接開く | 1つ | 出る | お知らせが気になる |
| Google フォームに置き換える | 2重のまま | — | 会員・動画のチェック・声の見本などが使えない |
| **AWS（Amplify）に受付ページを置く** | **1つ** | **出ない** | **採用**（2026-10-11） |

- Google サイトには入力欄の部品がないので、どの方法でも「窓（埋め込み）」になり、窓の高さは固定（自動で伸び縮みしない）
- スクロールバーを見えなくする直し（css.html）もしたが、2重のスクロール自体は残った

## しくみ

```
ホームページ（Google サイト）
  └「申し込み・ログインはこちら」ボタン（予定）
        ↓
受付ページ https://ad.alcoholiday.org/（AWS Amplify）
  web/index.html … 小さな入口だけ
        ↓ ページの中身をもらう（doPost の page）／ボタンの動き（doPost の call）
GAS（今のまま）… 台帳・メール・動画の受け渡し・自動制作とのやりとり
```

- ページの中身（トップ・申し込み・確認ページ）は **google/ のファイル（top.html・form.html・review.html など）だけ**で管理。Google 版と AWS 版で同じもの
- `common.html` の `run`：Google のページなら google.script.run、AWS の受付ページなら fetch で GAS を呼ぶ
- GAS で外から呼べる関数は `PUBLIC_FNS`（Google のページで呼べるものと同じ）。KAYO の呼び出しは今までどおりキーが必要
- ログインの合言葉は、AWS の受付ページではその端末に覚えておく（localStorage の `alc_session`）。トップページが出たら消す・ログアウトで消す。住所の欄の `?s=…` は消す
- Code.gs の `WEB_URL`（`https://ad.alcoholiday.org/`）：メールのリンク（会員登録・パスワード再設定・動画の確認ページ）がこの住所になる（2026-10-11 切り替え）

## ファイル

| ファイル | 中身 |
|---|---|
| `09_広告事業/web/index.html` | AWS に置く入口のページ |
| `amplify.yml`（フォルダのいちばん上） | Amplify の置き方の決まり。置くのは index.html と config.js だけ（ノートなどは公開しない） |
| `09_広告事業/tools/web_config.py` | パソコンで試すための config.js をつくる（.env の BAR_API_URL から。GitHub には送らない） |

パソコンで試す：`python 09_広告事業/tools/web_config.py` → `python -m http.server 8080 -d 09_広告事業/web` → http://localhost:8080/

## AWS の設定（社長が 2026-10-11 に行った）

1. **アカウント**：サインインは Google（AWS Builder ID・abetkc@alcoholiday.org）。アカウント名「Blank Canvas」。無料プラン（クレジット100ドル・2027-04-11 まで）
   - 最初の案内に出る「Agent Toolkit（AI を AWS につなぐ）」「Kiro」は使わない
2. **MFA**：AWS Builder ID の「セキュリティ」→「デバイスの登録」→「**認証アプリ**」（Google Authenticator・無料）。「組み込みの認証アプリ」は、そのパソコンが壊れると入れなくなるので選ばない。**スマホを機種変更するときは、認証アプリの設定も移す**
3. **Amplify**：「アプリケーションをデプロイ」→ GitHub → 許可は **alcoholiday-ad のリポジトリだけ** → ブランチ main・モノレポの印なし → 詳細設定の**環境変数 `ALC_API`** に GAS のウェブアプリの URL（…/exec）→ 保存してデプロイ。アプリ名 alcoholiday-ad。仮の住所 https://main.d2ka0x6jgn1g8d.amplifyapp.com/
   - **GitHub の main に送ると、自動で置き直す**。ふだん Amplify の画面は開かなくてよい
   - 最初は「Welcome」の仮ページが出る。数分で置き終わる
4. **住所 ad.alcoholiday.org**：Amplify の「ホスティング」→「カスタムドメイン」→ alcoholiday.org →「**手動設定**」（Route 53 は使わない。無料プランでは使えず、DNS ごと引っ越すとホームページとメールが止まるおそれ）→ **「ルートを除外」**して **ad → main** の1行だけ → Amplify マネージド証明書
5. **Squarespace の DNS**（カスタムレコード）に CNAME を2行足した。**もとの行（www → ghs.googlehosted.com・メール・Search Console の TXT など）は触らない**
   - 証明書の確認用：名前 `_e5b07c3…`（Amplify に出る名前から「.alcoholiday.org.」を消したもの）→ データ `_5d79d25f…acm-validations.aws.`
   - `ad` → `d3l6nj6bxlpdpg.cloudfront.net`
   - 数分で「使用可能」になった。http は https に自動で移る

## 確かめたこと（2026-10-11）

- KAYO：iPhone の大きさで、トップページ・ログインの画面・GAS の呼び出し・確認ページ・横のはみ出しなし・窓なし。ノートや .env は外から見えない（どれも「見つかりません」）
- 社長：携帯でログイン → テストの申し込み → 開き直してもログインしたまま → ログアウトまで問題なし

## 検索（SEO）対策（2026-11-08）

- 前は、検索ロボットが最初に見る中身が「読み込んでいます…」だけだった。`web/index.html` にトップページの説明（見出し・特長・申し込みの流れ）を最初から書き、GAS のページが届いたら入れ替わる
- 検索結果の題名「飲食店・BARのおすすめ紹介ショート動画作成｜スマホ動画3本でSNS用に｜ALCOHOLIDAY」と説明文、SNS で共有したときの題名・説明・画像（og.jpg）、会社とサービスの説明（構造化データ）を入れた。入れ替えたあとも残す
- `?〜` の付くお客さん専用のページ（確認ページなど）は検索に出さない（noindex と robots.txt）
- 新しく置くもの：`web/robots.txt`・`web/sitemap.xml`・`web/favicon.svg`（赤い四角に白い A）・`og.jpg`（`tools/og_image.py` が photos.html のカクテルの写真を取り出す。画像は GitHub に送らないため）
- **トップページ（google/top.html）の文を変えたら、web/index.html の #seo も合わせて直す**

## これから

- [x] Google Search Console（ドメイン alcoholiday.org）に https://ad.alcoholiday.org/sitemap.xml を送った（2026-11-08「成功しました」・ページ数1）

- [ ] ホームページ（Google サイトの「美味しいもの」）の埋め込みを、「申し込み・ログインはこちら」のボタン（https://ad.alcoholiday.org/）に替える
- [ ] 会員のログインを AWS（Cognito・OAuth）に変える（社長の方針。まだ実行しない）
- [ ] 2027-04-04 のリマインドが来たら、AWS を有料プランに切り替える

関連：[[広告事業]]／[[設置手順]]／[[06_日誌/2026/10/2026-10-11|日誌 10-11]]／[[ウェブサイト（Googleサイト）]]
