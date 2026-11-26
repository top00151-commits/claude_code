# -*- coding: utf-8 -*-
"""메일 1단계 — 잘못 발송 막기 (대표 2026-11-19 「1단계 진행해」).

운영 DB·운영 메일 서버 무접촉 — 임시 DB + 가짜 메일 서버(smtplib 대신 기록만 하는 가짜).
실제 메일 내용 없음 — 모두 가짜 주소(*.example).

증명할 것
  ① 받는 사람 여러 명을 한 명씩 나눔(이름 속 쉼표·꺾쇠·세미콜론·줄바꿈) · 틀린 주소는 콕 집어 · 같은 주소 한 번만
  ② 파이썬 판과 상관없이 같은 결과(parseaddr 에 기대지 않음)
  ③ 발송: 봉투 수신자 = 받는 사람+참조+숨은참조 전원 · 숨은참조는 머리에 없음 · 한글 이름 머리 깨지지 않음
  ④ 메일 서버가 일부만 거부 → 성공으로 덮지 않고 그 주소·사유를 돌려줌 · 전부 거부 → 실패
  ⑤ /mail/send: 틀린 주소 있으면 안 보내고 그 주소를 알려 줌 · 여러 명 전원 발송 · 보낸편지함에 전원 기록
  ⑥ 같은 보내기 표(send_token)로 두 번 → 두 번째는 안 보냄(dup) · 보내기 실패면 다시 보낼 수 있음
  ⑦ 전달: 원래 첨부가 함께 감 · 뺀 것은 안 감 · 남의 메일 첨부는 못 붙임
  ⑧ 전체 답장: 원래 받는 사람 전원 + 참조 · 나(이름 붙은 주소 포함)·원래 보낸 사람은 빠짐 · 이름 속 쉼표 안 쪼개짐
  ⑨ 받아 올 때 원문 「받는 사람」 전원 저장(to_all)
  ⑩ 임시 메일 다시 열면 서식(HTML) 그대로 · 쓰다 만 메일 버리기는 내 것만
  ⑪ 자동완성: 사내 직원·주고받은 사람도(내 메일함 것만)
  ⑫ 쓰기 화면: 확인 창·보내기 취소 10초·취소 묻기·창 닫힘 경고·자동 임시저장·대용량 올리는 중 막기·전달 첨부 표시
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
    _TMP = tempfile.mkdtemp(prefix="knk_msafe_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_send as sd
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
        print("  [FAIL]", name, "<-", str(extra)[:600])


# ── 가짜 메일 서버 ──
SENT = []          # [(from, to_addrs, msg)]
REFUSE = {}        # 주소 → (code, msg) — 일부 거부 흉내
REFUSE_ALL = [False]


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
        if REFUSE_ALL[0]:
            raise smtplib.SMTPRecipientsRefused({a: (550, b"no such user") for a in to_addrs})
        SENT.append((from_addr, list(to_addrs), msg))
        return {a: v for a, v in REFUSE.items() if a in to_addrs}


sd.smtplib.SMTP_SSL = FakeSMTP
_CFG = {"host": "smtp.fake.example", "port": 465, "user": "relay@fake.example", "password": "FAKE"}
sd.get_send_config_for = lambda c, owner_id=None: dict(_CFG)
sd.system_send_ready = lambda c, owner_id=None: True

print("== ① ② 주소 나누기 ==")
ok, bad = sd.parse_addr_list('홍길동 <hong@a.example>, b@b.example; "Kim, Minsu" <k@c.example>\nlee@d.example')
check("네 명으로 나눔 · 이름 속 쉼표 안 쪼갬", [a for _n, a in ok] == ["hong@a.example", "b@b.example", "k@c.example", "lee@d.example"] and not bad, (ok, bad))
check("이름 보존", ok[0][0] == "홍길동" and ok[2][0] == "Kim, Minsu", ok)
_rt = sd.addr_list_text(ok)
check("다시 글로 → 다시 나눠도 같은 사람들(이름 속 쉼표는 따옴표)", sd.parse_addr_list(_rt)[0] == ok and '"Kim, Minsu" <k@c.example>' in _rt, _rt)
ok, bad = sd.parse_addr_list("a@x.example, bad@@x, , no-at, A@X.example, c@y")
check("틀린 주소 콕 집기(bad@@x · no-at · c@y) · 빈 조각 무시 · 같은 주소(대소문자) 한 번만",
      bad == ["bad@@x", "no-at", "c@y"] and [a for _n, a in ok] == ["a@x.example"], (ok, bad))
check("하나짜리 검사(is_valid_email) — 둘이면 False(여러 명은 parse_addr_list)",
      sd.is_valid_email("홍 <h@a.example>") and not sd.is_valid_email("a@x.example, b@y.example") and not sd.is_valid_email(""))
check("parseaddr 안 씀(파이썬 판 무관)", "parseaddr" not in open(os.path.join(ROOT, "app", "mail_send.py"), encoding="utf-8").read().split("def parse_addr_list")[1].split("def addr_list_text")[0])

print("== ③ ④ 발송 ==")
SENT.clear()
rep = {}
okv, msg = sd._smtp_send("h", 465, "u", "p", "me@knknara.co.kr", "홍길동 <hong@a.example>, b@b.example", "제목", "본문",
                         from_name="시험", cc="c@c.example", bcc="secret@d.example", report=rep)
fr, env, mm = SENT[-1]
check("봉투 수신자 = 받는 사람+참조+숨은참조 전원", env == ["hong@a.example", "b@b.example", "c@c.example", "secret@d.example"], env)
check("숨은참조는 머리에 없음", "secret@d.example" not in str(mm) and mm.get("Bcc") is None)
check("받는 사람 머리에 두 명 · 한글 이름 규격 인코딩", "hong@a.example" in str(mm["To"]) and "b@b.example" in str(mm["To"]) and "=?utf-8?" in mm.as_string().split("\nTo:")[1].split("\n")[0].lower() or "홍길동" in str(mm["To"]), str(mm["To"]))
check("성공 · report.sent 전원", okv and rep.get("sent") == env and rep.get("refused") == {}, (okv, msg, rep))
REFUSE.clear(); REFUSE["b@b.example"] = (550, b"5.1.1 no such user")
rep = {}
okv, msg = sd._smtp_send("h", 465, "u", "p", "me@knknara.co.kr", "hong@a.example, b@b.example", "s", "b", report=rep)
check("일부 거부 → 성공으로 덮지 않음: 사유·주소를 돌려줌", okv and "b@b.example" in rep["refused"] and "550" in rep["refused"]["b@b.example"]
      and rep["sent"] == ["hong@a.example"] and "못 간 주소" in msg, (okv, msg, rep))
REFUSE.clear(); REFUSE_ALL[0] = True
okv, msg = sd._smtp_send("h", 465, "u", "p", "me@knknara.co.kr", "hong@a.example", "s", "b", report={})
check("전부 거부 → 실패 + 그 주소", (not okv) and "hong@a.example" in msg, msg)
REFUSE_ALL[0] = False
okv, msg = sd._smtp_send("h", 465, "u", "p", "me@knknara.co.kr", "hong@a.example, bad@@x", "s", "b")
check("틀린 주소 섞이면 아예 안 보냄", (not okv) and "bad@@x" in msg, msg)
check("서버 오류 글 = 사람 말(영어 원문은 괄호 짧게)", "응답하지 않습니다" in sd._send_err_text(TimeoutError("timed out")))

OWN, OTHER = 9101, 9102
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(9101,'kjr','시험대표','ceo',1,'x','boss@knknara.co.kr')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(9102,'t9102','시험이','member',1,'x','tester@knknara.co.kr')")
    c.execute("INSERT INTO app_settings(key,value) VALUES('mail_from_address','boss@knknara.co.kr') ON CONFLICT(key) DO UPDATE SET value=excluded.value")

_U = {"v": {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": "", "email": "boss@knknara.co.kr"}}
m.get_user = lambda req: _U["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

print("== ⑤ /mail/send ==")
SENT.clear()
r = k.post("/mail/send", data={"to": "홍길동 <hong@a.example>, bad@@x", "subject": "s", "body": "b"})
j = r.json()
check("틀린 주소 → 400 · 그 주소를 알려 줌 · 안 보냄", r.status_code == 400 and j.get("bad") == ["bad@@x"] and "bad@@x" in j.get("message", "") and not SENT, j)
r = k.post("/mail/send", data={"to": "홍길동 <hong@a.example>, b@b.example", "cc": "\"Kim, Minsu\" <k@c.example>",
                               "subject": "여러 명", "body": "b", "send_token": "tok-1"})
j = r.json()
check("여러 명 전원 발송", j.get("ok") and SENT and SENT[-1][1] == ["hong@a.example", "b@b.example", "k@c.example"] and j.get("sent_n") == 3, (j, SENT[-1][1] if SENT else None))
with _db.db_session() as c:
    row = c.execute("SELECT to_email, cc FROM mail_messages WHERE user_id=? AND direction='out' AND subject='여러 명'", (OWN,)).fetchone()
check("보낸편지함에 받는 사람 전원 기록(소문자 · 쉼표)", row and row["to_email"] == "hong@a.example, b@b.example" and "k@c.example" in row["cc"], dict(row) if row else None)

print("== ⑥ 두 번 막기 ==")
n0 = len(SENT)
j2 = k.post("/mail/send", data={"to": "hong@a.example", "subject": "여러 명", "body": "b", "send_token": "tok-1"}).json()
check("같은 보내기 표 → 두 번째는 안 보냄(dup)", j2.get("ok") and j2.get("dup") and len(SENT) == n0, j2)
REFUSE_ALL[0] = True
j3 = k.post("/mail/send", data={"to": "hong@a.example", "subject": "x", "body": "b", "send_token": "tok-2"}).json()
REFUSE_ALL[0] = False
j4 = k.post("/mail/send", data={"to": "hong@a.example", "subject": "x", "body": "b", "send_token": "tok-2"}).json()
check("실패한 보내기는 같은 표로 다시 보낼 수 있음", (not j3.get("ok")) and j4.get("ok") and not j4.get("dup"), (j3, j4))
REFUSE.clear(); REFUSE["x@b.example"] = (550, b"no such user")
j5 = k.post("/mail/send", data={"to": "a@a.example, x@b.example", "subject": "y", "body": "b", "send_token": "tok-3"}).json()
REFUSE.clear()
check("일부 거부 → 화면에 줄 주소·사유", j5.get("ok") and j5.get("refused") and j5["refused"][0]["addr"] == "x@b.example" and j5.get("sent_n") == 1, j5)

print("== ⑦ 전달 첨부 ==")
att = [{"filename": "견적서.pdf", "mime": "application/pdf", "size": 9, "content_id": "", "inline": False, "data": b"%PDF-fake"},
       {"filename": "도면.dwg", "mime": "application/octet-stream", "size": 4, "content_id": "", "inline": False, "data": b"DWG1"}]
with _db.db_session() as c:
    src, _o = ms.store_inbound(c, to_email="boss@knknara.co.kr", from_email="p@semco.example", from_name="박구매",
                               subject="견적 요청", text="견적 부탁드립니다", owner_id=OWN, run_ai=False,
                               attachments=att, message_id="fwd-1@test",
                               to_all='시험대표 <boss@knknara.co.kr>, "Lee, Jay" <jay@semco.example>, kim@partner.example')
    c.execute("UPDATE mail_messages SET cc=? WHERE id=?", ("Boss <BOSS@knknara.co.kr>, cc1@semco.example", src))
    aids = [r_["id"] for r_ in c.execute("SELECT id FROM mail_attachments WHERE mail_id=? ORDER BY id", (src,)).fetchall()]
    oth, _o = ms.store_inbound(c, to_email="tester@knknara.co.kr", from_email="z@z.example", subject="남의", text="x",
                               owner_id=OTHER, run_ai=False, attachments=[att[0]], message_id="oth-1@test")
    oth_aid = c.execute("SELECT id FROM mail_attachments WHERE mail_id=?", (oth,)).fetchone()["id"]
hf = k.get("/mail/compose?forward=%d" % src).text
_fw = hf[hf.find("window.CMP_FWD = ") + 17:]
_fw = json.loads(_fw[:_fw.find(";</script>")]) if "window.CMP_FWD = " in hf else []
check("전달 쓰기 화면에 원래 첨부 두 개(✕ 로 뺄 수 있음)", [x["filename"] for x in _fw] == ["견적서.pdf", "도면.dwg"], _fw)
check("전달 쓰기 화면: 원래 메일 번호", 'id="cFwdSrc" value="%d"' % src in hf)
SENT.clear()
j = k.post("/mail/send", data={"to": "out@vendor.example", "subject": "Fwd: 견적 요청", "body": "b", "fwd_src": str(src),
                               "fwd_att": [str(aids[0])], "send_token": "tok-f1"}).json()
msg_ = SENT[-1][2] if SENT else None
names = [p_.get_filename() for p_ in msg_.iter_attachments()] if msg_ else []
check("전달: 고른 원래 첨부만 함께 감(뺀 도면은 안 감)", j.get("ok") and names == ["견적서.pdf"], (j, names))
SENT.clear()
j = k.post("/mail/send", data={"to": "out@vendor.example", "subject": "x", "body": "b", "fwd_src": str(src),
                               "fwd_att": [str(oth_aid)], "send_token": "tok-f2"}).json()
names = [p_.get_filename() for p_ in SENT[-1][2].iter_attachments()] if SENT else ["?"]
check("남의 메일 첨부 번호를 넣어도 안 붙음", names == [], (j, names))
j = k.post("/mail/send", data={"to": "out@vendor.example", "subject": "x", "body": "b", "fwd_src": str(oth),
                               "fwd_att": [str(oth_aid)], "send_token": "tok-f3"})
check("남의 메일을 원래 메일로 → 404", j.status_code == 404, j.text[:200])

print("== ⑧ 전체 답장 · ⑨ to_all ==")
with _db.db_session() as c:
    ta = c.execute("SELECT to_all FROM mail_messages WHERE id=?", (src,)).fetchone()["to_all"]
check("받아 올 때 원문 받는 사람 전원 저장(to_all)", "jay@semco.example" in ta and "kim@partner.example" in ta, ta)
hr = k.get("/mail/compose?replyall=%d" % src).text
import re as _re
mcc = _re.search(r'id="cCc"[^>]*value="([^"]*)"', hr)
ccv = (mcc.group(1) if mcc else "").replace("&#34;", '"').replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
check("전체 답장 참조 = 원래 받는 사람(나 빼고) + 참조 · 이름 속 쉼표 안 쪼개짐",
      '"Lee, Jay" <jay@semco.example>' in ccv and "kim@partner.example" in ccv and "cc1@semco.example" in ccv, ccv)
check("전체 답장: 나(이름 붙은 대문자 주소 포함)·원래 보낸 사람은 빠짐", "boss@knknara.co.kr" not in ccv.lower() and "p@semco.example" not in ccv, ccv)
check("전체 답장: 받는 사람 = 원래 보낸 사람", 'value="p@semco.example"' in hr)
check("받아 오는 두 곳 모두 to_all 넘김", open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read().count('to_all=parsed.get("to_all", "")') == 1
      and open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read().count("_mailfetch_store_all(res, acct") == 2)   # 11-27 두 가져오기 = 한 저장 함수
check("원문 해석이 To 전체를 돌려줌", '"to_all": _h("To")' in open(os.path.join(ROOT, "app", "mail_store.py"), encoding="utf-8").read())

print("== ⑩ 임시 메일 ==")
r = k.post("/mail/draft/save", data={"to": "a@a.example", "subject": "임시", "body": "표", "body_html": "<table><tr><td>단가</td></tr></table><script>x()</script>"}).json()
did = r.get("draft_id")
hd = k.get("/mail/compose?draft=%s" % did).text
check("임시 메일 다시 열면 서식 그대로(표) · 위험한 것은 걸러짐", "&lt;table" in hd and "&lt;script" not in hd, hd[hd.find("cPrefillHtml"):hd.find("cPrefillHtml") + 200])
_U["v"] = {"id": OTHER, "role": "member", "name": "시험이", "team_id": None, "team_name": ""}
k.post("/mail/draft/%s/discard" % did)
_U["v"] = {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": "", "email": "boss@knknara.co.kr"}
with _db.db_session() as c:
    still = c.execute("SELECT 1 FROM mail_messages WHERE id=?", (did,)).fetchone()
check("남이 「버리기」 해도 내 임시 메일은 안 지워짐", bool(still))
k.post("/mail/draft/%s/discard" % did)
with _db.db_session() as c:
    gone = c.execute("SELECT 1 FROM mail_messages WHERE id=?", (did,)).fetchone()
check("내 것은 버리기로 지워짐", not gone)

print("== ⑪ 자동완성 ==")
it = k.get("/api/mail/contacts?q=%EC%8B%9C%ED%97%98").json().get("items") or []
check("사내 직원도 후보(사내 표시)", any(x.get("email") == "tester@knknara.co.kr" and x.get("src") == "사내" for x in it), it)
it = k.get("/api/mail/contacts?q=semco").json().get("items") or []
check("주고받은 사람도 후보(내 메일함)", any(x.get("email") == "p@semco.example" and x.get("src") == "주고받은 메일" for x in it), it)
it = k.get("/api/mail/contacts?q=z.example").json().get("items") or []
check("남의 메일함 보낸 사람은 후보에 안 나옴", not any(x.get("email") == "z@z.example" for x in it), it)

print("== ⑫ 쓰기 화면 ==")
hc = k.get("/mail/compose").text
for nm, needle in (("주소 한 명씩 검사(화면)", "function parseAddrs("), ("보내기 전 확인 창", 'id="scWrap"'),
                   ("받는 회사 여러 곳 확인", "받는 회사가 '+order.length+'곳입니다"), ("「첨부」라 썼는데 파일 없음", "「첨부」라고 쓰셨는데 붙인 파일이 없습니다"),
                   ("빈 제목", "제목이 비어 있습니다"), ("숨은참조 알림", "숨은참조 '+P.cBcc.ok.length+'명"), ("많은 사람", "all.length>=10"),
                   ("보내기 취소 10초", "var SEND_DELAY=10;"), ("보내기 취소 단추", "↺ 보내기 취소"), ("보내기 표", "fd.append('send_token', SEND_TOKEN)"),
                   ("대용량 올리는 중 막기", "LARGE_BUSY>0"), ("대용량 실패 막기", "LARGE_FAIL>0"), ("창 닫힘 경고", "addEventListener('beforeunload'"),
                   ("취소는 묻기", "쓰던 메일을 어떻게 할까요?"), ("자동 임시저장 30초", "}, 30000);"), ("일부 못 감 화면", "보냈지만, 일부 주소에는 못 갔습니다"),
                   ("자동완성 키보드", "e.key==='ArrowDown'"), ("자동완성 이름까지", "function acFmt(it)"), ("받는 칸 = 여러 명(type=email 아님)", 'id="cTo" type="text" inputmode="email" autocomplete="off"'),
                   ("휴대폰 숨은참조 잘림 고침", "#bccToggle{margin-left:auto}")):
    check("쓰기 화면: " + nm, needle in hc, needle)
check("옛 문구 「대용량 첨부는 추후 기능」 없음", "추후 기능" not in open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read().split('@app.post("/mail/send")')[1].split("_mail_send_do")[0] + open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read().split("async def _mail_send_do")[1][:4000])

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
