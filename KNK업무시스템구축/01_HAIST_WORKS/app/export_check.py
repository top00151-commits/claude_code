# -*- coding: utf-8 -*-
"""z1191z85 — 인보이스·패킹리스트 서류 점검 (대표 2026-11-20 「안지연 프로 입장에서 · 20년 수출입 배테랑이 만든 프로그램처럼」)

포워더·법인에 넘기기 전에 오래 한 실무자가 눈으로 보는 것을 파일에서 바로 본다.
  ① 인보이스 ↔ 패킹리스트 번호·날짜 · 품목 수 · 줄마다 수량
  ② 줄 금액 = 수량 × 단가 · TOTAL = 줄 금액 합
  ③ 패킹 무게·부피(비었는지 · 순중량 ≤ 총중량)
  ④ HS 8자리 · 베트남어 품명
  ⑤ 원산지 · C/O 표시(한국산이 아닌데 C/O 「O」)
  ⑥ 인보이스 % 섞임 · 선적일(인보이스 날짜보다 앞 · 너무 뒤)
  ⑦ 지난 수출과 비교 — 같은 규격이 지난번과 HS 다름 · 단가가 정한 범위(사용자 조건 · export_price) 밖(특수관계 거래 — 세관 가격 심사 대비)
양식이 14가지로 달라(2026-01~11 실측 55개 파일) 칸은 머리글 글자로 찾는다. 파일은 바꾸지 않는다(읽기만).
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime, timedelta

_INV_RX = re.compile(r"KNK-\d{6}(?:-\d+)?")


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = _s(v).replace(",", "")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _day(v) -> str:
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, (int, float)) and 30000 < v < 80000:      # 엑셀 날짜 숫자
        return (datetime(1899, 12, 30) + timedelta(days=int(v))).strftime("%Y-%m-%d")
    m = re.search(r"(20\d\d)[-./](\d{1,2})[-./](\d{1,2})", _s(v))
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3))) if m else ""


def _norm(s) -> str:
    return re.sub(r"\s+", "", _s(s)).upper()


def _grid(ws, max_row=3000, max_col=30) -> dict:
    g = {}
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or max_row, max_row), max_col=max_col):
        for c in row:
            v = getattr(c, "value", None)
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            g[(c.row, c.column)] = v
    return g


def _find(g, rx, rows=None):
    for (r, c), v in sorted(g.items()):
        if rows and not (rows[0] <= r <= rows[1]):
            continue
        if isinstance(v, str) and re.search(rx, v, re.I):
            return (r, c)
    return None


def _below(g, pos, span=2):
    """머리 칸(「4) Port of Loading」) 아래 값 — 같은 칸 또는 오른쪽 한 칸."""
    if not pos:
        return None
    for dr in range(1, span + 1):
        for dc in (0, 1):
            v = g.get((pos[0] + dr, pos[1] + dc))
            if v not in (None, ""):
                return v
    return None


# 머리글 → 뜻 (대소문자·공백 무시 · 실측 양식 14가지에서 모음)
_HDR = [
    ("origin", r"^(origin|원산지)$"),
    ("maker", r"^(manufacturer|manufaturer|supplier|maker)$"),
    ("pct", r"^invoice\s*%$"),
    ("co", r"^c/?o$"),
    ("hs", r"^hs\s*code$"),
    ("vn", r"^t[eê]n\s*h[aà]ng$"),
    ("cat", r"^category$"),
    ("mgmt", r"^관리코드$"),
    ("company", r"^company$"),
    ("ship_day", r"^(발송일|shipping\s*date)$"),
    ("size", r"^size$"),
]


def _header(g):
    """품목 머리 줄(「Description of Goods」) → (머리 줄, {뜻: 칸})."""
    pos = _find(g, r"Description\s+of\s+Goods")
    if not pos:
        return None, {}
    hr = pos[0]
    cols = {"desc": pos[1]}
    for (r, c), v in g.items():
        if not (hr <= r <= hr + 2) or not isinstance(v, str):
            continue
        t = re.sub(r"\s+", " ", v).strip()
        if re.search(r"Q'?ty", t, re.I) and "qty" not in cols:
            cols["qty"] = c
        elif re.search(r"Unit\s*Price", t, re.I):
            cols["price"] = c
        elif re.search(r"Amount", t, re.I) and c < 12 and "amount" not in cols:
            cols["amount"] = c
        elif re.search(r"^Net", t, re.I):
            cols["net"] = c
        elif re.search(r"^Gross", t, re.I):
            cols["gross"] = c
        elif re.search(r"Measurement", t, re.I):
            cols["meas"] = c
        elif re.search(r"Marks", t, re.I):
            cols["marks"] = c
        else:
            for k, rx in _HDR:
                if re.search(rx, t, re.I) and k not in cols:
                    cols[k] = c
    return hr, cols


def _items(g, hr, cols, need_amount=True):
    """품목 줄 — 규격과 수량이 있고(인보이스는 금액도) TOTAL 줄 앞까지."""
    out, total_row = [], None
    dc, qc = cols.get("desc"), cols.get("qty")
    if not dc or not qc:
        return out, None
    last = max((r for (r, _c) in g), default=hr)
    for r in range(hr + 1, last + 1):
        first = _s(g.get((r, 1))).upper()
        if first.startswith("TOTAL"):
            total_row = r
            break
        d, q = g.get((r, dc)), _num(g.get((r, qc)))
        if d in (None, "") or q is None:
            continue
        a = _num(g.get((r, cols["amount"]))) if cols.get("amount") else None
        if need_amount and a is None:
            continue
        it = {"row": r, "desc": _s(d), "qty": q, "amount": a,
              "price": _num(g.get((r, cols["price"]))) if cols.get("price") else None,
              "marks": _s(g.get((r, cols["marks"]))) if cols.get("marks") else _s(g.get((r, 2))),
              "use": _s(g.get((r, 10)))}
        for k in ("origin", "maker", "pct", "co", "hs", "vn", "cat", "mgmt", "company", "net", "gross", "meas"):
            if cols.get(k):
                it[k] = g.get((r, cols[k]))
        out.append(it)
    return out, total_row


def _head_facts(g) -> dict:
    f = {}
    for v in g.values():
        m = _INV_RX.search(_s(v))
        if m:
            f["invoice_no"] = m.group(0)
            break
    p = _find(g, r"^DATE\s*:?$", rows=(1, 12))
    if p:
        f["inv_date"] = _day(g.get((p[0], p[1] + 1)))
    acc = _find(g, r"For Account", rows=(1, 20))
    if acc:
        for dr in range(1, 4):
            v = g.get((acc[0] + dr, 2))
            if v:
                f["consignee"] = _s(v)[:80]
                break
        for (r, c), v in g.items():
            if r == acc[0] and c > acc[1] + 2 and isinstance(v, str) and v.strip():
                f["payment"] = v.strip()[:40]
    p = _find(g, r"INCOTERMS")
    if p:
        f["incoterms"] = re.sub(r"(?i)incoterms\s*:?\s*", "", _s(g[p])).replace(".", "").strip()
    f["pol"] = _s(_below(g, _find(g, r"Port of Loading")))[:40]
    f["dest"] = _s(_below(g, _find(g, r"Final Destination")))[:40]
    f["carrier"] = _s(_below(g, _find(g, r"\bCarrier\b")))[:40]
    f["sail_date"] = _day(_below(g, _find(g, r"Sailing On")))
    return f


def _same_desc(a, b) -> bool:
    """같은 품목 줄인가 — 패킹은 앞 품명(「PARTS OF CONNECTORS」)을 빼고 규격만 적기도 한다(2026-09 실측) → 한쪽이 다른 쪽 끝이면 같음."""
    #   인보이스는 장비 줄 아래에 「[S/N : …]」 일련번호를 덧붙인다(2026-03~08 실측 14건) → 첫 줄 · 괄호 앞만 견준다
    x, y = (_norm(re.split(r"[\n\[]", _s(t))[0]) for t in (a, b))
    return x == y or bool(x and y and (x in y or y in x))


def _first(t, n=30) -> str:
    return _s(t).splitlines()[0][:n] if _s(t) else ""


def _hs8(v) -> bool:
    return len(re.sub(r"\D", "", _s(v))) == 8


def _junk(v) -> bool:
    s = _s(v)
    return (not s) or s in ("0", "#N/A", "-") or s.startswith("#")


def read(data: bytes) -> dict:
    """엑셀 → {ok, invoice:{facts, items, total}, packing:{facts, items, total_net, total_gross, total_meas, boxes}} · 못 읽으면 {ok:False, error}."""
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    except Exception as e:
        return {"ok": False, "error": "엑셀을 열지 못했습니다 — %s" % str(e)[:120]}
    inv_ws = pl_ws = None
    for ws in wb.worksheets:
        t = ws.title.upper()
        if "PACK" in t and pl_ws is None:
            pl_ws = ws
        elif "INV" in t and inv_ws is None:
            inv_ws = ws
    if inv_ws is None and wb.worksheets:
        inv_ws = wb.worksheets[0]
    out = {"ok": True, "invoice": None, "packing": None}
    if inv_ws is not None:
        g = _grid(inv_ws)
        hr, cols = _header(g)
        items, trow = _items(g, hr, cols) if hr else ([], None)
        tot = _num(g.get((trow, cols.get("amount")))) if trow and cols.get("amount") else None
        out["invoice"] = {"facts": _head_facts(g), "items": items, "total": tot, "cols": sorted(cols)}
    if pl_ws is not None:
        g = _grid(pl_ws)
        hr, cols = _header(g)
        items, trow = _items(g, hr, cols, need_amount=False) if hr else ([], None)
        pk = {"facts": _head_facts(g), "items": items, "cols": sorted(cols)}
        for k in ("net", "gross", "meas"):
            v = _num(g.get((trow, cols[k]))) if trow and cols.get(k) else None
            if not v and cols.get(k):          # TOTAL 칸이 비면(수식 값 없음) 줄 값을 더한다
                s = sum(_num(it.get(k)) or 0 for it in items)
                v = s or v
            pk["total_" + k] = v
        # 박스 표(수책 양식 오른쪽 「NO. · SIZE · WEIGHT」) — 있으면 박스 수
        bno = _find(g, r"^NO\.?$", rows=(hr or 1, (hr or 1) + 2)) if hr else None
        if bno:
            nums = [g.get((r, bno[1])) for r in range(bno[0] + 1, bno[0] + 400) if _num(g.get((r, bno[1]))) is not None]
            pk["boxes"] = len(nums) or None
        out["packing"] = pk
    try:
        wb.close()
    except Exception:
        pass
    return out


def _w(level, title, detail="", rows=None):
    return {"level": level, "title": title, "detail": detail, "rows": (rows or [])[:8]}


def check(doc: dict, hist: dict | None = None, hist_hs: dict | None = None, rng=(15.0, 15.0)) -> dict:
    """read() 결과 → {facts, summary, items:[{level ok|warn|err|info, title, detail, rows}]}.
    hist = {규격 키: (단가, HS, 인보이스 번호, 날짜)} — 이 인보이스를 뺀 가장 최근 수출(지난 수출 이력에서).
    hist_hs = {규격 키: HS} — 법인 회신으로 이 인보이스에 확정된 HS(회신 파일은 보관하지 않아 이력 줄로 본다).
    rng = (오름 %, 내림 %) — 사용자가 정한 단가 조건(z1191z86 · None = 그쪽 안 봄)."""
    from .hs_fill import norm_key
    hist = hist or {}
    res = []
    inv, pk = doc.get("invoice") or {}, doc.get("packing") or {}
    its = inv.get("items") or []
    fi, fp = inv.get("facts") or {}, pk.get("facts") or {}
    if not its:
        return {"facts": fi, "summary": {"lines": 0}, "items": [_w("err", "품목 줄을 찾지 못했습니다",
                                                                     "「13) Description of Goods」 머리 줄 아래 규격·수량·금액이 있는 줄을 읽습니다")]}
    # ① 인보이스 ↔ 패킹
    if pk:
        diff = [k for k, nm in (("invoice_no", "번호"), ("inv_date", "날짜")) if fi.get(k) and fp.get(k) and fi[k] != fp[k]]
        if diff:
            res.append(_w("err", "인보이스와 패킹리스트의 번호·날짜가 다릅니다",
                          " · ".join("%s: 인보이스 %s / 패킹 %s" % ({"invoice_no": "번호", "inv_date": "날짜"}[k], fi[k], fp[k]) for k in diff)))
        else:
            res.append(_w("ok", "인보이스·패킹 번호와 날짜 같음"))
        pits = pk.get("items") or []
        if not pits:
            res.append(_w("warn", "패킹리스트 품목이 아직 비어 있습니다", "HS 확인 단계에서는 흔한 일 — 포워더·법인에 넘기기 전에 채우세요"))
        elif len(pits) != len(its):
            res.append(_w("err", "품목 수가 다릅니다 — 인보이스 %d줄 / 패킹 %d줄" % (len(its), len(pits)),
                          "줄을 더하거나 뺀 뒤 한쪽만 고친 경우가 많습니다"))
        else:
            bad = ["%d번째 %s — 인보이스 %g / 패킹 %g" % (i + 1, _first(a["desc"]), a["qty"], b["qty"])
                   for i, (a, b) in enumerate(zip(its, pits)) if abs(a["qty"] - b["qty"]) > 1e-9]
            word = ["%d번째 인보이스 「%s」 / 패킹 「%s」" % (i + 1, _first(a["desc"]), _first(b["desc"]))
                    for i, (a, b) in enumerate(zip(its, pits)) if not _same_desc(a["desc"], b["desc"])]
            if bad:
                res.append(_w("err", "인보이스와 패킹의 수량이 다른 줄 %d" % len(bad), "", bad))
            else:
                res.append(_w("ok", "품목 %d줄 · 수량 모두 같음" % len(its)))
            if word:
                res.append(_w("info", "품명 글자가 다른 줄 %d" % len(word), "같은 물건이면 괜찮습니다 — 세관은 두 서류의 품명이 같기를 바랍니다", word))
    else:
        res.append(_w("warn", "패킹리스트 시트가 없습니다", "시트 이름에 PACKING 이 든 시트를 찾습니다"))
    # ② 금액
    bad = []
    for it in its:
        if it.get("price") is not None and it.get("amount") is not None and abs(it["qty"] * it["price"] - it["amount"]) > 0.05:
            bad.append("%s — %g × %s = %s 인데 금액 %s" % (it["desc"][:30], it["qty"], _money(it["price"]), _money(it["qty"] * it["price"]), _money(it["amount"])))
    s = sum(it["amount"] or 0 for it in its)
    if bad:
        res.append(_w("err", "수량 × 단가 ≠ 금액 %d줄" % len(bad), "", bad))
    tot = inv.get("total")
    if tot is not None and abs(tot - s) > 0.5:
        res.append(_w("err", "TOTAL 이 줄 금액 합과 다릅니다 — TOTAL %s / 합 %s" % (_money(tot), _money(s)), "합계 수식 범위가 새 줄을 빠뜨렸는지 보세요"))
    elif not bad:
        res.append(_w("ok", "금액 계산 맞음 — 합계 USD %s" % _money(s)))
    # ③ 무게·부피
    if pk:
        n, gr, me = pk.get("total_net"), pk.get("total_gross"), pk.get("total_meas")
        if not pk.get("items"):
            pass
        elif not n or not gr:
            res.append(_w("warn", "패킹 무게가 비어 있습니다", "포워더 예약·세관 신고 전에 순중량·총중량(박스 포장 뒤)을 채워야 합니다"))
        elif n > gr:
            res.append(_w("err", "순중량이 총중량보다 큽니다 — 순 %s kg / 총 %s kg" % (_g(n), _g(gr))))
        else:
            res.append(_w("ok", "무게 — 순 %s kg · 총 %s kg%s%s" % (_g(n), _g(gr), (" · 부피 %s" % _g(me)) if me else "",
                                                               (" · 박스 %d" % pk["boxes"]) if pk.get("boxes") else "")))
    # ④ HS · 베트남어 품명
    hs_given = any("hs" in it for it in its)
    if hs_given or hist_hs:
        def _has_hs(it):
            return _hs8(it.get("hs")) or _hs8((hist_hs or {}).get(norm_key(it["desc"])))
        miss = [it["desc"][:40] for it in its if not _has_hs(it)]
        vmiss = [it["desc"][:40] for it in its if "vn" in it and _junk(it.get("vn")) and not (hist_hs or {}).get(norm_key(it["desc"]))]
        if miss:
            res.append(_w("warn", "HS 코드 8자리가 아닌 줄 %d" % len(miss), "법인 확인(노랑·주황)이 남았거나 회신을 아직 ③에 안 올렸습니다", miss))
        else:
            res.append(_w("ok", "HS 코드 모두 8자리" + (" (법인 회신 반영)" if hist_hs else "")))
        if vmiss:
            res.append(_w("warn", "베트남어 품명(Tên hàng)이 빈 줄 %d" % len(vmiss), "", vmiss))
    # ⑤ 원산지 · C/O
    if any("origin" in it for it in its):
        om = [it["desc"][:40] for it in its if not _s(it.get("origin")) or _s(it.get("origin")) == "-"]
        if om:
            res.append(_w("warn", "원산지가 빈 줄 %d" % len(om), "베트남 세관은 줄마다 원산지를 봅니다", om))
        co_bad = ["%s — 원산지 %s · C/O O" % (it["desc"][:30], _s(it.get("origin")) or "빈칸") for it in its
                  if _s(it.get("co")).upper() == "O" and _s(it.get("origin")).upper() not in ("KOREA", "KOREA, REPUBLIC OF", "KR")]
        if co_bad:
            res.append(_w("warn", "한국산이 아닌데 C/O 「O」인 줄 %d" % len(co_bad), "한-베트남 FTA 원산지증명(C/O)은 한국산만 됩니다 — 관세 혜택을 잘못 기대할 수 있습니다", co_bad))
        if not om and not co_bad:
            res.append(_w("ok", "원산지 모두 있음" + (" · C/O 표시 맞음" if any("co" in it for it in its) else "")))
    # ⑥ 인보이스 % · 선적일
    pcts = sorted({_s(it.get("pct")) for it in its if "pct" in it and _s(it.get("pct")) not in ("", "-")})
    if len(pcts) > 1:
        res.append(_w("info", "인보이스 % 가 섞여 있습니다 — " + " · ".join(pcts), "고객·품목마다 다르게 정한 것이면 괜찮습니다(세관이 물으면 근거를 댈 수 있게)"))
    if fi.get("inv_date") and fi.get("sail_date"):
        d0, d1 = fi["inv_date"], fi["sail_date"]
        gap = (datetime.strptime(d1, "%Y-%m-%d") - datetime.strptime(d0, "%Y-%m-%d")).days
        if gap < 0:
            res.append(_w("warn", "선적일(%s)이 인보이스 날짜(%s)보다 앞입니다" % (d1, d0)))
        elif gap > 14:
            res.append(_w("info", "선적일이 인보이스 날짜보다 %d일 뒤입니다" % gap, "지난 55건은 0~5일이었습니다"))
    # ⑦ 지난 수출과 비교
    hs_diff, pr_diff, px, seen = [], [], [], set()
    up, down = rng
    for it in its:
        k = norm_key(it["desc"])
        h = hist.get(k)
        if not h or (k, it.get("price")) in seen:      # 같은 규격이 설비마다 여러 줄 — 한 번만
            continue
        seen.add((k, it.get("price")))
        p0, hs0, ino0, d0 = h
        hs_now = _s(it.get("hs")) or _s((hist_hs or {}).get(k))
        if _hs8(hs_now) and _hs8(hs0) and re.sub(r"\D", "", hs_now) != re.sub(r"\D", "", hs0):
            hs_diff.append("%s — 이번 %s / 지난번 %s (%s)" % (it["desc"][:30], hs_now, hs0, ino0))
        if it.get("price") and p0:
            dif = (it["price"] - p0) / p0 * 100
            if (up is not None and dif > up + 1e-9) or (down is not None and dif < -down - 1e-9):
                pr_diff.append("%s — 이번 %s / 지난번 %s (%s · %+.1f%%)" % (it["desc"][:30], _money(it["price"]), _money(p0), ino0, dif))
                px.append({"key": k, "desc": it["desc"][:120], "now": round(it["price"], 4), "last": round(p0, 4), "diff": round(dif, 1),
                           "last_inv": ino0, "last_date": (d0 or "")[:10]})
    known = sum(1 for it in its if norm_key(it["desc"]) in hist)
    if hs_diff:
        res.append(_w("warn", "지난번과 HS 가 다른 규격 %d" % len(hs_diff), "같은 물건을 다른 HS 로 신고하면 세관 사후 심사 때 문제가 됩니다 — 바꾼 까닭이 있는지 확인", hs_diff))
    if pr_diff:
        it_pr = _w("warn", "정한 단가 범위를 벗어난 규격 %d" % len(pr_diff),
                   "본사↔법인 거래라 세관이 가격을 봅니다 — 줄마다 허용(까닭) 또는 고치기를 골라 주세요", pr_diff)
        it_pr["px"] = px            # 줄마다 고르기(화면이 고른 것을 붙인다 · export_price.overlay)
        res.append(it_pr)
    if known and not hs_diff and not pr_diff:
        res.append(_w("ok", "지난 수출과 같은 규격 %d줄 — HS 같고 단가는 정한 범위 안" % known))
    elif not known:
        res.append(_w("info", "지난 수출 이력에 같은 규격이 없습니다(처음 보내는 품목)"))
    lv = [x["level"] for x in res]
    summ = {"lines": len(its), "amount": round(s, 2), "err": lv.count("err"), "warn": lv.count("warn"),
            "net": pk.get("total_net"), "gross": pk.get("total_gross"), "meas": pk.get("total_meas"), "boxes": pk.get("boxes"),
            "uses": _top([it.get("use") for it in its]),   # 제조사·공급사는 넣지 않는다 — 구매처는 부서 단위 민감 정보(field_access_policy)
            "mgmt": _top([_s(it.get("mgmt")) or (it.get("marks") if re.match(r"^\d{3}[A-Z]\d{4}", it.get("marks") or "") else "") for it in its])}
    return {"facts": fi, "summary": summ, "items": res}


def _top(vals, n=4):
    from collections import Counter
    c = Counter(v for v in vals if v and str(v).strip() not in ("-", "0"))
    return [k for k, _ in c.most_common(n)]


def _money(v) -> str:
    try:
        return "{:,.2f}".format(float(v))
    except (TypeError, ValueError):
        return "—"


def _g(v) -> str:
    try:
        return "{:,.1f}".format(float(v)).rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return "—"
