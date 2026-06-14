# -*- coding: utf-8 -*-
"""메일 중복 자동정리 검증 — 진짜 같은 메일만 묶고, 답장 스레드(제목같고 본문다름)는 불가침.
실DB(메모리)로 store_inbound 중복차단 + dedup_inbox 정리 검증."""
import os, sys, io, sqlite3
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import mail_store as ms

ok = True
def chk(n, c):
    global ok; print(("[OK] " if c else "[FAIL] ")+n); ok = ok and bool(c)

con = sqlite3.connect(":memory:"); con.row_factory = sqlite3.Row
con.executescript("""
CREATE TABLE mail_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT, direction TEXT DEFAULT 'in',
 from_email TEXT, from_name TEXT, to_email TEXT, cc TEXT, subject TEXT, body_text TEXT, body_html TEXT,
 category TEXT, lang TEXT, summary TEXT, raw_size INT DEFAULT 0,
 is_read INT DEFAULT 0, is_starred INT DEFAULT 0, is_deleted INT DEFAULT 0,
 received_at TEXT DEFAULT (datetime('now','localtime')), deleted_at TEXT);
CREATE TABLE mail_attachments(id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INT, filename TEXT, mime TEXT,
 size INT, content_id TEXT, is_inline INT, data BLOB);
CREATE TABLE mail_rules(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT, match_type TEXT, pattern TEXT,
 category TEXT, enabled INT DEFAULT 1);
""")
def cnt(uid):
    return con.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND is_deleted=0", (uid,)).fetchone()[0]
def col(mid, c):
    return con.execute("SELECT %s FROM mail_messages WHERE id=?" % c, (mid,)).fetchone()[0]

def store(uid, **kw):
    return ms.store_inbound(con, owner_id=uid, run_ai=False, **kw)

# 1) 같은 Message-ID 두 번 → 새로 안 쌓고 dup_count++ (그룹메일 중복 시나리오)
id1,_ = store(1, to_email="me@k.co", from_email="grp@x", subject="[BIM] 보고서 송부", text="보고서 본문", message_id="<MID-1@x>")
id2,_ = store(1, to_email="me@k.co", from_email="grp@x", subject="[BIM] 보고서 송부", text="보고서 본문", message_id="<MID-1@x>")
chk("같은 Message-ID → 같은 id 반환", id1 == id2 and id1 is not None)
chk("행 1개만 (중복 안 쌓임)", cnt(1) == 1)
chk("dup_count=2", col(id1, "dup_count") == 2)

# 2) 같은 Message-ID 4번째까지 → dup_count=4, 여전히 1통
store(1, to_email="me@k.co", from_email="grp@x", subject="[BIM] 보고서 송부", text="보고서 본문", message_id="<MID-1@x>")
store(1, to_email="me@k.co", from_email="grp@x", subject="[BIM] 보고서 송부", text="보고서 본문", message_id="<MID-1@x>")
chk("4번 와도 1통 · dup_count=4", cnt(1) == 1 and col(id1, "dup_count") == 4)

# 3) ★답장 스레드 불가침: 제목 같고 본문 다름 → 별개로 저장(절대 안 묶임)
ida,_ = store(2, to_email="me@k.co", from_email="b@y", subject="질문 있습니다", text="원본 질문 내용")
idb,_ = store(2, to_email="me@k.co", from_email="b@y", subject="질문 있습니다", text="전혀 다른 답장 내용")
chk("제목같고 본문다름 → 별개 2통(답장 불가침)", ida != idb and idb is not None and cnt(2) == 2)

# 4) Message-ID 없이 내용 완전일치 → 묶임 (폴백 동작)
idp,_ = store(3, to_email="me@k.co", from_email="c@z", subject="공지", text="동일 내용입니다")
idq,_ = store(3, to_email="me@k.co", from_email="c@z", subject="공지", text="동일 내용입니다")
chk("Message-ID 없이 내용 완전일치 → 묶임", idp == idq and cnt(3) == 1)

# 5) dedup_inbox: 과거에 이미 쌓인 중복(레거시·dedup_hash 없음) 정리
#    4통 직접 삽입(하나는 읽음, 하나는 별표) → 1통만 남기고 3통 휴지통, 읽음/별표 보존, dup_count=4
for i in range(4):
    con.execute("INSERT INTO mail_messages(user_id,direction,from_email,subject,body_text,is_read,is_starred) "
                "VALUES(4,'in','dist@x','[전사] 안내','안내문 동일',?,?)",
                (1 if i == 1 else 0, 1 if i == 2 else 0))
removed = ms.dedup_inbox(con, 4)
keep = con.execute("SELECT id,is_read,is_starred,dup_count FROM mail_messages "
                   "WHERE user_id=4 AND is_deleted=0").fetchall()
chk("4중복 → 3정리(휴지통)", removed == 3)
chk("남은 1통", cnt(4) == 1 and len(keep) == 1)
chk("읽음 보존(그룹에 읽음 있었음)", keep[0]["is_read"] == 1)
chk("별표 보존(그룹에 별표 있었음)", keep[0]["is_starred"] == 1)
chk("dup_count=4 기록", keep[0]["dup_count"] == 4)
chk("정리된 3통은 휴지통(is_deleted=1)",
    con.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=4 AND is_deleted=1").fetchone()[0] == 3)

# 6) ★dedup_inbox 도 답장 스레드 불가침: 제목 같고 본문 다른 2통은 정리 0
con.execute("INSERT INTO mail_messages(user_id,direction,from_email,subject,body_text) VALUES(5,'in','d@x','회신','본문 하나')")
con.execute("INSERT INTO mail_messages(user_id,direction,from_email,subject,body_text) VALUES(5,'in','d@x','회신','본문 둘 (다름)')")
removed5 = ms.dedup_inbox(con, 5)
chk("제목같고 본문다름 → dedup_inbox 정리 0(불가침)", removed5 == 0 and cnt(5) == 2)

# 7) dedup_inbox 멱등(다시 돌려도 추가 정리 0)
chk("dedup_inbox 재실행 → 0", ms.dedup_inbox(con, 4) == 0)

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
