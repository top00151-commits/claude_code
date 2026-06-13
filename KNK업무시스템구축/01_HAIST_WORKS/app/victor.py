"""
HAIST Victor — 사내 AI 컨시어지 (Phase 1: 키워드 라우팅)
=========================================================

사용자 자연어 질문을 받아:
  1) 페이지 라우팅 ("결재 어디서 해?" → 외부 그룹웨어 링크)
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
  "결재 올려줘"            → 외부 그룹웨어 전자결재 링크
  "휴가 신청"              → 외부 그룹웨어 결재
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
    url = (get_setting("groupware_approval_url", "") or get_setting("hiworks_approval_url", "") or "").strip()
    return {
        "type": "external",
        "title": "📋 전자결재 (그룹웨어)",
        "text": "결재는 외부 그룹웨어에서 진행합니다. 결재 필요 변경/티켓은 URL을 첨부하면 영향 부서가 자동 확인합니다.",
        "links": [
            _link("전자결재 열기 ↗", url, "primary"),
            _link("변경 등록 (결재 URL 첨부 가능)", "/changes/new", "secondary"),
            _link("티켓 등록 (결재 URL 첨부 가능)", "/tickets/new", "secondary"),
        ],
    }


def h_mail(u, db):
    from .database import get_setting
    url = (get_setting("groupware_mail_url", "") or get_setting("hiworks_mail_url", "") or "").strip()
    return {
        "type": "external",
        "title": "📧 회사 메일",
        "text": "메일은 외부 그룹웨어에서 사용합니다.",
        "links": [_link("메일 열기 ↗", url, "primary")],
    }


def h_vacation(u, db):
    from .database import get_setting
    url = (get_setting("groupware_approval_url", "") or get_setting("hiworks_approval_url", "") or "").strip()
    return {
        "type": "external",
        "title": "🏖 휴가 신청",
        "text": "휴가는 외부 그룹웨어 전자결재에서 신청합니다.",
        "links": [_link("전자결재 열기 ↗", url, "primary")],
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
            _link("📈 매출·영업 센터 →", "/sales", "primary"),
            _link("전사 대시보드", "/dashboard", "secondary"),
            _link("프로젝트 목록", "/projects", "secondary"),
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
            try:
                if search_term:
                    like = f"%{search_term}%"
                    rows = c.execute(
                        """SELECT part_no, part_name, spec, stock_qty, safety_stock, unit, id
                           FROM parts
                           WHERE is_active=1 AND (part_name LIKE ? OR part_no LIKE ? OR spec LIKE ?)
                           ORDER BY part_name LIMIT 10""",
                        (like, like, like),
                    ).fetchall()
                else:
                    rows = c.execute(
                        """SELECT part_no, part_name, spec, stock_qty, safety_stock, unit, id
                           FROM parts WHERE is_active=1
                           ORDER BY (stock_qty < COALESCE(safety_stock,0)) DESC, part_name
                           LIMIT 10"""
                    ).fetchall()
                items = [dict(r) for r in rows]
                total_cnt = c.execute(
                    "SELECT COUNT(*) FROM parts WHERE is_active=1"
                ).fetchone()[0]
            except Exception as e:
                print(f"[VICTOR inventory] {e}")
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
        lines.append(f"  • [{r.get('part_no','')}] {r.get('part_name','')} — {stock}{r.get('unit') or ''}{mark}")
    label = f"'{search_term}' 검색 결과" if search_term else "전체"
    text = f"{label} {len(items)}건:\n" + "\n".join(lines)
    links = [
        _link("부품 목록 →", "/parts", "primary"),
        _link("수불부 →", "/stock/movements", "secondary"),
        _link("출고 등록 →", "/stock/issue", "secondary"),
    ]
    # 단일 품목이면 해당 부품 이력 링크 추가
    if len(items) == 1 and items[0].get("id"):
        links.insert(1, _link(f"{items[0]['part_name']} 이력 →",
                              f"/stock/movements?part_id={items[0]['id']}", "primary"))
    return {
        "type": "data",
        "title": "📦 자재 재고",
        "text": text,
        "links": links,
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
    """오늘 출근 현황 — 외부 그룹웨어 API 연동 시 확장 (Phase 2)"""
    return {
        "type": "guide",
        "title": "👥 오늘 출근 현황",
        "text": "근태 조회는 외부 그룹웨어 인사관리 API 연동 후 활성화됩니다.\n(admin 설정에서 토큰 발급 후 입력)",
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


# =====================================================
# 가이드 모드 — "어떻게 해?" 류 질문에 단계별 안내 + 자동 이동
# =====================================================
def _guide_step(title: str, intro: str, steps: list, go_url: str,
                go_label: str = "바로 이동 →", auto: bool = True,
                notes: str = "", extra_links: list = None) -> dict:
    """가이드 단계 응답 빌더."""
    numbered = []
    for i, s in enumerate(steps, 1):
        if s.lstrip().startswith(("①","②","③","④","⑤","⑥","⑦","⑧","⑨","1.","2.","3.")):
            numbered.append(s)
        else:
            numbered.append(f"{i}. {s}")
    links = [{"label": go_label, "href": go_url, "style": "primary"}]
    if extra_links:
        links.extend(extra_links)
    return {
        "type": "guide_step",
        "title": title,
        "text": (intro + "\n\n" if intro else "") + "\n".join(numbered) + (f"\n\n{notes}" if notes else ""),
        "links": links,
        "auto_redirect": go_url if auto else None,
        "step_count": len(steps),
    }


def h_how_to_sales(u, db):
    return _guide_step(
        title="💡 매출·수주 입력 방법",
        intro="매출·수주는 **📈 매출·영업 센터** 또는 관리자 페이지에서 **프로젝트 등록**으로 입력합니다.",
        steps=[
            "매출·영업 센터 (/sales) 또는 관리자 페이지로 이동",
            "'신규 프로젝트' 클릭 (또는 기존 프로젝트 수정)",
            "필수 입력: 관리코드·고객사·수주금액·수주일·사업부(T/M)",
            "저장 → 관리코드 8자리 자동 채번, 매출 KPI에 즉시 반영",
        ],
        go_url="/sales",
        go_label="📈 매출·영업 센터 →",
        notes="💡 대량 등록은 `관리코드발행목록.xls` 엑셀 업로드 (관리자 홈).",
        extra_links=[
            {"label": "관리자 페이지", "href": "/admin", "style": "secondary"},
            {"label": "전사 대시보드", "href": "/dashboard", "style": "secondary"},
        ],
    )


def h_how_to_change(u, db):
    return _guide_step(
        title="💡 설계 변경 등록 방법",
        intro="변경 Inform은 영향 부서에 **자동 알림**이 갑니다.",
        steps=[
            "변경 등록 페이지 열기",
            "Step 1: 변경 종류 선택 (기구설계/전장/SW/BOM/도면/Concept/사양)",
            "Step 2: 사업부(T/M) · 대상 프로젝트 선택 → 영향 부서 자동 판별",
            "Step 3: 제목·설명·전/후 값·출처(CAD) 입력",
            "Step 4: '📢 공지하기' 클릭 → 영향 부서원 전원 자동 통지",
        ],
        go_url="/changes/new",
        go_label="변경 등록 화면으로 →",
        notes="⚠️ 결재 필요한 변경은 외부 그룹웨어에서 결재 후 URL 첨부.",
        extra_links=[{"label": "변경 목록", "href": "/changes", "style": "secondary"}],
    )


def h_how_to_ticket(u, db):
    return _guide_step(
        title="💡 요청 티켓 등록 방법",
        intro="메신저·구두 요청 대신 티켓 → **자동 라우팅 + 이력 추적**.",
        steps=[
            "티켓 등록 페이지 열기",
            "카테고리 선택 (자재요청/긴급가공/MODIFY/검수/AS/기타) → 담당 팀 자동 배정",
            "제목·상세 내용 입력 + 긴급도 선택",
            "희망 완료일·예상 공수 입력 (선택)",
            "등록 → 수신 부서 즉시 알림, 상태 변경 시 요청자에게 피드백",
        ],
        go_url="/tickets/new",
        go_label="티켓 등록 화면으로 →",
        extra_links=[
            {"label": "받은 티켓", "href": "/tickets?scope=recv", "style": "secondary"},
            {"label": "보낸 티켓", "href": "/tickets?scope=me", "style": "secondary"},
        ],
    )


def h_how_to_issue(u, db):
    return _guide_step(
        title="💡 이슈·AS 등록 방법",
        intro="고객 이슈/AS는 **원인→조치→재발방지** 3단계로 자산화.",
        steps=[
            "이슈 등록 페이지 열기",
            "심각도·종류 선택 (치명/심각/중/경 · AS/품질/설계결함/SW버그 등)",
            "고객사·프로젝트 연결 (사업부 자동 배정)",
            "증상 설명 입력 → 접수 등록",
            "상세 화면에서 3단계 채우기: ① 원인분석 → ② 조치 → ③ 재발방지",
        ],
        go_url="/issues/new",
        go_label="이슈 등록 화면으로 →",
        notes="🚨 치명/심각 선택 시 담당 부서에 즉시 푸시.",
        extra_links=[{"label": "이슈 목록", "href": "/issues", "style": "secondary"}],
    )


def h_how_to_stock_out(u, db):
    return _guide_step(
        title="💡 자재 출고 방법",
        intro="출고는 **FIFO 원가 자동 계산** + 재고 자동 감소.",
        steps=[
            "출고 등록 화면 열기 (또는 부품 목록에서 '📤 출고' 버튼)",
            "부품 선택 → 현재고/안전재고 자동 표시",
            "출고 수량 입력",
            "프로젝트·고객사 지정 (감사 추적용)",
            "사유·위치·비고 입력 후 등록 → stock_qty 자동 감소, 수불부 이력",
        ],
        go_url="/stock/issue",
        go_label="출고 등록 화면으로 →",
        notes="⚠️ 안전재고 미달 시 구매팀에 자동 티켓.",
        extra_links=[
            {"label": "부품 목록", "href": "/parts", "style": "secondary"},
            {"label": "수불부(이력)", "href": "/stock/movements", "style": "secondary"},
        ],
    )


def h_how_to_stock_in(u, db):
    return _guide_step(
        title="💡 자재 입고 방법",
        intro="입고는 **발주서 기반**으로만 가능합니다 (감사 추적).",
        steps=[
            "발주 목록 열기",
            "해당 발주서 클릭 → '📥 입고 처리' 버튼",
            "라인별 입고 수량 + Lot 번호 입력 (이슈 역추적용)",
            "등록 → 재고 자동 증가, PO 상태 자동 전이",
        ],
        go_url="/po",
        go_label="발주 목록으로 →",
        notes="⭐ Lot 번호는 불량 역추적의 핵심입니다.",
        extra_links=[{"label": "수불부", "href": "/stock/movements", "style": "secondary"}],
    )


def h_how_to_task(u, db):
    return _guide_step(
        title="💡 일일업무 등록 방법",
        intro="업무 카드는 **오늘 할 일 + 진행 상태**를 5초 안에 기록.",
        steps=[
            "홈 또는 일일업무 페이지 열기",
            "상단 빠른 입력창에 업무 제목 입력 후 Enter",
            "필요 시 카드 클릭 → 공수·카테고리·프로젝트·고객사 추가 입력",
            "상태 4버튼으로 진행중/완료/지연/대기 1-클릭 지정",
            "부서 피드 + 팀장 뷰에 자동 반영",
        ],
        go_url="/daily",
        go_label="일일업무 화면으로 →",
        extra_links=[{"label": "홈(탭별 요약)", "href": "/home", "style": "secondary"}],
    )


def h_how_to_schedule(u, db):
    return _guide_step(
        title="💡 일정 입력 방법",
        intro="일정은 3가지 유형으로 입력할 수 있습니다.",
        steps=[
            "오늘 할 일 = 일일업무 카드 (빠른 입력)",
            "회의·출장·미팅 = 캘린더 (날짜 클릭 → 이벤트 추가)",
            "부서 공유 = 부서 게시판",
        ],
        go_url="/daily",
        go_label="일일업무로 이동 →",
        auto=False,
        extra_links=[
            {"label": "📅 캘린더", "href": "/calendar", "style": "secondary"},
            {"label": "부서 게시판", "href": "/board/team", "style": "secondary"},
        ],
    )


def h_how_to_approval(u, db):
    from .database import get_setting
    url = (get_setting("groupware_approval_url", "") or get_setting("hiworks_approval_url", "") or "").strip()
    return _guide_step(
        title="💡 전자결재 진행 방법",
        intro="결재는 **외부 그룹웨어**에서 진행 (HAIST WORKS에는 결재 기능 없음).",
        steps=[
            "전자결재 페이지 열기",
            "문서 작성 (기안)",
            "결재선 지정 + 제출",
            "승인 후 결재 문서 URL 복사",
            "관련 HAIST 변경/티켓에 결재 URL 첨부",
        ],
        go_url=url,
        go_label="전자결재 열기 ↗",
        auto=False,
        notes="📌 결재 URL 첨부는 변경/티켓 등록 4단계에서 가능.",
        extra_links=[
            {"label": "변경 등록", "href": "/changes/new", "style": "secondary"},
            {"label": "티켓 등록", "href": "/tickets/new", "style": "secondary"},
        ],
    )


def h_how_to_vacation(u, db):
    from .database import get_setting
    url = (get_setting("groupware_approval_url", "") or get_setting("hiworks_approval_url", "") or "").strip()
    return _guide_step(
        title="💡 휴가 신청 방법",
        intro="휴가는 **외부 그룹웨어 전자결재**에서 신청합니다.",
        steps=[
            "외부 그룹웨어 로그인",
            "전자결재 → 휴가신청서 양식 선택",
            "사용 일자·유형(연차/반차/월차) 선택",
            "결재선 지정 → 제출",
        ],
        go_url=url,
        go_label="그룹웨어 열기 ↗",
        auto=False,
    )


def h_how_to_stock_adjust(u, db):
    return _guide_step(
        title="💡 재고 실사 조정 방법",
        intro="실사 결과와 시스템 재고 차이를 조정 (감사 추적 필수).",
        steps=[
            "실사 조정 화면 열기",
            "부품 선택",
            "조정 수량 입력 (+ 증가 / - 감소)",
            "사유 입력 (필수 — 실사 차이/파손/분실)",
            "등록 → 수불부에 ADJUST 이력",
        ],
        go_url="/stock/adjust",
        go_label="실사 조정 화면으로 →",
        notes="⚠️ 사유가 감사 핵심. 명확히 기록.",
    )


def h_how_to_supplier(u, db):
    return _guide_step(
        title="💡 협력사 등록 방법",
        intro="협력사를 먼저 등록해야 발주서에서 선택 가능.",
        steps=[
            "협력사 목록 열기",
            "'신규 등록' 클릭",
            "필수: 회사명·담당자·연락처·통화(KRW/USD/VND)·결제조건",
            "저장 → 발주서에서 선택 가능",
            "수정 화면에서 **평균 리드타임 자동 통계** 확인 가능",
        ],
        go_url="/suppliers",
        go_label="협력사 목록으로 →",
    )


# ── 도움말 (모를 때 기본) ──────────────────────────────
def h_help(u, db):
    examples = [
        '💡 "매출입력 어떻게 해?" (가이드 + 자동 이동)',
        '💡 "변경 등록 방법" / "티켓 요청 어떻게"',
        '💡 "출고 어떻게" / "입고 방법"',
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
# "어떻게" 류 질문은 가이드 의도와 복합 매칭 필요 (아래 ask()에서 처리)
# =====================================================

# "어떻게 해?" 복합 키워드 — 아래 단어가 query에 있으면 how_to_* 로 라우팅
HOWTO_TRIGGERS = ["어떻게", "어떡", "어디서", "어디에서", "방법", "하려면", "해야", "써야", "쓰려면", "시작"]

# "어떻게" + 주제 → how_to 의도 매핑 (주제별 키워드)
HOWTO_MAP = [
    # (의도 id, 주제 키워드 리스트, 핸들러)
    ("how_sales",     ["매출", "수주", "오더", "주문금액"],        h_how_to_sales),
    ("how_change",    ["변경", "ECN", "ECO", "설계변경", "Inform"], h_how_to_change),
    ("how_ticket",    ["티켓", "요청", "의뢰"],                     h_how_to_ticket),
    ("how_issue",     ["이슈", "AS", "불량", "클레임", "결함"],     h_how_to_issue),
    ("how_out",       ["출고", "자재출고", "현장출고"],             h_how_to_stock_out),
    ("how_in",        ["입고", "입고처리", "받았"],                 h_how_to_stock_in),
    ("how_adjust",    ["실사", "실사조정", "재고조정"],             h_how_to_stock_adjust),
    ("how_supplier",  ["협력사", "거래처", "vendor"],               h_how_to_supplier),
    ("how_schedule",  ["일정", "캘린더", "달력", "스케줄"],          h_how_to_schedule),
    ("how_task",      ["일일업무", "업무", "할일", "일지", "카드"], h_how_to_task),
    ("how_vacation",  ["휴가", "연차", "반차"],                     h_how_to_vacation),
    ("how_approval",  ["결재", "기안", "승인"],                     h_how_to_approval),
]


INTENTS = [
    # 길 찾기 (외부 시스템)
    ("approval",      ["결재", "기안", "전자결재", "승인신청"], h_approval),
    ("vacation",      ["휴가", "연차", "반차", "월차"], h_vacation),
    ("mail",          ["메일", "이메일", "편지함"], h_mail),

    # 데이터 조회 — 구체적 키워드
    # 도메인 홈 (구체적 키워드 먼저)
    ("sales_home",    ["매출센터", "영업센터", "매출영업", "매출홈", "영업홈", "수주현황"],
                      _simple_route("📈 매출·영업 센터",
                                    "프로젝트·수주·관리코드·고객사 통합.",
                                    "/sales", "매출·영업 센터 →")),
    ("logistics_home",["자재구매", "구매센터", "자재센터", "구매자재"],
                      _simple_route("📦 자재·구매 센터",
                                    "부품·협력사·발주·입출고·수불부·환율.",
                                    "/logistics", "자재·구매 센터 →")),
    ("sales",         ["매출", "수주", "오더", "매출현황", "실적", "주문금액"], h_sales),
    ("inventory",     ["재고", "자재", "부품", "파트", "납품"], h_inventory),
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
    ("logistics",     ["물류", "공급"],
                      _simple_route("📦 자재·구매 센터",
                                    "부품·협력사·발주·입출고·수불부·환율.",
                                    "/logistics", "자재·구매 센터 →")),
    ("stock_mv",      ["수불부", "입출고", "재고이력", "원장", "재고변동"],
                      _simple_route("📒 수불부 (입출고 원장)",
                                    "모든 재고 변동 이력을 봅니다.",
                                    "/stock/movements", "수불부 →")),
    ("stock_in",      ["입고", "입고처리", "받았"],
                      _simple_route("📥 입고 처리",
                                    "발주서에서 입고 처리를 진행하세요.\n(발주 상세 → '입고 처리' 버튼)",
                                    "/po", "발주 목록 →")),
    ("stock_out",     ["출고", "출고등록", "자재출고", "현장출고"],
                      _simple_route("📤 출고 등록",
                                    "프로젝트/고객사에 자재를 출고합니다.",
                                    "/stock/issue", "출고 등록 →")),
    ("stock_adjust",  ["실사", "실사조정", "재고조정"],
                      _simple_route("⚖️ 재고 실사 조정",
                                    "실사 결과와 시스템 재고 차이를 조정합니다.",
                                    "/stock/adjust", "실사 조정 →")),
    ("rates",         ["환율", "USD", "VND", "exchange", "FX"],
                      _simple_route("💱 환율 관리",
                                    "KRW 기준 환율을 등록·조회합니다. 베트남 법인 VND 처리 필수.",
                                    "/rates", "환율 관리 →")),
    ("po_list",       ["발주", "발주서", "PO", "주문서"],
                      _simple_route("📋 발주 관리",
                                    "발주서 목록을 봅니다. 발주 상세에서 '입고 처리' 가능.",
                                    "/po", "발주 목록 →")),
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
                                    "외부 그룹웨어 URL/토큰 등을 관리합니다.",
                                    "/admin/settings", "시스템 설정 →")),

    # 도움말 (가장 마지막)
    ("help",          ["도움말", "도움", "help", "뭐있어", "뭐가능", "어떻게", "사용법"], h_help),
]


# =====================================================
# v5H226z410 (대표 지시) — 빅터 AI 메뉴 라우팅 (업무 순서 인지)
# 키워드 사전으로 못 잡은 자연어를 AI가 '메뉴 카탈로그'에서 직접 고르고,
# 일 순서상 '먼저 해야 할 단계'를 우선 추천한다.
#   예) "검사기 등록 어디서해?" → (검사기는 제작요청부터) → 제작요청 등록 추천 + 이유.
# =====================================================

# KNK 업무 순서(도메인 지식) — AI가 '먼저 할 일'을 알도록 주입하는 핵심 맥락.
KNK_WORK_SEQUENCE = """[KNK 업무 순서 — '먼저 할 일'을 추천할 때 반드시 참고]
· KNK는 검사기(사업부 T)·자동화 설비(사업부 M)를 제작하는 회사다. "검사기 / 자동화 / 설비 / 장비 / 호기" = 만들 제품.
· 새 설비를 시작·등록하는 순서:
  ① 제작요청 등록 (/projects/quick) ← 가장 먼저! 여기서 관리코드 자동 발번 + 전부서 통보가 시작된다.
     "검사기 등록·제작·주문", "자동화 등록", "새 설비 시작", "제작요청"은 모두 이 첫 단계로 보낸다.
  ② 수주 항목·호기 입력(프로젝트 상세) → ③ 작업일정표 진행관리 (/sales/schedule) → 출하·수금 (/sales/shipments-receipts).
· 소모품은 별도 흐름: 소모품 발주 등록 (/consumables/new).
· 견적 = 견적서 (/sales/quotations) · 부품/자재 = 부품 등록 (/parts/new) · 발주 = 발주 작성 (/po/new).
· '어디서 등록/시작하냐'는 질문엔 위 순서상 '첫 단계'를 첫 후보로 추천하고, 이유를 한 줄 곁들인다."""


def ai_pick_menu(user, query: str):
    """v5H226z410: 자연어 → 카탈로그에서 AI가 최적 메뉴 선택 + 업무순서 추천.
    반환: {ok, ai_route, msg(이유), candidates:[{code,label,path,tip}]} | None(AI 비활성·실패·무매칭).
    데이터 안전: 메뉴 카탈로그(공개 메뉴 구조)만 보냄 — 민감 DB 미전송."""
    try:
        from . import ai_client
        from . import menu_catalog as _menu
    except Exception:
        return None
    try:
        if not ai_client.ai_available():
            return None
    except Exception:
        return None
    try:
        menus = _menu.all_menus()
        catalog = "\n".join(
            f"{m['code']} | {m['label']} | {m['path']} | {m['tip']}" for m in menus
        )
    except Exception:
        return None
    system = (
        "당신은 ㈜케이엔케이(KNK) 'HAIST WORKS' 업무 플랫폼의 메뉴 안내 AI '빅터'입니다.\n"
        "사용자의 자연어 요청을 읽고, 아래 [메뉴 카탈로그] 중에서 가장 알맞은 화면을 1~3개 고르세요.\n\n"
        + KNK_WORK_SEQUENCE + "\n\n"
        "[메뉴 카탈로그] (code | 이름 | 경로 | 설명)\n" + catalog + "\n\n"
        "규칙:\n"
        "1) 반드시 위 카탈로그에 실제로 있는 code/path 만 사용한다(없는 경로를 지어내지 말 것).\n"
        "2) '등록·시작·어디서' 류 질문은 업무 순서상 '먼저 할 일'을 첫 후보로 둔다.\n"
        "3) 정말 맞는 메뉴가 없으면 picks 를 빈 배열([])로 둔다.\n"
        "4) 오직 아래 형식의 JSON 한 개만 출력한다(앞뒤 설명·코드블록 금지):\n"
        '{"reason":"한국어 한두 줄 이유","picks":[{"code":"M-..","path":"/.."}]}'
    )
    try:
        ok, ans = ai_client.ai_chat(query, system=system, max_tokens=400, temperature=0.1)
    except Exception:
        return None
    if not ok or not ans or not ans.strip():
        return None
    # JSON 파싱 (코드펜스·잡텍스트 관용)
    import json
    txt = ans.strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", txt).strip()
    mobj = re.search(r"\{.*\}", txt, re.S)
    if not mobj:
        return None
    try:
        data = json.loads(mobj.group(0))
    except Exception:
        return None
    reason = (data.get("reason") or "").strip()
    picks = data.get("picks") or []
    if not isinstance(picks, list):
        return None
    cands: list[dict] = []
    seen: set[str] = set()
    for p in picks[:3]:
        if not isinstance(p, dict):
            continue
        path = (p.get("path") or "").strip()
        code = (p.get("code") or "").strip().upper()
        mc = _menu.by_code(code) if code else None
        if not mc and path:
            mc = _menu.by_path(path.split("?")[0])
        if not mc or mc["code"] in seen:
            continue
        seen.add(mc["code"])
        # AI가 ?biz_div=M 같은 유효 쿼리를 준 경우 그 경로를 살림(카탈로그 경로의 확장일 때만).
        use_path = path if (path and path.split("?")[0] == mc["path"]) else mc["path"]
        cands.append({"code": mc["code"], "label": mc["label"], "path": use_path, "tip": mc["tip"]})
    if not cands:
        return None
    return {
        "ok": True, "ai_route": True,
        "msg": reason or "요청에 맞는 메뉴를 찾았어요.",
        "candidates": cands,
    }


# =====================================================
# 메인 진입점
# =====================================================
def h_ai_assist(user, db_session_func, query: str):
    """v5H226z126 (2026-05-31) — 빅터 AI(LLM) 폴백, Phase 1.
    규칙으로 못 푼 질문을 실제 AI로 응답. **읽기·안내·작성 보조만**(실행 없음).
    데이터 안전: 민감 DB를 통째로 보내지 않음 — 질문 + 사용자 이름/역할 + 기능 목록만 전송.
    AI 비활성(키 미설정) 시 None 반환 → 호출부가 기존 도움말로 폴백."""
    try:
        from . import ai_client
    except Exception:
        return None
    try:
        if not ai_client.ai_available():
            return None
    except Exception:
        return None
    uname = (user.get("name") if isinstance(user, dict) else None) or "사용자"
    urole = (user.get("role") if isinstance(user, dict) else None) or "member"
    system = (
        "당신은 ㈜케이엔케이(KNK)의 사내 통합 업무 플랫폼 'HAIST WORKS'의 AI 비서 '빅터'입니다. "
        "한국어로 친절하고 간결하게 답합니다.\n"
        "다룰 수 있는 영역: 매출·영업(견적/수주/프로젝트/고객사), 자재·구매·재고, "
        "품질·이슈·변경관리, 일일업무·할일·일정·전자결재·휴가, 연락처(주소록), 메일.\n"
        "규칙:\n"
        "1) 실제 회사 수치(매출액·재고수량 등)는 추측하지 말 것. 필요하면 '어느 메뉴에서 볼 수 있는지' 안내한다.\n"
        "2) 모르면 모른다고 솔직히 말한다.\n"
        "3) 비밀번호·개인정보를 묻거나 만들어내지 않는다.\n"
        "4) 등록·발송 같은 실제 작업은 직접 수행하지 말고 '하는 방법'을 단계로 안내한다(현재 읽기·안내·초안 단계).\n"
        "5) 답변은 핵심 위주 8줄 이내. 요청 시 메일·보고 초안을 작성해준다.\n"
        f"현재 사용자: {uname} ({urole})."
    )
    try:
        ok, ans = ai_client.ai_chat(query, system=system, max_tokens=700, temperature=0.4)
    except Exception:
        return None
    if not ok or not ans or not ans.strip():
        return None
    return {
        "type": "ai",
        "title": "🤖 빅터 AI",
        "text": ans.strip(),
        "links": [_link("홈 →", "/home", "primary")],
        "intent": "ai",
        "query": query,
        "ai": True,
    }


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

    # 0) "어떻게/방법/어디서" 트리거 감지 → how_to 가이드 우선 매칭
    is_howto = _match_any(q_norm, HOWTO_TRIGGERS)
    if is_howto:
        for intent_id, topic_kws, handler in HOWTO_MAP:
            if _match_any(q_norm, topic_kws):
                try:
                    result = handler(user, db_session_func)
                    result["intent"] = intent_id
                    result["query"] = q
                    return result
                except Exception as e:
                    return {
                        "type": "guide",
                        "title": "⚠️ 처리 중 오류",
                        "text": f"가이드 생성 중 오류: {e}",
                        "links": [_link("홈 →", "/home", "primary")],
                        "intent": intent_id, "query": q,
                    }

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

    # 2) 매칭 실패 → 빅터 AI(LLM) 폴백 시도 (Phase 1: 읽기·안내·작성 보조)
    try:
        ai_res = h_ai_assist(user, db_session_func, q)
        if ai_res:
            return ai_res
    except Exception:
        pass  # AI 실패해도 아래 도움말로 안전 폴백

    # 3) AI 비활성/실패 → 기존 도움말 안내
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
