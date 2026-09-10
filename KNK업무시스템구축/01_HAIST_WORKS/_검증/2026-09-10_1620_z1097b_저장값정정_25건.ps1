# =============================================================================
#  KNK WORKS - z1097b : fix stored projects.order_amount for mixed-currency
#                       projects (25 rows)
#  Created : 2026-09-10 16:20 KST  by session01 (Victor / sales)
#  CEO approval : 2026-09-10 "수정 진행해. 진행하고 검증까지 진행해."
#
#  WHAT IT DOES
#    projects.order_amount was filled by SUM(orders.total_amount) which ignored
#    currency - KRW and USD were added together. The CODE is already fixed and
#    live (5b96baa); this script fixes the STORED VALUES that are still wrong.
#
#  NOT URGENT: the deployed self-heal already corrects a project the moment
#    someone opens its detail page or edits one of its orders. This script just
#    does all 25 at once. Running it twice is harmless (idempotent).
#
#  SAFETY
#    1) takes a full DB backup first  -> knk_pre_z1097b_20260910.db
#    2) computes new values with the ACTUAL DEPLOYED code (no separate copy)
#    3) one transaction: all rows or none
#    4) writes a rollback file        -> z1097b_rollback_20260910.sql
#    5) records every change in project_history
#    6) verifies immediately afterwards
#    Single-currency projects are NOT touched (verified: 0 of 326 change).
#
#  USAGE (PowerShell)
#      .\2026-09-10_1620_z1097b_저장값정정_25건.ps1
#  SSH password is typed by you; it is never stored in this file.
#  Output is printed AND saved next to this script.
# =============================================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]   $Port    = 32201,
    [string]$User    = "root"
)

$ErrorActionPreference = "Stop"
$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$outFile = Join-Path $here "2026-09-10_1620_z1097b_저장값정정_결과.txt"

$py = @'
# -*- coding: utf-8 -*-
# z1097b data fix. ASCII output only.
import ast, io, os, sqlite3, time, types

MAIN = "/opt/knk_haist/app/main.py"
SRC  = "/opt/knk_haist/data/knk.db"
BK   = "/opt/knk_haist/data/knk_pre_z1097b_20260910.db"
RB   = "/opt/knk_haist/data/z1097b_rollback_20260910.sql"

# ---- 1) backup ------------------------------------------------------------
t0 = time.time()
s = sqlite3.connect("file:%s?mode=ro" % SRC, uri=True)
d = sqlite3.connect(BK)
s.backup(d)
d.close()
s.close()
print("== 1) BACKUP ==")
print("   %s" % BK)
print("   %.1f MB in %.1fs" % (os.path.getsize(BK) / 1048576.0, time.time() - t0))
_b = sqlite3.connect(BK)
print("   quick_check: %s" % _b.execute("PRAGMA quick_check").fetchone()[0])
_b.close()

# ---- 2) load the DEPLOYED calculation code --------------------------------
WANT = ["_fx_load_rates", "_fx_pick", "_fx_rate_for", "_fx_to_krw",
        "_ccy_get", "_ccy_breakdown", "_recalc_project_amount"]
tree = ast.parse(io.open(MAIN, encoding="utf-8").read())
picked, found = [], set()
for n in tree.body:
    nm = None
    if isinstance(n, ast.FunctionDef):
        nm = n.name
    elif (isinstance(n, ast.Assign) and len(n.targets) == 1
          and isinstance(n.targets[0], ast.Name)):
        nm = n.targets[0].id
    if nm in WANT:
        picked.append(n)
        found.add(nm)
missing = [w for w in WANT if w not in found]
print("")
print("== 2) DEPLOYED CODE ==")
if missing:
    print("   ERROR: deployed main.py is missing %s" % missing)
    print("   -> the code fix (5b96baa) is not live yet. Aborting.")
    raise SystemExit(1)
print("   loaded from live main.py: OK")
M = types.ModuleType("live")
exec(compile(ast.Module(body=picked, type_ignores=[]), MAIN, "exec"), M.__dict__)

# ---- 3) apply -------------------------------------------------------------
c = sqlite3.connect(SRC, timeout=30)
c.row_factory = sqlite3.Row
c.execute("PRAGMA busy_timeout=30000")
RATES = M._fx_load_rates(c)

allo = [dict(r) for r in c.execute(
    "SELECT project_id pid, COALESCE(currency,'KRW') currency"
    " FROM orders WHERE project_id IS NOT NULL")]
by = {}
for r in allo:
    by.setdefault(r["pid"], set()).add(r["currency"])
mixed = sorted(k for k, v in by.items() if len(v) > 1)

print("")
print("== 3) APPLY  (mixed-currency projects: %d) ==" % len(mixed))
done, same, skip, rb = 0, 0, 0, []
c.execute("BEGIN")
try:
    for pid in mixed:
        p = c.execute("SELECT mgmt_code, COALESCE(order_amount,0) oa"
                      " FROM projects WHERE id=?", (pid,)).fetchone()
        new = M._recalc_project_amount(c, pid, rates=RATES)
        if new is None:
            skip += 1
            print("   id=%-5s %-9s  SKIPPED (no fx rate) - left untouched"
                  % (pid, p["mgmt_code"]))
            continue
        old = float(p["oa"])
        if abs(old - new) < 0.005:
            same += 1
            continue
        rb.append("UPDATE projects SET order_amount=%.2f WHERE id=%d;  -- %s"
                  % (old, pid, p["mgmt_code"]))
        c.execute("UPDATE projects SET order_amount=? WHERE id=?", (float(new), pid))
        c.execute("INSERT INTO project_history(project_id, changed_by, field,"
                  " old_value, new_value, note) VALUES(?,?,?,?,?,?)",
                  (pid, None, "수주액(통화 환산 정정)",
                   "{:,.2f}".format(old), "{:,.2f}".format(new),
                   "z1097b 2026-09-10 - KRW+USD added without FX; corrected"
                   " using monthly base rates"))
        done += 1
        print("   id=%-5s %-9s %18s -> %18s"
              % (pid, p["mgmt_code"], "{:,.2f}".format(old), "{:,.2f}".format(new)))
    c.execute("COMMIT")
except Exception as e:
    c.execute("ROLLBACK")
    print("   !! FAILED, rolled back: %s" % e)
    raise
print("")
print("   corrected %d · already correct %d · left untouched %d" % (done, same, skip))

io.open(RB, "w", encoding="utf-8").write(
    "-- z1097b rollback (2026-09-10). Run with sqlite3 if ever needed.\n"
    + "\n".join(rb) + "\n")
print("   rollback file: %s  (%d rows)" % (RB, len(rb)))

# ---- 4) verify ------------------------------------------------------------
print("")
print("== 4) VERIFY ==")
bad = 0
for pid in mixed:
    p = c.execute("SELECT mgmt_code, COALESCE(order_amount,0) oa"
                  " FROM projects WHERE id=?", (pid,)).fetchone()
    exp = M._recalc_project_amount(c, pid, rates=RATES)
    if exp is not None and abs(float(p["oa"]) - exp) > 0.005:
        bad += 1
        print("   !! id=%s %s stored %.2f expected %.2f"
              % (pid, p["mgmt_code"], p["oa"], exp))
print("   mixed projects still wrong : %d of %d" % (bad, len(mixed)))

single = [k for k, v in by.items() if len(v) == 1]
sbad = 0
for pid in single:
    p = c.execute("SELECT COALESCE(order_amount,0) oa FROM projects WHERE id=?",
                  (pid,)).fetchone()
    exp = M._recalc_project_amount(c, pid, rates=RATES)
    if exp is not None and abs(float(p["oa"]) - exp) > 0.5:
        sbad += 1
print("   single-currency projects changed : %d of %d  (should be 0)"
      % (sbad, len(single)))

h = c.execute("SELECT COUNT(*) n FROM project_history"
              " WHERE field='수주액(통화 환산 정정)'").fetchone()["n"]
print("   history rows written : %d" % h)
print("   integrity            : %s" % c.execute("PRAGMA quick_check").fetchone()[0])
c.close()
print("")
print("== DONE ==")
'@

Write-Host "=====================================================" -ForegroundColor Yellow
Write-Host "  z1097b - fix stored project amounts (25 rows)"       -ForegroundColor Yellow
Write-Host ("  target : {0}@{1}:{2}" -f $User, $SshHost, $Port)    -ForegroundColor Yellow
Write-Host "  a full DB backup is taken before anything is written." -ForegroundColor Yellow
Write-Host "  running it twice is harmless." -ForegroundColor Yellow
Write-Host "=====================================================" -ForegroundColor Yellow

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")
$remote = "echo $b64 | base64 -d > /tmp/_z1097b_fix.py; /opt/knk_haist/.venv/bin/python -u /tmp/_z1097b_fix.py"

ssh @sshOpts "$User@$SshHost" $remote | Tee-Object -FilePath $outFile

Write-Host ""
Write-Host ("result saved : {0}" -f $outFile) -ForegroundColor Green
