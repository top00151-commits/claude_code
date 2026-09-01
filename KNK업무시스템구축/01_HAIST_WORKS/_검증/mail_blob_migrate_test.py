# -*- coding: utf-8 -*-
"""첨부 BLOB -> 파일 이관 스크립트 검증 (라이브 실행 전 필수).
핵심 증명: ①손실 0(검증 통과분만 BLOB 회수) ②중복제거 ③멱등·재개 ④실패 시 BLOB 보존
          ⑤빈 BLOB 무한루프 없음 ⑥이관 후 앱이 그대로 읽음."""
import os
import subprocess
import sqlite3
import sys
import tempfile
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from app import mail_store as ms  # noqa: E402

SCRIPT = os.path.join(ROOT, "deploy", "migrate_mail_blobs_to_files.py")
PASS = FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print("  [PASS]", name)
    else:
        FAIL += 1; print("  [FAIL]", name)


def run(db, *extra):
    r = subprocess.run([sys.executable, SCRIPT, "--db", db, "--sleep", "0", *extra],
                       capture_output=True, text=True)
    return r.stdout + r.stderr


def make_db(tmp, blobs):
    """운영과 같은 모양(기존 테이블·BLOB 보유)의 DB 생성."""
    db = os.path.join(tmp, "data", "knk.db")
    os.makedirs(os.path.dirname(db), exist_ok=True)
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE mail_messages(id INTEGER PRIMARY KEY, user_id INT, is_deleted INT DEFAULT 0)")
    c.execute("""CREATE TABLE mail_attachments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INT, filename TEXT, mime TEXT,
        size INT, path TEXT, content_id TEXT, is_inline INT DEFAULT 0, data BLOB,
        created_at TEXT)""")          # 구 스키마 = sha256 컬럼 없음(운영 상태)
    c.execute("INSERT INTO mail_messages(id,user_id) VALUES(1,85)")
    for i, b in enumerate(blobs, start=1):
        c.execute("INSERT INTO mail_attachments(mail_id,filename,mime,size,data) VALUES(1,?,?,?,?)",
                  ("f%d.bin" % i, "application/octet-stream", len(b), b))
    c.commit(); c.close()
    return db


def count_files(root):
    n = 0
    for dp, _dn, fns in os.walk(root):
        n += len([f for f in fns if not f.startswith(".tmp_")])
    return n


print("=== 1) 기본 이관: BLOB -> 파일, 내용 보존 ===")
tmp = tempfile.mkdtemp()
A, B = b"REPORT_PDF_CONTENT" * 40, b"DRAWING_DWG" * 33
db = make_db(tmp, [A, B])
out = run(db)
c = sqlite3.connect(db); c.row_factory = sqlite3.Row
rows = c.execute("SELECT id,data,path,sha256,size FROM mail_attachments ORDER BY id").fetchall()
check("모든 BLOB 회수됨(data NULL)", all(r["data"] is None for r in rows))
check("path·sha256 기록됨", all(r["path"] and r["sha256"] for r in rows))
check("실제 파일 존재", all(os.path.exists(r["path"]) for r in rows))
check("파일 내용 == 원본(손실 0)",
      open(rows[0]["path"], "rb").read() == A and open(rows[1]["path"], "rb").read() == B)
check("sha256 == 실제 내용 해시",
      rows[0]["sha256"] == hashlib.sha256(A).hexdigest())
check("내용해시 경로 구조(sha256/ab/hash)", "sha256" in rows[0]["path"].replace("\\", "/"))

print("=== 2) 이관 후 앱(get_attachment)이 그대로 읽음 ===")
ms._att_dir = lambda: os.path.join(tmp, "data", "mail_att")
g = ms.get_attachment(c, rows[0]["id"], 85)
check("앱이 파일에서 원본 바이트 읽음", g and g["data"] == A)

print("=== 3) 중복제거: 같은 내용 3건 = 물리 파일 1개 ===")
tmp2 = tempfile.mkdtemp()
same = b"NEWSLETTER_LOGO" * 100
db2 = make_db(tmp2, [same, same, same, b"OTHER"])
run(db2)
attroot = os.path.join(tmp2, "data", "mail_att")
check("파일 2개만 생성(같은내용 3건->1개 + 다른내용 1개)", count_files(attroot) == 2)
c2 = sqlite3.connect(db2); c2.row_factory = sqlite3.Row
rs = c2.execute("SELECT path,sha256 FROM mail_attachments ORDER BY id").fetchall()
check("같은 내용 3행이 같은 파일 참조", rs[0]["path"] == rs[1]["path"] == rs[2]["path"])
check("다른 내용은 다른 파일", rs[3]["path"] != rs[0]["path"])

print("=== 4) 멱등: 두 번 돌려도 안전(할 일 없음) ===")
out2 = run(db2)
check("2회차는 이관 대상 0", "nothing to migrate" in out2)
rs2 = c2.execute("SELECT COUNT(*) FROM mail_attachments WHERE data IS NOT NULL").fetchone()[0]
check("BLOB 남은 행 0", rs2 == 0)

print("=== 5) 중단 후 재개(컨테이너 재시작 흉내) ===")
tmp3 = tempfile.mkdtemp()
db3 = make_db(tmp3, [b"A" * 100, b"B" * 100, b"C" * 100, b"D" * 100])
run(db3, "--limit", "2")            # 2건만 하고 멈춤(= 중단)
c3 = sqlite3.connect(db3)
mid = c3.execute("SELECT COUNT(*) FROM mail_attachments WHERE data IS NOT NULL").fetchone()[0]
check("중단 시점: 2건 남아있음", mid == 2)
run(db3)                            # 재개
after = c3.execute("SELECT COUNT(*) FROM mail_attachments WHERE data IS NOT NULL").fetchone()[0]
check("재개하면 나머지 완료(0건)", after == 0)
check("재개 후에도 내용 보존",
      open(c3.execute("SELECT path FROM mail_attachments ORDER BY id").fetchone()[0], "rb").read() == b"A" * 100)

print("=== 6) 검증 실패 시 BLOB 보존(손실 0) — 디스크 이상 흉내 ===")
tmp4 = tempfile.mkdtemp()
db4 = make_db(tmp4, [b"MUST_NOT_LOSE" * 10])
# 파일이 엉뚱하게 써지는 상황(검증 불일치) 재현: 쓰기 후 내용을 훼손시키는 래퍼
patched = SCRIPT + ".patched.py"
src = open(SCRIPT, encoding="utf-8").read().replace(
    "def verify_file(p, sha, size):", "def verify_file(p, sha, size):\n    return False  # 강제 실패")
open(patched, "w", encoding="utf-8").write(src)
r = subprocess.run([sys.executable, patched, "--db", db4, "--sleep", "0"], capture_output=True, text=True)
os.remove(patched)
c4 = sqlite3.connect(db4)
kept = c4.execute("SELECT data FROM mail_attachments").fetchone()[0]
check("검증 실패하면 BLOB 그대로 보존(첨부 손실 0)", kept == b"MUST_NOT_LOSE" * 10)
check("실패 보고됨", "fail" in (r.stdout + r.stderr).lower())

print("=== 7) 빈 BLOB: 무한루프 없이 처리 ===")
tmp5 = tempfile.mkdtemp()
db5 = make_db(tmp5, [b"", b"REAL_DATA"])
out5 = run(db5)
c5 = sqlite3.connect(db5)
left5 = c5.execute("SELECT COUNT(*) FROM mail_attachments WHERE data IS NOT NULL").fetchone()[0]
check("빈 BLOB 포함해도 종료(무한루프 없음)", left5 == 0 and "RESULT" in out5)

print("=== 8) dry-run 은 아무것도 바꾸지 않음 ===")
tmp6 = tempfile.mkdtemp()
db6 = make_db(tmp6, [b"UNTOUCHED"])
run(db6, "--dry-run")
c6 = sqlite3.connect(db6)
check("dry-run 후 BLOB 그대로", c6.execute("SELECT data FROM mail_attachments").fetchone()[0] == b"UNTOUCHED")
check("dry-run 은 파일 안 만듦", count_files(os.path.join(tmp6, "data", "mail_att")) == 0)

print("\n===== 결과: %d PASS / %d FAIL =====" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
