# -*- coding: utf-8 -*-
"""메일 안전 1단계 시험 — 스팸함 자동(아는 사람 제외) · ✓ 스팸 아님 · 첨부 「속」 검사 · 받기 막기/경고 ·
SVG·HTML 바로 열기 금지 · 모르는 곳 바깥 그림 끄기 · 메일 AI = OpenAI 만(다른 AI 로 새지 않음).
가짜 직원·가짜 메일·가짜 파일·임시 DB(운영 무접촉 · 실제 메일 없음 · AI 실제 호출 없음).
대표 지시 2026-11-18 「스팸메일은 자동으로 걸러주고 위험한 피싱 파일들도 자동으로 찾아 안전하게」 · 「메일은 OpenAI 로 고정」.
사용: py -3.13 _검증/mail_safe_test.py"""
import io
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "KNK_AI_PROVIDER", "KNK_AI_MODEL"):
    os.environ.pop(_k, None)
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_msafe_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_guard as mg
    from app import mail_attcheck as ac
    from app import ai_client as aic
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
        print("  [FAIL]", name, "<-", str(extra)[:600])


def zbytes(files, encrypt=False):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for n, d in files.items():
            z.writestr(n, d)
    data = bytearray(b.getvalue())
    if encrypt:   # 첫 파일 머리의 「암호」 깃발만 세움(검사기는 깃발을 본다)
        i = data.find(b"PK\x03\x04")
        data[i + 6] |= 1
        j = data.find(b"PK\x01\x02")
        data[j + 8] |= 1
    return bytes(data)


PDF = b"%PDF-1.4\n%fake\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
MZ = b"MZ\x90\x00" + b"0" * 60

print("== 1. 첨부 「속」 검사(이 서버 안에서만) ==")
check("이름은 .pdf · 속은 실행파일(MZ) → 막기", ac.inspect("견적서.pdf", "application/pdf", MZ)["kind"] == "block")
check("문서로 위장한 실행파일 이름(.pdf.exe) → 막기", ac.inspect("송금확인서.pdf.exe", "", b"x")["kind"] == "block")
check("실행파일(이름 그대로) → exec(경고 뒤 받기)", ac.inspect("setup.exe", "", MZ)["kind"] == "exec")
r = ac.inspect("자료.zip", "application/zip", zbytes({"readme.txt": "a", "invoice.exe": "MZ"}))
check("압축 안에 실행파일 → 막기 + 안의 이름", r["kind"] == "block" and "invoice.exe" in r["why"] and "readme.txt" in r["inside"], r)
check("비밀번호 압축 → 주의", ac.inspect("자료.zip", "", zbytes({"a.pdf": "x"}, encrypt=True))["kind"] == "warn")
check("압축 안 웹페이지 → 주의", ac.inspect("자료.zip", "", zbytes({"login.html": "<form>"}))["kind"] == "warn")
check("보통 압축 → 괜찮음 + 안의 이름", ac.inspect("도면.zip", "", zbytes({"a.dwg": "x", "b.pdf": "y"})) == {"kind": "ok", "why": "", "inside": ["a.dwg", "b.pdf"]})
check(".xlsx 속에 매크로(vbaProject.bin) 숨김 → 주의", ac.inspect("단가표.xlsx", "", zbytes({"xl/workbook.xml": "x", "xl/vbaProject.bin": "v"}))["kind"] == "warn")
check("보통 .xlsx → 괜찮음", ac.inspect("단가표.xlsx", "", zbytes({"xl/workbook.xml": "x"}))["kind"] == "ok")
check("옛 .doc 속 매크로 → 주의", ac.inspect("a.doc", "", b"\xd0\xcf\x11\xe0" + b"0" * 40 + "_VBA_PROJECT".encode("utf-16-le"))["kind"] == "warn")
check(".docm·.html·.svg → 주의", all(ac.inspect(n, "", b"x")["kind"] == "warn" for n in ("a.docm", "b.html", "c.svg")))
check("진짜 PDF·PNG → 괜찮음", ac.inspect("a.pdf", "application/pdf", PDF)["kind"] == "ok" and ac.inspect("a.png", "image/png", PNG)["kind"] == "ok")
check("이름은 PDF 인데 속은 아님 → 주의(표시만)", ac.inspect("a.pdf", "application/pdf", b"hello")["kind"] == "warn")
check("바로 열기: 그림·PDF 만 · SVG·HTML 안 됨", ac.inline_ok("image/png") and ac.inline_ok("application/pdf") and not ac.inline_ok("image/svg+xml", "a.svg") and not ac.inline_ok("text/html") and not ac.inline_ok("image/png", "x.svg"))
check("너무 큰 파일은 속은 안 봄(이름만)", ac.inspect("big.pdf", "", b"%PDF" + b"0" * (ac.MAX_SCAN + 1))["kind"] == "ok")

print("== 2. 판별 + 스팸함으로 옮길 이유(codes) ==")
codes = []
lv, note = mg.assess(from_email="a@x.example", subject="견적", body="첨부", attachments=[{"filename": "견적서.pdf", "data": MZ}], codes=codes)
check("이름 바꾼 실행파일 첨부 → 위험(3) · 격리 대상", lv == 3 and "att_block" in codes and mg.should_quarantine("a@x.example", [{"filename": "견적서.pdf", "data": MZ}], None, lv), (lv, codes, note))
codes = []
lv, note = mg.assess(from_email="news@shop.example", subject="이번 주 할인", body="보기",
                     html='<a href="https://track.shop.example/r?u=1">https://www.shop.example/sale</a>', codes=codes)
check("⭐광고 메일의 추적 링크(보이는 주소≠실제)만으로는 옮길 이유 아님", codes == [], (lv, codes, note))
codes = []
mg.assess(from_email="kim@partner.example", subject="계좌", body="새 계좌로 송금 부탁", codes=codes)
check("송금 계좌 변경 → 옮길 이유(bec)", "bec" in codes, codes)
codes = []
mg.assess(from_email="sales@vendor.example", subject="견적", body="첨부", attachments=[{"filename": "q.pdf", "data": b"hello"}], codes=codes)
check("⭐PDF 이름·속 다름만으로는 옮기지 않음(깨진 PDF 도 있음)", codes == [], codes)

print("== 3. 저장 → 스팸함 자동(아는 사람 제외) ==")
OWN, MEM, ADM = 9001, 9002, 9003
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(9001,'kjr','시험대표','ceo',1,'x','boss@knknara.co.kr')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(9002,'t9002','시험직원','member',1,'x','m2@knknara.co.kr')")
    c.execute("INSERT INTO shared_contacts(name, email, company, visibility, created_by) VALUES('박구매','p@semco.example','삼성전기','company',9001)")


def put(frm, subject, text="내용", owner=OWN, html="", atts=None, reply_to=""):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="boss@knknara.co.kr", from_email=frm, from_name="보낸이", subject=subject, text=text,
                                   html=html, owner_id=owner, run_ai=False, attachments=atts, message_id="safe-%d@test" % _SEQ[0],
                                   reply_to=reply_to)
        return dict(c.execute("SELECT * FROM mail_messages WHERE id=?", (mid,)).fetchone())


r1 = put("stranger@unknown.example", "계좌 변경 안내", "거래 계좌가 변경되었습니다. 새 계좌로 송금 부탁드립니다.")
check("모르는 사람 + 송금 계좌 변경 → 스팸함 · 이유 「스팸함으로 옮김」", r1["is_blocked"] == 1 and r1["risk_level"] == 2 and r1["risk_note"].startswith("스팸함으로 옮김"), r1["risk_note"])
r2 = put("p@semco.example", "계좌 변경 안내", "거래 계좌가 변경되었습니다. 새 계좌로 송금 부탁드립니다.")
check("⭐주소록에 있는 사람 → 같은 내용이라도 받은편지함 · ⚠ 경고만", r2["is_blocked"] == 0 and r2["risk_level"] == 2, (r2["is_blocked"], r2["risk_note"]))
with _db.db_session() as c:
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, to_email, subject, body_text) VALUES(9001,'out','boss@knknara.co.kr','Kim <kim@partner.example>','견적 문의','x')")
r3 = put("kim@partner.example", "계좌 변경", "새 계좌로 송금 부탁")
check("⭐내가 메일을 보낸 적 있는 사람 → 받은편지함", r3["is_blocked"] == 0, r3["risk_note"])
r4 = put("news@shop.example", "이번 주 할인", "보기", html='<a href="https://track.shop.example/r?u=1">https://www.shop.example/sale</a>')
check("⭐모르는 광고 메일(추적 링크만) → 받은편지함(광고는 흐리게 그대로)", r4["is_blocked"] == 0, (r4["risk_level"], r4["risk_note"]))
r5 = put("a@x.example", "견적서", "첨부", atts=[{"filename": "견적서.pdf", "mime": "application/pdf", "data": MZ, "size": len(MZ), "inline": 0}])
check("이름 바꾼 실행파일 → 스팸함(격리)", r5["is_blocked"] == 1 and r5["risk_level"] == 3, r5["risk_note"])
rq = put("yj.ceo@gmail.com", "외주 가공 견적", "견적 보내드립니다")
with _db.db_session() as c:
    pass
check("⭐협력사 사장님 개인 메일(이름에 「사장」 · gmail) → 받은편지함(⚠ 경고만 · 시험 서버에서 실제로 걸렸던 것)", rq["is_blocked"] == 0, (rq["risk_level"], rq["risk_note"]))
codes = []
mg.assess(from_email="kjr.office@gmail.com", from_name="김정락 대표", subject="송금", body="확인 부탁", staff_names=("김정락",), codes=codes)
check("우리 직원 이름 + 개인 메일 → 옮길 이유(사칭)", "spoof_name" in codes, codes)
r6 = put("hong@knknara.co.kr", "송금", "새 계좌로 송금")
check("⭐사내 주소 → 옮기지 않음", r6["is_blocked"] == 0)
r7 = put("noreply@pay-check.example", "[긴급] 계정 정지 예정", "24시간 안에 비밀번호를 확인하지 않으면 계정이 정지됩니다.",
         html='<a href="https://pay-check.example/login">https://www.paypal.com/login</a>')
check("모르는 사람 + 비밀번호 확인 요구 + 속인 링크 → 스팸함", r7["is_blocked"] == 1, (r7["risk_level"], r7["risk_note"]))
r8 = put("x@vendor.example", "자료", "첨부합니다", atts=[{"filename": "자료.zip", "mime": "application/zip", "data": zbytes({"a.pdf": "x"}, encrypt=True), "size": 10, "inline": 0}])
check("모르는 사람 + 비밀번호 압축 → 스팸함", r8["is_blocked"] == 1, (r8["risk_level"], r8["risk_note"]))

_U = {"v": {"id": OWN, "role": "ceo", "name": "시험대표"}}
_keep = m.get_user
m.get_user = lambda req: _U["v"]


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


try:
    k = client()
    print("== 4. 스팸함 화면 · ✓ 스팸 아님 ==")
    hi = k.get("/mail/inbox").text
    check("왼쪽 「🚫 스팸함」 + 숫자", 'href="/mail/blocked"' in hi and "🚫 스팸함" in hi and '<span class="cnt">4</span>' in hi[hi.find('href="/mail/blocked"'):hi.find('href="/mail/blocked"') + 600])
    hb = k.get("/mail/blocked").text
    check("스팸함 화면: 4통 · 「✓ 스팸 아님」 단추 · 안내", hb.count("notSpam(event,") == 4 and "스팸함</b>" in hb, hb.count("notSpam(event,"))
    j = k.post("/mail/%d/notspam" % r1["id"]).json()
    with _db.db_session() as c:
        b1 = c.execute("SELECT is_blocked FROM mail_messages WHERE id=?", (r1["id"],)).fetchone()[0]
    check("✓ 스팸 아님 → 받은편지함으로 + 그 사람 기억", j.get("ok") and b1 == 0 and j.get("addr") == "stranger@unknown.example", j)
    r9 = put("stranger@unknown.example", "계좌 변경 2", "새 계좌로 송금 부탁")
    check("⭐한 번 「스팸 아님」 한 사람 → 다음 의심 메일도 받은편지함(⚠ 경고만)", r9["is_blocked"] == 0 and r9["risk_level"] == 2, r9["risk_note"])
    _U["v"] = {"id": MEM, "role": "member", "name": "시험직원"}
    check("남의 메일은 「스팸 아님」 못 함", k.post("/mail/%d/notspam" % r5["id"]).status_code == 404)
    _U["v"] = {"id": OWN, "role": "ceo", "name": "시험대표"}
    with _db.db_session() as c:
        ms.add_block(c, "evil@block.example", kind="email", note="시험", by=OWN)
    rb = put("evil@block.example", "x", "y")
    j = k.post("/mail/%d/notspam" % rb["id"]).json()
    check("회사 전체 차단목록 주소는 「스팸 아님」으로 못 풂(관리자 일)", not j.get("ok") and "관리자" in j.get("message", ""), j)

    print("== 5. 읽기 화면: 스팸함 안내 · 모르는 곳 그림 끄기 · 첨부 꼬리표 ==")
    v5 = k.get("/mail/%d/pane" % r5["id"]).text
    check("격리 메일 읽기: 「스팸함으로 옮겼습니다」 + 「✓ 스팸 아님」", "스팸함으로 옮겼습니다" in v5 and "mvNotSpam(%d)" % r5["id"] in v5)
    check("첨부 꼬리표(이름 기준): 견적서.pdf 는 이름만으론 보통 — 받을 때 속까지 검사", "견적서.pdf" in v5)
    IMG = '<p>안녕하세요</p><img src="https://tracker.example/p.gif" width="1" height="1"><img src="https://cdn.example/logo.png">'
    rn = put("hello@newco.example", "처음 인사", "안녕하세요", html=IMG)
    vn = k.get("/mail/%d/pane" % rn["id"]).text
    check("처음 보는 곳 → 바깥 그림 꺼 둠 + 「그림 보기」", "tracker.example/p.gif" not in vn and 'class="mv-imgoff"' in vn and "mvImgOn(this)" in vn)
    vn1 = k.get("/mail/%d/pane?img=1" % rn["id"]).text
    check("「그림 보기」(img=1) → 그림 보임", "tracker.example/p.gif" in vn1 and 'class="mv-imgoff"' not in vn1)
    rk = put("p@semco.example", "견적 회신", "견적입니다", html=IMG)
    vk = k.get("/mail/%d/pane" % rk["id"]).text
    check("⭐아는 사람(주소록) → 그림 그대로(꺼 둠 띠 없음)", "cdn.example/logo.png" in vk and 'class="mv-imgoff"' not in vk, (rk["risk_note"], vk.count("cdn.example")))
    vf = k.get("/mail/%d" % rn["id"]).text
    check("풀페이지도 처음 보는 곳이면 꺼 둠 띠", 'class="mv-imgoff"' in vf and "tracker.example" not in vf)
    rw = put("p@semco.example", "자료", "첨부", atts=[{"filename": "단가.xlsm", "mime": "application/octet-stream", "data": b"x", "size": 1, "inline": 0},
                                                    {"filename": "setup.exe", "mime": "application/octet-stream", "data": MZ, "size": len(MZ), "inline": 0}])
    vw = k.get("/mail/%d/pane" % rw["id"]).text
    check("첨부 꼬리표: 매크로 문서 = ⚠ 주의 · 실행파일 = ⛔ 위험", "(주의: 매크로가 든 문서" in vw and "(위험: 실행파일)" in vw, vw[vw.find("mv-atts"):vw.find("mv-atts") + 900])

    print("== 6. 첨부 받기: 속까지 보고 막기·경고 · SVG/HTML 바로 열기 금지 ==")

    def att_id(mid, name):
        with _db.db_session() as c:
            return c.execute("SELECT id FROM mail_attachments WHERE mail_id=? AND filename=?", (mid, name)).fetchone()[0]

    rx = put("p@semco.example", "도면", "첨부", atts=[
        {"filename": "도면.pdf", "mime": "application/pdf", "data": MZ, "size": len(MZ), "inline": 0},
        {"filename": "logo.svg", "mime": "image/svg+xml", "data": b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "size": 80, "inline": 0},
        {"filename": "photo.png", "mime": "image/png", "data": PNG, "size": len(PNG), "inline": 0},
        {"filename": "real.pdf", "mime": "application/pdf", "data": PDF, "size": len(PDF), "inline": 0},
        {"filename": "pack.zip", "mime": "application/zip", "data": zbytes({"x.pdf": "a"}, encrypt=True), "size": 10, "inline": 0},
    ])
    a_bad = att_id(rx["id"], "도면.pdf")
    _U["v"] = {"id": OWN, "role": "member", "name": "시험대표"}   # 일반 직원 권한으로
    g = k.get("/mail/%d/att/%d" % (rx["id"], a_bad))
    check("이름은 PDF·속은 실행파일 → ⛔ 막는 화면 · 받기 단추 없음(직원)", g.status_code == 200 and "열면 안 되는 첨부" in g.text and "confirm=1" not in g.text and "MZ" not in g.text)
    check("직원이 confirm=1 로 직접 와도 403", k.get("/mail/%d/att/%d?confirm=1" % (rx["id"], a_bad)).status_code == 403)
    _U["v"] = {"id": OWN, "role": "ceo", "name": "시험대표"}
    g = k.get("/mail/%d/att/%d" % (rx["id"], a_bad))
    check("관리자(대표)는 「관리자 — 위험을 감수하고 받기」 있음", "관리자 — 위험을 감수하고 받기" in g.text)
    g = k.get("/mail/%d/att/%d?confirm=1" % (rx["id"], a_bad))
    check("관리자 confirm=1 → 내려받기(바로 열기 아님)", g.status_code == 200 and g.headers.get("content-disposition", "").startswith("attachment"))
    a_svg = att_id(rx["id"], "logo.svg")
    g = k.get("/mail/%d/att/%d" % (rx["id"], a_svg))
    check("SVG → 주의 화면(바로 열지 않음)", "주의할 첨부" in g.text and "<script>alert" not in g.text)
    g = k.get("/mail/%d/att/%d?confirm=1" % (rx["id"], a_svg))
    check("SVG 받기 → 내려받기 + 스크립트 막는 머리글(CSP sandbox)", g.headers.get("content-disposition", "").startswith("attachment") and "sandbox" in g.headers.get("content-security-policy", ""), dict(g.headers))
    g = k.get("/mail/%d/att/%d" % (rx["id"], att_id(rx["id"], "photo.png")))
    check("그림(PNG) → 바로 보기 그대로", g.status_code == 200 and g.headers.get("content-disposition", "").startswith("inline") and g.content == PNG)
    g = k.get("/mail/%d/att/%d" % (rx["id"], att_id(rx["id"], "real.pdf")))
    check("진짜 PDF → 바로 보기 그대로(머리글로 막지 않음)", g.headers.get("content-disposition", "").startswith("inline") and "content-security-policy" not in g.headers)
    g = k.get("/mail/%d/att/%d" % (rx["id"], att_id(rx["id"], "pack.zip")))
    check("비밀번호 압축 → 주의 화면 + 「확인했습니다 — 받기」 + 안의 이름", "주의할 첨부" in g.text and "확인했습니다 — 받기" in g.text and "x.pdf" in g.text)

    print("== 7. 메일 AI = OpenAI 만(다른 AI 로 새지 않음) ==")
    calls = []
    aic._get_client = lambda prov: calls.append(prov) or object()
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-FAKE-for-test"
    _ok_keep = (aic._ANTHROPIC_OK, aic._OPENAI_OK)
    aic._ANTHROPIC_OK = aic._OPENAI_OK = True
    check("Claude 키만 있음 → 다른 기능 AI 는 켜짐(지금과 같음)", aic.ai_available() and aic.get_provider() == "claude")
    check("Claude 키만 있음 → 메일 AI 꺼짐", not aic.mail_ai_available() and not m.mail_ai_enabled_for({"id": OWN}))
    ok, msg = aic.ai_chat("메일 내용", provider="openai")
    check("openai 로 콕 집으면 키 없을 때 실패 — Claude 로 넘어가지 않음", not ok and calls == [], (ok, msg, calls))
    with _db.db_session() as c:
        check("메일 분류·요약: Claude 를 부르지 않고 그냥 넘어감", ms._ai_classify("s", "b") == ("일반", "") and ms._ai_summary("b") == "" and calls == [], calls)
        ok, msg = ms.translate_mail(c, r2["id"], OWN, "en")
        check("번역: 「OpenAI 키 필요」 안내 · Claude 안 부름", not ok and "OpenAI" in msg and calls == [], (msg, calls))
    rr = put("sales@new.example", "AI 시험", "본문")   # run_ai=False
    j = k.post("/api/mail/ai-compose", data={"body": "메모"}).json()
    check("AI로 정리: OpenAI 없으면 꺼짐 안내", not j.get("ok") and "OpenAI" in j.get("message", ""), j)
    with _db.db_session() as c:
        check("바깥 입구(run_ai=None) → 받는 사람 기준 · 메일 AI 꺼져 있으면 안 부름", ms._owner_mail_ai_ok(c, OWN) is False)
    # OpenAI 키가 생기면 → 메일 AI 는 OpenAI 로(화면 「모델」 이 Claude 모델이어도 OpenAI 기본 모델)
    os.environ["OPENAI_API_KEY"] = "sk-FAKE-for-test"
    seen = []

    class _R:
        class _C:
            class _M:
                content = '{"category":"견적","lang":"ko"}'
            message = _M()
        choices = [_C()]

    aic._openai_create = lambda client, mdl, msgs, mt, temp: seen.append(mdl) or _R()
    os.environ["KNK_AI_MODEL"] = "claude-sonnet-4-5"
    check("두 키 다 있으면 다른 기능은 여전히 Claude(지금과 같음) · 메일은 OpenAI", aic.get_provider() == "claude" and aic.mail_ai_available())
    cat = ms._ai_classify("견적 요청", "견적 부탁드립니다")
    check("메일 분류 → OpenAI 로만 · 모델은 OpenAI 기본(화면 모델이 Claude 여도)", cat == ("견적", "ko") and calls == ["openai"] and seen == [aic.DEFAULT_MODEL_OPENAI], (cat, calls, seen))
    calls.clear()
    with _db.db_session() as c:
        check("받는 사람 AI 허용 + OpenAI → 바깥 입구도 AI 켜짐", ms._owner_mail_ai_ok(c, OWN) is True)
    ok, _t = aic.ai_chat("hi")   # 공급사 안 집으면 지금과 똑같이(Claude)
    check("⭐공급사를 안 집은 다른 기능은 지금과 똑같이 Claude", calls == ["claude"], calls)
    for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "KNK_AI_MODEL"):
        os.environ.pop(_k, None)
    aic._ANTHROPIC_OK, aic._OPENAI_OK = _ok_keep

    print("== 8. kmail · 로그인 ==")
    km = client(port=5053, host="kmail.knknara.co.kr")
    check("kmail 스팸함 200 · 스팸 아님 POST", km.get("/mail/blocked").status_code == 200 and km.post("/mail/%d/notspam" % r7["id"]).json().get("ok"))
    _U["v"] = None
    check("로그인 안 하면 스팸 아님 401", k.post("/mail/%d/notspam" % r7["id"]).status_code == 401)
finally:
    m.get_user = _keep

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
