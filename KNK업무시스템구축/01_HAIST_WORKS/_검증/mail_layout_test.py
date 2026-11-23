# -*- coding: utf-8 -*-
"""메일 화면 배치 시험(대표 2026-11-21 「메뉴가 중복되는 게 많아 공간만 차지 · 받은 메일 정보를 한 번에 더 많이」) — 운영 무접촉 · 임시 DB · 가짜 사람·가짜 메일만.

증명할 것(기능은 하나도 빼지 않고 자리만 합치거나 접기)
  ① 넓은 화면 처음 값 = 세 칸(고른 값이 있으면 그 값) · 휴대폰 그대로
  ② 메일 앱 받은편지함: 도구 줄 한 줄(✏ 새 메일 · 찾기 · 오늘 챙길 숫자 · 테마…) · 겹치는 이동 길은 받은편지함에서만 숨김(쓰기·메일 보기·보낸편지함은 그대로)
  ③ 목록 명령 줄 = 고를 때만 「선택 N통」 막대(data-cmd 그대로) · 오른쪽 클릭·단축키·끌어 놓기 그대로
  ④ 거르기 줄 낮게 · 종류 셋 → 「🏷 종류 ▾」(링크 그대로) · 🗔 보기는 거르기 줄 끝 · 날짜 머리 얇게
  ⑤ 목록 줄 「촘촘하게 / 보통」(이 기기에 기억 · 꼬리표는 한 묶음으로 그대로)
  ⑥ 읽기 칸 머리 세 줄: 그룹 메일 칩 · 받는 사람 요약 · 중요·보관·삭제 그림 단추 · 기한·더 보기 짧게 · 회신 표시 작은 단추 · AI 요약 접기 · 본문 날짜·회신 필요 띠 그대로
사용: py -3.13 _검증/mail_layout_test.py"""
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
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mlay_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
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
        print("  [FAIL]", name, "<-", str(extra)[:500])


D = "@knknara.co.kr"
OWN = 9790
_SEQ = [0]
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(?,?,?,?,?,1,'x',?)",
              (OWN, "t_lay", "시험배치", "사원", "member", "lay" + D))
    c.execute("INSERT INTO customers(id, name) VALUES(9781,'㈜시험배치')")
    c.execute("INSERT INTO customer_contacts(customer_id, role, name, email) VALUES(9781,'구매','박시험','buy@lay-demo.example')")
    mw.ensure(c)
    c.execute("INSERT INTO mail_groups(kind, name, address, members) VALUES('company','시험 영업 그룹','grp-lay" + D + "',?)",
              ('[{"email":"a1' + D + '","name":"가시험"},{"email":"a2' + D + '","name":"나시험"}]',))


def put(frm, subject, text, cc="", name="보낸이", summary=""):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="lay" + D, cc=cc, from_email=frm, from_name=name, subject=subject, text=text,
                                   owner_id=OWN, run_ai=False, message_id="lay-%d@test" % _SEQ[0])
        c.execute("UPDATE mail_messages SET is_read=0, received_at=datetime('now','localtime', ?) WHERE id=?", ("-%d minutes" % _SEQ[0], mid))
        if summary:
            c.execute("UPDATE mail_messages SET summary=? WHERE id=?", (summary, mid))
    return mid


M_GRP = put("buy@lay-demo.example", "12월 발주 예정 공유", "12월 발주 예정 공유드립니다.\n11월 28일(금)까지 견적 회신 부탁드립니다.",
            cc="grp-lay" + D, name="박시험", summary="12월 발주 예정 공유.\n11월 28일까지 견적 회신 요청.")
M_PLAIN = put("hello@plain-demo.example", "안내드립니다", "안녕하세요. 참고로 공유드립니다.", name="안내")
for i in range(5):
    put("x%d@many-demo.example" % i, "가짜 목록 메일 %d" % i, "목록 채우기용 가짜 메일 %d" % i, name="가짜%d" % i)

m.get_user = lambda req: {"id": OWN, "role": "member", "name": "시험배치", "rank": "사원", "team_id": None, "team_name": "",
                          "login_id": "t_lay", "lang": "ko", "is_active": 1, "email": "lay" + D}


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


def T(r):
    return r.text.replace(chr(13) + chr(10), chr(10))


def seg(h, start, end):
    a = h.find(start)
    return h[a:h.find(end, a)] if a >= 0 else ""


km = client(port=5053, host="kmail.knknara.co.kr")   # 메일 앱(kmail) 화면
wk = client()                                          # WORKS 화면(앱 아님)

print("== ① 넓은 화면 처음 값 = 세 칸 ==")
h = T(km.get("/mail/inbox"))
check("받은편지함(메일 앱) 200", "mail-app-top" in h and 'class="mbx-split has-lh"' in h)
check("고른 값이 없으면 자동 — 칸 폭 1000 이상 오른쪽(세 칸) · 1250 이상 폴더 보이기(1600px 창은 세 칸)",
      "var v=get('knkmail.view','auto')" in h and "W>=1000 ? 'right' : 'list'" in h and "W>=1250 ? 'show' : 'hide'" in h)
check("고른 값(knkmail.view)이 있으면 그 값 · 휴대폰·태블릿(900 이하)은 예전대로 한 줄", "put('knkmail.view', t.value)" in h and "window.matchMedia('(max-width:900px)').matches" in h)

print("== ② 위쪽 막대 — 도구 줄 한 줄 ==")
tools = seg(h, 'id="mailTools"', "</nav>\n</div>")
check("도구 줄에 받은편지함 표시(mt-inbox)", 'class="mail-tools mt-inbox" id="mailTools"' in h)
check("도구 줄 순서: ✏ 새 메일 → 찾기 칸 → 오늘 챙길 숫자 → (빈칸) → 테마·글자·설정·도움말",
      0 < tools.find('class="new"') < tools.find('class="mt-in mt-in-l"') < tools.find('<form class="mbx-search"') < tools.find('class="mt-in mt-in-day"')
      < tools.find('class="sp"') < tools.find('id="mtThemeBtn"') < tools.find('id="mtBigTop"') < tools.find("mailHelpToggle(event)"), tools[:300])
check("도구 줄 찾기 = 같은 찾기 폼(검색 · ▾ 자세히 · 기간 칸)", 'name="q"' in tools and ">검색</button>" in tools and "▾ 자세히" in tools and 'name="per"' in tools)
check("오늘 챙길 칩(0 인 것 숨김): 회신 필요 · 오늘까지 기한 · 답 기다림 칸 규칙", 'class="mt-day-i"' in tools and "?reply=1" in tools and 'class="tx"' in tools)
check("☰ 폴더 단추는 한 곳만(도구 줄)", h.count('class="mbx-foldbtn"') == 1 and tools.count('class="mbx-foldbtn"') == 1)
check("예전 찾기 줄·오늘 챙길 줄은 넓은 화면에서만 숨김(data-wide=off · 좁은 화면 그대로)",
      '<div class="mbx-topbar" data-wide="off">' in h and 'id="mbxDay" data-wide="off"' in h and '[data-wide="off"]{display:none !important}' in h
      and h.find("@media(min-width:901px){\n    [data-wide=\"off\"]") > 0)
navs = ('href="/mail/inbox" data-k="in"', 'href="/mail/inbox?star=1"', 'href="/mail/inbox?reply=1" data-k="reply"', 'href="/mail/inbox?flag=1" data-k="flag"',
        'href="/mail/sent"', 'href="/mail/drafts"', 'href="/mail/inbox?arc=1" data-k="arc"', 'href="/mail/trash"', 'href="/mail/blocked"')
check("이동 길 9개는 그대로 있음(class mt-nav) — 숨김은 CSS 로만", all(('<a class="mt-nav" ' + x) in tools for x in navs), [x for x in navs if ('<a class="mt-nav" ' + x) not in tools])
check("받은편지함에서만 숨김 + 폴더 칸을 접으면 다시 보임",
      "body:not(:has(.mbx-split.fold-off)) #mailTools.mt-inbox .mt-nav{display:none}" in h)
side = seg(h, '<nav class="mbx-side"', "</nav>")
check("숫자는 왼쪽 메뉴에 그대로(받은편지함 안 읽음 · 회신 필요 · 기한 · 임시 · 스팸)",
      'id="unreadBadge"' in side and 'href="/mail/inbox?reply=1"' in side and 'href="/mail/inbox?flag=1"' in side and 'href="/mail/drafts"' in side and 'href="/mail/blocked"' in side)
check("도구 줄 숫자 칸 id 그대로(1분마다 바뀜)", all(('id="%s"' % x) in tools for x in ("mtcUnread", "mtcReply", "mtcFlag", "mtcDrafts", "mtcSpam")))
hc = T(km.get("/mail/compose"))
check("메일 쓰기 화면: 이동 길 그대로(받은편지함 자리 없음)", 'class="mail-tools" id="mailTools"' in hc and 'class="mt-in mt-in-l"' not in hc and 'href="/mail/sent"' in hc)
hv = T(km.get("/mail/%d" % M_PLAIN))
check("메일 보기(전체 화면): 이동 길 그대로", 'class="mail-tools" id="mailTools"' in hv and 'class="mt-in mt-in-l"' not in hv)
hs = T(km.get("/mail/sent"))
check("보낸편지함: 예전 찾기 줄(숨김 표시 없음) · ☰ 폴더 단추 찾기 줄에", '<div class="mbx-topbar">' in hs and '<div class="mbx-topbar" data-wide' not in hs
      and hs.count('class="mbx-foldbtn"') == 1 and 'class="mt-in mt-in-l"' not in hs)
hw = T(wk.get("/mail/inbox"))
check("WORKS 화면(앱 아님): 도구 줄 없음 · 찾기 줄 그대로 · ☰ 폴더 하나", 'id="mailTools"' not in hw and '<div class="mbx-topbar">' in hw
      and hw.count('class="mbx-foldbtn"') == 1 and '<form class="mbx-search"' in hw)
check("빨간 머리줄 높이만 줄임(넓은 화면)", ".mail-app-top{padding:3px 16px}" in h)

print("== ③ 목록 명령 줄 = 고를 때만 ==")
lh = seg(h, '<div class="mbx-lhead">', '<div class="mbx-listcol">')
check("명령 줄 안: 「선택 N통」 · data-cmd 8개 그대로 · 보이는 것 모두 · ✕ 고르기 풀기",
      'id="mbxCmdN"' in lh and all(('data-cmd="%s"' % x) in lh for x in ("delete", "archive", "move", "reply", "replyall", "forward", "read", "star"))
      and "mbxSelAll()" in lh and "mbxSelClear()" in lh and "✕ 고르기 풀기" in lh)
check("넓은 화면: 고른 것 없으면 숨김 · 고르면 보임(picking) · 예전 여러 통 띠는 넓은 화면에서 이 막대로",
      ".mbx-split.has-lh:not(.picking)>.mbx-lhead{display:none}" in h and "sp.classList.toggle('picking', ids.length>0)" in h
      and ".mbx-split.has-lh .mbx-listcol>.mbx-sel{display:none}" in h and 'id="mbxSel" hidden' in h)
check("선택 막대 = 여러 통 일(삭제·보관·이동·읽음·중요) · 답장류는 읽기 칸·오른쪽 클릭·R 키",
      ".mbx-lhead .mbx-cmd .c.k,.mbx-lhead .mbx-cmd .sep{display:none}" in h)
check("오른쪽 클릭 · 단축키 · 끌어 놓기 그대로",
      "addEventListener('contextmenu'" in h and all(x in h for x in ("'ArrowDown'", "mbxCmd('reply')", "mbxCmd('replyall')", "mbxCmd('forward')", "'Delete':'delete'", "'e':'archive'", "'u':'read'", "'Insert':'star'"))
      and "addEventListener('dragstart'" in h and "addEventListener('drop'" in h)
check("이동 ▾ 메뉴에 「↺ 「이 메일만」 옮김 풀기」(11-22 내 규칙·자동 분류를 따라감)", "↺ 「이 메일만」 옮김 풀기" in h)
ha = T(km.get("/mail/inbox?arc=1"))
check("보관함에서는 선택 막대 「📥 받은편지함으로」", 'data-cmd="archive" title="받은편지함으로 되돌리기 (E)">📥' in ha)

print("== ④ 거르기 줄 · 날짜 머리 ==")
ch = seg(h, '<div class="mbx-chips">', '<div class="mbx-newbar"')
check("거르기: 전체 · 안 읽음 · 첨부 · 광고 빼기 · 대화로 묶기 그대로", all(x in ch for x in (">전체</a>", "● 안 읽음", "📎 첨부", "🔕 광고·알림 빼기", "💬 대화로 묶기")))
check("종류 셋 → 「🏷 종류 ▾」 하나(링크 셋 그대로 안에)", 'id="mbxKindDd"' in ch and "mbxKindToggle(event)" in ch and ch.count("mbx-chip kind") == 3
      and all(("cat=" + x) in ch.replace("&amp;", "&") for x in ("견적", "발주", "세금계산서")))
check("좁은 화면은 예전 칩 셋(종류 ▾ 단추 숨김 · 상자 = display:contents)", ".mbx-kinddd{display:contents}" in h and ".mbx-kindbtn{display:none}" in h)
tb = seg(h, 'id="mailTools"', '</nav>')
check("🗔 읽기창보기(11-23 대표 「보기를 테마 옆으로 · 이름 읽기창보기」) = 도구 줄 테마 바로 앞 · 거르기 줄엔 없음 · 펼침 상자는 화면 기준 자리",
      'id="mbxViewDd"' not in ch and tb.find('<span class="sp"></span>') < tb.find('id="mbxViewDd"') < tb.find('id="mtThemeBtn"')
      and '<span class="t">읽기창보기</span>' in tb and "mbxPopAt(" in h and "#mailTools .mbx-viewmenu{position:fixed" in h
      and "@media(max-width:900px){ #mailTools .mbx-viewdd{display:none} }" in h and h.count('id="mbxViewDd"') == 1)
check("목록 칸이 좁으면 긴 칩은 그림만(글자는 남김 · data-ic)", '@container mbxlc (max-width:560px)' in h and 'data-ic="💬"' in ch and 'data-ic="🔕"' in ch)
check("날짜 머리 얇게 · 거르기 줄 바로 아래 붙음", ".mbx-list>.mbx-day{display:block;margin:0;padding:0 12px" in h and "--mbx-day-top" in h)

print("== ⑤ 목록 줄 촘촘하게 / 보통 ==")
check("🗔 보기 → 「목록 줄」 촘촘하게 · 보통", 'name="mbxd" value="compact"' in h and 'name="mbxd" value="normal"' in h)
check("이 기기에 기억(localStorage · try/catch 감싼 get/put) · 고른 적 없으면 촘촘하게", "put('knkmail.dense', t.value)" in h and "(d==='normal') ? 'normal' : 'compact'" in h
      and "function get(k,d){ try{" in h)
check("촘촘하게 = 1줄 보낸 사람·꼬리표·📎·시각 / 2줄 제목 — 미리보기", all(x in h for x in (
      ".mbx-split.dense .mbx-from{order:1", ".mbx-split.dense .mbx-tags{order:2", ".mbx-split.dense .mbx-att{order:3", ".mbx-split.dense .mbx-time{order:5",
      ".mbx-split.dense .mbx-main::after{content:\"\";order:6;flex-basis:100%", ".mbx-split.dense .mbx-subj{order:7", ".mbx-split.dense .mbx-pv{order:8")))
check("휴대폰(≤900)은 촘촘하게 규칙 밖", h.find("@media(min-width:901px){\n    .mbx-split.dense .mbx-row") > 0)
row = seg(h, 'data-mail-id="%d"' % M_GRP, "</a>")
check("목록 줄 꼬리표는 한 묶음(.mbx-tags) — 회신·종류·폴더 꼬리표 그대로", '<span class="mbx-tags">' in row and "mbx-reply" in h, row[:400])
check("끌어 놓은 뒤 붙는 꼬리표도 묶음 안으로", "r.querySelector('.mbx-tags')||r.querySelector('.mbx-r2')" in h)

print("== ⑥ 읽기 칸 머리 ==")
p = T(km.get("/mail/%d/pane" % M_GRP))
check("읽기 칸 200 · 순서 그대로(제목 → 첫 글자 → 보낸 사람 → 단추 → 폴더 칩)",
      0 < p.find('class="mv-subj"') < p.find('class="mv-av"') < p.find('class="mv-hwho"') < p.find('class="mv-actions"') < p.find('class="mv-chips"'))
# 11-22 대표 「받는 사람이 도대체 누구인지」 — 원문 한 줄(말줄임) 대신 받는 사람·참조 칩(mail_rcpt_from_test 가 자세히)
check("받는 사람 줄 = 받는 사람·참조 칩 · 시각", 'class="mv-rc mv-rc-to"><b class="mv-rc-l">받는 사람</b>' in p and 'class="mv-when"> · ' in p)
check("그룹 메일 = 칩 하나 「👥 이름(N명 ▾)」 · 넓은 화면 누르면 명단 · 휴대폰은 예전 상자", 'id="mvGrp"' in p and "/api/mail/addrinfo?a=" in p
      and "mv-grp-c" in p and "명 ▾)</span>" in p and "mvGrpToggle(this)" in p and ".mv-grp-t,.mv-grp-m{display:none}" in T(km.get("/mail/%d" % M_GRP)))
j = km.get("/api/mail/addrinfo?a=grp-lay" + D).json()
check("그룹 명단 API 그대로(2명)", j.get("ok") and j["info"]["grp-lay" + D]["kind"] == "group" and j["info"]["grp-lay" + D]["n"] == 2, j)
act = p[p.find('class="mv-actions"'):p.find('id="mvMore"')]
check("단추 글자: 답장 · 전체답장 · 확인 답장 · 전달", all(x in act for x in ("↩ 답장</a>", "↩↩ 전체답장", "✅ 확인 답장", "↪ 전달")))
check("중요·보관·삭제 = 그림만 + 뜻(title·aria-label)", 'id="mvStarBtn"' in act and 'aria-label="중요 표시">☆</button>' in act and 'aria-label="보관">📦</button>' in act
      and 'title="🗑 삭제 — 휴지통으로 (Delete)" aria-label="삭제">🗑</button>' in act)
check("기한·알림 · 더 보기 = 넓은 화면 그림만(휴대폰 글자)", '🚩<span class="mv-bt"> 기한·알림</span> ▾' in p and '⋯<span class="mv-bt"> 더 보기</span>' in p)
check("중요·보관 눌렀을 때 바뀌는 글자도 그림(mvStar·mvArchive)", "b.textContent = j.starred ? '⭐' : '☆';" in p and "b.textContent = on ? '📥' : '📦';" in p)
check("휴대폰: 중요·보관·삭제는 「⋯ 더 보기」 안 그대로", p.count('class="mv-mob') >= 3 and p.count("mv-desk") == 3)
check("📝 요약 = 한 줄로 접고 누르면 펼침(내용 그대로)", 'id="mvAi"' in p and 'class="mv-ai-h"' in p and "📝 요약" in p and "11월 28일까지 견적 회신 요청." in p)
check("📅 본문 날짜 띠 그대로", 'id="mvDates"' in p)
rp_in = p.find('id="mvReply"')
check("회신 필요(추정) 판정 있으면 띠 그대로(머리 아래)", 'class="mv-reply on lv' in p and rp_in > p.find('class="mv-chips"') and p.rfind("</div>", 0, rp_in) > 0 and 'id="mvDates"' in p)
pp = T(km.get("/mail/%d/pane" % M_PLAIN))
chs = pp[pp.find('class="mv-chips"'):pp.find('id="mvReply"') + 40]
check("판정 없는 메일: 「↩ 회신 필요로 표시」 = 폴더 칩 줄 끝 작은 단추", 'id="mvReply" class="mv-reply">' in pp and "replyMark('need')" in pp
      and pp.find('class="mv-chips"') < pp.find('id="mvReply"') < pp.find('class="mv-nav"'), chs)
check("표시를 바꾸면 자리도 옮김(판정 있음 = 띠 · 없음 = 칩 줄)", "box.closest('.mv-chips')" in pp and "ch.appendChild(box)" in pp)
check("메일 보기 기능 id·onclick 그대로", all(x in p for x in ('id="mvFu"', 'id="mvMore"', 'id="mvAck"', 'id="mvArcBtn"', "delMail(", "markUnread()", "translateMail('ko')", "mvPrint()", "mvFollow('flag','today')")))
sty = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_view_styles.html"), encoding="utf-8").read()
check("넓은 화면만 머리 세 줄(641px~) · 휴대폰 규칙 그대로", "@media(min-width:641px){\n    .mv-head{display:flex" in sty.replace("\r\n", "\n")
      and ".mv-actions .mv-desk{display:none !important}" in sty and ".mv-hrow .mv-actions .mv-more{position:static}" in sty)
check("인쇄 때 요약은 펼친 채", ".mv-ai.mv-ai-f .mv-ai-b{display:block !important}" in sty)
r = km.post("/mail/%d/star" % M_PLAIN).json()
p2 = T(km.get("/mail/%d/pane" % M_PLAIN))
check("중요 표시 저장 그대로 → 읽기 칸 ⭐", r.get("ok") and r.get("starred") and 'aria-label="중요">⭐</button>' in p2, r)

print("== ⑦ 표준 ==")
for t in ("mail_inbox.html", "_v5_partials/mail_app_head.html", "_v5_partials/mail_view_styles.html"):
    tx = io.open(os.path.join(ROOT, "app", "templates", t), encoding="utf-8").read()
    added = [ln for ln in tx.splitlines() if "11-21" in ln or "dense" in ln or "mt-inbox" in ln or "mv-ai-f" in ln]
    check("%s: 새 규칙에 100vh·height !important 없음" % t, not any("100vh" in ln or re.search(r"height:[^;]*!important", ln) for ln in added))

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
