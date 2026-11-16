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
