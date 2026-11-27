# -*- coding: utf-8 -*-
"""z1191z191 화면 전수 점검(04 지시문 11-27 21:00 최종) 묶음 A — 스크롤하면 표 칸 이름이 사라짐 · 글자 검사
   A-1 견적·발주서(/sales/quotations): 표의 overflow:hidden 빼기(칸 이름 고정이 본문 기준으로) · 휴대폰만 표 옆 스크롤 상자
   A-2 진행 매트릭스(/progress): 넓은 표 → 자체 스크롤 상자 + 높이 자동 채움 + 칸 이름(위)·관리코드(왼쪽) 고정
   A-3 수출(/export): 「달마다 인보이스」·「모든 선적 건」 칸 이름 고정 · 옆 스크롤은 휴대폰만
   (실제 화면 시험 = scratchpad z191 · 시험 서버 두 대 · 지시문 11-2 콘솔 코드 · 1440·892·820·412·360)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "app", "templates")
def rd(n): return open(os.path.join(T, n), encoding="utf-8").read()
def nocmt(s): return re.sub(r"\{#.*?#\}", "", re.sub(r"/\*.*?\*/", "", s, flags=re.S), flags=re.S)
R = []
def check(l, c):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l)

# ── A-1 ─────────────────────────────────────────────
q = nocmt(rd("sales_quotations.html"))
m = re.search(r"\.qm-t \{([^}]*)\}", q)
check("A-1 .qm-t 에 overflow 없음(칸 이름 고정이 표 안에 갇히지 않게)", m and "overflow" not in m.group(1))
check("A-1 칸 이름 고정(sticky top:0) 유지", re.search(r"\.qm-t th \{[^}]*position:sticky; top:0", q) is not None)
check("A-1 표 두 개 모두 옆 스크롤 상자(.qm-hs)로 감쌈", q.count('<div class="qm-hs"><table class="qm-t') == 2 and q.count("</table></div>") >= 2)
check("A-1 옆 스크롤은 휴대폰(767px 이하)만 — PC·폴드는 본문 스크롤 고정 그대로",
      re.search(r"@media \(max-width: 767px\) \{ \.qm-hs \{ overflow-x: auto;", q) is not None and re.search(r"^\.qm-hs \{[^}]*overflow", q, re.M) is None)

# ── A-2 ─────────────────────────────────────────────
p = nocmt(rd("progress_matrix.html"))
check("A-2 상자 = 자체 스크롤(overflow:auto) + 높이 자동 채움(data-knk-fill)", ".mtx-box {" in p and "overflow: auto" in p and 'class="mtx-box"{% if matrix %} data-knk-fill' in p)
check("A-2 칸 이름 고정(thead th sticky top:0)", re.search(r"\.mtx thead th \{ position: sticky; top: 0;", p) is not None)
check("A-2 관리코드 칸 왼쪽 고정", re.search(r"\.mtx td\.proj, \.mtx th\.proj \{ position: sticky; left: 0;", p) is not None)
check("A-2 메뉴로 옮겨 온 때도 높이 다시 채움(knkFill)", "window.knkFill && window.knkFill()" in p)
check("A-2 옛 인라인 overflow-x 상자 없음", 'style="margin: 0 var(--content-pad);overflow-x:auto' not in p)

# ── A-3 ─────────────────────────────────────────────
e = nocmt(rd("export_board.html"))
check("A-3 두 표에 칸 이름 고정 표시(exb-t)", e.count('<table class="ex-tbl exb-t">') == 2)
check("A-3 칸 이름 고정 규칙(sticky top:0 · 배경)", re.search(r"\.exb-t thead th \{ position: sticky; top: 0;[^}]*background", e) is not None)
check("A-3 감싼 칸의 옆 스크롤은 휴대폰만", 'style="overflow-x:auto"><table class="ex-tbl' not in e and "ex-card\" style=\"overflow-x:auto\"" not in e
      and re.search(r"@media \(max-width: 767px\) \{ \.exb-hs \{ overflow-x: auto;", e) is not None)
z85 = rd("_export_z85.html")
check("A-3 공용 수출 틀(_export_z85.html)은 그대로(다른 수출 화면 영향 0)", "exb-" not in z85)

# ── 바꾸지 말 것 ──────────────────────────────────────
sh = rd(os.path.join("_v5_partials", "knk_sticky_head.html"))
check("제목 띠 고정(z1191z106)·휴대폰 미고정 그대로", "@media (min-width: 768px)" in sh and "position: sticky; top: 0; z-index: 40;" in sh)

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
