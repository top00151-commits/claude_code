# ============================================================
# 메일 이전 — kmail DB 교체 (cutover, kmail 측 한 번에 안전 적용)
# ------------------------------------------------------------
# /haist/mail_new.db → /opt/knk_mail/data/mail.db 교체.
# 한 SSH 안에서: 워치독·앱 정지 → 기존 DB 백업(롤백용) → 교체 → 앱 재시작 → healthz·건수 → 워치독 재시작.
# 사용: ./apply_kmail_db.ps1   (-Port 32203 = kmail)
#   - SSH 비밀번호 직접 입력. 실패 시 백업(mail.db.bak.*)에서 복원 가능.
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]$Port       = 32203,
    [string]$User    = "root"
)
$ErrorActionPreference = "Stop"
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")

function Invoke-Remote([string]$bash) {
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  kmail DB 교체 (cutover) — 백업 후 교체·재시작·검증" -ForegroundColor Cyan
Write-Host "  (SSH 비밀번호를 물으면 직접 입력하세요)" -ForegroundColor Yellow
Write-Host "=================================================="

$probe = @'
set +e
DB=/opt/knk_mail/data/mail.db
NEW=/haist/mail_new.db
TS=$(date +%Y%m%d_%H%M%S)
if [ ! -f "$NEW" ]; then echo "[FAIL] /haist/mail_new.db 없음 (transfer_to_haist 먼저)"; exit 1; fi

echo "[1] 워치독·앱 정지"
pkill -f "[m]ail_watchdog.sh" 2>/dev/null; sleep 1
pkill -TERM -f "/opt/knk_mail/run.py" 2>/dev/null; sleep 3
pkill -9 -f "/opt/knk_mail/run.py" 2>/dev/null; sleep 1
echo "  run.py 잔존: $(pgrep -f '/opt/knk_mail/run.py' | wc -l) (0이어야 함)"

echo "[2] 기존 DB 백업(롤백용)"
if [ -f "$DB" ]; then cp "$DB" "$DB.bak.$TS" && echo "  백업: $DB.bak.$TS ($(stat -c%s "$DB.bak.$TS") bytes)"; else echo "  (기존 DB 없음)"; fi

echo "[3] 새 DB 교체"
cp "$NEW" "$DB" && chmod 644 "$DB" && echo "  교체 완료: $(stat -c%s "$DB") bytes" || { echo "[FAIL] 교체 실패"; exit 1; }

echo "[4] 앱 재시작"
( cd /opt/knk_mail 2>/dev/null || exit 0
  if [ -r ./.env ]; then set -a; . ./.env 2>/dev/null || true; set +a; fi
  exec setsid /opt/knk_mail/.venv/bin/python /opt/knk_mail/run.py >/tmp/mail_boot.log 2>&1 < /dev/null ) &
sleep 9
echo "  run.py pid: $(pgrep -f '/opt/knk_mail/run.py' | head -1)"

echo "[5] healthz"
/opt/knk_mail/.venv/bin/python -c "import urllib.request as u; print('  healthz =', u.urlopen('http://127.0.0.1:5053/healthz',timeout=12).status)" 2>&1 | head -3

echo "[6] 교체된 DB 건수"
/opt/knk_mail/.venv/bin/python -c "import sqlite3;c=sqlite3.connect('$DB');print('  메일', c.execute('SELECT COUNT(*) FROM mail_messages').fetchone()[0], '/ 첨부', c.execute('SELECT COUNT(*) FROM mail_attachments').fetchone()[0], '/ 사용자', c.execute('SELECT COUNT(*) FROM users').fetchone()[0])" 2>&1 | head -3

echo "[7] 워치독 재시작"
pgrep -f "[m]ail_watchdog.sh" >/dev/null 2>&1 || setsid /bin/sh /opt/knk_mail/mail_watchdog.sh >/dev/null 2>&1 &
sleep 1
echo "  워치독 pid: $(pgrep -f '[m]ail_watchdog.sh' | head -1)"
echo "[done] 롤백 필요시: cp $DB.bak.$TS $DB 후 앱 재시작"
'@
Invoke-Remote $probe
Write-Host "`n[완료] 위 출력 붙여주세요 — healthz=200 + 메일 464 + 사용자 1 이면 성공." -ForegroundColor Green
