# -*- coding: utf-8 -*-
"""메일 첨부 내용해시 저장 + 중복제거 검증 (대표 확정 2026-08-31). 실 DB/서버 무접촉.
- 신규 첨부 = 내용해시 경로 파일 저장(BLOB 아님)·sha256 기록
- 같은 내용(다른 메일) = 물리 파일 1개만(중복제거)·두 행 모두 읽힘
- 다른 내용 = 다른 파일
- 공유 안전: 한 메일 첨부행 삭제해도 물리파일 유지 → 다른 메일 그대로 읽힘(파일 삭제는 안 함)
- 파일명은 행별 유지(같은 물리파일이라도 메일별 원래 이름)
- 파일 기록 실패 → BLOB 폴백(데이터 손실 0)
- 기존(path NULL·data BLOB) 폴백·소유권·크기상한 메타만."""
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


def count_files(root):
    n = 0
    for dp, _dn, fns in os.walk(root):
        for f in fns:
            if not f.startswith(".tmp_"):
                n += 1
    return n


def make_db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE mail_messages(id INTEGER PRIMARY KEY, user_id INT, is_deleted INT DEFAULT 0)")
    c.execute("""CREATE TABLE mail_attachments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INT, filename TEXT, mime TEXT,
        size INT, content_id TEXT, is_inline INT DEFAULT 0, data BLOB, path TEXT, sha256 TEXT)""")
    c.execute("INSERT INTO mail_messages(id,user_id) VALUES(1,85)")
    c.execute("INSERT INTO mail_messages(id,user_id) VALUES(2,85)")
    c.execute("INSERT INTO mail_messages(id,user_id) VALUES(3,99)")   # 다른 소유자
    return c


print("=== 1) 신규 첨부 = 내용해시 파일 저장(BLOB 아님·sha256 기록) ===")
c = make_db()
ms._save_attachments(c, 1, [{"filename": "월간보고서.pdf", "mime": "application/pdf", "size": 9, "data": b"HELLO_PDF"}])
r = c.execute("SELECT id, filename, data, path, sha256 FROM mail_attachments").fetchone()
check("DB data 는 NULL(BLOB 저장 안 함)", r["data"] is None)
check("sha256 기록됨(64 hex)", bool(r["sha256"]) and len(r["sha256"]) == 64)
check("path=내용해시 경로", r["path"] and ("sha256" in r["path"].replace("\\", "/")) and r["sha256"] in r["path"])
check("나스 파일 실제 생성", os.path.exists(r["path"]))
check("파일 내용 == 원본", open(r["path"], "rb").read() == b"HELLO_PDF")
g = ms.get_attachment(c, r["id"], 85)
check("get = 파일에서 읽힘", g and g["data"] == b"HELLO_PDF")
check("파일명·mime 보존", g["filename"] == "월간보고서.pdf" and g["mime"] == "application/pdf")

print("=== 2) 같은 내용(다른 메일) = 물리 파일 1개(중복제거) ===")
c = make_db()
n0 = count_files(ATT)   # 앞 소단계가 남긴 파일 제외(증분으로 계수)
same = b"SAME_LOGO_BYTES_x" * 50
ms._save_attachments(c, 1, [{"filename": "logo.png", "mime": "image/png", "data": same}])
ms._save_attachments(c, 2, [{"filename": "signature_logo.png", "mime": "image/png", "data": same}])
rows = c.execute("SELECT id, mail_id, filename, path, sha256 FROM mail_attachments ORDER BY id").fetchall()
check("첨부 행 2개(메일마다 1행)", len(rows) == 2)
check("두 행 sha256 동일", rows[0]["sha256"] == rows[1]["sha256"])
check("두 행 path 동일(같은 물리파일)", rows[0]["path"] == rows[1]["path"])
check("같은내용 2회 저장 = 새 파일 1개만(중복제거)", count_files(ATT) - n0 == 1)
check("행별 파일명은 각자 유지", rows[0]["filename"] == "logo.png" and rows[1]["filename"] == "signature_logo.png")
check("두 메일 모두 바이트 읽힘", ms.get_attachment(c, rows[0]["id"], 85)["data"] == same
      and ms.get_attachment(c, rows[1]["id"], 85)["data"] == same)

print("=== 3) 다른 내용 = 다른 파일 ===")
before = count_files(ATT)
ms._save_attachments(c, 1, [{"filename": "other.bin", "data": b"COMPLETELY_DIFFERENT"}])
check("새 내용은 새 파일 생성", count_files(ATT) == before + 1)

print("=== 4) 공유 안전: 한 메일 첨부행 삭제해도 물리파일 유지·다른 메일 그대로 읽힘 ===")
# 현재 코드는 파일을 삭제하지 않음(행만 삭제) → 공유 파일이 깨지지 않음
shared_path = rows[0]["path"]
c.execute("DELETE FROM mail_attachments WHERE mail_id=1 AND path=?", (shared_path,))  # 메일1의 공유행 삭제
check("물리 파일 여전히 존재(안 지움)", os.path.exists(shared_path))
r2 = c.execute("SELECT id FROM mail_attachments WHERE mail_id=2").fetchone()
check("메일2는 공유파일 그대로 읽힘", ms.get_attachment(c, r2["id"], 85)["data"] == same)

print("=== 5) 소유권 강제(다른 사용자 차단) ===")
check("다른 user_id 는 None", ms.get_attachment(c, r2["id"], 99) is None)

print("=== 6) 파일 기록 실패 → BLOB 폴백(데이터 손실 0) ===")
c2 = make_db()
_orig = ms._write_content_file
ms._write_content_file = lambda p, data: False   # 디스크 실패 흉내
try:
    ms._save_attachments(c2, 1, [{"filename": "diskfail.pdf", "data": b"MUST_NOT_LOSE"}])
finally:
    ms._write_content_file = _orig
rf = c2.execute("SELECT data, path, sha256 FROM mail_attachments").fetchone()
check("파일실패 시 BLOB 로 보존", rf["data"] == b"MUST_NOT_LOSE" and rf["path"] is None)
check("실패해도 sha256 은 기록", bool(rf["sha256"]))
check("BLOB 폴백도 get 으로 읽힘",
      ms.get_attachment(c2, c2.execute("SELECT id FROM mail_attachments").fetchone()["id"], 85)["data"] == b"MUST_NOT_LOSE")

print("=== 7) 기존 첨부(path NULL·data BLOB) = 그대로 읽힘(마이그 전 호환) ===")
c3 = make_db()
c3.execute("INSERT INTO mail_attachments(mail_id,filename,mime,data,path,sha256) VALUES(1,'old.jpg','image/jpeg',?,NULL,NULL)", (b"OLD_BLOB",))
oid = c3.execute("SELECT id FROM mail_attachments WHERE filename='old.jpg'").fetchone()["id"]
check("마이그 전 BLOB 그대로 읽힘", ms.get_attachment(c3, oid, 85)["data"] == b"OLD_BLOB")

print("=== 8) path 있으나 파일 없음 → BLOB 폴백 ===")
c3.execute("INSERT INTO mail_attachments(mail_id,filename,data,path) VALUES(1,'both',?,?)", (b"FALLBACK", "/no/such/x.bin"))
bid = c3.execute("SELECT id FROM mail_attachments WHERE filename='both'").fetchone()["id"]
check("파일 유실 시 BLOB 폴백(안전망)", ms.get_attachment(c3, bid, 85)["data"] == b"FALLBACK")

print("=== 9) 큰 첨부(>12MB) = 메타만(파일·BLOB·sha256 없음) ===")
c4 = make_db()
big = b"x" * (ms._ATT_STORE_MAX + 1)
ms._save_attachments(c4, 1, [{"filename": "big.zip", "data": big}])
rb = c4.execute("SELECT data, path, sha256 FROM mail_attachments").fetchone()
check("상한 초과=파일 없음(path NULL)", rb["path"] is None)
check("상한 초과=BLOB 없음(data NULL)", rb["data"] is None)
check("상한 초과=sha256 없음", rb["sha256"] is None)

print("\n===== 결과: %d PASS / %d FAIL =====" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
