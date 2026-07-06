# ============================================================
# 메일 독립앱(kmail) 데이터 점검 — cutover 전환 점검 (읽기전용·아무것도 안 바꿈)
# ------------------------------------------------------------
# kmail DB(/opt/knk_mail/data/mail.db)에 메일·사용자 데이터가 있는지, 언제까지 받았는지 확인.
# 사용법: ./inspect_mail_data.ps1   (기본 -Port 32203 = 메일 컨테이너)
#   - SSH 비밀번호는 실행 중 직접 입력. 원격은 base64 전송(따옴표·한글 안전).
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
Write-Host "  메일 독립앱(kmail) 데이터 점검 — 읽기전용" -ForegroundColor Cyan
Write-Host "  (SSH 비밀번호를 물으면 직접 입력하세요)" -ForegroundColor Yellow
Write-Host "=================================================="

# single-quote here-string: PowerShell 확장 0 → python/bash 코드 그대로 원격 전송
$probe = @'
set +e
DB="/opt/knk_mail/data/mail.db"
echo "[DB 파일]"; ls -la "$DB" 2>/dev/null || echo "  DB 없음: $DB"
/opt/knk_mail/.venv/bin/python - <<'PYEOF'
import sqlite3
db="/opt/knk_mail/data/mail.db"
try:
    c=sqlite3.connect(db); c.row_factory=sqlite3.Row
except Exception as e:
    print("DB 열기 실패:", e); raise SystemExit
def cnt(t):
    try: return c.execute("SELECT COUNT(*) FROM "+t).fetchone()[0]
    except Exception: return "(테이블 없음)"
print("[행수]")
print("  mail_messages:", cnt("mail_messages"))
try: print("    - 받은(in):", c.execute("SELECT COUNT(*) FROM mail_messages WHERE direction='in'").fetchone()[0])
except Exception: pass
try: print("    - 보낸(out):", c.execute("SELECT COUNT(*) FROM mail_messages WHERE direction='out'").fetchone()[0])
except Exception: pass
print("  users:", cnt("users"))
print("  mail_accounts:", cnt("mail_accounts"))
print("  mail_aliases:", cnt("mail_aliases"))
print("  mail_attachments:", cnt("mail_attachments"))
try:
    r=c.execute("SELECT MIN(created_at), MAX(created_at) FROM mail_messages").fetchone()
    print("[메일 기간] 가장 오래된:", r[0], "/ 최근:", r[1])
except Exception as e:
    print("[메일 기간] 조회 실패:", e)
try:
    print("[사용자 샘플 최대 8명]")
    for u in c.execute("SELECT email, name FROM users ORDER BY id LIMIT 8").fetchall():
        print("  -", u["email"], "|", u["name"])
except Exception as e:
    print("  사용자 조회 실패:", e)
try:
    print("[최근 받은메일 5건 — 제목/날짜]")
    for m in c.execute("SELECT subject, created_at FROM mail_messages WHERE direction='in' ORDER BY id DESC LIMIT 5").fetchall():
        print("  -", (m["created_at"] or ""), "|", (m["subject"] or "")[:40])
except Exception as e:
    print("  최근메일 조회 실패:", e)
PYEOF
echo "[done]"
'@
Invoke-Remote $probe
Write-Host "`n[점검 완료] 위 출력을 빅터에게 붙여주세요 — 데이터 유무·기간·중복수신 위험을 판단합니다." -ForegroundColor Green
