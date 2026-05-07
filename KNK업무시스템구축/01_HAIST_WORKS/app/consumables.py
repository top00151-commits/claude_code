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


def generate_co_no(today=None) -> str:
    """CO-YYMMNN — 같은 달 내 일련번호 (NN, 01부터)."""
    d = today or datetime.now()
    ym = d.strftime("%y%m")
    pat = f"CO-{ym}%"
    with db_session() as c:
        rows = c.execute(
            "SELECT co_no FROM consumable_orders WHERE co_no LIKE ?", (pat,)
        ).fetchall()
    mx = 0
    for r in rows:
        no = (r[0] or "")
        try:
            n = int(no.split("-")[-1][4:])  # CO-YYMMNN → NN 부분
        except Exception:
            try:
                n = int(no[-2:])
            except Exception:
                n = 0
        if n > mx:
            mx = n
    return f"CO-{ym}{mx+1:02d}"


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
    # MODEL 단독은 우선순위 낮춤 (MODELUSE 가 못 잡혔을 때만)
    ("model_use",  ["MODEL"]),
]


def _norm(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s)).upper()


def detect_header(ws, max_scan_rows: int = 8) -> tuple[int, dict]:
    """헤더 row 자동 감지. (header_row, col_map) 반환.
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
                "error": "헤더를 찾지 못했습니다 (NO/MODEL/품명/수량 컬럼이 1~8행 안에 있어야 합니다)"}
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
        }
        lines.append(rec)
    # 이미지 추출 + 압축
    img_map: dict = {}
    if image_out_dir:
        os.makedirs(image_out_dir, exist_ok=True)
        try:
            for idx, img in enumerate(getattr(ws, "_images", []) or []):
                try:
                    a = img.anchor
                    row1 = a._from.row + 1   # 1-indexed
                    raw = img._data()
                    if not raw:
                        continue
                    # 가장 가까운 라인의 row 와 매칭 (anchor row 가 라인 row 와 정확히 같지 않을 수 있음)
                    matched_line = _find_nearest_line(lines, row1)
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
    return {"lines": lines, "images": img_map,
            "header_row": hdr_row, "col_map": col_map,
            "image_count": sum(len(v) for k, v in img_map.items() if isinstance(v, list) and k != "_errors")}


def _find_nearest_line(lines, anchor_row: int):
    """anchor_row 와 가장 가까운(<=) line.row 찾기. 없으면 가장 가까운 라인."""
    if not lines:
        return None
    candidates = [ln for ln in lines if ln["row"] <= anchor_row + 2]
    if candidates:
        return max(candidates, key=lambda ln: ln["row"])
    return min(lines, key=lambda ln: abs(ln["row"] - anchor_row))


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
    """parts.part_name 으로 LIKE 매칭. 신뢰도(level: exact/partial/none) 표시."""
    if not name or not str(name).strip():
        return None
    nm = str(name).strip()
    with db_session() as c:
        # 1. exact
        r = c.execute(
            "SELECT id, part_no, part_name, std_price, unit FROM parts "
            "WHERE part_name=? AND COALESCE(is_active,1)=1 LIMIT 1", (nm,)
        ).fetchone()
        if r:
            d = dict(r); d["match_level"] = "exact"; return d
        # 2. LIKE — 첫 단어
        first_word = nm.split()[0]
        r = c.execute(
            "SELECT id, part_no, part_name, std_price, unit FROM parts "
            "WHERE part_name LIKE ? AND COALESCE(is_active,1)=1 LIMIT 1",
            (f"%{first_word}%",)
        ).fetchone()
        if r:
            d = dict(r); d["match_level"] = "partial"; return d
    return None


def match_project_by_model(model_use: str) -> dict | None:
    """projects.model_name (또는 name) LIKE 매칭. NEW_EQUIP 만 후보."""
    if not model_use or not str(model_use).strip():
        return None
    mu = str(model_use).strip()
    # 첫 모델 토큰 (예: 'SM-A576B CTC AUTO' → 'SM-A576B')
    token = mu.split()[0]
    with db_session() as c:
        r = c.execute(
            "SELECT id, mgmt_code, name, model_name FROM projects "
            "WHERE COALESCE(project_type,'NEW_EQUIP')='NEW_EQUIP' "
            "  AND (model_name LIKE ? OR name LIKE ?) "
            "ORDER BY id DESC LIMIT 1",
            (f"%{token}%", f"%{token}%")
        ).fetchone()
        if r:
            d = dict(r); d["match_level"] = "model_token"; return d
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
    co_no = generate_co_no()
    try:
        from .database import generate_mgmt_code
        mgmt_code = generate_mgmt_code("S")
    except Exception:
        mgmt_code = None
    cust_id = None
    if customer_name:
        with db_session() as c:
            r = c.execute("SELECT id FROM customers WHERE name=? LIMIT 1",
                          (customer_name,)).fetchone()
            if r:
                cust_id = r[0]
    _bd = (biz_div or "").strip().upper()
    if _bd not in ("T", "M"):
        _bd = None  # 미선택 허용 (백워드 호환); UI 에서는 검증 강제
    with db_session() as c:
        cocols = {r2[1] for r2 in c.execute("PRAGMA table_info(consumable_orders)").fetchall()}
        # v5H218: biz_div 컬럼 동적 감지 — startup 마이그레이션이 추가한 후엔 always present
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
