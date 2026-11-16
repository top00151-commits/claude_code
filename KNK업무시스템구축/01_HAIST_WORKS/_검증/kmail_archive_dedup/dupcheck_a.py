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
