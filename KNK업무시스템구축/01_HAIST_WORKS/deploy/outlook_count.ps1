# KNK 메일 — 아웃룩 메일 「숫자만」 세기 (11-25 대표 「아웃룩에만 있는 옛 메일도 가져올 수 있나 → 진행해봐」)
#
# 하는 일(읽기만 · 아웃룩 메일을 바꾸거나 지우거나 옮기지 않음 · 인터넷으로 아무것도 보내지 않음):
#   아웃룩의 모든 메일함·모든 폴더(삭제된·보낸·보낼 편지함·임시 보관함 제외)의 받은 메일을
#   「해·달별 통수 · 크기(MB) · 첨부 있는 메일 수」로만 셉니다. 제목·본문·보낸 사람은 읽지 않습니다.
#   결과는 이 창에 표로 나오고, 바탕화면에 KNK_아웃룩_메일수_날짜_시각.txt 로도 저장됩니다.
#
# 실행(PowerShell 창 · 아웃룩을 켜 둔 PC):
#   powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\Downloads\outlook_count.ps1"

$ErrorActionPreference = 'Continue'
Write-Host '아웃룩을 여는 중입니다… (아웃룩이 「허용」을 물으면 허용해 주세요)'
try {
    $ol = New-Object -ComObject Outlook.Application
    $ns = $ol.GetNamespace('MAPI')
} catch {
    Write-Host '⚠ 아웃룩을 열지 못했습니다. 예전(클래식) 아웃룩이 설치된 PC 에서 실행해 주세요.' -ForegroundColor Red
    return
}
$skip = @{}
foreach ($id in 3, 4, 5, 16) { try { $skip[$ns.GetDefaultFolder($id).EntryID] = $true } catch { } }

$byMonth = @{}   # 'yyyy-MM' -> @(통수, 바이트, 첨부있는통수)
$script:total = 0; $script:err = 0

function Walk-Folder($f) {
    if ($skip.ContainsKey($f.EntryID)) { return }
    $n = 0
    try {
        foreach ($m in $f.Items) {
            try {
                if ($m.Class -ne 43) { continue }
                $k = $m.ReceivedTime.ToString('yyyy-MM')
                if (-not $byMonth.ContainsKey($k)) { $byMonth[$k] = @(0, [double]0, 0) }
                $v = $byMonth[$k]
                $v[0] += 1
                $v[1] += [double]$m.Size
                if ($m.Attachments.Count -gt 0) { $v[2] += 1 }
                $n++; $script:total++
            } catch { $script:err++ }
        }
    } catch { $script:err++ }
    if ($n -gt 0) { Write-Host ('  · ' + $f.FolderPath + ' — ' + $n + '통') }
    foreach ($sub in $f.Folders) { Walk-Folder $sub }
}
foreach ($st in $ns.Stores) {
    try { Write-Host ('메일함: ' + $st.DisplayName); Walk-Folder $st.GetRootFolder() } catch { $script:err++ }
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add('KNK 아웃룩 메일 수 (숫자만) · ' + (Get-Date -Format 'yyyy-MM-dd HH:mm'))
$lines.Add('달        통수     크기(MB)   첨부있는통수')
$years = @{}
foreach ($k in ($byMonth.Keys | Sort-Object)) {
    $v = $byMonth[$k]
    $lines.Add(('{0}  {1,7}  {2,10:N0}  {3,10}' -f $k, $v[0], ($v[1] / 1MB), $v[2]))
    $y = $k.Substring(0, 4)
    if (-not $years.ContainsKey($y)) { $years[$y] = @(0, [double]0) }
    $years[$y][0] += $v[0]; $years[$y][1] += $v[1]
}
$lines.Add('')
$lines.Add('해별 합계')
$sumB = [double]0
foreach ($y in ($years.Keys | Sort-Object)) {
    $lines.Add(('{0}년  {1,7}통  {2,10:N0} MB' -f $y, $years[$y][0], ($years[$y][1] / 1MB)))
    $sumB += $years[$y][1]
}
$lines.Add(('전체   {0,7}통  {1,10:N0} MB  (읽지 못하고 건너뛴 것 {2}개)' -f $script:total, ($sumB / 1MB), $script:err))

Write-Host ''
$lines | ForEach-Object { Write-Host $_ }
$out = Join-Path ([Environment]::GetFolderPath('Desktop')) ('KNK_아웃룩_메일수_' + (Get-Date -Format 'yyyyMMdd_HHmm') + '.txt')
[System.IO.File]::WriteAllLines($out, $lines, (New-Object System.Text.UTF8Encoding($true)))
Write-Host ''
Write-Host ('✅ 저장: ' + $out) -ForegroundColor Green
Write-Host '이 표(해별 합계)를 사진이나 글로 알려 주시면 기간·첨부를 정해 가져오기를 만들겠습니다.'
