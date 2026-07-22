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
    if not biz_div or biz_div not in ("T", "M", "L"):
        biz_div = "T"  # 기본 검사기
    d = ref_date or date.today()
    yymm = d.strftime("%y%m")
    suffix = f"{biz_div}{yymm}"
    # 같은 (T/M, YYMM) 내 최대 시퀀스 조회
    rows = c.execute(
        "SELECT mgmt_code FROM projects WHERE mgmt_code LIKE ?",
        (f"%{suffix}",)
    ).fetchall()
    # v5H226z871 (대표 지시): 폐기(완전삭제)로 봉인된 관리번호도 스캔 — 삭제로 빈 자리가 돼도 재사용 금지.
    #   봉인 명부(retired_mgmt_codes)의 같은 접미 번호를 max 계산에 포함(최고번호 삭제 시 재발급 방지).
    try:
        rows = list(rows) + list(c.execute(
            "SELECT mgmt_code FROM retired_mgmt_codes WHERE mgmt_code LIKE ?", (f"%{suffix}",)).fetchall())
    except Exception:
        pass   # 명부 미생성(구 DB) 시 기존 동작
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
    """v5H88 / v5H226z776: 수주번호 발급 — KNK 표준 [사업부]-[YYMMDD]-[N] 형식.
    z776(대표 지시): 첫 건도 -1 부터 부여해 형식 일관(장비 호기와 1:1 대응 명확화).
    예:
      첫 건       → T-260505-1
      두 번째     → T-260505-2
      세 번째     → T-260505-3
    (기존 접미 없는 번호 T-260505 는 그대로 유지 — 신규 발번만 변경·충돌 없음)
    """
    # v5H226z337 (대표 확정): 수주번호 앞글자 = 사업부 5종 — 검사기 T·자동화 M·라이프밸류 L·기타 E·소모품 C.
    #   (기존 T/M/L 만 허용 → E·C 가 T 로 강제되던 것 수정. 소모품 수주번호도 'C-YYMMDD' 로, 기타는 'E-YYMMDD' 로 발행.)
    if not biz_div or biz_div not in ("T", "M", "L", "E", "C"):
        biz_div = "T"
    d = ref_date or date.today()
    yymmdd = d.strftime("%y%m%d")
    base = f"{biz_div}-{yymmdd}"
    rows = list(c.execute(
        "SELECT order_no FROM orders WHERE order_no = ? OR order_no LIKE ?",
        (base, base + "-%")
    ).fetchall())
    # v5H226z248 (대표 지시): 소모품 발주번호도 동일 형식 사용 → consumable_orders.co_no 도
    #   함께 스캔해 수주번호와 충돌 방지 (양방향).
    try:
        rows += list(c.execute(
            "SELECT co_no FROM consumable_orders WHERE co_no = ? OR co_no LIKE ?",
            (base, base + "-%")
        ).fetchall())
    except Exception:
        pass
    if not rows:
        # v5H226z776 (대표 지시): 첫 건도 -1 접미 — 수주번호 형식 일관(T-YYMMDD-1 부터 시작).
        return f"{base}-1"
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
    # v5H171: 프로젝트 헤더의 currency 를 SO 에 상속 (단일 SO 경로 누락 버그 수정)
    so_no = generate_so_no(c, biz_div, ref_d)
    _proj_ccy = (proj.get("currency") or "KRW").upper()
    # orders 테이블에 currency 컬럼이 있을 때만 포함 (백워드 호환)
    try:
        _ord_cols = {r[1] for r in c.execute("PRAGMA table_info(orders)").fetchall()}
    except Exception:
        _ord_cols = set()
    if "currency" in _ord_cols:
        cur = c.execute(
            "INSERT INTO orders(order_no, customer_id, project_id, order_date, "
            "due_date, total_amount, currency, status, created_by) "
            "VALUES(?,?,?,?,?,?,?,'CONFIRMED',?)",
            (so_no, customer_id, project_id, order_date, due_date or None,
             total_amount or 0, _proj_ccy, created_by or None)
        )
    else:
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
                        note: str = "", qty: int = 1,
                        unit_label_pattern: str | None = None,
                        so_type: str | None = None,
                        currency: str = "",
                        ship_to: str = "",
                        order_customer_id: int | None = None,
                        expand_units: bool = True,
                        line_label: str | None = None,
                        po_type: str = "") -> dict:   # v5H226z1033: 이 수주의 PO유형(비우면 '추가')
    """추가 발주 — 동일 관리번호로 신규 SO만 발행 (KNK 표준).

    v5H131: qty 파라미터 추가 (1~100). N대 일괄 등록 시 N개 호기 라인 자동 생성.
      - total_amount 는 **1대 단가** 의미. SO 총액 = 단가 × qty
      - 라벨은 프로젝트 전체 기준 연속번호 (예: 3호기, 4호기, ...)
      - 백워드 호환: qty 미전달 시 1로 동작 (기존 호출부 영향 없음)
    v5H142: so_type 파라미터 추가 (EQUIPMENT/CONSUMABLE/SERVICE/OTHER).
      - 라벨/연속번호 카운트가 so_type 별로 분리.
      - 백워드 호환: so_type 미전달 → EQUIPMENT (기존 동작 동일)
    v5H226z204 (대표 지시): expand_units 파라미터 추가 (기본 True = 기존 동작).
      - True  : 장비 — qty 만큼 호기 라인 N줄 분할 (1호기..N호기). 상한 100대.
      - False : 부품/소모품 — 동일단가 × 수량 을 **1줄**(order_items.qty=N)로 저장.
                282칸 안 만들고 한 줄. 상한 9,999. line_label 로 품목명 라벨 지정 가능.

    Returns: {ok, mgmt_code (기존), so_no (신규), order_id, qty, ...}
    """
    # qty 검증
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        qty = 1
    if qty < 1:
        qty = 1
    if expand_units:
        if qty > 100:
            return {"ok": False, "message": "장비 호기는 한 번에 100대 초과 불가 (qty ≤ 100) — 부품/소모품이면 출고형태를 '부품/기타'로 등록하세요."}
    else:
        if qty > 9999:
            return {"ok": False, "message": "수량 9,999 초과 불가 (qty ≤ 9999)"}
    proj = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not proj:
        return {"ok": False, "message": "프로젝트를 찾을 수 없음"}
    proj = dict(proj)
    mgmt_code = (proj.get("mgmt_code") or "").strip()
    if not mgmt_code:
        return {"ok": False,
                "message": "관리번호가 발급되지 않은 프로젝트입니다. 먼저 '수주 확정'을 실행하세요."}
    customer_id = proj.get("customer_id")
    # v5H226z202 (대표 지시): 한 프로젝트에 발주처(구매대행사) 여러 곳 가능 →
    #   호출자가 발주처를 지정하면 그 SO의 customer_id 로 사용(프로젝트 고객 상속 대신).
    if order_customer_id is not None:
        customer_id = order_customer_id
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
    # v5H142: so_type 정규화. 미지원/미전달 → EQUIPMENT.
    try:
        from .database import (PROJECT_TYPE_UNIT_LABEL, PROJECT_TYPES,
                                SO_TYPES, SO_TYPE_UNIT_LABEL)
    except Exception:
        PROJECT_TYPE_UNIT_LABEL = {"NEW_EQUIP": "{n}호기"}
        PROJECT_TYPES = ("NEW_EQUIP",)
        SO_TYPES = ("EQUIPMENT", "CONSUMABLE", "SERVICE", "OTHER")
        SO_TYPE_UNIT_LABEL = {"EQUIPMENT": "{n}호기",
                              "CONSUMABLE": "소모품-{n}차",
                              "SERVICE": "정비-{n}차",
                              "OTHER": "{n}건"}
    _st = (so_type or "").upper().strip()
    if _st not in SO_TYPES:
        _st = "EQUIPMENT"

    # v5H142: 연속번호도 so_type 별로 분리 카운트.
    #   소모품-1차/소모품-2차 (CONSUMABLE) 와 정비-1차/정비-2차 (SERVICE) 와
    #   1호기/2호기 (EQUIPMENT) 는 서로 독립 카운터.
    try:
        if _st == "EQUIPMENT":
            # 호기는 기존처럼 모든 EQUIPMENT(또는 NULL=호환) SO 의 items 합산 + 1
            base_no = c.execute(
                "SELECT COUNT(*) FROM order_items oi "
                "JOIN orders o ON o.id = oi.order_id "
                "WHERE o.project_id=? AND COALESCE(o.so_type,'EQUIPMENT')='EQUIPMENT'",
                (project_id,)
            ).fetchone()[0] + 1
        else:
            base_no = c.execute(
                "SELECT COUNT(*) FROM order_items oi "
                "JOIN orders o ON o.id = oi.order_id "
                "WHERE o.project_id=? AND o.so_type=?",
                (project_id, _st)
            ).fetchone()[0] + 1
    except Exception:
        # so_type 컬럼 미생성 환경 폴백 — 기존 v5H131 동작
        try:
            base_no = c.execute(
                "SELECT COUNT(*) FROM order_items oi "
                "JOIN orders o ON o.id = oi.order_id WHERE o.project_id=?",
                (project_id,)
            ).fetchone()[0] + 1
        except Exception:
            base_no = 1

    # v5H137 + v5H142: 라벨 패턴 — 호출자가 unit_label_pattern 우선, 없으면
    #   so_type 으로 결정, 그래도 없으면 project_type 폴백.
    _pattern = unit_label_pattern
    if not _pattern:
        if _st in SO_TYPE_UNIT_LABEL:
            _pattern = SO_TYPE_UNIT_LABEL[_st]
        else:
            try:
                _pt = (proj.get("project_type") or "NEW_EQUIP").upper()
                if _pt not in PROJECT_TYPES:
                    _pt = "NEW_EQUIP"
                _pattern = PROJECT_TYPE_UNIT_LABEL[_pt]
            except Exception:
                _pattern = "{n}호기"
    # v5H226z204: 부품/소모품(expand_units=False)은 N줄 분할 대신 1줄(수량=N).
    #   라벨은 호출자가 준 품목명(line_label) 우선, 없으면 패턴 1개.
    if not expand_units:
        _single_lbl = (line_label or "").strip() or _pattern.format(n=base_no)
        if qty > 1:
            auto_label = f"{_single_lbl} ×{qty}"
        else:
            auto_label = _single_lbl
    else:
        labels_bulk = [_pattern.format(n=base_no + i) for i in range(qty)]
        auto_label = labels_bulk[0] if qty == 1 else f"{labels_bulk[0]}~{labels_bulk[-1]}"
    # v5H178: 통화 — 호출자 지정값이 있으면 그것, 없으면 프로젝트 헤더 통화
    eff_currency = (currency or "").strip().upper() or (proj.get("currency") or "KRW").upper()
    if eff_currency not in ("KRW","USD","VND","JPY","CNY","EUR"):
        eff_currency = "KRW"
    eff_ship = (ship_to or "").strip() or None
    # v5H142+v5H178: so_type + currency + ship_to 컬럼 INSERT (스키마 동적 감지)
    try:
        _ord_cols = {r[1] for r in c.execute("PRAGMA table_info(orders)").fetchall()}
    except Exception:
        _ord_cols = set()
    _has_currency = "currency" in _ord_cols
    _has_ship = "ship_to" in _ord_cols
    _has_sotype = "so_type" in _ord_cols
    cols = ["order_no","customer_id","project_id","order_date","due_date",
            "total_amount","status","created_by","unit_label","unit_qty"]
    vals = [so_no, customer_id, project_id, order_date, due_date or None,
            so_total, "CONFIRMED", created_by or None, auto_label, qty]
    # v5H226z1033 (안지연 프로 신고·대표 지시): 이 함수는 **정의상 '추가 발주'** 다(동일 관리번호·신규 SO).
    #   그런데 PO유형이 projects 에만 있어 작업일정표가 프로젝트 값('신규')을 모든 줄에 복사해 보여줬다.
    #   → 이 수주 자체의 유형을 '추가'로 남긴다. 호출자가 po_type 을 명시하면 그 값(개조·수리 등).
    if "po_type" in _ord_cols:
        cols.append("po_type")
        vals.append((str(po_type or "").strip() or "추가"))
    if _has_sotype:
        cols.append("so_type"); vals.append(_st)
    if _has_currency:
        cols.append("currency"); vals.append(eff_currency)
    if _has_ship:
        cols.append("ship_to"); vals.append(eff_ship)
    placeholders = ",".join("?" * len(cols))
    cur = c.execute(
        f"INSERT INTO orders({','.join(cols)}) VALUES({placeholders})",
        vals
    )
    order_id = cur.lastrowid
    # 호기 라인 N개 INSERT — 각 라인 동일 단가
    # v5H178: order_items.currency 도 SO 와 동일하게 저장 (override 가 아니라 명시 — 표시 일관성)
    try:
        _oi_cols = {r[1] for r in c.execute("PRAGMA table_info(order_items)").fetchall()}
    except Exception:
        _oi_cols = set()
    _oi_has_extra = ("due_date" in _oi_cols and "ship_to" in _oi_cols and "currency" in _oi_cols)
    if not expand_units:
        # 부품/소모품 — 1줄 (qty=N, 라인금액 = 단가 × N = so_total)
        try:
            if _oi_has_extra:
                c.execute(
                    "INSERT INTO order_items(order_id, qty, unit_price, amount, "
                    "unit_label, line_note, currency) VALUES(?,?,?,?,?,?,?)",
                    (order_id, qty, unit_price, so_total, auto_label, note or None, eff_currency)
                )
            else:
                c.execute(
                    "INSERT INTO order_items(order_id, qty, unit_price, amount, "
                    "unit_label, line_note) VALUES(?,?,?,?,?,?)",
                    (order_id, qty, unit_price, so_total, auto_label, note or None)
                )
        except Exception:
            pass
    else:
        # 장비 — 호기 라인 N개 INSERT (각 라인 동일 단가, qty=1)
        # v5H178: order_items.currency 도 SO 와 동일하게 저장 (override 아니라 명시 — 표시 일관성)
        for _lbl in labels_bulk:
            try:
                if _oi_has_extra:
                    c.execute(
                        "INSERT INTO order_items(order_id, qty, unit_price, amount, "
                        "unit_label, line_note, currency) VALUES(?,1,?,?,?,?,?)",
                        (order_id, unit_price, unit_price, _lbl, note or None, eff_currency)
                    )
                else:
                    c.execute(
                        "INSERT INTO order_items(order_id, qty, unit_price, amount, "
                        "unit_label, line_note) VALUES(?,1,?,?,?,?)",
                        (order_id, unit_price, unit_price, _lbl, note or None)
                    )
            except Exception:
                pass

    # 상태 이력
    _unit_word = "대" if expand_units else "개"   # 장비=대 / 부품·소모품=개
    try:
        if qty == 1:
            hist_msg = (f"추가 발주 (관리번호 {mgmt_code} · {auto_label} "
                        f"/ {unit_price:,.0f}원)")
        else:
            hist_msg = (f"추가 발주 (관리번호 {mgmt_code} · {auto_label} · "
                        f"{qty}{_unit_word} × 단가 {unit_price:,.0f}원 = {so_total:,.0f}원)")
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
        msg = (f"추가 수주번호 {so_no} 발행 완료 ({auto_label} · {qty}{_unit_word} / "
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
        "so_type": _st,
        "message": msg,
    }


def append_unit_to_order(c, order_id: int, unit_price: float = 0,
                          note: str = "", line_label: str | None = None,
                          currency: str = "", qty: int = 1,
                          due_date: str = "") -> dict:
    """v5H226z820 (대표 지시): 기존 수주(SO)에 '호기 1줄'을 추가(append)한다.

    일괄(엑셀) 업로드 전용 헬퍼 — 같은 관리번호+발주일+납기+납품지+통화+담당자 인
    장비(호기) 행들을 새 수주번호를 만들지 않고 '한 수주번호에 호기별 단가'로 묶기 위함.
    (엑셀은 단가가 다르면 행을 나눠 적으므로 두 행이 되던 것을 여기서 한 SO 로 합침.)

    confirm_order_multi / add_followup_order 의 '기존 SO 호기 추가' 패턴을 그대로 재사용:
      - 호기 번호(라벨) = 그 프로젝트 전체 EQUIPMENT 호기 수 + 1 (연속·add_followup_order L291 동일 규칙)
      - order_items 1줄 INSERT (qty=1, unit_price=단가, amount=단가)
      - orders.total_amount += 단가, unit_qty += 1, unit_label 에 새 호기 라벨 이어붙임
      - order_status_history 에 '호기 추가' 이력 1줄

    Args:
      order_id   : 호기를 추가할 대상 SO(orders.id)
      unit_price : 이 호기(1대) 단가 = 라인 금액
      note       : 호기 비고(엑셀 비고)
      line_label : 호기 라벨 강제 지정(비면 'N호기' 자동)
      currency   : order_items.currency 저장값(비면 SO/프로젝트 통화 상속)

    Returns: {ok, order_id, item_id, unit_label, unit_price}
    """
    _o = c.execute("SELECT id, project_id, order_no, total_amount, unit_qty, "
                   "unit_label FROM orders WHERE id=?", (order_id,)).fetchone()
    if not _o:
        return {"ok": False, "message": "대상 수주(SO)를 찾을 수 없음"}
    _o = dict(_o)
    project_id = _o.get("project_id")
    unit_price = float(unit_price or 0)

    # 호기 번호 — add_followup_order(L291~296)와 동일: 프로젝트 전체 EQUIPMENT 호기 수 + 1.
    #   (해당 SO 뿐 아니라 프로젝트 내 모든 EQUIPMENT SO 의 order_items 합산 → 호기 번호가 전역 연속)
    try:
        _base_no = c.execute(
            "SELECT COUNT(*) FROM order_items oi "
            "JOIN orders o ON o.id = oi.order_id "
            "WHERE o.project_id=? AND COALESCE(o.so_type,'EQUIPMENT')='EQUIPMENT'",
            (project_id,)
        ).fetchone()[0] + 1
    except Exception:
        try:
            _base_no = c.execute(
                "SELECT COUNT(*) FROM order_items oi "
                "JOIN orders o ON o.id = oi.order_id WHERE o.project_id=?",
                (project_id,)
            ).fetchone()[0] + 1
        except Exception:
            _base_no = 1

    # v5H226z979 (대표 승인): qty 지원 — 병합(z820) 대상 행의 '수량 N'만큼 호기 N줄을 붙인다.
    #   기존 1줄 고정이 002M2602(6대 행→1대)·005M2602(3대 행→1대) 수량·금액 증발의 원인.
    try:
        qty = int(qty)
    except Exception:
        qty = 1
    qty = max(1, min(100, qty))
    # 라벨 — 프로젝트 유형 패턴('{n}호기' 등). 호출자 지정(line_label)이 있어도
    #   호기 라벨은 항상 'N호기'로 통일(작업일정표 호기칸 일관 — 모델명은 line_note 로 별도 보존).
    try:
        from .database import project_unit_label as _pul
        _lbls = [_pul("NEW_EQUIP", _base_no + _i) for _i in range(qty)]
    except Exception:
        _lbls = [f"{_base_no + _i}호기" for _i in range(qty)]
    _lbl = _lbls[0]

    # order_items 컬럼 감지 (currency/line_note 유무 방어)
    try:
        _oi_cols = {r[1] for r in c.execute("PRAGMA table_info(order_items)").fetchall()}
    except Exception:
        _oi_cols = set()
    eff_currency = (currency or "").strip().upper()
    if eff_currency and eff_currency not in ("KRW", "USD", "VND", "JPY", "CNY", "EUR"):
        eff_currency = ""
    _has_cur = "currency" in _oi_cols
    _has_note = "line_note" in _oi_cols
    _has_due = "due_date" in _oi_cols
    _due_v = (str(due_date or "")).strip()[:10]
    item_ids = []
    for _albl in _lbls:
        _cols = ["order_id", "qty", "unit_price", "amount", "unit_label"]
        _vals = [order_id, 1, unit_price, unit_price, _albl]
        if _has_note:
            _cols.append("line_note"); _vals.append(note or None)
        if _has_cur and eff_currency:
            _cols.append("currency"); _vals.append(eff_currency)
        if _has_due and _due_v:
            _cols.append("due_date"); _vals.append(_due_v)   # v5H226z979: 호기 납기 = 그 행 납기(비면 SO 상속 표시)
        _ph = ",".join("?" * len(_cols))
        _cur = c.execute(f"INSERT INTO order_items({','.join(_cols)}) VALUES({_ph})", _vals)
        item_ids.append(_cur.lastrowid)
    item_id = item_ids[0]

    # orders 헤더 갱신 — 총액 += 단가×N, 수량 += N, 라벨 이어붙임 (v5H226z979: N줄)
    _new_total = float(_o.get("total_amount") or 0) + unit_price * qty
    _new_qty = int(_o.get("unit_qty") or 0) + qty
    _old_lbl = (_o.get("unit_label") or "").strip()
    _lbl_join = " · ".join(_lbls)
    _new_lbl = (_old_lbl + " · " + _lbl_join) if _old_lbl else _lbl_join
    try:
        c.execute("UPDATE orders SET total_amount=?, unit_qty=?, unit_label=? WHERE id=?",
                  (_new_total, _new_qty, _new_lbl, order_id))
    except Exception:
        # unit_qty/unit_label 컬럼 미생성 환경 폴백 — 총액만 갱신
        try:
            c.execute("UPDATE orders SET total_amount=? WHERE id=?", (_new_total, order_id))
        except Exception:
            pass

    # 상태 이력 (add_followup_order 와 동일 톤)
    try:
        c.execute(
            "INSERT INTO order_status_history(order_id, from_status, to_status, "
            "changed_by, note) VALUES(?,?,?,?,?)",
            (order_id, "CONFIRMED", "CONFIRMED", None,
             f"호기 추가 (일괄등록 · {(_lbls[0] if qty == 1 else _lbls[0] + '~' + _lbls[-1])} · {qty}대 × {unit_price:,.0f}원 — 같은 수주번호에 호기별 단가)")
        )
    except Exception:
        pass

    return {"ok": True, "order_id": order_id, "item_id": item_id, "item_ids": item_ids,
            "unit_label": (_lbls[0] if qty == 1 else _lbls[0] + "~" + _lbls[-1]),
            "unit_price": unit_price, "qty": qty}


def confirm_order_multi(c, project_id: int, units: list[dict],
                         order_date: str | None = None,
                         created_by: int = 0,
                         po_number: str = "",
                         so_type: str | None = None) -> dict:
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
    v5H223: units=[] 일 때는 빈 SO 생성 (CONSUMABLE 흐름 — 라인은 후속 추가).
    """
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
    # v5H225: OTHER → E (Etc.), CONSUMABLE → C (Consumable), NEW_EQUIP → biz_div
    _ptype_proj = (proj.get("project_type") or "NEW_EQUIP").upper()
    if _ptype_proj == "OTHER":
        _code_prefix = "E"
    elif _ptype_proj == "CONSUMABLE":
        _code_prefix = "C"
    else:
        _code_prefix = biz_div
    mgmt_code = (proj.get("mgmt_code") or "").strip()
    total = sum(float(u.get("amount") or 0) for u in units)
    if not mgmt_code:
        mgmt_code = generate_mgmt_code(c, _code_prefix, ref_d)
        c.execute(
            "UPDATE projects SET mgmt_code=?, code=COALESCE(NULLIF(code,''),?), "
            "status='수주확정', stage='수주', "
            "order_date=COALESCE(order_date,?), order_amount=? "
            "WHERE id=?",
            (mgmt_code, mgmt_code, order_date, total, project_id)
        )
    else:
        # v5H226z149: 코드가 이미 있는 경우 — '기존 SO 유무'로 분기 (코드 유무로 판단하면
        #   z148(관리코드 선입력) 프로젝트의 '첫 수주확정'이 추가발주로 오인돼 금액이 2배가 됨).
        try:
            _row = c.execute(
                "SELECT COUNT(*) FROM orders WHERE project_id=?", (project_id,)).fetchone()
            _has_so = int(_row[0]) if _row else 0
        except Exception:
            _has_so = 0
        if _has_so:
            # 이미 SO 가 있는 프로젝트에 추가 확정 → 금액 누적 (기존 동작 보존)
            c.execute(
                "UPDATE projects SET order_amount=COALESCE(order_amount,0)+? WHERE id=?",
                (total, project_id)
            )
        else:
            # 첫 수주확정 (관리코드만 미리 부여됨) → 신규 확정과 동일 처리: 금액 SET + 상태 승격
            c.execute(
                "UPDATE projects SET status='수주확정', stage='수주', "
                "order_date=COALESCE(order_date,?), order_amount=? WHERE id=?",
                (order_date, total, project_id)
            )

    # v5H223: units 가 비어있고 CONSUMABLE 인 경우 — 빈 SO 1건 발행 (라인은 후속 추가)
    # v5H226z: shipment_form='PARTS' (정식 PACKING LIST) 도 빈 SO 1건 발행
    _empty_so_allowed = (_ptype_proj == "CONSUMABLE")
    _so_type_for_empty = "CONSUMABLE"
    _ship_form_proj = (proj.get("shipment_form") or "ASSEMBLY").upper()
    if _ship_form_proj == "PARTS":
        _empty_so_allowed = True
        _so_type_for_empty = "PARTS_EXPORT"
    # v5H226z436 (대표 지시): 추가발주 — 기존 '장비(ASSEMBLY)' 프로젝트에 '형태=상품' 부품 SO 를 붙일 때,
    #   호출자가 so_type=PARTS_EXPORT 를 명시하면 프로젝트 shipment_form 과 무관하게 빈 PARTS SO 발행 허용.
    #   (신규 등록 z430 경로는 프로젝트가 이미 PARTS 라 영향 없음 — 상위호환.)
    if (so_type or "").upper() == "PARTS_EXPORT":
        _empty_so_allowed = True
        _so_type_for_empty = "PARTS_EXPORT"
    if not units:
        if _empty_so_allowed:
            so_no = generate_so_no(c, biz_div, ref_d)
            _ord_cols = {r[1] for r in c.execute("PRAGMA table_info(orders)").fetchall()}
            _cols = ["order_no", "customer_id", "project_id", "order_date",
                     "due_date", "total_amount", "status", "created_by",
                     "unit_label", "unit_note", "ship_to", "unit_qty"]
            # v5H226z977 (대표 승인): 빈 SO(소모품·상품)도 납기=프로젝트 납기 상속 — 상품 SO 납기가
            #   태생 NULL(기존 하드코딩 None)이라 수주카드·제작요청서목록 납품일이 비던 원인 수정.
            _vals = [so_no, customer_id, project_id, order_date,
                     (str(proj.get("due_date") or "").strip() or None),
                     0, "CONFIRMED", created_by or None,
                     "(라인 미입력)", (po_number or None), None, 0]
            if "currency" in _ord_cols:
                _cols.append("currency")
                _vals.append(proj.get("currency") or "KRW")
            if "so_type" in _ord_cols:
                _cols.append("so_type")
                _vals.append((so_type or _so_type_for_empty).upper())
            _ph = ",".join(["?"] * len(_vals))
            _cur_ins = c.execute(
                f"INSERT INTO orders({','.join(_cols)}) VALUES({_ph})",
                _vals
            )
            return {
                "ok": True, "mgmt_code": mgmt_code,
                "groups": [{"so_no": so_no, "order_id": _cur_ins.lastrowid,
                             "due_date": None, "ship_to": None,
                             "total_amount": 0, "units": []}],
                "total_amount": 0, "so_no": so_no,
                "message": f"빈 SO 발행 (so_type={_so_type_for_empty}, 라인은 상세에서 추가)",
            }
        else:
            return {"ok": False, "message": "호기 정보가 없습니다"}

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
        # v5H226z204: unit 에 qty(>1) 가 있으면 낱개 수량(부품/소모품) — 호기수가 아닌 piece 합산.
        #   장비(qty 키 없음) 는 1 로 처리 → 기존 동작과 100% 동일.
        g_qty = sum(int(u.get("qty") or 1) for u in g_units)
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
                # v5H226z1033: 이 수주의 PO유형 = 프로젝트 유형(신규 등록 경로). 컬럼 없으면 아래 폴백.
                cur = c.execute(
                    "INSERT INTO orders(order_no, customer_id, project_id, order_date, "
                    "due_date, total_amount, status, created_by, unit_label, unit_note, "
                    "ship_to, unit_qty, currency, po_type) "
                    "VALUES(?,?,?,?,?,?,'CONFIRMED',?,?,?,?,?,?,?)",
                    (so_no, customer_id, project_id, order_date, (g_due or None),
                     g_total, created_by or None, labels_concat,
                     (po_number or None), (g_ship or None), g_qty, g_cur,
                     (str(proj.get("po_type") or "").strip() or None))
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
        # v5H177: 호기별 발주일/납기/납품처 override 지원. SO 그룹값과 같으면 NULL 저장(상속).
        try:
            _oi_cols = {r[1] for r in c.execute("PRAGMA table_info(order_items)").fetchall()}
        except Exception:
            _oi_cols = set()
        _has_extra = ("due_date" in _oi_cols and "ship_to" in _oi_cols
                      and "order_date" in _oi_cols and "currency" in _oi_cols)
        for i, u in enumerate(g_units):
            lbl = (u.get("label") or "").strip() or f"{i+1}호기"
            amt = float(u.get("amount") or 0)
            # v5H226z204: 부품/소모품 라인은 qty=N(낱개), 단가=라인금액/N. 장비는 qty=1.
            _u_qty = int(u.get("qty") or 1)
            _u_unit_price = (amt / _u_qty) if _u_qty > 1 else amt
            note_u = (u.get("note") or "").strip()
            u_due = (u.get("due_date") or "").strip()
            u_ship = (u.get("ship_to") or "").strip()
            u_ord = (u.get("order_date") or "").strip()
            u_cur = (u.get("currency") or "").strip().upper()
            # SO 그룹값과 동일하면 NULL (상속) — 다르면 override 값 저장
            ov_due = u_due if (u_due and u_due != (g_due or "")) else None
            ov_ship = u_ship if (u_ship and u_ship != (g_ship or "")) else None
            ov_ord = u_ord if (u_ord and u_ord != order_date) else None
            ov_cur = u_cur if (u_cur and u_cur != g_cur) else None
            try:
                if _has_extra:
                    c.execute(
                        "INSERT INTO order_items(order_id, qty, unit_price, amount, "
                        "unit_label, line_note, order_date, due_date, ship_to, currency) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (oid, _u_qty, _u_unit_price, amt, lbl, note_u,
                         ov_ord, ov_due, ov_ship, ov_cur)
                    )
                else:
                    c.execute(
                        "INSERT INTO order_items(order_id, qty, unit_price, amount, "
                        "unit_label, line_note) VALUES(?,?,?,?,?,?)",
                        (oid, _u_qty, _u_unit_price, amt, lbl, note_u)
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

    # 1) 자식 데이터 정리 (참조 무결성) — v5H226z736: order_id 컬럼이 있는 '모든 테이블'에서
    #   이 수주 행 삭제(동적 스윕). FK ON 환경에서 안 지운 자식(생산지시 production_orders·
    #   세금계산서묶음 tax_invoice_lines·수출헤더 export_orders 등)이 남아 있으면 orders 삭제가
    #   FK 위반으로 죽어 500이 나던 것을, 테이블이 추가돼도 안전하게 일괄 처리.
    try:
        _tbls = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    except Exception:
        _tbls = []
    for _t in _tbls:
        if _t in ("orders", "sqlite_sequence"):
            continue
        try:
            _tc = {r[1] for r in c.execute(f"PRAGMA table_info({_t})").fetchall()}
        except Exception:
            continue
        if "order_id" in _tc:
            try:
                c.execute(f"DELETE FROM {_t} WHERE order_id=?", (order_id,))
            except Exception:
                pass

    # 2) 수주 본체 삭제
    c.execute("DELETE FROM orders WHERE id=?", (order_id,))

    mgmt_cleared = False
    # 3) 프로젝트 상태 복원 (선택) — 실패해도 수주 삭제는 성립(best-effort)
    if restore_project and project_id:
        try:
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
        except Exception:
            pass

    return {
        "ok": True,
        "message": f"수주번호 {order_no} 삭제됨" + (" + 관리번호 회수 (제안 단계로 복원)" if mgmt_cleared else ""),
        "project_id": project_id,
        "order_no": order_no,
        "mgmt_code_cleared": mgmt_cleared,
    }


def project_status_from_counts(raw_counts, fallback_stage: str = "") -> dict:
    """v5H226z867 O4-1: 호기 상태 분포(raw_counts={상태:개수})로 프로젝트 종합 상태 산출.
    단건(compute_project_display_status)·벌크(compute_project_display_status_bulk) 공용 — 라벨 로직 단일화(복사 금지).
    raw_counts = GROUP BY 결과 dict(unknown 상태 포함 가능·빈dict/None=호기0건=fallback). 동작은 기존 로직 그대로.
    반환: {label, tone, dist:{진행중,출하,취소,보류}, total, done, ratio_text, has_canceled, has_held}."""
    out = {
        "label": fallback_stage or "—",
        "tone": "muted",
        "dist": {"진행중": 0, "출하": 0, "취소": 0, "보류": 0},
        "total": 0, "done": 0, "ratio_text": "",
        "has_canceled": False, "has_held": False,
    }
    for st, n in (raw_counts or {}).items():
        st = st or "진행중"
        n = int(n or 0)
        if st in out["dist"]:
            out["dist"][st] = n
        else:
            # unknown 상태 — 진행중으로 합산
            out["dist"]["진행중"] += n
    out["total"] = sum(out["dist"].values())
    out["done"] = out["dist"]["출하"]
    out["has_canceled"] = out["dist"]["취소"] > 0
    out["has_held"] = out["dist"]["보류"] > 0
    if out["total"] == 0:
        # 호기 없음 → fallback
        out["label"] = fallback_stage or "—"
        out["tone"] = "muted"
        return out
    n_prog = out["dist"]["진행중"]
    n_done = out["dist"]["출하"]
    n_cancel = out["dist"]["취소"]
    n_hold = out["dist"]["보류"]
    n_active = out["total"] - n_cancel  # 취소 제외 활성 호기
    # 분류 우선순위
    if out["total"] == n_cancel and n_cancel > 0:
        out["label"] = "취소"
        out["tone"] = "danger"
    elif n_prog == 0 and n_done > 0 and n_active == n_done:
        # 활성 호기 모두 출하
        out["label"] = "출하"
        out["tone"] = "done"
    elif n_done > 0 and n_prog > 0:
        out["label"] = f"진행중 ({n_done}/{out['total']} 완료)"
        out["tone"] = "progress"
        out["ratio_text"] = f"{n_done}/{out['total']}"
    elif n_prog > 0:
        out["label"] = "진행중"
        out["tone"] = "progress"
    elif n_hold > 0 and n_active == n_hold:
        out["label"] = "보류"
        out["tone"] = "warn"
    else:
        out["label"] = "진행중"
        out["tone"] = "progress"
    return out


def compute_project_display_status(c, project_id: int, fallback_stage: str = "") -> dict:
    """v5H200: 호기(order_items.unit_status) 들로부터 프로젝트 종합 상태 산출 (A안).
    반환: {label, tone, dist:{진행중,출하,취소,보류}, total, done, ratio_text}.
    호기 0건이면 fallback_stage(예: '제안작성') 사용.
    v5H226z867 O4-1: 라벨 로직을 project_status_from_counts 로 분리(벌크와 공용) — 동작 불변."""
    try:
        oicols = {r[1] for r in c.execute("PRAGMA table_info(order_items)").fetchall()}
    except Exception:
        oicols = set()
    if "unit_status" not in oicols:
        return project_status_from_counts({}, fallback_stage)
    try:
        rows = c.execute(
            "SELECT COALESCE(oi.unit_status,'진행중') AS st, COUNT(*) AS n "
            "FROM order_items oi JOIN orders o ON o.id = oi.order_id "
            "WHERE o.project_id = ? "
            "GROUP BY COALESCE(oi.unit_status,'진행중')",
            (project_id,)
        ).fetchall()
    except Exception:
        rows = []
    return project_status_from_counts({r["st"]: r["n"] for r in rows}, fallback_stage)


def compute_project_display_status_bulk(c, project_ids=None) -> dict:
    """v5H226z867 O4-1: 여러 프로젝트의 호기 상태 분포를 GROUP BY 1방으로 — 목록 화면 N+1(프로젝트당 PRAGMA+쿼리) 제거.
    반환: {project_id: {상태:개수}} (raw counts). 호출측이 project_status_from_counts(counts, fallback)로 라벨 산출.
    ⚠단건 함수와 자구 동일 조건(취소 SO 미제외·WHERE 상태필터 없음) — _board_unit_status_maps(취소 제외)와 절대 혼용 금지.
    project_ids=None → 전체 / 리스트 → 그 프로젝트만(정수 IN·주입불가). 실패 시 {}(호출측이 fallback 처리)."""
    out: dict = {}
    try:
        oicols = {r[1] for r in c.execute("PRAGMA table_info(order_items)").fetchall()}
    except Exception:
        oicols = set()
    if "unit_status" not in oicols:
        return out
    sql = ("SELECT o.project_id AS pid, COALESCE(oi.unit_status,'진행중') AS st, COUNT(*) AS n "
           "FROM order_items oi JOIN orders o ON o.id = oi.order_id "
           "WHERE o.project_id IS NOT NULL")
    if project_ids is not None:
        _ids = [int(i) for i in project_ids if i is not None]
        if not _ids:
            return out
        sql += " AND o.project_id IN (%s)" % ",".join(str(i) for i in _ids)
    sql += " GROUP BY o.project_id, COALESCE(oi.unit_status,'진행중')"
    try:
        for r in c.execute(sql):
            out.setdefault(r["pid"], {})[r["st"]] = r["n"]
    except Exception:
        return {}
    return out


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
    # v5H226z600: exchange_rate·is_export 추가 — 상세 PACKING LIST 에서 매입/판매 KRW 환산·인보이스(USD) 표시
    for cn in ("ship_to", "unit_qty", "unit_label", "unit_note", "currency", "so_type",
               "exchange_rate", "is_export", "shipment_form",   # v5H226z699: 수주별 형태(완제품/제품/상품/기타) 배지용
               "so_form",   # v5H226z873: 수주별 '진짜 형태' 단일 진실(있으면 so_type 추론보다 우선)
               "model_name", "equip_name",   # v5H226z981: 수주별 모델명·장비명(SO 카드 표시)
               "po_type"):   # v5H226z1034: 수주별 PO유형 — SO 카드에서 그 수주만 고치게(z1033 저장분 표시)
        if cn in cols:
            extra.append(cn)
    extra_sql = (", " + ", ".join(extra)) if extra else ""
    # v5H226z202 (대표 지시): 수주(SO)별 발주처 표시 — customer_id + 고객사명(서브쿼리)
    rows = c.execute(
        f"SELECT id, order_no, order_date, due_date, total_amount, status, "
        f"created_at, customer_id, "
        f"(SELECT name FROM customers WHERE customers.id = orders.customer_id) AS so_customer"
        f"{extra_sql} FROM orders WHERE project_id=? "
        f"ORDER BY order_date DESC, id DESC",
        (project_id,)
    ).fetchall()
    # v5H226z874 (대표 지시): 이 프로젝트의 유형 — so_form 없는 옛 데이터의 형태 배지 폴백 판정용.
    #   소모품 프로젝트가 아닌데 so_type=CONSUMABLE 인 1줄은 '제품(z466)'을 저장방식으로 표기한 것이라 '소모품' 오표시 → '제품'으로 교정.
    try:
        _prow = c.execute("SELECT COALESCE(project_type,'NEW_EQUIP') AS pt FROM projects WHERE id=?",
                          (project_id,)).fetchone()
        _proj_ptype = ((_prow["pt"] if _prow else "NEW_EQUIP") or "NEW_EQUIP").upper()
    except Exception:
        _proj_ptype = "NEW_EQUIP"
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
        # v5H142: so_type — NULL → EQUIPMENT (백워드 호환)
        if "so_type" not in d or not d.get("so_type"):
            d["so_type"] = "EQUIPMENT"

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
            # v5H177: 호기별 발주일/납기/납품처/통화 override 컬럼
            # v5H186: unit_status (호기별 상태)
            # v5H197: is_export (호기별 거래구분)
            for _c in ("order_date", "due_date", "ship_to", "currency", "unit_status", "is_export",
                       "image_path", "image_thumb_path",  # v5H226e: 소모품 라인 이미지
                       "linked_project_id",               # v5H226g: 소모품 라인 → 장비 매칭
                       "maker", "origin", "box_no", "spec", "arrival_status",  # v5H226z: 정식 PACKING LIST
                       "supplier", "unit",  # v5H226z4: 업체명/단위 별도
                       "cost_price", "margin_pct",  # v5H226z460: 상품 원가관리(매입단가·마진%)
                       "cost_krw", "sell_krw",  # v5H226z737: 수출 건 매입/판매 KRW 원본(상세 표시·없으면 화면이 USD로 폴백하던 버그)
                       "fx_rate",  # v5H226z945: 부품 행별 환율(환율 칸을 부품별 실제 환율로 표시)
                       # v5H226z634 (대표 지시): 호기별 거래명세서·세금계산서(1/2/3) — 수주 내역 표에서 호기마다 보기
                       "statement_date", "tax_invoice_date", "tax_invoice_amt1",
                       "tax_invoice_date2", "tax_invoice_amt2",
                       "tax_invoice_date3", "tax_invoice_amt3",
                       # v5H226z5: 통관 컬럼
                       "hs_code", "duty_rate", "vat_rate",
                       "invoice_unit_price", "invoice_amount",
                       "invoice_unit_price_usd", "invoice_amount_usd",
                       "duty_krw", "duty_usd", "final_amount_usd",
                       "description", "pallet_size", "weight_kg"):
                if _c in oicols: sel_extra.append(_c)
            sel_extra_sql = (", " + ", ".join("oi." + _c for _c in sel_extra)) if sel_extra else ""
            # v5H226g: linked_project_id → projects.mgmt_code/name 자동 JOIN (소모품 행 표시용)
            _has_link = "linked_project_id" in oicols
            _join_sql = " LEFT JOIN projects lp ON lp.id = oi.linked_project_id" if _has_link else ""
            _link_cols = ", lp.mgmt_code AS linked_mgmt_code, lp.name AS linked_project_name" if _has_link else ""
            items = c.execute(
                f"SELECT oi.id, oi.qty, oi.unit_price, oi.amount{sel_extra_sql}{_link_cols} "
                f"FROM order_items oi{_join_sql} "
                f"WHERE oi.order_id=? ORDER BY oi.id ASC",
                (d["id"],)
            ).fetchall()
            d["units"] = [dict(it) for it in items]
            # v5H177: 각 호기에 effective 값 (override 없으면 SO 부모값) 채워줌
            for _u in d["units"]:
                _u["eff_order_date"] = _u.get("order_date") or d.get("order_date")
                _u["eff_due_date"]   = _u.get("due_date")   or d.get("due_date")
                _u["eff_ship_to"]    = _u.get("ship_to")    or d.get("ship_to")
                _u["eff_currency"]   = _u.get("currency")   or d.get("currency") or "KRW"
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
        # v5H226z974 (대표 지시): 상품(PARTS_EXPORT)은 unit_qty='완제품 몇 대분'·1줄=부품 1종 — 호기수 불일치 경고 대상 아님
        _is_parts974 = (str(d.get("so_type") or "").upper() == "PARTS_EXPORT")
        d["mismatch_qty"] = (items_n > 0 and items_n != qty and not _is_parts974)
        d["mismatch_sum"] = (items_n > 0 and abs(items_sum - float(d.get("total_amount") or 0)) > 0.5)
        d["items_n"] = items_n
        d["items_sum"] = items_sum

        # v5H226z699 (대표 지시): 수주(발주)별 '형태' 라벨 — 화면 표시(호기별 N줄=완제품 / 1줄=제품)와 일치하게.
        #   소모품/부품은 so_type, 장비는 shipment_form(있으면) 우선 + 호기-라벨(_sort_n<9999) 유무로 완제품/제품 판정.
        #   (과거 SO 는 shipment_form 이 NULL 인 경우가 많아, 실제 호기 분할 여부로 표시와 어긋나지 않게 함.)
        _styp = (d.get("so_type") or "").upper()
        _sf = (d.get("shipment_form") or "").upper()
        _hogi_n = sum(1 for _u in d["units"] if (_u.get("_sort_n") or 9999) < 9999)
        # v5H226z873 (대표 지시): so_form(수주별 진짜 형태)이 있으면 그것을 단일 진실로 — so_type 추론보다 우선.
        #   근본원인: 일괄등록이 '제품 1줄'을 so_type=CONSUMABLE 로 저장(호기오염 방지)해 제품이 소모품으로 오표시됐음.
        #   so_form 값(ASSEMBLY/SEMI/PARTS/ETC/CONSUMABLE) 은 형태를 직접 담아 오표시 원천 차단. 없으면(구 데이터) 기존 추론.
        _soform = (d.get("so_form") or "").upper()
        _FORM_LABELKEY = {"ASSEMBLY": ("완제품", "assembly"), "SEMI": ("제품", "semi"),
                          "PARTS": ("상품", "parts"), "ETC": ("기타", "etc"),
                          "CONSUMABLE": ("소모품", "consumable")}
        if _soform in _FORM_LABELKEY:
            d["form_label"], d["form_key"] = _FORM_LABELKEY[_soform]
        elif _styp == "CONSUMABLE":
            # v5H226z874 (대표 지시): so_form 없는 옛 데이터 교정 —
            #   소모품 프로젝트면 진짜 소모품, 아니면(장비/기타) '제품 1줄'을 so_type=CONSUMABLE 로 저장한 것(z466)이라 '제품'으로 표시.
            #   (정확한 상품/기타 구분은 so_form 이 있어야 가능 → 재업로드 시 그 값이 우선.)
            if _proj_ptype == "CONSUMABLE":
                d["form_label"], d["form_key"] = "소모품", "consumable"
            else:
                d["form_label"], d["form_key"] = "제품", "semi"
        elif _styp == "PARTS_EXPORT" or _sf == "PARTS":
            d["form_label"], d["form_key"] = "상품", "parts"
        elif _sf == "ETC":
            d["form_label"], d["form_key"] = "기타", "etc"
        elif _hogi_n >= 1 or _sf == "ASSEMBLY":
            d["form_label"], d["form_key"] = "완제품", "assembly"
        else:
            d["form_label"], d["form_key"] = "제품", "semi"

        out.append(d)
    return out


# ============================================================
# v5H226r: 프로젝트/SO/호기 상태 cascade 동기화
# ============================================================
# 보호 규칙
#   - SO: status IN ('INVOICED', 'PAID')  → cascade 제외 (수금 시작분 보존)
#   - 호기: unit_status IN ('출하', '취소') → cascade 제외 (terminal)
# 매핑
PROJECT_TO_UNIT_STATUS = {
    "진행중":   "진행중",
    "출하": "출하",
    "취소":     "취소",
    "보류":     "보류",
}
PROJECT_TO_SO_STATUS = {
    "진행중":   "IN_PRODUCTION",  # v5H226y: CONFIRMED 는 transient (수주발행 직후), 진행중 = IN_PRODUCTION 이 의미상 일치
    "출하": "SHIPPED",
    "취소":     "CANCELLED",
    "보류":     None,  # 보류는 SO 자체 상태 변경 안함
}
PROTECTED_SO_STATUSES = ("INVOICED", "PAID")
# v5H226w: terminal 보호 폐지 — 프로젝트 상태가 마스터, 호기는 따라옴.
# 재무 잠금(SO INVOICED/PAID) 만 보호. 호기 unit_status 는 모두 cascade 가능.


def cascade_project_status_to_so(c, project_id: int, new_status: str,
                                  changed_by: int | None = None) -> dict:
    """v5H226r/w — 프로젝트 status 변경 시 자식 SO·호기 자동 동기화.
    cascade 대상이 아닌 status (제안작성/초기협의/...) 는 no-op.
    INVOICED/PAID SO 만 보호 (재무 기록). 호기는 모두 cascade — 사용자 직관(프로젝트=마스터)."""
    target_unit = PROJECT_TO_UNIT_STATUS.get(new_status)
    target_so = PROJECT_TO_SO_STATUS.get(new_status)
    if not target_unit:
        return {"units_changed": 0, "orders_changed": 0, "skipped": True}
    units_changed = 0
    orders_changed = 0
    try:
        # 호기 unit_status 일괄 갱신 — 보호 SO(INVOICED/PAID)에 속한 것만 제외
        # v5H226w: terminal 보호('출하','취소') 폐지 → 프로젝트→진행중 등
        # 역방향 변경도 호기까지 일괄 cascade
        try:
            _r = c.execute(
                f"""UPDATE order_items SET unit_status=?
                    WHERE id IN (
                      SELECT oi.id FROM order_items oi
                      JOIN orders o ON o.id = oi.order_id
                      WHERE o.project_id=?
                        AND COALESCE(oi.unit_status,'진행중') != ?
                        AND COALESCE(o.status,'') NOT IN ({','.join('?'*len(PROTECTED_SO_STATUSES))})
                    )""",
                (target_unit, project_id, target_unit, *PROTECTED_SO_STATUSES)
            )
            units_changed = _r.rowcount or 0
        except Exception:
            units_changed = 0
        # SO orders.status 일괄 갱신 — 보호 SO 제외
        if target_so:
            try:
                _r2 = c.execute(
                    f"""UPDATE orders SET status=?
                        WHERE project_id=?
                          AND COALESCE(status,'') NOT IN ({','.join('?'*len(PROTECTED_SO_STATUSES))})
                          AND COALESCE(status,'') != ?""",
                    (target_so, project_id, *PROTECTED_SO_STATUSES, target_so)
                )
                orders_changed = _r2.rowcount or 0
            except Exception:
                orders_changed = 0
        # 변경 이력 (요약 1줄)
        if (units_changed or orders_changed):
            try:
                from .database import log_project_change
                _detail = f"호기 {units_changed}건"
                if orders_changed:
                    _detail += f" · SO {orders_changed}건 ({target_so})"
                log_project_change(c, project_id, changed_by,
                                    "상태 cascade 동기화",
                                    "", new_status,
                                    note=_detail)
            except Exception:
                pass
    except Exception as e:
        print(f"[v5H226r] cascade err pid={project_id}: {e}")
    return {"units_changed": units_changed, "orders_changed": orders_changed,
            "target_unit": target_unit, "target_so": target_so}


def cascade_project_meta_to_so(c, project_id: int,
                                old_meta: dict, new_meta: dict,
                                changed_by: int | None = None) -> list[str]:
    """v5H226s — 프로젝트 메타필드(due_date/order_date/currency) 변경 시 자식 SO·호기 동기화.
    원칙: '변경 전 부모값과 동일했던 행만' cascade. override(다른 값 명시)된 행은 보존.
    INVOICED/PAID SO 는 제외 (수금 시작분 보존)."""
    PROTECTED = ("INVOICED", "PAID")
    summary: list[str] = []
    # 1) due_date cascade
    new_due = new_meta.get("due_date")
    old_due = old_meta.get("due_date")
    if new_due is not None and (new_due or "") != (old_due or ""):
        try:
            r1 = c.execute(
                f"""UPDATE orders SET due_date=?
                    WHERE project_id=?
                      AND COALESCE(status,'') NOT IN ({','.join('?'*len(PROTECTED))})
                      AND COALESCE(due_date,'') = COALESCE(?,'')""",
                (new_due, project_id, *PROTECTED, old_due or "")
            )
            n_so = r1.rowcount or 0
            r2 = c.execute(
                f"""UPDATE order_items SET due_date=?
                    WHERE order_id IN (
                        SELECT id FROM orders WHERE project_id=?
                          AND COALESCE(status,'') NOT IN ({','.join('?'*len(PROTECTED))})
                    )
                    AND (due_date IS NULL OR COALESCE(due_date,'') = COALESCE(?,''))""",
                (new_due, project_id, *PROTECTED, old_due or "")
            )
            n_it = r2.rowcount or 0
            if n_so or n_it:
                summary.append(f"납기일 SO {n_so}건·호기 {n_it}건")
        except Exception as e:
            print(f"[v5H226s] due cascade err pid={project_id}: {e}")
    # 2) order_date cascade
    new_ord = new_meta.get("order_date")
    old_ord = old_meta.get("order_date")
    if new_ord is not None and (new_ord or "") != (old_ord or ""):
        try:
            r1 = c.execute(
                f"""UPDATE orders SET order_date=?
                    WHERE project_id=?
                      AND COALESCE(status,'') NOT IN ({','.join('?'*len(PROTECTED))})
                      AND COALESCE(order_date,'') = COALESCE(?,'')""",
                (new_ord, project_id, *PROTECTED, old_ord or "")
            )
            n_so = r1.rowcount or 0
            r2 = c.execute(
                f"""UPDATE order_items SET order_date=?
                    WHERE order_id IN (
                        SELECT id FROM orders WHERE project_id=?
                          AND COALESCE(status,'') NOT IN ({','.join('?'*len(PROTECTED))})
                    )
                    AND (order_date IS NULL OR COALESCE(order_date,'') = COALESCE(?,''))""",
                (new_ord, project_id, *PROTECTED, old_ord or "")
            )
            n_it = r2.rowcount or 0
            if n_so or n_it:
                summary.append(f"발주일 SO {n_so}건·호기 {n_it}건")
        except Exception as e:
            print(f"[v5H226s] ord cascade err pid={project_id}: {e}")
    # 3) currency cascade — 수금 없는 SO 만 (v5H187 정책)
    new_ccy = new_meta.get("currency")
    old_ccy = old_meta.get("currency")
    if new_ccy and (new_ccy or "") != (old_ccy or ""):
        try:
            r1 = c.execute(
                """UPDATE orders SET currency=?
                   WHERE project_id=?
                     AND COALESCE(currency,'KRW') != ?
                     AND NOT EXISTS (SELECT 1 FROM receipts_payment rp WHERE rp.order_id = orders.id)""",
                (new_ccy, project_id, new_ccy)
            )
            n_so = r1.rowcount or 0
            r2 = c.execute(
                """UPDATE order_items SET currency=?
                   WHERE order_id IN (SELECT id FROM orders WHERE project_id=?)
                     AND COALESCE(currency,'') != ?""",
                (new_ccy, project_id, new_ccy)
            )
            n_it = r2.rowcount or 0
            if n_so or n_it:
                summary.append(f"통화 SO {n_so}건·호기 {n_it}건")
        except Exception as e:
            print(f"[v5H226s] ccy cascade err pid={project_id}: {e}")
    # 4) 변경 이력 (요약 1줄)
    if summary:
        try:
            from .database import log_project_change
            log_project_change(c, project_id, changed_by,
                                "메타 cascade 동기화", "", " · ".join(summary),
                                note="프로젝트 메타필드 변경 → 자식 동기화")
        except Exception:
            pass
    return summary


def sync_ship_stage_from_units(c, project_id: int, on_date: str = "",
                               by_user: int | None = None, by_name: str = "") -> bool:
    """v5H226z473 (대표 지시): 출하(작업일정표 단계 'ship') ⟷ 호기 출하 양방향 연결의 [상세→보드] 방향.
    활성 호기(취소 제외) '전체'가 출하면 보드 단계칸 'ship'(출하) 완료 기록.
    호기가 있는데 전체 출하가 아니면 자동 출하표시 해제(보드 일관성). 호기 0건이면 손대지 않음
    (보드 단건/일괄출하로 찍은 출하 보존). 데이터 연결성 안전원칙: '전체 출하' 단일조건일 때만 set."""
    from datetime import datetime as _dt, date as _date
    try:
        rows = c.execute(
            "SELECT COALESCE(oi.unit_status,'진행중') st, COUNT(*) n "
            "FROM order_items oi JOIN orders o ON o.id=oi.order_id "
            "WHERE o.project_id=? GROUP BY 1", (project_id,)).fetchall()
    except Exception:
        return False
    total = sum(int(r[1] or 0) for r in rows)
    if total == 0:
        return False   # 호기 0건 → 보드 출하 표시 유지(손대지 않음)
    cancel = sum(int(r[1] or 0) for r in rows if r[0] == '취소')
    done = sum(int(r[1] or 0) for r in rows if r[0] == '출하')
    active = total - cancel
    all_delivered = (active > 0 and done == active)
    now = _dt.now().isoformat(timespec="seconds")
    od = (on_date or _date.today().isoformat())
    try:
        if all_delivered:
            c.execute(
                """INSERT INTO project_stage_log
                   (ref_kind,ref_id,stage_key,sub_key,done,on_date,by_user,by_name,memo,extra,updated_at)
                   VALUES ('project',?, 'ship','',1,?,?,?,?, '', ?)
                   ON CONFLICT(ref_kind,ref_id,stage_key,sub_key) DO UPDATE SET
                     done=1,
                     on_date=COALESCE(NULLIF(on_date,''), excluded.on_date),
                     updated_at=excluded.updated_at""",
                (project_id, od, by_user, (by_name or "출하 연동"),
                 "호기 전체 출하 → 출하", now))
        else:
            # 호기 있는데 전체 출하 아님 → 자동 출하표시 해제(부분납품은 출하 아님)
            c.execute(
                "UPDATE project_stage_log SET done=0, updated_at=? "
                "WHERE ref_kind='project' AND ref_id=? AND stage_key='ship' AND sub_key=''",
                (now, project_id))
        return all_delivered
    except Exception as e:
        print(f"[v5H226z473] ship-sync err pid={project_id}: {e}")
        return False


def mark_units_delivered(c, project_id: int, changed_by: int | None = None) -> int:
    """v5H226z473 (대표 지시): 출하 처리 [보드→상세] 방향 — 활성 호기(취소·기납품 제외) 전체를 '출하'로.
    이어서 cascade_unit_status_to_project(프로젝트·SO 상태 동기화 + sync_ship_stage_from_units)까지 호출.
    반환=새로 출하로 바뀐 호기 수."""
    try:
        r = c.execute(
            "UPDATE order_items SET unit_status='출하' "
            "WHERE order_id IN (SELECT id FROM orders WHERE project_id=?) "
            "  AND COALESCE(unit_status,'진행중') NOT IN ('출하','취소')",
            (project_id,))
        n = r.rowcount or 0
    except Exception:
        n = 0
    try:
        cascade_unit_status_to_project(c, project_id, changed_by)
    except Exception:
        pass
    return n


def cascade_unit_status_to_project(c, project_id: int,
                                    changed_by: int | None = None) -> dict:
    """v5H226r/x — 호기 unit_status 변경 시 부모 프로젝트 status + SO orders.status 동기화.
    모든 호기가 동일 상태일 때만 부모 상태 변경. 혼합/0건이면 no-op.
    v5H226x: 4종 모두(진행중/출하/취소/보류) 매핑 + SO orders.status 도 함께 동기화.
    v5H226z571: 단계 시스템 제거 — 출하 단계 거울 동기화(sync_ship_stage_from_units) 폐지(상태 동기화만 유지)."""
    try:
        rows = c.execute(
            """SELECT COALESCE(oi.unit_status,'진행중') AS st
               FROM order_items oi
               JOIN orders o ON o.id = oi.order_id
               WHERE o.project_id=?""",
            (project_id,)
        ).fetchall()
    except Exception:
        return {"changed": False, "reason": "쿼리 오류"}
    if not rows:
        return {"changed": False, "reason": "호기 0건"}
    statuses = {r[0] for r in rows}
    # 모든 호기가 동일 상태일 때만 cascade
    if len(statuses) != 1:
        return {"changed": False, "reason": f"혼합 상태 ({len(statuses)}종)"}
    only = statuses.pop()
    # v5H226x: 호기 → 프로젝트 매핑 4종 모두
    UNIT_TO_PROJECT = {"진행중": "진행중", "출하": "출하",
                        "취소": "취소", "보류": "보류"}
    new_proj_status = UNIT_TO_PROJECT.get(only)
    if not new_proj_status:
        return {"changed": False, "reason": f"매핑 외 상태 ({only})"}
    try:
        cur = c.execute(
            "SELECT status FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        if not cur:
            return {"changed": False, "reason": "프로젝트 없음"}
        old_status = cur[0] or ""
        # v5H226x: SO orders.status 도 함께 cascade (재무 잠금 SO 제외)
        target_so = PROJECT_TO_SO_STATUS.get(new_proj_status)
        so_changed = 0
        if target_so:
            try:
                _r = c.execute(
                    f"""UPDATE orders SET status=?
                        WHERE project_id=?
                          AND COALESCE(status,'') NOT IN ({','.join('?'*len(PROTECTED_SO_STATUSES))})
                          AND COALESCE(status,'') != ?""",
                    (target_so, project_id, *PROTECTED_SO_STATUSES, target_so)
                )
                so_changed = _r.rowcount or 0
            except Exception:
                so_changed = 0
        # 프로젝트 status 가 동일하면 SO 만 갱신하고 종료
        if old_status == new_proj_status:
            return {"changed": (so_changed > 0), "reason": "프로젝트 동일 상태 (SO 만 동기화)",
                    "so_changed": so_changed}
        # stage 도 동기화 (status 와 동일 — v5H215 정책)
        c.execute(
            "UPDATE projects SET status=?, stage=? WHERE id=?",
            (new_proj_status, new_proj_status, project_id)
        )
        try:
            from .database import log_project_change
            log_project_change(c, project_id, changed_by,
                                "프로젝트 상태",
                                old_status, new_proj_status,
                                note=f"호기 전체 cascade (SO {so_changed}건)")
        except Exception:
            pass
        return {"changed": True, "old": old_status, "new": new_proj_status,
                "so_changed": so_changed}
    except Exception as e:
        print(f"[v5H226x] up-cascade err pid={project_id}: {e}")
        return {"changed": False, "reason": str(e)}
