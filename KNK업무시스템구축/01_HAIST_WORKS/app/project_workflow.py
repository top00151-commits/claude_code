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
    """v5H88: 수주번호 발급 — KNK 표준 [사업부]-[YYMMDD] 형식.
    같은 날 첫 건은 접미 없음, 두 번째부터 -1, -2, -3 순차.
    예:
      첫 건       → T-260505
      두 번째     → T-260505-1
      세 번째     → T-260505-2
    (이전 v5H69 는 두 번째를 -2 로 부여해 -1 이 누락 — 대표 지적 수정)
    """
    if not biz_div or biz_div not in ("T", "M"):
        biz_div = "T"
    d = ref_date or date.today()
    yymmdd = d.strftime("%y%m%d")
    base = f"{biz_div}-{yymmdd}"
    rows = c.execute(
        "SELECT order_no FROM orders WHERE order_no = ? OR order_no LIKE ?",
        (base, base + "-%")
    ).fetchall()
    if not rows:
        return base  # 첫 건 → 접미 없음
    # 접미 N 의 최대값. base 단독은 접미 없음(0) 으로 간주 → 다음은 -1
    max_n = 0
    for r in rows:
        on = r[0]
        if not on:
            continue
        if on == base:
            continue  # 접미 없음 = N 카운트에서 제외
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
                        note: str = "", qty: int = 1) -> dict:
    """추가 발주 — 동일 관리번호로 신규 SO만 발행 (KNK 표준).

    v5H131: qty 파라미터 추가 (1~100). N대 일괄 등록 시 N개 호기 라인 자동 생성.
      - total_amount 는 **1대 단가** 의미. SO 총액 = 단가 × qty
      - 라벨은 프로젝트 전체 기준 연속번호 (예: 3호기, 4호기, ...)
      - 백워드 호환: qty 미전달 시 1로 동작 (기존 호출부 영향 없음)

    Returns: {ok, mgmt_code (기존), so_no (신규), order_id, qty, ...}
    """
    # qty 검증
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        qty = 1
    if qty < 1:
        qty = 1
    if qty > 100:
        return {"ok": False, "message": "한 번에 100대 초과 불가 (qty ≤ 100)"}
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
    # v5H106: 호기 라인도 함께 1건 자동 생성 (번호는 프로젝트 내 연속)
    # v5H131: qty 대 일괄 (각 라인 단가 = total_amount, SO 총액 = total_amount × qty)
    unit_price = float(total_amount or 0)
    so_total = unit_price * qty
    so_no = generate_so_no(c, biz_div, ref_d)
    # 프로젝트 전체에서 다음 호기 번호 계산 (모든 SO 의 items count + 1)
    try:
        base_no = c.execute(
            "SELECT COUNT(*) FROM order_items oi "
            "JOIN orders o ON o.id = oi.order_id WHERE o.project_id=?",
            (project_id,)
        ).fetchone()[0] + 1
    except Exception:
        base_no = 1
    labels_bulk = [f"{base_no + i}호기" for i in range(qty)]
    auto_label = labels_bulk[0] if qty == 1 else f"{labels_bulk[0]}~{labels_bulk[-1]}"
    cur = c.execute(
        "INSERT INTO orders(order_no, customer_id, project_id, order_date, "
        "due_date, total_amount, status, created_by, unit_label, unit_qty) "
        "VALUES(?,?,?,?,?,?,'CONFIRMED',?,?,?)",
        (so_no, customer_id, project_id, order_date, due_date or None,
         so_total, created_by or None, auto_label, qty)
    )
    order_id = cur.lastrowid
    # 호기 라인 N개 INSERT — 각 라인 동일 단가
    for _lbl in labels_bulk:
        try:
            c.execute(
                "INSERT INTO order_items(order_id, qty, unit_price, amount, "
                "unit_label, line_note) VALUES(?,1,?,?,?,?)",
                (order_id, unit_price, unit_price, _lbl, note or None)
            )
        except Exception:
            pass

    # 상태 이력
    try:
        if qty == 1:
            hist_msg = (f"추가 발주 (관리번호 {mgmt_code} · {auto_label} "
                        f"/ {unit_price:,.0f}원)")
        else:
            hist_msg = (f"추가 발주 (관리번호 {mgmt_code} · {auto_label} · "
                        f"{qty}대 × 단가 {unit_price:,.0f}원 = {so_total:,.0f}원)")
        if po_number:
            hist_msg += f" / 고객 PO {po_number}"
        c.execute(
            "INSERT INTO order_status_history(order_id, from_status, to_status, "
            "changed_by, note) VALUES(?,?,?,?,?)",
            (order_id, "DRAFT", "CONFIRMED", created_by or None, hist_msg)
        )
    except Exception:
        pass

    if qty == 1:
        msg = f"추가 수주번호 {so_no} 발행 완료 ({auto_label} / 관리번호 {mgmt_code} 유지)"
    else:
        msg = (f"추가 수주번호 {so_no} 발행 완료 ({auto_label} · {qty}대 / "
               f"단가 {unit_price:,.0f} × {qty} = {so_total:,.0f}원 / "
               f"관리번호 {mgmt_code} 유지)")
    return {
        "ok": True,
        "mgmt_code": mgmt_code,
        "so_no": so_no,
        "order_id": order_id,
        "auto_label": auto_label,
        "qty": qty,
        "unit_price": unit_price,
        "total_amount": so_total,
        "message": msg,
    }


def confirm_order_multi(c, project_id: int, units: list[dict],
                         order_date: str | None = None,
                         created_by: int = 0,
                         po_number: str = "") -> dict:
    """v5H81: 호기별 발주를 (납기, 납품지) 그룹화하여 SO 발행.

    KNK 표준 (대표 정의):
      SO 번호는 **호기/수량 구분이 아니라 진행 단위 구분용**.
      동일 관리번호라도 (납기 또는 납품지가 다르면) SO 분리.
      반대로 동일 납기 + 동일 납품지면 호기 N개라도 SO 1개.

    Args:
      project_id: 대상 프로젝트
      units: 호기 라인 [{label, amount, due_date, ship_to, note}, ...]
             label    : '1호기' 등 호기 라벨
             amount   : 호기 수주액
             due_date : 납기 (그룹화 키)
             ship_to  : 납품지 (그룹화 키)
             note     : 호기 비고
      order_date: 공통 발주일 (그룹화 키 — 같은 호출은 같은 일자)
      po_number : 고객 PO 번호 (전체 공통)

    Returns: {ok, mgmt_code, groups: [{so_no, order_id, due_date, ship_to,
              total_amount, units: [...]}], total_amount, message}
    """
    if not units:
        return {"ok": False, "message": "호기 정보가 없습니다"}
    proj = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not proj:
        return {"ok": False, "message": "프로젝트를 찾을 수 없음"}
    proj = dict(proj)
    biz_div = proj.get("biz_div") or "T"
    customer_id = proj.get("customer_id")
    # v5H89b: customer_id 비어 있으면 customer_name 으로 조회해서 채움
    if not customer_id and proj.get("customer_name"):
        try:
            row = c.execute(
                "SELECT id FROM customers WHERE name=? LIMIT 1",
                (proj["customer_name"],)
            ).fetchone()
            if row:
                customer_id = row[0]
                # 프로젝트에도 채워둠 (다음 호출 빠르게)
                c.execute("UPDATE projects SET customer_id=? WHERE id=?",
                          (customer_id, project_id))
        except Exception:
            pass

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

    # 1. 관리번호 — 미발급 시 1회만 발급
    mgmt_code = (proj.get("mgmt_code") or "").strip()
    total = sum(float(u.get("amount") or 0) for u in units)
    if not mgmt_code:
        mgmt_code = generate_mgmt_code(c, biz_div, ref_d)
        c.execute(
            "UPDATE projects SET mgmt_code=?, code=COALESCE(NULLIF(code,''),?), "
            "status='수주확정', stage='수주', "
            "order_date=COALESCE(order_date,?), order_amount=? "
            "WHERE id=?",
            (mgmt_code, mgmt_code, order_date, total, project_id)
        )
    else:
        c.execute(
            "UPDATE projects SET order_amount=COALESCE(order_amount,0)+? WHERE id=?",
            (total, project_id)
        )

    # 2. (납기, 납품지, 통화) 그룹화 — v5H92: 통화도 그룹키
    groups: dict[tuple, list[dict]] = {}
    for u in units:
        key = (
            (u.get("due_date") or "").strip(),
            (u.get("ship_to") or "").strip(),
            (u.get("currency") or "KRW").strip().upper(),
        )
        groups.setdefault(key, []).append(u)

    # 3. 그룹별 처리:
    #    v5H83 (대표 지시): 같은 날 + 같은 (납기, 납품지) 의 기존 SO 가
    #    이미 있으면 신규 SO 발행 대신 그 SO 에 호기를 추가(append).
    #    완료/송장/취소 상태인 SO 는 추가 대상에서 제외 (새로 발급).
    REUSABLE_STATUSES = ("DRAFT", "QUOTED", "CONFIRMED",
                         "IN_PRODUCTION", "READY_TO_SHIP")
    issued_groups = []
    for (g_due, g_ship, g_cur), g_units in groups.items():
        g_total = sum(float(u.get("amount") or 0) for u in g_units)
        g_qty = len(g_units)
        labels_concat = " · ".join(
            ((u.get("label") or "").strip() or f"{i+1}호기")
            for i, u in enumerate(g_units)
        )

        # 동일 (project_id, order_date, due_date, ship_to, currency) + 진행 가능 상태
        existing = None
        try:
            existing = c.execute(
                "SELECT id, order_no, total_amount, unit_qty, unit_label, status "
                "FROM orders WHERE project_id=? AND order_date=? "
                "AND COALESCE(due_date,'')=? AND COALESCE(ship_to,'')=? "
                "AND COALESCE(currency,'KRW')=? "
                "AND status IN (" + ",".join("?" * len(REUSABLE_STATUSES)) + ") "
                "ORDER BY id DESC LIMIT 1",
                (project_id, order_date, (g_due or ""), (g_ship or ""), g_cur,
                 *REUSABLE_STATUSES)
            ).fetchone()
        except Exception:
            existing = None

        if existing:
            # 기존 SO 에 호기 추가
            oid = existing["id"]
            so_no = existing["order_no"]
            new_total = float(existing["total_amount"] or 0) + g_total
            new_qty = int(existing["unit_qty"] or 1) + g_qty
            old_label = (existing["unit_label"] or "").strip()
            new_label = (old_label + " · " + labels_concat) if old_label else labels_concat
            c.execute(
                "UPDATE orders SET total_amount=?, unit_qty=?, unit_label=? WHERE id=?",
                (new_total, new_qty, new_label, oid)
            )
            reused = True
        else:
            # 신규 SO 발행 (v5H92: currency 포함)
            so_no = generate_so_no(c, biz_div, ref_d)
            try:
                cur = c.execute(
                    "INSERT INTO orders(order_no, customer_id, project_id, order_date, "
                    "due_date, total_amount, status, created_by, unit_label, unit_note, "
                    "ship_to, unit_qty, currency) "
                    "VALUES(?,?,?,?,?,?,'CONFIRMED',?,?,?,?,?,?)",
                    (so_no, customer_id, project_id, order_date, (g_due or None),
                     g_total, created_by or None, labels_concat,
                     (po_number or None), (g_ship or None), g_qty, g_cur)
                )
            except Exception:
                # currency 컬럼 미생성 환경 폴백
                cur = c.execute(
                    "INSERT INTO orders(order_no, customer_id, project_id, order_date, "
                    "due_date, total_amount, status, created_by, unit_label, unit_note, "
                    "ship_to, unit_qty) "
                    "VALUES(?,?,?,?,?,?,'CONFIRMED',?,?,?,?,?)",
                    (so_no, customer_id, project_id, order_date, (g_due or None),
                     g_total, created_by or None, labels_concat,
                     (po_number or None), (g_ship or None), g_qty)
                )
            oid = cur.lastrowid
            reused = False

        # 호기별 라인은 order_items 에 적재 (재사용/신규 모두 공통)
        for i, u in enumerate(g_units):
            lbl = (u.get("label") or "").strip() or f"{i+1}호기"
            amt = float(u.get("amount") or 0)
            note_u = (u.get("note") or "").strip()
            try:
                c.execute(
                    "INSERT INTO order_items(order_id, qty, unit_price, amount, "
                    "unit_label, line_note) VALUES(?,?,?,?,?,?)",
                    (oid, 1, amt, amt, lbl, note_u)
                )
            except Exception:
                pass

        # 상태 이력
        try:
            action_word = "호기 추가" if reused else "수주 발행"
            note_msg = (
                f"{action_word} (관리번호 {mgmt_code} · 납기 {g_due or '미지정'} · "
                f"납품지 {g_ship or '미지정'} · 호기 +{g_qty}대 — {labels_concat})"
                + (f" / 고객 PO {po_number}" if po_number else "")
            )
            c.execute(
                "INSERT INTO order_status_history(order_id, from_status, to_status, "
                "changed_by, note) VALUES(?,?,?,?,?)",
                (oid, "CONFIRMED" if reused else "DRAFT", "CONFIRMED",
                 created_by or None, note_msg)
            )
        except Exception:
            pass

        issued_groups.append({
            "so_no": so_no, "order_id": oid, "reused": reused,
            "due_date": g_due, "ship_to": g_ship, "currency": g_cur,
            "qty": g_qty, "total_amount": g_total,
            "units": [{"label": (u.get("label") or "").strip() or f"{i+1}호기",
                       "amount": float(u.get("amount") or 0),
                       "note": (u.get("note") or "").strip()}
                      for i, u in enumerate(g_units)],
        })

    n_reused = sum(1 for g in issued_groups if g.get("reused"))
    n_new = len(issued_groups) - n_reused
    msg_parts = []
    if n_new:
        msg_parts.append(f"신규 SO {n_new}건")
    if n_reused:
        msg_parts.append(f"기존 SO {n_reused}건에 호기 추가")
    return {
        "ok": True,
        "mgmt_code": mgmt_code,
        "groups": issued_groups,
        "total_amount": total,
        "message": f"관리번호 {mgmt_code} · " + " · ".join(msg_parts)
                   + f" (총 호기 {len(units)}대 / 합계 {total:,.0f}원)",
    }


def delete_order(c, order_id: int, restore_project: bool = True) -> dict:
    """v5H70: 잘못 생성한 수주 삭제 (관리번호 발급도 되돌림 옵션).

    Args:
      order_id: 삭제할 수주 ID
      restore_project: True 이면 프로젝트의 마지막 수주였을 때
                       관리번호 / status / stage 를 제안 단계로 되돌림

    Returns: {ok, message, project_id, mgmt_code_cleared}
    """
    o = c.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not o:
        return {"ok": False, "message": "수주를 찾을 수 없음"}
    o = dict(o)
    project_id = o.get("project_id")
    order_no = o.get("order_no")

    # 1) 자식 데이터 정리 (참조 무결성)
    try:
        c.execute("DELETE FROM order_status_history WHERE order_id=?", (order_id,))
    except Exception:
        pass
    try:
        c.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
    except Exception:
        pass
    try:
        c.execute("DELETE FROM invoices WHERE order_id=?", (order_id,))
    except Exception:
        pass
    try:
        c.execute("DELETE FROM receipts_payment WHERE order_id=?", (order_id,))
    except Exception:
        pass
    try:
        c.execute("DELETE FROM shipments WHERE order_id=?", (order_id,))
    except Exception:
        pass

    # 2) 수주 본체 삭제
    c.execute("DELETE FROM orders WHERE id=?", (order_id,))

    mgmt_cleared = False
    # 3) 프로젝트 상태 복원 (선택)
    if restore_project and project_id:
        # 같은 프로젝트의 다른 수주가 더 있는지 확인
        n = c.execute(
            "SELECT COUNT(*) FROM orders WHERE project_id=?",
            (project_id,)
        ).fetchone()[0]
        if n == 0:
            # 마지막 수주였다면 → 관리번호/상태 되돌림
            c.execute(
                "UPDATE projects SET mgmt_code=NULL, code=NULL, "
                "status='수주예정', stage='제안작성' "
                "WHERE id=?",
                (project_id,)
            )
            mgmt_cleared = True

    return {
        "ok": True,
        "message": f"수주번호 {order_no} 삭제됨" + (" + 관리번호 회수 (제안 단계로 복원)" if mgmt_cleared else ""),
        "project_id": project_id,
        "order_no": order_no,
        "mgmt_code_cleared": mgmt_cleared,
    }


def get_project_orders(c, project_id: int) -> list[dict]:
    """프로젝트에 연결된 모든 수주(SO) 목록 — 발주일 순.
    v5H85: 호기별 라인(order_items) 도 함께 fetch → 호기마다 금액이
           다른 경우 템플릿에서 분해 표시.
    """
    try:
        cols = {r[1] for r in c.execute("PRAGMA table_info(orders)").fetchall()}
    except Exception:
        cols = set()
    extra = []
    for cn in ("ship_to", "unit_qty", "unit_label", "unit_note", "currency"):
        if cn in cols:
            extra.append(cn)
    extra_sql = (", " + ", ".join(extra)) if extra else ""
    rows = c.execute(
        f"SELECT id, order_no, order_date, due_date, total_amount, status, "
        f"created_at{extra_sql} FROM orders WHERE project_id=? "
        f"ORDER BY order_date DESC, id DESC",
        (project_id,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if d.get("total_amount") is None:
            d["total_amount"] = 0
        if "unit_qty" not in d or d.get("unit_qty") is None:
            d["unit_qty"] = 1
        if "ship_to" not in d:
            d["ship_to"] = None
        if "unit_label" not in d:
            d["unit_label"] = None
        if "unit_note" not in d:
            d["unit_note"] = None
        if "currency" not in d or not d.get("currency"):
            d["currency"] = "KRW"

        # 호기별 라인 (order_items) — 있을 때만
        try:
            try:
                oicols = {r2[1] for r2 in c.execute(
                    "PRAGMA table_info(order_items)").fetchall()}
            except Exception:
                oicols = set()
            sel_extra = []
            if "unit_label" in oicols: sel_extra.append("unit_label")
            if "line_note" in oicols:  sel_extra.append("line_note")
            sel_extra_sql = (", " + ", ".join(sel_extra)) if sel_extra else ""
            items = c.execute(
                f"SELECT id, qty, unit_price, amount{sel_extra_sql} "
                f"FROM order_items WHERE order_id=? ORDER BY id ASC",
                (d["id"],)
            ).fetchall()
            d["units"] = [dict(it) for it in items]
            # v5H133: 호기 표시 순서를 내림차순(최근 호기 → 1호기)으로 반전 (대표 요청)
            # v5H134: 정렬 키를 각 행에 _sort_n 으로 내장 → 템플릿 sort 필터에서도 동일 키 사용
            try:
                import re as _re_u
                for _u in d["units"]:
                    _lbl = (_u.get("unit_label") or "") if isinstance(_u, dict) else ""
                    _m = _re_u.match(r"^(\d+)", _lbl)
                    _u["_sort_n"] = int(_m.group(1)) if _m else 9999
                def _u_key(_u):
                    return (_u.get("_sort_n", 9999), _u.get("unit_label") or "")
                d["units"].sort(key=_u_key, reverse=True)
            except Exception:
                pass
        except Exception:
            d["units"] = []

        # 단가 동질성 판단 — 모두 같으면 unit_price_uniform=값, 다르면 None
        if d["units"]:
            prices = {round(float(u.get("unit_price") or u.get("amount") or 0))
                      for u in d["units"]}
            d["unit_price_uniform"] = next(iter(prices)) if len(prices) == 1 else None
        else:
            d["unit_price_uniform"] = None

        # v5H91: 데이터 정합성 플래그 — 호기수/금액 불일치 감지
        items_n = len(d["units"])
        items_sum = sum(float(u.get("amount") or u.get("unit_price") or 0)
                        for u in d["units"])
        qty = int(d.get("unit_qty") or 1)
        d["mismatch_qty"] = (items_n > 0 and items_n != qty)
        d["mismatch_sum"] = (items_n > 0 and abs(items_sum - float(d.get("total_amount") or 0)) > 0.5)
        d["items_n"] = items_n
        d["items_sum"] = items_sum

        out.append(d)
    return out
