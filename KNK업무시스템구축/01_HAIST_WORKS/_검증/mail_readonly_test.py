# -*- coding: utf-8 -*-
"""메일 읽기 전용 조회 검증 (대표 지시 2026-11-09). 운영 DB·운영 메일 무접촉 — 가짜 데이터만.

증명할 것
  ① 읽기 전용 조회를 반복해도 읽음 상태(is_read)와 읽은 시각(read_at)이 바뀌지 않는다
  ② (대조군) mark_read 는 실제로 바꾼다 — 시험이 '변화'를 잡아낼 수 있음을 증명
  ③ 남의 메일·첨부에 접근할 수 없다
  ④ 권한 게이트(대표 본인만) 가 맞게 동작한다
  ⑤ 바깥 이미지·추적 링크가 자동으로 열리지 않게 제거된다
  ⑥ 읽기 전용 라우트에 상태를 바꾸는 호출이 섞여 있지 않다 (+ 심으면 잡히는지)
  ⑦ (회귀) 기존 화면 라우트는 여전히 읽음 처리를 한다 — 대표가 직접 열 때는 그대로
"""
import io
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from app import mail_store as ms  # noqa: E402

PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS]", name)
    else:
        FAIL += 1
        print("  [FAIL]", name, extra)


ME, OTHER = 85, 99


def make_db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE mail_messages(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT, direction TEXT DEFAULT 'in',
      from_email TEXT, from_name TEXT, to_email TEXT, cc TEXT, bcc TEXT, subject TEXT,
      body_text TEXT, body_html TEXT, category TEXT DEFAULT '일반', lang TEXT, summary TEXT,
      is_read INT DEFAULT 0, is_starred INT DEFAULT 0, is_deleted INT DEFAULT 0,
      raw_size INT DEFAULT 0, received_at TEXT, read_at TEXT, deleted_at TEXT,
      is_blocked INT DEFAULT 0, risk_level INT DEFAULT 0, risk_note TEXT);
    CREATE TABLE mail_attachments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INT, filename TEXT, mime TEXT,
      size INT, path TEXT, content_id TEXT, is_inline INT DEFAULT 0, data BLOB,
      sha256 TEXT, created_at TEXT);
    """)
    # 1=내 안읽음 / 2=내 읽음(시각 고정) / 3=남의 메일
    c.execute("INSERT INTO mail_messages(id,user_id,subject,body_text,body_html,is_read,read_at,received_at)"
              " VALUES(1,?,'안읽은 메일','본문A','<p>본문A</p>',0,NULL,'2026-11-09 09:00')", (ME,))
    c.execute("INSERT INTO mail_messages(id,user_id,subject,body_text,is_read,read_at,received_at)"
              " VALUES(2,?,'이미 읽은 메일','본문B',1,'2026-11-01 08:00','2026-11-08 09:00')", (ME,))
    c.execute("INSERT INTO mail_messages(id,user_id,subject,body_text,is_read,read_at,received_at)"
              " VALUES(3,?,'남의 메일','본문C',0,NULL,'2026-11-09 09:00')", (OTHER,))
    c.execute("INSERT INTO mail_attachments(id,mail_id,filename,mime,size,data,is_inline)"
              " VALUES(10,1,'내첨부.pdf','application/pdf',5,?,0)", (b"HELLO",))
    c.execute("INSERT INTO mail_attachments(id,mail_id,filename,mime,size,data,is_inline)"
              " VALUES(11,3,'남의첨부.pdf','application/pdf',5,?,0)", (b"SECRET",))
    c.commit()
    return c


def state(c, mid):
    r = c.execute("SELECT is_read, read_at FROM mail_messages WHERE id=?", (mid,)).fetchone()
    return (r["is_read"], r["read_at"])


print("=== 1) 읽기 전용 조회를 반복해도 읽음 상태·시각이 안 바뀐다 ===")
c = make_db()
before1, before2 = state(c, 1), state(c, 2)
for _ in range(3):
    ms.get_mail(c, 1, ME)
    ms.get_mail(c, 2, ME)
    ms.list_inbox(c, ME)
    ms.list_inbox(c, ME, unread=True)
    ms.list_sent(c, ME)
    ms.list_drafts(c, ME)
    ms.list_trash(c, ME)
    ms.list_attachments(c, 1)
    ms.get_attachment(c, 10, ME)
check("안읽은 메일: is_read·read_at 그대로", state(c, 1) == before1 == (0, None), state(c, 1))
check("읽은 메일: read_at 그대로(덧씌우지 않음)", state(c, 2) == before2 == (1, "2026-11-01 08:00"), state(c, 2))
check("첨부 바이트는 정상적으로 읽힌다", (ms.get_attachment(c, 10, ME) or {}).get("data") == b"HELLO")

print("=== 2) 대조군 — mark_read 는 실제로 바꾼다(시험이 변화를 잡아내는지) ===")
ms.mark_read(c, 1, ME)
after = state(c, 1)
check("mark_read 호출 시 is_read=1 로 바뀜", after[0] == 1, after)
check("mark_read 호출 시 read_at 이 채워짐", bool(after[1]), after)

print("=== 3) 남의 메일·첨부 차단 ===")
c2 = make_db()
check("남의 메일은 get_mail 로 안 보임", ms.get_mail(c2, 3, ME) is None)
check("남의 첨부는 get_attachment 로 안 보임", ms.get_attachment(c2, 11, ME) is None)
check("내 목록에 남의 메일이 안 섞임",
      all(int(r["id"]) != 3 for r in ms.list_inbox(c2, ME)))
check("차단 시도가 남의 메일 상태를 바꾸지 않음", state(c2, 3) == (0, None))

print("=== 4) 권한 게이트 — 대표 본인만 ===")
check("사번 5 통과", ms.ro_allowed({"employee_no": "5", "login_id": "zzz"}))
check("login_id kjr 통과", ms.ro_allowed({"employee_no": "77", "login_id": "KJR"}))
check("다른 직원 차단", not ms.ro_allowed({"employee_no": "77", "login_id": "lee"}))
check("빈 값 차단", not ms.ro_allowed({"employee_no": "", "login_id": ""}))
check("None 차단", not ms.ro_allowed(None))
check("dict 아닌 것 차단", not ms.ro_allowed("5"))

print("=== 5) 바깥 이미지·추적 링크 제거(자동으로 안 열리게) ===")
for html, keep, label in [
    ('<img src="https://track.ex/p.gif?u=1">', False, "원격 추적픽셀"),
    ("<img src='//cdn.ex/a.png'>", False, "프로토콜 생략 원격"),
    ('<td background="https://ex/bg.png">', False, "background 속성"),
    ('<div style="background:url(https://t.ex/x.png)">', False, "CSS 원격 url"),
    ('<img src="cid:logo1">', True, "인라인 cid 보존"),
    ('<img src="/mail/5/att/9">', True, "우리 서버 상대경로 보존"),
]:
    out = ms.strip_remote_refs(html)
    ok = (out == html) if keep else (out != html and "https://" not in out and "//cdn" not in out)
    check("%s" % label, ok, out)

print("=== 6) 읽기 전용 라우트에 상태를 바꾸는 호출이 없다 ===")
MAIN = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
START = "# ─── 🔒 메일 읽기 전용 조회"
END = "# ─── KNK 대용량 첨부"
check("읽기 전용 구역을 찾음", START in MAIN and END in MAIN)
block = MAIN[MAIN.index(START):MAIN.index(END)]
BANNED = ["mark_read", "set_read", "bump_large_download", "hard_delete", "empty_trash",
          "delete_mail", "restore_mail", "set_category", "toggle_star"]

def called_names(src):
    """글자가 아니라 '실제 호출'을 센다 — 주석·설명글에 적힌 이름에 속지 않게(오탐 방지)."""
    import ast
    names = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                names.add(f.attr)
            elif isinstance(f, ast.Name):
                names.add(f.id)
    return names


found = sorted(set(called_names(block)) & set(BANNED))
check("금지 호출 없음(주석 아닌 실제 호출 기준)", not found, found)
check("세션으로만 소유자 판정(요청 user_id 안 믿음)",
      "get_user(req)" in block and "user_id=" not in block.replace("u[\"id\"]", ""))
check("첨부는 소유권 2겹(get_mail → get_attachment)",
      "get_mail(" in block and "get_attachment(" in block)
# 가드가 헛돌지 않는지 — 금지 호출을 심으면 잡혀야 한다
poisoned = block + chr(10) + "_mailbox.mark_read(c, 1, 1)" + chr(10)
check("가드 증명: 금지 호출을 심으면 잡는다", bool(set(called_names(poisoned)) & set(BANNED)))
check("가드 증명: 주석에만 적힌 이름은 안 잡는다",
      not (set(called_names("# mark_read 금지" + chr(10) + "x = 1" + chr(10))) & set(BANNED)))

print("=== 7) (회귀) 기존 화면 라우트는 여전히 읽음 처리한다 ===")
for route in ['@app.get("/mail/{mail_id:int}")', '@app.get("/mail/{mail_id:int}/pane"']:
    i = MAIN.index(route)
    seg = MAIN[i:i + 1400]
    check("화면 라우트 유지: %s" % route[:34], "mark_read" in seg)

print("\n===== 결과: %d PASS / %d FAIL =====" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
