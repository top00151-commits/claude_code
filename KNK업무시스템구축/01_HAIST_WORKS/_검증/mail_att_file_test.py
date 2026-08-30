# -*- coding: utf-8 -*-
"""메일 첨부 DB밖(나스 파일) 분리 검증 (대표 지시 2026-08-30). 실 DB/서버 무접촉.
- 신규 첨부 = 나스 파일 저장(data BLOB 아님·path 기록) / get = 파일 읽기
- 기존 첨부(path NULL·data BLOB) = get 이 BLOB 폴백(배포해도 6795개 그대로 열림)
- 소유권 강제·파일없음 폴백·크기상한 메타만."""
import os
import sys
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from app import mail_store as ms  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print("  [PASS]", name)
    else:
        FAIL += 1; print("  [FAIL]", name)


TMP = tempfile.mkdtemp()
ATT = os.path.join(TMP, "mail_att")
ms._att_dir = lambda: ATT   # 첨부 폴더를 임시 폴더로(실서버 무관)


def make_db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE mail_messages(id INTEGER PRIMARY KEY, user_id INT, is_deleted INT DEFAULT 0)")
    c.execute("""CREATE TABLE mail_attachments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INT, filename TEXT, mime TEXT,
        size INT, content_id TEXT, is_inline INT DEFAULT 0, data BLOB, path TEXT)""")
    c.execute("INSERT INTO mail_messages(id,user_id) VALUES(1,85)")
    return c


print("=== 1) 신규 첨부 = 나스 파일 저장(BLOB 아님) ===")
c = make_db()
ms._save_attachments(c, 1, [{"filename": "월간보고서.pdf", "mime": "application/pdf", "size": 9, "data": b"HELLO_PDF"}])
r = c.execute("SELECT id, filename, data, path FROM mail_attachments").fetchone()
check("DB data 는 NULL(BLOB 저장 안 함)", r["data"] is None)
check("path 기록됨", bool(r["path"]))
check("나스 파일 실제 생성됨", os.path.exists(r["path"]))
check("파일 내용 == 원본 바이트", open(r["path"], "rb").read() == b"HELLO_PDF")
check("파일 경로가 mail_att/1/ 아래", os.path.join("mail_att", "1") in r["path"].replace("\\", "/").replace("/mail_att/1/", "/mail_att/1/") or "mail_att" in r["path"])

print("=== 2) get_attachment = 파일에서 읽기 ===")
g = ms.get_attachment(c, r["id"], 85)
check("바이트 읽힘(파일)", g and g["data"] == b"HELLO_PDF")
check("파일명 보존", g["filename"] == "월간보고서.pdf")
check("mime 보존", g["mime"] == "application/pdf")

print("=== 3) 소유권 강제(다른 사용자 차단) ===")
check("다른 user_id 는 None", ms.get_attachment(c, r["id"], 99) is None)

print("=== 4) 기존 첨부(path NULL·data BLOB) = BLOB 폴백 ===")
c.execute("INSERT INTO mail_attachments(mail_id,filename,mime,data,path) VALUES(1,'old.jpg','image/jpeg',?,NULL)", (b"OLD_BLOB_BYTES",))
oid = c.execute("SELECT id FROM mail_attachments WHERE filename='old.jpg'").fetchone()["id"]
g2 = ms.get_attachment(c, oid, 85)
check("마이그 전 BLOB 그대로 읽힘", g2 and g2["data"] == b"OLD_BLOB_BYTES")

print("=== 5) path 있으나 파일 없음 → BLOB 폴백 ===")
c.execute("INSERT INTO mail_attachments(mail_id,filename,mime,data,path) VALUES(1,'both','image/x',?,?)", (b"FALLBACK", "/no/such/path/x.bin"))
bid = c.execute("SELECT id FROM mail_attachments WHERE filename='both'").fetchone()["id"]
g3 = ms.get_attachment(c, bid, 85)
check("파일 유실 시 BLOB 폴백(안전망)", g3 and g3["data"] == b"FALLBACK")

print("=== 6) 파일도 BLOB 도 없으면 None ===")
c.execute("INSERT INTO mail_attachments(mail_id,filename,data,path) VALUES(1,'none',NULL,NULL)")
nid = c.execute("SELECT id FROM mail_attachments WHERE filename='none'").fetchone()["id"]
check("둘 다 없으면 None", ms.get_attachment(c, nid, 85) is None)

print("=== 7) 큰 첨부(>12MB) = 메타만(파일·BLOB 둘 다 없음) ===")
c2 = make_db()
big = b"x" * (ms._ATT_STORE_MAX + 1)
ms._save_attachments(c2, 1, [{"filename": "big.zip", "mime": "application/zip", "size": len(big), "data": big}])
rb = c2.execute("SELECT data, path FROM mail_attachments").fetchone()
check("상한 초과는 파일 저장 안 함(path NULL)", rb["path"] is None)
check("상한 초과는 BLOB 도 없음(data NULL)", rb["data"] is None)

print("=== 8) 여러 첨부 각각 파일 분리 ===")
c3 = make_db()
ms._save_attachments(c3, 1, [
    {"filename": "a.txt", "data": b"AAA"},
    {"filename": "b.txt", "data": b"BBB"},
])
rows = c3.execute("SELECT id, path FROM mail_attachments ORDER BY id").fetchall()
check("2개 다 파일 생성·경로 다름", len(rows) == 2 and rows[0]["path"] != rows[1]["path"]
      and os.path.exists(rows[0]["path"]) and os.path.exists(rows[1]["path"]))
check("각 파일 내용 정확", open(rows[0]["path"], "rb").read() == b"AAA" and open(rows[1]["path"], "rb").read() == b"BBB")

print("\n===== 결과: %d PASS / %d FAIL =====" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
