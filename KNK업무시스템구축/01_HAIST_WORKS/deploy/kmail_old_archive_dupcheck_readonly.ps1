# ============================================================
# Old mail archive - DUPLICATE CHECK.  READ ONLY.  2026-11-16.
#
# WHY: CEO decision 2026-11-16: "keep the old mail as an archive only; delete the
#      duplicate mails so they do not take up space". Before anything is deleted
#      we COUNT, with the real data:
#        (1) container KNKHAIST.MAIL (ssh 32203) - the old archive /opt/knk_mail/data/mail.db
#            how many mails are exact copies of another mail in the archive
#        (2) container KNKHAIST (ssh 32201) - the WORKS mailbox
#            how many archive mails are ALSO in WORKS (so the archive copy is redundant)
#
# !! READ ONLY !!  Both databases are opened read-only. Nothing is written, deleted,
#    restarted or stopped. No temporary file is created on the servers.
# !! NO MAIL CONTENT leaves the server or reaches the screen: no subject, no address,
#    no body, no file name. Only counts, sizes, dates and short one-way fingerprints
#    (8 hex digits of a hash) are handed from step 1 to step 2, packed, in memory.
# ASCII-ONLY (PowerShell 5.1 mis-reads UTF-8 -> Korean breaks the remote script).
#
# Usage (PowerShell):  ./kmail_old_archive_dupcheck_readonly.ps1
#   It connects twice (32203, then 32201). Type the SSH password each time.
#   Step 1 prints nothing until it ends (it reads about 220 MB) - wait a little.
#   Then paste the whole output back to Victor.
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [string]$User    = "root"
)
$ErrorActionPreference = "Continue"

# NOTE: PowerShell names are case-insensitive - keep these names different from the parameters above.
function Get-Remote([int]$Port, [string]$bash, [string]$packed = "") {
    $sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15")
    # the remote side is bash: it must get LF only
    $bash = $bash -replace "`r`n", "`n"
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    $cmd = "echo $b64 | base64 -d | bash"
    if ($packed) { $cmd = "export OLD_GZ_B64=$packed; " + $cmd }
    if ($cmd.Length -gt 31000) {
        Write-Host ("ABORT: the command would be too long ({0} characters). Nothing was run. Tell Victor." -f $cmd.Length) -ForegroundColor Red
        return $null
    }
    ssh @sshOpts "$User@$SshHost" $cmd
}

$bodyA = @'
set +e
[ "$(hostname)" = "KNKHAIST.MAIL" ] || { echo "ABORT: this is not container KNKHAIST.MAIL. Nothing was read."; exit 10; }
PY=${KNK_DUPCHECK_PY:-/opt/knk_mail/.venv/bin/python}
[ -x "$PY" ] || { echo "ABORT: $PY not found. Nothing was read."; exit 11; }
"$PY" - <<'PYEOF'
import collections, hashlib, os, sqlite3, sys
from email.utils import parseaddr

# READ ONLY. Prints COUNTS / SIZES / DATES only - never a subject, an address or a body.
DB = os.environ.get("KNK_DUPCHECK_DB") or "/opt/knk_mail/data/mail.db"
if not os.path.isfile(DB):
    print("ABORT: database not found: %s" % DB)
    sys.exit(2)
c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
c.row_factory = sqlite3.Row


def cols(t):
    return [r[1] for r in c.execute("PRAGMA table_info(%s)" % t)]


MC, AC = cols("mail_messages"), cols("mail_attachments")


def norm_addr(a):
    return (parseaddr(a or "")[1] or "").strip().lower()


def loose(fr, subj, body):
    # EXACTLY the WORKS rule for "the same mail" when there is no Message-ID (app/mail_store.py _dedup_hash)
    key = "c:" + norm_addr(fr) + "\x00" + (subj or "").strip() + "\x00" + (body or "").strip()
    return hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()


def weak(fr, subj):
    return hashlib.sha1((norm_addr(fr) + "\x00" + (subj or "").strip()).encode("utf-8", "replace")).hexdigest()


def mb(n):
    return "%.1f MB" % (n / 1048576.0)


# ---- attachments: content fingerprint of every stored file
atts = collections.defaultdict(list)
att_total = att_bytes = att_nodata = 0
blob_seen = {}
for r in c.execute("SELECT * FROM mail_attachments ORDER BY id"):
    att_total += 1
    d = r["data"] if "data" in AC else None
    p = r["path"] if "path" in AC else None
    if d is not None:
        hx, n = hashlib.sha256(bytes(d)).hexdigest(), len(d)
    elif p and os.path.isfile(p):
        hh, n = hashlib.sha256(), 0
        with open(p, "rb") as f:
            for ch in iter(lambda: f.read(1 << 20), b""):
                hh.update(ch)
                n += len(ch)
        hx = hh.hexdigest()
    else:
        att_nodata += 1
        hx, n = "nodata%d" % r["id"], 0
    atts[r["mail_id"]].append((hx, n))
    att_bytes += n
    blob_seen.setdefault(hx, n)

# ---- mails
rows = []
for r in c.execute("SELECT * FROM mail_messages ORDER BY id"):
    al = sorted(atts.get(r["id"], []))
    attset = hashlib.sha1("|".join(h for h, n in al).encode("ascii")).hexdigest() if al else "-"
    bt, bh = (r["body_text"] or ""), (r["body_html"] or "")
    strict = hashlib.sha1("\x00".join([
        str(r["user_id"]), r["direction"] or "", norm_addr(r["from_email"]), r["to_email"] or "", r["cc"] or "",
        r["subject"] or "", bt, bh, attset]).encode("utf-8", "replace")).hexdigest()
    rows.append(dict(
        id=r["id"], uid=r["user_id"], d=(r["direction"] or "in"), deleted=int(r["is_deleted"] or 0),
        lz=loose(r["from_email"], r["subject"], bt), wk=weak(r["from_email"], r["subject"]),
        attset=attset, strict=strict, al=al, rcv=(r["received_at"] or "")[:10],
        nbytes=len(bt.encode("utf-8", "replace")) + len(bh.encode("utf-8", "replace")) + sum(n for h, n in al)))

total_bytes = sum(x["nbytes"] for x in rows)
print("=== [A1] the old mail archive ===")
print("   database file      : %s" % mb(os.path.getsize(DB)))
try:
    ps = c.execute("PRAGMA page_size").fetchone()[0]
    fl = c.execute("PRAGMA freelist_count").fetchone()[0]
    print("   already-free space : %s (inside the file)" % mb(ps * fl))
except Exception:
    pass
print("   mails              : %d   (text + attachments = %s)" % (len(rows), mb(total_bytes)))
dc = collections.Counter(x["d"] for x in rows)
print("   by direction       : %s" % ", ".join("%s=%d" % kv for kv in sorted(dc.items())))
print("   in the trash       : %d" % sum(x["deleted"] for x in rows))
ds = sorted(x["rcv"] for x in rows if x["rcv"])
print("   received dates     : %s ~ %s" % ((ds[0], ds[-1]) if ds else ("-", "-")))
print("   attachments        : %d files, %s  (no stored content: %d)" % (att_total, mb(att_bytes), att_nodata))
print("   same file stored more than once: %d distinct of %d  -> %s could be shared" % (
    len(blob_seen), att_total, mb(att_bytes - sum(blob_seen.values()))))
print("   columns: mail_messages has message_id=%s dedup_hash=%s | mail_attachments has data=%s sha256=%s path=%s" % (
    "message_id" in MC, "dedup_hash" in MC, "data" in AC, "sha256" in AC, "path" in AC))

print("")
print("=== [A2] duplicates INSIDE the archive ===")
by_strict = collections.defaultdict(list)
for x in rows:
    by_strict[x["strict"]].append(x)
dup_rows = [x for g in by_strict.values() if len(g) > 1 for x in g[1:]]
for x in dup_rows:
    x["dup"] = True
print("   EXACT copies (same sender, receiver, subject, text, html AND the same attachments):")
print("      groups: %d   extra copies: %d mails   space: %s" % (
    sum(1 for g in by_strict.values() if len(g) > 1), len(dup_rows), mb(sum(x["nbytes"] for x in dup_rows))))
by_loose = collections.defaultdict(list)
for x in rows:
    by_loose[(x["uid"], x["d"], x["lz"])].append(x)
loose_extra = [x for g in by_loose.values() if len(g) > 1 for x in g[1:]]
risky = sum(1 for g in by_loose.values() if len(g) > 1 and len(set(y["attset"] for y in g)) > 1)
print("   by the WORKS rule only (same sender + subject + text, attachments NOT compared):")
print("      extra copies: %d mails   space: %s" % (len(loose_extra), mb(sum(x["nbytes"] for x in loose_extra))))
print("      !! groups where the 'copies' carry DIFFERENT attachments: %d  (these are NOT safe to merge)" % risky)

print("")
print("=== [A3] owners ===")
ucols = cols("users")
for r in c.execute("SELECT * FROM users ORDER BY id"):
    n = sum(1 for x in rows if x["uid"] == r["id"])
    emp = (r["employee_no"] if "employee_no" in ucols else "") or ""
    print("   user id %s : employee_no present=%s   mails=%d" % (r["id"], bool(emp), n))
    print("U|%s|%s" % (r["id"], emp))
orphan = sum(1 for x in rows if x["uid"] is None)
if orphan:
    print("   mails with no owner: %d" % orphan)

for x in rows:
    print("H|%s|%s|%d|%s|%s|%d|%s" % (
        x["lz"][:8], x["wk"][:6], x["nbytes"], x["d"][:1], x["uid"], 1 if x.get("dup") else 0,
        ",".join(h[:8] for h, n in x["al"])))
print("[done 32203]  NOTHING WAS MODIFIED.")
PYEOF
'@

$bodyB = @'
set +e
[ "$(hostname)" = "KNKHAIST" ] || { echo "ABORT: this is not container KNKHAIST. Nothing was read."; exit 10; }
PY=${KNK_DUPCHECK_PY:-/opt/knk_haist/.venv/bin/python}
[ -x "$PY" ] || { echo "ABORT: $PY not found. Nothing was read."; exit 11; }
"$PY" - <<'PYEOF'
import base64, collections, gzip, hashlib, os, sqlite3, sys
from email.utils import parseaddr

# READ ONLY. Prints COUNTS / SIZES / DATES only - never a subject, an address or a body.
DB = os.environ.get("KNK_DUPCHECK_DB") or "/opt/knk_haist/data/knk.db"
raw = os.environ.get("OLD_GZ_B64") or ""
if not raw:
    print("ABORT: no data from the archive step. Nothing was read.")
    sys.exit(2)
text = gzip.decompress(base64.b64decode(raw)).decode("ascii")
users, old = {}, []
for line in text.splitlines():
    p = line.split("|")
    if p[0] == "U":
        users[p[1]] = p[2]
    elif p[0] == "H":
        old.append(dict(lz=p[1], wk=p[2], nbytes=int(p[3]), d=p[4], uid=p[5], dup=(p[6] == "1"),
                        atts=[a for a in p[7].split(",") if a]))
if not os.path.isfile(DB):
    print("ABORT: database not found: %s" % DB)
    sys.exit(2)
c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
c.row_factory = sqlite3.Row


def cols(t):
    return [r[1] for r in c.execute("PRAGMA table_info(%s)" % t)]


AC = cols("mail_attachments")


def norm_addr(a):
    return (parseaddr(a or "")[1] or "").strip().lower()


def loose(fr, subj, body):
    key = "c:" + norm_addr(fr) + "\x00" + (subj or "").strip() + "\x00" + (body or "").strip()
    return hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()


def weak(fr, subj):
    return hashlib.sha1((norm_addr(fr) + "\x00" + (subj or "").strip()).encode("utf-8", "replace")).hexdigest()


def mb(n):
    return "%.1f MB" % (n / 1048576.0)


print("=== [B1] WORKS mailbox of the same owner(s) ===")
owner = {}
for uid, emp in sorted(users.items()):
    r = c.execute("SELECT id FROM users WHERE employee_no=? AND COALESCE(employee_no,'')<>''", (emp,)).fetchone() if emp else None
    owner[uid] = r["id"] if r else None
    print("   archive user %s -> found in WORKS by employee number: %s" % (uid, "yes" if r else "NO"))

works_loose = collections.defaultdict(list)     # (uid, direction, loose8) -> [works mail ids]
works_weak = set()
stats = {}
for uid, wid in owner.items():
    if wid is None:
        continue
    n = 0
    dates = []
    for r in c.execute("SELECT id, direction, from_email, subject, body_text, received_at FROM mail_messages WHERE user_id=?", (wid,)):
        n += 1
        d = (r["direction"] or "in")[:1]
        works_loose[(uid, d, loose(r["from_email"], r["subject"], r["body_text"])[:8])].append(r["id"])
        works_weak.add((uid, d, weak(r["from_email"], r["subject"])[:6]))
        if r["received_at"]:
            dates.append(r["received_at"][:10])
    dates.sort()
    stats[uid] = (n, dates[0] if dates else "-", dates[-1] if dates else "-")
    print("   archive user %s : WORKS has %d mails, received %s ~ %s" % (uid, n, stats[uid][1], stats[uid][2]))


def att_hashes(mail_ids):
    out = set()
    unknown = 0
    for i in range(0, len(mail_ids), 400):
        chunk = mail_ids[i:i + 400]
        q = "SELECT id, %s AS sha, %s AS has_data FROM mail_attachments WHERE mail_id IN (%s)" % (
            "sha256" if "sha256" in AC else "NULL", "(data IS NOT NULL)" if "data" in AC else "0", ",".join("?" * len(chunk)))
        for r in c.execute(q, chunk):
            if r["sha"]:
                out.add(r["sha"][:8])
            elif r["has_data"]:
                d = c.execute("SELECT data FROM mail_attachments WHERE id=?", (r["id"],)).fetchone()[0]
                out.add(hashlib.sha256(bytes(d)).hexdigest()[:8])
            else:
                unknown += 1
    return out, unknown


print("")
print("=== [B2] archive mails that are ALSO in WORKS ===")
cat = collections.Counter()
catb = collections.Counter()
for x in old:
    if x["dup"]:
        cat["DUP_INSIDE"] += 1
        catb["DUP_INSIDE"] += x["nbytes"]
        continue
    ids = works_loose.get((x["uid"], x["d"], x["lz"]))
    if ids:
        have, _unk = att_hashes(ids)
        k = "FULL" if all(a in have for a in x["atts"]) else "BODY_ONLY"
    elif (x["uid"], x["d"], x["wk"]) in works_weak:
        k = "WEAK"
    else:
        k = "NONE"
    cat[k] += 1
    catb[k] += x["nbytes"]
tot = len(old)
totb = sum(x["nbytes"] for x in old)
lab = [
    ("DUP_INSIDE", "extra copies inside the archive (exact, incl. attachments)"),
    ("FULL", "also in WORKS - same sender+subject+text, and WORKS has every attachment"),
    ("BODY_ONLY", "also in WORKS by text, but WORKS lacks some attachment -> KEEP"),
    ("WEAK", "same sender+subject exists in WORKS but the text differs -> KEEP"),
    ("NONE", "only in the archive -> KEEP"),
]
for k, name in lab:
    print("   %-10s %4d mails  %9s   %s" % (k, cat[k], mb(catb[k]), name))
print("   %-10s %4d mails  %9s" % ("TOTAL", tot, mb(totb)))
print("")
rm = cat["DUP_INSIDE"] + cat["FULL"]
rmb = catb["DUP_INSIDE"] + catb["FULL"]
print("=== [B3] if the duplicates (DUP_INSIDE + FULL) were removed from the archive ===")
print("   would remove : %d mails, about %s" % (rm, mb(rmb)))
print("   would remain : %d mails, about %s" % (tot - rm, mb(totb - rmb)))
print("SUMMARY|total=%d|dup_inside=%d|full=%d|body_only=%d|weak=%d|none=%d|remove_mb=%.1f|remain_mb=%.1f" % (
    tot, cat["DUP_INSIDE"], cat["FULL"], cat["BODY_ONLY"], cat["WEAK"], cat["NONE"], rmb / 1048576.0, (totb - rmb) / 1048576.0))
print("[done 32201]  NOTHING WAS MODIFIED.")
PYEOF
'@

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Old mail archive - duplicate check - READ ONLY" -ForegroundColor Cyan
Write-Host "  counts and sizes only / no mail content / nothing is changed" -ForegroundColor Yellow
Write-Host "=================================================="
Write-Host ""
Write-Host ">>> (1/2) KNKHAIST.MAIL - ssh port 32203   (type the SSH password)" -ForegroundColor Green
Write-Host "    reading the old archive ... nothing is shown until it ends (about 220 MB) - please wait"
$outA = @(Get-Remote 32203 $bodyA | ForEach-Object { "$_" })
$packLines = @($outA | Where-Object { $_ -match '^(H|U)\|' })
$outA | Where-Object { $_ -notmatch '^(H|U)\|' } | ForEach-Object { Write-Host $_ }
$doneA = @($outA | Where-Object { $_ -match '^\[done 32203\]' }).Count
if ($doneA -eq 0 -or $packLines.Count -eq 0) {
    Write-Host ""
    Write-Host "ABORT: step 1 did not finish (see above). Step 2 was NOT run. Paste this output to Victor." -ForegroundColor Red
    return
}

# pack the fingerprints (ASCII text -> gzip -> base64), all in memory
$raw = [Text.Encoding]::ASCII.GetBytes(($packLines -join "`n"))
$ms = New-Object System.IO.MemoryStream
$gz = New-Object System.IO.Compression.GZipStream($ms, [System.IO.Compression.CompressionMode]::Compress)
$gz.Write($raw, 0, $raw.Length)
$gz.Close()
$packed = [Convert]::ToBase64String($ms.ToArray())
Write-Host ""
Write-Host ("    handing over {0} fingerprint lines ({1} characters packed) - no mail content" -f $packLines.Count, $packed.Length)
Write-Host ""
Write-Host ">>> (2/2) KNKHAIST - ssh port 32201   (type the SSH password)" -ForegroundColor Green
Get-Remote 32201 $bodyB $packed

Write-Host ""
Write-Host "[check finished] Nothing was changed. Please paste the whole output to Victor." -ForegroundColor Green
