# -*- coding: utf-8 -*-
"""z1191z194 화면 전수 점검(04 지시문 11-27 21:00 최종) 묶음 S — 전환 속도·깜빡임·스크롤 · 글자 검사
   S-1 메뉴 누름 즉시 진행 막대·「여는 중」·0.3초 뒤 흐림·같은 링크 두 번 = 한 번(spa_nav)
   S-2 대표 결정 6: 새 판이 나와도 저절로 새로 고치지 않음(띠만 · 누르면 새로 고침 · 메뉴 옮길 때 새 판 z1191z126 그대로)
   S-3 프로젝트 상세: 정보 칸(HTML 맨 뒤)까지 받은 뒤 한 번에 그림(blocking=render)
   S-4 대표 결정 7: 큰 목록(프로젝트·연락처·출하·입금) 201번째부터 <template> 에 두고 내리면 이어 그림 · 「N건 더 있음」 · 거르기·정렬·전체 선택은 모두 붙인 뒤
       수주 목록은 서버가 최근 200건만 → 「최근 200건만 · 전체 N건」 알림(말없이 숨기지 않음)
   + 고객사 화면 다시 열 때 「이미 선언됨」 → 전체 새로 열기(번쩍임) 고침
   (실제 화면 시험 = scratchpad z194 · 시험 서버 두 대 · 3번 가운데 값)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "app", "templates")
def rd(*n):
    f = os.path.join(*n)
    return open(f, encoding="utf-8").read() if os.path.exists(f) else ""
def tp(*n): return rd(T, *n)
R = []
def check(l, c):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l)

spa = tp("_v5_partials", "spa_nav.html")
check("S-1 진행 막대·여는 중·흐림 규칙", "#knkNavBar.on{opacity:1;width:85%}" in spa and 'content:"여는 중…"' in spa and ".main.knk-nav-wait{opacity:.55" in spa)
check("S-1 0.3초 뒤 흐림 · 본문 교체 뒤 거둠", "}, 300);" in spa and "document.addEventListener('knk:navigated', busyOff);" in spa)
check("S-1 같은 링크 두 번 = 한 번 · 마지막 누른 것만 적용", "if (busyUrl && a.href === busyUrl) return;" in spa and "if (my !== busySeq) return null;" in spa)
check("S-1 FULL_ONLY 안전장치 그대로", r"/^\/project\/\d+\/?$/" in spa and r"/^\/sales\/quotations\/?$/" in spa and "if (mustFull(href)) return false;" in spa)
check("S-1 z1191z126 새 판이면 창 전체 새로 열기 그대로", "_v126 !== _lv126" in spa)

ch = tp("_v5_partials", "chrome.html")
i0 = ch.find("function onNewVersion()"); seg = re.sub(r"//.*", "", ch[i0:ch.find("var idleT", i0)])   # 설명 글(//) 빼고
check("S-2 새 판 → 띠만(저절로 새로 고침 안 부름)", "showBanner();" in seg and "safeReload()" not in seg and "watchIdle()" not in seg)
vc = ch[ch.find("document.addEventListener('visibilitychange'"):ch.find("document.addEventListener('visibilitychange'") + 200]
check("S-2 탭을 다시 보거나 뒤로 보내도 저절로 새로 고침 안 함", "safeReload" not in vc)
check("S-2 「지금 새로고침」 단추·입력 지킴(knkDraft) 그대로", "reload.onclick = function () { try { if (window.knkDraft) knkDraft.save(); }" in ch)
i18 = rd(ROOT, "app", "i18n.py")
check("S-2 띠 문구 = 누를 때만(「곧 자동으로」 없음)", "곧 자동으로 새로고침됩니다" not in i18 and "편할 때 「지금 새로고침」을 누르세요" in i18)

pd = tp("project_detail.html")
check("S-3 프로젝트 상세 = 정보 칸까지 받은 뒤 그림", '<link rel="expect" href="#pdPaintReady" blocking="render">' in pd and pd.find('id="pdPaintReady"') > pd.find("</aside>") > 0)

lz = tp("_v5_partials", "knk_rows_lazy.html")
st = tp("_v5_partials", "styles.html")
check("S-4 공용 이어 그리기(knkRowsAll·knkRowsEnsure·rows-added) · 공용 머리에 포함", "window.knkRowsAll" in lz and "window.knkRowsEnsure" in lz and "knk:rows-added" in lz and "knk_rows_lazy.html" in st)
check("S-4 위치 기억이 깊은 곳으로 갈 때 먼저 붙임", "window.knkRowsEnsure(el, it.top)" in ch and "window.knkRowsEnsure(null, wy)" in ch)
for f, extra in (("projects.html", 'colspan="10"'), ("contacts_list.html", 'colspan="15"'), ("sales_shipments_receipts.html", 'data-knk-unit="tr.sr-recA"')):
    s = tp(f)
    check("S-4 %s 201번째부터 template · N건 더 있음" % f, "loop.index0 == 200 %}<template data-knk-rest" in s and "loop.length - 200" in s and "knk-more-all" in s and extra in s)
pj = tp("projects.html")
check("S-4 프로젝트 거르기 = 모두 붙인 뒤", "window.knkRowsAll(tb);" in pj[pj.find("function applyProjFilter"):pj.find("function updateExportLinks")])
cx = tp("contacts_list.html")
check("S-4 연락처 전체 선택·휴대폰 없는 것 = 모두 붙인 뒤 · 새 줄 칸 숨김", "rowsAll().forEach" in cx and cx.count("rowsAll()") >= 3 and "window.__cxApplyHidden194 = applyHidden;" in cx)
sr = tp("sales_shipments_receipts.html")
check("S-4 출하·입금 수금 입력·이력 = 위임(이어 붙인 줄에서도)", "document.addEventListener('submit'" in sr and "closest('.sr-hist-btn')" in sr and "document.querySelectorAll('form.sr-recv-form').forEach" not in sr)
check("S-4 출하·입금 정렬·거르기 = 모두 붙인 뒤", sr.count("window.knkRowsAll(tb)") >= 2)
so = tp("sales_orders.html")
check("S-4 수주 목록 「최근 200건만 · 전체 N건」 알림", "최근 {{ items|length }}건만 · 전체" in so)
cu = tp("customers_list.html")
check("고객사 다시 열 때 「이미 선언됨」 없게(var)", "var cuImportRows = [];" in cu and "let cuImportRows" not in cu)

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
