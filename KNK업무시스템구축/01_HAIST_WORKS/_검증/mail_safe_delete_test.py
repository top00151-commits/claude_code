# -*- coding: utf-8 -*-
"""메일 삭제 = 30일 보관 후 시험 (대표 11-28 「삭제 점검 3가지 고쳐」 · 스킬 knk-safe-delete) — 가짜 자료로 만든 임시 DB 만 씀.
① 휴지통 한 통 완전 삭제 ② 휴지통 비우기 ③ 관리 「오래된 받은 메일 일괄 완전 삭제」 → 바로 지우지 않고 완전 삭제 대기(is_deleted=2 · 30일)
· 휴지통·목록·검색·세기에서 빠짐 · DB 줄·첨부 남음 · 되살리기 · 남의 메일 거절 · 권한 · 밤 정리(29일 남음 / 31일 지움 · 쓰는 곳 있으면 남김 · 금지 시간 안 돎)
실행: 프로젝트 루트(01_HAIST_WORKS)에서  PYTHONIOENCODING=utf-8 python _검증/mail_safe_delete_test.py"""
import datetime as dt
import io
import os
import re
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
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_msafedel_"), "knk.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
finally:
    sys.stdout = _so

A, B, ADM, MEM = 9801, 9802, 9803, 9804
with _db.db_session() as c:
    for uid, lid, nm, role in ((A, "t_sd_a", "시험갑", "member"), (B, "t_sd_b", "시험을", "member"),
                               (ADM, "t_sd_adm", "시험관리자", "admin"), (MEM, "t_sd_mem", "시험직원", "member")):
        c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (uid, lid, nm, role))
    ms._ensure_security_cols(c)


def put(uid, subj, *, deleted=0, days_ago=1, direction="in", att=True):
    with _db.db_session() as c:
        ra = c.execute("SELECT datetime('now','localtime', ?)", ("-%d days" % days_ago,)).fetchone()[0]
        cur = c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, "
                        "received_at, is_deleted, deleted_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (uid, direction, "fake.sender@example.test", "가짜 보낸이", "fake@knk-mailtest.com", subj,
                         "가짜 본문 " + subj, ra, deleted, ra if deleted else None))
        mid = cur.lastrowid
        if att:
            c.execute("INSERT INTO mail_attachments(mail_id, filename, mime, size, data, sha256) VALUES(?,?,?,?,?,?)",
                      (mid, "가짜첨부_%d.txt" % mid, "text/plain", 4, b"fake", "f" * 64))
        return mid


def row(mid):
    with _db.db_session() as c:
        r = c.execute("SELECT * FROM mail_messages WHERE id=?", (mid,)).fetchone()
        return dict(r) if r else None


def isd(mid, col="is_deleted"):
    """그 칸 값 · 줄이 없으면 「없음」(나쁜 판에서 시험이 멈추지 않고 [XX] 로 잡히게)."""
    r = row(mid)
    return r.get(col) if r else "없음"


def att_n(mid):
    with _db.db_session() as c:
        return c.execute("SELECT COUNT(*) FROM mail_attachments WHERE mail_id=?", (mid,)).fetchone()[0]


from starlette.testclient import TestClient  # noqa: E402
_who = {"u": None}


def as_(uid):
    role = {ADM: "admin"}.get(uid, "member")
    _who["u"] = {"id": uid, "role": role, "name": "시험", "login_id": "t_sd_%d" % uid, "lang": "ko"}


m.get_user = lambda req: _who["u"]
k = TestClient(m.app, base_url="http://127.0.0.1:5096", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
TODAY30 = (dt.date.today() + dt.timedelta(days=30))
LABEL30 = "%d월 %d일" % (TODAY30.month, TODAY30.day)


def in_trash_page(subj):
    return subj in k.get("/mail/trash").text


def in_search(subj, mid):
    """검색 결과 줄(data-mail-id)에 그 메일이 있나 — 화면에 검색어가 다시 찍히므로 글자로는 안 봄."""
    t = k.get("/mail/inbox", params={"q": subj}).text
    return ('data-mail-id="%d"' % mid) in t


print("① 휴지통 한 통 완전 삭제")
as_(A)
inbox1 = put(A, "가짜받은편지함메일1")
r = k.post("/mail/%d/purge" % inbox1)
ck("휴지통에 없는 메일 → 거절(400)", r.status_code == 400 and not r.json().get("ok"), (r.status_code, r.text[:200]))
ck("거절한 메일은 그대로(받은편지함 · 줄·첨부)", isd(inbox1) == 0 and att_n(inbox1) == 1, row(inbox1))
ck("거절한 메일은 검색에 그대로 보임", in_search("가짜받은편지함메일1", inbox1))

t1 = put(A, "가짜휴지통메일1", deleted=1)
ck("(준비) 휴지통 화면에 보임", in_trash_page("가짜휴지통메일1"))
with _db.db_session() as c:
    tn0 = ms.count_trash(c, A)
as_(B)
r = k.post("/mail/%d/purge" % t1)
ck("남의 메일 → 404 · 그대로", r.status_code == 404 and isd(t1) == 1, (r.status_code, isd(t1)))
as_(A)
r = k.post("/mail/%d/purge" % t1)
j = r.json()
ck("휴지통 메일 → 받음(200 · ok)", r.status_code == 200 and j.get("ok") and j.get("count") == 1, j)
ck("안내문 날짜 = 오늘 + 30일", (j.get("until") or "")[:10] == TODAY30.isoformat() and j.get("until_label") == LABEL30, (j.get("until"), LABEL30))
rw = row(t1)
ck("DB 줄 남음 · is_deleted=2(완전 삭제 대기) · 지울 날 적힘", rw and rw["is_deleted"] == 2 and rw["purge_at"][:10] == TODAY30.isoformat()
   and rw["purge_by"] == A and rw["purge_how"] == "trash_one", rw)
ck("첨부 줄 남음", att_n(t1) == 1)
ck("휴지통 화면에서 빠짐", not in_trash_page("가짜휴지통메일1"))
with _db.db_session() as c:
    ck("휴지통 세기에서 빠짐", ms.count_trash(c, A) == tn0 - 1, (ms.count_trash(c, A), tn0))
    ck("휴지통 목록 함수에서 빠짐", all(x["id"] != t1 for x in ms.list_trash(c, A)))
    ck("메일 열기(get_mail) = 없음", ms.get_mail(c, t1, A) is None)
ck("(준비) 받은편지함 메일은 검색 결과 줄에 보임", in_search("가짜받은편지함메일1", inbox1))
ck("검색에서 빠짐", not in_search("가짜휴지통메일1", t1))
r = k.get("/mail/%d" % t1)
ck("메일 주소로 열어도 안 보임", r.status_code in (302, 303, 404) or "가짜휴지통메일1" not in r.text, r.status_code)
r = k.post("/mail/%d/purge" % t1)
ck("이미 대기인 것 다시 → 404", r.status_code == 404, r.status_code)
r = k.post("/mail/%d/restore" % t1)
ck("휴지통 「복원」으로는 대기 메일이 안 살아남(되살리기 자리로만)", not r.json().get("ok") and isd(t1) == 2, r.text[:100])

print("② 되살리기")
pg = k.get("/mail/trash/pending").json()
ck("대기 목록에 보임 · 지울 날 글", pg.get("ok") and pg["count"] == 1 and pg["rows"][0]["id"] == t1 and pg["rows"][0]["until_label"] == LABEL30, pg)
tp = k.get("/mail/trash").text
ck("휴지통 화면 아래 「완전 삭제 대기 1통」 · 되살리기 단추", "완전 삭제 대기" in tp and "mbxPendN" in tp and "모두 되살리기" in tp, "")
as_(B)
ck("남의 대기 목록은 안 보임", k.get("/mail/trash/pending").json()["count"] == 0)
r = k.post("/mail/trash/pending/restore", data={"ids": str(t1)})
ck("남의 메일 되살리기 → 404 · 그대로", r.status_code == 404 and isd(t1) == 2, r.status_code)
as_(A)
r = k.post("/mail/trash/pending/restore", data={"ids": str(t1)})
ck("되살리기 → 원래 자리 = 휴지통(is_deleted=1 · 지울 날 지움)", r.json().get("ok") and isd(t1) == 1 and isd(t1, "purge_at") == "", row(t1))
ck("되살린 메일 휴지통 화면에 다시 보임", in_trash_page("가짜휴지통메일1"))
with _db.db_session() as c:
    logs = [tuple(x) for x in c.execute("SELECT action, n, actor_id FROM mail_purge_log WHERE user_id=? ORDER BY id", (A,)).fetchall()]
ck("이력 = 누가·무엇·몇 통(trash_one 1 · restore 1)", logs[:2] == [("trash_one", 1, A), ("restore", 1, A)], logs)

print("③ 휴지통 비우기")
early = put(A, "가짜먼저대기메일", deleted=1)
k.post("/mail/%d/purge" % early)
e1, e2 = put(A, "가짜비우기메일1", deleted=1), put(A, "가짜비우기메일2", deleted=1)
keep_in = put(A, "가짜비우기남는받은메일")
r = k.post("/mail/trash/empty")
j = r.json()
ck("비우기 → 휴지통 3통(t1·e1·e2) 대기 · 안내 날짜 +30", j.get("ok") and j["count"] == 3 and j["until_label"] == LABEL30 and j.get("batch"), j)
ck("비운 메일 줄·첨부 남음", all(isd(x) == 2 and att_n(x) == 1 for x in (t1, e1, e2)))
ck("받은편지함 메일은 그대로", isd(keep_in) == 0)
with _db.db_session() as c:
    ck("휴지통 0통", ms.count_trash(c, A) == 0, ms.count_trash(c, A))
ck("휴지통 화면에서 빠짐", not in_trash_page("가짜비우기메일1"))
r = k.post("/mail/trash/pending/restore", data={"batch": j["batch"]})
ck("결과 창 되살리기 = 방금 비운 3통만(먼저 대기한 1통은 그대로)", r.json().get("count") == 3 and isd(early) == 2
   and all(isd(x) == 1 for x in (t1, e1, e2)), (r.text[:120], isd(early)))
r = k.post("/mail/trash/pending/restore", data={"batch": "가짜|없는묶음"})
ck("없는 묶음 → 404", r.status_code == 404)
as_(B)
r = k.post("/mail/trash/empty")
ck("남(을)이 비우기 → 을의 휴지통만(갑 메일 그대로)", r.json()["count"] == 0 and isd(e1) == 1, r.text[:120])
as_(A)

print("④ 관리 「오래된 받은 메일 일괄 완전 삭제」")
old1, old2 = put(ADM, "가짜오래된메일1", days_ago=400), put(ADM, "가짜오래된메일2", days_ago=500, deleted=1)
new1 = put(ADM, "가짜최근메일1", days_ago=3)
oth = put(A, "가짜남의오래된메일", days_ago=600)
as_(MEM)
r1 = k.post("/admin/mail-purge/preview", data={"months": "12"})
r2 = k.post("/admin/mail-purge/run", data={"months": "12"})
ck("직원 → 미리보기·실행 403", r1.status_code == 403 and r2.status_code == 403, (r1.status_code, r2.status_code))
ck("직원 → 관리 화면 못 봄", k.get("/admin/mail-purge").status_code in (302, 303))
ck("직원이 눌러도 그대로", isd(old1) == 0)
as_(ADM)
pv = k.post("/admin/mail-purge/preview", data={"months": "12"}).json()
ck("미리보기 = 2통(받은편지함 1 + 휴지통 1) · 지울 날 +30", pv.get("count") == 2 and pv.get("until_label") == LABEL30, pv)
ap = k.get("/admin/mail-purge").text
ck("관리 화면 = 안내문 창(mailPurgeAsk) · 옛 「되돌릴 수 없습니다」 confirm 없음",
   "mailPurgeAsk" in ap and "되돌릴 수 없습니다" not in ap and "30일 보관" in ap, "")
j = k.post("/admin/mail-purge/run", data={"months": "12"}).json()
ck("실행 → 2통 대기 · 안내 날짜 +30", j.get("ok") and j["count"] == 2 and j["until_label"] == LABEL30, j)
ck("오래된 메일 줄·첨부 남음 · 대기", all(isd(x) == 2 and att_n(x) == 1 and isd(x, "purge_how") == "old_bulk" for x in (old1, old2)))
ck("최근 메일 그대로", isd(new1) == 0)
ck("남(갑)의 오래된 메일 그대로(관리자 본인 메일함만)", isd(oth) == 0)
ck("다시 미리보기 = 0통(대기는 다시 안 셈)", k.post("/admin/mail-purge/preview", data={"months": "12"}).json()["count"] == 0)
ck("(준비) 최근 메일은 검색 결과 줄에 보임", in_search("가짜최근메일1", new1))
ck("검색에서 빠짐", not in_search("가짜오래된메일1", old1))
r = k.post("/mail/trash/pending/restore", data={"batch": j["batch"]})
ck("되살리기 = 원래 자리(받은편지함에서 온 것 → 받은편지함 · 휴지통에서 온 것 → 휴지통)",
   r.json().get("count") == 2 and isd(old1) == 0 and isd(old1, "deleted_at") is None and isd(old2) == 1, (r.text[:100], isd(old1), isd(old2)))
ck("되살린 받은 메일은 검색에 다시 보임", in_search("가짜오래된메일1", old1))
j = k.post("/admin/mail-purge/run", data={"months": "12"}).json()
ck("(다시) 실행 → 2통 대기", j.get("count") == 2 and isd(old1) == 2 and isd(old2) == 2, j)

print("④-2 많은 통은 나눠 저장(한 번에 1통씩으로 시험)")
ch = [put(B, "가짜나눔%d" % i, deleted=1) for i in range(5)]
rr = ms.mark_pending_run(_db.db_session, B, "is_deleted=1", (), "trash_empty", B, chunk=1)
ck("나눠도 5통 모두 대기 · 묶음 열쇠 하나", rr["n"] == 5 and all(isd(x) == 2 for x in ch) and rr["batch"], rr)
with _db.db_session() as c:
    ck("이력은 한 줄(5통)", c.execute("SELECT n FROM mail_purge_log WHERE user_id=? AND action='trash_empty' ORDER BY id DESC LIMIT 1", (B,)).fetchone()[0] == 5)
n = ms.restore_pending_run(_db.db_session, B, None, rr["batch"], chunk=2)
ck("나눠 되살리기 5통 → 휴지통", n == 5 and all(isd(x) == 1 for x in ch), n)
with _db.db_session() as c:
    c.execute("DELETE FROM mail_messages WHERE user_id=? AND subject LIKE '가짜나눔%'", (B,))

print("⑤ 밤 정리 — 30일 지난 것만 지움 · 쓰는 곳 있으면 남김 · 금지 시간 안 돎")
NOW = dt.datetime(2026, 12, 30, 23, 30, 0)   # 수요일 23:30
d31 = (NOW - dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")    # 31일 전에 누름 → 어제 지울 날
d29 = (NOW + dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")    # 29일 전에 누름 → 내일 지울 날
x31, x29, xuse, xdlg = (put(A, "가짜31일", deleted=1), put(A, "가짜29일", deleted=1),
                        put(A, "가짜답기다림연결", deleted=1), put(A, "가짜맡기기연결", deleted=1))
sent = put(A, "가짜보낸메일", direction="out", att=False)
with _db.db_session() as c:
    for x in (x31, x29, xuse, xdlg):
        ms.hard_delete_mail(c, x, A)
    c.execute("UPDATE mail_messages SET purge_at=? WHERE id IN (?,?,?)", (d31, x31, xuse, xdlg))
    c.execute("UPDATE mail_messages SET purge_at=? WHERE id=?", (d29, x29))
    from app import mail_work as _mw
    _mw.ensure(c) if hasattr(_mw, "ensure") else None
    cols = {r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()}
    if "wait_reply_id" not in cols:
        c.execute("ALTER TABLE mail_messages ADD COLUMN wait_reply_id INTEGER")
        c.execute("ALTER TABLE mail_messages ADD COLUMN wait_state TEXT")
    c.execute("UPDATE mail_messages SET wait_state='replied', wait_reply_id=? WHERE id=?", (xuse, sent))
    from app import mail_delegate as _md
    _md.ensure(c)
    c.execute("INSERT INTO mail_delegations(mail_id, owner_id, ref, state) VALUES(?,?,?, 'working')", (xdlg, A, "f" * 32))
for qn, qt in (("월요일 03:00(NAS 백업)", dt.datetime(2026, 12, 28, 3, 0)), ("평일 09:00(출근)", dt.datetime(2026, 12, 30, 9, 0)),
               ("토요일 09:10(출근 시간 · 주말도)", dt.datetime(2026, 12, 26, 9, 10))):
    out = ms.purge_expired_pending(_db.db_session, now=qt)
    ck("금지 시간 %s → 안 돎 · 그대로" % qn, out["skip"] and out["deleted"] == 0 and row(x31) is not None, out)
with _db.db_session() as c:   # 앞 단계에서 대기로 둔 것 중 지울 날이 NOW 전인 것(early·old1·old2)도 함께 지워져야 맞음
    due = [r[0] for r in c.execute("SELECT id FROM mail_messages WHERE is_deleted=2 AND purge_at<=?", (NOW.strftime("%Y-%m-%d %H:%M:%S"),)).fetchall()]
    due_go = [x for x in due if x not in (xuse, xdlg)]
out = ms.purge_expired_pending(_db.db_session, now=NOW)
ck("31일 지난 것 지움(줄·첨부 줄 모두)", row(x31) is None and att_n(x31) == 0, (out, row(x31)))
ck("29일은 남음(줄·첨부)", row(x29) and isd(x29) == 2 and att_n(x29) == 1)
ck("보낸 메일의 답 기다림이 잡은 메일은 남김", row(xuse) is not None and att_n(xuse) == 1)
ck("맡기기(처리 중)가 잡은 메일은 남김", row(xdlg) is not None)
ck("앞서 대기한 다른 것(지울 날 지남)도 지움 · 돌려준 수 = 지움 %d · 남김 2" % len(due_go),
   out["deleted"] == len(due_go) == 4 and out["kept"] == 2 and all(row(x) is None for x in due_go), (out, due_go))
with _db.db_session() as c:
    lg = [tuple(x) for x in c.execute("SELECT action, n, actor_id FROM mail_purge_log WHERE action LIKE 'night_%' ORDER BY id").fetchall()]
    note = c.execute("SELECT note FROM mail_purge_log WHERE action='night_keep' ORDER BY id DESC LIMIT 1").fetchone()
ck("이력 = 밤 지움(사람마다 · 시스템) 갑 2 · 관리자 2 · 남김 2 + 까닭", lg.count(("night_delete", 2, None)) == 2 and ("night_keep", 2, None) in lg
   and note and "답 기다림" in note[0] and "맡기기" in note[0], (lg, note))
ck("남은 메일들 그대로(받은편지함·보낸 메일)", isd(keep_in) == 0 and row(sent) is not None)
out2 = ms.purge_expired_pending(_db.db_session, now=NOW + dt.timedelta(days=2))
ck("이틀 뒤 밤 → 29일이던 것도 지움 · 쓰는 곳 있는 것은 계속 남김", row(x29) is None and row(xuse) is not None and out2["deleted"] == 1, out2)

print("⑥ 화면·연결 점검(소스)")
src = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
tick = src[src.index("def _mail_vacuum_tick"):src.index("def _start_mail_vacuum_scheduler")]
ck("밤 23:30 정리에 붙어 있음(줄이기 전에)", "purge_expired_pending" in tick and tick.index("purge_expired_pending") < tick.index("_mail_vacuum_busy_and_run()"))
st = io.open(os.path.join(ROOT, "app", "mail_store.py"), encoding="utf-8").read()
body = st[st.index("def hard_delete_mail"):st.index("def purge_old_count")]
ck("휴지통 한 통·비우기 함수에 DELETE 없음", "DELETE FROM" not in body, "")
body2 = st[st.index("def purge_old_count"):st.index("def count_pending")]
ck("일괄 삭제 함수에 DELETE 없음", "DELETE FROM" not in body2, "")
ib = io.open(os.path.join(ROOT, "app", "templates", "mail_inbox.html"), encoding="utf-8").read()
ck("휴지통 화면 confirm 「되돌릴 수 없습니다」 없음 · 안내문 창", "되돌릴 수 없습니다" not in ib and "mailPurgeAsk(" in ib and "되돌릴 수 없음" not in ib)
pa = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_purge_ask.html"), encoding="utf-8").read()
ck("안내문 창 = ✕ 닫기 · 직접 #색 없음", "✕ 닫기" in pa and not re.search(r"#[0-9a-fA-F]{3,8}\b", re.sub(r"\{#.*?#\}", "", pa, flags=re.S)))

print("\n결과: %d/%d 통과" % (len(P), len(P) + len(F)))
if F:
    print("실패:", F)
sys.exit(1 if F else 0)
