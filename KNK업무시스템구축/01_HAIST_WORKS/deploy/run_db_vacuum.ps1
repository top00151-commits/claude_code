# ============================================================
# WORKS knk.db VACUUM - reclaim space freed by BLOB migration. 2026-08-31.
# !! VACUUM takes an EXCLUSIVE lock: every WORKS user is blocked until it ends.
#    Run off-peak, or with the CEO's explicit go. Duration is reported.
# Pre-checks free space (VACUUM needs ~= db size for its temp copy) and aborts if short.
# ASCII-ONLY (PS 5.1 mis-reads UTF-8 -> Korean breaks remote script).
# Usage:  ./run_db_vacuum.ps1 -Check     (measure only, NO lock, changes nothing)
#         ./run_db_vacuum.ps1            (actually VACUUM)
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]$Port       = 32201,
    [string]$User    = "root",
    [switch]$Check
)
$ErrorActionPreference = "Stop"
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")
$flagChk = if ($Check) { "1" } else { "0" }

$script = @"
set +e
APP=/opt/knk_haist
PY=`$APP/.venv/bin/python
DB=`$APP/data/knk.db
CHK=$flagChk
echo "################ [0] PRE-CHECK (no lock) ################"
`$PY - <<PYPRE
import os, sqlite3, shutil
db = "`$DB"
size = os.path.getsize(db)
free = shutil.disk_usage(os.path.dirname(db)).free
c = sqlite3.connect(db)
c.execute("PRAGMA busy_timeout=5000")
page = c.execute("PRAGMA page_size").fetchone()[0]
total = c.execute("PRAGMA page_count").fetchone()[0]
freelist = c.execute("PRAGMA freelist_count").fetchone()[0]
blob_left = c.execute("SELECT COUNT(*) FROM mail_attachments WHERE data IS NOT NULL").fetchone()[0]
print("db size        : %.1f MB" % (size/1048576.0))
print("free disk      : %.1f GB   (VACUUM needs ~%.1f GB temp)" % (free/1073741824.0, size/1073741824.0))
print("free pages     : %d of %d  (~%.1f MB reclaimable)" % (freelist, total, freelist*page/1048576.0))
print("rows still BLOB: %d  (should be 0 before VACUUM)" % blob_left)
ok = True
if free < size * 1.15:
    print("ERROR: not enough free disk for VACUUM temp copy"); ok = False
if blob_left:
    print("WARN: migration not finished - VACUUM now reclaims less than possible")
raise SystemExit(0 if ok else 3)
PYPRE
if [ "`$?" != "0" ]; then echo ">>> ABORT at pre-check"; exit 3; fi
if [ "`$CHK" = "1" ]; then echo ""; echo ">>> -Check requested: measured only, NO VACUUM run, nothing locked."; exit 0; fi
echo ""
echo "################ [1] VACUUM (DB LOCKED during this) ################"
date '+start %F %T'
`$PY - <<PYVAC
import os, sqlite3, time
db = "`$DB"
before = os.path.getsize(db)
c = sqlite3.connect(db, timeout=600, isolation_level=None)
c.execute("PRAGMA busy_timeout=600000")
t = time.time()
c.execute("VACUUM")
el = time.time() - t
c.close()
after = os.path.getsize(db)
print("VACUUM done in %.0f s (%.1f min)" % (el, el/60.0))
print("db size: %.1f MB -> %.1f MB   reclaimed %.1f MB"
      % (before/1048576.0, after/1048576.0, (before-after)/1048576.0))
PYVAC
rc=`$?
date '+end   %F %T'
if [ "`$rc" != "0" ]; then echo ">>> VACUUM returned error rc=`$rc"; fi
echo ""
echo "################ [2] POST-CHECK ################"
`$PY - <<PYPOST
import sqlite3
c = sqlite3.connect("`$DB", timeout=30)
print("integrity_check:", c.execute("PRAGMA quick_check").fetchone()[0])
print("attachments rows:", c.execute("SELECT COUNT(*) FROM mail_attachments").fetchone()[0])
print("rows on file    :", c.execute("SELECT COUNT(*) FROM mail_attachments WHERE path IS NOT NULL").fetchone()[0])
PYPOST
echo "-- app serving? --"
echo "5051 /api/version: HTTP `$(curl -s -o /tmp/vv -m 10 -w '%{http_code}' http://127.0.0.1:5051/api/version)  `$(head -c 120 /tmp/vv 2>/dev/null)"
echo "[done]"
"@

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  knk.db VACUUM" -ForegroundColor Cyan
if ($Check) { Write-Host "  MODE: CHECK ONLY (no lock, no changes)" -ForegroundColor Yellow }
else        { Write-Host "  WARNING: DB is LOCKED for all users during VACUUM" -ForegroundColor Red }
Write-Host "  (type SSH password when asked)" -ForegroundColor Yellow
Write-Host "=================================================="
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
Write-Host "`n[DONE] Paste the FULL output above to Victor." -ForegroundColor Green
