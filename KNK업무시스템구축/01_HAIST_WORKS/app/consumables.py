"""
v5H142 (2026-05-05) — 소모품 발주 전용 도메인
대표 직접 요청: 신규 검사기와 분리 / 관리번호 발급 X / 엑셀 일괄 import + 이미지 자동 압축

핵심 헬퍼:
  - parse_consumable_xlsx(file_path)          : 엑셀 → 라인 list + 이미지 매칭
  - compress_image_bytes(raw, max_dim, quality): bytes → (압축본 bytes, 썸네일 bytes)
  - generate_co_no()                           : CO-YYMMNN 자동 채번
  - match_part_by_name(name)                   : 자재 마스터 LIKE 매칭
  - match_project_by_model(model_use)          : projects.model_name LIKE 매칭
  - co_create / coi_bulk_insert / co_get / coi_list / coi_update / coi_delete
  - recompute_co_total(co_id)
"""
from __future__ import annotations
from io import BytesIO
from datetime import datetime
import os, re, json, shutil

from .database import db_session

# ────────────────────────────────────────────────────────────────────
# 채번 / 상태
# ────────────────────────────────────────────────────────────────────
CO_STATUSES = ["DRAFT", "QUOTED", "CONFIRMED", "SHIPPED", "PAID", "CANCELLED"]
CO_STATUS_LABELS = {
    "DRAFT": "작성중",
    "QUOTED": "견적완료",
    "CONFIRMED": "발주확정",
    "SHIPPED": "납품완료",
    "PAID": "수금완료",
    "CANCELLED": "취소",
}


def generate_co_no(biz_div: str = "M", today=None) -> str:
    """v5H226z248 (대표 지시): 소모품 발주번호 = 기존 수주번호와 동일 형식 [사업부]-[YYMMDD].
    같은 날 첫 건은 접미 없음, 두 번째부터 -1, -2 순차. (예: M-260602, M-260602-1)
    수주번호(orders.order_no)와 충돌 방지를 위해 orders + consumable_orders 양쪽을 스캔."""
    bd = (biz_div or "M").strip().upper()
    if bd not in ("T", "M", "L"):
        bd = "M"
    d = today or datetime.now()
    yymmdd = d.strftime("%y%m%d")
    base = f"{bd}-{yymmdd}"
    nums = []
    with db_session() as c:
        for tbl, col in (("orders", "order_no"), ("consumable_orders", "co_no")):
            try:
                for r in c.execute(
                    f"SELECT {col} FROM {tbl} WHERE {col}=? OR {col} LIKE ?",
                    (base, base + "-%")
                ):
                    if r[0]:
                        nums.append(r[0])
            except Exception:
                pass
    if not nums:
        return base  # 같은 날 첫 건 → 접미 없음
    max_n = 0
    for on in nums:
        if on == base:
            continue
        m = re.match(rf"^{re.escape(base)}-(\d+)$", on)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"{base}-{max_n + 1}"


# ────────────────────────────────────────────────────────────────────
# 엑셀 파싱 — 헤더 자동 감지 + 라인 + 이미지
# ────────────────────────────────────────────────────────────────────
# 헤더 매칭 — 우선순위 순서로 평가 (먼저 매칭된 컬럼은 다른 키에 양보)
# 더 구체적인 키워드(ORDER DATE)를 더 일반적인 것(QTY) 보다 먼저 둠
HEADER_KEYS = [
    ("order_date", ["ORDERDATE", "발주일", "요청일"]),
    ("part_name",  ["SUPPLIERNAME", "품명", "PARTNAME", "ITEMNAME"]),
    ("model_use",  ["MODELUSE", "모델"]),
    ("qty",        ["Q'TY", "QTY", "수량", "QUANTITY"]),
    ("unit",       ["UNIT", "단위"]),
    ("no",         ["NO", "번호", "순번"]),
    ("supplier",   ["업체", "VENDOR"]),
    ("spec",       ["SPEC", "규격", "BOM"]),
    # v5H226z285: 단가·금액 (머리글이 '단가 (KRW)' 처럼 통화 포함 수식이어도 '단가'/'금액'으로 인식)
    ("price",      ["단가", "UNITPRICE"]),
    ("amount",     ["금액", "AMOUNT"]),
    # MODEL 단독은 우선순위 낮춤 (MODELUSE 가 못 잡혔을 때만)
    ("model_use",  ["MODEL"]),
]

# v5H226z285: 통화 화이트리스트 + 정규화 (정보란 '통화' 값/머리글 '(KRW)' 에서 추출)
_CCY_WHITELIST = {"KRW", "USD", "VND", "JPY", "CNY", "EUR"}
_CCY_ALIAS = {"₩": "KRW", "원": "KRW", "$": "USD", "달러": "USD", "USD": "USD",
              "₫": "VND", "동": "VND", "¥": "JPY", "엔": "JPY", "JPY": "JPY",
              "€": "EUR", "유로": "EUR", "위안": "CNY", "CNY": "CNY", "RMB": "CNY"}


def _norm_ccy(v):
    """통화 표기 → 코드(KRW 등). 못 알아보면 None."""
    if v is None:
        return None
    s = str(v).strip().upper()
    if s in _CCY_WHITELIST:
        return s
    if s in _CCY_ALIAS:
        return _CCY_ALIAS[s]
    m = re.search(r"[A-Z]{3}", s)
    if m and m.group(0) in _CCY_WHITELIST:
        return m.group(0)
    for k, code in _CCY_ALIAS.items():
        if k in s:
            return code
    return None


def _right_value(ws, r, c, maxc):
    """(r,c) 오른쪽으로 첫 '비어있지 않은' 셀 값 (라벨 옆 값 읽기)."""
    for cc in range(c + 1, maxc + 1):
        v = ws.cell(r, cc).value
        if v is not None and str(v).strip() != "":
            return v
    return None


def read_order_meta(ws, header_row, col_map=None):
    """헤더 위 정보란에서 주문 단위 정보(통화·거래구분) 읽기 — 라벨 기반(셀 위치 무관).
    통화: '통화' 라벨 옆 값 → 코드. 못 찾으면 단가/금액 머리글 '단가 (KRW)' 괄호에서 보조 추출.
    거래구분: '거래구분' 라벨 옆 값에 '수출' 포함 시 is_export=1, 아니면 0."""
    meta = {"currency": None, "is_export": None}
    maxc = min(ws.max_column, 30)
    for r in range(1, max(1, header_row)):
        for c in range(1, maxc + 1):
            v = ws.cell(r, c).value
            if v is None:
                continue
            t = str(v).strip()
            tn = re.sub(r"\s+", "", t).upper()
            if meta["currency"] is None and tn in ("통화", "CURRENCY", "통화구분"):
                cc = _norm_ccy(_right_value(ws, r, c, maxc))
                if cc:
                    meta["currency"] = cc
            elif meta["is_export"] is None and "거래구분" in t:
                rv = _right_value(ws, r, c, maxc)
                if rv is not None:
                    s = str(rv)
                    meta["is_export"] = 1 if ("수출" in s or "EXPORT" in s.upper()) else 0
    # 보조: 단가/금액 머리글의 '(KRW)' 에서 통화 추출
    if meta["currency"] is None and col_map:
        for key in ("price", "amount"):
            if key in col_map:
                cc = _norm_ccy(ws.cell(header_row, col_map[key]).value)
                if cc:
                    meta["currency"] = cc
                    break
    return meta


def _norm(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s)).upper()


def detect_header(ws, max_scan_rows: int = 16) -> tuple[int, dict]:
    """헤더 row 자동 감지. (header_row, col_map) 반환.
    v5H226z283/z285: KNK 표준 양식은 정보란(통화·거래구분 추가로 확장) 아래에 헤더 → 스캔 16행.
    '가장 키 많은 행'을 헤더로 택하므로 상단 라벨(발주일·모델명 메모 등)에 오탐하지 않음.
    col_map = {'no': col_idx, 'part_name': col_idx, ...}  (1-indexed col).
    한 컬럼은 1개 키에만 매핑 (충돌 방지)."""
    best_row = 0
    best_map: dict = {}
    for r in range(1, min(max_scan_rows, ws.max_row) + 1):
        cur_map: dict = {}
        used_cols: set = set()
        for c in range(1, min(ws.max_column, 30) + 1):
            v = _norm(ws.cell(r, c).value)
            if not v:
                continue
            for key, kws in HEADER_KEYS:
                if key in cur_map:
                    continue
                if c in used_cols:
                    continue
                for kw in kws:
                    if _norm(kw) in v:
                        cur_map[key] = c
                        used_cols.add(c)
                        break
        if "part_name" in cur_map and ("qty" in cur_map or "model_use" in cur_map):
            if len(cur_map) > len(best_map):
                best_row = r
                best_map = cur_map
    return best_row, best_map


def parse_consumable_xlsx(file_path: str, image_out_dir: str | None = None) -> dict:
    """엑셀 파싱 → {'lines': [...], 'images': {row:[paths]}, 'header_row': N, 'col_map': {...}}.
    image_out_dir 가 주어지면 이미지 추출 후 압축본/썸네일 저장."""
    from openpyxl import load_workbook
    wb = load_workbook(file_path, data_only=True)
    ws = wb.worksheets[0]
    hdr_row, col_map = detect_header(ws)
    lines = []
    if hdr_row == 0 or "part_name" not in col_map:
        return {"lines": [], "images": {}, "header_row": 0, "col_map": {},
                "error": "헤더를 찾지 못했습니다 (NO/MODEL/품명/수량 컬럼이 1~16행 안에 있어야 합니다)"}
    pn_col = col_map["part_name"]
    line_no_seq = 0
    for r in range(hdr_row + 1, ws.max_row + 1):
        pn = ws.cell(r, pn_col).value
        if pn is None or str(pn).strip() == "":
            continue
        line_no_seq += 1
        rec = {
            "row": r,                                           # 엑셀 row (이미지 매칭 키)
            "line_no": line_no_seq,
            "model_use": str(ws.cell(r, col_map["model_use"]).value or "").strip() if "model_use" in col_map else "",
            "part_name": str(pn).strip(),
            "spec":      str(ws.cell(r, col_map["spec"]).value or "").strip() if "spec" in col_map else "",
            "qty":       _to_num(ws.cell(r, col_map["qty"]).value) if "qty" in col_map else 0,
            "unit":      str(ws.cell(r, col_map["unit"]).value or "EA").strip() if "unit" in col_map else "EA",
            "order_date": _date_str(ws.cell(r, col_map["order_date"]).value) if "order_date" in col_map else "",
            "unit_price": _to_num(ws.cell(r, col_map["price"]).value) if "price" in col_map else 0,
            "amount":     _to_num(ws.cell(r, col_map["amount"]).value) if "amount" in col_map else 0,
        }
        # v5H226z285: 금액 비고 단가·수량 있으면 금액=단가×수량 (수식 캐시 없을 때 보강)
        if not rec["amount"] and rec.get("unit_price") and rec.get("qty"):
            rec["amount"] = rec["unit_price"] * rec["qty"]
        lines.append(rec)
    # 이미지 추출 + 압축
    img_map: dict = {}
    if image_out_dir:
        os.makedirs(image_out_dir, exist_ok=True)
        # v5H226z284 (대표 지시): 행 높이 누적(EMU)으로 이미지 세로 '중심'이 속한 데이터 행에 매칭.
        #   셀 크기·병합·붙인 위치가 달라도 '보이는 위치' 그대로 연결(기존 '앵커행+2'는 전 사진이 2줄 밀렸음).
        _ymax = ws.max_row
        for _im in (getattr(ws, "_images", []) or []):
            _t = getattr(_im.anchor, "to", None) or getattr(_im.anchor, "_to", None)
            if _t is not None and getattr(_t, "row", None) is not None and (_t.row + 3) > _ymax:
                _ymax = _t.row + 3
        _P = _row_y_prefix(ws, _ymax)
        try:
            for idx, img in enumerate(getattr(ws, "_images", []) or []):
                try:
                    a = img.anchor
                    raw = img._data()
                    if not raw:
                        continue
                    # 이미지 세로 중심 → 해당 데이터 행. 못 구하면(절대앵커 등) 앵커 상단 행 최근접 폴백.
                    _cy = _image_center_y(a, _P)
                    matched_line = (_line_for_center(lines, _cy, _P) if _cy is not None
                                    else _find_nearest_line(lines, getattr(getattr(a, "_from", None), "row", 0) + 1))
                    if matched_line is None:
                        continue
                    fn = f"line_{matched_line['line_no']:03d}_{idx+1}.jpg"
                    fn_thumb = f"line_{matched_line['line_no']:03d}_{idx+1}_thumb.jpg"
                    full = os.path.join(image_out_dir, fn)
                    thumb = os.path.join(image_out_dir, fn_thumb)
                    big_bytes, thumb_bytes, info = compress_image_bytes(raw)
                    with open(full, "wb") as f:
                        f.write(big_bytes)
                    with open(thumb, "wb") as f:
                        f.write(thumb_bytes)
                    img_map.setdefault(matched_line["line_no"], []).append({
                        "full": fn, "thumb": fn_thumb,
                        "orig_size": len(raw), "compressed": len(big_bytes),
                        "info": info,
                    })
                except Exception as e:
                    img_map.setdefault("_errors", []).append(f"img{idx}: {e}")
        except Exception as e:
            img_map["_errors"] = [str(e)]
    meta = read_order_meta(ws, hdr_row, col_map)   # v5H226z285: 통화·거래구분
    return {"lines": lines, "images": img_map,
            "header_row": hdr_row, "col_map": col_map, "meta": meta,
            "image_count": sum(len(v) for k, v in img_map.items() if isinstance(v, list) and k != "_errors")}


def _find_nearest_line(lines, anchor_row: int):
    """anchor_row 와 가장 가까운(<=) line.row 찾기. 없으면 가장 가까운 라인. (절대앵커 폴백용)"""
    if not lines:
        return None
    candidates = [ln for ln in lines if ln["row"] <= anchor_row + 2]
    if candidates:
        return max(candidates, key=lambda ln: ln["row"])
    return min(lines, key=lambda ln: abs(ln["row"] - anchor_row))


# ── v5H226z284: 이미지 기하학적 매칭(행 높이 기반) — 셀 크기·병합·오프셋 무관 ──
def _row_y_prefix(ws, max_row: int) -> list:
    """행별 세로 위치 누적(EMU). P[r] = 1..r행 높이 합(기본 15pt).
    이미지 앵커의 row(0-index)+rowOff(EMU)로 절대 Y좌표를 계산하는 데 사용."""
    DEFAULT_PT = 15.0
    EMU_PER_PT = 12700.0
    n = max(1, int(max_row)) + 2
    P = [0.0] * (n + 1)
    for r in range(1, n + 1):
        try:
            h = ws.row_dimensions[r].height
        except Exception:
            h = None
        P[r] = P[r - 1] + (h if h else DEFAULT_PT) * EMU_PER_PT
    return P


def _image_center_y(anchor, P):
    """이미지의 세로 '중심' Y(EMU). TwoCellAnchor=from~to 중점,
    OneCellAnchor=from + 높이/2. 계산 불가 시 None."""
    frm = getattr(anchor, "_from", None)
    if frm is None or getattr(frm, "row", None) is None or frm.row + 1 >= len(P):
        return None
    top = P[frm.row] + (getattr(frm, "rowOff", 0) or 0)
    to = getattr(anchor, "to", None) or getattr(anchor, "_to", None)
    if to is not None and getattr(to, "row", None) is not None and to.row + 1 < len(P):
        bot = P[to.row] + (getattr(to, "rowOff", 0) or 0)
    else:
        ext = getattr(anchor, "ext", None)
        cy = getattr(ext, "height", 0) if ext is not None else 0
        bot = top + (cy or 0)
    return (top + bot) / 2.0


def _line_for_center(lines, center_y, P):
    """center_y(EMU)가 속한 데이터 행의 라인. 구간 밖이면 행 밴드 중심 최근접."""
    if not lines or center_y is None:
        return None
    for ln in lines:
        R = ln["row"]
        if R < len(P) and P[R - 1] <= center_y < P[R]:
            return ln
    def _mid(ln):
        R = ln["row"]
        return (P[R - 1] + P[R]) / 2.0 if R < len(P) else P[-1]
    return min(lines, key=lambda ln: abs(_mid(ln) - center_y))


def _to_num(v):
    if v is None:
        return 0
    try:
        return float(v)
    except (TypeError, ValueError):
        try:
            return float(str(v).replace(",", "").strip())
        except Exception:
            return 0


def _date_str(v):
    if v is None:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()


# ────────────────────────────────────────────────────────────────────
# 이미지 압축 (Pillow)
# ────────────────────────────────────────────────────────────────────
def compress_image_bytes(raw: bytes, max_dim: int = 1920, quality: int = 85,
                          thumb_dim: int = 240) -> tuple[bytes, bytes, dict]:
    """원본 bytes → (압축본 jpeg bytes, 썸네일 jpeg bytes, info dict)
    화질 유지 + 용량 최소화 절충: 긴변 1920px JPEG q=85 progressive."""
    from PIL import Image, ImageOps
    im = Image.open(BytesIO(raw))
    im = ImageOps.exif_transpose(im)
    orig_size = im.size
    if im.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    elif im.mode == "P":
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    # 풀사이즈
    big = im.copy()
    if max(big.size) > max_dim:
        ratio = max_dim / max(big.size)
        big = big.resize((max(1, int(big.size[0] * ratio)),
                          max(1, int(big.size[1] * ratio))), Image.LANCZOS)
    out_big = BytesIO()
    big.save(out_big, "JPEG", quality=quality, optimize=True, progressive=True)
    big_bytes = out_big.getvalue()
    # 썸네일
    thumb = im.copy()
    thumb.thumbnail((thumb_dim, thumb_dim), Image.LANCZOS)
    out_thumb = BytesIO()
    thumb.save(out_thumb, "JPEG", quality=78, optimize=True)
    thumb_bytes = out_thumb.getvalue()
    info = {
        "orig_dim": orig_size,
        "compressed_dim": big.size,
        "thumb_dim": thumb.size,
    }
    return big_bytes, thumb_bytes, info


# ────────────────────────────────────────────────────────────────────
# 자동 매칭
# ────────────────────────────────────────────────────────────────────
def match_part_by_name(name: str) -> dict | None:
    """parts.part_name 정확일치(+공백/대소문자 정규화)만 자동연결.
    v5H226z262 (대표 지시·연결성 감사): 근본원인 = '첫 단어 LIKE'가 고객사·규격 스코프 없이
      흔한 토큰('CABLE'/'SCREW'/'M3')으로 '아무 자재 1건'에 part_id 를 조용히 붙이던 것.
      재발방지 원칙: **자동연결은 명확한 단일 후보(정확일치)일 때만**. 애매하면 연결하지 않고
      미매칭으로 둬 사용자가 수동 연결하게 한다. (틀린 연결보다 미연결이 안전)
    """
    if not name or not str(name).strip():
        return None
    nm = str(name).strip()
    # 정규화 키(앞뒤·중복 공백 제거 + 대문자) — '동일 품명'의 표기차만 흡수, 다른 품목은 매칭 안 함
    import re as _re_p
    nm_key = _re_p.sub(r"\s+", " ", nm).strip().upper()
    with db_session() as c:
        rows = c.execute(
            "SELECT id, part_no, part_name, std_price, unit FROM parts "
            "WHERE UPPER(TRIM(part_name))=? AND COALESCE(is_active,1)=1", (nm_key,)
        ).fetchall()
        # 정확일치가 '정확히 1건'일 때만 자동연결 (동명 자재 2건 이상이면 애매 → 미매칭)
        if len(rows) == 1:
            d = dict(rows[0]); d["match_level"] = "exact"; return d
    return None


def match_project_by_model(model_use: str, customer_id: int | None = None) -> dict | None:
    """projects.model_name (또는 name) 토큰 매칭. NEW_EQUIP 만 후보.
    v5H226z252: '같은 고객사'로 스코프 — 다른 회사 모델로 오연결되던 문제 수정.
    v5H226z262 (대표 지시·연결성 감사): 근본원인 = 같은 고객사가 동일 모델을 여러 호기 보유하면
      'ORDER BY id DESC'가 무조건 '가장 최근 등록 호기'에 붙이던 것(실제 어느 호기용인지 무관).
      재발방지 원칙: **후보가 정확히 1건일 때만 자동연결**. 2건 이상(애매)이면 연결하지 않고
      미매칭으로 둬 사용자가 어느 호기인지 직접 고르게 한다.
      · customer_id 없으면 자동연결 안 함 / 토큰 2자 미만 매칭 안 함(과매칭 방지)
    """
    if not model_use or not str(model_use).strip():
        return None
    if not customer_id:
        return None  # 고객사 모르면 자동연결 안 함(오연결 방지) → 수동 연결 버튼 사용
    mu = str(model_use).strip()
    # 첫 모델 토큰 (예: 'SM-A576B CTC AUTO' → 'SM-A576B')
    token = mu.split()[0].strip()
    if len(token) < 2:
        return None
    with db_session() as c:
        # 같은 고객사·같은 토큰 후보를 2건까지 조회 → 정확히 1건일 때만 연결(애매하면 보류)
        rows = c.execute(
            "SELECT id, mgmt_code, name, model_name FROM projects "
            "WHERE COALESCE(project_type,'NEW_EQUIP')='NEW_EQUIP' "
            "  AND customer_id = ? "
            "  AND (model_name LIKE ? OR name LIKE ?) "
            "ORDER BY id DESC LIMIT 2",
            (customer_id, f"%{token}%", f"%{token}%")
        ).fetchall()
        if len(rows) == 1:
            d = dict(rows[0]); d["match_level"] = "model_token"; return d
        # len==0 → 미매칭 / len>=2 → 애매(여러 호기) → 자동연결 보류(수동 연결 유도)
    return None


# ────────────────────────────────────────────────────────────────────
# CRUD
# ────────────────────────────────────────────────────────────────────
def co_create(customer_name: str = "", biz_div: str = "",
              order_date: str = "", due_date: str = "",
              currency: str = "KRW", note: str = "", source_file: str = "",
              created_by: int | None = None) -> tuple[int, str]:
    """v5H216: 소모품 묶음 생성 시 'S' prefix 관리번호 자동 발급.
    v5H218: biz_div(T/M) 추가 — 진행 사업부 별 매출 집계용."""
    # v5H226z248: 발주번호 = 수주번호 형식 [사업부]-[YYMMDD]. 날짜는 발주일 기준(수주번호 관례).
    _co_ref = None
    try:
        if order_date:
            _co_ref = datetime.strptime(str(order_date)[:10], "%Y-%m-%d")
    except Exception:
        _co_ref = None
    # 고객사·사업부는 1회 계산 (재시도와 무관)
    cust_id = None
    if customer_name:
        with db_session() as c:
            r = c.execute("SELECT id FROM customers WHERE name=? LIMIT 1",
                          (customer_name,)).fetchone()
            if r:
                cust_id = r[0]
    _bd = (biz_div or "").strip().upper()
    if _bd not in ("T", "M", "L"):
        _bd = None  # 미선택 허용 (백워드 호환); UI 에서는 검증 강제
    # v5H226z262 (대표 지시·연결성 감사): co_no/mgmt_code UNIQUE 충돌(동시 업로드 race) 시
    #   재발급 후 재시도. 부분 UNIQUE 인덱스(uq_consumable_co_no/mgmt)가 충돌을 IntegrityError 로
    #   드러내면, generate_* 가 (직전에 커밋된 경쟁 행을 보고) 다음 번호를 발급 → 충돌 해소.
    import sqlite3 as _sqlite
    _last_err = None
    for _attempt in range(6):
        co_no = generate_co_no(biz_div, _co_ref)
        # v5H226z244: 소모품 묶음 생성(업로드) 즉시 C 관리코드 부여 — 프로젝트 C소모품 경로와 동일 체계.
        try:
            from .database import generate_mgmt_code
            mgmt_code = generate_mgmt_code("C")
        except Exception:
            mgmt_code = None
        try:
            with db_session() as c:
                cocols = {r2[1] for r2 in c.execute("PRAGMA table_info(consumable_orders)").fetchall()}
                _has_mgmt = "mgmt_code" in cocols
                _has_biz = "biz_div" in cocols
                if _has_mgmt and _has_biz:
                    cur = c.execute(
                        """INSERT INTO consumable_orders
                           (co_no, mgmt_code, biz_div, customer_id, customer_name, order_date, due_date,
                            currency, note, source_file, created_by)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (co_no, mgmt_code, _bd, cust_id, customer_name, order_date or "", due_date or "",
                         (currency or "KRW").upper(), note or "", source_file or "",
                         created_by)
                    )
                elif _has_mgmt:
                    cur = c.execute(
                        """INSERT INTO consumable_orders
                           (co_no, mgmt_code, customer_id, customer_name, order_date, due_date,
                            currency, note, source_file, created_by)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (co_no, mgmt_code, cust_id, customer_name, order_date or "", due_date or "",
                         (currency or "KRW").upper(), note or "", source_file or "",
                         created_by)
                    )
                else:
                    cur = c.execute(
                        """INSERT INTO consumable_orders
                           (co_no, customer_id, customer_name, order_date, due_date,
                            currency, note, source_file, created_by)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (co_no, cust_id, customer_name, order_date or "", due_date or "",
                         (currency or "KRW").upper(), note or "", source_file or "",
                         created_by)
                    )
                return int(cur.lastrowid), co_no
        except _sqlite.IntegrityError as _ie:
            _last_err = _ie  # co_no/mgmt_code UNIQUE 충돌 → 재발급 후 재시도
            continue
    raise RuntimeError(f"소모품 수주번호/관리코드 발급 충돌 — 재시도 초과: {_last_err}")


def coi_bulk_insert(co_id: int, items: list[dict]) -> int:
    """라인 일괄 INSERT. items: [{line_no, model_use, part_name, spec, qty, unit,
                                  unit_price, part_id, linked_project_id,
                                  image_path, image_thumb_path, note}, ...]"""
    n = 0
    with db_session() as c:
        for it in items:
            qty = float(it.get("qty") or 0)
            up = float(it.get("unit_price") or 0)
            amt = round(qty * up, 2)
            c.execute(
                """INSERT INTO consumable_order_items
                   (co_id, line_no, model_use, part_id, part_name, spec,
                    qty, unit, unit_price, amount,
                    linked_project_id, note, image_path, image_thumb_path)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (int(co_id), int(it.get("line_no") or 0),
                 (it.get("model_use") or "").strip(),
                 (int(it["part_id"]) if it.get("part_id") else None),
                 (it.get("part_name") or "").strip(),
                 (it.get("spec") or "").strip(),
                 qty, (it.get("unit") or "EA").strip(),
                 up, amt,
                 (int(it["linked_project_id"]) if it.get("linked_project_id") else None),
                 (it.get("note") or "").strip(),
                 (it.get("image_path") or None),
                 (it.get("image_thumb_path") or None))
            )
            n += 1
    recompute_co_total(co_id)
    return n


def recompute_co_total(co_id: int) -> float:
    with db_session() as c:
        row = c.execute(
            "SELECT COALESCE(SUM(amount),0) FROM consumable_order_items WHERE co_id=?",
            (int(co_id),)
        ).fetchone()
        total = float(row[0] or 0)
        c.execute("UPDATE consumable_orders SET total_amount=? WHERE id=?",
                  (total, int(co_id)))
    return total


def co_get(co_id: int) -> dict | None:
    with db_session() as c:
        r = c.execute(
            "SELECT * FROM consumable_orders WHERE id=?", (int(co_id),)
        ).fetchone()
        return dict(r) if r else None


def co_list(status: str = "", q: str = "", limit: int = 200) -> list[dict]:
    sql = "SELECT * FROM consumable_orders WHERE 1=1"
    params: list = []
    if status and status in CO_STATUSES:
        sql += " AND status=?"; params.append(status)
    if q:
        sql += " AND (co_no LIKE ? OR customer_name LIKE ? OR note LIKE ?)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    sql += " ORDER BY id DESC LIMIT ?"; params.append(int(limit))
    with db_session() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def coi_list(co_id: int) -> list[dict]:
    with db_session() as c:
        rows = c.execute(
            """SELECT i.*,
                      p.mgmt_code AS linked_mgmt_code,
                      p.name      AS linked_project_name,
                      pa.part_no  AS part_no
                 FROM consumable_order_items i
            LEFT JOIN projects p  ON p.id  = i.linked_project_id
            LEFT JOIN parts    pa ON pa.id = i.part_id
                WHERE i.co_id=?
             ORDER BY i.line_no, i.id""",
            (int(co_id),)
        ).fetchall()
        return [dict(r) for r in rows]


def coi_update(item_id: int, fields: dict) -> None:
    """라인 인라인 편집 — fields 의 키만 갱신."""
    allowed = {"model_use", "part_name", "spec", "qty", "unit",
               "unit_price", "linked_project_id", "part_id", "note"}
    keys = [k for k in fields.keys() if k in allowed]
    if not keys:
        return
    sets = ", ".join(f"{k}=?" for k in keys)
    vals = [fields[k] for k in keys]
    vals.append(int(item_id))
    with db_session() as c:
        c.execute(f"UPDATE consumable_order_items SET {sets} WHERE id=?", vals)
        # amount 재계산
        c.execute(
            "UPDATE consumable_order_items SET amount=ROUND(COALESCE(qty,0)*COALESCE(unit_price,0),2) WHERE id=?",
            (int(item_id),)
        )
        # 헤더 합계
        row = c.execute(
            "SELECT co_id FROM consumable_order_items WHERE id=?", (int(item_id),)
        ).fetchone()
        if row:
            co_id = row[0]
    if row:
        recompute_co_total(co_id)


def coi_delete(item_id: int) -> None:
    with db_session() as c:
        row = c.execute(
            "SELECT co_id, image_path, image_thumb_path FROM consumable_order_items WHERE id=?",
            (int(item_id),)
        ).fetchone()
        if not row:
            return
        c.execute("DELETE FROM consumable_order_items WHERE id=?", (int(item_id),))
    recompute_co_total(row[0])


def co_delete(co_id: int) -> None:
    """헤더 + 라인 + 이미지 디렉토리 일괄 삭제."""
    with db_session() as c:
        c.execute("DELETE FROM consumable_orders WHERE id=?", (int(co_id),))
    # 이미지 폴더 삭제
    img_dir = co_image_dir(co_id)
    if os.path.isdir(img_dir):
        try:
            shutil.rmtree(img_dir, ignore_errors=True)
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────
# 경로 헬퍼
# ────────────────────────────────────────────────────────────────────
def _uploads_root() -> str:
    """01_HAIST_WORKS/uploads/consumables/"""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, "..", "uploads", "consumables"))
    os.makedirs(root, exist_ok=True)
    return root


def co_image_dir(co_id: int) -> str:
    p = os.path.join(_uploads_root(), str(int(co_id)))
    os.makedirs(p, exist_ok=True)
    return p


def co_image_url(co_id: int, fname: str) -> str:
    """브라우저에서 접근할 URL — /uploads/consumables/{co_id}/{fname}"""
    return f"/uploads/consumables/{int(co_id)}/{fname}"


# ────────────────────────────────────────────────────────────────────
# 프로젝트별 소모품 이력 (project_detail 통합)
# ────────────────────────────────────────────────────────────────────
def get_project_consumable_orders(project_id: int, limit: int = 200) -> dict:
    """프로젝트(장비) 1건에 연결된 consumable_order_items + 합계."""
    with db_session() as c:
        rows = c.execute(
            """SELECT i.id, i.line_no, i.model_use, i.part_name, i.spec,
                      i.qty, i.unit, i.unit_price, i.amount,
                      i.image_thumb_path, i.image_path,
                      co.id   AS co_id,
                      co.co_no, co.order_date, co.customer_name,
                      co.status AS co_status, co.currency
                 FROM consumable_order_items i
                 JOIN consumable_orders co ON co.id = i.co_id
                WHERE i.linked_project_id=?
             ORDER BY co.order_date DESC, co.id DESC, i.line_no
                LIMIT ?""",
            (int(project_id), int(limit))
        ).fetchall()
    out = [dict(r) for r in rows]
    total_amt = sum(float(r["amount"] or 0) for r in out)
    total_qty = sum(float(r["qty"] or 0) for r in out)
    return {"rows": out, "total_amount": round(total_amt, 2),
            "total_qty": round(total_qty, 4), "count": len(out)}
