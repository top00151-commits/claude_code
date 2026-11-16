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
