"""
KNK 일일업무일지 v2 - Phase 1 MVP
Task Card 기반 일일업무 + 팀장 뷰 + 경영진 대시보드 + 개인 히스토리
"""
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os, io, calendar, tempfile
from datetime import datetime, timedelta, date
from .i18n import LANGS, t as i18n_t, get_all_translations
from .database import (db_session, init_db, seed_all, seed_sample_tasks, hash_pw,
                        parse_mgmt_xls, import_mgmt_rows,
                        regenerate_user_passwords, build_password_xlsx,
                        add_comment, get_task_comments, delete_comment,
                        get_notifications, count_unread, mark_notification_read,
                        mark_all_read,
                        log_activity, log_activity_standalone, get_activities,
                        add_reaction, get_reactions, get_reactions_bulk, get_meta_bulk,
                        notify_status_change, get_user_search,
                        upsert_retro, get_retro, search_all, detect_bottlenecks,
                        delegate_task, get_delegations, resolve_delegation,
                        get_setting, get_settings_all, set_setting)

BASE = os.path.dirname(os.path.dirname(__file__))
app = FastAPI(title="KNK 일일업무일지 v2")
app.add_middleware(SessionMiddleware, secret_key="knk-haist-2026-phase1")
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
tpl = Jinja2Templates(directory=os.path.join(BASE, "app", "templates"))


@app.on_event("startup")
def startup():
    init_db()
    seed_all()
    seed_sample_tasks(14)


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
    {"key": "sales", "name": "매출·영업 센터", "desc": "Sales Hub · 영업·수주·고객사",          "icon": "📈", "href": "/sales",     "external": True},
    {"key": "logi",  "name": "자재·구매 센터", "desc": "Logistics Hub · 자재·구매·재고",         "icon": "📦", "href": "/logistics", "external": True},
]

def workspaces_for(user):
    """권한 기반 워크스페이스 목록 (시안 12B 상단 ws-switcher 용)"""
    if not user:
        return [WORKSPACES[0]]
    out = [WORKSPACES[0]]
    role = (user.get("role") or "").lower() if isinstance(user, dict) else ""
    is_exec = role in ("ceo", "admin", "executive")
    can_sales = bool(user.get("can_use_sales")) if isinstance(user, dict) else False
    can_logi  = bool(user.get("can_use_logistics")) if isinstance(user, dict) else False
    if is_exec or can_sales:
        out.append(WORKSPACES[1])
    if is_exec or can_logi:
        out.append(WORKSPACES[2])
    return out

def current_workspace_for(path: str):
    """현재 path 기반 워크스페이스 매핑"""
    p = path or ""
    if p.startswith("/sales"):     return WORKSPACES[1]
    if p.startswith("/logistics") or p.startswith("/parts") or p.startswith("/po") or p.startswith("/stock"): return WORKSPACES[2]
    return WORKSPACES[0]


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

    base = {
        "categories": CATEGORIES,
        "statuses": STATUSES,
        "today": date.today().isoformat(),
        "now": datetime.now().strftime("%Y-%m-%d %H:%M"),
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
        # C안 §4 — 워크스페이스 스위처
        "workspaces":          workspaces_for(user) if user else [],
        "current_workspace":   current_workspace_for(str(request.url.path) if hasattr(request, "url") else ""),
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


def can_use_sales(user) -> bool:
    """매출·영업 모듈 접근 권한 (Plan Y S1 — 도메인 분리).
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
    with db_session() as c:
        cur = c.execute(
            """INSERT INTO tasks(user_id, work_date, title, category, project_id, customer_id,
                                  status, hours, notes, next_plan, due_date)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                u["id"],
                d.get("work_date") or date.today().isoformat(),
                (d.get("title") or "").strip(),
                d.get("category") or "기타",
                d.get("project_id") or None,
                d.get("customer_id") or None,
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
    with db_session() as c:
        c.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (tid, u["id"]))
    return JSONResponse({"ok": True})


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
    u = get_user(req)
    if not u:
        return JSONResponse({"error":"로그인 필요"}, 401)
    d = await req.json()
    text = (d.get("text") or "").strip()
    target = d.get("target") or "vi"  # 기본: 베트남어
    if not text:
        return JSONResponse({"error":"텍스트 없음"}, 400)
    # 방법1: deep_translator
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source='auto', target=target).translate(text)
        if result:
            return JSONResponse({"ok": True, "translated": result, "target": target})
    except Exception as e1:
        print(f"[번역] GoogleTranslator 실패: {e1}")
    # 방법2: MyMemoryTranslator (fallback)
    try:
        from deep_translator import MyMemoryTranslator
        src = 'ko-KR'
        tgt_map = {'vi':'vi-VN','en':'en-GB','ko':'ko-KR','ja':'ja-JP','zh-CN':'zh-CN'}
        result = MyMemoryTranslator(source=src, target=tgt_map.get(target,'en-GB')).translate(text)
        if result:
            return JSONResponse({"ok": True, "translated": result, "target": target})
    except Exception as e2:
        print(f"[번역] MyMemoryTranslator 실패: {e2}")
    # 방법3: urllib로 직접 Google Translate 호출
    try:
        import urllib.request, urllib.parse, json as _json
        encoded = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target}&dt=t&q={encoded}"
        req2 = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=10) as resp:
            data = _json.loads(resp.read().decode())
            translated = "".join(seg[0] for seg in data[0] if seg[0])
            return JSONResponse({"ok": True, "translated": translated, "target": target})
    except Exception as e3:
        print(f"[번역] urllib 직접호출 실패: {e3}")
    return JSONResponse({"ok": False, "error": "번역 서비스에 연결할 수 없습니다. 인터넷 연결을 확인해주세요."}, 500)


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
# 통합 검색
# =====================================================
@app.get("/search", response_class=HTMLResponse)
async def search_page(req: Request, q: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    res = search_all(q, 50) if q else {"tasks":[], "comments":[], "retros":[]}
    return ctx(req, "search.html", user=u, q=q, res=res, active="search")


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
                      can_edit_changes, can_close_tickets, is_admin
               FROM users
               WHERE team_id=? AND is_active=1
               ORDER BY
                 CASE role WHEN 'executive' THEN 0 WHEN 'leader' THEN 1 ELSE 2 END,
                 id""",
            (team_id,)
        ).fetchall()]
        all_teams = []
        if u["role"] in ("ceo", "admin", "executive"):
            all_teams = [dict(r) for r in c.execute(
                """SELECT t.*, (SELECT COUNT(*) FROM users u WHERE u.team_id=t.id AND u.is_active=1) AS member_count
                   FROM teams t ORDER BY t.display_order"""
            ).fetchall()]
    return ctx(req, "admin_team_perms.html", user=u, active="team_perms",
               team=team, members=members, all_teams=all_teams)


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
            sales = 1 if form.get(f"sales_{mid}") else 0
            logi  = 1 if form.get(f"logi_{mid}")  else 0
            chg   = 1 if form.get(f"chg_{mid}")   else 0
            tkt   = 1 if form.get(f"tkt_{mid}")   else 0
            # is_admin 은 ceo/admin만 변경 가능
            if is_admin_actor:
                adm = 1 if form.get(f"adm_{mid}") else 0
                c.execute(
                    "UPDATE users SET can_use_sales=?, can_use_logistics=?, "
                    "can_edit_changes=?, can_close_tickets=?, is_admin=? WHERE id=?",
                    (sales, logi, chg, tkt, adm, mid)
                )
            else:
                c.execute(
                    "UPDATE users SET can_use_sales=?, can_use_logistics=?, "
                    "can_edit_changes=?, can_close_tickets=? WHERE id=?",
                    (sales, logi, chg, tkt, mid)
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
# =====================================================
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
        target = role_home(u_any)
        if target == "/dashboard":
            target = "/home"  # 안전 폴백
        return RedirectResponse(target, 303)
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

    return ctx(req, "dashboard.html",
               user=u, teams=teams, total_stats=total_stats,
               mon=mon, sun=sun, today_s=today_s,
               participation_rate=participation_rate,
               today_reporters=today_reporters, total_users=total_users,
               delays=delays, customers=customers, narratives=narratives)


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
        my_stats = {
            "total": len(my_tasks),
            "done": sum(1 for t in my_tasks if t["status"] == "완료"),
            "progress": sum(1 for t in my_tasks if t["status"] == "진행중"),
            "delay": sum(1 for t in my_tasks if t["status"] == "지연"),
            "hours": round(sum(t["hours"] or 0 for t in my_tasks), 1),
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

    return ctx(req, "weekly.html",
               user=u, my_tasks=my_tasks, my_stats=my_stats, my_by_cat=my_by_cat,
               team_data=team_data, all_data=all_data,
               wk_mon=mon.isoformat(), wk_sun=sun.isoformat(),
               prev_mon=prev_mon, next_mon=next_mon, teams_all=teams_all,
               active="weekly")


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
    if not (fn.endswith(".xls") or fn.endswith(".xlsx")):
        return JSONResponse({"error": "xls/xlsx 파일만 업로드 가능"}, 400)
    try:
        data = await file.read()
        suffix = ".xls" if fn.endswith(".xls") else ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(data)
            tmp_path = tf.name
        try:
            rows = parse_mgmt_xls(tmp_path)
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
    out_path = os.path.join(out_dir, "초기비밀번호_배포용.xlsx")
    build_password_xlsx(rows, out_path)
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


@app.get("/admin/download-passwords")
async def dl_passwords(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    out_path = os.path.join(BASE, "data", "초기비밀번호_배포용.xlsx")
    if not os.path.exists(out_path):
        return JSONResponse({"error": "먼저 재생성을 수행하세요"}, 404)
    with open(out_path, "rb") as f:
        data = f.read()
    from urllib.parse import quote
    fn = "KNK_초기비밀번호_배포용.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename=KNK_passwords.xlsx; filename*=UTF-8''{quote(fn)}"
    }
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


# =====================================================
# PROFILE — 비밀번호 변경
# =====================================================
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(req: Request, msg: str = "", err: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    return ctx(req, "profile.html", user=u, msg=msg, err=err, active="profile")


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
# EXCEL EXPORT — 주간 요약 엑셀
# =====================================================
@app.get("/export/weekly")
async def export_weekly(req: Request, wk_mon: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        return JSONResponse({"error": "openpyxl 미설치"}, 500)
    if not wk_mon:
        td = date.today()
        wk_mon = (td - timedelta(days=td.weekday())).isoformat()
    mon = datetime.strptime(wk_mon, "%Y-%m-%d").date()
    sun = mon + timedelta(days=6)

    wb = Workbook()
    red_fill = PatternFill(start_color="A5282C", end_color="A5282C", fill_type="solid")
    head_font = Font(name="맑은 고딕", size=11, bold=True, color="FFFFFF")
    body_font = Font(name="맑은 고딕", size=10)
    thin = Side(border_style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    with db_session() as c:
        # Sheet 1: 전사 요약
        ws = wb.active
        ws.title = "전사 요약"
        ws["A1"] = f"㈜케이엔케이 주간 업무 요약"
        ws["A1"].font = Font(name="맑은 고딕", size=14, bold=True, color="A5282C")
        ws["A2"] = f"{mon} ~ {sun}"
        ws["A2"].font = Font(name="맑은 고딕", size=10, color="4A4A4A")
        headers = ["팀코드", "팀명", "팀장", "인원", "카드수", "완료", "지연", "공수(h)"]
        for col, h in enumerate(headers, start=1):
            cell = ws.cell(row=4, column=col, value=h)
            cell.font = head_font
            cell.fill = red_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border
        teams = [dict(r) for r in c.execute(
            """SELECT t.*, u.name AS leader_name,
                      (SELECT COUNT(*) FROM users WHERE team_id=t.id AND is_active=1) AS mc
               FROM teams t LEFT JOIN users u ON t.leader_id=u.id
               ORDER BY t.display_order"""
        ).fetchall()]
        row = 5
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
            vals = [t["code"], t["name"], t["leader_name"] or "-", t["mc"],
                    s["total"] or 0, s["done"] or 0, s["delay"] or 0, round(s["hours"] or 0, 1)]
            for col, v in enumerate(vals, start=1):
                cell = ws.cell(row=row, column=col, value=v)
                cell.font = body_font
                cell.border = border
                if col >= 4:
                    cell.alignment = Alignment(horizontal="right")
            row += 1
        for col, w in enumerate([8, 18, 14, 8, 10, 10, 10, 12], start=1):
            ws.column_dimensions[chr(64 + col)].width = w

        # Sheet 2: 카드 상세
        ws2 = wb.create_sheet("카드 상세")
        headers2 = ["날짜", "팀", "이름", "직급", "제목", "분류", "프로젝트", "고객사", "상태", "공수(h)"]
        for col, h in enumerate(headers2, start=1):
            cell = ws2.cell(row=1, column=col, value=h)
            cell.font = head_font
            cell.fill = red_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = border
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
        for ri, r in enumerate(rows, start=2):
            for col, v in enumerate(r, start=1):
                cell = ws2.cell(row=ri, column=col, value=v)
                cell.font = body_font
                cell.border = border
        for col, w in enumerate([12, 14, 10, 10, 40, 10, 24, 14, 10, 10], start=1):
            ws2.column_dimensions[chr(64 + col)].width = w
        ws2.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f"KNK_주간요약_{mon}_{sun}.xlsx"
    from urllib.parse import quote
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
    return ctx(req, "ticket_detail.html", user=u, active="tickets",
               ticket=ticket, comments=comments,
               is_requester=is_requester, is_recipient=is_recipient,
               TICKET_STATUSES=TICKET_STATUSES)


@app.post("/tickets/{tid}/status")
async def tickets_status_change(req: Request, tid: int,
                                 new_status: str = Form(...),
                                 note: str = Form("")):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    ticket_change_status(tid, new_status, u["id"], note)
    return RedirectResponse(f"/tickets/{tid}", 303)


@app.post("/tickets/{tid}/comment")
async def tickets_add_comment(req: Request, tid: int, body: str = Form(...)):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    ticket_add_comment(tid, u["id"], body)
    return RedirectResponse(f"/tickets/{tid}", 303)


@app.post("/tickets/{tid}/delete")
async def tickets_delete_submit(req: Request, tid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    ticket = ticket_get(tid)
    if ticket and (ticket["requester_id"] == u["id"] or u["role"] in ("admin", "ceo")):
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
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    post = board_post_get(post_id)
    if post and _is_team_leader(u, post.get("board_team_id")):
        board_post_approve(post_id, u["id"])
    return RedirectResponse(f"/board/team/{post['board_team_id']}" if post else "/home", 303)


@app.post("/board/post/{post_id}/reject")
async def board_reject(req: Request, post_id: int, reason: str = Form("")):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    post = board_post_get(post_id)
    if post and _is_team_leader(u, post.get("board_team_id")):
        board_post_reject(post_id, u["id"], reason)
    return RedirectResponse(f"/board/team/{post['board_team_id']}" if post else "/home", 303)


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
    if not can_use_logistics(u):
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
    if not can_use_sales(u):
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
    if not can_use_logistics(u):
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
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    rows = _logi.projects_list_logi(q=q, biz_div=biz_div, stage=stage, status=status)
    return ctx(request, "projects.html",
               user=u, active="logi_projects",
               projects=rows, q=q, biz_div=biz_div, stage=stage, status=status,
               STAGES=_logi.STAGES, STATUSES=_logi.LOGI_STATUSES)


@app.get("/projects/new", response_class=HTMLResponse)
async def projects_new_form(request: Request):
    u = get_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    return ctx(request, "project_form.html",
               user=u, active="logi_projects",
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
    if not can_use_logistics(_u):
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
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    p = _logi.projects_get_logi(pid)
    if not p:
        return RedirectResponse("/projects", status_code=303)
    return ctx(request, "project_form.html",
               user=u, active="logi_projects",
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
    if not can_use_logistics(_u):
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
    if not can_use_logistics(_u):
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
    if not can_use_logistics(u):
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
    if not can_use_logistics(u):
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
                        MOVEMENT_KINDS, MOVEMENT_KIND_LABEL,
                        gen_movement_no,
                        exchange_rate_create, exchange_rates_list, exchange_rates_latest,
                        get_exchange_rate, CURRENCIES,
                        part_price_create, part_price_approve, part_prices_list,
                        part_active_price, PRICE_TYPES,
                        supplier_leadtime_stats)


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
    try:
        part_price_create({
            "part_id": pid,
            "supplier_id": int(supplier_id) if supplier_id.isdigit() else None,
            "price_type": price_type,
            "unit_price": float(unit_price),
            "currency": currency,
            "effective_from": effective_from,
            "effective_to": effective_to or None,
            "negotiated_at": negotiated_at or None,
            "min_qty": float(min_qty or 0),
            "max_qty": float(max_qty) if max_qty else None,
            "note": note,
        }, user_id=u["id"])
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
    if not can_use_logistics(u):
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
               default_part_id=part_id, active="stock")


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
    if not can_use_logistics(u):
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
    if not can_use_logistics(u):
        return RedirectResponse("/home", 303)
    with db_session() as c:
        parts = c.execute(
            """SELECT id, part_no, part_name, unit, stock_qty
               FROM parts WHERE is_active=1 ORDER BY part_name"""
        ).fetchall()
    return ctx(request, "stock_adjust.html", user=u,
               parts=[dict(r) for r in parts],
               default_part_id=part_id, active="stock")


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
    if not can_use_logistics(u):
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
    if not can_use_logistics(u):
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

