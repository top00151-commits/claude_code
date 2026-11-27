# -*- coding: utf-8 -*-
"""z1191z197 화면 전수 점검(04 지시문 11-27 21:00 최종) 묶음 C + 대표 11-28 「수주 목록 전체 보이게」 · 글자·그리기 검사
   C-1 오류 화면(error.html) = 디자인 견본(가짜 전화·「5분 이내 복구」·가짜 진행률) → 상황 하나 · 뒤로·홈·✕ 닫기 · 한글 설명만
   C-2 /guide = 개발 메모(KNK_시작.bat · 검은 명령창 · 09 빅터 팀장 · 시스템 종료 · 사이클 진행 · spike 발주)만 뺌 · 인쇄 규칙 그대로
   C-3 /home 전사 현황 「총괄」「구매팀」 2개씩 = 본사·베트남 법인 부서 같은 이름 → 베트남 부서 앞에 「베트남 · 」
   C-4 알림 요청자 = 이름 직책 부서(vname_full) — 제작요청·소모품 요청·영업 기회 검토 요청
   수주 목록: 서버 200건 제한 없음 · 201번째부터 이어 그림 · 「최근 200건만」 알림 없음
   (실제 화면 시험 = scratchpad z197 · 시험 서버 두 대)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "app", "templates")
def rd(*n):
    f = os.path.join(*n)
    return open(f, encoding="utf-8").read() if os.path.exists(f) else ""
R = []
def check(l, c):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l)

# ── C-1 ─────────────────────────────────────────────
er = re.sub(r"\{#.*?#\}", "", rd(T, "error.html"), flags=re.S)   # 설명 글(주석) 빼고
check("C-1 견본 글 없음(가짜 전화·5분 이내·65%·견본 제목)", all(x not in er for x in ("02-3142", "5분 이내", "65%", "에러 / 로딩", "class=\"gallery\"")))
check("C-1 상황 하나(404·403·그 밖) · 뒤로·홈·✕ 닫기", "_c == 404" in er and "_c == 403" in er and "knkErrBack()" in er and 'href="/home"' in er and 'aria-label="닫기"' in er)
check("C-1 설명은 한글 안내(403·404)만 · 내부 내용 안 보임", "_hangul.on" in er and "{% if _c in (403, 404) and _hangul.on %}" in er)
check("C-1 없는 기능 약속 없음(자동 알림·복구 시간)", "자동으로 알림" not in er and "복구됩니다" not in er)
try:
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(T))
    t = env.get_template("error.html")
    h404 = t.render(status_code=404, detail="Not Found")
    h403 = t.render(status_code=403, detail="게시글 승인 권한이 없습니다")
    h503 = t.render(status_code=503, detail="db locked /app/data/knk.db")
    check("C-1 그리기: 404 제목·영어 설명 안 보임", "찾는 화면이 없습니다" in h404 and "Not Found" not in h404.split("</title>", 1)[1])
    check("C-1 그리기: 403 한글 설명 보임", "이 화면을 볼 권한이 없습니다" in h403 and "게시글 승인 권한이 없습니다" in h403)
    check("C-1 그리기: 503 내부 내용 안 보임 · 다시 시도", "knk.db" not in h503 and "다시 시도" in h503)
except Exception as e:
    check("C-1 그리기(jinja2) %s" % e, False)

# ── C-2 ─────────────────────────────────────────────
gd = rd(T, "guide.html")
body = re.sub(r"\{#.*?#\}", "", gd, flags=re.S)
check("C-2 개발 메모 없음(보이는 글)", all(x not in body for x in ("KNK_시작.bat", "검은 명령창", "09 빅터 팀장", "빅터(09 팀장)", "spike 발주", "사이클 1~73", "99_DISPATCH", "localhost:8081", "핫패치 보존")))
check("C-2 나머지 내용 그대로(빅터AI 도크·핵심 페이지·단축키·문제 발생 시)", all(x in body for x in ("3. 빅터AI 도크", "4. 대표가 직접 확인할 핵심 페이지", "5. 자주 쓰는 단축키", "6. 사용 중 문제 발생 시", "빅터AI가 응답 안 함")))
check("C-2 인쇄 규칙 그대로", "@media print{ .guide-bar{ display:none; }" in gd)
check("C-2 태그 짝 맞음(div)", len(re.findall(r"<div\b", body)) == body.count("</div>"))

# ── C-3 ─────────────────────────────────────────────
hm = rd(T, "home.html")
check("C-3 홈 전사 현황: 베트남 법인 부서만 「베트남 · 」(공용 teamlabel)", "teamlabel(td.team.name, td.team.entity) if ((td.team.entity or '')|string|upper) in ('VN', 'VNM') else td.team.name" in hm)

# ── C-4 ─────────────────────────────────────────────
mn = rd(ROOT, "app", "main.py")
check("C-4 제작요청·소모품 요청 알림 요청자 = vname_full(저장 값 by_name 그대로)", mn.count("by_disp = vname_full(user) if user.get(\"name\") else by_name") == 2 and mn.count("요청자 {by_disp}") == 2 and "취소 {by_disp}" in mn)
check("C-4 영업 기회 검토 요청 요청자 = vname_full", "요청자: {(vname_full(u) if u.get('name') else '—')}" in mn)
check("C-4 저장(issued_by_name)은 그대로 by_name", mn.count("(user.get(\"id\") or None), by_name, sent_to") == 2)

# ── 수주 목록 전체 ───────────────────────────────────
so = rd(T, "sales_orders.html")
check("수주 목록 서버 200건 제한 없음(수주·소모품)", "ORDER BY o.id DESC LIMIT 200" not in mn and "ORDER BY co.id DESC LIMIT 200" not in mn and "ORDER BY o.id DESC\"\"\",   # z1191z197" in mn)
check("수주 목록 201번째부터 이어 그림 · N건 더 있음(전체 = 그린 줄 + 더 있음)", "{% if loop.index0 == 200 %}<template data-knk-rest>" in so and "loop.length - 200" in so and 'colspan="11"' in so)
check("수주 목록 「최근 200건만」 알림 없음", "최근 {{ items|length }}건만" not in so)

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
