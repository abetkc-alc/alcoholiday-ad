/**
 * ALCOHOLIDAY BAR広告 ショート動画作成の受付・お渡しシステム（Google Apps Script）
 *
 * できること
 *   0. トップページ（お客さん用）：サービスの紹介と「Google でログインして申し込む」ボタン
 *      （2026-11-07 タケシの指示：ログインは Google だけ。パスワードはあずからない。メールアドレスは Google が確かめたものを使う）
 *   1. 受付ページ（Google でログインした人）：店・おすすめ商品・お店で撮った動画3本とその説明・ナレーションの声を入力してもらう
 *      Google でメールアドレスを確かめてあるので、「申し込む」でそのまま受付になる（2026-11-03〜11-06 の「申し込みを確定する」メールはやめた）
 *      体験版（前の無料版）は、1つの Google アカウントで1回だけ（2026-11-07）。送ってもらった動画（素材）は受付から30日で消す
 *   2. 確認ページ（お客さん用）：完成した動画を見て、ダウンロードしてもらう（有料版は、読み上げのひらがなを直して作り直しを頼める。1回まで）
 *      保存のボタンで、ページの中からそのままスマホのカメラロールへ保存してもらう（お客さんへのお礼・投稿文のメールは送らない）。ページは受付から24時間で使えなくする
 *   3. 決まったら、動画のダウンロードのリンクと、えらばれた SNS ごとの投稿文をメールで送る
 *      （2026-10-10 社長の指示：ALCOHOLIDAY のアカウントには投稿しない。お客さんが自分の SNS に投稿する。Upload-Post の自動投稿はやめた）
 *   4. KAYO（パソコン側の bar_sync.py）との受け渡し口（API）
 *
 * 置き方は「設置手順.md」を見る。最初に一度だけ setup() を実行する。
 */

const CONFIG = {
  OWNER_EMAIL: 'abetkc@alcoholiday.org',   // 新しい依頼・承認の知らせを受け取るメール
  MAIL_FROM: 'info@alcoholiday.org',          // お客さんに届くメールの送り主（2026-10-08 社長の指示。Gmail の「他のアドレスから送る」に登録が必要）
  TZ: 'Asia/Tokyo',
  // テスト中は、下のメールアドレスの人だけが申し込める（2026-10-08 社長の指示。公開するときは false にする）
  TEST_ONLY: true,
  TEST_EMAILS: ['abetkc@gmail.com', 'abetkc@alcoholiday.org',
    'k.yoshida.s.mentor@gmail.com'],   // 先生（ショート動画を見てもらう。2026-10-31 タケシの指示）
  // 体験版の回数の決まりを使わない人（ALCOHOLIDAY のテスト用。公開したあとも、何回でも試せるように）
  NO_LIMIT_EMAILS: ['abetkc@gmail.com', 'abetkc@alcoholiday.org', 'k.yoshida.s.mentor@gmail.com'],
  // 受付サイトを埋め込んだホームページのページ（2026-10-08）。メールのトップページへのリンクはここにする
  //   （Google のページを直接開くと「Google Apps Script のユーザーによって作成…」のお知らせが出るため）
  SITE_URL: 'https://www.alcoholiday.org/%E7%BE%8E%E5%91%B3%E3%81%97%E3%81%84%E3%82%82%E3%81%AE',
  // AWS（Amplify）に置いた受付ページの住所（2026-10-11）。例：'https://ad.alcoholiday.org/'
  //   空のあいだは今までどおり（メールのリンクは Google のページ・ホームページ）。入れると、メールのリンク（申し込みの確定・
  //   動画の確認ページ・もう一度申し込む）がこの住所になる。切り替えは、AWS の受付ページで試してから
  WEB_URL: 'https://ad.alcoholiday.org/',   // 2026-10-11 切り替え（社長の指示）
  MAKE_MINUTES: 20,          // 受付から動画確認のメールまでの目安（分）。受付のメールに書く（2026-10-09。2026-10-11 社長の指示で 15→20）
  APPROVE_DAYS: 1,           // 受付から何日以内に動画を決めてもらうか（過ぎたら期限切れ・お渡ししない。2026-10-10 社長の指示で 7→1）
  VIDEOS: [                  // お客さんに撮ってもらう動画（各5秒くらい）。この順につなぐ
    { key: 1, title: 'お店の雰囲気', hint: '入口・看板・カウンター・店内など', example: '例：恵比寿駅から歩いて3分。木のカウンターが落ち着く小さなお店です' },
    { key: 2, title: 'おすすめ商品', hint: 'いちばん売りたいもの。つくるところ・注ぐところ・グラスのアップなど', example: '例：岡山の白桃を丸ごと使ったベリーニ。秋だけの限定です' },
    { key: 3, title: '自由', hint: 'バーテンダー・乾杯・お店の自慢など', example: '例：マスターは銀座で20年。好みを伝えれば一杯つくってくれます' },
  ],
  MAX_VIDEO_MB: 25,          // 1本の大きさの上限（2026-10-07 社長の指示で150→25。5秒・1080p なら10MBくらい。大きいと受け取りに時間がかかる）
  MAX_VIDEO_SEC: 10,         // 1本の長さの上限（秒）。使うのは1本4〜5秒
  // 動画1本ごとの説明の欄は、2026-10-16 社長の指示でなくした（商品の説明1つから、声の案内・字幕・投稿文をつくる）
  // 2026-11-03 タケシの指示：会員登録（パスワード）をやめ、申し込みのたびにメールで確定してもらう
  //   → 2026-11-07 タケシの指示：Google でログインしてもらう形に変えた。確定のメールは送らない（前に「確認待ち」になった申し込みのためだけに残す）
  CONFIRM_HOURS: 24,         // 申し込みを確定するメールのリンクが使える時間。過ぎたら「未確定」にして、動画はつくらない
  // Google のログイン（2026-11-07）。Google Cloud の「OAuth クライアント ID」はスクリプト プロパティ GOOGLE_CLIENT_ID に入れる（設置手順.md の手順9）
  LOGIN_HOURS: 6,            // ログインしたままでいられる時間（Google の一時保管の上限が6時間）。過ぎたら、もう一度ログインしてもらう
  KEEP_SOURCE_DAYS: 30,      // 送ってもらった動画（素材）を残す日数。過ぎたら消す（できあがった動画は残す）
  MAX_FIX: 1,                // 動画の直しは何回までか（2026-10-04 社長の指示：1回だけ。直したあとは2本から選んで決める）
  PRODUCT_MAX: 40,           // 商品の名前の文字数の上限（動画の上に出すので短め）
  DESC_MAX: 300,             // 商品の説明の文字数の上限（2026-10-16 社長の指示で50→300。この説明から声の案内・字幕・投稿文をつくる）
  GUIDES: [                  // ナレーションの声（案内役。動画には出ず、声だけ担当）
    { key: 'A', name: 'ローズ', desc: '明るく親しみやすい声' },
    { key: 'B', name: 'ラフィ', desc: 'クールで大人っぽい声' },
    { key: 'C', name: 'アイラ', desc: 'ゆっくり落ち着いた声' },
    { key: 'D', name: 'アルビン', desc: '男性の声' },
  ],
  // 背景の音楽（2026-10-11 社長の指示：お客さんが申し込みページでえらぶ。曲は KAYO のパソコンの ALCOHOLIDAY/音声/backmusic）
  MUSICS: ['バンドサウンド', 'ボサノバ', 'ジャズ', 'ポップ', '音楽なし'],
  PLATFORMS: ['instagram', 'tiktok', 'x'],
  PLATFORM_NAMES: { instagram: 'Instagram', tiktok: 'TikTok', x: 'X' },
  // お客さんに送るメールの最後（署名の下）に必ず付ける（2026-10-10 社長の指示）
  MAIL_LINKS: 'ALCOHOLIDAY のサイト：https://www.alcoholiday.org/\n' +
    'Amazon のお店：https://www.amazon.co.jp/stores/ALCOHOLIDAY/page/F79A1788-B8AA-4248-973D-17D360788C0C',
  // 2026-11-07 タケシの指示：「無料版」は「体験版」に名前を変え、1つの Google アカウントで1回だけ。前の申し込みの「無料」も体験版として数える
  PLANS: ['体験', '有料'],   // 体験（前の無料）＝動画の上下に透かしのロゴ＋最後に締め画像と声／有料＝最後に小さくロゴ（2026-10-10 社長の指示。お支払いの仕組みはまだ）
};

const SHEET_NAME = '依頼';
const COLS = ['id', '会員ID', '受付日時', '状態', '店名', '担当者', 'メール', '電話', '都道府県', '住所', 'エリア', '営業時間',
  '店のSNS', '商品名', '商品の説明', '価格', '数量限定', '投稿日', '時間帯', '案内役', '要望', 'お客さんの投稿文', '素材動画', '動画の説明', '承認キー',
  '動画', '投稿文', '投稿日時', '承認日時', 'お客さんのコメント', '予約ID', '履歴',
  '前の動画', '前の投稿文',   // 直しのあと、お客さんが「直す前」を選べるように残す（2026-10-04 追加。台帳の右端に足される）
  'SNS',                     // 投稿文をつくる SNS（instagram,tiktok,x のように。2026-10-06 追加）
  'プラン', '音楽',
  '店名カナ',                // 店名の読み（ナレーションで使う。2026-10-31 タケシの指示）。前の段の「プラン」は 無料／有料（2026-10-10 追加。いまは受付で「体験」（2026-11-07 までは「無料」）。有料にするときは、制作の前に社長が台帳で「有料」に変える）
  'よみ', 'よみの直し',       // 有料版：読み上げの文のひらがな（動画1〜3）と、お客さんが直したひらがな（JSON の配列。2026-10-31 タケシの指示）
  '確定キー', '再申込キー'];  // メールの「申し込みを確定する」のリンクの合言葉と、「前回の内容でもう一度申し込む」のリンクの合言葉（2026-11-03）
// 「会員ID」「担当者」の列は、前の申し込みのために残す（2026-11-03 から会員登録はなく、担当者の名前も聞かない）
// 2026-10-31 タケシの指示：無料版は直しなし。有料版は、確認ページで読み上げをひらがなで見せ、お客さんが直した読み方で作り直す（1回まで）
const YOMI_RE = /^[ぁ-んァ-ヶー・、。！？!?「」 　0-9０-９]*$/;   // 読みの直しに使える文字（ひらがな・カタカナ・のばす音・句読点・数字・スペース）
const YOMI_MAX = 120;      // 1本の読みの文字数の上限
// 2026-11-03 タケシの指示で会員登録をやめた。台帳の「会員」シートは、もう読み書きしない（消してはいない）
// 受付ページの入力欄の名前 → 受付台帳の列（「前回の内容でもう一度申し込む」で最初から入れておくお店の情報）
const PROFILE = { shop: '店名', kana: '店名カナ', tel: '電話', pref: '都道府県', address: '住所', area: 'エリア', hours: '営業時間', sns: '店のSNS' };
// 店名のカナ：ひらがな・カタカナと、のばす音・スペース・中黒だけ（ナレーションでこの読み方にする。2026-10-31 タケシの指示）
const KANA_RE = /^[ぁ-んァ-ヶー・ 　]+$/;
const WAIT_STATE = '確認待ち';     // 申し込んだが、まだメールの「申し込みを確定する」を押していない
const UNSURE_STATE = '未確定';     // 確定しないまま CONFIRM_HOURS が過ぎた（動画はつくらない）
// 体験版の回数に数えない状態（確定していない・ALCOHOLIDAY が取り消した）
const NOT_COUNTED = [WAIT_STATE, UNSURE_STATE, 'キャンセル'];
// 素材を消してはいけない状態（つくっている・直している途中）
const BUSY_STATES = ['受付', '制作中', '修正依頼'];

/* ────────────────────────────── 最初に一度だけ ────────────────────────────── */

function setup() {
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('SHEET_ID')) {
    const ss = SpreadsheetApp.create('ALCOHOLIDAY BAR広告 受付台帳');
    const sh = ss.getSheets()[0];
    sh.setName(SHEET_NAME);
    sh.getRange(1, 1, sh.getMaxRows(), COLS.length).setNumberFormat('@');   // 日付や時刻を勝手に変換させない（文字のまま）
    sh.getRange(1, 1, 1, COLS.length).setValues([COLS]).setFontWeight('bold').setBackground('#f3e6c8');
    sh.setFrozenRows(1);
    props.setProperty('SHEET_ID', ss.getId());
  }
  if (!props.getProperty('FOLDER_ID')) {
    const root = DriveApp.createFolder('ALCOHOLIDAY BAR広告');
    root.createFolder('案件');
    root.createFolder('声見本');
    root.createFolder('送信中');
    props.setProperty('FOLDER_ID', root.getId());
  }
  if (!props.getProperty('API_KEY')) {
    props.setProperty('API_KEY', Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, ''));
  }
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'hourlyCheck') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('hourlyCheck').timeBased().everyHours(1).create();

  const ss = SpreadsheetApp.openById(props.getProperty('SHEET_ID'));
  Logger.log('受付台帳（スプレッドシート）: ' + ss.getUrl());
  Logger.log('Googleドライブのフォルダ: ' + DriveApp.getFolderById(props.getProperty('FOLDER_ID')).getUrl());
  Logger.log('API_KEY（パソコンの BAR_API_KEY に設定する）: ' + props.getProperty('API_KEY'));
}

/* ────────────────────────────── ページ ────────────────────────────── */

function doGet(e) {
  return pageTemplate_((e && e.parameter) || {}).evaluate()
    .setTitle(PAGE_TITLE)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

const PAGE_TITLE = 'ALCOHOLIDAY ショート動画作成';

/** 開くページを決めて、ひな形にデータを入れる（Google のページ・AWS の受付ページで共通） */
function pageTemplate_(p) {
  let t;
  if (p.p === 'review') {
    t = HtmlService.createTemplateFromFile('review');
    t.data = Object.assign(reviewData_(p.id, p.k), { logo: logo_() });
  } else if (p.p === 'confirm') {   // メールの「申し込みを確定する」のリンクから
    t = HtmlService.createTemplateFromFile('confirm');
    t.data = Object.assign(confirmData_(p.id, p.k), { logo: logo_() });
  } else if (p.p === 'form') {      // a：「前回の内容でもう一度申し込む」のリンクの合言葉
    t = HtmlService.createTemplateFromFile('form');
    t.data = formData_(p.a);
  } else {
    t = HtmlService.createTemplateFromFile('top');
    // 前の会員登録のころのメールのリンク（パスワードの再設定・ログアウト）から来た人への案内
    t.data = topData_(p.p === 'reset' || p.p === 'logout' ? '会員登録はなくなりました。そのままお申し込みいただけます。' : '');
  }
  return t;
}

/* ───── AWS（Amplify）に置いた受付ページからの呼び出し（2026-10-11） ─────
   受付ページ（web/index.html）は、ページの中身を GAS から受け取って表示し、ボタンの動きも GAS を呼んで行う。
   呼べるのは、Google のページで google.script.run から呼べるものと同じ関数だけ（PUBLIC_FNS） */
const PUBLIC_FNS = ['googleLogin', 'musicSample', 'formPage', 'checkLimit', 'confirmOrder', 'orderResult',
  'startUpload', 'uploadChunk', 'submitOrder', 'reviewVideo', 'videoFile', 'downloaded', 'requestChange', 'requestReading'];

/** 受付ページで表示する HTML（AWS の受付ページだと分かる印・画面の幅の設定・題名を足す） */
function webHtml_(html) {
  const head = '<meta name="viewport" content="width=device-width, initial-scale=1"><title>' + PAGE_TITLE + '</title>' +
    '<script>window.ALC_WEB = ' + JSON.stringify({ api: webAppUrl_() }) + ';</script>';
  return String(html).replace('<head>', '<head>' + head);
}

function publicApi_(req) {
  if (req.action === 'page') return webHtml_(pageTemplate_(req.params || {}).evaluate().getContent());
  const fn = String(req.fn || '');
  if (PUBLIC_FNS.indexOf(fn) < 0) throw new Error('知らない呼び出し: ' + fn);
  const res = globalThis[fn].apply(null, Array.isArray(req.args) ? req.args : []);
  return fn === 'formPage' ? webHtml_(res) : res;
}

/** ページの中に別の HTML ファイル（css・common）を入れる */
function include_(name) { return HtmlService.createHtmlOutputFromFile(name).getContent(); }
function logo_() { return include_('logo'); }

function topData_(msg) {
  return { logo: logo_(), msg: msg, testOnly: CONFIG.TEST_ONLY, formUrl: pageUrl_() + '?p=form',
    clientId: prop_('GOOGLE_CLIENT_ID') || '' };
}

/* ───── Google でログイン（2026-11-07 タケシの指示：ログインは Google だけ） ─────
   ページの「Google でログイン」で Google が渡す身分証（ID トークン）を、Google に問い合わせて本物か確かめる。
   本物なら、合言葉（session）をつくって LOGIN_HOURS のあいだ覚えておく。パスワードや Google のトークンは残さない */
function googleLogin(credential) {
  const clientId = prop_('GOOGLE_CLIENT_ID');
  if (!clientId) throw new Error('ただいま準備中です（Google のログインの設定がまだです）');
  if (!/^[\w.-]{20,4096}$/.test(String(credential || ''))) throw new Error('Google のログインがうまくいきませんでした。もう一度お試しください');
  const res = UrlFetchApp.fetch('https://oauth2.googleapis.com/tokeninfo?id_token=' + encodeURIComponent(credential), { muteHttpExceptions: true });
  const t = res.getResponseCode() === 200 ? JSON.parse(res.getContentText()) : {};
  const ok = t.aud === clientId && (t.iss === 'accounts.google.com' || t.iss === 'https://accounts.google.com') &&
    String(t.email_verified) === 'true' && Number(t.exp) * 1000 > Date.now() && EMAIL_RE.test(String(t.email || ''));
  if (!ok) throw new Error('Google のログインがうまくいきませんでした。もう一度お試しください');
  const email = String(t.email).trim().toLowerCase();
  if (!testOk_(email)) throw new Error(TEST_NG);
  const session = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
  CacheService.getScriptCache().put('login-' + session, email, CONFIG.LOGIN_HOURS * 3600);
  return { session: session, email: email, until: Date.now() + CONFIG.LOGIN_HOURS * 3600000 - 600000 };   // until：ページがログインを覚えておく期限（少し早めに切る）
}

/** ログインした人のメールアドレス（ログインしていない・期限が過ぎたときは断る） */
function loginEmail_(session) {
  const email = /^[0-9a-f]{64}$/.test(String(session || '')) ? CacheService.getScriptCache().get('login-' + session) : null;
  if (!email) throw new Error(LOGIN_NG);
  return email;
}
const LOGIN_NG = 'ログインの期限が切れました。もう一度「Google でログイン」を押してください（入力した内容は消えません）';

/** テスト中は、決めた人だけ通す */
function testOk_(email) {
  return !CONFIG.TEST_ONLY || CONFIG.TEST_EMAILS.indexOf(String(email || '').trim().toLowerCase()) >= 0;
}
const TEST_NG = 'ただいま準備中です。公開まで、もうしばらくお待ちください。';

/** 申し込みのページのデータ。again（「前回の内容でもう一度申し込む」の合言葉）があれば、前回のお店の情報を最初から入れておく */
function formData_(again) {
  const prefill = {};
  const r = /^[0-9a-f]{32}$/.test(String(again || '')) ? findBy_('再申込キー', again) : null;
  if (r) {
    Object.keys(PROFILE).forEach(k => { prefill[k] = r.rec[PROFILE[k]]; });
    prefill.email = r.rec['メール'];
  }
  return {
    prefill: prefill, topUrl: pageUrl_(), clientId: prop_('GOOGLE_CLIENT_ID') || '', confirmHours: CONFIG.CONFIRM_HOURS,
    keepDays: CONFIG.KEEP_SOURCE_DAYS,
    platforms: CONFIG.PLATFORMS.map(p => ({ key: p, name: CONFIG.PLATFORM_NAMES[p] })),
    musics: CONFIG.MUSICS,
    guides: (s => CONFIG.GUIDES.map(g => Object.assign({ sample: s[g.key] || '' }, g)))(voiceSamples()),   // 声の見本（フォルダを1回だけ見る）
    videos: CONFIG.VIDEOS,
    maxVideoMb: CONFIG.MAX_VIDEO_MB,
    maxVideoSec: CONFIG.MAX_VIDEO_SEC,
    productMax: CONFIG.PRODUCT_MAX,
    descMax: CONFIG.DESC_MAX,
    approveDays: CONFIG.APPROVE_DAYS,
    logo: logo_(),
  };
}

/** メールに書くトップページの URL（ホームページに埋め込んだページ） */
function siteUrl_() { return CONFIG.WEB_URL || CONFIG.SITE_URL || webAppUrl_(); }

/** お客さんに見せるページの住所（AWS の受付ページがあればそちら。なければ Google のページ） */
function pageUrl_() { return CONFIG.WEB_URL || webAppUrl_(); }

function webAppUrl_() {
  return PropertiesService.getScriptProperties().getProperty('WEB_APP_URL') || ScriptApp.getService().getUrl();
}

/** 声の見本（ドライブの「声見本」フォルダの A.mp3 など）をページに埋め込む。受付ページの「▶ 声を聞く」で流す */
// 申し込みのページの「▶ 声を聞く」の見本（A〜D をまとめて渡す）
function voiceSamples() {
  const out = {};
  try {
    const it = voiceFolder_().getFiles();
    while (it.hasNext()) {
      const f = it.next(), key = f.getName().split('.')[0].toUpperCase();
      if (CONFIG.GUIDES.some(g => g.key === key)) out[key] = 'data:audio/mpeg;base64,' + Utilities.base64Encode(f.getBlob().getBytes());
    }
  } catch (err) { /* 見本がまだ無いときは「声を聞く」を出さない */ }
  return out;
}

/** 背景の音楽の見本（「声見本」フォルダの 音楽_ジャズ.mp3 など。12秒ほど）。「▶ 聞く」を押したときだけ受け取る（2026-10-11）
 *  見本は KAYO が tools/music_samples.py で置く */
function musicSample(name) {
  if (CONFIG.MUSICS.indexOf(name) < 0) throw new Error('音楽の名前が違います');
  const it = voiceFolder_().getFilesByName('音楽_' + name + '.mp3');
  return it.hasNext() ? 'data:audio/mpeg;base64,' + Utilities.base64Encode(it.next().getBlob().getBytes()) : '';
}

function voiceSample_(key) {
  try {
    const it = voiceFolder_().getFiles();
    while (it.hasNext()) {
      const f = it.next();
      if (f.getName().split('.')[0].toUpperCase() === key) {
        return 'data:audio/mpeg;base64,' + Utilities.base64Encode(f.getBlob().getBytes());
      }
    }
  } catch (err) { /* 見本がまだ無いときは「声を聞く」を出さない */ }
  return '';
}

/* ──────────────────── 申し込みの確定・体験版の回数 ──────────────────── */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** 申し込みを受け付けたかどうか（返事がスマホに届かなかったときに、スマホから確かめる。2026-10-08） */
function orderResult(upload) {
  if (!/^[\w-]{8,}$/.test(String(upload || ''))) return null;
  const v = CacheService.getScriptCache().get('order-' + upload);
  return v ? JSON.parse(v) : null;
}

/** トップページの「申し込む」：申し込みのページに入れ替えるために、ページの中身を渡す
 *  （Google のページは、ボタンを押さないと別のページへ移れないため） */
function formPage(again) {
  const t = HtmlService.createTemplateFromFile('form');
  t.data = formData_(again);
  return t.evaluate().getContent();
}

/** 体験版かどうか（前の申し込みの「無料」と、空も体験版） */
function isTrial_(plan) { return plan !== '有料'; }
/** お客さんに見せるプランの名前（体験版・有料版） */
function planLabel_(plan) { return isTrial_(plan) ? '体験版' : '有料版'; }

/** 体験版の回数の決まり（2026-11-07 タケシの指示：1つの Google アカウント（メールアドレス）で1回だけ）。
 *  もう使ったときは true。exceptId：その申し込み自身は数えない */
function trialUsed_(f, exceptId) {
  if (!isTrial_(f.plan)) return false;
  const email = String(f.email || '').trim().toLowerCase();
  if (CONFIG.NO_LIMIT_EMAILS.indexOf(email) >= 0) return false;
  return rows_().some(r => r.id !== exceptId && isTrial_(r['プラン']) && NOT_COUNTED.indexOf(r['状態']) < 0 &&
    String(r['メール']).trim().toLowerCase() === email);
}
const TRIAL_NG = '体験版は、1つの Google アカウントで1回までです。この Google アカウントでは、もう体験版をお使いいただいています。\n' +
  '2回目からは、有料版でお申し込みください。';

/** 申し込みのページ：動画を送り始める前に、申し込めるかを確かめる（送ってから断られないように） */
function checkLimit(f) {
  f = f || {};
  const email = loginEmail_(f.session);   // メールアドレスは、Google でログインしたもの（2026-11-07）
  if (!testOk_(email)) throw new Error(TEST_NG);
  if (trialUsed_(Object.assign({}, f, { email: email }), '')) throw new Error(TRIAL_NG);
  return 'ok';
}

/** メールの「申し込みを確定する」のページのデータ */
function confirmData_(id, k) {
  const r = findRow_(id);
  if (!r || !k || r.rec['確定キー'] !== k) return { error: 'ページが見つかりません。メールのリンクをもう一度開いてください。' };
  const rec = r.rec;
  return {
    id: rec.id, key: k, state: rec['状態'], shop: rec['店名'], product: rec['商品名'], plan: planLabel_(rec['プラン']),
    when: snsLabel_(snsOf_(rec)), email: rec['メール'], waiting: rec['状態'] === WAIT_STATE && !confirmClosed_(rec),
    deadline: jaTime_(confirmDeadline_(rec)), makeMinutes: CONFIG.MAKE_MINUTES, approveDays: CONFIG.APPROVE_DAYS,
  };
}

function confirmDeadline_(rec) { return new Date(parseTime_(rec['受付日時']).getTime() + CONFIG.CONFIRM_HOURS * 3600000); }
function confirmClosed_(rec) { return new Date() >= confirmDeadline_(rec); }

/** 確定のページの「申し込みを確定する」：ここで「受付」になり、パソコン（bar_auto.py）が動画をつくり始める */
function confirmOrder(id, k) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const r = findRow_(id);
    if (!r || !k || r.rec['確定キー'] !== k) throw new Error('ページが見つかりません。メールのリンクをもう一度開いてください。');
    const rec = r.rec;
    if (rec['状態'] !== WAIT_STATE && rec['状態'] !== UNSURE_STATE) return { id: rec.id, already: true };   // もう確定している（2回押した）
    if (rec['状態'] === UNSURE_STATE || confirmClosed_(rec)) {
      throw new Error('確定の期限（' + jaTime_(confirmDeadline_(rec)) + '）が過ぎました。お手数ですが、もう一度お申し込みください。');
    }
    if (trialUsed_({ plan: rec['プラン'], email: rec['メール'] }, rec.id)) throw new Error(TRIAL_NG);
    // 受付日時は、確定した時にする（動画のお渡しの期限は、ここから数える）
    const now = new Date();
    update_(r.row, { '状態': '受付', '受付日時': fmt_(now) }, 'お客さんがメールで申し込みを確定した');
    acceptedMails_(findRow_(id).rec, 'お客さんがメールで確定しました');
    return { id: id, already: false };
  } finally {
    lock.releaseLock();
  }
}

/** 受け付けたときのメール（お客さんへ「受け付けました」・社長へ「新しい依頼」）。how：どうやって受け付けたか（社長へのメールに書く） */
function acceptedMails_(done, how) {
  const snsText = snsLabel_(snsOf_(done));
  mail_(done['メール'], '【ALCOHOLIDAY】ショート動画のお申し込みを受け付けました（' + done.id + '）',
    done['店名'] + '\n' + dear_(done) + '\n\n' +
    '以下の内容で受け付けました。\n\n' +
    '受付番号：' + done.id + '\nプラン：' + planLabel_(done['プラン']) + '\n背景の音楽：' + done['音楽'] + '\n投稿文をつくる SNS：' + snsText + '\nおすすめ商品：' + done['商品名'] + '\n\n' +
    '■ このあとの流れ\n' +
    '1. ALCOHOLIDAY が動画をつくります\n' +
    '2. 動画ができたら、確認用ページのリンクをメールでお送りします（約' + CONFIG.MAKE_MINUTES + '分後。混み合っているときは、遅れることがあります）\n' +
    '3. 確認ページで動画を見て、ダウンロードしてください（受付から24時間以内）\n' +
    '4. ' + snsText + ' ごとの投稿文は、確認ページでコピーできます\n' +
    '5. お店の SNS アカウントから、ご自身で投稿してください\n\n' +
    '※ 送っていただいた動画（素材）は、受付から' + CONFIG.KEEP_SOURCE_DAYS + '日で消します。\n' +
    '※ お問い合わせは、受付番号を書いて、このメールにご返信ください。\n\n' +
    'ALCOHOLIDAY（アルコホリディ）');
  mail_(CONFIG.OWNER_EMAIL, '【BAR広告】新しい依頼 ' + done.id + ' ' + done['店名'],
    '新しい依頼が届きました（' + how + '）。\n\n店名：' + done['店名'] + '（' + done['都道府県'] + done['住所'] + '）\n' +
    '商品：' + done['商品名'] + '\n投稿文：' + snsText + '\nプラン：' + planLabel_(done['プラン']) + '\n音楽：' + done['音楽'] + '\n声：' + guideName_(done['案内役']) + '\n\n' +
    'Claude Code に「KAYO、BAR広告の新しい依頼を確認して」と話しかけてください。\n' +
    '受付台帳：' + SpreadsheetApp.openById(prop_('SHEET_ID')).getUrl());
}

/** 台帳の日時（2026-11-03 16:50）を日付にする */
function parseTime_(s) { return new Date(String(s).replace(' ', 'T') + ':00+09:00'); }

/* ────────────────────────────── 受付 ────────────────────────────── */

/** 依頼の投稿文をつくる SNS（古い依頼で空なら、3つとも） */
function snsOf_(rec) {
  const list = String(rec['SNS'] || '').split(/[,、\s]+/).filter(p => CONFIG.PLATFORMS.indexOf(p) >= 0);
  return list.length ? list : CONFIG.PLATFORMS.slice();
}

/** SNS の名前を「Instagram・TikTok」のようにつなぐ */
function snsLabel_(list) {
  return list.map(p => CONFIG.PLATFORM_NAMES[p] || p).join('・');
}

/** 受付ページの「申し込む」 */
function submitOrder(f) {
  // 受け付けたのに、返事がスマホに届かなかった（電波・画面が消えた）あとでもう一度押されたときは、同じ受付の返事を返す（2重に受け付けない）
  const done = orderResult(f.upload);
  if (done) return done;
  f.email = loginEmail_(f.session);   // メールアドレスは、Google でログインしたもの（入力欄はない。2026-11-07）
  const need = { shop: '店名', kana: '店名のカナ', tel: '電話番号', pref: '都道府県',
    address: '住所', product: 'おすすめ商品の名前', desc: '商品の説明' };   // お店の SNS か Google マップは、なくてもよい（2026-11-03）
  Object.keys(need).forEach(k => {
    if (!f[k] || !String(f[k]).trim()) throw new Error(need[k] + 'を入力してください');
  });
  if (!testOk_(f.email)) throw new Error(TEST_NG);
  if (!KANA_RE.test(String(f.kana).trim())) throw new Error('店名のカナは、ひらがなかカタカナで入力してください');
  const vids = f.videos || [];
  if (vids.length !== CONFIG.VIDEOS.length) throw new Error('動画を' + CONFIG.VIDEOS.length + '本えらんでください');
  vids.forEach((v, i) => {
    if (Number(v.size) > CONFIG.MAX_VIDEO_MB * 1024 * 1024) throw new Error('動画' + (i + 1) + 'が大きすぎます。' + CONFIG.MAX_VIDEO_MB + 'MB までの短い動画（5秒くらい）にしてください');
    if (Number(v.sec) > CONFIG.MAX_VIDEO_SEC + 0.5) throw new Error('動画' + (i + 1) + 'が長すぎます。' + CONFIG.MAX_VIDEO_SEC + '秒までの短い動画（5秒くらい）にしてください');
  });
  const upFolder = uploadFolder_(f.upload);
  const parts = {};
  const it = upFolder.getFiles();
  while (it.hasNext()) { const m = /^v(\d)\.part\d+$/.exec(it.next().getName()); if (m) parts[m[1]] = (parts[m[1]] || 0) + 1; }
  vids.forEach((v, i) => {
    if ((parts[i + 1] || 0) !== Number(v.parts)) throw new Error('動画' + (i + 1) + 'が最後まで届いていません。もう一度「申し込む」を押してください');
  });
  if (!f.agree) throw new Error('注意事項への同意が必要です');
  const platforms = CONFIG.PLATFORMS.slice();   // どの申し込みにも3つとも投稿文をつくる（2026-11-03 タケシの指示。SNS をえらぶ欄はなくした）
  const guide = CONFIG.GUIDES.filter(g => g.key === f.guide)[0];
  if (CONFIG.MUSICS.indexOf(f.music) < 0) throw new Error('背景の音楽をえらんでください');

  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const plan = CONFIG.PLANS.indexOf(f.plan) >= 0 ? f.plan : '体験';
    if (trialUsed_({ plan: plan, email: f.email }, '')) throw new Error(TRIAL_NG);
    const now = new Date();
    const id = newId_(now);
    const folder = upFolder;   // 送ってもらった動画のフォルダを、そのまま案件のフォルダにする
    folder.moveTo(caseFolder_());
    folder.setName(id + ' ' + clip_(f.shop, 40));
    const videoInfo = vids.map((v, i) => ({
      no: i + 1, title: CONFIG.VIDEOS[i].title, desc: clip_(v.desc || '', 300), name: clip_(v.name, 120),
      type: clip_(v.type, 40), size: Number(v.size) || 0, sec: Math.round((Number(v.sec) || 0) * 10) / 10, parts: Number(v.parts),
    }));
    const key = Utilities.getUuid().replace(/-/g, '').slice(0, 20);
    const rec = {
      'id': id, '受付日時': fmt_(now), '状態': '受付',   // Google でメールアドレスを確かめてあるので、そのまま受付（パソコンが動画をつくり始める。2026-11-07）
      '店名': clip_(f.shop, 80), '店名カナ': clip_(f.kana, 80), 'メール': clip_(f.email, 120),
      '電話': clip_(f.tel, 30), '都道府県': clip_(f.pref, 10), '住所': clip_(f.address, 120), 'エリア': clip_(f.area, 80),
      '営業時間': clip_(f.hours, 80), '店のSNS': clip_(f.sns, 200), '商品名': clip_(f.product, CONFIG.PRODUCT_MAX),
      '商品の説明': clip_(f.desc, CONFIG.DESC_MAX), '価格': clip_(f.price, 40), '数量限定': f.limited ? 'はい' : '', 'SNS': platforms.join(','),
      '案内役': guide ? guide.key : 'おまかせ', '音楽': f.music,   // 2026-10-11 から「ご要望」の欄はない（列は前の申し込みのために残す）
      // 投稿文は、商品の説明をもとに KAYO が自動でつくる（2026-10-10 から申し込みページに入力欄はない）
      '素材動画': folder.getId(), '動画の説明': JSON.stringify(videoInfo), '承認キー': key,
      'プラン': plan,   // 申し込みページでえらぶ（2026-10-11〜。お支払いの仕組みはまだない）
      '再申込キー': Utilities.getUuid().replace(/-/g, ''),
      '履歴': fmt_(now) + ' 申し込み（Google でログイン）',
    };
    const sh = sheet_();
    ensureCols_(sh);
    sh.getRange(sh.getLastRow() + 1, 1, 1, COLS.length).setNumberFormat('@')
      .setValues([COLS.map(c => rec[c] === undefined ? '' : rec[c])]);

    acceptedMails_(findRow_(id).rec, 'Google でログインして申し込み');
    const res = { id: id, when: snsLabel_(platforms), plan: planLabel_(rec['プラン']), email: rec['メール'] };   // when の例：Instagram・TikTok・X
    if (f.upload) CacheService.getScriptCache().put('order-' + f.upload, JSON.stringify(res), 21600);   // 6時間おぼえておく
    return res;
  } finally {
    lock.releaseLock();
  }
}

function newId_(now) {
  // 受付番号は ALC-日付-連番（2026-10-10 社長の指示で BAR- から変更。前の案件は BAR- のまま）
  const base = 'ALC-' + Utilities.formatDate(now, CONFIG.TZ, 'yyyyMMdd') + '-';
  const used = rows_().filter(r => String(r.id).indexOf(base) === 0).length;
  return base + ('0' + (used + 1)).slice(-2);
}

/** メールのあて名（担当者の名前がなければ「ご担当者様」） */
function dear_(rec) { return (rec['担当者'] ? rec['担当者'] : 'ご担当者') + ' 様'; }

function guideName_(key) {
  const g = CONFIG.GUIDES.filter(x => x.key === key)[0];
  return g ? g.name + '（' + g.key + '）' : 'おまかせ';
}

/* 動画の受け取り：大きい動画を少しずつ（約4MBずつ）送ってもらい、「送信中」フォルダにためる。
   つなぎ合わせはパソコン（bar_sync.py pull）で行う（Google の1ファイル50MBの制限を避けるため） */

/** 受付ページ：送り始める前に呼ぶ（session：Google でログインした合言葉）。送信用の合言葉（フォルダ名）を返す */
function startUpload(session) {
  loginEmail_(session);   // ログインした人だけ送れる（2026-11-07）
  const token = 'up-' + Utilities.getUuid().replace(/-/g, '');
  uploadRoot_().createFolder(token);
  return token;
}

/** 受付ページ：動画のひとかけらを受け取る（vi＝何本目 1〜3、part＝何番目のかけら） */
function uploadChunk(token, vi, part, b64) {
  vi = Number(vi); part = Number(part);
  if (!(vi >= 1 && vi <= CONFIG.VIDEOS.length) || !(part >= 0 && part < Math.ceil(CONFIG.MAX_VIDEO_MB / 4) + 2)) throw new Error('送り方が正しくありません');
  const folder = uploadFolder_(token);
  const name = 'v' + vi + '.part' + ('00' + part).slice(-3);
  const old = folder.getFilesByName(name);
  while (old.hasNext()) old.next().setName('old_' + name);   // 送り直しのとき（消さずに名前を変える）
  folder.createFile(Utilities.newBlob(Utilities.base64Decode(b64), 'application/octet-stream', name));
  return part;
}

function uploadRoot_() {
  const root = DriveApp.getFolderById(prop_('FOLDER_ID'));
  const it = root.getFoldersByName('送信中');
  return it.hasNext() ? it.next() : root.createFolder('送信中');
}

function uploadFolder_(token) {
  if (!/^up-[0-9a-f]{32}$/.test(String(token))) throw new Error('送信の合言葉が正しくありません。ページを開き直してください');
  const it = uploadRoot_().getFoldersByName(token);
  if (!it.hasNext()) throw new Error('送信した動画が見つかりません。ページを開き直してください');
  return it.next();
}

/* ────────────────────────────── 確認（動画を決める） ────────────────────────────── */

const DONE_STATE = 'お渡し済み';   // お客さんが確認ページで動画をダウンロードしたあと（2026-10-10 社長の指示。「この動画に決める」ボタンはやめた）
const END_STATE = '公開終了';      // お渡し済みのあと、期限（受付から24時間）が来て、ページとダウンロードのリンクを止めた

/** 動画をダウンロードするリンク（deliver のときに「リンクを知っている人は見られる」にしてある） */
function downloadUrl_(fileId) { return 'https://drive.google.com/uc?export=download&id=' + fileId; }

/** えらばれた SNS ごとの投稿文を、メールに入れる形にする */
function captionsText_(rec) {
  const cap = parseCaptions_(rec['投稿文']);
  return snsOf_(rec).filter(p => cap[p]).map(p => '━━ ' + CONFIG.PLATFORM_NAMES[p] + ' の投稿文 ━━\n' + cap[p]).join('\n\n');
}

function reviewData_(id, k) {
  const r = findRow_(id);
  if (!r || !k || r.rec['承認キー'] !== k) return { error: 'ページが見つかりません。メールのリンクをもう一度開いてください。' };
  const rec = r.rec;
  // 確認ページは期限（受付から24時間）を過ぎたら見られなくする（2026-10-10 社長の指示。動画のファイルは消さない）
  if (pageClosed_(rec)) return { error: 'このページの公開期間（' + jaTime_(approveDeadline_(rec)) + ' まで）は終わりました。ご用の方は、メールにご返信ください。' };
  const captions = parseCaptions_(rec['投稿文']);
  const yomi = yomiOf_(rec);
  return {
    id: rec.id, key: k, state: rec['状態'], shop: rec['店名'], product: rec['商品名'],
    when: snsLabel_(snsOf_(rec)), plan: rec['プラン'] || '無料', yomi: yomi, yomiMax: YOMI_MAX,
    // 動画をダウンロードできるのは、お客さんが見ている動画があるときだけ（直しを待っているあいだは出さない）。直したあとは2本とも
    download: rec['動画'] && canDownload_(rec) ? downloadUrl_(rec['動画']) : '',
    prevDownload: rec['前の動画'] && canDownload_(rec) ? downloadUrl_(rec['前の動画']) : '',
    videoId: rec['動画'], captions: captions, comment: rec['お客さんのコメント'],
    deadline: jaTime_(approveDeadline_(rec)), canAct: rec['状態'] === '承認待ち' && new Date() < approveDeadline_(rec),
    canFix: canFix_(rec) && yomi.length > 0,   // 有料版で、読み上げのひらがながあるときだけ
    prev:rec['前の動画'] ? { videoId: rec['前の動画'], captions: parseCaptions_(rec['前の投稿文']) } : null,
  };
}

function parseCaptions_(t) {
  let cap;
  try { cap = JSON.parse(t || '{}'); } catch (err) { cap = { instagram: t }; }
  // 前につくった投稿文の「提供：アルコホリディ」も、見せるときは「動画制作：」にする（2026-11-07 タケシの指示）
  Object.keys(cap).forEach(k => { if (typeof cap[k] === 'string') cap[k] = cap[k].replace(/提供：アルコホリディ/g, '動画制作：アルコホリディ'); });
  return cap;
}

// これまでに直しを頼まれた回数（履歴から数える）
function fixCount_(rec) {
  return (String(rec['履歴'] || '').match(/お客さんが修正を依頼/g) || []).length;
}

// 直しを頼めるか：有料版で、まだ1回も直していないとき（無料版は直しなし。2026-10-31 タケシの指示）
function canFix_(rec) { return rec['プラン'] === '有料' && fixCount_(rec) < CONFIG.MAX_FIX; }

// 読み上げのひらがな（動画1〜3）。ないとき（無料版・前の申し込み）は空
function yomiOf_(rec) {
  try { const a = JSON.parse(rec['よみ'] || '[]'); return Array.isArray(a) ? a.map(String) : []; } catch (err) { return []; }
}

// ダウンロードの期限（確認ページとリンクが使える期限）：受付から APPROVE_DAYS 日（24時間）
function approveDeadline_(rec) {
  return new Date(new Date(String(rec['受付日時']).replace(' ', 'T') + ':00+09:00').getTime() + CONFIG.APPROVE_DAYS * 86400000);
}

// 確認ページを閉じたか（受付から24時間。2026-10-10 社長の指示）
function pageClosed_(rec) { return new Date() >= approveDeadline_(rec); }

function canDownload_(rec) { return (rec['状態'] === '承認待ち' || rec['状態'] === DONE_STATE) && !pageClosed_(rec); }

/** 確認ページの「カメラロールに保存」：本番の動画をページに渡す（2026-10-10 社長の指示：別のページを開かず、その場で保存する）
 *  which：new＝いまの動画／prev＝直す前の動画 */
function videoFile(id, k, which) {
  const r = findRow_(id);
  if (!r || !k || r.rec['承認キー'] !== k) throw new Error('ページが見つかりません');
  if (!canDownload_(r.rec)) throw new Error(pageClosed_(r.rec) ? 'このページの公開期間は終わりました' : 'いまは保存できません（' + r.rec['状態'] + '）');
  const vid = which === 'prev' ? r.rec['前の動画'] : r.rec['動画'];
  if (!vid) throw new Error('動画が見つかりません');
  const file = DriveApp.getFileById(vid);
  if (file.getSize() > 35 * 1024 * 1024) throw new Error('動画が大きすぎて、このページでは保存できません。ALCOHOLIDAY へご連絡ください');
  return Utilities.base64Encode(file.getBlob().getBytes());
}

/** 確認ページで動画が保存されたとき（2026-10-10 社長の指示）
 *  はじめの1回だけ「お渡し済み」にする。お客さんへのお礼・投稿文のメールは送らない（2026-10-10 社長の指示で取りやめ）。社長には知らせる
 *  which：new＝いまの動画／prev＝直す前の動画（直したあとに、直す前のほうを保存したとき） */
function downloaded(id, k, which) {
  const r = findRow_(id);
  if (!r || !k || r.rec['承認キー'] !== k) throw new Error('ページが見つかりません');
  if (pageClosed_(r.rec)) throw new Error('このページの公開期間は終わりました');
  const until = jaTime_(approveDeadline_(r.rec));
  if (r.rec['状態'] === DONE_STATE) return { until: until, first: false };
  if (r.rec['状態'] !== '承認待ち') throw new Error('いまは保存できません（' + r.rec['状態'] + '）');
  if (which === 'prev' && r.rec['前の動画']) {   // 保存したほうを、お渡しした動画として台帳に残す
    update_(r.row, { '動画': r.rec['前の動画'], '投稿文': r.rec['前の投稿文'], '前の動画': r.rec['動画'], '前の投稿文': r.rec['投稿文'] },
      'お客さんが「直す前」の動画を保存した');
  }
  update_(r.row, { '状態': DONE_STATE, '承認日時': fmt_(new Date()) }, 'お客さんが動画を保存した');
  const rec = findRow_(id).rec;
  mail_(CONFIG.OWNER_EMAIL, '【BAR広告】動画が保存されました ' + id + ' ' + rec['店名'],
    rec['店名'] + ' が確認ページで動画を保存しました（お客さんへのメールはなし）。\nプラン：' + planLabel_(rec['プラン']) + '\n確認ページは ' + until + ' で止めます。');
  return { until: until, first: true };
}

/** 確認ページの「直してほしい」 */
// 確認ページの動画を、ページの中で直接再生するために渡す（スマホは Google ドライブの再生画面だとログインを求められたり再生できないことがあるため）
//   KAYO が届けた「確認用（小さい動画）」があればそれを、なければ本番の動画を渡す
function reviewVideo(id, k, which) {
  const r = findRow_(id);
  const vid = which === 'prev' ? r && r.rec['前の動画'] : r && r.rec['動画'];
  if (!r || !k || r.rec['承認キー'] !== k || !vid) throw new Error('動画が見つかりません');
  if (pageClosed_(r.rec)) throw new Error('このページの公開期間は終わりました');
  const main = DriveApp.getFileById(vid);
  let file = main;
  const it = DriveApp.getFolderById(r.rec['素材動画']).getFilesByName('確認用_' + main.getName());
  if (it.hasNext()) file = it.next();
  if (file.getSize() > 20 * 1024 * 1024) throw new Error('動画が大きすぎて、このページでは再生できません');
  return Utilities.base64Encode(file.getBlob().getBytes());
}

/** 確認ページ（有料版）の「この読み方で直しをお願いする」：お客さんが直したひらがな（動画1〜3）を受け取る（2026-10-31 タケシの指示）
 *  KAYO（bar_auto.py）が、変わった動画だけ、このひらがなで読み直して作り直す */
function requestReading(id, k, list) {
  const r = checkReview_(id, k);
  if (r.rec['プラン'] !== '有料') throw new Error('体験版は、動画の直しはできません');
  if (!canFix_(r.rec)) throw new Error('読み上げの直しは1回までです。2本のうち、よいほうを保存してください');
  const old = yomiOf_(r.rec);
  if (!Array.isArray(list) || list.length !== old.length) throw new Error('読み方の数が合いません。ページを開き直してください');
  const yomi = list.map((s, i) => {
    s = String(s || '').replace(/\s+/g, ' ').trim();
    if (!s) throw new Error('動画' + (i + 1) + 'の読み方が空です');
    if (s.length > YOMI_MAX) throw new Error('動画' + (i + 1) + 'の読み方が長すぎます（' + YOMI_MAX + '文字まで）');
    if (!YOMI_RE.test(s)) throw new Error('動画' + (i + 1) + 'の読み方は、ひらがなで書いてください（漢字・英字は使えません）');
    return s;
  });
  const changed = yomi.map((s, i) => s !== old[i].replace(/\s+/g, ' ').trim() ? '動画' + (i + 1) + '「' + old[i] + '」→「' + s + '」' : '').filter(Boolean);
  if (!changed.length) throw new Error('読み方が変わっていません。直したいところを書きかえてから押してください');
  const comment = '読み方の直し：' + changed.join('／');
  update_(r.row, { '状態': '修正依頼', 'よみの直し': JSON.stringify(yomi), 'お客さんのコメント': clip_(comment, 1000) }, 'お客さんが修正を依頼（読み方）');
  mail_(CONFIG.OWNER_EMAIL, '【BAR広告】読み方の直しの依頼 ' + id + ' ' + r.rec['店名'],
    'お客さんから読み上げの読み方の直しが届きました。自動で作り直します。\n\n' + changed.join('\n'));
  return '受け付けました。直した動画ができたら、またメールでお知らせします。';
}

function requestChange(id, k, comment) {
  if (!comment || !String(comment).trim()) throw new Error('直してほしいところを書いてください');
  const r = checkReview_(id, k);
  if (r.rec['プラン'] !== '有料') throw new Error('体験版は、動画の直しはできません');
  if (fixCount_(r.rec) >= CONFIG.MAX_FIX) throw new Error('動画の直しは1回までです。2本のうち、よいほうをダウンロードしてください');
  update_(r.row, { '状態': '修正依頼', 'お客さんのコメント': clip_(comment, 1000) }, 'お客さんが修正を依頼');
  mail_(CONFIG.OWNER_EMAIL, '【BAR広告】修正の依頼 ' + id + ' ' + r.rec['店名'],
    'お客さんから修正の依頼が届きました。\n\n' + comment + '\n\nClaude Code に「KAYO、BAR広告の修正依頼を確認して」と話しかけてください。');
  return '受け付けました。直した動画ができたら、またメールでお知らせします。';
}

function checkReview_(id, k) {
  const r = findRow_(id);
  if (!r || r.rec['承認キー'] !== k) throw new Error('ページが見つかりません');
  if (r.rec['状態'] !== '承認待ち') throw new Error('この動画はいま直しをお願いできる状態ではありません（' + r.rec['状態'] + '）');
  if (new Date() >= approveDeadline_(r.rec)) throw new Error('期限を過ぎました。ALCOHOLIDAY へご連絡ください');
  return r;
}

/* ────────────────────────────── 1時間ごとの見回り ────────────────────────────── */

// 2026-10-10 から自動投稿（Upload-Post）はしない。見回りは、期限（受付から24時間）が来た依頼の後かたづけだけ
//   ・ダウンロードのリンクを止める（動画のファイルの共有を「自分だけ」に戻す。ファイルは消さない）
//   ・ダウンロードしなかった依頼は「期限切れ」にして、お客さんに知らせる。ダウンロード済みは「公開終了」にする
function hourlyCheck() {
  const now = new Date();
  remindOwner_(now);
  removeOldUploads_(now);
  rows_().forEach((rec, i) => {
    const row = i + 2;
    // メールで確定しないまま期限が過ぎた申し込みは「未確定」にする（動画はつくらない。2026-11-03）
    if (rec['状態'] === WAIT_STATE && confirmClosed_(rec)) {
      update_(row, { '状態': UNSURE_STATE }, CONFIG.CONFIRM_HOURS + '時間たっても確定されなかった');
      return;
    }
    removeSources_(row, rec, now);
    if (now < approveDeadline_(rec) || (rec['状態'] !== '承認待ち' && rec['状態'] !== DONE_STATE)) return;
    stopSharing_(rec);
    if (rec['状態'] === DONE_STATE) {
      update_(row, { '状態': END_STATE }, '期限が来たので、確認ページとダウンロードのリンクを止めた');
      return;
    }
    update_(row, { '状態': '期限切れ' }, '期限までにダウンロードされなかった（リンクを止めた）');
    mail_(rec['メール'], '【ALCOHOLIDAY】動画のお渡しの期限が過ぎました（' + rec.id + '）',
      rec['店名'] + ' ' + dear_(rec) + '\n\n期限（' + jaTime_(approveDeadline_(rec)) + '）までに動画のダウンロードがなかったため、この動画のお渡しは終了しました。\n' +
      'あらためてご希望の場合は、このメールにご返信ください。\n\nALCOHOLIDAY（アルコホリディ）');
    mail_(CONFIG.OWNER_EMAIL, '【BAR広告】期限切れ ' + rec.id + ' ' + rec['店名'], 'ダウンロードされないまま期限を過ぎました。リンクは止めました。');
  });
}

/* 社長へのリマインド（2026-10-11 社長の指示）。日が来たら、社長のメールに1回だけ送る（送ったらスクリプトのプロパティに印を残す） */
const OWNER_REMINDERS = [
  { key: 'REMIND_AWS_FREE_2027', at: '2027-04-04',
    subject: '【リマインド】AWS の無料プランは 2027年4月11日 で終わります',
    body: 'AWS（受付ページ https://ad.alcoholiday.org/ を置いている Amplify）の無料プランは、2027年4月11日 で終わります（あと1週間）。\n' +
      'そのままにすると、受付ページが止まります。続けて使うには、AWS の管理画面の「プランをアップグレード」から有料プランに切り替えてください（今の使い方なら月に数十円〜数百円ほどの見込み）。\n\n' +
      'Claude Code に「KAYO、AWS の無料プランの切り替えを手伝って」と話しかけてください。\n' +
      '記録：09_広告事業/AWS 受付ページの設置記録.md' },
];

function remindOwner_(now) {
  const props = PropertiesService.getScriptProperties();
  const today = Utilities.formatDate(now, CONFIG.TZ, 'yyyy-MM-dd');
  OWNER_REMINDERS.forEach(r => {
    if (today < r.at || props.getProperty(r.key)) return;
    mail_(CONFIG.OWNER_EMAIL, r.subject, r.body);
    props.setProperty(r.key, fmt_(now));
  });
}

/* 送ってもらった動画（素材）を、受付から KEEP_SOURCE_DAYS 日で消す（2026-11-03 タケシの指示）
   消すのは、お客さんの動画のかけら（v1.part000 など）だけ。できあがった動画・確認用の動画は残す。
   ドライブのゴミ箱に入れる（ゴミ箱は Google が30日で空にする）。消したら台帳の履歴に残し、二度は消さない */
function removeSources_(row, rec, now) {
  if (!rec['素材動画'] || BUSY_STATES.indexOf(rec['状態']) >= 0 || /素材の動画を消した/.test(rec['履歴'])) return;
  if (now.getTime() < parseTime_(rec['受付日時']).getTime() + CONFIG.KEEP_SOURCE_DAYS * 86400000) return;
  let n = 0;
  try {
    const it = DriveApp.getFolderById(rec['素材動画']).getFiles();
    while (it.hasNext()) {
      const f = it.next();
      if (/^(old_)?v\d\.part\d+$/.test(f.getName())) { f.setTrashed(true); n++; }
    }
  } catch (err) { console.warn('素材を消せませんでした：' + rec.id + ' ' + err); return; }
  update_(row, {}, '素材の動画を消した（' + CONFIG.KEEP_SOURCE_DAYS + '日たった・' + n + '個）');
}

/** 送り始めたが申し込みまで進まなかった動画（「送信中」フォルダに残ったもの）も、KEEP_SOURCE_DAYS 日で消す */
function removeOldUploads_(now) {
  const it = uploadRoot_().getFolders();
  while (it.hasNext()) {
    const f = it.next();
    if (/^up-[0-9a-f]{32}$/.test(f.getName()) && now.getTime() - f.getDateCreated().getTime() > CONFIG.KEEP_SOURCE_DAYS * 86400000) f.setTrashed(true);
  }
}

/** 動画のダウンロードのリンクを止める（共有を「自分だけ」に戻す。ファイルは消さない） */
function stopSharing_(rec) {
  [rec['動画'], rec['前の動画']].filter(Boolean).forEach(id => {
    try { DriveApp.getFileById(id).setSharing(DriveApp.Access.PRIVATE, DriveApp.Permission.NONE); } catch (err) { console.warn('共有を止められませんでした：' + id + ' ' + err); }
  });
}

/* ────────────────────────────── KAYO との受け渡し口（API） ────────────────────────────── */

function doPost(e) {
  let out, name = '?';
  try {
    const req = JSON.parse(e.postData.contents);
    name = String(req.fn || req.action || '?').slice(0, 40);   // Apps Script の「実行数」に、何を呼んだかを残す（中身・キーは残さない。2026-10-31）
    console.log(name);
    if (req.action === 'page' || req.action === 'call') {   // AWS の受付ページから（お客さん）
      out = { ok: true, result: publicApi_(req) };
    } else {                                               // KAYO（パソコン）から：キーが必要
      if (!req.key || req.key !== prop_('API_KEY')) throw new Error('キーが違います');
      out = { ok: true, result: api_(req) };
    }
  } catch (err) {
    console.error(name + ' で断った：' + err.message);   // 「実行数」の行を開くと見える（2026-10-31 先生の PC の「通信が切れました」の原因さがし）
    out = { ok: false, error: err.message };
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

function api_(req) {
  switch (req.action) {
    case 'list':
      return rows_().filter(r => !req.state || r['状態'] === req.state);
    case 'sources': {   // 送ってもらった動画のかけらの一覧
      const r = mustFind_(req.id);
      const out = [];
      const it = DriveApp.getFolderById(r.rec['素材動画']).getFiles();
      while (it.hasNext()) {
        const f = it.next();
        if (/^v\d\.part\d+$/.test(f.getName())) out.push({ fileId: f.getId(), name: f.getName(), size: f.getSize() });
      }
      return out.sort((a, b) => a.name < b.name ? -1 : 1);
    }
    case 'part': {      // かけらを1つ受け取る
      const r = mustFind_(req.id);
      const f = DriveApp.getFileById(req.fileId);
      const parents = f.getParents();
      if (!parents.hasNext() || parents.next().getId() !== r.rec['素材動画']) throw new Error('この依頼のファイルではありません');
      return Utilities.base64Encode(f.getBlob().getBytes());
    }
    case 'update': {
      const r = mustFind_(req.id);
      const allowed = ['状態', '投稿文', 'SNS', '案内役', 'お客さんのコメント', 'プラン'];
      const fields = {};
      Object.keys(req.fields || {}).forEach(k => { if (allowed.indexOf(k) >= 0) fields[k] = req.fields[k]; });
      update_(r.row, fields, req.log || ('KAYO: ' + JSON.stringify(fields)));
      return findRow_(req.id).rec;
    }
    case 'deliver': {   // 動画を置いて、お客さんに「動画ができました」メールを送る
      const r = mustFind_(req.id);
      const folderId = r.rec['素材動画'];
      const blob = Utilities.newBlob(Utilities.base64Decode(req.video), 'video/mp4', req.name || (req.id + '.mp4'));
      const file = DriveApp.getFolderById(folderId).createFile(blob);
      // お客さんが確認ページとメールのリンクからダウンロードできるように「リンクを知っている人は見られる」にする（受付から24時間で止める）
      try { file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW); } catch (err) { /* 共有できない設定のとき */ }
      if (req.preview) {   // 確認ページで再生する確認用の小さい動画（同じ名前の古いものは名前を変えて残す）
        const folder = DriveApp.getFolderById(folderId);
        const old = folder.getFilesByName('確認用_' + file.getName());
        while (old.hasNext()) { const o = old.next(); o.setName('old_' + o.getName()); }
        folder.createFile(Utilities.newBlob(Utilities.base64Decode(req.preview), 'video/mp4', '確認用_' + file.getName()));
      }
      const keep = r.rec['状態'] === '修正依頼' && r.rec['動画'] ? { '前の動画': r.rec['動画'], '前の投稿文': r.rec['投稿文'] } : {};
      if (Array.isArray(req.yomi)) keep['よみ'] = JSON.stringify(req.yomi.map(String));   // 有料版：読み上げのひらがな（2026-10-31）
      update_(r.row, Object.assign({ '動画': file.getId(), '投稿文': JSON.stringify(req.captions || {}), '状態': '承認待ち' }, keep),
        '動画を届けた（' + file.getName() + '）');
      const rec = findRow_(req.id).rec;
      const url = pageUrl_() + '?p=review&id=' + encodeURIComponent(rec.id) + '&k=' + rec['承認キー'];
      // 直しの案内は、有料版で直しがまだできるときだけ（無料版は直しなし。2026-10-31 タケシの指示）
      const fixNote = canFix_(rec) && yomiOf_(rec).length ? '読み上げの読み方を直したいときは、同じページで、ひらがなの読み方を書きかえてお知らせください（1回まで）。\n' : '';
      mail_(rec['メール'], '【ALCOHOLIDAY】動画ができました。ご確認ください（' + rec.id + '）',
        rec['店名'] + ' ' + dear_(rec) + '\n\nおすすめ商品「' + rec['商品名'] + '」の動画ができました。\n' +
        '下のページで動画と投稿文を見て、よければ「カメラロールに保存」を押して、スマホに保存してください。\n' +
        fixNote + '\n' + url + '\n\n' +
        '投稿文をつくった SNS：' + snsLabel_(snsOf_(rec)) + '\nダウンロードの期限：' + jaTime_(approveDeadline_(rec)) + '\n' +
        '※ SNS ごとの投稿文は、同じページの「コピーする」ボタンでコピーできます。\n' +
        '※ ' + jaTime_(approveDeadline_(rec)) + ' までにダウンロードいただけない場合、動画のお渡しは終了します。' +
        'このページとダウンロードのリンクも ' + jaTime_(approveDeadline_(rec)) + ' で使えなくなります。\n' +
        againText_(rec) + '\nALCOHOLIDAY（アルコホリディ）');
      return { videoId: file.getId(), reviewUrl: url };
    }
    case 'voice': {     // 声の見本を置く（A / B / C / D の mp3）
      const folder = voiceFolder_();
      const it = folder.getFiles();
      while (it.hasNext()) {
        const f = it.next();
        if (f.getName().split('.')[0].toUpperCase() === req.guide) f.setName('old_' + fmt_(new Date()).replace(/\D/g, '') + '_' + f.getName());   // 古い見本は消さずに名前を変えて残す
      }
      folder.createFile(Utilities.newBlob(Utilities.base64Decode(req.data), 'audio/mpeg', req.guide + '.mp3'));
      return 'ok';
    }
    case 'info':
      return { sheet: SpreadsheetApp.openById(prop_('SHEET_ID')).getUrl(), form: webAppUrl_() };
    default:
      throw new Error('知らない action: ' + req.action);
  }
}

/* ────────────────────────────── 道具 ────────────────────────────── */

function prop_(k) { return PropertiesService.getScriptProperties().getProperty(k); }
function sheet_() { return SpreadsheetApp.openById(prop_('SHEET_ID')).getSheetByName(SHEET_NAME); }
function caseFolder_() { return DriveApp.getFolderById(prop_('FOLDER_ID')).getFoldersByName('案件').next(); }
function voiceFolder_() {
  const root = DriveApp.getFolderById(prop_('FOLDER_ID'));
  const it = root.getFoldersByName('声見本');
  return it.hasNext() ? it.next() : root.createFolder('声見本');
}
function fmt_(d) { return Utilities.formatDate(d, CONFIG.TZ, 'yyyy-MM-dd HH:mm'); }
// お客さんに見せる日時（例：10月11日 11:50）。台帳には fmt_ の形で残す
function jaTime_(d) { return Utilities.formatDate(d, CONFIG.TZ, 'M月d日 H:mm'); }
function clip_(s, n) { return String(s || '').trim().slice(0, n); }

function rows_() {
  const v = sheet_().getDataRange().getDisplayValues();
  return v.slice(1).map(row => {
    const o = {};
    COLS.forEach((c, i) => { o[c] = row[i]; });
    return o;
  });
}

function findRow_(id) { return id ? findBy_('id', id) : null; }

function findBy_(col, value) {
  const all = rows_();
  for (let i = 0; i < all.length; i++) if (all[i][col] === value) return { row: i + 2, rec: all[i] };
  return null;
}

/** 「動画ができました」メールの最後：次の申し込みのリンク（お店の情報が最初から入る）（2026-11-03） */
function againText_(rec) {
  if (!rec['再申込キー']) return '';
  return '\n■ 次のお申し込みは、下のリンクから（お店の情報が最初から入っています）\n' + pageUrl_() + '?p=form&a=' + rec['再申込キー'] + '\n' +
    (rec['プラン'] === '有料' ? '' : '※ 体験版は、1つの Google アカウントで1回までです。次からは有料版でお申し込みください。\n');
}

function mustFind_(id) {
  const r = findRow_(id);
  if (!r) throw new Error('依頼が見つかりません: ' + id);
  return r;
}

// 受付台帳の見出しが COLS より少ないとき（あとから列を足したとき）、右端に見出しを足す
function ensureCols_(sh) {
  const n = sh.getLastColumn();
  if (n < COLS.length) sh.getRange(1, n + 1, 1, COLS.length - n).setValues([COLS.slice(n)]).setFontWeight('bold').setBackground('#f3e6c8');
}

function update_(row, fields, log) {
  const sh = sheet_();
  ensureCols_(sh);
  Object.keys(fields).forEach(k => {
    const c = COLS.indexOf(k);
    if (c >= 0) sh.getRange(row, c + 1).setNumberFormat('@').setValue(fields[k]);
  });
  if (log) {
    const c = COLS.indexOf('履歴') + 1;
    const old = sh.getRange(row, c).getValue();
    sh.getRange(row, c).setValue((old ? old + '\n' : '') + fmt_(new Date()) + ' ' + log);
  }
}

function mail_(to, subject, body) {
  // 送り主は CONFIG.MAIL_FROM（2026-10-08 社長の指示）。Gmail の「他のアドレスから送る」に登録されていないときは、
  // いままでどおりのアドレスから送り、返信先だけ MAIL_FROM にする（メールが止まらないように）
  const from = CONFIG.MAIL_FROM;
  if (to !== CONFIG.OWNER_EMAIL) body += '\n\n――――――――――\n' + CONFIG.MAIL_LINKS;   // お客さんあてだけ、サイトと Amazon の URL を付ける
  try {
    if (from && GmailApp.getAliases().indexOf(from) >= 0) {
      GmailApp.sendEmail(to, subject, body, { from: from, name: 'ALCOHOLIDAY', replyTo: from });
      return;
    }
  } catch (e) {
    console.warn('送り主を ' + from + ' にできませんでした：' + e);
  }
  MailApp.sendEmail({ to: to, subject: subject, body: body, name: 'ALCOHOLIDAY', replyTo: from || CONFIG.OWNER_EMAIL });
}

/** エディタで実行して確かめる：送り主のアドレスが使えるか（はじめての実行で Gmail の許可を求められる） */
function checkMailFrom() {
  const list = GmailApp.getAliases();
  console.log('送り主に使えるアドレス：' + (list.join('、') || 'なし'));
  console.log(list.indexOf(CONFIG.MAIL_FROM) >= 0 ? 'OK：' + CONFIG.MAIL_FROM + ' から送ります'
    : 'まだ使えません：Gmail の設定 →「アカウント」→「他のメールアドレスを追加」で ' + CONFIG.MAIL_FROM + ' を登録してください（それまでは返信先だけ ' + CONFIG.MAIL_FROM + ' になります）');
}
