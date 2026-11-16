# ============================================================
# Old mail archive - REMOVE DUPLICATES.  2026-11-16.
#
# CEO decision 2026-11-16: "keep the old mail as an archive only; delete the duplicate
# mails so they do not take up space".
# The read-only check of the same day found: 464 archived mails, of which about 459
# are duplicates (3 exact copies inside the archive + 456 fully present in WORKS).
#
#   -Apply         three connections, three SSH passwords:
#                  1) KNKHAIST.MAIL (32203)  read the archive            (read only)
#                  2) KNKHAIST      (32201)  compare with WORKS          (read only)
#                     a mail counts as "in WORKS" only if: same owner, same sender+subject+text,
#                     the WORKS mail is NOT in the trash, and EVERY attachment is in that WORKS
#                     mail with its file really on disk (each file is re-read and re-hashed)
#                  -- you are shown the numbers and must type DELETE --
#                  3) KNKHAIST.MAIL (32203)  backup -> delete -> verify -> compact
#                     a full backup copy is made and VERIFIED first, and is KEPT.
#                     if any check fails, nothing is changed (or the backup is put back).
#   -PurgeBackup   remove the backup copy made by -Apply (this is what finally frees the space)
#   -Restore       put the backup back (undo of -Apply; only possible before -PurgeBackup)
#
# !! Only the OLD archive (/opt/knk_mail/data/mail.db) is ever written. WORKS is only READ.
# !! No mail content reaches the screen or leaves the servers: counts, sizes and short
#    one-way fingerprints only.
# ASCII-ONLY (PowerShell 5.1 mis-reads UTF-8 -> Korean breaks the remote script).
#
# Usage (PowerShell):  ./kmail_old_archive_dedup.ps1 -Apply
# ============================================================
param(
    [switch]$Apply,
    [switch]$PurgeBackup,
    [switch]$Restore,
    [string]$SshHost = "o.knknara.co.kr",
    [string]$User    = "root"
)
$ErrorActionPreference = "Continue"

# NOTE: PowerShell names are case-insensitive - variable names below must differ from the parameters above.
function Get-Remote([int]$Port, [string]$bash, [string]$envName = "", [string]$envValue = "") {
    $sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15")
    $bash = $bash -replace "`r`n", "`n"
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    $cmd = "echo $b64 | base64 -d | bash"
    if ($envName) { $cmd = "export $envName=$envValue; " + $cmd }
    if ($cmd.Length -gt 31000) {
        Write-Host ("ABORT: the command would be too long ({0} characters). Nothing was run. Tell Victor." -f $cmd.Length) -ForegroundColor Red
        return $null
    }
    ssh @sshOpts "$User@$SshHost" $cmd
}

function Pack-Lines([string[]]$lines) {
    $raw = [Text.Encoding]::ASCII.GetBytes(($lines -join "`n"))
    $ms = New-Object System.IO.MemoryStream
    $gz = New-Object System.IO.Compression.GZipStream($ms, [System.IO.Compression.CompressionMode]::Compress)
    $gz.Write($raw, 0, $raw.Length)
    $gz.Close()
    return [Convert]::ToBase64String($ms.ToArray())
}

$guardMail = @'
set +e
[ "$(hostname)" = "KNKHAIST.MAIL" ] || { echo "ABORT: this is not container KNKHAIST.MAIL. Nothing was changed."; exit 10; }
PY=${KNK_DEDUP_PY:-/opt/knk_mail/.venv/bin/python}
[ -x "$PY" ] || { echo "ABORT: $PY not found. Nothing was changed."; exit 11; }
'@
$guardStopped = @'
if pgrep -f '/opt/knk_mail/mail_watchdog\.sh|/opt/knk_mail/.*run\.py' >/dev/null 2>&1; then
  echo "ABORT: the old mail app (or its watchdog) is running - the archive must not be touched while it runs. Nothing was changed."
  exit 12
fi
'@
$guardWorks = @'
set +e
[ "$(hostname)" = "KNKHAIST" ] || { echo "ABORT: this is not container KNKHAIST. Nothing was read."; exit 10; }
PY=${KNK_DEDUP_PY:-/opt/knk_haist/.venv/bin/python}
[ -x "$PY" ] || { echo "ABORT: $PY not found. Nothing was read."; exit 11; }
'@

$py1 = @'
import collections, hashlib, os, sqlite3, sys
from email.utils import parseaddr

# STEP 1 (archive, READ ONLY): fingerprints of every archived mail. No content is printed.
DB = os.environ.get("KNK_DEDUP_DB") or "/opt/knk_mail/data/mail.db"
if not os.path.isfile(DB):
    print("ABORT: database not found: %s" % DB)
    sys.exit(2)
c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
c.row_factory = sqlite3.Row
AC = [r[1] for r in c.execute("PRAGMA table_info(mail_attachments)")]
UC = [r[1] for r in c.execute("PRAGMA table_info(users)")]


def norm_addr(a):
    return (parseaddr(a or "")[1] or "").strip().lower()


def loose(fr, subj, body):
    # the WORKS rule for "the same mail" (app/mail_store.py _dedup_hash, no Message-ID case)
    key = "c:" + norm_addr(fr) + "\x00" + (subj or "").strip() + "\x00" + (body or "").strip()
    return hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()


atts = collections.defaultdict(list)
for r in c.execute("SELECT * FROM mail_attachments ORDER BY id"):
    d = r["data"] if "data" in AC else None
    p = r["path"] if "path" in AC else None
    if d is not None:
        atts[r["mail_id"]].append(hashlib.sha256(bytes(d)).hexdigest()[:12])
    elif p and os.path.isfile(p):
        hh = hashlib.sha256()
        with open(p, "rb") as f:
            for ch in iter(lambda: f.read(1 << 20), b""):
                hh.update(ch)
        atts[r["mail_id"]].append(hh.hexdigest()[:12])
    else:
        atts[r["mail_id"]].append("X")          # a record with no stored content

n = 0
nbytes = {}
for r in c.execute("SELECT id, user_id, direction, from_email, subject, body_text, body_html FROM mail_messages ORDER BY id"):
    n += 1
    print("M|%d|%s|%s|%s|%s" % (r["id"], r["user_id"], (r["direction"] or "in")[:1],
                                loose(r["from_email"], r["subject"], r["body_text"])[:12], ",".join(atts.get(r["id"], []))))
for r in c.execute("SELECT * FROM users ORDER BY id"):
    print("U|%s|%s" % (r["id"], (r["employee_no"] if "employee_no" in UC else "") or ""))
st = os.stat(DB)
print("S|%d|%d|%d" % (st.st_size, int(st.st_mtime), n))
print("   archive: %d mails, database %.1f MB" % (n, st.st_size / 1048576.0))
print("[step1 done]  NOTHING WAS MODIFIED.")
'@
$py2 = @'
import base64, collections, gzip, hashlib, os, sqlite3, sys
from email.utils import parseaddr

# STEP 2 (WORKS, READ ONLY): which archived mails are fully present in WORKS. No content is printed.
#   "fully present" = same owner + same direction + same sender/subject/text, the WORKS mail is NOT in the trash,
#   and every archived attachment exists in that WORKS mail with its file REALLY on disk (re-hashed here).
DB = os.environ.get("KNK_DEDUP_DB") or "/opt/knk_haist/data/knk.db"
raw = os.environ.get("OLD_GZ_B64") or ""
if not raw:
    print("ABORT: no data from step 1. Nothing was read.")
    sys.exit(2)
text = gzip.decompress(base64.b64decode(raw)).decode("ascii")
users, old = {}, []
for line in text.splitlines():
    p = line.split("|")
    if p[0] == "U":
        users[p[1]] = p[2]
    elif p[0] == "M":
        old.append(dict(id=int(p[1]), uid=p[2], d=p[3], lz=p[4], atts=[a for a in p[5].split(",") if a]))
if not os.path.isfile(DB):
    print("ABORT: database not found: %s" % DB)
    sys.exit(2)
c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
c.row_factory = sqlite3.Row
MC = [r[1] for r in c.execute("PRAGMA table_info(mail_messages)")]
AC = [r[1] for r in c.execute("PRAGMA table_info(mail_attachments)")]


def norm_addr(a):
    return (parseaddr(a or "")[1] or "").strip().lower()


def loose(fr, subj, body):
    key = "c:" + norm_addr(fr) + "\x00" + (subj or "").strip() + "\x00" + (body or "").strip()
    return hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()


owner = {}
for uid, emp in users.items():
    r = c.execute("SELECT id FROM users WHERE employee_no=? AND COALESCE(employee_no,'')<>''", (emp,)).fetchone() if emp else None
    owner[uid] = r["id"] if r else None

live = collections.defaultdict(list)      # (uid, d, loose12) -> WORKS mail ids NOT in the trash
trash = set()                             # same key, but only found in the trash
delcol = "COALESCE(is_deleted,0)" if "is_deleted" in MC else "0"
for uid, wid in owner.items():
    if wid is None:
        continue
    for r in c.execute("SELECT id, direction, from_email, subject, body_text, %s AS del FROM mail_messages WHERE user_id=?" % delcol, (wid,)):
        k = (uid, (r["direction"] or "in")[:1], loose(r["from_email"], r["subject"], r["body_text"])[:12])
        if r["del"]:
            trash.add(k)
        else:
            live[k].append(r["id"])

_ok_cache = {}


def content_ok(row):
    """Is the attachment content REALLY there? Returns its sha256 (hex) or None. The file is re-hashed."""
    sha = (row["sha"] or "").strip().lower()
    p = row["path"]
    if p and os.path.isfile(p):
        if p not in _ok_cache:
            hh = hashlib.sha256()
            with open(p, "rb") as f:
                for ch in iter(lambda: f.read(1 << 20), b""):
                    hh.update(ch)
            _ok_cache[p] = hh.hexdigest()
        real = _ok_cache[p]
        if not sha or real == sha:
            return real
        return None                        # the file does not match its own fingerprint -> do not trust it
    if row["has_data"]:
        d = c.execute("SELECT data FROM mail_attachments WHERE id=?", (row["id"],)).fetchone()[0]
        real = hashlib.sha256(bytes(d)).hexdigest()
        if not sha or real == sha:
            return real
    return None


def works_atts(mail_id):
    q = "SELECT id, %s AS sha, %s AS path, %s AS has_data FROM mail_attachments WHERE mail_id=?" % (
        "sha256" if "sha256" in AC else "NULL", "path" if "path" in AC else "NULL",
        "(data IS NOT NULL)" if "data" in AC else "0")
    out = set()
    for r in c.execute(q, (mail_id,)):
        real = content_ok(r)
        if real:
            out.add(real[:12])
    return out


cat = collections.Counter()
for x in old:
    k = (x["uid"], x["d"], x["lz"])
    if owner.get(x["uid"]) is None:
        cat["KEEP owner not found in WORKS"] += 1
        continue
    if "X" in x["atts"]:
        cat["KEEP archive attachment has no stored content (cannot be compared)"] += 1
        continue
    ids = live.get(k)
    if not ids:
        cat["KEEP only in the WORKS trash" if k in trash else "KEEP not in WORKS"] += 1
        continue
    need = set(x["atts"])
    if any(need <= works_atts(i) for i in ids):
        cat["DELETE"] += 1
        print("D|%d|%s" % (x["id"], x["lz"]))
    else:
        cat["KEEP WORKS copy lacks an attachment (or its file is missing/damaged)"] += 1

print("=== [step 2] archive mails against WORKS (strict rules, files re-read) ===")
print("   archive mails checked                       : %d" % len(old))
print("   fully present in WORKS -> can be deleted    : %d" % cat["DELETE"])
for k in sorted(cat):
    if k != "DELETE":
        print("   %-44s: %d" % (k, cat[k]))
print("   WORKS attachment files re-read and verified : %d" % len(_ok_cache))
print("C|%d|%d" % (len(old), cat["DELETE"]))
print("[step2 done]  NOTHING WAS MODIFIED.")
'@
$py3 = @'
import base64, collections, gzip, hashlib, os, shutil, sqlite3, sys, time
from email.utils import parseaddr

# STEP 3 (archive, WRITES): remove the duplicates from the OLD archive.
#   backup first -> verify the backup -> delete in ONE transaction -> verify -> integrity check -> compact.
#   Any failed check = nothing is changed (or the backup is put back). No content is printed.
DB = os.environ.get("KNK_DEDUP_DB") or "/opt/knk_mail/data/mail.db"
raw = os.environ.get("DEL_GZ_B64") or ""
if not raw:
    print("ABORT: no delete list. Nothing was changed.")
    sys.exit(2)
text = gzip.decompress(base64.b64decode(raw)).decode("ascii")
want, snap = {}, None
for line in text.splitlines():
    p = line.split("|")
    if p[0] == "D":
        want[int(p[1])] = p[2]
    elif p[0] == "S":
        snap = (int(p[1]), int(p[2]), int(p[3]))
if snap is None or not os.path.isfile(DB):
    print("ABORT: missing snapshot line or database. Nothing was changed.")
    sys.exit(2)


def norm_addr(a):
    return (parseaddr(a or "")[1] or "").strip().lower()


def loose(fr, subj, body):
    key = "c:" + norm_addr(fr) + "\x00" + (subj or "").strip() + "\x00" + (body or "").strip()
    return hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()


def mb(n):
    return "%.1f MB" % (n / 1048576.0)


def state(path):
    """Fingerprint of every mail in a database file: {id: (loose12, strict, [attachment hashes])} + counts."""
    c = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    c.row_factory = sqlite3.Row
    ac = [r[1] for r in c.execute("PRAGMA table_info(mail_attachments)")]
    atts = collections.defaultdict(list)
    n_att = 0
    orphan = 0
    ids = set(r[0] for r in c.execute("SELECT id FROM mail_messages"))
    for r in c.execute("SELECT * FROM mail_attachments ORDER BY id"):
        n_att += 1
        if r["mail_id"] not in ids:
            orphan += 1
        d = r["data"] if "data" in ac else None
        p = r["path"] if "path" in ac else None
        if d is not None:
            hx = hashlib.sha256(bytes(d)).hexdigest()
        elif p and os.path.isfile(p):
            hh = hashlib.sha256()
            with open(p, "rb") as f:
                for ch in iter(lambda: f.read(1 << 20), b""):
                    hh.update(ch)
            hx = hh.hexdigest()
        else:
            hx = "nodata%d" % r["id"]
        atts[r["mail_id"]].append(hx)
    out = {}
    for r in c.execute("SELECT * FROM mail_messages ORDER BY id"):
        al = sorted(atts.get(r["id"], []))
        attset = hashlib.sha1("|".join(al).encode("ascii")).hexdigest() if al else "-"
        bt, bh = (r["body_text"] or ""), (r["body_html"] or "")
        strict = hashlib.sha1("\x00".join([
            str(r["user_id"]), r["direction"] or "", norm_addr(r["from_email"]), r["to_email"] or "", r["cc"] or "",
            r["subject"] or "", bt, bh, attset]).encode("utf-8", "replace")).hexdigest()
        out[r["id"]] = (loose(r["from_email"], r["subject"], bt)[:12], strict, al)
    c.close()
    return out, n_att, orphan


st = os.stat(DB)
if (st.st_size, int(st.st_mtime)) != snap[:2]:
    print("ABORT: the archive file changed since step 1 (size/time differ). Nothing was changed. Run again.")
    sys.exit(3)
size0 = st.st_size
free = shutil.disk_usage(os.path.dirname(DB)).free
if free < int(size0 * 2.5):
    print("ABORT: not enough free disk space for a safe run (free %s, need %s). Nothing was changed." % (mb(free), mb(size0 * 2.5)))
    sys.exit(3)

print("=== [3-1] reading the archive ===")
before, natt0, orph0 = state(DB)
if len(before) != snap[2]:
    print("ABORT: mail count differs from step 1 (%d vs %d). Nothing was changed." % (len(before), snap[2]))
    sys.exit(3)
bad = [i for i, lz in want.items() if i not in before or before[i][0] != lz]
if bad:
    print("ABORT: %d entries of the delete list do not match the archive. Nothing was changed." % len(bad))
    sys.exit(3)
groups = collections.defaultdict(list)
for i in sorted(before):
    groups[before[i][1]].append(i)
extras = set()
for g in groups.values():
    rest = [i for i in g if i not in want]          # members that are NOT in WORKS
    extras.update(rest[1:])                         # keep the first of them, the others are exact copies
todel = set(want) | extras
keep = sorted(set(before) - todel)
att_del = sum(len(before[i][2]) for i in todel)
print("   mails: %d   attachments: %d   file: %s" % (len(before), natt0, mb(size0)))
print("   to delete: %d mails  (= %d fully present in WORKS + %d exact copies inside the archive), %d attachments" % (
    len(todel), len(want), len(extras), att_del))
print("   to keep  : %d mails" % len(keep))
if not todel:
    print("RESULT: DEDUP - nothing to delete. The archive has no duplicates left. Nothing was changed (no backup made).")
    sys.exit(0)

print("=== [3-2] backup first ===")
BK = "%s.bak.dedup.%s" % (DB, time.strftime("%Y%m%d_%H%M%S"))
src = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
dst = sqlite3.connect(BK)
src.backup(dst)
dst.close()
src.close()
bstate, bnatt, _ = state(BK)
bc = sqlite3.connect("file:%s?mode=ro" % BK, uri=True)
bok = bc.execute("PRAGMA integrity_check").fetchone()[0]
bc.close()
if bok != "ok" or bstate != before or bnatt != natt0:
    print("ABORT: the backup does not match the archive (integrity=%s). Nothing was changed." % bok)
    try:
        os.remove(BK)
    except Exception:
        pass
    sys.exit(4)
print("   backup: %s  (%s)  - verified: every mail and attachment identical, integrity ok" % (BK, mb(os.path.getsize(BK))))

print("=== [3-3] delete (one transaction) ===")
c = sqlite3.connect(DB, isolation_level=None, timeout=30)
try:
    c.execute("BEGIN IMMEDIATE")
    ids = sorted(todel)
    for k in range(0, len(ids), 300):
        ch = ids[k:k + 300]
        q = ",".join("?" * len(ch))
        c.execute("DELETE FROM mail_attachments WHERE mail_id IN (%s)" % q, ch)
        c.execute("DELETE FROM mail_messages WHERE id IN (%s)" % q, ch)
    left = [r[0] for r in c.execute("SELECT id FROM mail_messages ORDER BY id")]
    natt1 = c.execute("SELECT COUNT(*) FROM mail_attachments").fetchone()[0]
    if left != keep or natt1 != natt0 - att_del:
        c.execute("ROLLBACK")
        print("ABORT: the result would not be what was planned (mails %d/%d, attachments %d/%d). Rolled back - nothing was changed."
              % (len(left), len(keep), natt1, natt0 - att_del))
        sys.exit(5)
    c.execute("COMMIT")
except SystemExit:
    raise
except Exception as e:
    try:
        c.execute("ROLLBACK")
    except Exception:
        pass
    print("ABORT: delete failed (%s). Rolled back - nothing was changed." % type(e).__name__)
    sys.exit(5)
print("   deleted %d mails and %d attachments" % (len(todel), att_del))

print("=== [3-4] verify, then compact ===")
ok1 = c.execute("PRAGMA integrity_check").fetchone()[0]
vac = "done"
try:
    c.execute("VACUUM")
except Exception as e:
    vac = "skipped (%s) - the archive is correct, only not compacted" % type(e).__name__
ok2 = c.execute("PRAGMA integrity_check").fetchone()[0]
c.close()
after, natt2, orph2 = state(DB)
same = (sorted(after) == keep and all(after[i] == before[i] for i in keep) and natt2 == natt0 - att_del and orph2 <= orph0)
dups_left = len(after) - len(set(v[1] for v in after.values()))
if ok1 != "ok" or ok2 != "ok" or not same:
    shutil.copy2(BK, DB)
    print("!! verification FAILED (integrity %s/%s, kept-mails-identical=%s) -> the backup was put back. The archive is as it was." % (ok1, ok2, same))
    sys.exit(6)
size1 = os.path.getsize(DB)
print("   integrity: ok   compact: %s" % vac)
print("   kept mails are identical to before (text and every attachment re-read): yes   exact copies left: %d" % dups_left)
print("   archive : %d -> %d mails,  %d -> %d attachments,  %s -> %s" % (len(before), len(after), natt0, natt2, mb(size0), mb(size1)))
print("   backup kept: %s (%s)" % (BK, mb(os.path.getsize(BK))))
print("R|%d|%d|%d|%d|%.1f|%.1f" % (len(before), len(after), len(want), len(extras), size0 / 1048576.0, size1 / 1048576.0))
print("RESULT: DEDUP OK - the duplicates are removed. The backup is still there (remove it later with -PurgeBackup).")
'@
$pyPurge = @'
import glob, os, sqlite3, sys

# Remove the safety backups made by the dedup step - only if the archive itself is healthy.
DB = os.environ.get("KNK_DEDUP_DB") or "/opt/knk_mail/data/mail.db"


def mb(n):
    return "%.1f MB" % (n / 1048576.0)


baks = sorted(glob.glob(DB + ".bak.dedup.*"))
if not baks:
    print("   no backup file found - nothing to remove.")
    print("RESULT: PURGE - nothing to do.")
    sys.exit(0)
if not os.path.isfile(DB):
    print("ABORT: the archive database is missing - the backups are NOT removed.")
    sys.exit(3)
c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
ok = c.execute("PRAGMA integrity_check").fetchone()[0]
n = c.execute("SELECT COUNT(*) FROM mail_messages").fetchone()[0]
na = c.execute("SELECT COUNT(*) FROM mail_attachments").fetchone()[0]
c.close()
if ok != "ok":
    print("ABORT: the archive does not pass the integrity check (%s) - the backups are NOT removed." % ok[:60])
    sys.exit(3)
print("   archive is healthy: %d mails, %d attachments, %s" % (n, na, mb(os.path.getsize(DB))))
freed = 0
for b in baks:
    s = os.path.getsize(b)
    os.remove(b)
    freed += s
    print("   removed backup: %s (%s)" % (b, mb(s)))
print("RESULT: PURGE OK - %d backup file(s) removed, %s freed." % (len(baks), mb(freed)))
'@
$pyRestore = @'
import glob, os, shutil, sqlite3, sys

# Put the newest safety backup back as the archive (undo of the dedup step).
DB = os.environ.get("KNK_DEDUP_DB") or "/opt/knk_mail/data/mail.db"


def mb(n):
    return "%.1f MB" % (n / 1048576.0)


def facts(path):
    c = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    ok = c.execute("PRAGMA integrity_check").fetchone()[0]
    n = c.execute("SELECT COUNT(*) FROM mail_messages").fetchone()[0]
    na = c.execute("SELECT COUNT(*) FROM mail_attachments").fetchone()[0]
    c.close()
    return ok, n, na


baks = sorted(glob.glob(DB + ".bak.dedup.*"))
if not baks:
    print("ABORT: no backup file found (already purged?). Nothing was changed.")
    sys.exit(3)
# several backups can exist if -Apply was run more than once: undo means "back to the ORIGINAL",
# so take the backup that holds the MOST mails (the oldest one on a tie) - never simply the newest.
best = None
for b in baks:
    try:
        f = facts(b)
    except Exception:
        continue
    print("   backup found: %d mails, %d attachments, integrity %s  (%s)" % (f[1], f[2], f[0], os.path.basename(b)))
    if f[0] == "ok" and (best is None or f[1] > best[1][1]):
        best = (b, f)
if best is None:
    print("ABORT: no backup passes the integrity check. Nothing was changed.")
    sys.exit(3)
bk, (ok, n, na) = best
if os.path.isfile(DB):
    ok0, n0, na0 = facts(DB)
    print("   archive now : %d mails, %d attachments, %s" % (n0, na0, mb(os.path.getsize(DB))))
print("   backup      : %d mails, %d attachments, %s  (%s)" % (n, na, mb(os.path.getsize(bk)), bk))
tmp = DB + ".restore_tmp"
shutil.copy2(bk, tmp)
os.replace(tmp, DB)
for ext in ("-wal", "-shm", "-journal"):
    try:
        os.remove(DB + ext)
    except OSError:
        pass
ok2, n2, na2 = facts(DB)
if ok2 != "ok" or (n2, na2) != (n, na):
    print("!! restore verification failed (integrity %s, %d mails). Paste this output to Victor NOW." % (ok2, n2))
    sys.exit(4)
print("   archive restored: %d mails, %d attachments, %s   (the backup file is kept)" % (n2, na2, mb(os.path.getsize(DB))))
print("RESULT: RESTORE OK - the archive is back to what it was before the dedup.")
'@

function Wrap-Py([string]$guard, [string]$pyText) {
    return $guard + "`n" + '"$PY" - <<' + "'PYEOF'`n" + $pyText + "`nPYEOF`n"
}

$picked = @(@($Apply.IsPresent, $PurgeBackup.IsPresent, $Restore.IsPresent) | Where-Object { $_ }).Count
if ($picked -ne 1) {
    Write-Host "Choose exactly ONE of:  -Apply   -PurgeBackup   -Restore" -ForegroundColor Yellow
    Write-Host "  -Apply        remove the duplicates from the OLD archive (backup first; 3 SSH passwords)"
    Write-Host "  -PurgeBackup  remove the backup made by -Apply (frees the space; cannot be undone)"
    Write-Host "  -Restore      put the backup back (undo of -Apply)"
    return
}

Write-Host "==================================================" -ForegroundColor Cyan
if ($Apply) {
    Write-Host "  Old mail archive - remove duplicates" -ForegroundColor Cyan
    Write-Host "  read archive -> compare with WORKS -> (you confirm) -> backup, delete, verify" -ForegroundColor Yellow
    Write-Host "=================================================="
    Write-Host ""
    Write-Host ">>> (1/3) KNKHAIST.MAIL - ssh 32203 - read the archive   (type the SSH password)" -ForegroundColor Green
    Write-Host "    nothing is shown until it ends (about 220 MB) - please wait"
    $out1 = @(Get-Remote 32203 (Wrap-Py $guardMail $py1) | ForEach-Object { "$_" })
    $out1 | Where-Object { $_ -notmatch '^(M|U|S)\|' } | ForEach-Object { Write-Host $_ }
    $pack1 = @($out1 | Where-Object { $_ -match '^(M|U)\|' })
    $snapLine = @($out1 | Where-Object { $_ -match '^S\|' })
    if (@($out1 | Where-Object { $_ -match '^\[step1 done\]' }).Count -eq 0 -or $pack1.Count -eq 0 -or $snapLine.Count -ne 1) {
        Write-Host "ABORT: step 1 did not finish. Nothing was changed. Paste this output to Victor." -ForegroundColor Red
        return
    }
    Write-Host ""
    Write-Host ">>> (2/3) KNKHAIST - ssh 32201 - compare with WORKS (read only)   (type the SSH password)" -ForegroundColor Green
    Write-Host "    the WORKS attachment files are re-read one by one - this can take a little while"
    $out2 = @(Get-Remote 32201 (Wrap-Py $guardWorks $py2) "OLD_GZ_B64" (Pack-Lines $pack1) | ForEach-Object { "$_" })
    $out2 | Where-Object { $_ -notmatch '^(D|C)\|' } | ForEach-Object { Write-Host $_ }
    $delLines = @($out2 | Where-Object { $_ -match '^D\|' })
    $countLine = @($out2 | Where-Object { $_ -match '^C\|' })
    if (@($out2 | Where-Object { $_ -match '^\[step2 done\]' }).Count -eq 0 -or $countLine.Count -ne 1) {
        Write-Host "ABORT: step 2 did not finish. Nothing was changed. Paste this output to Victor." -ForegroundColor Red
        return
    }
    $nums = $countLine[0].Split("|")
    if ([int]$nums[2] -ne $delLines.Count) {
        Write-Host "ABORT: the delete list is incomplete. Nothing was changed. Paste this output to Victor." -ForegroundColor Red
        return
    }
    Write-Host ""
    Write-Host "--------------------------------------------------" -ForegroundColor Yellow
    Write-Host ("  OLD archive: {0} mails.   Fully present in WORKS: {1} mails." -f $nums[1], $nums[2]) -ForegroundColor Yellow
    Write-Host "  Step 3 will PERMANENTLY remove from the OLD archive:" -ForegroundColor Yellow
    Write-Host ("    - those {0} mails (WORKS keeps its own copy - WORKS is not touched)" -f $nums[2]) -ForegroundColor Yellow
    Write-Host "    - exact copies inside the archive (one of each is kept)" -ForegroundColor Yellow
    Write-Host "  A full backup is made and verified first, and is kept until you run -PurgeBackup." -ForegroundColor Yellow
    Write-Host "--------------------------------------------------" -ForegroundColor Yellow
    $answer = Read-Host "Type DELETE (capital letters) to continue, anything else to stop"
    if ("$answer".Trim() -cne "DELETE") {
        Write-Host "Stopped. Nothing was changed." -ForegroundColor Green
        return
    }
    Write-Host ""
    Write-Host ">>> (3/3) KNKHAIST.MAIL - ssh 32203 - backup, delete, verify   (type the SSH password)" -ForegroundColor Green
    Get-Remote 32203 (Wrap-Py ($guardMail + "`n" + $guardStopped) $py3) "DEL_GZ_B64" (Pack-Lines ($delLines + $snapLine))
} elseif ($PurgeBackup) {
    Write-Host "  Old mail archive - remove the backup copy" -ForegroundColor Cyan
    Write-Host "=================================================="
    Write-Host "  This removes the backup made by -Apply. After this, -Restore is no longer possible." -ForegroundColor Yellow
    $answer = Read-Host "Type PURGE (capital letters) to continue, anything else to stop"
    if ("$answer".Trim() -cne "PURGE") {
        Write-Host "Stopped. Nothing was changed." -ForegroundColor Green
        return
    }
    Write-Host "(type the SSH password)" -ForegroundColor Green
    Get-Remote 32203 (Wrap-Py $guardMail $pyPurge)
} else {
    Write-Host "  Old mail archive - put the backup back (undo)" -ForegroundColor Cyan
    Write-Host "=================================================="
    $answer = Read-Host "Type RESTORE (capital letters) to continue, anything else to stop"
    if ("$answer".Trim() -cne "RESTORE") {
        Write-Host "Stopped. Nothing was changed." -ForegroundColor Green
        return
    }
    Write-Host "(type the SSH password)" -ForegroundColor Green
    Get-Remote 32203 (Wrap-Py ($guardMail + "`n" + $guardStopped) $pyRestore)
}
Write-Host ""
Write-Host "[finished] Please paste the whole output to Victor." -ForegroundColor Green
