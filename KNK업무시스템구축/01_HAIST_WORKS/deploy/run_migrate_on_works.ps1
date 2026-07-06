# ============================================================
# 메일 이전 — WORKS 컨테이너 안에서 변환 실행 (cutover, scp 없이 ssh 만 사용)
# ------------------------------------------------------------
# scp 가 원격 셸 출력 때문에 깨져서, 226MB 를 주고받지 않고 WORKS 컨테이너 안에서
# knk.db → /tmp/mail_new.db 로 변환한다. 결과(190MB)만 나중에 kmail 로 옮긴다.
# 사용:
#   ./run_migrate_on_works.ps1            # DRY-RUN(분석만·안전·아무것도 안 씀)
#   ./run_migrate_on_works.ps1 -Apply     # 실제 변환 → /tmp/mail_new.db 생성
#   - SSH 비밀번호는 실행 중 직접 입력. WORKS 원본(knk.db)은 읽기만 함.
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]$Port       = 32201,
    [string]$User    = "root",
    [switch]$Apply
)
$ErrorActionPreference = "Stop"
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")

function Invoke-Remote([string]$bash) {
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
}

$migLocal = Join-Path $PSScriptRoot "migrate_mail_to_kmail.py"
if (-not (Test-Path $migLocal)) { Write-Host "migrate 스크립트 없음: $migLocal" -ForegroundColor Red; return }
$mig = (Get-Content -Raw -Encoding UTF8 $migLocal) -replace "`r`n", "`n"
$migb64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($mig))

$mode = if ($Apply) { "APPLY(실제 변환)" } else { "DRY-RUN(분석만)" }
$applyFlag = if ($Apply) { "--apply" } else { "" }
$rmLine = if ($Apply) { "rm -f /tmp/mail_new.db" } else { "true" }

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  메일 이전 변환 — WORKS 컨테이너 ($mode)" -ForegroundColor Cyan
Write-Host "  (SSH 비밀번호를 물으면 직접 입력하세요)" -ForegroundColor Yellow
Write-Host "=================================================="

$cmd = @"
set +e
echo $migb64 | base64 -d > /tmp/migrate_mail.py
echo '[migrate.py 설치]'; wc -l /tmp/migrate_mail.py
$rmLine
/opt/knk_haist/.venv/bin/python /tmp/migrate_mail.py --works /opt/knk_haist/data/knk.db --kmail /tmp/mail_new.db --ensure-schema $applyFlag
echo '[결과 파일]'; ls -la /tmp/mail_new.db 2>/dev/null || echo '  (dry-run: 빈 스키마만·정상)'
"@
Invoke-Remote $cmd
Write-Host "`n[완료] 위 출력을 빅터에게 붙여주세요." -ForegroundColor Green
if (-not $Apply) { Write-Host "DRY-RUN 결과가 맞으면 -Apply 로 실제 변환합니다." -ForegroundColor Yellow }
