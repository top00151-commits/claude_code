# -*- coding: utf-8 -*-
"""z1191z205 디자인 4단계(화면 옮기기) — 화면별 직접 색 · 화면 안 <style> · 끝 기준 · 일부러 어김
대표 11-28 「진행해」 · 기준 문서 HAIST WORKS디자인변경/2026-11-28_화면기준표_KNK브랜드/2026-11-28_1121_…_v2_디자인을_코드로.md 4단계
이번 판 = 앞 3화면(작업 일정표 · 수주 목록 · 수주 상세) · z204(75f157c9) 위로 합친 뒤 남은 17색까지. 견적서·홈·로그인은 다음 판.
"""
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(H, "deploy"))
import check_standards as C

ok = fail = 0
def check(name, cond):
    global ok, fail
    if cond: ok += 1; print("  ✅", name)
    else: fail += 1; print("  ❌", name)

def rd(rel): return open(os.path.join(H, rel), encoding="utf-8").read()

def hexes(rel, src=None):
    s = C._strip_comments_keep_lines(src if src is not None else rd(rel))
    return [(s[:m.start()].count("\n") + 1, m.group(0)) for m in C.HEX_RE.finditer(s)]

def styles(src):
    return re.findall(r"<style\b[^>]*>(.*?)</style>", src, re.S | re.I)

# ── 1. 화면별 직접 색 ──
# 작업 일정표: 남은 직접 색은 z204(명단·달력)가 고치는 「오늘」 줄과 맞닿은 줄뿐(273-276 · 317-319 · 518-520 둘레)
SB_KEEP = re.compile(r"\.day\.today|\.sched \.day \{|tr:hover:not\(\.unit-exp-row\) > td|row-selected:hover > td\.c1")
sb_css = rd("static/css/schedule_board.css")
left = hexes("static/css/schedule_board.css")
lines = sb_css.split("\n")
check("작업 일정표 화면 직접 색 0", hexes("app/templates/schedule_board.html") == [])
check("작업 일정표 CSS 직접 색 0 (z204 합친 뒤 오늘 표시 줄까지)", left == [])
check("일정표 오늘 = --knk-cal-today 테두리 · 마우스 올린 줄 = --knk-highlight",
      ".sched .day.today { box-shadow: inset 2px 0 0 var(--knk-cal-today), inset -2px 0 0 var(--knk-cal-today)" in sb_css
      and "box-shadow: inset 0 2px 0 var(--knk-highlight), inset 0 -2px 0 var(--knk-highlight) !important" in sb_css and "#f59e0b" not in sb_css.lower())
check("수주 목록 직접 색 0 (z204 합친 뒤 월 고르기 칸까지)", hexes("app/templates/sales_orders.html") == [])
check("수주 상세 직접 색 0", hexes("app/templates/sales_order_detail.html") == [])
check("수주 상태 알약 직접 색 0", hexes("app/templates/_v5_partials/so_status_pill.html") == [])

# ── 2. 화면 안 <style> ──
sb = rd("app/templates/schedule_board.html")
check("작업 일정표 화면 안 <style> 0 (연·월 고르기 판·연기 창 → schedule_board.css)", styles(sb) == [] and ".ym-pop{" in sb_css and "#dl128 .dl128-box" in sb_css)
check("옮긴 연·월 단추 = !important 없이 같은 힘(.ym-pop .ym-mb{ padding:0; })", ".ym-pop .ym-mb{ padding:0; }" in sb_css and "padding:0 !important" not in sb_css.split("z1191z205")[-1])
so = rd("app/templates/sales_orders.html")
check("수주 목록 화면만의 --qv-* 덮기 뺌", "--qv-surface:" not in so and "--qv-ink:" not in so)
check("수주 목록 그러데이션 0", "linear-gradient(135deg" not in so)
sd = rd("app/templates/sales_order_detail.html")
check("수주 상세 <style> = 사업부 색 + 배치 몇 줄(--qv 다리 뺌)", len(styles(sd)) == 1 and "--qv-surface:" not in sd and len(styles(sd)[0].strip().splitlines()) <= 22)

# ── 3. 뜻 이름 ──
tok = rd("static/css/v5_tokens.css")
for n in ("--knk-cat-violet", "--knk-cat-violet-subtle", "--knk-cat-violet-line", "--knk-cat-orange", "--knk-cat-orange-subtle", "--knk-cat-orange-line",
          "--knk-highlight", "--knk-highlight-subtle", "--knk-cal-holiday", "--knk-cal-sat", "--knk-cal-vn", "--knk-cal-today"):
    check("새 이름 %s = v5_tokens.css 에 정의 · 견본(/admin/design-kit)에 보임" % n, re.search(re.escape(n) + r"\s*:", tok) and ("'%s'" % n) in rd("app/templates/admin_design_kit.html"))
check("달력 색 = knk-calendar 값 그대로", all(x in tok for x in ("--knk-cal-holiday:       #DC2626", "--knk-cal-sat:           #2563EB", "--knk-cal-vn:            #FB923C", "--knk-cal-today:         #D4A574")))
check("일정표 달력 머리: 일·휴일 = --knk-cal-holiday · 토 = --knk-cal-sat · V = --knk-cal-vn",
      "th.day.redday { color:var(--knk-cal-holiday)" in sb_css and "th.day.satday { color:var(--knk-cal-sat)" in sb_css and ".hb i.v { background:var(--knk-cal-vn)" in sb_css)
check("수주 목록 달력: 오늘 = --knk-cal-today · 일 빨강 · 토 파랑", ".cal-day.today { box-shadow:inset 0 0 0 2px var(--knk-cal-today)" in so and ".cal-dow.sun { color:var(--knk-cal-holiday); } .cal-dow.sat { color:var(--knk-cal-sat); }" in so)
check("납품·출하·지연 범례 = 정보·완료·위험 이름(일정표 막대와 같은 이름)",
      '<i style="background:var(--knk-info);"></i>납품' in sb and '<i style="background:var(--knk-success);"></i>출하' in sb and '<i style="background:var(--knk-danger);"></i>지연' in sb
      and ".m-deliver { color:var(--knk-info)" in sb_css and ".m-ship    { color:var(--knk-success)" in sb_css)
check("「확인 필요」 노랑(단가 미정) = --knk-warning-subtle 뜻 그대로", 'style="background:var(--knk-warning-subtle);color:var(--knk-warning);border-color:var(--knk-warning-line);">미정' in sb)
pill = rd("app/templates/_v5_partials/so_status_pill.html")
check("수주 상태 알약 = 뜻 이름(완료·위험·정보·확인)", ".so-pill-paid          { background:var(--knk-success-subtle)" in pill and ".so-pill-cancelled     { background:var(--knk-danger-subtle)" in pill and ".so-pill-shipped       { background:var(--knk-info-subtle)" in pill)

# ── 4. 빨강 채운 단추 한 화면에 하나 ──
check("일정표 💾 저장 확인 = 흰 바탕 + 빨강 글자·테두리(채운 빨강 단추 늘리지 않음)",
      'id="sbSaveBtn"' in sb and 'style="background:var(--knk-bg-surface);color:var(--knk-brand);border:1px solid var(--knk-brand);"' in sb)

# ── 5. 머리 = 세 줄 표식(제목 띠 높이 그대로) ──
T3 = '<span class="k-tri" aria-hidden="true"><i></i><i></i><i></i></span>'
check("제목 앞 세 줄 표식 — 일정표·수주 목록·수주 상세", T3 + "<em>작업 일정표</em>" in sb and T3 + "<em>수주</em> 목록" in so and T3 + "{{ order.order_no }}" in sd)
check("세 줄 표식 자리 규칙(knk-components.css)", ".page-title > .k-tri, .knk-page-title > .k-tri { margin-right:8px; vertical-align:-1px; }" in rd("static/css/knk-components.css"))

# ── 6. 검사기 ⑤-2 가 일부러 어긴 코드를 잡는지 ──
base = C.COLOR_BASE
for rel in ("app/templates/schedule_board.html", "static/css/schedule_board.css", "app/templates/sales_orders.html", "app/templates/sales_order_detail.html"):
    n = len(hexes(rel))
    check("⑤-2 면제값 내림 %s = %d" % (rel, n), base.get(rel, 0) == n)
bad_src = rd("app/templates/sales_order_detail.html").replace("</style>", ".x{color:#123456}</style>", 1)
hits = [h for h in C.check_direct_colors([os.path.join(H, "app/templates/sales_order_detail.html")]) ]
import tempfile, shutil
td = tempfile.mkdtemp(); p2 = os.path.join(td, "sales_order_detail.html"); open(p2, "w", encoding="utf-8").write(bad_src)
check("일부러 어김: 수주 상세에 #123456 → ⑤-2 가 한 줄 잡음", len(C.check_direct_colors([p2])) == len(hits) + 1 == 1)
bad2 = sb.replace("var(--knk-info);\"></i>납품", "#2563eb;\"></i>납품", 1); p3 = os.path.join(td, "schedule_board.html"); open(p3, "w", encoding="utf-8").write(bad2)
check("일부러 어김: 일정표 범례 색을 되돌림 → ⑤-2 가 잡음", len(C.check_direct_colors([p3])) == 1)
shutil.rmtree(td, ignore_errors=True)

print("결과: %d 통과 / %d 실패" % (ok, fail))
sys.exit(1 if fail else 0)
