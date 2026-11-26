# -*- coding: utf-8 -*-
"""메일 「다」 묶음 — 사내 보낸 사람 「이름 직책 부서」(6-1) · 👔 윗분(3-2) · ✅ 확인 답장(3-3) · 나 = 받는 사람/참조(6-2)
(대표 2026-11-21 「다음 진행해」). 운영 무접촉 · 임시 DB(knk_mpb_*) · 가짜 직원·가짜 메일만.

증명할 것
  ① 윗분 판정: 대표·임원(이사 이상) · 우리 팀장(팀 leader) · 우리 팀 윗 직책 → 👔 / 동료·아랫사람·다른 팀 과장·나 자신·바깥 주소 → 없음
     · 대표가 볼 때 임원 메일은 👔 아님 · 직책 모름(프로)은 직책으로 가르지 않음 · 퇴사자·한 주소 두 사람은 뺌
  ② 받은편지함: 사내 보낸 사람 = 「이름 직책 부서」 · 👔 꼬리표 · 오늘 챙길 메일 「👔 윗분 지시 N」 · ?reply=1&boss=1 = 그 메일만
  ③ 메일 보기: 「이름 직책 부서」·👔 · 「📌 나 = 받는 사람」/「👀 나 = 참조」/「🙈 숨은참조·그룹」 · ✅ 확인 답장 상자
  ④ ✅ 확인 답장: 쓰기 화면 글 = 사내 「확인했습니다 — 11/27(금)까지 처리하겠습니다」 · 바깥 정중 · 영어 메일 영어 · 오늘 = 「오늘 중으로」 · 틀린 날짜 = 글 없음
  ⑤ 읽기만(명부·메일 표 그대로) · 파이썬 3.8
"""
import ast
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
os.environ["KNK_RUN_MAIL_FETCH"] = "0"

_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mpb_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_people as MP
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402
import json as _json  # noqa: E402
import re as _re  # noqa: E402


def ack_of(html):
    """쓰기 화면의 window.CMP_ACK 글(JSON) 꺼내기."""
    mm = _re.search(r"window\.CMP_ACK = (\"(?:[^\"\\]|\\.)*\");", html)
    return _json.loads(mm.group(1)) if mm else ""

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:500])


D = "@knknara.co.kr"
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO teams(id, code, name, display_order, leader_id) VALUES(9861,'T9861','시험영업팀',3,9863)")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(9862,'T9862','시험설계팀',4)")
    people = [  # id, login, 이름, 직책, 역할, 팀, 재직
        (9860, "t_ceo", "시험대표", "대표이사", "ceo", None, 1),
        (9861, "t_exec", "시험상무", "상무", "executive", 9862, 1),
        (9862, "t_me", "시험신입", "사원", "member", 9861, 1),
        (9863, "t_lead", "시험팀장", "과장", "member", 9861, 1),     # 우리 팀장(직책은 과장)
        (9864, "t_sun", "시험선배", "대리", "member", 9861, 1),      # 같은 팀 윗 직책
        (9865, "t_peer", "시험동기", "사원", "member", 9861, 1),     # 동료
        (9866, "t_other", "시험타팀", "과장", "member", 9862, 1),    # 다른 팀 과장 = 윗분 아님
        (9867, "t_pro", "시험프로", "프로", "member", 9861, 1),      # 직책 모름
        (9868, "t_gone", "시험퇴사", "부장", "member", 9861, 0),     # 퇴사
        (9869, "t_dup1", "시험겹침1", "부장", "member", 9861, 1),
        (9870, "t_dup2", "시험겹침2", "사원", "member", 9861, 1),
    ]
    for uid, lid, nm, rk, role, tid, act in people:
        em = ("shared" + D) if uid in (9869, 9870) else (lid.replace("t_", "") + D)
        c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email) VALUES(?,?,?,?,?,?,?,'x',?)",
                  (uid, lid, nm, rk, role, tid, act, em))

print("① 윗분 판정")
with _db.db_session() as c:
    st = MP.staff(c)
    me = MP.me_of(c, 9862, st)
    ceo_me = MP.me_of(c, 9860, st)


def why(addr, who=None):
    return MP.sender(st, who or me, addr).get("boss", "")


check("대표 → 👔 대표", why("ceo" + D) == "대표", why("ceo" + D))
check("상무(다른 팀이라도) → 👔 임원", why("exec" + D) == "임원", why("exec" + D))
check("우리 팀장(직책 과장) → 👔 우리 팀장", why("lead" + D) == "우리 팀장", why("lead" + D))
check("같은 팀 대리 → 👔 우리 팀 윗 직책", why("sun" + D) == "우리 팀 윗 직책", why("sun" + D))
check("동료(같은 직책) → 없음", why("peer" + D) == "")
check("다른 팀 과장 → 없음", why("other" + D) == "")
check("직책 모름(프로) → 없음", why("pro" + D) == "")
check("나 자신 → 없음", why("me" + D) == "")
check("대표가 볼 때 상무 메일 → 없음", why("exec" + D, ceo_me) == "")
check("퇴사자 주소는 명부에서 뺌", "gone" + D not in st)
check("한 주소 두 사람 → 뺌(잘못 붙이지 않음)", "shared" + D not in st)
check("바깥 주소 → 없음", MP.sender(st, me, "lead@knknara.co.kr.evil-demo.example") == {} and MP.sender(st, me, "") == {})
check("크고 작은 글자 무시", why("LEAD" + D.upper()) == "우리 팀장")
check("「이름 직책 부서」", MP.sender(st, me, "lead" + D).get("disp") == "시험팀장 과장 시험영업팀", MP.sender(st, me, "lead" + D))
check("직책 높낮이: 과장(팀장) = 과장 · 임원 역할은 이사 이상", MP.rank_level("과장(팀장)") == 40 and MP.rank_level("프로", "executive") == 75
      and MP.rank_level("프로") is None)
mine = {"me" + D}
check("나 = 받는 사람", MP.my_role({"direction": "in", "to_email": "\"신입\" <ME" + D.upper() + ">", "cc": ""}, mine) == "to")
check("나 = 참조", MP.my_role({"direction": "in", "to_email": "a" + D, "cc": "me" + D}, mine) == "cc")
check("받는 사람(to_all)에 있으면 받는 사람", MP.my_role({"direction": "in", "to_email": "a" + D, "to_all": "a" + D + ", me" + D, "cc": "me" + D}, mine) == "to")
check("어디에도 없음 = 숨은참조·그룹", MP.my_role({"direction": "in", "to_email": "group" + D, "cc": ""}, mine) == "bcc")
check("보낸 메일·주소 없음 = 표시 안 함", MP.my_role({"direction": "out", "to_email": "me" + D}, mine) == "" and MP.my_role({"direction": "in"}, mine) == "")

print("\n② 받은편지함")
with _db.db_session() as c:
    def put(frm, subj, body, to="me" + D, cc=""):
        c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, cc, subject, body_text, is_deleted, received_at) "
                  "VALUES(9862,'in',?,?,?,?,?,?,0,datetime('now','localtime'))", (frm, "메일프로그램이름", to, cc, subj, body))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]
    M_LEAD = put("lead" + D, "팀장 지시", "견적 자료 다음 주 화요일까지 정리해서 제출 바랍니다.")
    M_PEER = put("peer" + D, "동기 부탁", "자료 좀 보내 주세요.")
    M_SUN = put("sun" + D, "선배 공유", "방문 결과 공유드립니다.", to="a" + D, cc="me" + D)
    M_EXT = put("buyer@vendor-demo.example", "견적 요청", "견적 부탁드립니다.")

ME = {"id": 9862, "role": "member", "name": "시험신입", "rank": "사원", "team_id": 9861, "login_id": "t_me", "email": "me" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})


def snap():
    with _db.db_session() as c:
        return (c.execute("SELECT group_concat(id||name||COALESCE(rank,'')||COALESCE(team_id,'')) FROM users").fetchone()[0],
                c.execute("SELECT group_concat(x) FROM (SELECT id||COALESCE(from_name,'')||COALESCE(subject,'') AS x FROM mail_messages ORDER BY id)").fetchone()[0])   # 11-26 순서 고정(새 색인이 생기면 읽는 순서가 바뀜)


S0 = snap()
r = k.get("/mail/inbox")
h = r.text
check("받은편지함 200", r.status_code == 200, r.status_code)
check("사내 보낸 사람 = 「이름 직책 부서」(메일 프로그램 이름 대신)", "시험팀장 과장 시험영업팀" in h and "시험동기 사원 시험영업팀" in h, "")
check("👔 꼬리표(우리 팀장 · 우리 팀 윗 직책)", "👔 우리 팀장" in h and "👔 우리 팀 윗 직책" in h, "")
check("오늘 챙길 메일 「👔 윗분 지시 1」(회신 필요 중 윗분 메일만)", "👔 윗분 지시 <b>1</b>" in h, h[h.find("mbxDay"):h.find("mbxDay") + 900])
r = k.get("/mail/inbox?reply=1&boss=1")
check("윗분 지시만 보기 = 팀장 메일만", "팀장 지시" in r.text and "동기 부탁" not in r.text and "견적 요청" not in r.text, "")
r = k.get("/mail/inbox?reply=1")
check("회신 필요 = 팀장·동기·바깥 모두(그대로)", all(x in r.text for x in ("팀장 지시", "동기 부탁", "견적 요청")), "")

print("\n③ 메일 보기")
r = k.get("/mail/%d/pane" % M_LEAD)
t = r.text
check("보기: 「이름 직책 부서」 · 👔 우리 팀장 · 📌 나 = 받는 사람", r.status_code == 200 and "시험팀장 과장 시험영업팀" in t and "👔 우리 팀장" in t
      and 'class="mv-rc-p me"' in t and ">나</span>" in t, r.status_code)   # 11-22 「📌 나 = 받는 사람」 띠 → 받는 사람 줄의 초록 「나」 칩
check("보기: ✅ 확인 답장 상자 · 본문 기한 단추", 'id="mvAck"' in t and "mvAck('" in t and "본문 기한" in t, "")
r = k.get("/mail/%d" % M_SUN)
_cc = r.text[r.text.find('class="mv-rc mv-rc-cc"'):]
_cc = _cc[:_cc.find('</span><span class="mv-when">') if '</span><span class="mv-when">' in _cc else 600]
check("전체 보기: 나 = 참조 줄의 초록 「나」 칩(11-22 「👀 나 = 참조」 띠 대신) · 👔 우리 팀 윗 직책", 'class="mv-rc-p me"' in _cc and "👔 우리 팀 윗 직책" in r.text, _cc[:300])
r = k.get("/mail/%d/pane" % M_EXT)
check("바깥 메일: 👔 없음 · 이름 그대로", "👔" not in r.text.split('class="mv-actions"')[0] and "메일프로그램이름" in r.text, "")
check("읽기만 — 직원 명부·메일 표 그대로", snap() == S0)
# 11-26 「메일 누르면 2초」 — 읽음 표시를 화면 계산 뒤 짧게 따로 저장: 열면 여전히 읽음이 되는지 · 쓰기 잠금이 남지 않는지
with _db.db_session() as _c:
    _c.execute("UPDATE mail_messages SET is_read=0, read_at=NULL WHERE id=?", (M_EXT,))
r = k.get("/mail/%d/pane" % M_EXT)
with _db.db_session() as _c:
    _rd = _c.execute("SELECT is_read, read_at FROM mail_messages WHERE id=?", (M_EXT,)).fetchone()
    _c.execute("BEGIN IMMEDIATE"); _c.execute("ROLLBACK")
check("읽기 창을 열면 읽음 표시(끝에서 짧게 저장) · 쓰기 잠금 안 남음", r.status_code == 200 and _rd["is_read"] == 1 and _rd["read_at"], dict(_rd))
with _db.db_session() as _c:
    _c.execute("UPDATE mail_messages SET is_read=0, read_at=NULL WHERE id=?", (M_EXT,))
r = k.get("/mail/%d" % M_EXT)
with _db.db_session() as _c:
    _rd = _c.execute("SELECT is_read FROM mail_messages WHERE id=?", (M_EXT,)).fetchone()
check("전체 보기 화면도 열면 읽음 표시", r.status_code == 200 and _rd["is_read"] == 1, dict(_rd))
with _db.db_session() as _c:
    _ix = [x[0] for x in _c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name IN ('idx_mail_cover','idx_mail_fdpin')").fetchall()]
check("세기 색인 두 개가 만들어짐(idx_mail_cover · idx_mail_fdpin)", sorted(_ix) == ["idx_mail_cover", "idx_mail_fdpin"], _ix)


print("\n④ ✅ 확인 답장")
r = k.post("/mail/flag", data={"ids": str(M_LEAD), "due": "2026-11-27"})
check("기한 먼저 저장(기존 길)", r.status_code == 200 and r.json().get("due") == "2026-11-27", r.text[:200])
r = k.get("/mail/compose?reply=%d&ack=2026-11-27" % M_LEAD)
check("쓰기 화면: 사내 「확인했습니다 — 11/27(금)까지 처리하겠습니다」", r.status_code == 200 and ack_of(r.text) == "확인했습니다.\n11/27(금)까지 처리하겠습니다.\n\n감사합니다.", ack_of(r.text))
r = k.get("/mail/compose?reply=%d&ack=2026-02-30" % M_LEAD)
check("틀린 날짜 = 확인 글 없이 그냥 답장", r.status_code == 200 and ack_of(r.text) == "", ack_of(r.text))
r = k.get("/mail/compose?reply=%d&ack=2026-11-27" % M_EXT)
check("바깥 메일 = 정중한 글", "11/27(금)까지 확인 후 회신드리겠습니다" in ack_of(r.text), ack_of(r.text))
check("영어 메일 = 영어 글", "by Nov 27 (Fri)" in m._mail_ack_text({"subject": "Quote", "body_text": "Please send", "from_email": "a@b-demo.example"}, "2026-11-27", "2026-11-21"))
check("오늘 = 「오늘 중으로」", "오늘 중으로 처리하겠습니다" in m._mail_ack_text({"subject": "지시", "body_text": "보고", "from_email": "lead" + D}, "2026-11-21", "2026-11-21"))
r = k.get("/mail/compose?reply=%d" % M_LEAD)
check("그냥 답장은 그대로(확인 글 없음)", r.status_code == 200 and ack_of(r.text) == "", ack_of(r.text))

print("\n⑤ 문법·화면")
cmp_html = io.open(os.path.join(ROOT, "app", "templates", "mail_compose.html"), encoding="utf-8").read()
check("쓰기 화면: 확인 글은 맨 위에 넣고 보내기는 직접", "if(window.CMP_ACK){ insertTpl({body:window.CMP_ACK}, true); }" in cmp_html)
for p in ("app/mail_people.py", "app/main.py"):
    try:
        ast.parse(io.open(os.path.join(ROOT, p), encoding="utf-8").read(), feature_version=(3, 8))
        ok = True
    except SyntaxError as e:
        ok = e
    check("파이썬 3.8 문법: %s" % p, ok is True, ok)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
