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
