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
