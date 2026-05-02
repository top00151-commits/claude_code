"""
KNK 일일업무일지 v2 - Phase 1 MVP
Task Card 기반 일일업무 + 팀장 뷰 + 경영진 대시보드 + 개인 히스토리
"""
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os, io, calendar, tempfile
from datetime import datetime, timedelta, date
from .i18n import LANGS, t as i18n_t, get_all_translations
from . import menu_catalog as _menu  # Phase 1 (2026-04-29): M-코드 카탈로그
from .database import (db_session, init_db, seed_all, seed_sample_tasks, hash_pw,
                        parse_mgmt_xls, parse_mgmt_csv, import_mgmt_rows,
                        regenerate_user_passwords, build_password_csv,
                        add_comment, get_task_comments, delete_comment,
                        get_notifications, count_unread, mark_notification_read,
                        mark_all_read, notify_user,
                        log_activity, log_activity_standalone, get_activities,
                        add_reaction, get_reactions, get_reactions_bulk, get_meta_bulk,
                        notify_status_change, get_user_search,
                        upsert_retro, get_retro, search_all, detect_bottlenecks,
                        delegate_task, get_delegations, resolve_delegation,
                        get_setting, get_settings_all, set_setting,
                        global_search, GLOBAL_SEARCH_CATEGORIES,
                        search_orders, search_customers, search_parts,
                        search_issues, search_tickets, search_users,
                        search_boards, search_exports, search_audits,
                        ceo_dashboard_kpis)

# ═══════════════════════════════════════════════════════════════════════════════
#  HAIST WORKS — main.py 목차 (TABLE OF CONTENTS)
#  v1.0 (2026-04-29 대표 결재 옵션 A — 코드 정리 Phase 1)
# ═══════════════════════════════════════════════════════════════════════════════
#
#  PART I. 기반 (Core)
#    §1.  IMPORTS                                              L 1
#    §2.  APP 초기화                                            L 32
#    §3.  STARTUP + 일일 미작성자 알림 스케줄러                  L 40
#    §4.  Phase 1 — 빅터 자연어 라우팅 + 메뉴 도움말 API          L 220
#    §5.  HELPERS (ctx, get_user, role_home...)                 L 310
#    §6.  Phase 1 — 메뉴 식별번호 헬퍼                           L 395
#
#  PART II. 인증·진입점
#    §7.  AUTH (login/logout)                                  L 624
#    §8.  ROOT (/)                                             L 658
#
#  PART III. 일상 업무 (전 직원)
#    §9.  HOME — 직관적 단일 페이지                              L 669
#    §10. DAILY — 일일 업무카드                                 L 904
#    §11. SUMMARY — 통합 요약                                   L 1137
#    §12. HISTORY — 개인 히스토리                                L 1851
#    §13. CALENDAR — 월간 뷰                                    L 2899
#    §14. FEED — 부서간 피드                                    L 2974
#
#  PART IV. 통신·협업
#    §15. COMMENTS API                                         L 1303
#    §16. TASK DETAIL API                                      L 1337
#    §17. REACTIONS API                                        L 1365
#    §18. 번역 API + set-lang                                   L 1380
#    §19. 업무 위임 API                                         L 1462
#    §20. 멘션 자동완성 API                                     L 1490
#    §21. SIDEBAR TREE API                                     L 1501
#    §22. ACTIVITIES API                                       L 1550
#    §23. NOTIFICATIONS API                                    L 1784
#    §24. CHANGES INFORM (변경 공지)                            L 3926
#    §25. TICKETS (요청 티켓)                                   L 4237
#    §26. ISSUES (이슈·AS DB)                                   L 4548
#    §27. BOARD (게시판)                                        L 4723
#
#  PART V. 분석·보고
#    §28. SEARCH — 통합 검색                                    L 1583
#    §29. RETRO                                                L 1674
#    §30. COCKPIT (팀장/CEO 라이브)                              L 1694
#    §31. BOTTLENECKS                                          L 1770
#    §32. TEAM DASHBOARD                                       L 1904
#    §33. CEO DASHBOARD                                        L 2176
#    §34. WEEKLY                                               L 2368
#
#  PART VI. 프로젝트
#    §35. PROJECT DETAIL                                       L 2749
#    §36. PROGRESS DASHBOARD                                   L 4150
#    §37. PROGRESS GANTT/BURNDOWN                              L 8713
#
#  PART VII. 매출영업 (M-01)
#    §38. CUSTOMER LIST                                        L 2825
#    §39. CUSTOMER DETAIL                                      L 2853
#    §40. SALES S1 가드 / 라이프사이클                           L 7161
#    §41. COMPANY INFO (견적서 헤더)                             L 7246
#    §42. SALES QUOTATIONS                                     L 7273
#    §43. SALES DASHBOARD / FORECAST                           L 7707
#    §44. OUTSTANDING / RECEIPTS                               L 7914
#
#  PART VIII. 수출입 (M-01-10/11)
#    §45. EXPORT P11                                           L 8122
#    §46. EXPORT PRINT                                         L 8555
#    §47. FTA CERTIFICATES                                     L 9894
#
#  PART IX. 자재구매 (M-02)
#    §48. LOGISTICS HUB                                        L 4952
#    §49. SUPPLIERS                                            L 5269
#    §50. PURCHASE ORDERS                                      L 5368
#    §51. STOCK MOVEMENTS                                      L 5539
#    §52. STOCK S2 가드 / 입출고                                L 6870
#    §53. STOCK AUDIT                                          L 5885
#    §54. STOCK AUDIT v2 (첨부파일·close)                        L 6039
#    §55. SAFETY STOCK / REORDER                               L 9667
#    §56. RATES                                                L 5574
#    §57. RATES STRENGTHENING (단가시뮬·알림)                    L 9455
#    §58. PRICES BY DATE                                       L 5621
#    §59. FX RATES                                             L 9740
#
#  PART X. 품질관리 (QMS)
#    §60. QMS                                                  L 9006
#    §61. QMS CAPA / PARETO                                    L 9218
#    §62. QC INSPECTION REPORTS                                L 10102
#
#  PART XI. 생산
#    §63. WORK ORDERS                                          L 10319
#
#  PART XII. 관리·설정 (M-04)
#    §64. ADMIN                                                L 3097
#    §65. MGMT CODE IMPORT                                     L 3194
#    §66. PASSWORD REGENERATION                                L 3231
#    §67. GUIDE                                                L 3270
#    §68. EXTERNAL ASSETS REVIEW                               L 3283
#    §69. COMPANY INFO ADMIN                                   L 3445
#    §70. HIWORKS LINKS (HR)                                   L 3519
#    §71. PROFILE                                              L 3616
#    §72. REMINDERS                                            L 3799
#    §73. EXPORT WEEKLY CSV                                    L 3840
#    §74. PERMISSIONS S3 (위임 1차)                              L 6208
#    §75. PERMISSIONS S3 v3 (그룹·매트릭스)                       L 6458
#    §76. PERMISSIONS REPORT                                   L 6749
#
#  PART XIII. AI 통합
#    §77. VICTOR AI ASK                                        L 6177
#
# ───────────────────────────────────────────────────────────────────────────────
#  사용법:
#   - 특정 영역 수정: PART X 의 §N 라인으로 점프 (에디터 Ctrl+G)
#   - 전체 검색: 파일 내 "§N." 검색 (예: "§42." → SALES QUOTATIONS)
#   - 라우트 검색: "@app.get(" 또는 "@app.post("
#   - 행 수가 정확하지 않을 수 있음 (수정 시 변동) — _INDEX_main_py.md 참조
#  관련 문서: app/menu_catalog.py (사용자용 M-XX-YY 코드)
# ═══════════════════════════════════════════════════════════════════════════════


BASE = os.path.dirname(os.path.dirname(__file__))
app = FastAPI(title="KNK 일일업무일지 v2")
app.add_middleware(SessionMiddleware, secret_key="knk-haist-2026-phase1")
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
tpl = Jinja2Templates(directory=os.path.join(BASE, "app", "templates"))

# v5H5 (2026-05-02) — t() Jinja 전역: 어느 템플릿에서든 {{ t('키', '기본값') }} 호출 가능
# lang은 request.session.get('lang','ko') 로 자동 결정 (캐시 컨텍스트 없을 시 'ko')
def _t_helper(key: str, default: str = "", lang: str = "ko"):
    try:
        from app.i18n import T
        v = T.get(key)
        if isinstance(v, dict):
            return v.get(lang) or v.get("ko") or default or key
    except Exception:
        pass
    return default or key
tpl.env.globals["t"] = _t_helper


# =====================================================
# v5 H5 (2026-04-29 대표 일괄 승인) — 에러 페이지 핸들러 (404/500)
# 시안 G_standalone/master_G_error_v5H5.html 직접 이식
# =====================================================
from fastapi import HTTPException as _HTTPException
from starlette.exceptions import HTTPException as _StarletteHTTPException

@app.exception_handler(_StarletteHTTPException)
async def _v5_http_exception_handler(request: Request, exc: _StarletteHTTPException):
    code = exc.status_code
    if code in (404, 403, 500, 502, 503):
        try:
            return tpl.TemplateResponse(
                request=request, name="error.html",
                context={"status_code": code, "detail": str(exc.detail or ""),
                         "request": request, "user": get_user(request) if hasattr(request, 'session') else None,
                         "lang": "ko", "i": {}, "LANGS": LANGS,
                         "app_name": "HAIST WORKS"},
                status_code=code,
            )
        except Exception:
            pass
    return JSONResponse({"error": str(exc.detail), "status": code}, status_code=code)


@app.on_event("startup")
def startup():
    init_db()
    seed_all()
    seed_sample_tasks(14)
    # OPS-P1-A2 (B2 안 채택): 일일 미작성자 시스템 알림 스케줄러 시작
    _start_daily_reminder_scheduler()


# =====================================================
# OPS-P1-A2 [D-008] B2 안 — 일일 미작성자 시스템 알림 (16:30 평일)
# 외부 의존 0건 (stdlib threading.Timer). 메일·메신저 발송 X.
# notifications 테이블 INSERT만 → 다음 로그인 시 🔔 자동 표시.
# =====================================================
def _send_daily_missing_reminders():
    """오늘 일일업무카드를 작성하지 않은 활성 사용자에게 시스템 알림."""
    try:
        today_iso = date.today().isoformat()
        with db_session() as c:
            # 활성 + role 'admin'/'ceo' 제외 (대표·관리자는 일지 의무 X)
            missing = [dict(r) for r in c.execute(
                """SELECT u.id, u.name, u.rank
                   FROM users u
                   WHERE u.is_active = 1
                     AND u.role NOT IN ('admin','ceo')
                     AND NOT EXISTS (
                       SELECT 1 FROM tasks t
                       WHERE t.user_id = u.id AND t.work_date = ?
                     )""",
                (today_iso,)
            ).fetchall()]
        sent = 0
        for u in missing:
            try:
                ok = notify_user(
                    user_id=u["id"], type="TASK",
                    title="🔔 오늘 업무카드 미작성",
                    body=f"{u.get('name','')} {u.get('rank','') or ''}님, 오늘({today_iso}) 일일업무카드가 아직 등록되지 않았습니다.",
                    link="/daily",
                )
                if ok:
                    sent += 1
            except Exception:
                continue
        print(f"[DAILY-REMINDER] {today_iso} → 미작성 {len(missing)}명 / 알림 {sent}건 발송")
    except Exception as e:
        print(f"[DAILY-REMINDER ERR] {e}")


def _seconds_until_next_1630_weekday() -> float:
    """다음 평일(월~금) 16:30 까지 남은 초. 토·일이면 다음 월요일 16:30."""
    from datetime import datetime as _dt, timedelta as _td
    now = _dt.now()
    target = now.replace(hour=16, minute=30, second=0, microsecond=0)
    if target <= now:
        target = target + _td(days=1)
    # 주말 건너뛰기
    while target.weekday() >= 5:  # 5=토, 6=일
        target = target + _td(days=1)
    return max(60.0, (target - now).total_seconds())


def _daily_reminder_tick():
    """타이머 콜백 — 평일 16:30에 알림 발송 후 다음 일정 재예약."""
    import threading as _th
    from datetime import datetime as _dt
    try:
        if _dt.now().weekday() < 5:  # 평일만
            _send_daily_missing_reminders()
    except Exception as e:
        print(f"[DAILY-REMINDER tick ERR] {e}")
    # 다음 평일 16:30 재예약
    delay = _seconds_until_next_1630_weekday()
    timer = _th.Timer(delay, _daily_reminder_tick)
    timer.daemon = True
    timer.start()


def _start_daily_reminder_scheduler():
    """startup 1회 호출 — 첫 실행 시각 예약."""
    import threading as _th
    delay = _seconds_until_next_1630_weekday()
    print(f"[DAILY-REMINDER] 스케줄러 시작. 다음 발송까지 {int(delay)}초 ({int(delay/3600)}시간).")
    timer = _th.Timer(delay, _daily_reminder_tick)
    timer.daemon = True
    timer.start()


# =====================================================
# Phase 1 — 빅터 자연어 라우팅 + 메뉴 도움말 API (대표 결재 2026-04-29)
# =====================================================
@app.post("/victor/route")
async def victor_route_query(req: Request):
    """빅터 자연어 → 페이지 후보. 정확 매치 1건이면 redirect URL 반환.
    Body: {q: "견적서 작성"} → JSON.
    """
    u = get_user(req)
    if not u:
        print("[VICTOR-ROUTE] 401 login_required")
        return JSONResponse({"error": "login_required"}, 401)
    try:
        data = await req.json()
        q = (data.get("q") or "").strip()
    except Exception:
        q = ""
    print(f"[VICTOR-ROUTE] 요청 q='{q}' user={u.get('name','?')}")
    if not q:
        return JSONResponse({"ok": False, "msg": "검색어가 비어있습니다."})
    candidates = _menu.search(q, limit=5)
    print(f"[VICTOR-ROUTE] candidates={len(candidates)} → {[c['code'] for c in candidates]}")
    if not candidates:
        return JSONResponse({
            "ok": False,
            "msg": f"'{q}' 와 일치하는 메뉴를 찾지 못했습니다. M-XX-YY 코드 또는 메뉴 이름으로 시도해주세요.",
            "candidates": []
        })
    # 단일 매치 → 자동 이동 / 다중 매치 → 후보 표시
    if len(candidates) == 1:
        m = candidates[0]
        return JSONResponse({
            "ok": True,
            "auto_navigate": True,
            "code": m["code"], "label": m["label"], "path": m["path"], "tip": m["tip"]
        })
    return JSONResponse({
        "ok": True,
        "auto_navigate": False,
        "msg": f"'{q}' 후보 {len(candidates)}개 — 클릭하여 이동:",
        "candidates": [
            {"code": m["code"], "label": m["label"], "path": m["path"], "tip": m["tip"]}
            for m in candidates
        ],
    })


@app.get("/api/menu-help")
async def api_menu_help(req: Request, path: str = "", code: str = ""):
    """현재 페이지의 M-코드·라벨·도움말 조회 (❓ 버튼이 호출)."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "login_required"}, 401)
    m: dict | None = None
    if code:
        m = _menu.by_code(code)
    elif path:
        m = _menu.by_path(path.split("?")[0])
    if not m:
        return JSONResponse({"ok": False, "msg": "이 화면의 도움말이 아직 등록되지 않았습니다."})
    return JSONResponse({
        "ok": True,
        "code": m["code"], "label": m["label"], "path": m["path"],
        "tip": m["tip"], "persona": m["persona"], "aliases": m["aliases"],
    })


@app.get("/api/menu-catalog")
async def api_menu_catalog(req: Request):
    """전체 카탈로그 — 사이드바·도움말 일괄 조회용."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "login_required"}, 401)
    return JSONResponse({"ok": True, "menus": _menu.all_menus(), "hubs": _menu.hubs()})


@app.post("/admin/daily-reminder/run-now")
async def admin_daily_reminder_run_now(req: Request):
    """관리자 수동 트리거 — 즉시 발송 (테스트/긴급용)."""
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    _send_daily_missing_reminders()
    return JSONResponse({"ok": True, "msg": "일일 미작성자 알림 즉시 발송 완료"})


CATEGORIES = ["설계", "제조", "고객대응", "회의", "출장", "검토", "개발", "구매", "품질", "기타"]
STATUSES = ["진행중", "완료", "지연", "대기", "보류"]


# =====================================================
# HELPERS
# =====================================================

# Victor 사이드 도크 — 현재 페이지 기반 맥락 칩 (제안 #08)
VICTOR_CONTEXT_CHIPS = {
    "/home":        ["내 할 일", "오늘 등록", "팀 현황"],
    "/daily":       ["오늘 업무 입력", "어제 업무", "이번 주 보고"],
    "/calendar":    ["이번 달 일정", "내 휴가", "회의 등록"],
    "/notifications": ["최신 알림", "읽지 않은 알림", "내 관련 변경"],
    "/feed":        ["오늘 팀 현황", "지연 공정", "최근 변경"],
    "/now":         ["실시간 누가 무엇을", "지연 공정", "최근 티켓"],
    "/progress":    ["지연 공정", "내 미완료 공정", "납기 임박"],
    "/tickets":     ["미처리 티켓", "내가 받은 요청", "티켓 등록 방법"],
    "/issues":      ["미해결 이슈", "긴급 이슈", "이슈 등록 방법"],
    "/changes":     ["미확인 변경", "내 관련 변경", "긴급 변경"],
    "/dashboard":   ["이번달 매출", "지연 공정", "미처리 업무"],
    "/bottlenecks": ["병목 상세", "담당자 배정", "해결 기록"],
    "/admin":       ["사용자 추가", "권한 변경", "Excel 내보내기"],
    "/sales":       ["이번달 수주", "고객사 Top 5", "영업 단계별"],
    "/logistics":   ["안전재고 미달", "미입고 발주", "재고 금액"],
    "/parts":       ["부품 검색", "FIFO 원가", "공급사 단가"],
    "/po":          ["발주 등록", "미입고 발주", "공급사 리드타임"],
    "/stock/movements": ["최근 출고", "재고 실사", "수불부"],
    "/rates":       ["오늘 환율", "최근 갱신", "통화별 추세"],
    "/board/company": ["긴급 공지", "내 관련 글", "새 글쓰기"],
    "/board/team": ["팀 공지", "내 팀 글", "승인 대기"],
}

def _victor_chips_for_path(path: str):
    """현재 URL 경로에 맞는 맥락 칩 반환. 매칭 없으면 기본 칩."""
    if not path:
        return VICTOR_CONTEXT_CHIPS["/home"]
    # exact match 먼저
    if path in VICTOR_CONTEXT_CHIPS:
        return VICTOR_CONTEXT_CHIPS[path]
    # prefix match (/changes/123 → /changes)
    for key in VICTOR_CONTEXT_CHIPS:
        if path.startswith(key + "/"):
            return VICTOR_CONTEXT_CHIPS[key]
    return VICTOR_CONTEXT_CHIPS["/home"]


# C안 §4 — 워크스페이스 스위처 (시안 12B 헤더)
WORKSPACES = [
    {"key": "hub",   "name": "통합",          "desc": "HAIST WORKS 메인 (업무·진행·이슈·요청)", "icon": "🏢", "href": "/home",      "external": False},
    {"key": "sales", "name": "매출·영업 센터", "desc": "Sales Hub · 영업·수주·고객사",          "icon": "📈", "href": "/sales",     "external": False},
    {"key": "logi",  "name": "자재·구매 센터", "desc": "Logistics Hub · 자재·구매·재고",         "icon": "📦", "href": "/logistics", "external": False},
]

def workspaces_for(user):
    """권한 기반 워크스페이스 목록 (시안 12B 상단 ws-switcher 용).

    2026-04-28 R/W 분리: VIEW 권한자에게도 메뉴 노출 (읽기 전용 진입).
    쓰기 권한 없으면 들어가서 등록 버튼이 비활성/숨김으로 표시.
    """
    if not user:
        return [WORKSPACES[0]]
    out = [WORKSPACES[0]]
    if can_view_sales(user):
        out.append(WORKSPACES[1])
    if can_view_logistics(user):
        out.append(WORKSPACES[2])
    return out

def current_workspace_for(path: str):
    """현재 path 기반 워크스페이스 매핑 (2026-04-28 G8 보강 — 사이드바 모든 sales/logi 경로 정합)"""
    p = path or ""
    # 매출·영업 센터 (Sales Hub)
    #   /sales* · /customer* · /export* (수출입·FTA) · /quotation* · /order*
    if (p.startswith("/sales") or p.startswith("/customer")
        or p.startswith("/export") or p.startswith("/quotation")
        or p.startswith("/order")):
        return WORKSPACES[1]
    # 자재·구매 센터 (Logistics Hub)
    #   /logistics* · /parts* · /po* · /stock* · /supplier* · /rates · /fx*
    if (p.startswith("/logistics") or p.startswith("/parts")
        or p.startswith("/po") or p.startswith("/stock")
        or p.startswith("/supplier") or p.startswith("/rates")
        or p.startswith("/fx")):
        return WORKSPACES[2]
    # 그 외 = 통합 (Hub)
    return WORKSPACES[0]


# =====================================================
# Phase 1 — 메뉴 식별번호 헬퍼 (대표 결재 2026-04-29)
# =====================================================
def _current_menu_for(path: str) -> dict | None:
    """현재 URL → 카탈로그 매칭 결과 (없으면 None)."""
    try:
        # 쿼리스트링 제거
        clean = (path or "").split("?")[0]
        return _menu.by_path(clean)
    except Exception:
        return None


# v5H35 (2026-05-02) — 테스트용 가짜 날짜 헬퍼 (세션 기반, 개인별)
def fake_today_iso(request) -> str:
    """세션에 fake_today 가 설정되면 그 값, 아니면 실제 today (ISO)."""
    try:
        if hasattr(request, "session"):
            fk = request.session.get("fake_today")
            if fk:
                return str(fk)
    except Exception:
        pass
    return date.today().isoformat()


def ctx(request, name, **kwargs):
    # 사용자 언어 결정
    user = kwargs.get("user")
    lang = "ko"
    if user and isinstance(user, dict):
        lang = user.get("lang") or "ko"
    elif hasattr(request, "session"):
        lang = request.session.get("lang", "ko")

    # 번역 사전 생성
    i = get_all_translations(lang)

    # CX23c v4 마스트헤드 컨텍스트 (대표 승인 2026-04-28)
    _today_d = date.today()
    _wkdays = ['월', '화', '수', '목', '금', '토', '일']
    _today_kor = f"{_today_d.year} · {_today_d.month}월 {_today_d.day}일 {_wkdays[_today_d.weekday()]}요일"
    _edition_no = _today_d.timetuple().tm_yday  # 일년 중 N번째 발행

    # v5H35: 테스트 모드 가짜 날짜 (세션 fake_today 가 설정된 경우만)
    _today_iso = fake_today_iso(request)
    _fake_active = False
    try:
        if hasattr(request, "session"):
            _fake_active = bool(request.session.get("fake_today"))
    except Exception:
        pass

    base = {
        "categories": CATEGORIES,
        "statuses": STATUSES,
        "today": _today_iso,
        "real_today": date.today().isoformat(),
        "fake_date_active": _fake_active,
        "now": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "today_kor": _today_kor,            # CX23c 마스트헤드용
        "edition_no": _edition_no,          # CX23c VOL/NO 표시
        "lang": lang,
        "i": i,
        "LANGS": LANGS,
        # HAIST WORKS 브랜드 (통합 후)
        "app_name": "HAIST WORKS",
        "app_subtitle": "KNK 통합 업무 플랫폼",
        "brand_slogan": "Human & AI create the Best",
        # 하이웍스 외부 시스템 URL (admin 설정에서 변경 가능)
        "hiworks_approval_url": get_setting("hiworks_approval_url", "https://office.hiworks.com/"),
        "hiworks_mail_url":     get_setting("hiworks_mail_url",     "https://mail.hiworks.com/"),
        "hiworks_domain":       get_setting("hiworks_domain", ""),
        # Victor 도크 맥락 칩 (제안 #08)
        "victor_chips":         _victor_chips_for_path(str(request.url.path) if hasattr(request, "url") else ""),
        # C안 v2 §2-4 — 워크스페이스 스위처 (uppercase + lowercase 양쪽 노출)
        "workspaces":          workspaces_for(user) if user else [],
        "current_workspace":   current_workspace_for(str(request.url.path) if hasattr(request, "url") else ""),
        "WORKSPACES":          workspaces_for(user) if user else [],
        # Phase 1 (대표 결재 2026-04-29): 메뉴 식별번호 — 현재 페이지 M-코드 + 도움말
        "current_menu":        _current_menu_for(str(request.url.path) if hasattr(request, "url") else ""),
    }
    # 글로벌 알림 카운트 (로그인 상태일 때만)
    uid = request.session.get("user_id") if hasattr(request, "session") else None
    if uid:
        try:
            base["unread_notif"] = count_unread(uid)
        except Exception:
            base["unread_notif"] = 0
    else:
        base["unread_notif"] = 0
    base.update(kwargs)
    return tpl.TemplateResponse(request=request, name=name, context=base)


def get_user(req: Request):
    uid = req.session.get("user_id")
    if not uid:
        return None
    with db_session() as c:
        row = c.execute(
            """SELECT u.*, t.name AS team_name, t.code AS team_code, t.is_lab AS team_is_lab,
                      t.sector AS team_sector
               FROM users u LEFT JOIN teams t ON u.team_id=t.id
               WHERE u.id=? AND u.is_active=1""",
            (uid,),
        ).fetchone()
        return dict(row) if row else None


def require(req: Request, roles=None):
    u = get_user(req)
    if not u:
        return None
    if roles and u["role"] not in roles:
        return None
    return u


def role_home(user) -> str:
    """ESC-02 (감사보고_04 2026-04-22): role별 홈 URL 반환.
    require() 실패 + 로그인 상태인 경우 /login 대신 적절한 홈으로 리다이렉트.
    - ceo/admin/executive → /dashboard
    - leader → /team
    - member/그 외 → /home
    """
    if not user:
        return "/login"
    role = (user.get("role") or "member") if isinstance(user, dict) else str(user["role"])
    if role in ("ceo", "admin", "executive"):
        return "/dashboard"
    elif role == "leader":
        return "/team"
    else:
        return "/home"


def can_use_logistics(user) -> bool:
    """HAIST WORKS 물류 모듈 접근 권한.
    - admin / ceo / executive: 항상 허용
    - team_id == 7 (제조팀): 읽기 허용 (2026-04-22 대표 결재 D01-02 안B)
    - 그 외: users.can_use_logistics 플래그가 1일 때만
    """
    if not user:
        return False
    role = user.get("role") if isinstance(user, dict) else user["role"]
    if role in ("admin", "ceo", "executive"):
        return True
    # 제조팀(team_id=7) 읽기 허용 — 쓰기·발주·단가수정은 구매팀 권한 그대로 유지
    team_id = user.get("team_id") if isinstance(user, dict) else user["team_id"]
    if team_id == 7:
        return True
    flag = user.get("can_use_logistics") if isinstance(user, dict) else user["can_use_logistics"]
    return bool(flag)


def can_view_sales(user) -> bool:
    """매출·영업 **읽기 전용** 권한 (2026-04-28 대표 결재 — R/W 분리).
    - admin / ceo / executive / leader: 항상 허용 (전사 매출 현황 조회)
    - team_id 1·2·3 (영업·검사기·품질): 항상 허용
    - 그 외: users.can_view_sales 플래그 1
    - 쓰기 권한자(can_use_sales=1)는 자동 포함
    """
    if not user:
        return False
    role = user.get("role") if isinstance(user, dict) else user["role"]
    if role in ("admin", "ceo", "executive", "leader"):
        return True
    team_id = user.get("team_id") if isinstance(user, dict) else user["team_id"]
    if team_id in (1, 2, 3):
        return True
    try:
        if user.get("can_view_sales") or user.get("can_use_sales"):
            return True
    except (KeyError, IndexError):
        pass
    return False


def can_view_logistics(user) -> bool:
    """자재·구매 **읽기 전용** 권한 (2026-04-28 대표 결재 — R/W 분리).
    실무자가 부품·재고·단가·구매처를 조회해야 할 때 폭넓게 허용.
    - admin / ceo / executive / leader: 항상 허용
    - team_id 1,2,3,7,8,9,10 (영업·검사기·품질·생산1·생산2·가공·구매): 항상 허용
    - 그 외: users.can_view_logistics 플래그 1
    - 쓰기 권한자(can_use_logistics=1)는 자동 포함
    """
    if not user:
        return False
    role = user.get("role") if isinstance(user, dict) else user["role"]
    if role in ("admin", "ceo", "executive", "leader"):
        return True
    team_id = user.get("team_id") if isinstance(user, dict) else user["team_id"]
    if team_id in (1, 2, 3, 7, 8, 9, 10):
        return True
    try:
        if user.get("can_view_logistics") or user.get("can_use_logistics"):
            return True
    except (KeyError, IndexError):
        pass
    return False


def can_use_sales(user) -> bool:
    """매출·영업 **쓰기** (등록·편집·견적·수주) 권한 (Plan Y S1).
    - admin / ceo / executive: 항상 허용
    - 영업팀·관리팀 leader/member: 항상 허용 (현장 입력자)
    - 그 외: users.can_use_sales 플래그가 1일 때만
    회귀 폴백: can_use_sales 컬럼이 없거나 미설정인 경우 can_use_logistics 로 graceful 폴백.
    """
    if not user:
        return False
    role = user.get("role") if isinstance(user, dict) else user["role"]
    if role in ("admin", "ceo", "executive"):
        return True
    # team_id 1·2·3 (대표직속·영업·관리) 폭넓게 허용 — 추후 팀장 위임 UI 로 정밀화 (S1-2)
    team_id = user.get("team_id") if isinstance(user, dict) else user["team_id"]
    if team_id in (1, 2, 3):
        return True
    try:
        flag = user.get("can_use_sales") if isinstance(user, dict) else user["can_use_sales"]
        if flag:
            return True
    except (KeyError, IndexError):
        pass
    # 회귀 폴백: 기존 logistics 권한자도 일단 허용 (S1 안전 모드, S2에서 분리 강화)
    return can_use_logistics(user)


def status_color(s):
    return {
        "진행중": ("#FFF8E1", "#F57F17"),
        "완료":   ("#E8F5E9", "#2E7D32"),
        "지연":   ("#FFEBEE", "#A5282C"),
        "대기":   ("#F5F5F5", "#4A4A4A"),
        "보류":   ("#F5F5F5", "#4A4A4A"),
    }.get(s, ("#F5F5F5", "#4A4A4A"))


def fetch_projects(c):
    return [dict(r) for r in c.execute(
        """SELECT p.id, p.code, p.name, p.type, c.name AS customer_name
           FROM projects p LEFT JOIN customers c ON p.customer_id=c.id
           WHERE p.status='진행중' ORDER BY p.id"""
    ).fetchall()]


def fetch_customers(c):
    return [dict(r) for r in c.execute(
        "SELECT id, name, tier FROM customers ORDER BY tier DESC, name"
    ).fetchall()]


# =====================================================
# AUTH
# =====================================================
@app.get("/login", response_class=HTMLResponse)
async def login_page(req: Request):
    return ctx(req, "login.html", error=None)


@app.post("/login")
async def login_post(req: Request, login_id: str = Form(...), password: str = Form(...)):
    with db_session() as c:
        u = c.execute(
            "SELECT * FROM users WHERE login_id=? AND password=? AND is_active=1",
            (login_id.strip(), hash_pw(password)),
        ).fetchone()
        if u:
            req.session["user_id"] = u["id"]
            r = u["role"]
            if r == "admin":
                return RedirectResponse("/dashboard", 303)
            if r == "ceo":
                return RedirectResponse("/dashboard", 303)
            if r in ("leader", "executive"):
                return RedirectResponse("/team", 303)
            return RedirectResponse("/daily", 303)
    return ctx(req, "login.html", error="아이디 또는 비밀번호가 올바르지 않습니다.")


@app.get("/logout")
async def logout(req: Request):
    req.session.clear()
    return RedirectResponse("/login", 303)


# =====================================================
# ROOT
# =====================================================
@app.get("/")
async def root(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    return RedirectResponse("/home", 303)


# =====================================================
# HOME — 직관적 단일 페이지 (역할별 자동 분기)
# =====================================================
@app.get("/home", response_class=HTMLResponse)
@app.get("/home/{sel_date}", response_class=HTMLResponse)
async def home_page(req: Request, sel_date: str = "", tab: str = "",
                    no_perm: str = ""):  # D01-NEW-BANNER: 권한 없음 안내 파라미터
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if not sel_date:
        sel_date = date.today().isoformat()
    # 05 디자인팀: 3탭 분할 (내 업무 / 우리 팀 / 전사)
    # role 기반 기본값 — leader 는 team, 경영진은 all, 그 외는 my
    if tab not in ("my", "team", "all"):
        role = (u.get("role") or "member").lower()
        if role in ("ceo", "admin", "executive"):
            tab = "all"
        elif role == "leader":
            tab = "team"
        else:
            tab = "my"

    prev_d = (datetime.strptime(sel_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    next_d = (datetime.strptime(sel_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    with db_session() as c:
        teams = [dict(r) for r in c.execute(
            """SELECT t.*, u.name AS leader_name, u.rank AS leader_rank
               FROM teams t LEFT JOIN users u ON t.leader_id=u.id
               ORDER BY t.display_order"""
        ).fetchall()]

        projects = fetch_projects(c)
        customers = fetch_customers(c)

        # 전체 사용자 수
        total_users = c.execute(
            "SELECT COUNT(*) FROM users WHERE is_active=1 AND role!='admin'"
        ).fetchone()[0]
        today_reporters = c.execute(
            "SELECT COUNT(DISTINCT user_id) FROM tasks WHERE work_date=?",
            (sel_date,),
        ).fetchone()[0]
        participation_rate = round(today_reporters * 100 / total_users) if total_users else 0

        # 팀별 데이터 구축
        team_data = []
        for tm in teams:
            members = [dict(r) for r in c.execute(
                """SELECT id, name, rank, role FROM users
                   WHERE team_id=? AND is_active=1
                   ORDER BY CASE role WHEN 'ceo' THEN 0 WHEN 'executive' THEN 1
                            WHEN 'leader' THEN 2 ELSE 3 END, id""",
                (tm["id"],),
            ).fetchall()]
            mids = [m["id"] for m in members]
            if not mids:
                continue
            ph = ",".join("?" * len(mids))
            tasks = [dict(r) for r in c.execute(
                f"""SELECT t.*, u.name AS user_name, u.rank AS user_rank,
                           p.name AS project_name, p.code AS project_code,
                           cu.name AS customer_name,
                           (SELECT COUNT(*) FROM task_comments WHERE task_id=t.id) AS comment_count
                    FROM tasks t JOIN users u ON t.user_id=u.id
                    LEFT JOIN projects p ON t.project_id=p.id
                    LEFT JOIN customers cu ON t.customer_id=cu.id
                    WHERE t.user_id IN ({ph}) AND t.work_date=?
                    ORDER BY u.id, CASE t.status WHEN '지연' THEN 0 WHEN '진행중' THEN 1
                             WHEN '대기' THEN 2 WHEN '보류' THEN 3 ELSE 4 END, t.id""",
                mids + [sel_date],
            ).fetchall()]

            reported = len(set(t["user_id"] for t in tasks))
            delay_count = len([t for t in tasks if t["status"] == "지연"])
            progress_count = len([t for t in tasks if t["status"] == "진행중"])
            done_count = len([t for t in tasks if t["status"] == "완료"])

            # 신호등: 지연 있으면 빨강, 참여 50% 미만 노랑, 나머지 초록
            if delay_count > 0:
                signal = "red"
            elif reported < len(members) * 0.5:
                signal = "yellow"
            else:
                signal = "green"

            # 멤버별 그룹
            member_tasks = {}
            for m in members:
                mt = [t for t in tasks if t["user_id"] == m["id"]]
                member_tasks[m["id"]] = mt

            team_data.append({
                "team": tm,
                "members": members,
                "tasks": tasks,
                "member_tasks": member_tasks,
                "reported": reported,
                "total_members": len(members),
                "delay": delay_count,
                "progress": progress_count,
                "done": done_count,
                "total": len(tasks),
                "signal": signal,
            })

        # 내 업무 (직원/팀장 공통)
        my_tasks = [dict(r) for r in c.execute(
            """SELECT t.*, p.name AS project_name, p.code AS project_code,
                      cu.name AS customer_name,
                      (SELECT COUNT(*) FROM task_comments WHERE task_id=t.id) AS comment_count
               FROM tasks t
               LEFT JOIN projects p ON t.project_id=p.id
               LEFT JOIN customers cu ON t.customer_id=cu.id
               WHERE t.user_id=? AND t.work_date=?
               ORDER BY CASE t.status WHEN '지연' THEN 0 WHEN '진행중' THEN 1
                        WHEN '대기' THEN 2 WHEN '보류' THEN 3 ELSE 4 END, t.id""",
            (u["id"], sel_date),
        ).fetchall()]

        # 어제 미완료 (이월 후보)
        yday = (datetime.strptime(sel_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        pending_yday = [dict(r) for r in c.execute(
            """SELECT t.*, p.name AS project_name, cu.name AS customer_name
               FROM tasks t LEFT JOIN projects p ON t.project_id=p.id
               LEFT JOIN customers cu ON t.customer_id=cu.id
               WHERE t.user_id=? AND t.work_date=? AND t.status IN ('진행중','지연','대기')
               AND NOT EXISTS (SELECT 1 FROM tasks t2 WHERE t2.carry_from_id=t.id AND t2.work_date=?)
               ORDER BY t.id""",
            (u["id"], yday, sel_date),
        ).fetchall()]

        # 전사 요약
        all_delay = sum(td["delay"] for td in team_data)
        all_tasks = sum(td["total"] for td in team_data)

    # HAIST WORKS — 물류 KPI (간단 집계)
    try:
        from . import database as _logi_db
        logi_parts_stats = _logi_db.parts_count()
        logi_proj_stats = _logi_db.projects_count_logi()
    except Exception:
        logi_parts_stats = {"total": 0, "active": 0, "by_div": {}}
        logi_proj_stats = {"total": 0, "with_code": 0, "in_progress": 0,
                           "by_div": {}, "by_stage": {}}

    # 1순위 신규 기능 카운트 (변경/티켓/진행률 지연)
    hw_counts = {"changes_unread": 0, "tickets_pending": 0, "phases_delayed": 0,
                 "changes_recent": 0}
    try:
        from .database import (change_unread_count, change_recent_count,
                                tickets_count_for_user, progress_summary_for_user)
        hw_counts["changes_unread"] = change_unread_count(u["id"])
        hw_counts["changes_recent"] = change_recent_count(days=1)
        tk = tickets_count_for_user(u["id"], u.get("team_id"))
        hw_counts["tickets_pending"] = tk["my_open"] + tk["recv_pending"]
        pg = progress_summary_for_user(u["id"], u.get("team_id"))
        hw_counts["phases_delayed"] = pg["delayed"]
        hw_counts["phases_my_open"] = pg["my_open"]
    except Exception as e:
        print(f"[HW COUNTS ERROR] {e}")

    # 힐링 #12 §8-bis — 민감 데이터 권한 분기 (매출 컨텍스트 이중 방어)
    # 대표 지적 2026-04-24: "매출을 전직원 공개는 아닌 것 같은데…"
    # 1) UI 조건 분기 (home.html Jinja) · 2) 컨텍스트 분기 (여기) · 3) 라우트 권한 (별도)
    role = (u.get("role") or "member").lower()
    is_executive = role in ("ceo", "admin", "executive")
    is_leader_plus = role in ("ceo", "admin", "executive", "leader")

    monthly_revenue = None
    yoy_delta = None
    if is_executive:
        # 경영진만 매출 지표 컨텍스트 수신
        try:
            from datetime import date as _d
            ym = _d.today().strftime("%Y-%m")
            with db_session() as c:
                r = c.execute(
                    "SELECT COALESCE(SUM(order_amount),0) AS t "
                    "FROM projects WHERE order_date LIKE ? AND order_amount>0",
                    (f"{ym}%",)).fetchone()
                monthly_revenue = r["t"] if r else 0
                # YoY 전년 동월 대비
                last_year_ym = f"{_d.today().year - 1}-{_d.today().strftime('%m')}"
                r2 = c.execute(
                    "SELECT COALESCE(SUM(order_amount),0) AS t "
                    "FROM projects WHERE order_date LIKE ? AND order_amount>0",
                    (f"{last_year_ym}%",)).fetchone()
                last = r2["t"] if r2 else 0
                if last > 0:
                    yoy_delta = round((monthly_revenue - last) / last * 100, 1)
        except Exception as e:
            print(f"[REVENUE KPI ERROR] {e}")

    # 시간대별 인사말 (힐링 원칙서 §7-1)
    greeting_bucket = "default"
    try:
        _h = datetime.now().hour
        _n = u.get("name", "")
        if 6 <= _h < 11:
            greeting = f"좋은 아침입니다, {_n}님 ☀️"; greeting_bucket = "morning"
        elif 11 <= _h < 14:
            greeting = f"점심은 드셨나요, {_n}님? 잠깐 쉬어가요"; greeting_bucket = "lunch"
        elif 14 <= _h < 18:
            greeting = f"오후도 힘내세요, {_n}님 🌿"; greeting_bucket = "afternoon"
        elif 18 <= _h < 22:
            greeting = f"오늘도 수고하셨어요, {_n}님"; greeting_bucket = "evening"
        else:
            greeting = f"늦은 시간까지 애쓰시네요, {_n}님"; greeting_bucket = "night"
    except Exception:
        greeting = f"오늘도 평안하세요, {u.get('name','')}님"

    return ctx(
        req, "home.html",
        user=u, sel_date=sel_date, prev_date=prev_d, next_date=next_d,
        team_data=team_data, my_tasks=my_tasks, pending_yday=pending_yday,
        projects=projects, customers=customers,
        participation_rate=participation_rate,
        today_reporters=today_reporters, total_users=total_users,
        all_delay=all_delay, all_tasks=all_tasks,
        logi_parts_stats=logi_parts_stats, logi_proj_stats=logi_proj_stats,
        hw_counts=hw_counts,
        tab=tab,           # 05 디자인팀 3탭
        no_perm=no_perm,   # D01-NEW-BANNER: 권한 없음 안내 배너
        # 힐링 #12 §8-bis 권한 분기 컨텍스트
        monthly_revenue=monthly_revenue,
        yoy_delta=yoy_delta,
        is_executive=is_executive,
        is_leader_plus=is_leader_plus,
        greeting=greeting,
        greeting_bucket=greeting_bucket,  # QA-H6 패치 ④
    )


# =====================================================
# DAILY — 개인 일일 업무카드
# =====================================================
@app.get("/daily", response_class=HTMLResponse)
@app.get("/daily/{sel_date}", response_class=HTMLResponse)
async def daily_page(req: Request, sel_date: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if not sel_date:
        sel_date = date.today().isoformat()

    prev_d = (datetime.strptime(sel_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    next_d = (datetime.strptime(sel_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    with db_session() as c:
        tasks = [dict(r) for r in c.execute(
            """SELECT t.*, p.name AS project_name, p.code AS project_code,
                      c.name AS customer_name,
                      (SELECT COUNT(*) FROM task_comments WHERE task_id=t.id) AS comment_count,
                      (SELECT MAX(is_ceo_request) FROM task_comments WHERE task_id=t.id) AS has_ceo_req
               FROM tasks t
               LEFT JOIN projects p ON t.project_id=p.id
               LEFT JOIN customers c ON t.customer_id=c.id
               WHERE t.user_id=? AND t.work_date=?
               ORDER BY t.status, t.id""",
            (u["id"], sel_date),
        ).fetchall()]
        # 각 카드에 댓글 첨부
        for t in tasks:
            t["comments"] = [dict(r) for r in c.execute(
                """SELECT tc.*, u.name AS author_name, u.rank AS author_rank, u.role AS author_role
                   FROM task_comments tc JOIN users u ON tc.author_id=u.id
                   WHERE tc.task_id=? ORDER BY tc.created_at""",
                (t["id"],),
            ).fetchall()]

        # 어제 미완료 (carry-forward 후보)
        yday = (datetime.strptime(sel_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        pending_yday = [dict(r) for r in c.execute(
            """SELECT t.*, p.name AS project_name, c.name AS customer_name
               FROM tasks t
               LEFT JOIN projects p ON t.project_id=p.id
               LEFT JOIN customers c ON t.customer_id=c.id
               WHERE t.user_id=? AND t.work_date=? AND t.status IN ('진행중','지연','대기')
               AND NOT EXISTS (
                   SELECT 1 FROM tasks t2 WHERE t2.carry_from_id=t.id AND t2.work_date=?
               )
               ORDER BY t.id""",
            (u["id"], yday, sel_date),
        ).fetchall()]

        projects = fetch_projects(c)
        customers = fetch_customers(c)

        # 통계 - 이번 주
        wk_mon = (datetime.strptime(sel_date, "%Y-%m-%d") -
                  timedelta(days=datetime.strptime(sel_date, "%Y-%m-%d").weekday())).strftime("%Y-%m-%d")
        wk_sun = (datetime.strptime(wk_mon, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
        week_stats = c.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN status='완료' THEN 1 ELSE 0 END) AS done,
                      SUM(CASE WHEN status='진행중' THEN 1 ELSE 0 END) AS progress,
                      SUM(CASE WHEN status='지연' THEN 1 ELSE 0 END) AS delay,
                      COALESCE(SUM(hours),0) AS hours
               FROM tasks WHERE user_id=? AND work_date>=? AND work_date<=?""",
            (u["id"], wk_mon, wk_sun),
        ).fetchone()
        week_stats = dict(week_stats)

    return ctx(
        req, "daily.html",
        user=u, tasks=tasks, sel_date=sel_date,
        prev_date=prev_d, next_date=next_d,
        pending_yday=pending_yday,
        projects=projects, customers=customers,
        week_stats=week_stats, week_range=f"{wk_mon} ~ {wk_sun}",
    )


@app.post("/api/task")
async def api_create_task(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    d = await req.json()
    # v5H28-29: project/customer — FK(매출 프로젝트·고객사) 또는 label(자유 텍스트, 사내업무 등) 자동 분기
    _pid = d.get("project_id") or None
    _plabel = (d.get("project_label") or "").strip() or None
    _cid = d.get("customer_id") or None
    _clabel = (d.get("customer_label") or "").strip() or None
    with db_session() as c:
        cur = c.execute(
            """INSERT INTO tasks(user_id, work_date, title, category, project_id, project_label,
                                  customer_id, customer_label,
                                  status, hours, notes, next_plan, due_date)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                u["id"],
                d.get("work_date") or date.today().isoformat(),
                (d.get("title") or "").strip(),
                d.get("category") or "기타",
                _pid,
                _plabel if not _pid else None,  # FK 있으면 라벨 무시
                _cid,
                _clabel if not _cid else None,
                d.get("status") or "진행중",
                float(d.get("hours") or 0),
                d.get("notes") or "",
                (d.get("next_plan") or "").strip(),
                d.get("due_date") or None,
            ),
        )
        new_id = cur.lastrowid
        log_activity(c, u["id"], "task_create",
                     title=f"{u['name']} 신규 카드: {(d.get('title') or '')[:60]}",
                     body=(d.get("notes") or "")[:200],
                     task_id=new_id,
                     project_id=d.get("project_id") or None,
                     team_id=u.get("team_id"))
    # 지연으로 생성된 경우도 알림
    if (d.get("status") or "") == "지연":
        notify_status_change(new_id, u["id"], "", "지연")
    return JSONResponse({"ok": True, "id": new_id})


@app.put("/api/task/{tid}")
async def api_update_task(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    d = await req.json()
    with db_session() as c:
        prev = c.execute("SELECT user_id, status, title, project_id FROM tasks WHERE id=?", (tid,)).fetchone()
        if not prev or prev["user_id"] != u["id"]:
            return JSONResponse({"error": "권한 없음"}, 403)
        new_status = d.get("status") or "진행중"
        c.execute(
            """UPDATE tasks SET title=?, category=?, project_id=?, customer_id=?,
                               status=?, hours=?, notes=?, next_plan=?, due_date=?,
                               updated_at=datetime('now','localtime')
               WHERE id=?""",
            (
                (d.get("title") or "").strip(),
                d.get("category") or "기타",
                d.get("project_id") or None,
                d.get("customer_id") or None,
                new_status,
                float(d.get("hours") or 0),
                d.get("notes") or "",
                (d.get("next_plan") or "").strip(),
                d.get("due_date") or None,
                tid,
            ),
        )
        if prev["status"] != new_status:
            log_activity(c, u["id"], "task_status",
                         title=f"{u['name']}: {prev['title'][:50]} — {prev['status']} → {new_status}",
                         task_id=tid, project_id=prev["project_id"], team_id=u.get("team_id"))
    if prev["status"] != new_status and new_status == "지연":
        notify_status_change(tid, u["id"], prev["status"], new_status)
    return JSONResponse({"ok": True})


@app.delete("/api/task/{tid}")
async def api_delete_task(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    try:
        with db_session() as c:
            # v5H36: 실제 권한 확인 — 카드 존재 여부 + 작성자/관리자 검증
            row = c.execute("SELECT user_id FROM tasks WHERE id=?", (tid,)).fetchone()
            if not row:
                return JSONResponse({"ok": False, "error": "카드를 찾을 수 없습니다"}, 404)
            is_owner = (int(row["user_id"]) == int(u["id"]))
            is_admin = u.get("role","") in ("ceo","admin")
            if not (is_owner or is_admin):
                return JSONResponse({"ok": False, "error": "작성자만 삭제 가능"}, 403)
            # v5H37: carry_from_id 자기참조 FK가 CASCADE 아님 → 자식(이월된 카드)의 참조 NULL 처리 후 삭제
            c.execute("UPDATE tasks SET carry_from_id=NULL WHERE carry_from_id=?", (tid,))
            # activity_logs / notifications 등 task_id 참조도 안전하게 정리 (CASCADE 미설정 가능성)
            try: c.execute("UPDATE activity_logs SET task_id=NULL WHERE task_id=?", (tid,))
            except Exception: pass
            try: c.execute("UPDATE notifications SET task_id=NULL WHERE task_id=?", (tid,))
            except Exception: pass
            # 본 카드 삭제 (task_comments/task_reactions 등은 ON DELETE CASCADE)
            c.execute("DELETE FROM tasks WHERE id=?", (tid,))
        return JSONResponse({"ok": True})
    except Exception as e:
        # FK violation 또는 기타 오류 → 명확한 메시지
        import traceback; traceback.print_exc()
        return JSONResponse({"ok": False, "error": f"DB 오류: {type(e).__name__}: {str(e)[:200]}"}, 500)


@app.post("/api/task/{tid}/status")
async def api_quick_status(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    d = await req.json()
    new_status = d.get("status") or "진행중"
    with db_session() as c:
        prev = c.execute("SELECT status, title, user_id, project_id FROM tasks WHERE id=?", (tid,)).fetchone()
        if not prev or prev["user_id"] != u["id"]:
            return JSONResponse({"error":"권한 없음"}, 403)
        c.execute(
            "UPDATE tasks SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
            (new_status, tid),
        )
        if prev["status"] != new_status:
            log_activity(c, u["id"], "task_status",
                         title=f"{u['name']}: {prev['title'][:50]} — {prev['status']} → {new_status}",
                         task_id=tid, project_id=prev["project_id"], team_id=u.get("team_id"))
    if prev["status"] != new_status and new_status == "지연":
        notify_status_change(tid, u["id"], prev["status"], new_status)
    return JSONResponse({"ok": True})


@app.post("/api/carry-forward")
async def api_carry_forward(req: Request):
    """어제 미완료 카드 → 오늘로 이월 (전부 또는 선택)"""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    d = await req.json()
    target = d.get("date") or date.today().isoformat()
    ids = d.get("ids") or []
    with db_session() as c:
        if not ids:
            yday = (datetime.strptime(target, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            rows = c.execute(
                """SELECT id FROM tasks WHERE user_id=? AND work_date=?
                   AND status IN ('진행중','지연','대기')""",
                (u["id"], yday),
            ).fetchall()
            ids = [r["id"] for r in rows]
        cnt = 0
        for src_id in ids:
            src = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?",
                            (src_id, u["id"])).fetchone()
            if not src:
                continue
            exists = c.execute(
                "SELECT id FROM tasks WHERE carry_from_id=? AND work_date=?",
                (src_id, target),
            ).fetchone()
            if exists:
                continue
            c.execute(
                """INSERT INTO tasks(user_id, work_date, title, category, project_id,
                                      customer_id, status, hours, notes, due_date, carry_from_id)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    u["id"], target, src["title"], src["category"], src["project_id"],
                    src["customer_id"], "진행중", 0, src["notes"], src["due_date"], src_id,
                ),
            )
            cnt += 1
    return JSONResponse({"ok": True, "count": cnt})


# =====================================================
# SUMMARY — 통합 요약 (일/주/월 × 개인/부서/전사)
# =====================================================
@app.get("/summary", response_class=HTMLResponse)
async def summary_page(req: Request, period: str = "weekly", scope: str = "me", ref: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if period not in ("daily", "weekly", "monthly"):
        period = "weekly"
    if scope not in ("me", "team", "all"):
        scope = "me"
    # 권한: 일반 직원은 me/team만, all은 ceo/admin/executive
    if scope == "all" and u["role"] not in ("ceo", "admin", "executive"):
        scope = "team" if u.get("team_id") else "me"
    if scope == "team" and not u.get("team_id"):
        scope = "me"

    today = date.today()
    if not ref:
        ref = today.isoformat()
    rd = datetime.strptime(ref, "%Y-%m-%d").date()

    # 기간 범위 계산
    if period == "daily":
        frm = to = ref
        prev_ref = (rd - timedelta(days=1)).isoformat()
        next_ref = (rd + timedelta(days=1)).isoformat()
        period_label = ref
    elif period == "weekly":
        mon = rd - timedelta(days=rd.weekday())
        sun = mon + timedelta(days=6)
        frm, to = mon.isoformat(), sun.isoformat()
        prev_ref = (mon - timedelta(days=7)).isoformat()
        next_ref = (mon + timedelta(days=7)).isoformat()
        period_label = f"{frm} ~ {to}"
    else:  # monthly
        first = rd.replace(day=1)
        next_month_first = (first + timedelta(days=32)).replace(day=1)
        last = next_month_first - timedelta(days=1)
        frm, to = first.isoformat(), last.isoformat()
        prev_first = (first - timedelta(days=1)).replace(day=1)
        prev_ref = prev_first.isoformat()
        next_ref = next_month_first.isoformat()
        period_label = first.strftime("%Y년 %m월")

    # 스코프 필터 SQL 조각
    if scope == "me":
        scope_filter = "AND t.user_id = ?"
        scope_args = (u["id"],)
        scope_label = f"{u['name']} {u['rank']}"
    elif scope == "team":
        scope_filter = "AND uu.team_id = ?"
        scope_args = (u["team_id"],)
        scope_label = u["team_name"] or "(부서 미배정)"
    else:
        scope_filter = ""
        scope_args = ()
        scope_label = "전사"

    with db_session() as c:
        # 통계
        sql = f"""SELECT COUNT(*) AS total,
                         SUM(CASE WHEN t.status='완료' THEN 1 ELSE 0 END) AS done,
                         SUM(CASE WHEN t.status='진행중' THEN 1 ELSE 0 END) AS progress,
                         SUM(CASE WHEN t.status='지연' THEN 1 ELSE 0 END) AS delay,
                         SUM(CASE WHEN t.status='대기' THEN 1 ELSE 0 END) AS waiting,
                         COALESCE(SUM(t.hours),0) AS hours
                  FROM tasks t JOIN users uu ON t.user_id = uu.id
                  WHERE t.work_date BETWEEN ? AND ? {scope_filter}"""
        stats = dict(c.execute(sql, (frm, to) + scope_args).fetchone())
        for k in stats:
            stats[k] = stats[k] or 0
        completion_rate = round(stats["done"] * 100 / stats["total"]) if stats["total"] else 0

        # 카드 목록 (내러티브용)
        cards_sql = f"""SELECT t.*, uu.name AS user_name, uu.rank, tm.name AS team_name,
                              p.name AS project_name, cu.name AS customer_name
                       FROM tasks t JOIN users uu ON t.user_id = uu.id
                       LEFT JOIN teams tm ON uu.team_id = tm.id
                       LEFT JOIN projects p ON t.project_id=p.id
                       LEFT JOIN customers cu ON t.customer_id=cu.id
                       WHERE t.work_date BETWEEN ? AND ? {scope_filter}
                       ORDER BY CASE t.status WHEN '지연' THEN 0 WHEN '진행중' THEN 1
                                              WHEN '대기' THEN 2 ELSE 3 END, t.work_date DESC, t.id"""
        cards = [dict(r) for r in c.execute(cards_sql, (frm, to) + scope_args).fetchall()]

        # 팀별/사용자별/프로젝트별 집계
        team_agg = [dict(r) for r in c.execute(
            f"""SELECT tm.name AS team_name, COUNT(*) AS cnt,
                       SUM(CASE WHEN t.status='완료' THEN 1 ELSE 0 END) AS done,
                       SUM(CASE WHEN t.status='지연' THEN 1 ELSE 0 END) AS delay,
                       COALESCE(SUM(t.hours),0) AS hours
                FROM tasks t JOIN users uu ON t.user_id = uu.id
                LEFT JOIN teams tm ON uu.team_id = tm.id
                WHERE t.work_date BETWEEN ? AND ? {scope_filter}
                GROUP BY tm.name ORDER BY cnt DESC""",
            (frm, to) + scope_args,
        ).fetchall()]

        user_agg = [dict(r) for r in c.execute(
            f"""SELECT uu.name AS user_name, uu.rank, COUNT(*) AS cnt,
                       SUM(CASE WHEN t.status='완료' THEN 1 ELSE 0 END) AS done,
                       COALESCE(SUM(t.hours),0) AS hours
                FROM tasks t JOIN users uu ON t.user_id = uu.id
                WHERE t.work_date BETWEEN ? AND ? {scope_filter}
                GROUP BY uu.id ORDER BY cnt DESC LIMIT 20""",
            (frm, to) + scope_args,
        ).fetchall()]

        project_agg = [dict(r) for r in c.execute(
            f"""SELECT p.name AS project_name, p.code AS project_code, COUNT(*) AS cnt,
                       COALESCE(SUM(t.hours),0) AS hours
                FROM tasks t JOIN users uu ON t.user_id = uu.id
                JOIN projects p ON t.project_id = p.id
                WHERE t.work_date BETWEEN ? AND ? {scope_filter}
                GROUP BY p.id ORDER BY cnt DESC LIMIT 15""",
            (frm, to) + scope_args,
        ).fetchall()]

        # 월간일 때만 전월 대비 비교
        prev_stats = None
        delta = None
        if period == "monthly":
            prev_first = (rd.replace(day=1) - timedelta(days=1)).replace(day=1)
            prev_last = rd.replace(day=1) - timedelta(days=1)
            prev_stats = dict(c.execute(sql, (prev_first.isoformat(), prev_last.isoformat()) + scope_args).fetchone())
            for k in prev_stats:
                prev_stats[k] = prev_stats[k] or 0
            def pct(cur, prev):
                if not prev:
                    return None
                return round((cur - prev) * 100 / prev, 1)
            delta = {
                "total": pct(stats["total"], prev_stats["total"]),
                "done": pct(stats["done"], prev_stats["done"]),
                "delay": pct(stats["delay"], prev_stats["delay"]),
                "hours": pct(stats["hours"], prev_stats["hours"]),
            }

        # 일별 추이 (월간일 때)
        daily_trend = []
        if period == "monthly":
            daily_trend = [dict(r) for r in c.execute(
                f"""SELECT t.work_date AS d, COUNT(*) AS cnt,
                           SUM(CASE WHEN t.status='완료' THEN 1 ELSE 0 END) AS done,
                           COALESCE(SUM(t.hours),0) AS hours
                    FROM tasks t JOIN users uu ON t.user_id = uu.id
                    WHERE t.work_date BETWEEN ? AND ? {scope_filter}
                    GROUP BY t.work_date ORDER BY t.work_date""",
                (frm, to) + scope_args,
            ).fetchall()]

    return ctx(req, "summary.html", user=u,
               period=period, scope=scope, ref=ref,
               period_label=period_label, scope_label=scope_label,
               frm=frm, to=to, prev_ref=prev_ref, next_ref=next_ref,
               stats=stats, completion_rate=completion_rate,
               cards=cards[:80], total_cards=len(cards),
               team_agg=team_agg, user_agg=user_agg, project_agg=project_agg,
               prev_stats=prev_stats, delta=delta, daily_trend=daily_trend,
               can_all=u["role"] in ("ceo","admin","executive"),
               can_team=u.get("team_id") is not None,
               active="summary")


# =====================================================
# COMMENTS — 업무카드 댓글/요청사항
# =====================================================
@app.get("/api/task/{tid}/comments")
async def api_list_comments(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    return JSONResponse({"ok": True, "comments": get_task_comments(tid)})


@app.post("/api/task/{tid}/comment")
async def api_add_comment(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    d = await req.json()
    body = (d.get("body") or "").strip()
    if not body:
        return JSONResponse({"error": "내용을 입력하세요"}, 400)
    parent_id = d.get("parent_id") or None
    cid = add_comment(tid, u["id"], body, parent_id)
    return JSONResponse({"ok": True, "id": cid})


@app.delete("/api/comment/{cid}")
async def api_delete_comment(req: Request, cid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    ok = delete_comment(cid, u["id"])
    return JSONResponse({"ok": ok})


# =====================================================
# TASK DETAIL — 모달용 단일 카드 정보 (어디서든 호출)
# =====================================================
# v5H35 (2026-05-02) — 테스트용 가짜 날짜 설정 (세션 기반, ceo/admin/leader 만)
@app.post("/dev/fake-date")
async def dev_set_fake_date(req: Request):
    u = get_user(req)
    if not u or u.get("role","") not in ("ceo","admin","leader","executive"):
        return JSONResponse({"error":"권한 없음"}, 403)
    d = await req.json()
    fk = (d.get("date") or "").strip()
    if fk in ("", "clear", "today"):
        req.session.pop("fake_today", None)
        return JSONResponse({"ok": True, "active": False, "today": date.today().isoformat()})
    # YYYY-MM-DD 검증
    try:
        datetime.strptime(fk, "%Y-%m-%d")
    except Exception:
        return JSONResponse({"error":"형식 오류 (YYYY-MM-DD)"}, 400)
    req.session["fake_today"] = fk
    return JSONResponse({"ok": True, "active": True, "today": fk, "real": date.today().isoformat()})


# v5H30 (2026-05-02) — 일일업무 카드 상세 페이지 (대표 지시: 상세 클릭 시 페이지 부재)
@app.get("/task/{tid}", response_class=HTMLResponse)
async def task_detail_page(request: Request, tid: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        t = c.execute(
            """SELECT t.*, u.name AS user_name, u.rank AS user_rank,
                      p.name AS project_name, p.code AS project_code, p.id AS project_id_link,
                      cs.name AS customer_name, cs.id AS customer_id_link,
                      tm.name AS team_name
               FROM tasks t LEFT JOIN users u ON t.user_id=u.id
               LEFT JOIN projects p ON t.project_id=p.id
               LEFT JOIN customers cs ON t.customer_id=cs.id
               LEFT JOIN teams tm ON u.team_id=tm.id
               WHERE t.id=?""", (tid,)
        ).fetchone()
        if not t:
            return HTMLResponse("<h1>업무 카드를 찾을 수 없습니다</h1><a href='/daily'>← 일일업무로</a>", 404)
        task = dict(t)
        # v5H32: 동일 프로젝트(또는 라벨)의 누적 공수·카드 수 계산 — '며칠/몇주 걸리는 업무' 추적용
        cum = {"hours": 0.0, "cards": 0, "first": None, "last": None}
        if task.get("project_id"):
            row = c.execute("SELECT COALESCE(SUM(hours),0) AS h, COUNT(*) AS n, MIN(work_date) AS f, MAX(work_date) AS l FROM tasks WHERE project_id=? AND user_id=?", (task["project_id"], task["user_id"])).fetchone()
            if row: cum = {"hours": float(row["h"] or 0), "cards": int(row["n"] or 0), "first": row["f"], "last": row["l"]}
        elif task.get("project_label"):
            row = c.execute("SELECT COALESCE(SUM(hours),0) AS h, COUNT(*) AS n, MIN(work_date) AS f, MAX(work_date) AS l FROM tasks WHERE project_label=? AND user_id=?", (task["project_label"], task["user_id"])).fetchone()
            if row: cum = {"hours": float(row["h"] or 0), "cards": int(row["n"] or 0), "first": row["f"], "last": row["l"]}
    comments = get_task_comments(tid)
    reactions = get_reactions(tid)
    return ctx(request, "task_detail.html",
               user=u, active="daily",
               task=task, comments=comments, reactions=reactions, cum=cum)


@app.get("/api/task/{tid}/detail")
async def api_task_detail(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error":"로그인 필요"}, 401)
    with db_session() as c:
        t = c.execute(
            """SELECT t.*, u.name AS user_name, u.rank AS user_rank,
                      p.name AS project_name, cs.name AS customer_name,
                      tm.name AS team_name
               FROM tasks t LEFT JOIN users u ON t.user_id=u.id
               LEFT JOIN projects p ON t.project_id=p.id
               LEFT JOIN customers cs ON t.customer_id=cs.id
               LEFT JOIN teams tm ON u.team_id=tm.id
               WHERE t.id=?""", (tid,)
        ).fetchone()
        if not t:
            return JSONResponse({"error":"카드 없음"}, 404)
    comments = get_task_comments(tid)
    reactions = get_reactions(tid)
    delegations = get_delegations(tid)
    return JSONResponse({"ok":True, "task":dict(t), "comments":comments,
                         "reactions":reactions, "delegations":delegations})


# =====================================================
# REACTIONS — 1-click 빠른 피드백
# =====================================================
@app.post("/api/task/{tid}/reaction")
async def api_reaction(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error":"로그인 필요"}, 401)
    d = await req.json()
    res = add_reaction(tid, u["id"], d.get("kind") or "")
    if not res:
        return JSONResponse({"error":"잘못된 반응"}, 400)
    return JSONResponse({"ok":True, "result":res, "reactions":get_reactions(tid)})


# =====================================================
# 번역 API
# =====================================================
@app.api_route("/api/set-lang", methods=["GET", "POST"])
async def api_set_lang(req: Request):
    """사용자 UI 언어 변경.
    - POST(JSON body): 기존 프런트 fetch 호출용 (base.html changeLang)
    - GET(쿼리스트링 ?lang=vi): 주소창·북마크·테스트 호출용
    """
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    # lang 값 획득: GET 은 쿼리, POST 는 JSON body
    lang = None
    if req.method == "POST":
        try:
            data = await req.json()
            lang = (data or {}).get("lang")
        except Exception:
            lang = None
    if not lang:
        lang = req.query_params.get("lang") or "ko"
    if lang not in LANGS:
        lang = "ko"
    with db_session() as c:
        c.execute("UPDATE users SET lang=? WHERE id=?", (lang, u["id"]))
    req.session["lang"] = lang
    # GET 이면 이전 페이지로 303 리다이렉트(주소창/북마크 UX), POST 는 JSON
    if req.method == "GET":
        back = req.headers.get("referer") or "/home"
        return RedirectResponse(back, status_code=303)
    return JSONResponse({"ok": True, "lang": lang})


@app.post("/api/translate")
async def api_translate(req: Request):
    """
    사내 사전 번역 (외부 API 0건).
    사이클 69 (2026-04-27): deep_translator + Google Translate URL 직접 호출 제거.
    오리엔테이션 §3.1 외부 자산 0건 정책 이행. 대표 14:19 "부분 처리" 결정.
    동작: app/i18n.py T 사전(약 472키 / ko·vi·en)에서 입력 텍스트와 매칭되는 항목을 찾아 응답.
    매칭 실패 시 "사내 사전 미등록" 안내 + 빅터AI 등록 기능(사이클 70+) 예고.
    """
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    d = await req.json()
    text = (d.get("text") or "").strip()
    target = d.get("target") or "vi"  # 기본: 베트남어
    if not text:
        return JSONResponse({"error": "텍스트 없음"}, 400)
    if target not in ("ko", "vi", "en"):
        return JSONResponse({"error": "지원 언어: ko/vi/en"}, 400)

    # 사내 사전 lookup — i18n.py T 사전 정/역방향 모두 시도
    try:
        from .i18n import T as _T
    except Exception:
        return JSONResponse({"ok": False,
                             "error": "사내 사전 모듈 로드 실패"}, 500)

    norm = text.strip()
    # 1) value(원문 문구) → 다른 언어 value 매칭
    for _key, entry in _T.items():
        if not isinstance(entry, dict):
            continue
        for _src_lang, _src_text in entry.items():
            if isinstance(_src_text, str) and _src_text.strip() == norm:
                tgt_text = entry.get(target)
                if tgt_text:
                    return JSONResponse({"ok": True,
                                         "translated": tgt_text,
                                         "target": target,
                                         "source": "사내 사전"})
    # 2) 매칭 실패 — 빅터AI 등록 안내
    return JSONResponse({
        "ok": False,
        "error": "사내 사전 미등록 — 빅터AI 단어 등록 기능(예정)으로 추가 가능합니다.",
        "source": "사내 사전",
    }, 200)


# =====================================================
# 업무 위임 (Delegation)
# =====================================================
@app.post("/api/task/{tid}/delegate")
async def api_delegate(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error":"로그인 필요"}, 401)
    d = await req.json()
    to_id = d.get("to_user_id")
    msg = (d.get("message") or "").strip()
    if not to_id:
        return JSONResponse({"error":"위임 대상을 선택하세요"}, 400)
    delegate_task(tid, u["id"], int(to_id), msg)
    return JSONResponse({"ok": True})


@app.post("/api/delegation/{did}/resolve")
async def api_resolve_delegation(req: Request, did: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error":"로그인 필요"}, 401)
    ok = resolve_delegation(did, u["id"])
    if not ok:
        return JSONResponse({"error":"본인만 완료 처리 가능"}, 403)
    return JSONResponse({"ok": True})


# =====================================================
# @멘션 자동완성
# =====================================================
@app.get("/api/users/search")
async def api_user_search(req: Request, q: str = ""):
    u = get_user(req)
    if not u:
        return JSONResponse({"error":"로그인 필요"}, 401)
    return JSONResponse({"ok":True, "users":get_user_search(q.strip(), 8)})


# =====================================================
# SIDEBAR TREE — Notion 스타일 좌측 트리 데이터
# =====================================================
@app.get("/api/sidebar-tree")
async def api_sidebar_tree(req: Request):
    """좌측 사이드바에 표시할 트리 구조:
       팀 목록 > 하위 프로젝트 > (선택시 해당 페이지 이동)
       + 오늘 카드 수, 지연 카운트"""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    today_s = date.today().isoformat()
    with db_session() as c:
        teams = [dict(r) for r in c.execute(
            """SELECT t.id, t.name, t.code, t.is_lab, t.display_order,
                      u.name AS leader_name
               FROM teams t LEFT JOIN users u ON t.leader_id=u.id
               ORDER BY t.display_order"""
        ).fetchall()]
        for t in teams:
            stats = c.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN tk.status='지연' THEN 1 ELSE 0 END) AS delay
                   FROM tasks tk JOIN users u ON tk.user_id=u.id
                   WHERE u.team_id=? AND tk.work_date=?""",
                (t["id"], today_s)
            ).fetchone()
            t["today_count"] = stats["total"] or 0
            t["delay_count"] = stats["delay"] or 0
            # 팀 하위 활성 프로젝트
            projects = [dict(r) for r in c.execute(
                """SELECT DISTINCT p.id, p.name, p.status
                   FROM projects p
                   JOIN tasks tk ON tk.project_id=p.id
                   JOIN users u ON tk.user_id=u.id
                   WHERE u.team_id=? AND p.status IN ('active','진행중','planning')
                   ORDER BY p.name""",
                (t["id"],)
            ).fetchall()]
            t["projects"] = projects
        # 즐겨찾기 / 내 카드 요약
        my_today = c.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND work_date=?",
            (u["id"], today_s)
        ).fetchone()[0]
    return JSONResponse({"ok": True, "teams": teams, "my_today": my_today,
                         "user_role": u["role"], "user_team_id": u.get("team_id")})


# =====================================================
# ACTIVITIES — 실시간 활동 피드
# =====================================================
@app.get("/api/activities")
async def api_activities(req: Request, scope: str = "all", since_id: int = 0):
    u = get_user(req)
    if not u:
        return JSONResponse({"error":"로그인 필요"}, 401)
    team_id = None
    actor_id = None
    if scope == "team" and u.get("team_id"):
        team_id = u["team_id"]
    elif scope == "me":
        actor_id = u["id"]
    items = get_activities(limit=80, team_id=team_id, actor_id=actor_id, since_id=since_id)
    return JSONResponse({"ok":True, "items":items})


@app.get("/now", response_class=HTMLResponse)
async def now_feed(req: Request, scope: str = "all"):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    team_id = None; actor_id = None
    if scope == "team" and u.get("team_id"):
        team_id = u["team_id"]
    elif scope == "me":
        actor_id = u["id"]
    items = get_activities(limit=80, team_id=team_id, actor_id=actor_id)
    return ctx(req, "now.html", user=u, items=items, scope=scope,
               can_team=u.get("team_id") is not None, active="now")


# =====================================================
# 통합 검색 (글로벌 검색 강화 — 2026-04-26)
# 카테고리: 카드/댓글/회고 + 수주/고객/부품/이슈/티켓/사용자/게시판/수출입/재고
# 외부 검색엔진 0건 (Elasticsearch 등 절대 금지) · LIKE parameter binding 절대.
# =====================================================
SEARCH_CAT_LABELS = {
    "tasks": "📋 카드", "comments": "💬 댓글", "retros": "📖 회고",
    "orders": "📦 수주", "customers": "🤝 고객", "parts": "🔩 부품",
    "issues": "⚠️ 이슈", "tickets": "🎫 티켓", "users": "👤 사용자",
    "boards": "📰 게시판", "exports": "🚢 수출입", "audits": "📊 재고실사",
}


@app.get("/search", response_class=HTMLResponse)
async def search_page(req: Request, q: str = "", cat: str = "all"):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    cat = (cat or "all").strip().lower()
    cats = None if cat == "all" else [cat]
    res = {"tasks":[], "comments":[], "retros":[]}
    res_global = {}
    if q and len(q.strip()) >= 1:
        # 카드/댓글/회고 (기존 search_all)
        if cat in ("all", "tasks", "comments", "retros"):
            full = search_all(q, 50)
            if cat == "all":
                res = full
            elif cat == "tasks":
                res = {"tasks": full.get("tasks", []), "comments": [], "retros": []}
            elif cat == "comments":
                res = {"tasks": [], "comments": full.get("comments", []), "retros": []}
            elif cat == "retros":
                res = {"tasks": [], "comments": [], "retros": full.get("retros", [])}
        # 글로벌 9개 카테고리
        global_cats = list(GLOBAL_SEARCH_CATEGORIES.keys())
        if cat == "all":
            res_global = global_search(q, None, 5)
        elif cat in global_cats:
            res_global = global_search(q, [cat], 5)
    return ctx(req, "search.html", user=u, q=q, cat=cat, res=res,
               res_global=res_global, cat_labels=SEARCH_CAT_LABELS, active="search")


@app.post("/search/suggest")
async def api_search_suggest(req: Request):
    """헤더 검색창 자동완성 — 카테고리별 상위 3건씩, 라벨만."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error":"로그인 필요"}, 401)
    try:
        d = await req.json()
    except Exception:
        d = {}
    q = (d.get("q") or "").strip()
    if len(q) < 2:
        return JSONResponse({"ok": True, "items": []})
    items = []
    # 핵심 5개 카테고리 (자동완성 부담 최소)
    suggest_cats = ["orders", "customers", "parts", "issues", "users"]
    res = global_search(q, suggest_cats, 3)
    for cat in suggest_cats:
        for r in res.get(cat, []):
            label = ""
            if cat == "orders":
                label = f"{r.get('order_no','')} · {r.get('customer_name','') or ''}"
                link = "/sales/orders"
            elif cat == "customers":
                label = r.get("name", "")
                link = f"/customer/{r['id']}"
            elif cat == "parts":
                label = f"{r.get('part_no','')} · {r.get('part_name','')}"
                link = f"/parts/{r['id']}"
            elif cat == "issues":
                label = f"{r.get('issue_no','') or ''} · {r.get('title','')}"
                link = f"/issues/{r['id']}"
            elif cat == "users":
                label = f"{r.get('name','')} · {r.get('rank','') or r.get('team_name','') or ''}"
                link = "/search?cat=users&q=" + q
            else:
                label = str(r.get("id", ""))
                link = "/search?q=" + q
            items.append({
                "cat": cat,
                "cat_label": SEARCH_CAT_LABELS.get(cat, cat),
                "label": label.strip(" ·"),
                "link": link,
            })
    return JSONResponse({"ok": True, "q": q, "items": items[:15]})


# =====================================================
# 프로젝트 회고 (Retro)
# =====================================================
@app.post("/api/project/{pid}/retro")
async def api_retro_save(req: Request, pid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error":"로그인 필요"}, 401)
    d = await req.json()
    rid = upsert_retro(pid, u["id"],
                       (d.get("went_well") or "").strip(),
                       (d.get("went_bad") or "").strip(),
                       (d.get("next_action") or "").strip(),
                       (d.get("risk_note") or "").strip())
    log_activity_standalone(u["id"], "retro",
                            title=f"{u['name']} 프로젝트 회고 작성",
                            project_id=pid, team_id=u.get("team_id"))
    return JSONResponse({"ok":True, "id":rid})


# =====================================================
# 코크핏 (팀장/CEO 라이브 시야)
# =====================================================
@app.get("/cockpit", response_class=HTMLResponse)
async def cockpit_page(req: Request):
    # Plan Y S1 대표 승인 2026-04-24: /cockpit 은 /dashboard 와 기능 중복 → 301 합병
    # 기존 기능(조종석 지표)은 /dashboard 내 "코크핏" 탭으로 제공 예정 (S2).
    # 기존 북마크 보호를 위해 라우트는 유지하되 리다이렉트로 전환.
    return RedirectResponse("/dashboard?view=cockpit", 301)


@app.get("/_cockpit_legacy", response_class=HTMLResponse)
async def _cockpit_legacy_unused(req: Request):
    """[DEPRECATED 2026-04-24] 합병 이전 구 /cockpit 로직 — 복원용 보관."""
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if u["role"] not in ("leader","executive","ceo","admin"):
        return RedirectResponse("/dashboard", 303)
    today_iso = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    is_global = u["role"] in ("ceo","admin","executive")
    team_filter = ""
    params = []
    if not is_global and u.get("team_id"):
        team_filter = "AND u.team_id = ?"
        params = [u["team_id"]]

    with db_session() as c:
        # 우리팀(또는 전사) 멤버
        members = c.execute(
            f"""SELECT u.id, u.name, u.rank, tm.name AS team_name,
                       (SELECT COUNT(*) FROM tasks WHERE user_id=u.id AND work_date=?) AS today_cn,
                       (SELECT COUNT(*) FROM tasks WHERE user_id=u.id AND status='지연') AS delay_cn,
                       (SELECT COUNT(*) FROM tasks WHERE user_id=u.id AND status='진행중') AS prog_cn,
                       (SELECT COUNT(*) FROM tasks t JOIN task_comments tc ON tc.task_id=t.id
                        WHERE t.user_id=u.id AND tc.is_ceo_request=1
                        AND NOT EXISTS (SELECT 1 FROM task_comments tc2
                                        WHERE tc2.task_id=tc.task_id AND tc2.id>tc.id)) AS unanswered_ceo
                FROM users u LEFT JOIN teams tm ON u.team_id=tm.id
                WHERE u.is_active=1 AND u.role NOT IN ('admin') {team_filter}
                ORDER BY tm.display_order, u.id""",
            tuple([today_iso] + params)
        ).fetchall()

        # 막힌 카드 (지연 + 코멘트 미해결)
        stuck = c.execute(
            f"""SELECT t.id, t.title, t.work_date, u.name AS owner_name, tm.name AS team_name,
                       (SELECT COUNT(*) FROM task_comments WHERE task_id=t.id) AS cn
                FROM tasks t JOIN users u ON t.user_id=u.id
                LEFT JOIN teams tm ON u.team_id=tm.id
                WHERE t.status='지연' {team_filter}
                ORDER BY t.work_date LIMIT 30""",
            tuple(params)
        ).fetchall()

        # 미작성자 (오늘)
        missing = c.execute(
            f"""SELECT u.id, u.name, u.rank, tm.name AS team_name
                FROM users u LEFT JOIN teams tm ON u.team_id=tm.id
                WHERE u.is_active=1 AND u.role NOT IN ('admin','ceo')
                AND NOT EXISTS (SELECT 1 FROM tasks WHERE user_id=u.id AND work_date=?)
                {team_filter} ORDER BY tm.display_order, u.name""",
            tuple([today_iso] + params)
        ).fetchall()

    bn = detect_bottlenecks() if is_global else []
    return ctx(req, "cockpit.html", user=u,
               members=[dict(r) for r in members],
               stuck=[dict(r) for r in stuck],
               missing=[dict(r) for r in missing],
               bottlenecks=bn,
               is_global=is_global,
               active="cockpit")


# =====================================================
# 병목 자동 감지 페이지
# =====================================================
@app.get("/bottlenecks", response_class=HTMLResponse)
async def bottlenecks_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if u["role"] not in ("leader","executive","ceo","admin"):
        return RedirectResponse("/dashboard", 303)
    items = detect_bottlenecks()
    return ctx(req, "bottlenecks.html", user=u, items=items, active="bottlenecks")


# =====================================================
# NOTIFICATIONS — 알림 (벨 아이콘 + 드롭다운)
# =====================================================
@app.get("/api/notifications")
async def api_notifications(req: Request, only_unread: int = 0):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    items = get_notifications(u["id"], only_unread=bool(only_unread), limit=30)
    return JSONResponse({"ok": True, "items": items, "unread": count_unread(u["id"])})


@app.post("/api/notification/{nid}/read")
async def api_notif_read(req: Request, nid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    mark_notification_read(nid, u["id"])
    return JSONResponse({"ok": True})


@app.post("/api/notifications/read-all")
async def api_notif_read_all(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    mark_all_read(u["id"])
    return JSONResponse({"ok": True})


@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    items = get_notifications(u["id"], limit=100)
    return ctx(req, "notifications.html", user=u, items=items, active="notifications")


# 통합 알림 — 비-/api/ 경로 (사이클 2026-04-26 알림시스템-통합)
@app.post("/notifications/{nid}/read")
async def notifications_read(req: Request, nid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "auth"}, 401)
    mark_notification_read(nid, u["id"])
    return JSONResponse({"ok": True})


@app.post("/notifications/read-all")
async def notifications_read_all(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "auth"}, 401)
    mark_all_read(u["id"])
    return JSONResponse({"ok": True})


@app.get("/notifications/badge")
async def notifications_badge(req: Request):
    """헤더 배지 카운트 (UNREAD)."""
    u = get_user(req)
    if not u:
        return JSONResponse({"count": 0})
    return JSONResponse({"count": count_unread(u["id"])})


# =====================================================
# HISTORY — 개인 히스토리 (내가 한 일 검색/조회)
# =====================================================
@app.get("/history", response_class=HTMLResponse)
async def history_page(req: Request, q: str = "", frm: str = "", to: str = "", status: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if not frm:
        frm = (date.today() - timedelta(days=30)).isoformat()
    if not to:
        to = date.today().isoformat()
    # 유효한 status만 필터 허용
    valid_statuses = {"완료", "진행중", "지연", "대기", "보류"}
    if status and status not in valid_statuses:
        status = ""
    with db_session() as c:
        sql = """SELECT t.*, p.name AS project_name, c.name AS customer_name
                 FROM tasks t
                 LEFT JOIN projects p ON t.project_id=p.id
                 LEFT JOIN customers c ON t.customer_id=c.id
                 WHERE t.user_id=? AND t.work_date>=? AND t.work_date<=?"""
        params = [u["id"], frm, to]
        if q:
            sql += " AND (t.title LIKE ? OR t.notes LIKE ?)"
            params += [f"%{q}%", f"%{q}%"]
        if status:
            sql += " AND t.status=?"
            params.append(status)
        sql += " ORDER BY t.work_date DESC, t.id DESC"
        tasks = [dict(r) for r in c.execute(sql, params).fetchall()]

        summary = c.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN status='완료' THEN 1 ELSE 0 END) AS done,
                      COALESCE(SUM(hours),0) AS hours
               FROM tasks WHERE user_id=? AND work_date>=? AND work_date<=?""",
            (u["id"], frm, to),
        ).fetchone()
        summary = dict(summary)

        by_category = [dict(r) for r in c.execute(
            """SELECT category, COUNT(*) AS cnt, COALESCE(SUM(hours),0) AS hrs
               FROM tasks WHERE user_id=? AND work_date>=? AND work_date<=?
               GROUP BY category ORDER BY cnt DESC""",
            (u["id"], frm, to),
        ).fetchall()]

    return ctx(req, "history.html",
               user=u, tasks=tasks, q=q, frm=frm, to=to, status=status,
               summary=summary, by_category=by_category)


# =====================================================
# TEAM — 팀장 뷰 + 팀원 권한 위임 UI (Plan Y S1)
# =====================================================
@app.get("/team/permissions", response_class=HTMLResponse)
async def team_permissions_index(req: Request):
    """팀원 권한 관리 인덱스 — team_id 없는 사용자(CEO/admin/임원) 진입점.
    - leader: 본인 팀으로 redirect
    - 그 외 권한자: 14팀 카드 인덱스 표시
    """
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if u["role"] not in ("leader", "executive", "ceo", "admin"):
        return RedirectResponse("/home", 303)
    if u["role"] == "leader" and u.get("team_id"):
        return RedirectResponse(f"/team/{u['team_id']}/permissions", 303)
    # CEO/임원/admin → 첫 활성 팀으로 redirect (인덱스도 페이지 구조 동일)
    with db_session() as c:
        first = c.execute(
            "SELECT id FROM teams ORDER BY display_order LIMIT 1"
        ).fetchone()
    if first:
        return RedirectResponse(f"/team/{first['id']}/permissions", 303)
    return RedirectResponse("/home", 303)


@app.get("/team/{team_id:int}/permissions", response_class=HTMLResponse)
async def team_permissions_page(req: Request, team_id: int):
    """Plan Y S1: 팀장 권한 위임 UI — 팀원별 4~5개 권한 토글 (3 클릭 원칙).
    - 팀장: 본인 팀만 관리 가능
    - CEO/executive/admin: 전 팀 관리 가능
    """
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if u["role"] not in ("leader", "executive", "ceo", "admin"):
        return RedirectResponse("/home", 303)
    # 팀장은 본인 팀만 (감사 가드)
    if u["role"] == "leader" and u.get("team_id") != team_id:
        return RedirectResponse(f"/team/{u.get('team_id')}/permissions", 303)

    with db_session() as c:
        team = c.execute("SELECT * FROM teams WHERE id=?", (team_id,)).fetchone()
        if not team:
            return RedirectResponse("/home", 303)
        team = dict(team)
        members = [dict(r) for r in c.execute(
            """SELECT id, name, rank, role,
                      can_use_sales, can_use_logistics,
                      can_view_sales, can_view_logistics,
                      can_edit_changes, can_close_tickets, is_admin
               FROM users
               WHERE team_id=? AND is_active=1
               ORDER BY
                 CASE role WHEN 'executive' THEN 0 WHEN 'leader' THEN 1 ELSE 2 END,
                 id""",
            (team_id,)
        ).fetchall()]
        # KPI: 권한별 부여 인원 (현재 팀) — 2026-04-28 view/use 분리
        kpi = {
            "total":      len(members),
            "view_sales": sum(1 for m in members if m.get("can_view_sales") or m.get("can_use_sales")),
            "sales":      sum(1 for m in members if m.get("can_use_sales")),
            "view_logi":  sum(1 for m in members if m.get("can_view_logistics") or m.get("can_use_logistics")),
            "logi":       sum(1 for m in members if m.get("can_use_logistics")),
            "chg":        sum(1 for m in members if m.get("can_edit_changes")),
            "tkt":        sum(1 for m in members if m.get("can_close_tickets")),
            "adm":        sum(1 for m in members if m.get("is_admin")),
            "seed":       sum(1 for m in members if m.get("role") in ("ceo", "executive")),
        }
        # 최근 7일 권한 변경 이력 (notifications 에서 "권한 변경" 항목)
        try:
            recent_changes = [dict(r) for r in c.execute(
                """SELECT n.title, n.body, n.created_at,
                          u.name AS actor_name, u.rank AS actor_rank
                   FROM notifications n
                   LEFT JOIN users u ON u.id = n.user_id
                   WHERE n.title='권한 변경'
                     AND n.body LIKE ?
                     AND date(n.created_at) >= date('now', '-7 days')
                   ORDER BY n.created_at DESC LIMIT 10""",
                (f"%team_id={team_id}%",)
            ).fetchall()]
        except Exception:
            recent_changes = []
        # 전 팀 목록 (CEO/임원/admin 만)
        all_teams = []
        if u["role"] in ("ceo", "admin", "executive"):
            all_teams = [dict(r) for r in c.execute(
                """SELECT t.*, (SELECT COUNT(*) FROM users u WHERE u.team_id=t.id AND u.is_active=1) AS member_count
                   FROM teams t ORDER BY t.display_order"""
            ).fetchall()]
    is_admin_actor = u["role"] in ("ceo", "admin")
    return ctx(req, "admin_team_perms.html", user=u, active="team_perms",
               team=team, members=members, kpi=kpi,
               recent_changes=recent_changes, all_teams=all_teams,
               is_admin_actor=is_admin_actor)


@app.post("/team/{team_id:int}/permissions")
async def team_permissions_save(req: Request, team_id: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if u["role"] not in ("leader", "executive", "ceo", "admin"):
        return RedirectResponse("/home", 303)
    if u["role"] == "leader" and u.get("team_id") != team_id:
        return RedirectResponse("/home", 303)

    form = await req.form()
    is_admin_actor = u["role"] in ("ceo", "admin")
    saved = 0
    with db_session() as c:
        members = c.execute(
            "SELECT id, role FROM users WHERE team_id=? AND is_active=1", (team_id,)
        ).fetchall()
        for m in members:
            mid = m["id"]
            if not form.get(f"touch_{mid}"):
                continue
            # CEO/임원은 시드 유지 (해제 불가)
            if m["role"] in ("ceo", "executive"):
                continue
            v_sales = 1 if form.get(f"vsales_{mid}") else 0
            sales   = 1 if form.get(f"sales_{mid}")  else 0
            v_logi  = 1 if form.get(f"vlogi_{mid}")  else 0
            logi    = 1 if form.get(f"logi_{mid}")   else 0
            chg     = 1 if form.get(f"chg_{mid}")    else 0
            tkt     = 1 if form.get(f"tkt_{mid}")    else 0
            # write implies read (등록 권한 있으면 보기 자동 ON)
            if sales: v_sales = 1
            if logi:  v_logi = 1
            # is_admin 은 ceo/admin만 변경 가능
            if is_admin_actor:
                adm = 1 if form.get(f"adm_{mid}") else 0
                c.execute(
                    "UPDATE users SET can_view_sales=?, can_use_sales=?, "
                    "can_view_logistics=?, can_use_logistics=?, "
                    "can_edit_changes=?, can_close_tickets=?, is_admin=? WHERE id=?",
                    (v_sales, sales, v_logi, logi, chg, tkt, adm, mid)
                )
            else:
                c.execute(
                    "UPDATE users SET can_view_sales=?, can_use_sales=?, "
                    "can_view_logistics=?, can_use_logistics=?, "
                    "can_edit_changes=?, can_close_tickets=? WHERE id=?",
                    (v_sales, sales, v_logi, logi, chg, tkt, mid)
                )
            saved += 1
        # 감사 로그: notification 자동 기록
        try:
            c.execute(
                "INSERT INTO notifications(user_id, title, body, created_at) VALUES(?,?,?,?)",
                (u["id"], "권한 변경", f"{saved}명의 권한을 업데이트하셨습니다 (team_id={team_id})",
                 datetime.now().isoformat(timespec="seconds"))
            )
        except Exception:
            pass
    return RedirectResponse(f"/team/{team_id}/permissions?saved={saved}", 303)


@app.get("/team", response_class=HTMLResponse)
@app.get("/team/{sel_date}", response_class=HTMLResponse)
async def team_page(req: Request, sel_date: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if u["role"] not in ("leader", "executive", "ceo", "admin"):
        return RedirectResponse("/daily", 303)
    if not sel_date:
        sel_date = date.today().isoformat()

    # CEO/admin은 쿼리로 team 선택 가능, 기본 전체
    with db_session() as c:
        teams = [dict(r) for r in c.execute(
            "SELECT * FROM teams ORDER BY display_order"
        ).fetchall()]

        target_team_id = req.query_params.get("team_id")
        if u["role"] in ("leader", "executive"):
            target_team_id = u["team_id"]
        elif target_team_id:
            target_team_id = int(target_team_id)
        else:
            target_team_id = teams[0]["id"] if teams else None

        members = []
        if target_team_id:
            members = [dict(r) for r in c.execute(
                """SELECT id, name, rank, role FROM users
                   WHERE team_id=? AND is_active=1
                   ORDER BY CASE role
                        WHEN 'ceo' THEN 0 WHEN 'executive' THEN 1
                        WHEN 'leader' THEN 2 ELSE 3 END, id""",
                (target_team_id,),
            ).fetchall()]

        mids = [m["id"] for m in members]
        day_tasks = []
        week_tasks = []
        if mids:
            ph = ",".join("?" * len(mids))
            day_tasks = [dict(r) for r in c.execute(
                f"""SELECT t.*, u.name AS user_name, u.rank AS user_rank,
                           p.name AS project_name, cu.name AS customer_name
                    FROM tasks t JOIN users u ON t.user_id=u.id
                    LEFT JOIN projects p ON t.project_id=p.id
                    LEFT JOIN customers cu ON t.customer_id=cu.id
                    WHERE t.user_id IN ({ph}) AND t.work_date=?
                    ORDER BY u.id, t.status, t.id""",
                mids + [sel_date],
            ).fetchall()]

            # 이번 주
            d0 = datetime.strptime(sel_date, "%Y-%m-%d")
            mon = (d0 - timedelta(days=d0.weekday())).strftime("%Y-%m-%d")
            sun = (d0 - timedelta(days=d0.weekday()) + timedelta(days=6)).strftime("%Y-%m-%d")
            week_tasks = [dict(r) for r in c.execute(
                f"""SELECT t.*, u.name AS user_name FROM tasks t JOIN users u ON t.user_id=u.id
                    WHERE t.user_id IN ({ph}) AND t.work_date>=? AND t.work_date<=?""",
                mids + [mon, sun],
            ).fetchall()]

            # 카드 표면 메타(댓글/리액션 카운트) 일괄 조회
            meta = get_meta_bulk([t["id"] for t in day_tasks])
            for t in day_tasks:
                m = meta.get(t["id"], {})
                t["meta_comments"] = m.get("comments", 0)
                t["meta_ack"] = m.get("ack", 0)
                t["meta_question"] = m.get("question", 0)
                t["meta_risk"] = m.get("risk", 0)
                t["meta_ok"] = m.get("ok", 0)
                t["meta_last_comment"] = m.get("last_comment", "")
                t["meta_has_activity"] = bool(
                    t["meta_comments"] or t["meta_ack"] or t["meta_question"]
                    or t["meta_risk"] or t["meta_ok"]
                )

        # 팀 전체 통계 (오늘)
        stats_by_user = {}
        for m in members:
            ut = [t for t in day_tasks if t["user_id"] == m["id"]]
            stats_by_user[m["id"]] = {
                "total": len(ut),
                "done": len([t for t in ut if t["status"] == "완료"]),
                "progress": len([t for t in ut if t["status"] == "진행중"]),
                "delay": len([t for t in ut if t["status"] == "지연"]),
                "hours": sum(t["hours"] or 0 for t in ut),
                "reported": 1 if ut else 0,
            }

        team_summary = {
            "members": len(members),
            "reported": sum(1 for s in stats_by_user.values() if s["reported"]),
            "total": len(day_tasks),
            "done": len([t for t in day_tasks if t["status"] == "완료"]),
            "delay": len([t for t in day_tasks if t["status"] == "지연"]),
            "progress": len([t for t in day_tasks if t["status"] == "진행중"]),
            "week_total": len(week_tasks),
            "week_done": len([t for t in week_tasks if t["status"] == "완료"]),
        }

    prev_d = (datetime.strptime(sel_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    next_d = (datetime.strptime(sel_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    return ctx(req, "team.html",
               user=u, teams=teams, target_team_id=target_team_id,
               members=members, day_tasks=day_tasks, stats_by_user=stats_by_user,
               team_summary=team_summary, sel_date=sel_date,
               prev_date=prev_d, next_date=next_d)


# =====================================================
# DASHBOARD — 대표이사 전사 뷰
# 2026-04-26 CEO 통합 대시보드 — /ceo 별칭 추가 (CEO·admin·executive 전용)
# =====================================================
@app.get("/ceo", response_class=HTMLResponse)
async def ceo_dashboard_alias(req: Request):
    """CEO 전용 통합 대시보드 — /dashboard 로 위임 (권한 동일)."""
    return RedirectResponse("/dashboard", 303)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(req: Request):
    # ESC-02: 로그인 상태 구분 — 미인증→/login, 권한 부족→role 홈
    u_any = get_user(req)
    if not u_any:
        return RedirectResponse("/login", 303)
    u = require(req, ["ceo", "admin", "executive"])
    if not u:
        # Plan Y S1 회귀 #1: leader 가 /dashboard 직접 접근 → /team 폴백
        # (이전: role_home 호출 후 leader 도 /dashboard 로 무한 루프 가능성 존재)
        # OPS-P1-G1 [A-008]: 권한 차단 무음 → no_perm 배너 안내
        target = role_home(u_any)
        if target == "/dashboard":
            target = "/home"  # 안전 폴백
        # 폴백 대상에 ?no_perm=dashboard 부착 (이미 쿼리 있으면 & 처리)
        sep = "&" if "?" in target else "?"
        return RedirectResponse(f"{target}{sep}no_perm=dashboard", 303)
    today = date.today()
    mon = (today - timedelta(days=today.weekday())).isoformat()
    sun = (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat()
    today_s = today.isoformat()

    with db_session() as c:
        teams = [dict(r) for r in c.execute(
            """SELECT t.*, u.name AS leader_name, u.rank AS leader_rank
               FROM teams t LEFT JOIN users u ON t.leader_id=u.id
               ORDER BY t.display_order"""
        ).fetchall()]

        for t in teams:
            mc = c.execute(
                "SELECT COUNT(*) FROM users WHERE team_id=? AND is_active=1",
                (t["id"],),
            ).fetchone()[0]
            t["member_count"] = mc
            s = c.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN status='완료' THEN 1 ELSE 0 END) AS done,
                          SUM(CASE WHEN status='진행중' THEN 1 ELSE 0 END) AS progress,
                          SUM(CASE WHEN status='지연' THEN 1 ELSE 0 END) AS delay,
                          COALESCE(SUM(hours),0) AS hours
                   FROM tasks tk JOIN users u ON tk.user_id=u.id
                   WHERE u.team_id=? AND tk.work_date>=? AND tk.work_date<=?""",
                (t["id"], mon, sun),
            ).fetchone()
            t["week_stats"] = {k: (s[k] or 0) for k in s.keys()}
            td = c.execute(
                """SELECT COUNT(*) AS total FROM tasks tk JOIN users u ON tk.user_id=u.id
                   WHERE u.team_id=? AND tk.work_date=?""",
                (t["id"], today_s),
            ).fetchone()
            t["today_count"] = td["total"] or 0
            # 참여율: 오늘 카드 작성자 수 / 팀원 수
            rp = c.execute(
                """SELECT COUNT(DISTINCT tk.user_id) FROM tasks tk JOIN users u ON tk.user_id=u.id
                   WHERE u.team_id=? AND tk.work_date=?""",
                (t["id"], today_s),
            ).fetchone()[0]
            t["reported"] = rp
            t["participation"] = round(rp * 100 / mc) if mc else 0

        total_stats = c.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN status='완료' THEN 1 ELSE 0 END) AS done,
                      SUM(CASE WHEN status='지연' THEN 1 ELSE 0 END) AS delay,
                      SUM(CASE WHEN status='진행중' THEN 1 ELSE 0 END) AS progress,
                      COALESCE(SUM(hours),0) AS hours
               FROM tasks WHERE work_date>=? AND work_date<=?""",
            (mon, sun),
        ).fetchone()
        total_stats = {k: (total_stats[k] or 0) for k in total_stats.keys()}

        total_users = c.execute(
            "SELECT COUNT(*) FROM users WHERE is_active=1 AND role!='admin'"
        ).fetchone()[0]
        today_reporters = c.execute(
            "SELECT COUNT(DISTINCT user_id) FROM tasks WHERE work_date=?",
            (today_s,),
        ).fetchone()[0]
        participation_rate = round(today_reporters * 100 / total_users) if total_users else 0

        delays = [dict(r) for r in c.execute(
            """SELECT t.*, u.name AS user_name, tm.name AS team_name,
                      p.name AS project_name, cu.name AS customer_name
               FROM tasks t JOIN users u ON t.user_id=u.id
               LEFT JOIN teams tm ON u.team_id=tm.id
               LEFT JOIN projects p ON t.project_id=p.id
               LEFT JOIN customers cu ON t.customer_id=cu.id
               WHERE t.status='지연' AND t.work_date>=? AND t.work_date<=?
               ORDER BY t.work_date DESC LIMIT 10""",
            (mon, sun),
        ).fetchall()]

        customers = [dict(r) for r in c.execute(
            """SELECT cu.name AS customer_name, COUNT(*) AS cnt,
                      COALESCE(SUM(t.hours),0) AS hours
               FROM tasks t JOIN customers cu ON t.customer_id=cu.id
               WHERE t.work_date>=? AND t.work_date<=?
               GROUP BY cu.name ORDER BY cnt DESC LIMIT 10""",
            (mon, sun),
        ).fetchall()]

        # 내러티브: 팀별 진행중 핵심 카드 3건씩 + 다음 계획
        narratives = []
        for t in teams:
            cards = [dict(r) for r in c.execute(
                """SELECT t.title, t.status, t.next_plan, u.name AS user_name, u.rank,
                          p.name AS project_name
                   FROM tasks t JOIN users u ON t.user_id=u.id
                   LEFT JOIN projects p ON t.project_id=p.id
                   WHERE u.team_id=? AND t.work_date=?
                     AND t.status IN ('진행중','지연')
                   ORDER BY CASE t.status WHEN '지연' THEN 0 ELSE 1 END, t.id
                   LIMIT 3""",
                (t["id"], today_s),
            ).fetchall()]
            if cards:
                narratives.append({"team": t, "cards": cards})

    # 2026-04-26 CEO 통합 대시보드 — 9 KPI + 알림 + 빠른 액션
    ceo_kpis = ceo_dashboard_kpis(user_id=u["id"])
    with db_session() as c:
        unread_notifs = [dict(r) for r in c.execute(
            "SELECT id, kind, title, body, link, created_at "
            "FROM notifications WHERE user_id=? AND is_read=0 "
            "ORDER BY created_at DESC LIMIT 5",
            (u["id"],),
        ).fetchall()]

    # 2026-04-27 사이클53 — 안전재고 알림 위젯 (6번째 패널)
    # recommend_reorders(limit=5) 직접 호출 → safety_top5 컨텍스트 전달
    from .database import recommend_reorders as _ceo_recommend_reorders
    try:
        safety_top5 = _ceo_recommend_reorders(limit=5) or []
    except Exception:
        safety_top5 = []

    return ctx(req, "dashboard.html",
               user=u, teams=teams, total_stats=total_stats,
               mon=mon, sun=sun, today_s=today_s,
               participation_rate=participation_rate,
               today_reporters=today_reporters, total_users=total_users,
               delays=delays, customers=customers, narratives=narratives,
               ceo_kpis=ceo_kpis, unread_notifs=unread_notifs,
               safety_top5=safety_top5)


# =====================================================
# TEAM DAILY SUMMARY — 팀장 "오늘의 한 줄"
# =====================================================
@app.post("/api/team-summary")
async def api_team_summary(req: Request):
    u = require(req, ["leader", "executive", "ceo", "admin"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    d = await req.json()
    tid = d.get("team_id") or u.get("team_id")
    wdate = d.get("work_date") or date.today().isoformat()
    headline = (d.get("headline") or "").strip()
    notes = d.get("notes") or ""
    if not headline or not tid:
        return JSONResponse({"error": "내용/팀 필수"}, 400)
    with db_session() as c:
        ex = c.execute(
            "SELECT id FROM team_summaries WHERE team_id=? AND work_date=?",
            (tid, wdate),
        ).fetchone()
        if ex:
            c.execute(
                """UPDATE team_summaries SET headline=?, notes=?, author_id=?,
                       updated_at=datetime('now','localtime') WHERE id=?""",
                (headline, notes, u["id"], ex["id"]),
            )
        else:
            c.execute(
                """INSERT INTO team_summaries(team_id, work_date, author_id, headline, notes)
                   VALUES(?,?,?,?,?)""",
                (tid, wdate, u["id"], headline, notes),
            )
    return JSONResponse({"ok": True})


# =====================================================
# WEEKLY — 주간 자동 요약
# =====================================================
@app.get("/weekly", response_class=HTMLResponse)
@app.get("/weekly/{wk_mon}", response_class=HTMLResponse)
async def weekly_page(req: Request, wk_mon: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if not wk_mon:
        td = date.today()
        wk_mon = (td - timedelta(days=td.weekday())).isoformat()
    mon = datetime.strptime(wk_mon, "%Y-%m-%d").date()
    sun = mon + timedelta(days=6)
    prev_mon = (mon - timedelta(days=7)).isoformat()
    next_mon = (mon + timedelta(days=7)).isoformat()

    with db_session() as c:
        # 개인 요약
        my_tasks = [dict(r) for r in c.execute(
            """SELECT t.*, p.name AS project_name, cu.name AS customer_name
               FROM tasks t LEFT JOIN projects p ON t.project_id=p.id
               LEFT JOIN customers cu ON t.customer_id=cu.id
               WHERE t.user_id=? AND t.work_date>=? AND t.work_date<=?
               ORDER BY t.work_date, t.id""",
            (u["id"], mon.isoformat(), sun.isoformat()),
        ).fetchall()]
        # 주간보고 2차 — KPI 8개 (오버타임/정시완료율 포함)
        _hours_total = sum(t["hours"] or 0 for t in my_tasks)
        _done_cnt = sum(1 for t in my_tasks if t["status"] == "완료")
        _overtime = max(0.0, _hours_total - 40.0)  # 주 40h 초과분
        _on_time_rate = round((_done_cnt / len(my_tasks) * 100), 0) if my_tasks else 0
        my_stats = {
            "total": len(my_tasks),
            "done": _done_cnt,
            "progress": sum(1 for t in my_tasks if t["status"] == "진행중"),
            "delay": sum(1 for t in my_tasks if t["status"] == "지연"),
            "hours": round(_hours_total, 1),
            "overtime": round(_overtime, 1),
            "on_time_rate": int(_on_time_rate),
        }
        # 분류별
        my_by_cat = {}
        for t in my_tasks:
            k = t["category"] or "기타"
            my_by_cat.setdefault(k, {"cnt": 0, "hours": 0})
            my_by_cat[k]["cnt"] += 1
            my_by_cat[k]["hours"] += t["hours"] or 0

        # 팀 요약 (팀장/임원/CEO/admin만)
        team_data = None
        if u["role"] in ("leader", "executive", "ceo", "admin"):
            tid = req.query_params.get("team_id")
            if u["role"] in ("leader", "executive"):
                tid = u["team_id"]
            elif tid:
                tid = int(tid)
            if tid:
                t_row = c.execute("SELECT * FROM teams WHERE id=?", (tid,)).fetchone()
                members = [dict(r) for r in c.execute(
                    "SELECT id, name, rank FROM users WHERE team_id=? AND is_active=1", (tid,)
                ).fetchall()]
                mids = [m["id"] for m in members]
                t_tasks = []
                if mids:
                    ph = ",".join("?" * len(mids))
                    t_tasks = [dict(r) for r in c.execute(
                        f"""SELECT tk.*, u.name AS user_name, p.name AS project_name,
                                  cu.name AS customer_name
                           FROM tasks tk JOIN users u ON tk.user_id=u.id
                           LEFT JOIN projects p ON tk.project_id=p.id
                           LEFT JOIN customers cu ON tk.customer_id=cu.id
                           WHERE tk.user_id IN ({ph}) AND tk.work_date>=? AND tk.work_date<=?
                           ORDER BY u.id, tk.work_date""",
                        mids + [mon.isoformat(), sun.isoformat()],
                    ).fetchall()]
                # 팀원별 집계
                per_user = {}
                for m in members:
                    per_user[m["id"]] = {"name": m["name"], "rank": m["rank"],
                                          "total": 0, "done": 0, "hours": 0, "tasks": []}
                for t in t_tasks:
                    per_user.setdefault(t["user_id"], {"name": t["user_name"], "rank": "",
                                                        "total": 0, "done": 0, "hours": 0, "tasks": []})
                    per_user[t["user_id"]]["total"] += 1
                    if t["status"] == "완료":
                        per_user[t["user_id"]]["done"] += 1
                    per_user[t["user_id"]]["hours"] += t["hours"] or 0
                    per_user[t["user_id"]]["tasks"].append(t)
                # 프로젝트별
                pj_agg = {}
                for t in t_tasks:
                    k = t["project_name"] or "(기타)"
                    pj_agg.setdefault(k, {"cnt": 0, "hours": 0, "done": 0})
                    pj_agg[k]["cnt"] += 1
                    pj_agg[k]["hours"] += t["hours"] or 0
                    if t["status"] == "완료":
                        pj_agg[k]["done"] += 1
                # 고객사별
                cu_agg = {}
                for t in t_tasks:
                    k = t["customer_name"] or "(기타)"
                    cu_agg.setdefault(k, {"cnt": 0, "hours": 0})
                    cu_agg[k]["cnt"] += 1
                    cu_agg[k]["hours"] += t["hours"] or 0
                team_data = {
                    "team": dict(t_row),
                    "members": members,
                    "per_user": per_user,
                    "pj_agg": sorted(pj_agg.items(), key=lambda x: -x[1]["cnt"])[:15],
                    "cu_agg": sorted(cu_agg.items(), key=lambda x: -x[1]["cnt"])[:15],
                    "total": len(t_tasks),
                    "done": sum(1 for t in t_tasks if t["status"] == "완료"),
                    "delay": sum(1 for t in t_tasks if t["status"] == "지연"),
                    "hours": round(sum(t["hours"] or 0 for t in t_tasks), 1),
                }

        # 전사 요약 (CEO/admin/executive)
        all_data = None
        if u["role"] in ("ceo", "admin", "executive"):
            all_tasks = [dict(r) for r in c.execute(
                """SELECT tk.*, u.name AS user_name, tm.name AS team_name, tm.code AS team_code,
                          p.name AS project_name, cu.name AS customer_name
                   FROM tasks tk JOIN users u ON tk.user_id=u.id
                   LEFT JOIN teams tm ON u.team_id=tm.id
                   LEFT JOIN projects p ON tk.project_id=p.id
                   LEFT JOIN customers cu ON tk.customer_id=cu.id
                   WHERE tk.work_date>=? AND tk.work_date<=?""",
                (mon.isoformat(), sun.isoformat()),
            ).fetchall()]
            by_team = {}
            for t in all_tasks:
                k = t["team_name"] or "(미배정)"
                by_team.setdefault(k, {"code": t["team_code"], "cnt": 0, "done": 0, "hours": 0})
                by_team[k]["cnt"] += 1
                if t["status"] == "완료":
                    by_team[k]["done"] += 1
                by_team[k]["hours"] += t["hours"] or 0
            by_cust = {}
            for t in all_tasks:
                if not t["customer_name"]:
                    continue
                by_cust.setdefault(t["customer_name"], {"cnt": 0, "hours": 0})
                by_cust[t["customer_name"]]["cnt"] += 1
                by_cust[t["customer_name"]]["hours"] += t["hours"] or 0
            all_data = {
                "total": len(all_tasks),
                "done": sum(1 for t in all_tasks if t["status"] == "완료"),
                "delay": sum(1 for t in all_tasks if t["status"] == "지연"),
                "hours": round(sum(t["hours"] or 0 for t in all_tasks), 1),
                "by_team": sorted(by_team.items(), key=lambda x: -x[1]["cnt"]),
                "by_cust": sorted(by_cust.items(), key=lambda x: -x[1]["cnt"])[:10],
            }

        teams_all = [dict(r) for r in c.execute(
            "SELECT * FROM teams ORDER BY display_order"
        ).fetchall()]

        # 갭서베이 Top10 #5 — 개인 8주 트렌드 (주간보고 2차 — 4→8주 확장 · VIEW 자동 집계)
        my_trend = []
        for i in range(7, -1, -1):
            wk_s = (mon - timedelta(days=7 * i)).isoformat()
            row = c.execute(
                """SELECT total_tasks, completed, in_progress, delayed, total_hours
                   FROM weekly_summary
                   WHERE user_id=? AND week_start=?""",
                (u["id"], wk_s),
            ).fetchone()
            if row:
                my_trend.append({
                    "week_start": wk_s,
                    "total": row["total_tasks"],
                    "done": row["completed"],
                    "progress": row["in_progress"],
                    "delay": row["delayed"],
                    "hours": row["total_hours"] or 0,
                })
            else:
                my_trend.append({"week_start": wk_s, "total": 0, "done": 0,
                                 "progress": 0, "delay": 0, "hours": 0})

        # 부서별 비교 (VIEW 자동 집계 · 팀장+ 권한일 때만 의미)
        dept_compare = []
        if u["role"] in ("leader", "executive", "ceo", "admin"):
            dept_compare = [dict(r) for r in c.execute(
                """SELECT tm.id AS team_id, tm.name AS team_name, tm.code AS team_code,
                          COALESCE(SUM(ws.total_tasks), 0)  AS total,
                          COALESCE(SUM(ws.completed), 0)    AS done,
                          COALESCE(SUM(ws.delayed), 0)      AS delay,
                          COALESCE(SUM(ws.total_hours), 0)  AS hours
                   FROM teams tm
                   LEFT JOIN weekly_summary ws
                          ON ws.team_id = tm.id AND ws.week_start = ?
                   GROUP BY tm.id, tm.name, tm.code
                   ORDER BY tm.display_order""",
                (mon.isoformat(),),
            ).fetchall()]

    return ctx(req, "weekly.html",
               user=u, my_tasks=my_tasks, my_stats=my_stats, my_by_cat=my_by_cat,
               team_data=team_data, all_data=all_data,
               my_trend=my_trend, dept_compare=dept_compare,
               wk_mon=mon.isoformat(), wk_sun=sun.isoformat(),
               prev_mon=prev_mon, next_mon=next_mon, teams_all=teams_all,
               active="weekly")


# 팀장 전용 — 부서별 집계 보기 (VIEW 자동 집계)
@app.get("/weekly/team", response_class=HTMLResponse)
async def weekly_team_page(req: Request, wk_mon: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if u["role"] not in ("leader", "executive", "ceo", "admin"):
        return RedirectResponse("/weekly", 303)
    if not wk_mon:
        td = date.today()
        wk_mon = (td - timedelta(days=td.weekday())).isoformat()
    return RedirectResponse(f"/weekly/{wk_mon}?scope=team", 303)


# 경영진 전용 — 전사 집계 보기
@app.get("/weekly/company", response_class=HTMLResponse)
async def weekly_company_page(req: Request, wk_mon: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if u["role"] not in ("ceo", "admin", "executive"):
        return RedirectResponse("/weekly", 303)
    if not wk_mon:
        td = date.today()
        wk_mon = (td - timedelta(days=td.weekday())).isoformat()
    return RedirectResponse(f"/weekly/{wk_mon}?scope=company", 303)


# 수동 재집계 트리거 (VIEW 기반이라 SQLite 의 ANALYZE 만 호출 — 캐시 갱신용)
@app.post("/weekly/refresh")
async def weekly_refresh(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "auth"}, 401)
    with db_session() as c:
        try:
            c.execute("ANALYZE weekly_summary")
        except Exception:
            pass
    # OPS-P1-A7 [D-017]: 클라이언트 캐시 무효화 헤더
    return JSONResponse(
        {"ok": True, "msg": "재집계 완료"},
        headers={"Cache-Control": "no-cache, no-store, must-revalidate",
                 "Pragma": "no-cache", "Expires": "0"},
    )


# 주간보고 2차 — 마감 알림 (토 18시 발동 가정)
@app.post("/weekly/notify")
async def weekly_notify(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "auth"}, 401)
    td = date.today()
    wk_mon = (td - timedelta(days=td.weekday())).isoformat()
    sun = (td - timedelta(days=td.weekday()) + timedelta(days=6)).isoformat()
    sent = 0
    with db_session() as c:
        # 본인 + 부서장 두 사람에게 INSERT
        targets = [u["id"]]
        if u.get("team_id"):
            row = c.execute("SELECT leader_id FROM teams WHERE id=?", (u["team_id"],)).fetchone()
            if row and row["leader_id"] and row["leader_id"] != u["id"]:
                targets.append(row["leader_id"])
    # 알림시스템 통합 (사이클 2026-04-26) — notify_user 단일 헬퍼 사용 (1시간 중복 방지 내장)
    for uid in targets:
        if notify_user(
            uid, "WEEKLY",
            f"📊 주간보고 마감 임박 ({wk_mon}~{sun})",
            body=wk_mon, link=f"/weekly/{wk_mon}",
        ):
            sent += 1
    return JSONResponse({"ok": True, "sent": sent, "wk_mon": wk_mon})


# 주간보고 2차 — CSV 다운로드 (csv 모듈만 · 외부 라이브러리 0)
@app.get("/weekly/export.csv")
async def weekly_export_csv(req: Request, wk_mon: str = "", scope: str = "me"):
    import csv as _csv
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if not wk_mon:
        td = date.today()
        wk_mon = (td - timedelta(days=td.weekday())).isoformat()
    mon = datetime.strptime(wk_mon, "%Y-%m-%d").date()
    sun = mon + timedelta(days=6)

    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM (엑셀 한글 호환)
    w = _csv.writer(buf)
    w.writerow(["일자", "이름", "팀", "제목", "분류", "프로젝트", "고객사", "상태", "공수"])
    with db_session() as c:
        if scope == "team" and u["role"] in ("leader", "executive", "ceo", "admin"):
            tid = u["team_id"]
            rows = c.execute(
                """SELECT t.work_date, u.name AS uname, tm.name AS tname,
                          t.title, t.category, p.name AS pname, cu.name AS cname,
                          t.status, t.hours
                   FROM tasks t JOIN users u ON t.user_id=u.id
                   LEFT JOIN teams tm ON u.team_id=tm.id
                   LEFT JOIN projects p ON t.project_id=p.id
                   LEFT JOIN customers cu ON t.customer_id=cu.id
                   WHERE u.team_id=? AND t.work_date>=? AND t.work_date<=?
                   ORDER BY t.work_date, u.name""",
                (tid, mon.isoformat(), sun.isoformat())
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT t.work_date, u.name AS uname, tm.name AS tname,
                          t.title, t.category, p.name AS pname, cu.name AS cname,
                          t.status, t.hours
                   FROM tasks t JOIN users u ON t.user_id=u.id
                   LEFT JOIN teams tm ON u.team_id=tm.id
                   LEFT JOIN projects p ON t.project_id=p.id
                   LEFT JOIN customers cu ON t.customer_id=cu.id
                   WHERE t.user_id=? AND t.work_date>=? AND t.work_date<=?
                   ORDER BY t.work_date""",
                (u["id"], mon.isoformat(), sun.isoformat())
            ).fetchall()
        for r in rows:
            w.writerow([r["work_date"], r["uname"], r["tname"] or "",
                        r["title"], r["category"] or "", r["pname"] or "",
                        r["cname"] or "", r["status"], r["hours"] or 0])
    fn = f"weekly_{scope}_{wk_mon}.csv"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={fn}"}
    )


# 주간보고 2차 — 두 주 비교 (선택)
@app.get("/weekly/compare/{wk1}/{wk2}", response_class=HTMLResponse)
async def weekly_compare(req: Request, wk1: str, wk2: str):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        def _agg(wk):
            row = c.execute(
                """SELECT total_tasks, completed, in_progress, delayed, total_hours
                   FROM weekly_summary
                   WHERE user_id=? AND week_start=?""",
                (u["id"], wk)
            ).fetchone()
            if row:
                return {"wk": wk, "total": row["total_tasks"], "done": row["completed"],
                        "progress": row["in_progress"], "delay": row["delayed"],
                        "hours": row["total_hours"] or 0}
            return {"wk": wk, "total": 0, "done": 0, "progress": 0, "delay": 0, "hours": 0}
        a, b = _agg(wk1), _agg(wk2)
    diff = {
        "total": b["total"] - a["total"],
        "done": b["done"] - a["done"],
        "delay": b["delay"] - a["delay"],
        "hours": round(b["hours"] - a["hours"], 1),
    }
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>주간 비교 {wk1} vs {wk2}</title>
<style>body{{font-family:'맑은 고딕',sans-serif;padding:24px;color:#333}}
table{{border-collapse:collapse;margin-top:12px}}th,td{{padding:8px 14px;border:1px solid #d0d0d0}}
th{{background:#A5282C;color:#fff}}.dn{{color:#16a34a}}.up{{color:#dc2626}}</style></head>
<body><h1>주간 비교 — {u['name']}</h1>
<p>{wk1} → {wk2}</p>
<table><tr><th>항목</th><th>{wk1}</th><th>{wk2}</th><th>차이</th></tr>
<tr><td>총 카드</td><td>{a['total']}</td><td>{b['total']}</td><td class="{'up' if diff['total']>0 else 'dn'}">{diff['total']:+d}</td></tr>
<tr><td>완료</td><td>{a['done']}</td><td>{b['done']}</td><td class="{'up' if diff['done']>0 else 'dn'}">{diff['done']:+d}</td></tr>
<tr><td>지연</td><td>{a['delay']}</td><td>{b['delay']}</td><td class="{'dn' if diff['delay']<0 else 'up'}">{diff['delay']:+d}</td></tr>
<tr><td>공수(h)</td><td>{a['hours']:.1f}</td><td>{b['hours']:.1f}</td><td>{diff['hours']:+.1f}</td></tr>
</table>
<p><a href="/weekly">← 주간 요약</a></p></body></html>"""
    return HTMLResponse(html)


# =====================================================
# PROJECT DETAIL
# =====================================================
@app.get("/project/{pid}", response_class=HTMLResponse)
async def project_detail(req: Request, pid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        p = c.execute(
            """SELECT p.*, cu.name AS customer_name FROM projects p
               LEFT JOIN customers cu ON p.customer_id=cu.id WHERE p.id=?""",
            (pid,),
        ).fetchone()
        if not p:
            return RedirectResponse("/", 303)
        p = dict(p)
        # 참여 전체 카드
        tasks = [dict(r) for r in c.execute(
            """SELECT tk.*, u.name AS user_name, u.rank AS user_rank,
                      tm.name AS team_name, tm.code AS team_code
               FROM tasks tk JOIN users u ON tk.user_id=u.id
               LEFT JOIN teams tm ON u.team_id=tm.id
               WHERE tk.project_id=? ORDER BY tk.work_date DESC, tk.id DESC""",
            (pid,),
        ).fetchall()]
        stats = {
            "total": len(tasks),
            "done": sum(1 for t in tasks if t["status"] == "완료"),
            "progress": sum(1 for t in tasks if t["status"] == "진행중"),
            "delay": sum(1 for t in tasks if t["status"] == "지연"),
            "hours": round(sum(t["hours"] or 0 for t in tasks), 1),
        }
        # 팀별 집계
        by_team = {}
        for t in tasks:
            k = t["team_name"] or "(미배정)"
            by_team.setdefault(k, {"cnt": 0, "hours": 0, "members": set()})
            by_team[k]["cnt"] += 1
            by_team[k]["hours"] += t["hours"] or 0
            by_team[k]["members"].add(t["user_name"])
        by_team_list = [(k, {"cnt": v["cnt"], "hours": v["hours"], "members": sorted(v["members"])})
                        for k, v in sorted(by_team.items(), key=lambda x: -x[1]["cnt"])]
        # 참여자 개별
        by_user = {}
        for t in tasks:
            k = f"{t['user_name']} ({t['team_name'] or '-'})"
            by_user.setdefault(k, {"cnt": 0, "hours": 0, "last": None})
            by_user[k]["cnt"] += 1
            by_user[k]["hours"] += t["hours"] or 0
            if not by_user[k]["last"] or t["work_date"] > by_user[k]["last"]:
                by_user[k]["last"] = t["work_date"]
        by_user_list = sorted(by_user.items(), key=lambda x: -x[1]["cnt"])[:20]

        # 타임라인용 — 일자별 그룹화
        timeline = {}
        for t in tasks:
            timeline.setdefault(t["work_date"], []).append(t)
        timeline_list = sorted(timeline.items(), reverse=True)
        # 댓글 통합
        all_comments = [dict(r) for r in c.execute(
            """SELECT tc.*, u.name AS author_name, u.rank AS author_rank,
                      tk.title AS task_title, tk.id AS tid
               FROM task_comments tc
               JOIN tasks tk ON tc.task_id=tk.id
               JOIN users u ON tc.author_id=u.id
               WHERE tk.project_id=? ORDER BY tc.created_at DESC LIMIT 30""",
            (pid,)
        ).fetchall()]
    retro = get_retro(pid)
    return ctx(req, "project_detail.html",
               user=u, p=p, tasks=tasks[:50], stats=stats,
               by_team=by_team_list, by_user=by_user_list, total_tasks=len(tasks),
               timeline=timeline_list[:30], all_comments=all_comments, retro=retro)


# =====================================================
# CUSTOMER LIST (2026-04-28 신설 — 사이드바 /customers 링크 broken 수정)
# =====================================================
@app.get("/customers", response_class=HTMLResponse)
async def customers_list(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        try:
            rows = c.execute(
                """SELECT cu.id, cu.name, cu.tier, cu.note,
                          COUNT(DISTINCT p.id) AS proj_count,
                          COALESCE(SUM(p.order_amount), 0) AS total_amount,
                          MAX(p.order_date) AS last_order
                   FROM customers cu
                   LEFT JOIN projects p ON p.customer_id = cu.id
                   GROUP BY cu.id
                   ORDER BY total_amount DESC, cu.tier DESC, cu.name"""
            ).fetchall()
            customers = [dict(r) for r in rows]
        except Exception:
            customers = [dict(r) for r in c.execute(
                "SELECT id, name, tier, note FROM customers ORDER BY tier DESC, name"
            ).fetchall()]
    return ctx(req, "customers_list.html", user=u, active="customers", customers=customers)


# =====================================================
# CUSTOMER DETAIL
# =====================================================
@app.get("/customer/{cid}", response_class=HTMLResponse)
async def customer_detail(req: Request, cid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        cu = c.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
        if not cu:
            return RedirectResponse("/", 303)
        cu = dict(cu)
        # 고객사 프로젝트
        pjts = [dict(r) for r in c.execute(
            "SELECT * FROM projects WHERE customer_id=? ORDER BY id DESC", (cid,),
        ).fetchall()]
        # 최근 2주 카드
        since = (date.today() - timedelta(days=30)).isoformat()
        tasks = [dict(r) for r in c.execute(
            """SELECT tk.*, u.name AS user_name, tm.name AS team_name, p.name AS project_name
               FROM tasks tk JOIN users u ON tk.user_id=u.id
               LEFT JOIN teams tm ON u.team_id=tm.id
               LEFT JOIN projects p ON tk.project_id=p.id
               WHERE tk.customer_id=? AND tk.work_date>=? ORDER BY tk.work_date DESC""",
            (cid, since),
        ).fetchall()]
        stats = {
            "total": len(tasks),
            "done": sum(1 for t in tasks if t["status"] == "완료"),
            "delay": sum(1 for t in tasks if t["status"] == "지연"),
            "hours": round(sum(t["hours"] or 0 for t in tasks), 1),
        }
        by_team = {}
        for t in tasks:
            k = t["team_name"] or "(미배정)"
            by_team.setdefault(k, {"cnt": 0, "hours": 0})
            by_team[k]["cnt"] += 1
            by_team[k]["hours"] += t["hours"] or 0
        by_team_list = sorted(by_team.items(), key=lambda x: -x[1]["cnt"])

    return ctx(req, "customer_detail.html",
               user=u, cu=cu, pjts=pjts, tasks=tasks[:80],
               stats=stats, by_team=by_team_list, total_tasks=len(tasks))


# =====================================================
# CALENDAR (개인 월간 뷰)
# =====================================================
@app.get("/calendar", response_class=HTMLResponse)
@app.get("/calendar/{month}", response_class=HTMLResponse)
async def calendar_page(req: Request, month: str = "", scope: str = "me"):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if not month:
        month = date.today().strftime("%Y-%m")
    # 리더 이상이 아니면 me로 강제
    if scope == "team" and u["role"] not in ("leader", "executive", "ceo", "admin"):
        scope = "me"
    y, m = int(month[:4]), int(month[5:7])
    with db_session() as c:
        if scope == "team" and u.get("team_id"):
            rows = [dict(r) for r in c.execute(
                """SELECT work_date, status, COUNT(*) AS cnt, COALESCE(SUM(hours),0) AS hours
                   FROM tasks t JOIN users u ON t.user_id=u.id
                   WHERE u.team_id=? AND work_date LIKE ?
                   GROUP BY work_date, status""",
                (u["team_id"], f"{month}%"),
            ).fetchall()]
        else:
            rows = [dict(r) for r in c.execute(
                """SELECT work_date, status, COUNT(*) AS cnt, COALESCE(SUM(hours),0) AS hours
                   FROM tasks WHERE user_id=? AND work_date LIKE ?
                   GROUP BY work_date, status""",
                (u["id"], f"{month}%"),
            ).fetchall()]
    by_date = {}
    for r in rows:
        by_date.setdefault(r["work_date"], {"total": 0, "done": 0, "progress": 0,
                                              "delay": 0, "hours": 0})
        by_date[r["work_date"]]["total"] += r["cnt"]
        by_date[r["work_date"]]["hours"] += r["hours"]
        if r["status"] == "완료":
            by_date[r["work_date"]]["done"] += r["cnt"]
        elif r["status"] == "진행중":
            by_date[r["work_date"]]["progress"] += r["cnt"]
        elif r["status"] == "지연":
            by_date[r["work_date"]]["delay"] += r["cnt"]

    first_wd, ndays = calendar.monthrange(y, m)
    weeks = []
    day = 1 - first_wd
    for _ in range(6):
        week = []
        for wd in range(7):
            if day < 1 or day > ndays:
                week.append({"day": 0, "date": "", "d": None, "is_today": False, "wd": wd})
            else:
                ds = f"{y}-{m:02d}-{day:02d}"
                week.append({
                    "day": day, "date": ds, "d": by_date.get(ds),
                    "is_today": ds == date.today().isoformat(), "wd": wd,
                })
            day += 1
        if any(c["day"] > 0 for c in week):
            weeks.append(week)

    prev_m = f"{y-1 if m==1 else y}-{12 if m==1 else m-1:02d}"
    next_m = f"{y+1 if m==12 else y}-{1 if m==12 else m+1:02d}"
    month_total = sum(d["total"] for d in by_date.values())
    month_done = sum(d["done"] for d in by_date.values())
    month_hours = round(sum(d["hours"] for d in by_date.values()), 1)

    return ctx(req, "calendar.html",
               user=u, weeks=weeks, month=month, prev_m=prev_m, next_m=next_m,
               month_total=month_total, month_done=month_done, month_hours=month_hours,
               scope=scope, can_team=u["role"] in ("leader","executive","ceo","admin") and u.get("team_id") is not None,
               active="calendar")


# =====================================================
# FEED (부서간 오늘 피드)
# =====================================================
@app.get("/feed", response_class=HTMLResponse)
@app.get("/feed/{sel_date}", response_class=HTMLResponse)
async def feed_page(req: Request, sel_date: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if not sel_date:
        sel_date = date.today().isoformat()
    with db_session() as c:
        # 팀별 오늘 한 줄 요약
        summaries = [dict(r) for r in c.execute(
            """SELECT ts.*, t.name AS team_name, t.code AS team_code, t.is_lab,
                      u.name AS author_name
               FROM team_summaries ts JOIN teams t ON ts.team_id=t.id
               LEFT JOIN users u ON ts.author_id=u.id
               WHERE ts.work_date=? ORDER BY t.display_order""",
            (sel_date,),
        ).fetchall()]
        # 전 팀 오늘 카드 (요약)
        tasks = [dict(r) for r in c.execute(
            """SELECT tk.*, u.name AS user_name, u.rank AS user_rank, u.team_id AS team_id,
                      t.name AS team_name, t.code AS team_code,
                      p.name AS project_name, cu.name AS customer_name
               FROM tasks tk JOIN users u ON tk.user_id=u.id
               LEFT JOIN teams t ON u.team_id=t.id
               LEFT JOIN projects p ON tk.project_id=p.id
               LEFT JOIN customers cu ON tk.customer_id=cu.id
               WHERE tk.work_date=? ORDER BY t.display_order, u.id, tk.id""",
            (sel_date,),
        ).fetchall()]
        # 메타데이터(댓글수+리액션수) 일괄 조회 → 카드 표면 배지로 표시
        meta = get_meta_bulk([t["id"] for t in tasks])
        # 현재 사용자 멘션/응답대기 카운트 (나를 @멘션한 댓글이 달린 카드)
        mentioned_ids = set()
        if tasks:
            ph = ",".join("?" * len(tasks))
            mrows = c.execute(
                f"""SELECT DISTINCT tc.task_id
                    FROM comment_mentions cm
                    JOIN task_comments tc ON cm.comment_id=tc.id
                    WHERE cm.user_id=? AND tc.task_id IN ({ph})""",
                (u["id"],) + tuple(t["id"] for t in tasks)
            ).fetchall()
            mentioned_ids = {r["task_id"] for r in mrows}
        for t in tasks:
            m = meta.get(t["id"], {})
            t["meta_comments"] = m.get("comments", 0)
            t["meta_ack"] = m.get("ack", 0)
            t["meta_question"] = m.get("question", 0)
            t["meta_risk"] = m.get("risk", 0)
            t["meta_ok"] = m.get("ok", 0)
            t["meta_last_comment"] = m.get("last_comment", "")
            t["meta_mentioned_me"] = 1 if t["id"] in mentioned_ids else 0
            t["meta_has_activity"] = bool(
                t["meta_comments"] or t["meta_ack"] or t["meta_question"]
                or t["meta_risk"] or t["meta_ok"]
            )
            # 정렬 키: 지연(0) → 리스크(1) → 멘션(2) → 활동(3) → 진행중(4) → 대기(5) → 완료(6)
            if t["status"] == "지연":
                sk = 0
            elif t["meta_risk"]:
                sk = 1
            elif t["meta_mentioned_me"]:
                sk = 2
            elif t["meta_has_activity"]:
                sk = 3
            elif t["status"] == "진행중":
                sk = 4
            elif t["status"] in ("대기", "보류"):
                sk = 5
            else:
                sk = 6
            t["_sort"] = sk

        by_team = {}
        for t in tasks:
            k = t["team_name"] or "(미배정)"
            by_team.setdefault(k, {"code": t["team_code"], "tasks": [],
                                    "has_urgent": False})
            by_team[k]["tasks"].append(t)
            if t["_sort"] <= 2:  # 지연/리스크/멘션 중 하나라도 있으면 긴급팀
                by_team[k]["has_urgent"] = True
        # 각 팀 내부 정렬: 우선순위 → 담당자 → id
        for k, d in by_team.items():
            d["tasks"].sort(key=lambda x: (x["_sort"], x.get("user_name") or "", x["id"]))
        by_team_list = sorted(by_team.items(), key=lambda x: x[1]["code"] or "99")

        # 전체 카운트 (필터칩용)
        all_total = len(tasks)
        all_done = sum(1 for t in tasks if t["status"] == "완료")
        all_progress = sum(1 for t in tasks if t["status"] == "진행중")
        all_delay = sum(1 for t in tasks if t["status"] == "지연")
        all_wait = sum(1 for t in tasks if t["status"] in ("대기", "보류"))
        all_risk = sum(1 for t in tasks if t["meta_risk"])
        all_mentioned = sum(1 for t in tasks if t["meta_mentioned_me"])
    prev_d = (datetime.strptime(sel_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    next_d = (datetime.strptime(sel_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    # 멀티뷰용 flat JSON (칸반/캘린더)
    import json as _json
    flat_tasks = _json.dumps([{
        "id": t["id"], "title": t["title"], "status": t["status"],
        "user_name": t["user_name"], "user_rank": t.get("user_rank") or "",
        "team_name": t.get("team_name") or "", "project_name": t.get("project_name") or "",
        "customer_name": t.get("customer_name") or "",
        "hours": t.get("hours") or 0,
        "cm": t.get("meta_comments", 0), "risk": t.get("meta_risk", 0),
        "question": t.get("meta_question", 0), "ack": t.get("meta_ack", 0),
    } for t in tasks], ensure_ascii=False)
    # 역할 기반 기본 펼침 로직용 — 내 팀 id
    my_team_id = u.get("team_id")
    return ctx(req, "feed.html",
               user=u, summaries=summaries, by_team=by_team_list,
               sel_date=sel_date, prev_date=prev_d, next_date=next_d,
               all_total=all_total, all_done=all_done, all_progress=all_progress,
               all_delay=all_delay, all_wait=all_wait,
               all_risk=all_risk, all_mentioned=all_mentioned,
               my_team_id=my_team_id, flat_tasks_json=flat_tasks,
               sel_date_obj=sel_date, active="feed")


# =====================================================
# ADMIN — 관리자 페이지
# =====================================================
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        teams = [dict(r) for r in c.execute(
            """SELECT t.*, u.name AS leader_name,
                      (SELECT COUNT(*) FROM users WHERE team_id=t.id AND is_active=1) AS member_count
               FROM teams t LEFT JOIN users u ON t.leader_id=u.id
               ORDER BY t.display_order"""
        ).fetchall()]
        users = [dict(r) for r in c.execute(
            """SELECT u.*, t.name AS team_name FROM users u
               LEFT JOIN teams t ON u.team_id=t.id
               WHERE u.role!='admin' ORDER BY t.display_order, u.role DESC, u.id"""
        ).fetchall()]
        projects = [dict(r) for r in c.execute(
            """SELECT p.*, cu.name AS customer_name FROM projects p
               LEFT JOIN customers cu ON p.customer_id=cu.id ORDER BY p.id DESC"""
        ).fetchall()]
        customers = [dict(r) for r in c.execute("SELECT * FROM customers ORDER BY tier DESC, id").fetchall()]
    return ctx(req, "admin.html",
               user=u, teams=teams, users=users, projects=projects, customers=customers,
               active="admin")


@app.post("/api/admin/user")
async def api_admin_user(req: Request):
    u = require(req, ["admin"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    d = await req.json()
    with db_session() as c:
        if d.get("id"):
            c.execute(
                "UPDATE users SET name=?, team_id=?, rank=?, role=?, is_active=? WHERE id=?",
                (d["name"], d.get("team_id") or None, d.get("rank", ""),
                 d.get("role", "member"), int(d.get("is_active", 1)), d["id"]),
            )
            if d.get("password"):
                c.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(d["password"]), d["id"]))
        else:
            c.execute(
                """INSERT INTO users(name, login_id, password, team_id, rank, role)
                   VALUES(?,?,?,?,?,?)""",
                (d["name"], d["login_id"], hash_pw(d.get("password", "knk1234")),
                 d.get("team_id") or None, d.get("rank", ""), d.get("role", "member")),
            )
    return JSONResponse({"ok": True})


@app.post("/api/admin/project")
async def api_admin_project(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    d = await req.json()
    with db_session() as c:
        if d.get("id"):
            c.execute(
                "UPDATE projects SET code=?, name=?, customer_id=?, type=?, status=? WHERE id=?",
                (d.get("code", ""), d["name"], d.get("customer_id") or None,
                 d.get("type", ""), d.get("status", "진행중"), d["id"]),
            )
        else:
            c.execute(
                "INSERT INTO projects(code, name, customer_id, type, status) VALUES(?,?,?,?,?)",
                (d.get("code", ""), d["name"], d.get("customer_id") or None,
                 d.get("type", ""), d.get("status", "진행중")),
            )
    return JSONResponse({"ok": True})


@app.post("/api/admin/customer")
async def api_admin_customer(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    d = await req.json()
    with db_session() as c:
        if d.get("id"):
            c.execute(
                "UPDATE customers SET name=?, tier=?, note=? WHERE id=?",
                (d["name"], d.get("tier", "일반"), d.get("note", ""), d["id"]),
            )
        else:
            c.execute(
                "INSERT INTO customers(name, tier, note) VALUES(?,?,?)",
                (d["name"], d.get("tier", "일반"), d.get("note", "")),
            )
    return JSONResponse({"ok": True})


# =====================================================
# MGMT CODE IMPORT — 관리코드발행목록.xls 업로드
# =====================================================
@app.post("/api/admin/import-mgmt")
async def api_admin_import_mgmt(req: Request, file: UploadFile = File(...)):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    fn = (file.filename or "").lower()
    # 사이클 71: pandas 제거(대표 결정 2026-04-27) → .csv 만 허용. .xls/.xlsx는 안내 메시지.
    if fn.endswith(".xls") or fn.endswith(".xlsx"):
        return JSONResponse({"error": (
            ".xls/.xlsx 직접 파싱은 사이클 71(2026-04-27)에서 폐기되었습니다 (외부 의존 0 정책). "
            "Excel/LibreOffice에서 .csv (UTF-8) 로 저장 후 업로드해 주세요."
        )}, 400)
    if not fn.endswith(".csv"):
        return JSONResponse({"error": "csv 파일만 업로드 가능 (.xls/.xlsx 는 .csv 변환 후 업로드)"}, 400)
    try:
        data = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tf:
            tf.write(data)
            tmp_path = tf.name
        try:
            rows = parse_mgmt_csv(tmp_path)
            result = import_mgmt_rows(rows)
            result["parsed"] = len(rows)
            result["filename"] = file.filename
            return JSONResponse({"ok": True, "result": result})
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as e:
        return JSONResponse({"error": f"파싱 실패: {type(e).__name__}: {e}"}, 500)


# =====================================================
# INITIAL PASSWORD REGENERATION (A안 킥오프)
# =====================================================
@app.post("/api/admin/regenerate-passwords")
async def api_regen_pw(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    rows = regenerate_user_passwords()
    out_dir = os.path.join(BASE, "data")
    os.makedirs(out_dir, exist_ok=True)
    # 사이클 68 (2026-04-27): openpyxl 제거 → CSV (UTF-8 BOM · 대표 결정 이행)
    out_path = os.path.join(out_dir, "초기비밀번호_배포용.csv")
    build_password_csv(rows, out_path)
    return JSONResponse({"ok": True, "count": len(rows),
                         "download": "/admin/download-passwords"})


@app.get("/admin/health", response_class=HTMLResponse)
async def admin_health_page(req: Request):
    """건전성 점검 — 어떤 기능이 진짜 동작하는지 한눈에"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    from .database import health_check
    checks = health_check()
    # 레벨별 그룹
    by_level = {"core": [], "data": [], "external": [], "ops": []}
    for c in checks:
        by_level.setdefault(c.get("level", "ops"), []).append(c)
    # 상태별 카운트
    counts = {"ok": 0, "warn": 0, "error": 0, "info": 0}
    for c in checks:
        counts[c.get("status", "info")] += 1
    return ctx(req, "admin_health.html", user=u,
               checks=checks, by_level=by_level, counts=counts,
               active="admin")


# =====================================================
# 사이클 73 (2026-04-27): 사용 가이드 페이지
# 대표 16:20 직접 지시 — "내가 직접 사용해볼려고 하는데 사용 가이드가 있어야할것 같은데"
# 모든 로그인 사용자 접근 가능 (admin/ceo/sales/finance/etc.)
# =====================================================
@app.get("/guide", response_class=HTMLResponse)
async def guide_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    return ctx(req, "guide.html", user=u, active="guide")


# =====================================================
# 외부자산 점검 (대표 직접 판단용 spike, 2026-04-27)
# 출처: 00_HAIST_WORKS_감사팀/_TO_09팀장_2026-04-27_긴급감사_openpyxl외부자산.md
# =====================================================
EXTERNAL_ASSETS_REVIEW = [
    {
        "name": "openpyxl",
        "type": "PyPI 라이브러리 (엑셀 파일 생성)",
        "status": "removed_2026-04-27_cycle68",
        "usage": [
            {"file": "app/main.py", "lines": "(제거됨)",
             "purpose": "사이클 68: 주간 요약 CSV 라우트로 대체 (line 3300~)",
             "deprecated": True},
            {"file": "app/database.py", "lines": "2271~2287",
             "purpose": "사이클 68: build_password_csv 로 교체 (csv 표준 모듈)",
             "deprecated": True},
            {"file": "scripts/migrate_baby_v2.py", "lines": "79",
             "purpose": "baby Excel → web SQLite 마이그레이션 (운영 외 1회성, baby 폐기 시 자연 제거)"},
            {"file": "scripts/baby_web_sync_check.py", "lines": "38",
             "purpose": "baby/web 정합성 체크 (운영 외 스크립트, baby 폐기 시 자연 제거)"},
        ],
        "alternatives": [
            "CSV 다운로드 (csv 표준 모듈) — 사이클 68 적용",
            "HTML 인쇄 view (브라우저 인쇄 기능)",
        ],
        "impact_summary": (
            "사이클 68 (2026-04-27 대표 결정 Remove) 적용 완료. "
            "운영 라우트에서 openpyxl import 0건. "
            "scripts/ 2개 파일은 baby 폐기 시 자연 제거 예정."
        ),
        "risk_security": 1,
        "risk_dependency": 3,
        "introduced_at": "2026-04-15 (commit 546fb23, 초기 구축)",
        "duration": "12일 + 55사이클 누적",
    },
    {
        "name": "pandas",
        "type": "PyPI 라이브러리 (데이터 분석, numpy 의존)",
        "status": "removed_2026-04-27_cycle71",
        "usage": [
            {"file": "app/database.py", "lines": "(제거됨)",
             "purpose": "사이클 71: parse_mgmt_xls는 NotImplementedError 안내, parse_mgmt_csv (csv 표준 모듈) 신설",
             "deprecated": True},
            {"file": "app/main.py", "lines": "(라우트 수정)",
             "purpose": "사이클 71: /api/admin/import-mgmt 가 .csv 만 수용, .xls/.xlsx 업로드는 변환 안내 400",
             "deprecated": True},
        ],
        "alternatives": [
            "외부 환경에서 .xls → .csv 변환 후 csv 표준 모듈로 처리 — 사이클 71 적용",
            "parse_mgmt_csv (database.py) — 표준 csv 모듈 기반 새 헬퍼",
        ],
        "impact_summary": (
            "사이클 71 (2026-04-27 대표 결정 Remove 2회 제출 14:20:25 + 14:22:08) 적용 완료. "
            "pandas import 0건. requirements.txt 도 0건 (이전부터 미명시였음). "
            "관리코드 마이그레이션은 사용자가 .xls → .csv 변환 후 업로드하는 1회성 흐름으로 전환."
        ),
        "risk_security": 1,
        "risk_dependency": 4,
        "introduced_at": "2026-04-15 (commit 546fb23, 초기 구축)",
        "duration": "12일 + 55사이클 누적",
    },
    {
        "name": "deep_translator",
        "type": "PyPI 라이브러리 + 외부 번역 API (Google Translate / MyMemory)",
        "status": "removed_2026-04-27_cycle69",
        "usage": [
            {"file": "app/main.py", "lines": "(제거됨)",
             "purpose": "사이클 69: api_translate() 사내 i18n 사전 lookup으로 교체",
             "deprecated": True},
            {"file": "requirements.txt", "lines": "(제거됨)",
             "purpose": "사이클 69: deep-translator 의존성 제거",
             "deprecated": True},
        ],
        "alternatives": [
            "사내 i18n 사전 lookup (app/i18n.py 약 472키 ko/vi/en) — 사이클 69 적용",
            "빅터AI 단어 등록 기능 (사이클 70+ 신설 예정, 대표 결재 후)",
        ],
        "impact_summary": (
            "사이클 69 (2026-04-27 대표 결정 Partial 부분처리) 적용 완료. "
            "외부 API 호출 0건. "
            "/api/translate 라우트는 i18n.py T 사전 lookup 기반으로 동작 (외부 자산 0)."
        ),
        "risk_security": 4,
        "risk_dependency": 3,
        "introduced_at": "2026-04-15 (commit 546fb23, 초기 구축)",
        "duration": "12일 + 55사이클 누적",
    },
]


@app.get("/admin/external-assets", response_class=HTMLResponse)
async def admin_external_assets(req: Request):
    """외부자산 점검 — 대표 직접 판단 (spike 2026-04-27)"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    saved = req.query_params.get("saved", "")
    return ctx(req, "external_assets_review.html", user=u,
               assets=EXTERNAL_ASSETS_REVIEW,
               saved=saved,
               active="admin")


@app.post("/admin/external-assets/decision")
async def admin_external_assets_decision(req: Request):
    """대표 결정 제출 → 99_DISPATCH 폴더에 결정 .md 자동 추가"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    form = await req.form()
    asset_name = (form.get("asset_name") or "").strip()
    decision = (form.get("decision") or "").strip()
    note = (form.get("note") or "").strip()

    # 입력 화이트리스트 (XSS/주입 방지)
    allowed_assets = {"openpyxl", "pandas", "deep_translator"}
    allowed_decisions = {"remove", "keep", "partial"}
    if asset_name not in allowed_assets or decision not in allowed_decisions:
        return RedirectResponse("/admin/external-assets?saved=err", 303)

    # 99_DISPATCH 폴더에 결정 추가 (append)
    dispatch_dir = os.path.join(BASE, "..", "99_DISPATCH")
    dispatch_dir = os.path.abspath(dispatch_dir)
    try:
        os.makedirs(dispatch_dir, exist_ok=True)
    except Exception:
        pass
    out_path = os.path.join(dispatch_dir, "외부자산_결정_2026-04-27.md")

    decision_label = {"remove": "제거(Remove)", "keep": "유지(Keep)",
                       "partial": "부분 처리(Partial)"}[decision]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 메모는 마크다운 안전을 위해 라인 단위로 정리
    safe_note = "\n".join(("> " + ln) for ln in note.splitlines()) if note else "> (메모 없음)"

    block = (
        f"\n---\n\n"
        f"## {asset_name} — {decision_label}\n\n"
        f"- 결정 시각: {ts}\n"
        f"- 결정자: {u.get('name','?')} (id={u.get('id','?')}, role={u.get('role','?')})\n"
        f"- 자산: `{asset_name}`\n"
        f"- 결정: **{decision_label}**\n"
        f"- 메모:\n{safe_note}\n"
    )
    header_needed = not os.path.exists(out_path)
    try:
        with open(out_path, "a", encoding="utf-8") as f:
            if header_needed:
                f.write(
                    "# 외부자산 점검 — 대표 결정 기록\n\n"
                    "> 자동 생성 (POST /admin/external-assets/decision)\n"
                    "> spike 발주: 2026-04-27 (대표 직접 지시 12:30)\n"
                    "> 본 파일은 09 팀장(빅터)이 모니터링하여 후속 spike 발주\n"
                )
            f.write(block)
    except Exception:
        return RedirectResponse("/admin/external-assets?saved=err", 303)

    return RedirectResponse(
        f"/admin/external-assets?saved={asset_name}", 303)


# =====================================================
# 회사 정보 admin (사이클 61 U6 — 대표가 직접 입력 / 외부자산 0건)
# 출처: 04 _TO_09팀장_2026-04-27_사이클58_UX재검증.md S2 U6
# 저장: app_settings 테이블 (key = "company_*")
# =====================================================
@app.get("/admin/company-info", response_class=HTMLResponse)
async def admin_company_info_page(req: Request):
    """회사 식별 정보 입력 페이지 — 견적서 헤더용 (대표 직접 입력)."""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    # OPS-P0-4: saved 정수화 (문자열 "0" truthy 방지)
    try:
        saved = int(req.query_params.get("saved", "0") or "0")
    except (TypeError, ValueError):
        saved = 0
    # 현재 입력된 값 (default 미적용 raw)
    current = {key: (get_setting(key, "") or "") for key, _l, _d in COMPANY_INFO_KEYS}
    return ctx(req, "admin_company_info.html", user=u,
               keys=COMPANY_INFO_KEYS,
               current=current,
               saved=saved,
               active="admin")


@app.post("/admin/company-info")
async def admin_company_info_save(req: Request):
    """회사 정보 저장 → app_settings UPSERT."""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    form = await req.form()
    # 화이트리스트 (XSS/주입 방지) — 정의된 키만 저장
    allowed_keys = {key for key, _l, _d in COMPANY_INFO_KEYS}
    saved = 0
    for k, v in form.items():
        if not k.startswith("k_"):
            continue
        key = k[2:].strip()
        if key not in allowed_keys:
            continue
        set_setting(key, (v or "").strip(), user_id=u["id"])
        saved += 1
    return RedirectResponse(f"/admin/company-info?saved={saved}", 303)


@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    settings = get_settings_all()
    return ctx(req, "admin_settings.html", user=u, settings=settings, active="admin")


@app.post("/admin/settings")
async def admin_settings_save(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    form = await req.form()
    # form 키는 "k_<key>" 형식 (XSS/주입 방지)
    saved = 0
    for k, v in form.items():
        if not k.startswith("k_"):
            continue
        key = k[2:].strip()
        if not key:
            continue
        set_setting(key, (v or "").strip(), user_id=u["id"])
        saved += 1
    return RedirectResponse(f"/admin/settings?saved={saved}", 303)


# =====================================================
# 사이클 79 (DEC-2 · 2026-04-27) — 인사총무 하이웍스 연동 카드
# 인사총무 업무는 하이웍스 외부 시스템 사용. HAIST WORKS는 연동 카드 + 외부 링크 + 본인 KNK 정보 조회만.
# 외부 자산 0건 (iframe import 없음, 외부 링크만 노출)
# =====================================================
HIWORKS_LINK_KEYS = [
    ("hiworks_main_url",       "하이웍스 메인",       "https://office.hiworks.com/"),
    ("hiworks_attendance_url", "출퇴근 / 근태",       ""),
    ("hiworks_leave_url",      "휴가 신청",           ""),
    ("hiworks_payroll_url",    "급여 명세서",         ""),
    ("hiworks_profile_url",    "인사 정보",           ""),
]


@app.get("/hr/hiworks", response_class=HTMLResponse)
async def hr_hiworks_page(req: Request):
    """인사총무 하이웍스 연동 페이지 — 모든 로그인 사용자, 본인 KNK 정보만 노출."""
    u = require(req)
    if not u:
        return RedirectResponse("/login", 303)
    # admin_settings 에 입력된 외부 링크 (미입력 시 빈 문자열)
    links = [{"key": k, "label": label, "url": (get_setting(k, "") or "").strip(), "default": default}
             for k, label, default in HIWORKS_LINK_KEYS]
    # 본인 KNK 정보 (다른 직원 정보 노출 금지 — 개인정보 보호)
    me = {
        "name":       u.get("name", ""),
        "login_id":   u.get("login_id", ""),
        "team_name":  u.get("team_name", "") or "(미지정)",
        "rank":       u.get("rank", "") or "(미지정)",
        "role":       u.get("role", "member"),
        "email":      u.get("email", "") or "",
        "hire_date":  u.get("created_at", "") or "",
    }
    return ctx(req, "hr_hiworks.html", user=u,
               links=links, me=me, active="hr_hiworks")


@app.get("/admin/hiworks-settings", response_class=HTMLResponse)
async def admin_hiworks_settings_page(req: Request):
    """하이웍스 연동 URL 설정 (admin/ceo only)."""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    saved = req.query_params.get("saved", "")
    current = {k: (get_setting(k, "") or "") for k, _l, _d in HIWORKS_LINK_KEYS}
    return ctx(req, "admin_hiworks_settings.html", user=u,
               keys=HIWORKS_LINK_KEYS, current=current,
               saved=saved, active="admin")


@app.post("/admin/hiworks-settings")
async def admin_hiworks_settings_save(req: Request):
    """하이웍스 URL 저장 → app_settings UPSERT (화이트리스트만)."""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    form = await req.form()
    allowed = {k for k, _l, _d in HIWORKS_LINK_KEYS}
    saved = 0
    for k, v in form.items():
        if not k.startswith("k_"):
            continue
        key = k[2:].strip()
        if key not in allowed:
            continue
        set_setting(key, (v or "").strip(), user_id=u["id"])
        saved += 1
    return RedirectResponse(f"/admin/hiworks-settings?saved={saved}", 303)


@app.get("/admin/download-passwords")
async def dl_passwords(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    # 사이클 68 (2026-04-27): openpyxl 제거 → CSV 다운로드 (UTF-8 BOM · 대표 결정 이행)
    out_path = os.path.join(BASE, "data", "초기비밀번호_배포용.csv")
    # 구버전 .xlsx 파일이 남아있다면 호환을 위해 폴백
    if not os.path.exists(out_path):
        legacy_xlsx = os.path.join(BASE, "data", "초기비밀번호_배포용.xlsx")
        if os.path.exists(legacy_xlsx):
            return JSONResponse({"error": "구버전 .xlsx 파일이 존재합니다. [비밀번호 재생성]을 1회 다시 실행하면 .csv로 자동 갱신됩니다."}, 410)
        return JSONResponse({"error": "먼저 재생성을 수행하세요"}, 404)
    with open(out_path, "rb") as f:
        data = f.read()
    from urllib.parse import quote
    fn = "KNK_초기비밀번호_배포용.csv"
    headers = {
        "Content-Disposition": f"attachment; filename=KNK_passwords.csv; filename*=UTF-8''{quote(fn)}"
    }
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8-sig",
        headers=headers,
    )


# =====================================================
# PROFILE — 본인 프로필 (정보 + 활동 30일 + 권한 매트릭스 1인)
# =====================================================
def _profile_payload(c, uid: int):
    """본인 프로필 페이로드 — 활동/권한/위임 토큰 (단일 사용자)."""
    out = {
        "tasks_30d": 0, "tasks_open": 0, "tasks_done": 0,
        "comments_30d": 0, "notifs_30d": 0, "notifs_unread": 0,
        "recent_tasks": [], "recent_comments": [], "recent_acts": [],
        "perms_direct": [], "perms_group": [], "perms_deleg": [],
        "tokens_received": [], "tokens_granted": [],
    }
    try:
        # 활동 집계 (최근 30일)
        out["tasks_30d"] = (c.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE user_id=? AND date(work_date) >= date('now','-30 day','localtime')",
            (uid,)).fetchone() or {"n": 0})["n"]
        out["tasks_open"] = (c.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE user_id=? AND status IN ('진행중','대기','지연','보류')",
            (uid,)).fetchone() or {"n": 0})["n"]
        out["tasks_done"] = (c.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE user_id=? AND status='완료' AND date(work_date) >= date('now','-30 day','localtime')",
            (uid,)).fetchone() or {"n": 0})["n"]
        out["comments_30d"] = (c.execute(
            "SELECT COUNT(*) AS n FROM task_comments WHERE author_id=? AND date(created_at) >= date('now','-30 day','localtime')",
            (uid,)).fetchone() or {"n": 0})["n"]
        out["notifs_30d"] = (c.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND date(created_at) >= date('now','-30 day','localtime')",
            (uid,)).fetchone() or {"n": 0})["n"]
        out["notifs_unread"] = (c.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND is_read=0",
            (uid,)).fetchone() or {"n": 0})["n"]
        # 최근 task 10건
        out["recent_tasks"] = [dict(r) for r in c.execute(
            "SELECT id, work_date, title, status, COALESCE(category,'') AS category "
            "FROM tasks WHERE user_id=? ORDER BY work_date DESC, id DESC LIMIT 10",
            (uid,)).fetchall()]
        # 최근 댓글 10건 (task 제목 join)
        out["recent_comments"] = [dict(r) for r in c.execute(
            "SELECT tc.id, tc.task_id, tc.body, tc.created_at, COALESCE(t.title,'') AS task_title "
            "FROM task_comments tc LEFT JOIN tasks t ON t.id=tc.task_id "
            "WHERE tc.author_id=? ORDER BY tc.created_at DESC LIMIT 10",
            (uid,)).fetchall()]
    except Exception:
        pass
    # activities 본인 행 (선택)
    try:
        out["recent_acts"] = [dict(r) for r in c.execute(
            "SELECT id, kind, title, created_at FROM activities WHERE actor_id=? ORDER BY id DESC LIMIT 10",
            (uid,)).fetchall()]
    except Exception:
        out["recent_acts"] = []
    # 권한 — 직접/그룹/위임 (단일 사용자 매트릭스)
    try:
        out["perms_direct"] = [dict(r) for r in c.execute(
            "SELECT p.id, COALESCE(p.resource||'.'||p.action, p.name) AS label "
            "FROM user_permissions up JOIN permissions p ON p.id=up.permission_id "
            "WHERE up.user_id=? ORDER BY label LIMIT 60", (uid,)).fetchall()]
    except Exception:
        out["perms_direct"] = []
    try:
        out["perms_group"] = [dict(r) for r in c.execute(
            "SELECT DISTINCT p.id, COALESCE(p.resource||'.'||p.action, p.name) AS label, g.name AS group_name "
            "FROM user_groups ug "
            "JOIN group_permissions gp ON gp.group_id=ug.group_id "
            "JOIN permissions p ON p.id=gp.permission_id "
            "JOIN permission_groups g ON g.id=ug.group_id "
            "WHERE ug.user_id=? ORDER BY label LIMIT 60", (uid,)).fetchall()]
    except Exception:
        out["perms_group"] = []
    try:
        out["perms_deleg"] = [dict(r) for r in c.execute(
            "SELECT dt.id, COALESCE(p.resource||'.'||p.action, p.name) AS label, "
            "       dt.expires_at, dt.status, uf.name AS from_name "
            "FROM delegation_tokens dt "
            "JOIN permissions p ON p.id=dt.permission_id "
            "LEFT JOIN users uf ON uf.id=dt.from_user "
            "WHERE dt.to_user=? AND dt.status='ACTIVE' ORDER BY dt.id DESC LIMIT 30",
            (uid,)).fetchall()]
        out["tokens_received"] = out["perms_deleg"]
        out["tokens_granted"] = [dict(r) for r in c.execute(
            "SELECT dt.id, COALESCE(p.resource||'.'||p.action, p.name) AS label, "
            "       dt.expires_at, dt.status, ut.name AS to_name "
            "FROM delegation_tokens dt "
            "JOIN permissions p ON p.id=dt.permission_id "
            "LEFT JOIN users ut ON ut.id=dt.to_user "
            "WHERE dt.from_user=? ORDER BY dt.id DESC LIMIT 30",
            (uid,)).fetchall()]
    except Exception:
        out["perms_deleg"] = []
        out["tokens_received"] = []
        out["tokens_granted"] = []
    # task_delegations (위임 받은 task)
    try:
        out["task_delegs_in"] = [dict(r) for r in c.execute(
            "SELECT td.id, td.task_id, td.message, td.status, td.created_at, "
            "       COALESCE(t.title,'') AS task_title, uf.name AS from_name "
            "FROM task_delegations td LEFT JOIN tasks t ON t.id=td.task_id "
            "LEFT JOIN users uf ON uf.id=td.from_user_id "
            "WHERE td.to_user_id=? ORDER BY td.id DESC LIMIT 10",
            (uid,)).fetchall()]
    except Exception:
        out["task_delegs_in"] = []
    return out


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(req: Request, msg: str = "", err: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        pdata = _profile_payload(c, u["id"])
    return ctx(req, "profile.html", user=u, msg=msg, err=err, active="profile", **pdata)


@app.get("/me", response_class=HTMLResponse)
async def me_alias(req: Request, msg: str = "", err: str = ""):
    """본인 프로필 별칭 (/me → /profile)."""
    return await profile_page(req, msg=msg, err=err)


@app.post("/profile/change-password")
async def change_password(req: Request,
                          current_pw: str = Form(...),
                          new_pw: str = Form(...),
                          confirm_pw: str = Form(...)):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if new_pw != confirm_pw:
        return RedirectResponse("/profile?err=새 비밀번호가 일치하지 않습니다", 303)
    if len(new_pw) < 6:
        return RedirectResponse("/profile?err=비밀번호는 6자 이상", 303)
    with db_session() as c:
        row = c.execute("SELECT password FROM users WHERE id=?", (u["id"],)).fetchone()
        if not row or row["password"] != hash_pw(current_pw):
            return RedirectResponse("/profile?err=현재 비밀번호가 맞지 않습니다", 303)
        c.execute("UPDATE users SET password=? WHERE id=?",
                  (hash_pw(new_pw), u["id"]))
    return RedirectResponse("/profile?msg=비밀번호가 변경되었습니다", 303)


@app.post("/me")
async def me_update(req: Request,
                    email: str = Form(""),
                    lang: str = Form("")):
    """본인 프로필 수정 — email / lang 만 (본인 한정).
    phone/dept 컬럼은 스키마에 따라 선택 적용 (PRAGMA로 존재 시만).
    """
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    email = (email or "").strip()
    lang = (lang or "").strip()
    sets, vals = [], []
    if email:
        if "@" in email and len(email) <= 120:
            sets.append("email=?"); vals.append(email)
    if lang in ("ko", "en", "vi", "zh"):
        sets.append("lang=?"); vals.append(lang)
    # phone / dept (스키마에 존재할 때만)
    try:
        with db_session() as c:
            ucols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    except Exception:
        ucols = []
    # form 에서 추가 필드 (있을 때만)
    form = await req.form()
    if "phone" in ucols and form.get("phone") is not None:
        ph = (form.get("phone") or "").strip()[:30]
        sets.append("phone=?"); vals.append(ph)
    if "dept" in ucols and form.get("dept") is not None:
        dp = (form.get("dept") or "").strip()[:60]
        sets.append("dept=?"); vals.append(dp)
    if not sets:
        return RedirectResponse("/profile?err=변경할 항목이 없습니다", 303)
    vals.append(u["id"])
    with db_session() as c:
        c.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", vals)
    return RedirectResponse("/profile?msg=프로필이 갱신되었습니다", 303)


# =====================================================
# REMINDERS — 팀장용 오늘 미작성자 리스트
# =====================================================
@app.get("/admin/reminders", response_class=HTMLResponse)
async def reminders_page(req: Request, sel_date: str = ""):
    u = require(req, ["leader", "executive", "ceo", "admin"])
    if not u:
        return RedirectResponse("/login", 303)
    if not sel_date:
        sel_date = date.today().isoformat()
    with db_session() as c:
        teams = [dict(r) for r in c.execute(
            """SELECT t.*, ul.name AS leader_name, ul.email AS leader_email
               FROM teams t LEFT JOIN users ul ON t.leader_id=ul.id
               ORDER BY t.display_order"""
        ).fetchall()]
        # 팀장이면 자기 팀만 표시
        if u["role"] == "leader":
            teams = [t for t in teams if t["id"] == u["team_id"]]
        for t in teams:
            members = [dict(r) for r in c.execute(
                """SELECT u.id, u.name, u.rank, u.email
                   FROM users u WHERE u.team_id=? AND u.is_active=1
                   AND u.role!='admin' ORDER BY u.id""",
                (t["id"],),
            ).fetchall()]
            reported_ids = {r["user_id"] for r in c.execute(
                """SELECT DISTINCT user_id FROM tasks
                   WHERE work_date=? AND user_id IN
                   (SELECT id FROM users WHERE team_id=?)""",
                (sel_date, t["id"]),
            ).fetchall()}
            t["members"] = members
            t["missing"] = [m for m in members if m["id"] not in reported_ids]
            t["reported_count"] = len(members) - len(t["missing"])
            t["total"] = len(members)
            t["participation"] = round(t["reported_count"] * 100 / max(t["total"], 1))
    return ctx(req, "reminders.html", user=u, teams=teams,
               sel_date=sel_date, active="reminders")


# =====================================================
# EXPORT — 주간 요약 CSV (사이클 68: openpyxl 제거 → csv 표준 모듈)
# 대표 결정 (2026-04-27 14:20:16): openpyxl 제거(Remove)
# 출처: 99_DISPATCH/외부자산_결정_2026-04-27.md
# 단일 .csv 안에 [전사 요약] 섹션 + [카드 상세] 섹션 2개를 빈 줄로 분리해 출력.
# UTF-8 BOM 으로 Excel/구글시트 한글 호환.
# =====================================================
@app.get("/export/weekly")
async def export_weekly(req: Request, wk_mon: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    import csv as _csv
    if not wk_mon:
        td = date.today()
        wk_mon = (td - timedelta(days=td.weekday())).isoformat()
    mon = datetime.strptime(wk_mon, "%Y-%m-%d").date()
    sun = mon + timedelta(days=6)

    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM (Excel 한글 호환)
    w = _csv.writer(buf)

    # 헤더 메타
    w.writerow([f"㈜케이엔케이 주간 업무 요약  {mon} ~ {sun}"])
    w.writerow([])

    with db_session() as c:
        # 섹션 1: 전사 요약
        w.writerow(["[전사 요약]"])
        w.writerow(["팀코드", "팀명", "팀장", "인원", "카드수", "완료", "지연", "공수(h)"])
        teams = [dict(r) for r in c.execute(
            """SELECT t.*, u.name AS leader_name,
                      (SELECT COUNT(*) FROM users WHERE team_id=t.id AND is_active=1) AS mc
               FROM teams t LEFT JOIN users u ON t.leader_id=u.id
               ORDER BY t.display_order"""
        ).fetchall()]
        for t in teams:
            s = c.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN status='완료' THEN 1 ELSE 0 END) AS done,
                          SUM(CASE WHEN status='지연' THEN 1 ELSE 0 END) AS delay,
                          COALESCE(SUM(hours),0) AS hours
                   FROM tasks tk JOIN users u ON tk.user_id=u.id
                   WHERE u.team_id=? AND tk.work_date>=? AND tk.work_date<=?""",
                (t["id"], mon.isoformat(), sun.isoformat()),
            ).fetchone()
            w.writerow([t["code"], t["name"], t["leader_name"] or "-", t["mc"],
                        s["total"] or 0, s["done"] or 0, s["delay"] or 0,
                        round(s["hours"] or 0, 1)])

        # 섹션 사이 공백
        w.writerow([])
        w.writerow([])

        # 섹션 2: 카드 상세
        w.writerow(["[카드 상세]"])
        w.writerow(["날짜", "팀", "이름", "직급", "제목", "분류", "프로젝트",
                    "고객사", "상태", "공수(h)"])
        rows = c.execute(
            """SELECT tk.work_date, t.name AS team_name, u.name AS user_name, u.rank,
                      tk.title, tk.category, p.name AS pj, cu.name AS cu,
                      tk.status, tk.hours
               FROM tasks tk JOIN users u ON tk.user_id=u.id
               LEFT JOIN teams t ON u.team_id=t.id
               LEFT JOIN projects p ON tk.project_id=p.id
               LEFT JOIN customers cu ON tk.customer_id=cu.id
               WHERE tk.work_date>=? AND tk.work_date<=?
               ORDER BY tk.work_date, t.display_order, u.id""",
            (mon.isoformat(), sun.isoformat()),
        ).fetchall()
        for r in rows:
            w.writerow([r["work_date"], r["team_name"] or "", r["user_name"] or "",
                        r["rank"] or "", r["title"] or "", r["category"] or "",
                        r["pj"] or "", r["cu"] or "", r["status"] or "",
                        r["hours"] or 0])

    fname = f"KNK_주간요약_{mon}_{sun}.csv"
    from urllib.parse import quote
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}"},
    )


# =====================================================
# HAIST WORKS — 변경 Inform 시스템 (1순위 ② / 6팀 + 제조2 사고 사례)
# 설계: HAIST_WORKS/_DESIGN_변경_Inform.md
# =====================================================
from .database import (changes_list, change_get, change_create,
                        change_get_impacts, change_get_reads,
                        change_mark_read, change_ack, change_delete,
                        change_unread_count, change_recent_count,
                        CHANGE_TYPES, CHANGE_URGENCIES, CHANGE_STATUSES,
                        CHANGE_SOURCES,
                        detect_impact_teams, hiworks_notify)


@app.get("/changes", response_class=HTMLResponse)
async def changes_page(req: Request, q: str = "", change_type: str = "",
                       urgency: str = "", status: str = "", scope: str = "all"):
    """변경 목록 (필터 + scope=me/all)"""
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    scope_user_id = u["id"] if scope == "me" else None
    rows = changes_list(q=q, change_type=change_type, urgency=urgency,
                         status=status, scope_user_id=scope_user_id)
    return ctx(req, "changes_list.html", user=u, active="changes",
               changes=rows, q=q, change_type=change_type, urgency=urgency,
               status=status, scope=scope,
               CHANGE_TYPES=CHANGE_TYPES, CHANGE_URGENCIES=CHANGE_URGENCIES,
               CHANGE_STATUSES=CHANGE_STATUSES)


@app.get("/changes/new", response_class=HTMLResponse)
async def changes_new_form(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    # 활성 프로젝트 (관리코드 발급된 것)
    with db_session() as c:
        projects = c.execute(
            """SELECT id, mgmt_code, name, biz_div, customer_name
               FROM projects
               WHERE mgmt_code IS NOT NULL AND mgmt_code != ''
               ORDER BY id DESC LIMIT 200"""
        ).fetchall()
    return ctx(req, "change_form.html", user=u, active="changes",
               change=None, projects=projects,
               CHANGE_TYPES=CHANGE_TYPES, CHANGE_URGENCIES=CHANGE_URGENCIES,
               CHANGE_SOURCES=CHANGE_SOURCES)


@app.post("/changes/new")
async def changes_new_submit(
    req: Request,
    change_type: str = Form(...),
    biz_div: str = Form(""),
    target_kind: str = Form(""),
    target_label: str = Form(""),
    project_id: str = Form(""),
    title: str = Form(...),
    description: str = Form(""),
    before_value: str = Form(""),
    after_value: str = Form(""),
    urgency: str = Form("일반"),
    source: str = Form("수동"),
    source_ref: str = Form(""),
    approval_url: str = Form(""),
):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)

    # 프로젝트 ID에서 사업부 자동 추출 (없으면 폼 입력 사용)
    pid = None
    if project_id:
        try:
            pid = int(project_id)
            with db_session() as c:
                p = c.execute(
                    "SELECT biz_div, mgmt_code, name FROM projects WHERE id=?", (pid,)
                ).fetchone()
            if p:
                if not biz_div:
                    biz_div = p["biz_div"] or ""
                if not target_label:
                    target_label = f"{p['mgmt_code']} {p['name']}"
        except (ValueError, TypeError):
            pid = None

    cid, change_no = change_create({
        "change_type": change_type, "biz_div": biz_div,
        "target_kind": target_kind, "target_label": target_label,
        "project_id": pid, "title": title, "description": description,
        "before_value": before_value, "after_value": after_value,
        "urgency": urgency,
        "source": source, "source_ref": source_ref,
        "approval_url": approval_url.strip() or None,
    }, author_id=u["id"])

    # 알림 발송 (web 게시판 자동 글 + 하이웍스 메신저)
    try:
        notify_change_impacts(cid, change_no, change_type, title, urgency, u)
    except Exception as e:
        print(f"[NOTIFY ERROR] {e}")

    return RedirectResponse(f"/changes/{cid}", 303)


def notify_change_impacts(cid, change_no, change_type, title, urgency, author):
    """변경 등록 후 통합 알림 발송 — 영향 강도별 차별화 (알림 피로 방지)
    - high: 즉시 카톡 푸시 + web 알림 + 게시판
    - medium: web 알림 + 게시판 (카톡 안 보냄)
    - low: 게시판 글에만 노출 (직접 알림 X)
    - 긴급(urgency=긴급): 강도 무시하고 모두 high로 격상
    """
    from .database import get_impact_intensity
    impacts = change_get_impacts(cid)
    icon = "🔴" if urgency == "긴급" else "🟡"
    biz_div = ""  # 변경 본체에서 가져와야 함
    with db_session() as c:
        row = c.execute("SELECT biz_div FROM changes WHERE id=?", (cid,)).fetchone()
        biz_div = row["biz_div"] if row else ""

    # 영향 부서별 강도 분류
    high_teams, medium_teams, low_teams = [], [], []
    for imp in impacts:
        if not imp.get("team_name"):
            continue
        intensity = "high" if urgency == "긴급" else \
                    get_impact_intensity(change_type, biz_div, imp["team_name"])
        if intensity == "high":
            high_teams.append(imp)
        elif intensity == "medium":
            medium_teams.append(imp)
        else:
            low_teams.append(imp)

    # 1. high 강도 → 하이웍스 메신저 즉시 푸시 (토큰 없으면 silent skip)
    for imp in high_teams:
        hiworks_notify(
            channel_id=f"team_{imp['impact_team_id']}",
            text=f"{icon} [{change_type}·직접영향] {title}\n변경번호: {change_no}\n작성자: {author['name']}\n→ /changes/{cid}",
        )

    # 2. 게시판 자동 글 — 모든 영향 부서 표시 (강도별 분류)
    try:
        bid = board_get_or_create_company()
        high_names = ", ".join([imp["team_name"] for imp in high_teams]) or "없음"
        medium_names = ", ".join([imp["team_name"] for imp in medium_teams]) or "없음"
        low_names = ", ".join([imp["team_name"] for imp in low_teams]) or "없음"
        body = (f"종류: {change_type}\n"
                f"긴급도: {urgency}\n"
                f"━━ 영향 강도 ━━\n"
                f"🔴 직접 영향: {high_names}\n"
                f"🟡 일정 영향: {medium_names}\n"
                f"⚪ 참고: {low_names}\n\n"
                f"변경번호: {change_no}\n"
                f"상세: /changes/{cid}")
        board_post_create(bid, author["id"],
                          f"[변경공지] {title}", body, category="공지",
                          approval_status="approved")
    except Exception as e:
        print(f"[BOARD POST ERROR] {e}")


@app.get("/changes/{cid}", response_class=HTMLResponse)
async def changes_detail(req: Request, cid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    change = change_get(cid)
    if not change:
        return RedirectResponse("/changes", 303)
    impacts = change_get_impacts(cid)
    reads = change_get_reads(cid)
    # 자동 read 기록 (영향자인 경우만)
    is_impacted = any(
        r["user_id"] == u["id"] for r in reads
    )
    if is_impacted:
        change_mark_read(cid, u["id"])
    # 내 ack 상태
    my_ack = next((r for r in reads if r["user_id"] == u["id"]), None)
    return ctx(req, "change_detail.html", user=u, active="changes",
               change=change, impacts=impacts, reads=reads,
               is_impacted=is_impacted, my_ack=my_ack,
               is_author=(change["author_id"] == u["id"]))


@app.post("/changes/{cid}/ack")
async def changes_ack(req: Request, cid: int, note: str = Form("")):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    change_ack(cid, u["id"], note)
    return RedirectResponse(f"/changes/{cid}", 303)


@app.post("/changes/{cid}/delete")
async def changes_delete_submit(req: Request, cid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    change = change_get(cid)
    if change and (change["author_id"] == u["id"] or u["role"] in ("admin", "ceo")):
        change_delete(cid)
    return RedirectResponse("/changes", 303)


@app.get("/api/changes/unread")
async def api_changes_unread(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"count": 0})
    return JSONResponse({"count": change_unread_count(u["id"])})


@app.get("/api/changes/recent")
async def api_changes_recent(req: Request, scope: str = "me", days: int = 1):
    u = get_user(req)
    if not u:
        return JSONResponse({"count": 0})
    uid = u["id"] if scope == "me" else None
    return JSONResponse({"count": change_recent_count(uid, days)})


# =====================================================
# HAIST WORKS — 진행률 대시보드 (1순위 ① / 8팀 공통 요구)
# =====================================================
from .database import (PHASE_DEFS, PHASE_CODE_TO_LABEL, PHASE_STATUSES,
                        ensure_phases_for_project, progress_matrix,
                        project_phases_get, project_phase_update,
                        progress_summary_for_user)


@app.get("/progress", response_class=HTMLResponse)
async def progress_dashboard(req: Request, biz_div: str = "", customer: str = "",
                              status: str = "", limit: int = 50):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    matrix = progress_matrix(biz_div=biz_div, customer=customer, status=status, limit=limit)
    return ctx(req, "progress_matrix.html", user=u, active="progress",
               matrix=matrix, biz_div=biz_div, customer=customer, status=status,
               PHASE_DEFS=PHASE_DEFS, PHASE_STATUSES=PHASE_STATUSES)


@app.get("/progress/{project_id}", response_class=HTMLResponse)
async def progress_project_detail(req: Request, project_id: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        proj = c.execute(
            """SELECT p.*, p.name AS project_name FROM projects p WHERE p.id=?""",
            (project_id,)
        ).fetchone()
    if not proj:
        return RedirectResponse("/progress", 303)
    project = dict(proj)
    phases = project_phases_get(project_id)
    return ctx(req, "progress_detail.html", user=u, active="progress",
               project=project, phases=phases,
               PHASE_DEFS=PHASE_DEFS, PHASE_CODE_TO_LABEL=PHASE_CODE_TO_LABEL,
               PHASE_STATUSES=PHASE_STATUSES)


@app.post("/progress/phase/{phase_id}/update")
async def progress_phase_update(
    req: Request,
    phase_id: int,
    status: str = Form(""),
    progress_pct: str = Form(""),
    note: str = Form(""),
    project_id: str = Form(""),
):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    data = {}
    if status:
        data["status"] = status
        # 완료 시 자동 100% / 진행 시 0%면 50%로
        if status == "완료":
            data["progress_pct"] = 100
            data["actual_end"] = _logi_now()[:10]
        elif status == "진행":
            try:
                cur = float(progress_pct) if progress_pct else 0
                if cur == 0:
                    data["progress_pct"] = 50
            except (ValueError, TypeError):
                pass
            data["actual_start"] = _logi_now()[:10]
    if progress_pct:
        try:
            data["progress_pct"] = float(progress_pct)
        except (ValueError, TypeError):
            pass
    if note:
        data["note"] = note
    project_phase_update(phase_id, data, u["id"])
    return RedirectResponse(f"/progress/{project_id}" if project_id else "/progress", 303)


@app.get("/api/progress/summary")
async def api_progress_summary(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"my_open": 0, "delayed": 0})
    return JSONResponse(progress_summary_for_user(u["id"], u.get("team_id")))


# =====================================================
# HAIST WORKS — 요청 티켓 시스템 (1순위 ③ / 10팀 카톡 누락 해결)
# =====================================================
from .database import (tickets_list, ticket_get, ticket_create,
                        ticket_change_status, ticket_comments_list,
                        ticket_add_comment, ticket_delete,
                        tickets_count_for_user, route_ticket_team,
                        TICKET_CATEGORIES, TICKET_URGENCIES, TICKET_STATUSES,
                        TICKET_SOURCES)


# ─── 티켓 권한 가드 (2026-04-28 대표 결재 (나)안) ───────────────
def _can_edit_ticket(u, ticket) -> bool:
    """티켓 본문 편집·상태변경 권한:
    (a) 작성자 본인
    (b) 작성자와 같은 팀원 (휴가·출장 시 대리)
    (c) 수신팀의 can_close_tickets 보유자
    (d) CEO/admin/임원 (전사)
    """
    if not u or not ticket:
        return False
    role = (u.get("role") or "").lower()
    if role in ("ceo", "admin", "executive"):
        return True
    uid = u.get("id")
    # 작성자 본인
    if ticket.get("requester_id") == uid:
        return True
    utid = u.get("team_id")
    # 작성자와 같은 팀원
    try:
        with db_session() as c:
            r = c.execute(
                "SELECT team_id FROM users WHERE id=?", (ticket.get("requester_id"),)
            ).fetchone()
            if r and utid and r["team_id"] == utid:
                return True
    except Exception:
        pass
    # 수신팀의 can_close_tickets 보유자
    if (utid and ticket.get("recipient_team_id") == utid
            and bool(u.get("can_close_tickets"))):
        return True
    return False


def _can_delete_ticket(u, ticket) -> bool:
    """티켓 삭제: 작성자 본인 + CEO/admin (전사)."""
    if not u or not ticket:
        return False
    role = (u.get("role") or "").lower()
    if role in ("ceo", "admin"):
        return True
    return ticket.get("requester_id") == u.get("id")


@app.get("/tickets", response_class=HTMLResponse)
async def tickets_page(req: Request, scope: str = "me", q: str = "",
                       category: str = "", urgency: str = "", status: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    suid = u["id"] if scope == "me" else None
    stid = u.get("team_id") if scope == "team" else None
    rows = tickets_list(scope_user_id=suid, scope_team_id=stid,
                        status=status, category=category, urgency=urgency, q=q)
    return ctx(req, "tickets_list.html", user=u, active="tickets",
               tickets=rows, scope=scope, q=q,
               category=category, urgency=urgency, status=status,
               TICKET_CATEGORIES=TICKET_CATEGORIES,
               TICKET_URGENCIES=TICKET_URGENCIES,
               TICKET_STATUSES=TICKET_STATUSES)


@app.get("/tickets/new", response_class=HTMLResponse)
async def tickets_new_form(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        projects = c.execute(
            """SELECT id, mgmt_code, name, biz_div, customer_name FROM projects
               WHERE mgmt_code IS NOT NULL AND mgmt_code != ''
               ORDER BY id DESC LIMIT 200"""
        ).fetchall()
        teams = c.execute("SELECT id, name FROM teams ORDER BY display_order").fetchall()
    return ctx(req, "ticket_form.html", user=u, active="tickets",
               ticket=None, projects=projects, teams=teams,
               TICKET_CATEGORIES=TICKET_CATEGORIES,
               TICKET_URGENCIES=TICKET_URGENCIES)


@app.post("/tickets/new")
async def tickets_new_submit(
    req: Request,
    category: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    biz_div: str = Form(""),
    project_id: str = Form(""),
    target_label: str = Form(""),
    recipient_team_id: str = Form(""),
    urgency: str = Form("일반"),
    due_date: str = Form(""),
    hours_estimated: str = Form(""),
    source: str = Form("web"),
    approval_url: str = Form(""),
):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)

    pid = None
    if project_id:
        try:
            pid = int(project_id)
            with db_session() as c:
                p = c.execute(
                    "SELECT biz_div, mgmt_code, name FROM projects WHERE id=?", (pid,)
                ).fetchone()
            if p:
                if not biz_div:
                    biz_div = p["biz_div"] or ""
                if not target_label:
                    target_label = f"{p['mgmt_code']} {p['name']}"
        except (ValueError, TypeError):
            pid = None

    rtid = None
    if recipient_team_id:
        try:
            rtid = int(recipient_team_id)
        except (ValueError, TypeError):
            rtid = None

    # OPS-P1-A1 [D-003]: 카테고리 기반 자동 라우팅 — 사용자 미선택 시 TICKET_ROUTING 사용
    if rtid is None:
        try:
            from app.database import TICKET_ROUTING  # noqa: F811
        except ImportError:
            TICKET_ROUTING = {}
        target_team_name = TICKET_ROUTING.get(category)
        if target_team_name:
            with db_session() as c:
                row = c.execute(
                    "SELECT id FROM teams WHERE name=? LIMIT 1", (target_team_name,)
                ).fetchone()
            if row:
                rtid = row["id"] if hasattr(row, "keys") else row[0]

    tid, ticket_no = ticket_create({
        "category": category, "title": title, "description": description,
        "biz_div": biz_div, "project_id": pid,
        "target_label": target_label, "recipient_team_id": rtid,
        "urgency": urgency, "due_date": due_date,
        "hours_estimated": hours_estimated, "source": source,
        "approval_url": approval_url,
    }, requester_id=u["id"])

    # 하이웍스 메신저 푸시 (수신 부서) — 토큰 없으면 silent skip
    try:
        ticket = ticket_get(tid)
        if ticket and ticket.get("recipient_team_id"):
            icon = "🔴" if urgency == "긴급" else "🎫"
            hiworks_notify(
                channel_id=f"team-{ticket['recipient_team_id']}",
                text=f"{icon} [{category}] {title}\n티켓: {ticket_no}\n요청: {u['name']}\n→ http://localhost:8081/tickets/{tid}",
            )
    except Exception as e:
        print(f"[TICKET NOTIFY ERROR] {e}")

    return RedirectResponse(f"/tickets/{tid}", 303)


@app.get("/tickets/{tid}", response_class=HTMLResponse)
async def tickets_detail(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    ticket = ticket_get(tid)
    if not ticket:
        return RedirectResponse("/tickets", 303)
    comments = ticket_comments_list(tid)
    is_requester = ticket["requester_id"] == u["id"]
    is_recipient = (ticket.get("recipient_user_id") == u["id"]) or \
                   (ticket.get("recipient_team_id") == u.get("team_id"))
    can_edit = _can_edit_ticket(u, ticket)
    can_delete = _can_delete_ticket(u, ticket)
    # 편집 폼용 전팀 목록
    with db_session() as c:
        all_teams_for_edit = [dict(r) for r in c.execute(
            "SELECT id, name FROM teams ORDER BY display_order"
        ).fetchall()]
    return ctx(req, "ticket_detail.html", user=u, active="tickets",
               ticket=ticket, comments=comments,
               is_requester=is_requester, is_recipient=is_recipient,
               can_edit=can_edit, can_delete=can_delete,
               all_teams_for_edit=all_teams_for_edit,
               TICKET_STATUSES=TICKET_STATUSES,
               TICKET_URGENCIES=TICKET_URGENCIES)


@app.post("/tickets/{tid}/status")
async def tickets_status_change(req: Request, tid: int,
                                 new_status: str = Form(...),
                                 note: str = Form("")):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    ticket = ticket_get(tid)
    if not _can_edit_ticket(u, ticket):
        return RedirectResponse(f"/tickets/{tid}?err=no_perm", 303)
    ticket_change_status(tid, new_status, u["id"], note)
    return RedirectResponse(f"/tickets/{tid}", 303)


# ─── 티켓 본문 편집 (2026-04-28 신설 · (나)안 · 이력 자동) ───────────
@app.post("/tickets/{tid}/edit")
async def tickets_edit_submit(
    req: Request, tid: int,
    title: str = Form(""),
    description: str = Form(""),
    due_date: str = Form(""),
    urgency: str = Form(""),
    recipient_team_id: str = Form(""),
    target_label: str = Form(""),
    hours_estimated: str = Form(""),
):
    from .database import ticket_edit as _ticket_edit
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    ticket = ticket_get(tid)
    if not ticket:
        return RedirectResponse("/tickets", 303)
    if not _can_edit_ticket(u, ticket):
        return RedirectResponse(f"/tickets/{tid}?err=no_perm", 303)
    changes = {
        "title": title, "description": description,
        "due_date": due_date, "urgency": urgency,
        "recipient_team_id": recipient_team_id or None,
        "target_label": target_label, "hours_estimated": hours_estimated,
    }
    n = _ticket_edit(tid, changes, editor_id=u["id"],
                     editor_name=f"{u.get('name','')} {u.get('rank','') or ''}".strip())
    return RedirectResponse(f"/tickets/{tid}?edited={n}", 303)


@app.post("/tickets/{tid}/comment")
async def tickets_add_comment(req: Request, tid: int, body: str = Form(...)):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    ticket_add_comment(tid, u["id"], body)
    # OPS-P1-A3 [D-018]: 댓글 후 티켓 관여자(요청자/담당자/팀장) 알림
    try:
        ticket = ticket_get(tid)
        if ticket:
            recipients = set()
            if ticket.get("requester_id") and ticket["requester_id"] != u["id"]:
                recipients.add(ticket["requester_id"])
            if ticket.get("assignee_id") and ticket["assignee_id"] != u["id"]:
                recipients.add(ticket["assignee_id"])
            preview = (body or "").strip().replace("\n", " ")[:40]
            for rid in recipients:
                try:
                    notify_user(
                        user_id=rid,
                        type="ticket_comment",
                        title=f"💬 티켓 댓글 — {ticket.get('ticket_no','')}",
                        body=f"{u.get('name','')}: {preview}",
                        link=f"/tickets/{tid}",
                    )
                except Exception:
                    pass
            # 수신팀 메신저 푸시 (토큰 없으면 silent)
            if ticket.get("recipient_team_id"):
                try:
                    hiworks_notify(
                        channel_id=f"team-{ticket['recipient_team_id']}",
                        text=f"💬 [{ticket.get('ticket_no','')}] {u.get('name','')}: {preview}",
                    )
                except Exception:
                    pass
    except Exception as e:
        print(f"[TICKET COMMENT NOTIFY ERROR] {e}")
    return RedirectResponse(f"/tickets/{tid}", 303)


@app.post("/tickets/{tid}/delete")
async def tickets_delete_submit(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    ticket = ticket_get(tid)
    if not ticket:
        return RedirectResponse("/tickets", 303)
    if not _can_delete_ticket(u, ticket):
        return RedirectResponse(f"/tickets/{tid}?err=no_perm_delete", 303)
    ticket_delete(tid)
    return RedirectResponse("/tickets", 303)


@app.get("/api/tickets/count")
async def api_tickets_count(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"my_open": 0, "recv_pending": 0})
    return JSONResponse(tickets_count_for_user(u["id"], u.get("team_id")))


# =====================================================
# HAIST WORKS — 이슈·AS DB (3순위 ⑦)
# 고객사 이슈 추적 → 원인분석 → 재발방지 학습 → 변경 연계
# =====================================================
from .database import (issues_list, issue_get, issue_create, issue_update,
                        issue_delete, issue_logs_get, issues_kpi,
                        ISSUE_SEVERITIES, ISSUE_TYPES, ISSUE_STATUSES,
                        route_issue_team)


@app.get("/issues", response_class=HTMLResponse)
async def issues_page(req: Request, scope: str = "open", q: str = "",
                      status: str = "", severity: str = "", issue_type: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    items = issues_list(scope=scope, user_id=u["id"], team_id=u.get("team_id"),
                        status=status, severity=severity, issue_type=issue_type, q=q)
    kpi = issues_kpi()
    return ctx(req, "issues_list.html", user=u, items=items, kpi=kpi,
               scope=scope, q=q, status=status, severity=severity, issue_type=issue_type,
               ISSUE_STATUSES=ISSUE_STATUSES, ISSUE_SEVERITIES=ISSUE_SEVERITIES,
               ISSUE_TYPES=ISSUE_TYPES, active="issues")


@app.get("/issues/new", response_class=HTMLResponse)
async def issues_new_form(req: Request, project_id: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        teams = [dict(r) for r in c.execute(
            "SELECT id, name FROM teams ORDER BY display_order"
        ).fetchall()]
        projects = [dict(r) for r in c.execute(
            """SELECT id, mgmt_code, name, biz_div, customer_id
               FROM projects WHERE status IN ('active','진행중','planning')
               ORDER BY mgmt_code DESC LIMIT 200"""
        ).fetchall()]
        customers = [dict(r) for r in c.execute(
            "SELECT id, name FROM customers ORDER BY tier DESC, name"
        ).fetchall()]
    return ctx(req, "issue_form.html", user=u, teams=teams, projects=projects,
               customers=customers, default_project_id=project_id,
               ISSUE_SEVERITIES=ISSUE_SEVERITIES, ISSUE_TYPES=ISSUE_TYPES,
               active="issues")


@app.post("/issues/new")
async def issues_new_submit(
    req: Request,
    title: str = Form(...),
    severity: str = Form("중"),
    issue_type: str = Form("AS"),
    biz_div: str = Form(""),
    project_id: str = Form(""),
    customer_id: str = Form(""),
    customer_name: str = Form(""),
    occurred_at: str = Form(""),
    detected_by: str = Form(""),
    description: str = Form(""),
    owner_team_id: str = Form(""),
):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    pid = int(project_id) if project_id and project_id.isdigit() else None
    cid = int(customer_id) if customer_id and customer_id.isdigit() else None
    otid = int(owner_team_id) if owner_team_id and owner_team_id.isdigit() else None
    iid, issue_no = issue_create({
        "title": title, "severity": severity, "issue_type": issue_type,
        "biz_div": biz_div, "project_id": pid, "customer_id": cid,
        "customer_name": customer_name,
        "occurred_at": occurred_at, "detected_by": detected_by,
        "description": description, "owner_team_id": otid,
    }, created_by=u["id"])

    # 치명/심각 이슈 → 하이웍스 메신저 즉시 푸시
    if severity in ("치명", "심각"):
        try:
            issue = issue_get(iid)
            recip = f"team-{issue['owner_team_id']}" if issue and issue.get("owner_team_id") else None
            icon = "🚨" if severity == "치명" else "⚠️"
            hiworks_notify(
                channel_id=recip or "all",
                text=(f"{icon} [{severity}·{issue_type}] {title}\n"
                      f"이슈번호: {issue_no}\n고객사: {customer_name or '-'}\n"
                      f"발견: {detected_by or u['name']}\n→ /issues/{iid}"),
            )
        except Exception as e:
            print(f"[ISSUE NOTIFY ERROR] {e}")

    return RedirectResponse(f"/issues/{iid}", 303)


@app.get("/issues/{iid}", response_class=HTMLResponse)
async def issues_detail(req: Request, iid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    issue = issue_get(iid)
    if not issue:
        return RedirectResponse("/issues", 303)
    logs = issue_logs_get(iid)
    with db_session() as c:
        teams = [dict(r) for r in c.execute(
            "SELECT id, name FROM teams ORDER BY display_order"
        ).fetchall()]
    is_owner = (issue["owner_user_id"] == u["id"]
                or (issue["owner_team_id"] and issue["owner_team_id"] == u.get("team_id")))
    can_edit = is_owner or issue["created_by"] == u["id"] or u["role"] in ("admin", "ceo")
    return ctx(req, "issue_detail.html", user=u, issue=issue, logs=logs,
               teams=teams, can_edit=can_edit,
               ISSUE_STATUSES=ISSUE_STATUSES, ISSUE_SEVERITIES=ISSUE_SEVERITIES,
               ISSUE_TYPES=ISSUE_TYPES, active="issues")


@app.post("/issues/{iid}/update")
async def issues_update_submit(
    req: Request, iid: int,
    status: str = Form(""),
    root_cause: str = Form(""),
    action_taken: str = Form(""),
    prevention: str = Form(""),
    owner_team_id: str = Form(""),
    cost_estimate: str = Form(""),
    related_change_id: str = Form(""),
    comment: str = Form(""),
    note: str = Form(""),
):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    data = {"note": note, "comment": comment.strip() or None}
    if status:
        data["status"] = status
    if root_cause.strip():
        data["root_cause"] = root_cause.strip()
    if action_taken.strip():
        data["action_taken"] = action_taken.strip()
    if prevention.strip():
        data["prevention"] = prevention.strip()
    if owner_team_id and owner_team_id.isdigit():
        data["owner_team_id"] = int(owner_team_id)
    if cost_estimate:
        try:
            data["cost_estimate"] = float(cost_estimate)
        except ValueError:
            pass
    if related_change_id and related_change_id.isdigit():
        data["related_change_id"] = int(related_change_id)
    issue_update(iid, data, user_id=u["id"])
    return RedirectResponse(f"/issues/{iid}", 303)


@app.post("/issues/{iid}/delete")
async def issues_delete_submit(req: Request, iid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    issue = issue_get(iid)
    if issue and (issue["created_by"] == u["id"] or u["role"] in ("admin", "ceo")):
        issue_delete(iid)
    return RedirectResponse("/issues", 303)


@app.get("/api/issues/count")
async def api_issues_count(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"open": 0, "critical": 0})
    kpi = issues_kpi()
    return JSONResponse({"open": kpi["open"], "critical": kpi["critical"]})


# =====================================================
# HAIST WORKS — 게시판 라우트
# =====================================================
from .database import (board_get_or_create_company, board_get_or_create_team,
                        board_posts_list, board_posts_pending, board_post_get,
                        board_post_create, board_post_update, board_post_delete,
                        board_post_approve, board_post_reject, board_post_toggle_pin,
                        board_post_increment_view,
                        board_comments_list, board_comment_create, board_comment_delete,
                        BOARD_CATEGORIES)


def _is_team_leader(user, team_id):
    """사용자가 해당 팀의 팀장인지 확인"""
    if not user:
        return False
    if user.get("role") in ("admin", "ceo", "executive"):
        return True
    if user.get("role") == "leader" and user.get("team_id") == team_id:
        return True
    return False


@app.get("/board/company", response_class=HTMLResponse)
async def board_company(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    bid = board_get_or_create_company()
    posts = board_posts_list(bid)
    can_write = u["role"] in ("admin", "ceo", "executive")
    return ctx(req, "board_list.html", user=u, active="board_company",
               board_id=bid, board_name="전사 게시판", board_type="company",
               posts=posts, can_write=can_write, is_leader=False,
               pending_count=0, CATEGORIES=BOARD_CATEGORIES)


@app.get("/board/team", response_class=HTMLResponse)
async def board_team_my(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    tid = u.get("team_id")
    # 팀 미소속 (admin/ceo 등) → 전체 부서 게시판 목록
    if not tid:
        with db_session() as c:
            teams = c.execute(
                """SELECT t.id, t.name, t.sector,
                          (SELECT COUNT(*) FROM board_posts bp
                           JOIN boards b ON bp.board_id=b.id
                           WHERE b.type='team' AND b.team_id=t.id
                           AND bp.approval_status='approved') AS post_count,
                          (SELECT COUNT(*) FROM board_posts bp
                           JOIN boards b ON bp.board_id=b.id
                           WHERE b.type='team' AND b.team_id=t.id
                           AND bp.approval_status='pending') AS pending_count
                   FROM teams t ORDER BY t.display_order"""
            ).fetchall()
        return ctx(req, "board_teams.html", user=u, active="board_team",
                   teams=teams)
    bid = board_get_or_create_team(tid)
    is_leader = _is_team_leader(u, tid)
    posts = board_posts_list(bid, include_pending=is_leader)
    pending = board_posts_pending(bid) if is_leader else []
    return ctx(req, "board_list.html", user=u, active="board_team",
               board_id=bid, board_name=f"{u.get('team_name','')} 게시판",
               board_type="team", team_id=tid,
               posts=posts, can_write=True, is_leader=is_leader,
               pending_count=len(pending), pending_posts=pending,
               CATEGORIES=BOARD_CATEGORIES)


@app.get("/board/team/{team_id}", response_class=HTMLResponse)
async def board_team_specific(req: Request, team_id: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    bid = board_get_or_create_team(team_id)
    is_leader = _is_team_leader(u, team_id)
    with db_session() as c:
        t = c.execute("SELECT name FROM teams WHERE id=?", (team_id,)).fetchone()
    team_name = t["name"] if t else f"팀{team_id}"
    posts = board_posts_list(bid, include_pending=is_leader)
    pending = board_posts_pending(bid) if is_leader else []
    can_write = (u.get("team_id") == team_id) or u["role"] in ("admin", "ceo", "executive")
    return ctx(req, "board_list.html", user=u, active="board_team",
               board_id=bid, board_name=f"{team_name} 게시판",
               board_type="team", team_id=team_id,
               posts=posts, can_write=can_write, is_leader=is_leader,
               pending_count=len(pending), pending_posts=pending,
               CATEGORIES=BOARD_CATEGORIES)


@app.get("/board/new", response_class=HTMLResponse)
async def board_new_form(req: Request, board_id: int = 0):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    return ctx(req, "board_form.html", user=u, active="board",
               board_id=board_id, post=None, CATEGORIES=BOARD_CATEGORIES)


@app.post("/board/new")
async def board_new_submit(req: Request,
                           board_id: int = Form(...),
                           title: str = Form(...),
                           body: str = Form(""),
                           category: str = Form("일반")):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    # 전사 게시판: admin/ceo/executive만 → 바로 approved
    # 부서 게시판: 팀장/경영진 → approved, 일반 부서원 → pending
    with db_session() as c:
        board = c.execute("SELECT type, team_id FROM boards WHERE id=?", (board_id,)).fetchone()
    if not board:
        return RedirectResponse("/home", 303)

    if board["type"] == "company":
        status = "approved"
        redirect_url = "/board/company"
    else:
        if _is_team_leader(u, board["team_id"]):
            status = "approved"
        else:
            status = "pending"
        redirect_url = f"/board/team/{board['team_id']}"

    board_post_create(board_id, u["id"], title, body, category, status)
    return RedirectResponse(redirect_url, 303)


@app.get("/board/post/{post_id}", response_class=HTMLResponse)
async def board_post_detail(req: Request, post_id: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    post = board_post_get(post_id)
    if not post:
        return RedirectResponse("/home", 303)
    board_post_increment_view(post_id)
    comments = board_comments_list(post_id)
    is_leader = _is_team_leader(u, post.get("board_team_id"))
    is_author = post["author_id"] == u["id"]
    return ctx(req, "board_detail.html", user=u, active="board",
               post=post, comments=comments,
               is_leader=is_leader, is_author=is_author)


@app.post("/board/post/{post_id}/comment")
async def board_add_comment(req: Request, post_id: int, body: str = Form(...)):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    board_comment_create(post_id, u["id"], body)
    return RedirectResponse(f"/board/post/{post_id}", 303)


@app.post("/board/post/{post_id}/approve")
async def board_approve(req: Request, post_id: int):
    # OPS-P1-G2 [D-006]: 게시글 승인 권한 명시 검증 (leader/admin/ceo 만)
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    post = board_post_get(post_id)
    if not post:
        return RedirectResponse("/home", 303)
    is_team_leader = _is_team_leader(u, post.get("board_team_id"))
    is_priv = u.get("role") in ("admin", "ceo")
    if not (is_team_leader or is_priv):
        raise HTTPException(403, "게시글 승인 권한이 없습니다 (팀장/관리자/대표 전용)")
    board_post_approve(post_id, u["id"])
    return RedirectResponse(f"/board/team/{post['board_team_id']}", 303)


@app.post("/board/post/{post_id}/reject")
async def board_reject(req: Request, post_id: int, reason: str = Form("")):
    # OPS-P1-G2 [D-006]: 게시글 반려 권한 명시 검증
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    post = board_post_get(post_id)
    if not post:
        return RedirectResponse("/home", 303)
    is_team_leader = _is_team_leader(u, post.get("board_team_id"))
    is_priv = u.get("role") in ("admin", "ceo")
    if not (is_team_leader or is_priv):
        raise HTTPException(403, "게시글 반려 권한이 없습니다 (팀장/관리자/대표 전용)")
    board_post_reject(post_id, u["id"], reason)
    return RedirectResponse(f"/board/team/{post['board_team_id']}", 303)


@app.post("/board/post/{post_id}/pin")
async def board_pin(req: Request, post_id: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    post = board_post_get(post_id)
    if post and _is_team_leader(u, post.get("board_team_id")):
        board_post_toggle_pin(post_id)
    redir = f"/board/team/{post['board_team_id']}" if post and post["board_type"] == "team" else "/board/company"
    return RedirectResponse(redir, 303)


@app.post("/board/post/{post_id}/delete")
async def board_delete(req: Request, post_id: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    post = board_post_get(post_id)
    if post and (post["author_id"] == u["id"] or _is_team_leader(u, post.get("board_team_id"))):
        board_post_delete(post_id)
    redir = f"/board/team/{post['board_team_id']}" if post and post["board_type"] == "team" else "/board/company"
    return RedirectResponse(redir, 303)


@app.post("/board/comment/{cid}/delete")
async def board_del_comment(req: Request, cid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        cm = c.execute("SELECT bc.post_id, bc.author_id FROM board_comments bc WHERE bc.id=?", (cid,)).fetchone()
    if cm and (cm["author_id"] == u["id"] or u["role"] in ("admin", "ceo")):
        board_comment_delete(cid)
        return RedirectResponse(f"/board/post/{cm['post_id']}", 303)
    return RedirectResponse("/home", 303)


# =====================================================
# HAIST WORKS — 물류 모듈 라우트
# =====================================================
from . import database as _logi


# ── 관리자: 물류 권한 토글 ─────────────────────────────
@app.post("/api/admin/user-logistics")
async def admin_toggle_logistics(request: Request,
                                 user_id: int = Form(...),
                                 can_use_logistics: str = Form("0")):
    me = require(request, roles=["admin", "ceo"])
    if not me:
        return JSONResponse({"ok": False, "error": "관리자 권한 필요"}, status_code=403)
    flag = 1 if can_use_logistics == "1" else 0
    with db_session() as c:
        c.execute(
            "UPDATE users SET can_use_logistics = ? WHERE id = ?",
            (flag, user_id),
        )
    return JSONResponse({"ok": True, "user_id": user_id, "can_use_logistics": flag})


# ── 자재·구매 홈 (기존 /logistics — 명칭 통일) ──────────────
@app.get("/logistics", response_class=HTMLResponse)
async def logi_dashboard(request: Request):
    """자재·구매 센터 (부품·공급사·발주·입출고·수불·환율)"""
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_logistics(u):
        return RedirectResponse("/home", 303)
    parts_stats = _logi.parts_count()
    from .database import stock_kpi as _stock_kpi
    try:
        s_kpi = _stock_kpi()
    except Exception:
        s_kpi = None
    return ctx(request, "logistics_home.html",
               user=u, active="logistics",
               parts_stats=parts_stats,
               stock_kpi=s_kpi)


# ── 매출·영업 홈 (신규 · 2026-04-21 도메인 분리) ──────────────
@app.get("/sales", response_class=HTMLResponse)
async def sales_dashboard(request: Request):
    """매출·영업 센터 (프로젝트·관리코드·고객사·수주·매출 KPI)"""
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    # Plan Y S1 회귀 #2: /sales 는 can_use_sales (도메인 분리). /logistics 와 권한 독립
    if not can_view_sales(u):
        return RedirectResponse("/home", 303)
    proj_stats = _logi.projects_count_logi()
    # 매출 KPI (Victor sales 핸들러와 동일 로직)
    today = date.today()
    ym = today.strftime("%Y-%m")
    year = today.year
    with db_session() as c:
        month = c.execute(
            """SELECT COALESCE(SUM(order_amount),0) AS total, COUNT(*) AS cnt
               FROM projects WHERE order_date LIKE ? AND order_amount > 0""",
            (f"{ym}%",)).fetchone()
        ytd = c.execute(
            """SELECT COALESCE(SUM(order_amount),0) AS total, COUNT(*) AS cnt
               FROM projects WHERE order_date LIKE ? AND order_amount > 0""",
            (f"{year}%",)).fetchone()
        by_biz = [dict(r) for r in c.execute(
            """SELECT biz_div, COALESCE(SUM(order_amount),0) AS total, COUNT(*) AS cnt
               FROM projects WHERE order_date LIKE ? AND biz_div IN ('T','M')
               GROUP BY biz_div""",
            (f"{year}%",)).fetchall()]
        by_stage = [dict(r) for r in c.execute(
            """SELECT stage, COUNT(*) AS cnt,
                      COALESCE(SUM(order_amount),0) AS amount
               FROM projects WHERE stage IS NOT NULL AND stage != ''
               GROUP BY stage ORDER BY cnt DESC"""
        ).fetchall()]
        recent = [dict(r) for r in c.execute(
            """SELECT id, mgmt_code, name, customer_name, stage, order_amount,
                      order_date, due_date, biz_div
               FROM projects
               WHERE mgmt_code IS NOT NULL AND mgmt_code != ''
               ORDER BY id DESC LIMIT 10""").fetchall()]
        customers_top = [dict(r) for r in c.execute(
            """SELECT customer_name, COUNT(*) AS cnt,
                      COALESCE(SUM(order_amount),0) AS total
               FROM projects
               WHERE customer_name IS NOT NULL AND customer_name != ''
                 AND order_date LIKE ?
               GROUP BY customer_name
               ORDER BY total DESC LIMIT 5""",
            (f"{year}%",)).fetchall()]
    sales_kpi = {
        "month_total": month["total"], "month_cnt": month["cnt"],
        "ytd_total": ytd["total"], "ytd_cnt": ytd["cnt"],
        "by_biz": by_biz, "by_stage": by_stage,
        "recent": recent, "top_customers": customers_top,
        "ym": ym, "year": year,
    }
    return ctx(request, "sales_home.html",
               user=u, active="sales",
               proj_stats=proj_stats, sales_kpi=sales_kpi)


# ── 부품 마스터 (parts) ────────────────────────────────
@app.get("/parts", response_class=HTMLResponse)
async def parts_list_page(request: Request, q: str = "", biz_div: str = "",
                          category: str = ""):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_logistics(u):
        return RedirectResponse("/home", 303)
    rows = _logi.parts_list(q=q, biz_div=biz_div, category=category)
    return ctx(request, "parts.html",
               user=u, active="parts",
               parts=rows, q=q, biz_div=biz_div, category=category)


@app.get("/parts/new", response_class=HTMLResponse)
async def parts_new_form(request: Request):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    return ctx(request, "part_form.html", user=u, active="parts", part=None)


@app.post("/parts/new")
async def parts_new_submit(
    request: Request,
    part_no: str = Form(...), part_name: str = Form(...),
    spec: str = Form(""), maker: str = Form(""), origin: str = Form(""),
    unit: str = Form("EA"), currency: str = Form("KRW"),
    std_price: str = Form("0"), biz_div: str = Form(""),
    category: str = Form(""), note: str = Form(""), is_active: str = Form("1"),
    safety_stock: str = Form("0"), location: str = Form(""),
):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(_u):
        return RedirectResponse("/home", 303)
    _logi.parts_create({
        "part_no": part_no, "part_name": part_name, "spec": spec,
        "maker": maker, "origin": origin, "unit": unit,
        "currency": currency, "std_price": std_price,
        "biz_div": biz_div, "category": category, "note": note,
        "is_active": is_active,
        "safety_stock": safety_stock, "location": location,
    })
    return RedirectResponse("/parts", status_code=303)


@app.get("/parts/{pid}/edit", response_class=HTMLResponse)
async def parts_edit_form(request: Request, pid: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    p = _logi.parts_get(pid)
    if not p:
        return RedirectResponse("/parts", status_code=303)
    return ctx(request, "part_form.html", user=u, active="parts", part=p)


@app.post("/parts/{pid}/edit")
async def parts_edit_submit(
    request: Request,
    pid: int, part_no: str = Form(...), part_name: str = Form(...),
    spec: str = Form(""), maker: str = Form(""), origin: str = Form(""),
    unit: str = Form("EA"), currency: str = Form("KRW"),
    std_price: str = Form("0"), biz_div: str = Form(""),
    category: str = Form(""), note: str = Form(""), is_active: str = Form("1"),
    safety_stock: str = Form("0"), location: str = Form(""),
):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(_u):
        return RedirectResponse("/home", 303)
    _logi.parts_update(pid, {
        "part_no": part_no, "part_name": part_name, "spec": spec,
        "maker": maker, "origin": origin, "unit": unit,
        "currency": currency, "std_price": std_price,
        "biz_div": biz_div, "category": category, "note": note,
        "is_active": is_active,
        "safety_stock": safety_stock, "location": location,
    })
    return RedirectResponse("/parts", status_code=303)


@app.post("/parts/{pid}/delete")
async def parts_delete_submit(request: Request, pid: int):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(_u):
        return RedirectResponse("/home", 303)
    _logi.parts_delete(pid)
    return RedirectResponse("/parts", status_code=303)


# ── 프로젝트 / 관리코드 발행대장 ─────────────────────────
@app.get("/projects", response_class=HTMLResponse)
async def projects_list_page(request: Request, q: str = "", biz_div: str = "",
                             stage: str = "", status: str = ""):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_sales(u):
        return RedirectResponse("/home", 303)
    rows = _logi.projects_list_logi(q=q, biz_div=biz_div, stage=stage, status=status)
    return ctx(request, "projects.html",
               user=u, active="sales_projects",
               projects=rows, q=q, biz_div=biz_div, stage=stage, status=status,
               STAGES=_logi.STAGES, STATUSES=_logi.LOGI_STATUSES)


@app.get("/projects/new", response_class=HTMLResponse)
async def projects_new_form(request: Request):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_sales(u):
        return RedirectResponse("/home", 303)
    return ctx(request, "project_form.html",
               user=u, active="sales_projects",
               project=None,
               STAGES=_logi.STAGES, STATUSES=_logi.LOGI_STATUSES,
               PO_TYPES=_logi.PO_TYPES)


@app.post("/projects/new")
async def projects_new_submit(
    request: Request,
    biz_div: str = Form(...), project_name: str = Form(...),
    customer: str = Form(""), model: str = Form(""),
    stage: str = Form("제안작성"), po_type: str = Form("신규"),
    status: str = Form("수주예정"), customer_po: str = Form(""),
    currency: str = Form("KRW"), order_amount: str = Form("0"),
    order_date: str = Form(""), due_date: str = Form(""),
    pm: str = Form(""), sales: str = Form(""), note: str = Form(""),
):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_sales(_u):
        return RedirectResponse("/home", 303)
    _logi.projects_create_logi({
        "biz_div": biz_div, "project_name": project_name, "customer": customer,
        "model": model, "stage": stage, "po_type": po_type, "status": status,
        "customer_po": customer_po, "currency": currency,
        "order_amount": order_amount, "order_date": order_date, "due_date": due_date,
        "pm": pm, "sales": sales, "note": note,
    })
    return RedirectResponse("/projects", status_code=303)


@app.get("/projects/{pid}/edit", response_class=HTMLResponse)
async def projects_edit_form(request: Request, pid: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_sales(u):
        return RedirectResponse("/home", 303)
    p = _logi.projects_get_logi(pid)
    if not p:
        return RedirectResponse("/projects", status_code=303)
    return ctx(request, "project_form.html",
               user=u, active="sales_projects",
               project=p,
               STAGES=_logi.STAGES, STATUSES=_logi.LOGI_STATUSES,
               PO_TYPES=_logi.PO_TYPES)


@app.post("/projects/{pid}/edit")
async def projects_edit_submit(
    request: Request,
    pid: int, biz_div: str = Form(...), project_name: str = Form(...),
    customer: str = Form(""), model: str = Form(""),
    stage: str = Form("제안작성"), po_type: str = Form("신규"),
    status: str = Form("수주예정"), customer_po: str = Form(""),
    currency: str = Form("KRW"), order_amount: str = Form("0"),
    order_date: str = Form(""), due_date: str = Form(""),
    pm: str = Form(""), sales: str = Form(""), note: str = Form(""),
):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_sales(_u):
        return RedirectResponse("/home", 303)
    _logi.projects_update_logi(pid, {
        "biz_div": biz_div, "project_name": project_name, "customer": customer,
        "model": model, "stage": stage, "po_type": po_type, "status": status,
        "customer_po": customer_po, "currency": currency,
        "order_amount": order_amount, "order_date": order_date, "due_date": due_date,
        "pm": pm, "sales": sales, "note": note,
    })
    return RedirectResponse("/projects", status_code=303)


@app.post("/projects/{pid}/delete")
async def projects_delete_submit(request: Request, pid: int):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_sales(_u):
        return RedirectResponse("/home", 303)
    _logi.projects_delete_logi(pid)
    return RedirectResponse("/projects", status_code=303)


# =====================================================
# HAIST WORKS — 공급사 (suppliers) 라우트
# =====================================================
@app.get("/suppliers", response_class=HTMLResponse)
async def suppliers_list_page(request: Request, q: str = ""):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_logistics(u):
        return RedirectResponse("/home", 303)
    rows = _logi.suppliers_list(q=q)
    return ctx(request, "suppliers.html",
               user=u, active="suppliers",
               suppliers=rows, q=q)


@app.get("/suppliers/new", response_class=HTMLResponse)
async def suppliers_new_form(request: Request):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    return ctx(request, "supplier_form.html",
               user=u, active="suppliers", supplier=None,
               PAYMENT_TERMS=_logi.PAYMENT_TERMS)


@app.post("/suppliers/new")
async def suppliers_new_submit(
    request: Request,
    name: str = Form(...), code: str = Form(""), contact: str = Form(""),
    email: str = Form(""), phone: str = Form(""), country: str = Form(""),
    currency: str = Form("KRW"), payment_terms: str = Form(""),
    note: str = Form(""), is_active: str = Form("1"),
):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(_u):
        return RedirectResponse("/home", 303)
    _logi.supplier_create({
        "name": name, "code": code, "contact": contact, "email": email,
        "phone": phone, "country": country, "currency": currency,
        "payment_terms": payment_terms, "note": note, "is_active": is_active,
    })
    return RedirectResponse("/suppliers", status_code=303)


@app.get("/suppliers/{sid}/edit", response_class=HTMLResponse)
async def suppliers_edit_form(request: Request, sid: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    s = _logi.supplier_get(sid)
    if not s:
        return RedirectResponse("/suppliers", 303)
    # 리드타임 통계 자동 계산 (동적 변수 ⑤)
    leadtime = supplier_leadtime_stats(sid)
    return ctx(request, "supplier_form.html",
               user=u, active="suppliers", supplier=s,
               leadtime=leadtime,
               PAYMENT_TERMS=_logi.PAYMENT_TERMS)


@app.post("/suppliers/{sid}/edit")
async def suppliers_edit_submit(
    request: Request, sid: int,
    name: str = Form(...), code: str = Form(""), contact: str = Form(""),
    email: str = Form(""), phone: str = Form(""), country: str = Form(""),
    currency: str = Form("KRW"), payment_terms: str = Form(""),
    note: str = Form(""), is_active: str = Form("1"),
):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(_u):
        return RedirectResponse("/home", 303)
    _logi.supplier_update(sid, {
        "name": name, "code": code, "contact": contact, "email": email,
        "phone": phone, "country": country, "currency": currency,
        "payment_terms": payment_terms, "note": note, "is_active": is_active,
    })
    return RedirectResponse("/suppliers", status_code=303)


@app.post("/suppliers/{sid}/delete")
async def suppliers_delete_submit(request: Request, sid: int):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(_u):
        return RedirectResponse("/home", 303)
    _logi.supplier_delete(sid)
    return RedirectResponse("/suppliers", status_code=303)


# =====================================================
# HAIST WORKS — 발주 (purchase_orders) 라우트
# =====================================================
@app.get("/po", response_class=HTMLResponse)
async def po_list_page(request: Request, q: str = "", status: str = ""):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_logistics(u):
        return RedirectResponse("/home", 303)
    rows = _logi.po_list(q=q, status=status)
    return ctx(request, "po_list.html",
               user=u, active="po",
               orders=rows, q=q, status=status,
               PO_STATUSES=_logi.PO_STATUSES)


@app.get("/po/new", response_class=HTMLResponse)
async def po_new_form(request: Request):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    # 드롭다운용 데이터
    suppliers = _logi.suppliers_list(active_only=True)
    # 관리코드 발급된 프로젝트만 선택 가능
    projects = _logi.projects_list_logi()
    projects_with_code = [p for p in projects if p["mgmt_code"]]
    parts_all = _logi.parts_list()
    return ctx(request, "po_form.html",
               user=u, active="po", po=None, items=[],
               suppliers=suppliers, projects=projects_with_code,
               parts_all=parts_all,
               PO_STATUSES=_logi.PO_STATUSES,
               SHIPPING_TERMS=_logi.SHIPPING_TERMS,
               PAYMENT_TERMS=_logi.PAYMENT_TERMS,
               PO_TYPES_KIND=_logi.PO_TYPES_KIND)


@app.post("/po/new")
async def po_new_submit(request: Request):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    form = await request.form()
    header = {
        "project_id": form.get("project_id", ""),
        "supplier_id": form.get("supplier_id", ""),
        "order_date": form.get("order_date", ""),
        "expected_date": form.get("expected_date", ""),
        "currency": form.get("currency", "KRW"),
        "exchange_rate": form.get("exchange_rate", "1"),
        "status": form.get("status", "작성중"),
        "shipping_terms": form.get("shipping_terms", ""),
        "payment_terms": form.get("payment_terms", ""),
        "po_type": form.get("po_type", "일반"),
        "note": form.get("note", ""),
    }
    # 라인 파싱: item_part_id[], item_qty[], item_price[], item_delivery[], item_note[]
    part_ids = form.getlist("item_part_id")
    qtys = form.getlist("item_qty")
    prices = form.getlist("item_price")
    delivs = form.getlist("item_delivery")
    notes = form.getlist("item_note")
    items = []
    for i, pid in enumerate(part_ids):
        if not pid and not (qtys[i] if i < len(qtys) else ""):
            continue
        items.append({
            "part_id": pid,
            "quantity": qtys[i] if i < len(qtys) else "0",
            "unit_price": prices[i] if i < len(prices) else "0",
            "delivery_date": delivs[i] if i < len(delivs) else "",
            "note": notes[i] if i < len(notes) else "",
        })
    po_id, po_num = _logi.po_create(header, items, created_by=u["id"])
    return RedirectResponse(f"/po/{po_id}", status_code=303)


@app.get("/po/{po_id}", response_class=HTMLResponse)
async def po_detail(request: Request, po_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    header, items = _logi.po_get(po_id)
    if not header:
        return RedirectResponse("/po", 303)
    return ctx(request, "po_detail.html",
               user=u, active="po", po=header, items=items)


@app.get("/po/{po_id}/edit", response_class=HTMLResponse)
async def po_edit_form(request: Request, po_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    header, items = _logi.po_get(po_id)
    if not header:
        return RedirectResponse("/po", 303)
    suppliers = _logi.suppliers_list(active_only=True)
    projects = [p for p in _logi.projects_list_logi() if p["mgmt_code"]]
    parts_all = _logi.parts_list()
    return ctx(request, "po_form.html",
               user=u, active="po", po=header, items=items,
               suppliers=suppliers, projects=projects,
               parts_all=parts_all,
               PO_STATUSES=_logi.PO_STATUSES,
               SHIPPING_TERMS=_logi.SHIPPING_TERMS,
               PAYMENT_TERMS=_logi.PAYMENT_TERMS,
               PO_TYPES_KIND=_logi.PO_TYPES_KIND)


@app.post("/po/{po_id}/edit")
async def po_edit_submit(request: Request, po_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    form = await request.form()
    header = {
        "project_id": form.get("project_id", ""),
        "supplier_id": form.get("supplier_id", ""),
        "order_date": form.get("order_date", ""),
        "expected_date": form.get("expected_date", ""),
        "currency": form.get("currency", "KRW"),
        "exchange_rate": form.get("exchange_rate", "1"),
        "status": form.get("status", "작성중"),
        "shipping_terms": form.get("shipping_terms", ""),
        "payment_terms": form.get("payment_terms", ""),
        "po_type": form.get("po_type", "일반"),
        "note": form.get("note", ""),
    }
    part_ids = form.getlist("item_part_id")
    qtys = form.getlist("item_qty")
    prices = form.getlist("item_price")
    delivs = form.getlist("item_delivery")
    notes = form.getlist("item_note")
    items = []
    for i, pid in enumerate(part_ids):
        if not pid and not (qtys[i] if i < len(qtys) else ""):
            continue
        items.append({
            "part_id": pid,
            "quantity": qtys[i] if i < len(qtys) else "0",
            "unit_price": prices[i] if i < len(prices) else "0",
            "delivery_date": delivs[i] if i < len(delivs) else "",
            "note": notes[i] if i < len(notes) else "",
        })
    _logi.po_update(po_id, header, items)
    return RedirectResponse(f"/po/{po_id}", status_code=303)


@app.post("/po/{po_id}/delete")
async def po_delete_submit(request: Request, po_id: int):
    _u = get_user(request)
    if not _u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(_u):
        return RedirectResponse("/home", 303)
    _logi.po_delete(po_id)
    return RedirectResponse("/po", status_code=303)


# =====================================================
# 입고·출고·수불부 (2026-04-20 물류 본질 완성)
# =====================================================
from .database import (stock_movement_create, po_receive, stock_issue,
                        stock_adjust, stock_movements_list, stock_kpi,
                        part_stock_history, part_fifo_layers, part_price_history,
                        # Top3 S2 3차 (2026-04-26): FIFO 강화 + ABC + 회전율
                        fifo_layers, abc_classification, stock_turnover,
                        MOVEMENT_KINDS, MOVEMENT_KIND_LABEL,
                        gen_movement_no,
                        exchange_rate_create, exchange_rates_list, exchange_rates_latest,
                        get_exchange_rate, CURRENCIES,
                        part_price_create, part_price_approve, part_prices_list,
                        part_active_price, PRICE_TYPES,
                        supplier_leadtime_stats,
                        # 재고 실사·조정 (Top10 #10 — 2026-04-26)
                        stock_audit_create, stock_audits_list, stock_audit_get,
                        stock_audit_item_upsert, stock_adjustments_list,
                        stock_adjustment_approve, stock_adjustment_reject,
                        # 재고실사 2차 (2026-04-26): 첨부 + close + 효과
                        audit_attachment_create, audit_attachments_list,
                        audit_attachment_get, stock_audit_close,
                        stock_audit_effect_summary,
                        # 환율·단가 강화 (Top10 #9 — 2026-04-26)
                        cost_simulation_create, cost_simulations_list,
                        price_change_log, price_change_history_list,
                        rate_alert_create, rate_alerts_list,
                        exchange_rates_csv_upload,
                        # 발견 3건 통합 (2026-04-26)
                        check_rate_alerts,
                        # 사이클 54 환율·단가 1차 (2026-04-27)
                        get_latest_fx_rate, convert_amount,
                        get_latest_part_price)


# =====================================================
# 환율 관리 (동적 변수 ③)
# =====================================================
@app.get("/rates", response_class=HTMLResponse)
async def rates_page(request: Request, currency: str = ""):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    items = exchange_rates_list(limit=200, currency=currency)
    latest = exchange_rates_latest()
    return ctx(request, "rates.html", user=u, items=items, latest=latest,
               currency=currency, CURRENCIES=CURRENCIES, active="rates")


@app.post("/rates/new")
async def rates_create_submit(
    request: Request,
    rate_date: str = Form(...),
    from_currency: str = Form(...),
    to_currency: str = Form("KRW"),
    rate: str = Form(...),
    source: str = Form("수동"),
    note: str = Form(""),
):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    try:
        exchange_rate_create({
            "rate_date": rate_date,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": float(rate),
            "source": source,
            "note": note,
        }, user_id=u["id"])
        # S3-1 옵션 A: 수동 등록 시점에도 자동 알림 발동 검사
        check_rate_alerts(from_currency, float(rate))
    except Exception as e:
        return RedirectResponse(f"/rates?error={e}", 303)
    return RedirectResponse("/rates?success=1", 303)


# =====================================================
# 적용일자 단가 (동적 변수 ②)
# =====================================================
@app.post("/parts/{pid}/prices/new")
async def parts_price_create_submit(
    request: Request, pid: int,
    supplier_id: str = Form(""),
    price_type: str = Form("견적"),
    unit_price: str = Form(...),
    currency: str = Form("KRW"),
    effective_from: str = Form(...),
    effective_to: str = Form(""),
    negotiated_at: str = Form(""),
    min_qty: str = Form("0"),
    max_qty: str = Form(""),
    note: str = Form(""),
):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    sid = int(supplier_id) if supplier_id.isdigit() else None
    new_price = float(unit_price)
    # S4-1 옵션 A: 직전 활성 단가 조회 (애플리케이션 레벨 훅)
    prev = part_active_price(pid, supplier_id=sid or 0) or {}
    old_price = prev.get("unit_price")
    try:
        part_price_create({
            "part_id": pid,
            "supplier_id": sid,
            "price_type": price_type,
            "unit_price": new_price,
            "currency": currency,
            "effective_from": effective_from,
            "effective_to": effective_to or None,
            "negotiated_at": negotiated_at or None,
            "min_qty": float(min_qty or 0),
            "max_qty": float(max_qty) if max_qty else None,
            "note": note,
        }, user_id=u["id"])
        # S4-1 옵션 A: price_change_history 자동 INSERT (변동률 자동 계산)
        try:
            price_change_log(pid, sid, old_price, new_price,
                             effective_from, u["id"], note=note or "")
        except Exception:
            pass  # 본 등록은 성공했으므로 훅 실패는 흡수
    except Exception as e:
        return RedirectResponse(f"/parts/{pid}?error={e}", 303)
    return RedirectResponse(f"/parts/{pid}?price_added=1", 303)


@app.post("/parts/prices/{price_id}/approve")
async def parts_price_approve_submit(request: Request, price_id: int):
    u = get_user(request)
    if not u or u["role"] not in ("admin", "ceo", "leader", "executive"):
        return JSONResponse({"error": "권한 없음"}, 401)
    with db_session() as c:
        row = c.execute("SELECT part_id FROM part_prices WHERE id=?", (price_id,)).fetchone()
    part_price_approve(price_id, user_id=u["id"])
    pid = row["part_id"] if row else 0
    return RedirectResponse(f"/parts/{pid}?approved=1", 303)


@app.get("/parts/{pid}", response_class=HTMLResponse)
async def parts_detail_page(request: Request, pid: int):
    """부품 상세 — FIFO 레이어, 공급사 단가 이력, 적용일자 단가, 입출고 이력 통합"""
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    part = _logi.parts_get(pid)
    if not part:
        return RedirectResponse("/parts", 303)
    layers = part_fifo_layers(pid)
    price_hist = part_price_history(pid, limit=30)
    recent_moves = part_stock_history(pid, limit=30)
    stock_value = sum((l.get("remaining_qty") or 0) * (l.get("unit_price") or 0) for l in layers)
    # 적용일자 단가 (동적 변수 ②)
    managed_prices = part_prices_list(pid)
    active_price = part_active_price(pid)
    # 공급사 선택지 (단가 등록 폼용)
    with db_session() as c:
        suppliers = [dict(r) for r in c.execute(
            "SELECT id, name FROM suppliers WHERE is_active=1 ORDER BY name"
        ).fetchall()]
    return ctx(request, "part_detail.html", user=u,
               part=dict(part), layers=layers,
               price_history=price_hist["history"],
               by_supplier=price_hist["by_supplier"],
               managed_prices=managed_prices,
               active_price=active_price,
               recent_moves=recent_moves,
               stock_value=stock_value,
               suppliers=suppliers,
               CURRENCIES=CURRENCIES, PRICE_TYPES=PRICE_TYPES,
               active="parts")


@app.get("/po/{po_id}/receive", response_class=HTMLResponse)
async def po_receive_form(request: Request, po_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    header, items = _logi.po_get(po_id)
    if not header:
        return RedirectResponse("/po", 303)
    po_ctx = dict(header)
    po_ctx["items"] = [dict(r) for r in items]
    return ctx(request, "po_receive.html", user=u, po=po_ctx, active="po")


@app.post("/po/{po_id}/receive")
async def po_receive_submit(request: Request, po_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    form = await request.form()
    occurred = form.get("occurred_at", "") or ""
    item_ids = form.getlist("po_item_id")
    qtys = form.getlist("receive_qty")
    notes = form.getlist("item_note")
    lots = form.getlist("lot_no")
    expiries = form.getlist("expiry_date")
    lines = []
    for i, iid in enumerate(item_ids):
        try:
            q = float(qtys[i]) if i < len(qtys) and qtys[i] else 0
        except ValueError:
            q = 0
        if q > 0:
            lines.append({
                "po_item_id": int(iid),
                "receive_qty": q,
                "note": notes[i] if i < len(notes) else "",
                "lot_no": lots[i] if i < len(lots) else "",
                "expiry_date": expiries[i] if i < len(expiries) else "",
            })
    if not lines:
        return RedirectResponse(f"/po/{po_id}/receive?error=empty", 303)
    result = po_receive(po_id, lines, u["id"], occurred_at=occurred)
    if not result.get("ok"):
        return RedirectResponse(f"/po/{po_id}/receive?error=1", 303)
    return RedirectResponse(f"/po/{po_id}?received={result['count']}", 303)


@app.get("/stock/issue", response_class=HTMLResponse)
async def stock_issue_form(request: Request, part_id: str = ""):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_logistics(u):
        return RedirectResponse("/home", 303)
    with db_session() as c:
        parts = c.execute(
            """SELECT id, part_no, part_name, unit, stock_qty, std_price, safety_stock
               FROM parts WHERE is_active=1 ORDER BY part_name"""
        ).fetchall()
        projects = c.execute(
            """SELECT id, mgmt_code, name FROM projects
               WHERE status IN ('active','진행중','planning','수주확정','납품')
               ORDER BY mgmt_code DESC LIMIT 200"""
        ).fetchall()
        customers = c.execute(
            "SELECT id, name FROM customers ORDER BY tier DESC, name"
        ).fetchall()
    return ctx(request, "stock_issue.html", user=u,
               parts=[dict(r) for r in parts],
               projects=[dict(r) for r in projects],
               customers=[dict(r) for r in customers],
               default_part_id=part_id, active="stock_issue")


@app.post("/stock/issue")
async def stock_issue_submit(
    request: Request,
    part_id: str = Form(...),
    quantity: str = Form(...),
    project_id: str = Form(""),
    customer_id: str = Form(""),
    unit_price: str = Form("0"),
    reason: str = Form("현장 출고"),
    location: str = Form(""),
    occurred_at: str = Form(""),
    note: str = Form(""),
):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_logistics(u):
        return RedirectResponse("/home", 303)
    try:
        pid = int(part_id)
        qty = float(quantity)
    except ValueError:
        return RedirectResponse("/stock/issue?error=invalid", 303)
    if qty <= 0:
        return RedirectResponse("/stock/issue?error=qty", 303)
    try:
        mid, mno = stock_issue({
            "part_id": pid,
            "quantity": qty,
            "project_id": int(project_id) if project_id.isdigit() else None,
            "customer_id": int(customer_id) if customer_id.isdigit() else None,
            "unit_price": float(unit_price or 0),
            "reason": reason,
            "location": location,
            "occurred_at": occurred_at or None,
            "note": note,
        }, u["id"])
    except ValueError as e:
        return RedirectResponse(f"/stock/issue?error={e}", 303)
    return RedirectResponse(f"/stock/movements?success={mno}", 303)


@app.get("/stock/adjust", response_class=HTMLResponse)
async def stock_adjust_form(request: Request, part_id: str = ""):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_logistics(u):
        return RedirectResponse("/home", 303)
    with db_session() as c:
        parts = c.execute(
            """SELECT id, part_no, part_name, unit, stock_qty
               FROM parts WHERE is_active=1 ORDER BY part_name"""
        ).fetchall()
    return ctx(request, "stock_adjust.html", user=u,
               parts=[dict(r) for r in parts],
               default_part_id=part_id, active="stock_adjust")


@app.post("/stock/adjust")
async def stock_adjust_submit(
    request: Request,
    part_id: str = Form(...),
    quantity: str = Form(...),
    reason: str = Form(...),
    note: str = Form(""),
):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_logistics(u):
        return RedirectResponse("/home", 303)
    try:
        pid = int(part_id)
        qty = float(quantity)
    except ValueError:
        return RedirectResponse("/stock/adjust?error=invalid", 303)
    stock_adjust({
        "part_id": pid,
        "quantity": qty,
        "reason": reason,
        "note": note,
    }, u["id"])
    return RedirectResponse("/stock/movements?success=adjust", 303)


# =====================================================
# 재고 실사·조정 워크플로 (Top10 #10 — 2026-04-26 P4 자재팀 분기 1회)
# - 자재팀(can_use_logistics) + admin/ceo: 실사 진행 가능
# - 조정 승인: admin/ceo/executive 또는 team_id==10(구매팀) leader (자재팀장)
# =====================================================
def _audit_guard(u) -> bool:
    """실사 화면 접근 권한 — 물류 권한자."""
    return bool(u) and can_use_logistics(u)


def _audit_approve_guard(u) -> bool:
    """조정 승인 권한 — admin/ceo/executive 또는 자재팀장(team_id=10 leader)."""
    if not u:
        return False
    role = u.get("role") if isinstance(u, dict) else u["role"]
    if role in ("admin", "ceo", "executive"):
        return True
    team_id = u.get("team_id") if isinstance(u, dict) else u["team_id"]
    if team_id == 10 and role == "leader":
        return True
    return False


@app.get("/stock/audits", response_class=HTMLResponse)
async def stock_audits_page(request: Request):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_guard(u):
        return RedirectResponse("/home", 303)
    audits = stock_audits_list(limit=50)
    return ctx(request, "stock_audits.html", user=u, audits=audits,
               can_approve=_audit_approve_guard(u), active="stock")


@app.post("/stock/audits/new")
async def stock_audits_new(request: Request, note: str = Form("")):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_guard(u):
        return RedirectResponse("/home", 303)
    aid, ano = stock_audit_create(led_by=u["id"], note=note)
    return RedirectResponse(f"/stock/audits/{aid}?success={ano}", 303)


@app.get("/stock/audits/{audit_id}", response_class=HTMLResponse)
async def stock_audit_detail(request: Request, audit_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_guard(u):
        return RedirectResponse("/home", 303)
    audit = stock_audit_get(audit_id)
    if not audit:
        return RedirectResponse("/stock/audits", 303)
    with db_session() as c:
        parts = c.execute(
            """SELECT id, part_no, part_name, unit, stock_qty
               FROM parts WHERE is_active=1 ORDER BY part_name LIMIT 500"""
        ).fetchall()
        # close 가능 조건 사전 계산
        pending_lines = c.execute(
            "SELECT COUNT(*) FROM stock_audit_items WHERE audit_id=? AND status='PENDING'",
            (audit_id,),
        ).fetchone()[0]
        pending_adjs = c.execute(
            """SELECT COUNT(*) FROM stock_adjustments adj
               JOIN stock_audit_items ai ON adj.audit_item_id=ai.id
               WHERE ai.audit_id=? AND adj.status='PENDING'""",
            (audit_id,),
        ).fetchone()[0]
    can_close = (audit["status"] != "CLOSED" and pending_lines == 0
                 and pending_adjs == 0 and (audit["items"] or []))
    effect = stock_audit_effect_summary(audit_id)
    return ctx(request, "stock_audit.html", user=u, mode="detail",
               audits=[], audit=audit, parts=[dict(r) for r in parts],
               can_approve=_audit_approve_guard(u),
               can_close=bool(can_close), pending_lines=pending_lines,
               pending_adjs=pending_adjs, effect=effect, active="stock")


@app.post("/stock/audits/{audit_id}/items")
async def stock_audit_item_add(
    request: Request, audit_id: int,
    part_id: str = Form(...),
    counted_qty: str = Form(...),
    variance_reason: str = Form(""),
):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_guard(u):
        return RedirectResponse("/home", 303)
    try:
        pid = int(part_id)
        cq = float(counted_qty)
    except ValueError:
        return RedirectResponse(f"/stock/audits/{audit_id}?error=invalid", 303)
    stock_audit_item_upsert(audit_id, pid, cq, variance_reason.strip(), u["id"])
    return RedirectResponse(f"/stock/audits/{audit_id}?success=line", 303)


@app.get("/stock/adjustments", response_class=HTMLResponse)
async def stock_adjustments_page(request: Request, status: str = "PENDING"):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_guard(u):
        return RedirectResponse("/home", 303)
    items = stock_adjustments_list(status=status, limit=200)
    # 첨부 카운트 (라인 옆 표시용)
    att_counts = {}
    if items:
        with db_session() as c:
            ids = [int(x["id"]) for x in items]
            qmarks = ",".join("?" * len(ids))
            rows = c.execute(
                f"SELECT adjustment_id, COUNT(*) AS cnt FROM audit_attachments "
                f"WHERE adjustment_id IN ({qmarks}) GROUP BY adjustment_id",
                ids,
            ).fetchall()
            att_counts = {r["adjustment_id"]: r["cnt"] for r in rows}
    return ctx(request, "stock_adjustment.html", user=u,
               adjustments=items, filter_status=status, att_counts=att_counts,
               can_approve=_audit_approve_guard(u), active="stock")


@app.post("/stock/adjustments/{adj_id}/approve")
async def stock_adjustments_approve(request: Request, adj_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_approve_guard(u):
        return RedirectResponse("/stock/adjustments?error=denied", 303)
    try:
        _mid, mno = stock_adjustment_approve(adj_id, u["id"])
    except ValueError as e:
        return RedirectResponse(f"/stock/adjustments?error={e}", 303)
    return RedirectResponse(f"/stock/adjustments?success={mno}", 303)


@app.post("/stock/adjustments/{adj_id}/reject")
async def stock_adjustments_reject(request: Request, adj_id: int,
                                   note: str = Form("")):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_approve_guard(u):
        return RedirectResponse("/stock/adjustments?error=denied", 303)
    stock_adjustment_reject(adj_id, u["id"], note=note.strip())
    return RedirectResponse("/stock/adjustments?success=rejected", 303)


# =====================================================
# 재고실사 2차 (2026-04-26): 증명서 첨부 + close 워크플로
# 외부 파일 저장소 0건 — 로컬 디스크 ./uploads/audits/<adj_id>/<file>
# =====================================================
_AUDIT_UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "audits")
_AUDIT_ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".xlsx"}
_AUDIT_MAX_BYTES = 10 * 1024 * 1024  # 10MB


def _audit_safe_filename(name: str) -> str:
    """path traversal 방지 — basename만 + 영숫자/._- 외 _로 치환."""
    base = os.path.basename((name or "").replace("\\", "/"))
    base = base.lstrip(".") or "file"
    out = []
    for ch in base:
        if ch.isalnum() or ch in "._-":
            out.append(ch)
        else:
            out.append("_")
    safe = "".join(out)[:120]
    return safe or "file"


@app.post("/stock/adjustments/{adj_id}/attach")
async def stock_adjustment_attach(request: Request, adj_id: int,
                                  file: UploadFile = File(...)):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_guard(u):
        return RedirectResponse("/home", 303)
    raw = await file.read()
    if len(raw) > _AUDIT_MAX_BYTES:
        return RedirectResponse(f"/stock/adjustments?error=size_over_10MB", 303)
    if len(raw) == 0:
        return RedirectResponse("/stock/adjustments?error=empty_file", 303)
    safe_name = _audit_safe_filename(file.filename or "upload")
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in _AUDIT_ALLOWED_EXT:
        return RedirectResponse("/stock/adjustments?error=ext_not_allowed", 303)
    target_dir = os.path.join(_AUDIT_UPLOAD_ROOT, str(int(adj_id)))
    os.makedirs(target_dir, exist_ok=True)
    # 동명파일 충돌 회피 — 타임스탬프 prefix
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    final_name = f"{ts}_{safe_name}"
    final_path = os.path.join(target_dir, final_name)
    # path traversal 2차 검증 — 정규화 후 root 안에 있는지
    abs_root = os.path.abspath(_AUDIT_UPLOAD_ROOT)
    abs_final = os.path.abspath(final_path)
    if not abs_final.startswith(abs_root + os.sep):
        return RedirectResponse("/stock/adjustments?error=path_invalid", 303)
    with open(final_path, "wb") as f:
        f.write(raw)
    audit_attachment_create(adj_id, abs_final, safe_name, u["id"])
    return RedirectResponse(f"/stock/adjustments/{adj_id}/attachments?success=uploaded", 303)


@app.get("/stock/adjustments/{adj_id}/attachments", response_class=HTMLResponse)
async def stock_adjustment_attachments_page(request: Request, adj_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_guard(u):
        return RedirectResponse("/home", 303)
    atts = audit_attachments_list(adj_id)
    return ctx(request, "stock_adjustment.html", user=u,
               adjustments=[], filter_status="ATTACH", att_counts={},
               attach_view=True, attach_adj_id=adj_id, attachments=atts,
               can_approve=_audit_approve_guard(u), active="stock")


@app.get("/stock/adjustments/{adj_id}/attachments/{att_id}/download")
async def stock_adjustment_attachment_download(request: Request, adj_id: int, att_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_guard(u):
        return RedirectResponse("/home", 303)
    rec = audit_attachment_get(att_id)
    if not rec or int(rec["adjustment_id"]) != int(adj_id):
        return RedirectResponse(f"/stock/adjustments/{adj_id}/attachments?error=not_found", 303)
    fp = rec["file_path"]
    abs_root = os.path.abspath(_AUDIT_UPLOAD_ROOT)
    abs_fp = os.path.abspath(fp)
    if not abs_fp.startswith(abs_root + os.sep) or not os.path.exists(abs_fp):
        return RedirectResponse(f"/stock/adjustments/{adj_id}/attachments?error=file_missing", 303)
    return FileResponse(abs_fp, filename=rec.get("file_name") or os.path.basename(abs_fp))


@app.post("/stock/audits/{audit_id}/close")
async def stock_audits_close_route(request: Request, audit_id: int):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _audit_approve_guard(u):
        return RedirectResponse(f"/stock/audits/{audit_id}?error=denied", 303)
    ok, msg = stock_audit_close(audit_id)
    if not ok:
        return RedirectResponse(f"/stock/audits/{audit_id}?error={msg}", 303)
    return RedirectResponse(f"/stock/audits/{audit_id}?success=closed", 303)
# ===== /재고실사 2차 =====


@app.get("/stock/movements", response_class=HTMLResponse)
async def stock_movements_page(
    request: Request,
    part_id: str = "",
    kind: str = "",
    since: str = "",
    until: str = "",
    po_id: str = "",
    project_id: str = "",
    q: str = "",
):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_view_logistics(u):
        return RedirectResponse("/home", 303)
    items = stock_movements_list(
        part_id=int(part_id) if part_id.isdigit() else 0,
        kind=kind,
        since=since, until=until,
        po_id=int(po_id) if po_id.isdigit() else 0,
        project_id=int(project_id) if project_id.isdigit() else 0,
        q=q,
        limit=300,
    )
    kpi = stock_kpi()
    part_filter = None
    if part_id.isdigit():
        part_filter = _logi.parts_get(int(part_id))
    return ctx(request, "stock_movements.html", user=u, items=items, kpi=kpi,
               part_filter=part_filter, filter_kind=kind, filter_since=since,
               filter_until=until, q=q, MOVEMENT_KIND_LABEL=MOVEMENT_KIND_LABEL,
               active="stock")


# =====================================================
# HAIST Victor — 사내 AI 컨시어지 (Phase 1)
# 자연어 질문 → 데이터/페이지 자동 라우팅
# =====================================================
from .victor import ask as victor_ask


@app.post("/api/victor/ask")
async def api_victor_ask(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    try:
        data = await req.json()
        query = (data.get("query") or "").strip()
    except Exception:
        query = ""
    result = victor_ask(query, u, db_session)
    return JSONResponse({"ok": True, "result": result})


@app.get("/api/victor/ask")
async def api_victor_ask_get(req: Request, q: str = ""):
    """GET 방식 지원 (간단한 테스트/디버깅용)"""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    result = victor_ask(q, u, db_session)
    return JSONResponse({"ok": True, "result": result})


# =====================================================
# TOP3 S3 — 권한 위임 1차 라우트 골격 (2026-04-25)
# 시안: 05_HAIST_WORKS_디자인팀/_TO_01_정식시안_Top3_S3_v1.md
# 1차 = 골격만 (UI 본문·토큰 발행 로직은 다음 사이클).
# 권한 분기: CEO·admin only — 평직원/팀장 차단.
# =====================================================
@app.get("/admin/permissions", response_class=HTMLResponse)
async def admin_permissions_page(req: Request):
    """권한 위임 메인 — 보내기/회수 2탭 (시안 §0)"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    return ctx(req, "admin_permissions.html", user=u, active="admin")


@app.get("/admin/permissions/grant", response_class=HTMLResponse)
async def admin_permissions_grant_page(req: Request):
    """보내기 탭 — 위임 발송 폼 (시안 §1-A)"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    return ctx(req, "admin_permissions_grant.html", user=u, active="admin")


@app.post("/admin/permissions/grant")
async def admin_permissions_grant_submit(req: Request):
    """위임 토큰 발행 (S3 2차 본문 · 시안 §1-A 5필드)
    트랜잭션: delegation_tokens INSERT + delegation_audit INSERT (audit 누락 0건)
    RBAC 컬럼 분리: resource + action 셀렉터 → permissions 조회 (없으면 자동 INSERT)
    """
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    to_user_q  = (form.get("to_user") or "").strip()
    resource   = (form.get("resource") or "").strip()
    action     = (form.get("action") or "").strip()
    expires_at = (form.get("expires_at") or "").strip()
    reason     = (form.get("reason") or "").strip()
    can_redel  = 1 if form.get("can_redelegate") else 0
    if not (to_user_q and resource and action and expires_at):
        return JSONResponse({"error": "필수 항목 누락"}, 400)
    with db_session() as c:
        # 위임받는 자 조회 (이름 또는 이메일)
        tu = c.execute(
            "SELECT id, name FROM users WHERE name=? OR login_id=? LIMIT 1",
            (to_user_q, to_user_q)
        ).fetchone()
        if not tu:
            return JSONResponse({"error": "대상 사용자 없음"}, 404)
        # 권한 카탈로그 조회/INSERT (resource/action/scope 신규 컬럼 사용 — RBAC 분리)
        prow = c.execute(
            "SELECT id FROM permissions WHERE resource=? AND action=? LIMIT 1",
            (resource, action)
        ).fetchone()
        if prow:
            perm_id = prow["id"]
        else:
            # 신규 권한 자동 등록 (name = 'resource.action' 호환 유지)
            c.execute(
                "INSERT INTO permissions(name, resource, action, scope, description) VALUES(?,?,?,?,?)",
                (f"{resource}.{action}", resource, action, resource, f"{resource} {action}")
            )
            perm_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        # delegation_tokens INSERT
        c.execute(
            "INSERT INTO delegation_tokens(from_user, to_user, permission_id, expires_at, can_redelegate, status) "
            "VALUES(?,?,?,?,?,'ACTIVE')",
            (u["id"], tu["id"], perm_id, expires_at, can_redel)
        )
        token_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        # delegation_audit INSERT (트랜잭션 무결성 — audit 누락 0건)
        c.execute(
            "INSERT INTO delegation_audit(token_id, action, actor, details) VALUES(?,?,?,?)",
            (token_id, "GRANT", u["id"], f"{resource}.{action} → {tu['name']} / 만료 {expires_at} / 사유: {reason or '-'}")
        )
        _grant_target = tu["id"]
    # 알림시스템 통합 (사이클 2026-04-26) — 위임 받는 자에게 PERMISSION 알림
    notify_user(
        _grant_target, "PERMISSION",
        f"🔑 권한 위임 — {resource}.{action}",
        body=f"{u.get('name','')} 님이 권한을 위임했습니다 (만료 {expires_at})",
        link="/admin/permissions",
    )
    return RedirectResponse("/admin/permissions", 303)


@app.get("/admin/permissions/revoke", response_class=HTMLResponse)
async def admin_permissions_revoke_page(req: Request):
    """회수 탭 — 위임 카드 리스트 (시안 §6-1)"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    return ctx(req, "admin_permissions_revoke.html", user=u, active="admin")


@app.post("/admin/permissions/revoke")
async def admin_permissions_revoke_submit(req: Request):
    """위임 토큰 회수 + Cascade (S3 2차 본문 · 시안 §6-1)
    트랜잭션: 본 토큰 UPDATE status=REVOKED + 하위 재위임 토큰 Cascade UPDATE
              + delegation_audit INSERT (각 회수마다 1행, immutable)
    2단계 확인: confirm_text == '회수합니다' 인 경우만 실행
    """
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    token_id     = form.get("token_id")
    confirm_text = (form.get("confirm_text") or "").strip()
    if not token_id:
        return JSONResponse({"error": "token_id 필수"}, 400)
    if confirm_text != "회수합니다":
        return JSONResponse({"error": "2단계 확인 실패 (회수합니다 입력 필요)"}, 400)
    with db_session() as c:
        # 본 토큰 회수
        row = c.execute("SELECT to_user FROM delegation_tokens WHERE id=?", (token_id,)).fetchone()
        if not row:
            return JSONResponse({"error": "토큰 없음"}, 404)
        c.execute("UPDATE delegation_tokens SET status='REVOKED' WHERE id=? AND status='ACTIVE'", (token_id,))
        c.execute(
            "INSERT INTO delegation_audit(token_id, action, actor, details) VALUES(?,?,?,?)",
            (token_id, "REVOKE", u["id"], f"본 토큰 회수 (token_id={token_id})")
        )
        _revoke_target = row["to_user"]
        # Cascade — 본 토큰 수령자가 재위임한 ACTIVE 하위 토큰 회수
        children = c.execute(
            "SELECT id FROM delegation_tokens WHERE from_user=? AND status='ACTIVE'",
            (row["to_user"],)
        ).fetchall()
        _cascade_targets = []
        for ch in children:
            c.execute("UPDATE delegation_tokens SET status='REVOKED' WHERE id=?", (ch["id"],))
            c.execute(
                "INSERT INTO delegation_audit(token_id, action, actor, details) VALUES(?,?,?,?)",
                (ch["id"], "REVOKE", u["id"], f"Cascade 회수 (parent_token_id={token_id})")
            )
            ct = c.execute(
                "SELECT to_user FROM delegation_tokens WHERE id=?", (ch["id"],)
            ).fetchone()
            if ct and ct["to_user"]:
                _cascade_targets.append(ct["to_user"])
    # 알림시스템 통합 (사이클 2026-04-26) — 회수 대상자에게 PERMISSION 알림
    notify_user(
        _revoke_target, "PERMISSION",
        "🔒 권한 회수",
        body=f"위임 권한이 회수되었습니다 (token_id={token_id})",
        link="/admin/permissions",
    )
    for tgt in _cascade_targets:
        notify_user(
            tgt, "PERMISSION", "🔒 권한 회수 (Cascade)",
            body=f"상위 위임 회수에 따라 하위 권한이 회수되었습니다 (parent_token_id={token_id})",
            link="/admin/permissions",
        )
    return RedirectResponse("/admin/permissions", 303)


def _audit_query(c, action: str = "", date_from: str = "", date_to: str = "",
                 actor: str = "", target: str = "", q: str = "", limit: int = 200):
    """S3 4차 — 감사 로그 검색·필터 공용 빌더.
    - action: GRANT/DELEGATE/REVOKE/EXPIRE/REDELEGATE (whitelist)
    - date_from/date_to: YYYY-MM-DD (timestamp 부분일치)
    - actor/target: 사용자명 LIKE (actor=u.name, target=tu.name via dt.to_user)
    - q: resource·action·token_id·details LIKE
    """
    sql = (
        "SELECT da.id, da.timestamp, da.action, da.details, da.actor, da.token_id, "
        "       u.name AS actor_name, tu.name AS target_name, "
        "       COALESCE(p.resource||'.'||p.action, p.name) AS perm_label, "
        "       p.resource AS perm_resource, p.action AS perm_action "
        "FROM delegation_audit da "
        "LEFT JOIN users u ON u.id = da.actor "
        "LEFT JOIN delegation_tokens dt ON dt.id = da.token_id "
        "LEFT JOIN users tu ON tu.id = dt.to_user "
        "LEFT JOIN permissions p ON p.id = dt.permission_id "
    )
    where, params = [], []
    if action in ("GRANT", "DELEGATE", "REVOKE", "EXPIRE", "REDELEGATE"):
        where.append("da.action=?"); params.append(action)
    if date_from:
        where.append("da.timestamp>=?"); params.append(date_from + " 00:00:00")
    if date_to:
        where.append("da.timestamp<=?"); params.append(date_to + " 23:59:59")
    if actor:
        where.append("u.name LIKE ?"); params.append(f"%{actor}%")
    if target:
        where.append("tu.name LIKE ?"); params.append(f"%{target}%")
    if q:
        where.append("(p.resource LIKE ? OR p.action LIKE ? OR CAST(da.token_id AS TEXT)=? OR da.details LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", q, f"%{q}%"])
    if where:
        sql += "WHERE " + " AND ".join(where) + " "
    sql += f"ORDER BY da.timestamp DESC, da.id DESC LIMIT {int(limit)}"
    try:
        return [dict(r) for r in c.execute(sql, params).fetchall()]
    except Exception:
        return []


@app.get("/admin/permissions/audit", response_class=HTMLResponse)
async def admin_permissions_audit_page(req: Request, action: str = "",
                                        date_from: str = "", date_to: str = "",
                                        actor: str = "", target: str = "", q: str = ""):
    """감사 로그 — 시간역순 타임라인 (시안 §6-2, append-only).
    S3 4차 — 액션·기간·actor·target·검색(q) 필터 강화.
    """
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    af = action if action in ("GRANT", "DELEGATE", "REVOKE", "EXPIRE", "REDELEGATE") else ""
    with db_session() as c:
        rows = _audit_query(c, af, date_from, date_to, actor, target, q, 200)
    return ctx(req, "admin_permissions_audit.html", user=u, active="admin",
               audit_rows=rows, action_filter=af,
               date_from=date_from, date_to=date_to,
               actor_q=actor, target_q=target, q=q)


@app.get("/admin/permissions/audit.csv")
async def admin_permissions_audit_csv(req: Request, action: str = "",
                                       date_from: str = "", date_to: str = "",
                                       actor: str = "", target: str = "", q: str = ""):
    """감사 로그 CSV 다운로드 — csv 모듈 단독 (외부 라이브러리 0).
    동일 필터 재사용 (LIMIT 5000 으로 상향)."""
    import csv as _csv
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    af = action if action in ("GRANT", "DELEGATE", "REVOKE", "EXPIRE", "REDELEGATE") else ""
    with db_session() as c:
        rows = _audit_query(c, af, date_from, date_to, actor, target, q, 5000)
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM
    w = _csv.writer(buf)
    w.writerow(["id", "timestamp", "action", "actor", "target", "permission", "token_id", "details"])
    for r in rows:
        w.writerow([r.get("id"), r.get("timestamp"), r.get("action"),
                    r.get("actor_name") or r.get("actor") or "",
                    r.get("target_name") or "",
                    r.get("perm_label") or "",
                    r.get("token_id") or "",
                    (r.get("details") or "").replace("\n", " ")])
    fn = f"audit_{date.today().isoformat()}.csv"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={fn}"}
    )


# =====================================================
# TOP3 S3 — 권한 위임 3차 (2026-04-26)
# 시안: 05_HAIST_WORKS_디자인팀/_TO_01_정식시안_Top3_S3_v1.md
# 3차 = 권한 그룹 관리 + 매트릭스 보기 + 그룹 단위 위임.
# 권한 분기: CEO·admin only — 평직원/팀장 차단.
# =====================================================
@app.get("/admin/permissions/groups", response_class=HTMLResponse)
async def admin_permissions_groups_list(req: Request):
    """그룹 목록 — permission_groups + 권한 카운트 + 멤버 카운트 (시안 §5 그룹 상속)"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        try:
            rows = c.execute(
                "SELECT g.id, g.name, g.description, g.created_at, "
                "       (SELECT COUNT(*) FROM group_permissions gp WHERE gp.group_id=g.id) AS perm_count, "
                "       (SELECT COUNT(*) FROM user_groups ug WHERE ug.group_id=g.id) AS user_count "
                "FROM permission_groups g ORDER BY g.id ASC"
            ).fetchall()
            groups = [dict(r) for r in rows]
        except Exception:
            groups = []
    return ctx(req, "admin_permissions_groups.html", user=u, active="admin",
               groups=groups, group_detail=None, all_perms=[], all_users=[],
               group_perm_ids=set(), group_user_ids=set())


@app.post("/admin/permissions/groups")
async def admin_permissions_groups_create(req: Request):
    """그룹 신규 INSERT — name UNIQUE 가드"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    name = (form.get("name") or "").strip()
    desc = (form.get("description") or "").strip()
    if not name:
        return JSONResponse({"error": "그룹명 필수"}, 400)
    with db_session() as c:
        exists = c.execute("SELECT id FROM permission_groups WHERE name=?", (name,)).fetchone()
        if exists:
            return RedirectResponse(f"/admin/permissions/groups/{exists['id']}", 303)
        c.execute(
            "INSERT INTO permission_groups(name, description) VALUES(?,?)",
            (name, desc)
        )
        gid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return RedirectResponse(f"/admin/permissions/groups/{gid}", 303)


@app.get("/admin/permissions/groups/{group_id}", response_class=HTMLResponse)
async def admin_permissions_groups_detail(req: Request, group_id: int):
    """그룹 상세 — 그룹 정보 + 권한 + 멤버 + 추가 가능한 권한/사용자 목록"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        try:
            grow = c.execute(
                "SELECT id, name, description, created_at FROM permission_groups WHERE id=?",
                (group_id,)
            ).fetchone()
            if not grow:
                return RedirectResponse("/admin/permissions/groups", 303)
            group_detail = dict(grow)
            # 전체 그룹 목록 (좌측 사이드)
            grows = c.execute(
                "SELECT g.id, g.name, "
                "       (SELECT COUNT(*) FROM group_permissions gp WHERE gp.group_id=g.id) AS perm_count, "
                "       (SELECT COUNT(*) FROM user_groups ug WHERE ug.group_id=g.id) AS user_count "
                "FROM permission_groups g ORDER BY g.id ASC"
            ).fetchall()
            groups = [dict(r) for r in grows]
            # 전체 권한 카탈로그
            prows = c.execute(
                "SELECT id, COALESCE(resource||'.'||action, name) AS label, scope "
                "FROM permissions ORDER BY label"
            ).fetchall()
            all_perms = [dict(r) for r in prows]
            # 전체 사용자
            urows = c.execute(
                "SELECT id, name, login_id FROM users ORDER BY name LIMIT 200"
            ).fetchall()
            all_users = [dict(r) for r in urows]
            # 그룹에 이미 등록된 권한/사용자 ID
            gpids = {r["permission_id"] for r in c.execute(
                "SELECT permission_id FROM group_permissions WHERE group_id=?",
                (group_id,)
            ).fetchall()}
            guids = {r["user_id"] for r in c.execute(
                "SELECT user_id FROM user_groups WHERE group_id=?",
                (group_id,)
            ).fetchall()}
        except Exception:
            group_detail, groups, all_perms, all_users = None, [], [], []
            gpids, guids = set(), set()
    return ctx(req, "admin_permissions_groups.html", user=u, active="admin",
               groups=groups, group_detail=group_detail,
               all_perms=all_perms, all_users=all_users,
               group_perm_ids=gpids, group_user_ids=guids)


@app.post("/admin/permissions/groups/{group_id}/permissions")
async def admin_permissions_groups_perms(req: Request, group_id: int):
    """그룹↔권한 매핑 갱신 — checkbox 제출 후 전체 재기록 (트랜잭션)"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    perm_ids = form.getlist("perm_id") if hasattr(form, "getlist") else form.getlist("perm_id")
    pids = []
    for v in perm_ids:
        try:
            pids.append(int(v))
        except (TypeError, ValueError):
            continue
    with db_session() as c:
        c.execute("DELETE FROM group_permissions WHERE group_id=?", (group_id,))
        for pid in pids:
            c.execute(
                "INSERT OR IGNORE INTO group_permissions(group_id, permission_id) VALUES(?,?)",
                (group_id, pid)
            )
    return RedirectResponse(f"/admin/permissions/groups/{group_id}", 303)


@app.post("/admin/permissions/groups/{group_id}/users")
async def admin_permissions_groups_users(req: Request, group_id: int):
    """그룹↔사용자 매핑 갱신 — checkbox 제출 후 전체 재기록 (트랜잭션)"""
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    user_ids = form.getlist("user_id") if hasattr(form, "getlist") else form.getlist("user_id")
    uids = []
    for v in user_ids:
        try:
            uids.append(int(v))
        except (TypeError, ValueError):
            continue
    with db_session() as c:
        c.execute("DELETE FROM user_groups WHERE group_id=?", (group_id,))
        for uid in uids:
            c.execute(
                "INSERT OR IGNORE INTO user_groups(user_id, group_id) VALUES(?,?)",
                (uid, group_id)
            )
    return RedirectResponse(f"/admin/permissions/groups/{group_id}", 303)


@app.get("/admin/permissions/matrix", response_class=HTMLResponse)
async def admin_permissions_matrix(req: Request, dept: str = "", q: str = ""):
    """권한 매트릭스 — 사용자 vs 권한 (resource×action). 직접/그룹/위임 3색 (정적 CSS grid)
    - 부서 필터 + 검색 (이름/login_id 부분일치)
    - JS 0건 (서버 렌더링)
    """
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    dept_filter = (dept or "").strip()
    query = (q or "").strip()
    matrix = []
    perms = []
    depts = []
    with db_session() as c:
        try:
            # 권한 카탈로그
            prows = c.execute(
                "SELECT id, COALESCE(resource||'.'||action, name) AS label "
                "FROM permissions ORDER BY label LIMIT 30"
            ).fetchall()
            perms = [dict(r) for r in prows]
            # 부서 목록 (셀렉터)
            try:
                drows = c.execute("SELECT DISTINCT dept FROM users WHERE dept IS NOT NULL AND dept<>'' ORDER BY dept").fetchall()
                depts = [r["dept"] for r in drows]
            except Exception:
                depts = []
            # 사용자 목록
            usql = "SELECT id, name, login_id, COALESCE(dept,'') AS dept FROM users WHERE 1=1 "
            uparams = []
            if dept_filter:
                usql += "AND dept=? "
                uparams.append(dept_filter)
            if query:
                usql += "AND (name LIKE ? OR login_id LIKE ?) "
                uparams.extend([f"%{query}%", f"%{query}%"])
            usql += "ORDER BY name LIMIT 60"
            urows = c.execute(usql, uparams).fetchall()
            # 각 사용자 × 권한 셀: 직접(D) / 그룹(G) / 위임(T) 마크
            for ur in urows:
                uid = ur["id"]
                # 그룹 상속 권한
                ginh = {r["permission_id"] for r in c.execute(
                    "SELECT DISTINCT gp.permission_id FROM group_permissions gp "
                    "JOIN user_groups ug ON ug.group_id=gp.group_id WHERE ug.user_id=?",
                    (uid,)
                ).fetchall()}
                # 위임 토큰 (ACTIVE만)
                tdel = {r["permission_id"] for r in c.execute(
                    "SELECT permission_id FROM delegation_tokens WHERE to_user=? AND status='ACTIVE'",
                    (uid,)
                ).fetchall()}
                # 직접 권한 — user_permissions 가 별도로 없으면 빈셋 (스키마에 따라)
                try:
                    drect = {r["permission_id"] for r in c.execute(
                        "SELECT permission_id FROM user_permissions WHERE user_id=?",
                        (uid,)
                    ).fetchall()}
                except Exception:
                    drect = set()
                cells = []
                for p in perms:
                    pid = p["id"]
                    mark = ""
                    if pid in drect:
                        mark = "D"
                    elif pid in ginh:
                        mark = "G"
                    elif pid in tdel:
                        mark = "T"
                    cells.append(mark)
                matrix.append({
                    "user_id": uid, "name": ur["name"],
                    "login_id": ur["login_id"], "dept": ur["dept"],
                    "cells": cells,
                })
        except Exception:
            matrix, perms, depts = [], [], []
    return ctx(req, "admin_permissions_matrix.html", user=u, active="admin",
               matrix=matrix, perms=perms, depts=depts,
               dept_filter=dept_filter, query=query)


@app.post("/admin/permissions/grant-group")
async def admin_permissions_grant_group(req: Request):
    """그룹 단위 위임 — 그룹 전체 멤버에 동일 권한을 위임 토큰으로 발행
    트랜잭션: 멤버별 delegation_tokens INSERT + delegation_audit INSERT (1 트랜잭션)
    """
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    group_id   = form.get("group_id")
    resource   = (form.get("resource") or "").strip()
    action     = (form.get("action") or "").strip()
    expires_at = (form.get("expires_at") or "").strip()
    reason     = (form.get("reason") or "").strip()
    can_redel  = 1 if form.get("can_redelegate") else 0
    if not (group_id and resource and action and expires_at):
        return JSONResponse({"error": "필수 항목 누락"}, 400)
    with db_session() as c:
        gr = c.execute("SELECT id, name FROM permission_groups WHERE id=?", (group_id,)).fetchone()
        if not gr:
            return JSONResponse({"error": "그룹 없음"}, 404)
        # 권한 카탈로그 조회/INSERT
        prow = c.execute(
            "SELECT id FROM permissions WHERE resource=? AND action=? LIMIT 1",
            (resource, action)
        ).fetchone()
        if prow:
            perm_id = prow["id"]
        else:
            c.execute(
                "INSERT INTO permissions(name, resource, action, scope, description) VALUES(?,?,?,?,?)",
                (f"{resource}.{action}", resource, action, resource, f"{resource} {action}")
            )
            perm_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        # 그룹 멤버 조회
        members = c.execute(
            "SELECT user_id FROM user_groups WHERE group_id=?", (group_id,)
        ).fetchall()
        if not members:
            return JSONResponse({"error": "그룹 멤버 없음"}, 400)
        # 멤버별 토큰 + audit 발행
        for m in members:
            c.execute(
                "INSERT INTO delegation_tokens(from_user, to_user, permission_id, expires_at, can_redelegate, status) "
                "VALUES(?,?,?,?,?,'ACTIVE')",
                (u["id"], m["user_id"], perm_id, expires_at, can_redel)
            )
            tid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute(
                "INSERT INTO delegation_audit(token_id, action, actor, details) VALUES(?,?,?,?)",
                (tid, "GRANT", u["id"],
                 f"[그룹위임] {gr['name']} → user_id={m['user_id']} / {resource}.{action} / 만료 {expires_at} / 사유: {reason or '-'}")
            )
    return RedirectResponse(f"/admin/permissions/groups/{group_id}", 303)


# =====================================================
# TOP3 S3 — 권한 위임 4차 (2026-04-26): 권한 리포트 + 만료 정리
# 시안: 05_HAIST_WORKS_디자인팀/_TO_01_정식시안_Top3_S3_v1.md §7 운영 리포트
# 4차 = 사용자/그룹/만료임박 3리포트 + 만료 토큰 자동 정리(audit immutable).
# 권한: CEO·admin only.
# =====================================================
@app.get("/admin/permissions/report/users", response_class=HTMLResponse)
async def admin_permissions_report_users(req: Request):
    """사용자별 권한 카운트 + 활성 토큰 (시안 §7-1)."""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        try:
            rows = c.execute(
                "SELECT u.id, u.name, u.role, t.name AS team_name, "
                "       (SELECT COUNT(*) FROM delegation_tokens dt "
                "          WHERE dt.to_user=u.id AND dt.status='ACTIVE') AS active_tokens, "
                "       (SELECT COUNT(*) FROM delegation_tokens dt "
                "          WHERE dt.from_user=u.id AND dt.status='ACTIVE') AS granted_tokens, "
                "       (SELECT COUNT(DISTINCT ug.group_id) FROM user_groups ug "
                "          WHERE ug.user_id=u.id) AS group_count "
                "FROM users u LEFT JOIN teams t ON t.id=u.team_id "
                "ORDER BY active_tokens DESC, u.name ASC LIMIT 500"
            ).fetchall()
            users = [dict(r) for r in rows]
        except Exception:
            users = []
    return ctx(req, "admin_permissions_report.html", user=u, active="admin",
               report_kind="users", users=users, groups=[], expiring=[])


@app.get("/admin/permissions/report/groups", response_class=HTMLResponse)
async def admin_permissions_report_groups(req: Request):
    """그룹별 멤버·권한 분포 (시안 §7-2)."""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        try:
            rows = c.execute(
                "SELECT g.id, g.name, g.description, "
                "       (SELECT COUNT(*) FROM group_permissions gp WHERE gp.group_id=g.id) AS perm_count, "
                "       (SELECT COUNT(*) FROM user_groups ug WHERE ug.group_id=g.id) AS user_count "
                "FROM permission_groups g ORDER BY user_count DESC, g.name ASC"
            ).fetchall()
            groups = [dict(r) for r in rows]
        except Exception:
            groups = []
    return ctx(req, "admin_permissions_report.html", user=u, active="admin",
               report_kind="groups", users=[], groups=groups, expiring=[])


@app.get("/admin/permissions/report/expiring", response_class=HTMLResponse)
async def admin_permissions_report_expiring(req: Request, days: int = 7):
    """만료 임박 토큰 (시안 §7-3) — 기본 7일 내 ACTIVE."""
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    try:
        d = max(1, min(int(days), 90))
    except Exception:
        d = 7
    cutoff = (date.today() + timedelta(days=d)).isoformat()
    with db_session() as c:
        try:
            rows = c.execute(
                "SELECT dt.id AS token_id, dt.expires_at, dt.status, "
                "       fu.name AS from_name, tu.name AS to_name, "
                "       COALESCE(p.resource||'.'||p.action, p.name) AS perm_label "
                "FROM delegation_tokens dt "
                "LEFT JOIN users fu ON fu.id=dt.from_user "
                "LEFT JOIN users tu ON tu.id=dt.to_user "
                "LEFT JOIN permissions p ON p.id=dt.permission_id "
                "WHERE dt.status='ACTIVE' AND dt.expires_at IS NOT NULL "
                "  AND dt.expires_at<=? "
                "ORDER BY dt.expires_at ASC LIMIT 500",
                (cutoff,)
            ).fetchall()
            expiring = [dict(r) for r in rows]
        except Exception:
            expiring = []
    return ctx(req, "admin_permissions_report.html", user=u, active="admin",
               report_kind="expiring", users=[], groups=[], expiring=expiring,
               expiring_days=d)


@app.post("/admin/permissions/cleanup-expired")
async def admin_permissions_cleanup_expired(req: Request):
    """만료 토큰 자동 정리 — status='ACTIVE' AND expires_at<=now → status='EXPIRED'.
    트랜잭션: UPDATE + delegation_audit INSERT (각 토큰별 1행, immutable, audit 누락 0건).
    수동 트리거 (스케줄러 미구현).
    """
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cleaned = 0
    with db_session() as c:
        try:
            rows = c.execute(
                "SELECT id FROM delegation_tokens "
                "WHERE status='ACTIVE' AND expires_at IS NOT NULL AND expires_at<=?",
                (now_str,)
            ).fetchall()
            ids = [r["id"] for r in rows]
            for tid in ids:
                c.execute(
                    "UPDATE delegation_tokens SET status='EXPIRED' WHERE id=? AND status='ACTIVE'",
                    (tid,)
                )
                c.execute(
                    "INSERT INTO delegation_audit(token_id, action, actor, details) VALUES(?,?,?,?)",
                    (tid, "EXPIRE", u["id"], f"수동 만료 정리 (cleanup-expired @ {now_str})")
                )
                cleaned += 1
        except Exception as e:
            return JSONResponse({"error": str(e)}, 500)
    return RedirectResponse(f"/admin/permissions/report/expiring?msg={cleaned}건+정리완료", 303)


# =====================================================
# TOP3 S2 — 재고 입출고 1차 라우트 골격 (2026-04-25)
# 시안: 05_HAIST_WORKS_디자인팀/_TO_01_정식시안_Top3_S2_v1.md
# 1차 = 골격만 (UI 본문 · INSERT/UPDATE 로직은 다음 사이클).
# 권한: P4 구매팀(can_use_logistics) 또는 admin/ceo.
# =====================================================
def _s2_guard(req: Request):
    """S2 권한 가드 — 구매팀 권한 OR admin/ceo. 없으면 None 반환."""
    u = get_user(req)
    if not u:
        return None
    if u.get("role") in ("admin", "ceo") or can_use_logistics(u):
        return u
    return None


@app.get("/stock/balances", response_class=HTMLResponse)
async def stock_balances_page(req: Request):
    """재고 잔고 — stock_balances VIEW 조회 (시안 §화면 영역 잔고)"""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        rows = c.execute(
            """SELECT part_id, part_no, part_name, on_hand, unit, last_movement_at
               FROM stock_balances ORDER BY part_no LIMIT 200"""
        ).fetchall()
    balances = [dict(r) for r in rows]
    last_update = max((r.get("last_movement_at") or "") for r in balances) if balances else "-"
    return ctx(req, "stock_balances.html", user=u, active="stock",
               balances=balances, last_update=last_update or "-")


# Top3 S2 3차 (2026-04-26) — FIFO 레이어 상세 / ABC 분류 / 재고회전율 ==========
@app.get("/stock/balances/fifo/{part_id}", response_class=HTMLResponse)
async def stock_fifo_page(req: Request, part_id: int):
    """FIFO 레이어 상세 — 입고일·잔량·단가 시각화 (S2-3차)."""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    summary = fifo_layers(part_id)
    return ctx(req, "stock_fifo.html", user=u, active="stock", summary=summary)


@app.get("/stock/abc", response_class=HTMLResponse)
async def stock_abc_page(req: Request, days: int = 90, top: int = 50):
    """ABC 분류 — 최근 N일 출고 매출 누적 비중 기준 (A 80%, B 95%, C 나머지)."""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    items = abc_classification(days=days)
    a_cnt = sum(1 for r in items if r["abc_class"] == "A")
    b_cnt = sum(1 for r in items if r["abc_class"] == "B")
    c_cnt = sum(1 for r in items if r["abc_class"] == "C")
    return ctx(req, "stock_abc.html", user=u, active="stock",
               items=items[:top], total=len(items),
               a_count=a_cnt, b_count=b_cnt, c_count=c_cnt, days=days)


@app.get("/stock/turnover", response_class=HTMLResponse)
async def stock_turnover_page(req: Request, days: int = 90):
    """재고 회전율 — 출고량/평균재고 (FAST≥2 / NORMAL 0.5~2 / SLOW<0.5)."""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    items = stock_turnover(days=days)
    fast = sum(1 for r in items if r["band"] == "FAST")
    normal = sum(1 for r in items if r["band"] == "NORMAL")
    slow = sum(1 for r in items if r["band"] == "SLOW")
    return ctx(req, "stock_turnover.html", user=u, active="stock",
               items=items, fast=fast, normal=normal, slow=slow, days=days)


@app.get("/stock/receipts", response_class=HTMLResponse)
async def stock_receipts_page(req: Request):
    """입고 목록 — receipts 테이블 (시안 §화면 영역 입고 GR)"""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        rows = c.execute(
            """SELECT id, po_id, total_qty, qc_inspection_id, status, received_at, note
               FROM receipts ORDER BY id DESC LIMIT 100"""
        ).fetchall()
    return ctx(req, "stock_receipts.html", user=u, active="stock",
               receipts=[dict(r) for r in rows])


@app.post("/stock/receipts")
async def stock_receipts_submit(req: Request):
    """입고 등록 (Top3-S2-2차) — INSERT receipts + INSERT stock_movements{kind=IN, qty +}.
    receipts.status=PENDING (검수 대기). 트랜잭션 무결성: 두 INSERT 동일 db_session.
    """
    u = _s2_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    try:
        po_id = int(form.get("po_id") or 0) or None
        part_id = int(form.get("part_id") or 0)
        qty = float(form.get("qty") or 0)
        if part_id <= 0 or qty <= 0:
            raise ValueError("part_id/qty invalid")
    except Exception:
        return RedirectResponse("/stock/receipts?error=invalid", 303)
    # 1) receipts INSERT
    with db_session() as c:
        c.execute(
            """INSERT INTO receipts (po_id, received_by, total_qty, status, note)
               VALUES (?,?,?,?,?)""",
            (po_id, u.get("id"), qty, "PENDING", "S2-2차 GR")
        )
        gr_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    # 2) stock_movements INSERT (kind=IN, qty +) — balance VIEW 자동 반영
    try:
        from .database import stock_movement_create
        stock_movement_create({
            "part_id": part_id, "kind": "IN", "quantity": qty,
            "po_id": po_id, "reason": f"GR-{gr_id}", "note": "Top3-S2-2차 입고"
        }, u.get("id") or 0)
    except Exception as e:
        return RedirectResponse(f"/stock/receipts?error=mv:{e}", 303)
    return RedirectResponse(f"/stock/receipts?success=GR-{gr_id}", 303)


# 라우트 등록 순서 보정 (04 V10 권고): /stock/qc/disposition 을 /stock/qc/{po_item_id} 위로
@app.get("/stock/qc/disposition/{qc_id}", response_class=HTMLResponse)
async def stock_qc_disposition_page(req: Request, qc_id: int):
    """부적합 처리 모달 — RETURN/SPECIAL_ACCEPT/SCRAP (시안 §데이터 모델 qc_disposition)"""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    return ctx(req, "stock_qc.html", user=u, qc_id=qc_id, mode="disposition", active="stock")


@app.post("/stock/qc/disposition")
async def stock_qc_disposition_submit(req: Request):
    """부적합 처리 — INSERT qc_disposition + UPDATE qc_inspections.status (FAIL 분기 확정)"""
    u = _s2_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    try:
        qc_id = int(form.get("qc_inspection_id") or 0)
        action = (form.get("action") or "").upper()
        note = (form.get("note") or "").strip()
        if qc_id <= 0 or action not in ("RETURN", "SPECIAL_ACCEPT", "SCRAP"):
            raise ValueError("invalid")
    except Exception:
        return RedirectResponse("/stock/receipts?error=disp_invalid", 303)
    with db_session() as c:
        c.execute(
            """INSERT INTO qc_disposition (qc_inspection_id, action, decided_by, note)
               VALUES (?,?,?,?)""",
            (qc_id, action, u.get("id"), note or None)
        )
        # SPECIAL_ACCEPT는 부분 사용 가능 → status 유지, RETURN/SCRAP는 FAIL 확정
        if action in ("RETURN", "SCRAP"):
            c.execute("UPDATE qc_inspections SET status='FAIL' WHERE id=?", (qc_id,))
    return RedirectResponse(f"/stock/receipts?success=disp-{action}", 303)


@app.get("/stock/qc/{po_item_id}", response_class=HTMLResponse)
async def stock_qc_page(req: Request, po_item_id: int):
    """검수 화면 — qc_inspections 작성 (시안 §화면 영역 QC 우 패널)"""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    return ctx(req, "stock_qc.html", user=u, po_item_id=po_item_id, active="stock")


@app.post("/stock/qc/{po_item_id}")
async def stock_qc_submit(req: Request, po_item_id: int):
    """검수 결과 등록 (Top3-S2-2차) — INSERT qc_inspections + UPDATE receipts.qc_inspection_id.
    status 분기: PASS / PARTIAL / HOLD / FAIL. FAIL/PARTIAL 시 부적합 모달로 redirect.
    """
    u = _s2_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    try:
        pass_qty = float(form.get("pass_qty") or 0)
        fail_qty = float(form.get("fail_qty") or 0)
        status = (form.get("status") or "PENDING").upper()
        if status not in ("PASS", "PARTIAL", "HOLD", "FAIL"):
            status = "PENDING"
        fail_reason = (form.get("fail_reason") or "").strip() or None
    except Exception:
        return RedirectResponse(f"/stock/qc/{po_item_id}?error=invalid", 303)
    # OPS-V5 [정적점검]: 음수 차단 + FAIL/PARTIAL 사유 필수 (감사 추적)
    if pass_qty < 0 or fail_qty < 0:
        return RedirectResponse(f"/stock/qc/{po_item_id}?error=qty_negative", 303)
    if status in ("FAIL", "PARTIAL") and not fail_reason:
        return RedirectResponse(f"/stock/qc/{po_item_id}?error=fail_reason_required", 303)
    # po_item_id 가 receipts.id 로 들어올 수 있으므로 둘다 시도 (UI 단순화)
    with db_session() as c:
        c.execute(
            """INSERT INTO qc_inspections
               (po_item_id, receipt_id, inspector_id, pass_qty, fail_qty, fail_reason, status)
               VALUES (?,?,?,?,?,?,?)""",
            (po_item_id, po_item_id, u.get("id"), pass_qty, fail_qty, fail_reason, status)
        )
        qc_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        # receipts UPDATE: qc_inspection_id 연결 + status 동기화
        c.execute(
            "UPDATE receipts SET qc_inspection_id=?, status=? WHERE id=?",
            (qc_id, status, po_item_id)
        )
    # FAIL/PARTIAL → 부적합 모달
    if status in ("FAIL", "PARTIAL"):
        return RedirectResponse(f"/stock/qc/disposition/{qc_id}", 303)
    return RedirectResponse(f"/stock/receipts?success=qc-{status}", 303)


@app.get("/stock/issues", response_class=HTMLResponse)
async def stock_issues_page(req: Request):
    """출고 목록 — issues_out 테이블 (시안 §화면 영역 출고 GI)"""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        rows = c.execute(
            """SELECT id, part_id, qty, purpose, status, requested_at, issued_at
               FROM issues_out ORDER BY id DESC LIMIT 100"""
        ).fetchall()
    return ctx(req, "stock_issues.html", user=u, active="stock",
               issues=[dict(r) for r in rows])


@app.post("/stock/issues")
async def stock_issues_submit(req: Request):
    """출고 등록 (Top3-S2-2차) — INSERT issues_out · status=PENDING.
    실제 재고 차감은 /stock/issues/{id}/approve 에서 stock_movements 동시 INSERT.
    """
    u = _s2_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    try:
        part_id = int(form.get("part_id") or 0)
        qty = float(form.get("qty") or 0)
        purpose = (form.get("purpose") or "").strip() or None
        if part_id <= 0 or qty <= 0:
            raise ValueError("invalid")
    except Exception:
        return RedirectResponse("/stock/issues?error=invalid", 303)
    with db_session() as c:
        c.execute(
            """INSERT INTO issues_out (part_id, requester_id, qty, purpose, status)
               VALUES (?,?,?,?,?)""",
            (part_id, u.get("id"), qty, purpose, "PENDING")
        )
        gi_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return RedirectResponse(f"/stock/issues?success=GI-{gi_id}", 303)


@app.post("/stock/issues/{issue_id}/approve")
async def stock_issues_approve(req: Request, issue_id: int):
    """출고 승인·실행 (Top3-S2-2차) — UPDATE issues_out.status=ISSUED + INSERT stock_movements{kind=OUT, qty -}.
    트랜잭션 무결성: stock_movement_create 가 자체 db_session 으로 balance VIEW 즉시 반영.
    """
    u = _s2_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    # 1) issues_out 조회 + 승인
    with db_session() as c:
        row = c.execute(
            "SELECT id, part_id, qty, status FROM issues_out WHERE id=?", (issue_id,)
        ).fetchone()
        if not row:
            return RedirectResponse("/stock/issues?error=notfound", 303)
        if row["status"] != "PENDING":
            return RedirectResponse(f"/stock/issues?error=already-{row['status']}", 303)
        c.execute(
            "UPDATE issues_out SET status='ISSUED', approver_id=?, issued_at=datetime('now','localtime') WHERE id=?",
            (u.get("id"), issue_id)
        )
        part_id = row["part_id"]
        qty = float(row["qty"] or 0)
    # 2) stock_movements INSERT (kind=OUT, qty -) — balance VIEW 자동 반영 (FIFO)
    try:
        from .database import stock_movement_create
        stock_movement_create({
            "part_id": part_id, "kind": "OUT", "quantity": qty,
            "reason": f"GI-{issue_id}", "note": "Top3-S2-2차 출고 승인"
        }, u.get("id") or 0)
    except Exception as e:
        return RedirectResponse(f"/stock/issues?error=mv:{e}", 303)
    return RedirectResponse(f"/stock/issues?success=GI-{issue_id}-ISSUED", 303)


# =====================================================
# TOP3 S1 — 매출 라이프사이클 1차 라우트 골격 (2026-04-25)
# 시안: 05_HAIST_WORKS_디자인팀/_TO_01_정식시안_Top3_S1_v1.md
# 1차 = 골격만 (UI 본문 · INSERT/UPDATE 로직은 다음 사이클).
# 권한: P2 영업팀(can_use_sales) 또는 admin/ceo. 평직원 차단.
# 4탭: 견적QT(탭1) / 수주SO(탭2) / 생산WO(탭3) / 출하DO·수금RC(탭4)
# 9 enum: DRAFT/QUOTED/CONFIRMED/IN_PRODUCTION/READY_TO_SHIP/SHIPPED/INVOICED/PAID/CANCELLED
#         (database.py orders.status CHECK constraint · invoices 추가 정합)
# =====================================================
def _s1_guard(req: Request):
    """S1 권한 가드 — 영업팀 권한 OR admin/ceo. 없으면 None 반환."""
    u = get_user(req)
    if not u:
        return None
    if u.get("role") in ("admin", "ceo") or can_use_sales(u):
        return u
    return None


@app.get("/sales/quotations", response_class=HTMLResponse)
async def sales_quotations_page(req: Request):
    """견적 탭 (시안 §1 탭1 QT) — quotations 리스트 + Empty State"""
    u = _s1_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        rows = c.execute(
            """SELECT q.id, q.quote_no, q.customer_id,
                      COALESCE(cu.name,'-') AS customer_name,
                      q.total_amount, q.valid_until, q.version, q.status,
                      q.created_at
               FROM quotations q
               LEFT JOIN customers cu ON cu.id = q.customer_id
               ORDER BY q.id DESC LIMIT 200"""
        ).fetchall()
        items = [dict(r) for r in rows]
        # 사이클 61 U5 — 각 견적의 라인 사전 로드 (삭제 UI 노출용)
        lines_by_quote = {}
        if items:
            quote_ids = [it["id"] for it in items]
            placeholders = ",".join(["?"] * len(quote_ids))
            line_rows = c.execute(
                f"""SELECT id, quotation_id, line_no, item_name, qty, unit,
                          unit_price, total_price, note
                   FROM quotation_items
                   WHERE quotation_id IN ({placeholders})
                   ORDER BY quotation_id, line_no""",
                quote_ids,
            ).fetchall()
            for lr in line_rows:
                lines_by_quote.setdefault(lr["quotation_id"], []).append(dict(lr))
    return ctx(req, "sales_quotations.html", user=u, active="sales_quotations",
               tab="quotations", items=items, lines_by_quote=lines_by_quote)


@app.post("/sales/quotations")
async def sales_quotations_create(req: Request):
    """견적 생성 (Top3-S1-2차 — quotations INSERT, status=DRAFT)"""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    customer_id = form.get("customer_id") or None
    total_amount = float(form.get("total_amount") or 0)
    valid_until = form.get("valid_until") or None
    version = int(form.get("version") or 1)
    with db_session() as c:
        # quote_no = QT-YYYYMM-#### (월별 시퀀스)
        ym = datetime.now().strftime("%Y%m")
        row = c.execute(
            "SELECT COUNT(*) FROM quotations WHERE quote_no LIKE ?",
            (f"QT-{ym}-%",),
        ).fetchone()
        seq = (row[0] if row else 0) + 1
        quote_no = f"QT-{ym}-{seq:04d}"
        cur = c.execute(
            """INSERT INTO quotations
               (quote_no, customer_id, total_amount, valid_until, version,
                status, created_by)
               VALUES (?,?,?,?,?,'DRAFT',?)""",
            (quote_no, customer_id, total_amount, valid_until, version, u.get("id")),
        )
        return JSONResponse({"ok": True, "quote_id": cur.lastrowid, "quote_no": quote_no})


# =====================================================
# 회사 식별 정보 (사이클 61 — 견적서 헤더용 / 외부자산 0건)
# 실제 값은 /admin/company-info 페이지에서 대표가 직접 입력 → app_settings 테이블
# 미입력 시 placeholder 텍스트 노출 ("[등록 대기]")
# =====================================================
COMPANY_INFO_KEYS = [
    ("company_name_ko",  "회사명 (국문)",   "주식회사 케이엔케이 (KNK)"),
    ("company_name_en",  "Company (EN)",   "KNK Co., Ltd."),
    ("company_biz_no",   "사업자등록번호",  ""),
    ("company_address",  "회사 주소",       ""),
    ("company_address_en", "Address (EN)",  ""),
    ("company_tel",      "대표 전화",       ""),
    ("company_fax",      "팩스",            ""),
    ("company_email",    "대표 이메일",     ""),
    ("company_ceo_ko",   "대표자 (국문)",   "김정락"),
    ("company_ceo_en",   "CEO (EN)",       "Jeongrak Kim"),
]

def _company_info_dict() -> dict:
    """app_settings 에서 회사 정보 조회. 미입력 키는 default 값 반환."""
    out = {}
    for key, label, default in COMPANY_INFO_KEYS:
        val = (get_setting(key, "") or "").strip()
        out[key] = val if val else default
    return out


# =====================================================
# Sales 견적 라인 + 인쇄 + 수주 전환 (사이클 58 — 2차 보강)
# =====================================================

@app.get("/sales/quotations/{quote_id}/print", response_class=HTMLResponse)
async def sales_quotation_print(req: Request, quote_id: int, lang: str = ""):
    """견적서 인쇄 view — 1페이지 A4, @media print 인라인 CSS, 외부 자산 0건.
    사이클 63 P11 — 다국어 지원 (?lang=ko|en|vi 쿼리. 미지정 시 사용자 lang)."""
    u = _s1_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        h = c.execute(
            """SELECT q.id, q.quote_no, q.customer_id,
                      COALESCE(cu.name,'-')   AS customer_name,
                      COALESCE(cu.tier,'')    AS customer_tier,
                      COALESCE(cu.note,'')    AS customer_note,
                      q.total_amount, q.valid_until, q.version, q.status,
                      q.created_at,
                      COALESCE(us.name,'-')   AS owner_name
               FROM quotations q
               LEFT JOIN customers cu ON cu.id = q.customer_id
               LEFT JOIN users     us ON us.id = q.created_by
               WHERE q.id = ?""",
            (quote_id,),
        ).fetchone()
        if not h:
            return RedirectResponse("/sales/quotations", 303)
        header = dict(h)
    # 라인 (헬퍼 호출 — 자체 db_session)
    from .database import get_quotation_items as _gqi
    lines = _gqi(quote_id)
    company = _company_info_dict()  # 사이클 61 U6 — 회사 식별 정보
    # 사이클 63 — 견적서 인쇄 언어 override (?lang=ko|en|vi 만 허용. 그 외 무시)
    # ctx() 의 base.update(kwargs) 가 마지막에 실행 → 여기서 lang/i 덮어쓰기 가능.
    # print_lang 미지정 시 사용자 lang 그대로 사용 (ctx 기본 동작).
    extra = {"header": header, "lines": lines, "company": company,
             "quote_id": quote_id}
    if lang in ("ko", "en", "vi"):
        extra["lang"] = lang
        extra["i"] = get_all_translations(lang)
    return ctx(req, "quotation_print.html", user=u, active="sales", **extra)


@app.post("/sales/quotations/{quote_id}/items")
async def sales_quotation_item_add(req: Request, quote_id: int):
    """견적 라인 추가 — quotation_items INSERT + quotations.total_amount 재합계."""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    item_name = (form.get("item_name") or "").strip()
    if not item_name:
        return JSONResponse({"error": "품목명 누락"}, 400)
    part_id = form.get("part_id") or None
    try:
        part_id = int(part_id) if part_id else None
    except (TypeError, ValueError):
        part_id = None
    qty = float(form.get("qty") or 0)
    unit = (form.get("unit") or "EA").strip()
    unit_price = float(form.get("unit_price") or 0)
    note = (form.get("note") or "").strip()
    total_price = qty * unit_price
    with db_session() as c:
        # 견적 존재 검증
        h = c.execute("SELECT id FROM quotations WHERE id=?", (quote_id,)).fetchone()
        if not h:
            return JSONResponse({"error": "견적 없음"}, 404)
        # 다음 line_no 채번
        row = c.execute(
            "SELECT COALESCE(MAX(line_no),0)+1 FROM quotation_items WHERE quotation_id=?",
            (quote_id,),
        ).fetchone()
        line_no = row[0] if row else 1
        cur = c.execute(
            """INSERT INTO quotation_items
               (quotation_id, line_no, part_id, item_name, qty, unit,
                unit_price, total_price, note)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (quote_id, line_no, part_id, item_name, qty, unit,
             unit_price, total_price, note or None),
        )
        # 헤더 total_amount 재합계
        s = c.execute(
            "SELECT COALESCE(SUM(total_price),0) FROM quotation_items WHERE quotation_id=?",
            (quote_id,),
        ).fetchone()
        c.execute(
            "UPDATE quotations SET total_amount=? WHERE id=?",
            (float(s[0] or 0), quote_id),
        )
    return RedirectResponse(f"/sales/quotations", 303)


@app.post("/sales/quotations/{quote_id}/items/{item_id}/delete")
async def sales_quotation_item_delete(req: Request, quote_id: int, item_id: int):
    """견적 라인 제거 + total_amount 재합계."""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    with db_session() as c:
        c.execute(
            "DELETE FROM quotation_items WHERE id=? AND quotation_id=?",
            (item_id, quote_id),
        )
        s = c.execute(
            "SELECT COALESCE(SUM(total_price),0) FROM quotation_items WHERE quotation_id=?",
            (quote_id,),
        ).fetchone()
        c.execute(
            "UPDATE quotations SET total_amount=? WHERE id=?",
            (float(s[0] or 0), quote_id),
        )
    return RedirectResponse(f"/sales/quotations", 303)


@app.post("/sales/quotations/{quote_id}/convert-to-order")
async def sales_quotation_convert_to_order(req: Request, quote_id: int):
    """수주 전환 — quotations.CONFIRMED + clone_quotation_to_order 헬퍼 + history."""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    due_date = form.get("due_date") or None
    from .database import clone_quotation_to_order as _clone
    with db_session() as c:
        q = c.execute(
            "SELECT id, status FROM quotations WHERE id=?", (quote_id,)
        ).fetchone()
        if not q:
            return JSONResponse({"error": "견적 없음"}, 404)
        # 견적 상태 CONFIRMED 전환
        c.execute(
            "UPDATE quotations SET status='CONFIRMED' WHERE id=?", (quote_id,)
        )
    # 헬퍼는 자체 db_session — 위 트랜잭션 커밋 후 호출
    order_id, order_no = _clone(quote_id, due_date=due_date,
                                 created_by=u.get("id") or 0)
    if not order_id:
        return JSONResponse({"error": "수주 전환 실패"}, 500)
    # 상태 이력
    with db_session() as c:
        c.execute(
            """INSERT INTO order_status_history
               (order_id, from_status, to_status, changed_by, note)
               VALUES (?,?,?,?,?)""",
            (order_id, "DRAFT", "CONFIRMED", u.get("id"),
             "견적→수주 전환 (라인 자동 복제)"),
        )
    return RedirectResponse("/sales/orders", 303)


@app.get("/sales/orders", response_class=HTMLResponse)
async def sales_orders_page(req: Request):
    """수주 탭 (시안 §1 탭2 SO) — orders 리스트 + status tag (시안 §3)"""
    u = _s1_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        rows = c.execute(
            """SELECT o.id, o.order_no, o.customer_id,
                      COALESCE(cu.name,'-') AS customer_name,
                      o.total_amount, o.due_date, o.status,
                      o.order_date,
                      COALESCE(o.tax_invoice_issued,0) AS tax_invoice_issued,
                      o.tax_invoice_no, o.tax_invoice_date, o.tax_invoice_note
               FROM orders o
               LEFT JOIN customers cu ON cu.id = o.customer_id
               ORDER BY o.id DESC LIMIT 200"""
        ).fetchall()
        items = [dict(r) for r in rows]
    return ctx(req, "sales_orders.html", user=u, active="sales_orders",
               tab="orders", items=items)


@app.post("/sales/orders")
async def sales_orders_confirm(req: Request):
    """수주 확정 (Top3-S1-2차 — quotation.CONFIRMED + orders INSERT + history)"""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    quote_id = form.get("quote_id") or None
    due_date = form.get("due_date") or None
    if not quote_id:
        return JSONResponse({"error": "quote_id 누락"}, 400)
    with db_session() as c:
        q = c.execute(
            "SELECT customer_id, total_amount FROM quotations WHERE id=?",
            (quote_id,),
        ).fetchone()
        if not q:
            return JSONResponse({"error": "견적 없음"}, 404)
        # 견적 상태 CONFIRMED 로 전환
        c.execute(
            "UPDATE quotations SET status='CONFIRMED' WHERE id=?", (quote_id,)
        )
        # 수주 헤더 INSERT (status=CONFIRMED)
        ym = datetime.now().strftime("%Y%m")
        row = c.execute(
            "SELECT COUNT(*) FROM orders WHERE order_no LIKE ?",
            (f"SO-{ym}-%",),
        ).fetchone()
        seq = (row[0] if row else 0) + 1
        order_no = f"SO-{ym}-{seq:04d}"
        cur = c.execute(
            """INSERT INTO orders
               (order_no, quote_id, customer_id, order_date, due_date,
                total_amount, status, created_by)
               VALUES (?,?,?,?,?,?,'CONFIRMED',?)""",
            (order_no, quote_id, q[0], date.today().isoformat(),
             due_date, q[1] or 0, u.get("id")),
        )
        order_id = cur.lastrowid
        # 상태 이력 (DRAFT → CONFIRMED)
        c.execute(
            """INSERT INTO order_status_history
               (order_id, from_status, to_status, changed_by, note)
               VALUES (?,?,?,?,?)""",
            (order_id, "DRAFT", "CONFIRMED", u.get("id"), "견적→수주 전환"),
        )
        return JSONResponse({"ok": True, "order_id": order_id, "order_no": order_no})


@app.post("/sales/orders/{order_id}/tax-invoice")
async def sales_order_tax_invoice_update(order_id: int, req: Request):
    """세금계산서 발행여부 체크 (사이클 78 DEC-1)
    KNK 내부 회계 시스템에서 실제 발행 후, HAIST WORKS 는 발행 여부만 기록.
    권한: admin/ceo 또는 영업 (_s1_guard)."""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    issued_raw = (form.get("tax_invoice_issued") or "").strip().lower()
    issued = 1 if issued_raw in ("1", "on", "true", "yes") else 0
    inv_no = (form.get("tax_invoice_no") or "").strip() or None
    inv_date = (form.get("tax_invoice_date") or "").strip() or None
    inv_note = (form.get("tax_invoice_note") or "").strip() or None
    with db_session() as c:
        o = c.execute("SELECT id FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o:
            return JSONResponse({"error": "수주 없음"}, 404)
        c.execute(
            """UPDATE orders
               SET tax_invoice_issued = ?,
                   tax_invoice_no     = ?,
                   tax_invoice_date   = ?,
                   tax_invoice_note   = ?
               WHERE id = ?""",
            (issued, inv_no, inv_date, inv_note, order_id),
        )
    return RedirectResponse("/sales/orders", 303)


@app.get("/sales/production", response_class=HTMLResponse)
async def sales_production_page(req: Request):
    """생산지시 탭 (시안 §1 탭3 WO) — production_orders 리스트 + 진행률"""
    u = _s1_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        rows = c.execute(
            """SELECT p.id, p.order_id, o.order_no,
                      p.planned_start, p.planned_end,
                      p.actual_start, p.actual_end, p.status
               FROM production_orders p
               LEFT JOIN orders o ON o.id = p.order_id
               ORDER BY p.id DESC LIMIT 200"""
        ).fetchall()
        items = [dict(r) for r in rows]
    return ctx(req, "sales_production.html", user=u, active="sales_production",
               tab="production", items=items)


@app.post("/sales/production/start")
async def sales_production_start(req: Request):
    """생산 시작 (Top3-S1-2차 — orders.IN_PRODUCTION + production_orders + history)"""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    order_id = form.get("order_id") or None
    planned_start = form.get("planned_start") or date.today().isoformat()
    planned_end = form.get("planned_end") or None
    if not order_id:
        return JSONResponse({"error": "order_id 누락"}, 400)
    with db_session() as c:
        o = c.execute("SELECT status FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o:
            return JSONResponse({"error": "수주 없음"}, 404)
        prev_status = o[0]
        c.execute(
            "UPDATE orders SET status='IN_PRODUCTION' WHERE id=?", (order_id,)
        )
        cur = c.execute(
            """INSERT INTO production_orders
               (order_id, planned_start, planned_end, actual_start, status)
               VALUES (?,?,?,?,'IN_PRODUCTION')""",
            (order_id, planned_start, planned_end, datetime.now().isoformat(timespec="seconds")),
        )
        c.execute(
            """INSERT INTO order_status_history
               (order_id, from_status, to_status, changed_by, note)
               VALUES (?,?,?,?,?)""",
            (order_id, prev_status, "IN_PRODUCTION", u.get("id"), "생산 시작"),
        )
        return JSONResponse({"ok": True, "production_id": cur.lastrowid})


@app.get("/sales/shipments-receipts", response_class=HTMLResponse)
async def sales_shipments_receipts_page(req: Request):
    """출하·수금 탭 (시안 §1 탭4 DO+INV+RC) — shipments + receipts_payment 통합 라인"""
    u = _s1_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        # 수주별 통합 라인: 출하 합계 + 수금 합계 + 세금계산서 발행 여부
        rows = c.execute(
            """SELECT o.id AS order_id, o.order_no, o.total_amount, o.status,
                      COALESCE(cu.name,'-') AS customer_name,
                      (SELECT COALESCE(SUM(s.shipped_qty),0)
                         FROM shipments s WHERE s.order_id = o.id) AS shipped_qty_sum,
                      (SELECT COALESCE(SUM(r.amount),0)
                         FROM receipts_payment r WHERE r.order_id = o.id) AS paid_total,
                      (SELECT COUNT(*) FROM invoices i
                         WHERE i.order_id = o.id AND i.status='ISSUED') AS invoice_issued
               FROM orders o
               LEFT JOIN customers cu ON cu.id = o.customer_id
               WHERE o.status IN ('IN_PRODUCTION','READY_TO_SHIP','SHIPPED','INVOICED','PAID')
               ORDER BY o.id DESC LIMIT 200"""
        ).fetchall()
        items = [dict(r) for r in rows]
    return ctx(req, "sales_shipments_receipts.html", user=u, active="sales_shipments",
               tab="shipments", items=items)


@app.post("/sales/shipments")
async def sales_shipments_create(req: Request):
    """출하 등록 (Top3-S1-2차 — shipments INSERT + orders.SHIPPED + history · 1:N 부분출하)"""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    order_id = form.get("order_id") or None
    shipped_qty = float(form.get("shipped_qty") or 0)
    tracking = form.get("tracking") or None
    if not order_id:
        return JSONResponse({"error": "order_id 누락"}, 400)
    with db_session() as c:
        o = c.execute("SELECT status FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o:
            return JSONResponse({"error": "수주 없음"}, 404)
        prev_status = o[0]
        cur = c.execute(
            """INSERT INTO shipments
               (order_id, shipped_at, shipped_qty, shipped_by, tracking)
               VALUES (?,?,?,?,?)""",
            (order_id, datetime.now().isoformat(timespec="seconds"),
             shipped_qty, u.get("id"), tracking),
        )
        # SHIPPED 으로 전환 (READY_TO_SHIP 또는 IN_PRODUCTION → SHIPPED)
        if prev_status != "SHIPPED":
            c.execute("UPDATE orders SET status='SHIPPED' WHERE id=?", (order_id,))
            c.execute(
                """INSERT INTO order_status_history
                   (order_id, from_status, to_status, changed_by, note)
                   VALUES (?,?,?,?,?)""",
                (order_id, prev_status, "SHIPPED", u.get("id"),
                 f"출하 등록 (수량 {shipped_qty})"),
            )
        _ship_id = cur.lastrowid
    # 알림시스템 통합 (사이클 2026-04-26) — 출하 담당자에게 SALES 알림 (1시간 중복 방지 내장)
    notify_user(
        u.get("id"), "SALES",
        f"🚚 출하 등록 — 수주 {order_id}",
        body=f"수량 {shipped_qty} / 송장 {tracking or '-'}",
        link=f"/sales/orders/{order_id}",
    )
    return JSONResponse({"ok": True, "shipment_id": _ship_id})


@app.post("/sales/receipts")
async def sales_receipts_create(req: Request):
    """수금 등록 (Top3-S1-2차 — receipts_payment INSERT + 합계 비교 → PAID/유지 + history)
    PARTIAL_RECEIPT 별도 enum 폐기 — 합계 < 수주금액이면 SHIPPED 유지, 합계 >= 이면 PAID."""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    order_id = form.get("order_id") or None
    amount = float(form.get("amount") or 0)
    method = form.get("method") or None
    note = form.get("note") or None
    if not order_id:
        return JSONResponse({"error": "order_id 누락"}, 400)
    with db_session() as c:
        o = c.execute(
            "SELECT status, total_amount FROM orders WHERE id=?", (order_id,)
        ).fetchone()
        if not o:
            return JSONResponse({"error": "수주 없음"}, 404)
        prev_status, total = o[0], (o[1] or 0)
        cur = c.execute(
            """INSERT INTO receipts_payment
               (order_id, received_at, amount, method, received_by, note)
               VALUES (?,?,?,?,?,?)""",
            (order_id, datetime.now().isoformat(timespec="seconds"),
             amount, method, u.get("id"), note),
        )
        # 누적 수금 합계 → PAID 분기 (시안 §3 PAID 강조)
        row = c.execute(
            "SELECT COALESCE(SUM(amount),0) FROM receipts_payment WHERE order_id=?",
            (order_id,),
        ).fetchone()
        paid_total = row[0] or 0
        new_status = "PAID" if paid_total >= total and total > 0 else prev_status
        if new_status != prev_status:
            c.execute(
                "UPDATE orders SET status=? WHERE id=?", (new_status, order_id)
            )
            c.execute(
                """INSERT INTO order_status_history
                   (order_id, from_status, to_status, changed_by, note)
                   VALUES (?,?,?,?,?)""",
                (order_id, prev_status, new_status, u.get("id"),
                 f"수금 누적 {paid_total}/{total}"),
            )
        return JSONResponse({
            "ok": True, "receipt_id": cur.lastrowid,
            "paid_total": paid_total, "status": new_status,
        })


# =====================================================
# Top3 S1 3차 — 매출 대시 강화 + 매출 예측 (2026-04-26)
# 외부 차트·numpy 0건. _linear_regression (line 6572) 재사용.
# G1~G5 핫패치 보존, v2 본체 무수정.
# =====================================================

def _sales_monthly_series(c, months: int = 12):
    """최근 N개월 매출 시계열 (orders.order_date + total_amount).
    반환: [{ym, total, cnt}, ...] (오름차순). 빈 달은 0 채움."""
    today = date.today()
    out = []
    for i in range(months - 1, -1, -1):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        ym = f"{y:04d}-{m:02d}"
        row = c.execute(
            """SELECT COALESCE(SUM(total_amount),0) AS total, COUNT(*) AS cnt
               FROM orders WHERE order_date LIKE ?
                 AND status NOT IN ('CANCELLED','DRAFT')""",
            (f"{ym}%",),
        ).fetchone()
        out.append({"ym": ym, "total": row[0] or 0, "cnt": row[1] or 0})
    return out


def _sales_forecast(series, horizon: int = 3):
    """선형회귀 → 다음 N개월 예측. _linear_regression 재사용 (numpy 0).
    반환: {points:[{ym,total,is_pred}], slope, intercept, r2, horizon, end_ym}."""
    if not series or len(series) < 2:
        return None
    xs = list(range(len(series)))
    ys = [float(s["total"]) for s in series]
    slope, intercept, r2 = _linear_regression(xs, ys)
    pts = [{"ym": s["ym"], "total": s["total"], "is_pred": False} for s in series]
    last_ym = series[-1]["ym"]
    ly, lm = int(last_ym[:4]), int(last_ym[5:7])
    for k in range(1, horizon + 1):
        lm += 1
        if lm > 12:
            lm -= 12
            ly += 1
        x = len(series) - 1 + k
        pred = max(0.0, slope * x + intercept)
        pts.append({"ym": f"{ly:04d}-{lm:02d}", "total": pred, "is_pred": True})
    return {"points": pts, "slope": slope, "intercept": intercept,
            "r_squared": r2, "horizon": horizon, "end_ym": pts[-1]["ym"],
            "end_total": pts[-1]["total"], "sample_n": len(series)}


def _sales_dashboard_ctx(c):
    """대시보드 + 예측 공통 컨텍스트 (KPI 8 + 차트 데이터 + 파이프라인)."""
    today = date.today()
    ym = today.strftime("%Y-%m")
    # 전월
    py, pm = today.year, today.month - 1
    if pm <= 0:
        pm += 12; py -= 1
    prev_ym = f"{py:04d}-{pm:02d}"
    month_total = c.execute(
        """SELECT COALESCE(SUM(total_amount),0) FROM orders
           WHERE order_date LIKE ? AND status NOT IN ('CANCELLED','DRAFT')""",
        (f"{ym}%",),
    ).fetchone()[0] or 0
    prev_total = c.execute(
        """SELECT COALESCE(SUM(total_amount),0) FROM orders
           WHERE order_date LIKE ? AND status NOT IN ('CANCELLED','DRAFT')""",
        (f"{prev_ym}%",),
    ).fetchone()[0] or 0
    mom = ((month_total - prev_total) / prev_total * 100.0) if prev_total > 0 else 0.0
    # 수금률 = 수금 합계 / INVOICED+PAID 수주 합계
    inv_total = c.execute(
        """SELECT COALESCE(SUM(total_amount),0) FROM orders
           WHERE status IN ('INVOICED','PAID','SHIPPED')"""
    ).fetchone()[0] or 0
    rcv_total = c.execute(
        "SELECT COALESCE(SUM(amount),0) FROM receipts_payment"
    ).fetchone()[0] or 0
    rcv_rate = (rcv_total / inv_total * 100.0) if inv_total > 0 else 0.0
    # 평균 결제 일수 (issue_date → 첫 수금)
    avg_days = 0.0
    rows = c.execute(
        """SELECT i.order_id, MIN(i.issue_date) AS iss,
                  MIN(rp.received_at) AS rcv
           FROM invoices i
           LEFT JOIN receipts_payment rp ON rp.order_id = i.order_id
           WHERE i.issue_date IS NOT NULL AND rp.received_at IS NOT NULL
           GROUP BY i.order_id LIMIT 200"""
    ).fetchall()
    if rows:
        days_list = []
        for r in rows:
            try:
                d1 = datetime.strptime(r[1][:10], "%Y-%m-%d")
                d2 = datetime.strptime(r[2][:10], "%Y-%m-%d")
                days_list.append((d2 - d1).days)
            except Exception:
                pass
        if days_list:
            avg_days = sum(days_list) / len(days_list)
    # 미수금 = INVOICED 수주 합 - 수금
    unpaid = max(0.0, inv_total - rcv_total)
    active_orders = c.execute(
        """SELECT COUNT(*) FROM orders
           WHERE status IN ('CONFIRMED','IN_PRODUCTION','READY_TO_SHIP')"""
    ).fetchone()[0] or 0
    in_prod = c.execute(
        "SELECT COUNT(*) FROM production_orders WHERE status='IN_PRODUCTION'"
    ).fetchone()[0] or 0
    # 출하 임박 = due_date 7일 이내 + status IN_PRODUCTION/READY_TO_SHIP
    soon_end = (today + timedelta(days=7)).isoformat()
    ship_soon = c.execute(
        """SELECT COUNT(*) FROM orders
           WHERE due_date IS NOT NULL AND due_date <= ? AND due_date >= ?
             AND status IN ('IN_PRODUCTION','READY_TO_SHIP','CONFIRMED')""",
        (soon_end, today.isoformat()),
    ).fetchone()[0] or 0
    # 파이프라인 9 status 분포
    pipeline = {s: 0 for s in ["DRAFT", "QUOTED", "CONFIRMED", "IN_PRODUCTION",
                                "READY_TO_SHIP", "SHIPPED", "INVOICED", "PAID", "CANCELLED"]}
    for r in c.execute(
        "SELECT status, COUNT(*) AS cnt FROM orders GROUP BY status"
    ).fetchall():
        if r[0] in pipeline:
            pipeline[r[0]] = r[1]
    # 거래처 Top 5 (Pareto)
    top_customers = [dict(r) for r in c.execute(
        """SELECT COALESCE(cu.name,'-') AS name,
                  COUNT(*) AS cnt, COALESCE(SUM(o.total_amount),0) AS total
           FROM orders o LEFT JOIN customers cu ON cu.id = o.customer_id
           WHERE o.status NOT IN ('CANCELLED','DRAFT')
           GROUP BY o.customer_id ORDER BY total DESC LIMIT 5"""
    ).fetchall()]
    grand_total = sum(t["total"] for t in top_customers) or 1
    cum = 0.0
    for t in top_customers:
        cum += t["total"]
        t["pct"] = (t["total"] / grand_total * 100.0)
        t["cum_pct"] = (cum / grand_total * 100.0)
    series = _sales_monthly_series(c, 12)
    chart_max = max((s["total"] for s in series), default=1) or 1
    return {
        "kpi": {
            "month_total": month_total, "mom": mom,
            "rcv_rate": rcv_rate, "avg_days": avg_days,
            "unpaid": unpaid, "active_orders": active_orders,
            "in_prod": in_prod, "ship_soon": ship_soon,
        },
        "ym": ym, "prev_ym": prev_ym,
        "pipeline": pipeline,
        "top_customers": top_customers,
        "series": series, "chart_max": chart_max,
    }


@app.get("/sales/dashboard", response_class=HTMLResponse)
async def sales_dashboard_v3(req: Request):
    """Top3-S1-3차 강화 대시 — KPI 8 + 월별 차트 + Pareto Top5 + 파이프라인 9."""
    u = _s1_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        ctx_data = _sales_dashboard_ctx(c)
    return ctx(req, "sales_dashboard.html", user=u, active="sales_dashboard",
               tab="dashboard", **ctx_data)


@app.get("/sales/forecast", response_class=HTMLResponse)
async def sales_forecast_page(req: Request):
    """Top3-S1-3차 매출 예측 — 최근 12개월 → 향후 3개월 (선형회귀, R²)."""
    u = _s1_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        series = _sales_monthly_series(c, 12)
    fc_row = None  # 매출 전용 저장 테이블은 다음 사이클 (read-only)
    forecast = _sales_forecast(series, horizon=3)
    chart_max = max(
        max((s["total"] for s in series), default=1),
        max((p["total"] for p in (forecast["points"] if forecast else [])), default=1),
    ) or 1
    return ctx(req, "sales_forecast.html", user=u, active="sales",
               tab="forecast", series=series, forecast=forecast,
               chart_max=chart_max, saved_forecast=fc_row)


@app.post("/sales/forecast/refresh")
async def sales_forecast_refresh(req: Request):
    """Top3-S1-3차 예측 재계산 트리거 — JSON {ok, end_ym, end_total, r2, sample_n}."""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    with db_session() as c:
        series = _sales_monthly_series(c, 12)
    fc = _sales_forecast(series, horizon=3)
    if not fc:
        return JSONResponse({"error": "insufficient_data",
                              "sample_n": len(series)}, status_code=400)
    return JSONResponse({
        "ok": True, "end_ym": fc["end_ym"],
        "end_total": fc["end_total"], "r_squared": fc["r_squared"],
        "slope": fc["slope"], "sample_n": fc["sample_n"],
    })


# =====================================================
# Top3 S1 4차 — 미수금 추적 + 수금 알림 자동 (2026-04-26)
# 헬퍼 _outstanding_receivables / check_receivable_alerts.
# 알림 통합 (사이클 2026-04-26 notify_user SALES) 활용 · 1시간 중복 방지 내장.
# G1~G5 핫패치 보존 · v2 본체 무수정 · 외부 자산 0건.
# =====================================================

def _parse_terms_days(terms: str) -> int:
    """payment_terms 문자열 → 일수. NET30/30일/선금 등 휴리스틱.
    매칭 실패 시 30 (기본 NET30)."""
    if not terms:
        return 30
    s = str(terms).upper().replace(" ", "")
    # NET#, #일, #DAYS
    import re
    m = re.search(r"(\d{1,3})", s)
    if m:
        try:
            d = int(m.group(1))
            if 0 < d <= 365:
                return d
        except Exception:
            pass
    if "선금" in str(terms) or "CASH" in s or "현금" in str(terms):
        return 0
    return 30


def _outstanding_receivables(c, only_overdue: bool = False):
    """미수금 건별 집계 — orders.total_amount - SUM(receipts_payment.amount).
    연체일 = today - (order_date + payment_terms.terms days).
    등급: CURRENT(미만기) / D-30 / D-60 / D-90+ (연체일 기준).
    Returns: list of dicts (overdue desc).
    """
    today = date.today()
    rows = c.execute(
        """SELECT o.id AS order_id, o.order_no, o.order_date, o.due_date,
                  o.total_amount, o.status, o.customer_id,
                  COALESCE(cu.name,'-') AS customer_name,
                  COALESCE((SELECT SUM(amount) FROM receipts_payment rp
                            WHERE rp.order_id=o.id), 0) AS paid_total,
                  COALESCE((SELECT terms FROM payment_terms pt
                            WHERE pt.customer_id=o.customer_id
                            ORDER BY pt.id DESC LIMIT 1), '') AS terms
           FROM orders o
           LEFT JOIN customers cu ON cu.id = o.customer_id
           WHERE o.status IN ('SHIPPED','INVOICED')
             AND o.total_amount > 0"""
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        outstanding = (d["total_amount"] or 0) - (d["paid_total"] or 0)
        if outstanding <= 0:
            continue
        # 만기일: order_date + terms일
        days_terms = _parse_terms_days(d["terms"])
        try:
            od = datetime.strptime((d["order_date"] or today.isoformat())[:10], "%Y-%m-%d").date()
        except Exception:
            od = today
        due = od + timedelta(days=days_terms)
        overdue_days = (today - due).days  # 음수 = 만기 이전
        if only_overdue and overdue_days <= 0:
            continue
        if overdue_days <= 0:
            grade = "CURRENT"
        elif overdue_days <= 30:
            grade = "D-30"
        elif overdue_days <= 60:
            grade = "D-60"
        else:
            grade = "D-90+"
        d["outstanding"] = outstanding
        d["due_date_calc"] = due.isoformat()
        d["overdue_days"] = overdue_days
        d["grade"] = grade
        d["terms_days"] = days_terms
        out.append(d)
    out.sort(key=lambda x: (-x["overdue_days"], -x["outstanding"]))
    return out


def _outstanding_summary(items):
    """등급별 집계 KPI."""
    grades = {"CURRENT": 0.0, "D-30": 0.0, "D-60": 0.0, "D-90+": 0.0}
    counts = {"CURRENT": 0, "D-30": 0, "D-60": 0, "D-90+": 0}
    total = 0.0
    overdue_total = 0.0
    for it in items:
        g = it["grade"]
        amt = it["outstanding"]
        grades[g] = grades.get(g, 0.0) + amt
        counts[g] = counts.get(g, 0) + 1
        total += amt
        if g != "CURRENT":
            overdue_total += amt
    return {
        "by_grade": grades, "counts": counts,
        "total": total, "overdue_total": overdue_total,
        "n_total": len(items),
        "overdue_rate": (overdue_total / total * 100.0) if total > 0 else 0.0,
    }


def check_receivable_alerts():
    """수금 알림 트리거 — 만기 임박(D-7) + 연체(D+1, D+30, D+60).
    notify_user(SALES, ...) 사용 (1시간 중복 방지 내장).
    수신자: orders.created_by (수주 등록자) → can_use_sales 폴백.
    Returns: {sent: int, skipped: int, items: int}.
    """
    sent = 0; skipped = 0; total_items = 0
    with db_session() as c:
        items = _outstanding_receivables(c)
        total_items = len(items)
        # 영업 권한자 폴백 (주된 알림 대상 미상시)
        sales_uids = [r[0] for r in c.execute(
            "SELECT id FROM users WHERE can_use_sales=1 OR role IN ('admin','ceo')"
        ).fetchall()]
        for it in items:
            ov = it["overdue_days"]
            order_no = it.get("order_no") or f"#{it['order_id']}"
            cust = it.get("customer_name") or "-"
            outstanding = it.get("outstanding") or 0
            # 발송 조건: 만기 7일 임박 OR 연체 1/30/60일 도달
            tag = None
            if ov == -7:
                tag = "만기 임박 (D-7)"
            elif ov == 1:
                tag = "연체 1일"
            elif ov == 30:
                tag = "연체 30일"
            elif ov == 60:
                tag = "연체 60일"
            if not tag:
                continue
            title = f"💰 미수금 {tag} — {order_no}"
            body = (f"거래처: {cust} / 미수금: {int(outstanding):,}원 / "
                    f"등급: {it['grade']} / 만기: {it['due_date_calc']}")
            link = f"/sales/orders/{it['order_id']}"
            # 우선 created_by, 폴백 영업권한자 전체
            recipients = []
            cb = c.execute(
                "SELECT created_by FROM orders WHERE id=?", (it["order_id"],)
            ).fetchone()
            if cb and cb[0]:
                recipients.append(cb[0])
            else:
                recipients.extend(sales_uids)
            for uid in recipients:
                if notify_user(uid, "SALES", title, body=body, link=link):
                    sent += 1
                else:
                    skipped += 1
    return {"sent": sent, "skipped": skipped, "items": total_items}


@app.get("/sales/outstanding", response_class=HTMLResponse)
async def sales_outstanding_page(req: Request):
    """Top3-S1-4차 미수금 대시 — 등급별 집계 + 상세 (D-30/D-60/D-90+/CURRENT)."""
    u = _s1_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        items = _outstanding_receivables(c)
    summary = _outstanding_summary(items)
    return ctx(req, "sales_outstanding.html", user=u, active="sales_outstanding",
               tab="outstanding", items=items, summary=summary)


@app.get("/sales/aging", response_class=HTMLResponse)
async def sales_aging_page(req: Request):
    """Top3-S1-4차 연체 분석 — 거래처별 연체 매트릭스 (히트맵 테이블)."""
    u = _s1_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        items = _outstanding_receivables(c)
    # 거래처 × 등급 매트릭스
    matrix = {}
    for it in items:
        cust = it.get("customer_name") or "-"
        if cust not in matrix:
            matrix[cust] = {"CURRENT": 0.0, "D-30": 0.0, "D-60": 0.0,
                             "D-90+": 0.0, "total": 0.0, "max_overdue": 0}
        matrix[cust][it["grade"]] += it["outstanding"]
        matrix[cust]["total"] += it["outstanding"]
        if it["overdue_days"] > matrix[cust]["max_overdue"]:
            matrix[cust]["max_overdue"] = it["overdue_days"]
    rows = sorted(
        [{"customer": k, **v} for k, v in matrix.items()],
        key=lambda x: (-x["max_overdue"], -x["total"]),
    )
    summary = _outstanding_summary(items)
    return ctx(req, "sales_aging.html", user=u, active="sales",
               tab="aging", rows=rows, summary=summary)


@app.post("/sales/alerts/check")
async def sales_alerts_check(req: Request):
    """Top3-S1-4차 수금 알림 수동 트리거 — JSON {sent, skipped, items}."""
    u = _s1_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    result = check_receivable_alerts()
    return JSONResponse({"ok": True, **result})


# =====================================================
# 수출입 서류 — P11 베트남 수출 실무자 1차 라우트 골격 (2026-04-25)
# 한국 수출 표준 4단계: CI(상업송장) / PL(패킹리스트) / BL(선하증권) / 관세신고
# 1차 = 골격만 (UI 본문 · 외부 운송사 API 미도입 · 다음 사이클).
# 권한: P11(team_id=12 베트남법인) OR admin/ceo/executive OR can_use_sales.
# 매출 자동 채움: orders 테이블 참조 → export_orders INSERT 시 자동 조회.
# =====================================================
def _export_guard(req: Request):
    """수출입 권한 가드 — 베트남법인(team_id=12) OR admin/ceo/executive OR 영업권한자."""
    u = get_user(req)
    if not u:
        return None
    role = u.get("role") if isinstance(u, dict) else u["role"]
    if role in ("admin", "ceo", "executive"):
        return u
    team_id = u.get("team_id") if isinstance(u, dict) else u["team_id"]
    if team_id == 12:  # 12 베트남법인 (P11)
        return u
    if can_use_sales(u):
        return u
    return None


@app.get("/export", response_class=HTMLResponse)
async def export_home(req: Request):
    """수출 메인 (수주 목록 + 진행 상태 KPI) — 2차 본문."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        rows = c.execute(
            """SELECT eo.id, eo.buyer, eo.shipping_terms, eo.payment_terms,
                      eo.port_of_loading, eo.port_of_discharge, eo.status,
                      eo.created_at, eo.order_id,
                      COALESCE(o.order_no,'-') AS order_no,
                      COALESCE(o.total_amount,0) AS order_amount
               FROM export_orders eo
               LEFT JOIN orders o ON o.id = eo.order_id
               ORDER BY eo.id DESC LIMIT 200"""
        ).fetchall()
        items = [dict(r) for r in rows]
        # 상태별 카운트 (KPI)
        st_rows = c.execute(
            "SELECT status, COUNT(*) AS n FROM export_orders GROUP BY status"
        ).fetchall()
        st_map = {r["status"]: r["n"] for r in st_rows}
    return ctx(req, "export_home.html", user=u, active="export", items=items,
               st_draft=st_map.get("DRAFT", 0),
               st_ci=st_map.get("CI_ISSUED", 0),
               st_pl=st_map.get("PL_READY", 0),
               st_ship=st_map.get("SHIPPED", 0),
               st_clr=st_map.get("CLEARED", 0))


@app.get("/export/orders/new", response_class=HTMLResponse)
async def export_order_new_form(req: Request):
    """수출 수주 등록 폼 — 1차 골격 (UI 본문 다음 사이클)."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        orders = [dict(r) for r in c.execute(
            """SELECT id, order_no, customer_id, total_amount, order_date
               FROM orders ORDER BY id DESC LIMIT 100"""
        ).fetchall()]
    return ctx(req, "export_order_form.html", user=u, active="export",
               orders=orders)


@app.post("/export/orders")
async def export_order_create(req: Request):
    """수출 수주 INSERT — 매출 자동 채움 가설 핸들러.
    order_id 받으면 orders 에서 customer / total_amount / order_date 자동 조회."""
    u = _export_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    order_id = form.get("order_id") or None
    buyer = form.get("buyer") or None
    shipping_terms = form.get("shipping_terms") or None
    payment_terms = form.get("payment_terms") or None
    port_of_loading = form.get("port_of_loading") or "BUSAN"
    port_of_discharge = form.get("port_of_discharge") or None
    with db_session() as c:
        # 매출 자동 채움 — order_id 검증 (orders 존재 확인)
        if order_id:
            o = c.execute(
                "SELECT id, customer_id, total_amount, order_date FROM orders WHERE id=?",
                (order_id,)
            ).fetchone()
            if not o:
                return JSONResponse({"error": "수주 없음(order_id)"}, 404)
        cur = c.execute(
            """INSERT INTO export_orders
               (order_id, buyer, shipping_terms, payment_terms,
                port_of_loading, port_of_discharge, status, created_by)
               VALUES (?,?,?,?,?,?,'DRAFT',?)""",
            (order_id, buyer, shipping_terms, payment_terms,
             port_of_loading, port_of_discharge, u.get("id")),
        )
        return JSONResponse({"ok": True, "export_order_id": cur.lastrowid})


@app.get("/export/orders/{eo_id}", response_class=HTMLResponse)
async def export_order_detail(req: Request, eo_id: int):
    """수출 수주 상세 (CI/PL/BL/관세 탭) — 1차 골격."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        eo = c.execute(
            """SELECT eo.*, COALESCE(o.order_no,'-') AS order_no,
                      COALESCE(o.total_amount,0) AS order_amount,
                      COALESCE(o.order_date,'-') AS order_date,
                      COALESCE(cu.name,'-') AS customer_name
               FROM export_orders eo
               LEFT JOIN orders o ON o.id = eo.order_id
               LEFT JOIN customers cu ON cu.id = o.customer_id
               WHERE eo.id = ?""",
            (eo_id,)
        ).fetchone()
        if not eo:
            return RedirectResponse("/export", 303)
        eo = dict(eo)
        ci = [dict(r) for r in c.execute(
            "SELECT * FROM commercial_invoices WHERE export_order_id=? ORDER BY id DESC",
            (eo_id,)).fetchall()]
        pl = [dict(r) for r in c.execute(
            "SELECT * FROM packing_lists WHERE export_order_id=? ORDER BY id DESC",
            (eo_id,)).fetchall()]
        bl = [dict(r) for r in c.execute(
            "SELECT * FROM bills_of_lading WHERE export_order_id=? ORDER BY id DESC",
            (eo_id,)).fetchall()]
        cu_decl = [dict(r) for r in c.execute(
            "SELECT * FROM customs_declarations WHERE export_order_id=? ORDER BY id DESC",
            (eo_id,)).fetchall()]
    return ctx(req, "export_order_detail.html", user=u, active="export",
               eo=eo, ci=ci, pl=pl, bl=bl, customs=cu_decl)


@app.get("/export/ci/{eo_id}", response_class=HTMLResponse)
async def export_ci_form(req: Request, eo_id: int):
    """CI 작성/조회 (매출 자동 채움) — 2차 본문."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        eo = c.execute(
            """SELECT eo.*, COALESCE(o.total_amount,0) AS order_amount
               FROM export_orders eo
               LEFT JOIN orders o ON o.id = eo.order_id
               WHERE eo.id = ?""", (eo_id,)).fetchone()
        if not eo:
            return RedirectResponse("/export", 303)
        eo = dict(eo)
        items = [dict(r) for r in c.execute(
            "SELECT * FROM commercial_invoices WHERE export_order_id=? ORDER BY id DESC",
            (eo_id,)).fetchall()]
    return ctx(req, "export_ci.html", user=u, active="export",
               eo=eo, items=items, today=date.today().isoformat())


def _next_seq_no(c, table: str, col: str, prefix: str) -> str:
    """월별 시퀀스 발급 — `{prefix}-YYYYMM-####` (idempotent · race 방어 transaction 내).
    예: CI-202604-0001, PL-202604-0023."""
    ym = datetime.now().strftime("%Y%m")
    pat = f"{prefix}-{ym}-%"
    row = c.execute(
        f"SELECT {col} FROM {table} WHERE {col} LIKE ? "
        f"ORDER BY {col} DESC LIMIT 1", (pat,)
    ).fetchone()
    if row and row[col]:
        try:
            seq = int(str(row[col]).rsplit("-", 1)[-1]) + 1
        except Exception:
            seq = 1
    else:
        seq = 1
    return f"{prefix}-{ym}-{seq:04d}"


@app.post("/export/ci")
async def export_ci_create(req: Request):
    """CI INSERT — 2차 본문.
    invoice_no = `CI-YYYYMM-####` 자동. total_amount = 폼 우선, 미입력 시 orders 자동 채움.
    동시 UPDATE export_orders.status DRAFT/BOOKED → CI_ISSUED."""
    u = _export_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    eo_id = form.get("export_order_id")
    if not eo_id:
        return JSONResponse({"error": "export_order_id 필수"}, 400)
    issue_date = form.get("issue_date") or date.today().isoformat()
    currency = form.get("currency") or "USD"
    raw_amt = form.get("total_amount")
    with db_session() as c:
        eo = c.execute(
            """SELECT eo.id, eo.status, COALESCE(o.total_amount,0) AS auto_amt
               FROM export_orders eo LEFT JOIN orders o ON o.id=eo.order_id
               WHERE eo.id=?""", (eo_id,)).fetchone()
        if not eo:
            return JSONResponse({"error": "수출 수주 없음"}, 404)
        # 매출 자동 채움 — 폼 미입력 시 orders.total_amount
        try:
            total_amount = float(raw_amt) if raw_amt not in (None, "") else float(eo["auto_amt"] or 0)
        except Exception:
            total_amount = float(eo["auto_amt"] or 0)
        invoice_no = _next_seq_no(c, "commercial_invoices", "invoice_no", "CI")
        cur = c.execute(
            """INSERT INTO commercial_invoices
               (invoice_no, export_order_id, issue_date, total_amount, currency,
                signed_by, status)
               VALUES (?,?,?,?,?,?, 'ISSUED')""",
            (invoice_no, eo_id, issue_date, total_amount, currency, u.get("id")),
        )
        # 상태 전이: DRAFT/BOOKED → CI_ISSUED
        if eo["status"] in ("DRAFT", "BOOKED"):
            c.execute(
                "UPDATE export_orders SET status='CI_ISSUED' WHERE id=?", (eo_id,)
            )
    return RedirectResponse(f"/export/orders/{eo_id}", 303)


@app.get("/export/pl/{eo_id}", response_class=HTMLResponse)
async def export_pl_form(req: Request, eo_id: int):
    """PL 작성/조회 — 1차 골격."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        eo = c.execute(
            "SELECT * FROM export_orders WHERE id=?", (eo_id,)).fetchone()
        if not eo:
            return RedirectResponse("/export", 303)
        eo = dict(eo)
        items = [dict(r) for r in c.execute(
            "SELECT * FROM packing_lists WHERE export_order_id=? ORDER BY id DESC",
            (eo_id,)).fetchall()]
    return ctx(req, "export_pl.html", user=u, active="export",
               eo=eo, items=items)


@app.post("/export/pl")
async def export_pl_create(req: Request):
    """PL INSERT — 2차 본문 (헤더 + 다중 라인 packing_items).
    pl_no = `PL-YYYYMM-####`. 라인 합계는 폼 total_* 우선, 라인만 있으면 서버 합산.
    동시 UPDATE export_orders.status CI_ISSUED → PL_READY."""
    u = _export_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    eo_id = form.get("export_order_id")
    if not eo_id:
        return JSONResponse({"error": "export_order_id 필수"}, 400)
    # 다중 라인 — line_qty 등 getlist
    line_parts = form.getlist("line_part")
    line_qtys = form.getlist("line_qty")
    line_pkgs = form.getlist("line_pkg")
    line_ws = form.getlist("line_weight")
    line_vs = form.getlist("line_volume")
    # 헤더 합계 (폼 → 미입력 시 서버 재합산)
    def _f(x, d=0.0):
        try: return float(x) if x not in (None, "") else d
        except: return d
    tot_pkg = int(_f(form.get("total_packages")))
    tot_w = _f(form.get("total_weight"))
    tot_v = _f(form.get("total_volume"))
    if tot_pkg == 0 and line_qtys:
        tot_pkg = int(sum(_f(q) for q in line_qtys))
    if tot_w == 0 and line_ws:
        tot_w = sum(_f(w) for w in line_ws)
    if tot_v == 0 and line_vs:
        tot_v = sum(_f(v) for v in line_vs)
    with db_session() as c:
        eo = c.execute(
            "SELECT id, status FROM export_orders WHERE id=?", (eo_id,)).fetchone()
        if not eo:
            return JSONResponse({"error": "수출 수주 없음"}, 404)
        pl_no = _next_seq_no(c, "packing_lists", "pl_no", "PL")
        cur = c.execute(
            """INSERT INTO packing_lists
               (pl_no, export_order_id, total_packages, total_weight, total_volume)
               VALUES (?,?,?,?,?)""",
            (pl_no, eo_id, tot_pkg, tot_w, tot_v),
        )
        pl_id = cur.lastrowid
        # 라인 INSERT (다중)
        n = max(len(line_parts), len(line_qtys))
        for i in range(n):
            qty = _f(line_qtys[i] if i < len(line_qtys) else 0)
            if qty <= 0:
                continue
            c.execute(
                """INSERT INTO packing_items
                   (pl_id, part_id, qty, package_type, weight, volume)
                   VALUES (?, NULL, ?, ?, ?, ?)""",
                (pl_id, qty,
                 (line_pkgs[i] if i < len(line_pkgs) else "CARTON"),
                 _f(line_ws[i] if i < len(line_ws) else 0),
                 _f(line_vs[i] if i < len(line_vs) else 0)),
            )
        # 상태 전이: CI_ISSUED → PL_READY (DRAFT/BOOKED 도 허용 — 동시 진행)
        if eo["status"] in ("DRAFT", "BOOKED", "CI_ISSUED"):
            c.execute(
                "UPDATE export_orders SET status='PL_READY' WHERE id=?", (eo_id,)
            )
    return RedirectResponse(f"/export/orders/{eo_id}", 303)


@app.get("/export/bl/{eo_id}", response_class=HTMLResponse)
async def export_bl_form(req: Request, eo_id: int):
    """BL · 관세 통합 폼 — 2차 본문 (CI 자동 채움 → declared_value)."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        eo = c.execute(
            "SELECT * FROM export_orders WHERE id=?", (eo_id,)).fetchone()
        if not eo:
            return RedirectResponse("/export", 303)
        eo = dict(eo)
        bl = [dict(r) for r in c.execute(
            "SELECT * FROM bills_of_lading WHERE export_order_id=? ORDER BY id DESC",
            (eo_id,)).fetchall()]
        customs = [dict(r) for r in c.execute(
            "SELECT * FROM customs_declarations WHERE export_order_id=? ORDER BY id DESC",
            (eo_id,)).fetchall()]
        # CI 자동 채움 — 가장 최근 ISSUED CI 의 total_amount
        ci_row = c.execute(
            """SELECT total_amount FROM commercial_invoices
               WHERE export_order_id=? AND status='ISSUED'
               ORDER BY id DESC LIMIT 1""", (eo_id,)).fetchone()
        ci_amount = ci_row["total_amount"] if ci_row else 0
    return ctx(req, "export_bl_customs.html", user=u, active="export",
               eo=eo, bl=bl, customs=customs, ci_amount=ci_amount,
               today=date.today().isoformat())


@app.post("/export/bl")
async def export_bl_create(req: Request):
    """BL INSERT — 2차 본문 (외부 운송사 API 미사용 · 수동 입력 그대로 저장).
    동시 UPDATE export_orders.status PL_READY/CI_ISSUED → SHIPPED."""
    u = _export_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    eo_id = form.get("export_order_id")
    bl_no = (form.get("bl_no") or "").strip()
    if not eo_id or not bl_no:
        return JSONResponse({"error": "export_order_id / bl_no 필수"}, 400)
    with db_session() as c:
        eo = c.execute(
            "SELECT id, status FROM export_orders WHERE id=?", (eo_id,)).fetchone()
        if not eo:
            return JSONResponse({"error": "수출 수주 없음"}, 404)
        c.execute(
            """INSERT INTO bills_of_lading
               (bl_no, export_order_id, shipping_company, vessel,
                departure_date, arrival_date, tracking_no, status)
               VALUES (?,?,?,?,?,?,?, 'ISSUED')""",
            (bl_no, eo_id,
             form.get("shipping_company") or None,
             form.get("vessel") or None,
             form.get("departure_date") or None,
             form.get("arrival_date") or None,
             form.get("tracking_no") or None),
        )
        # 상태 전이: PL_READY/CI_ISSUED/BOOKED → SHIPPED
        if eo["status"] in ("DRAFT", "BOOKED", "CI_ISSUED", "PL_READY"):
            c.execute(
                "UPDATE export_orders SET status='SHIPPED' WHERE id=?", (eo_id,)
            )
    return RedirectResponse(f"/export/orders/{eo_id}", 303)


@app.get("/export/customs/{eo_id}", response_class=HTMLResponse)
async def export_customs_view(req: Request, eo_id: int):
    """관세 신고 조회 — 1차 골격 (BL 템플릿 재사용)."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    return RedirectResponse(f"/export/bl/{eo_id}", 303)


@app.post("/export/customs")
async def export_customs_create(req: Request):
    """관세 신고 INSERT — 2차 본문.
    declared_value = 폼 우선, 미입력 시 최신 CI total_amount 자동 채움.
    동시 UPDATE export_orders.status SHIPPED → CLEARED."""
    u = _export_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    eo_id = form.get("export_order_id")
    hs_code = (form.get("hs_code") or "").strip()
    if not eo_id or not hs_code:
        return JSONResponse({"error": "export_order_id / hs_code 필수"}, 400)
    declaration_no = (form.get("declaration_no") or "").strip() or None
    fta_origin = form.get("fta_origin") or None
    raw_dv = form.get("declared_value")
    with db_session() as c:
        eo = c.execute(
            "SELECT id, status FROM export_orders WHERE id=?", (eo_id,)).fetchone()
        if not eo:
            return JSONResponse({"error": "수출 수주 없음"}, 404)
        # CI 자동 채움
        try:
            declared_value = float(raw_dv) if raw_dv not in (None, "") else 0.0
        except Exception:
            declared_value = 0.0
        if declared_value <= 0:
            ci_row = c.execute(
                """SELECT total_amount FROM commercial_invoices
                   WHERE export_order_id=? AND status='ISSUED'
                   ORDER BY id DESC LIMIT 1""", (eo_id,)).fetchone()
            if ci_row:
                declared_value = float(ci_row["total_amount"] or 0)
        c.execute(
            """INSERT INTO customs_declarations
               (declaration_no, export_order_id, hs_code, fta_origin,
                declared_value, cleared_at, status)
               VALUES (?,?,?,?,?, datetime('now','localtime'), 'CLEARED')""",
            (declaration_no, eo_id, hs_code, fta_origin, declared_value),
        )
        # 상태 전이: SHIPPED → CLEARED
        if eo["status"] in ("DRAFT", "BOOKED", "CI_ISSUED", "PL_READY", "SHIPPED"):
            c.execute(
                "UPDATE export_orders SET status='CLEARED' WHERE id=?", (eo_id,)
            )
    return RedirectResponse(f"/export/orders/{eo_id}", 303)


# =====================================================
# 수출입 P11 3차 — 인쇄용 view + 일정 자동 알림 (2026-04-26)
# 외부 PDF 라이브러리 0건. HTML 인쇄 layout(@media print) 만 사용.
# G1~G5 핫패치 보존, v2 본체 무수정.
# =====================================================
@app.get("/export/ci/{ci_id}/print", response_class=HTMLResponse)
async def export_ci_print(req: Request, ci_id: int):
    """CI 인쇄용 (한국어 + 영어 양식 · 헤더/사이드바 숨김)."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        ci = c.execute(
            """SELECT ci.*, eo.buyer, eo.shipping_terms, eo.payment_terms,
                      eo.port_of_loading, eo.port_of_discharge,
                      COALESCE(o.order_no,'-') AS order_no,
                      COALESCE(cu.name,'-') AS customer_name
               FROM commercial_invoices ci
               JOIN export_orders eo ON eo.id = ci.export_order_id
               LEFT JOIN orders o ON o.id = eo.order_id
               LEFT JOIN customers cu ON cu.id = o.customer_id
               WHERE ci.id = ?""", (ci_id,)).fetchone()
        if not ci:
            return RedirectResponse("/export", 303)
        ci = dict(ci)
    return tpl.TemplateResponse(
        "export_ci_print.html",
        {"request": req, "ci": ci, "today": date.today().isoformat()})


@app.get("/export/pl/{pl_id}/print", response_class=HTMLResponse)
async def export_pl_print(req: Request, pl_id: int):
    """PL 인쇄용 (라인 합계 · 헤더/사이드바 숨김)."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        pl = c.execute(
            """SELECT pl.*, eo.buyer, eo.shipping_terms,
                      eo.port_of_loading, eo.port_of_discharge,
                      COALESCE(o.order_no,'-') AS order_no
               FROM packing_lists pl
               JOIN export_orders eo ON eo.id = pl.export_order_id
               LEFT JOIN orders o ON o.id = eo.order_id
               WHERE pl.id = ?""", (pl_id,)).fetchone()
        if not pl:
            return RedirectResponse("/export", 303)
        pl = dict(pl)
        lines = [dict(r) for r in c.execute(
            "SELECT * FROM packing_items WHERE pl_id=? ORDER BY id ASC",
            (pl_id,)).fetchall()]
    return tpl.TemplateResponse(
        "export_pl_print.html",
        {"request": req, "pl": pl, "lines": lines,
         "today": date.today().isoformat()})


@app.get("/export/bl/{bl_id}/print", response_class=HTMLResponse)
async def export_bl_print(req: Request, bl_id: int):
    """BL/관세 인쇄용 (헤더/사이드바 숨김)."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        bl = c.execute(
            """SELECT bl.*, eo.buyer, eo.shipping_terms,
                      eo.port_of_loading, eo.port_of_discharge,
                      COALESCE(o.order_no,'-') AS order_no
               FROM bills_of_lading bl
               JOIN export_orders eo ON eo.id = bl.export_order_id
               LEFT JOIN orders o ON o.id = eo.order_id
               WHERE bl.id = ?""", (bl_id,)).fetchone()
        if not bl:
            return RedirectResponse("/export", 303)
        bl = dict(bl)
        customs = [dict(r) for r in c.execute(
            "SELECT * FROM customs_declarations WHERE export_order_id=? ORDER BY id DESC",
            (bl["export_order_id"],)).fetchall()]
    return tpl.TemplateResponse(
        "export_bl_print.html",
        {"request": req, "bl": bl, "customs": customs,
         "today": date.today().isoformat()})


def check_export_alerts():
    """수출입 일정 자동 알림 — 출하 D-3 / CI 만료(90일) / 관세 신고 임박.
    notify_user 1시간 중복 방지 내장. 매 호출 idempotent.
    Returns: {'shipping': n, 'ci_expire': n, 'customs': n} 카운트."""
    fired = {"shipping": 0, "ci_expire": 0, "customs": 0}
    today = date.today()
    d3 = (today + timedelta(days=3)).isoformat()
    today_iso = today.isoformat()
    d90 = (today - timedelta(days=90)).isoformat()
    with db_session() as c:
        # 베트남법인(team_id=12) + admin/ceo/executive + 영업권 사용자에게 송부
        recipients = [r["id"] for r in c.execute(
            "SELECT id FROM users WHERE is_active=1 AND "
            "(team_id=12 OR role IN ('admin','ceo','executive'))"
        ).fetchall()]
        # 1) 출하 임박 D-3 — bills_of_lading.departure_date
        bls = c.execute(
            """SELECT bl.id, bl.bl_no, bl.departure_date, bl.export_order_id
               FROM bills_of_lading bl
               WHERE bl.departure_date IS NOT NULL
                 AND bl.departure_date BETWEEN ? AND ?
                 AND bl.status IN ('DRAFT','ISSUED')""",
            (today_iso, d3)).fetchall()
        for bl in bls:
            for uid in recipients:
                if notify_user(uid, "EXPORT",
                               f"출하 임박 D-3 — B/L {bl['bl_no']}",
                               f"출항일 {bl['departure_date']}",
                               f"/export/orders/{bl['export_order_id']}"):
                    fired["shipping"] += 1
        # 2) CI 만료 — issue_date + 90일 경과 ISSUED 상태
        cis = c.execute(
            """SELECT id, invoice_no, issue_date, export_order_id
               FROM commercial_invoices
               WHERE status='ISSUED' AND issue_date IS NOT NULL
                 AND issue_date <= ?""", (d90,)).fetchall()
        for ci in cis:
            for uid in recipients:
                if notify_user(uid, "EXPORT",
                               f"CI 만료 — {ci['invoice_no']} (90일 경과)",
                               f"발급일 {ci['issue_date']}",
                               f"/export/orders/{ci['export_order_id']}"):
                    fired["ci_expire"] += 1
        # 3) 관세 신고 임박 — SHIPPED 인데 미신고
        ships = c.execute(
            """SELECT eo.id FROM export_orders eo
               WHERE eo.status='SHIPPED'
                 AND NOT EXISTS (SELECT 1 FROM customs_declarations cd
                                 WHERE cd.export_order_id=eo.id
                                   AND cd.status IN ('SUBMITTED','CLEARED'))"""
        ).fetchall()
        for eo in ships:
            for uid in recipients:
                if notify_user(uid, "EXPORT",
                               f"관세 신고 미접수 — 수출 #{eo['id']}",
                               "출하 후 관세 신고가 누락되었습니다.",
                               f"/export/orders/{eo['id']}"):
                    fired["customs"] += 1
    return fired


@app.post("/export/alerts/check")
async def export_alerts_check(req: Request):
    """수출입 일정 알림 점검 트리거 (관리자/CEO 전용)."""
    u = _export_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    role = u.get("role") if isinstance(u, dict) else u["role"]
    if role not in ("admin", "ceo", "executive"):
        return JSONResponse({"error": "관리자 전용"}, 403)
    fired = check_export_alerts()
    return JSONResponse({"ok": True, "fired": fired})


# =====================================================
# HAIST WORKS — 진행 간트/번다운 1차 (2026-04-26 갭서베이 Top10 #4)
# DB: project_milestones / project_burndown_snapshots (idempotent)
# UI: progress_gantt.html / progress_burndown.html (외부 차트 라이브러리 0)
# 페르소나: P1 PM(주 2~3회) · P2 CEO 전사 대시
# =====================================================
def _progress_guard(req: Request, project_id: int = None):
    """진행 가드 — admin/ceo/executive OR PM(pm_id) OR 프로젝트 lead OR 동일 팀."""
    u = get_user(req)
    if not u:
        return None
    role = u.get("role") if isinstance(u, dict) else u["role"]
    if role in ("admin", "ceo", "executive"):
        return u
    if project_id is None:
        return u  # 전사 대시는 별도 분기 (대시 라우트에서 admin/ceo만 허용)
    with db_session() as c:
        proj = c.execute(
            "SELECT pm_id, lead_user_id FROM projects WHERE id=?", (project_id,)
        ).fetchone()
    if not proj:
        return None
    if u["id"] in (proj["pm_id"], proj["lead_user_id"]):
        return u
    if role in ("leader", "pm"):
        return u
    return None


def _burndown_compute(project_id: int):
    """프로젝트의 task 기반 번다운 스냅샷 데이터 계산. 외부 라이브러리 0."""
    with db_session() as c:
        total = c.execute(
            "SELECT COUNT(*) FROM tasks WHERE project_id=?", (project_id,)
        ).fetchone()[0]
        done = c.execute(
            "SELECT COUNT(*) FROM tasks WHERE project_id=? AND status='완료'",
            (project_id,),
        ).fetchone()[0]
        rem_h = c.execute(
            """SELECT COALESCE(SUM(hours), 0) FROM tasks
               WHERE project_id=? AND status != '완료'""",
            (project_id,),
        ).fetchone()[0]
    return {"total_tasks": total, "completed_tasks": done,
            "remaining_hours": float(rem_h or 0)}


@app.get("/progress/{project_id}/gantt", response_class=HTMLResponse)
async def progress_gantt(req: Request, project_id: int):
    """간트 차트 — project_phases 의 planned_start/planned_end 를 CSS bar 로 렌더."""
    u = _progress_guard(req, project_id)
    if not u:
        return RedirectResponse("/progress", 303)
    with db_session() as c:
        proj = c.execute(
            "SELECT p.*, p.name AS project_name FROM projects p WHERE p.id=?",
            (project_id,),
        ).fetchone()
        if not proj:
            return RedirectResponse("/progress", 303)
        phases = [dict(r) for r in c.execute(
            """SELECT id, phase_code, phase_order, status, progress_pct,
                      planned_start, planned_end, actual_start, actual_end, note
               FROM project_phases WHERE project_id=? ORDER BY phase_order""",
            (project_id,),
        ).fetchall()]
        milestones = [dict(r) for r in c.execute(
            """SELECT id, name, target_date, completed_at, status
               FROM project_milestones WHERE project_id=?
               ORDER BY target_date ASC""",
            (project_id,),
        ).fetchall()]
    today_str = datetime.now().strftime("%Y-%m-%d")
    return ctx(req, "progress_gantt.html", user=u, active="progress",
               project=dict(proj), phases=phases, milestones=milestones,
               today_str=today_str,
               PHASE_CODE_TO_LABEL=PHASE_CODE_TO_LABEL)


def _linear_regression(xs, ys):
    """순수 Python 선형 회귀 (slope, intercept, r_squared). 외부 라이브러리 0."""
    n = len(xs)
    if n < 2:
        return 0.0, 0.0, 0.0
    sx = sum(xs); sy = sum(ys)
    mx = sx / n; my = sy / n
    num = 0.0; den = 0.0; sst = 0.0
    for i in range(n):
        dx = xs[i] - mx; dy = ys[i] - my
        num += dx * dy
        den += dx * dx
        sst += dy * dy
    if den == 0:
        return 0.0, my, 0.0
    slope = num / den
    intercept = my - slope * mx
    if sst == 0:
        return slope, intercept, 1.0
    ssr = 0.0
    for i in range(n):
        pred = slope * xs[i] + intercept
        ssr += (ys[i] - pred) ** 2
    r2 = max(0.0, 1.0 - ssr / sst)
    return slope, intercept, r2


def _burndown_forecast(snaps):
    """스냅샷 리스트 → (forecast_date_str, slope, r2, days_to_zero) 또는 None.
    snaps: [{snap_date, total_tasks, completed_tasks, ...}, ...] (날짜 오름차순)"""
    if not snaps or len(snaps) < 2:
        return None
    base = datetime.strptime(snaps[0]["snap_date"], "%Y-%m-%d")
    xs = []; ys = []
    for s in snaps:
        d = datetime.strptime(s["snap_date"], "%Y-%m-%d")
        xs.append((d - base).days)
        ys.append(float(s["total_tasks"] - s["completed_tasks"]))
    slope, intercept, r2 = _linear_regression(xs, ys)
    if slope >= 0:
        return {"slope": slope, "intercept": intercept, "r_squared": r2,
                "forecast_date": None, "days_to_zero": None,
                "base_date": snaps[0]["snap_date"]}
    x_zero = -intercept / slope
    fdate = base + timedelta(days=int(round(x_zero)))
    return {"slope": slope, "intercept": intercept, "r_squared": r2,
            "forecast_date": fdate.strftime("%Y-%m-%d"),
            "days_to_zero": x_zero,
            "base_date": snaps[0]["snap_date"]}


@app.get("/progress/{project_id}/burndown", response_class=HTMLResponse)
async def progress_burndown(req: Request, project_id: int):
    """번다운 — 일별 스냅샷 + 회귀 기반 예측 종료일. 외부 차트 0건 (SVG 직접)."""
    u = _progress_guard(req, project_id)
    if not u:
        return RedirectResponse("/progress", 303)
    with db_session() as c:
        proj = c.execute(
            "SELECT p.*, p.name AS project_name FROM projects p WHERE p.id=?",
            (project_id,),
        ).fetchone()
        if not proj:
            return RedirectResponse("/progress", 303)
        snaps = [dict(r) for r in c.execute(
            """SELECT snap_date, total_tasks, completed_tasks, remaining_hours
               FROM project_burndown_snapshots WHERE project_id=?
               ORDER BY snap_date ASC""",
            (project_id,),
        ).fetchall()]
        fc_row = c.execute(
            """SELECT computed_at, sample_n, slope, intercept, r_squared,
                      forecast_date, planned_end
               FROM project_forecasts WHERE project_id=?""",
            (project_id,),
        ).fetchone()
    today_pt = _burndown_compute(project_id)
    forecast = _burndown_forecast(snaps)
    today_str = datetime.now().strftime("%Y-%m-%d")
    return ctx(req, "progress_burndown.html", user=u, active="progress",
               project=dict(proj), snaps=snaps, today_pt=today_pt,
               forecast=forecast, today_str=today_str,
               saved_forecast=dict(fc_row) if fc_row else None)


@app.post("/progress/{project_id}/forecast")
async def progress_forecast(req: Request, project_id: int):
    """선형 회귀로 예측 종료일 산출 후 project_forecasts UPSERT.
    응답 JSON: {forecast_date, current_slope, r_squared, sample_n}."""
    u = _progress_guard(req, project_id)
    if not u:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    with db_session() as c:
        proj = c.execute(
            "SELECT id, end_date FROM projects WHERE id=?", (project_id,),
        ).fetchone()
        if not proj:
            return JSONResponse({"error": "not_found"}, status_code=404)
        snaps = [dict(r) for r in c.execute(
            """SELECT snap_date, total_tasks, completed_tasks
               FROM project_burndown_snapshots WHERE project_id=?
               ORDER BY snap_date ASC""",
            (project_id,),
        ).fetchall()]
    fc = _burndown_forecast(snaps)
    if not fc:
        return JSONResponse({"error": "insufficient_data",
                              "sample_n": len(snaps)}, status_code=400)
    with db_session() as c:
        c.execute(
            """INSERT INTO project_forecasts
                 (project_id, sample_n, slope, intercept, r_squared,
                  forecast_date, planned_end, computed_at)
               VALUES (?,?,?,?,?,?,?,datetime('now','localtime'))
               ON CONFLICT(project_id) DO UPDATE SET
                   sample_n=excluded.sample_n,
                   slope=excluded.slope,
                   intercept=excluded.intercept,
                   r_squared=excluded.r_squared,
                   forecast_date=excluded.forecast_date,
                   planned_end=excluded.planned_end,
                   computed_at=excluded.computed_at""",
            (project_id, len(snaps), fc["slope"], fc["intercept"],
             fc["r_squared"], fc["forecast_date"], proj["end_date"]),
        )
    return JSONResponse({
        "forecast_date": fc["forecast_date"],
        "current_slope": fc["slope"],
        "r_squared": fc["r_squared"],
        "sample_n": len(snaps),
        "planned_end": proj["end_date"],
    })


@app.get("/progress/{project_id}/milestones", response_class=HTMLResponse)
async def progress_milestones(req: Request, project_id: int):
    """마일스톤 페이지 — 프로젝트별 목록 + 달성률."""
    u = _progress_guard(req, project_id)
    if not u:
        return RedirectResponse("/progress", 303)
    with db_session() as c:
        proj = c.execute(
            "SELECT p.*, p.name AS project_name FROM projects p WHERE p.id=?",
            (project_id,),
        ).fetchone()
        if not proj:
            return RedirectResponse("/progress", 303)
        ms = [dict(r) for r in c.execute(
            """SELECT id, name, target_date, completed_at, status
               FROM project_milestones WHERE project_id=?
               ORDER BY target_date IS NULL, target_date ASC""",
            (project_id,),
        ).fetchall()]
    total = len(ms)
    done = sum(1 for m in ms if m["status"] == "DONE")
    pct = (done * 100.0 / total) if total else 0.0
    today_str = datetime.now().strftime("%Y-%m-%d")
    return ctx(req, "progress_milestones.html", user=u, active="progress",
               project=dict(proj), milestones=ms,
               total_ms=total, done_ms=done, pct_ms=pct,
               today_str=today_str)


@app.post("/progress/{project_id}/snapshot")
async def progress_snapshot(req: Request, project_id: int):
    """일별 스냅샷 트리거. 같은 날 중복 시 UPDATE (UNIQUE constraint)."""
    u = _progress_guard(req, project_id)
    if not u:
        return RedirectResponse("/progress", 303)
    pt = _burndown_compute(project_id)
    today = datetime.now().strftime("%Y-%m-%d")
    with db_session() as c:
        c.execute(
            """INSERT INTO project_burndown_snapshots
                 (project_id, snap_date, total_tasks, completed_tasks, remaining_hours)
               VALUES (?,?,?,?,?)
               ON CONFLICT(project_id, snap_date) DO UPDATE SET
                   total_tasks=excluded.total_tasks,
                   completed_tasks=excluded.completed_tasks,
                   remaining_hours=excluded.remaining_hours""",
            (project_id, today, pt["total_tasks"],
             pt["completed_tasks"], pt["remaining_hours"]),
        )
    return RedirectResponse(f"/progress/{project_id}/burndown", 303)


@app.get("/progress-dashboard", response_class=HTMLResponse)
async def progress_dashboard_company(req: Request):
    """전사 프로젝트 대시 — admin/ceo/executive 전용. /progress/{int} 충돌 회피용 하이픈 URL."""
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    role = u.get("role") if isinstance(u, dict) else u["role"]
    if role not in ("admin", "ceo", "executive"):
        return RedirectResponse("/progress", 303)
    with db_session() as c:
        rows = [dict(r) for r in c.execute(
            """SELECT p.id, p.name, p.mgmt_code, p.status, p.start_date, p.end_date,
                      (SELECT COUNT(*) FROM tasks t WHERE t.project_id=p.id) AS total_t,
                      (SELECT COUNT(*) FROM tasks t WHERE t.project_id=p.id
                          AND t.status='완료') AS done_t,
                      (SELECT COUNT(*) FROM project_milestones m
                          WHERE m.project_id=p.id AND m.status='DONE') AS done_ms,
                      (SELECT COUNT(*) FROM project_milestones m
                          WHERE m.project_id=p.id) AS total_ms
               FROM projects p
               WHERE p.status IN ('진행중','진행')
               ORDER BY (p.end_date IS NULL), p.end_date ASC LIMIT 50"""
        ).fetchall()]
    return ctx(req, "progress_dashboard.html", user=u, active="progress",
               projects=rows)


# =====================================================
# HAIST WORKS — QMS 강화 1차 (2026-04-26 갭서베이 Top10 #6)
# DB: qms_audit_log / corrective_actions / preventive_actions (idempotent)
#     + issues 5컬럼 ALTER ADD (sla_hours/detected_at/responded_at/recurrence_id/sla_breached)
# UI: qms_dashboard.html / qms_recurrence.html (외부 차트 라이브러리 0)
# 페르소나: P2 제조/품질팀 주2회 · P-CEO 분기 품질 KPI
# =====================================================
def _qms_guard(req: Request):
    """품질 가드 — admin/ceo/executive OR 품질팀(team name LIKE %품질%) OR can_use_quality=1."""
    u = get_user(req)
    if not u:
        return None
    role = u.get("role") if isinstance(u, dict) else u["role"]
    if role in ("admin", "ceo", "executive"):
        return u
    if u.get("can_use_quality"):
        return u
    # 팀명 LIKE '%품질%' (is_team("quality") 대용)
    tid = u.get("team_id")
    if tid:
        with db_session() as c:
            row = c.execute(
                "SELECT name FROM teams WHERE id=?", (tid,)
            ).fetchone()
        if row and "품질" in (row["name"] or ""):
            return u
    return None


def _qms_sla_status(issue: dict) -> dict:
    """SLA 현황 계산 — sla_hours 기반 elapsed/remaining/breached 계산. 외부 라이브러리 0."""
    sla_h = issue.get("sla_hours") or 24
    detected = issue.get("detected_at") or issue.get("occurred_at") or issue.get("created_at")
    if not detected:
        return {"sla_hours": sla_h, "elapsed_h": 0, "remaining_h": sla_h, "breached": False}
    try:
        det_dt = datetime.strptime(detected[:19], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        try:
            det_dt = datetime.strptime(detected[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return {"sla_hours": sla_h, "elapsed_h": 0, "remaining_h": sla_h, "breached": False}
    resolved = issue.get("resolved_at")
    if resolved:
        try:
            end_dt = datetime.strptime(resolved[:19], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            end_dt = datetime.now()
    else:
        end_dt = datetime.now()
    elapsed_h = (end_dt - det_dt).total_seconds() / 3600.0
    remaining_h = sla_h - elapsed_h
    return {"sla_hours": sla_h, "elapsed_h": round(elapsed_h, 1),
            "remaining_h": round(remaining_h, 1), "breached": remaining_h < 0 and not resolved}


@app.get("/qms", response_class=HTMLResponse)
async def qms_dashboard(req: Request):
    """QMS 품질 대시 — severity/SLA/재발 KPI 통합."""
    u = _qms_guard(req)
    if not u:
        return RedirectResponse("/issues", 303)
    with db_session() as c:
        total = c.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
        open_cnt = c.execute(
            "SELECT COUNT(*) FROM issues WHERE status NOT IN ('해결','종결')"
        ).fetchone()[0]
        critical = c.execute(
            "SELECT COUNT(*) FROM issues WHERE severity IN ('치명','심각','CRITICAL','HIGH') "
            "AND status NOT IN ('해결','종결')"
        ).fetchone()[0]
        breached = c.execute(
            "SELECT COUNT(*) FROM issues WHERE COALESCE(sla_breached,0)=1 "
            "AND status NOT IN ('해결','종결')"
        ).fetchone()[0]
        recur = c.execute(
            "SELECT COUNT(DISTINCT recurrence_id) FROM issues WHERE recurrence_id IS NOT NULL AND recurrence_id != ''"
        ).fetchone()[0]
        ca_open = c.execute(
            "SELECT COUNT(*) FROM corrective_actions WHERE status IN ('OPEN','IN_PROGRESS')"
        ).fetchone()[0]
        # SLA 위반 위험 목록 (open + 잔여 시간 < 4h or breached)
        rows = [dict(r) for r in c.execute(
            """SELECT id, issue_no, title, severity, status, sla_hours,
                      occurred_at, detected_at, resolved_at, owner_team_id, recurrence_id
               FROM issues WHERE status NOT IN ('해결','종결')
               ORDER BY (severity IN ('치명','심각','CRITICAL','HIGH')) DESC,
                        occurred_at ASC LIMIT 50"""
        ).fetchall()]
        for r in rows:
            r["sla"] = _qms_sla_status(r)
    kpi = {"total": total, "open": open_cnt, "critical": critical,
           "breached": breached, "recurrence_groups": recur, "ca_open": ca_open}
    return ctx(req, "qms_dashboard.html", user=u, active="qms",
               kpi=kpi, items=rows)


@app.get("/qms/issues/{iid}/sla", response_class=HTMLResponse)
async def qms_issue_sla(req: Request, iid: int):
    """단일 이슈 SLA 현황 — JSON 반환."""
    u = _qms_guard(req)
    if not u:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    with db_session() as c:
        row = c.execute("SELECT * FROM issues WHERE id=?", (iid,)).fetchone()
    if not row:
        return JSONResponse({"error": "notfound"}, status_code=404)
    return JSONResponse(_qms_sla_status(dict(row)))


@app.post("/qms/issues/{iid}/corrective")
async def qms_corrective_add(req: Request, iid: int,
                              action: str = Form(...),
                              responsible: str = Form(""),
                              due_date: str = Form("")):
    """시정조치 추가 + 감사로그 기록."""
    u = _qms_guard(req)
    if not u:
        return RedirectResponse(f"/issues/{iid}", 303)
    resp_id = int(responsible) if responsible and responsible.isdigit() else None
    with db_session() as c:
        cur = c.execute(
            """INSERT INTO corrective_actions
                 (issue_id, action, responsible, due_date, created_by)
               VALUES (?,?,?,?,?)""",
            (iid, action.strip(), resp_id, due_date or None, u["id"]),
        )
        ca_id = cur.lastrowid
        c.execute(
            """INSERT INTO qms_audit_log (issue_id, action, actor, note)
               VALUES (?, 'corrective_added', ?, ?)""",
            (iid, u["id"], f"CA#{ca_id}: {action[:80]}"),
        )
    # 알림시스템 통합 (사이클 2026-04-26) — 시정조치 담당자에게 QMS 알림 (SLA due_date 표기)
    if resp_id:
        notify_user(
            resp_id, "QMS",
            f"⚙️ 시정조치 배정 — Issue #{iid} (CA#{ca_id})",
            body=f"기한 {due_date or '미지정'} / {action[:80]}",
            link=f"/issues/{iid}",
        )
    return RedirectResponse(f"/issues/{iid}", 303)


@app.post("/qms/issues/{iid}/preventive")
async def qms_preventive_add(req: Request, iid: int,
                              corrective_id: str = Form(...),
                              action: str = Form(...)):
    """예방조치 추가 (특정 corrective_action 에 종속) + 감사로그."""
    u = _qms_guard(req)
    if not u:
        return RedirectResponse(f"/issues/{iid}", 303)
    if not corrective_id.isdigit():
        return RedirectResponse(f"/issues/{iid}", 303)
    ca_id = int(corrective_id)
    with db_session() as c:
        cur = c.execute(
            """INSERT INTO preventive_actions
                 (corrective_id, action, created_by)
               VALUES (?,?,?)""",
            (ca_id, action.strip(), u["id"]),
        )
        pa_id = cur.lastrowid
        c.execute(
            """INSERT INTO qms_audit_log (issue_id, action, actor, note)
               VALUES (?, 'preventive_added', ?, ?)""",
            (iid, u["id"], f"PA#{pa_id} (CA#{ca_id}): {action[:80]}"),
        )
    return RedirectResponse(f"/issues/{iid}", 303)


@app.get("/qms/recurrence", response_class=HTMLResponse)
async def qms_recurrence(req: Request):
    """재발 추적 — 같은 root_cause/recurrence_id 그룹화 트리."""
    u = _qms_guard(req)
    if not u:
        return RedirectResponse("/issues", 303)
    with db_session() as c:
        # recurrence_id 명시 그룹
        groups_by_rid = [dict(r) for r in c.execute(
            """SELECT recurrence_id AS gid, COUNT(*) AS cnt,
                      MIN(occurred_at) AS first_at, MAX(occurred_at) AS last_at
               FROM issues
               WHERE recurrence_id IS NOT NULL AND recurrence_id != ''
               GROUP BY recurrence_id
               HAVING cnt >= 2
               ORDER BY cnt DESC, last_at DESC LIMIT 50"""
        ).fetchall()]
        # root_cause 텍스트 그룹 (recurrence_id 없을 때 fallback)
        groups_by_rc = [dict(r) for r in c.execute(
            """SELECT SUBSTR(root_cause,1,60) AS gid, COUNT(*) AS cnt,
                      MIN(occurred_at) AS first_at, MAX(occurred_at) AS last_at
               FROM issues
               WHERE root_cause IS NOT NULL AND TRIM(root_cause) != ''
                     AND (recurrence_id IS NULL OR recurrence_id = '')
               GROUP BY SUBSTR(root_cause,1,60)
               HAVING cnt >= 2
               ORDER BY cnt DESC, last_at DESC LIMIT 30"""
        ).fetchall()]
        # 각 그룹의 이슈 리스트 (recurrence_id 기준)
        details = {}
        for g in groups_by_rid:
            details[g["gid"]] = [dict(r) for r in c.execute(
                """SELECT id, issue_no, title, severity, status, occurred_at
                   FROM issues WHERE recurrence_id = ?
                   ORDER BY occurred_at DESC LIMIT 20""",
                (g["gid"],),
            ).fetchall()]
    return ctx(req, "qms_recurrence.html", user=u, active="qms",
               groups_rid=groups_by_rid, groups_rc=groups_by_rc, details=details)


# =====================================================
# QMS 2차 Pareto + CAPA 심화 (2026-04-26)
# Pareto: root_cause 빈도 + 누적 % (80/20 법칙)
# CAPA 라이프사이클: DRAFT → APPROVED → IN_PROGRESS → COMPLETED → VERIFIED
# 외부 차트 라이브러리 0건 (CSS bar + SVG cumulative line)
# =====================================================
def _qms_capa_guard(req: Request):
    """승인/검증 권한 — admin/ceo/executive OR 품질팀장(role 'leader')."""
    u = _qms_guard(req)
    if not u:
        return None
    role = u.get("role") if isinstance(u, dict) else u["role"]
    if role in ("admin", "ceo", "executive", "leader"):
        return u
    return None


def _capa_kpi(c) -> dict:
    """CAPA KPI 계산 — 평균 closure time / 검증 비율 / 부서별 분포 (외부 라이브러리 0)."""
    # 평균 closure time: created_at(DRAFT 진입) → completed_at (단위: 일)
    rows = c.execute(
        """SELECT created_at, completed_at FROM corrective_actions
           WHERE completed_at IS NOT NULL AND created_at IS NOT NULL"""
    ).fetchall()
    days = []
    for r in rows:
        try:
            t0 = datetime.strptime(r["created_at"][:19], "%Y-%m-%d %H:%M:%S")
            t1 = datetime.strptime(r["completed_at"][:19], "%Y-%m-%d %H:%M:%S")
            days.append((t1 - t0).total_seconds() / 86400.0)
        except (ValueError, TypeError):
            continue
    avg_closure = round(sum(days) / len(days), 1) if days else 0
    # 검증 비율: VERIFIED / COMPLETED
    completed = c.execute(
        "SELECT COUNT(*) FROM corrective_actions "
        "WHERE lifecycle_status IN ('COMPLETED','VERIFIED')"
    ).fetchone()[0]
    verified = c.execute(
        "SELECT COUNT(*) FROM corrective_actions WHERE lifecycle_status='VERIFIED'"
    ).fetchone()[0]
    verify_rate = round(100.0 * verified / completed, 1) if completed else 0
    # 부서별 분포 (issue.owner_team_id → teams.name 조인)
    dept_rows = [dict(r) for r in c.execute(
        """SELECT COALESCE(t.name,'(미지정)') AS dept, COUNT(ca.id) AS cnt
           FROM corrective_actions ca
           LEFT JOIN issues i ON i.id = ca.issue_id
           LEFT JOIN teams t ON t.id = i.owner_team_id
           GROUP BY t.name
           ORDER BY cnt DESC LIMIT 10"""
    ).fetchall()]
    return {"avg_closure_days": avg_closure, "verify_rate": verify_rate,
            "completed": completed, "verified": verified, "by_dept": dept_rows,
            "sample_size": len(days)}


@app.get("/qms/pareto", response_class=HTMLResponse)
async def qms_pareto(req: Request):
    """Pareto 차트 — root_cause 빈도 + 누적 % (80/20 법칙)."""
    u = _qms_guard(req)
    if not u:
        return RedirectResponse("/issues", 303)
    with db_session() as c:
        rows = [dict(r) for r in c.execute(
            """SELECT SUBSTR(root_cause,1,40) AS cause, COUNT(*) AS cnt
               FROM issues
               WHERE root_cause IS NOT NULL AND TRIM(root_cause) != ''
               GROUP BY SUBSTR(root_cause,1,40)
               ORDER BY cnt DESC LIMIT 20"""
        ).fetchall()]
    total = sum(r["cnt"] for r in rows) or 1
    cum = 0
    p80_idx = -1
    for i, r in enumerate(rows):
        cum += r["cnt"]
        r["pct"] = round(100.0 * r["cnt"] / total, 1)
        r["cum_pct"] = round(100.0 * cum / total, 1)
        if p80_idx < 0 and r["cum_pct"] >= 80.0:
            p80_idx = i
    max_cnt = rows[0]["cnt"] if rows else 1
    summary = {
        "total_issues": total, "distinct_causes": len(rows),
        "p80_cutoff_idx": p80_idx + 1 if p80_idx >= 0 else 0,
        "p80_pct_of_causes": round(100.0 * (p80_idx + 1) / len(rows), 1) if rows and p80_idx >= 0 else 0,
    }
    return ctx(req, "qms_pareto.html", user=u, active="qms",
               rows=rows, summary=summary, max_cnt=max_cnt)


@app.get("/qms/capa", response_class=HTMLResponse)
async def qms_capa_dashboard(req: Request):
    """CAPA 라이프사이클 관리 — DRAFT/APPROVED/IN_PROGRESS/COMPLETED/VERIFIED 분포 + KPI."""
    u = _qms_guard(req)
    if not u:
        return RedirectResponse("/issues", 303)
    with db_session() as c:
        # 라이프사이클 카운트 (corrective)
        ca_buckets = {"DRAFT": 0, "APPROVED": 0, "IN_PROGRESS": 0, "COMPLETED": 0, "VERIFIED": 0}
        for r in c.execute(
            "SELECT COALESCE(lifecycle_status,'DRAFT') AS s, COUNT(*) AS n "
            "FROM corrective_actions GROUP BY lifecycle_status"
        ).fetchall():
            ca_buckets[r["s"] if r["s"] in ca_buckets else "DRAFT"] = r["n"]
        # 라이프사이클 카운트 (preventive)
        pa_buckets = {"DRAFT": 0, "APPROVED": 0, "IN_PROGRESS": 0, "COMPLETED": 0, "VERIFIED": 0}
        for r in c.execute(
            "SELECT COALESCE(lifecycle_status,'DRAFT') AS s, COUNT(*) AS n "
            "FROM preventive_actions GROUP BY lifecycle_status"
        ).fetchall():
            pa_buckets[r["s"] if r["s"] in pa_buckets else "DRAFT"] = r["n"]
        # CAPA 목록 (최근 30개, 진행중 우선)
        items = [dict(r) for r in c.execute(
            """SELECT ca.id, ca.action, ca.due_date, ca.created_at,
                      ca.completed_at, ca.verified_at,
                      COALESCE(ca.lifecycle_status,'DRAFT') AS lifecycle_status,
                      i.id AS issue_id, i.issue_no, i.title AS issue_title
               FROM corrective_actions ca
               LEFT JOIN issues i ON i.id = ca.issue_id
               ORDER BY (ca.lifecycle_status='VERIFIED'),
                        (ca.lifecycle_status='COMPLETED'),
                        ca.created_at DESC
               LIMIT 30"""
        ).fetchall()]
        kpi = _capa_kpi(c)
    return ctx(req, "qms_capa.html", user=u, active="qms",
               ca_buckets=ca_buckets, pa_buckets=pa_buckets,
               items=items, kpi=kpi)


def _capa_transition(req: Request, table: str, cid: int, target: str,
                      need_admin: bool, note: str = "") -> bool:
    """CAPA 라이프사이클 전이 헬퍼 — 가드/UPDATE/감사로그 통합. table='corrective_actions' or 'preventive_actions'."""
    u = _qms_capa_guard(req) if need_admin else _qms_guard(req)
    if not u:
        return False
    if table not in ("corrective_actions", "preventive_actions"):
        return False
    col_map = {
        "APPROVED":    ("approved_by", "approved_at"),
        "COMPLETED":   (None, "completed_at"),
        "VERIFIED":    ("verified_by", "verified_at"),
        "IN_PROGRESS": (None, None),
    }
    if target not in col_map:
        return False
    actor_col, ts_col = col_map[target]
    sets = ["lifecycle_status = ?"]
    vals = [target]
    if actor_col:
        sets.append(f"{actor_col} = ?")
        vals.append(u["id"])
    if ts_col:
        sets.append(f"{ts_col} = datetime('now','localtime')")
    if target == "VERIFIED" and note:
        sets.append("effectiveness_note = ?")
        vals.append(note.strip())
    vals.append(cid)
    with db_session() as c:
        try:
            c.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id=?", vals)
            # 감사로그 (issue_id 조회)
            if table == "corrective_actions":
                row = c.execute(
                    "SELECT issue_id FROM corrective_actions WHERE id=?", (cid,)
                ).fetchone()
            else:
                row = c.execute(
                    "SELECT ca.issue_id FROM preventive_actions pa "
                    "JOIN corrective_actions ca ON ca.id = pa.corrective_id "
                    "WHERE pa.id=?", (cid,)
                ).fetchone()
            if row:
                tag = "ca" if table == "corrective_actions" else "pa"
                c.execute(
                    """INSERT INTO qms_audit_log (issue_id, action, actor, note)
                       VALUES (?, ?, ?, ?)""",
                    (row["issue_id"], f"{tag}_{target.lower()}", u["id"],
                     f"#{cid} → {target}" + (f" · {note[:60]}" if note else "")),
                )
        except Exception:
            return False
    return True


@app.post("/qms/corrective/{cid}/approve")
async def qms_corrective_approve(req: Request, cid: int):
    """시정조치 승인 — DRAFT → APPROVED (admin/ceo/executive/leader)."""
    ok = _capa_transition(req, "corrective_actions", cid, "APPROVED", need_admin=True)
    return RedirectResponse("/qms/capa" if ok else "/qms", 303)


@app.post("/qms/corrective/{cid}/start")
async def qms_corrective_start(req: Request, cid: int):
    """시정조치 진행 — APPROVED → IN_PROGRESS (담당자)."""
    ok = _capa_transition(req, "corrective_actions", cid, "IN_PROGRESS", need_admin=False)
    return RedirectResponse("/qms/capa" if ok else "/qms", 303)


@app.post("/qms/corrective/{cid}/complete")
async def qms_corrective_complete(req: Request, cid: int):
    """시정조치 완료 — IN_PROGRESS → COMPLETED (담당자)."""
    ok = _capa_transition(req, "corrective_actions", cid, "COMPLETED", need_admin=False)
    return RedirectResponse("/qms/capa" if ok else "/qms", 303)


@app.post("/qms/corrective/{cid}/verify")
async def qms_corrective_verify(req: Request, cid: int,
                                  effectiveness_note: str = Form("")):
    """시정조치 효과 검증 — COMPLETED → VERIFIED (admin/leader)."""
    ok = _capa_transition(req, "corrective_actions", cid, "VERIFIED",
                          need_admin=True, note=effectiveness_note)
    return RedirectResponse("/qms/capa" if ok else "/qms", 303)


@app.post("/qms/preventive/{pid}/approve")
async def qms_preventive_approve(req: Request, pid: int):
    """예방조치 승인 — DRAFT → APPROVED."""
    ok = _capa_transition(req, "preventive_actions", pid, "APPROVED", need_admin=True)
    return RedirectResponse("/qms/capa" if ok else "/qms", 303)


@app.post("/qms/preventive/{pid}/complete")
async def qms_preventive_complete(req: Request, pid: int):
    """예방조치 완료 — IN_PROGRESS → COMPLETED."""
    ok = _capa_transition(req, "preventive_actions", pid, "COMPLETED", need_admin=False)
    return RedirectResponse("/qms/capa" if ok else "/qms", 303)


@app.post("/qms/preventive/{pid}/verify")
async def qms_preventive_verify(req: Request, pid: int,
                                  effectiveness_note: str = Form("")):
    """예방조치 효과 검증 — COMPLETED → VERIFIED."""
    ok = _capa_transition(req, "preventive_actions", pid, "VERIFIED",
                          need_admin=True, note=effectiveness_note)
    return RedirectResponse("/qms/capa" if ok else "/qms", 303)


# =====================================================
# 환율·단가 강화 1차 (2026-04-26 Top10 #9 P4 구매팀 월 1회)
# 외부 환율 API 미사용 (수동 입력 + CSV 업로드만)
# =====================================================
def _rates_guard(req: Request):
    """환율·단가 가드 — can_use_logistics 위임 (구매팀 + admin/ceo/executive)."""
    u = get_user(req)
    if not u:
        return None
    if not can_use_logistics(u):
        return None
    return u


@app.get("/rates/dashboard", response_class=HTMLResponse)
async def rates_dashboard_page(request: Request):
    u = _rates_guard(request)
    if not u:
        return RedirectResponse("/login", 303)
    items = exchange_rates_list(limit=60, currency="")
    latest = exchange_rates_latest()
    alerts = rate_alerts_list(active_only=True)
    # 트렌드: 통화별 최근 14일 (대시보드 KPI)
    with db_session() as c:
        trend_rows = [dict(r) for r in c.execute(
            """SELECT from_currency, rate_date, rate
               FROM exchange_rates
               WHERE to_currency='KRW' AND rate_date >= date('now','-30 days')
               ORDER BY rate_date DESC, from_currency"""
        ).fetchall()]
    return ctx(request, "rates_dashboard.html", user=u, items=items,
               latest=latest, alerts=alerts, trend=trend_rows,
               CURRENCIES=CURRENCIES, active="rates")


@app.post("/rates/upload")
async def rates_csv_upload(request: Request, csv_text: str = Form(...)):
    """CSV 일괄 업로드 — 외부 API 미호출. 헤더 필수: rate_date,from_currency(또는 from),to_currency(또는 to),rate.
    S2-1 헤더 가드: 첫 비주석 행을 헤더로 검증, BOM 제거, 잘못된 형식은 400 반환."""
    u = _rates_guard(request)
    if not u:
        return RedirectResponse("/login", 303)
    raw = csv_text or ""
    if raw.startswith("﻿"):  # S2-1: UTF-8 BOM 제거
        raw = raw.lstrip("﻿")
    lines = [ln.strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("#")]
    if not lines:
        return JSONResponse({"error": "CSV 비어있음"}, 400)
    header_cols = [c.strip().lower().lstrip("﻿") for c in lines[0].split(",")]
    HEADER_ALIAS = {"from": "from_currency", "to": "to_currency",
                    "date": "rate_date", "currency": "from_currency"}
    norm_header = [HEADER_ALIAS.get(h, h) for h in header_cols]
    REQUIRED = {"rate_date", "from_currency", "rate"}
    missing = REQUIRED - set(norm_header)
    if missing:
        return JSONResponse(
            {"error": f"CSV 헤더 누락: {sorted(missing)} · 필수=rate_date,from_currency(또는 from),rate"},
            400,
        )
    idx = {k: norm_header.index(k) for k in norm_header}
    rows = []
    for ln in lines[1:]:
        cols = [c.strip() for c in ln.split(",")]
        if not any(cols):
            continue  # S2-1: 빈 행 정리
        try:
            rd = cols[idx["rate_date"]] if idx.get("rate_date", -1) >= 0 else ""
            fc = cols[idx["from_currency"]] if idx.get("from_currency", -1) >= 0 else ""
            rt = cols[idx["rate"]] if idx.get("rate", -1) >= 0 else ""
        except IndexError:
            continue
        if not (rd and fc and rt):
            continue  # S2-1: 필수 빈 값 정리
        rows.append({
            "rate_date": rd,
            "from_currency": fc,
            "to_currency": (cols[idx["to_currency"]] if idx.get("to_currency", -1) >= 0
                            and idx["to_currency"] < len(cols) and cols[idx["to_currency"]]
                            else "KRW"),
            "rate": rt,
            "source": (cols[idx["source"]] if idx.get("source", -1) >= 0
                       and idx["source"] < len(cols) else "CSV"),
            "note": (cols[idx["note"]] if idx.get("note", -1) >= 0
                     and idx["note"] < len(cols) else ""),
        })
    res = exchange_rates_csv_upload(rows, user_id=u["id"])
    # S3-1 옵션 A: 업로드 후 자동 알림 발동 검사 (통화별 평균 rate 사용)
    fired_total = 0
    by_cur: dict = {}
    for r in rows:
        try:
            by_cur.setdefault(r["from_currency"].upper(), []).append(float(r["rate"]))
        except Exception:
            pass
    for cur, vals in by_cur.items():
        if vals:
            fired_total += check_rate_alerts(cur, vals[-1])  # 최신 행 기준
    msg = f"OK={res['ok']}/NG={res['ng']}/FIRED={fired_total}"
    return RedirectResponse(f"/rates/dashboard?upload={msg}", 303)


@app.get("/rates/cost-sim/{part_id}", response_class=HTMLResponse)
async def rates_cost_sim_page(request: Request, part_id: int):
    u = _rates_guard(request)
    if not u:
        return RedirectResponse("/login", 303)
    part = _logi.parts_get(part_id)
    if not part:
        return RedirectResponse("/parts", 303)
    sims = cost_simulations_list(part_id, limit=20)
    latest = exchange_rates_latest()
    active = part_active_price(part_id) or {}
    return ctx(request, "rates_cost_sim.html", user=u,
               part=dict(part), sims=sims, latest=latest,
               active_price=active, CURRENCIES=CURRENCIES, active="rates")


@app.post("/rates/cost-sim")
async def rates_cost_sim_submit(
    request: Request,
    part_id: str = Form(...),
    base_currency: str = Form("USD"),
    target_currency: str = Form("KRW"),
    exchange_rate: str = Form(...),
    unit_price_base: str = Form(...),
    margin_pct: str = Form("0"),
    note: str = Form(""),
):
    u = _rates_guard(request)
    if not u:
        return RedirectResponse("/login", 303)
    # OPS-V3 [정적점검 결함]: 입력 검증 누락 → ValueError/0음수 차단
    try:
        pid = int(part_id)
        base = float(unit_price_base)
        rate = float(exchange_rate)
        margin = float(margin_pct or 0)
    except (ValueError, TypeError):
        return RedirectResponse("/rates?error=입력값+형식+오류", 303)
    if pid <= 0 or base <= 0 or rate <= 0:
        return RedirectResponse(f"/rates/cost-sim/{pid}?error=part_id/단가/환율은+양수여야+합니다", 303)
    if margin < -100:
        return RedirectResponse(f"/rates/cost-sim/{pid}?error=마진율은+-100%+이상이어야+합니다", 303)
    if base_currency == target_currency and abs(rate - 1.0) > 1e-9:
        # 같은 통화인데 환율 != 1.0 → 사용자 실수 가능 (경고만, 계속 진행)
        pass
    target = base * rate * (1.0 + margin / 100.0)
    try:
        cost_simulation_create({
            "part_id": pid,
            "base_currency": base_currency,
            "target_currency": target_currency,
            "exchange_rate": rate,
            "unit_price_base": base,
            "unit_price_target": target,
            "margin_pct": margin,
            "note": note,
        }, user_id=u["id"])
    except Exception as e:
        return RedirectResponse(f"/rates/cost-sim/{pid}?error={e}", 303)
    return RedirectResponse(f"/rates/cost-sim/{pid}?saved=1", 303)


@app.get("/rates/price-history/{part_id}", response_class=HTMLResponse)
async def rates_price_history_page(request: Request, part_id: int):
    u = _rates_guard(request)
    if not u:
        return RedirectResponse("/login", 303)
    part = _logi.parts_get(part_id)
    if not part:
        return RedirectResponse("/parts", 303)
    history = price_change_history_list(part_id, limit=80)
    return ctx(request, "rates_history.html", user=u,
               part=dict(part), history=history, active="rates")


@app.get("/rates/alerts", response_class=HTMLResponse)
async def rates_alerts_page(request: Request):
    u = _rates_guard(request)
    if not u:
        return RedirectResponse("/login", 303)
    alerts = rate_alerts_list(active_only=False)
    latest = exchange_rates_latest()
    return ctx(request, "rates_alerts.html", user=u, alerts=alerts,
               latest=latest, CURRENCIES=CURRENCIES, active="rates")


@app.post("/rates/alerts")
async def rates_alerts_submit(
    request: Request,
    target_currency: str = Form(...),
    threshold: str = Form(...),
    direction: str = Form("above"),
):
    u = _rates_guard(request)
    if not u:
        return RedirectResponse("/login", 303)
    try:
        rate_alert_create(target_currency, float(threshold), direction, u["id"])
    except Exception as e:
        return RedirectResponse(f"/rates/alerts?error={e}", 303)
    # 알림시스템 통합 (사이클 2026-04-26) — 등록자에게 RATE 알림
    notify_user(
        u["id"], "RATE",
        f"💱 환율 알림 등록 — {target_currency}",
        body=f"임계 {threshold} ({direction})",
        link="/rates/alerts",
    )
    return RedirectResponse("/rates/alerts?saved=1", 303)


# =====================================================
# 사이클 51 S2-4차 (2026-04-27) — 안전재고 / 재발주점 / 발주 추천 / 알림 자동
# 라우트 +4: GET /stock/safety · POST /stock/safety/{part_id}
#           GET /stock/reorder-recommendations · POST /stock/alerts/check
# 권한: _s2_guard (구매팀 또는 admin/ceo). 알림 트리거는 admin/ceo 한정.
# =====================================================
@app.get("/stock/safety", response_class=HTMLResponse)
async def stock_safety_page(req: Request, q: str = ""):
    """안전재고 설정 페이지 — parts 별 safety_stock / reorder_point / reorder_qty."""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    from .database import parts_safety_settings_list
    items = parts_safety_settings_list(q=q)
    return ctx(req, "stock_safety.html", user=u, active="stock",
               items=items, q=q)


@app.post("/stock/safety/{part_id}")
async def stock_safety_save(req: Request, part_id: int):
    """안전재고 등록/수정 — safety_stock / reorder_point / reorder_qty 일괄 갱신."""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    form = await req.form()
    from .database import parts_safety_update
    ok = parts_safety_update(
        part_id,
        safety_stock=form.get("safety_stock") or 0,
        reorder_point=form.get("reorder_point") or 0,
        reorder_qty=form.get("reorder_qty") or 0,
    )
    suffix = "saved=1" if ok else "error=1"
    q = form.get("q") or ""
    qs = f"?q={q}&{suffix}" if q else f"?{suffix}"
    return RedirectResponse(f"/stock/safety{qs}", 303)


@app.get("/stock/reorder-recommendations", response_class=HTMLResponse)
async def stock_reorder_page(req: Request, limit: int = 200):
    """발주 추천 — 재발주점 미달 부품 + 권장 발주량 + 우선순위(HIGH/MID/LOW)."""
    u = _s2_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    # OPS-V4 [정적점검]: limit 상한 가드 (메모리 폭주 방지)
    limit = max(1, min(int(limit or 200), 1000))
    from .database import recommend_reorders
    items = recommend_reorders(limit=limit)
    high = sum(1 for r in items if r["priority"] == "HIGH")
    mid = sum(1 for r in items if r["priority"] == "MID")
    low = sum(1 for r in items if r["priority"] == "LOW")
    return ctx(req, "stock_reorder.html", user=u, active="stock",
               items=items, high_cnt=high, mid_cnt=mid, low_cnt=low)


@app.post("/stock/alerts/check")
async def stock_alerts_check(req: Request):
    """알림 트리거 — 관리자 한정. check_stock_alerts() 실행 후 결과 리턴."""
    u = _s2_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    if u.get("role") not in ("admin", "ceo"):
        return JSONResponse({"error": "관리자 전용"}, 403)
    from .database import check_stock_alerts
    out = check_stock_alerts()
    return JSONResponse({
        "ok": True,
        "checked": out.get("checked", 0),
        "alerts_sent": out.get("alerts_sent", 0),
        "low_count": len(out.get("low_parts", [])),
    })


# =====================================================
# 사이클 54 환율·단가 1차 (2026-04-27)
# 외부 API 0건. 수동 입력 + 이력 보존 + 단가 자동 적용 흐름.
# 권한: admin / finance(team_id=3 관리팀) / ceo (+ logistics 권한자)
# =====================================================
def _fx_guard(user) -> bool:
    """환율 관리 권한 — admin/ceo/executive + 관리팀(finance) + logistics 권한자"""
    if not user:
        return False
    role = user.get("role") if isinstance(user, dict) else user["role"]
    if role in ("admin", "ceo", "executive"):
        return True
    team_id = user.get("team_id") if isinstance(user, dict) else user["team_id"]
    if team_id == 3:  # 관리팀 = finance
        return True
    return can_use_logistics(user)


@app.get("/fx/rates", response_class=HTMLResponse)
async def fx_rates_page(request: Request, currency: str = ""):
    """
    환율 목록 + 입력 폼 (사이클 54 1차).

    외부 도메인 코드 호환용 영문 표준 경로 환율 관리 endpoint.
    사내 사용자는 기존 /rates 사용 권장 (사이드바 링크).
    본 endpoint는 외부 시스템·API 통합용으로 별도 운영.
    사이클 55 (2026-04-27) S2-1 A안 적용.
    """
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _fx_guard(u):
        return RedirectResponse("/home", 303)
    items = exchange_rates_list(limit=200, currency=currency)
    latest = exchange_rates_latest()
    return ctx(request, "fx_rates.html", user=u, items=items, latest=latest,
               currency=currency, CURRENCIES=CURRENCIES, active="fx_rates")


@app.post("/fx/rates")
async def fx_rates_create(
    request: Request,
    rate_date: str = Form(...),
    from_currency: str = Form(...),
    to_currency: str = Form("KRW"),
    rate: str = Form(...),
    source: str = Form("수동"),
    note: str = Form(""),
):
    """
    환율 신규 등록 — 같은 날짜+통화쌍 중복 시 UPSERT (exchange_rate_create 내부 처리).

    외부 도메인 코드 호환용 영문 표준 경로 환율 등록 endpoint.
    사내 사용자는 기존 /rates 사용 권장 (사이드바 링크).
    본 endpoint는 외부 시스템·API 통합용으로 별도 운영.
    사이클 55 (2026-04-27) S2-1 A안 적용.
    """
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not _fx_guard(u):
        return RedirectResponse("/home", 303)
    try:
        exchange_rate_create({
            "rate_date": rate_date,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": float(rate),
            "source": source,
            "note": note,
        }, user_id=u["id"])
    except Exception as e:
        return RedirectResponse(f"/fx/rates?error={e}", 303)
    return RedirectResponse("/fx/rates?success=1", 303)


@app.get("/parts/{part_id}/prices", response_class=HTMLResponse)
async def part_prices_page(request: Request, part_id: int):
    """부품 단가 이력 + 입력 폼 (사이클 54 1차)."""
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not (_fx_guard(u) or can_use_sales(u)):
        return RedirectResponse("/home", 303)
    part = _logi.parts_get(part_id)
    if not part:
        return RedirectResponse("/parts", 303)
    prices = part_prices_list(part_id)
    active = part_active_price(part_id)
    latest_cost = get_latest_part_price(part_id, price_type="cost")
    with db_session() as c:
        suppliers = [dict(r) for r in c.execute(
            "SELECT id, name FROM suppliers WHERE is_active=1 ORDER BY name"
        ).fetchall()]
    return ctx(request, "part_prices.html", user=u,
               part=dict(part), prices=prices, active_price=active,
               latest_cost=latest_cost, suppliers=suppliers,
               CURRENCIES=CURRENCIES, PRICE_TYPES=PRICE_TYPES,
               active="parts")


@app.post("/parts/{part_id}/prices")
async def part_prices_create(
    request: Request, part_id: int,
    supplier_id: str = Form(""),
    price_type: str = Form("견적"),
    unit_price: str = Form(...),
    currency: str = Form("KRW"),
    effective_from: str = Form(...),
    effective_to: str = Form(""),
    negotiated_at: str = Form(""),
    min_qty: str = Form("0"),
    max_qty: str = Form(""),
    note: str = Form(""),
):
    """
    부품 단가 신규 등록 (사이클 54 1차) — 이력 보존 (UPDATE 아닌 INSERT).
    사이클 55 S4-1 보강: negotiated_at / min_qty / max_qty + price_change_log 자동 INSERT.
    """
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not (_fx_guard(u) or can_use_sales(u)):
        return RedirectResponse("/home", 303)
    sid = int(supplier_id) if supplier_id and supplier_id.isdigit() else None
    new_price = float(unit_price)
    # S4-1: 직전 활성 단가 조회 (애플리케이션 레벨 훅)
    prev = part_active_price(part_id, supplier_id=sid or 0) or {}
    old_price = prev.get("unit_price")
    try:
        part_price_create({
            "part_id": part_id,
            "supplier_id": sid,
            "price_type": price_type,
            "unit_price": new_price,
            "currency": currency,
            "effective_from": effective_from,
            "effective_to": effective_to or None,
            "negotiated_at": negotiated_at or None,
            "min_qty": float(min_qty or 0),
            "max_qty": float(max_qty) if max_qty else None,
            "note": note,
        }, user_id=u["id"])
        # S4-1: price_change_history 자동 INSERT (변동률 자동 계산)
        try:
            price_change_log(part_id, sid, old_price, new_price,
                             effective_from, u["id"], note=note or "")
        except Exception:
            pass  # 본 등록은 성공했으므로 훅 실패는 흡수
    except Exception as e:
        return RedirectResponse(f"/parts/{part_id}/prices?error={e}", 303)
    return RedirectResponse(f"/parts/{part_id}/prices?success=1", 303)


# =====================================================
# 사이클 75 — FTA 원산지증명서 (C/O) 발급 모듈 (2026-04-27)
# 04 시뮬 MISSING #1: 안지연 본업. KAFTA/KEUFTA/RCEP 5종 처리.
# 외부 PDF 라이브러리 0건 (HTML 인쇄 view + window.print() 사이클 63 패턴).
# v2 본체 미접촉 / 핫패치 130 보존 / SQL 파라미터 바인딩.
# =====================================================
from .database import (create_fta_certificate, get_fta_certificates,
                       get_fta_certificate)

FTA_TYPES = [
    ("KAFTA",  "한·아세안 FTA (Korea-ASEAN)"),
    ("KEUFTA", "한·EU FTA (Korea-EU)"),
    ("KCFTA",  "한·중 FTA (Korea-China)"),
    ("KVFTA",  "한·베트남 FTA (Korea-Vietnam)"),
    ("RCEP",   "역내포괄적경제동반자협정 (RCEP)"),
]
FTA_TYPE_CODES = {code for code, _label in FTA_TYPES}
ORIGIN_COUNTRIES = [("KR", "한국"), ("VN", "베트남"), ("CN", "중국")]


@app.get("/export/fta", response_class=HTMLResponse)
async def export_fta_list(req: Request):
    """원산지증명서 목록 (안지연 본업 · 04 시뮬 MISSING #1)."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    status = req.query_params.get("status") or None
    fta_type = req.query_params.get("fta_type") or None
    items = get_fta_certificates(status=status, fta_type=fta_type, limit=300)
    return ctx(req, "fta_list.html", user=u, active="export",
               items=items, FTA_TYPES=FTA_TYPES,
               filter_status=status or "", filter_fta_type=fta_type or "")


@app.get("/export/fta/new", response_class=HTMLResponse)
async def export_fta_new_form(req: Request):
    """원산지증명서 신규 발급 폼."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        customers = [dict(r) for r in c.execute(
            "SELECT id, name, country FROM customers ORDER BY name LIMIT 200"
        ).fetchall()]
        export_orders = [dict(r) for r in c.execute(
            """SELECT eo.id, eo.buyer, COALESCE(o.order_no,'-') AS order_no
               FROM export_orders eo
               LEFT JOIN orders o ON o.id = eo.order_id
               ORDER BY eo.id DESC LIMIT 100"""
        ).fetchall()]
        parts_options = [dict(r) for r in c.execute(
            "SELECT id, name, spec, unit FROM parts ORDER BY name LIMIT 300"
        ).fetchall()]
    return ctx(req, "fta_form.html", user=u, active="export",
               customers=customers, export_orders=export_orders,
               parts_options=parts_options,
               FTA_TYPES=FTA_TYPES, ORIGIN_COUNTRIES=ORIGIN_COUNTRIES,
               cert=None)


@app.post("/export/fta")
async def export_fta_create(req: Request):
    """원산지증명서 신규 등록. cert_no 자동 생성 (FTA-YYYY-####)."""
    u = _export_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    fta_type = (form.get("fta_type") or "").strip().upper()
    if fta_type not in FTA_TYPE_CODES:
        return JSONResponse({"error": "fta_type 필수"}, 400)
    customer_id_raw = form.get("customer_id")
    customer_id = int(customer_id_raw) if (customer_id_raw and customer_id_raw.isdigit()) else None
    customer_name = (form.get("customer_name") or "").strip() or None
    customer_address = (form.get("customer_address") or "").strip() or None
    customer_country = (form.get("customer_country") or "").strip() or None
    eo_raw = form.get("export_order_id")
    export_order_id = int(eo_raw) if (eo_raw and eo_raw.isdigit()) else None
    export_invoice_no = (form.get("export_invoice_no") or "").strip() or None
    export_date = (form.get("export_date") or "").strip() or None
    origin_country = (form.get("origin_country") or "KR").strip() or "KR"
    currency = (form.get("currency") or "USD").strip() or "USD"
    remarks = (form.get("remarks") or "").strip() or None
    # 라인 파싱 — line_part_id[], line_part_name[], line_hs[], line_qty[], line_unit[], line_unit_price[], line_origin[]
    part_ids = form.getlist("line_part_id") if hasattr(form, "getlist") else []
    part_names = form.getlist("line_part_name") if hasattr(form, "getlist") else []
    hs_codes = form.getlist("line_hs") if hasattr(form, "getlist") else []
    qtys = form.getlist("line_qty") if hasattr(form, "getlist") else []
    units = form.getlist("line_unit") if hasattr(form, "getlist") else []
    unit_prices = form.getlist("line_unit_price") if hasattr(form, "getlist") else []
    origins = form.getlist("line_origin") if hasattr(form, "getlist") else []
    items = []
    total_value = 0.0
    n = max(len(part_names), len(hs_codes), len(qtys))
    for i in range(n):
        pname = (part_names[i] if i < len(part_names) else "").strip()
        hs = (hs_codes[i] if i < len(hs_codes) else "").strip()
        if not pname and not hs:
            continue
        pid_raw = part_ids[i] if i < len(part_ids) else ""
        try:
            pid = int(pid_raw) if pid_raw and pid_raw.isdigit() else None
        except Exception:
            pid = None
        try:
            qv = float(qtys[i]) if i < len(qtys) and qtys[i] else 0.0
        except Exception:
            qv = 0.0
        try:
            up = float(unit_prices[i]) if i < len(unit_prices) and unit_prices[i] else 0.0
        except Exception:
            up = 0.0
        line_total = round(qv * up, 2)
        total_value += line_total
        items.append({
            "part_id": pid,
            "part_name": pname or None,
            "hs_code": hs or None,
            "qty": qv,
            "unit": (units[i] if i < len(units) else "") or None,
            "unit_price": up,
            "origin_country": (origins[i] if i < len(origins) else "") or origin_country,
            "total": line_total,
        })
    issuer_id = u["id"] if isinstance(u, dict) else u["id"]
    issuer_name = (u.get("name") if isinstance(u, dict) else u["name"]) or None
    cert_id, cert_no = create_fta_certificate(
        fta_type=fta_type,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_address=customer_address,
        customer_country=customer_country,
        export_order_id=export_order_id,
        export_invoice_no=export_invoice_no,
        export_date=export_date,
        origin_country=origin_country,
        total_value=total_value,
        currency=currency,
        issuer_id=issuer_id,
        issuer_name=issuer_name,
        items=items,
        remarks=remarks,
        created_by=issuer_id,
    )
    return RedirectResponse(f"/export/fta/{cert_id}", 303)


@app.get("/export/fta/{cert_id}", response_class=HTMLResponse)
async def export_fta_detail(req: Request, cert_id: int):
    """원산지증명서 상세 (라인 + 발급/인쇄 액션)."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    cert = get_fta_certificate(cert_id)
    if not cert:
        return RedirectResponse("/export/fta", 303)
    company = _company_info_dict()
    with db_session() as c:
        customers = [dict(r) for r in c.execute(
            "SELECT id, name, country FROM customers ORDER BY name LIMIT 200"
        ).fetchall()]
        export_orders = [dict(r) for r in c.execute(
            """SELECT eo.id, eo.buyer, COALESCE(o.order_no,'-') AS order_no
               FROM export_orders eo
               LEFT JOIN orders o ON o.id = eo.order_id
               ORDER BY eo.id DESC LIMIT 100"""
        ).fetchall()]
        parts_options = [dict(r) for r in c.execute(
            "SELECT id, name, spec, unit FROM parts ORDER BY name LIMIT 300"
        ).fetchall()]
    return ctx(req, "fta_form.html", user=u, active="export",
               cert=cert, company=company,
               customers=customers, export_orders=export_orders,
               parts_options=parts_options,
               FTA_TYPES=FTA_TYPES, ORIGIN_COUNTRIES=ORIGIN_COUNTRIES)


@app.post("/export/fta/{cert_id}/issue")
async def export_fta_issue(req: Request, cert_id: int):
    """원산지증명서 발급 확정 (DRAFT → ISSUED)."""
    u = _export_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    with db_session() as c:
        c.execute(
            "UPDATE fta_certificates SET status='ISSUED', "
            "issued_at=datetime('now','localtime') "
            "WHERE id=? AND status='DRAFT'",
            (int(cert_id),)
        )
    return RedirectResponse(f"/export/fta/{cert_id}", 303)


@app.get("/export/fta/{cert_id}/print", response_class=HTMLResponse)
async def export_fta_print(req: Request, cert_id: int):
    """원산지증명서 인쇄 view (HTML + window.print(), 외부 PDF 0건)."""
    u = _export_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    cert = get_fta_certificate(cert_id)
    if not cert:
        return RedirectResponse("/export/fta", 303)
    company = _company_info_dict()
    fta_label_map = {code: label for code, label in FTA_TYPES}
    return ctx(req, "fta_print.html", user=u,
               cert=cert, company=company,
               fta_label=fta_label_map.get(cert.get("fta_type"), cert.get("fta_type") or "FTA"))


# =====================================================
# 검사기 출하성적서 QC INSPECTION REPORT (사이클 76 · 2026-04-27)
# 김정록 본업 — 검사기 반복성 검증 + 출하성적서 작성 (04 시뮬 MISSING #2)
# 외부 PDF 라이브러리 0건 (HTML 인쇄 view + window.print() 사이클 75 패턴)
# v2 본체 미접촉 / 핫패치 130 보존 / SQL 파라미터 바인딩
# =====================================================
from .database import (create_qc_inspection_report, get_qc_inspection_reports,
                       get_qc_inspection_report, QC_STANDARD_ITEMS)

QC_OVERALL_OPTIONS = [
    ("PASS",              "합격 (PASS)"),
    ("CONDITIONAL_PASS",  "조건부 합격 (CONDITIONAL PASS)"),
    ("FAIL",              "불합격 (FAIL)"),
]


def _qcr_guard(req: Request):
    """검사기 출하성적서 가드 — admin/ceo/executive OR 품질팀 OR 검사기팀 OR can_use_quality."""
    u = get_user(req)
    if not u:
        return None
    role = u.get("role") if isinstance(u, dict) else u["role"]
    if role in ("admin", "ceo", "executive"):
        return u
    if u.get("can_use_quality"):
        return u
    tid = u.get("team_id")
    if tid:
        with db_session() as c:
            row = c.execute(
                "SELECT name FROM teams WHERE id=?", (tid,)
            ).fetchone()
        if row:
            tname = row["name"] or ""
            if "품질" in tname or "검사기" in tname or "QA" in tname.upper():
                return u
    return None


@app.get("/qc/inspection-reports", response_class=HTMLResponse)
async def qc_report_list(req: Request):
    """검사기 출하성적서 목록 (김정록 본업 · 04 시뮬 MISSING #2)."""
    u = _qcr_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    status = req.query_params.get("status") or None
    overall = req.query_params.get("overall") or None
    items = get_qc_inspection_reports(status=status, overall=overall, limit=300)
    return ctx(req, "qc_report_list.html", user=u, active="qc_reports",
               items=items, QC_OVERALL_OPTIONS=QC_OVERALL_OPTIONS,
               filter_status=status or "", filter_overall=overall or "")


@app.get("/qc/inspection-reports/new", response_class=HTMLResponse)
async def qc_report_new_form(req: Request):
    """검사기 출하성적서 신규 발급 폼."""
    u = _qcr_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        customers = [dict(r) for r in c.execute(
            "SELECT id, name, country FROM customers ORDER BY name LIMIT 200"
        ).fetchall()]
        orders = [dict(r) for r in c.execute(
            """SELECT o.id, o.order_no, COALESCE(cu.name,'-') AS cust_name
               FROM orders o
               LEFT JOIN customers cu ON cu.id = o.customer_id
               ORDER BY o.id DESC LIMIT 100"""
        ).fetchall()]
        parts_options = [dict(r) for r in c.execute(
            "SELECT id, name, spec, unit FROM parts ORDER BY name LIMIT 300"
        ).fetchall()]
    return ctx(req, "qc_report_form.html", user=u, active="qc_reports",
               customers=customers, orders=orders, parts_options=parts_options,
               QC_OVERALL_OPTIONS=QC_OVERALL_OPTIONS,
               QC_STANDARD_ITEMS=QC_STANDARD_ITEMS,
               report=None)


@app.post("/qc/inspection-reports")
async def qc_report_create(req: Request):
    """검사기 출하성적서 신규 등록. report_no 자동 생성 (QCR-YYYY-####)."""
    u = _qcr_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    customer_id_raw = form.get("customer_id")
    customer_id = int(customer_id_raw) if (customer_id_raw and customer_id_raw.isdigit()) else None
    customer_name = (form.get("customer_name") or "").strip() or None
    order_id_raw = form.get("order_id")
    order_id = int(order_id_raw) if (order_id_raw and order_id_raw.isdigit()) else None
    order_no = (form.get("order_no") or "").strip() or None
    part_id_raw = form.get("part_id")
    part_id = int(part_id_raw) if (part_id_raw and part_id_raw.isdigit()) else None
    machine_model = (form.get("machine_model") or "").strip() or None
    machine_serial = (form.get("machine_serial") or "").strip() or None
    inspection_date = (form.get("inspection_date") or "").strip() or None
    overall = (form.get("overall") or "PASS").strip().upper()
    if overall not in ("PASS", "FAIL", "CONDITIONAL_PASS"):
        overall = "PASS"
    qa_raw = form.get("qa_manager_id")
    qa_manager_id = int(qa_raw) if (qa_raw and qa_raw.isdigit()) else None
    qa_manager_name = (form.get("qa_manager_name") or "").strip() or None
    remarks = (form.get("remarks") or "").strip() or None
    # 라인 파싱 — line_item_name[], line_spec[], line_measured[], line_judgment[], line_remarks[]
    item_names = form.getlist("line_item_name") if hasattr(form, "getlist") else []
    specs = form.getlist("line_spec") if hasattr(form, "getlist") else []
    measureds = form.getlist("line_measured") if hasattr(form, "getlist") else []
    judgments = form.getlist("line_judgment") if hasattr(form, "getlist") else []
    line_remarks_l = form.getlist("line_remarks") if hasattr(form, "getlist") else []
    items = []
    fail_seen = False
    n = max(len(item_names), len(specs), len(measureds))
    for i in range(n):
        nm = (item_names[i] if i < len(item_names) else "").strip()
        if not nm:
            continue
        jdg = (judgments[i] if i < len(judgments) else "PASS").strip().upper() or "PASS"
        if jdg not in ("PASS", "FAIL", "NA"):
            jdg = "PASS"
        if jdg == "FAIL":
            fail_seen = True
        items.append({
            "item_name": nm,
            "spec_value": (specs[i] if i < len(specs) else "").strip() or None,
            "measured_value": (measureds[i] if i < len(measureds) else "").strip() or None,
            "judgment": jdg,
            "remarks": (line_remarks_l[i] if i < len(line_remarks_l) else "").strip() or None,
        })
    # overall 자동 보정 — 라인 중 FAIL 있고 사용자가 PASS 만 선택했으면 CONDITIONAL_PASS 로 보정
    if fail_seen and overall == "PASS":
        overall = "CONDITIONAL_PASS"
    inspector_id = u["id"] if isinstance(u, dict) else u["id"]
    inspector_name = (u.get("name") if isinstance(u, dict) else u["name"]) or None
    report_id, report_no = create_qc_inspection_report(
        customer_id=customer_id,
        customer_name=customer_name,
        order_id=order_id,
        order_no=order_no,
        part_id=part_id,
        machine_model=machine_model,
        machine_serial=machine_serial,
        inspection_date=inspection_date,
        inspector_id=inspector_id,
        inspector_name=inspector_name,
        qa_manager_id=qa_manager_id,
        qa_manager_name=qa_manager_name,
        overall=overall,
        items=items,
        remarks=remarks,
        created_by=inspector_id,
    )
    return RedirectResponse(f"/qc/inspection-reports/{report_id}", 303)


@app.get("/qc/inspection-reports/{report_id}", response_class=HTMLResponse)
async def qc_report_detail(req: Request, report_id: int):
    """검사기 출하성적서 상세 (라인 + 발급/인쇄 액션)."""
    u = _qcr_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    report = get_qc_inspection_report(report_id)
    if not report:
        return RedirectResponse("/qc/inspection-reports", 303)
    company = _company_info_dict()
    with db_session() as c:
        customers = [dict(r) for r in c.execute(
            "SELECT id, name, country FROM customers ORDER BY name LIMIT 200"
        ).fetchall()]
        orders = [dict(r) for r in c.execute(
            """SELECT o.id, o.order_no, COALESCE(cu.name,'-') AS cust_name
               FROM orders o
               LEFT JOIN customers cu ON cu.id = o.customer_id
               ORDER BY o.id DESC LIMIT 100"""
        ).fetchall()]
        parts_options = [dict(r) for r in c.execute(
            "SELECT id, name, spec, unit FROM parts ORDER BY name LIMIT 300"
        ).fetchall()]
    return ctx(req, "qc_report_form.html", user=u, active="qc_reports",
               report=report, company=company,
               customers=customers, orders=orders, parts_options=parts_options,
               QC_OVERALL_OPTIONS=QC_OVERALL_OPTIONS,
               QC_STANDARD_ITEMS=QC_STANDARD_ITEMS)


@app.post("/qc/inspection-reports/{report_id}/issue")
async def qc_report_issue(req: Request, report_id: int):
    """검사기 출하성적서 발급 확정 (DRAFT → ISSUED)."""
    u = _qcr_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    with db_session() as c:
        c.execute(
            "UPDATE qc_inspection_reports SET status='ISSUED', "
            "issued_at=datetime('now','localtime') "
            "WHERE id=? AND status='DRAFT'",
            (int(report_id),)
        )
    return RedirectResponse(f"/qc/inspection-reports/{report_id}", 303)


@app.get("/qc/inspection-reports/{report_id}/print", response_class=HTMLResponse)
async def qc_report_print(req: Request, report_id: int):
    """검사기 출하성적서 인쇄 view (HTML + window.print(), 외부 PDF 0건)."""
    u = _qcr_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    report = get_qc_inspection_report(report_id)
    if not report:
        return RedirectResponse("/qc/inspection-reports", 303)
    company = _company_info_dict()
    overall_label_map = {code: label for code, label in QC_OVERALL_OPTIONS}
    return ctx(req, "qc_report_print.html", user=u,
               report=report, company=company,
               overall_label=overall_label_map.get(report.get("overall"), report.get("overall") or "PASS"))


# =====================================================
# WORK ORDERS — 가공팀 작업지시서 (2026-04-27 사이클77)
# 윤영조·이수빈 본업 · 04 시뮬 MISSING #3 보완 · 외부 자산 0건
# =====================================================
from .database import (create_work_order, get_work_orders, get_work_order)

WO_STATUS_OPTIONS = [
    ("DRAFT",       "작성 중 (DRAFT)"),
    ("RELEASED",    "발행 (RELEASED)"),
    ("IN_PROGRESS", "진행 중 (IN_PROGRESS)"),
    ("COMPLETED",   "완료 (COMPLETED)"),
    ("CANCELLED",   "취소 (CANCELLED)"),
]

WO_STD_STEPS = [
    ("절삭", 60),
    ("연마", 30),
    ("검수", 15),
]


def _wo_guard(req: Request):
    """가공팀 작업지시서 가드 — admin/ceo/executive OR 가공팀(team_id=9) OR production 권한 OR leader."""
    u = get_user(req)
    if not u:
        return None
    role = u.get("role") if isinstance(u, dict) else u["role"]
    if role in ("admin", "ceo", "executive", "production"):
        return u
    tid = u.get("team_id")
    if tid:
        with db_session() as c:
            row = c.execute(
                "SELECT name FROM teams WHERE id=?", (tid,)
            ).fetchone()
        if row:
            tname = row["name"] or ""
            if "가공" in tname or "machining" in tname.lower():
                return u
    # 팀장이면 자기 팀이 가공팀인 경우 통과
    if u.get("is_leader"):
        return u
    return None


@app.get("/production/work-orders", response_class=HTMLResponse)
async def wo_list(req: Request):
    """가공팀 작업지시서 목록 (윤영조·이수빈 본업 · MISSING #3)."""
    u = _wo_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    status = req.query_params.get("status") or None
    items = get_work_orders(status=status, limit=300)
    return ctx(req, "wo_list.html", user=u, active="work_orders",
               items=items, WO_STATUS_OPTIONS=WO_STATUS_OPTIONS,
               filter_status=status or "")


@app.get("/production/work-orders/new", response_class=HTMLResponse)
async def wo_new_form(req: Request):
    """가공팀 작업지시서 신규 폼."""
    u = _wo_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    with db_session() as c:
        orders = [dict(r) for r in c.execute(
            """SELECT o.id, o.order_no, COALESCE(cu.name,'-') AS cust_name
               FROM orders o
               LEFT JOIN customers cu ON cu.id = o.customer_id
               ORDER BY o.id DESC LIMIT 100"""
        ).fetchall()]
        projects = [dict(r) for r in c.execute(
            "SELECT id, name FROM projects ORDER BY id DESC LIMIT 100"
        ).fetchall()]
        parts_options = [dict(r) for r in c.execute(
            "SELECT id, name, spec, unit FROM parts ORDER BY name LIMIT 300"
        ).fetchall()]
        users_options = [dict(r) for r in c.execute(
            "SELECT id, name FROM users WHERE active=1 ORDER BY name LIMIT 200"
        ).fetchall()]
    return ctx(req, "wo_form.html", user=u, active="work_orders",
               orders=orders, projects=projects,
               parts_options=parts_options, users_options=users_options,
               WO_STATUS_OPTIONS=WO_STATUS_OPTIONS,
               WO_STD_STEPS=WO_STD_STEPS,
               wo=None)


@app.post("/production/work-orders")
async def wo_create(req: Request):
    """가공팀 작업지시서 신규 등록. wo_no 자동 생성 (WO-YYYY-####)."""
    u = _wo_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    form = await req.form()
    order_id_raw = form.get("order_id")
    order_id = int(order_id_raw) if (order_id_raw and order_id_raw.isdigit()) else None
    project_id_raw = form.get("project_id")
    project_id = int(project_id_raw) if (project_id_raw and project_id_raw.isdigit()) else None
    part_id_raw = form.get("part_id")
    part_id = int(part_id_raw) if (part_id_raw and part_id_raw.isdigit()) else None
    try:
        qty = float(form.get("qty") or 0)
    except Exception:
        qty = 0
    assigned_raw = form.get("assigned_to")
    assigned_to = int(assigned_raw) if (assigned_raw and assigned_raw.isdigit()) else None
    assigned_name = (form.get("assigned_name") or "").strip() or None
    planned_start = (form.get("planned_start") or "").strip() or None
    planned_end = (form.get("planned_end") or "").strip() or None
    specifications = (form.get("specifications") or "").strip() or None
    remarks = (form.get("remarks") or "").strip() or None
    # 라인 파싱
    step_names = form.getlist("line_step") if hasattr(form, "getlist") else []
    durations = form.getlist("line_duration") if hasattr(form, "getlist") else []
    progresses = form.getlist("line_progress") if hasattr(form, "getlist") else []
    workers = form.getlist("line_worker") if hasattr(form, "getlist") else []
    line_remarks_l = form.getlist("line_remarks") if hasattr(form, "getlist") else []
    items = []
    n = max(len(step_names), len(durations), len(progresses))
    for i in range(n):
        nm = (step_names[i] if i < len(step_names) else "").strip()
        if not nm:
            continue
        items.append({
            "step_name": nm,
            "duration_min": durations[i] if i < len(durations) else 0,
            "progress": progresses[i] if i < len(progresses) else 0,
            "worker_name": (workers[i] if i < len(workers) else "").strip() or None,
            "remarks": (line_remarks_l[i] if i < len(line_remarks_l) else "").strip() or None,
        })
    creator_id = u["id"] if isinstance(u, dict) else u["id"]
    creator_name = (u.get("name") if isinstance(u, dict) else u["name"]) or None
    wo_id, wo_no = create_work_order(
        order_id=order_id,
        project_id=project_id,
        part_id=part_id,
        qty=qty,
        assigned_to=assigned_to,
        assigned_name=assigned_name,
        created_by=creator_id,
        created_by_name=creator_name,
        planned_start=planned_start,
        planned_end=planned_end,
        specifications=specifications,
        items=items,
        remarks=remarks,
    )
    return RedirectResponse(f"/production/work-orders/{wo_id}", 303)


@app.get("/production/work-orders/{wo_id}", response_class=HTMLResponse)
async def wo_detail(req: Request, wo_id: int):
    """가공팀 작업지시서 상세 (라인 + 진행률 + 발행/인쇄 액션)."""
    u = _wo_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    wo = get_work_order(wo_id)
    if not wo:
        return RedirectResponse("/production/work-orders", 303)
    return ctx(req, "wo_form.html", user=u, active="work_orders",
               wo=wo, WO_STATUS_OPTIONS=WO_STATUS_OPTIONS,
               WO_STD_STEPS=WO_STD_STEPS)


@app.post("/production/work-orders/{wo_id}/release")
async def wo_release(req: Request, wo_id: int):
    """가공팀 작업지시서 발행 확정 (DRAFT → RELEASED)."""
    u = _wo_guard(req)
    if not u:
        return JSONResponse({"error": "권한 없음"}, 401)
    with db_session() as c:
        c.execute(
            "UPDATE work_orders SET status='RELEASED' "
            "WHERE id=? AND status='DRAFT'",
            (int(wo_id),)
        )
    return RedirectResponse(f"/production/work-orders/{wo_id}", 303)


@app.get("/production/work-orders/{wo_id}/print", response_class=HTMLResponse)
async def wo_print(req: Request, wo_id: int):
    """가공팀 작업지시서 인쇄 view (HTML + window.print, 외부 PDF 0건)."""
    u = _wo_guard(req)
    if not u:
        return RedirectResponse("/home", 303)
    wo = get_work_order(wo_id)
    if not wo:
        return RedirectResponse("/production/work-orders", 303)
    company = _company_info_dict()
    return ctx(req, "wo_print.html", user=u,
               wo=wo, company=company)
