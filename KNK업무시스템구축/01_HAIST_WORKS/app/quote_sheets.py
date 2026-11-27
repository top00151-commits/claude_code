# -*- coding: utf-8 -*-
"""z1191z121 (대표 11-23 「견적서를 등록하는 이유는 향후 고객사가 비슷한 걸 요구했을 때 최종이 어떤 거였는지 확인 · 견적서 내 상세 항목들도 확인」)
견적서 엑셀 → 웍스 안에서 보고 찾을 수 있는 모양으로 읽기(AI 없이 · 엑셀 칸 그대로).

  read_book(raw) → {
    "ok": True/False, "message": "...",
    "fronts": [ {sheet, filled, meta{견적일·업체명·담당자·품명}, items[...], header[...] } ... ],   # 앞장(견적서 표지) 후보
    "front": 최종 앞장 번호(후보가 하나면 그것 · 채워진 게 여럿이면 None → 올릴 때 고름),
    "sheets": [ {title, internal, hidden_cols[...], rows[[...]], applied[줄번호...]} ... ],      # 시트 전부(보기용)
  }
  search_rows(book, can_cost) → [(시트, 줄번호, 글)]  # 찾기용 글(원가 칸·시트는 권한 있을 때만)

  - 회사 기본 양식(KNK 10-01-01): 머리(견적일·업체명·담당자·품명) + 항목 표(No.·품명·규격·수량·단가·금액)
  - 검사기 「세부항목」 선택표: 수량이 있는 줄만 「적용 항목」(applied)
  - 회사 안에서만 볼 것(internal): 숨긴 시트·숨긴 열 · 이름에 원가·NEGO·마진·산출 · 머리에 원가·NEGO·마진 인 열
    → 매입가 볼 권한(purchase_price)이 있는 사람만 화면·찾기에 보인다
  - 비밀번호 걸린 파일은 여기 오기 전에 풀어서 준다(비밀번호는 저장하지 않음 — z1191z62 와 같음)
"""
import io, re, datetime

MAX_ROWS = 3000
MAX_COLS = 80

_LBL = {
    "qdate": re.compile(r"^견\s*적\s*(일|일자)\s*:?\s*$"),
    "customer": re.compile(r"^업\s*체\s*명\s*:?\s*$"),
    "contact": re.compile(r"^담\s*당\s*자\s*:?\s*$"),
    "title": re.compile(r"^품\s*명\s*:?\s*$"),
}
# 값 자리에 오면 안 되는 「다른 머리 글」(공급자 칸 등)
_NOT_VAL = re.compile(r"^(:|사업장.*|업\s*태|전\s*화|TEL|FAX|등\s*록\s*번\s*호|상\s*호.*|대\s*표|종\s*목|모델명|공|급|자)\s*:?$", re.I)
_HDR = {
    "no": re.compile(r"^(no\.?|번호|순번)$", re.I),
    "name": re.compile(r"품\s*명|부\s*품\s*명|원가\s*요소|항\s*목"),
    "spec": re.compile(r"규\s*격|상세\s*요소"),
    "qty": re.compile(r"^수\s*량$"),
    "unit_price": re.compile(r"단\s*가"),
    "amount": re.compile(r"금\s*액"),
    "note": re.compile(r"비\s*고|특이\s*사항"),
}
_INTERNAL_SHEET = re.compile(r"원가|NEGO|마진|산출|내부", re.I)
_INTERNAL_COL = re.compile(r"^\s*원\s*가\s*(단\s*가|금\s*액)?\s*$|원가\s*율|NEGO|마진|이익률", re.I)   # 「원가요소」(항목 이름 칸)는 아님
_STOP = re.compile(r"특이\s*사항|^\s*\d\)\s*납|견적서\s*유효")


def _clean(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v != v:   # NaN
            return None
        r = round(v, 4)
        return int(r) if r == int(r) and abs(r) < 1e15 else r
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, datetime.time):
        return v.strftime("%H:%M")
    s = str(v).strip()
    if not s or s.startswith("#DIV") or s in ("#N/A", "#REF!", "#VALUE!"):
        return None
    return s


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _txt(v):
    return "" if v is None else str(v)


def _grid(ws):
    """보이는 값 격자(빈 줄·빈 열 정리) · 숨긴 열 번호 · 병합 칸의 왼쪽 위 값만."""
    rows = []
    for r in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 0, MAX_ROWS), max_col=min(ws.max_column or 0, MAX_COLS), values_only=True):
        rows.append([_clean(v) for v in r])
    hidden_rows = set()
    try:
        for k, d in ws.row_dimensions.items():
            if d.hidden:
                hidden_rows.add(k - 1)
    except Exception:
        pass
    hidden_cols = set()
    try:
        from openpyxl.utils import column_index_from_string
        for k, d in ws.column_dimensions.items():
            if d.hidden:
                a = column_index_from_string(k) - 1
                b = (d.max or (a + 1)) - 1
                for i in range(a, max(a, b) + 1):
                    hidden_cols.add(i)
    except Exception:
        pass
    # 끝쪽 빈 줄·빈 열 자르기
    while rows and not any(v is not None for v in rows[-1]):
        rows.pop()
    width = 0
    for r in rows:
        for i in range(len(r) - 1, -1, -1):
            if r[i] is not None:
                width = max(width, i + 1)
                break
    rows = [r[:width] + [None] * (width - len(r[:width])) for r in rows]
    return rows, sorted(i for i in hidden_cols if i < width), sorted(i for i in hidden_rows if i < len(rows))


_INLINE = [("qdate", re.compile(r"^(?:견\s*적\s*일\s*자?|작\s*성\s*일)\s*[:：]\s*(.+)$")),
           ("customer", re.compile(r"^업\s*체\s*명\s*[:：]\s*(.+)$")),
           ("contact", re.compile(r"^담\s*당\s*자?\s*[:：]\s*(.+)$")),
           ("title", re.compile(r"^(?:품\s*명|설\s*비\s*명|건\s*명)\s*[:：]\s*(.+)$"))]
_LBL["qdate"] = re.compile(r"^(견\s*적\s*(일|일자)|작\s*성\s*일)\s*:?\s*$")
_LBL["title"] = re.compile(r"^(품\s*명|설\s*비\s*명|건\s*명)\s*:?\s*$")
_GWIHA = re.compile(r"^(.+?)\s*(貴\s*下|귀\s*하|귀\s*중)\s*$")


def _xl_date(v):
    """엑셀 날짜 숫자(46062) → 2026-02-09"""
    if _is_num(v) and 30000 < v < 80000:
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))).strftime("%Y-%m-%d")
    return None


def _meta(rows):
    """머리 값 · 머리 글이 있었는지(값이 비어 있어도 앞장 후보)."""
    m, seen = {}, set()
    for r in rows[:20]:
        for i, v in enumerate(r):
            s = _txt(v).strip()
            for k, rx in _INLINE:
                mm = rx.match(s)
                if mm:
                    seen.add(k)
                    if k not in m and mm.group(1).strip():
                        m[k] = mm.group(1).strip()[:120]
            g = _GWIHA.match(s)
            if g and "customer" not in m:
                seen.add("customer"); m["customer"] = g.group(1).strip()[:120]
            for k, rx in _LBL.items():
                if not rx.match(s):
                    continue
                seen.add(k)
                if k in m:
                    continue
                for j in range(i + 1, min(i + 8, len(r))):
                    w = r[j]
                    if w is None:
                        continue
                    if k == "qdate" and _xl_date(w):
                        m[k] = _xl_date(w); break
                    ws = _txt(w).strip()
                    if not ws or _NOT_VAL.match(ws):
                        if ws and ws != ":":
                            break   # 다른 머리 글이 먼저 오면 값 없음
                        continue
                    m[k] = ws[:120]
                    break
    return m, seen


def _meta_old(rows):
    m = {}
    for r in rows[:20]:
        for i, v in enumerate(r):
            s = _txt(v)
            for k, rx in _LBL.items():
                if k in m or not rx.match(s):
                    continue
                for j in range(i + 1, min(i + 8, len(r))):
                    w = r[j]
                    if w is None:
                        continue
                    ws = _txt(w).strip()
                    if not ws or _NOT_VAL.match(ws):
                        if ws and ws != ":":
                            break   # 다른 머리 글이 먼저 오면 값 없음
                        continue
                    m[k] = ws[:120]
                    break
    return m


def _header_row(rows, start=0, end=None):
    for i in range(start, min(len(rows), end or len(rows))):
        cols = {}
        for j, v in enumerate(rows[i]):
            s = re.sub(r"\s+", " ", _txt(v)).strip()
            if not s or len(s) > 30:
                continue
            for k, rx in _HDR.items():
                if k not in cols and rx.search(s):
                    cols[k] = j
                    break
        if len({"name", "qty", "unit_price", "amount"} & set(cols)) >= 3:
            return i, cols
    return None, {}


def _span(cols, key, width):
    """머리 열 → 그 열부터 다음 머리 열 전까지(병합 칸 때문에 값이 오른쪽에 있을 수 있음)."""
    if key not in cols:
        return None
    a = cols[key]
    nxt = sorted(v for v in cols.values() if v > a)
    return (a, (nxt[0] if nxt else width))


def _pick_num(row, sp):
    if not sp:
        return None
    for j in range(sp[0], min(sp[1], len(row))):
        if _is_num(row[j]):
            return row[j]
    return None


def _items(rows, hi, cols, skip=()):
    width = max((len(r) for r in rows), default=0)
    sp = {k: _span(cols, k, width) for k in _HDR}
    qa = cols.get("qty", cols.get("unit_price", width))
    out = []
    group = 1
    for ri in range(hi + 1, len(rows)):
        r = rows[ri]
        line = " ".join(_txt(v) for v in r if v is not None).strip()
        if not line:
            continue
        if _STOP.search(line):
            break
        h2, c2 = _header_row(rows, ri, ri + 1)
        if h2 is not None:   # 앞장 아래 두 번째 표(구성별 금액) — 그 머리로 바꿔 이어 읽는다
            cols = c2; group += 1
            sp = {k: _span(cols, k, width) for k in _HDR}
            qa = cols.get("qty", cols.get("unit_price", width))
            continue
        r = [None if j in skip else v for j, v in enumerate(r)]
        texts = [(j, _txt(v)) for j, v in enumerate(r) if v is not None and not _is_num(v) and j < qa]
        no = None
        if "no" in cols and cols["no"] < len(r) and r[cols["no"]] is not None and re.fullmatch(r"\d{1,3}|-", _txt(r[cols["no"]]).strip()):
            no = _txt(r[cols["no"]])
        name_parts = [t for j, t in texts if not (j == cols.get("no") and no is not None) and t not in ("-",) and j not in skip]
        spec = None
        if sp.get("spec"):
            s0 = [_txt(r[j]) for j in range(sp["spec"][0], min(sp["spec"][1], len(r))) if r[j] is not None and not _is_num(r[j])]
            spec = " ".join(s0) or None
            name_parts = [t for t in name_parts if t not in s0]
        unit = None
        if "qty" in cols:
            for j in range(cols["qty"], min(cols.get("unit_price", width), len(r))):
                if r[j] is not None and not _is_num(r[j]):
                    unit = _txt(r[j])
                    break
        it = {"row": ri, "group": group, "no": no, "name": " ".join(name_parts)[:200] or None, "spec": spec,
              "qty": _pick_num(r, sp.get("qty")), "unit": unit,
              "unit_price": _pick_num(r, sp.get("unit_price")), "amount": _pick_num(r, sp.get("amount"))}
        if it["name"] or (it["qty"] is not None and it["amount"] is not None):
            out.append(it)
    return out


def _date_ok(s):
    return bool(re.search(r"20\d\d\s*[.\-/년]\s*\d{1,2}", s or ""))


def read_book(raw):
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    except Exception as e:
        return {"ok": False, "message": "엑셀을 열지 못했습니다: %s" % str(e)[:120], "fronts": [], "front": None, "sheets": []}
    sheets, fronts = [], []
    for si, ws in enumerate(wb.worksheets):
        try:
            rows, hcols, hrows = _grid(ws)
        except Exception as e:
            print(f"[z1191z121] 시트 읽기 실패 {ws.title}: {e}")
            continue
        hidden_sheet = (getattr(ws, "sheet_state", "visible") or "visible") != "visible"
        hi, cols = _header_row(rows, 0, 40)
        internal_cols = set(hcols)
        if hi is not None:
            for j, v in enumerate(rows[hi]):
                if _INTERNAL_COL.search(_txt(v)):
                    internal_cols.add(j)
        # 머리줄 오른쪽의 「원가」 칸(자동화 양식: 비 고 | 원가 | 0.4) — 그 열부터 끝까지 회사 안에서만
        if hi is not None:
            for j, v in enumerate(rows[hi]):
                if re.fullmatch(r"원\s*가", _txt(v).strip()):
                    st = j
                    if "note" in cols and cols["note"] < j:
                        st = cols["note"] + 1
                        # 비고 칸이 병합으로 넓으면 그 칸 글이 있는 마지막 열 다음부터
                        for rr in rows[hi + 1:]:
                            for k in range(cols["note"] + 1, j):
                                if k < len(rr) and _is_num(rr[k]):
                                    st = min(st, k) if st > cols["note"] + 1 else st
                    for k in range(st, len(rows[hi])):
                        internal_cols.add(k)
                    break
            # 회사 양식 앞장: 「비고」 오른쪽에 머리 글이 있는 열(원가·가공품 비율·마진율 계산기 등)부터 끝까지 = 회사 안
            if "note" in cols:
                for j in range(cols["note"] + 1, len(rows[hi])):
                    if rows[hi][j] is not None and _txt(rows[hi][j]).strip():
                        for k in range(j, len(rows[hi])):
                            internal_cols.add(k)
                        break
        
        applied = []
        if hi is not None and "qty" in cols:
            for ri in range(hi + 1, len(rows)):
                q = rows[ri][cols["qty"]] if cols["qty"] < len(rows[ri]) else None
                if _is_num(q) and q > 0:
                    applied.append(ri)
        sh = {"title": ws.title, "internal": bool(hidden_sheet or _INTERNAL_SHEET.search(ws.title or "")),
              "hidden_sheet": hidden_sheet, "internal_cols": sorted(internal_cols), "hidden_rows": hrows,
              "rows": rows, "header_row": hi, "applied": applied}
        try:   # z1191z170: 엑셀 모양(칸 너비·병합·테두리·글꼴·바탕·정렬) — 화면을 엑셀처럼
            sh["lay"] = layout_of_ws(ws, len(rows), max((len(x) for x in rows), default=0))
        except Exception as e:
            print(f"[z1191z170] 시트 모양 읽기 실패 {ws.title}: {e}")
        sheets.append(sh)
        m, seen = _meta(rows)
        if hi is not None and ({"customer", "qdate"} & seen) and hi <= 25 and not hidden_sheet:
            filled = bool(m.get("customer")) and (_date_ok(m.get("qdate")) or bool(re.match(r"20\d\d-\d\d-\d\d", m.get("qdate") or "")))
            items = _items(rows, hi, cols, internal_cols)
            fronts.append({"sheet": len(sheets) - 1, "title": ws.title, "filled": filled, "meta": m,
                           "header": [_txt(v) for v in rows[hi]], "cols": cols, "items": items})
    front_sheets = {f["sheet"] for f in fronts}
    for si, sh in enumerate(sheets):   # 선택표(검사기 「세부항목」) = 앞장이 아니고 수량 든 줄이 일부(80% 미만)인 표
        body = len(sh["rows"]) - (sh["header_row"] or 0) - 1 if sh["header_row"] is not None else 0
        sh["select"] = bool(si not in front_sheets and sh["applied"] and body > 0 and len(sh["applied"]) < 0.8 * body)
    for f in fronts:   # 첫 줄(제품 전체 줄)에 이름이 비어 있으면 앞장 품명
        its = f["items"]
        if its and not its[0]["name"] and f["meta"].get("title"):
            its[0]["name"] = f["meta"]["title"]
    filled = [i for i, f in enumerate(fronts) if f["filled"]]
    front = filled[0] if len(filled) == 1 else (0 if (len(fronts) == 1) else None)
    for i, f in enumerate(fronts):   # 입력 실수 알림: 업체명·견적일이 비어 있는 앞장
        f["warn"] = [w for w, ok in (("업체명이 비어 있습니다", bool(f["meta"].get("customer"))), ("견적일이 비어 있습니다", bool(f["meta"].get("qdate")))) if not ok]
    return {"ok": True, "message": "", "fronts": fronts, "front": front, "sheets": sheets}


def search_rows(book, can_cost):
    out = []
    for si, sh in enumerate(book.get("sheets") or []):
        if sh.get("internal") and not can_cost:
            continue
        ic = set(sh.get("internal_cols") or []) if not can_cost else set()
        ap = set(sh.get("applied") or [])
        sel = bool(sh.get("select"))
        for ri, r in enumerate(sh.get("rows") or []):
            if sel and ri > (sh["header_row"] or 0) and ri not in ap:
                continue   # 선택표: 수량 없는 줄(안 들어간 항목)은 찾기에서 뺀다
            t = " ".join(_txt(v) for j, v in enumerate(r) if v is not None and j not in ic).strip()
            if t:
                out.append((si, ri, t[:600]))
    return out


def view_of(book, can_cost, lays=None):
    """화면에 보낼 모양 — 권한 없으면 원가 시트·칸을 뺀다.
    z1191z170: lays = 원본에서 다시 읽은 시트 모양(예전에 읽어 둔 견적서엔 모양이 없어서) · 엑셀 모양 표 xl"""
    shs = []
    for si, sh in enumerate(book.get("sheets") or []):
        if sh.get("internal") and not can_cost:
            continue
        ic = set(sh.get("internal_cols") or []) if not can_cost else set()
        rows = [[(None if j in ic else v) for j, v in enumerate(r)] for r in sh["rows"]]
        width = 0
        for r in rows:
            for i in range(len(r) - 1, -1, -1):
                if r[i] is not None:
                    width = max(width, i + 1)
                    break
        _lay = sh.get("lay") or (lays or {}).get(sh["title"])
        try:
            _xl = xl_render(rows, _lay, ic) if _lay else None   # 권한 없으면 원가 칸은 엑셀 모양에서도 통째로 뺌
        except Exception as e:
            print(f"[z1191z170] 엑셀 모양 그리기 실패 {sh['title']}: {e}")
            _xl = None
        shs.append({"i": si, "title": sh["title"], "internal": sh.get("internal"), "rows": [r[:width] for r in rows], "xl": _xl,
                    "header_row": sh.get("header_row"), "applied": sh.get("applied") or [], "select": bool(sh.get("select")),
                    "cost_cols": sorted(set(sh.get("internal_cols") or [])) if can_cost else []})
    fr = []
    for f in book.get("fronts") or []:
        g = dict(f)
        if not can_cost:
            g["items"] = [{k: v for k, v in it.items()} for it in f["items"]]
        fr.append(g)
    return {"fronts": fr, "front": book.get("front"), "sheets": shs}



# ── z1191z170 (대표 11-27 「견적서 보기가 엑셀 파일과 형태가 너무 달라 · 최대한 엑셀 형태를 유지」) ──
# 원본 엑셀의 칸 너비·줄 높이·병합·테두리·글꼴(굵게·크기·색)·바탕색·정렬을 읽어 화면에 그대로 그린다.
_THEME170 = ["FFFFFF", "000000", "E7E6E6", "44546A", "4472C4", "ED7D31", "A5A5A5", "FFC000", "5B9BD5", "70AD47", "0563C1", "954F72"]


def _tint170(hexv, tint):
    try:
        t = float(tint or 0)
    except Exception:
        t = 0.0
    if not t:
        return hexv
    r, g, b = int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16)

    def f(c):
        return int(round(c * (1 + t))) if t < 0 else int(round(c + (255 - c) * t))
    return "%02X%02X%02X" % tuple(max(0, min(255, f(c))) for c in (r, g, b))


def _rgb170(col):
    """openpyxl 색 → '#RRGGBB' (모르면 None)."""
    if col is None:
        return None
    try:
        tp = getattr(col, "type", None)
        if tp == "rgb":
            v = col.rgb if isinstance(col.rgb, str) else None
            if not v or len(v) < 6:
                return None
            return "#" + v[-6:]
        if tp == "indexed":
            from openpyxl.styles.colors import COLOR_INDEX
            i = int(col.indexed)
            if 0 <= i < len(COLOR_INDEX) and i < 64:
                return "#" + COLOR_INDEX[i][-6:]
            return None
        if tp == "theme":
            i = int(col.theme)
            if 0 <= i < len(_THEME170):
                return "#" + _tint170(_THEME170[i], getattr(col, "tint", 0))
    except Exception:
        return None
    return None


_BSTY170 = {"thin": "1px solid", "hair": "1px solid", "dotted": "1px dotted", "dashed": "1px dashed", "dashDot": "1px dashed",
            "dashDotDot": "1px dashed", "medium": "2px solid", "mediumDashed": "2px dashed", "mediumDashDot": "2px dashed",
            "mediumDashDotDot": "2px dashed", "slantDashDot": "2px dashed", "thick": "3px solid", "double": "3px double"}


def _side170(s):
    st = getattr(s, "style", None) if s is not None else None
    if not st or st not in _BSTY170:
        return None
    return "%s %s" % (_BSTY170[st], _rgb170(getattr(s, "color", None)) or "#000")


def _cell_css170(cell):
    """칸 하나의 모양 → (css 글, 테두리 4면 dict)."""
    out = []
    try:
        ft = cell.font
        if ft is not None:
            if ft.b:
                out.append("font-weight:700")
            if ft.i:
                out.append("font-style:italic")
            if ft.u:
                out.append("text-decoration:underline")
            if ft.sz:
                out.append("font-size:%spt" % (round(float(ft.sz), 1)))
            c = _rgb170(ft.color)
            if c and c.upper() != "#000000":
                out.append("color:%s" % c)
    except Exception:
        pass
    try:
        fl = cell.fill
        if fl is not None and getattr(fl, "fill_type", None) == "solid":
            c = _rgb170(fl.fgColor)
            if c and c.upper() != "#FFFFFF":
                out.append("background:%s" % c)
    except Exception:
        pass
    try:
        al = cell.alignment
        h = getattr(al, "horizontal", None)
        if h in ("center", "centerContinuous", "distributed"):
            out.append("text-align:center")
        elif h == "right":
            out.append("text-align:right")
        elif h in ("left", "justify", "fill"):
            out.append("text-align:left")
        v = getattr(al, "vertical", None)
        out.append("vertical-align:%s" % ({"top": "top", "center": "middle", "justify": "middle", "distributed": "middle"}.get(v, "bottom")))
        if getattr(al, "wrap_text", False):
            out.append("white-space:pre-wrap")
        if getattr(al, "indent", 0):
            out.append("padding-left:%dpx" % (int(al.indent) * 9 + 3))
    except Exception:
        pass
    bd = {}
    try:
        b = cell.border
        for k in ("left", "right", "top", "bottom"):
            v = _side170(getattr(b, k, None))
            if v:
                bd[k] = v
    except Exception:
        pass
    return ";".join(out), bd


def layout_of_ws(ws, nrows, ncols):
    """시트 모양 — nrows×ncols 격자(_grid 와 같은 번호) 안만."""
    try:
        dw = float(ws.sheet_format.defaultColWidth or 0) or (float(ws.sheet_format.baseColWidth or 8) + 0.43)
    except Exception:
        dw = 8.43
    widths = [dw] * ncols
    hc = set()
    for k, d in ws.column_dimensions.items():
        try:
            a = int(d.min) - 1
            b = int(d.max or d.min) - 1
        except Exception:
            continue
        for i in range(a, max(a, b) + 1):
            if 0 <= i < ncols:
                if d.width:
                    widths[i] = float(d.width)
                if d.hidden:
                    hc.add(i)
    try:
        dh = float(ws.sheet_format.defaultRowHeight or 15)
    except Exception:
        dh = 15.0
    heights, hr = [dh] * nrows, set()
    for k, d in ws.row_dimensions.items():
        i = int(k) - 1
        if 0 <= i < nrows:
            if d.ht:
                heights[i] = float(d.ht)
            if d.hidden:
                hr.add(i)
    merges = []
    for mr in ws.merged_cells.ranges:
        r0, c0, r1, c1 = mr.min_row - 1, mr.min_col - 1, mr.max_row - 1, mr.max_col - 1
        if r0 >= nrows or c0 >= ncols:
            continue
        merges.append([r0, c0, min(r1, nrows - 1), min(c1, ncols - 1)])
    css, bds, nfs = {}, {}, {}
    if nrows and ncols:
        for r in ws.iter_rows(min_row=1, max_row=nrows, max_col=ncols):
            for cell in r:
                try:
                    ri, ci = cell.row - 1, cell.column - 1
                except Exception:
                    continue
                s, b = _cell_css170(cell)
                key = "%d,%d" % (ri, ci)
                try:
                    _nf = cell.number_format
                    if _nf and _nf != "General" and ((isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool))
                                                     or isinstance(cell.value, (datetime.date, datetime.datetime))):
                        nfs[key] = _nf
                except Exception:
                    pass
                if s:
                    css[key] = s
                if b:
                    bds[key] = b
    return {"w": [round(x, 2) for x in widths], "h": [round(x, 1) for x in heights], "hc": sorted(hc), "hr": sorted(hr),
            "m": merges, "css": css, "bd": bds, "nf": nfs, "v": 170}


def layouts_of(raw):
    """원본 엑셀 → {시트 이름: 모양} (값 격자는 read_book 과 같은 _grid 기준)."""
    import openpyxl
    out = {}
    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    for ws in wb.worksheets:
        try:
            rows, _hc, _hr = _grid(ws)
            out[ws.title] = layout_of_ws(ws, len(rows), max((len(x) for x in rows), default=0))
        except Exception as e:
            print(f"[z1191z170] 시트 모양 읽기 실패 {ws.title}: {e}")
    return out


_NF_DATE170 = re.compile(r"(?i)(yy|dd|mmm|^m+[/.\-]|[/.\-]m+|aaa|ddd)")


def fmt_num170(v, nf):
    """엑셀 셀 표시 형식(자주 쓰는 것) — 날짜·천 단위 쉼표·소수 자리·% · 따옴표 글자. 모르면 None(원래 표시)."""
    try:
        sec = nf.split(";")
        f = sec[0]
        if v < 0 and len(sec) > 1 and sec[1].strip():
            f, v = sec[1], -v if "-" not in sec[1] else v
        f = re.sub(r"\[(Red|Blue|Black|Green|White|Color\d+|빨강|파랑)\]", "", f, flags=re.I)
        f = re.sub(r"\[\$([^\]-]*)-?[^\]]*\]", lambda m: '"' + m.group(1) + '"', f)
        f = f.replace("_)", "").replace("_(", "").replace("*", "").replace("\\", "")
        core = re.sub(r'"[^"]*"', "", f)
        if _NF_DATE170.search(core) and 0 < v < 2958466:
            from openpyxl.utils.datetime import from_excel
            d = from_excel(v)
            out, i = "", 0
            toks = re.findall(r'"[^"]*"|yyyy|yy|mmmm|mmm|mm|m|dd|d|hh|h|ss|s|[^ymdhs"]+', f, flags=re.I)
            seen_h = False
            for t in toks:
                tl = t.lower()
                if tl == "yyyy": out += "%04d" % d.year
                elif tl == "yy": out += "%02d" % (d.year % 100)
                elif tl in ("mm", "m") and seen_h: out += ("%02d" % d.minute) if tl == "mm" else str(d.minute)
                elif tl == "mm": out += "%02d" % d.month
                elif tl == "m": out += str(d.month)
                elif tl in ("mmm", "mmmm"): out += d.strftime("%b" if tl == "mmm" else "%B")
                elif tl == "dd": out += "%02d" % d.day
                elif tl == "d": out += str(d.day)
                elif tl in ("hh", "h"): out += ("%02d" % d.hour) if tl == "hh" else str(d.hour); seen_h = True
                elif tl in ("ss", "s"): out += "%02d" % d.second
                elif t.startswith('"'): out += t[1:-1]
                else: out += t
            return out
        pct = "%" in core
        x = v * 100 if pct else v
        m = re.search(r"\.(0+)", core)
        dec = len(m.group(1)) if m else 0
        if not re.search(r"[0#]", core):
            return None
        body = ("{:,.%df}" if "," in core else "{:.%df}") % dec
        num = body.format(x)
        pre = "".join(re.findall(r'"([^"]*)"', f.split("0")[0].split("#")[0]))
        tail = f[max(f.rfind("0"), f.rfind("#")) + 1:]
        suf = "".join(re.findall(r'"([^"]*)"', tail))
        return pre + num + ("%" if pct else "") + suf
    except Exception:
        return None


def _px_w170(w):
    return int(round(float(w) * 7 + 5))


def xl_render(rows, lay, hide_cols=()):
    """값 격자 + 모양 → 화면 표(보이는 줄·칸만 · 병합은 colspan/rowspan). 모양이 없으면 None."""
    if not lay or not rows:
        return None
    nr = len(rows)
    nc = max((len(r) for r in rows), default=0)
    if not nc:
        return None
    hc = set(lay.get("hc") or []) | set(hide_cols or [])
    hr = set(lay.get("hr") or [])
    vis_c = [c for c in range(nc) if c not in hc]
    vis_r = [r for r in range(nr) if r not in hr]
    if not vis_c or not vis_r:
        return None
    W = lay.get("w") or []
    H = lay.get("h") or []
    css = lay.get("css") or {}
    bd = lay.get("bd") or {}
    anchor, covered = {}, set()
    for r0, c0, r1, c1 in lay.get("m") or []:
        rs = [r for r in range(r0, r1 + 1) if r < nr and r not in hr]
        cs = [c for c in range(c0, c1 + 1) if c < nc and c not in hc]
        if not rs or not cs:
            continue
        anchor[(rs[0], cs[0])] = (r0, c0, r1, c1, len(rs), len(cs))
        for r in rs:
            for c in cs:
                if (r, c) != (rs[0], cs[0]):
                    covered.add((r, c))
    classes, out_rows = {}, []

    def cls_of(s):
        if not s:
            return ""
        if s not in classes:
            classes[s] = "x%d" % len(classes)
        return classes[s]
    for r in vis_r:
        cells = []
        for c in vis_c:
            if (r, c) in covered:
                continue
            a = anchor.get((r, c))
            if a:
                r0, c0, r1, c1, rsn, csn = a
                v = rows[r0][c0] if r0 < len(rows) and c0 < len(rows[r0]) else None
                st = css.get("%d,%d" % (r0, c0), "")
                b = dict(bd.get("%d,%d" % (r0, c0)) or {})
                for k, (rr, cc) in (("right", (r0, c1)), ("bottom", (r1, c0))):
                    e = (bd.get("%d,%d" % (rr, cc)) or {}).get(k)
                    if e:
                        b[k] = e
            else:
                rsn = csn = 1
                v = rows[r][c] if c < len(rows[r]) else None
                st = css.get("%d,%d" % (r, c), "")
                b = bd.get("%d,%d" % (r, c)) or {}
            full = st + "".join(";border-%s:%s" % (k, x) for k, x in sorted(b.items()))
            _nfk = ("%d,%d" % (r0, c0)) if a else ("%d,%d" % (r, c))
            if isinstance(v, str) and (lay.get("nf") or {}).get(_nfk) and re.match(r"^\d{4}-\d\d-\d\d", v):
                try:   # 읽을 때 날짜 글자(2026-02-09)로 바뀐 칸 → 엑셀 날짜 숫자로 되돌려 그 칸 형식대로
                    from openpyxl.utils.datetime import to_excel
                    v = to_excel(datetime.datetime.fromisoformat(v[:19]))
                except Exception:
                    pass
            if isinstance(v, (int, float)) and not isinstance(v, bool) and (lay.get("nf") or {}).get(_nfk):
                _fv = fmt_num170(v, lay["nf"][_nfk])
                if _fv is not None:
                    if "text-align" not in st:
                        full += ";text-align:right"
                    v = _fv
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                # 표시 형식 「일반」 = 엑셀처럼 쉼표 없이(정수는 그대로 · 소수는 유효 숫자 10자리까지)
                if "text-align" not in st:
                    full += ";text-align:right"
                v = str(int(v)) if float(v).is_integer() else ("%.10g" % v)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and "text-align" not in st:
                full += ";text-align:right"
            cells.append({"v": v, "rs": rsn, "cs": csn, "c": c, "k": cls_of(full.strip(";")), "ow": 0})
        # 엑셀처럼: 줄바꿈 없는 왼쪽 맞춤 글자는 오른쪽 빈 칸까지 넘어가 보임(다음 글자 있는 칸에서 잘림)
        for ii, cl in enumerate(cells):
            if not isinstance(cl["v"], str) or cl["cs"] != 1 or cl["rs"] != 1:
                continue
            st = css.get("%d,%d" % (r, cl["c"]), "")
            if "pre-wrap" in st or "text-align:center" in st or "text-align:right" in st:
                continue
            ow = _px_w170(W[cl["c"]] if cl["c"] < len(W) else 8.43)
            for nx in cells[ii + 1:]:
                if nx["v"] is not None or nx["cs"] != 1 or nx["rs"] != 1:
                    break
                ow += _px_w170(W[nx["c"]] if nx["c"] < len(W) else 8.43)
            cl["ow"] = ow - 6
        out_rows.append({"r": r, "h": int(round((H[r] if r < len(H) else 15) * 4 / 3)), "cells": cells})
    cols = [_px_w170(W[c] if c < len(W) else 8.43) for c in vis_c]
    return {"cols": cols, "width": sum(cols), "rows": out_rows,
            "css": [(k, s) for s, k in classes.items()]}
