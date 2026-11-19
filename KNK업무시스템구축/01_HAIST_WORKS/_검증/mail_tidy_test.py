# -*- coding: utf-8 -*-
"""메일 3단계 — 메뉴·이름 다듬기 (대표 2026-11-19 「3단계 진행해」). 운영 무접촉 · 임시 DB · 가짜 메일.

증명할 것
  ① 대화 묶기 = 제목 + 상대 회사(다른 회사의 같은 제목은 따로 · 우리 회사끼리 주고받은 것은 그 회사 대화에)
  ② 삭제는 어디서나 같게(묻지 않고 휴지통 + 「↺ 되돌리기」) — 여러 통 띠 · 읽기 칸
  ③ 이름 통일: 「🔕 다시 안 받기(나만)」 · 「⛔ 회사 전체 차단(관리자)」 · 「⭐ 중요」(별표 아님) · 「← 받은편지함」 · 「📮 내 회사 주소 연결」 · 「🏷 메일 종류 규칙」 · 🛒 수주 등록
  ④ 낡은 안내·영어 정리: 「📁 다른 폴더로…」 · 「위 ✏️ 새 메일」 · NAS·발송망·AI 키 말 없음 · 언어 이름(영어·베트남어) · 관리자 차단 문구 앞뒤 맞음
  ⑤ 단축키 S = 중요(노트북) · 명령 줄 ◐ 읽음 · 도움말 휴대폰 · 도구 줄 「옆으로 밀면 더」 표시
  ⑥ 인쇄 = 메일만(읽기 칸이면 메일만 창 → 저절로 인쇄 · 단추·메뉴는 인쇄에서 뺌)
  ⑦ 스팸함 숫자 = 실제 통수(300통 한도 아님) · 보관하면 「회신 필요에서도 빠짐」 알림 · 휴지통 찾기 안내
"""
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
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mtidy_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
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


def rd(f):
    return open(os.path.join(ROOT, "app", "templates", f), encoding="utf-8").read()


print("== ① 대화 묶기 ==")
mails = [
    {"id": 1, "subject": "견적 요청", "from_email": "a@samsung.example", "direction": "in", "is_read": 1},
    {"id": 2, "subject": "RE: 견적 요청", "from_email": "b@lg.example", "direction": "in", "is_read": 1},
    {"id": 3, "subject": "Re: 견적 요청", "from_email": "c@samsung.example", "direction": "in", "is_read": 0},
    {"id": 4, "subject": "주간 회의", "from_email": "x@knknara.co.kr", "direction": "in", "is_read": 1},
    {"id": 5, "subject": "RE: 주간 회의", "to_email": "y@knknara.co.kr", "direction": "out", "is_read": 1},
    {"id": 6, "subject": "도면 송부", "from_email": "d@partner.example", "direction": "in", "is_read": 1},
    {"id": 7, "subject": "FW: 도면 송부", "from_email": "e@knknara.co.kr", "direction": "in", "is_read": 1},
]
gs = ms.group_threads(mails)
by = {tuple(sorted(i["id"] for i in g["items"])) for g in gs}
check("같은 제목이라도 회사가 다르면 따로(삼성 1·3 / LG 2)", (1, 3) in by and (2,) in by, by)
check("우리 회사끼리 주고받은 것은 한 대화(4·5)", (4, 5) in by, by)
check("바깥 회사가 하나뿐이면 우리 회사 사람 메일도 그 대화에(6·7)", (6, 7) in by, by)
check("묶음 안 읽음 수", next(g for g in gs if 3 in [i["id"] for i in g["items"]])["unread_count"] == 1)

print("== ② 삭제 통일 ==")
inbox = rd("mail_inbox.html")
vb = rd("_v5_partials/mail_view_body.html")
check("여러 통 띠의 삭제 = 묻지 않고 휴지통 + 되돌리기(mbxCmd)", "if(op==='delete' && window.mbxCmd){ mbxCmd('delete', ids);" in inbox)
check("읽기 칸 🗑 삭제 = 목록과 같은 길(되돌리기)", "if(IN_PANE && window.mbxCmd && !window.KNK_MAIL_WIN){ return window.mbxCmd('delete', [String(id)]); }" in vb)

print("== ③ 이름 통일 ==")
check("「🔕 다시 안 받기(나만 · 스팸함으로)」 — 경고 상자·⋯·오른쪽 클릭 같게", vb.count("🔕 다시 안 받기(나만 · 스팸함으로)") == 2 and "🔕 다시 안 받기(나만 · 스팸함으로)" in inbox
      and "🚫 스팸함으로 · 다시 안 받기" not in vb and "이 사람 다시 안 받기'" not in inbox)
check("관리자 = 「⛔ 회사 전체 차단(관리자)」 두 곳 같게", vb.count("⛔ 회사 전체 차단(관리자)") == 2 and "🚫 이 발신 차단" not in vb)
cl = rd("mail_cleanup.html")
check("보낸 곳별 정리: 「⭐ 중요」(별표 아님) · 「← 받은편지함」", "별표" not in cl and "⭐ 중요 표시한 메일은 남" in cl and "← 받은편지함" in cl)
check("돌아가기 단추 「← 받은편지함」(폴더·규칙)", "← 메일함" not in rd("mail_folders.html") and "← 메일함" not in rd("mail_rules.html"))
check("「📮 내 회사 주소 연결」(쓰기 화면·계정 화면 같은 이름)", "📮 내 계정" not in rd("mail_compose.html") and "📮 내 회사 주소 연결" in rd("mail_compose.html")
      and "📮 내 <em>회사 주소 연결</em>" in rd("mail_account.html"))
check("「🏷 메일 종류 규칙」(설정 줄과 같은 이름)", "메일 자동분류 규칙" not in rd("mail_rules.html") and "종류 규칙" in rd("mail_rules.html"))
check("🛒 수주 등록(📦 보관과 그림 안 겹침)", "🛒 수주 등록" in vb and "📦 수주 등록" not in vb)

print("== ④ 낡은 안내·영어 ==")
check("「📁 이 폴더로」 → 「📁 다른 폴더로…」", "「📁 이 폴더로」" not in rd("mail_folders.html") and "「📁 다른 폴더로…」" in rd("mail_folders.html"))
check("보낸편지함 빈 안내 = 「위 ✏️ 새 메일」", "왼쪽 <b>✏️ 메일 쓰기</b>" not in inbox and "위 <b>✏️ 새 메일</b>" in inbox)
cp = rd("mail_compose.html")
check("NAS · 발송망(Cloudflare/AWS SMTP) 말 없음(쓰기 화면)", "NAS" not in cp.split("<script")[0] and "Cloudflare/AWS SMTP" not in cp, [x for x in ("NAS", "Cloudflare") if x in cp.split("<script")[0]])
check("「AI 키」 말 없음", "AI 키" not in inbox)
check("언어 이름(영어·베트남어)", "{'en':'영어','vi':'베트남어'" in vb)
check("관리자 차단 확인창 문구 앞뒤 맞음(「이미 받은 것도 이동 아님」 없음)", "이미 받은 것도 이동·삭제 아님" not in vb and "이미 받은 메일도 스팸함으로 옮깁니다" in vb)

print("== ⑤ 단축키·도움말 ==")
check("단축키 S = 중요(Insert 도)", "'Insert':'star','s':'star','S':'star'" in inbox and "{k:'S'}" in inbox)
check("명령 줄 읽음 그림 ◐(새 메일 ✉ 와 안 겹침)", "◐ <span class=\"t\">읽음·안 읽음</span>" in inbox)
hd = rd("_v5_partials/mail_app_head.html")
check("도움말: S 단축키 · 휴대폰 쓰는 법", "<kbd>S</kbd>(또는 <kbd>Insert</kbd>) 중요" in hd and "📱 휴대폰에서" in hd)
check("도구 줄 「옆으로 밀면 더」 흐림 표시", ".mail-tools.more" in hd and "t.classList.toggle('more'" in hd)

print("== ⑥ 인쇄 = 메일만 ==")
check("읽기 칸 🖨 = 메일만 창(?win=1&print=1) · 그 창은 저절로 인쇄", "window.open('/mail/'+MAIL_ID+'?win=1&print=1'" in vb and "/[?&]print=1/.test(location.search)" in vb and 'onclick="mvPrint()"' in vb)
check("인쇄에서 단추·메뉴 뺌", ".mv-actions, .mv-nav, .mv-fu" in rd("_v5_partials/mail_view_styles.html"))

print("== ⑦ 숫자·알림·찾기 ==")
OWN = 9401
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9401,'kjr','시험대표','ceo',1,'x')")
    for i in range(5):
        mid, _o = ms.store_inbound(c, to_email="ceo@knknara.co.kr", from_email="s%d@spam.example" % i, subject="광고 %d" % i,
                                   text="x", owner_id=OWN, run_ai=False, message_id="tidy-%d@t" % i)
        c.execute("UPDATE mail_messages SET is_blocked=1 WHERE id=?", (mid,))
m.get_user = lambda req: {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": ""}
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
hb = k.get("/mail/blocked").text
check("스팸함 숫자 = 실제 통수(목록 길이 아님)", "<b>스팸함</b> <span>5통" in hb, hb[hb.find("<b>스팸함</b>"):hb.find("<b>스팸함</b>") + 60])
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("스팸함 숫자 계산 = count_blocked", 'spam_n = _mailbox.count_blocked(c, u["id"])   # 11-19 3단계' in src)
check("보관하면 「회신 필요에서도 빠짐」 알림(조용히 빠지지 않게)", "↩ 「회신 필요」에서도 빠졌어요" in inbox and "reply:!!r.querySelector('.mbx-reply')" in inbox)
ht = k.get("/mail/trash").text
check("휴지통의 찾기 칸 = 「받은편지함에서 찾기」라고 알림", "받은편지함에서 찾기" in ht)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
