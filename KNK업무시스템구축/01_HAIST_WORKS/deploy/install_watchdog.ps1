# ============================================================
# KNK 자동복구 워치독 설치 (대표 지시 2026-06-21 "앱 자동 재시작 강화")
# ------------------------------------------------------------
# 컨테이너별로 워치독을 올리고(base64) + 부팅 자동기동 훅(.bash_profile) + 즉시 기동.
# 본 deploy 스크립트는 안 건드림(격리). 원격 명령은 base64 전송 → 따옴표/한글 깨짐 0.
# 사용법(본인 PC PowerShell):
#   ./install_watchdog.ps1 -Port 32201   # WORKS  (works_watchdog.sh, supervisorctl restart)
#   ./install_watchdog.ps1 -Port 32203   # 메일    (mail_watchdog.sh, python healthz·직접 재기동)
#   - SSH 비밀번호는 실행 중 직접 입력(스크립트에 저장 안 함).
# 안전: 읽기 아님(설치). 단 워치독 파일 배치 + 훅 1줄 추가 + 기동만. 앱 코드/DB 무변경.
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]$Port       = 32201,
    [string]$User    = "root"
)
$ErrorActionPreference = "Stop"
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")

function Invoke-Remote([string]$bash) {
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
}

if ($Port -eq 32203) {
    $wdLocal  = Join-Path $PSScriptRoot "..\..\15_KNK_Mail\mail_watchdog.sh"
    $wdRemote = "/opt/knk_mail/mail_watchdog.sh"
    $rdir     = "/opt/knk_mail"
    $tag      = "KNK-MAIL-WATCHDOG-START"
    $pat      = "[m]ail_watchdog.sh"
    $name     = "메일"
} elseif ($Port -eq 32201) {
    $wdLocal  = Join-Path $PSScriptRoot "works_watchdog.sh"
    $wdRemote = "/opt/knk_haist/deploy/works_watchdog.sh"
    $rdir     = "/opt/knk_haist/deploy"
    $tag      = "KNK-WORKS-WATCHDOG-START"
    $pat      = "[w]orks_watchdog.sh"
    $name     = "WORKS"
} else {
    Write-Host "지원 안 함 Port=$Port (32201=WORKS / 32203=메일)" -ForegroundColor Red
    return
}

if (-not (Test-Path $wdLocal)) {
    Write-Host "워치독 파일 없음: $wdLocal" -ForegroundColor Red
    return
}

# sh 스크립트는 LF 로 정규화(CRLF 섞이면 'bad interpreter' 오류)
$wd = (Get-Content -Raw -Encoding UTF8 $wdLocal) -replace "`r`n", "`n"
$wdb64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($wd))

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ("  {0} 워치독 설치 -> {1}:{2}" -f $name, $SshHost, $Port) -ForegroundColor Cyan
Write-Host "  (SSH 비밀번호를 물으면 직접 입력하세요)" -ForegroundColor Yellow
Write-Host "=================================================="

$inst = @"
set +e
mkdir -p $rdir 2>/dev/null
echo $wdb64 | base64 -d > $wdRemote
chmod +x $wdRemote
echo "[file]"; ls -la $wdRemote
if sh -n $wdRemote 2>/dev/null; then echo "[syntax OK]"; else echo "[SYNTAX ERROR - 설치 중단 권장]"; fi
if grep -q '$tag' /root/.bash_profile 2>/dev/null; then
  echo "[hook already exists]"
else
  printf '\n# %s (auto-recover on crash/hang)\npgrep -f "%s" >/dev/null 2>&1 || setsid /bin/sh %s >/dev/null 2>&1 &\n' '$tag' '$pat' '$wdRemote' >> /root/.bash_profile
  echo "[hook added to .bash_profile]"
fi
pgrep -f "$pat" >/dev/null 2>&1 || setsid /bin/sh $wdRemote >/dev/null 2>&1 &
sleep 3
echo "[watchdog proc]"; pgrep -af "$pat" 2>/dev/null | head
echo "[done]"
"@
Invoke-Remote $inst
Write-Host "`n[설치 완료] 위 출력에서 [syntax OK] 와 [watchdog proc](프로세스 보임)을 확인하고, 출력을 빅터에게 붙여주세요." -ForegroundColor Green
