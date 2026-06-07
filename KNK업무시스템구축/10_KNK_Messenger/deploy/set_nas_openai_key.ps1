# ============================================================
# 메신저 OpenAI 키 설정 (NAS) — 대표 지시 2026-05-31
#   대표님이 키를 직접 입력 → NAS /opt/knk_messenger/.env 의 OPENAI_API_KEY 를 갱신 → 메신저 재시작.
#   ※ 이 스크립트에는 키가 들어있지 않습니다. 실행 시 입력받습니다.
#   ※ app.py 가 .env 를 자동 로딩하므로, 한 번 넣으면 재시작에도 영구 유지됩니다.
# ============================================================
$ErrorActionPreference = "Stop"

# --- NAS 접속 설정 (배포 스크립트와 동일 환경변수) ---
$NasHost = if ($env:KNK_NAS_HOST) { $env:KNK_NAS_HOST } else { "o.knknara.co.kr" }
$NasPort = if ($env:KNK_NAS_PORT) { $env:KNK_NAS_PORT } else { "31201" }
$NasUser = if ($env:KNK_NAS_USER) { $env:KNK_NAS_USER } else { "root" }
$KeyFile = $env:KNK_NAS_KEY
$Password = $env:KNK_NAS_PASSWORD

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  메신저 OpenAI 키 설정 (NAS)" -ForegroundColor Cyan
Write-Host "  대상: $NasUser@${NasHost}:$NasPort  /opt/knk_messenger/.env" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "메신저용 OpenAI API 키를 붙여넣고 Enter 를 누르세요." -ForegroundColor Yellow
Write-Host "(보통 'sk-' 로 시작합니다. WORKS 용으로 새로 발급한 키를 같이 써도 됩니다.)" -ForegroundColor Gray
$key = (Read-Host "OpenAI API 키").Trim()

if (-not $key) { Write-Host "[중단] 키가 비어 있습니다." -ForegroundColor Red; exit 1 }
if ($key -notlike "sk-*") {
    Write-Host "[주의] 입력한 값이 'sk-' 로 시작하지 않습니다." -ForegroundColor Yellow
    $yn = Read-Host "그래도 진행할까요? (Y/N)"
    if ($yn -notmatch '^[Yy]') { Write-Host "취소했습니다."; exit 1 }
}

# 키를 base64 로 인코딩해 원격 스크립트에 안전 전달 (따옴표/특수문자 회피)
$keyB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($key))

# 원격 bash — 리터럴 here-string(@'...'@). __KEYB64__ 만 치환.
$bashTemplate = @'
cd /opt/knk_messenger || { echo NO_DIR; exit 1; }
KEY=$(printf '%s' '__KEYB64__' | base64 -d)
if [ -f .env ]; then cp .env ".env.bak.$(date +%s)"; fi
touch .env
grep -v '^[[:space:]]*OPENAI_API_KEY[[:space:]]*=' .env > .env.new 2>/dev/null
printf 'OPENAI_API_KEY="%s"\n' "$KEY" >> .env.new
mv .env.new .env
chmod 600 .env
echo SET_OK
echo "OPENAI_LEN=$(awk -F= '/^OPENAI_API_KEY=/{v=$2; gsub(/["[:space:]]/,"",v); print length(v)}' .env | head -1)"
supervisorctl restart knk-messenger >/dev/null 2>&1
sleep 4
supervisorctl status knk-messenger
echo DONE
'@
$bash = $bashTemplate.Replace('__KEYB64__', $keyB64)
$scriptB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($bash -replace "`r`n", "`n")))
$remote = "echo $scriptB64 | base64 -d | bash"

# --- SSH (배포 스크립트와 동일: 키파일 또는 SSH_ASKPASS 비밀번호) ---
$sshOpts = @("-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=20", "-p", "$NasPort", "-n")
if ($KeyFile -and (Test-Path $KeyFile)) { $sshOpts += @("-i", $KeyFile) }

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "ssh.exe"
$psi.Arguments = ($sshOpts -join " ") + " $NasUser@$NasHost " + '"' + $remote + '"'
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$askpass = $null
if ($Password) {
    $askpass = Join-Path $env:TEMP ("knk_ap_" + [guid]::NewGuid().ToString('N') + ".cmd")
    "@echo off`r`necho $Password" | Set-Content -Encoding ASCII $askpass
    $psi.EnvironmentVariables["DISPLAY"] = ":0"
    $psi.EnvironmentVariables["SSH_ASKPASS"] = $askpass
    $psi.EnvironmentVariables["SSH_ASKPASS_REQUIRE"] = "force"
}

Write-Host ""
Write-Host "NAS 에 적용 중..." -ForegroundColor Cyan
$proc = [System.Diagnostics.Process]::Start($psi)
$out = $proc.StandardOutput.ReadToEnd()
$err = $proc.StandardError.ReadToEnd()
$proc.WaitForExit()
if ($askpass) { Remove-Item $askpass -Force -ErrorAction SilentlyContinue }

Write-Host ""
if (($out -match "SET_OK") -and ($out -match "DONE")) {
    $len = 0
    if ($out -match "OPENAI_LEN=(\d+)") { $len = [int]$Matches[1] }
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "  키 설정 완료 + 메신저 재시작됨" -ForegroundColor Green
    Write-Host "  .env 의 키 길이: $len 자 (0 이면 입력 확인 필요)" -ForegroundColor Green
    if ($out -match "knk-messenger\s+RUNNING") { Write-Host "  메신저 상태: RUNNING" -ForegroundColor Green }
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "이제 메신저를 새로고침(Ctrl+Shift+R) 하고 번역을 해보세요." -ForegroundColor Yellow
} else {
    Write-Host "[실패] 원격 적용이 확인되지 않았습니다." -ForegroundColor Red
    Write-Host "---- 출력 ----" -ForegroundColor Gray
    Write-Host $out
    if ($err) { Write-Host "---- stderr ----" -ForegroundColor Gray; Write-Host $err }
    exit 1
}
