# ============================================================
# 메일 이전 — 변환본을 공유볼륨(/haist)으로 복사 (WORKS 측)
# ------------------------------------------------------------
# WORKS /tmp/mail_new.db → /haist/mail_new.db (양쪽 컨테이너 공유). scp 회피.
# 사용: ./transfer_to_haist.ps1   (-Port 32201 = WORKS)
#   - SSH 비밀번호 직접 입력. WORKS 원본 무관(임시 변환본만 복사).
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

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  변환본 → 공유볼륨(/haist) 복사 (WORKS)" -ForegroundColor Cyan
Write-Host "  (SSH 비밀번호를 물으면 직접 입력하세요)" -ForegroundColor Yellow
Write-Host "=================================================="

$probe = @'
set +e
SRC=/tmp/mail_new.db
DST=/haist/mail_new.db
if [ ! -f "$SRC" ]; then echo "[FAIL] 변환본 없음: $SRC (run_migrate_on_works.ps1 -Apply 먼저)"; exit 1; fi
echo "[원본] "; ls -la "$SRC"
cp "$SRC" "$DST" 2>/tmp/cp_err && echo "[OK] /haist 복사 완료" || { echo "[FAIL] 복사 실패:"; cat /tmp/cp_err; }
ls -la "$DST" 2>/dev/null
S=$(stat -c%s "$SRC" 2>/dev/null); D=$(stat -c%s "$DST" 2>/dev/null)
echo "[크기 비교] src=$S dst=$D $([ "$S" = "$D" ] && echo '=> 일치 OK' || echo '=> 불일치!')"
echo "[done]"
'@
Invoke-Remote $probe
Write-Host "`n[완료] 위 출력을 빅터에게 붙여주세요 — '일치 OK'면 kmail 교체로 넘어갑니다." -ForegroundColor Green
