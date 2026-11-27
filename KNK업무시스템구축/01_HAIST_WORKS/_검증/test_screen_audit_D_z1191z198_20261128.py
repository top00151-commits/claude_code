# -*- coding: utf-8 -*-
"""z1191z198 화면 전수 점검(04 지시문 11-27 21:00 최종) 묶음 D(P2·P3) · 글자 검사
   홈 일일업무 카드 = 작성 안 함/작성함 · 메뉴 5화면 권한 없음 = ?no_perm=sales 안내 · 휴대폰 허브 단추 = 권한대로
   맨 위 그림 단추 aria-label · 좁은 창 빅터 도크 320px · /weekly 업무 0건 = 「이번 주 업무 없음」 · /export/fta 거르기 한국어·베트남어
   /daily·/profile 숫자 카드 2칸 · 제목 위 영어 글씨 · /changes 빈 화면 첫 등록
   (실제 확인 = scratchpad z198 · 권한 없는 직원(제조기술2팀)으로 시험 사본에서 화면 부르기)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "app", "templates")
def rd(*n):
    f = os.path.join(*n)
    return open(f, encoding="utf-8").read() if os.path.exists(f) else ""
def nocmt(s): return re.sub(r"\{#.*?#\}", "", s, flags=re.S)
R = []
def check(l, c):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l)

hm = nocmt(rd(T, "home.html"))
check("홈 일일업무 카드 = 작성 안 함 / 작성함(1·0 고정 없음)", "{% if total_my == 0 %}작성 안 함{% else %}작성함{% endif %}" in hm and "{{ 1 if total_my == 0 else 0 }}" not in hm)
check("홈 날짜 ‹ › 44px(묶음 M) 그대로", "min-width: 44px; min-height: 44px" in rd(T, "home.html"))

mn = rd(ROOT, "app", "main.py")
check("메뉴 3화면(견적·수주·미수) 권한 없음 = ?no_perm=sales · 로그인 풀림 = 로그인", mn.count('RedirectResponse("/home?no_perm=sales" if get_user(req) else "/login", 303)') == 3)
check("프로젝트 권한 없음 = ?no_perm=sales", 'if not can_view_sales(u):\n        return RedirectResponse("/home?no_perm=sales", 303)' in mn)
check("영업 기회 권한 없음 = 역할 홈 + ?no_perm=sales", 'RedirectResponse(role_home(u) + "?no_perm=sales", 303)' in mn)

ch = rd(T, "_v5_partials", "chrome.html")
check("휴대폰 허브 단추 = 권한대로(workspaces) · 통합 단추 그대로", "_wsk198 = (workspaces|default([], true))|map(attribute='key')|list" in ch and "{% if not _wsk198 or 'sales' in _wsk198 %}" in ch and "{% if not _wsk198 or 'logi' in _wsk198 %}" in ch and 'href="/home">{{ i.ch_hub_home }}</a>' in ch)
for lab in ('aria-label="{{ i.ch_refresh_t }}"', 'aria-label="{{ i.ch_noti }}"', 'aria-label="{{ i.ch_theme_t }}"', 'aria-label="{{ i.ch_help }}"', 'aria-label="{{ i.ch_logout }}"', 'aria-label="휴대폰에 WORKS 앱 설치"', 'aria-label="{{ i.ch_install_t }}"'):
    check("맨 위 단추 이름 %s" % lab, lab in ch)
check("빅터 AI 단추 이름", 'aria-label="{{ i.ch_vd_name }} AI' in ch)
check("좁은 창(768~1023) 빅터 도크 320px · 휴대폰 전체 폭 그대로", re.search(r"@media \(min-width:768px\) and \(max-width:1023px\) \{[^\n]*\n\s*\.victor-dock \{ width: 320px; max-width: 100%; \}", ch) is not None and ".victor-dock { width: 100%; }" in ch)

wk = nocmt(rd(T, "weekly.html"))
check("/weekly 업무 0건 = 「이번 주 업무 없음」(미흡·준비 아님)", wk.count("이번 주 업무 없음") >= 2 and "{% elif total == 0 %}준비" not in wk)

ft = nocmt(rd(T, "fta_list.html"))
check("/export/fta 상태 거르기 = 한국어(베트남어 화면 = 베트남어) · 주소 값 그대로", "('DRAFT', '초안', 'Nháp')" in ft and "status={{ _c }}" in ft and ">DRAFT</a>" not in ft)

for f, sel in (("daily.html", '[data-dn="daily-kpi-bento"]'), ("profile.html", '[data-dn="profile-kpi"]')):
    check("%s 숫자 카드 1023px 이하 2칸" % f, (".bento%s { grid-template-columns: repeat(2, minmax(0, 1fr)) !important;" % sel) in rd(T, f))

for f, bad in (("changes_list.html", "Change Notice"), ("tickets_list.html", "Ticket Tracker"), ("issues_list.html", "AS Database"), ("board_list.html", "|upper }} BOARD"), ("dashboard.html", "CEO DASHBOARD")):
    check("%s 제목 위 영어 글씨 없음" % f, bad not in rd(T, f))
check("/changes 빈 화면 첫 등록 단추", "＋ 첫 변경 공지 등록" in rd(T, "changes_list.html"))

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
