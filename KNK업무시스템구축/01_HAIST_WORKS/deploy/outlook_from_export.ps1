# KNK 메일 — 예전 아웃룩에서 「보낸 사람」만 뽑기 (11-25 대표 「예전 아웃룩에 남아있는데 어떻게 전달하지?」)
#
# 하는 일(읽기만 · 아웃룩의 메일을 바꾸거나 지우거나 옮기지 않음):
#   아웃룩의 모든 메일함·모든 폴더(삭제된 편지함·보낸 편지함 제외)에서 2026-05-25 ~ 2026-11-30 에 받은 메일의
#   4칸만 뽑아 바탕화면에 CSV 파일로 저장합니다.
#     ① 메일 번호(Message-ID) ② 보낸 사람 주소 ③ 보낸 사람 이름 ④ 받은 시각
#   제목·본문·첨부는 읽지 않습니다.
# 다음: 메일 › 설정·정리 › 「아웃룩에서 보낸 사람 채우기」 화면에서 이 파일을 올립니다.
#
# 실행(PowerShell 창에서 · 아웃룩이 설치된 PC):
#   powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\Downloads\outlook_from_export.ps1"

$ErrorActionPreference = 'Continue'
$From = Get-Date '2026-05-25 00:00:00'
$To   = Get-Date '2026-11-30 23:59:59'
$PR_MSGID  = 'http://schemas.microsoft.com/mapi/proptag/0x1035001F'
$PR_SMTP   = 'http://schemas.microsoft.com/mapi/proptag/0x5D01001F'

Write-Host '아웃룩을 여는 중입니다… (처음이면 아웃룩 창에서 「허용」을 물을 수 있습니다)'
try {
    $ol = New-Object -ComObject Outlook.Application
    $ns = $ol.GetNamespace('MAPI')
} catch {
    Write-Host '⚠ 아웃룩을 열지 못했습니다. 아웃룩이 설치된 PC 에서 실행해 주세요.' -ForegroundColor Red
    return
}

# 건너뛸 폴더: 삭제된 편지함(3) · 보낸 편지함(5) · 보낼 편지함(4) · 임시 보관함(16)
$skip = @{}
foreach ($id in 3, 4, 5, 16) {
    try { $skip[$ns.GetDefaultFolder($id).EntryID] = $true } catch { }
}

$seen = @{}
$rows = New-Object System.Collections.Generic.List[object]
$script:err = 0

function Get-SenderAddr($m) {
    $a = ''
    try {
        if ($m.SenderEmailType -eq 'EX') {
            $ex = $m.Sender.GetExchangeUser()
            if ($ex) { $a = $ex.PrimarySmtpAddress }
        } else {
            $a = $m.SenderEmailAddress
        }
    } catch { }
    if (-not $a -or $a -notmatch '@') {
        try { $a = $m.PropertyAccessor.GetProperty($PR_SMTP) } catch { }
    }
    return [string]$a
}

function Walk-Folder($f) {
    if ($skip.ContainsKey($f.EntryID)) { return }
    $n = 0
    try {
        $items = $f.Items
        foreach ($m in $items) {
            try {
                if ($m.Class -ne 43) { continue }          # 43 = 메일
                $t = $m.ReceivedTime
                if ($t -lt $From -or $t -gt $To) { continue }
                $mid = ''
                try { $mid = [string]$m.PropertyAccessor.GetProperty($PR_MSGID) } catch { }
                $mid = $mid.Trim().Trim('<', '>').Trim()
                if (-not $mid) { continue }
                if ($seen.ContainsKey($mid)) { continue }
                $seen[$mid] = $true
                $rows.Add([pscustomobject]@{
                    message_id  = $mid
                    from_email  = (Get-SenderAddr $m)
                    from_name   = [string]$m.SenderName
                    received_at = $t.ToString('yyyy-MM-dd HH:mm:ss')
                })
                $n++
            } catch { $script:err++ }
        }
    } catch { $script:err++ }
    Write-Host ('  · ' + $f.FolderPath + ' — ' + $n + '통')
    foreach ($sub in $f.Folders) { Walk-Folder $sub }
}

foreach ($st in $ns.Stores) {
    try {
        Write-Host ('메일함: ' + $st.DisplayName)
        Walk-Folder $st.GetRootFolder()
    } catch { $script:err++ }
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmm'
$out = Join-Path ([Environment]::GetFolderPath('Desktop')) ('KNK_아웃룩_보낸사람_' + $stamp + '.csv')
$csv = $rows | ConvertTo-Csv -NoTypeInformation
[System.IO.File]::WriteAllLines($out, $csv, (New-Object System.Text.UTF8Encoding($true)))

Write-Host ''
Write-Host ('✅ ' + $rows.Count + '통 저장 · 파일 위치: ' + $out) -ForegroundColor Green
if ($script:err -gt 0) { Write-Host ('(읽지 못하고 건너뛴 메일 ' + $script:err + '개)') }
Write-Host '이제 메일 › 설정·정리 › 「아웃룩에서 보낸 사람 채우기」 화면에서 이 파일을 올려 주세요.'
