# ============================================================
# WORKS DB 메일 규모·소유자 매핑 조사 — cutover 2-1 (읽기전용·아무것도 안 바꿈)
# ------------------------------------------------------------
# WORKS 통합 DB(/opt/knk_haist/data/knk.db)의 메일 건수·첨부 용량·소유자(login_id/email) 확인.
# 메일을 kmail로 옮길 때 '주인 매핑'의 기준(login_id=사번)을 파악하기 위함.
# 사용법: ./inspect_works_mail.ps1   (기본 -Port 32201 = WORKS 컨테이너)
#   - SSH 비밀번호는 실행 중 직접 입력. 원격은 base64 전송(따옴표·한글 안전).
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
Write-Host "  WORKS DB 메일 규모·소유자 조사 — 읽기전용" -ForegroundColor Cyan
Write-Host "  (SSH 비밀번호를 물으면 직접 입력하세요)" -ForegroundColor Yellow
Write-Host "=================================================="

# single-quote here-string: PowerShell 확장 0 → python/bash 그대로 원격 전송
$probe = @'
set +e
DB="/opt/knk_haist/data/knk.db"
echo "[DB 파일]"; ls -la "$DB" 2>/dev/null || echo "  DB 없음: $DB"
/opt/knk_haist/.venv/bin/python - <<'PYEOF'
import sqlite3
c=sqlite3.connect("/opt/knk_haist/data/knk.db"); c.row_factory=sqlite3.Row
def q1(sql):
    try: return c.execute(sql).fetchone()[0]
    except Exception as e: return "ERR:"+str(e)
print("[메일 건수]")
print("  전체:", q1("SELECT COUNT(*) FROM mail_messages"))
print("  받은(in):", q1("SELECT COUNT(*) FROM mail_messages WHERE direction='in'"))
print("  보낸(out):", q1("SELECT COUNT(*) FROM mail_messages WHERE direction='out'"))
print("  임시(draft):", q1("SELECT COUNT(*) FROM mail_messages WHERE direction='draft'"))
print("  삭제됨(is_deleted=1):", q1("SELECT COUNT(*) FROM mail_messages WHERE is_deleted=1"))
print("  고유 소유자 수:", q1("SELECT COUNT(DISTINCT user_id) FROM mail_messages"))
print("[첨부]")
print("  건수:", q1("SELECT COUNT(*) FROM mail_attachments"))
try:
    mb=(q1("SELECT COALESCE(SUM(LENGTH(data)),0) FROM mail_attachments") or 0)/1048576.0
    print("  BLOB 총용량:", round(mb,1), "MB")
except Exception as e: print("  용량조회 실패", e)
print("[메일 소유자별(매핑 키 확인용)]")
try:
    for r in c.execute("SELECT m.user_id uid, u.login_id lid, u.email em, u.name nm, COUNT(*) n FROM mail_messages m LEFT JOIN users u ON u.id=m.user_id GROUP BY m.user_id ORDER BY n DESC LIMIT 20").fetchall():
        print("   - uid=%s login_id=%s email=%s name=%s : %s건" % (r["uid"], r["lid"], r["em"], r["nm"], r["n"]))
except Exception as e: print("   조회실패", e)
print("[자동수신 계정(일원화 대상)]")
try:
    for r in c.execute("SELECT owner_user_id ouid, username un, enabled en, protocol pr FROM mail_fetch_accounts").fetchall():
        print("   - owner=%s user=%s enabled=%s %s" % (r["ouid"], r["un"], r["en"], r["pr"]))
except Exception as e: print("   (mail_fetch_accounts 조회실패)", e)
print("[기타]")
print("  mail_aliases:", q1("SELECT COUNT(*) FROM mail_aliases"))
print("  users 총:", q1("SELECT COUNT(*) FROM users"))
PYEOF
echo "[done]"
'@
Invoke-Remote $probe
Write-Host "`n[조사 완료] 위 출력을 빅터에게 붙여주세요 — 이전 규모·소요·소유자 매핑(login_id=사번?)을 판단합니다." -ForegroundColor Green
