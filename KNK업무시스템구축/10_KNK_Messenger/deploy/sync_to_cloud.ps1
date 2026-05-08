# ============================================================
# KNK Messenger - 로컬(Windows) -> 클라우드(Lightsail Ubuntu) 동기화
# ============================================================
# 사용 시나리오:
#   1) 빅터/대표가 로컬에서 코드 수정
#   2) 이 스크립트 1번 실행 -> 변경된 파일만 서버로 업로드
#   3) 서버 자동 재시작 + 헬스체크
#   4) https://msg.knknara.co.kr 에서 즉시 확인
#
# 첫 사용 전 환경변수 1회 설정 (PowerShell 영구):
#   [Environment]::SetEnvironmentVariable("KNK_CLOUD_HOST", "1.2.3.4", "User")
#   [Environment]::SetEnvironmentVariable("KNK_CLOUD_KEY",  "C:\Users\top00\.ssh\lightsail.pem", "User")
#   (PowerShell 창 새로 열기)
#
# 실행:
#   cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\10_KNK_Messenger"
#   .\deploy\sync_to_cloud.ps1
#
# 옵션:
#   -Server <IP>      환경변수 무시하고 직접 지정
#   -KeyFile <path>   환경변수 무시하고 직접 지정
#   -SkipRestart      파일만 동기화하고 서비스 재시작 안 함
#   -Verbose          scp 상세 로그
# ============================================================

[CmdletBinding()]
param(
    [string]$Server  = $env:KNK_CLOUD_HOST,
    [string]$KeyFile = $env:KNK_CLOUD_KEY,
    [string]$RemoteDir = "/opt/knk_messenger",
    [string]$RemoteUser = "ubuntu",
    [switch]$SkipRestart
)

$ErrorActionPreference = "Stop"

function Fail($msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    exit 1
}
function Info($msg) {
    Write-Host "[*] $msg" -ForegroundColor Cyan
}
function Ok($msg) {
    Write-Host "[OK] $msg" -ForegroundColor Green
}

# --- 사전 점검 ---
if (-not $Server)  { Fail "Server IP 가 없습니다. KNK_CLOUD_HOST 환경변수 설정 또는 -Server 인자 사용" }
if (-not $KeyFile) { Fail "SSH 키 경로가 없습니다. KNK_CLOUD_KEY 환경변수 설정 또는 -KeyFile 인자 사용" }
if (-not (Test-Path $KeyFile)) { Fail "SSH 키 파일이 없습니다: $KeyFile" }
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Fail "ssh 명령어가 없습니다. Windows 10+ '설정 > 앱 > 선택적 기능 > OpenSSH 클라이언트' 설치 필요"
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "===============================================" -ForegroundColor Yellow
Write-Host "  KNK Messenger -> Cloud Sync" -ForegroundColor Yellow
Write-Host "  Server:  ${RemoteUser}@${Server}:${RemoteDir}"
Write-Host "  Local:   $ProjectRoot"
Write-Host "===============================================" -ForegroundColor Yellow
Write-Host ""

# --- 1) 코드 동기화 ---
Info "1/3 Syncing files (scp)..."

# 동기화 대상: 코드/템플릿/정적/배포 스크립트만. data/ backups/ .venv/ 제외
$Items = @(
    "app.py",
    "wsgi.py",
    "requirements.txt",
    "templates",
    "static",
    "deploy"
)

# 임시 tar로 압축 후 한 번에 전송 (개별 scp보다 10배 빠름)
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Tarball = Join-Path $env:TEMP "knk_sync_$Stamp.tar.gz"

# Windows 10+ 내장 tar 사용
$TarArgs = @("-czf", $Tarball, "--exclude=__pycache__", "--exclude=*.pyc") + $Items
$tarOut = & tar @TarArgs 2>&1
if ($LASTEXITCODE -ne 0) { Fail "tar 압축 실패: $tarOut" }

$TarSize = [math]::Round((Get-Item $Tarball).Length / 1KB, 1)
Info "  archive: $Tarball ($TarSize KB)"

# 서버로 업로드
$ScpOut = & scp -i $KeyFile -q $Tarball "${RemoteUser}@${Server}:/tmp/knk_sync.tar.gz" 2>&1
if ($LASTEXITCODE -ne 0) { Fail "scp 실패: $ScpOut" }
Ok "  upload done"

# 서버에서 풀기
$ExtractCmd = "cd $RemoteDir && sudo tar -xzf /tmp/knk_sync.tar.gz && sudo chown -R ${RemoteUser}:${RemoteUser} . && rm /tmp/knk_sync.tar.gz"
$ExtractOut = & ssh -i $KeyFile -o StrictHostKeyChecking=accept-new "${RemoteUser}@${Server}" $ExtractCmd 2>&1
if ($LASTEXITCODE -ne 0) { Fail "원격 압축 해제 실패: $ExtractOut" }
Ok "  extract done"

Remove-Item $Tarball -ErrorAction SilentlyContinue

if ($SkipRestart) {
    Ok "DONE (재시작 생략)"
    exit 0
}

# --- 2) 서비스 재시작 ---
Info "2/3 Restarting service..."
$RestartCmd = "sudo systemctl restart knk-messenger; sleep 2"
& ssh -i $KeyFile "${RemoteUser}@${Server}" $RestartCmd
Ok "  restarted"

# --- 3) 헬스체크 ---
Info "3/3 Health check..."
$HealthCmd = "curl -fs -o /dev/null -w '%{http_code}' http://127.0.0.1:5050/login || echo 000"
$Status = & ssh -i $KeyFile "${RemoteUser}@${Server}" $HealthCmd
$Status = "$Status".Trim()

if ($Status -eq "200" -or $Status -eq "302") {
    Ok "  HTTP $Status - server responding"
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "  SYNC COMPLETE" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
} else {
    Write-Host "[FAIL] HTTP $Status - server not healthy" -ForegroundColor Red
    Write-Host ""
    Write-Host "Last 30 log lines:" -ForegroundColor Yellow
    & ssh -i $KeyFile "${RemoteUser}@${Server}" "sudo journalctl -u knk-messenger -n 30 --no-pager"
    exit 2
}
