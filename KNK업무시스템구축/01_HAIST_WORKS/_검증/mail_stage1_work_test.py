# -*- coding: utf-8 -*-
"""메일 다음 1단계(대표 2026-11-19 「1단계 진행해」) — 실무자 시간 줄이기 + 그룹 메일 명단.
운영 무접촉 · 임시 DB · 가짜 메일 서버(보내지 않고 기록만) · 가짜 주소·가짜 회사.

증명할 것
  ① 📝 자주 쓰는 글: 기본 양식(한·영·베) · 내 양식 만들기·고치기·지우기 · 회사 양식은 관리자만 · 남의 양식 못 만짐 · 쓰기 화면 「📝 양식」·빈칸 검사·노란 표시 빼고 보냄
  ② ⏳ 답 기다리기: 보낼 때 「3일」 → 기다림 · 사내만이면 안 붙음 · 같은 회사에서 같은 제목 답이 오면 저절로 「답 옴」 · 다른 제목은 아님 · 기한 지나면 받은편지함 띠 · 다시 묻기(받는 사람·제목·3일) · 보내면 원래 메일 빠짐 · 그만·끝·남의 것 못 만짐
  ③ 📎 첨부 모아 찾기: 보낸 메일 첨부도 보관 · 종류·받음/보냄·이름·상대로 찾기 · 본문 그림 뺌 · 남의 메일 첨부 안 보임
  ④ 👥 묶음·그룹 메일: 회사 그룹 메일은 관리자만 · 주소 확인 · 같은 주소 두 번 안 됨 · 직원은 웍스 이름으로 · 주소마다 그룹/직원/명단 없는 사내/바깥 · 자동완성 맨 위(그룹·내 묶음·부서) · 묶음 펼쳐 넣기 · 받은 메일로 찾아보기(관리자) · 화면
"""
import io
import json
import os
import smtplib
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
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_ms1w_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_send as sd
    from app import mail_work as mw
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:400])


SENT = []


class FakeSMTP:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, u, p):
        pass

    def send_message(self, msg, from_addr=None, to_addrs=None):
        SENT.append((list(to_addrs), msg))
        return {}


sd.smtplib.SMTP_SSL = FakeSMTP
sd.get_send_config_for = lambda c, owner_id=None: {"host": "h", "port": 465, "user": "u", "password": "p"}
sd.system_send_ready = lambda c, owner_id=None: True

OWN, OTHER, STAFF1, STAFF2 = 9601, 9602, 9603, 9604
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(9601,'T9601','시험영업팀',1)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id, rank) VALUES(9601,'kjr','시험대표','ceo',1,'x','boss@knknara.co.kr',NULL,'')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9602,'t9602','시험이','member',1,'x','t2@knknara.co.kr',NULL)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9603,'t9603','김영업','member',1,'x','s1@knknara.co.kr',9601)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9604,'t9604','이영업','member',1,'x','s2@knknara.co.kr',9601)")
    c.execute("INSERT INTO app_settings(key,value) VALUES('mail_from_address','boss@knknara.co.kr') ON CONFLICT(key) DO UPDATE SET value=excluded.value")
U_CEO = {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": "", "email": "boss@knknara.co.kr"}
U_MEM = {"id": OTHER, "role": "member", "name": "시험이", "team_id": None, "team_name": "", "email": "t2@knknara.co.kr"}
_U = {"v": dict(U_CEO)}
m.get_user = lambda req: _U["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
km = TestClient(m.app, base_url="http://127.0.0.1:5053", raise_server_exceptions=False, follow_redirects=False)
km.headers.update({"host": "kmail.knknara.co.kr", "x-forwarded-proto": "https"})


def as_(u):
    _U["v"] = dict(u)


def rd(f):
    return open(os.path.join(ROOT, "app", "templates", f), encoding="utf-8").read()


_SEQ = [0]


def put(subject, frm, owner=OWN, atts=None, to_all="boss@knknara.co.kr", to="boss@knknara.co.kr"):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email=to, from_email=frm, from_name="보낸이", subject=subject, text="본문",
                                   owner_id=owner, run_ai=False, message_id="s1w-%d@t" % _SEQ[0], to_all=to_all, attachments=atts)
    return mid


def last_out(uid=OWN):
    with _db.db_session() as c:
        mw.ensure(c)
        return dict(c.execute("SELECT * FROM mail_messages WHERE user_id=? AND direction='out' ORDER BY id DESC LIMIT 1", (uid,)).fetchone())


print("== ① 자주 쓰는 글(양식) ==")
j = k.get("/api/mail/templates").json()
langs = {t["lang"] for t in j["builtin"]}
check("기본 양식 = 한국어·영어·베트남어 · 견적·발주·납기·세금계산서·자료 요청·재촉", {"ko", "en", "vi"} <= langs and len([t for t in j["builtin"] if t["lang"] == "ko"]) == 6, langs)
check("기본 양식에 [빈칸] · [내 이름]", all("[" in t["body"] for t in j["builtin"]) and any("[내 이름]" in t["body"] for t in j["builtin"]))
r = k.post("/mail/templates/save", data={"title": "삼성 견적", "subject": "[KNK] [품명] 견적", "body": "안녕하세요 [담당자]님", "lang": "ko"}).json()
check("내 양식 만들기", r["ok"] and r["id"], r)
tid = r["id"]
check("이름 없으면 거절", not k.post("/mail/templates/save", data={"title": "", "body": "x"}).json()["ok"])
as_(U_MEM)
r2 = k.post("/mail/templates/save", data={"title": "회사 것", "body": "x", "company": "1"})
check("회사 양식 = 관리자만(직원은 거절)", r2.status_code == 400 and "관리자" in r2.json()["message"], r2.text)
check("남의 양식 못 고침", not k.post("/mail/templates/save", data={"id": str(tid), "title": "가로채기", "body": "x"}).json()["ok"])
check("남의 양식 못 지움", not k.post("/mail/templates/%d/delete" % tid).json()["ok"])
check("남의 양식은 목록에 안 보임", all(t["id"] != tid for t in k.get("/api/mail/templates").json()["mine"]))
as_(U_CEO)
rc = k.post("/mail/templates/save", data={"title": "회사 견적 양식", "body": "회사 문장 [품명]", "company": "1", "lang": "ko"}).json()
check("관리자는 회사 양식 만듦", rc["ok"], rc)
as_(U_MEM)
check("직원에게도 회사 양식이 보임", any(t["title"] == "회사 견적 양식" for t in k.get("/api/mail/templates").json()["company"]))
as_(U_CEO)
check("고치기", k.post("/mail/templates/save", data={"id": str(tid), "title": "삼성 견적2", "body": "본문2", "lang": "en"}).json()["ok"]
      and any(t["title"] == "삼성 견적2" and t["lang"] == "en" for t in k.get("/api/mail/templates").json()["mine"]))
check("지우기", k.post("/mail/templates/%d/delete" % tid).json()["ok"] and not k.get("/api/mail/templates").json()["mine"])
check("양식 관리 화면 열림", km.get("/mail/templates").status_code == 200 and "자주 쓰는" in km.get("/mail/templates").text)
cp = rd("mail_compose.html")
check("쓰기 화면 「📝 양식」 · 빈칸 Tab · [내 이름] 저절로", 'id="cTplBtn"' in cp and "if(e.key!=='Tab') return;" in cp and "ME_KEYS=['[내 이름]'" in cp)
check("보낼 때 노란 빈칸 표시는 빼고 보냄(cmpCleanHtml)", "fd.append('body_html', cmpCleanHtml());" in cp)
check("안 채운 빈칸이면 보내기 전 확인에 알림 · 제목 머리 [KNK] 는 빈칸 아님", "양식의 빈칸을 아직 안 채웠습니다" in cp and "FIXED_TAG=/^\\[(KNK|" in cp)

print("== ② 답 기다리기 ==")
SENT.clear()
r = k.post("/mail/send", data={"to": "buyer@cust-a.example", "subject": "[KNK] 장비 견적서 송부", "body": "견적 보냅니다", "wait_days": "3", "send_token": "w1"}).json()
o1 = last_out()
today = m._mail_local_today(9)
from datetime import date, timedelta  # noqa: E402
check("보낼 때 「3일」 → 기다림 · 기한 = 오늘+3(본사 날짜)", r.get("ok") and o1["wait_state"] == "wait" and o1["wait_until"] == (date.fromisoformat(today) + timedelta(days=3)).isoformat(), (r, o1.get("wait_state"), o1.get("wait_until")))
k.post("/mail/send", data={"to": "t2@knknara.co.kr", "subject": "사내 메일", "body": "x", "wait_days": "3", "send_token": "w2"})
o2 = last_out()
check("받는 사람이 모두 사내면 기다림 안 붙음(이음 요청 몫)", not o2.get("wait_state"), o2.get("wait_state"))
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime','-1 minute') WHERE id=?", (o1["id"],))
put("관계없는 메일", "kim@cust-a.example")
with _db.db_session() as c:
    w = mw.list_waiting(c, OWN, today, ms._normalize_subject)
check("다른 제목 메일은 답으로 안 봄", [x["id"] for x in w] == [o1["id"]], w)
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET wait_until=? WHERE id=?", ((date.fromisoformat(today) - timedelta(days=1)).isoformat(), o1["id"]))
hi = km.get("/mail/inbox").text
check("기한 지나면 받은편지함 위 「⏳ 답 안 온 메일 1통」 · 왼쪽 「⏳ 답 기다림」", 'id="mbxWaitBar"' in hi and "답 안 온 메일 1통" in hi and 'href="/mail/waiting"' in hi)
check("숫자 API(가벼운 판 아님) 답 기다림", k.get("/api/mail/counts").json().get("wait_due") == 1 and "wait" not in k.get("/api/mail/counts?lite=1").json())
hw = km.get("/mail/waiting").text
check("답 기다리는 메일 화면 · 다시 묻기 · 답 받음 · ＋3일 · 그만", "장비 견적서 송부" in hw and "/mail/compose?nudge=%d" % o1["id"] in hw and "✓ 답 받음" in hw and "＋3일" in hw)
hn = km.get("/mail/compose?nudge=%d" % o1["id"]).text
check("다시 묻기 = 원래 받는 사람 · 「[확인 요청] 원래 제목」 · 원래 메일 인용 · 재촉 글", 'value="buyer@cust-a.example"' in hn and "[확인 요청] [KNK] 장비 견적서 송부" in hn
      and "원본 메일" in hn and 'CMP_NUDGE_TPL = "b-nudge-ko"' in hn and 'id="cNudgeOf" value="%d"' % o1["id"] in hn)
hn2 = km.get("/mail/compose?nudge=%d" % o2["id"]).text
check("남의/사내 메일이 아니어도 원래 보낸 것만(받은 메일 번호로는 안 됨)", "[확인 요청]" not in km.get("/mail/compose?nudge=%d" % put("x", "a@b.example")).text)
r = k.post("/mail/send", data={"to": "buyer@cust-a.example", "subject": "[확인 요청] [KNK] 장비 견적서 송부", "body": "다시 여쭙니다", "wait_days": "3", "nudge_of": str(o1["id"]), "send_token": "w3"}).json()
o3 = last_out()
with _db.db_session() as c:
    st1 = c.execute("SELECT wait_state FROM mail_messages WHERE id=?", (o1["id"],)).fetchone()[0]
check("다시 묻기를 보내면 원래 메일은 목록에서 빠지고 새 메일이 기다림", st1 == "nudged" and o3["wait_state"] == "wait", (st1, o3.get("wait_state")))
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime','-1 minute') WHERE id=?", (o3["id"],))
rid = put("RE: [확인 요청] [KNK] 장비 견적서 송부", "lee@cust-a.example")
with _db.db_session() as c:
    w = mw.list_waiting(c, OWN, today, ms._normalize_subject)
    st3 = dict(c.execute("SELECT wait_state, wait_reply_id FROM mail_messages WHERE id=?", (o3["id"],)).fetchone())
check("같은 회사 다른 사람이 같은 제목으로 답하면 저절로 「답 옴」(목록에서 빠짐)", not w and st3["wait_state"] == "replied" and st3["wait_reply_id"] == rid, (w, st3))
check("끝난 것 보기 = 「✅ 답 옴」 · 온 답 보기", "✅ 답 옴" in km.get("/mail/waiting?all=1").text and "/mail/%d" % rid in km.get("/mail/waiting?all=1").text)
r = k.post("/mail/%d/wait" % o1["id"], data={"days": "2"}).json()
check("보낸 메일 열어 「⏳ 답 기다리기」(다시 켜기)", r["ok"], r)
check("그만", k.post("/mail/%d/wait" % o1["id"], data={"days": "0"}).json()["ok"])
check("답 받음으로 끝", k.post("/mail/%d/wait" % o1["id"], data={"done": "1"}).json()["ok"])
r = k.post("/mail/%d/wait" % o2["id"], data={"days": "3"})
check("사내 메일엔 못 붙임(이음 요청 안내)", r.status_code == 400 and "이음 요청" in r.json()["message"], r.text)
as_(U_MEM)
check("남의 메일엔 못 붙임", not k.post("/mail/%d/wait" % o1["id"], data={"days": "3"}).json()["ok"])
as_(U_CEO)
hv = km.get("/mail/%d" % o3["id"]).text
check("읽기 화면 — 답 옴이면 「✅ 답 옴 — 보기」", "✅ 답 옴 — 보기" in hv)
k.post("/mail/send", data={"to": "x@cust-b.example", "subject": "새 견적", "body": "x", "send_token": "w4"})
hv2 = km.get("/mail/%d" % last_out()["id"]).text
check("읽기 화면 — 보낸 메일에 「⏳ 답 기다리기」 단추", 'onclick="mvWait(3)"' in hv2)
check("쓰기 화면 「⏳ 답 받기」 · 사내만이면 잠금", 'id="cWait"' in cp and "사내 업무는 이음 요청이 독촉·회신까지" in cp and "fd.append('wait_days'" in cp)

print("== ③ 첨부 모아 찾기 ==")
r = k.post("/mail/send", data={"to": "buyer@cust-a.example", "subject": "도면 송부", "body": "도면", "send_token": "f1"},
           files=[("files", ("A도면.dwg", b"DWG-FAKE-1", "application/octet-stream")), ("files", ("견적서.pdf", b"%PDF-1.4 fake", "application/pdf"))]).json()
of = last_out()
with _db.db_session() as c:
    oatt = [dict(x) for x in c.execute("SELECT filename, size FROM mail_attachments WHERE mail_id=?", (of["id"],)).fetchall()]
check("보낸 메일 첨부도 보관(전엔 안 남았음)", r.get("ok") and sorted(a["filename"] for a in oatt) == ["A도면.dwg", "견적서.pdf"], (r, oatt))
put("단가표", "p@cust-c.example", atts=[{"filename": "단가표.xlsx", "mime": "application/vnd.ms-excel", "size": 9, "data": b"XLSX-FAKE"},
                                       {"filename": "logo.png", "mime": "image/png", "size": 5, "data": b"PNG", "inline": True, "content_id": "logo"}])
put("남의 첨부", "p@cust-d.example", owner=OTHER, atts=[{"filename": "남의파일.pdf", "mime": "application/pdf", "size": 3, "data": b"PDF"}])
with _db.db_session() as c:
    allf, _ = mw.list_files(c, OWN)
    names = [x["filename"] for x in allf]
    cad, _ = mw.list_files(c, OWN, kind="cad")
    inn, _ = mw.list_files(c, OWN, direction="in")
    qn, _ = mw.list_files(c, OWN, q="견적")
    who, _ = mw.list_files(c, OWN, who="cust-c")
    etc, _ = mw.list_files(c, OWN, kind="etc")
check("받은·보낸 첨부 모두 · 본문 그림(서명 로고) 뺌 · 남의 첨부 안 보임", {"A도면.dwg", "견적서.pdf", "단가표.xlsx"} <= set(names) and "logo.png" not in names and "남의파일.pdf" not in names, names)
check("종류(도면) · 받은 메일만 · 이름 · 상대로 찾기", [x["filename"] for x in cad] == ["A도면.dwg"] and {x["filename"] for x in inn} == {"단가표.xlsx"}
      and [x["filename"] for x in qn] == ["견적서.pdf"] and [x["filename"] for x in who] == ["단가표.xlsx"], (cad, inn, qn, who))
check("기타 = 정한 종류 밖만", all(x["kind"] == "etc" for x in etc))
hf = km.get("/mail/files?kind=cad").text
check("첨부 모아 보기 화면 · 받기·메일·전달 · 종류 단추", km.get("/mail/files").status_code == 200 and "A도면.dwg" in hf and "견적서.pdf" not in hf and "/att/" in hf and "kind=pdf" in hf)
check("왼쪽 칸 「📎 첨부 모아 보기」", 'href="/mail/files"' in hi)

print("== ④ 받는 사람 묶음 · 회사 그룹 메일 ==")
as_(U_MEM)
r = k.post("/mail/groups/save", data={"kind": "company", "name": "기술영업 공용", "address": "knksales@knknara.co.kr", "members": "s1@knknara.co.kr"})
check("회사 그룹 메일 등록 = 관리자만", r.status_code == 400 and "관리자" in r.json()["message"], r.text)
as_(U_CEO)
check("그룹 메일 주소가 틀리면 거절", not k.post("/mail/groups/save", data={"kind": "company", "name": "x", "address": "knksales", "members": "s1@knknara.co.kr"}).json()["ok"])
check("명단이 비면 거절", not k.post("/mail/groups/save", data={"kind": "company", "name": "x", "address": "a@knknara.co.kr", "members": "  "}).json()["ok"])
r = k.post("/mail/groups/save", data={"kind": "company", "name": "기술영업 공용", "address": "KNKSales@knknara.co.kr", "note": "견적·발주 문의",
                                      "members": "아무개 <s1@knknara.co.kr>\ns2@knknara.co.kr, 홍길동 <partner@vendor.example>\ns2@knknara.co.kr"}).json()
check("관리자 등록 · 같은 주소 한 번만 · 3명", r["ok"] and "3명" in r["message"], r)
gid = r["id"]
check("같은 그룹 주소 두 번 등록 안 됨", not k.post("/mail/groups/save", data={"kind": "company", "name": "y", "address": "knksales@knknara.co.kr", "members": "s1@knknara.co.kr"}).json()["ok"])
info = k.get("/api/mail/addrinfo?a=knksales@knknara.co.kr,s1@knknara.co.kr,ghost@knknara.co.kr,b@out.example").json()["info"]
g = info.get("knksales@knknara.co.kr", {})
check("그룹 메일 → 명단 3명 · 직원은 웍스 이름(적은 이름 「아무개」 아님) · 부서", g.get("kind") == "group" and g.get("n") == 3
      and [x["name"] for x in g["members"]][:2] == ["김영업", "이영업"] and "시험영업팀" in g["members"][0]["disp"], g)
check("사내 직원 · 명단 없는 사내 주소(그룹일 수 있음) · 바깥", info["s1@knknara.co.kr"]["kind"] == "staff" and info["ghost@knknara.co.kr"]["kind"] == "unknown" and info["b@out.example"]["kind"] == "external", info)
r = k.post("/mail/groups/save", data={"kind": "mine", "name": "A과제 고객", "members": "a1@cust-a.example\na2@cust-a.example"}).json()
check("내 묶음 만들기", r["ok"], r)
mine_id = r["id"]
ac = k.get("/api/mail/contacts?q=knksales").json()["items"]
check("자동완성 맨 위 = 회사 그룹 메일(주소 하나 · 3명)", ac and ac[0]["email"] == "knksales@knknara.co.kr" and "3명" in ac[0]["src"], ac[:2])
ac2 = k.get("/api/mail/contacts?q=A과제").json()["items"]
check("내 묶음 = 펼쳐 넣기(2명)", ac2 and len(ac2[0].get("expand") or []) == 2, ac2[:1])
ac3 = k.get("/api/mail/contacts?q=시험영업").json()["items"]
check("부서 묶음(웍스 부서 읽기) = 부서원 펼쳐 넣기", any(len(x.get("expand") or []) == 2 and "시험영업팀 전체" in x["name"] for x in ac3), ac3)
as_(U_MEM)
check("남의 내 묶음은 안 보임", not any(x.get("expand") and "A과제" in x["name"] for x in k.get("/api/mail/contacts?q=A과제").json()["items"]))
check("남의 묶음 못 지움 · 회사 그룹 메일 못 지움(직원)", not k.post("/mail/groups/%d/delete" % mine_id).json()["ok"] and not k.post("/mail/groups/%d/delete" % gid).json()["ok"])
check("받은 메일로 찾아보기 = 관리자만", k.get("/api/mail/groups/guess?addr=knksales@knknara.co.kr").status_code == 403)
as_(U_CEO)
put("그룹으로 온 메일", "c@cust-e.example", owner=OWN, to="knksales@knknara.co.kr", to_all="knksales@knknara.co.kr")
put("그룹으로 온 메일", "c@cust-e.example", owner=STAFF1, to="knksales@knknara.co.kr", to_all="knksales@knknara.co.kr")
gs = k.get("/api/mail/groups/guess?addr=knksales@knknara.co.kr").json()["items"]
check("받은 메일로 찾아보기 = 이 주소로 온 메일이 들어간 메일함(2명)", {x["email"] for x in gs} == {"boss@knknara.co.kr", "s1@knknara.co.kr"}, gs)
hg = km.get("/mail/groups").text
check("묶음·그룹 메일 화면 = 회사 그룹(주소·3명·명단) · 내 묶음 · 부서 묶음", "knksales@knknara.co.kr" in hg and "3명" in hg and "A과제 고객" in hg and "시험영업팀 전체" in hg and "📥 하이웍스 파일로 올리기" in hg and "＋ 하나씩 등록" in hg)
as_(U_MEM)
hg2 = km.get("/mail/groups").text
check("직원도 회사 그룹 메일 명단은 봄 · 등록 단추는 없음", "knksales@knknara.co.kr" in hg2 and "📥 하이웍스 파일로 올리기" not in hg2 and "＋ 하나씩 등록" not in hg2)
as_(U_CEO)
check("쓰기 화면 — 그룹 메일이면 「N명이 받습니다」 + 명단 · 명단 없는 사내 주소 알림 · 묶음 펼쳐 넣기",
      'id="cGrpInfo"' in cp and "명</b>이 받습니다" in cp and "직원 주소가 아닌 사내 주소입니다" in cp and "it.expand.map(acFmt)" in cp)
vb = rd("_v5_partials/mail_view_body.html")
check("읽기 화면 — 받는 사람 중 그룹 메일이면 명단", 'id="mvGrp"' in vb and "/api/mail/addrinfo?a=" in vb)
tl = km.get("/mail/tools").text
check("설정·정리에 「📝 자주 쓰는 글」 · 「👥 받는 사람 묶음 · 그룹 메일」", 'href="/mail/templates"' in tl and 'href="/mail/groups"' in tl)
check("묶음 지우기(주인)", k.post("/mail/groups/%d/delete" % mine_id).json()["ok"])

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
