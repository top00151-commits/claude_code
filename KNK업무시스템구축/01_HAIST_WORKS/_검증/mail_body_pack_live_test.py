# -*- coding: utf-8 -*-
"""서식 본문 받을 때 바로 압축 · 그룹 메일 한 벌 · 밤 정리 날짜 상관없이 모두 — 시험(대표 11-26 「1번 진행해」).
빈 임시 DB · 가짜 직원·가짜 메일만(운영 무접촉).
실행: 프로젝트 루트(01_HAIST_WORKS)에서  py -3.13 _검증/mail_body_pack_live_test.py"""
import io
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_bodylive_"), "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_body_pack as mbp
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P, F = [], []


def ck(n, ok, extra=""):
    (P if ok else F).append(n)
    print(("  [OK] " if ok else "  [XX] ") + n + ("" if ok else "  " + str(extra)[:400]))


A, B, C3 = 9201, 9202, 9203
with _db.db_session() as c:
    for i in (A, B, C3):
        c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (i, "t%d" % i, "가짜%d" % i, "member"))

H_GROUP = "<table><tr><td>" + "그룹 메일 견적 표 가짜 " * 200 + "</td></tr></table>"
H_ONE = "<div><b>개별</b> " + "가짜 거래처 개별 메일 " * 200 + "</div>"
_seq = [0]


def put(uid, html, mid=None, text="가짜 글 본문"):
    _seq[0] += 1
    with _db.db_session() as c:
        i, _o = ms.store_inbound(c, to_email="t%d@knknara.co.kr" % uid, from_email="sales@partner-demo.example", from_name="가짜",
                                 subject="가짜 제목 %d" % _seq[0], text=text, html=html, owner_id=uid, run_ai=False,
                                 message_id=mid or ("live-%d@demo" % _seq[0]))
    return i


def row(i):
    with _db.db_session() as c:
        r = c.execute("SELECT body_html, html_sha, body_text, direction FROM mail_messages WHERE id=?", (i,)).fetchone()
        return dict(r) if r else None


def store_n():
    with _db.db_session() as c:
        return c.execute("SELECT COUNT(*) FROM mail_body_store").fetchone()[0]


print("① 받을 때 바로 압축")
a1 = put(A, H_ONE)
r = row(a1)
ck("받은 메일: 서식 본문 칸 비움 + 지문", r["body_html"] == "" and len(r["html_sha"]) == 64, r)
ck("글 본문(찾기·미리 보기)은 그대로", r["body_text"] == "가짜 글 본문")
with _db.db_session() as c:
    g = ms.get_mail(c, a1, A)
ck("⭐열면 원래 HTML 그대로(get_mail)", g["body_html"] == H_ONE)
small = put(A, "<p>짧은 본문</p>")
ck("1KB 안 짧은 본문은 그대로", row(small)["body_html"] == "<p>짧은 본문</p>" and not row(small)["html_sha"])
notxt = put(A, "", text="글만 있는 메일")
ck("서식 본문 없는 메일은 그대로", row(notxt)["body_html"] == "" and not row(notxt)["html_sha"])

print("② 그룹 메일 = 세 사람 · 보관함 한 벌")
s0 = store_n()
g1 = put(A, H_GROUP, mid="grp-1@demo")
g2 = put(B, H_GROUP, mid="grp-1@demo")
g3 = put(C3, H_GROUP, mid="grp-1@demo")
shas = {row(x)["html_sha"] for x in (g1, g2, g3)}
ck("세 사람 메일 줄은 각자(읽음·폴더 따로)", len({g1, g2, g3}) == 3)
ck("세 통 모두 같은 지문 하나", len(shas) == 1 and "" not in shas, shas)
ck("⭐보관함에는 한 벌만 늘어남", store_n() == s0 + 1, (s0, store_n()))
with _db.db_session() as c:
    ok3 = all(ms.get_mail(c, x, u)["body_html"] == H_GROUP for x, u in ((g1, A), (g2, B), (g3, C3)))
    ck("세 사람 모두 자기 메일에서 원래 본문", ok3)
    ck("남의 메일은 못 엶(get_mail 소유 확인 그대로)", ms.get_mail(c, g2, A) is None)

print("③ 보낸 메일 · 임시보관")
with _db.db_session() as c:
    o1 = ms.store_outbound(c, user_id=A, from_email="t%d@knknara.co.kr" % A, to_email="x@partner-demo.example",
                           subject="가짜 보냄", body="가짜", body_html=H_ONE.replace("개별", "보낸"))
ck("보낸 메일도 바로 압축", row(o1)["body_html"] == "" and row(o1)["html_sha"])
with _db.db_session() as c:
    ck("보낸 메일 열면 원래 HTML", ms.get_mail(c, o1, A)["body_html"] == H_ONE.replace("개별", "보낸"))
    d1 = ms.save_draft(c, user_id=A, to_email="x@partner-demo.example", subject="임시", body="x", body_html=H_ONE)
ck("임시보관은 압축 안 함(계속 고치는 글)", row(d1)["body_html"] == H_ONE and not row(d1)["html_sha"], row(d1))

print("④ 화면 — 읽기 창 · 답장 인용 · 전달")
_U = {"id": A, "role": "member"}
m.get_user = lambda req: dict(_U, name="가짜", team_id=None, team_name="")
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
h = k.get("/mail/%d/pane" % g1)
ck("읽기 창 200 · 본문 글자 보임", h.status_code == 200 and "그룹 메일 견적 표 가짜" in h.text, h.status_code)
h = k.get("/mail/%d" % a1)
ck("전체 보기 200 · 본문 글자 보임", h.status_code == 200 and "가짜 거래처 개별 메일" in h.text, h.status_code)
h = k.get("/mail/compose?reply=%d" % g1)
ck("답장 쓰기: 원본 표 모양 인용에 본문", h.status_code == 200 and "그룹 메일 견적 표 가짜" in h.text, h.status_code)
h = k.get("/mail/compose?forward=%d" % a1)
ck("전달 쓰기: 원본 본문 들어감", h.status_code == 200 and "가짜 거래처 개별 메일" in h.text, h.status_code)

print("⑤ 밤 정리 = 날짜 상관없이 남은 것 모두(스위치 껐을 때 들어온 최근 메일)")
mbp.LIVE_PACK = False
late = put(A, H_ONE.replace("개별", "늦게"))
late2 = put(B, H_GROUP.replace("그룹", "공지"), mid="grp-2@demo")
mbp.LIVE_PACK = True
ck("스위치 끄면 그대로 저장(되돌림 길)", row(late)["body_html"] != "" and not row(late)["html_sha"])
pl = mbp.plan(_db.db_session)
ck("셈: 최근 본문 2통(6개월 안 · 하나뿐) 대상", pl["mails"] == 2 and pl["new_n"] == 2 and pl["pack_all"] is True, pl)
out = mbp.apply(_db.db_session)
ck("정리: 2통 · 건너뜀 0", out["packed"] == 2 and out["skipped"] == 0, out)
ck("늦게 들어온 메일도 압축", row(late)["body_html"] == "" and row(late)["html_sha"])
with _db.db_session() as c:
    ck("정리한 메일 열면 원래 HTML", ms.get_mail(c, late, A)["body_html"] == H_ONE.replace("개별", "늦게"))
    why = {r[0] for r in c.execute("SELECT why FROM mail_body_pack_log WHERE batch=?", (out["batch"],)).fetchall()}
ck("정리 기록 까닭 = 최근 본문", why == {"최근 본문"}, why)
ck("두 번째 정리 0통", mbp.apply(_db.db_session)["packed"] == 0)

print("⑥ 되돌리기 · 보관함 청소")
n = mbp.undo(_db.db_session)
ck("밤 정리 되돌리기 = 그 묶음 2통만", n == 2 and row(late)["body_html"] == H_ONE.replace("개별", "늦게"), n)
ck("받을 때 압축한 메일은 되돌리기에 안 섞임(그대로 열림)", row(g1)["html_sha"] and row(a1)["html_sha"])
with _db.db_session() as c:
    ms.hard_delete_mail(c, g1, A)
mbp.gc_store(_db.db_session)
with _db.db_session() as c:
    ck("⭐한 사람이 완전히 지워도 다른 사람 그룹 메일 본문은 남음", ms.get_mail(c, g2, B)["body_html"] == H_GROUP)
with _db.db_session() as c:
    ms.hard_delete_mail(c, g2, B)
    ms.hard_delete_mail(c, g3, C3)
mbp.gc_store(_db.db_session)
with _db.db_session() as c:
    left = c.execute("SELECT COUNT(*) FROM mail_body_store WHERE sha IN (%s)" % ",".join("?" * len(shas)), list(shas)).fetchone()[0]
ck("세 사람 모두 지우면 보관함에서도 지워짐", left == 0, left)

print("⑦ 실패해도 메일은 그대로")
s1 = store_n()
with _db.db_session() as c:
    _r = mbp.pack_now(c, 99999999, H_ONE.replace("개별", "없는 번호"))
ck("없는 메일 번호 = False · 보관함에도 안 남음", _r is False and store_n() == s1, (_r, s1, store_n()))
_orig = mbp.zlib.compress
mbp.zlib.compress = lambda b, lv=9: b"\x00broken"
bad = put(A, H_ONE.replace("개별", "망가진 압축"))
mbp.zlib.compress = _orig
r = row(bad)
ck("압축이 망가지면 원래 칸 그대로 · 메일 저장은 됨", r and r["body_html"] == H_ONE.replace("개별", "망가진 압축") and not r["html_sha"], r)
with _db.db_session() as c:
    ck("망가진 압축은 보관함에도 안 남음", c.execute("SELECT COUNT(*) FROM mail_body_store WHERE z=?", (b"\x00broken",)).fetchone()[0] == 0)

print("결과: %d 통과 / %d 실패" % (len(P), len(F)))
sys.exit(1 if F else 0)
