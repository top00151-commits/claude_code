# -*- coding: utf-8 -*-
"""보관함 → 최근 3·6·12개월 받은편지함으로 되돌리기 시험 (11-23) — 빈 임시 DB · 가짜 자료만.
실행: 프로젝트 루트(01_HAIST_WORKS)에서  python _검증/mail_unarchive_recent_test.py"""
import io
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
import app.database as _db  # noqa: E402
_db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_unarc_"), "t.db")
_db.init_db()
from app import mail_store as ms  # noqa: E402
sys.stdout = _so
P, F = [], []


def ck(n, ok, extra=""):
    (P if ok else F).append(n)
    print(("  [OK] " if ok else "  [XX] ") + n + ("" if ok else "  " + str(extra)))


with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9101,'t_ua','시험','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9102,'t_ua2','남','member',1,'x')")


def put(uid, days, arc=1, deleted=0, mid=None):
    with _db.db_session() as c:
        i, _o = ms.store_inbound(c, to_email="t@knknara.co.kr", from_email="a@partner-demo.example", subject="s%d-%d" % (uid, days),
                                 text="가짜", owner_id=uid, run_ai=False, message_id=mid or ("ua-%d-%d-%d@demo" % (uid, days, arc)))
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?), is_archived=?, is_read=1, is_deleted=? WHERE id=?",
                  ("-%d days" % days, arc, deleted, i))
    return i


a20 = put(9101, 20)        # 1개월 안
a70 = put(9101, 70)        # 3개월 안
a150 = put(9101, 150)      # 6개월 안
a300 = put(9101, 300)      # 12개월 안
a500 = put(9101, 500)      # 12개월 넘음
inbox = put(9101, 10, arc=0)
trash = put(9101, 10, deleted=1, mid="ua-trash@demo")
other = put(9102, 10)

with _db.db_session() as c:
    ck("셈: 최근 3개월 = 2통", ms.unarchive_recent(c, 9101, 3, dry=True)[0] == 2)
    ck("셈: 최근 6개월 = 3통", ms.unarchive_recent(c, 9101, 6, dry=True)[0] == 3)
    ck("셈: 최근 12개월 = 4통", ms.unarchive_recent(c, 9101, 12, dry=True)[0] == 4)
    ck("셈만으로는 안 바뀜", c.execute("SELECT is_archived FROM mail_messages WHERE id=?", (a20,)).fetchone()[0] == 1)
    ck("이상한 기간 → 3개월로", ms.unarchive_recent(c, 9101, "99", dry=True)[0] == 2)
    ids, cut = ms.unarchive_recent(c, 9101, 6, dry=False)
    ck("6개월 되돌리기 = 3통(20·70·150일)", sorted(ids) == sorted([a20, a70, a150]), ids)
    g = lambda i: c.execute("SELECT is_archived FROM mail_messages WHERE id=?", (i,)).fetchone()[0]
    ck("300·500일 메일은 보관함 그대로", g(a300) == 1 and g(a500) == 1)
    ck("휴지통 메일 안 건드림", g(trash) == 1)
    ck("남의 메일 안 건드림", g(other) == 1)
    ck("받은편지함 메일 그대로", g(inbox) == 0)
    n = ms.rearchive_ids(c, 9101, [str(x) for x in ids] + [str(other)])
    ck("↺ 되돌리기 = 3통 다시 보관(남의 번호는 무시)", n == 3 and g(a20) == 1 and g(a150) == 1, n)
print("결과: %d 통과 / %d 실패" % (len(P), len(F)))
