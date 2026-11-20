# ALCOHOLIDAY editing部：Tシャツ「1966 ISLAY WAS FRUIT」宣伝動画 v2（案内役A・明るい版／2026-10-10-02）の Higgsfield 動画生成 v1
# 2026-10-10 社長指示：案内役Aの女性で、2026-10-03-02 と同じスタイル。前回より少し動きのある動画。話し方は明るく朗らか。
# ①話す（Kling 3.0・声あり・上限 $0.70）②Tシャツのアップ（Kling 3.0・声なし・上限 $0.40）③乾杯（Kling 3.0・声あり・上限 $0.70）
# 前回の学び：プリントの近くの布は動かさない（文字が崩れる）。動きは顔・頭・手・グラス・髪・背景の光で出す。
# 同名ファイルがあれば生成しない（二重課金防止）。使い方: generate-kling-v1.ps1 [名前...]（省略時は全部）
param([string[]]$Only)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$envFile = 'C:\Users\abetk\Desktop\AIアルコホリディ\.env'
$key = ''
if (Test-Path -LiteralPath $envFile) { $key = (Get-Content -LiteralPath $envFile -Encoding UTF8 | Where-Object { $_ -match '^HF_KEY=' }) -replace '^HF_KEY=', '' }
if ([string]::IsNullOrWhiteSpace($key)) { $key = [Environment]::GetEnvironmentVariable('HF_KEY','User') }
if ([string]::IsNullOrWhiteSpace($key)) { throw 'HF_KEY is not available.' }
$headers = @{ Authorization = "Key $($key.Trim())" }

$root = $PSScriptRoot
$designDir = Join-Path $root '..\..\..\design\成果物\2026-10-10-02'
$lock = "The camera is completely locked off like a tripod shot: no zoom, no push-in, no drift, no pan, no camera movement at all."
$print = "The yellow print on her black T-shirt (the words '1966', 'ISLAY', 'WAS', 'FRUIT' and the seagull line drawing) stays exactly the same: same letters, same spelling, same shapes, perfectly upright typewriter-style serif letters, never italic, never slanted, never redrawn, never morphing."
$face = "Her face stays exactly the same person as in the first frame in every frame: same eyes, same eyebrows, same nose, same lips, same face shape, same bangs; her identity never changes."
$negBase = 'zoom, zooming in, zooming out, camera push-in, dolly, pan, tilt, camera shake, garbled text, changing letters, misspelled words, nonsense text, extra text, new text, morphing print, print redrawing, italic letters, slanted letters, warped logo, extra fingers, deformed hands, distorted face, face morphing, identity change, different person, teeth distortion, flicker, watermark, captions, subtitles'

$k3 = 'kling-video/v3.0/std/image-to-video'
$items = @(
  @{ name='a-talk-kling3-sound-v1'; image='tshirt1966-A-base.png'; model=$k3; max=[decimal]0.70;
     extra=@{ sound='on' };
     prompt="$lock $print A cheerful young Japanese woman with a black bob haircut at a warm whisky bar counter. She starts with a bright, curious look, tilts her head playfully to one side, then lifts her left hand beside her face (away from her chest) in a small friendly wave and leans her head a little toward the camera as she talks. She speaks to the viewer in natural, fluent Japanese, in a bright, cheerful, warm and friendly young female voice, lively and smiling while she talks: 「ねえ、この意味わかる？シングルモルト好きなら、わかるよね！」 Her lips move in exact sync with the Japanese words. She says only this sentence, nothing else. Her eyes sparkle and her expression is happy and lively, her bob hair sways softly. Her chest and the T-shirt print stay calm and do not twist; her hand never covers the print. Audio: only her voice and a very faint quiet bar ambience, no music, no other voices. The warm bokeh lights of the bar glimmer in the background. Avoid: $negBase, hand covering the chest, body twisting, music, singing, English speech, extra words" },
  @{ name='closeup-kling3-v1'; image='tshirt1966-A-closeup-v1-blend.png'; model=$k3; max=[decimal]0.50;
     extra=@{ sound='off' };
     prompt="$lock $print Close-up of a woman's chest wearing a black T-shirt with a yellow print at a whisky bar. The T-shirt fabric and the print do not move at all. In her hand at her side, the whisky on the rocks gently swirls: she slowly turns the glass, the ice cubes rotate and clink, the amber whisky catches the warm light and sparkles. The warm bokeh lights of the bar twinkle in the background. Only the glass, the ice and the whisky move. Realistic cinematic product shot. Avoid: $negBase, fabric movement, wrinkles moving, glass covering the print, face, head, steam, smoke" },
  @{ name='cheers-kling3-sound-v1'; image='tshirt1966-A-cheers-start-v1-blend.png'; model=$k3; max=[decimal]0.70;
     extra=@{ sound='on' };
     prompt="$lock $print A cheerful young Japanese woman with a black bob haircut at a warm whisky bar, holding a whisky glass at shoulder height beside her body. She breaks into a big, bright, happy smile, raises the glass a little toward the camera in a toast and says in a bright, cheerful young female voice in Japanese: 「かんぱい！」 Her lips move in sync. Then she keeps smiling warmly at the camera, eyes crinkling with joy, the ice in the glass clinks and her bob hair sways. The glass and her arm stay outside her chest and never cover the print; her chest and the T-shirt stay calm. Audio: only her voice, the clink of ice and a very faint quiet bar ambience, no music, no other voices. Warm bokeh lights glimmer in the background. Avoid: $negBase, glass covering the print, arm crossing the chest, body twisting, spilling, music, singing, English speech, extra words" },
  # v2（2026-10-10 社長の直し）：「落ち着いた動画に」「動画が進むにつれて前回の動画と顔が同じになる → 元画像に忠実に」「乾杯で画像が二重」
  #   → 動きは小さく、声はゆっくりやさしく。大きな笑顔は顔が変わりやすいので、おだやかな表情だけ。①は A.png、③は A.png の腕だけ直した写真から
  @{ name='a-talk-kling3-sound-v2'; image='tshirt1966-A-base.png'; model=$k3; max=[decimal]0.70;
     extra=@{ sound='on' };
     prompt="$lock $print $face A calm young Japanese woman with a black bob haircut leans quietly against a warm whisky bar counter. She looks into the camera with a calm, gentle face and speaks slowly and softly in natural, fluent Japanese, in a calm, gentle, warm, relaxed female voice, like quietly talking to a friend at a bar: 「ねえ、この意味わかる？シングルモルト好きなら、わかるよね。」 Her lips move in exact sync with the Japanese words. She says only this sentence, nothing else. Very small, slow movements only: a slight gentle tilt of her head, a slow blink, a faint soft smile at the end with lips closed. Her hands stay still at her sides, her shoulders, chest and T-shirt stay still. Audio: only her voice and a very faint quiet bar ambience, no music, no other voices. The warm bokeh lights of the bar softly glimmer in the background. Avoid: $negBase, big smile, laughing, teeth, exaggerated expression, waving, hand gestures, leaning forward, fast movement, music, singing, English speech, extra words" },
  @{ name='cheers-kling3-sound-v2'; image='tshirt1966-A-cheers-start-v2.png'; model=$k3; max=[decimal]0.70;
     extra=@{ sound='on' };
     prompt="$lock $print $face A calm young Japanese woman with a black bob haircut at a warm whisky bar holds a whisky glass on the rocks beside her chest. She slowly and gently lifts the glass a little toward the camera in a quiet toast and says softly in a calm, gentle, warm female voice in Japanese: 「乾杯。」 Her lips move in sync. Then she keeps looking at the camera with a soft, gentle, closed-mouth smile. The ice in the glass clinks softly. Very small, slow movements only; her other arm, her shoulders, chest and T-shirt stay still, and the glass and her hand never cover the print. Audio: only her voice, the soft clink of ice and a very faint quiet bar ambience, no music, no other voices. Warm bokeh lights glimmer softly in the background. Avoid: $negBase, big smile, laughing, teeth, exaggerated expression, raising the glass high, fast movement, glass covering the print, spilling, music, singing, English speech, extra words" }
)

foreach ($item in $items) {
  if ($Only -and ($Only -notcontains $item.name)) { continue }
  Write-Host "=== $($item.name) ==="
  try {
    $image = Join-Path $designDir $item.image
    if (!(Test-Path -LiteralPath $image)) { throw "Input image not found: $($item.image)" }
    $outputPath = Join-Path $root ($item.name + '.mp4')
    if (Test-Path -LiteralPath $outputPath) { Write-Host "Already exists, skipping"; continue }

    $upload = Invoke-RestMethod -Method Post -Uri 'https://api.higgsfield.ai/files/generate-upload-url' -Headers $headers -ContentType 'application/json' -Body '{"content_type":"image/png"}'
    $uploadHeaders = @{}
    if ($upload.upload_headers) { foreach ($h in $upload.upload_headers.PSObject.Properties) { $uploadHeaders[$h.Name] = [string]$h.Value } }
    Invoke-WebRequest -UseBasicParsing -Method Put -Uri $upload.upload_url -Headers $uploadHeaders -InFile $image | Out-Null

    $req = [ordered]@{ prompt=$item.prompt; duration=5; image_url=$upload.public_url }
    foreach ($k in $item.extra.Keys) { $req[$k] = $item.extra[$k] }
    $body = $req | ConvertTo-Json -Depth 8
    $estimate = Invoke-RestMethod -Method Post -Uri ("https://api.higgsfield.ai/estimate/" + $item.model) -Headers $headers -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))
    $usd = [decimal]::Parse([string]$estimate.usd, [Globalization.CultureInfo]::InvariantCulture)
    Write-Host ('Estimate USD: ' + $usd)
    if ($usd -gt $item.max) { throw ('Estimate exceeds safety limit of $' + $item.max) }

    $submit = Invoke-RestMethod -Method Post -Uri ("https://api.higgsfield.ai/" + $item.model) -Headers $headers -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))
    if (!$submit.request_id) { throw 'No request_id returned.' }
    $requestId = [string]$submit.request_id
    $statusUrl = if ($submit.status_url) { [string]$submit.status_url } else { "https://api.higgsfield.ai/requests/$requestId/status" }
    Write-Host ('Submitted: ' + $requestId)
    $deadline = (Get-Date).AddMinutes(15)
    do {
      if ((Get-Date) -gt $deadline) { throw "Timed out. request_id=$requestId (do not resubmit blindly)" }
      Start-Sleep -Seconds 10
      $status = Invoke-RestMethod -Method Get -Uri $statusUrl -Headers $headers
      if ($status.status -in @('failed','nsfw','canceled')) { throw ('Generation ended: ' + $status.status + ' ' + $status.error) }
    } while ($status.status -ne 'completed')
    Invoke-WebRequest -UseBasicParsing -Uri $status.video.url -OutFile $outputPath
    if ((Get-Item -LiteralPath $outputPath).Length -lt 1024) { throw 'Downloaded video is too small.' }
    [ordered]@{ generated_at=(Get-Date).ToString('o'); model=$item.model; request_id=$requestId; estimate_usd=[string]$estimate.usd; source=$item.image; input=$req } |
      ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root ($item.name + '-result.json')) -Encoding UTF8
    Write-Host "DONE $($item.name).mp4"
  } catch {
    Write-Host ('FAILED [' + $item.name + ']: ' + $_.Exception.Message)
  }
}
Write-Host '=== all items processed ==='
