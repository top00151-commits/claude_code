# ============================================================
# kmail switch - APPLY.  2026-11-16.  CEO decision: "apply with 5053".
#
#   The NAS reverse proxy is NOT touched (kmail -> localhost:5053, works -> localhost:5051).
#   WORKS itself starts listening on 5053 too (same process, new code in app/mail_site.py),
#   and the old standalone mail app that holds 5053 today is stopped.
#
#   -Step1   container KNKHAIST (ssh 32201)
#            1) smoke-test the new code with the REAL libraries on SPARE ports
#               (separate short process - the running WORKS is not touched)
#            2) add ONE line to /opt/knk_haist/.env :  KNK_MAIL_SITE_PORT=5053   (backup first)
#            3) restart knk-works (the same command every deploy uses, about 15 seconds)
#            4) confirm WORKS is healthy and is WAITING for port 5053
#            If WORKS does not come back, the line is removed and WORKS restarted again (auto-undo).
#
#   -Step2   container KNKHAIST.MAIL (ssh 32203)
#            1) comment out the auto-start hooks in /root/.bash_profile and /root/.bashrc (backup first)
#            2) stop the watchdog, then stop the old mail app
#               !! NO file and NO database is deleted. /opt/knk_mail stays as it is.
#            3) wait until WORKS answers on 5053
#            If WORKS does not take the port within 60s, the old app is put back (auto-undo).
#
#   -Undo1   KNKHAIST      : remove the .env line + restart knk-works  (WORKS stops listening on 5053)
#   -Undo2   KNKHAIST.MAIL : re-enable the hooks + start the watchdog  (old app comes back; run -Undo1 FIRST)
#
# ORDER:  Step1  ->  Step2.      To go back:  Undo1  ->  Undo2.
#
# !! Never stops or restarts a CONTAINER. Never reads mail content, passwords or tokens.
#    .env is only appended to / one line removed; its values are never printed.
# ASCII-ONLY (PowerShell 5.1 mis-reads UTF-8 -> Korean breaks the remote script).
#
# Usage (PowerShell):   ./kmail_switch_apply.ps1 -Step1
#                       ./kmail_switch_apply.ps1 -Step2
#   Type the SSH password when asked. Paste the whole output back to Victor.
# ============================================================
param(
    [switch]$Step1,
    [switch]$Step2,
    [switch]$Undo1,
    [switch]$Undo2,
    [string]$SshHost = "o.knknara.co.kr",
    [string]$User    = "root"
)
$ErrorActionPreference = "Continue"
# NOTE: PowerShell names are case-insensitive - the script bodies below must NOT be named like the
#       switches ($Step1 ...), or assigning the text to them fails. Hence $bodyStep1 etc.

function Invoke-Remote([int]$Port, [string]$bash) {
    $sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15")
    # the remote side is bash: it must get LF only (a CRLF checkout of this file would break 'fi', 'done' ...)
    $bash = $bash -replace "`r`n", "`n"
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
}

# ---------------------------------------------------------------- Step1 (KNKHAIST / 32201)
$bodyStep1 = @'
set +e
APP=/opt/knk_haist
E=$APP/.env
PY=$APP/.venv/bin/python
MOD=$APP/app/mail_site.py
PORT=5053
MAIN=5051
ver(){ curl -s -m 5 http://127.0.0.1:$MAIN/api/version 2>/dev/null | head -c 60; }
wait_works(){ n=0; while [ $n -lt 30 ]; do V=$(ver); case "$V" in *'"v"'*) return 0;; esac; sleep 3; n=$((n+1)); done; return 1; }

echo "=== [1-0] which container ==="
hostname
[ "$(hostname)" = "KNKHAIST" ] || { echo "ABORT: this is not container KNKHAIST. Nothing was changed."; exit 10; }
echo ""

echo "=== [1-1] is the new code deployed AND running? ==="
[ -f "$MOD" ] || { echo "ABORT: $MOD not found - the code is not deployed yet. Nothing was changed."; exit 11; }
grep -q 'KNK_MAIL_SITE_PORT' "$MOD" || { echo "ABORT: $MOD is not the expected file. Nothing was changed."; exit 11; }
H=$(git -C $APP log -1 --format=%h 2>/dev/null | cut -c1-7)
V0=$(ver)
echo "   mail_site.py : $(wc -l < "$MOD") lines   sha256(16) $(sha256sum "$MOD" | cut -c1-16)"
echo "   deployed commit: $H    5051 /api/version: $V0"
case "$V0" in *'"v"'*) ;; *) echo "ABORT: WORKS is not answering normally right now. Nothing was changed."; exit 12;; esac
[ -n "$H" ] || { echo "ABORT: cannot read the deployed commit. Nothing was changed."; exit 13; }
case "$V0" in *"$H"*) ;; *) echo "ABORT: the running WORKS is not the deployed commit yet ($H). Wait one minute and run again. Nothing was changed."; exit 13;; esac
grep -q '_mail_site.Guard' $APP/app/main.py || { echo "ABORT: app/main.py does not have the new wiring. Nothing was changed."; exit 14; }
echo ""

echo "=== [1-2] smoke test - real libraries, real kernel, SPARE ports, separate process ==="
"$PY" - "$MOD" <<'PYEOF'
import asyncio, http.client, importlib.util, json, os, socket, sys, threading, time, warnings
warnings.simplefilter("ignore")
MOD = sys.argv[1]

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

A = free_port(); B = free_port()
while B == A:
    B = free_port()
os.environ["KNK_MAIL_SITE_PORT"] = str(B)
os.environ["KNK_MAIL_SITE_BIND"] = "127.0.0.1"
spec = importlib.util.spec_from_file_location("mail_site_smoke", MOD)
ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)
ms._RETRY_SEC = 1.0
LOG = []
ms.print = lambda *a, **k: LOG.append(" ".join(str(x) for x in a))

import fastapi, starlette, uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
app.add_middleware(ms.Guard)

@app.get("/api/version")
async def _v(req: Request):
    return JSONResponse({"port": req.scope["server"][1], "mail": ms.is_mail_site(req), "base": ms.public_base(req),
                         "loop": type(asyncio.get_running_loop()).__module__})

@app.get("/home")
async def _h(req: Request):
    return JSONResponse({"home": True, "mail": ms.is_mail_site(req)})

@app.get("/mail/x")
async def _m(req: Request):
    return JSONResponse({"mailx": True, "port": req.scope["server"][1]})

@app.on_event("startup")
async def _s():
    ms.start(app)

@app.on_event("shutdown")
async def _e():
    await ms.stop()

R = []
def ok(name, cond, extra=""):
    R.append(bool(cond))
    print("   [%s] %s%s" % ("PASS" if cond else "FAIL", name, "" if cond else "   <- " + str(extra)[:160]))
    sys.stdout.flush()

def asc(x):
    return x.encode("ascii", "ignore").decode()[:46]

def get(port, path, host, method="GET"):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=6)
    try:
        c.request(method, path, headers={"Host": host})
        r = c.getresponse(); b = r.read()
        return r.status, dict((k.lower(), v) for k, v in r.getheaders()), b
    finally:
        c.close()

def wait(cond, sec):
    end = time.time() + sec
    while time.time() < end:
        try:
            if cond():
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False

print("   versions: python %s | uvicorn %s | starlette %s | fastapi %s" % (
    sys.version.split()[0], uvicorn.__version__, starlette.__version__, fastapi.__version__))

# another program holds port B first - exactly like the old mail app (uvicorn default: SO_REUSEADDR only)
squat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
squat.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
squat.bind(("127.0.0.1", B)); squat.listen(5)

srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=A, log_config=None, proxy_headers=True, forwarded_allow_ips="*"))
th = threading.Thread(target=srv.run, daemon=True); th.start()
try:
    up = wait(lambda: get(A, "/api/version", "works.knknara.co.kr")[0] == 200, 25)
    ok("test server is up on spare port A (startup hook ran)", up)
    s, h, b = get(A, "/api/version", "works.knknara.co.kr"); j = json.loads(b) if s == 200 else {}
    print("   (info) event loop in this test: %s" % j.get("loop"))
    ok("port B is held by another program: entrance waits, port A keeps serving", (not ms.listening()) and s == 200 and j.get("mail") is False, (s, j))
    time.sleep(2.5)
    ok("exactly ONE 'WAIT' log line (no log flood while waiting)", len([x for x in LOG if x.startswith("[MAIL-SITE] WAIT ")]) == 1, [asc(x) for x in LOG])
    squat.close()
    took = wait(ms.listening, 8) and wait(lambda: get(B, "/api/version", "localhost:%d" % B)[0] == 200, 8)
    ok("port freed -> the entrance takes it over BY ITSELF, no restart ('LISTEN' log)", took and any(x.startswith("[MAIL-SITE] LISTEN ") for x in LOG), [asc(x) for x in LOG])
    s, h, b = get(B, "/api/version", "localhost:%d" % B); j = json.loads(b) if s == 200 else {}
    ok("request on port B with Host=localhost is judged 'mail site' BY PORT", s == 200 and j.get("mail") is True and j.get("port") == B and j.get("base") == "https://kmail.knknara.co.kr", (s, j))
    s, h, b = get(B, "/home", "localhost:%d" % B)
    ok("port B /home -> 307 to the same path on works", s == 307 and h.get("location") == "https://works.knknara.co.kr/home", (s, h.get("location")))
    s, h, b = get(B, "/", "localhost:%d" % B)
    ok("port B /     -> 303 to the inbox", s == 303 and h.get("location") == "/mail/inbox?app=1", (s, h.get("location")))
    s, h, b = get(B, "/mail/x", "kmail.knknara.co.kr")
    ok("port B /mail/x is served (mail paths pass)", s == 200 and json.loads(b).get("port") == B, (s, b[:60]))
    s, h, b = get(B, "/home", "works.knknara.co.kr")
    ok("port B with Host=works is NOT redirected (no redirect loop possible)", s == 200 and json.loads(b).get("mail") is False, (s, b[:60]))
    s, h, b = get(A, "/home", "works.knknara.co.kr")
    ok("port A /home is served normally (works side unchanged)", s == 200 and json.loads(b).get("mail") is False, (s, b[:60]))
    mixed = True
    for i in range(10):
        if get(A, "/home", "works.knknara.co.kr")[0] != 200 or get(B, "/home", "localhost")[0] != 307:
            mixed = False
    ok("20 alternating requests on the two ports: never mixed up", mixed)
finally:
    srv.should_exit = True
    th.join(25)
ok("main server stops -> entrance stops too, thread ends (no hang)", (not th.is_alive()) and (not ms.listening()))
ok("'STOP' log present and no 'ERROR' log at all", any(x.startswith("[MAIL-SITE] STOP ") for x in LOG) and not [x for x in LOG if x.startswith("[MAIL-SITE] ERROR")], [asc(x) for x in LOG])
try:
    t = socket.socket(); t.bind(("127.0.0.1", B)); t.close(); freed = True
except OSError:
    freed = False
ok("port B is free again after the stop", freed)
print("   SMOKE RESULT: %s (%d/%d)" % ("PASS" if all(R) else "FAIL", sum(R), len(R)))
sys.exit(0 if all(R) else 1)
PYEOF
RC=$?
[ $RC -eq 0 ] || { echo "ABORT: the smoke test did not pass (rc=$RC). Nothing was changed. Paste this output to Victor."; exit 20; }
echo ""

echo "=== [1-3] switch ON: one line in .env (backup first; values are never printed) ==="
ADDED=0
BK=""
if grep -qE '^[[:space:]]*(export[[:space:]]+)?KNK_MAIL_SITE_PORT[[:space:]]*=' "$E"; then
  echo "   a KNK_MAIL_SITE_PORT line is already there - .env not touched"
else
  TS=$(date +%Y%m%d_%H%M%S)
  BK="$E.bak.kmail.$TS"
  cp -p "$E" "$BK" || { echo "ABORT: cannot back up .env. Nothing was changed."; exit 30; }
  [ -n "$(tail -c1 "$E")" ] && printf '\n' >> "$E"
  printf 'KNK_MAIL_SITE_PORT=%s\n' "$PORT" >> "$E"
  ADDED=1
  echo "   line added.  backup: $BK   (.env lines: $(wc -l < "$BK") -> $(wc -l < "$E"))"
fi
N=$(grep -cE "^KNK_MAIL_SITE_PORT=$PORT\$" "$E")
if [ "$N" != "1" ]; then
  echo "ABORT: expected exactly one 'KNK_MAIL_SITE_PORT=$PORT' line, found $N."
  [ "$ADDED" = "1" ] && cp -p "$BK" "$E" && echo "   .env restored from the backup. Nothing else was changed."
  exit 31
fi
echo ""

echo "=== [1-4] restart knk-works so it reads the switch (about 15 seconds) ==="
supervisorctl restart knk-works 2>&1 | tail -2
if wait_works; then
  echo "   WORKS is back: 5051 /api/version: $(ver)"
else
  echo "!! WORKS did not come back within 90s  ->  UNDOING the switch"
  if [ "$ADDED" = "1" ]; then cp -p "$BK" "$E"; else sed -i '/^KNK_MAIL_SITE_PORT=/d' "$E"; fi
  supervisorctl restart knk-works 2>&1 | tail -2
  wait_works
  echo "   after undo: 5051 /api/version: $(ver)"
  supervisorctl status knk-works 2>&1 | head -2
  echo "-- last lines of the error log:"
  tail -25 $APP/logs/uvicorn-error.log 2>/dev/null | cut -c1-200
  echo "RESULT: STEP1 FAILED and was UNDONE (the .env line is removed). Paste this output to Victor."
  exit 40
fi
echo ""

echo "=== [1-5] is the mail entrance waiting for port $PORT ? ==="
NP=$(supervisorctl pid knk-works 2>/dev/null)
sleep 4
L=$(grep -a "^\[MAIL-SITE\] [A-Z]* pid=$NP " $APP/logs/uvicorn.log 2>/dev/null | tail -1 | cut -d' ' -f1-4)
echo "   knk-works pid: $NP     last entrance log: ${L:-(none)}"
case "$L" in
  *" WAIT "*)   STATE=WAIT;   echo "   => WAITING for port $PORT (the old mail app still holds it) - exactly as planned" ;;
  *" LISTEN "*) STATE=LISTEN; echo "   => already LISTENING on port $PORT" ;;
  *)            STATE=UNKNOWN; echo "   => no WAIT / LISTEN line for this pid yet. Recent entrance lines:"
                grep -a "^\[MAIL-SITE\]" $APP/logs/uvicorn.log 2>/dev/null | tail -4 | cut -d' ' -f1-4 ;;
esac
echo "   ERROR lines from the entrance since this start: $(grep -a "^\[MAIL-SITE\] ERROR pid=$NP " $APP/logs/uvicorn.log 2>/dev/null | wc -l)"
echo "-- listeners:"
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | grep -E ':(5051|5053)[[:space:]]' | cut -c1-120
echo "-- 5053 right now: $(curl -s -m 5 -w ' [HTTP %{http_code}]' http://127.0.0.1:$PORT/api/version 2>/dev/null | head -c 100)"
echo ""
if [ "$STATE" = "UNKNOWN" ]; then
  echo "RESULT: STEP1 DONE BUT NOT CONFIRMED - WORKS is healthy, the switch is on, but the entrance state was not seen."
  echo "        Do NOT run Step2 yet. Paste this output to Victor."
  exit 50
fi
echo "RESULT: STEP1 OK - WORKS is healthy, the switch is on, entrance state = $STATE."
echo "NEXT  : ./kmail_switch_apply.ps1 -Step2      (stops the old mail app in KNKHAIST.MAIL)"
echo "UNDO  : ./kmail_switch_apply.ps1 -Undo1"
'@

# ---------------------------------------------------------------- Step2 (KNKHAIST.MAIL / 32203)
$bodyStep2 = @'
set +e
PYM=/opt/knk_mail/.venv/bin/python
WD='/opt/knk_mail/mail_watchdog\.sh'
APPP='/opt/knk_mail/.*run\.py'
HOOKRE='mail_watchdog\.sh|/opt/knk_mail.*run\.py'
probe(){ "$PYM" -c "
import urllib.request as u
try:
    r = u.urlopen('http://127.0.0.1:5053/api/version', timeout=4)
    print(r.status, r.read(90).decode('ascii', 'replace'))
except Exception as e:
    print('NO-ANSWER', type(e).__name__)
" 2>&1 | head -1; }
hooks_on(){ for F in /root/.bash_profile /root/.bashrc; do [ -f "$F" ] && sed -i 's/^#KMAIL-OFF-20261116# //' "$F"; done; }
hooks_off(){ for F in /root/.bash_profile /root/.bashrc; do [ -f "$F" ] && sed -i -E '/^[[:space:]]*#/! { /mail_watchdog\.sh|\/opt\/knk_mail.*run\.py/ s/^/#KMAIL-OFF-20261116# / }' "$F"; done; }
stop_old(){
  for P in $(pgrep -f "$WD"); do kill -TERM "$P" 2>/dev/null; done
  n=0; while [ $n -lt 10 ] && pgrep -f "$WD" >/dev/null 2>&1; do sleep 0.5; n=$((n+1)); done
  for P in $(pgrep -f "$WD"); do kill -KILL "$P" 2>/dev/null; done
  for P in $(pgrep -f "$APPP"); do kill -TERM "$P" 2>/dev/null; done
  n=0; while [ $n -lt 20 ] && pgrep -f "$APPP" >/dev/null 2>&1; do sleep 0.5; n=$((n+1)); done
  for P in $(pgrep -f "$APPP"); do kill -KILL "$P" 2>/dev/null; done
  sleep 1
}

echo "=== [2-0] which container / state before ==="
hostname
[ "$(hostname)" = "KNKHAIST.MAIL" ] || { echo "ABORT: this is not container KNKHAIST.MAIL. Nothing was changed."; exit 10; }
[ -x "$PYM" ] || { echo "ABORT: $PYM not found. Nothing was changed."; exit 11; }
echo "   5053 answers: $(probe)"
pgrep -af "$WD|$APPP" | cut -c1-110
echo ""

echo "=== [2-1] switch OFF the auto-start hooks (backup first) ==="
TS=$(date +%Y%m%d_%H%M%S)
TOUCHED=""
for F in /root/.bash_profile /root/.bashrc; do
  [ -f "$F" ] || continue
  A0=$(grep -vE '^[[:space:]]*#' "$F" | grep -cE "$HOOKRE")
  if [ "$A0" = "0" ]; then echo "   $F : no active hook line (already off)"; continue; fi
  cp -p "$F" "$F.bak.kmailoff.$TS" || { echo "ABORT: cannot back up $F."; for G in $TOUCHED; do cp -p "$G.bak.kmailoff.$TS" "$G"; done; echo "   Nothing was stopped."; exit 20; }
  sed -i -E '/^[[:space:]]*#/! { /mail_watchdog\.sh|\/opt\/knk_mail.*run\.py/ s/^/#KMAIL-OFF-20261116# / }' "$F"
  A1=$(grep -vE '^[[:space:]]*#' "$F" | grep -cE "$HOOKRE")
  if [ "$A1" != "0" ] || ! bash -n "$F" 2>/dev/null; then
    echo "ABORT: $F did not come out right (active lines left: $A1). Restoring the backups. Nothing was stopped."
    cp -p "$F.bak.kmailoff.$TS" "$F"
    for G in $TOUCHED; do cp -p "$G.bak.kmailoff.$TS" "$G"; done
    exit 21
  fi
  TOUCHED="$TOUCHED $F"
  echo "   $F : $A0 active hook line(s) -> 0     backup: $F.bak.kmailoff.$TS"
done
echo "   lines now switched off:"
grep -n '^#KMAIL-OFF-20261116# ' /root/.bash_profile /root/.bashrc 2>/dev/null | grep -viE 'key|token|pass|secret' | cut -c1-150
echo ""

echo "=== [2-2] stop the watchdog FIRST (it would start the app again) ==="
for P in $(pgrep -f "$WD"); do kill -TERM "$P" 2>/dev/null; done
n=0; while [ $n -lt 10 ] && pgrep -f "$WD" >/dev/null 2>&1; do sleep 0.5; n=$((n+1)); done
for P in $(pgrep -f "$WD"); do kill -KILL "$P" 2>/dev/null; done
sleep 0.5
if pgrep -f "$WD" >/dev/null 2>&1; then
  echo "ABORT: the watchdog is still running. Putting the hooks back. The app was NOT stopped."
  hooks_on
  exit 22
fi
echo "   watchdog stopped"
echo ""

echo "=== [2-3] stop the old mail app (NO file, NO database is touched) ==="
for P in $(pgrep -f "$APPP"); do kill -TERM "$P" 2>/dev/null; done
n=0; while [ $n -lt 20 ] && pgrep -f "$APPP" >/dev/null 2>&1; do sleep 0.5; n=$((n+1)); done
if pgrep -f "$APPP" >/dev/null 2>&1; then
  echo "   still running after 10s -> KILL"
  for P in $(pgrep -f "$APPP"); do kill -KILL "$P" 2>/dev/null; done
  sleep 1
fi
if pgrep -f "$WD|$APPP" >/dev/null 2>&1; then
  echo "!! something is still running:"; pgrep -af "$WD|$APPP" | cut -c1-110
else
  echo "   old mail app stopped"
fi
echo ""

echo "=== [2-4] wait for WORKS to take port 5053 (it retries every 10 seconds) ==="
report_ok(){
  echo "-- old app data is still there, untouched:"
  du -sh /opt/knk_mail 2>/dev/null | cut -c1-60
  ls -la /opt/knk_mail/data/mail.db 2>/dev/null | awk '{print "   mail.db size:", $5, "bytes"}'
  echo "-- old app processes now (must be none):"
  pgrep -af "$WD|$APPP" | cut -c1-110 || true
  pgrep -f "$WD|$APPP" >/dev/null 2>&1 || echo "   (none)"
  echo "RESULT: STEP2 OK - the old mail app is stopped and WORKS answers on port 5053."
  echo "UNDO  : ./kmail_switch_apply.ps1 -Undo1     then     ./kmail_switch_apply.ps1 -Undo2"
}
TAKEN=0
n=0
while [ $n -lt 30 ]; do
  R=$(probe)
  echo "   $(date +%H:%M:%S)   5053 answers: $R"
  case "$R" in *'"v"'*) TAKEN=1; break;; esac
  sleep 3; n=$((n+1))
done
echo ""
if [ "$TAKEN" = "1" ]; then
  report_ok
  exit 0
fi
echo "!! WORKS did not take port 5053 within 90s  ->  putting the old app back (auto-undo)"
hooks_on
setsid /bin/sh /opt/knk_mail/mail_watchdog.sh >/dev/null 2>&1 &
n=0
while [ $n -lt 50 ]; do
  R=$(probe)
  case "$R" in
    *'"v"'*)
      echo "   $(date +%H:%M:%S)   WORKS took the port after all: $R  ->  stopping the old app again"
      hooks_off
      stop_old
      report_ok
      exit 0 ;;
    200*) break ;;
  esac
  sleep 3; n=$((n+1))
done
echo "   after auto-undo, 5053 answers: $R"
pgrep -af "$WD|$APPP" | cut -c1-110
case "$R" in
  200*) echo "RESULT: STEP2 UNDONE - the old app is running again (hooks are back on). Was Step1 finished? Paste this output to Victor." ;;
  *)    echo "RESULT: STEP2 UNDONE BUT NOTHING ANSWERS ON 5053 YET - the watchdog will keep trying. Paste this output to Victor NOW." ;;
esac
exit 30
'@

# ---------------------------------------------------------------- Undo1 (KNKHAIST / 32201)
$bodyUndo1 = @'
set +e
APP=/opt/knk_haist
E=$APP/.env
MAIN=5051
ver(){ curl -s -m 5 http://127.0.0.1:$MAIN/api/version 2>/dev/null | head -c 60; }
echo "=== [U1] which container ==="
hostname
[ "$(hostname)" = "KNKHAIST" ] || { echo "ABORT: this is not container KNKHAIST. Nothing was changed."; exit 10; }
if grep -qE '^KNK_MAIL_SITE_PORT=' "$E"; then
  TS=$(date +%Y%m%d_%H%M%S)
  cp -p "$E" "$E.bak.kmailundo.$TS" || { echo "ABORT: cannot back up .env. Nothing was changed."; exit 30; }
  sed -i '/^KNK_MAIL_SITE_PORT=/d' "$E"
  echo "   line removed.  backup: $E.bak.kmailundo.$TS   (.env lines now: $(wc -l < "$E"))"
else
  echo "   no KNK_MAIL_SITE_PORT line in .env - nothing to remove"
fi
echo "=== restart knk-works (about 15 seconds) ==="
supervisorctl restart knk-works 2>&1 | tail -2
n=0; while [ $n -lt 30 ]; do V=$(ver); case "$V" in *'"v"'*) break;; esac; sleep 3; n=$((n+1)); done
echo "   5051 /api/version: $V"
supervisorctl status knk-works 2>&1 | head -2
echo "-- listeners:"
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | grep -E ':(5051|5053)[[:space:]]' | cut -c1-120
case "$V" in *'"v"'*) echo "RESULT: UNDO1 OK - WORKS is healthy and no longer listens on 5053." ;; *) echo "RESULT: UNDO1 - WORKS is NOT answering. Paste this output to Victor NOW."; exit 40 ;; esac
'@

# ---------------------------------------------------------------- Undo2 (KNKHAIST.MAIL / 32203)
$bodyUndo2 = @'
set +e
PYM=/opt/knk_mail/.venv/bin/python
WD='/opt/knk_mail/mail_watchdog\.sh'
APPP='/opt/knk_mail/.*run\.py'
probe(){ "$PYM" -c "
import urllib.request as u
try:
    r = u.urlopen('http://127.0.0.1:5053/healthz', timeout=4)
    print(r.status, r.read(90).decode('ascii', 'replace'))
except Exception as e:
    print('NO-ANSWER', type(e).__name__)
" 2>&1 | head -1; }
echo "=== [U2] which container ==="
hostname
[ "$(hostname)" = "KNKHAIST.MAIL" ] || { echo "ABORT: this is not container KNKHAIST.MAIL. Nothing was changed."; exit 10; }
echo "   5053 /healthz before: $(probe)"
for F in /root/.bash_profile /root/.bashrc; do
  [ -f "$F" ] || continue
  N=$(grep -c '^#KMAIL-OFF-20261116# ' "$F")
  sed -i 's/^#KMAIL-OFF-20261116# //' "$F"
  echo "   $F : $N hook line(s) switched back on"
done
pgrep -f "$WD" >/dev/null 2>&1 || setsid /bin/sh /opt/knk_mail/mail_watchdog.sh >/dev/null 2>&1 &
echo "=== waiting for the old app (the watchdog starts it; up to about 2 minutes) ==="
n=0
while [ $n -lt 50 ]; do
  R=$(probe)
  case "$R" in 200*'KNK Eum MAIL'*) break;; esac
  sleep 3; n=$((n+1))
done
echo "   5053 /healthz now: $R"
pgrep -af "$WD|$APPP" | cut -c1-110
case "$R" in 200*'KNK Eum MAIL'*) echo "RESULT: UNDO2 OK - the old mail app is running again." ;; *) echo "RESULT: UNDO2 - the old app did not come up (is port 5053 still held by WORKS? run -Undo1 first). Paste this output to Victor."; exit 40 ;; esac
'@

$n = @(@($Step1.IsPresent, $Step2.IsPresent, $Undo1.IsPresent, $Undo2.IsPresent) | Where-Object { $_ }).Count
if ($n -ne 1) {
    Write-Host "Choose exactly ONE of:  -Step1   -Step2   -Undo1   -Undo2" -ForegroundColor Yellow
    Write-Host "  order:      Step1 (KNKHAIST 32201)  ->  Step2 (KNKHAIST.MAIL 32203)"
    Write-Host "  to go back: Undo1                   ->  Undo2"
    return
}

Write-Host "==================================================" -ForegroundColor Cyan
if ($Step1) {
    Write-Host "  kmail switch - STEP 1   (KNKHAIST, ssh 32201)" -ForegroundColor Cyan
    Write-Host "  smoke test -> one line in .env -> restart knk-works (about 15s) -> confirm" -ForegroundColor Yellow
    Write-Host "==================================================" ; Write-Host "(type the SSH password)" -ForegroundColor Green
    Invoke-Remote 32201 $bodyStep1
} elseif ($Step2) {
    Write-Host "  kmail switch - STEP 2   (KNKHAIST.MAIL, ssh 32203)" -ForegroundColor Cyan
    Write-Host "  hooks off -> stop watchdog -> stop old mail app (no file deleted) -> wait for WORKS on 5053" -ForegroundColor Yellow
    Write-Host "==================================================" ; Write-Host "(type the SSH password)" -ForegroundColor Green
    Invoke-Remote 32203 $bodyStep2
} elseif ($Undo1) {
    Write-Host "  kmail switch - UNDO 1   (KNKHAIST, ssh 32201)" -ForegroundColor Cyan
    Write-Host "  remove the .env line -> restart knk-works" -ForegroundColor Yellow
    Write-Host "==================================================" ; Write-Host "(type the SSH password)" -ForegroundColor Green
    Invoke-Remote 32201 $bodyUndo1
} else {
    Write-Host "  kmail switch - UNDO 2   (KNKHAIST.MAIL, ssh 32203)" -ForegroundColor Cyan
    Write-Host "  hooks back on -> start the watchdog -> old mail app comes back" -ForegroundColor Yellow
    Write-Host "==================================================" ; Write-Host "(type the SSH password)" -ForegroundColor Green
    Invoke-Remote 32203 $bodyUndo2
}
Write-Host ""
Write-Host "[finished] Please paste the whole output to Victor." -ForegroundColor Green
