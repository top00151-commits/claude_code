# -*- coding: utf-8 -*-
"""사람마다 오래된 메일·광고·알림·스팸함 자동 삭제 시험 (대표 11-28) — 가짜 자료로 만든 임시 DB 만 씀.
· 처음 값 3년·3개월 · 기간 경계(하루 전·후) · 별표 남음 · 보낸·임시보관·예약 남음 · 「끄기」면 안 지움
· 바로 안 지우고 완전 삭제 대기(30일) · 되살리면 원래 자리 · 남의 설정 못 바꿈 · 설정 바꾸면 미리 세기 수가 바뀜
· 하룻밤 상한 · 금지 시간 · 관리 일괄 7년 가능 · 휴지통 대기 띠 「자동 삭제(3년)로 N통」 · 처음 안내 띠
실행: 프로젝트 루트(01_HAIST_WORKS)에서  PYTHONIOENCODING=utf-8 python _검증/mail_auto_delete_test.py"""
import datetime as dt
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

P, F = [], []


def ck(n, ok, extra=""):
    (P if ok else F).append(n)
    print(("  [OK] " if ok else "  [XX] ") + n + ("" if ok else "  " + str(extra)[:400]))


_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_mautodel_"), "knk.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_find as mfind
finally:
    sys.stdout = _so

A, B, C3, ADM = 9821, 9822, 9823, 9824
with _db.db_session() as c:
    for uid, lid, nm, role in ((A, "t_ad_a", "시험갑", "member"), (B, "t_ad_b", "시험을", "member"),
                               (C3, "t_ad_c", "시험병", "member"), (ADM, "t_ad_adm", "시험관리자", "admin")):
        c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (uid, lid, nm, role))
    ms._ensure_security_cols(c)

NOW = dt.datetime(2026, 12, 1, 23, 40)          # 화요일 23:40(금지 시간 아님)
F_ = "%Y-%m-%d %H:%M:%S"


def at(**kw):
    return (NOW - dt.timedelta(**kw)).strftime(F_)


Y3 = ms._minus_months(NOW, 36)                    # 3년 전 바로 그 시각
M3 = ms._minus_months(NOW, 3)


def put(uid, subj, received, *, direction="in", deleted=0, star=0, blocked=0, frm="fake.sender@example.test"):
    with _db.db_session() as c:
        cur = c.execute("INSERT INTO mail_messages(user_id, direction, from_email, to_email, subject, body_text, received_at, "
                        "is_deleted, is_starred, is_blocked) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (uid, direction, frm, "fake@knk-mailtest.com", subj, "가짜 본문", received, deleted, star, blocked))
        return cur.lastrowid


def isd(mid, col="is_deleted"):
    with _db.db_session() as c:
        r = c.execute("SELECT * FROM mail_messages WHERE id=?", (mid,)).fetchone()
        return dict(r).get(col) if r else "없음"


def run(now=NOW, **kw):
    so = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return ms.run_auto_delete(_db.db_session, now=now, **kw)
    finally:
        sys.stdout = so


# 광고·알림 = 📢 칸과 같은 기준(bulk_map) — 시험에서는 가짜 주소 하나를 광고로 봄
AD_ADDR = "fake.news@ads.example.test"
_orig_bulk = mfind.bulk_map
mfind.bulk_map = lambda c, uid: {AD_ADDR: ""} if uid in (A, B, C3) else {}

print("① 처음 값")
with _db.db_session() as c:
    g = ms.get_autodel(c, A)
ck("처음 값 = 3년 · 3개월 · 저장 안 함", g["years"] == 3 and g["ad_months"] == 3 and not g["saved"], g)

print("② 기간 경계 · 별표 · 보낸·임시·예약 · 대기로")
a_before = put(A, "가짜3년하루더지남", (Y3 - dt.timedelta(days=1)).strftime(F_))
a_after = put(A, "가짜3년하루덜지남", (Y3 + dt.timedelta(days=1)).strftime(F_))
a_h_after = put(A, "가짜3년한시간덜지남", (Y3 + dt.timedelta(hours=1)).strftime(F_))
a_star = put(A, "가짜별표4년", at(days=4 * 365), star=1)
a_sent = put(A, "가짜보낸4년", at(days=4 * 365), direction="out")
a_draft = put(A, "가짜임시4년", at(days=4 * 365), direction="draft")
a_sched = put(A, "가짜예약4년", at(days=4 * 365), direction="sched")
a_trash = put(A, "가짜휴지통4년", at(days=4 * 365), deleted=1)
a_arc = put(A, "가짜보관함4년", at(days=4 * 365))
with _db.db_session() as c:
    cols = {r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()}
    if "is_archived" in cols:
        c.execute("UPDATE mail_messages SET is_archived=1 WHERE id=?", (a_arc,))
a_noempty = put(A, "가짜받은시각없음", "")
ad_old = put(A, "가짜광고3개월하루더", (M3 - dt.timedelta(days=1)).strftime(F_), frm=AD_ADDR)
ad_new = put(A, "가짜광고3개월하루덜", (M3 + dt.timedelta(days=1)).strftime(F_), frm=AD_ADDR)
spam_old = put(A, "가짜스팸4개월", at(days=120), blocked=1)
spam_star = put(A, "가짜스팸별표4개월", at(days=120), blocked=1, star=1)
normal_4m = put(A, "가짜보통4개월", at(days=120))
with _db.db_session() as c:
    pv = ms.autodel_preview(c, A, now=NOW)
ck("미리 세기 = 오래된 2(하루 더 지남·보관함) + 광고·스팸 2 · 별표 2 남음", pv["old_n"] == 2 and pv["ad_n"] == 2 and pv["star_n"] == 2, pv)
ck("미리 세기 날짜 = 서버 계산(오늘 + 30일)", pv["until_label"] == ms.purge_date_label(pv["until"]) and pv["days"] == 30, pv)
r = run()
ck("3년 하루 더 지남 → 완전 삭제 대기", isd(a_before) == 2, isd(a_before))
ck("3년 하루 덜 지남 → 그대로", isd(a_after) == 0)
ck("3년 한 시간 덜 지남 → 그대로(기준 하루 어긋나면 잡힘)", isd(a_h_after) == 0)
ck("별표 메일 그대로", isd(a_star) == 0 and isd(spam_star) == 0)
ck("보낸·임시보관·예약 그대로", isd(a_sent) == 0 and isd(a_draft) == 0 and isd(a_sched) == 0)
ck("이미 휴지통인 것은 안 건드림(그대로 휴지통)", isd(a_trash) == 1)
ck("보관함 메일도 대상", isd(a_arc) == 2)
ck("받은 시각 없는 메일은 안 건드림", isd(a_noempty) == 0)
ck("광고·알림 3개월 하루 더 지남 → 대기 · 하루 덜 → 그대로", isd(ad_old) == 2 and isd(ad_new) == 0)
ck("스팸함 4개월 → 대기 · 보통 메일 4개월 → 그대로", isd(spam_old) == 2 and isd(normal_4m) == 0)
ck("바로 지우지 않음(줄 남음) · 누른 사람 NULL · 까닭", isd(a_before, "purge_by") is None and isd(a_before, "purge_how") == "auto_old_3y"
   and isd(ad_old, "purge_how") == "auto_ad_3m", (isd(a_before, "purge_how"), isd(ad_old, "purge_how")))
with _db.db_session() as c:
    lg = [tuple(x) for x in c.execute("SELECT action, n, actor_id, note FROM mail_purge_log WHERE user_id=? ORDER BY id", (A,)).fetchall()]
ck("이력 = 「자동 삭제 3년」 2통 · 광고·스팸 2통 · 시스템", ("auto_old_3y", 2, None, "자동 삭제 3년") in lg
   and any(x[0] == "auto_ad_3m" and x[1] == 2 and x[2] is None for x in lg), lg)
r2 = run()
ck("다시 돌려도 더 안 옮김(이미 대기)", r2["n"] == 0, r2)

print("③ 되살리면 원래 자리 · 휴지통 대기 띠")
from starlette.testclient import TestClient  # noqa: E402
_who = {"u": None}


def as_(uid):
    _who["u"] = {"id": uid, "role": "admin" if uid == ADM else "member", "name": "시험", "login_id": "t_ad_%d" % uid, "lang": "ko"}


m.get_user = lambda req: _who["u"]
k = TestClient(m.app, base_url="http://127.0.0.1:5096", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
as_(A)
tp = k.get("/mail/trash").text
ck("휴지통 대기 띠 = 「자동 삭제(3년)로 2통」 · 광고·스팸 따로", "자동 삭제(3년)로 2통" in tp and "자동 삭제(광고·알림·스팸 3개월)로 2통" in tp, "")
rr = k.post("/mail/trash/pending/restore", data={"ids": str(a_before)})
if rr.status_code != 200 or not rr.json().get("ok"):
    with _db.db_session() as c:
        ms.restore_pending(c, A, [a_before])
ck("되살리면 받은편지함(원래 자리)", isd(a_before) == 0 and isd(a_before, "deleted_at") is None, (rr.status_code, rr.text[:120]))

print("④ 끄기 · 설정 바꾸면 미리 세기 수가 바뀜 · 남의 설정")
b_old = put(B, "가짜을2년반", at(days=900))
b_ad = put(B, "가짜을광고7개월", at(days=210), frm=AD_ADDR)
as_(B)
j = k.get("/mail/autodel").json()
ck("미리 세기(처음 값 3년) = 오래된 0 · 광고 1", j.get("ok") and j["old_n"] == 0 and j["ad_n"] == 1, j)
j2 = k.get("/mail/autodel", params={"years": "2", "ad_months": "6"}).json()
ck("2년·6개월로 고르면 = 오래된 1 · 광고 1(저장 안 함)", j2["old_n"] == 1 and j2["ad_n"] == 1, j2)
with _db.db_session() as c:
    ck("고르기만 하면 저장 안 됨", not ms.get_autodel(c, B)["saved"])
bad = k.get("/mail/autodel", params={"years": "9"})
ck("없는 값 → 400", bad.status_code == 400, bad.status_code)
s = k.post("/mail/autodel", data={"years": "0", "ad_months": "0", "user_id": str(C3)}).json()
ck("끄기 저장 → 오늘 밤 0통", s.get("ok") and s["n"] == 0 and s["years"] == 0, s)
with _db.db_session() as c:
    ck("남의 번호를 보내도 내 설정만 바뀜(병 = 처음 값 그대로)", ms.get_autodel(c, C3)["saved"] is False and ms.get_autodel(c, B)["years"] == 0)
run()
ck("끄기면 안 지움(2년 반 · 광고 7개월 그대로)", isd(b_old) == 0 and isd(b_ad) == 0)
k.post("/mail/autodel", data={"years": "2", "ad_months": "6"})
run()
ck("2년·6개월로 저장 → 그날 밤 둘 다 대기", isd(b_old) == 2 and isd(b_ad) == 2, (isd(b_old), isd(b_ad)))
with _db.db_session() as c:
    ck("까닭 = 「자동 삭제 2년」", c.execute("SELECT COUNT(*) FROM mail_purge_log WHERE user_id=? AND note='자동 삭제 2년'", (B,)).fetchone()[0] == 1)

print("⑤ 하룻밤 상한 · 금지 시간")
cs = [put(C3, "가짜병오래된%d" % i, at(days=5 * 365 + i)) for i in range(5)]
for nm, qt in (("평일 출근 09:00", dt.datetime(2026, 12, 2, 9, 0)), ("월 NAS 03:00", dt.datetime(2026, 11, 30, 3, 0))):
    rq = run(now=qt)
    ck("금지 시간 안 돎 — " + nm, rq["skip"] and all(isd(x) == 0 for x in cs), rq)
r3 = run(max_per_user=2)
ck("상한 2 → 2통만 · 상한 걸림 1명", sum(1 for x in cs if isd(x) == 2) == 2 and r3["capped"] >= 1, r3)
with _db.db_session() as c:
    note = c.execute("SELECT note FROM mail_purge_log WHERE user_id=? ORDER BY id DESC LIMIT 1", (C3,)).fetchone()[0]
ck("이력에 「다음 밤에 이어서」", "다음 밤에 이어서" in note, note)
run(max_per_user=2)
run(max_per_user=2)
ck("다음 밤에 이어서 모두", all(isd(x) == 2 for x in cs))
with _db.db_session() as c:
    pvc = ms.autodel_preview(c, C3, now=NOW)
ck("미리 세기 상한 표시 재료(over·cap)", "over" in pvc and pvc["cap"] == ms.AUTODEL_MAX_PER_USER, pvc)

print("⑥ 관리 일괄 7년 · 화면")
as_(ADM)
old8 = put(ADM, "가짜관리8년", at(days=8 * 365))
old6 = put(ADM, "가짜관리6년", at(days=6 * 365))
pv7 = k.post("/admin/mail-purge/preview", data={"months": "84"}).json()
ck("관리 일괄 7년(84개월) = 8년 것만", pv7.get("count") == 1, pv7)
pv99 = k.post("/admin/mail-purge/preview", data={"months": "999"}).json()
ck("7년 넘는 값은 7년으로 막음", pv99.get("count") == 1 and pv99.get("before") == pv7.get("before"), pv99)
ap = k.get("/admin/mail-purge").text
ck("관리 화면 고르기 = 4·5·6·7년", all(('value="%d"' % v) in ap for v in (48, 60, 72, 84)))
as_(C3)
tt = k.get("/mail/tools").text
ck("설정·정리 화면 = 자동 삭제 칸 · 고르기 1~5년·끄기 · 3·6개월·끄기 · 처음 값 3년 선택",
   'id="autodel"' in tt and 'id="mtAdY"' in tt and '<option value="3" selected>3년</option>' in tt
   and '<option value="3" selected>3개월</option>' in tt and ">끄기<" in tt and "별표 메일" in tt, "")
ib = k.get("/mail/inbox").text
ck("처음 한 번 안내 띠 = 「3년으로 설정돼 있습니다 · 바꾸기」 · ✕ 닫기", "mbxAutodelNote" in ib and "3년</b>으로 설정돼 있습니다" in ib and "✕ 닫기" in ib, "")
k.post("/mail/autodel", data={"seen": "1"})
ib2 = k.get("/mail/inbox").text
ck("닫은 뒤엔 안내 띠 안 나옴 · 설정은 처음 값 그대로", 'id="mbxAutodelNote"' not in ib2)
with _db.db_session() as c:
    gg = ms.get_autodel(c, C3)
ck("닫기만 하면 값은 그대로(3년)", gg["years"] == 3 and gg["seen"], gg)

print("⑦ 밤 23:30 틀 순서")
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
tick = src[src.index("def _mail_vacuum_tick"):src.index("def _start_mail_vacuum_scheduler")]
ck("순서 = 자동 삭제 → 대기 정리 → 안 쓰는 첨부", "run_auto_delete" in tick and
   tick.index("run_auto_delete") < tick.index("purge_expired_pending") < tick.index("purge_orphan_att_files"))
st = open(os.path.join(ROOT, "app", "mail_store.py"), encoding="utf-8").read()
body = st[st.index("def run_auto_delete"):st.index("def pending_auto_breakdown")]
ck("자동 삭제 함수에 DELETE 없음", "DELETE FROM" not in body)

mfind.bulk_map = _orig_bulk
print("\n결과: %d/%d" % (len(P), len(P) + len(F)))
sys.exit(1 if F else 0)
