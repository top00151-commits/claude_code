# -*- coding: utf-8 -*-
"""메일 「마」 묶음 (대표 2026-11-21 「다음 진행해」) — 운영 무접촉 · 임시 DB(knk_mma_*) · 가짜 사람·가짜 메일만.

증명할 것
  ① 오늘 챙길 메일 더: 📭 2일 넘게 안 읽음(최근 30일 · 광고·알림 빼고 · 누르면 같은 목록) · 🚩 내일까지 · 🚫 스팸함 새(오늘만) · 없으면 안 보임
  ② 화면: 목록 명령 줄 답장·전체 답장·전달 글자 남김(1-1) · 휴대폰 위 메뉴 글자·「›」(6-3) · 휴대폰 메일 보기 중요·보관·삭제 → 「⋯ 더 보기」(6-4)
  ③ 자동 완성: 회사 이름 빈 연락처 = 연결된 거래처 이름 · 사내 직원 = 직책 + 부서(4-5)
  ④ 본문 첫 줄 부른 이름 ↔ 받는 사람(4-3): 다르면 🙋 · 같으면 조용 · 받는 사람 이름을 모르면 조용 · 사내끼리도 봄 · 영어로 부르고 이름이 한글뿐이면 조용
  ⑤ 쓰기 화면: 「?」 받는사람·참조·숨은참조(4-4) · 전체 답장 바깥 사람(4-6) · 짧은 제목(5-3) · 답장 제목 「RE: RE:」 → 「Re: 」 하나(5-3)
  ⑥ 1-2 「임시보관함」 이름은 11-18 대표 2단계 결정대로 그대로 · 파이썬 3.8
"""
import _mail_ico; _mail_ico.install()  # noqa: E402  11-28 4단계: 화면의 선 아이콘을 [i:이름] 으로 읽음(그림 문자 대신 · 아이콘 이름까지 확인)
import ast
import io
import os
import re
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
    _TMP = tempfile.mkdtemp(prefix="knk_mma_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_precheck as PC
    from app import mail_store as MS
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


D = "@knknara.co.kr"
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(9891,'T9891','시험영업팀',3)")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email) VALUES(9890,'t_me','시험신입','사원','member',9891,1,'x','me" + D + "')")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email) VALUES(9892,'t_sun','시험선배','대리','member',9891,1,'x','sun" + D + "')")
    c.execute("INSERT INTO customers(id, name) VALUES(9881,'㈜시험드림')")
    c.execute("INSERT INTO shared_contacts(name, email, company, customer_id, visibility, created_by) VALUES('한시험','han@dream-demo.example','',9881,'company',9890)")
    c.execute("INSERT INTO shared_contacts(name, email, company, customer_id, visibility, created_by) VALUES('오시험','oh@part-demo.example','시험파트',NULL,'company',9890)")

    def put(frm, subj, days_ago=0, read=0, blocked=0, flag="", hours_ago=0):
        c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, is_deleted, received_at) "
                  "VALUES(9890,'in',?,?,?,?,'가짜',?,0,datetime('now','localtime',?))",
                  (frm, "가짜", "me" + D, subj, read, "-%d hours" % (days_ago * 24 + hours_ago)))
        mid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        MS._ensure_security_cols(c)
        if blocked:
            c.execute("UPDATE mail_messages SET is_blocked=1 WHERE id=?", (mid,))
        if flag:
            c.execute("UPDATE mail_messages SET flag_due=? WHERE id=?", (flag, mid))
        return mid
    M_OLD = put("oh@part-demo.example", "오래 안 읽은 메일", days_ago=5)
    put("oh@part-demo.example", "오래됐지만 읽음", days_ago=5, read=1)
    put("oh@part-demo.example", "아주 옛날 안 읽음", days_ago=60)
    put("han@dream-demo.example", "오늘 온 안 읽음", days_ago=0)
    M_SPAM_T = put("x@spam-demo.example", "오늘 스팸", hours_ago=0, blocked=1)   # 자정 바로 뒤에 돌려도 「오늘」이 되게(1시간 전 → 지금)
    put("x@spam-demo.example", "지난 스팸", days_ago=3, blocked=1)

ME = {"id": 9890, "role": "member", "name": "시험신입", "rank": "사원", "team_id": 9891, "login_id": "t_me", "email": "me" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

print("① 오늘 챙길 메일 더")
today = m._mail_local_today(9)
from datetime import date, timedelta  # noqa: E402
tmr = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET flag_due=? WHERE id=?", (tmr, M_OLD))
r = k.get("/mail/inbox")
h = r.text
day = h[h.find('id="mbxDay"'):h.find("</nav>", h.find('id="mbxDay"'))]
check("받은편지함 200", r.status_code == 200, r.status_code)
check("📭 2일 넘게 안 읽음 1(5일 전 안 읽음만 · 읽은 것·60일 전·오늘 것 빼고)", "[i:mail-open] 2일 넘게 안 읽음 <b>1</b>" in day, day[:600])
check("🚩 내일까지 1", "[i:flag] 내일까지 <b>1</b>" in day, day[:600])
check("🚫 스팸함 새 1(오늘 옮긴 것만)", "[i:ban] 스팸함 새 <b>1</b>" in day, day[:600])
mm = re.search(r'href="(/mail/inbox\?unread=1&amp;noad=1&amp;df=[0-9-]+&amp;dt=[0-9-]+)"', day)
check("📭 누르는 곳 = 같은 조건 목록", bool(mm), day[:400])
if mm:
    r2 = k.get(mm.group(1).replace("&amp;", "&"))
    check("📭 목록 = 그 메일만", "오래 안 읽은 메일" in r2.text and "오늘 온 안 읽음" not in r2.text and "아주 옛날 안 읽음" not in r2.text, "")
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET is_read=1, flag_due='' WHERE user_id=9890")
    c.execute("UPDATE mail_messages SET is_blocked=0 WHERE id=?", (M_SPAM_T,))
h = k.get("/mail/inbox").text
check("없으면 안 보임(📭·🚩 내일·🚫)", "2일 넘게 안 읽음" not in h and "🚩 내일까지" not in h and "[i:flag] 내일까지" not in h and "스팸함 새" not in h, "")

print("\n② 화면")
inbox = io.open(os.path.join(ROOT, "app", "templates", "mail_inbox.html"), encoding="utf-8").read()
check("1-1 답장·전체 답장·전달 = 좁아도 글자(짧은 글자 「전체」)", inbox.count('class="c k"') == 3 and '<span class="ts">전체</span>' in inbox
      and "@container (max-width:760px){.mbx-cmd .c.k .t{display:inline}}" in inbox)
head = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_app_head.html"), encoding="utf-8").read()
check("6-3 휴대폰 위 메뉴: 그림 아래 글자 · 「›」 더 보기", ".mail-tools .t{display:inline !important;font-size:10px" in head and 'class="mt-more"' in head
      and ".mail-tools.more .mt-more{display:inline-flex" in head)
body = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_view_body.html"), encoding="utf-8").read()
sty = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_view_styles.html"), encoding="utf-8").read()
check("6-4 휴대폰: 중요·보관·삭제는 「⋯ 더 보기」 안(데스크톱 그대로)", body.count("mv-desk") - body.count("mv-quick") == 3 and body.count('class="mv-mob') >= 3
      and ".mv-actions .mv-desk{display:none !important}" in sty and ".mv-more-box .mv-mob{display:none}" in sty)
check("6-4 펼친 상자 = 단추 줄 폭(화면 밖으로 안 나감)", ".mv-hrow .mv-actions .mv-more{position:static}" in sty)
check("1-2 「임시보관함」 이름 그대로(11-18 대표 2단계 결정)", "📝 임시보관함" in inbox and "쓰다 만 메일" not in inbox)

print("\n③ 자동 완성")
r = k.get("/api/mail/contacts?q=시험")
it = {x["email"]: x for x in (r.json().get("items") or [])}
check("회사 이름 빈 연락처 → 연결된 거래처 이름", it.get("han@dream-demo.example", {}).get("company") == "㈜시험드림", it.get("han@dream-demo.example"))
check("회사 이름 있으면 그대로", it.get("oh@part-demo.example", {}).get("company") == "시험파트", it.get("oh@part-demo.example"))
check("사내 직원 = 직책 + 부서", it.get("sun" + D, {}).get("position") == "대리 시험영업팀", it.get("sun" + D))

print("\n④ 부른 이름 ↔ 받는 사람")
G = [("박구매님,\n견적 보내드립니다", "박구매"), ("안녕하세요 한드림 과장님.\n견적", "한드림"), ("김 과장님\n보고", "김"),
     ("팀장님,\n보고드립니다", ""), ("고객님 안녕하세요", ""), ("Dear Mr. Kim,\nPlease", "Kim"), ("안녕하세요.\n담당자님께", ""),
     ("견적 보내 드립니다.\n감사합니다.", ""), ("본문만 있고\n둘째 줄\n셋째 줄에 박구매님", ""), ("자료는\n어제 말씀하신 박구매님 것", ""), ("안녕하세요.\n박구매 차장님,", "박구매")]
bad = [(t, PC.greet_name(t), w) for t, w in G if PC.greet_name(t) != w]
check("첫 두 줄에서 부른 이름 찾기(직함뿐이면 없음)", not bad, bad)
with _db.db_session() as c:
    w1 = PC.run(c, ME, to="oh@part-demo.example", own="한시험 과장님,\n견적 보내 드립니다.")
    w2 = PC.run(c, ME, to="oh@part-demo.example", own="오시험 과장님,\n견적 보내 드립니다.")
    w3 = PC.run(c, ME, to="nobody@unknown-demo.example", own="박모름님,\n견적")
    w4 = PC.run(c, ME, to="sun" + D, own="한시험님,\n보고드립니다")
    w5 = PC.run(c, ME, to="\"시험 고객\" <x@unknown2-demo.example>", own="시험 고객님,\n안녕하세요")
    w6 = PC.run(c, ME, to="oh@part-demo.example", own="Dear Mr. Han,\nPlease")
    w7 = PC.run(c, ME, to="oh@part-demo.example", own="오 과장님,\n견적")
gk = lambda ws: [w for w in ws if w.get("kind") == "greet"]   # noqa: E731
check("다른 사람 이름 → 🙋 + 받는 사람 이름", gk(w1) and "한시험" in gk(w1)[0]["t"] and "오시험" in gk(w1)[0]["who"][0], w1)
check("맞는 이름 → 조용", not gk(w2), w2)
check("받는 사람 이름을 모름 → 조용", not gk(w3), w3)
check("사내끼리도 봄", gk(w4) and "시험선배" in gk(w4)[0]["who"][0], w4)
check("칸에 적힌 이름도 씀(「시험 고객」)", not gk(w5), w5)
check("영어로 부르고 아는 이름이 한글뿐 → 조용", not gk(w6), w6)
check("성만 불러도 맞으면 조용(오 과장님 ↔ 오시험)", not gk(w7), w7)

print("\n⑤ 쓰기 화면")
cmp_html = io.open(os.path.join(ROOT, "app", "templates", "mail_compose.html"), encoding="utf-8").read()
check("4-4 「?」 세 칸 · 설명 창", cmp_html.count('onclick="cmpRoleHelp()"') == 3 and "window.cmpRoleHelp=function()" in cmp_html)
check("4-6 전체 답장 + 사내·바깥 섞임 → 알림", "/[?&]replyall=\\d/.test(location.search) && all.length>ext.length" in cmp_html)
check("5-3 짧은 제목(답장 제외) → 알림", "kind:'subj'" in cmp_html and "(re|회신|답장)" in cmp_html)
with _db.db_session() as c:
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_deleted, received_at) "
              "VALUES(9890,'in','oh@part-demo.example','가짜','me" + D + "','RE: RE: 회신: 견적 건','가짜',0,datetime('now','localtime'))")
    M_RE = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_deleted, received_at) "
              "VALUES(9890,'in','oh@part-demo.example','가짜','me" + D + "','FW: 도면','가짜',0,datetime('now','localtime'))")
    M_FW = c.execute("SELECT last_insert_rowid()").fetchone()[0]
sj = lambda html: (re.search(r'id="cSubj"[^>]*value="([^"]*)"', html) or re.search(r'value="([^"]*)"[^>]*id="cSubj"', html))   # noqa: E731
r = k.get("/mail/compose?reply=%d" % M_RE)
s1 = sj(r.text)
check("답장 제목: 「RE: RE: 회신: 견적 건」 → 「Re: 견적 건」", s1 and s1.group(1) == "Re: 견적 건", s1 and s1.group(1))
r = k.get("/mail/compose?reply=%d" % M_FW)
s2 = sj(r.text)
check("답장 제목: 「FW: 도면」 → 「Re: FW: 도면」(전달 표시는 그대로)", s2 and s2.group(1) == "Re: FW: 도면", s2 and s2.group(1))

print("\n⑥ 문법")
for p in ("app/main.py", "app/mail_precheck.py", "app/mail_store.py"):
    try:
        ast.parse(io.open(os.path.join(ROOT, p), encoding="utf-8").read(), feature_version=(3, 8))
        ok = True
    except SyntaxError as e:
        ok = e
    check("파이썬 3.8 문법: %s" % p, ok is True, ok)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
