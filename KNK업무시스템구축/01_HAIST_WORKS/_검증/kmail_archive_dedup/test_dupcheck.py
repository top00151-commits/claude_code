# -*- coding: utf-8 -*-
"""옛 메일 보관함 중복 점검(dupcheck_a/b) — 가짜 DB 두 개로 숫자가 맞게 나오는지 시험(서버·실제 메일 무접촉)."""
import base64, gzip, hashlib, os, sqlite3, subprocess, sys, tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD_ONLY = len(sys.argv) > 2 and sys.argv[1] == "--build-only"
T = sys.argv[2] if BUILD_ONLY else tempfile.mkdtemp(prefix="knk_dupcheck_")
os.makedirs(T, exist_ok=True)
for _f in ("old.db", "works.db"):
    if BUILD_ONLY and os.path.exists(os.path.join(T, _f)):
        os.remove(os.path.join(T, _f))
OLD, WORKS = os.path.join(T, "old.db"), os.path.join(T, "works.db")
PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS]", name)
    else:
        FAIL += 1
        print("  [FAIL]", name, extra)


# ── 가짜 옛 보관함(옛 앱 스키마 그대로) ──
o = sqlite3.connect(OLD)
o.executescript("""
CREATE TABLE users (id INTEGER PRIMARY KEY, employee_no TEXT, name TEXT, email TEXT);
CREATE TABLE mail_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, direction TEXT DEFAULT 'in',
  from_email TEXT, from_name TEXT, to_email TEXT, cc TEXT, bcc TEXT, subject TEXT, body_text TEXT, body_html TEXT,
  category TEXT, lang TEXT, summary TEXT, is_read INTEGER DEFAULT 0, is_starred INTEGER DEFAULT 0, is_deleted INTEGER DEFAULT 0,
  raw_size INTEGER DEFAULT 0, received_at TEXT, read_at TEXT, deleted_at TEXT, created_at TEXT);
CREATE TABLE mail_attachments (id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INTEGER, filename TEXT, mime TEXT, size INTEGER,
  path TEXT, content_id TEXT, is_inline INTEGER DEFAULT 0, data BLOB, created_at TEXT);
""")
o.execute("INSERT INTO users(id, employee_no, name, email) VALUES(1, '5', 'fake', 'fake@example.com')")
A1, A2, A3, A4 = b"AAAA" * 1000, b"BBBB" * 500, b"CCCC" * 100, b"DDDD" * 100


def om(fr, subj, body, atts=(), d="in", html="", rcv="2026-06-20 10:00:00"):
    cur = o.execute("INSERT INTO mail_messages(user_id,direction,from_email,to_email,cc,subject,body_text,body_html,received_at) "
                    "VALUES(1,?,?,?,?,?,?,?,?)", (d, fr, "me@example.com", "", subj, body, html, rcv))
    for i, b in enumerate(atts):
        o.execute("INSERT INTO mail_attachments(mail_id,filename,size,data) VALUES(?,?,?,?)", (cur.lastrowid, "f%d.bin" % i, len(b), b))


om("Kim <a@x.example>", "S1", "B1")                        # 1  WORKS 에도 있음 → FULL
om("Kim <a@x.example>", "S1", "B1")                        # 2  1의 완전 사본 → DUP_INSIDE
om("a@x.example", "S2", "B2", [A1])                        # 3  WORKS 에 첨부까지 있음 → FULL
om("b@y.example", "S3", "B3", [A2])                        # 4  WORKS 에 본문만(첨부 없음) → BODY_ONLY
om("b@y.example", "S4", "B4-old")                          # 5  WORKS 엔 같은 제목·다른 본문 → WEAK
om("c@z.example", "S5", "B5")                              # 6  보관함에만 → NONE
om("c@z.example", "S6", "B6", [A3])                        # 7  보관함에만 → NONE
om("c@z.example", "S6", "B6", [A4])                        # 8  7과 글은 같지만 **첨부가 다름** → 사본 아님(NONE)
om("a@x.example", "S2", "B2", [A1])                        # 9  3의 완전 사본(첨부까지) → DUP_INSIDE
om("me@example.com", "S7", "B7", d="out")                  # 10 보낸 메일 · WORKS 에도 있음 → FULL
o.commit()
o.close()

# ── 가짜 WORKS(WORKS 스키마 — sha256 열 있음) ──
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


def wm(fr, subj, body, sha=(), d="in", uid=85, rcv="2026-09-01 09:00:00"):
    cur = w.execute("INSERT INTO mail_messages(user_id,direction,from_email,subject,body_text,received_at) VALUES(?,?,?,?,?,?)",
                    (uid, d, fr, subj, body, rcv))
    for s in sha:
        w.execute("INSERT INTO mail_attachments(mail_id,filename,size,sha256) VALUES(?,?,?,?)", (cur.lastrowid, "x", 1, s))


wm("a@x.example", "S1", "B1  ")                             # 끝 빈칸은 같은 메일로 본다(strip)
wm("A@X.example", "S2", "B2", [hashlib.sha256(A1).hexdigest()])   # 주소 대소문자 무시
wm("b@y.example", "S3", "B3")                               # 첨부 없이
wm("b@y.example", "S4", "B4-new")
wm("me@example.com", "S7", "B7", d="out")
wm("c@z.example", "S5", "B5", uid=86)                       # ⚠다른 사람의 같은 메일 — 주인이 달라 「WORKS 에 있음」으로 치면 안 됨
for i in range(5):
    wm("n%d@q.example" % i, "other %d" % i, "body %d" % i)
w.commit()
w.close()
if BUILD_ONLY:
    print("built", OLD, WORKS)
    sys.exit(0)


def run(script, env_extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.update(env_extra)
    p = subprocess.run([sys.executable, os.path.join(HERE, script)], capture_output=True, env=env, timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


rc, outA, errA = run("dupcheck_a.py", {"KNK_DUPCHECK_DB": OLD})
check("A(보관함 점검) 정상 종료", rc == 0 and "[done 32203]" in outA, errA[-300:])
linesA = outA.splitlines()
H = [l for l in linesA if l.startswith("H|")]
U = [l for l in linesA if l.startswith("U|")]
human = "\n".join(l for l in linesA if not l.startswith(("H|", "U|")))
check("메일마다 한 줄(H) 10개 · 주인 한 줄(U) 1개", len(H) == 10 and U == ["U|1|5"], (len(H), U))
check("화면 글에 제목·주소·본문이 한 글자도 없다(가짜 값 S1·B1·example 로 확인)",
      not any(t in human for t in ("S1", "B1", "B4-old", "example", "Kim", "f0.bin")), human[:300])
check("H 줄에도 내용이 없다(지문·숫자뿐)", all(set(l) <= set("H|0123456789abcdef,io-") for l in H), H[:2])
check("보관함 안 완전 사본: 2통(2번·9번)", "extra copies: 2 mails" in human, human)
check("WORKS 규칙만으로 세면 3통 · 그중 첨부가 다른 묶음 1개를 따로 경고", "extra copies: 3 mails" in human and "DIFFERENT attachments: 1" in human, human)
check("첨부 4개 중 내용이 다른 것 4... 같은 파일 재저장 1개(A1 두 번) 감지", "4 distinct of 5" in human, human)
check("받은 날짜 범위·방향별 수가 나온다", "2026-06-20 ~ 2026-06-20" in human and "in=9" in human and "out=1" in human, human)

data = base64.b64encode(gzip.compress("\n".join(U + H).encode("ascii"))).decode("ascii")
rc, outB, errB = run("dupcheck_b.py", {"KNK_DUPCHECK_DB": WORKS, "OLD_GZ_B64": data})
check("B(WORKS 대조) 정상 종료", rc == 0 and "[done 32201]" in outB, errB[-300:])
summ = [l for l in outB.splitlines() if l.startswith("SUMMARY|")]
got = dict(kv.split("=") for kv in summ[0].split("|")[1:]) if summ else {}
check("⭐분류: 전체 10 · 보관함 안 사본 2 · WORKS 에 온전히 있음 3 · 본문만 1 · 제목만 1 · 보관함에만 3",
      (got.get("total"), got.get("dup_inside"), got.get("full"), got.get("body_only"), got.get("weak"), got.get("none")) == ("10", "2", "3", "1", "1", "3"), got)
check("⭐다른 사람(주인이 다른) WORKS 메일은 「있음」으로 치지 않는다(6번 = 보관함에만)", got.get("none") == "3")
check("⭐글은 같아도 첨부가 다른 8번은 사본으로 치지 않는다", got.get("dup_inside") == "2")
check("주인을 사번으로 찾았다고 나온다", "found in WORKS by employee number: yes" in outB, outB[:300])
check("B 화면에도 내용이 없다(가짜 값 example·Kim·B4-·other·body 로 확인)", not any(t in outB for t in ("example", "Kim", "B4-", "other 1", "body 1", "S6")), outB[:300])
exp_remove = (0 + (len(b"B2") + len(A1)) + len(b"B1") + (len(b"B2") + len(A1)) + len(b"B1") + len(b"B7")) / 1048576.0
check("지울 수 있는 용량 계산이 맞다(%.4f MB)" % exp_remove, abs(float(got.get("remove_mb", -1)) - round(exp_remove, 1)) < 0.11, got)

# 빈 자료를 넘기면 아무것도 읽지 않고 멈춘다
rc, outB2, _ = run("dupcheck_b.py", {"KNK_DUPCHECK_DB": WORKS, "OLD_GZ_B64": ""})
check("보관함 자료 없이 B 를 돌리면 멈춘다(ABORT)", rc == 2 and "ABORT" in outB2, outB2)
# 읽기 전용 — 두 DB 가 그대로인가
import shutil  # noqa: E402
h1 = hashlib.sha256(open(OLD, "rb").read()).hexdigest()
h2 = hashlib.sha256(open(WORKS, "rb").read()).hexdigest()
run("dupcheck_a.py", {"KNK_DUPCHECK_DB": OLD})
run("dupcheck_b.py", {"KNK_DUPCHECK_DB": WORKS, "OLD_GZ_B64": data})
check("⭐읽기 전용 — 돌린 뒤에도 두 DB 파일이 한 글자도 안 바뀜",
      h1 == hashlib.sha256(open(OLD, "rb").read()).hexdigest() and h2 == hashlib.sha256(open(WORKS, "rb").read()).hexdigest())
shutil.rmtree(T, ignore_errors=True)
print("\n결과: PASS %d / FAIL %d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
