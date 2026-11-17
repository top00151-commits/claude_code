# -*- coding: utf-8 -*-
"""② 업체별(같은 회사 주소 → 거래처 폴더) · ④ 회신 필요(추정) 시험 — 가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 지시 2026-11-17 「규칙으로 먼저 만들어」. 규칙만(AI·외부 전송 없음).
① 판단 규칙: 요청·질문은 잡고, 참고·광고·자동 발송·옛 인용 글·피싱 의심은 안 잡는다
② 훑기: 답장한 메일 · 같은 대화의 옛 메일 · 오래된 메일 · 차단함 · 끈 메일은 빠지고, 직접 켠 메일은 들어간다
③ 화면: 목록 「↩ 회신」 · 왼쪽 「↩ 회신 필요 N」 · 모아 보기 · 읽기 칸 상자 · 끄기/켜기/되돌리기 · 남의 메일 막기
④ 거래처 폴더: 같은 회사 주소가 한 거래처만 가리킬 때만 묶음 · 개인 메일·우리 회사·두 거래처 주소는 안 묶음 · 목록 거르기와 숫자가 같음
사용: py -3.13 _검증/mail_reply_folder_test.py"""
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
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_reply_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_reply as mr
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0
_SEQ = [0]


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:500])


def A(**kw):
    return mr.assess(**kw)


print("== 1. 판단 규칙(한 통) ==")
lv, why = A(subject="도면 송부", body="도면 송부드립니다.\n검토 후 회신 부탁드립니다.\n\n감사합니다.", from_email="kim@vendor.example")
check("「검토 후 회신 부탁드립니다」 → 회신 필요(보통)", lv == 1 and "회신 부탁" in why[0], (lv, why))
lv, why = A(subject="납기 문의", body="12월 납품 가능할까요?", from_email="kim@vendor.example")
check("질문 「가능할까요」 → 회신 필요", lv == 1, (lv, why))
lv, why = A(subject="자료", body="첨부 자료 보내 주시기 바랍니다.", from_email="kim@vendor.example")
check("「보내 주시기 바랍니다」 → 회신 필요", lv == 1, (lv, why))
lv, why = A(subject="견적 요청의 건", body="안녕하세요.\n첨부 확인 부탁드립니다.", from_email="kim@vendor.example")
check("제목 「요청」 + 확인 부탁 → 회신 필요", lv == 1, (lv, why))
lv, why = A(subject="회의록 공유", body="어제 회의록 공유드립니다. 참고 바랍니다.", from_email="kim@vendor.example")
check("「공유드립니다 · 참고 바랍니다」만 → 표시 안 함", lv == 0, (lv, why))
lv, why = A(subject="인사", body="앞으로도 잘 부탁드립니다. 감사합니다.", from_email="kim@vendor.example")
check("인사말 「잘 부탁드립니다」만 → 표시 안 함", lv == 0, (lv, why))
lv, why = A(subject="자료 송부", body="자료 송부드립니다. 회신은 하지 않으셔도 됩니다. 확인 부탁드립니다.", from_email="kim@vendor.example")
check("「회신은 하지 않으셔도 됩니다」 → 표시 안 함", lv == 0, (lv, why))
lv, why = A(subject="(광고) 신제품 안내", body="확인 부탁드립니다", from_email="ad@shop.example")
check("(광고) → 표시 안 함", lv == 0, (lv, why))
lv, why = A(subject="결재 문서", body="결재 부탁드립니다", from_email="noreply@system.example")
check("자동 발송 주소(noreply) → 표시 안 함", lv == 0, (lv, why))
lv, why = A(subject="이벤트", body="참여 부탁드립니다?\n\n수신거부를 원하시면 여기를", from_email="hello@mall.example")
check("수신거부 안내가 붙은 메일 → 표시 안 함", lv == 0, (lv, why))
lv, why = A(subject="자동 회신: 부재중", body="휴가 중입니다. 급한 건은 연락 부탁드립니다", from_email="kim@vendor.example")
check("자동 회신(부재중) → 표시 안 함", lv == 0, (lv, why))
lv, why = A(subject="계정 확인", body="확인 부탁드립니다", from_email="x@evil.example", risk_level=2)
check("피싱 의심(2) → 표시 안 함(답장하면 안 되는 메일)", lv == 0, (lv, why))
QUOTED = "네 알겠습니다. 감사합니다.\n\n-----Original Message-----\nFrom: 박우리\nSent: Monday\nTo: 최바깥\nSubject: 견적\n\n견적 검토 후 회신 부탁드립니다?"
lv, why = A(subject="RE: 견적", body=QUOTED, from_email="out@other.example")
check("요청이 딸려 온 옛 글(인용)에만 있으면 → 표시 안 함", lv == 0, (lv, why))
lv, why = A(subject="RE: 견적 요청", body="네, 확인했습니다. 내일 오전 중으로 회신드리겠습니다.", from_email="out@other.example")
check("답장 메일(RE:)은 제목 「요청」만으로 잡지 않음(상대가 「회신드리겠습니다」)", lv == 0, (lv, why))
lv, why = A(subject="RE: 견적 요청", body="단가 확인 부탁드립니다.", from_email="out@other.example")
check("답장 메일이라도 본문에 요청이 있으면 잡음", lv == 1, (lv, why))
lv, why = A(subject="납기", body="오늘 중으로 회신 부탁드립니다.", from_email="kim@vendor.example")
check("「오늘 중」 → 중요(2)", lv == 2 and any("급함" in r for r in why), (lv, why))
lv, why = A(subject="발주", body="발주서 확인 부탁드립니다.", from_email="kim@vendor.example", category="발주")
check("발주 메일 → 중요(2)", lv == 2 and "발주 메일" in why, (lv, why))
lv, why = A(subject="자료", body="확인 부탁드립니다.", from_email="kim@vendor.example", partner=True)
check("거래처 메일 → 중요(2)", lv == 2 and "거래처 메일" in why, (lv, why))
lv, why = A(subject="PO", body="Please confirm the delivery date.\n\nBest regards", from_email="john@parts.example")
check("영문 「Please confirm」 → 회신 필요", lv == 1, (lv, why))
lv, why = A(subject="Báo giá", body="Vui lòng xác nhận giúp em.", from_email="an@vn.example")
check("베트남어 「Vui lòng」 → 회신 필요", lv == 1, (lv, why))
lv, why = A(subject="안내", body="자세한 내용은 https://example.com/faq?id=1 참고", from_email="kim@vendor.example")
check("주소 속 물음표는 질문이 아님", lv == 0, (lv, why))
lv, why = A(subject="Out of Office: PO", body="I am out. Please contact my colleague.", from_email="john@parts.example")
check("영문 부재중 자동 회신 → 표시 안 함", lv == 0, (lv, why))

print("== 2. 훑기(받은편지함) ==")
OWN = 9001
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9001,'t9001','시험일','member',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9002,'t9002','시험이','member',1,'x')")
    c.execute("INSERT INTO customers(id, name) VALUES(501,'㈜가나다전자')")
    c.execute("INSERT INTO customers(id, name) VALUES(502,'㈜라마바상사')")
    c.execute("INSERT INTO customers(id, name) VALUES(503,'㈜사아자')")
    # 가나다전자 = 회사 주소 ganada.example 한 곳만 · shared.example 는 두 거래처가 같이 씀 · gmail 은 개인 메일
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by, customer_id) VALUES('홍길동','gildong@ganada.example','company',9001,501)")
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by, customer_id) VALUES('이라마','rama@shared.example','company',9001,502)")
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by, customer_id) VALUES('정사아','saa@shared.example','company',9001,503)")
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by, customer_id) VALUES('최개인','choi.private@gmail.com','company',9001,502)")
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by, customer_id) VALUES('사내','dong@knknara.co.kr','company',9001,503)")


def put(frm, subject, text, owner=OWN, days_ago=0, **kw):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="t%d@knknara.co.kr" % owner, from_email=frm, from_name="보낸이",
                                   subject=subject, text=text, owner_id=owner, run_ai=False,
                                   message_id="rp-%d@test" % _SEQ[0], **kw)
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?, ?) WHERE id=?",
                  ("-%d days" % days_ago, "-%d seconds" % (5000 - _SEQ[0]), mid))
    return mid


M_REQ = put("kim@vendor.example", "도면 검토 요청", "검토 후 회신 부탁드립니다.")
M_FYI = put("kim@vendor.example", "회의록 공유", "회의록 공유드립니다. 참고 바랍니다.")
M_DONE_REPLY = put("park@client.example", "견적 문의", "견적 가능할까요?")
M_OLD = put("old@client.example", "옛 요청", "회신 부탁드립니다.", days_ago=30)
M_T1 = put("lee@client.example", "일정 협의", "일정 확인 부탁드립니다.")
M_T2 = put("lee@client.example", "RE: 일정 협의", "네 감사합니다. 그 일정으로 하겠습니다.")
M_PART = put("someone@ganada.example", "샘플 송부", "샘플 확인 부탁드립니다.")
M_NEED = put("info@notice.example", "안내", "새 제도 안내입니다.")
M_OFF = put("han@client.example", "자료 요청", "자료 보내 주세요.")
M_OTHER = put("kim@vendor.example", "남의 요청", "회신 부탁드립니다.", owner=9002)
with _db.db_session() as c:
    ms.store_outbound(c, user_id=OWN, from_email="t9001@knknara.co.kr", to_email="박고객 <park@client.example>", subject="RE: 견적 문의", body="가능합니다")
    mr.set_mark(c, OWN, M_NEED, "need")
    mr.set_mark(c, OWN, M_OFF, "done")
    S = mr.scan(c, OWN)
check("요청 메일 → 들어감", M_REQ in S and S[M_REQ]["lv"] == 1 and "아직 답장 안 함" in S[M_REQ]["why"], S.get(M_REQ))
check("참고 메일 → 빠짐", M_FYI not in S)
check("내가 이미 답장한 메일 → 빠짐", M_DONE_REPLY not in S)
check("30일 전 메일 → 빠짐(최근 14일만)", M_OLD not in S)
check("같은 대화의 옛 메일 → 빠짐 · 새 메일(요청 없음)도 빠짐", M_T1 not in S and M_T2 not in S)
check("같은 회사 주소(가나다전자) → 거래처 메일로 중요(2)", S.get(M_PART, {}).get("lv") == 2 and "거래처 메일" in S[M_PART]["why"], S.get(M_PART))
check("직접 「회신 필요로 표시」 → 규칙과 상관없이 들어감", S.get(M_NEED, {}).get("manual") is True)
check("「회신 안 해도 됨」으로 끈 메일 → 빠짐", M_OFF not in S)
check("남의 메일은 섞이지 않음", M_OTHER not in S)
with _db.db_session() as c:
    ms.store_outbound(c, user_id=OWN, from_email="t9001@knknara.co.kr", to_email="info@notice.example", subject="RE: 안내", body="확인했습니다")
    S2 = mr.scan(c, OWN)
    one_req = mr.one(c, OWN, M_REQ)
    one_off = mr.one(c, OWN, M_OFF)
    one_t1 = mr.one(c, OWN, M_T1)
check("직접 켠 메일도 답장하면 저절로 빠짐", M_NEED not in S2)
check("읽기 칸 판단 = 목록 판단(요청 메일)", one_req.get("lv") == S[M_REQ]["lv"] and one_req.get("why") == S[M_REQ]["why"], (one_req, S[M_REQ]))
check("읽기 칸: 끈 메일은 state=done", one_off.get("state") == "done" and not one_off.get("lv"), one_off)
check("읽기 칸: 같은 대화의 옛 메일은 표시 없음(목록과 같음)", not one_t1.get("lv"), one_t1)

print("== 3. 화면 ==")
_UID = {"v": OWN}
_keep = m.get_user
m.get_user = lambda req: ({"id": _UID["v"], "role": "member", "name": "시험", "team_id": None, "team_name": ""} if _UID["v"] else None)


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


try:
    k = client()
    with _db.db_session() as c:
        n_now = len(mr.scan(c, OWN))
    h = k.get("/mail/inbox?thread=0").text
    check("목록에 「↩ 회신」 표시", 'class="mbx-reply lv1"' in h and 'class="mbx-reply lv2"' in h)
    check("왼쪽 「↩ 회신 필요」 + 숫자", "/mail/inbox?reply=1" in h and (">%d</span></a>" % n_now) in h, n_now)
    hr = k.get("/mail/inbox?reply=1&thread=0").text
    check("모아 보기: 요청 메일은 있고 참고 메일은 없음", "도면 검토 요청" in hr and "회의록 공유" not in hr and "견적 문의" not in hr)
    with _db.db_session() as c:
        c.execute("DELETE FROM mail_reply_marks")
    for nm, rr in (("모아 보기에 0통이면 빈 목록", None),):
        pass
    p = k.get("/mail/%d/pane" % M_REQ).text
    check("읽기 칸: 회신 필요 상자 + 답장 쓰기 + 회신 안 해도 됨", 'id="mvReply"' in p and "회신 필요(추정)" in p and "↩ 답장 쓰기" in p and "replyMark('done')" in p, p[:0])
    p2 = k.get("/mail/%d/pane" % M_FYI).text
    check("읽기 칸: 참고 메일은 「회신 필요로 표시」 단추만", 'id="mvReply" class="mv-reply">' in p2 and "replyMark('need')" in p2 and "회신 필요(추정)" not in p2.split('id="mvReply"')[1].split("</div>")[0])
    r = k.post("/mail/%d/reply-mark" % M_REQ, data={"state": "done"}).json()
    check("끄기 → ok · 표시 없음 · state=done", r.get("ok") and not r.get("lv") and r.get("state") == "done", r)
    check("끈 뒤 읽기 칸: 「되돌리기」", "replyMark('clear')" in k.get("/mail/%d/pane" % M_REQ).text)
    r = k.post("/mail/%d/reply-mark" % M_REQ, data={"state": "clear"}).json()
    check("되돌리기 → 다시 규칙대로 회신 필요", r.get("ok") and r.get("lv") == 1 and r.get("state") is None, r)
    r = k.post("/mail/%d/reply-mark" % M_FYI, data={"state": "need"}).json()
    check("켜기 → 회신 필요(2) · 「직접 표시함」", r.get("ok") and r.get("lv") == 2 and "직접" in r.get("why", ""), r)
    r = k.post("/mail/%d/reply-mark" % M_OTHER, data={"state": "done"})
    check("남의 메일은 못 바꿈(404)", r.status_code == 404, r.status_code)
    r = k.post("/mail/%d/reply-mark" % M_REQ, data={"state": "drop table"})
    check("이상한 값은 거절(400)", r.status_code == 400, r.status_code)
    _UID["v"] = None
    r = k.post("/mail/%d/reply-mark" % M_REQ, data={"state": "done"})
    check("로그인 없이는 거절(401)", r.status_code == 401, r.status_code)
    _UID["v"] = OWN
    km = client(5053, "kmail.knknara.co.kr")
    check("메일 전용 주소에서도 표시 바꾸기 길이 열림", km.post("/mail/%d/reply-mark" % M_REQ, data={"state": "clear"}).status_code == 200)
    check("메일 전용 주소 받은편지함 열림 + 회신 표시", "mbx-reply" in km.get("/mail/inbox").text)

    print("== 4. 거래처 폴더(같은 회사 주소) ==")
    put("gildong@ganada.example", "직접 등록된 사람", "본문")
    put("other@ganada.example", "같은 회사 다른 사람", "본문")
    put("x@shared.example", "두 거래처가 쓰는 주소", "본문")
    put("choi.other@gmail.com", "개인 메일 다른 사람", "본문")
    put("choi.private@gmail.com", "개인 메일 등록된 사람", "본문")
    put("new@knknara.co.kr", "사내 다른 사람", "본문")
    with _db.db_session() as c:
        fc = ms.customer_folder_counts(c, OWN)
        cust = {x["id"]: x for x in fc["customers"]}
        g = lambda cu: [x["subject"] for x in ms.list_inbox(c, OWN, cust=cu)]
        L501, L502, L503, LN = g("501"), g("502"), g("503"), g("none")
        ALL = ms.list_inbox(c, OWN, limit=1000)
    check("가나다전자 폴더: 등록된 사람 + 같은 회사 다른 사람(+앞 샘플 메일)", "직접 등록된 사람" in L501 and "같은 회사 다른 사람" in L501 and "샘플 송부" in L501, L501)
    check("폴더 숫자 = 목록 통수(가나다전자)", cust.get(501, {}).get("cnt") == len(L501), (cust.get(501), len(L501)))
    check("같은 회사 주소로 묶은 통수 따로 표시(by_domain)", cust.get(501, {}).get("by_domain") == 2, cust.get(501))
    check("두 거래처가 같이 쓰는 회사 주소는 묶지 않음(미분류)", "두 거래처가 쓰는 주소" in LN and "두 거래처가 쓰는 주소" not in L502 + L503)
    check("개인 메일(gmail) 다른 사람은 묶지 않음 · 등록된 사람은 그대로", "개인 메일 다른 사람" in LN and "개인 메일 등록된 사람" in L502 and "개인 메일 다른 사람" not in L502)
    check("우리 회사 주소는 회사 단위로 묶지 않음", "사내 다른 사람" in LN and "사내 다른 사람" not in L503)
    check("미분류 숫자 = 미분류 목록 통수(받은편지함·차단 아님 기준이 같을 때)", fc["unclassified"] == len(LN), (fc["unclassified"], len(LN)))
    check("거래처 폴더 합 + 미분류 = 전체", sum(x["cnt"] for x in fc["customers"]) + fc["unclassified"] == fc["total"] == len(ALL), (sum(x["cnt"] for x in fc["customers"]), fc["unclassified"], fc["total"], len(ALL)))
    h = k.get("/mail/inbox").text
    check("화면: 거래처 폴더 설명에 「같은 회사 주소 … 2통 포함」", "같은 회사 주소(@ 뒤가 같은 곳) 메일 2통 포함" in h)
finally:
    m.get_user = _keep

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
