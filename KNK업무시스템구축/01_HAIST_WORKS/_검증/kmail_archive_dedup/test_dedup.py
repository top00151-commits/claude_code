# -*- coding: utf-8 -*-
"""옛 메일 보관함 중복 삭제(dedup_1·2·3 · purge · restore) — 가짜 DB·가짜 첨부 파일로 전 과정 시험.
서버·실제 메일 무접촉. 전부 임시 폴더 안."""
import base64, glob, gzip, hashlib, os, shutil, sqlite3, subprocess, sys, tempfile, time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD_ONLY = len(sys.argv) > 2 and sys.argv[1] == "--build-only"
T = sys.argv[2] if BUILD_ONLY else tempfile.mkdtemp(prefix="knk_dedup_")
os.makedirs(T, exist_ok=True)
OLD, WORKS, ATT = os.path.join(T, "old.db"), os.path.join(T, "works.db"), os.path.join(T, "mail_att")
for _p in glob.glob(OLD + "*") + [WORKS]:
    if os.path.exists(_p):
        os.remove(_p)
shutil.rmtree(ATT, ignore_errors=True)
PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS]", name)
    else:
        FAIL += 1
        print("  [FAIL]", name, extra)


def blob(ch, n):
    return (ch * 4).encode() * n


A1, A2, A3, A4 = blob("A", 60000), blob("B", 20000), blob("C", 20000), blob("D", 20000)
A5, A6, A7 = blob("E", 30000), blob("F", 30000), blob("G", 40000)

o = sqlite3.connect(OLD)
o.executescript("""
CREATE TABLE users (id INTEGER PRIMARY KEY, employee_no TEXT, name TEXT, email TEXT);
CREATE TABLE mail_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, direction TEXT DEFAULT 'in',
  from_email TEXT, from_name TEXT, to_email TEXT, cc TEXT, bcc TEXT, subject TEXT, body_text TEXT, body_html TEXT,
  category TEXT, lang TEXT, summary TEXT, is_read INTEGER DEFAULT 0, is_starred INTEGER DEFAULT 0, is_deleted INTEGER DEFAULT 0,
  raw_size INTEGER DEFAULT 0, received_at TEXT, read_at TEXT, deleted_at TEXT, created_at TEXT);
CREATE TABLE mail_attachments (id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INTEGER, filename TEXT, mime TEXT, size INTEGER,
  path TEXT, content_id TEXT, is_inline INTEGER DEFAULT 0, data BLOB, created_at TEXT);
CREATE TABLE mail_fetch_seen (account_id INTEGER, uidl TEXT, PRIMARY KEY(account_id, uidl));
""")
o.execute("INSERT INTO users(id, employee_no, name, email) VALUES(1, '5', 'fake', 'fake@example.com')")
o.execute("INSERT INTO users(id, employee_no, name, email) VALUES(2, '67', 'fake2', 'fake2@example.com')")
o.execute("INSERT INTO mail_fetch_seen VALUES(1, 'uidl-1')")


def om(fr, subj, body, atts=(), d="in"):
    cur = o.execute("INSERT INTO mail_messages(user_id,direction,from_email,to_email,cc,subject,body_text,body_html,received_at) "
                    "VALUES(1,?,?,?,?,?,?,?,?)", (d, fr, "me@example.com", "", subj, body, "<p>%s</p>" % body, "2026-06-20 10:00:00"))
    for i, b in enumerate(atts):
        o.execute("INSERT INTO mail_attachments(mail_id,filename,size,data) VALUES(?,?,?,?)",
                  (cur.lastrowid, "f%d.bin" % i, (len(b) if b is not None else 777), b))


om("Kim <a@x.example>", "S1", "B1")                 # 1  WORKS 에 있음 → 삭제
om("Kim <a@x.example>", "S1", "B1")                 # 2  1의 완전 사본(역시 WORKS 에 있음) → 삭제
om("a@x.example", "S2", "B2", [A1])                 # 3  WORKS 에 첨부 파일까지 온전 → 삭제
om("b@y.example", "S3", "B3", [A2])                 # 4  WORKS 사본에 첨부 없음 → 남김
om("b@y.example", "S4", "B4")                       # 5  WORKS 에는 휴지통에만 → 남김
om("c@z.example", "S5", "B5", [A3])                 # 6  WORKS 에 첨부 줄은 있는데 **파일이 없음** → 남김
om("c@z.example", "S6", "B6", [A4])                 # 7  WORKS 첨부 파일이 **깨져 있음**(지문 불일치) → 남김
om("c@z.example", "S7", "B7", [None])               # 8  보관함 첨부에 내용이 없음(견줄 수 없음) → 남김
om("d@w.example", "S8", "B8")                       # 9  WORKS 에 없음 → 남김
om("d@w.example", "S8", "B8")                       # 10 9의 완전 사본 → 삭제(보관함 안 사본)
om("d@w.example", "S8", "B8")                       # 11 9의 완전 사본 → 삭제
om("e@v.example", "S9", "B9", [A5])                 # 12 WORKS 에 이 첨부로 있음 → 삭제
om("e@v.example", "S9", "B9", [A6])                 # 13 글은 12와 같지만 첨부가 다름 · WORKS 에 이 첨부는 없음 → 남김
om("f@u.example", "S10", "B10")                     # 14 WORKS 에는 **다른 사람** 것으로만 → 남김
om("me@example.com", "S11", "B11", d="out")         # 15 WORKS 에는 방향이 다른(in) 것만 → 남김
om("g@t.example", "S12", "B12", [A7])               # 16 WORKS 첨부가 파일이 아니라 DB 안(BLOB)에 있음 → 삭제
o.commit()
o.close()

w = sqlite3.connect(WORKS)
w.executescript("""
CREATE TABLE users (id INTEGER PRIMARY KEY, employee_no TEXT, name TEXT);
CREATE TABLE mail_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, direction TEXT DEFAULT 'in',
  from_email TEXT, to_email TEXT, cc TEXT, subject TEXT, body_text TEXT, body_html TEXT, is_deleted INTEGER DEFAULT 0,
  received_at TEXT, dedup_hash TEXT);
CREATE TABLE mail_attachments (id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INTEGER, filename TEXT, size INTEGER,
  path TEXT, data BLOB, sha256 TEXT);
""")
w.execute("INSERT INTO users(id, employee_no, name) VALUES(85, '5', 'fake')")
w.execute("INSERT INTO users(id, employee_no, name) VALUES(86, '67', 'other')")


def store(b, write=True, corrupt=False):
    sha = hashlib.sha256(b).hexdigest()
    p = os.path.join(ATT, "sha256", sha[:2], sha)
    if write:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"corrupted!" + b[10:] if corrupt else b)
    return sha, p


def wm(fr, subj, body, atts=(), d="in", uid=85, deleted=0):
    cur = w.execute("INSERT INTO mail_messages(user_id,direction,from_email,subject,body_text,is_deleted,received_at) VALUES(?,?,?,?,?,?,?)",
                    (uid, d, fr, subj, body, deleted, "2026-06-20 10:00:01"))
    for a in atts:
        w.execute("INSERT INTO mail_attachments(mail_id,filename,size,path,data,sha256) VALUES(?,?,?,?,?,?)",
                  (cur.lastrowid, "x", 1, a.get("path"), a.get("data"), a.get("sha")))


s1, p1 = store(A1)
s3, p3 = store(A3, write=False)
s4, p4 = store(A4, corrupt=True)
s5, p5 = store(A5)
wm("a@x.example", "S1", "B1 ")
wm("A@X.example", "S2", "B2", [dict(sha=s1, path=p1)])
wm("b@y.example", "S3", "B3")
wm("b@y.example", "S4", "B4", deleted=1)
wm("c@z.example", "S5", "B5", [dict(sha=s3, path=p3)])
wm("c@z.example", "S6", "B6", [dict(sha=s4, path=p4)])
wm("c@z.example", "S7", "B7")
wm("e@v.example", "S9", "B9", [dict(sha=s5, path=p5)])
wm("f@u.example", "S10", "B10", uid=86)
wm("me@example.com", "S11", "B11", d="in")
wm("g@t.example", "S12", "B12", [dict(sha=None, path=None, data=A7)])
for i in range(6):
    wm("n%d@q.example" % i, "other %d" % i, "body %d" % i)
w.commit()
w.close()
if BUILD_ONLY:
    print("built", T)
    sys.exit(0)

WANT_DEL, WANT_KEEP = [1, 2, 3, 10, 11, 12, 16], [4, 5, 6, 7, 8, 9, 13, 14, 15]


def run(script, db, **env_extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", KNK_DEDUP_DB=db)
    env.update(env_extra)
    p = subprocess.run([sys.executable, os.path.join(HERE, script)], capture_output=True, env=env, timeout=300)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def pack(lines):
    return base64.b64encode(gzip.compress("\n".join(lines).encode("ascii"))).decode("ascii")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def ids(db):
    c = sqlite3.connect(db)
    r = [x[0] for x in c.execute("SELECT id FROM mail_messages ORDER BY id")]
    a = [x[0] for x in c.execute("SELECT mail_id FROM mail_attachments ORDER BY id")]
    ok = c.execute("PRAGMA integrity_check").fetchone()[0]
    c.close()
    return r, a, ok


def steps12(db=OLD):
    rc1, out1, err1 = run("dedup_1.py", db)
    L1 = out1.splitlines()
    rc2, out2, err2 = run("dedup_2.py", WORKS, OLD_GZ_B64=pack([l for l in L1 if l.startswith(("M|", "U|"))]))
    return rc1, out1, err1, rc2, out2, err2, [l for l in L1 if l.startswith("S|")], [l for l in out2.splitlines() if l.startswith("D|")]


FAKE_TOKENS = ("example", "Kim", "B1", "S12", "B4", "other 1", "f0.bin")
print("\n§1 1단계(보관함 읽기) · 2단계(WORKS 대조) — 읽기 전용")
h_old0, h_works0 = sha(OLD), sha(WORKS)
rc1, out1, err1, rc2, out2, err2, S, D = steps12()
check("1단계 정상 종료 · 메일 16줄 · 상태줄 1개", rc1 == 0 and out1.count("\nM|") + out1.startswith("M|") == 16 and len(S) == 1, err1[-300:])
check("2단계 정상 종료", rc2 == 0 and "[step2 done]" in out2, err2[-400:])
got = sorted(int(l.split("|")[1]) for l in D)
check("⭐삭제 대상(WORKS 에 온전히 있음) = 1·2·3·12·16 뿐", got == [1, 2, 3, 12, 16], got)
for token, why in (("only in the WORKS trash", "휴지통에만 있는 것(5번)"), ("lacks an attachment (or its file is missing/damaged)", "첨부 없음·파일 없음·파일 깨짐(4·6·7·13번)"),
                   ("no stored content", "보관함 첨부에 내용 없음(8번)"), ("not in WORKS", "WORKS 에 없음·다른 사람 것·방향 다름(9·10·11·14·15번)")):
    check("남기는 까닭이 화면에 나온다 — %s" % why, token in out2, out2)
import re  # noqa: E402
_n = {l.rsplit(":", 1)[0].strip(): int(l.rsplit(":", 1)[1]) for l in out2.splitlines() if l.strip().startswith("KEEP ")}
check("남기는 수: 휴지통 1 · 첨부 문제 4 · 내용 없음 1 · 없음 5",
      sorted(_n.values()) == [1, 1, 4, 5] and _n.get("KEEP only in the WORKS trash") == 1 and _n.get("KEEP not in WORKS") == 5, _n)
check("화면·전달 자료에 메일 내용이 없다(1·2단계)", not any(t in out1 + out2 for t in FAKE_TOKENS), (out1 + out2)[:200])
check("⭐1·2단계는 두 DB 를 한 글자도 안 바꾼다", sha(OLD) == h_old0 and sha(WORKS) == h_works0)

print("\n§2 3단계가 멈춰야 할 때 — 멈추고, 아무것도 안 바꾼다")
bad_D = [("D|3|%s" % "0" * 12) if l.startswith("D|3|") else l for l in D]
rc, out, err = run("dedup_3.py", OLD, DEL_GZ_B64=pack(bad_D + S))
check("삭제 목록이 보관함과 안 맞으면(지문 다름) 중단", rc == 3 and "do not match" in out and sha(OLD) == h_old0 and not glob.glob(OLD + ".bak*"), (rc, out, err[-200:]))
rc, out, err = run("dedup_3.py", OLD, DEL_GZ_B64=pack(D + ["D|999|abcdefabcdef"] + S))
check("없는 번호가 목록에 있으면 중단", rc == 3 and sha(OLD) == h_old0, (rc, out))
sz, mt, n = S[0].split("|")[1:]
rc, out, err = run("dedup_3.py", OLD, DEL_GZ_B64=pack(D + ["S|%s|%d|%s" % (sz, int(mt) - 5, n)]))
check("1단계 뒤 보관함 파일이 바뀌었으면(시각 다름) 중단", rc == 3 and "changed since step 1" in out and sha(OLD) == h_old0, (rc, out))
rc, out, err = run("dedup_3.py", OLD, DEL_GZ_B64="")
check("삭제 목록이 없으면 중단", rc == 2 and sha(OLD) == h_old0, (rc, out))
rc, out, err = run("dedup_3.py", OLD, DEL_GZ_B64=pack(D))
check("상태줄(S)이 없으면 중단", rc == 2 and sha(OLD) == h_old0, (rc, out))

print("\n§3 3단계 — 사본 → 삭제 → 검증 → 압축")
size0 = os.path.getsize(OLD)
rc, out3, err = run("dedup_3.py", OLD, DEL_GZ_B64=pack(D + S))
check("3단계 정상 종료(DEDUP OK)", rc == 0 and "RESULT: DEDUP OK" in out3, (rc, out3[-500:], err[-300:]))
r, a, ok = ids(OLD)
check("⭐남은 메일 = 4·5·6·7·8·9·13·14·15 (9통)", r == WANT_KEEP, r)
check("⭐지워진 메일 = 1·2·3·10·11·12·16 (WORKS 에 있는 5 + 보관함 안 사본 2)", sorted(set(range(1, 17)) - set(r)) == WANT_DEL and "= 5 fully present in WORKS + 2 exact copies" in out3, out3)
check("남은 첨부는 남은 메일 것뿐(4·6·7·8·13번) · 주인 없는 첨부 0", a == [4, 6, 7, 8, 13], a)
check("무결성 검사 ok · 파일이 줄었다", ok == "ok" and os.path.getsize(OLD) < size0 * 0.6, (ok, size0, os.path.getsize(OLD)))
baks = glob.glob(OLD + ".bak.dedup.*")
check("사본이 1개 남아 있고, 원래 보관함과 내용이 같다(16통 · 첨부 8개)", len(baks) == 1 and ids(baks[0])[0] == list(range(1, 17)) and len(ids(baks[0])[1]) == 8, baks)
c = sqlite3.connect(OLD)
check("메일과 무관한 표(mail_fetch_seen · users)는 그대로", c.execute("SELECT COUNT(*) FROM mail_fetch_seen").fetchone()[0] == 1 and c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2)
kept_att = c.execute("SELECT length(data) FROM mail_attachments WHERE mail_id=13").fetchone()[0]
c.close()
check("⭐글은 같고 첨부만 다른 13번은 첨부째 그대로 남았다(12번만 지워짐)", kept_att == len(A6), kept_att)
check("3단계 화면에도 메일 내용이 없다", not any(t in out3 for t in FAKE_TOKENS), out3[:300])
check("WORKS 는 3단계 뒤에도 한 글자도 안 바뀜", sha(WORKS) == h_works0)

print("\n§4 한 번 더 돌려도 안전 · 되돌리기 · 사본 지우기")
rc1, o1, _, rc2, o2, _, S2, D2 = steps12()
check("지운 뒤 다시 대조하면 삭제 대상 0", rc2 == 0 and D2 == [], D2)
h_after = sha(OLD)
rc, out, err = run("dedup_3.py", OLD, DEL_GZ_B64=pack(D2 + S2))
r2, a2, ok2 = ids(OLD)
check("다시 실행해도 남은 9통 그대로 · 지울 것이 없으면 **사본도 만들지 않는다**",
      rc == 0 and r2 == WANT_KEEP and "nothing to delete" in out and len(glob.glob(OLD + ".bak.dedup.*")) == 1 and sha(OLD) == h_after, (rc, out[-300:]))
for b in glob.glob(OLD + ".bak.dedup.*")[1:]:
    pass
rc, out, err = run("dedup_restore.py", OLD)
r3, a3, ok3 = ids(OLD)
check("⭐되돌리기 → 16통 · 첨부 8개가 전부 돌아온다", rc == 0 and "RESULT: RESTORE OK" in out and r3 == list(range(1, 17)) and len(a3) == 8 and ok3 == "ok", (rc, out, err[-200:]))
time.sleep(1.1)
rc1, o1, _, rc2, o2, _, S3, D3 = steps12()
rc, out, err = run("dedup_3.py", OLD, DEL_GZ_B64=pack(D3 + S3))
check("되돌린 뒤 다시 적용하면 같은 결과(9통)", rc == 0 and ids(OLD)[0] == WANT_KEEP, (rc, out[-300:]))
nb = len(glob.glob(OLD + ".bak.dedup.*"))
check("이제 사본이 2개(원본 16통짜리 둘) — 그 상태에서 되돌리기는 **가장 온전한 것**을 고른다", nb == 2, nb)
# 사본 하나를 '줄어든 상태'로 바꿔 놓고(최신 이름으로) 되돌리기가 그걸 고르지 않는지
_newest = sorted(glob.glob(OLD + ".bak.dedup.*"))[-1]
shutil.copy2(OLD, _newest)                      # 최신 사본 = 9통짜리(함정)
rc, out, err = run("dedup_restore.py", OLD)
check("⭐최신 사본이 줄어든 상태여도 되돌리기는 16통짜리 원본 사본을 고른다", rc == 0 and ids(OLD)[0] == list(range(1, 17)), (rc, out))
time.sleep(1.1)
rc1, o1, _, rc2, o2, _, S4, D4 = steps12()
rc, out, err = run("dedup_3.py", OLD, DEL_GZ_B64=pack(D4 + S4))
check("그 뒤 다시 적용 → 9통", rc == 0 and ids(OLD)[0] == WANT_KEEP, (rc, out[-200:]))
nb = len(glob.glob(OLD + ".bak.dedup.*"))
rc, out, err = run("dedup_purge.py", OLD)
check("사본 지우기 → 사본 0개 · 보관함은 그대로 9통", rc == 0 and "RESULT: PURGE OK" in out and not glob.glob(OLD + ".bak.dedup.*") and ids(OLD)[0] == WANT_KEEP and nb >= 1, (rc, out, nb))
rc, out, err = run("dedup_purge.py", OLD)
check("사본이 없을 때 지우기 = 할 일 없음(오류 아님)", rc == 0 and "nothing to do" in out, (rc, out))
rc, out, err = run("dedup_restore.py", OLD)
check("사본을 지운 뒤 되돌리기 = 중단(되돌릴 것이 없다고 알려 줌)", rc == 3 and "no backup file" in out and ids(OLD)[0] == WANT_KEEP, (rc, out))

shutil.rmtree(T, ignore_errors=True)
print("\n결과: PASS %d / FAIL %d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
