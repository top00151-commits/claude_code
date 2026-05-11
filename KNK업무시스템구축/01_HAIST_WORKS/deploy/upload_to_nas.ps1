# ============================================================
# HAIST WORKS — Windows PC → NAS Ubuntu 컨테이너 업로드
# v5H226z76 (2026-05-11)
# ============================================================
# 사용법:
#   PowerShell:
#     cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS"
#     ./deploy/upload_to_nas.ps1
#
# 옵션:
#   -External  : o.knknara.co.kr:31201 (외부에서)
#   -Internal  : 192.168.12.5:31201    (회사 LAN)
#   -DryRun    : tar 만 만들고 업로드 안 함
# ============================================================
param(
    [switch]$Internal,
    [switch]$External = $true,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$SourceRoot = (Split-Path -Parent $PSScriptRoot)
Set-Location $SourceRoot

if ($Internal) {
    $NAS_HOST = "192.168.12.5"
} else {
    $NAS_HOST = "o.knknara.co.kr"
}
$NAS_PORT = "31201"
$NAS_USER = "root"
$REMOTE_TMP = "/tmp/knk_haist_sync.tar.gz"
$REMOTE_DIR = "/opt/knk_haist"

Write-Host "=================================================="
Write-Host "  HAIST WORKS → ${NAS_USER}@${NAS_HOST}:${NAS_PORT}"
Write-Host "  Source: ${SourceRoot}"
Write-Host "  Target: ${REMOTE_DIR}"
Write-Host "=================================================="

# 1. 로컬 tar 만들기 (Git Bash 또는 WSL의 tar 사용)
$TarFile = "$env:TEMP\knk_haist_sync.tar.gz"
Write-Host "[1/3] tar 생성: $TarFile"

# Windows 10/11 기본 tar 사용
tar --exclude='data/*.db' `
    --exclude='data/*.db-journal' `
    --exclude='data/backups' `
    --exclude='uploads/*' `
    --exclude='__pycache__' `
    --exclude='*.pyc' `
    --exclude='.venv' --exclude='venv' `
    --exclude='*.log' --exclude='server.log' `
    --exclude='HAIST WORKS디자인변경' --exclude='참고자료' `
    --exclude='_audit_*.py' `
    -czf "$TarFile" `
    app run.py requirements.txt Dockerfile .dockerignore .env.synology.example Synology_배포가이드.md deploy scripts static

$TarSize = (Get-Item $TarFile).Length / 1MB
Write-Host "    완료 — $([math]::Round($TarSize, 2)) MB"

if ($DryRun) {
    Write-Host "[DryRun] 업로드 생략. tar 위치: $TarFile"
    exit 0
}

# 2. scp 업로드
Write-Host "[2/3] scp 업로드 → ${NAS_HOST}:${REMOTE_TMP}"
Write-Host "       (비밀번호 입력 요청 시: knk123!)"
scp -P $NAS_PORT $TarFile "${NAS_USER}@${NAS_HOST}:${REMOTE_TMP}"

# 3. SSH 로 압축 해제 + 셋업
Write-Host "[3/3] SSH 압축 해제 + 셋업 스크립트 실행"
Write-Host "       (비밀번호 입력 요청 시: knk123!)"
ssh -p $NAS_PORT "${NAS_USER}@${NAS_HOST}" @"
set -e
mkdir -p ${REMOTE_DIR}
cd ${REMOTE_DIR}
tar -xzf ${REMOTE_TMP}
rm -f ${REMOTE_TMP}
chmod +x deploy/*.sh
echo "---"
echo "이제 컨테이너 셋업 실행:"
echo "  cd ${REMOTE_DIR}"
echo "  bash deploy/setup_ubuntu_container.sh"
"@

Write-Host "=================================================="
Write-Host "  업로드 완료"
Write-Host ""
Write-Host "  다음 단계 (SSH 접속 후 실행):"
Write-Host "    ssh ${NAS_USER}@${NAS_HOST} -p ${NAS_PORT}"
Write-Host "    cd ${REMOTE_DIR}"
Write-Host "    bash deploy/setup_ubuntu_container.sh"
Write-Host "=================================================="
