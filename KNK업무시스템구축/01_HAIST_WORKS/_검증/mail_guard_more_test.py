# -*- coding: utf-8 -*-
"""메일 본문 정리 · 첨부 이름 읽기 · 링크 찾기 · 송금 문구 — 시험(11-26). 가짜 자료·임시 DB(운영 무접촉).
실행: PYTHONIOENCODING=utf-8 py -3.13 _검증/mail_guard_more_test.py"""
import io
import os
import sys
import tempfile
import time

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
    _TMP = tempfile.mkdtemp(prefix="knk_gmore_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms, mail_guard as g, mail_attcheck as ac
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
        print("  [FAIL]", name, "<-", str(extra)[:300])


print("① 본문 정리 — 이벤트 속성 · 주소 칸")
S = lambda h: ms.sanitize_html_for_view(h, 0, [])
for h in ('<img src="https://x.example/a.png"/onerror=alert(1)>', "<img src='x'/onload=alert(1)>", '<p title="a"onclick=alert(1)>x</p>',
          '<img src=x onerror=alert(1)>', '<div\tonmouseover="alert(1)">x</div>'):
    o = S(h)
    check("on* 지움: %s" % h[:40], "alert" not in o.lower() or "on" not in o.lower().split("alert")[0][-12:], o)
for h in ('<a href="javascript:alert(1)">x</a>', "<a href=javascript:alert(1)>x</a>", '<a href="&#106;avascript:alert(1)">x</a>',
          '<a href="java\tscript:alert(1)">x</a>', '<a href=" vbscript:msgbox(1)">x</a>', '<a href="data:text/html,<b>x</b>">x</a>',
          '<form action="javascript:alert(1)"><button formaction=javascript:alert(1)>b</button></form>'):
    o = S(h).lower().replace("&#106;", "j")
    check("주소 칸 무력화: %s" % h[:40], "javascript:" not in o.replace("\t", "") and "vbscript:" not in o and "data:text/html" not in o, o)
ok_html = '<a href="https://partner-demo.example/q?a=1">견적</a><img src="cid:logo1"><img src="data:image/png;base64,AAAA"><p style="color:red">글</p>'
o = S(ok_html)
check("보통 링크·그림·서식은 그대로", 'href="https://partner-demo.example/q?a=1"' in o and "data:image/png" in o and "color:red" in o, o)
check("보통 글 속 「on」 단어는 그대로", "online" in S("<p>Join online meeting</p>"))
o = S("<img/onerror=alert(1) src=x>")
check("태그 이름 바로 뒤 빗금 + on* 도 지움", "onerror" not in o.lower(), o)
o = S('<a href="https://x-demo.example/shop/onsale=2?q=1">세일</a>')
check("주소 값 속 「/onsale=」 은 그대로(주소 안 깨짐)", 'href="https://x-demo.example/shop/onsale=2?q=1"' in o, o)
o = S('<img src="https://x.example/a.png"/onerror=alert(1)>')
check("따옴표 바로 뒤 빗금 + on* 지움", "onerror" not in o.lower() and 'src="https://x.example/a.png"' in o, o)

print("② 첨부 이름 — 끝 점·빈칸·보이지 않는 글자")
for n, e in (("invoice.js.", ".js"), ("invoice.js ", ".js"), ("a.exe..", ".exe"), ("a.exe​", ".exe"), ("보고서.pdf", ".pdf"), ("noext", "")):
    check("확장자 %r → %s (세 곳 같게)" % (n, e), ac.ext_of(n) == e and ms._att_ext(n) == e and g.name_ext(n) == e, (ac.ext_of(n), ms._att_ext(n), g.name_ext(n)))
check("내려받기 경고(quick) — 끝 점 붙은 스크립트도", (ac.quick("invoice.js.") or {}).get("kind") in ("block", "warn") or bool(ac.quick("invoice.js.")), ac.quick("invoice.js."))
cd = []
lv, _n = g.assess(from_email="x@partner-demo.example", attachments=[{"filename": "invoice.js.", "mime": "application/octet-stream", "data": b"x", "inline": True}], codes=cd)
check("그림이 아닌 inline 첨부도 판정(실행파일 → 3)", lv >= 3 and "exec" in cd, (lv, cd))
check("진짜 본문 속 그림(png)은 첨부 판정에서 빠짐", g.real_inline({"filename": "logo.png", "mime": "image/png", "inline": True})
      and not g.real_inline({"filename": "a.js", "mime": "image/png", "inline": True})
      and not g.real_inline({"filename": "x.svg", "mime": "image/svg+xml", "inline": True}))
cd = []
lv, _n = g.assess(from_email="x@partner-demo.example", attachments=[{"filename": "견적서.pdf.exe.", "mime": "application/octet-stream", "data": b"x"}], codes=cd)
check("이중 확장자 + 끝 점 → 위장 실행파일(3)", lv >= 3, (lv, cd))

print("③ 링크 찾기 — 결과는 예전과 같고 긴 본문도 빠르게")
html = '<p><a href="https://real-demo.example/">www.bank-demo.example</a> <a name="x">앵커</a> <a href=\'http://10.20.30.40/x\'>자료</a></p>'
lk = g.a_links(html)
check("href 있는 링크만 · 순서대로", [x[3] for x in lk] == ["https://real-demo.example/", "http://10.20.30.40/x"], lk)
notes, sc, _n = g.link_findings(html, "")
check("보이는 주소≠실제 주소 · 숫자 주소 잡음", sc >= 2 and any("다름" in x for x in notes) and any("IP" in x for x in notes), notes)
d = g.defang_links_html(html)
check("링크 막기: href 없앰 · 글자는 남음", 'href="https://real' not in d and "www.bank-demo.example" in d and "자료" in d, d)
d2 = g.defang_links_html('<p><a href="https://x-demo.example/">닫지 않은 링크 <b>글</b>')
check("닫는 태그 없는 링크도 막음", "href=" not in d2.replace("data-x-href=", ""), d2)
for n in (400, 1600):
    big = '<a href="http://x-demo.example/">a' * n
    t = time.time()
    g.assess(from_email="x@partner-demo.example", html=big, body="x", codes=[])
    dt = time.time() - t
    check("긴 본문(%dKB) 판정 1초 안(%.2f초)" % (len(big) // 1024, dt), dt < 1.0, dt)
t = time.time()
g.defang_links_html('<a href="http://x-demo.example/">a' * 1600)
check("긴 본문 링크 막기도 1초 안", time.time() - t < 1.0)

print("④ 송금·계좌 변경 문구")
for txt in ("계좌번호가 변경되었습니다", "통장이 바뀌었으니 새 통장으로 보내 주세요", "수취 은행 정보가 변경되었습니다", "변경된 계좌로 입금 바랍니다",
            "Our bank details have changed", "please use our new beneficiary", "banking details changed effective today",
            "입금 계좌 변경 안내", "Số tài khoản mới của chúng tôi"):
    cd = []
    lv, _n = g.assess(from_email="x@partner-demo.example", subject="안내", body=txt, codes=cd)
    check("잡음: %s" % txt, lv >= 2 and "bec" in cd, (lv, cd))
for txt in ("견적서 보내 드립니다", "계좌 이체 확인했습니다 감사합니다", "다음 주 납기 일정 변경 요청드립니다"):
    cd = []
    lv, _n = g.assess(from_email="x@partner-demo.example", subject="안내", body=txt, codes=cd)
    check("보통 업무 글은 안 잡음: %s" % txt, "bec" not in cd, (lv, cd))

print("⑤ 「피싱 아님」 단추 — 주소는 data 칸으로(스크립트 글자 속에 넣지 않음)")
ME = 9871
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (ME, "t9871", "가짜나", "member"))
    mid, _o = ms.store_inbound(c, to_email="t9871@knknara.co.kr", from_email="a'b@partner-demo.example", from_name="가짜",
                               subject="가짜", text="가짜 http://10.20.30.40/x", html='<p><a href="http://10.20.30.40/x">자료</a></p>',
                               owner_id=ME, run_ai=False, message_id="gm-1@demo")
    c.execute("UPDATE mail_messages SET risk_level=2, risk_note='숫자(IP) 주소 링크' WHERE id=?", (mid,))
m.get_user = lambda req: {"id": ME, "role": "member", "name": "가짜나", "team_id": None, "team_name": ""}
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
h = k.get("/mail/%d/pane" % mid).text
i = h.find("mvNotPhish(%d" % mid)
btn = h[max(0, h.rfind("<button", 0, i)):h.find(">", i)]
check("단추 = data-addr + this.dataset.addr · onclick 안에 주소 글자 없음", "this.dataset.addr" in btn and "partner-demo" not in btn.split("onclick=")[1], btn)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
