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
