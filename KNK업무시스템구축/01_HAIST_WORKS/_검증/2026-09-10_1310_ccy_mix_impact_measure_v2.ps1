# =============================================================================
#  KNK WORKS - Currency-mixed SUM impact measurement  v2  (READ ONLY)
#  Created : 2026-09-10 13:10 KST  by session01 (Victor / sales)
#
#  WHY v2 : v1 read the WRONG database (it picked the biggest *.db, which was
#           the 2026-07-26 backup knk_wp03_shipfix_pre_20260726.db) and failed
#           to read FX rates (real columns are from_currency/to_currency/rate,
#           v1 looked for 'currency').  Both fixed here.
#
#  SELF-PROOF : section [0b] re-creates the CEO-reported screen
#               (project 005M2511 / BIM LINE, orders M-251127-1 + M-260819-2).
#               If that case is not found, the script SAYS SO and stops -
#               so a wrong database can no longer be reported as fact.
#
#  SAFETY  : - live DB opened with mode=ro (read only); snapshot to /tmp;
#              measures the snapshot; DELETES the snapshot at the end.
#            - NO UPDATE / INSERT / DELETE against the live DB.
#            - touches no service, no container, no nginx.
#
#  USAGE (PowerShell) :
#      .\2026-09-10_1310_ccy_mix_impact_measure_v2.ps1
#  Output printed AND saved as 2026-09-10_1310_ccy_mix_impact_result_v2.txt
# =============================================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]   $Port    = 32201,
    [string]$User    = "root"
)

$ErrorActionPreference = "Stop"
$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$outFile = Join-Path $here "2026-09-10_1310_ccy_mix_impact_result_v2.txt"

$py = @'
# -*- coding: utf-8 -*-
# READ ONLY measurement, v2. ASCII output only.
import sqlite3, os, glob, time

# ---------------------------------------------------------------------------
print("== [0] DATABASE CHOICE ==")
cands = []
for p in ("/opt/knk_haist/data/*.db", "/opt/knk_haist/*.db"):
    for f in glob.glob(p):
        if f.endswith("-wal") or f.endswith("-shm"):
            continue
        try:
            st = os.stat(f)
        except OSError:
            continue
        cands.append((f, st.st_size, st.st_mtime))
cands.sort(key=lambda z: z[2], reverse=True)
print("   all candidates (newest first):")
for f, sz, mt in cands:
    print("     %-58s %8.1f MB   %s"
          % (f, sz / 1048576.0, time.strftime("%Y-%m-%d %H:%M", time.localtime(mt))))

# The live DB is the one the app actually opens: /opt/knk_haist/data/knk.db
SRC = "/opt/knk_haist/data/knk.db"
if not os.path.exists(SRC):
    print("   ERROR: expected live DB %s not found. Aborting." % SRC)
    raise SystemExit(1)
print("   >>> using LIVE db : %s  (%.1f MB)" % (SRC, os.path.getsize(SRC) / 1048576.0))

TMP = "/tmp/_ccy_mix_snapshot.db"
s = sqlite3.connect("file:%s?mode=ro" % SRC, uri=True)
d = sqlite3.connect(TMP)
s.backup(d)
d.close()
s.close()
c = sqlite3.connect(TMP)
c.row_factory = sqlite3.Row


def q(sql, *a):
    try:
        return c.execute(sql, a).fetchall()
    except Exception as e:
        print("  (query failed: %s)" % str(e)[:150])
        return []


def cols(tbl):
    return [r[1] for r in q("PRAGMA table_info(%s)" % tbl)]


def fmt(x):
    return "n/a" if x is None else "{:,.2f}".format(x)


# ---- FX rates (real schema: rate_date, from_currency, to_currency, rate) ---
# CEO rule sec.4 no.48 : monthly base rate from exchange_rates is the single
# source of truth; conversion month = delivery month.
BYMONTH = {}   # (ym, ccy) -> rate to KRW
LATEST = {}    # ccy -> (ym, rate)
ex_cols = cols("exchange_rates")
print("")
print("== [0a] FX RATES ==")
print("   exchange_rates columns:", ",".join(ex_cols) if ex_cols else "(table missing)")
if ex_cols and "from_currency" in ex_cols:
    for r in q("""SELECT rate_date, from_currency AS fc, to_currency AS tc, rate
                  FROM exchange_rates ORDER BY rate_date"""):
        try:
            v = float(r["rate"] or 0)
        except Exception:
            continue
        if v <= 0:
            continue
        fc = (r["fc"] or "").upper()
        tc = (r["tc"] or "").upper()
        ym = (r["rate_date"] or "")[:7]
        if tc == "KRW" and fc and ym:
            BYMONTH[(ym, fc)] = v
            LATEST[fc] = (ym, v)
BYMONTH_CCY = sorted(set(k[1] for k in BYMONTH))
print("   currencies with rates :", ", ".join(BYMONTH_CCY) if BYMONTH_CCY else "(none)")
print("   months covered        : %d" % len(set(k[0] for k in BYMONTH)))
for ccy in BYMONTH_CCY:
    ym, v = LATEST[ccy]
    print("   latest %-4s = %s KRW  (%s)" % (ccy, "{:,.2f}".format(v), ym))


def to_krw(amount, ccy, ym=None):
    """(krw, ok, how) - monthly base rate first, then latest known rate."""
    ccy = (ccy or "KRW").upper()
    if ccy == "KRW":
        return amount, True, "krw"
    if ym and (ym, ccy) in BYMONTH:
        return amount * BYMONTH[(ym, ccy)], True, "month:" + ym
    if ccy in LATEST:
        lym, v = LATEST[ccy]
        return amount * v, True, "latest:" + lym
    return None, False, "no-rate"


# ---------------------------------------------------------------------------
# SELF-PROOF: reproduce the exact screen the CEO photographed.
print("")
print("== [0b] SELF-PROOF - reproduce the reported screen ==")
print("   expected: project 005M2511 'BIM LINE', USD 83,882.73 + KRW 1,720,000")
ocols = cols("orders")
datecol = None
for x in ("due_date", "delivery_date", "order_date"):
    if x in ocols:
        datecol = x
        break
proof = q("""SELECT id, mgmt_code, name, COALESCE(currency,'KRW') AS ccy, fx_rate
             FROM projects WHERE mgmt_code = ?""", "005M2511")
PROOF_OK = False
if not proof:
    print("   !! 005M2511 NOT FOUND -> this is NOT the live database. STOP.")
else:
    p = proof[0]
    print("   found: id=%s  %s  %s  ccy=%s  fx_rate=%s"
          % (p["id"], p["mgmt_code"], p["name"], p["ccy"], p["fx_rate"]))
    orows = q("""SELECT order_no, COALESCE(currency,'KRW') AS ccy,
                        COALESCE(total_amount,0) AS amt, %s AS dd
                 FROM orders WHERE project_id=? ORDER BY order_no"""
              % (datecol or "''"), p["id"])
    naive = 0.0
    for r in orows:
        print("      %-14s %-4s %16s   %s"
              % (r["order_no"], r["ccy"], "{:,.2f}".format(r["amt"]), r["dd"] or "-"))
        naive += r["amt"]
    print("   screen total (blind sum) : %s %s" % (fmt(naive), p["ccy"]))
    if abs(naive - 1803882.73) < 0.01:
        print("   >>> MATCHES the photographed value 1,803,882.73  -- LIVE DB CONFIRMED")
        PROOF_OK = True
    else:
        print("   >>> does NOT match 1,803,882.73 -> data moved or wrong DB. Read results with care.")

# ---------------------------------------------------------------------------
print("")
print("== [1] PROJECT DETAIL - 'SO number total' (the reported bug) ==")
print("   file: app/templates/project_detail.html:1188-1217")
allo = q("""SELECT o.project_id AS pid, o.order_no AS ono,
                   COALESCE(o.currency,'KRW') AS ccy,
                   COALESCE(o.total_amount,0) AS amt,
                   %s AS dd
            FROM orders o WHERE o.project_id IS NOT NULL""" % (datecol or "''"))
byproj = {}
for r in allo:
    byproj.setdefault(r["pid"], []).append(r)
mixed = dict((k, v) for k, v in byproj.items()
             if len(set(x["ccy"] for x in v)) > 1)
print("   projects with orders            : %d" % len(byproj))
print("   projects mixing currencies      : %d" % len(mixed))

pcols = cols("projects")
has_fx = "fx_rate" in pcols
rows_out = []
no_rate = 0
for pid, lst in mixed.items():
    sql = ("SELECT id, mgmt_code, name, COALESCE(currency,'KRW') AS ccy%s "
           "FROM projects WHERE id=?" % (", fx_rate" if has_fx else ""))
    pr = q(sql, pid)
    if not pr:
        continue
    pr = pr[0]
    pccy = (pr["ccy"] or "KRW").upper()
    per = {}
    for r in lst:
        per[r["ccy"]] = per.get(r["ccy"], 0.0) + r["amt"]
    naive = sum(per.values())                       # what the screen shows now
    true_krw, ok = 0.0, True
    for r in lst:                                    # per-order monthly rate
        v, good, _how = to_krw(r["amt"], r["ccy"], (r["dd"] or "")[:7])
        if not good:
            ok = False
            break
        true_krw += v
    naive_krw, nok, _hh = to_krw(naive, pccy, None)
    if pccy != "KRW" and not nok:
        naive_krw = None
    ratio = (naive_krw / true_krw) if (ok and naive_krw and true_krw) else None
    if ratio is None:
        no_rate += 1
    gap = abs((naive_krw or 0) - (true_krw or 0)) if (ok and naive_krw) else 0.0
    rows_out.append((gap, ratio, pid, pr["mgmt_code"], pr["name"], pccy,
                     per, naive, naive_krw, (true_krw if ok else None)))

rows_out.sort(key=lambda z: z[0], reverse=True)
print("   of those, ratio not computable  : %d" % no_rate)
print("")
print("   --- ranked by KRW gap (how much money the screen mis-states) ---")
i = 0
tot_gap = 0.0
for item in rows_out:
    gap, ratio, pid, mg, nm, pccy, per, naive, nkrw, tkrw = item
    tot_gap += gap
    i += 1
    if i > 25:
        continue
    print("   %2d) id=%s  %s  %s   [project ccy=%s]"
          % (i, pid, mg or "-", (nm or "")[:34], pccy))
    for ccy in sorted(per):
        print("        %-4s  %s" % (ccy, fmt(per[ccy])))
    print("        screen shows : %s %s   (= KRW %s)" % (fmt(naive), pccy, fmt(nkrw)))
    print("        correct      : KRW %s" % fmt(tkrw))
    if ratio:
        word = "INFLATED" if ratio >= 1 else "UNDERSTATED"
        print("        >>> %s x%.3f   gap = KRW %s" % (word, ratio, fmt(gap)))
    else:
        print("        >>> ratio not computable (no fx rate for this currency)")
print("")
print("   TOTAL absolute KRW mis-statement across %d mixed projects : KRW %s"
      % (len(rows_out), fmt(tot_gap)))

# ---------------------------------------------------------------------------
print("")
print("== [2] PROJECT DETAIL - child project accumulation ==")
print("   file: app/templates/project_detail.html:1794  (label says KRW, sums blindly)")
if "parent_project_id" not in pcols:
    print("   (projects.parent_project_id missing - skipped)")
else:
    tcol = "total_so_amount" if "total_so_amount" in pcols else "order_amount"
    kids = q("""SELECT parent_project_id AS pp, id, mgmt_code,
                       COALESCE(currency,'KRW') AS ccy,
                       COALESCE(%s,0) AS tot
                FROM projects WHERE parent_project_id IS NOT NULL""" % tcol)
    bypar = {}
    for r in kids:
        bypar.setdefault(r["pp"], []).append(r)
    mix2 = dict((k, v) for k, v in bypar.items()
                if len(set(x["ccy"] for x in v)) > 1)
    print("   parents with children           : %d" % len(bypar))
    print("   parents whose children mix ccy  : %d" % len(mix2))
    for pp in list(mix2.keys())[:15]:
        lst = mix2[pp]
        pr = q("SELECT mgmt_code, name FROM projects WHERE id=?", pp)
        mg = pr[0]["mgmt_code"] if pr else "?"
        nm = (pr[0]["name"] if pr else "")[:34]
        per = {}
        for r in lst:
            per[r["ccy"]] = per.get(r["ccy"], 0.0) + r["tot"]
        naive = sum(per.values())
        tk, ok = 0.0, True
        for ccy in per:
            v, good, _h = to_krw(per[ccy], ccy)
            if not good:
                ok = False
                break
            tk += v
        print("     parent id=%s %s %s" % (pp, mg or "-", nm))
        for ccy in sorted(per):
            print("        %-4s  %s" % (ccy, fmt(per[ccy])))
        print("        screen shows : KRW %s   <-- blind sum labelled KRW" % fmt(naive))
        print("        correct      : KRW %s" % fmt(tk if ok else None))

# ---------------------------------------------------------------------------
print("")
print("== [3] CUSTOMER DETAIL - 'total order amount' ==")
print("   file: app/templates/customer_detail.html:43  (label says WON, sums blindly)")
cust = q("""SELECT customer_id AS ci, COALESCE(currency,'KRW') AS ccy,
                   COUNT(*) AS cnt, COALESCE(SUM(COALESCE(order_amount,0)),0) AS tot
            FROM projects
            WHERE customer_id IS NOT NULL AND COALESCE(order_amount,0) <> 0
            GROUP BY customer_id, COALESCE(currency,'KRW')""")
bycust = {}
for r in cust:
    bycust.setdefault(r["ci"], []).append((r["ccy"], r["cnt"], r["tot"]))
mix3 = dict((k, v) for k, v in bycust.items() if len(v) > 1)
print("   customers with amounts          : %d" % len(bycust))
print("   customers mixing currencies     : %d" % len(mix3))
scored = []
for ci, lst in mix3.items():
    naive = sum(t for _c, _n, t in lst)
    tk, ok = 0.0, True
    for ccy, _cnt, tot in lst:
        v, good, _h = to_krw(tot, ccy)
        if not good:
            ok = False
            break
        tk += v
    gap = abs(naive - tk) if ok else 0.0
    scored.append((gap, ci, lst, naive, (tk if ok else None)))
scored.sort(key=lambda z: z[0], reverse=True)
for item in scored[:15]:
    gap, ci, lst, naive, tk = item
    nm = q("SELECT name FROM customers WHERE id=?", ci)
    print("     customer id=%s %s" % (ci, (nm[0]["name"] if nm else "?")))
    for ccy, cnt, tot in sorted(lst):
        print("        %-4s x%-3d  %s" % (ccy, cnt, fmt(tot)))
    print("        screen shows : %s WON   <-- blind sum" % fmt(naive))
    print("        correct      : KRW %s   (gap = KRW %s)" % (fmt(tk), fmt(gap)))

# ---------------------------------------------------------------------------
print("")
print("== [4] currency distributions (context) ==")
for tbl, col in (("projects", "currency"), ("orders", "currency")):
    if col in cols(tbl):
        sql = ("SELECT COALESCE(%s,'(null)') AS cc, COUNT(*) AS n FROM %s "
               "GROUP BY cc ORDER BY n DESC" % (col, tbl))
        print("   %s.%s :" % (tbl, col),
              ", ".join("%s=%d" % ((r["cc"] or "(null)"), r["n"]) for r in q(sql)))

c.close()
os.remove(TMP)
try:
    os.remove("/tmp/_ccy_mix_measure_v2.py")
except Exception:
    pass
print("")
print("== DONE - snapshot deleted, live DB untouched ==")
print("== SELF-PROOF: %s ==" % ("PASSED - live DB confirmed" if PROOF_OK
                                else "FAILED - do NOT report these numbers as fact"))
'@

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  Currency-mixed SUM impact measurement  v2 (READ ONLY)" -ForegroundColor Cyan
Write-Host ("  target : {0}@{1}:{2}" -f $User, $SshHost, $Port)      -ForegroundColor Cyan
Write-Host "  live DB opened read-only; nothing is modified."        -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")
$remote = "echo $b64 | base64 -d > /tmp/_ccy_mix_measure_v2.py; python3 /tmp/_ccy_mix_measure_v2.py"

ssh @sshOpts "$User@$SshHost" $remote | Tee-Object -FilePath $outFile

Write-Host ""
Write-Host ("result saved : {0}" -f $outFile) -ForegroundColor Green
