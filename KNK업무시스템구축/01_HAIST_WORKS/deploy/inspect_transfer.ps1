# ============================================================
# 전송 경로(공유 폴더) 확인 + 변환 결과 검증 (읽기전용)
# ------------------------------------------------------------
# 두 컨테이너가 공유 마운트를 갖는지 확인(있으면 cp 한 번으로 전송) + /tmp/mail_new.db 검증.
# 사용: ./inspect_transfer.ps1 -Port 32201   (WORKS: 검증+공유폴더)
#       ./inspect_transfer.ps1 -Port 32203   (kmail: 공유폴더)
#   - SSH 비밀번호 직접 입력. 읽기 전용.
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
Write-Host "  전송 경로 확인 + 변환 검증 (Port $Port) — 읽기전용" -ForegroundColor Cyan
Write-Host "  (SSH 비밀번호를 물으면 직접 입력하세요)" -ForegroundColor Yellow
Write-Host "=================================================="

$probe = @'
set +e
echo "[공유 마운트 후보]"
mount 2>/dev/null | grep -iE "haist|migrate|volume|share|/mnt|/data" | head -15
echo "[공유 경로 후보 존재 여부]"
for d in /haist /haist/_migrate /share /knk_share /mnt /migrate /opt/_migrate /data_share; do
  [ -d "$d" ] && { echo "  존재: $d"; ls -la "$d" 2>/dev/null | head -4; }
done
echo "[/tmp 용량(전송 임시 공간)]"; df -h /tmp 2>/dev/null | tail -2
if [ -f /tmp/mail_new.db ]; then
  echo "[mail_new.db 검증]"
  ls -la /tmp/mail_new.db
  /opt/knk_haist/.venv/bin/python - <<'PYEOF'
import sqlite3
c = sqlite3.connect("/tmp/mail_new.db")
print("  메일:", c.execute("SELECT COUNT(*) FROM mail_messages").fetchone()[0])
print("  첨부:", c.execute("SELECT COUNT(*) FROM mail_attachments").fetchone()[0])
print("  고아 첨부(연결 끊김):", c.execute("SELECT COUNT(*) FROM mail_attachments a LEFT JOIN mail_messages m ON m.id=a.mail_id WHERE m.id IS NULL").fetchone()[0])
print("  메일 주인 user_id:", [r[0] for r in c.execute("SELECT DISTINCT user_id FROM mail_messages").fetchall()])
print("  사용자:", [(r[0], r[1], r[2]) for r in c.execute("SELECT id, login_id, name FROM users").fetchall()])
for r in c.execute("SELECT subject, received_at FROM mail_messages ORDER BY id DESC LIMIT 3").fetchall():
    print("  최근:", r[1], (r[0] or "")[:34])
PYEOF
fi
echo "[done]"
'@
Invoke-Remote $probe
Write-Host "`n[완료] 위 출력을 빅터에게 붙여주세요." -ForegroundColor Green
