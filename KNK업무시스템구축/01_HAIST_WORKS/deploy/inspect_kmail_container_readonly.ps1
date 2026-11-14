# ============================================================
# Old standalone mail app on kmail.knknara.co.kr - READ ONLY. 2026-11-14.
#
# WHY: 2026-11-09 I reported "knk-mail decommissioned". That was only the
#      GitHub repo. The APP is still serving a public login page:
#        https://kmail.knknara.co.kr/healthz
#          -> {"ok":true,"app":"KNK Eum MAIL","db":"mail.db","tables":13}
#      That probe looked at /opt/knk_mail inside container KNKHAIST (32201).
#      The app actually lives in a SEPARATE container: KNKHAIST.MAIL (32203 / 5053).
#      We must know what is inside before deciding to stop / keep / migrate it.
#
# !! READ ONLY !!  No writes, no deletes, no restarts, no deploys, no stop.
# !! Does NOT read mail bodies, attachments, addresses, passwords or tokens.
#    Only: existence, paths, sizes, timestamps, table names and ROW COUNTS.
#    Secrets are checked by NAME only (present / absent), never printed.
# ASCII-ONLY (PowerShell 5.1 mis-reads UTF-8 -> Korean breaks the remote script).
#
# Usage (PowerShell):  ./inspect_kmail_container_readonly.ps1
#   (type the SSH password when asked)
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]$Port       = 32203,          # KNKHAIST.MAIL
    [string]$User    = "root"
)
$ErrorActionPreference = "Continue"
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15")

function Invoke-Remote([string]$bash) {
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Old mail app (kmail) check - READ ONLY" -ForegroundColor Cyan
Write-Host "  no writes / no restarts / no stop / no mail content" -ForegroundColor Yellow
Write-Host "  target: $User@$SshHost port $Port (KNKHAIST.MAIL)" -ForegroundColor Yellow
Write-Host "=================================================="

$probe = @'
set +e
echo "=== [0] which container am I in? ==="
hostname; cat /etc/hostname 2>/dev/null
echo ""

echo "=== [1] where is the mail app? ==="
for D in /opt/knk_mail /opt/kmail /opt/knk_eum_mail /app /opt/app; do
  [ -d "$D" ] && { echo "DIR $D"; du -sh "$D" 2>/dev/null; ls -la "$D" 2>/dev/null | head -12; echo "--"; }
done
echo "-- processes that look like the mail app --"
(ps -ef 2>/dev/null || ps aux 2>/dev/null) | grep -iE 'mail|uvicorn|gunicorn|python' | grep -v grep | head -10
echo ""

echo "=== [2] what is listening ==="
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | head -20
echo ""

echo "=== [3] supervisor / service state ==="
supervisorctl status 2>&1 | head -15
echo ""

echo "=== [4] the database: tables + ROW COUNTS only (no contents) ==="
PY=""
for C in /opt/knk_mail/.venv/bin/python /opt/knk_haist/.venv/bin/python /usr/bin/python3 python3; do
  command -v "$C" >/dev/null 2>&1 && { PY="$C"; break; }
done
echo "python: $PY"
for DB in $(find / -maxdepth 5 -name 'mail.db' -not -path '*/proc/*' 2>/dev/null | head -5); do
  echo "-- $DB --"
  ls -l "$DB" 2>/dev/null | awk '{print "   size:", $5, "bytes   mtime:", $6, $7, $8}'
  "$PY" - "$DB" <<'PYEOF'
import sqlite3, sys, os, datetime
db = sys.argv[1]
try:
    print("   last modified: %s" % datetime.datetime.fromtimestamp(os.path.getmtime(db)).strftime('%Y-%m-%d %H:%M'))
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)   # read-only open
    for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        try:
            n = c.execute("SELECT COUNT(*) FROM [%s]" % t).fetchone()[0]
        except Exception:
            n = "?"
        print("   %-30s rows=%s" % (t, n))
    c.close()
except Exception as e:
    print("   (cannot open read-only):", e)
PYEOF
done
echo ""

echo "=== [5] is anything still USING it? (newest write) ==="
find /opt -maxdepth 4 -name '*.db' -o -maxdepth 4 -name '*.log' 2>/dev/null | head -10 | while read F; do
  [ -f "$F" ] && echo "   $(date -r "$F" '+%Y-%m-%d %H:%M')  $F"
done
echo "-- recent app log lines (count only, not contents) --"
for L in /opt/knk_mail/data/*.log /var/log/*.log; do
  [ -f "$L" ] && echo "   $(wc -l < "$L") lines  $(date -r "$L" '+%Y-%m-%d %H:%M')  $L"
done 2>/dev/null | head -8
echo ""

echo "=== [6] does a cron still try to pull the DELETED repo? ==="
crontab -l 2>/dev/null | grep -vE '^\s*#' | head -10
echo "-- git remote (repo was deleted 2026-11-09, so a pull should be failing) --"
for D in /opt/knk_mail /opt/kmail /app; do
  [ -d "$D/.git" ] && { echo "$D:"; git -C "$D" remote -v 2>/dev/null | head -2; git -C "$D" log -1 --format='   last commit: %h | %ci' 2>/dev/null; }
done
echo ""

echo "=== [7] secrets: PRESENT / ABSENT by NAME only (values never printed) ==="
for D in /opt/knk_mail /opt/kmail /app; do
  E="$D/.env"
  [ -f "$E" ] || continue
  echo "$E:"
  for K in KNK_MAIL_KEY MAIL_INBOUND_TOKEN SSO_SHARED_KEY SECRET_KEY; do
    if grep -qE "^[[:space:]]*$K[[:space:]]*=" "$E" 2>/dev/null; then echo "   $K = PRESENT"; else echo "   $K = absent"; fi
  done
done
echo ""
echo "[done]  NOTHING WAS MODIFIED."
'@

Invoke-Remote $probe
Write-Host ""
Write-Host "[DONE] Paste the FULL output above to Victor (session 15_KNK_Mail)." -ForegroundColor Green
Write-Host "       If SSH to port $Port fails, tell Victor - the container may use a different port." -ForegroundColor Yellow
