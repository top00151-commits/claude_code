"""
v5H58 (2026-05-03 대표 지시) — 고객사 등급 자동 산정

5개 지표를 점수화하여 0~100점 산출 → 5단계 등급 자동 매핑.
사용자 수동 선택 폐지 — 시스템 자동 분류 (방치 방지).

[지표 5종]
1. 매출 (12M)         : 0~30점
2. 활성 프로젝트 수    : 0~20점
3. 최근 거래 활성도    : 0~20점 (최근 거래일 기준)
4. 업무 빈도 (90일)   : 0~15점 (해당 거래처 task 수)
5. 발주 건수 (12M)    : 0~15점 (PO + 매출 orders)

[등급 매핑]
- 70점+        : VIP    (전략 거래처, 대표 직접 관리)
- 50~69점      : 주요    (Key Account)
- 25~49점      : 일반    (정기 거래)
- 1~24점       : 신규    (시작 단계 또는 점진 감소)
- 0점 + 365일+ : 휴면    (1년 무거래)
"""

import json
from datetime import date, timedelta


def _score_revenue(amount_12m: float) -> tuple[int, str]:
    """12개월 매출 점수 (0~30)"""
    if amount_12m >= 500_000_000:
        return 30, f"5억+ ({_kw(amount_12m)})"
    if amount_12m >= 100_000_000:
        return 20, f"1~5억 ({_kw(amount_12m)})"
    if amount_12m >= 30_000_000:
        return 12, f"3천~1억 ({_kw(amount_12m)})"
    if amount_12m > 0:
        return 5, f"3천 미만 ({_kw(amount_12m)})"
    return 0, "매출 0"


def _score_active_projects(n: int) -> tuple[int, str]:
    if n >= 5: return 20, f"{n}건"
    if n >= 2: return 12, f"{n}건"
    if n >= 1: return 6,  f"{n}건"
    return 0, "0건"


def _score_recency(days_ago: int | None) -> tuple[int, str]:
    if days_ago is None:    return 0, "거래 없음"
    if days_ago <= 30:      return 20, f"{days_ago}일 전"
    if days_ago <= 90:      return 12, f"{days_ago}일 전"
    if days_ago <= 180:     return 6,  f"{days_ago}일 전"
    if days_ago <= 365:     return 2,  f"{days_ago}일 전"
    return 0, f"{days_ago}일 전 (휴면)"


def _score_task_freq(n_90d: int) -> tuple[int, str]:
    if n_90d >= 20: return 15, f"{n_90d}건/90일"
    if n_90d >= 5:  return 10, f"{n_90d}건/90일"
    if n_90d >= 1:  return 5,  f"{n_90d}건/90일"
    return 0, "0건/90일"


def _score_orders(n_12m: int) -> tuple[int, str]:
    if n_12m >= 10: return 15, f"{n_12m}건"
    if n_12m >= 3:  return 10, f"{n_12m}건"
    if n_12m >= 1:  return 5,  f"{n_12m}건"
    return 0, "0건"


def _kw(amt: float) -> str:
    if amt >= 1e8: return f"{amt/1e8:.1f}억"
    if amt >= 1e4: return f"{amt/1e4:,.0f}만"
    return f"{int(amt):,}"


def score_to_tier(score: int, days_inactive: int | None) -> str:
    """점수 + 비활성 일수 → 등급명."""
    if score == 0 and (days_inactive is None or days_inactive > 365):
        return "휴면"
    if score >= 70: return "VIP"
    if score >= 50: return "주요"
    if score >= 25: return "일반"
    return "신규"


# z1157 (대표 2026-10-11 「등급순 · VIP 먼저」): 화면의 등급 **순서**와 **색**의 기준 한 곳.
#   예전엔 화면마다 따로 적어, 고객 목록·관리자·상세 제목이 옛 A·B 등급 색을 보고 있었고(지금 등급엔 색이 안 들어감),
#   고르기 목록은 `ORDER BY tier DESC`(등급 글자 내림차순)라 휴면→주요→일반→신규→VIP 로 나왔다.
TIER_ORDER = ("VIP", "주요", "일반", "신규", "휴면")      # 같은 등급 안은 가나다(이름)
TIER_ORDER_SQL = ("CASE tier " + " ".join("WHEN '%s' THEN %d" % (t, i) for i, t in enumerate(TIER_ORDER))
                  + " ELSE %d END" % len(TIER_ORDER))
TIER_PILL = {"VIP": "pill-danger", "주요": "pill-progress", "일반": "pill-done", "신규": "pill-warn", "휴면": "pill-muted"}


# z1158 (대표 2026-10-11 「전부 같은 기준」): 고객 **고르기 목록**의 표시·순서 기준 한 곳.
#   표시 = 공용 고객 선택기(z621 · _v5_partials/customer_picker.html 의 disp())와 같다 — 시스템명(별칭) 우선, 없으면 정식 상호 + [종사업장번호]
#   (전 화면 고객사 표시는 시스템명 우선 = 대표 정책 z706). 서류(견적서·세금계산서 등)에 찍히는 이름은 정식 상호 그대로.
#   순서 = 등급순(VIP 먼저) → 같은 등급 안은 **보이는 이름** 가나다.
#   예전엔 고르기 목록마다 정식 상호만 보여, 같은 상호 「(주) 드림텍」 본사·아산·동탄이 똑같은 세 줄이었고
#   일일업무는 글자로 고객을 찾아 **늘 첫 번째(본사)로 기록**했다.
CUSTOMER_PICK_COLS = "id, name, COALESCE(alias,'') AS alias, COALESCE(sub_biz_no,'') AS sub_biz_no, tier"
CUSTOMER_PICK_ORDER_SQL = TIER_ORDER_SQL + ", COALESCE(NULLIF(TRIM(alias),''), name) COLLATE NOCASE, id"


def customer_pick_label(c):
    """고객 고르기 목록에 보일 이름(템플릿에선 `cust_label(…)`) — 공용 선택기 disp() 와 같다."""
    if c is None:
        return ""
    if hasattr(c, "get"):
        get = c.get
    else:                                   # sqlite3.Row
        keys = c.keys()
        get = (lambda k: c[k] if k in keys else None)
    base = str(get("alias") or "").strip() or str(get("name") or "").strip()
    sub = str(get("sub_biz_no") or "").strip()
    return base + (" [" + sub + "]" if sub else "")


def tier_pill_class(tier):
    """화면의 등급 알약 색 — 고객 목록·상세·수정·관리자 화면이 함께 쓴다(z1157 · 템플릿에선 `tier_pill(…)`).
    모르는 값(옛 A·B 등)은 회색."""
    return TIER_PILL.get(str(tier or "").strip(), "pill-muted")


def compute_customer_tier(c, customer_id: int, rates=None) -> dict:
    """1개 거래처의 5지표 측정 + 점수화 + 등급 산정.
    c: sqlite3.Connection (db_session 안에서 호출)
    반환: {tier, score, breakdown:[5개 항목], updated_at}
    """
    today = date.today()
    one_year_ago = (today - timedelta(days=365)).isoformat()
    ninety_ago = (today - timedelta(days=90)).isoformat()
    today_iso = today.isoformat()

    # 1. 매출 (12M) — z1191z161 (대표 11-26 「금액은 정말 중요」): 이 고객사가 1차 고객사로 적힌 수주(orders.customer_id)만,
    #    매출 홈 수주매출과 같은 식(호기 금액 · 통화/발주일 = 호기 → 수주 → 프로젝트 · 발주 달 기준환율 · 취소 수주·취소 호기·폐기 관리번호 제외).
    #    예전엔 orders.total_amount + projects.order_amount 를 둘 다 더해 같은 수주를 두 번 셌고, 통화를 안 봐 달러가 원화로 셈해졌으며,
    #    관리번호 고객(처음 등록 때 값)으로 남의 수주까지 들어갔다.
    revenue_12m = 0.0
    try:
        from .main import SALES_CCY_ITEM, SALES_DD_ORDER, _fx_load_rates, _fx_to_krw
        _rates = rates if rates is not None else _fx_load_rates(c)
        for _a, _ccy, _dd in c.execute(
                "SELECT oi.amount, " + SALES_CCY_ITEM + ", " + SALES_DD_ORDER + " "
                "FROM order_items oi JOIN orders o ON o.id=oi.order_id JOIN projects p ON p.id=o.project_id "
                "WHERE o.customer_id=? AND COALESCE(o.status,'')<>'CANCELLED' AND COALESCE(p.is_archived,0)=0 "
                "AND COALESCE(oi.unit_status,'')<>'취소'", (customer_id,)).fetchall():
            _d = str(_dd or "")[:10]
            if not _d or _d < one_year_ago:
                continue
            revenue_12m += float(_fx_to_krw(_rates, _a, _ccy, _d[:7]) or 0)
    except Exception as _e161:
        print(f"[z1191z161] 고객 등급 매출 계산 실패(고객 {customer_id}) — 매출 점수 0: {_e161!r}")
        revenue_12m = 0.0

    # 2. 활성 프로젝트 수 — z1191z161: 이 고객사 수주가 있는 관리번호(관리번호 고객 칸은 쓰지 않음)
    active_proj = 0
    try:
        r = c.execute(
            "SELECT COUNT(DISTINCT p.id) FROM projects p JOIN orders o ON o.project_id=p.id "
            "WHERE o.customer_id=? AND COALESCE(o.status,'')<>'CANCELLED' "
            "AND COALESCE(p.status,'') NOT IN ('완료','종료','취소')",
            (customer_id,)
        ).fetchone()
        active_proj = int(r[0] or 0)
    except Exception:
        pass

    # 3. 최근 거래일 (orders / tasks / 발주 중 가장 최근)
    last_dates = []
    for sql in [
        "SELECT MAX(order_date) FROM orders WHERE customer_id=?",
        "SELECT MAX(work_date) FROM tasks WHERE customer_id=?",
        "SELECT MAX(po.order_date) FROM purchase_orders po "   # z1191z161: 이 고객사 수주가 있는 관리번호
        "WHERE po.project_id IN (SELECT o.project_id FROM orders o WHERE o.customer_id=? AND COALESCE(o.status,'')<>'CANCELLED')",
    ]:
        try:
            r = c.execute(sql, (customer_id,)).fetchone()
            if r and r[0]:
                last_dates.append(r[0][:10])
        except Exception:
            pass
    days_ago = None
    if last_dates:
        last = max(last_dates)
        try:
            from datetime import datetime as _dt
            d = _dt.strptime(last, "%Y-%m-%d").date()
            days_ago = (today - d).days
        except Exception:
            days_ago = None

    # 4. 업무 빈도 (90일)
    task_n = 0
    try:
        r = c.execute(
            "SELECT COUNT(*) FROM tasks WHERE customer_id=? AND work_date>=?",
            (customer_id, ninety_ago)
        ).fetchone()
        task_n = int(r[0] or 0)
    except Exception:
        pass

    # 5. 주문/발주 건수 (12M)
    order_n = 0
    try:
        r = c.execute(
            "SELECT COUNT(*) FROM orders WHERE customer_id=? AND order_date>=?",
            (customer_id, one_year_ago)
        ).fetchone()
        order_n += int(r[0] or 0)
    except Exception:
        pass
    try:
        r = c.execute(
            "SELECT COUNT(*) FROM purchase_orders po "   # z1191z161: 이 고객사 수주가 있는 관리번호
            "WHERE po.project_id IN (SELECT o.project_id FROM orders o WHERE o.customer_id=? AND COALESCE(o.status,'')<>'CANCELLED') "
            "AND po.order_date>=?",
            (customer_id, one_year_ago)
        ).fetchone()
        order_n += int(r[0] or 0)
    except Exception:
        pass

    # 점수 합산
    s_rev,   d_rev   = _score_revenue(revenue_12m)
    s_proj,  d_proj  = _score_active_projects(active_proj)
    s_rec,   d_rec   = _score_recency(days_ago)
    s_task,  d_task  = _score_task_freq(task_n)
    s_ord,   d_ord   = _score_orders(order_n)
    total = s_rev + s_proj + s_rec + s_task + s_ord
    tier = score_to_tier(total, days_ago)

    breakdown = [
        {"label": "12개월 매출",    "score": s_rev,  "max": 30, "detail": d_rev},
        {"label": "활성 프로젝트",  "score": s_proj, "max": 20, "detail": d_proj},
        {"label": "거래 최근성",    "score": s_rec,  "max": 20, "detail": d_rec},
        {"label": "업무 빈도(90일)","score": s_task, "max": 15, "detail": d_task},
        {"label": "주문/발주 건수", "score": s_ord,  "max": 15, "detail": d_ord},
    ]
    return {
        "tier": tier, "score": total,
        "breakdown": breakdown,
        "updated_at": today_iso,
    }


def refresh_customer_tier(c, customer_id: int, rates=None) -> dict:
    """1개 거래처 등급 재계산 + DB 업데이트."""
    res = compute_customer_tier(c, customer_id, rates)
    c.execute(
        "UPDATE customers SET tier=?, tier_score=?, tier_computed_at=?, "
        "tier_breakdown=? WHERE id=?",
        (res["tier"], res["score"], res["updated_at"],
         json.dumps(res["breakdown"], ensure_ascii=False), customer_id)
    )
    return res


def refresh_all_customer_tiers(c) -> int:
    """전체 거래처 등급 일괄 재계산. 반환: 처리 건수."""
    rows = c.execute("SELECT id FROM customers").fetchall()
    n = 0
    rates = None   # z1191z161: 기준환율은 한 번만 읽는다
    try:
        from .main import _fx_load_rates
        rates = _fx_load_rates(c)
    except Exception as _e161:
        print(f"[z1191z161] 고객 등급 일괄 — 기준환율 미리 읽기 실패(고객마다 다시 읽음): {_e161!r}")
    for r in rows:
        try:
            refresh_customer_tier(c, r["id"] if hasattr(r, '__getitem__') and not isinstance(r, tuple) else r[0], rates)
            n += 1
        except Exception as e:
            print(f"[TIER ERR] customer {r[0]}: {e}")
    return n


def parse_breakdown(s: str | None) -> list:
    """tier_breakdown JSON 컬럼 → list. 빈 값/오류 시 빈 리스트."""
    if not s:
        return []
    try:
        return json.loads(s)
    except Exception:
        return []
