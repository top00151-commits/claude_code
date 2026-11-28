# -*- coding: utf-8 -*-
"""메일 화면 1단계 「메뉴 단순하게」 시험 — 가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 지시 2026-11-18 「메일 메뉴 구성을 사용자 입장에서 … 쉽게 보이고 쉽게 사용할 수 있게」 → 2차 검토 → 「진행해」.
① 받은편지함: 왼쪽 = 메일 쓰기 · 빨리 보기(받은편지함·⭐ 중요·↩ 회신 필요) · 내 메일 · 폴더 · ⚙ 설정·정리
   위 도구줄 8개·메일 종류(분류) 칸·보기 칸은 없음 · 목록 위 거르기(전체·안 읽음·첨부·대화로 묶기) · 날짜는 「▾ 자세히」 안(2단계에서 기간·어디서·무엇을과 함께)
② 목록 꼬리표 = 폴더 이름(「일반」은 안 붙임) · 메일 없는 폴더는 접힘(＋ 메일 없는 N곳)
③ 읽기: 한 줄(답장·전체답장·전달·중요·삭제) + ⋯ 더 보기(안 읽음·할 일·주소록·번역·인쇄·다시 안 받기) · 「답장 쓰기」 중복 없음
④ ⚙ 설정·정리 한 화면 — 관리자 칸은 관리자만 · 앱 머리띠 링크는 왼쪽 메뉴가 없는 화면에만
사용: py -3.13 _검증/mail_menu_test.py"""
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
    _TMP = tempfile.mkdtemp(prefix="knk_mmenu_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
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


OWN, OTHER = 9001, 9002
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9001,'kjr','시험대표','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9002,'t9002','시험이','member',1,'x')")
    c.execute("INSERT INTO customers(id, name) VALUES(701,'삼성전기㈜')")
    c.execute("INSERT INTO customer_contacts(customer_id, role, name, email) VALUES(701,'구매','박구매','p@semco.example')")


def put(frm, subject, text, owner=OWN, name="보낸이"):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="t%d@knknara.co.kr" % owner, from_email=frm, from_name=name,
                                   subject=subject, text=text, owner_id=owner, run_ai=False,
                                   message_id="mm-%d@test" % _SEQ[0])
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?) WHERE id=?",
                  ("-%d seconds" % (9000 - _SEQ[0]), mid))
    return mid


M_CUST = put("p@semco.example", "11월 발주서 송부", "발주서 송부드립니다. 확인 부탁드립니다.", name="박구매")
M_GEN = put("someone@unknown-x.example", "처음 연락드립니다", "안녕하세요.", name="모르는이")
M_OTHER = put("p@semco.example", "남의 메일", "x", owner=OTHER)

_U = {"v": {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": ""}}
_keep = m.get_user
m.get_user = lambda req: _U["v"]


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    # 11-28 4단계: 단추·폴더 이름 그림 문자 → 선 아이콘 — 화면 글을 [i:이름] 으로 읽어 같은 뜻(아이콘 이름까지)을 확인
    from _mail_ico import IcoClient
    return IcoClient(k)


def side(h):
    a = h.find('<nav class="mbx-side"')
    return h[a:h.find("</nav>", a)] if a >= 0 else ""


try:
    k = client()
    print("== 1. 받은편지함 — 왼쪽 메뉴 ==")
    r = k.get("/mail/inbox")
    h = r.text
    sd = side(h)
    check("받은편지함 200", r.status_code == 200, r.status_code)
    check("왼쪽 맨 위 「✏️ 메일 쓰기」", sd.find('class="mbx-write"') >= 0 and sd.find('class="mbx-write"') < sd.find("받은편지함"), sd[:300])
    check("빨리 보기: 받은편지함 → ⭐ 중요 → ↩ 회신 필요 (순서)",
          0 < sd.find("[i:inbox] 받은편지함") < sd.find("[i:star] 중요") < sd.find("↩ 회신 필요"), (sd.find("[i:inbox] 받은편지함"), sd.find("[i:star] 중요"), sd.find("↩ 회신 필요")))
    check("메일함(11-18 2단계 아웃룩·하이웍스 이름): 보낸편지함 · 임시보관함 · 휴지통", "[i:send] 보낸편지함" in sd and "[i:file-pen] 임시보관함" in sd and ">즐겨찾기</div>" in sd and ">메일함</div>" in sd and "[i:trash-2] 휴지통" in sd)
    check("「쓰다 만 메일」 이름 없음 → 「임시보관함」(익숙한 이름 · 11-18 2단계) · 「📦 보관함」과 따로", "쓰다 만 메일" not in h and "[i:archive] 보관함" in sd)
    check("폴더가 빨리 보기 아래 · ⚙ 설정·정리는 맨 아래", sd.find("↩ 회신 필요") < sd.find("[i:folder] 폴더") < sd.find("[i:settings] 설정·정리"), (sd.find("[i:folder] 폴더"), sd.find("[i:settings] 설정·정리")))
    check("⚙ 설정·정리 → /mail/tools", 'href="/mail/tools"' in sd)
    check("메일 종류(분류) 칸 없음 — ?cat= 링크·「분류」 머리 없음", "?cat=" not in sd and '>분류</div>' not in sd)
    check("보기 칸(⭐ 별표·● 안읽음·💬 대화묶기) 왼쪽에서 빠짐", "⭐ 별표" not in sd and "[i:star] 별표" not in sd and "● 안읽음" not in sd and "💬 대화묶기" not in sd and "[i:message-square] 대화묶기" not in sd)
    check("보낸 곳별 정리·차단목록 관리 → 왼쪽에서 빠짐(설정·정리 안)", "/mail/cleanup" not in sd and "/mail/blocklist" not in sd)
    check("🚫 스팸함은 왼쪽 「내 메일」에 늘 보임(11-18 대표 「스팸은 자동으로 걸러」 — 아웃룩처럼)", 'href="/mail/blocked"' in sd and "[i:ban] 스팸함" in sd and sd.find("[i:trash-2] 휴지통") < sd.find("[i:ban] 스팸함") < sd.find("[i:folder] 폴더"))
    check("「일반」 + 「🧹 일반 정리하기」는 그대로", ">일반</span>" in sd and "[i:eraser] 일반 정리하기" in sd)

    print("== 2. 위 도구줄 · 찾기 · 거르기 ==")
    top = h[h.find('class="mbx-topbar"'):h.find('</form>', h.find('class="mbx-topbar"'))]  # 찾기 줄(폰 전용 떠 있는 쓰기 단추 앞)
    for nm, needle in (("⚙ 받기", "/admin/mail-inbound"), ("⚙ 보내기", "/admin/mail-send"), ("가져오기", "/admin/mail-fetch"),
                       ("정리(디스크)", "/admin/mail-purge"), ("자동분류", "/mail/rules"), ("보낸 곳별 정리", "/mail/cleanup"),
                       ("중복정리", "dedupInbox")):
        check("도구줄에 「%s」 없음" % nm, needle not in top, needle)
    check("위 명령 줄 「✉ 새 메일」(아웃룩처럼 · 11-18 2단계) — 찾기 칸 안에는 쓰기 단추 없음", 'id="mbxCmd"' in h and "새 메일</span>" in h and "/mail/compose" not in top[top.find('<form class="mbx-search"'):])
    check("찾기 칸 + 검색 단추는 그대로", 'name="q"' in top and ">검색</button>" in top)
    check("날짜는 「▾ 자세히」 안(늘 보이지 않음)", "<details class=\"mbx-more\"" in top and 'name="df"' in top and "▾ 자세히" in top)
    check("첨부 체크박스(숫자만 보이던 것) 없음", 'type="checkbox" name="att"' not in top)
    ch = h[h.find('class="mbx-chips"'):h.find('class="mbx-chips"') + 2000]
    check("목록 위 거르기: 전체 · ● 안 읽음 · 📎 첨부 · 💬 대화로 묶기", all(x in ch for x in (">전체</a>", "● 안 읽음", "[i:paperclip] 첨부", "[i:message-square] 대화로 묶기")))
    check("폰: 떠 있는 「✏️ 쓰기」", 'class="mbx-fab"' in h)
    r2 = k.get("/mail/inbox?unread=1&att=1&thread=0")
    check("거르기 겹쳐 쓰기 200", r2.status_code == 200)
    ch2 = r2.text[r2.text.find('class="mbx-chips"'):r2.text.find('class="mbx-chips"') + 2000].replace("&amp;", "&")
    check("대화 묶기 끈 채로 「안 읽음」 누르면 끈 상태 유지(&thread=0)", "&unread=1&thread=0" in ch2, ch2[:600])
    _hd = k.get("/mail/inbox?df=2026-01-01").text
    check("날짜로 찾으면 「▾ 자세히 ●」 표시 · 결과 띠에 날짜", "▾ 자세히 ●" in _hd and "2026-01-01 ~" in _hd)

    print("== 3. 목록 꼬리표 · 폴더 접기 ==")
    check("메일 종류 「일반」 꼬리표 없음", 'class="mbx-badge"' not in h[h.find('class="mbx-list"'):])
    check("폴더 이름 꼬리표(삼성전기 · 고객사 색)", 'class="mbx-fdtag fk-customer" title="폴더">삼성전기</span>' in h, h.count("mbx-fdtag"))
    gen_row = h[h.find('data-mail-id="%d"' % M_GEN):]
    gen_row = gen_row[:gen_row.find("</a>")]
    check("「일반」 메일에는 폴더 꼬리표 안 붙임", "mbx-fdtag" not in gen_row, gen_row[:300])
    check("메일 없는 폴더는 접힘 — 「＋ 메일 없는 N곳」", "＋ 메일 없는 " in sd and "mfShowZero(" in h)

    print("== 4. 앱 머리띠(kmail) — 빨간 줄 + 늘 보이는 도구 줄(11-19 대표 「고정」) ==")
    km = client(port=5053, host="kmail.knknara.co.kr")
    hk = km.get("/mail/inbox").text
    top = hk[hk.find('class="mail-app-top"'):hk.find('id="mailTools"')]
    tools = hk[hk.find('id="mailTools"'):hk.find('</nav>', hk.find('id="mailTools"'))]
    # 11-23 대표 「메일함 글자 누르면 첫 화면 · 그 줄 오른쪽에 자주 쓰는 메뉴 7개 · 뒤로/앞으로」 — 새 메일 쓰기는 도구 줄에만
    _qk = top[top.find('class="mt-quick"'):top.find('</nav>', top.find('class="mt-quick"'))]
    check("머리줄: 메일함 글자 = 받은편지함 첫 화면", 'class="brand" href="/mail/inbox"' in top, top[:200])
    check("머리줄: 자주 쓰는 메뉴 7개(새 메일 쓰기는 없음)", _qk.count('data-q=') == 7 and 'href="/mail/compose"' not in top, _qk[:200])
    check("머리줄: 뒤로·앞으로 두 단추", top.count('mt-hist') == 2 and 'mailGoFwd()' in top)
    check("도구 줄: 새 메일·받은편지함·중요·회신 필요·보낸편지함·임시보관함·보관함·휴지통·스팸함·글자 크게·설정·정리·도움말",
          all(x in tools for x in ('href="/mail/compose"', 'href="/mail/inbox"', 'href="/mail/inbox?star=1"', 'href="/mail/inbox?reply=1"', 'href="/mail/sent"',
                                   'href="/mail/drafts"', 'href="/mail/inbox?arc=1"', 'href="/mail/trash"', 'href="/mail/blocked"', "mailFsStep(1)", 'href="/mail/tools"', "mailHelpToggle")), tools[:300])
    check("빨간 줄 + 도구 줄은 한 상자로 고정(스크롤해도 위에) · body 가 스크롤 상자가 되지 않게", '<div class="mail-app-fixed">' in hk and ".mail-app-fixed { position:sticky; top:0" in hk and "body { height:auto !important; min-height:100dvh !important; overflow:visible !important; }" in hk)
    check("숫자는 바로바로(안 읽음·회신 필요·임시·스팸) · 「새 메일」은 도구 줄 한 곳만", "/api/mail/counts" in hk and "mtcUnread" in hk and ".mbx-cmd .c.new, .mbx-side .mbx-write { display:none !important; }" in hk)
    j = km.get("/api/mail/counts").json()
    check("숫자 API 200 · 칸 다섯", j.get("ok") and all(x in j for x in ("unread", "reply", "drafts", "spam", "arc")), j)
    hc = km.get("/mail/compose").text
    check("kmail 쓰기 화면도 같은 도구 줄 · 보내기 단추줄은 고정 줄 바로 아래", 'id="mailTools"' in hc and "임시보관함" in hc and ".cmp-actions-top { top:var(--mail-fixed-h,0px) !important; }" in hc)
    check("kmail ⚙ 설정·정리 200 · 도구 줄 받은편지함 길 있음", km.get("/mail/tools").status_code == 200 and 'href="/mail/inbox" data-k="in"' in km.get("/mail/tools").text)

    print("== 4-1. 화면 테마 3가지(11-19 대표 「누런 바탕이라 눈이 아프고 글씨가 잘 안 보임 · 골라서 쓰게」) ==")
    check("테마 셋(밝게·부드럽게·어둡게) · 기본 = 밝게 · 이 컴퓨터에 기억 · 화면 그리기 전에 적용",
          all(x in hk for x in ('html[data-mt="clear"]', 'html[data-mt="soft"]', 'html[data-mt="dark"]', "knkmail.theme", "setAttribute('data-mt', t)"))
          and hk.find("knkmail.theme") < hk.find('class="mail-app-top"'))
    check("도구 줄 「🎨 테마」 → 카드 셋(누르면 바로) · Esc·바깥 누르면 닫힘",
          "mailThemeToggle(event)" in tools and 'id="mailThemePop"' in hk and all(("mailThemeSet('%s')" % k_) in hk for k_ in ("clear", "soft", "dark")) and "e.key==='Escape'" in hk)
    _tt = km.get("/mail/tools").text
    check("⚙ 설정·정리에도 「화면 테마」 카드 셋(같은 설정)", 'id="mtThemeRow"' in _tt and _tt.count('class="mt-card"') == 6, _tt.count('class="mt-card"'))
    check("메일 본문·쓰는 칸은 어느 테마에서나 흰 종이(받는 사람 모양 그대로)",
          "html[data-mt] .mv-frame{ background:#fff !important" in hk and "html[data-mt] .cmp-editor{ background:#fff !important; color:#111 !important; }" in hk)
    check("화면 글 속 고정 색 = 테마 값(없으면 원래 색) — 기본 모양 그대로", "var(--mt-surface,var(--knk-mail-c-white))" in hk and "var(--mt-surface,var(--knk-mail-c-yellow-02))" in hk and "--knk-mail-c-white:#ffffff;" in hk)
    check("새 창(더블클릭)도 같은 테마", "knkmail.theme" in km.get("/mail/%d?win=1" % M_CUST).text)
    check("칸 구분선 또렷하게(11-19 대표 「구분선이 잘 안 보여」): 테마마다 경계선·손잡이 줄 색 · 칸 사이 줄 양쪽 선 · 스크롤 막대 회색",
          # 11-22 밤 새 디자인(mail_design_v2 · 테마 조각 뒤에 붙음)이 밝게 테마 선 색을 한 번 더 정함 → 테마 3가지 정의 부분만 센다
          # 11-28 1단계: 테마 값은 --knk-*(경계선 = --knk-border-strong · 손잡이 줄 = --knk-mail-gutter) · --mt-sep·--mt-gutter 는 별칭 한 번
          hk.split("window.MD_ICONS")[0].count("--knk-border-strong:") == 3 and hk.split("window.MD_ICONS")[0].count("--knk-mail-gutter:") == 3 and "--mt-sep:var(--knk-border-strong)" in hk and "--mt-gutter:var(--knk-mail-gutter)" in hk and "html[data-mt] .mbx-gutter{ background:var(--mt-gutter) !important; box-shadow:inset 1px 0 0 var(--mt-sep)" in hk
          and "html[data-mt] .main{ scrollbar-color:var(--mt-thumb) var(--mt-track); }" in hk)
    # 11-19 대표 「화면 구성 비율이 안 맞지? 이런 게 많은데 · 모니터 크기 비율에 자동으로 맞게」 — 회사 표준(시트여백·자동 높이)
    import re as _re
    _caps = []
    for _f in ("mail_compose", "mail_tools", "mail_folders", "mail_folders_general", "mail_cleanup", "mail_signature", "mail_rules", "mail_account", "mail_view_win"):
        _src = open(os.path.join(ROOT, "app", "templates", _f + ".html"), encoding="utf-8").read()
        for _cls in ("cmp-card", "mt-wrap", "mf-wrap", "gn-wrap", "cl-wrap", "sig-card", "rl-card", "ac-card", "mw-wrap"):
            _m = _re.search(r"\." + _cls + r"\{([^}]*)\}", _src)
            if _m and ("max-width" in _m.group(1) or "margin:0 auto" in _m.group(1)):
                _caps.append(_f + "." + _cls)
    check("메일 화면 래퍼에 폭 캡(max-width)·가운데 정렬 없음 — 모니터 폭 꽉(좌우 여백만)", not _caps, _caps)
    _hc2 = km.get("/mail/compose").text
    check("메일 쓰기: 쓰는 칸 높이 = 화면 남은 높이(창 크기 바꾸면 다시) · 카드 풀폭",
          "window.cmpFitEditor=fit" in _hc2 and "addEventListener('resize', later)" in _hc2 and "padding:18px;margin:0 var(--content-pad,32px) 24px}" in _hc2)
    check("설정·정리: 넓은 모니터면 정리 칸 6개 한 줄", "@media(min-width:1800px){.mt-tiles{grid-template-columns:repeat(6,minmax(0,1fr))}}" in km.get("/mail/tools").text)
    _tw = k.get("/mail/tools").text
    check("WORKS 화면(앱 아님)에는 테마 안 들어감(회사 다른 화면 그대로)", "knkmail.theme" not in h and 'id="mtThemeRow"' not in _tw and 'class="mail-app-top"' not in h)

    print("== 5. 읽기 화면 ==")
    p = k.get("/mail/%d/pane" % M_CUST).text
    act = p[p.find('class="mv-actions"'):p.find('id="mvMore"')]
    more = p[p.find('id="mvMore"'):p.find("</details>", p.find('id="mvMore"'))]
    # 11-21 대표 「메뉴 중복 · 메일 내용을 더 많이」 — 중요·보관·삭제 단추는 그림만(뜻은 title·aria-label) → 「🗑 삭제」 글자 대신 그림 단추+뜻으로 확인
    check("밖: 답장 · 전체답장 · 전달 · 중요 · 삭제", all(x in act for x in ("↩ 답장</a>", "↩↩ 전체답장", "↪ 전달", 'id="mvStarBtn"', 'title="🗑 삭제 — 휴지통으로 (Delete)" aria-label="삭제">[i:trash-2]</button>')), act[:500])
    # 11-26 대표 「메뉴 중 가장 많이 사용할 것들은 맡기기 오른쪽으로」 — 안 읽음·할 일·인쇄는 PC 빠른 단추(mv-quick · 휴대폰은 메뉴 안 mv-mob) · 다시 안 받기는 메뉴 안 그대로
    _qk = "".join(seg for seg in act.split("<") if "mv-quick" in seg)
    check("밖: 안 읽음·할 일·인쇄 = PC 빠른 단추(mv-quick)만 · 다시 안 받기는 밖에 없음", "muteSender()" not in act and "markUnread()" in _qk and "mvPrint()" in _qk
          and act.count("markUnread()") == 1 and act.count("mvPrint()") == 1, _qk[:300])
    check("⋯ 메뉴 안 안 읽음·인쇄 = 휴대폰에서만(mv-mob)", 'class="mv-mob" onclick="markUnread()"' in more and 'class="mv-mob" onclick="mvPrint()"' in more)
    check("⋯ 더 보기 안: 안 읽음 · 할 일·일정(→ 🚩 상자) · 주소록 · 번역 3 · 인쇄 · 다시 안 받기",
          all(x in more for x in ("markUnread()", "[i:clipboard-list] 할 일·일정으로", 'id="mvContactBtn"', "translateMail('ko')", "translateMail('vi')", "translateMail('en')", "mvPrint()", "muteSender()")), more[:600])
    check("「↩ 답장 쓰기」(회신 띠) 중복 없음", "↩ 답장 쓰기" not in p)
    check("제목 옆 「일반」 꼬리표 없음", 'class="mv-badge"' not in p)
    check("「☆ 중요 표시」 처음 상태(11-21 그림 단추 ☆ + 뜻)", 'aria-label="중요 표시">[i:star]</button>' in act and "☆ 중요 표시" in act and 'mv-star"' in act)
    j = k.post("/mail/%d/star" % M_CUST).json()
    p2 = k.get("/mail/%d/pane" % M_CUST).text
    check("중요 표시 → 읽기 화면 「⭐ 중요」 · 왼쪽 ⭐ 중요 목록에 나옴",
          j.get("ok") and j.get("starred") and 'aria-label="중요">[i:star]</button>' in p2 and 'mv-star on"' in p2 and 'data-mail-id="%d"' % M_CUST in k.get("/mail/inbox?star=1").text, j)
    pf = k.get("/mail/%d" % M_CUST).text
    check("풀페이지 읽기도 200 · ← 목록 단추", "← 목록" in pf and 'id="mvMore"' in pf)
    check("남의 메일 중요 표시 못 함", k.post("/mail/%d/star" % M_OTHER).status_code in (403, 404) or not k.post("/mail/%d/star" % M_OTHER).json().get("ok"))

    print("== 6. ⚙ 설정·정리 ==")
    t = k.get("/mail/tools")
    th = t.text
    check("설정·정리 200", t.status_code == 200, t.status_code)
    for nm, needle in (("보낸 곳별 정리", 'href="/mail/cleanup"'), ("같은 메일 정리", "dedupInbox(event)"), ("일반 정리하기", 'href="/mail/folders/general"'),
                       ("휴지통", 'href="/mail/trash"'), ("폴더 관리", 'href="/mail/folders"'), ("자동 분류 규칙", 'href="/mail/rules"'),
                       ("서명", 'href="/mail/signature"'), ("내 회사 주소 연결", 'href="/mail/account"'), ("스팸함", 'href="/mail/blocked"')):
        check("설정·정리에 「%s」" % nm, needle in th, needle)
    check("대표(관리자): 관리자 칸(받기·보내기·가져오기·저장 공간) + 차단 목록 관리",
          all(x in th for x in ("/admin/mail-inbound", "/admin/mail-send", "/admin/mail-fetch", "/admin/mail-purge", "/mail/blocklist")))
    check("같은 메일 정리 단추 동작(POST /mail/dedup)", k.post("/mail/dedup").json().get("ok"))
    _U["v"] = {"id": OTHER, "role": "member", "name": "시험이", "team_id": None, "team_name": ""}
    th2 = k.get("/mail/tools").text
    check("직원: 관리자 칸·차단 목록 관리 안 보임", "/admin/mail-" not in th2 and "/mail/blocklist" not in th2 and 'href="/mail/cleanup"' in th2)
    check("직원도 처음부터 「케이엔케이」 부서 폴더(11-24) → 일반 정리하기 보임", "/mail/folders/general" in th2)
    h2 = k.get("/mail/inbox").text
    check("직원 받은편지함 200 · 「📁 폴더」(케이엔케이 부서) · 대표 고객사 폴더 없음 · 분류 칸 없음(11-24)", "[i:folder] 폴더" in side(h2) and "1.고객사" not in side(h2) and "?cat=" not in side(h2))
    _U["v"] = {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": ""}

    print("== 7. 다른 메일함 ==")
    for path in ("/mail/sent", "/mail/drafts", "/mail/trash", "/mail/blocked", "/mail/inbox?fd=gen", "/mail/inbox?reply=1", "/mail/inbox?star=1", "/mail/inbox?q=%EB%B0%9C%EC%A3%BC"):
        rr = k.get(path)
        check("%s 200 · 왼쪽 메일 쓰기" % path, rr.status_code == 200 and 'class="mbx-write"' in rr.text, rr.status_code)
    check("스팸함을 열면 왼쪽 「🚫 스팸함」에 지금 위치 표시", re.search(r'href="/mail/blocked" class="mbx-fold on"', side(k.get("/mail/blocked").text)) is not None)
    _U["v"] = None
    check("로그인 안 하면 설정·정리 → /login", k.get("/mail/tools").status_code == 303)
finally:
    m.get_user = _keep

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
