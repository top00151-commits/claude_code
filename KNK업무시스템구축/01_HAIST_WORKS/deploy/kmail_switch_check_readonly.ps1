# ============================================================
# kmail switch - PRE-CHECK.  READ ONLY.  2026-11-16.
#
# WHY: CEO decision 2026-11-16: keep the NAS reverse proxy as it is
#      (kmail -> localhost:5053, works -> localhost:5051) and make WORKS
#      itself listen on 5053 too. Before we stop the old mail app and
#      switch, we must SEE (not guess):
#        (M) container KNKHAIST.MAIL (ssh 32203): what starts the old app
#            at boot and what keeps reviving it (watchdog + login hook)
#        (W) container KNKHAIST      (ssh 32201): how WORKS is started,
#            library versions, and whether the new switch is already set
#
# !! READ ONLY !!  No writes, no deletes, no restarts, no stop, no deploy.
# !! Does NOT read mail bodies, attachments, addresses, passwords or tokens.
#    Config lines that look like secrets (key/token/pass/secret) are SKIPPED,
#    not masked. Secrets are checked by NAME only (PRESENT / absent).
# ASCII-ONLY (PowerShell 5.1 mis-reads UTF-8 -> Korean breaks the remote script).
#
# Usage (PowerShell):  ./kmail_switch_check_readonly.ps1
#   It connects twice (32203, then 32201). Type the SSH password each time.
#   Then paste the whole output back to Victor.
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [string]$User    = "root",
    [switch]$OnlyMail,      # only container 32203
    [switch]$OnlyWorks      # only container 32201
)
$ErrorActionPreference = "Continue"

function Invoke-Remote([int]$Port, [string]$bash) {
    $sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15")
    # the remote side is bash: it must get LF only (a CRLF checkout of this file would break 'fi', 'done' ...)
    $bash = $bash -replace "`r`n", "`n"
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
}

$probeMail = @'
set +e
echo "=== [M0] which container ==="
hostname
echo ""

echo "=== [M1] PID 1 and every process (how things start at boot) ==="
echo "pid1 cmdline: $(tr '\0' ' ' < /proc/1/cmdline 2>/dev/null)"
ps -eo pid,ppid,lstart,args 2>/dev/null | grep -viE 'key=|token=|pass(word)?=|secret=' | cut -c1-200 | head -45
echo ""

echo "=== [M2] boot / login hooks that mention the mail app ==="
echo "    (line numbers + 2 lines of context; secret-looking lines are skipped)"
for F in /root/.bash_profile /root/.bashrc /root/.profile /root/.bash_login /etc/profile /etc/bash.bashrc /etc/rc.local /start.sh /entrypoint.sh /docker-entrypoint.sh /usr/local/bin/start.sh; do
  [ -f "$F" ] || continue
  N=$(grep -cE 'knk_mail|mail_watchdog|run\.py|KNK-MAIL' "$F" 2>/dev/null)
  echo "-- $F   total lines: $(wc -l < "$F")   matching lines: $N"
  [ "$N" -gt 0 ] && grep -nE -B2 -A2 'knk_mail|mail_watchdog|run\.py|KNK-MAIL' "$F" 2>/dev/null | grep -viE 'key|token|pass|secret' | cut -c1-260
done
echo "-- /etc/profile.d files mentioning the mail app:"
grep -lE 'knk_mail|mail_watchdog' /etc/profile.d/* 2>/dev/null || echo "   (none)"
echo ""

echo "=== [M3] cron ==="
(crontab -l 2>/dev/null | grep -vE '^\s*(#|$)' | grep -viE 'key|token|pass|secret' | cut -c1-200 | head -10) || true
[ -z "$(crontab -l 2>/dev/null | grep -vE '^\s*(#|$)')" ] && echo "   (no crontab lines)"
ls /etc/cron.d 2>/dev/null | head -10
echo "   supervisorctl: $(command -v supervisorctl >/dev/null 2>&1 && echo PRESENT || echo absent)"
echo ""

echo "=== [M4] the two processes we would stop (FULL-PATH match) ==="
echo "-- watchdog:"; pgrep -af '/opt/knk_mail/mail_watchdog\.sh' || echo "   (not running)"
echo "-- app:";      pgrep -af '/opt/knk_mail/run\.py'           || echo "   (not running)"
echo "-- any OTHER python / uvicorn here (must be none besides the above):"
ps -eo pid,ppid,args 2>/dev/null | grep -E '[p]ython|[u]vicorn|[g]unicorn' | grep -v '/opt/knk_mail/' | cut -c1-160 | head -8
echo ""

echo "=== [M5] who listens on 5053 / 5051 (seen from this container) ==="
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | grep -E ':(5053|5051)[[:space:]]' || echo "   (nothing)"
echo ""

echo "=== [M6] watchdog file on the server ==="
ls -la /opt/knk_mail/mail_watchdog.sh 2>&1 | tail -1
echo "   sha256(first 16): $(sha256sum /opt/knk_mail/mail_watchdog.sh 2>/dev/null | cut -c1-16)   lines: $(wc -l < /opt/knk_mail/mail_watchdog.sh 2>/dev/null)"
echo "-- last 6 watchdog log lines (timestamps + state words only, no mail data in this log):"
tail -6 /opt/knk_mail/logs/watchdog.log 2>/dev/null | cut -c1-160
echo ""

echo "=== [M7] tools the stop script needs ==="
for T in pkill pgrep flock setsid sed cp grep date; do command -v $T >/dev/null 2>&1 && echo "   $T ok" || echo "   $T MISSING"; done
echo ""
echo "[done 32203]  NOTHING WAS MODIFIED."
'@

$probeWorks = @'
set +e
echo "=== [W0] which container ==="
hostname
echo ""

echo "=== [W1] how knk-works is started (the wrapper only sources .env; secret-looking lines skipped) ==="
W=/opt/knk_haist/.venv/bin/run_knk_works.sh
ls -la "$W" 2>&1 | tail -1
grep -vE '^\s*#' "$W" 2>/dev/null | grep -viE 'key=|token=|pass(word)?=|secret=' | cut -c1-200
echo ""

echo "=== [W2] versions ==="
PY=/opt/knk_haist/.venv/bin/python
"$PY" -c "import sys,socket,uvicorn,starlette,fastapi;print('python',sys.version.split()[0]);print('uvicorn',uvicorn.__version__);print('starlette',starlette.__version__);print('fastapi',fastapi.__version__);print('SO_REUSEPORT',hasattr(socket,'SO_REUSEPORT'))" 2>&1
"$PY" -c "import httptools;print('httptools',httptools.__version__)" 2>&1 | tail -1
"$PY" -c "import uvloop;print('uvloop',uvloop.__version__)" 2>&1 | tail -1
echo "kernel: $(uname -r)"
echo ""

echo "=== [W3] settings in .env - by NAME only ==="
E=/opt/knk_haist/.env
for K in KNK_MAIL_SITE_PORT KNK_MAIL_SITE_BIND KNK_MODE KNK_WORKERS WEB_CONCURRENCY FORWARDED_ALLOW_IPS KNK_RUN_MAIL_FETCH KNK_SECRET_KEY KNK_MAIL_KEY; do
  if grep -qE "^[[:space:]]*(export[[:space:]]+)?$K[[:space:]]*=" "$E" 2>/dev/null; then echo "   $K = PRESENT"; else echo "   $K = absent"; fi
done
echo "-- two NON-secret values, read by name:"
grep -E '^[[:space:]]*(export[[:space:]]+)?(KNK_MODE|KNK_WORKERS)[[:space:]]*=' "$E" 2>/dev/null | cut -c1-60
echo "   .env total lines: $(wc -l < "$E" 2>/dev/null)    last byte is a newline: $( [ -z "$(tail -c1 "$E" 2>/dev/null)" ] && echo yes || echo NO )"
ls -la "$E" 2>&1 | awk '{print "   perms/owner:", $1, $3, $4}'
echo ""

echo "=== [W4] workers, listeners, supervisor ==="
ps -eo pid,ppid,etime,rss,args 2>/dev/null | grep -E '[u]vicorn' | cut -c1-190
echo "--"
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | grep -E ':(5051|5053)[[:space:]]' || echo "   (nothing on 5051/5053 ?)"
echo "--"
supervisorctl status 2>&1 | head -8
echo ""

echo "=== [W5] deployed code ==="
git -C /opt/knk_haist log -1 --format='   commit: %h | %ci | %s' 2>/dev/null | cut -c1-150
ls -la /opt/knk_haist/app/mail_site.py 2>&1 | tail -1
echo "   5051 /api/version: $(curl -s -m 6 -w ' [HTTP %{http_code}]' http://127.0.0.1:5051/api/version 2>/dev/null | head -c 120)"
echo ""

echo "=== [W6] what answers on 5053 right now (the OLD app is expected) ==="
echo "   5053 /healthz    : $(curl -s -m 6 -w ' [HTTP %{http_code}]' http://127.0.0.1:5053/healthz 2>/dev/null | head -c 160)"
echo "   5053 /api/version: $(curl -s -m 6 -w ' [HTTP %{http_code}]' http://127.0.0.1:5053/api/version 2>/dev/null | head -c 160)"
echo ""

echo "=== [W7] memory ==="
free -m 2>/dev/null | head -3
echo ""

echo "=== [W8] recent startup lines of the app (errors would show here) ==="
grep -nE 'MAIL-SITE|Started server process|Application startup complete|Traceback' /opt/knk_haist/logs/uvicorn-error.log 2>/dev/null | tail -8 | cut -c1-160
grep -nE 'MAIL-SITE' /opt/knk_haist/logs/uvicorn.log 2>/dev/null | tail -6 | cut -c1-200
echo ""
echo "[done 32201]  NOTHING WAS MODIFIED."
'@

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  kmail switch PRE-CHECK - READ ONLY" -ForegroundColor Cyan
Write-Host "  no writes / no restarts / no stop / no mail content" -ForegroundColor Yellow
Write-Host "=================================================="

if (-not $OnlyWorks) {
    Write-Host ""
    Write-Host ">>> (1/2) KNKHAIST.MAIL  - ssh port 32203   (type the SSH password)" -ForegroundColor Green
    Invoke-Remote 32203 $probeMail
}
if (-not $OnlyMail) {
    Write-Host ""
    Write-Host ">>> (2/2) KNKHAIST       - ssh port 32201   (type the SSH password)" -ForegroundColor Green
    Invoke-Remote 32201 $probeWorks
}

Write-Host ""
Write-Host "[check finished] Nothing was changed. Please paste the whole output to Victor." -ForegroundColor Green
