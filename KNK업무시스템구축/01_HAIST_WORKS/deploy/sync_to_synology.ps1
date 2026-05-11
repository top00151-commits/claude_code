# ============================================================
# HAIST WORKS - Windows PC → Synology NAS 동기화
# v5H226z75 (2026-05-11)
# ============================================================
# 사용법:
#   PowerShell 에서:
#     ./sync_to_synology.ps1                     (코드만 동기화)
#     ./sync_to_synology.ps1 -Rebuild            (동기화 + 컨테이너 재빌드)
#     ./sync_to_synology.ps1 -NasIP 192.168.1.10 (NAS IP 지정)
#
# 사전: NAS SSH 접속 가능 + .env 미리 NAS에 배치
# ============================================================
param(
    [string]$NasUser = "admin",
    [string]$NasIP   = "192.168.1.10",
    [string]$NasPort = "22",
    [string]$NasPath = "/volume1/docker/knk-haist/src",
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$SourceRoot = (Split-Path -Parent $PSScriptRoot)

Write-Host "=================================================="
Write-Host "  HAIST WORKS Sync → NAS ${NasUser}@${NasIP}"
Write-Host "  Source: ${SourceRoot}"
Write-Host "  Target: ${NasPath}"
Write-Host "=================================================="

# rsync over SSH (WSL 또는 Git Bash 의 rsync 사용)
# Windows 네이티브 rsync 없으면 scp 로 폴백
$rsyncExists = Get-Command rsync -ErrorAction SilentlyContinue
if ($rsyncExists) {
    Write-Host "[1/2] rsync 동기화..."
    rsync -avz --delete `
        --exclude='__pycache__' --exclude='*.pyc' `
        --exclude='data/*.db' --exclude='data/backups' `
        --exclude='uploads/*' `
        --exclude='.git' --exclude='.venv' --exclude='venv' `
        --exclude='*.log' --exclude='server.log' `
        --exclude='HAIST WORKS디자인변경' --exclude='참고자료' `
        -e "ssh -p ${NasPort}" `
        "${SourceRoot}/" "${NasUser}@${NasIP}:${NasPath}/"
} else {
    Write-Host "[!] rsync 미설치 — scp 폴백 (느림)"
    scp -P $NasPort -r `
        "${SourceRoot}/app" `
        "${SourceRoot}/static" `
        "${SourceRoot}/scripts" `
        "${SourceRoot}/deploy" `
        "${SourceRoot}/run.py" `
        "${SourceRoot}/requirements.txt" `
        "${SourceRoot}/Dockerfile" `
        "${SourceRoot}/.dockerignore" `
        "${NasUser}@${NasIP}:${NasPath}/"
}

if ($Rebuild) {
    Write-Host "[2/2] NAS 컨테이너 재빌드"
    ssh -p $NasPort "${NasUser}@${NasIP}" "cd ${NasPath} && bash deploy/setup_synology_container.sh"
} else {
    Write-Host "[2/2] 동기화만 완료 — 재빌드는 -Rebuild 플래그"
}

Write-Host "=================================================="
Write-Host "  완료"
Write-Host "=================================================="
