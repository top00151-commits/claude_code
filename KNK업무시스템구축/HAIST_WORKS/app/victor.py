"""
HAIST Victor — 사내 AI 컨시어지 (Phase 1: 키워드 라우팅)
=========================================================

사용자 자연어 질문을 받아:
  1) 페이지 라우팅 ("결재 어디서 해?" → 하이웍스 링크)
  2) 데이터 조회 ("이번달 매출 알려줘" → DB 집계 + 카드)
  3) 검색 안내 ("리니어가이드 재고" → 자재 검색 결과)
  4) 모르면 → "이렇게 물어보세요" 가이드

정책:
  - Phase 1: 키워드 매칭만 (AI 비용 0)
  - Phase 2: Claude API tool use (사용자 결정 후)
  - AI가 데이터를 수정하지 않음 — 조회·라우팅만
  - 모든 질의/응답은 로그 가능 (DB 추가 시)

사용자 예시:
  "일정 입력 어디서해?"   → 일일업무/캘린더 링크
  "전체 매출 현황"         → 대시보드 데이터 + 링크
  "리니어가이드 입고 현황"  → 자재 검색 결과
  "결재 올려줘"            → 하이웍스 전자결재 링크
  "휴가 신청"              → 하이웍스 결재
  "내 할 일"               → 홈 개인화
  "확인 안 한 변경"         → /changes 필터 링크
"""
from __future__ import annotations
import re
from datetime import date, timedelta

# =====================================================
# 의도 정의 — 30개 핵심 의도
# 각 의도는 (id, 키워드리스트, 핸들러 이름)
# 핸들러는 ctx(user_dict, db_session_func) → dict 반환
# =====================================================

# 키워드 정규화: 공백/특수문자 제거, 소문자
def _norm(s: str) -> str:
    return re.sub(r"[\s\?!\.,~·\-_/]+", "", s.lower())


# 질문에서 키워드가 하나라도 포함되면 매치
def _match_any(q_norm: str, keywords: list[str]) -> bool:
    return any(_norm(k) in q_norm for k in keywords)


# =====================================================
# 핸들러 — 각 의도별 응답 생성
# 반환 구조: {
#   "type": "route|data|search|guide|external",
#   "title": "...",            # 답변 제목
#   "text":  "...",            # 본문 (줄바꿈 OK)
#   "links": [{"label","href","style"}],  # 클릭 가능한 링크들
#   "data":  [...],            # (선택) 데이터 카드들
#   "intent": "intent_id"
# }
# =====================================================

def _link(label: str, href: str, style: str = "primary") -> dict:
    return {"label": label, "href": href, "style": style}


# ── 길 찾기 (라우팅) ──────────────────────────────
def h_schedule_input(u, db):
    return {
        "type": "route",
        "title": "📅 일정/업무 입력",
        "text": "일정은 세 가지 유형으로 입력할 수 있습니다:",
        "links": [
            _link("오늘 할 일 입력 (일일업무)", "/daily", "primary"),
            _link("내 달력 (회의·출장)", "/calendar", "secondary"),
            _link("부서 게시판 공유", "/board/team", "secondary"),
        ],
    }


def h_approval(u, db):
    from .database import get_setting
    url = get_setting("hiworks_approval_url", "https://office.hiworks.com/")
    return {
        "type": "external",
        "title": "📋 전자결재 (하이웍스)",
        "text": "결재는 하이웍스에서 진행합니다. 결재 필요 변경/티켓은 URL을 첨부하면 영향 부서가 자동 확인합니다.",
        "links": [
            _link("하이웍스 전자결재 열기 ↗", url, "primary"),
            _link("변경 등록 (결재 URL 첨부 가능)", "/changes/new", "secondary"),
            _link("티켓 등록 (결재 URL 첨부 가능)", "/tickets/new", "secondary"),
        ],
    }


def h_mail(u, db):
    from .database import get_setting
    url = get_setting("hiworks_mail_url", "https://mail.hiworks.com/")
    return {
        "type": "external",
        "title": "📧 회사 메일",
        "text": "메일은 하이웍스에서 사용합니다.",
        "links": [_link("하이웍스 메일 열기 ↗", url, "primary")],
    }


def h_vacation(u, db):
    from .database import get_setting
    url = get_setting("hiworks_approval_url", "https://office.hiworks.com/")
    return {
        "type": "external",
        "title": "🏖 휴가 신청",
        "text": "휴가는 하이웍스 전자결재에서 신청합니다.",
        "links": [_link("하이웍스 결재 열기 ↗", url, "primary")],
    }


# ── 데이터 조회 ──────────────────────────────
def h_sales(u, db):
    """매출/수주 현황 집계"""
    today = date.today()
    ym = today.strftime("%Y-%m")
    year = today.year
    try:
        with db() as c:
            month_total = c.execute(
                """SELECT COALESCE(SUM(order_amount), 0) AS total, COUNT(*) AS cnt
                   FROM projects
                   WHERE order_date LIKE ? AND order_amount > 0""",
                (f"{ym}%",),
            ).fetchone()
            ytd_total = c.execute(
                """SELECT COALESCE(SUM(order_amount), 0) AS total, COUNT(*) AS cnt
                   FROM projects
                   WHERE order_date LIKE ? AND order_amount > 0""",
                (f"{year}%",),
            ).fetchone()
            by_biz = [dict(r) for r in c.execute(
                """SELECT biz_div, COALESCE(SUM(order_amount), 0) AS total, COUNT(*) AS cnt
                   FROM projects
                   WHERE order_date LIKE ? AND biz_div IN ('T','M')
                   GROUP BY biz_div""",
                (f"{year}%",),
            ).fetchall()]
            active = c.execute(
                "SELECT COUNT(*) FROM projects WHERE status IN ('active','진행중','planning')"
            ).fetchone()[0]
    except Exception as e:
        return {
            "type": "data",
            "title": "💰 매출 현황",
            "text": f"데이터 조회 오류: {e}",
            "links": [_link("전사 대시보드 →", "/dashboard", "primary")],
        }

    def _won(v):
        if v >= 100000000:
            return f"{v/100000000:.1f}억원"
        if v >= 10000000:
            return f"{v/10000000:.1f}천만원"
        return f"{int(v):,}원"

    biz_lines = []
    for r in by_biz:
        name = "T(검사기)" if r["biz_div"] == "T" else "M(자동화)"
        biz_lines.append(f"  • {name}: {_won(r['total'])} ({r['cnt']}건)")

    text = (
        f"📆 {ym} 당월: {_won(month_total['total'])} ({month_total['cnt']}건)\n"
        f"📅 {year} YTD: {_won(ytd_total['total'])} ({ytd_total['cnt']}건)\n\n"
        f"사업부별 (YTD):\n" + ("\n".join(biz_lines) if biz_lines else "  (데이터 없음)") +
        f"\n\n진행 중 프로젝트: {active}건"
    )
    return {
        "type": "data",
        "title": "💰 매출 · 수주 현황",
        "text": text,
        "links": [
            _link("전사 대시보드 →", "/dashboard", "primary"),
            _link("프로젝트 목록 →", "/admin", "secondary"),
        ],
    }


def h_inventory(u, db, query: str = ""):
    """자재 재고 검색 — 검색어 자동 추출"""
    # 질문에서 키워드 추출 (매우 간단한 휴리스틱)
    # "리니어가이드 입고 현황" → "리니어가이드"
    cleaned = re.sub(r"(입고|재고|현황|알려|줘|검색|찾아|있나|얼마|어디)", "", query).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    search_term = cleaned if len(cleaned) >= 2 else ""

    items = []
    total_cnt = 0
    try:
        with db() as c:
            # parts 테이블 존재 여부 먼저 확인
            try:
                if search_term:
                    like = f"%{search_term}%"
                    rows = c.execute(
                        """SELECT part_no, name, spec, stock_qty, safety_stock, unit
                           FROM parts
                           WHERE is_active=1 AND (name LIKE ? OR part_no LIKE ? OR spec LIKE ?)
                           ORDER BY name LIMIT 10""",
                        (like, like, like),
                    ).fetchall()
                else:
                    rows = c.execute(
                        """SELECT part_no, name, spec, stock_qty, safety_stock, unit
                           FROM parts WHERE is_active=1
                           ORDER BY (stock_qty < COALESCE(safety_stock,0)) DESC, name
                           LIMIT 10"""
                    ).fetchall()
                items = [dict(r) for r in rows]
                total_cnt = c.execute(
                    "SELECT COUNT(*) FROM parts WHERE is_active=1"
                ).fetchone()[0]
            except Exception:
                items = []
                total_cnt = 0
    except Exception:
        pass

    if not items and not search_term:
        return {
            "type": "data",
            "title": "📦 자재 재고",
            "text": f"전체 활성 자재: {total_cnt}개\n\n검색어를 포함해서 물어봐 주세요.\n예: \"리니어가이드 재고\", \"볼트 얼마 있어?\"",
            "links": [_link("자재 관리 →", "/logistics/parts", "primary")],
        }

    if not items:
        return {
            "type": "data",
            "title": "📦 자재 재고",
            "text": f"'{search_term}' 검색 결과가 없습니다.",
            "links": [_link("자재 관리 →", "/logistics/parts", "primary")],
        }

    lines = []
    for r in items:
        stock = r.get("stock_qty") or 0
        safe = r.get("safety_stock") or 0
        mark = " 🔴 안전재고↓" if safe and stock < safe else ""
        lines.append(f"  • [{r.get('part_no','')}] {r.get('name','')} — {stock}{r.get('unit') or ''}{mark}")
    label = f"'{search_term}' 검색 결과" if search_term else "전체"
    text = f"{label} {len(items)}건:\n" + "\n".join(lines)
    return {
        "type": "data",
        "title": "📦 자재 재고",
        "text": text,
        "links": [
            _link("자재 관리 →", "/logistics/parts", "primary"),
            _link("발주 현황 →", "/logistics/po", "secondary"),
        ],
    }


def h_my_todo(u, db):
    """내 미처리 업무 요약"""
    uid = u.get("id") if u else None
    team_id = u.get("team_id") if u else None
    if not uid:
        return {"type": "guide", "title": "로그인 필요", "text": "로그인 후 다시 물어봐 주세요.", "links": []}

    today_s = date.today().isoformat()
    try:
        with db() as c:
            my_tasks = c.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id=? AND work_date=?",
                (uid, today_s),
            ).fetchone()[0]
            my_tickets_open = c.execute(
                "SELECT COUNT(*) FROM tickets WHERE requester_id=? AND status NOT IN ('완료','반려')",
                (uid,),
            ).fetchone()[0]
            my_tickets_recv = c.execute(
                """SELECT COUNT(*) FROM tickets
                   WHERE (recipient_user_id=? OR (recipient_team_id=? AND recipient_user_id IS NULL))
                   AND status IN ('요청','접수')""",
                (uid, team_id or 0),
            ).fetchone()[0]
            unread_changes = c.execute(
                """SELECT COUNT(*) FROM change_reads
                   WHERE user_id=? AND ack_at IS NULL""",
                (uid,),
            ).fetchone()[0]
            try:
                my_issues = c.execute(
                    """SELECT COUNT(*) FROM issues
                       WHERE (owner_user_id=? OR owner_team_id=?)
                       AND status NOT IN ('해결','종결')""",
                    (uid, team_id or 0),
                ).fetchone()[0]
            except Exception:
                my_issues = 0
    except Exception as e:
        return {"type": "data", "title": "🗒 내 할 일", "text": f"조회 오류: {e}", "links": []}

    lines = [
        f"📝 오늘 일일업무 카드: {my_tasks}건",
        f"🎫 내가 요청한 티켓 (미완): {my_tickets_open}건",
        f"📥 내가 받은 티켓 (미처리): {my_tickets_recv}건",
        f"🔔 확인 안 한 변경: {unread_changes}건",
        f"🔥 내 담당 이슈 (미해결): {my_issues}건",
    ]
    return {
        "type": "data",
        "title": f"🗒 {u.get('name')}님 할 일 요약",
        "text": "\n".join(lines),
        "links": [
            _link("홈 (업무현황) →", "/home", "primary"),
            _link("일일업무 →", "/daily", "secondary"),
            _link("받은 티켓 →", "/tickets?scope=recv", "secondary"),
            _link("미확인 변경 →", "/changes?scope=impacted", "secondary"),
        ],
    }


def h_attendance_today(u, db):
    """오늘 출근 현황 — 하이웍스 API 연동 시 확장 (Phase 2)"""
    return {
        "type": "guide",
        "title": "👥 오늘 출근 현황",
        "text": "근태 조회는 하이웍스 인사관리 API 연동 후 활성화됩니다.\n(admin 설정에서 토큰 발급 후 입력)",
        "links": [
            _link("일일업무 피드 →", "/feed", "primary"),
            _link("(관리자) API 설정 →", "/admin/settings", "secondary"),
        ],
    }


def h_issues_recent(u, db):
    try:
        with db() as c:
            try:
                rows = c.execute(
                    """SELECT issue_no, title, severity, status, customer_name,
                              (SELECT name FROM teams WHERE id=i.owner_team_id) AS team_name
                       FROM issues i
                       WHERE status NOT IN ('해결','종결')
                       ORDER BY
                         CASE severity WHEN '치명' THEN 1 WHEN '심각' THEN 2 WHEN '중' THEN 3 ELSE 4 END,
                         created_at DESC
                       LIMIT 5"""
                ).fetchall()
                items = [dict(r) for r in rows]
            except Exception:
                items = []
    except Exception:
        items = []
    if not items:
        return {
            "type": "data",
            "title": "🔥 미해결 이슈",
            "text": "현재 미해결 이슈가 없습니다. 👏",
            "links": [_link("이슈 · AS DB →", "/issues", "primary")],
        }
    lines = [
        f"  • [{r['issue_no']}] {r['severity']} · {r['title']}"
        f" — {r.get('customer_name') or '-'} · 담당: {r.get('team_name') or '미지정'} ({r['status']})"
        for r in items
    ]
    return {
        "type": "data",
        "title": f"🔥 미해결 이슈 Top {len(items)}",
        "text": "\n".join(lines),
        "links": [_link("이슈 · AS DB →", "/issues?scope=open", "primary")],
    }


def h_changes_recent(u, db):
    try:
        with db() as c:
            rows = c.execute(
                """SELECT change_no, title, urgency, status, change_type, created_at
                   FROM changes
                   WHERE status IN ('공지중','작성중')
                   ORDER BY created_at DESC LIMIT 5"""
            ).fetchall()
            items = [dict(r) for r in rows]
    except Exception:
        items = []
    if not items:
        return {
            "type": "data",
            "title": "🔔 진행 중 변경",
            "text": "현재 공지 중인 변경이 없습니다.",
            "links": [_link("변경 Inform →", "/changes", "primary")],
        }
    lines = [
        f"  • [{r['change_no']}] {r['urgency']} · {r['change_type']} — {r['title']}"
        for r in items
    ]
    return {
        "type": "data",
        "title": f"🔔 최근 변경 {len(items)}건",
        "text": "\n".join(lines),
        "links": [_link("변경 Inform →", "/changes", "primary")],
    }


def h_progress_delayed(u, db):
    try:
        with db() as c:
            rows = c.execute(
                """SELECT p.mgmt_code, p.name, pp.phase_code, pp.status, pp.progress_pct
                   FROM project_phases pp JOIN projects p ON pp.project_id=p.id
                   WHERE pp.status='지연'
                   ORDER BY pp.updated_at DESC LIMIT 5"""
            ).fetchall()
            items = [dict(r) for r in rows]
    except Exception:
        items = []
    if not items:
        return {
            "type": "data",
            "title": "🚧 지연 공정",
            "text": "현재 지연된 공정이 없습니다. 👏",
            "links": [_link("진행률 대시보드 →", "/progress", "primary")],
        }
    from .database import PHASE_CODE_TO_LABEL
    lines = [
        f"  • [{r['mgmt_code']}] {r['name']} — {PHASE_CODE_TO_LABEL.get(r['phase_code'], r['phase_code'])} ({int(r.get('progress_pct') or 0)}%)"
        for r in items
    ]
    return {
        "type": "data",
        "title": f"🚧 지연 공정 {len(items)}건",
        "text": "\n".join(lines),
        "links": [_link("진행률 대시보드 →", "/progress", "primary")],
    }


def h_tickets_pending(u, db):
    uid = u.get("id") if u else None
    team_id = u.get("team_id") if u else None
    if not uid:
        return {"type": "guide", "title": "로그인 필요", "text": "로그인 후 다시 물어봐 주세요.", "links": []}
    try:
        with db() as c:
            my_sent = c.execute(
                "SELECT COUNT(*) FROM tickets WHERE requester_id=? AND status NOT IN ('완료','반려')",
                (uid,),
            ).fetchone()[0]
            recv = c.execute(
                """SELECT COUNT(*) FROM tickets
                   WHERE (recipient_user_id=? OR (recipient_team_id=? AND recipient_user_id IS NULL))
                   AND status IN ('요청','접수')""",
                (uid, team_id or 0),
            ).fetchone()[0]
    except Exception:
        my_sent, recv = 0, 0
    return {
        "type": "data",
        "title": "🎫 티켓 현황",
        "text": f"내가 요청한 것 (미완): {my_sent}건\n내가 받은 것 (미처리): {recv}건",
        "links": [
            _link("받은 티켓 →", "/tickets?scope=recv", "primary"),
            _link("보낸 티켓 →", "/tickets?scope=me", "secondary"),
            _link("티켓 등록 →", "/tickets/new", "secondary"),
        ],
    }


# ── 페이지 라우팅 (단순 링크) ──────────────────────────────
def _simple_route(title: str, desc: str, href: str, href_label: str):
    def handler(u, db):
        return {
            "type": "route",
            "title": title,
            "text": desc,
            "links": [_link(href_label, href, "primary")],
        }
    return handler


# ── 도움말 (모를 때 기본) ──────────────────────────────
def h_help(u, db):
    examples = [
        '"일정 입력 어디서해?"',
        '"이번달 매출 현황"',
        '"리니어가이드 재고"',
        '"내 할 일"',
        '"미해결 이슈"',
        '"확인 안 한 변경"',
        '"결재 올리기"',
        '"휴가 신청"',
        '"티켓 현황"',
        '"지연된 공정"',
    ]
    return {
        "type": "guide",
        "title": "🤖 안녕하세요, 빅터(Victor)입니다",
        "text": (
            "이렇게 물어봐 주세요:\n\n" +
            "\n".join(f"  • {e}" for e in examples) +
            "\n\n매출/자재/일정/이슈/변경/티켓/진행률/결재/메일 등을 도와드립니다."
        ),
        "links": [
            _link("홈 대시보드 →", "/home", "primary"),
            _link("전체 검색 →", "/search", "secondary"),
        ],
    }


# =====================================================
# 의도 레지스트리 (순서: 구체적인 것 먼저)
# =====================================================
INTENTS = [
    # 길 찾기 (외부 시스템)
    ("approval",      ["결재", "기안", "전자결재", "승인신청"], h_approval),
    ("vacation",      ["휴가", "연차", "반차", "월차"], h_vacation),
    ("mail",          ["메일", "이메일", "편지함"], h_mail),

    # 데이터 조회 — 구체적 키워드
    ("sales",         ["매출", "수주", "오더", "매출현황", "실적", "주문금액"], h_sales),
    ("inventory",     ["재고", "자재", "입고", "부품", "파트", "발주", "납품"], h_inventory),
    ("attendance",    ["출근", "근태", "휴가현황", "오늘출근", "누구출근"], h_attendance_today),
    ("issues",        ["이슈", "AS", "불량", "클레임", "결함", "미해결이슈", "심각"], h_issues_recent),
    ("changes",       ["변경", "ECN", "Inform", "공지", "미확인변경", "확인안한"], h_changes_recent),
    ("delayed",       ["지연", "딜레이", "늦어", "연체", "병목"], h_progress_delayed),
    ("tickets",       ["티켓", "요청", "의뢰"], h_tickets_pending),

    # 개인화
    ("my_todo",       ["내할일", "내업무", "오늘할일", "todo", "할일"], h_my_todo),

    # 길 찾기 (내부 페이지)
    ("schedule",      ["일정", "캘린더", "달력", "스케줄", "일정입력"],
                      h_schedule_input),
    ("progress",      ["진행률", "진척", "공정", "매트릭스", "진행현황"],
                      _simple_route("📊 진행률 대시보드",
                                    "프로젝트별 12공정 진척을 매트릭스로 봅니다.",
                                    "/progress", "진행률 대시보드 →")),
    ("board_company", ["전사게시판", "공지사항", "전체공지"],
                      _simple_route("📢 전사 게시판", "회사 공지를 봅니다.",
                                    "/board/company", "전사 게시판 →")),
    ("board_team",    ["부서게시판", "팀게시판"],
                      _simple_route("📢 부서 게시판", "우리 부서 게시판을 봅니다.",
                                    "/board/team", "부서 게시판 →")),
    ("daily",         ["일일업무", "일일", "업무일지", "일지"],
                      _simple_route("📝 일일업무",
                                    "오늘 할 일 카드를 관리합니다.",
                                    "/daily", "일일업무 →")),
    ("weekly",        ["주간", "주간보고", "위클리"],
                      _simple_route("📅 주간 뷰", "주간 업무 뷰로 이동합니다.",
                                    "/weekly", "주간 뷰 →")),
    ("notifications", ["알림", "알람", "notification", "공지알림"],
                      _simple_route("🔔 알림", "내 알림 목록으로 이동합니다.",
                                    "/notifications", "알림 보기 →")),
    ("dashboard",     ["대시보드", "전사", "경영", "KPI"],
                      _simple_route("📈 전사 대시보드",
                                    "경영진용 전사 KPI 대시보드로 이동합니다.",
                                    "/dashboard", "대시보드 →")),
    ("cockpit",       ["코크핏", "cockpit", "현황실"],
                      _simple_route("🎯 코크핏",
                                    "팀장·경영진용 코크핏 뷰로 이동합니다.",
                                    "/cockpit", "코크핏 →")),
    ("bottleneck",    ["병목", "bottleneck", "막힘"],
                      _simple_route("🚨 병목 탐지",
                                    "현재 병목 지점을 분석합니다.",
                                    "/bottlenecks", "병목 탐지 →")),
    ("logistics",     ["물류", "매출흐름", "공급"],
                      _simple_route("📦 매출흐름·물류", "물류 모듈로 이동합니다.",
                                    "/logistics", "물류 시스템 ↗")),
    ("search",        ["검색", "찾기", "find", "search"],
                      _simple_route("🔍 전체 검색",
                                    "업무·코멘트·회고 통합 검색으로 이동합니다.",
                                    "/search", "전체 검색 →")),
    ("profile",       ["내정보", "프로필", "비밀번호", "계정"],
                      _simple_route("👤 내 계정",
                                    "프로필·비밀번호 관리로 이동합니다.",
                                    "/profile", "내 계정 →")),
    ("admin",         ["관리자", "admin", "관리페이지"],
                      _simple_route("⚙️ 관리자",
                                    "관리자 페이지로 이동합니다.",
                                    "/admin", "관리자 →")),
    ("settings",      ["설정", "시스템설정", "API설정", "토큰"],
                      _simple_route("⚙️ 시스템 설정",
                                    "하이웍스 URL/토큰 등을 관리합니다.",
                                    "/admin/settings", "시스템 설정 →")),

    # 도움말 (가장 마지막)
    ("help",          ["도움말", "도움", "help", "뭐있어", "뭐가능", "어떻게", "사용법"], h_help),
]


# =====================================================
# 메인 진입점
# =====================================================
def ask(query: str, user: dict | None, db_session_func) -> dict:
    """사용자 질문을 받아 응답 dict를 반환.

    Args:
        query: 사용자 자연어 질문
        user: get_user(req) 결과 dict (없으면 None)
        db_session_func: database.db_session 컨텍스트 매니저 함수

    Returns:
        응답 dict — 최소 {type, title, text, links, intent}
    """
    if not query or not query.strip():
        return h_help(user, db_session_func) | {"intent": "help", "query": ""}

    q = query.strip()
    q_norm = _norm(q)

    # 1) 키워드 매칭 (순서대로)
    for intent_id, kws, handler in INTENTS:
        if _match_any(q_norm, kws):
            try:
                # inventory는 query 문자열도 전달 (검색어 추출용)
                if intent_id == "inventory":
                    result = handler(user, db_session_func, q)
                else:
                    result = handler(user, db_session_func)
                result["intent"] = intent_id
                result["query"] = q
                return result
            except Exception as e:
                return {
                    "type": "guide",
                    "title": "⚠️ 처리 중 오류",
                    "text": f"질문을 처리하다 오류가 발생했습니다: {e}",
                    "links": [_link("홈 →", "/home", "primary")],
                    "intent": intent_id,
                    "query": q,
                }

    # 2) 매칭 실패 → 도움말 안내
    result = h_help(user, db_session_func)
    result["intent"] = "unmatched"
    result["query"] = q
    result["title"] = "🤔 아직 그 질문은 이해하지 못했어요"
    result["text"] = (
        f'"{q}"를 이해하지 못했습니다.\n\n'
        "이렇게 물어봐 주세요:\n\n" +
        "\n".join(f"  • 일정 입력 어디서해?\n  • 이번달 매출\n  • 리니어가이드 재고\n  • 내 할 일"[:200].split("\n"))
    )
    return result
