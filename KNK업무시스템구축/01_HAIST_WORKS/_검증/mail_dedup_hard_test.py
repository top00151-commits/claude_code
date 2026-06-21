# -*- coding: utf-8 -*-
"""과거 중복정리 자동화 검증 (대표 지시 2026-06-21 "같은 메일은 하나만·용량 최대한 줄이기").
dedup_inbox(hard=True) = 영구삭제(첨부 포함·원본 1통/읽음/별표 보존), hard=False = 휴지통(기존).
실 DB 무사용 — 인메모리 SQLite. 의존 최소(mail_store 의 dedup_inbox·_dedup_hash 만)."""
import os
import sys
import sqlite3

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
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}")


def make_db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE mail_messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, direction TEXT,
        from_email TEXT, from_name TEXT, to_email TEXT, cc TEXT, subject TEXT,
        body_text TEXT, body_html TEXT, category TEXT, lang TEXT, summary TEXT,
        raw_size INTEGER, is_read INTEGER DEFAULT 0, is_starred INTEGER DEFAULT 0,
        is_deleted INTEGER DEFAULT 0, deleted_at TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("""CREATE TABLE mail_attachments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INTEGER, filename TEXT,
        mime TEXT, size INTEGER, content_id TEXT, inline INTEGER, data BLOB)""")
    ms._DEDUP_COLS_OK = False           # 프로세스 캐시 초기화(인메모리마다 새 컬럼)
    ms._ensure_dedup_cols(c)            # dedup_hash·dup_count 컬럼 보장
    return c


def add_mail(c, uid, frm, subj, body, mid="", read=0, star=0, deleted=0, n_att=0, backfill_null=False):
    dh = "" if backfill_null else ms._dedup_hash(mid, frm, subj, body)
    cur = c.execute(
        "INSERT INTO mail_messages(user_id,direction,from_email,subject,body_text,"
        "is_read,is_starred,is_deleted,dedup_hash,dup_count) VALUES(?,?,?,?,?,?,?,?,?,1)",
        (uid, "in", frm, subj, body, read, star, deleted, dh))
    mid_row = cur.lastrowid
    for i in range(n_att):
        c.execute("INSERT INTO mail_attachments(mail_id,filename,mime,size,data) VALUES(?,?,?,?,?)",
                  (mid_row, f"a{i}.pdf", "application/pdf", 1000, b"x" * 1000))
    return mid_row


def cnt(c, sql, *a):
    return c.execute("SELECT COUNT(*) FROM " + sql, a).fetchone()[0]


print("=== 1) hard=True 영구삭제: 같은 메일 3통 → 1통만, 첨부까지 삭제 ===")
c = make_db()
add_mail(c, 1, "spam@x.com", "광고", "본문A", mid="<m1@x>", n_att=1)
add_mail(c, 1, "spam@x.com", "광고", "본문A", mid="<m1@x>", n_att=1)
add_mail(c, 1, "spam@x.com", "광고", "본문A", mid="<m1@x>", n_att=1)
removed = ms.dedup_inbox(c, 1, hard=True)
check("정리 통수 = 2", removed == 2)
check("메일 행 1통만 남음(영구삭제)", cnt(c, "mail_messages WHERE user_id=1") == 1)
check("휴지통(is_deleted=1) 0건 — 휴지통 안 거침", cnt(c, "mail_messages WHERE is_deleted=1") == 0)
check("첨부도 1개만 남음(중복 사본 첨부 영구삭제)", cnt(c, "mail_attachments") == 1)
row = c.execute("SELECT dup_count FROM mail_messages WHERE user_id=1").fetchone()
check("남은 1통에 dup_count=3 기록", row["dup_count"] == 3)

print("=== 2) 읽음/별표 승계: 그룹에 하나라도 읽음·별표면 남은 1통에 보존 ===")
c = make_db()
a = add_mail(c, 1, "a@x.com", "제목", "동일본문", mid="<m2@x>", read=0, star=0)
add_mail(c, 1, "a@x.com", "제목", "동일본문", mid="<m2@x>", read=1, star=0)   # 읽음
add_mail(c, 1, "a@x.com", "제목", "동일본문", mid="<m2@x>", read=0, star=1)   # 별표
ms.dedup_inbox(c, 1, hard=True)
kept = c.execute("SELECT id,is_read,is_starred FROM mail_messages WHERE user_id=1").fetchone()
check("남은 통수 1", cnt(c, "mail_messages WHERE user_id=1") == 1)
check("남은 1통 읽음 보존(is_read=1)", kept["is_read"] == 1)
check("남은 1통 별표 보존(is_starred=1)", kept["is_starred"] == 1)
check("남은 것은 원본(가장 빠른 id)", kept["id"] == a)

print("=== 3) hard=False(수동·기본): 휴지통으로만, 행은 남음(복구 가능) ===")
c = make_db()
add_mail(c, 1, "a@x.com", "제목", "본문Z", mid="<m3@x>", n_att=1)
add_mail(c, 1, "a@x.com", "제목", "본문Z", mid="<m3@x>", n_att=1)
removed = ms.dedup_inbox(c, 1, hard=False)
check("정리 통수 = 1", removed == 1)
check("행은 2개 다 남음(영구삭제 아님)", cnt(c, "mail_messages WHERE user_id=1") == 2)
check("1통이 휴지통(is_deleted=1)", cnt(c, "mail_messages WHERE is_deleted=1") == 1)
check("첨부도 그대로 남음(소프트삭제라 BLOB 보존)", cnt(c, "mail_attachments") == 2)

print("=== 4) 답장 스레드 불가침: 제목 같고 본문 다르면 절대 안 묶임 ===")
c = make_db()
add_mail(c, 1, "a@x.com", "RE: 견적", "처음 문의드립니다", mid="")
add_mail(c, 1, "a@x.com", "RE: 견적", "답변드립니다 감사합니다", mid="")
removed = ms.dedup_inbox(c, 1, hard=True)
check("정리 0건(본문 달라 해시 다름)", removed == 0)
check("두 통 모두 보존", cnt(c, "mail_messages WHERE user_id=1") == 2)

print("=== 5) 사용자 격리: 다른 user_id 의 같은 메일은 각자 1통(안 건드림) ===")
c = make_db()
add_mail(c, 1, "a@x.com", "공지", "동일", mid="<m5@x>")
add_mail(c, 1, "a@x.com", "공지", "동일", mid="<m5@x>")
add_mail(c, 2, "a@x.com", "공지", "동일", mid="<m5@x>")   # 다른 사용자
ms.dedup_inbox(c, 1, hard=True)
check("user1 은 1통으로 정리", cnt(c, "mail_messages WHERE user_id=1") == 1)
check("user2 는 그대로 1통(영향 없음)", cnt(c, "mail_messages WHERE user_id=2") == 1)

print("=== 6) 과거 dedup_hash NULL 백필 후 정리(도입 전 메일) ===")
c = make_db()
add_mail(c, 1, "a@x.com", "옛메일", "같은본문", backfill_null=True)
add_mail(c, 1, "a@x.com", "옛메일", "같은본문", backfill_null=True)
removed = ms.dedup_inbox(c, 1, hard=True)
check("백필 후 중복 1건 영구삭제", removed == 1)
check("1통만 남음", cnt(c, "mail_messages WHERE user_id=1") == 1)

print("=== 7) _dedup_hash 규칙(신규 dedup 무영향 확인) ===")
check("같은 Message-ID → 같은 해시(본문 달라도)",
      ms._dedup_hash("<id@x>", "a@x", "제목1", "본문1") == ms._dedup_hash("<id@x>", "b@y", "제목2", "본문2"))
check("Message-ID 없고 본문 다르면 → 다른 해시(답장 안전)",
      ms._dedup_hash("", "a@x", "제목", "본문1") != ms._dedup_hash("", "a@x", "제목", "본문2"))
check("Message-ID 없고 보낸이+제목+본문 같으면 → 같은 해시",
      ms._dedup_hash("", "a@x", "제목", "본문") == ms._dedup_hash("", "a@x", "제목", "본문"))

print(f"\n===== 결과: {PASS} PASS / {FAIL} FAIL =====")
sys.exit(0 if FAIL == 0 else 1)
