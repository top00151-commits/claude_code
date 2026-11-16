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
