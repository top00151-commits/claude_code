# -*- coding: utf-8 -*-
"""메일 이전 스크립트(migrate_mail_to_kmail.py) 합성 데이터 검증 — 실 DB 무관·안전.
가짜 WORKS knk.db(대표 1명·메일 3·첨부 2) + 빈 kmail mail.db → dry-run/apply → 결과 검증.
user_id 재매핑(login_id 기준)·첨부 mail_id 재매핑·미매핑 보류·중복적재 방지를 확인."""
import os
import sys
import sqlite3
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MIG = os.path.join(ROOT, "deploy", "migrate_mail_to_kmail.py")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print("  [PASS]", name)
    else:
        FAIL += 1; print("  [FAIL]", name)


def make_works(path):
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, login_id TEXT UNIQUE,
        password TEXT, email TEXT, team_id INTEGER, rank TEXT, role TEXT, is_active INTEGER DEFAULT 1,
        lang TEXT DEFAULT 'ko', created_at TEXT);
    CREATE TABLE mail_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, direction TEXT,
        from_email TEXT, from_name TEXT, to_email TEXT, cc TEXT, bcc TEXT, subject TEXT, body_text TEXT,
        body_html TEXT, category TEXT, lang TEXT, summary TEXT, is_read INTEGER, is_starred INTEGER,
        is_deleted INTEGER, raw_size INTEGER, received_at TEXT, read_at TEXT, deleted_at TEXT, created_at TEXT,
        dedup_hash TEXT, dup_count INTEGER);
    CREATE TABLE mail_attachments(id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INTEGER, filename TEXT,
        mime TEXT, size INTEGER, path TEXT, content_id TEXT, is_inline INTEGER, data BLOB, created_at TEXT);
    CREATE TABLE mail_aliases(address TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT);
    """)
    # 대표(uid=85, login_id=5) + 메일 안 쓰는 직원(uid=86)
    c.execute("INSERT INTO users(id,name,login_id,password,email,role) VALUES(85,'김정락','5','x','top0015@knknara.co.kr','ceo')")
    c.execute("INSERT INTO users(id,name,login_id,password,email,role) VALUES(86,'홍길동','7','x','hong@knknara.co.kr','member')")
    for i in range(3):
        c.execute("INSERT INTO mail_messages(user_id,direction,subject,body_text,is_read,is_deleted,raw_size) "
                  "VALUES(85,'in',?,?,0,0,100)", ("제목%d" % i, "본문%d" % i))
    # 첨부 2개 (첫 메일에)
    mid = c.execute("SELECT MIN(id) FROM mail_messages").fetchone()[0]
    for i in range(2):
        c.execute("INSERT INTO mail_attachments(mail_id,filename,mime,size,data) VALUES(?,?,?,?,?)",
                  (mid, "a%d.pdf" % i, "application/pdf", 50, b"x" * 50))
    c.execute("INSERT INTO mail_aliases(address,user_id) VALUES('top0015@knknara.co.kr',85)")
    c.commit(); c.close()


def make_kmail(path):
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, employee_no TEXT, login_id TEXT,
        password TEXT, name TEXT, name_en TEXT, name_vi TEXT, email TEXT, phone TEXT, dept_code TEXT,
        team_id INTEGER, rank TEXT, role TEXT DEFAULT 'member', entity TEXT, is_active INTEGER DEFAULT 1,
        password_version INTEGER DEFAULT 1, lang TEXT DEFAULT 'ko', created_at TEXT);
    CREATE TABLE mail_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, direction TEXT,
        from_email TEXT, from_name TEXT, to_email TEXT, cc TEXT, bcc TEXT, subject TEXT, body_text TEXT,
        body_html TEXT, category TEXT, lang TEXT, summary TEXT, is_read INTEGER, is_starred INTEGER,
        is_deleted INTEGER, raw_size INTEGER, received_at TEXT, read_at TEXT, deleted_at TEXT, created_at TEXT);
    CREATE TABLE mail_attachments(id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INTEGER, filename TEXT,
        mime TEXT, size INTEGER, path TEXT, content_id TEXT, is_inline INTEGER, data BLOB, created_at TEXT);
    CREATE TABLE mail_aliases(address TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT);
    CREATE TABLE mail_signatures(user_id INTEGER PRIMARY KEY, body TEXT, updated_at TEXT);
    CREATE TABLE mail_rules(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match_type TEXT, pattern TEXT, category TEXT, enabled INTEGER, created_at TEXT);
    CREATE TABLE mail_fetch_accounts(id INTEGER PRIMARY KEY AUTOINCREMENT, owner_user_id INTEGER UNIQUE, label TEXT, protocol TEXT, host TEXT, port INTEGER, use_ssl INTEGER, username TEXT, password_enc TEXT, last_uid INTEGER, enabled INTEGER, last_run TEXT, last_status TEXT, last_count INTEGER, created_at TEXT);
    """)
    c.commit(); c.close()


def run(works, kmail, apply=False):
    cmd = [sys.executable, MIG, "--works", works, "--kmail", kmail]
    if apply:
        cmd.append("--apply")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return r.stdout + r.stderr


tmp = tempfile.mkdtemp()
works = os.path.join(tmp, "knk.db")
kmail = os.path.join(tmp, "mail.db")
make_works(works)
make_kmail(kmail)

print("=== 1) DRY-RUN: 분석만, kmail 변화 없어야 ===")
out = run(works, kmail, apply=False)
check("소유자 1명 인식(메일 가진 대표만)", "메일 소유자 1명" in out)
check("복사 대상 3건 표시", "복사:3" in out or "복사 대상" in out)
k = sqlite3.connect(kmail)
check("dry-run 후 kmail 메일 0(변화 없음)", k.execute("SELECT COUNT(*) FROM mail_messages").fetchone()[0] == 0)
k.close()

print("=== 2) APPLY: 실제 복사 ===")
out = run(works, kmail, apply=True)
print(out)
k = sqlite3.connect(kmail); k.row_factory = sqlite3.Row
check("kmail 메일 3건", k.execute("SELECT COUNT(*) FROM mail_messages").fetchone()[0] == 3)
check("kmail 첨부 2건", k.execute("SELECT COUNT(*) FROM mail_attachments").fetchone()[0] == 2)
check("kmail 사용자 1명 생성(대표만·메일 없는 직원 제외)", k.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1)
u = k.execute("SELECT login_id, employee_no, name, role FROM users").fetchone()
check("생성된 사용자 = 대표(login_id=5)", u["login_id"] == "5" and u["name"] == "김정락")
check("employee_no=login_id(사번)", u["employee_no"] == "5")
check("역할 보존(ceo)", u["role"] == "ceo")
# 메일 주인이 kmail 대표 id 가리키는지
kuid = u["id"] if "id" in u.keys() else k.execute("SELECT id FROM users").fetchone()[0]
allmail = k.execute("SELECT DISTINCT user_id FROM mail_messages").fetchall()
check("모든 메일이 대표(kmail uid) 소유", len(allmail) == 1 and allmail[0]["user_id"] == kuid)
# 첨부가 옮겨진 메일에 연결됐는지(고아 없음)
orphan = k.execute("SELECT COUNT(*) FROM mail_attachments a LEFT JOIN mail_messages m ON m.id=a.mail_id WHERE m.id IS NULL").fetchone()[0]
check("고아 첨부 0(mail_id 재매핑 정상)", orphan == 0)
check("alias 복사됨", k.execute("SELECT COUNT(*) FROM mail_aliases").fetchone()[0] == 1)
k.close()

print("=== 3) 재적용 방지: 이미 메일 있는 kmail에 apply → 중단 ===")
out = run(works, kmail, apply=True)
check("중복 적재 차단(중단 메시지)", "중단" in out and "이미" in out)
k = sqlite3.connect(kmail)
check("메일 여전히 3건(이중 적재 안 됨)", k.execute("SELECT COUNT(*) FROM mail_messages").fetchone()[0] == 3)
k.close()

print("\n===== 결과: %d PASS / %d FAIL =====" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
