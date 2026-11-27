# -*- coding: utf-8 -*-
"""z1191z192 화면 전수 점검(04 지시문 11-27 21:00 최종) 묶음 B — 한 화면에 보이는 자료가 적음 · 글자 검사
   B-1 표 상자가 화면 밖 → /projects · /sales/outstanding 높이 자동 채움(화면별 최소 높이) · 그리기 전에 높이 정함
       공용 높이 채움(knk_autofill): 메뉴로 옮겨 온 화면에서도 다시 잼 · 화면별 최소 높이(data-knk-fill-min)
   B-2 견적: 올리기 칸 두 개를 한 줄 단추 모양(768px 이상)
   B-3 프로젝트: 노란 안내를 한 줄로 접기(자세히 · 폐기함 링크는 접힌 줄에도)
   대표 결정 1: 제목 띠 높이 통일 — 좁은 창 가로 배치 · 글자만 있는 안내 줄 한 줄 접기(CSS 만 · 누르면 펼침)
   대표 결정 2: 수주 목록 — 한 줄로 쌓이는 폭(1100 이하)에서 표 먼저 · 달력 접기/펼치기 · 넓은 PC 그대로
   (실제 화면 시험 = scratchpad z192 · 시험 서버 두 대 · 11-2 콘솔 코드 · 1440·1024·892·820·768·412·360)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "app", "templates")
def rd(*n): return open(os.path.join(T, *n), encoding="utf-8").read()
def nocmt(s): return re.sub(r"\{#.*?#\}", "", re.sub(r"/\*.*?\*/", "", s, flags=re.S), flags=re.S)
R = []
def check(l, c):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l)

# ── 공용 높이 채움 ─────────────────────────────────────
af = nocmt(rd("_v5_partials", "knk_autofill.html"))
check("공용 높이 채움: 메뉴로 옮겨 온 화면(knk:navigated)에서도 다시 잼", "addEventListener('knk:navigated'" in af)
check("공용 높이 채움: 화면별 최소 높이(data-knk-fill-min) · 없으면 기존 340", "data-knk-fill-min" in af and "FLOOR = 340" in af and "if (!(fl > 0)) fl = FLOOR;" in af)

# ── B-1 ─────────────────────────────────────────────
pj = rd("projects.html")
check("B-1 프로젝트 표 상자 = 높이 채움 + 최소 220", 'class="tbl-wrap tbl-sticky" data-knk-fill data-knk-fill-min="220"' in pj)
check("B-1 프로젝트: 그리기 전에 높이 정함(상자 바로 뒤 knkFill)", re.search(r'data-knk-fill-min="220">\{#.*?#\}<script>[^<]*window\.knkFill\(\)', pj) is not None)
ou = rd("sales_outstanding.html")
check("B-1 미수 현황 표 상자 = 높이 채움 + 최소 220 + 그리기 전에", 'data-dn="ar-table" data-knk-fill data-knk-fill-min="220"' in ou and "window.knkFill()" in ou)
ki = rd("_v5_partials", "knk_inputs.html")
check("공용 .tbl-wrap.tbl-sticky 기본값은 그대로(35개 화면 영향 0)", "max-height: calc(100vh - 280px);\n  min-height: 200px;" in ki)

# ── B-2 ─────────────────────────────────────────────
q = rd("sales_quotations.html")
check("B-2 올리기 칸: 768px 이상 한 줄(긴 설명 숨김 · 짧은 설명 보임)", re.search(r"@media \(min-width:768px\)\{ \.qm-drop \{ padding:6px 12px; \} \.qm-drop \.qm-hint \{ display:none; \} \.qm-drop \.qm-hint-s \{ display:inline; \} \}", q) is not None)
check("B-2 끌어다 놓기·누르기 칸(파일 입력) 그대로", 'id="qmTopFile"' in q and 'id="qmPoFile"' in q and q.count('class="qm-hint-s"') == 2)

# ── B-3 ─────────────────────────────────────────────
check("B-3 노란 안내 = 접는 안내(details) · 펼치면 원래 글 그대로", '<details class="proj-intro-note proj-note-fold"' in pj and "관리코드 없이는 등록되지 않습니다." in pj and "행 클릭 시 해당 프로젝트 상세 화면으로 이동합니다." in pj)
summ = pj[pj.find('<details class="proj-intro-note proj-note-fold"'):pj.find("</summary>")]
check("B-3 폐기함 링크는 접힌 줄(summary)에도", 'href="/projects?archived=1"' in summ)
check("10절 「＋ 등록은 왼쪽 메뉴에서」 안내 그대로", "등록은 왼쪽 메뉴" in pj)

# ── 대표 결정 1 ─────────────────────────────────────
sh = rd("_v5_partials", "knk_sticky_head.html")
shc = nocmt(sh)
check("결정1 제목 띠 고정(z1191z106) 그대로", "position: sticky; top: 0; z-index: 40;" in shc and "@media (min-width: 768px)" in shc)
check("결정1 좁은 창(768~1023) 제목 띠 가로 배치", re.search(r"@media \(min-width: 768px\) and \(max-width: 1023px\) \{\s*\.main \.page-head:not\(\.knk-head-free\) \{ flex-direction: row;", shc) is not None)
check("결정1 글자만 있는 안내 줄 = CSS 한 줄 접기(링크·단추·꾸민 칸 든 줄 제외)", "-webkit-line-clamp: 1" in shc and ":not(:has(a, button, input, select, textarea, label, [class]))" in shc)
check("결정1 그린 뒤 스크립트로 접지 않음(누를 때만 펼침)", "foldLines" not in sh and "classList.toggle('knk-head-open')" in sh)

# ── 대표 결정 2 ─────────────────────────────────────
so = rd("sales_orders.html")
check("결정2 1100px 이하: 달력 칸 접힘 · 펼치면 보임 · 표(오른쪽 칸) 순서", re.search(r"\.split > \.col-left \{ display:none; order:1; \}", so) and ".split.so-cal-open > .col-left { display:flex; }" in so and ".split > .col-right { order:2; }" in so)
check("결정2 펼치기 단추 · 넓은 PC 에선 안 보임", 'id="soCalTog"' in so and re.search(r"^\.so-cal-tog \{ display:none;", so, re.M) is not None)
check("결정2 펼침 기억(이 기기) · 목록 상자 높이 채움은 쌓이는 폭에서만", "knk_so_cal_open_z192" in so and "ls.setAttribute('data-knk-fill-min', '300')" in so and "ls.removeAttribute('data-knk-fill')" in so)
check("결정2 넓은 PC 좌우 2단 규칙 그대로", ".split { display:grid; grid-template-columns: var(--so-left-w, 430px) 7px 1fr;" in so and "height: calc(100vh - 230px); min-height: 480px; }" in so)

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
