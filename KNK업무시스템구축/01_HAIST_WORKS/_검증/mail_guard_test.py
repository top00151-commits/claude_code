# -*- coding: utf-8 -*-
"""📮 스팸·피싱 판별 시험 — 전부 가짜 메일(실제 메일·주소·첨부 없음 · 운영 무접촉 · 링크 접속 없음).
① 위험한 메일을 잡는가  ② ⭐정상 업무 메일을 잘못 잡지 않는가(오탐)  ③ 저장·격리·화면까지 이어지는가
사용: py -3.13 _검증/mail_guard_test.py"""
import io
import os
import sqlite3
import sys
import tempfile
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_guard_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    from app import mail_guard as g
    from app import mail_store as ms
finally:
    sys.stdout = _so

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:300])


def A(**k):
    k.setdefault("staff_names", ("홍길동", "김철수"))
    return g.assess(**k)


LINK = '<a href="%s">%s</a>'
print("§1 위험한 메일을 잡는가")
lv, n = A(from_email="ceo@knknara.co.kr", from_name="대표", subject="급한 송금", body="오늘 안에 송금", auth={"spf": "fail", "dmarc": "fail"})
check("우리 회사 주소인데 인증 실패 → 위험(3) · 격리", lv == 3 and "회사 사칭" in n and g.should_quarantine("ceo@knknara.co.kr", None, {"dmarc": "fail"}, lv), (lv, n))
for dom in ("knknara.co.kr.evil.com", "knknara-co.kr", "knknarra.co.kr", "kmknara.co.kr", "knknara.com", "xn--knknar-0wa.co.kr"):
    lv, n = A(from_email="sales@" + dom, subject="견적", body="확인 바랍니다")
    check("우리 회사 흉내 주소 %-26s → 위험(3) · 격리" % dom, lv == 3 and g.should_quarantine("sales@" + dom, None, None, lv), (lv, n))
lv, n = A(from_email="hong123@gmail.com", from_name="홍길동 부장", subject="자료", body="확인")
check("직원 이름 + 개인 무료 메일 → 의심(2)", lv == 2 and "사칭" in n, (lv, n))
lv, n = A(from_email="boss@naver.com", from_name="KNK 대표이사", subject="급히", body="연락 바람")
check("회사·대표 이름 + 개인 무료 메일 → 의심(2)", lv == 2, (lv, n))
lv, n = A(from_email="kim@partner-a.example", reply_to="kim.partner.a@gmail.com", subject="입금 계좌 변경 안내", body="새 계좌로 송금 부탁드립니다")
check("회사 주소로 보내고 답장은 개인 메일 + 계좌 변경 → 의심(2) · 전화 확인 안내", lv == 2 and "전화로" in n and "답장이 다른 곳" in n, (lv, n))
lv, n = A(from_email="acc@vendor.example", subject="Payment", body="Please note our bank account has changed. Remit to our new account.")
check("영문 계좌 변경 요구 → 의심(2)", lv == 2 and "계좌 변경" in n, (lv, n))
lv, n = A(from_email="it@mailer.example", subject="메일함 용량 초과", body="즉시 로그인하세요", html=LINK % ("http://203.0.113.9/login", "https://kmail.knknara.co.kr"))
check("보이는 주소(우리 메일) ≠ 실제(IP) + 로그인 요구 → 의심(2)", lv == 2 and "다름" in n and "IP" in n, (lv, n))
lv, n = A(from_email="a@x.example", subject="확인", body="여기 https://bit.ly/abc 비밀번호 확인 긴급")
check("단축 주소 + 비밀번호 + 긴급 → 의심(2)", lv == 2 and "단축 주소" in n, (lv, n))
lv, n = A(from_email="a@x.example", subject="t", body="t", html=LINK % ("https://knknara.co.kr@evil.example/x", "열기"))
check("주소 안 '@' 속임수 → 의심(2)", lv == 2 and "'@'" in n, (lv, n))
for fn, word in (("견적서.pdf.exe", "위장"), ("invoice.xlsx.scr", "위장"), ("setup.exe", "실행파일"), ("주문.lnk", "실행파일"), ("a.iso", "실행파일")):
    att = [{"filename": fn}]
    lv, n = A(from_email="a@x.example", subject="견적", body="첨부", attachments=att)
    check("첨부 %-18s → 위험(3) · 격리" % fn, lv == 3 and word in n and g.should_quarantine("a@x.example", att, None, lv), (lv, n))
lv, n = A(from_email="a@x.example", subject="발주", body="첨부", attachments=[{"filename": "PO.xlsm"}])
check("회사 밖 매크로 문서 → 의심(2) · 격리는 안 함", lv == 2 and "매크로" in n and not g.should_quarantine("a@x.example", [{"filename": "PO.xlsm"}], None, lv), (lv, n))
lv, n = A(from_email="a@x.example", subject="문서", body="첨부", attachments=[{"filename": "scan.html"}])
check("웹페이지 파일 첨부 → 의심(2)", lv == 2 and "웹페이지" in n, (lv, n))
lv, n = A(from_email="a@x.example", subject="자료", body="압축 비밀번호: 1234", attachments=[{"filename": "doc.zip"}])
check("비밀번호 걸린 압축파일 → 의심(2)", lv == 2 and "압축파일" in n, (lv, n))
lv, n = A(from_email="a@x.example", subject="hi", body="hi", auth={"dmarc": "fail"})
check("외부 DMARC 실패 → 의심(2)", lv == 2, (lv, n))

print("\n§2 ⭐정상 업무 메일을 잘못 잡지 않는가(오탐)")
OKAUTH = {"spf": "pass", "dkim": "pass", "dmarc": "pass"}
lv, n = A(from_email="hong@knknara.co.kr", from_name="홍길동", subject="회의 자료", body="첨부 확인 바랍니다 https://works.knknara.co.kr/home", auth=OKAUTH)
check("사내 메일(링크 포함) → 안전(0) · 이유 없음", lv == 0 and n == "", (lv, n))
lv, n = A(from_email="hong@knknara.co.kr", from_name="홍길동", subject="설치 파일", body="첨부", attachments=[{"filename": "tool.exe"}], auth=OKAUTH)
check("사내 동료가 보낸 실행파일 → 경고는 하되(3) 격리하지 않는다", lv == 3 and not g.should_quarantine("hong@knknara.co.kr", [{"filename": "tool.exe"}], OKAUTH, lv), (lv, n))
lv, n = A(from_email="hong@knknara.co.kr", subject="t", body="t")
check("사내 메일 · 인증 머리글이 없어도(판단 재료 없음) 격리하지 않는다", lv == 0, (lv, n))
lv, n = A(from_email="kim@partner-a.example", from_name="김영업", subject="견적서 송부", body="견적서 첨부드립니다. 검토 부탁드립니다.", attachments=[{"filename": "견적서.pdf"}, {"filename": "도면.dwg"}], auth=OKAUTH)
check("거래처 견적 메일(PDF·도면) → 외부(1)까지만", lv == 1 and n == "외부 발신", (lv, n))
lv, n = A(from_email="tax@vendor.example", subject="세금계산서 발행 안내", body="결제 계좌는 기존과 동일합니다. 입금 확인 부탁드립니다.", attachments=[{"filename": "세금계산서.pdf"}])
check("세금계산서 · 「계좌는 기존과 동일」 → 외부(1)까지만(계좌 변경 아님)", lv == 1, (lv, n))
lv, n = A(from_email="news@brand.example", subject="뉴스레터", body="소식", html=LINK % ("https://click.mailer.example/t/abc", "www.brand.example") + LINK % ("https://brand.example/a", "자세히 보기"), reply_to="support@brand.example")
check("뉴스레터(추적 링크 = 보이는 주소와 다름) → 경고까지만 · ⭐격리하지 않는다", lv <= 2 and not g.should_quarantine("news@brand.example", None, None, lv), (lv, n))
lv, n = A(from_email="noreply@ticket.example", reply_to="case-123@support-desk.example", subject="접수 안내", body="문의가 접수되었습니다")
check("접수 시스템(답장 주소가 다른 회사) → 외부(1) 표시만", lv == 1 and "답장이 다른 곳" in n, (lv, n))
lv, n = A(from_email="a@list.example", subject="공지", body="안내", auth={"spf": "softfail", "dkim": "pass"})
check("전달된 메일(SPF softfail · DKIM 통과) → 외부(1) 표시만", lv == 1, (lv, n))
lv, n = A(from_email="qa@lab.example", subject="ISO 인증 심사 일정", body="인증 심사 일정 안내드립니다. 계정 담당자 확인 https://lab.example/schedule")
check("「인증·계정」 낱말이 있어도 평범한 업무 메일 → 외부(1)까지만", lv == 1, (lv, n))
lv, n = A(from_email="drive@files.example", subject="자료 공유", body="자료", attachments=[{"filename": "도면모음.zip"}])
check("압축파일만(비밀번호 안내 없음) → 외부(1) 표시만", lv == 1 and "압축파일" in n, (lv, n))
lv, n = A(from_email="kim@samsung.com", from_name="김철수 책임", subject="회의", body="회의 일정")
check("거래처 사람 이름이 우리 직원과 같아도(회사 주소) → 표시(1)까지만", lv == 1, (lv, n))
for dom in ("knk-partner.example", "nara.co.kr", "kkk.co.kr", "naver.com", "partner.co.kr"):
    check("흉내 주소 아님: %s" % dom, g.lookalike_of_ours(dom) == "", g.lookalike_of_ours(dom))
check("흉내 주소 판정에서 우리 주소·하위 주소는 제외", g.lookalike_of_ours("knknara.co.kr") == "" and g.lookalike_of_ours("mail.knknara.co.kr") == "")

print("\n§3 재료 읽기 · 링크 막기")
check("인증 결과 읽기(여러 줄 · 대소문자 · 맨 위 것 우선)",
      g.parse_auth_results(["mx.example; spf=PASS smtp.mailfrom=a; dkim=fail header.d=x; dmarc=fail", "old; spf=fail"]) == {"spf": "pass", "dkim": "fail", "dmarc": "fail"})
check("인증 머리글 없음 → 빈 값(판단하지 않음)", g.parse_auth_results([]) == {} and g.parse_auth_results(None) == {})
d = g.defang_links_html('<p>보기 ' + LINK % ("https://evil.example/x?a=1&b=2", "<b>여기</b>") + ' 끝</p>')
check("링크 막기: <a> 가 사라지고 글자는 남고 실제 주소는 설명글로", "<a" not in d and "<b>여기</b>" in d and "evil.example" in d and "cursor:not-allowed" in d, d)
d2 = g.defang_links_html('<a href="x&quot; onmouseover=&quot;alert(1)">t</a><a href=\'https://a.example/"><script>x\'>t2</a>')
check("링크 막기가 새 태그·속성을 만들지 않는다", "<script" not in d2 and "<a" not in d2 and d2.count('title="') == d2.count("</span>") - d2.count("[a.example]</span>"), d2)

print("\n§4 저장까지 — 원문(가짜) → 해석 → 저장 → 차단함/받은편지함")
con = sqlite3.connect(":memory:")
con.row_factory = sqlite3.Row
con.executescript("""
CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, email TEXT, is_active INTEGER DEFAULT 1);
INSERT INTO users(id,name,email) VALUES(1,'홍길동','hong@knknara.co.kr');
""")
# 메일 표는 운영 스키마(app/database.py) 글자 그대로 만든다 — 시험용으로 줄인 표를 쓰지 않는다
import re as _re  # noqa: E402
_src = io.open(os.path.join(ROOT, "app", "database.py"), encoding="utf-8").read()
for _t in ("mail_messages", "mail_attachments"):
    _mo = _re.search(r"CREATE TABLE IF NOT EXISTS %s \(.*?\n\);" % _t, _src, _re.S)
    con.executescript(_mo.group(0))


def raw(frm, subj, body, *, auth=None, reply_to=None, att=None, html=None):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Message-ID"] = frm, "hong@knknara.co.kr", subj, "<%s@t>" % abs(hash((frm, subj)))
    if auth:
        m["Authentication-Results"] = auth
    if reply_to:
        m["Reply-To"] = reply_to
    m.set_content(body)
    if html:
        m.add_alternative(html, subtype="html")
    if att:
        m.add_attachment(b"FAKE", maintype="application", subtype="octet-stream", filename=att)
    return m.as_bytes()


def put(rawmsg):
    p = ms.parse_raw_email(rawmsg)
    mid, _o = ms.store_inbound(con, to_email=p["to_email"], from_email=p["from_email"], from_name=p["from_name"], subject=p["subject"],
                               text=p["text"], html=p["html"], owner_id=1, run_ai=False, attachments=p["attachments"],
                               message_id=p["message_id"], auth=p.get("auth"), reply_to=p.get("reply_to", ""))
    return dict(con.execute("SELECT * FROM mail_messages WHERE id=?", (mid,)).fetchone()), p


r, p = put(raw("대표 <ceo@knknara.co.kr>", "송금", "오늘 송금", auth="mx; spf=fail; dmarc=fail"))
check("원문의 인증 결과를 읽어 넘긴다 → 위험(3) · 차단함(is_blocked=1)", p["auth"] == {"spf": "fail", "dmarc": "fail"} and r["risk_level"] == 3 and r["is_blocked"] == 1, (p.get("auth"), r["risk_level"], r["is_blocked"]))
r, p = put(raw("Kim <kim@partner-a.example>", "계좌", "새 계좌로 송금", reply_to="x@gmail.com"))
check("원문의 답장 주소를 읽어 넘긴다 → 의심(2) · 받은편지함에 남고 ⚠", p["reply_to"] == "x@gmail.com" and r["risk_level"] == 2 and r["is_blocked"] == 0, (p.get("reply_to"), r["risk_level"]))
r, p = put(raw("a@x.example", "견적", "첨부", att="견적서.pdf.exe"))
check("위장 실행파일 → 차단함", r["risk_level"] == 3 and r["is_blocked"] == 1, (r["risk_level"], r["is_blocked"], r["risk_note"]))
r, p = put(raw("홍길동 <hong@knknara.co.kr>", "도구", "첨부", att="tool.exe", auth="mx; spf=pass; dkim=pass; dmarc=pass"))
check("⭐사내 동료의 실행파일 → 받은편지함에 남는다(경고만)", r["risk_level"] == 3 and r["is_blocked"] == 0, (r["risk_level"], r["is_blocked"]))
r, p = put(raw("김영업 <kim@partner-a.example>", "견적서 송부", "견적서 첨부드립니다", att="견적서.pdf", auth="mx; spf=pass; dkim=pass; dmarc=pass"))
check("⭐정상 거래처 메일 → 받은편지함 · 외부(1) · ⚠ 없음", r["risk_level"] == 1 and r["is_blocked"] == 0, (r["risk_level"], r["risk_note"]))
inbox = [x["subject"] for x in ms.list_inbox(con, 1)]
blocked = [x["subject"] for x in ms.list_blocked(con, 1)]
check("받은편지함 3통 · 차단함 2통으로 나뉜다(차단함은 복구 가능 · 지우지 않음)", sorted(inbox) == sorted(["계좌", "도구", "견적서 송부"]) and sorted(blocked) == sorted(["송금", "견적"]), (inbox, blocked))
ms.set_blocked(con, 1, con.execute("SELECT id FROM mail_messages WHERE subject='견적'").fetchone()[0], False)
check("차단함에서 꺼내면 받은편지함으로 돌아온다", "견적" in [x["subject"] for x in ms.list_inbox(con, 1)])
lv, n = ms.assess_risk("a@x.example", "", "s", "b", "", [{"filename": "a.exe"}])
check("옛 호출 모양(인자 6개)도 그대로 동작", lv == 3 and "실행파일" in n, (lv, n))
h = ms.sanitize_html_for_view('<p><a href="https://evil.example/">go</a><script>x()</script></p>', 1, [], defang=True)
h0 = ms.sanitize_html_for_view('<p><a href="https://ok.example/">go</a></p>', 1, [])
check("의심 메일 보기 = 링크 막힘 · 보통 메일 보기 = 링크 그대로", "<a" not in h and "<script" not in h and '<a href="https://ok.example/">' in h0, (h, h0))

from jinja2 import Environment, FileSystemLoader  # noqa: E402
t = Environment(loader=FileSystemLoader(os.path.join(ROOT, "app", "templates")), autoescape=True).get_template("_v5_partials/mail_view_body.html")


class M(dict):
    __getattr__ = dict.get


def render(level, note):
    return t.render(m=M(id=1, subject="s", category="일반", risk_level=level, risk_note=note, body_text="b", from_email="a@x", from_name="a"),
                    safe_html="", has_html=False, file_atts=[], sender_contact=None, is_admin=False, ai_on=False, user=None)


v3 = render(3, "우리 회사 주소(knknara.co.kr)를 흉내 낸 주소(knknarra.co.kr) / 실행파일 첨부(a.exe)")
check("읽기 화면: 위험(3) = 「차단함으로 옮겼습니다」 · 이유가 줄마다", "차단함으로 옮겼습니다" in v3 and v3.count("<li>") == 2 and "전화로 확인" in v3, v3[:400])
v2 = render(2, "송금·계좌 변경 요구 — 반드시 전화로 거래처에 직접 확인")
check("읽기 화면: 의심(2) = 「피싱·사칭 의심 메일」", "피싱·사칭 의심 메일" in v2 and v2.count("<li>") == 1)
check("읽기 화면: 이유 글에 태그가 섞여도 그대로 글자로(끼워넣기 불가)", "<script>alert(1)" not in render(2, "<script>alert(1)</script>") and "&lt;script&gt;alert(1)" in render(2, "<script>alert(1)</script>"))
check("읽기 화면: 외부(1)는 옛 안내 그대로 · 안전(0)은 안내 없음", "외부에서 온 메일입니다" in render(1, "외부 발신") and "mv-warn" not in render(0, ""))

print("\n결과: PASS %d / FAIL %d" % (P, F))
sys.exit(1 if F else 0)
