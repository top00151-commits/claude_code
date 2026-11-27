# -*- coding: utf-8 -*-
"""z1191z193 화면 전수 점검(04 지시문 11-27 21:00 최종) 묶음 M — 휴대폰 · 글자 검사
   M-1 휴대폰 넘침: 매출 홈 · 프로젝트 · 프로젝트 상세 · 일일업무 · 출고 이력 · 작업 일정표 · 고객사 상세 + 새로 찾은 소모품 · 수주 칸 확인 · 매출 보고서 · FTA
   M-2 표가 깊은 곳: 수출 요약 설명 접기(휴대폰) · 프로젝트 사업부·상태 단추 줄 접기(1024 이하 · 대표 11-27)
   대표 11-27: 미수 계산 설명 1024 이하 한 줄 접기
   M-3 누르는 칸: 휴대폰 표 안 링크 위아래 여백 · 줄 링크 40px · 홈 날짜 ‹ › 44px
   M-4 아이폰만 입력 글자 16px(@supports -webkit-touch-callout)
   (실제 화면 시험 = scratchpad z193 · 시험 서버 두 대 · 150화면 휴대폰 훑기 · 45화면 5크기)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "app", "templates")
def rd(*n): return open(os.path.join(*n), encoding="utf-8").read()
def tp(*n): return rd(T, *n)
R = []
def check(l, c):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l)

# ── M-1 ─────────────────────────────────────────────
sh = tp("sales_home.html")
check("M-1 매출 홈 두 칸 = minmax(0,1fr) · 카드 최소 0", "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)" in sh and ".grid-2 > .card { min-width: 0; }" in sh and ".grid-2 { grid-template-columns: 1fr; }" not in sh)
pj = tp("projects.html")
check("M-1 프로젝트: 「＋ 등록은 왼쪽 메뉴」 안내 그대로 · 휴대폰에선 탭 아래 줄로", pj.count("＋ 등록은 왼쪽 메뉴 <b>🆕 등록</b>에서") == 2 and "reg-hint-box-z193" in pj and re.search(r"\.reg-hint-box-z193 \{ flex:1 0 100%;", pj))
pd = rd(ROOT, "static", "css", "project_detail.css")
check("M-1 프로젝트 상세 정보 칸 = minmax(0,1fr) · 긴 값 줄바꿈", "grid-template-columns: 76px minmax(0, 1fr)" in pd and "overflow-wrap: anywhere" in pd)
dl = tp("daily.html")
check("M-1 일일업무 빠른 입력 줄·머리 단추 줄바꿈(휴대폰)", ".qa-bar { flex-wrap: wrap;" in dl and 'style="display:flex;gap:10px;flex-wrap:wrap;"' in dl)
# /stock/issues(자재구매센터 · 재고 = 세션 05·ERP 구역)는 이번 배포에서 뺌 — 대표 판단 뒤 따로
sb = rd(ROOT, "static", "css", "schedule_board.css")
check("M-1 작업 일정표 기간 찾기 줄바꿈(휴대폰)", ".period-grp { flex-wrap:wrap;" in sb)
cd = tp("customer_detail.html")
check("M-1 고객사 상세 칸 최소 0", "grid-template-columns: minmax(0, 1fr) 320px" in cd and ".detail-grid > * { min-width: 0; }" in cd and "repeat(4,minmax(0,1fr))" in cd)
for f, sel in (("consumables.html", "table.list"), ("so_check_z154.html", ".sc-t"), ("sales_report.html", ".rp-t")):
    check("M-1 %s 휴대폰 표 옆 스크롤" % f, re.search(r"@media \(max-width:767px\)\{ %s \{ display:block; max-width:100%%; overflow-x:auto;" % re.escape(sel), tp(f)) is not None)
check("M-1 FTA 거르기 줄바꿈", "@media (max-width:767px){ .filter-bar .group { flex-wrap:wrap; } }" in tp("fta_list.html"))

# ── M-2 · 대표 11-27 접기 ──────────────────────────────
check("M-2 프로젝트 단추 줄: 1024 이하 처음부터 접힘(CSS · 체크 칸) · 고른 단추(.on)는 보임 · 펼치기 단추",
      'id="projFltTog"' in pj and "@media (max-width:1024px)" in pj and ".proj-flt-tog:not(:checked) + .proj-flt-z193 .proj-bm .bm:not(.on)" in pj and 'for="projFltTog"' in pj)
check("M-2 프로젝트 거르기 함수 그대로(projDivFilter·projFilter)", "onclick=\"projDivFilter('T');return false;\"" in pj and "onclick=\"projFilter('ongoing');return false;\"" in pj)
ou = tp("sales_outstanding.html")
check("대표 11-27 미수 설명 1024 이하 한 줄 접기 · 누르면 펼침", "@media (max-width:1024px){ .ar-lead{display:-webkit-box;" in ou and "this.classList.toggle('open')" in ou)
ex = tp("export_board.html")
check("M-2 수출 요약 설명 접기(휴대폰 · 숫자는 보임 · 펼치기)", 'id="exbSumTog"' in ex and ".exb-sum-tog:not(:checked) + .ex-kpis .ex-kpi .s { display:none; }" in ex and 'for="exbSumTog"' in ex)
check("M-2 수출: 묶음 A 칸 이름 고정 그대로 · z85 시험 글자와 안 겹침", ex.count('<table class="ex-tbl exb-t">') == 2 and ex.count("모든 선적 건") == 1)
check("그린 뒤 스크립트로 접지 않음(접기는 CSS·체크 칸)", "projFltTog').checked" not in pj and "exbSumTog').checked" not in ex)

# ── M-3 · M-4 ────────────────────────────────────────
ch = tp("_v5_partials", "chrome.html")
check("M-3 휴대폰 표 안 링크 누르는 칸(위아래 8px) · 줄 링크 40px", ".main .tbl tbody td a:not(.btn):not(.knk-rowlink) { display: inline-block; padding-top: 8px; padding-bottom: 8px; }" in ch and ".main .tbl tbody td a.knk-rowlink { display: block; min-height: 40px; }" in ch)
check("M-3 홈 날짜 ‹ › 44px(휴대폰)", "@media (max-width: 767px) { .page-date-nav a { min-width: 44px; min-height: 44px;" in tp("home.html"))
check("M-4 아이폰만 입력 글자 16px", "@supports (-webkit-touch-callout: none)" in ch and "font-size: 16px !important;" in ch)

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
