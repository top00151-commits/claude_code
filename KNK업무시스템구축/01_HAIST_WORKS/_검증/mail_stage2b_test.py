# -*- coding: utf-8 -*-
"""메일 2단계-나 (대표 2026-11-19 「2-나 진행해」) — 서명 여러 개 · ⏱ 예약 발송 · 🏖 부재중 자동 응답.
운영 무접촉 · 임시 DB · 가짜 메일 서버(보내지 않고 기록만) · 가짜 주소.

증명할 것
  ① 서명: 기본 + 2개 · 이름 · 비어 있는 것은 안 나옴 · 쓰기 화면에서 고르기
  ② 예약: 틀린 주소·지난 시각·90일 넘음 거절 · 첨부(파일·전달 원래 첨부) 함께 저장 · 받은편지함·보낸편지함 목록엔 안 섞임
  ③ 예약 보내기: 때가 되면 한 번만(두 번 잡히지 않음) · 보낸 뒤 예약 줄 지움 · 보낸편지함 기록 · 첨부 그대로
  ④ 예약 실패: 상태 「못 보냄」+ 까닭 · 받은편지함에 「KNK 메일 알림」 · 지금 다시 보내기 · 취소 → 임시보관함 · 남의 예약 못 만짐
  ⑤ 자동 응답 설정: 켤 때 기간·내용 필수 · 끝이 시작보다 앞이면 거절 · 지난 기간 거절
  ⑥ 자동 응답 안 보내는 경우: 꺼짐 · 기간 밖 · 자동 발송 머리 · no-reply 주소 · 스팸 · 나를 참조로만 · 모르는 사람(아는 사람만) · 같은 사람 두 번째 · 나 자신
  ⑦ 자동 응답 보냄: 아는 사람 · 「Auto-Submitted: auto-replied」 표시 · 보낸편지함 기록 · 기록 남김
  ⑧ 원문 머리로 자동 발송 알아보기(List-Id · Precedence · Auto-Submitted)
  ⑨ 화면: 예약 단추·때 고르기 · 보낸편지함 「보낼 예정」 · 받은편지함 🏖 표시 · 설정 줄 · 설정 화면
"""
import io
import json
import os
import re
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
    _TMP = tempfile.mkdtemp(prefix="knk_ms2b_")
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
        print("  [FAIL]", name, "<-", str(extra)[:500])


SENT = []
FAIL_SMTP = [False]


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
        if FAIL_SMTP[0]:
            raise smtplib.SMTPRecipientsRefused({a: (550, b"no such user") for a in to_addrs})
        SENT.append((list(to_addrs), msg))
        return {}


sd.smtplib.SMTP_SSL = FakeSMTP
sd.get_send_config_for = lambda c, owner_id=None: {"host": "h", "port": 465, "user": "u", "password": "p"}
sd.system_send_ready = lambda c, owner_id=None: True

OWN, OTHER = 9301, 9302
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(9301,'kjr','시험대표','ceo',1,'x','boss@knknara.co.kr')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(9302,'t9302','시험이','member',1,'x','t2@knknara.co.kr')")
    c.execute("INSERT INTO app_settings(key,value) VALUES('mail_from_address','boss@knknara.co.kr') ON CONFLICT(key) DO UPDATE SET value=excluded.value")
U = {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": "", "email": "boss@knknara.co.kr"}
_U = {"v": dict(U)}
m.get_user = lambda req: _U["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
km = TestClient(m.app, base_url="http://127.0.0.1:5053", raise_server_exceptions=False, follow_redirects=False)
km.headers.update({"host": "kmail.knknara.co.kr", "x-forwarded-proto": "https"})
_SEQ = [0]


def put(subject, frm="p@semco.example", owner=OWN, to_all="boss@knknara.co.kr", atts=None):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="boss@knknara.co.kr", from_email=frm, from_name="보낸이", subject=subject,
                                   text="본문", owner_id=owner, run_ai=False, message_id="s2b-%d@t" % _SEQ[0],
                                   to_all=to_all, attachments=atts)
    return mid


print("== ① 서명 여러 개 ==")
k.post("/mail/signature", data={"slot": "0", "body": "기본 서명입니다"})
k.post("/mail/signature", data={"slot": "1", "name": "English", "body": "Best regards"})
with _db.db_session() as c:
    sl = ms.get_signatures(c, OWN)
check("기본 + 내용 있는 서명만(2번은 비어 있어 안 나옴) · 이름", [x["name"] for x in sl] == ["기본 서명", "English"], sl)
hs = k.get("/mail/signature?slot=1").text
check("서명 화면 탭 셋 · 이름 칸", len(re.findall(r'class="sig-tab(?: on)?"', hs)) == 3 and 'id="sigName"' in hs and 'value="English"' in hs, len(re.findall(r'class="sig-tab(?: on)?"', hs)))
hc = km.get("/mail/compose").text
check("쓰기 화면 「✍ 서명」 고르기(기본·English·서명 없음)", 'id="cSigSel"' in hc and "English" in hc and "서명 없음" in hc and "window.cmpSigSwap" in hc)

print("== ② 예약 걸기 ==")
check("틀린 주소 거절", k.post("/mail/schedule", data={"to": "bad@@x", "subject": "s", "body": "b", "at": "tom9"}).status_code == 400)
check("지난 시각 거절", k.post("/mail/schedule", data={"to": "a@b.example", "subject": "s", "body": "b", "at": "2020-01-01T09:00"}).status_code == 400)
check("90일 넘음 거절", k.post("/mail/schedule", data={"to": "a@b.example", "subject": "s", "body": "b", "at": "2099-01-01T09:00"}).status_code == 400)
FA = put("도면 송부", atts=[{"filename": "도면.pdf", "mime": "application/pdf", "size": 4, "content_id": "", "inline": False, "data": b"%PDF"}])
with _db.db_session() as c:
    fa_aid = c.execute("SELECT id FROM mail_attachments WHERE mail_id=?", (FA,)).fetchone()["id"]
r = k.post("/mail/schedule", data={"to": "홍길동 <hong@vendor.example>", "cc": "c@vendor.example", "subject": "예약 시험", "body": "내일 보냅니다",
                                   "body_html": "<p>내일 보냅니다</p>", "at": "tom9", "fwd_src": str(FA), "fwd_att": [str(fa_aid)]},
           files={"files": ("견적.xlsx", b"XLSX-FAKE", "application/octet-stream")})
j = r.json()
SID = j.get("id")
check("예약 걸기(내일 9시) · 안내 글", j.get("ok") and SID and "보낼 예정" in j.get("message", ""), j)
with _db.db_session() as c:
    row = dict(c.execute("SELECT direction, sched_state, to_email, sched_at FROM mail_messages WHERE id=?", (SID,)).fetchone())
    natt = c.execute("SELECT COUNT(*) FROM mail_attachments WHERE mail_id=?", (SID,)).fetchone()[0]
check("예약 줄 = 기다림 · 받는 사람 그대로", row["direction"] == "sched" and row["sched_state"] == "wait" and "hong@vendor.example" in row["to_email"], row)
check("첨부(새 파일 + 전달 원래 첨부) 함께 저장", natt == 2, natt)
check("받은편지함 목록에 안 섞임", ('data-mail-id="%d"' % SID) not in k.get("/mail/inbox").text)
hsent = k.get("/mail/sent").text
check("보낸편지함 위 「보낼 예정」 줄(지금 보내기 · 취소)", "보낼 예정 1통" in hsent and ('data-sid="%d"' % SID) in hsent and "mbxSched(%d,'cancel')" % SID in hsent)
check("숫자 API 예약 1", k.get("/api/mail/counts?lite=1").json().get("sched") == 1)

print("== ③ 예약 보내기 ==")
SENT.clear()
m._mail_sched_run_once()
check("때가 안 됐으면 안 보냄", not SENT)
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET sched_at=datetime('now','localtime','-1 minutes') WHERE id=?", (SID,))
with _db.db_session() as c:
    first = ms.claim_scheduled(c, SID)
    second = ms.claim_scheduled(c, SID)
    c.execute("UPDATE mail_messages SET sched_state='wait' WHERE id=?", (SID,))
check("한 번만 잡힘(두 번 안 보냄)", first and not second)
m._mail_sched_run_once()
check("때가 되면 보냄 · 받는 사람 전원", len(SENT) == 1 and SENT[0][0] == ["hong@vendor.example", "c@vendor.example"], SENT[0][0] if SENT else None)
names = [p.get_filename() for p in SENT[0][1].iter_attachments()] if SENT else []
check("첨부 그대로(견적.xlsx · 도면.pdf)", sorted(names) == sorted(["견적.xlsx", "도면.pdf"]), names)
with _db.db_session() as c:
    gone = c.execute("SELECT 1 FROM mail_messages WHERE id=?", (SID,)).fetchone()
    out = c.execute("SELECT to_email FROM mail_messages WHERE user_id=? AND direction='out' AND subject='예약 시험'", (OWN,)).fetchone()
check("보낸 뒤 예약 줄 지움 · 보낸편지함에 기록", not gone and out and "hong@vendor.example" in out["to_email"], out and dict(out))
m._mail_sched_run_once()
check("다시 돌려도 또 안 보냄", len(SENT) == 1)

print("== ④ 예약 실패·취소 ==")
j = k.post("/mail/schedule", data={"to": "x@vendor.example", "subject": "실패 시험", "body": "b", "at": "tom8"}).json()
S2 = j["id"]
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET sched_at=datetime('now','localtime','-1 minutes') WHERE id=?", (S2,))
FAIL_SMTP[0] = True
m._mail_sched_run_once()
FAIL_SMTP[0] = False
with _db.db_session() as c:
    st = dict(c.execute("SELECT sched_state, sched_err FROM mail_messages WHERE id=?", (S2,)).fetchone())
    notice = c.execute("SELECT subject FROM mail_messages WHERE user_id=? AND direction='in' AND from_name='KNK 메일 알림'", (OWN,)).fetchone()
check("실패 → 「못 보냄」 + 까닭", st["sched_state"] == "fail" and st["sched_err"], st)
check("받은편지함에 「KNK 메일 알림」(못 보냄)", notice and "보내지 못했습니다" in notice["subject"], notice and dict(notice))
check("보낸편지함 줄에 「⚠ 못 보냄」 · 지금 다시 보내기", "⚠ 못 보냄" in k.get("/mail/sent").text and "지금 다시 보내기" in k.get("/mail/sent").text)
_U["v"] = {"id": OTHER, "role": "member", "name": "시험이", "team_id": None, "team_name": ""}
oc = k.post("/mail/sched/%d/cancel" % S2).json()
_U["v"] = dict(U)
check("남의 예약은 취소 못 함", not oc.get("ok"))
SENT.clear()
j = k.post("/mail/sched/%d/now" % S2).json()
check("지금 다시 보내기 → 바로 보냄", j.get("ok") and len(SENT) == 1, (j, len(SENT)))
j = k.post("/mail/schedule", data={"to": "y@vendor.example", "subject": "취소 시험", "body": "b", "at": "nextmon9"}).json()
S3 = j["id"]
j = k.post("/mail/sched/%d/cancel" % S3).json()
with _db.db_session() as c:
    d = c.execute("SELECT direction FROM mail_messages WHERE id=?", (S3,)).fetchone()
check("취소 → 📝 임시보관함으로(지우지 않음)", j.get("ok") and d and d["direction"] == "draft", (j, d and dict(d)))

print("== ⑤ 자동 응답 설정 ==")
check("켤 때 기간 필수", k.post("/mail/autoreply", data={"enabled": "1", "body": "x"}).status_code == 400)
check("끝이 시작보다 앞이면 거절", k.post("/mail/autoreply", data={"enabled": "1", "start_date": "2026-12-05", "end_date": "2026-12-01", "body": "x"}).status_code == 400)
check("지난 기간 거절", k.post("/mail/autoreply", data={"enabled": "1", "start_date": "2020-01-01", "end_date": "2020-01-02", "body": "x"}).status_code == 400)
today = m._mail_local_today(9)
j = k.post("/mail/autoreply", data={"enabled": "1", "start_date": today, "end_date": "2099-12-31", "body": "출장 중입니다", "only_known": "1"}).json()
check("켜기", j.get("ok"), j)

print("== ⑥ ⑦ 자동 응답 판단·보냄 ==")
with _db.db_session() as c:
    c.execute("INSERT INTO shared_contacts(name, email, created_by, visibility) VALUES('박구매','p@semco.example',9301,'company')")
KN = put("견적 요청", frm="p@semco.example")
UNK = put("처음 연락", frm="stranger@unknown.example")
NOREP = put("알림", frm="no-reply@service.example")
CC = put("참조 메일", frm="p@semco.example", to_all="other@semco.example")
AUTO = put("뉴스", frm="p@semco.example")
SELF = put("나에게", frm="boss@knknara.co.kr")
SENT.clear()
m._mail_autoreply_run(dict(U), [(KN, False), (UNK, False), (NOREP, False), (CC, False), (AUTO, True), (SELF, False)])
check("아는 사람 한 통에만 보냄(모르는 사람·no-reply·참조만·자동 발송·나 자신 = 안 보냄)", len(SENT) == 1 and SENT[0][0] == ["p@semco.example"], [s_[0] for s_ in SENT])
mm = SENT[0][1] if SENT else None
check("자동 응답 표시 머리(Auto-Submitted: auto-replied · X-Auto-Response-Suppress)", mm is not None and mm["Auto-Submitted"] == "auto-replied" and mm["X-Auto-Response-Suppress"] == "All")
check("제목 「[자동 회신] 원래 제목」 · 내용", mm is not None and mm["Subject"].startswith("[자동 회신] 견적 요청") and "출장 중입니다" in mm.get_body(("plain",)).get_content())
KN2 = put("두 번째 메일", frm="p@semco.example")
SENT.clear()
m._mail_autoreply_run(dict(U), [(KN2, False)])
check("같은 사람에게 이번 기간 두 번째는 안 보냄", not SENT)
with _db.db_session() as c:
    why = ms.autoreply_should(c, OWN, ms.get_mail(c, UNK, OWN), today, {"boss@knknara.co.kr"})[1]
    c.execute("UPDATE mail_messages SET is_blocked=1 WHERE id=?", (UNK,))
    why_b = ms.autoreply_should(c, OWN, ms.get_mail(c, UNK, OWN), today, {"boss@knknara.co.kr"})[1]
check("까닭: 모르는 사람 · 스팸", "모르는 사람" in why and "스팸" in why_b, (why, why_b))
k.post("/mail/autoreply", data={"enabled": "1", "start_date": today, "end_date": "2099-12-31", "body": "출장 중입니다", "only_known": "0"})
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET is_blocked=0 WHERE id=?", (UNK,))
SENT.clear()
m._mail_autoreply_run(dict(U), [(UNK, False)])
check("「모든 사람」이면 모르는 사람에게도(스팸·자동 발송 빼고)", len(SENT) == 1)
k.post("/mail/autoreply", data={"enabled": "0"})
NEWM = put("꺼진 뒤", frm="z@zz.example")
SENT.clear()
m._mail_autoreply_run(dict(U), [(NEWM, False)])
check("끄면 안 보냄", not SENT)
with _db.db_session() as c:
    outs = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='out' AND subject LIKE '[자동 회신]%'", (OWN,)).fetchone()[0]
check("보낸 자동 응답은 보낸편지함에 남음", outs == 2, outs)

print("== ⑧ 원문 머리로 자동 발송 알아보기 ==")
def raw(h):
    return ("From: a@x.example\r\nTo: boss@knknara.co.kr\r\nSubject: t\r\n" + h + "\r\n\r\nbody").encode()
check("List-Id · Precedence: bulk · Auto-Submitted → 자동 발송",
      ms.parse_raw_email(raw("List-Id: <news.x>\r\n"))["auto_hdr"] and ms.parse_raw_email(raw("Precedence: bulk\r\n"))["auto_hdr"]
      and ms.parse_raw_email(raw("Auto-Submitted: auto-replied\r\n"))["auto_hdr"])
check("보통 메일 · Auto-Submitted: no → 사람 메일", not ms.parse_raw_email(raw("X-Mailer: Outlook\r\n"))["auto_hdr"] and not ms.parse_raw_email(raw("Auto-Submitted: no\r\n"))["auto_hdr"])
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("받아 온 뒤(저장 끝난 뒤) 자동 응답 부름 · 새 메일만", "_mail_autoreply_run(owner_user, _ar_cand)" in src and "if mid > _ar_max:" in src)
check("예약 시계 = 메일 수집 서버에서만 · 나스 백업 시간엔 쉼", "_sch_th.Timer(90, _mail_sched_tick)" in src and "if not _nas_quiet_now():" in src)

print("== ⑨ 화면 ==")
check("쓰기 화면 「⏱ 예약」 · 때 고르기(내일 8·9·14시 · 다음 주 월 · 직접 = 웍스 달력 — 11-19 고른 뒤 확인 → 보내기)", 'id="cSchedBtn"' in hc and "cmpSchedQuick(\\'tom8\\',this)" in hc and "cmpSchedQuick(\\'nextmon9\\',this)" in hc and 'id="scDate"' in hc)
k.post("/mail/autoreply", data={"enabled": "1", "start_date": today, "end_date": "2099-12-31", "body": "출장 중입니다"})
hi = km.get("/mail/inbox").text
check("받은편지함 위 「🏖 부재중 자동 응답 켜짐」(설정·끄기)", 'class="mbx-arbar' in hi and "부재중 자동 응답 켜짐" in hi and 'href="/mail/autoreply"' in hi)
tl = km.get("/mail/tools").text
check("설정·정리 「🏖 부재중 자동 응답」 줄(켜짐·기간) · 서명 개수", 'href="/mail/autoreply"' in tl and "켜짐" in tl and "· 2개" in tl)
ar = km.get("/mail/autoreply").text
check("설정 화면: 켜기·기간·제목·내용·누구에게·안 보내는 경우 안내", all(x in ar for x in ('id="arOn"', 'id="arStart"', 'id="arEnd"', 'id="arSubj"', 'id="arBody"', 'name="arWho"', "이럴 때는 보내지 않습니다")))

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
