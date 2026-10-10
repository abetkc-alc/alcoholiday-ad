/**
 * ALCOHOLIDAY BAR広告 ショート動画作成の受付・お渡しシステム（Google Apps Script）
 *
 * できること
 *   0. トップページ（お客さん用）：サービスの紹介・会員登録・ログイン（メール＋パスワード）
 *   1. 受付ページ（会員用）：店・おすすめ商品・お店で撮った動画3本とその説明・動画を載せる SNS・ナレーションの声を入力してもらう
 *   2. 確認ページ（お客さん用）：完成した動画を見て「この動画に決める」か「直してほしい」を押してもらう
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
  // テスト中は、下のメールアドレスの人だけが会員登録・ログインできる（2026-10-08 社長の指示。公開するときは false にする）
  TEST_ONLY: true,
  TEST_EMAILS: ['abetkc@gmail.com', 'abetkc@alcoholiday.org'],
  // 受付サイトを埋め込んだホームページのページ（2026-10-08）。メールのトップページへのリンクはここにする
  //   （Google のページを直接開くと「Google Apps Script のユーザーによって作成…」のお知らせが出るため）
  SITE_URL: 'https://www.alcoholiday.org/%E7%BE%8E%E5%91%B3%E3%81%97%E3%81%84%E3%82%82%E3%81%AE',
  MAKE_MINUTES: 15,          // 受付から動画確認のメールまでの目安（分）。受付のメールに書く（2026-10-09。いつもは8〜12分）
  APPROVE_DAYS: 7,           // 受付から何日以内に動画を決めてもらうか（過ぎたら期限切れ・お渡ししない）
  VIDEOS: [                  // お客さんに撮ってもらう動画（各5秒くらい）。この順につなぐ
    { key: 1, title: 'お店の雰囲気', hint: '入口・看板・カウンター・店内など', example: '例：恵比寿駅から歩いて3分。木のカウンターが落ち着く小さなお店です' },
    { key: 2, title: 'おすすめ商品', hint: 'いちばん売りたいもの。つくるところ・注ぐところ・グラスのアップなど', example: '例：岡山の白桃を丸ごと使ったベリーニ。秋だけの限定です' },
    { key: 3, title: '自由', hint: 'バーテンダー・乾杯・お店の自慢など', example: '例：マスターは銀座で20年。好みを伝えれば一杯つくってくれます' },
  ],
  MAX_VIDEO_MB: 25,          // 1本の大きさの上限（2026-10-07 社長の指示で150→25。5秒・1080p なら10MBくらい。大きいと受け取りに時間がかかる）
  MAX_VIDEO_SEC: 10,         // 1本の長さの上限（秒）。使うのは1本4〜5秒
  VIDEO_DESC_MAX: 50,        // 動画1本ごとの説明の文字数の上限（2026-10-06 社長の指示で100→50。声と字幕にほぼそのまま使う）
  PW_MIN: 8,                 // パスワードの最短の文字数
  SESSION_DAYS: 30,          // ログインしたままでいられる日数
  LOGIN_MAX_FAIL: 5,         // パスワードを何回まちがえたら、しばらくログインできなくするか
  LOCK_MINUTES: 15,          // そのときの待ち時間（分）
  RESET_HOURS: 1,            // パスワード再設定のリンクの有効時間
  MAX_FIX: 1,                // 動画の直しは何回までか（2026-10-04 社長の指示：1回だけ。直したあとは2本から選んで決める）
  PRODUCT_MAX: 40,           // 商品の名前の文字数の上限（動画の上に出すので短め）
  DESC_MAX: 50,              // 商品の説明の文字数の上限（2026-10-06 社長の指示で300→50）
  GUIDES: [                  // ナレーションの声（案内役。動画には出ず、声だけ担当）
    { key: 'A', name: 'ローズ', desc: '明るく親しみやすい声' },
    { key: 'B', name: 'ラフィ', desc: 'クールで大人っぽい声' },
    { key: 'C', name: 'アイラ', desc: 'ゆっくり落ち着いた声' },
    { key: 'D', name: 'アルビン', desc: '男性の声' },
  ],
  PLATFORMS: ['instagram', 'tiktok', 'x'],
  PLATFORM_NAMES: { instagram: 'Instagram', tiktok: 'TikTok', x: 'X' },
  PLANS: ['無料', '有料'],   // 無料＝動画の上下に透かしのロゴ＋最後に締め画像と声／有料＝最後に小さくロゴ（2026-10-10 社長の指示。お支払いの仕組みはまだ）
};

const SHEET_NAME = '依頼';
const COLS = ['id', '会員ID', '受付日時', '状態', '店名', '担当者', 'メール', '電話', '都道府県', '住所', 'エリア', '営業時間',
  '店のSNS', '商品名', '商品の説明', '価格', '数量限定', '投稿日', '時間帯', '案内役', '要望', 'お客さんの投稿文', '素材動画', '動画の説明', '承認キー',
  '動画', '投稿文', '投稿日時', '承認日時', 'お客さんのコメント', '予約ID', '履歴',
  '前の動画', '前の投稿文',   // 直しのあと、お客さんが「直す前」を選べるように残す（2026-10-04 追加。台帳の右端に足される）
  'SNS',                     // 投稿文をつくる SNS（instagram,tiktok,x のように。2026-10-06 追加）
  'プラン'];                 // 無料／有料（2026-10-10 追加。いまは受付で「無料」。有料にするときは、制作の前に社長が台帳で「有料」に変える）
// 会員（受付台帳の「会員」シート）。パスワードはそのまま保存せず、ソルトを足して何度もハッシュにした値だけを残す
const MEMBER_SHEET = '会員';
const MCOLS = ['会員ID', '登録日時', '状態', 'メール', 'パスワード', 'ソルト', '店名', '担当者', '電話', '都道府県', '住所',
  'エリア', '営業時間', '店のSNS', 'セッション', 'セッション期限', '失敗回数', 'ロック期限', '再設定キー', '再設定期限', '最終ログイン', '履歴'];
// 受付ページの入力欄の名前 → 会員シートの列
const PROFILE = { shop: '店名', person: '担当者', tel: '電話', pref: '都道府県', address: '住所', area: 'エリア', hours: '営業時間', sns: '店のSNS' };
// 枠を使っていない（ほかの人が申し込める）状態
const FREE_STATES = ['キャンセル', '期限切れ'];

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
  memberSheet_();   // 「会員」シートをつくる
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
  const p = (e && e.parameter) || {};
  let t;
  if (p.p === 'review') {
    t = HtmlService.createTemplateFromFile('review');
    t.data = Object.assign(reviewData_(p.id, p.k), { logo: logo_() });
  } else if (p.p === 'logout') {   // 申し込みのページの「ログアウト」から
    logout(p.s);
    t = HtmlService.createTemplateFromFile('top');
    t.data = topData_('', '', 'ログアウトしました。');
  } else if (p.p === 'form') {
    const m = memberBySession_(p.s);
    if (m && testOk_(m.rec['メール'])) {
      t = HtmlService.createTemplateFromFile('form');
      t.data = formData_(m, p.s);
    } else {
      t = HtmlService.createTemplateFromFile('top');
      t.data = topData_('', '', 'ログインの期限が切れました。もう一度ログインしてください。');
    }
  } else {
    t = HtmlService.createTemplateFromFile('top');
    t.data = topData_(p.p === 'reset' ? 'reset' : '', p.k || '', '');
  }
  return t.evaluate()
    .setTitle('ALCOHOLIDAY BAR広告')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/** ページの中に別の HTML ファイル（css・common）を入れる */
function include_(name) { return HtmlService.createHtmlOutputFromFile(name).getContent(); }
function logo_() { return include_('logo'); }

function topData_(mode, key, msg) {
  return { logo: logo_(), mode: mode, key: key, msg: msg, pwMin: CONFIG.PW_MIN, testOnly: CONFIG.TEST_ONLY };
}

/** テスト中は、決めた人だけ通す */
function testOk_(email) {
  return !CONFIG.TEST_ONLY || CONFIG.TEST_EMAILS.indexOf(String(email || '').trim().toLowerCase()) >= 0;
}
const TEST_NG = 'ただいま準備中です。公開まで、もうしばらくお待ちください。';

function formData_(m, session) {
  const member = {};
  Object.keys(PROFILE).forEach(k => { member[k] = m.rec[PROFILE[k]]; });
  member.email = m.rec['メール'];
  return {
    session: session, member: member, topUrl: webAppUrl_(),
    platforms: CONFIG.PLATFORMS.map(p => ({ key: p, name: CONFIG.PLATFORM_NAMES[p] })),
    guides: (s => CONFIG.GUIDES.map(g => Object.assign({ sample: s[g.key] || '' }, g)))(voiceSamples()),   // 声の見本（フォルダを1回だけ見る）
    videos: CONFIG.VIDEOS,
    maxVideoMb: CONFIG.MAX_VIDEO_MB,
    maxVideoSec: CONFIG.MAX_VIDEO_SEC,
    videoDescMax: CONFIG.VIDEO_DESC_MAX,
    productMax: CONFIG.PRODUCT_MAX,
    descMax: CONFIG.DESC_MAX,
    approveDays: CONFIG.APPROVE_DAYS,
    logo: logo_(),
  };
}

/** メールに書くトップページの URL（ホームページに埋め込んだページ） */
function siteUrl_() { return CONFIG.SITE_URL || webAppUrl_(); }

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

/* ────────────────────────────── 会員 ────────────────────────────── */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** 申し込みを受け付けたかどうか（返事がスマホに届かなかったときに、スマホから確かめる。2026-10-08） */
function orderResult(upload) {
  if (!/^[\w-]{8,}$/.test(String(upload || ''))) return null;
  const v = CacheService.getScriptCache().get('order-' + upload);
  return v ? JSON.parse(v) : null;
}

/** トップページの「登録して申し込みへ進む」 */
function registerMember(f) {
  const email = String(f.email || '').trim().toLowerCase();
  if (!EMAIL_RE.test(email)) throw new Error('メールアドレスの形が正しくありません');
  if (!testOk_(email)) throw new Error(TEST_NG);
  if (String(f.password || '').length < CONFIG.PW_MIN) throw new Error('パスワードは' + CONFIG.PW_MIN + '文字以上にしてください');
  const need = { shop: '店名', tel: 'お店の電話番号', pref: '都道府県', address: '住所', hours: '営業時間' };
  Object.keys(need).forEach(k => { if (!String(f[k] || '').trim()) throw new Error(need[k] + 'を入力してください'); });

  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    if (mfind_('メール', email)) throw new Error('このメールアドレスは、すでに登録されています。「会員の方」からログインしてください');
    const now = new Date();
    const salt = Utilities.getUuid().replace(/-/g, '');
    const rec = {
      '会員ID': 'M-' + ('000' + (mrows_().length + 1)).slice(-4), '登録日時': fmt_(now), '状態': '有効',
      'メール': email, 'パスワード': hash_(f.password, salt), 'ソルト': salt, '失敗回数': '0', '履歴': fmt_(now) + ' 会員登録',
    };
    Object.keys(PROFILE).forEach(k => { rec[PROFILE[k]] = clip_(f[k], k === 'address' ? 120 : (k === 'sns' ? 200 : 80)); });
    const sh = memberSheet_();
    sh.getRange(sh.getLastRow() + 1, 1, 1, MCOLS.length).setNumberFormat('@')
      .setValues([MCOLS.map(c => rec[c] === undefined ? '' : rec[c])]);
    const m = mfind_('メール', email);
    const token = newSession_(m.row);
    mail_(email, '【ALCOHOLIDAY】会員登録が完了しました',
      rec['店名'] + '\n' + dear_(rec) + '\n\n' +
      'ALCOHOLIDAY のショート動画作成に会員登録いただき、ありがとうございます。\n' +
      '次からは、下のページの「会員の方」から、このメールアドレスとパスワードでログインしてください。\n\n' +
      siteUrl_() + '\n\n会員ID：' + rec['会員ID'] + '\n\n' +
      '※ お心当たりのない場合は、このメールにご返信ください。\n\nALCOHOLIDAY（アルコホリディ）');
    mail_(CONFIG.OWNER_EMAIL, '【BAR広告】新しい会員 ' + rec['会員ID'] + ' ' + rec['店名'],
      '新しい会員が登録しました。\n\n店名：' + rec['店名'] + '（' + rec['都道府県'] + rec['住所'] + '）\n' +
      '電話：' + rec['電話'] + '\nメール：' + email + '\n\n受付台帳の「会員」シートで確認できます。止めたいときは「状態」を「停止」にします。');
    return { url: formUrl_(token), session: token };
  } finally {
    lock.releaseLock();
  }
}

/** トップページの「ログインする」 */
function login(email, password) {
  email = String(email || '').trim().toLowerCase();
  const m = mfind_('メール', email);
  const ng = 'メールアドレスかパスワードがちがいます';
  if (!testOk_(email)) throw new Error(TEST_NG);
  if (!m) throw new Error(ng);
  const now = new Date();
  if (m.rec['ロック期限'] && now < new Date(m.rec['ロック期限'].replace(' ', 'T') + ':00+09:00')) {
    throw new Error('パスワードを何回もまちがえたため、しばらくログインできません。' + CONFIG.LOCK_MINUTES + '分ほどたってから、もう一度お試しください');
  }
  if (m.rec['状態'] === '停止') throw new Error('この会員は利用を止めています。ALCOHOLIDAY へご連絡ください');
  if (hash_(password, m.rec['ソルト']) !== m.rec['パスワード']) {
    const fails = (Number(m.rec['失敗回数']) || 0) + 1;
    const fields = { '失敗回数': String(fails) };
    if (fails >= CONFIG.LOGIN_MAX_FAIL) {
      fields['ロック期限'] = fmt_(new Date(now.getTime() + CONFIG.LOCK_MINUTES * 60000));
      fields['失敗回数'] = '0';
    }
    mupdate_(m.row, fields, fails >= CONFIG.LOGIN_MAX_FAIL ? 'パスワードのまちがいが続いたので一時停止' : '');
    throw new Error(ng);
  }
  mupdate_(m.row, { '失敗回数': '0', 'ロック期限': '', '最終ログイン': fmt_(now) }, '');
  const token = newSession_(m.row);
  return { url: formUrl_(token), session: token };
}

/** 受付ページの「ログアウト」 */
// ログインのあと、トップページの中身を申し込みのページに入れ替えるために、申し込みのページを渡す
//   （Google のページは、ボタンを押さないと別のページへ移れないため）
function formPage(session) {
  const m = memberBySession_(session);
  if (!m) throw new Error('ログインの期限が切れました。もう一度ログインしてください。');
  if (!testOk_(m.rec['メール'])) throw new Error(TEST_NG);
  const t = HtmlService.createTemplateFromFile('form');
  t.data = formData_(m, session);
  return t.evaluate().getContent();
}

function logout(session) {
  const m = memberBySession_(session);
  if (m) mupdate_(m.row, { 'セッション': '', 'セッション期限': '' }, 'ログアウト');
  return 'ok';
}

/** 「パスワードを忘れた方」：再設定のリンクをメールで送る（登録がなくても同じ返事にする） */
function requestReset(email) {
  email = String(email || '').trim().toLowerCase();
  const m = EMAIL_RE.test(email) && testOk_(email) ? mfind_('メール', email) : null;
  if (m && m.rec['状態'] !== '停止') {
    const key = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    mupdate_(m.row, { '再設定キー': key, '再設定期限': fmt_(new Date(Date.now() + CONFIG.RESET_HOURS * 3600000)) }, '再設定のメールを送った');
    mail_(email, '【ALCOHOLIDAY】パスワードの再設定',
      m.rec['店名'] + '\n' + dear_(m.rec) + '\n\n下のリンクを開いて、新しいパスワードを決めてください（' + CONFIG.RESET_HOURS + '時間だけ使えます）。\n\n' +
      webAppUrl_() + '?p=reset&k=' + key + '\n\n※ お心当たりのない場合は、このメールは捨ててください。パスワードは変わりません。\n\nALCOHOLIDAY（アルコホリディ）');
  }
  return 'ご登録のメールアドレスであれば、再設定のメールをお送りしました。\nメールのリンクを開いて、新しいパスワードを決めてください。\n届かないときは、迷惑メールのフォルダもご覧ください。';
}

/** メールのリンクから：新しいパスワードを決める */
function resetPassword(key, password) {
  if (!/^[0-9a-f]{64}$/.test(String(key))) throw new Error('リンクが正しくありません。もう一度「パスワードを忘れた方」からお試しください');
  if (String(password || '').length < CONFIG.PW_MIN) throw new Error('パスワードは' + CONFIG.PW_MIN + '文字以上にしてください');
  const m = mfind_('再設定キー', key);
  if (!m || new Date() > new Date(m.rec['再設定期限'].replace(' ', 'T') + ':00+09:00')) {
    throw new Error('リンクの期限が切れています。もう一度「パスワードを忘れた方」からお試しください');
  }
  const salt = Utilities.getUuid().replace(/-/g, '');
  mupdate_(m.row, { 'パスワード': hash_(password, salt), 'ソルト': salt, '再設定キー': '', '再設定期限': '', '失敗回数': '0', 'ロック期限': '' }, 'パスワードを再設定');
  const token = newSession_(m.row);
  return { url: formUrl_(token), session: token };
}

/** 受付ページの合言葉（セッション）から会員をさがす。期限切れ・停止中なら null */
function memberBySession_(session) {
  if (!/^[0-9a-f]{40}$/.test(String(session || ''))) return null;
  const m = mfind_('セッション', session);
  if (!m || m.rec['状態'] === '停止') return null;
  if (new Date() > new Date(m.rec['セッション期限'].replace(' ', 'T') + ':00+09:00')) return null;
  return m;
}

function newSession_(row) {
  const token = (Utilities.getUuid() + Utilities.getUuid()).replace(/-/g, '').slice(0, 40);
  mupdate_(row, { 'セッション': token, 'セッション期限': fmt_(new Date(Date.now() + CONFIG.SESSION_DAYS * 86400000)) }, '');
  return token;
}

function formUrl_(token) { return webAppUrl_() + '?p=form&s=' + token; }

/** パスワードをそのまま残さないための変換（ソルトを足して 1000 回くり返す） */
function hash_(password, salt) {
  let h = salt + ':' + String(password);
  for (let i = 0; i < 1000; i++) {
    h = Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, h + salt, Utilities.Charset.UTF_8));
  }
  return h;
}

function memberSheet_() {
  const ss = SpreadsheetApp.openById(prop_('SHEET_ID'));
  let sh = ss.getSheetByName(MEMBER_SHEET);
  if (!sh) {
    sh = ss.insertSheet(MEMBER_SHEET);
    sh.getRange(1, 1, sh.getMaxRows(), MCOLS.length).setNumberFormat('@');
    sh.getRange(1, 1, 1, MCOLS.length).setValues([MCOLS]).setFontWeight('bold').setBackground('#dce8f5');
    sh.setFrozenRows(1);
  }
  return sh;
}

function mrows_() {
  const v = memberSheet_().getDataRange().getDisplayValues();
  return v.slice(1).map(row => {
    const o = {};
    MCOLS.forEach((c, i) => { o[c] = row[i]; });
    return o;
  });
}

function mfind_(col, value) {
  if (!value) return null;
  const all = mrows_();
  for (let i = 0; i < all.length; i++) {
    if (String(all[i][col]).toLowerCase() === String(value).toLowerCase()) return { row: i + 2, rec: all[i] };
  }
  return null;
}

function mupdate_(row, fields, log) {
  const sh = memberSheet_();
  Object.keys(fields).forEach(k => {
    const c = MCOLS.indexOf(k);
    if (c >= 0) sh.getRange(row, c + 1).setNumberFormat('@').setValue(fields[k]);
  });
  if (log) {
    const c = MCOLS.indexOf('履歴') + 1;
    const old = sh.getRange(row, c).getValue();
    sh.getRange(row, c).setValue((old ? old + '\n' : '') + fmt_(new Date()) + ' ' + log);
  }
}

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
  const member = memberBySession_(f.session);
  if (!member) throw new Error('ログインの期限が切れました。トップページからもう一度ログインしてください（入力した内容は消えてしまいます。お手数ですが、もう一度入力してください）');
  const need = { shop: '店名', email: 'メールアドレス', tel: '電話番号', pref: '都道府県',
    address: '住所', hours: '営業時間', product: 'おすすめ商品の名前', desc: '商品の説明' };
  Object.keys(need).forEach(k => {
    if (!f[k] || !String(f[k]).trim()) throw new Error(need[k] + 'を入力してください');
  });
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) throw new Error('メールアドレスの形が正しくありません');
  const vids = f.videos || [];
  if (vids.length !== CONFIG.VIDEOS.length) throw new Error('動画を' + CONFIG.VIDEOS.length + '本えらんでください');
  vids.forEach((v, i) => {
    if (!v.desc || !String(v.desc).trim()) throw new Error('動画' + (i + 1) + '（' + CONFIG.VIDEOS[i].title + '）の説明を入力してください');
    if (String(v.desc).length > CONFIG.VIDEO_DESC_MAX) throw new Error('動画' + (i + 1) + 'の説明は' + CONFIG.VIDEO_DESC_MAX + '文字までです');
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
  const platforms = (Array.isArray(f.platforms) ? f.platforms : []).filter((p, i, a) => CONFIG.PLATFORMS.indexOf(p) >= 0 && a.indexOf(p) === i);
  if (!platforms.length) throw new Error('動画を載せる SNS を1つ以上えらんでください');
  const guide = CONFIG.GUIDES.filter(g => g.key === f.guide)[0];

  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const now = new Date();
    const id = newId_(now);
    const folder = upFolder;   // 送ってもらった動画のフォルダを、そのまま案件のフォルダにする
    folder.moveTo(caseFolder_());
    folder.setName(id + ' ' + clip_(f.shop, 40));
    const videoInfo = vids.map((v, i) => ({
      no: i + 1, title: CONFIG.VIDEOS[i].title, desc: clip_(v.desc, 300), name: clip_(v.name, 120),
      type: clip_(v.type, 40), size: Number(v.size) || 0, sec: Math.round((Number(v.sec) || 0) * 10) / 10, parts: Number(v.parts),
    }));
    const key = Utilities.getUuid().replace(/-/g, '').slice(0, 20);
    const rec = {
      'id': id, '会員ID': member.rec['会員ID'], '受付日時': fmt_(now), '状態': '受付',
      '店名': clip_(f.shop, 80), '担当者': clip_(f.person, 60), 'メール': clip_(f.email, 120),
      '電話': clip_(f.tel, 30), '都道府県': clip_(f.pref, 10), '住所': clip_(f.address, 120), 'エリア': clip_(f.area, 80),
      '営業時間': clip_(f.hours, 80), '店のSNS': clip_(f.sns, 200), '商品名': clip_(f.product, CONFIG.PRODUCT_MAX),
      '商品の説明': clip_(f.desc, CONFIG.DESC_MAX), '価格': clip_(f.price, 40), '数量限定': f.limited ? 'はい' : '', 'SNS': platforms.join(','),
      '案内役': guide ? guide.key : 'おまかせ', '要望': clip_(f.note, 600),
      // 投稿文は、商品の説明をもとに KAYO が自動でつくる（2026-10-10 から申し込みページに入力欄はない）
      '素材動画': folder.getId(), '動画の説明': JSON.stringify(videoInfo), '承認キー': key,
      'プラン': '無料',   // お支払いの仕組みができるまでは、受付は無料版
      '履歴': fmt_(now) + ' 受付',
    };
    const sh = sheet_();
    ensureCols_(sh);
    sh.getRange(sh.getLastRow() + 1, 1, 1, COLS.length).setNumberFormat('@')
      .setValues([COLS.map(c => rec[c] === undefined ? '' : rec[c])]);
    if (f.saveProfile) {   // 受付ページで直したお店の情報を、会員情報にも保存する
      const prof = {};
      Object.keys(PROFILE).forEach(k => { if (String(f[k] || '') !== member.rec[PROFILE[k]]) prof[PROFILE[k]] = rec[PROFILE[k]]; });
      if (Object.keys(prof).length) mupdate_(member.row, prof, '受付ページで会員情報を更新（' + Object.keys(prof).join('・') + '）');
    }

    const snsText = snsLabel_(platforms);
    mail_(rec['メール'], '【ALCOHOLIDAY】ショート動画のお申し込みを受け付けました（' + id + '）',
      rec['店名'] + '\n' + dear_(rec) + '\n\n' +
      'お申し込みありがとうございます。以下の内容で受け付けました。\n\n' +
      '受付番号：' + id + '\n投稿文をつくる SNS：' + snsText + '\nおすすめ商品：' + rec['商品名'] + '\n\n' +
      '■ このあとの流れ\n' +
      '1. ALCOHOLIDAY が動画をつくります\n' +
      '2. 動画ができたら、確認用ページのリンクをメールでお送りします（受付から約' + CONFIG.MAKE_MINUTES + '分後。混み合っているときは、遅れることがあります）\n' +
      '3. 動画を見て「この動画に決める」を押してください（受付から' + CONFIG.APPROVE_DAYS + '日以内）\n' +
      '4. 動画のダウンロードのリンクと、' + snsText + ' ごとの投稿文をメールでお送りします\n' +
      '5. お店の SNS アカウントから、ご自身で投稿してください\n\n' +
      'ALCOHOLIDAY（アルコホリディ）');
    mail_(CONFIG.OWNER_EMAIL, '【BAR広告】新しい依頼 ' + id + ' ' + rec['店名'],
      '新しい依頼が届きました。\n\n店名：' + rec['店名'] + '（' + rec['都道府県'] + rec['住所'] + '）\n' +
      '商品：' + rec['商品名'] + '\n投稿文：' + snsText + '\nプラン：' + rec['プラン'] + '\n声：' + guideName_(rec['案内役']) + '\n\n' +
      'Claude Code に「KAYO、BAR広告の新しい依頼を確認して」と話しかけてください。\n' +
      '受付台帳：' + SpreadsheetApp.openById(prop_('SHEET_ID')).getUrl());
    const res = { id: id, when: snsText };   // 例：Instagram・TikTok
    if (f.upload) CacheService.getScriptCache().put('order-' + f.upload, JSON.stringify(res), 21600);   // 6時間おぼえておく
    return res;
  } finally {
    lock.releaseLock();
  }
}

function newId_(now) {
  const base = 'BAR-' + Utilities.formatDate(now, CONFIG.TZ, 'yyyyMMdd') + '-';
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

/** 受付ページ：送り始める前に呼ぶ。送信用の合言葉（フォルダ名）を返す */
function startUpload() {
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

const DONE_STATE = 'お渡し済み';   // お客さんが「この動画に決める」を押したあと（ダウンロードできる）

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
  const captions = parseCaptions_(rec['投稿文']);
  return {
    id: rec.id, key: k, state: rec['状態'], shop: rec['店名'], product: rec['商品名'],
    when: snsLabel_(snsOf_(rec)), plan: rec['プラン'] || '無料',
    download: rec['状態'] === DONE_STATE && rec['動画'] ? downloadUrl_(rec['動画']) : '',
    videoId: rec['動画'], captions: captions, comment: rec['お客さんのコメント'],
    deadline: fmt_(approveDeadline_(rec)), canAct: rec['状態'] === '承認待ち' && new Date() < approveDeadline_(rec),
    canFix: fixCount_(rec) < CONFIG.MAX_FIX,
    prev: rec['前の動画'] ? { videoId: rec['前の動画'], captions: parseCaptions_(rec['前の投稿文']) } : null,
  };
}

function parseCaptions_(t) {
  try { return JSON.parse(t || '{}'); } catch (err) { return { instagram: t }; }
}

// これまでに直しを頼まれた回数（履歴から数える）
function fixCount_(rec) {
  return (String(rec['履歴'] || '').match(/お客さんが修正を依頼/g) || []).length;
}

// 動画を決める期限：受付から APPROVE_DAYS 日
function approveDeadline_(rec) {
  return new Date(new Date(String(rec['受付日時']).replace(' ', 'T') + ':00+09:00').getTime() + CONFIG.APPROVE_DAYS * 86400000);
}

/** 確認ページの「この動画に決める」：ダウンロードのリンクと、SNS ごとの投稿文をメールで送る */
function approve(id, k, choice) {
  const r = checkReview_(id, k);
  if (choice === 'prev' && r.rec['前の動画']) {
    update_(r.row, { '動画': r.rec['前の動画'], '投稿文': r.rec['前の投稿文'], '前の動画': r.rec['動画'], '前の投稿文': r.rec['投稿文'] },
      'お客さんが「直す前」の動画を選んだ');
  }
  update_(r.row, { '状態': DONE_STATE, '承認日時': fmt_(new Date()) }, 'お客さんが動画を決めた（ダウンロードのメールを送った）');
  const rec = findRow_(id).rec;
  const url = downloadUrl_(rec['動画']);
  const page = webAppUrl_() + '?p=review&id=' + encodeURIComponent(rec.id) + '&k=' + rec['承認キー'];
  mail_(rec['メール'], '【ALCOHOLIDAY】動画のダウンロードと投稿文のお知らせ（' + id + '）',
    rec['店名'] + ' ' + dear_(rec) + '\n\n' +
    'おすすめ商品「' + rec['商品名'] + '」の動画をお選びいただき、ありがとうございます。\n' +
    '下のリンクから動画をダウンロードして、お店の SNS アカウントから投稿してください。\n\n' +
    '■ 動画のダウンロード\n' + url + '\n' +
    '（スマホで開けないときは、こちらのページの「動画をダウンロード」ボタンからどうぞ：' + page + '）\n\n' +
    '■ SNS ごとの投稿文（そのままコピーしてお使いください）\n\n' + captionsText_(rec) + '\n\n' +
    '※ 「#PR」と、お酒の注意書き（20歳未満の飲酒・飲酒運転の禁止）は、消さずにお使いください。\n' +
    '※ 投稿した内容と、投稿のあとに起きたことについては、投稿したお店の責任となります。\n\n' +
    'ALCOHOLIDAY（アルコホリディ）');
  mail_(CONFIG.OWNER_EMAIL, '【BAR広告】動画が決まりました ' + id + ' ' + rec['店名'],
    rec['店名'] + ' が動画を決めました。ダウンロードのリンクと投稿文（' + snsLabel_(snsOf_(rec)) + '）をメールで送りました。\nプラン：' + (rec['プラン'] || '無料'));
  return 'ありがとうございます。動画のダウンロードのリンクと、SNS ごとの投稿文をメールでお送りしました。下の「動画をダウンロード」からも保存できます。';
}

/** 確認ページの「直してほしい」 */
// 確認ページの動画を、ページの中で直接再生するために渡す（スマホは Google ドライブの再生画面だとログインを求められたり再生できないことがあるため）
//   KAYO が届けた「確認用（小さい動画）」があればそれを、なければ本番の動画を渡す
function reviewVideo(id, k, which) {
  const r = findRow_(id);
  const vid = which === 'prev' ? r && r.rec['前の動画'] : r && r.rec['動画'];
  if (!r || !k || r.rec['承認キー'] !== k || !vid) throw new Error('動画が見つかりません');
  const main = DriveApp.getFileById(vid);
  let file = main;
  const it = DriveApp.getFolderById(r.rec['素材動画']).getFilesByName('確認用_' + main.getName());
  if (it.hasNext()) file = it.next();
  if (file.getSize() > 20 * 1024 * 1024) throw new Error('動画が大きすぎて、このページでは再生できません');
  return Utilities.base64Encode(file.getBlob().getBytes());
}

function requestChange(id, k, comment) {
  if (!comment || !String(comment).trim()) throw new Error('直してほしいところを書いてください');
  const r = checkReview_(id, k);
  if (fixCount_(r.rec) >= CONFIG.MAX_FIX) throw new Error('動画の直しは1回までです。2本のうち、よいほうを選んで「この動画に決める」を押してください');
  update_(r.row, { '状態': '修正依頼', 'お客さんのコメント': clip_(comment, 1000) }, 'お客さんが修正を依頼');
  mail_(CONFIG.OWNER_EMAIL, '【BAR広告】修正の依頼 ' + id + ' ' + r.rec['店名'],
    'お客さんから修正の依頼が届きました。\n\n' + comment + '\n\nClaude Code に「KAYO、BAR広告の修正依頼を確認して」と話しかけてください。');
  return '受け付けました。直した動画ができたら、またメールでお知らせします。';
}

function checkReview_(id, k) {
  const r = findRow_(id);
  if (!r || r.rec['承認キー'] !== k) throw new Error('ページが見つかりません');
  if (r.rec['状態'] !== '承認待ち') throw new Error('この動画はいま決められる状態ではありません（' + r.rec['状態'] + '）');
  if (new Date() >= approveDeadline_(r.rec)) throw new Error('動画を決める期限を過ぎました。ALCOHOLIDAY へご連絡ください');
  return r;
}

/* ────────────────────────────── 1時間ごとの見回り ────────────────────────────── */

// 2026-10-10 から自動投稿（Upload-Post）はしない。見回りは「動画を決める期限が過ぎたもの」を期限切れにするだけ
function hourlyCheck() {
  const now = new Date();
  rows_().forEach((rec, i) => {
    const row = i + 2;
    if (rec['状態'] === '承認待ち' && now >= approveDeadline_(rec)) {
      update_(row, { '状態': '期限切れ' }, '動画を決める期限が過ぎた（お渡ししない）');
      mail_(rec['メール'], '【ALCOHOLIDAY】動画をお選びいただく期限が過ぎました（' + rec.id + '）',
        rec['店名'] + ' ' + dear_(rec) + '\n\n期限（' + fmt_(approveDeadline_(rec)) + '）までに動画をお選びいただけなかったため、この動画のお渡しは終了しました。\n' +
        'あらためてご希望の場合は、このメールにご返信ください。\n\nALCOHOLIDAY（アルコホリディ）');
      mail_(CONFIG.OWNER_EMAIL, '【BAR広告】期限切れ ' + rec.id + ' ' + rec['店名'], '動画が決まらないまま期限を過ぎました。お渡しはしていません。');
    }
  });
}

/* ────────────────────────────── KAYO との受け渡し口（API） ────────────────────────────── */

function doPost(e) {
  let out;
  try {
    const req = JSON.parse(e.postData.contents);
    if (!req.key || req.key !== prop_('API_KEY')) throw new Error('キーが違います');
    out = { ok: true, result: api_(req) };
  } catch (err) {
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
      // 動画を決めたあと、お客さんがメールのリンクからダウンロードできるように「リンクを知っている人は見られる」にする
      try { file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW); } catch (err) { /* 共有できない設定のとき */ }
      if (req.preview) {   // 確認ページで再生する確認用の小さい動画（同じ名前の古いものは名前を変えて残す）
        const folder = DriveApp.getFolderById(folderId);
        const old = folder.getFilesByName('確認用_' + file.getName());
        while (old.hasNext()) { const o = old.next(); o.setName('old_' + o.getName()); }
        folder.createFile(Utilities.newBlob(Utilities.base64Decode(req.preview), 'video/mp4', '確認用_' + file.getName()));
      }
      const keep = r.rec['状態'] === '修正依頼' && r.rec['動画'] ? { '前の動画': r.rec['動画'], '前の投稿文': r.rec['投稿文'] } : {};
      update_(r.row, Object.assign({ '動画': file.getId(), '投稿文': JSON.stringify(req.captions || {}), '状態': '承認待ち' }, keep),
        '動画を届けた（' + file.getName() + '）');
      const rec = findRow_(req.id).rec;
      const url = webAppUrl_() + '?p=review&id=' + encodeURIComponent(rec.id) + '&k=' + rec['承認キー'];
      mail_(rec['メール'], '【ALCOHOLIDAY】動画ができました。ご確認ください（' + rec.id + '）',
        rec['店名'] + ' ' + dear_(rec) + '\n\nおすすめ商品「' + rec['商品名'] + '」の動画ができました。\n' +
        '下のページで動画と投稿文を見て、「この動画に決める」か「直してほしい」を押してください。\n\n' + url + '\n\n' +
        '投稿文をつくった SNS：' + snsLabel_(snsOf_(rec)) + '\nお選びいただく期限：' + fmt_(approveDeadline_(rec)) + '\n' +
        '※ 「この動画に決める」を押すと、動画のダウンロードのリンクと、SNS ごとの投稿文をメールでお送りします。\n' +
        '※ 期限までにお選びいただけない場合、動画のお渡しは終了します。\n\nALCOHOLIDAY（アルコホリディ）');
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
function clip_(s, n) { return String(s || '').trim().slice(0, n); }

function rows_() {
  const v = sheet_().getDataRange().getDisplayValues();
  return v.slice(1).map(row => {
    const o = {};
    COLS.forEach((c, i) => { o[c] = row[i]; });
    return o;
  });
}

function findRow_(id) {
  const all = rows_();
  for (let i = 0; i < all.length; i++) if (all[i].id === id) return { row: i + 2, rec: all[i] };
  return null;
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
