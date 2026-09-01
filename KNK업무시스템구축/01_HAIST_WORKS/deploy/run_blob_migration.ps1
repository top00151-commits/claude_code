# ============================================================
# WORKS mail attachment BLOB -> content-hash file migration (STAGED, LIVE).
# 2026-08-31. Stages: state -> backup -> pilot(200) -> full -> post-verify.
# Aborts if any stage fails. Does NOT run VACUUM (separate, locks DB).
# Safe to re-run: migration is idempotent and resumable.
# ASCII-ONLY (PS 5.1 mis-reads UTF-8 -> Korean breaks remote script).
# Usage:  ./run_blob_migration.ps1            (full)
#         ./run_blob_migration.ps1 -DryRun    (state only, changes nothing)
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]$Port       = 32201,
    [string]$User    = "root",
    [switch]$DryRun,
    [switch]$SkipBackup
)
$ErrorActionPreference = "Stop"
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")

# ship the migration script (single source of truth = the .py in this repo)
$pyLocal = Join-Path $PSScriptRoot "migrate_mail_blobs_to_files.py"
if (-not (Test-Path $pyLocal)) { throw "missing: $pyLocal" }
$pyB64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($pyLocal))

$flagDry  = if ($DryRun)     { "1" } else { "0" }
$flagNoBk = if ($SkipBackup) { "1" } else { "0" }

$script = @"
set +e
APP=/opt/knk_haist
PY=`$APP/.venv/bin/python
DB=`$APP/data/knk.db
MIG=/tmp/migrate_mail_blobs.py
DRY=$flagDry
NOBK=$flagNoBk
echo '$pyB64' | base64 -d > "`$MIG" || { echo 'ERROR: cannot write migration script'; exit 1; }
echo "[ship] migration script -> `$MIG (`$(wc -l < `$MIG) lines)"
echo ""
echo "################ [0] STATE + DISK (no changes) ################"
`$PY "`$MIG" --db "`$DB" --dry-run
rc=`$?
if [ "`$rc" != "0" ]; then echo ">>> ABORT at state check (rc=`$rc)"; exit `$rc; fi
if [ "`$DRY" = "1" ]; then echo ""; echo ">>> DryRun requested - stopping here. Nothing changed."; exit 0; fi
echo ""
echo "################ [1] BACKUP live DB (house standard .backup) ################"
if [ "`$NOBK" = "1" ]; then
  echo "(skipped by flag)"
else
  BK=`$APP/data/backups
  mkdir -p "`$BK"
  TS=`$(date '+%Y%m%d_%H%M%S')
  echo "backup -> `$BK/knk_premigrate_`$TS.db"
  `$PY - <<PYBK
import sqlite3, os, time
src, dst = "`$DB", "`$BK/knk_premigrate_`$TS.db"
free = os.statvfs(os.path.dirname(dst))
need = os.path.getsize(src)
if free.f_bavail * free.f_frsize < need * 1.1:
    print("ERROR: not enough space for backup"); raise SystemExit(9)
t = time.time()
s = sqlite3.connect(src); d = sqlite3.connect(dst)
with d: s.backup(d)
s.close(); d.close()
print("backup OK: %.1f MB in %.0fs" % (os.path.getsize(dst)/1048576.0, time.time()-t))
PYBK
  if [ "`$?" != "0" ]; then echo ">>> ABORT: backup failed"; exit 9; fi
fi
echo ""
echo "################ [2] PILOT: first 200 rows ################"
`$PY "`$MIG" --db "`$DB" --batch 50 --limit 200 --sleep 0.2
if [ "`$?" != "0" ]; then echo ">>> ABORT: pilot failed"; exit 4; fi
echo ""
echo "-- pilot integrity: re-verify migrated rows against files --"
`$PY - <<PYCK
import sqlite3, hashlib, os
c = sqlite3.connect("`$DB"); c.row_factory = sqlite3.Row
rows = c.execute("SELECT id,path,sha256 FROM mail_attachments WHERE data IS NULL AND path IS NOT NULL AND sha256 IS NOT NULL ORDER BY id LIMIT 200").fetchall()
bad = 0
for r in rows:
    try:
        h = hashlib.sha256(open(r["path"],"rb").read()).hexdigest()
        if h != r["sha256"]: bad += 1; print("MISMATCH id=", r["id"])
    except Exception as e:
        bad += 1; print("UNREADABLE id=", r["id"], e)
print("checked %d migrated rows, mismatches=%d" % (len(rows), bad))
raise SystemExit(1 if bad else 0)
PYCK
if [ "`$?" != "0" ]; then echo ">>> ABORT: pilot integrity check FAILED (BLOBs still safe)"; exit 5; fi
echo "pilot OK"
echo ""
echo "################ [3] FULL migration (rest of rows) ################"
`$PY "`$MIG" --db "`$DB" --batch 100 --sleep 0.2
if [ "`$?" != "0" ]; then echo ">>> full run returned error - re-runnable, BLOBs kept"; fi
echo ""
echo "################ [4] POST-VERIFY ################"
`$PY - <<PYPV
import sqlite3, os
c = sqlite3.connect("`$DB")
left = c.execute("SELECT COUNT(*) FROM mail_attachments WHERE data IS NOT NULL").fetchone()[0]
onfile = c.execute("SELECT COUNT(*) FROM mail_attachments WHERE data IS NULL AND path IS NOT NULL").fetchone()[0]
nopath = c.execute("SELECT COUNT(*) FROM mail_attachments WHERE data IS NULL AND path IS NULL").fetchone()[0]
print("rows still BLOB      :", left, " (0 = fully migrated)")
print("rows on file         :", onfile)
print("rows meta-only(nopath):", nopath, " (oversize/empty - normal)")
print("db size              : %.1f MB (VACUUM not run yet)" % (os.path.getsize("`$DB")/1048576.0))
PYPV
echo "-- attachment store size --"
du -sh "`$APP/data/mail_att" 2>/dev/null
echo "-- unique content files --"
find "`$APP/data/mail_att/sha256" -type f 2>/dev/null | wc -l
echo ""
echo "-- app still serving? (port 5051) --"
code=`$(curl -s -o /tmp/vv -m 8 -w '%{http_code}' http://127.0.0.1:5051/api/version)
echo "5051 /api/version: HTTP `$code  `$(head -c 120 /tmp/vv 2>/dev/null)"
echo ""
echo "NOTE: VACUUM was NOT run (it locks the whole DB). Reclaim step is separate."
echo "[done]"
"@

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  BLOB -> file migration (STAGED)" -ForegroundColor Cyan
if ($DryRun) { Write-Host "  MODE: DRY-RUN (no changes)" -ForegroundColor Yellow }
Write-Host "  This can take several minutes. Leave the window open." -ForegroundColor Yellow
Write-Host "  (type SSH password when asked)" -ForegroundColor Yellow
Write-Host "=================================================="
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
Write-Host "`n[DONE] Paste the FULL output above to Victor." -ForegroundColor Green
