# -*- coding: utf-8 -*-
"""📇 메일 서명 → 주소록 채우기 시험 — 전부 가짜 메일·가짜 사람(실제 메일·번호 없음 · 운영 무접촉).
① 여러 꼴의 서명에서 칸을 맞게 읽는가  ② ⭐답장에 딸려 온 옛 글(우리 직원 서명)을 읽지 않는가
③ 서명이 없으면 틀린 값을 채우지 않는가  ④ 같은 도메인 기존 연락처로 회사·거래처를 한 곳일 때만 고르는가
사용: py -3.13 _검증/mail_signature_test.py"""
import io
import os
import sqlite3
import sys
import tempfile

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
    _TMP = tempfile.mkdtemp(prefix="knk_sig_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    from app import mail_signature as sg
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
        print("  [FAIL]", name, "<-", str(extra)[:400])


def D(body, name="", email="", html=""):
    return sg.draft_from_mail({"body_text": body, "body_html": html, "from_name": name, "from_email": email})


def want(tag, d, **exp):
    f = d["fields"]
    for k, v in exp.items():
        check("%s · %s = %s" % (tag, k, v or "(빈 칸)"), (f.get(k) or "") == v, "실제=%r / 서명=%r" % (f.get(k), d.get("sig_text")))


print("== 1. 한국 회사 서명(라벨 있음) ==")
d = D("""안녕하세요, 견적서 송부드립니다.
검토 부탁드립니다.

감사합니다.

홍길동 부장
㈜가나다전자 구매팀
Tel. 031-000-1234  Fax. 031-000-1235
Mobile. 010-0000-1234
E-mail. gildong@ganada-elec.example
주소: 경기도 화성시 가나다로 12, 3층
""", "홍길동", "gildong@ganada-elec.example")
want("라벨", d, name="홍길동", position="부장", company="㈜가나다전자", department="구매팀",
     mobile="010-0000-1234", phone="031-000-1234", fax="031-000-1235",
     email="gildong@ganada-elec.example", address="경기도 화성시 가나다로 12, 3층")

print("== 2. 라벨 없는 서명 ==")
d = D("""자료 보내드립니다.

감사합니다.
김철수 과장
주식회사 라마바산업
영업1팀
010-0000-5678
02-000-1111
서울특별시 금천구 라마바로 100 5층
""", "김철수 과장", "cs.kim@lamaba.example")
want("무라벨", d, name="김철수", position="과장", company="주식회사 라마바산업", department="영업1팀",
     mobile="010-0000-5678", phone="02-000-1111", address="서울특별시 금천구 라마바로 100 5층")

print("== 3. 한 줄에 여러 항목(| · /) ==")
d = D("""회신드립니다.

이영희 대리 | 품질관리팀 | (주)사아자테크
T. 02-000-2222 | M. 010-0000-9999 | F. 02-000-2223
""", "이영희", "yh.lee@saaja.example")
want("한 줄", d, name="이영희", position="대리", company="(주)사아자테크", department="품질관리팀",
     mobile="010-0000-9999", phone="02-000-2222", fax="02-000-2223")

d = D("""수고하세요.

**************************
부장 한직책 / 영업부
(주)별표산업
핸드폰 : 010-0000-3333
사무실 : 032-000-4444 (내선 12)
팩스 : 032-000-4445
본사: 인천광역시 남동구 별표로 9
**************************
""", "", "p@star.example")
want("직책이 앞·별표 가름줄", d, name="한직책", position="부장", company="(주)별표산업", department="영업부",
     mobile="010-0000-3333", phone="032-000-4444", fax="032-000-4445", address="인천광역시 남동구 별표로 9")

d = D("""검토 부탁드립니다.

홍길동 드림

가나다전자㈜ 구매팀 홍길동 부장
TEL 031-000-1234 / FAX 031-000-1235 / HP 010.0000.1234
(18000) 경기도 화성시 가나다로 12
www.ganada.example
""", "홍길동", "a@ganada.example")
want("드림 뒤 한 줄 서명", d, name="홍길동", position="부장", company="가나다전자㈜", department="구매팀",
     mobile="010-0000-1234", phone="031-000-1234", fax="031-000-1235", address="(18000) 경기도 화성시 가나다로 12")

print("== 4. 영문 서명 · 해외 번호 ==")
d = D("""Please find the attached PO.

Best regards,
John Smith
Sales Manager
Example Parts Co., Ltd.
T: +82-2-000-3333 / M: +82 10-0000-4444
Address: 12 Example-ro, Gangnam-gu, Seoul
""", "John Smith", "john@exampleparts.example")
want("영문", d, name="John Smith", position="Sales Manager", company="Example Parts Co., Ltd.",
     mobile="010-0000-4444", phone="02-000-3333", address="12 Example-ro, Gangnam-gu, Seoul")

d = D("""Dear Mr. Kim,

Thanks,
Nguyen Van An
Purchasing Manager
Example Vina Co., Ltd
Mobile: +84 90 000 1234
Tel: +84 24 0000 5678
""", "Nguyen Van An", "an.nv@examplevina.example")
want("베트남", d, name="Nguyen Van An", position="Purchasing Manager", mobile="+84 90 000 1234", phone="+84 24 0000 5678")
check("베트남 · 회사에 Co., Ltd 포함", "Example Vina" in d["fields"]["company"], d["fields"]["company"])

print("== 5. ⭐답장 — 옛 글(우리 직원 서명)은 읽지 않는다 ==")
QUOTE_OURS = """
-----Original Message-----
From: 박우리 <woori@knknara.co.kr>
Sent: Monday, November 16, 2026 9:00 AM
To: 최바깥
Subject: 견적 요청

안녕하세요. 견적 요청드립니다.

박우리 차장
㈜케이엔케이 기술영업팀
M. 010-1111-0000
woori@knknara.co.kr
"""
d = D("네 확인했습니다. 내일 회신드리겠습니다." + QUOTE_OURS, "최바깥", "out@other-co.example")
check("답장(서명 없음) → 서명 글 없음", d["sig_text"] == "", d["sig_text"])
want("답장(서명 없음)", d, name="최바깥", mobile="", company="", position="", email="out@other-co.example")

d = D("""네 확인했습니다.

감사합니다.
최바깥 팀장
(주)다른회사
M. 010-0000-7777
""" + QUOTE_OURS, "최바깥", "out@other-co.example")
want("답장(본인 서명 있음)", d, name="최바깥", position="팀장", company="(주)다른회사", mobile="010-0000-7777")

d = D("""확인했습니다.

2026년 11월 16일 (월) 오전 9:00, 박우리 <woori@knknara.co.kr>님이 작성:
> 견적 요청드립니다.
> 박우리 차장
> M. 010-1111-0000
""", "최바깥", "out@other-co.example")
want("지메일식 인용", d, mobile="", position="")

d = D("""확인했습니다.

보낸 사람: 박우리 <woori@knknara.co.kr>
보낸 날짜: 2026년 11월 16일 월요일 오전 9:00
받는 사람: 최바깥
제목: 견적 요청

박우리 차장 / ㈜케이엔케이
M. 010-1111-0000
""", "최바깥", "out@other-co.example")
want("아웃룩 한글 머리", d, mobile="", position="", company="")

# 인용 표시가 전혀 없는데 우리 서명이 딸려 온 경우 — 서명 줄의 메일 주소가 우리 것이면 버린다
d = D("""확인했습니다.

박우리 차장
㈜케이엔케이 기술영업팀
M. 010-1111-0000
woori@knknara.co.kr
""", "최바깥", "out@other-co.example")
want("표시 없는 우리 서명", d, name="최바깥", mobile="", position="", company="")

print("== 6. HTML 메일(표로 된 서명 · 인용 묶음) ==")
HTML = """<html><body><div>자료 송부드립니다.</div><div>감사합니다.</div>
<table><tr><td><b>정민수</b> 차장</td></tr><tr><td>㈜바사아엔지니어링 설계팀</td></tr>
<tr><td>Tel</td><td>: 051-000-1234</td></tr><tr><td>H.P</td><td>: 010-0000-2468</td></tr>
<tr><td>부산광역시 강서구 바사아로 77</td></tr></table>
<blockquote><p>박우리 차장</p><p>M. 010-1111-0000</p><p>woori@knknara.co.kr</p></blockquote>
</body></html>"""
d = D("자료 송부드립니다. 감사합니다. 정민수 차장 ㈜바사아엔지니어링 설계팀 Tel : 051-000-1234", "정민수", "ms@basaa.example", html=HTML)
want("HTML 표", d, name="정민수", position="차장", company="㈜바사아엔지니어링", department="설계팀",
     mobile="010-0000-2468", phone="051-000-1234", address="부산광역시 강서구 바사아로 77")

HTML2 = """<div>확인했습니다.</div><div class="gmail_quote"><div>2026년 … 작성:</div>
<div>박우리 차장<br>M. 010-1111-0000</div></div>"""
d = D("", "최바깥", "out@other-co.example", html=HTML2)
want("HTML 지메일 인용", d, mobile="", position="")

print("== 7. 서명이 없거나 안내문만 있는 메일 — 틀린 값을 채우지 않는다 ==")
d = D("네 알겠습니다.\n\nSent from my iPhone", "한모바일", "mob@some-co.example")
check("휴대폰에서 보냄 → 서명 없음", d["sig_text"] == "", d["sig_text"])
want("휴대폰", d, name="한모바일", email="mob@some-co.example", mobile="", company="")
check("휴대폰 · 안내 글 있음", any("서명을 찾지 못했습니다" in n for n in d["notes"]), d["notes"])

d = D("""견적 건으로 연락드립니다. 010-0000-1357 로 전화 주시면 설명드리겠습니다.
납기는 2주입니다. 회의는 11월 20일 14시에 저희 회사 3층에서 진행하면 좋겠습니다.
자세한 내용은 첨부를 봐 주세요. 금액은 1,250,000원입니다. 추가 문의는 언제든 주세요.
그리고 지난번 말씀하신 사양 변경 건은 설계팀과 협의 중이며 이번 주 안에 결과를 정리해 드리겠습니다.
긴 본문이 계속 이어집니다. 긴 본문이 계속 이어집니다. 긴 본문이 계속 이어집니다. 긴 본문이 계속 이어집니다.
여기까지가 본문입니다.
그럼 이만 줄입니다.
좋은 결과 있기를 바랍니다.
내일 뵙겠습니다.
""", "오본문", "body@some-co.example")
want("본문 속 번호는 서명이 아님", d, name="오본문", position="", company="", mobile="", phone="")
check("본문 속 번호 → 서명 글 없음", d["sig_text"] == "", d["sig_text"])

d = D("""견적 감사합니다.

감사합니다.

추가로 급한 건은 010-0000-2580 으로 전화 주세요.
내일 뵙겠습니다.
""", "나추신", "ps@some-co.example")
want("맺음말 뒤 글월 속 번호", d, mobile="", phone="")

d = D("""안내드립니다.

감사합니다.
서고지 주임
(주)고지상사
M. 010-0000-8642

본 메일은 지정된 수신인만을 위한 것이며 기밀 정보를 포함하고 있을 수 있습니다. 무단 사용을 금합니다.
This e-mail is confidential and intended only for the recipient.
""", "서고지", "notice@goji.example")
want("기밀 고지문 뒤", d, name="서고지", position="주임", company="(주)고지상사", mobile="010-0000-8642")

d = D("", "", "noname@some-co.example")
want("본문·이름 없음", d, name="noname", email="noname@some-co.example")

d = D("""뉴스레터입니다.

감사합니다.
가나다 뉴스팀
수신거부는 여기를 누르세요
""", "가나다 뉴스", "news@news.example")
check("뉴스레터 꼬리 → 서명 없음", d["sig_text"] == "", d["sig_text"])

print("== 8. 머리글 이름 다듬기 ==")
for raw, nm, pos in (("홍길동 부장", "홍길동", "부장"), ("홍길동(구매팀)", "홍길동", ""), ("홍길동/구매팀/가나다", "홍길동", ""),
                     ('"홍 길 동"', "홍길동", ""), ("ABC Trading", "ABC Trading", ""), ("a@b.example", "", ""),
                     ("이사랑", "이사랑", ""), ("김대리", "김대리", ""), ("홍길동부장", "홍길동", "부장"),
                     ("부장 홍길동", "홍길동", "부장"), ("박이사 이사", "박이사", "이사")):
    r = sg._clean_header_name(raw)
    check("머리글 이름 %r → %r · %r" % (raw, nm, pos), r == (nm, pos), r)

print("== 9. 서명에 다른 메일 주소 — 보낸 주소로 채우고 알린다 ==")
d = D("""감사합니다.
유대리 대리
㈜공용상사
M. 010-0000-1111
sales@other-domain.example
""", "유대리", "yu@gongyong.example")
want("다른 주소", d, email="yu@gongyong.example", mobile="010-0000-1111")
check("다른 주소 · 알림", any("보낸 주소와 다릅니다" in n for n in d["notes"]), d["notes"])

print("== 10. 사람이 붙여 넣은 서명(다시 채우기) ==")
r = sg.draft_from_text("조붙임 이사\n㈜붙임테크\nH.P 010-0000-3333\n대전광역시 유성구 붙임로 5", "조붙임", "jo@buchim.example", is_block=True)
want("붙여 넣기", r, name="조붙임", position="이사", company="㈜붙임테크", mobile="010-0000-3333", address="대전광역시 유성구 붙임로 5")

print("== 11. 같은 도메인 기존 연락처 → 회사·거래처 (한 곳일 때만) ==")
c = sqlite3.connect(":memory:")
c.execute("CREATE TABLE shared_contacts(id INTEGER PRIMARY KEY, name TEXT, company TEXT, email TEXT, customer_id INTEGER)")
c.executemany("INSERT INTO shared_contacts(name, company, email, customer_id) VALUES(?,?,?,?)", [
    ("가", "㈜한곳전자", "a@one.example", 7), ("나", "㈜한곳전자", "b@one.example", 7),
    ("다", "㈜두곳A", "a@two.example", 1), ("라", "㈜두곳B", "b@two.example", 2),
    ("마", "개인", "x@gmail.com", 9),
])
check("한 곳 → 회사·거래처", sg.company_hint(c, "new@one.example") == {"company": "㈜한곳전자", "customer_id": 7}, sg.company_hint(c, "new@one.example"))
check("두 곳 → 고르지 않음", sg.company_hint(c, "new@two.example") == {"company": "", "customer_id": None}, sg.company_hint(c, "new@two.example"))
check("무료 메일 → 고르지 않음", sg.company_hint(c, "y@gmail.com") == {"company": "", "customer_id": None})
check("처음 보는 도메인 → 없음", sg.company_hint(c, "z@never.example") == {"company": "", "customer_id": None})
d = sg.draft_from_mail({"body_text": "네 알겠습니다.", "from_name": "신입", "from_email": "new@one.example"}, c)
check("서명 없어도 회사·거래처 채움", d["fields"]["company"] == "㈜한곳전자" and d["customer_id"] == 7, d)
d = sg.draft_from_mail({"body_text": "감사합니다.\n신입 사원\n㈜서명회사\nM. 010-0000-0001", "from_name": "신입", "from_email": "new@one.example"}, c)
check("서명의 회사가 먼저", d["fields"]["company"] == "㈜서명회사", d["fields"]["company"])

print("== 12. 줄 변환·자르기 ==")
t = sg.html_to_lines("<p>가</p><div>나<br>다</div><table><tr><td>라</td><td>마</td></tr></table><script>x()</script>")
check("HTML → 줄", [x.strip() for x in t.split("\n") if x.strip()] == ["가", "나", "다", "라  마"], repr(t))
check("스크립트 글 없음", "x()" not in t)
check("인용 없는 글은 그대로", sg.own_part("가\n나\n다") == "가\n나\n다")
check("'>' 한 줄은 인용 아님", "다음" in sg.own_part("가\n> 표시 한 줄\n다음"))
check("긴 줄은 서명이 아님", sg.signature_block("감사합니다.\n" + "가" * 150) == "")

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
