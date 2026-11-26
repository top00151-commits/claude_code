# -*- coding: utf-8 -*-
"""본문 정리 시험 (11-23 대표 「1번 2번 진행해」) — 6개월 지난 본문 압축 · 같은 본문 하나로 · 원래 날짜 · 되돌리기. 빈 임시 DB · 가짜 자료만.
실행: 프로젝트 루트(01_HAIST_WORKS)에서  python _검증/mail_body_pack_test.py"""
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
_db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_bodypack_"), "t.db")
_db.init_db()
from app import mail_store as ms  # noqa: E402
from app import mail_body_pack as mbp  # noqa: E402
from app import mail_body_refill as mbr  # noqa: E402
sys.stdout = _so
# 11-26 「받을 때 바로 · 날짜 상관없이 모두」 스위치를 끄면 11-23 규칙 그대로인지 = 이 시험(켠 쪽은 mail_body_pack_live_test.py)
mbp.LIVE_PACK = False
mbp.PACK_ALL = False

P, F = [], []


def ck(n, ok, extra=""):
    (P if ok else F).append(n)
    print(("  [OK] " if ok else "  [XX] ") + n + ("" if ok else "  " + str(extra)))


with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9101,'t_pk','시험','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9102,'t_pk2','직원','member',1,'x')")


def put(uid, subj, html, days=0, sent_days=None, mid=None):
    with _db.db_session() as c:
        i, _o = ms.store_inbound(c, to_email="t@knknara.co.kr", from_email="a@partner-demo.example", from_name="가짜", subject=subj,
                                 text="글 본문 " + subj, html=html, owner_id=uid, run_ai=False, message_id=mid or ("pk-%s-%d@demo" % (subj, uid)),
                                 sent_at=("" if sent_days is None else "2000-01-01 00:00:00"))
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?) WHERE id=?", ("-%d days" % days, i))
        if sent_days is not None:
            c.execute("UPDATE mail_messages SET sent_at=datetime('now','localtime', ?) WHERE id=?", ("-%d days" % sent_days, i))
    return i


H_OLD = "<div>" + "옛 거래처 메일 표 " * 300 + "</div>"
H_NEW = "<div>" + "새 거래처 메일 " * 300 + "</div>"
H_NOTICE = "<div>" + "전사 공지 같은 본문 " * 300 + "</div>"
a_old = put(9101, "old", H_OLD, days=200)                       # 받은 지 200일 → 6개월 지남
a_new = put(9101, "new", H_NEW, days=10)                        # 새 메일 · 하나뿐 → 그대로
a_imp = put(9101, "imported", H_NEW.replace("새", "가져온"), days=1, sent_days=300)   # 어제 가져왔지만 원래 날짜 300일 전 → 6개월 지남
n1 = put(9101, "notice", H_NOTICE, days=3)                      # 같은 공지 두 사람 → 같은 본문
n2 = put(9102, "notice", H_NOTICE, days=3)
small = put(9101, "small", "<p>짧음</p>", days=400)              # 1KB 안 → 그대로
with _db.db_session() as c:
    c.execute("INSERT INTO mail_messages(user_id, direction, subject, body_text, body_html, is_read) VALUES(9101,'draft','임시','x',?,1)", (H_OLD,))
    c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime','-400 days') WHERE direction='draft'")

pl = mbp.plan(_db.db_session)
ck("셈: 대상 4통(옛 1 · 원래 날짜로 옛 1 · 같은 공지 2)", pl["mails"] == 4 and pl["old_n"] == 2 and pl["dup_n"] == 2, pl)
ck("셈: 같은 본문 하나로 치면 3가지", pl["unique_n"] == 3, pl)
with _db.db_session() as c:
    ck("셈만으로는 안 바뀜", (c.execute("SELECT body_html FROM mail_messages WHERE id=?", (a_old,)).fetchone()[0] or "") == H_OLD)

out = mbp.apply(_db.db_session)
ck("정리: 4통 · 건너뜀 0", out["packed"] == 4 and out["skipped"] == 0, out)
with _db.db_session() as c:
    def row(i):
        return c.execute("SELECT body_html, html_sha, body_text FROM mail_messages WHERE id=?", (i,)).fetchone()
    ck("옛 메일: 칸 비우고 지문 적음", row(a_old)[0] == "" and len(row(a_old)[1]) == 64)
    ck("원래 날짜 300일 전 메일도 정리", row(a_imp)[0] == "" and row(a_imp)[1])
    ck("새 메일(하나뿐)은 그대로", row(a_new)[0] == H_NEW and not row(a_new)[1])
    ck("짧은 본문은 그대로", row(small)[0] == "<p>짧음</p>")
    ck("임시보관함은 그대로", c.execute("SELECT body_html FROM mail_messages WHERE direction='draft'").fetchone()[0] == H_OLD)
    ck("글 본문은 그대로(찾기·미리 보기)", row(a_old)[2] == "글 본문 old")
    ck("같은 공지 두 통 → 보관함 한 벌", row(n1)[1] == row(n2)[1] and c.execute("SELECT COUNT(*) FROM mail_body_store WHERE sha=?", (row(n1)[1],)).fetchone()[0] == 1)
    ck("보관함 3가지 · 압축돼 작아짐", tuple(c.execute("SELECT COUNT(*), SUM(z_len) < SUM(raw_len) FROM mail_body_store").fetchone()) == (3, 1))
    g = ms.get_mail(c, a_old, 9101)
    ck("⭐메일 열면 원래 HTML 그대로(get_mail)", g["body_html"] == H_OLD)
    ck("⭐다른 사람 메일도 자기 것 그대로", ms.get_mail(c, n2, 9102)["body_html"] == H_NOTICE)
    ck("화면 정리(sanitize)도 그대로", "옛 거래처 메일 표" in ms.sanitize_html_for_view(g["body_html"], a_old, []))
    ck("본문 다시 채우기 대상 아님(압축된 메일)", mbr.count(c, 9101)["mails"] == 0)
ck("두 번 정리해도 0통", mbp.apply(_db.db_session)["packed"] == 0)

# 정리 중에 본문이 바뀐 메일은 건너뜀
cnt, meta = mbp._scan(_db.db_session)
ck("남은 대상 없음(다시 셈 0)", mbp.plan(_db.db_session)["mails"] == 0)

# 원래 날짜(Date 머리) 읽기
raw = ("From: a@partner-demo.example\r\nTo: t@knknara.co.kr\r\nSubject: d\r\nDate: Tue, 05 May 2026 09:30:00 +0900\r\n"
       "Message-ID: <date1@demo>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nbody\r\n").encode()
p = ms.parse_raw_email(raw)
ck("Date 머리 → 원래 날짜(서버 시각 글자)", p.get("sent_at", "").startswith("2026-05-0"), p.get("sent_at"))
ck("Date 없거나 틀리면 빈 값", ms._sent_at("엉터리") == "" and ms._sent_at(None) == "")

# 되돌리기
n = mbp.undo(_db.db_session)
with _db.db_session() as c:
    ck("되돌리기 4통", n == 4, n)
    ck("되돌린 뒤 칸에 원래 HTML", tuple(c.execute("SELECT body_html, html_sha FROM mail_messages WHERE id=?", (a_old,)).fetchone()) == (H_OLD, ""))
    ck("되돌린 뒤 같은 공지도 원래대로", c.execute("SELECT body_html FROM mail_messages WHERE id=?", (n2,)).fetchone()[0] == H_NOTICE)
    ck("되돌린 뒤 보관함 비움(쓰는 메일 없음)", c.execute("SELECT COUNT(*) FROM mail_body_store").fetchone()[0] == 0)
print("결과: %d 통과 / %d 실패" % (len(P), len(F)))
