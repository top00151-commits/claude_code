# KNK 메일 — 아웃룩 옛 메일 가져오기 (11-25 대표 「기간 5·3·2·1년 · 첨부도 같은 기간 · 폴더 방식 고르기」)
#
# 하는 일: 이 PC 아웃룩의 모든 메일함·폴더(삭제된·보낸·보낼 편지함·임시 보관함·정크 제외)에서
#   메일 화면에서 고른 기간의 메일을 최근 것부터 한 통씩 KNK 메일(내 메일함)로 보냅니다.
#   · 아웃룩의 메일은 바꾸지도 지우지도 않습니다(읽기만) · 첨부는 잠깐 임시 폴더에 꺼냈다가 보내고 바로 지웁니다
#   · 같은 메일은 서버가 건너뜁니다 · 중간에 끊기면 같은 명령을 다시 실행하면 이어서 합니다
#   · 보내는 곳은 회사 서버(works.knknara.co.kr) 한 곳뿐입니다
#
# 실행: 메일 › 설정·정리 › 「아웃룩 옛 메일 가져오기」 화면에서 번호를 만들고, 그 화면의 한 줄을 PowerShell 에 붙여 넣습니다.

param(
    [Parameter(Mandatory = $true)][string]$Code,
    [string]$Server = 'https://works.knknara.co.kr'
)
$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$MaxAttach = 30MB
$PR_MSGID = 'http://schemas.microsoft.com/mapi/proptag/0x1035001F'
$PR_SMTP  = 'http://schemas.microsoft.com/mapi/proptag/0x5D01001F'
$PR_RSMTP = 'http://schemas.microsoft.com/mapi/proptag/0x39FE001F'
$PR_HDRS  = 'http://schemas.microsoft.com/mapi/proptag/0x007D001F'
$PR_CID   = 'http://schemas.microsoft.com/mapi/proptag/0x3712001F'

function Post-Json($path, $obj) {
    $json = $obj | ConvertTo-Json -Depth 6 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Method Post -Uri ($Server + $path) -Body $bytes -ContentType 'application/json; charset=utf-8' -TimeoutSec 600
        return ($r.Content | ConvertFrom-Json)
    } catch {
        $code = 0
        try { $code = [int]$_.Exception.Response.StatusCode } catch { }
        $res = $null
        try {
            $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $res = ($sr.ReadToEnd() | ConvertFrom-Json)
        } catch { }
        if (-not $res) { $res = [pscustomobject]@{ ok = $false; result = 'fail'; message = ('연결 오류 ' + $code) } }
        $res | Add-Member -NotePropertyName http -NotePropertyValue $code -Force
        return $res
    }
}

Write-Host '서버에 번호를 확인하는 중입니다…'
$chk = Post-Json '/api/mail/import-outlook/check' @{ code = $Code }
if (-not $chk.ok) {
    Write-Host ('⚠ 끝나지 않았습니다 — ' + $chk.message) -ForegroundColor Red
    Write-Host '👉 남은 일 — 메일 화면에서 새 번호를 만들어 그 화면의 명령을 다시 실행해 주세요.'
    return
}
if ($chk.disk_ok -eq $false) {
    Write-Host '⚠ 끝나지 않았습니다 — 서버 남은 공간이 모자랍니다. 빅터에게 알려 주세요.' -ForegroundColor Red
    return
}
$since = [datetime]::ParseExact([string]$chk.since, 'yyyy-MM-dd', $null)
Write-Host ('기간: ' + $chk.since + ' 부터(' + $chk.years + '년) · 폴더: ' + $chk.mode_name)

Write-Host '아웃룩을 여는 중입니다… (아웃룩이 「허용」을 물으면 허용해 주세요)'
try {
    $ol = New-Object -ComObject Outlook.Application
    $ns = $ol.GetNamespace('MAPI')
} catch {
    Write-Host '⚠ 끝나지 않았습니다 — 아웃룩을 열지 못했습니다. 예전(클래식) 아웃룩이 설치된 PC 에서 실행해 주세요.' -ForegroundColor Red
    return
}
# 건너뛸 폴더: 삭제된 편지함(3) · 보낼 편지함(4) · 보낸 편지함(5) · 임시 보관함(16) · 정크 메일(23)
$skip = @{}
foreach ($id in 3, 4, 5, 16, 23) { try { $skip[$ns.GetDefaultFolder($id).EntryID] = $true } catch { } }

# 1) 기간 안 메일 목록(번호·시각·폴더만) — 최근 것부터 보내려고 먼저 모음
$list = New-Object System.Collections.Generic.List[object]
function Walk-Folder($f) {
    if ($skip.ContainsKey($f.EntryID)) { return }
    $sid = $f.StoreID
    $n = 0
    try {
        foreach ($m in $f.Items) {
            try {
                if ($m.Class -ne 43) { continue }
                $t = $m.ReceivedTime
                if ($t -lt $since) { continue }
                $list.Add([pscustomobject]@{ e = $m.EntryID; s = $sid; t = $t; p = $f.FolderPath })
                $n++
            } catch { }
        }
    } catch { }
    if ($n -gt 0) { Write-Host ('  · ' + $f.FolderPath + ' — ' + $n + '통') }
    foreach ($sub in $f.Folders) { Walk-Folder $sub }
}
foreach ($st in $ns.Stores) {
    try { Write-Host ('메일함: ' + $st.DisplayName); Walk-Folder $st.GetRootFolder() } catch { }
}
$items = @($list | Sort-Object -Property t -Descending)
$total = $items.Count
Write-Host ('보낼 메일: ' + $total + '통 (최근 것부터)')

# 이어하기 — 이미 보낸 메일 표시(바탕화면 진행 파일)
$desk = [Environment]::GetFolderPath('Desktop')
$progFile = Join-Path $desk 'KNK_아웃룩_가져오기_진행.txt'
$done = @{}
if (Test-Path -LiteralPath $progFile) { foreach ($ln in [System.IO.File]::ReadAllLines($progFile)) { if ($ln) { $done[$ln] = $true } } }
$tmp = Join-Path $env:TEMP ('knk_imp_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

function Smtp-Of($entry, $pa, $fallback) {
    $a = ''
    try { if ($entry -and $entry.Type -eq 'EX') { $x = $entry.GetExchangeUser(); if ($x) { $a = $x.PrimarySmtpAddress } } } catch { }
    if (-not $a -or $a -notmatch '@') { try { $a = $pa.GetProperty($PR_RSMTP) } catch { } }
    if (-not $a -or $a -notmatch '@') { $a = $fallback }
    return [string]$a
}

$saved = 0; $skipped = 0; $failed = 0; $streak = 0; $k = 0
$stopWhy = ''
foreach ($it in $items) {
    $k++
    if ($done.ContainsKey($it.e)) { $skipped++; continue }
    $m = $null
    try { $m = $ns.GetItemFromID($it.e, $it.s) } catch { }
    if (-not $m) { $failed++; continue }
    try {
        $mid = ''
        try { $mid = [string]$m.PropertyAccessor.GetProperty($PR_MSGID) } catch { }
        $from = ''
        try {
            if ($m.SenderEmailType -eq 'EX') { $x = $m.Sender.GetExchangeUser(); if ($x) { $from = $x.PrimarySmtpAddress } } else { $from = $m.SenderEmailAddress }
        } catch { }
        if (-not $from -or $from -notmatch '@') { try { $from = $m.PropertyAccessor.GetProperty($PR_SMTP) } catch { } }
        $to = New-Object System.Collections.Generic.List[string]
        $cc = New-Object System.Collections.Generic.List[string]
        foreach ($r in $m.Recipients) {
            try {
                $ad = Smtp-Of $r.AddressEntry $r.PropertyAccessor $r.Address
                if ($r.Name -and $r.Name -ne $ad) { $s1 = $r.Name + ' <' + $ad + '>' } else { $s1 = $ad }
                if ($r.Type -eq 2) { $cc.Add($s1) } elseif ($r.Type -eq 1) { $to.Add($s1) }
            } catch { }
        }
        $hdr = ''
        try { $hdr = [string]$m.PropertyAccessor.GetProperty($PR_HDRS) } catch { }
        $html = ''
        try { $html = [string]$m.HTMLBody } catch { }
        $text = ''
        try { $text = [string]$m.Body } catch { }
        $atts = New-Object System.Collections.Generic.List[object]
        $dropped = 0
        $sum = [int64]0
        try { foreach ($a in $m.Attachments) { $sum += [int64]$a.Size } } catch { }
        if ($sum -gt $MaxAttach) {
            try { $dropped = $m.Attachments.Count } catch { $dropped = 1 }
        } else {
            $ai = 0
            foreach ($a in $m.Attachments) {
                $ai++
                try {
                    $fn = [string]$a.FileName
                    if (-not $fn) { $fn = 'attachment' + $ai }
                    $p = Join-Path $tmp ([string]$ai + '_' + ($fn -replace '[\\/:*?"<>|]', '_'))
                    $a.SaveAsFile($p)
                    $b = [System.IO.File]::ReadAllBytes($p)
                    Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
                    $cid = ''
                    try { $cid = [string]$a.PropertyAccessor.GetProperty($PR_CID) } catch { }
                    $inl = [bool]($cid -and $html -and $html.Contains('cid:' + $cid))
                    $atts.Add(@{ name = $fn; mime = ''; b64 = [Convert]::ToBase64String($b); content_id = $cid; inline = $inl })
                } catch { $dropped++ }
            }
        }
        $sentOn = ''
        try { $sentOn = $m.SentOn.ToString('yyyy-MM-dd HH:mm:ss') } catch { }
        $mail = @{
            message_id = $mid; received_at = $it.t.ToString('yyyy-MM-dd HH:mm:ss'); sent_at = $sentOn
            from_email = [string]$from; from_name = [string]$m.SenderName
            to = ($to -join ', '); cc = ($cc -join ', '); subject = [string]$m.Subject
            html = $html; text = $text; folder_path = [string]$it.p; transport_headers = $hdr
            attachments = $atts; att_dropped = $dropped
        }
        $res = Post-Json '/api/mail/import-outlook/mail' @{ code = $Code; mail = $mail }
        if ($res.http -eq 413) {
            $mail.att_dropped = $dropped + $atts.Count
            $mail.attachments = @()
            $res = Post-Json '/api/mail/import-outlook/mail' @{ code = $Code; mail = $mail }
        }
        $rr = [string]$res.result
        if ($rr -eq 'saved') { $saved++; $streak = 0 }
        elseif ($rr -eq 'skip' -or $rr -eq 'outside') { $skipped++; $streak = 0 }
        elseif ($rr -eq 'disk') { $stopWhy = 'disk'; break }
        elseif ($rr -eq 'token') { $stopWhy = 'token'; break }
        else { $failed++; $streak++ }
        if ($rr -eq 'saved' -or $rr -eq 'skip' -or $rr -eq 'outside') {
            [System.IO.File]::AppendAllText($progFile, $it.e + [Environment]::NewLine)
        }
        if ($streak -ge 20) { $stopWhy = 'net'; break }
    } catch { $failed++; $streak++ }
    if ($k % 10 -eq 0 -or $k -eq $total) {
        Write-Host ('  ' + $k + ' / ' + $total + ' · 가져옴 ' + $saved + ' · 건너뜀 ' + $skipped + ' · 실패 ' + $failed)
    }
}
Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ''
if ($stopWhy -eq 'disk') {
    Write-Host '⚠ 끝나지 않았습니다 — 서버 남은 공간이 모자라 멈췄습니다. 빅터에게 알려 주세요(가져온 메일은 그대로 있습니다).' -ForegroundColor Red
} elseif ($stopWhy -eq 'token') {
    Write-Host '⚠ 끝나지 않았습니다 — 번호가 끝났습니다(멈춤·기한). 메일 화면에서 새 번호를 만들어 다시 실행하면 이어서 합니다.' -ForegroundColor Yellow
} elseif ($stopWhy -eq 'net') {
    Write-Host '⚠ 끝나지 않았습니다 — 연속으로 20통이 실패해 멈췄습니다(인터넷 연결 확인). 같은 명령을 다시 실행하면 이어서 합니다.' -ForegroundColor Yellow
} else {
    $fin = Post-Json '/api/mail/import-outlook/done' @{ code = $Code }
    if ($failed -gt 0) {
        Write-Host ('👉 남은 일 — ' + $saved + '통을 가져왔고 실패 ' + $failed + '통이 남았습니다. 메일 화면에서 새 번호를 만들어 다시 실행하면 실패한 것만 다시 보냅니다.') -ForegroundColor Yellow
    } else {
        Write-Host ('✅ 완료 — 이 작업은 끝났습니다. ' + $saved + '통을 가져왔고, ' + $skipped + '통은 이미 있어 건너뛰었습니다.') -ForegroundColor Green
        Write-Host '   더 하실 일은 없습니다. 이 창을 닫으셔도 됩니다(바탕화면 KNK_아웃룩_가져오기_진행.txt 는 지우셔도 됩니다).'
    }
}
