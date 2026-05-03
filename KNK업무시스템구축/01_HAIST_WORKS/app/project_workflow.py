"""
v5H68 (2026-05-03) — 프로젝트/수주 라이프사이클 워크플로우 (KNK 표준)

[KNK 운영 방식 — 대표 정의]
1) 고객사 미팅 → 프로젝트 등록 (관리번호 없음, 단계="제안작성")
2) 제안서 작성 (설계팀 주도, 타부서 검토 지원)
3) 견적 제출 → 수주 확정
   ★ 수주 확정 순간 → 관리번호 자동 발급 (NNN + T/M + YYMM)
   ★ 동시에 수주번호(SO) 발행 (발주일 기준)
4) 추가 발주 → 동일 관리번호 + 신규 SO만 발행 (날짜별 추적)

[관리번호 형식]
  001T2604 = 시퀀스 3자리 + 사업부(T검사기/M자동화) + YYMM
  - 시퀀스: 같은 (사업부, 년월) 내에서 1부터 증가
  - T = 검사기, M = 자동화

[수주번호 형식]
  SO-YYYYMM-#### = SO + 발주년월 + 4자리 시퀀스
  - 같은 프로젝트에 추가 발주 시 새 SO 발행
"""

import re
from datetime import date


def generate_mgmt_code(c, biz_div: str, ref_date: date | None = None) -> str:
    """관리번호 자동 발급 — NNN + T/M + YYMM 형식.
    같은 (사업부, 년월) 내 시퀀스 자동 증가.
    c: sqlite3.Connection (db_session 안에서)
    """
    if not biz_div or biz_div not in ("T", "M"):
        biz_div = "T"  # 기본 검사기
    d = ref_date or date.today()
    yymm = d.strftime("%y%m")
    suffix = f"{biz_div}{yymm}"
    # 같은 (T/M, YYMM) 내 최대 시퀀스 조회
    rows = c.execute(
        "SELECT mgmt_code FROM projects WHERE mgmt_code LIKE ?",
        (f"%{suffix}",)
    ).fetchall()
    max_seq = 0
    for r in rows:
        mc = r[0] if isinstance(r, tuple) or hasattr(r, "__getitem__") else None
        if not mc:
            continue
        m = re.match(r"^(\d{1,4})" + re.escape(suffix) + r"$", mc)
        if m:
            seq = int(m.group(1))
            if seq > max_seq:
                max_seq = seq
    next_seq = max_seq + 1
    return f"{next_seq:03d}{suffix}"


def generate_so_no(c, biz_div: str = "T",
                    ref_date: date | None = None) -> str:
    """v5H69: 수주번호 발급 — KNK 표준 [사업부]-[YYMMDD] 형식.
    예: T-260501  (검사기, 2026-05-01 발주)
    같은 사업부+날짜 복수 건: -2, -3, ...
    예: T-260501-2 (같은 날 두 번째 수주)"""
    if not biz_div or biz_div not in ("T", "M"):
        biz_div = "T"
    d = ref_date or date.today()
    yymmdd = d.strftime("%y%m%d")
    base = f"{biz_div}-{yymmdd}"
    # 같은 base / base-N 패턴 모두 조회
    rows = c.execute(
        "SELECT order_no FROM orders WHERE order_no = ? OR order_no LIKE ?",
        (base, base + "-%")
    ).fetchall()
    if not rows:
        return base  # 첫 건 → 접미 없음
    # -N 중 최대 N 찾기 (base 단독은 N=1로 간주)
    max_n = 0
    for r in rows:
        on = r[0]
        if not on:
            continue
        if on == base:
            max_n = max(max_n, 1)
        else:
            m = re.match(rf"^{re.escape(base)}-(\d+)$", on)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return f"{base}-{max_n + 1}"


def confirm_order(c, project_id: int, order_date: str | None = None,
                   total_amount: float = 0, due_date: str = "",
                   created_by: int = 0,
                   po_number: str = "",
                   note: str = "") -> dict:
    """프로젝트 수주 확정 — 관리번호 발급 + SO 발행 일괄 처리.

    Args:
      project_id: 대상 프로젝트 ID
      order_date: 발주일 (YYYY-MM-DD), None 이면 today()
      total_amount: 수주액 (원)
      due_date: 납기일
      po_number: 고객사 PO 번호 (수기 입력, 선택)

    Returns: {ok, mgmt_code, so_no, order_id, project_status, message}
    """
    proj = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not proj:
        return {"ok": False, "message": "프로젝트를 찾을 수 없음"}
    proj = dict(proj)
    biz_div = proj.get("biz_div") or "T"
    customer_id = proj.get("customer_id")

    # 발주일 파싱
    if order_date:
        try:
            from datetime import datetime as _dt
            ref_d = _dt.strptime(order_date, "%Y-%m-%d").date()
        except Exception:
            ref_d = date.today()
            order_date = ref_d.isoformat()
    else:
        ref_d = date.today()
        order_date = ref_d.isoformat()

    # 1. 관리번호 — 미발급 시 자동 발급 (v5H69: SO 발급 전 필수 단계)
    mgmt_code = (proj.get("mgmt_code") or "").strip()
    if not mgmt_code:
        mgmt_code = generate_mgmt_code(c, biz_div, ref_d)
        c.execute(
            "UPDATE projects SET mgmt_code=?, code=COALESCE(NULLIF(code,''),?), "
            "status='수주확정', stage='수주', "
            "order_date=COALESCE(order_date,?), order_amount=COALESCE(NULLIF(order_amount,0),?) "
            "WHERE id=?",
            (mgmt_code, mgmt_code, order_date, total_amount or 0, project_id)
        )

    # 2. 수주번호 발행 — 관리코드 채번 후만 (KNK 표준)
    so_no = generate_so_no(c, biz_div, ref_d)
    cur = c.execute(
        "INSERT INTO orders(order_no, customer_id, project_id, order_date, "
        "due_date, total_amount, status, created_by) "
        "VALUES(?,?,?,?,?,?,'CONFIRMED',?)",
        (so_no, customer_id, project_id, order_date, due_date or None,
         total_amount or 0, created_by or None)
    )
    order_id = cur.lastrowid

    # 3. 상태 이력 기록 (테이블 있으면)
    try:
        c.execute(
            "INSERT INTO order_status_history(order_id, from_status, to_status, "
            "changed_by, note) VALUES(?,?,?,?,?)",
            (order_id, "DRAFT", "CONFIRMED", created_by or None,
             f"신규 수주 (관리번호 {mgmt_code})" + (f" / 고객 PO {po_number}" if po_number else ""))
        )
    except Exception:
        pass

    return {
        "ok": True,
        "mgmt_code": mgmt_code,
        "so_no": so_no,
        "order_id": order_id,
        "project_status": "수주확정",
        "message": f"관리번호 {mgmt_code} 발급 + 수주번호 {so_no} 발행 완료",
    }


def add_followup_order(c, project_id: int, order_date: str | None = None,
                        total_amount: float = 0, due_date: str = "",
                        created_by: int = 0, po_number: str = "",
                        note: str = "") -> dict:
    """추가 발주 — 동일 관리번호로 신규 SO만 발행 (KNK 표준).

    Returns: {ok, mgmt_code (기존), so_no (신규), order_id, ...}
    """
    proj = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not proj:
        return {"ok": False, "message": "프로젝트를 찾을 수 없음"}
    proj = dict(proj)
    mgmt_code = (proj.get("mgmt_code") or "").strip()
    if not mgmt_code:
        return {"ok": False,
                "message": "관리번호가 발급되지 않은 프로젝트입니다. 먼저 '수주 확정'을 실행하세요."}
    customer_id = proj.get("customer_id")
    biz_div = proj.get("biz_div") or "T"

    if order_date:
        try:
            from datetime import datetime as _dt
            ref_d = _dt.strptime(order_date, "%Y-%m-%d").date()
        except Exception:
            ref_d = date.today()
            order_date = ref_d.isoformat()
    else:
        ref_d = date.today()
        order_date = ref_d.isoformat()

    # 신규 SO 발행 (관리번호는 그대로 유지) — v5H69: 사업부 인자
    so_no = generate_so_no(c, biz_div, ref_d)
    cur = c.execute(
        "INSERT INTO orders(order_no, customer_id, project_id, order_date, "
        "due_date, total_amount, status, created_by) "
        "VALUES(?,?,?,?,?,?,'CONFIRMED',?)",
        (so_no, customer_id, project_id, order_date, due_date or None,
         total_amount or 0, created_by or None)
    )
    order_id = cur.lastrowid

    # 상태 이력
    try:
        c.execute(
            "INSERT INTO order_status_history(order_id, from_status, to_status, "
            "changed_by, note) VALUES(?,?,?,?,?)",
            (order_id, "DRAFT", "CONFIRMED", created_by or None,
             f"추가 발주 (관리번호 {mgmt_code})" + (f" / 고객 PO {po_number}" if po_number else ""))
        )
    except Exception:
        pass

    return {
        "ok": True,
        "mgmt_code": mgmt_code,
        "so_no": so_no,
        "order_id": order_id,
        "message": f"추가 수주번호 {so_no} 발행 완료 (관리번호 {mgmt_code} 유지)",
    }


def get_project_orders(c, project_id: int) -> list[dict]:
    """프로젝트에 연결된 모든 수주(SO) 목록 — 발주일 순."""
    rows = c.execute(
        "SELECT id, order_no, order_date, due_date, total_amount, status, "
        "created_at FROM orders WHERE project_id=? ORDER BY order_date DESC, id DESC",
        (project_id,)
    ).fetchall()
    return [dict(r) for r in rows]
