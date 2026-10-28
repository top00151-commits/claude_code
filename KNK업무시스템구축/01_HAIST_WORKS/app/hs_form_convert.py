# -*- coding: utf-8 -*-
"""z1191u — 옛 인보이스 양식 → 최종 양식(수책통관 · 일반통관)으로 옮겨 담기
   대표 2026-10-28 「본사에서 업로드하는 양식, 베트남에서 업로드하는 양식을 지금 첨부한 파일로 반영해서 만들어줘..
   기존에 올리는 양식들이 이전꺼라 조금씩 다른데.. 확인해서 작성한 내용들이 포함된 문서는 항상 최종 양식으로 변경되어
   작성이 되도록 적용해줘...」 → 이해 보고(옮기는 규칙 · COMPANY·박스 표 · 수책/일반 자동+고름) → 「진행해」

옮기는 규칙 = 대표가 수책 261015 · 일반 260921 을 최종 양식으로 다시 만든 것을 칸마다 견줘 얻은 것(10-28 실측)
  · 머리: 최종 양식 공통 정보(TAX ID · BAC NINH CITY …) 그대로 + 번호 · 날짜 · 선적일만 옮긴다
  · 품목: A~H(표시 · 관리코드 · 번호 · 품명 · 수량 · 단가)는 같은 칸 · I 금액은 원본이 수량×단가 수식이면 틀 수식, 아니면 원본 값 ·
          오른쪽 칸은 **제목으로** 맞춘다
      수책: COMPANY · 관리코드 · MODEL · 품명 · Q'TY · ORIGIN · SUPPLIER · CATEGORY · HS CODE · Tên hàng · SHIPPING DATE
            관리코드 = 줄의 B(없으면 C) · MODEL·품명·Q'TY = 표 위 장비 묶음(관리코드 → MODEL·품명·수량) · 없으면 J칸 「장비명(N대)」
      일반: COMPANY · IMAGE(사진) · Origin · Manufacturer · invoice % · C/O · SIZE · HS CODE · Tên hàng
            제목 없는 J칸 = 회사(크기 모양이면 SIZE) · 품목 사진 = IMAGE 칸 안에 맞춰(한 줄 여러 장이면 나란히)
  · 패킹리스트: 품명 · 수량 · 순중량 · 총중량 · 부피 + 박스 표(NO. · SIZE · G/W → WEIGHT) — 세로로 합친 칸은 위 칸 하나에
  · 옛 양식에만 있는 칸(Duty · VAT · HS CODE CHECK · Loại hình …)은 뺀다 — 뺀 칸과 값 수를 돌려준다
  · 품목이 틀보다 많으면 줄을 늘린다(합계 수식 · 서명 그림 · 인쇄 영역 · 필터 · 병합 · 조건부 서식을 함께 민다)
  · 옮긴 뒤 새 파일을 다시 읽어 칸마다 · 품목 수 · 금액 합 · 사진을 대조 — 하나라도 다르면 ok=False(부르는 쪽은 옛 모양 그대로 채운다)
⚠ 파일은 엑셀 도구로 통째 저장하지 않는다 — XML 칸만 바꾼다(그림 · 서식 · 인쇄 설정을 지킨다 · hs_fill 과 같은 방식)
⚠ 읽기는 엑셀 XML 을 바로 읽는다(hs_fill.sheet_cells · scan_fast) — 최종 양식 틀은 서식이 3만 개 넘게 쌓여 있어
   openpyxl 로 한 번 읽는 데 2~3초(10-28 실측 · 한 파일 13초 → 1초)
"""
import datetime as _dt
import io
import os
import re
import zipfile
from xml.sax.saxutils import escape as _xml_escape

from . import hs_fill as H

SEED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed")
TEMPLATES = {"수책": "invoice_form_suchaek.xlsx", "소모품": "invoice_form_somo.xlsx"}

# 제목 → 뜻(정규화한 글자로 찾는다: 대문자 · 빈칸·줄바꿈·점 없앰)
_MEAN = {
    "COMPANY": "company", "관리코드": "code", "MODEL": "model", "품명": "ename", "Q'TY": "eqty", "QTY": "eqty",
    "ORIGIN": "origin", "원산지": "origin", "SUPPLIER": "supplier", "MANUFACTURER": "maker", "MANUFATURER": "maker",
    "CATEGORY": "category", "HSCODE": "hs", "TÊNHÀNG": "vn", "TENHANG": "vn", "SHIPPINGDATE": "ship", "발송일": "ship",
    "IMAGE": "image", "INVOICE%": "inv_pct", "C/O": "co", "SIZE": "size",
    # 옛 양식에만 있는 칸 — 최종 양식에 자리가 없어 뺀다(이름은 보고용)
    "DUTY": "-duty", "VAT": "-vat", "DUTYAMOUNT": "-duty_amt", "VATAMOUNT": "-vat_amt", "HSCODECHECK": "-hs_check",
    "LOẠIHÌNH": "-loai_hinh", "LOAIHINH": "-loai_hinh", "MALH": "-ma_lh",
}
# 뜻 → 화면에 보일 칸 이름
_LABEL = {"company": "COMPANY", "code": "관리코드", "model": "MODEL", "ename": "품명", "eqty": "Q'TY", "origin": "ORIGIN",
          "supplier": "SUPPLIER", "maker": "Manufacturer", "category": "CATEGORY", "hs": "HS CODE", "vn": "Tên hàng",
          "ship": "SHIPPING DATE(발송일)", "image": "IMAGE", "inv_pct": "invoice %", "co": "C/O", "size": "SIZE"}
# 뜻이 비면 대신 쓸 칸(수책 SUPPLIER ← 옛 Manufacturer · 일반 Manufacturer ← 옛 SUPPLIER)
_FALLBACK = {"supplier": "maker", "maker": "supplier"}
_CODE = re.compile(r"^\d{3}M\d{4}$")                       # 관리코드(예: 006M2510)
_EQUIP = re.compile(r"^\s*'?\s*(.+?)\s*[\(（]?\s*(\d+)\s*대\s*[\)）]?\s*$")   # 「CTC 부착기(6대)」 · 「Fold 부착기(CTC) 2대」
_DIM = re.compile(r"\d\s*[*xX×]\s*\d")                     # 「85*48*1.6(H) / FR4」 같은 크기
_TOTAL = H.TOTAL_ROW
PHOTO_BOX = (821100, 360000)     # IMAGE 칸 안 그림 크기 상한(EMU) — 대표 최종 양식 사진과 같은 크기(가로 86 · 세로 38 화소쯤)


def _norm(s) -> str:
    return re.sub(r"[\s.]+", "", str(s if s is not None else "")).upper()


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _mean_of(label) -> str:
    n = _norm(label)
    if n in _MEAN:
        return _MEAN[n]
    if n.startswith("HSCODECHECK"):
        return "-hs_check"
    if n in ("HSCODE", "HS"):
        return "hs"
    return ""


def _book(data: bytes) -> dict:
    """엑셀 bytes → {zip, paths:[(이름, 상태, 경로)], ss, cells(경로) — 칸 사전을 한 번만 읽어 둔다}"""
    z = zipfile.ZipFile(io.BytesIO(data))
    bk = {"zip": z, "paths": H._sheet_paths(z), "ss": H.shared_strings(z), "_c": {}}

    def cells(path):
        if path not in bk["_c"]:
            bk["_c"][path] = H.sheet_cells(z, path, bk["ss"])
        return bk["_c"][path]
    bk["cells"] = cells
    return bk


def _v(cells, r, c):
    x = cells.get((r, c))
    return x[0] if x else None


def _f(cells, r, c):
    x = cells.get((r, c))
    return x[1] if x else None


# ─────────────────────────────────────────────────────────────
# 틀(최종 양식) — 시트 · 머리글 줄 · 첫·끝 품목 줄 · 합계 줄 · 오른쪽 칸 뜻
# ─────────────────────────────────────────────────────────────
_TPL_CACHE = {}


def _template(kind: str) -> dict:
    """{bytes, sheets:{INV:{name, path, head, first, last, total, cols:{뜻: 칸}, no_cell, date_cell, sail_cell, vmerge,
                           header:{(줄,칸): 값}}, PL:{…, box:{no,size,weight: 칸}}}}"""
    if kind in _TPL_CACHE:
        return _TPL_CACHE[kind]
    data = open(os.path.join(SEED_DIR, TEMPLATES[kind]), "rb").read()
    bk = _book(data)
    out = {"bytes": data, "sheets": {}}
    for name, _st, path in bk["paths"]:
        cells = bk["cells"](path)
        head = next((r for r in range(1, 60) if any(isinstance(_v(cells, r, c), str) and "Description" in _v(cells, r, c)
                                                     for c in range(1, 10))), None)
        if not head:
            continue
        top = max((r for r, _ in cells), default=head)
        total = next((r for r in range(head + 1, top + 1) if isinstance(_v(cells, r, 1), str) and _TOTAL.match(_v(cells, r, 1))), None)
        is_pl = bool(re.search(r"PACK", name, re.I))
        info = {"name": name, "path": path, "head": head, "first": head + 3, "last": (total or head + 4) - 2, "total": total,
                "cols": {}, "box": {}}
        for c in range(10, 27):
            v = _v(cells, head, c)
            if isinstance(v, str) and v.strip():
                m = _mean_of(v)
                if m:
                    info["cols"][m] = c
                bm = {"NO": "no", "SIZE": "size", "WEIGHT": "weight", "G/W": "weight"}.get(_norm(v))
                if bm and is_pl:
                    info["box"][bm] = c
        info.update(_label_cells(cells))
        info["header"] = {(r, c): _v(cells, r, c) for r in range(1, 31) for c in range(1, 10) if not _blank(_v(cells, r, c))}
        info["hcells"] = {(r, c): cells[(r, c)] for (r, c) in cells if r <= head - 1 and c <= 10}
        x = bk["zip"].read(path).decode("utf-8")
        info["vmerge"] = set()
        for m in re.finditer(r'<mergeCell ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"', x):
            if m.group(1) == m.group(3) and int(m.group(2)) <= info["first"] and int(m.group(4)) >= info["last"]:
                info["vmerge"].add(H._col_num(m.group(1)))
        out["sheets"]["PL" if is_pl else "INV"] = info
    _TPL_CACHE[kind] = out
    return out


# 머리 칸 묶음 — 제목 글자로 찾고(옛 양식은 줄이 밀린 것이 있다: 260508 은 4줄) 원본과 최종 틀이 다르면 원본 묶음을 통째로 옮긴다
#   (제목 줄 기준 아래 줄 수 · 왼쪽부터 칸 수). 보내는 곳 · 받는 곳(주소 · TAX ID · TEL)은 최종 양식 것을 쓴다.
#   10-28 실측: INCOTERMS D.A.P 7 · F.O.B 2 · D.D.U 2 · 「No payment as processing」·「Contract No.」(260824_R1) — 인보이스마다 다르다
_HBLOCKS = [
    ("9) L/C · 결제", r"No\.?\s*&\s*Date\s*of\s*L/?C", 5, 4),
    ("10) Issuing Bank", r"Issuing\s*Bank", 5, 4),
    ("3) Notify Party", r"Notify\s*Party", 4, 5),
    ("11) Remarks(INCOTERMS)", r"^\s*\d*\)?\s*Remarks\s*$", 4, 4),
    ("4) Port of Loading", r"Port\s*of\s*Loading", 3, 3),
    ("5) Final Destination", r"Final\s*Destination", 3, 2),
    ("6) Carrier", r"^\s*\d*\)?\s*Carrier\s*$", 2, 3),
]


def _find_label(get, rx, max_r=40) -> tuple:
    for r in range(1, max_r + 1):
        for c in range(1, 10):
            v = get(r, c)
            if isinstance(v, str) and len(v) < 40 and re.search(rx, v, re.I):
                return r, c
    return None


def _header_blocks(src_get, tpl_cells) -> tuple:
    """원본 머리 ↔ 최종 틀 머리 — 다른 묶음은 원본 값을 틀 자리로({(줄,칸): 값}) · 옮긴 묶음 목록. 틀 칸이 수식이면 안 건드림."""
    def tget(r, c):
        x = tpl_cells.get((r, c))
        return x[0] if x else None
    writes, moved = {}, []
    st, tt = src_get(1, 1), tget(1, 1)
    if not _blank(st) and _norm(st) != _norm(tt) and not (tpl_cells.get((1, 1)) or (None, None))[1]:
        writes[(1, 1)] = st
        moved.append({"block": "문서 제목", "src": [str(st).strip()], "final": [str(tt or "").strip()]})
    for name, rx, nr, nc in _HBLOCKS:
        ls, lt = _find_label(src_get, rx), _find_label(tget, rx)
        if not ls or not lt:
            continue
        sv = {(dr, dc): src_get(ls[0] + dr, ls[1] + dc) for dr in range(1, nr + 1) for dc in range(nc)}
        tv = {(dr, dc): tget(lt[0] + dr, lt[1] + dc) for dr in range(1, nr + 1) for dc in range(nc)}
        if all(_same(sv[k], tv[k]) for k in sv):
            continue
        for (dr, dc), v in sv.items():
            pos = (lt[0] + dr, lt[1] + dc)
            if (tpl_cells.get(pos) or (None, None))[1]:
                continue                                     # 틀 칸이 수식(패킹 → 인보이스)이면 그대로
            if not (_blank(v) and _blank(tv[(dr, dc)])):
                writes[pos] = v
        moved.append({"block": name, "src": [str(v).strip() for v in sv.values() if not _blank(v)],
                      "final": [str(v).strip() for v in tv.values() if not _blank(v)]})
    return writes, moved


def _label_cells(cells) -> dict:
    """머리(1~30줄)에서 번호 칸(DATE: 라벨 왼쪽) · 날짜 칸(DATE: 오른쪽) · 선적일 칸(Sailing On or About 아래) → (줄, 칸)."""
    out = {"no_cell": None, "date_cell": None, "sail_cell": None}
    for r in range(1, 31):
        for c in range(1, 12):
            v = _v(cells, r, c)
            if not isinstance(v, str):
                continue
            if out["date_cell"] is None and H.HEAD_DATE.match(v):
                out["date_cell"] = (r, c + 1)
                out["no_cell"] = (r, c - 1)
            if out["sail_cell"] is None and "Sailing On or About" in v:
                out["sail_cell"] = (r + 1, c)
    return out


# ─────────────────────────────────────────────────────────────
# 원본(옛 양식) 읽기
# ─────────────────────────────────────────────────────────────
def layout_kind(data: bytes, bk=None):
    """이미 최종 양식이면 '수책'·'소모품'(인보이스 머리글 줄의 오른쪽 칸 제목이 틀과 같은 자리 — 틀 칸이 모두 제자리면
    직원이 덧붙인 칸(비고 등)이 더 있어도 최종 양식: 다시 바꾸면 그 칸이 빠진다) · 아니면 None."""
    try:
        bk = bk or _book(data)
    except zipfile.BadZipFile:
        return None
    for kind in ("수책", "소모품"):
        t = _template(kind)["sheets"]["INV"]
        want = {c: m for m, c in t["cols"].items()}
        for name, st, path in bk["paths"]:
            if st != "visible" or re.search(r"PACK", name, re.I) or path not in bk["zip"].namelist():
                continue
            cells = bk["cells"](path)
            got = {c: _mean_of(_v(cells, t["head"], c)) for c in range(10, 27)
                   if isinstance(_v(cells, t["head"], c), str) and _v(cells, t["head"], c).strip()}
            if got and all(got.get(c) == m for c, m in want.items()):
                return kind
    return None


def extract(data: bytes, bk=None) -> dict:
    """옛 인보이스 → {no, date, sail, items:[{sheet,row,left:{칸:값},right:{뜻:값},unl:{칸:값},amount_f}], equip, pl, right, dropped,
    unlabeled, header, photos, sheets}"""
    bk = bk or _book(data)
    sc = H.scan_fast(data)
    if not sc["sheets"]:
        raise ValueError("인보이스 시트를 찾지 못했습니다")
    src = {"invoice_no": sc.get("invoice_no") or "", "items": [], "equip": {}, "pl": {"items": [], "box": {}, "unl": {}},
           "right": {}, "dropped": {}, "header": {}, "sheets": [s["title"] for s in sc["sheets"]], "sheet_nos": [],
           "layout_bad": [], "no": None, "date": None, "sail": None}
    for si, sh in enumerate(sc["sheets"]):
        cells = bk["cells"](sh["path"])
        top = max((r for r, _ in cells), default=0)
        nc = _label_cells(cells)["no_cell"]
        src["sheet_nos"].append((sh["title"], _v(cells, *nc) if nc else None))
        if si == 0:
            lc = _label_cells(cells)
            for key in ("no", "date", "sail"):
                rc = lc[key + "_cell"]
                if rc:
                    src[key] = _v(cells, *rc)
            src["equip"] = _equip_block(cells)
        ds = next((r for r in range(1, 46) if any(isinstance(_v(cells, r, c), str) and "Description" in _v(cells, r, c)
                                                  for c in range(1, 10))), 31)
        # KNK 인보이스 칸 모양(머리글 줄 D 품명 · F 수량 · H 단가 · I 금액 · HS 는 J 오른쪽)만 옮긴다 — 10-28 실측 59 시트 모두 이 모양.
        #   다른 표(머리글만 맞는 간단한 표 등)는 칸 뜻이 달라 옮기면 엉뚱한 칸에 들어간다 → 바꾸지 않음(convert)
        hd = {c: _norm(_v(cells, ds, c)) for c in (4, 6, 8, 9)}
        if not ("DESCRIPTION" in hd[4] and re.search(r"Q'?TY", hd[6]) and "PRICE" in hd[8] and "AMOUNT" in hd[9]
                and sh["col_hs"] >= 10):
            src["layout_bad"].append(sh["title"])
        if si == 0:
            src["header"] = {(r, c): _v(cells, r, c) for r in range(1, ds) for c in range(1, 11) if not _blank(_v(cells, r, c))}
        # 머리글 줄 = Description 줄 + 그 아래 3줄 안에서 D 가 비고 오른쪽에 아는 제목이 있는 줄(옛 양식은 31~33줄에 나눠 적었다 —
        #   260507 은 33줄에 CATEGORY 만 · 그 줄을 품목으로 읽으면 안 된다) + HS·Tên hàng 제목 줄
        hdr_rows = {ds, sh["header_row"]}
        for r in range(ds + 1, ds + 4):
            if _blank(_v(cells, r, 4)) and any(isinstance(_v(cells, r, c), str) and (_mean_of(_v(cells, r, c)) or H.HEAD_VN.search(_v(cells, r, c)))
                                               for c in range(10, 27)):
                hdr_rows.add(r)
        start = max(hdr_rows) + 1
        labels = {}
        for c in range(10, 27):
            for r in sorted(hdr_rows, reverse=True):
                v = _v(cells, r, c)
                if isinstance(v, str) and v.strip():
                    labels[c] = v.strip()
                    break
        means = {c: _mean_of(t) for c, t in labels.items()}
        for c in list(means):
            if means[c] in ("hs", "vn"):
                means[c] = ""
        means[sh["col_hs"]] = "hs"                 # HS · Tên hàng 칸은 hs_fill.scan 이 고른 칸 그대로(같은 규칙)
        if sh.get("col_vn"):
            means[sh["col_vn"]] = "vn"
        for c, t in labels.items():
            src["right"].setdefault(c, t)
        rows = []
        for r in range(start, top + 1):
            if any(isinstance(_v(cells, r, c), str) and _TOTAL.match(_v(cells, r, c)) for c in range(1, 5)):
                break
            vals = {c: _v(cells, r, c) for c in range(1, 27) if not _blank(_v(cells, r, c))}
            if vals:
                rows.append((r, vals))
        # 제목 없는 칸의 뜻 — 베트남어 글이면 Tên hàng(260402 · 260420 · 260804-1 은 제목이 없다) · 'A41' 꼴이면 수입 유형(MA LH) ·
        #   제목 붙은 칸보다 오른쪽이면 표 밖 계산 칸 · J 는 줄마다(_row_values)
        last_lab = max([c for c in labels] + [sh["col_hs"], sh.get("col_vn") or 0])
        for c in range(11, 27):
            if c in labels or c == sh["col_hs"] or c == sh.get("col_vn"):
                continue
            k = _col_kind([vals[c] for _, vals in rows if c in vals], c, last_lab)
            if k == "vn":
                k = "vn" if "vn" not in means.values() else "vn2"
            if k:
                means[c] = k
        for r, vals in rows:
            # 옛 양식에만 있는 칸(Duty·VAT …)에만 값이 있는 줄은 품목 줄로 넣지 않는다(뺀 값으로만 센다)
            if not any(c <= 10 or not means.get(c, "").startswith("-") for c in vals):
                for c, v in vals.items():
                    _drop(src, labels.get(c, H._col_letter(c)), means.get(c, ""), v)
                continue
            it = {"sheet": sh["title"], "row": r, "left": {}, "right": {}, "unl": {}, "amount_f": _f(cells, r, 9)}
            for c, v in vals.items():
                if c < 10:
                    it["left"][c] = v
                    continue
                m = means.get(c, "")
                if m and not m.startswith("-"):
                    it["right"].setdefault(m, v)
                elif m.startswith("-"):
                    _drop(src, labels.get(c, H._col_letter(c)), m, v)
                else:
                    it["unl"][c] = v
            src["items"].append(it)
    pl = next(((n, p) for n, st, p in bk["paths"] if re.search(r"PACK", n, re.I) and st == "visible"
               and p in bk["zip"].namelist()), None)
    if pl:
        src["pl"] = _pl_extract(bk["cells"](pl[1]))
    src["photos"] = _photos(bk["zip"], sc, src)
    return src


_VN_CH = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]|#&", re.I)
_WHY = {
    "-duty": "옛 양식에만 있던 칸(최종 양식에서 없앰)", "-vat": "옛 양식에만 있던 칸(최종 양식에서 없앰)",
    "-duty_amt": "옛 양식에만 있던 칸(최종 양식에서 없앰)", "-vat_amt": "옛 양식에만 있던 칸(최종 양식에서 없앰)",
    "-hs_check": "옛 양식에만 있던 칸(최종 양식에서 없앰)", "-loai_hinh": "옛 양식에만 있던 칸(최종 양식에서 없앰)",
    "-ma_lh": "수입 유형 코드(MA LH · 최종 양식에서 없앰)", "-outside": "표 밖 계산 칸(제목 없음)",
    "unl": "제목 없는 칸", "no_place": "최종 양식에 그 칸이 없음", "vn2": "Tên hàng 이 두 칸 — 앞 칸 값을 옮김",
    "size_no_place": "수책통관 최종 양식에 SIZE 칸이 없음", "photo": "수책통관 최종 양식에 사진 칸이 없음",
    "g": "G 칸(수량 F:G 합친 칸) 값", "pl_unl": "패킹리스트 제목 없는 칸(메모·계산)",
}


def _drop(src_or_report, label, why_key, value):
    """뺀 값 셈 — {이름: {n, why, ex:[예 3개]}} (src['dropped'] 또는 report['dropped'])."""
    d = src_or_report.setdefault("dropped", {})
    e = d.setdefault(str(label), {"n": 0, "why": _WHY.get(why_key, why_key or "제목 없는 칸"), "ex": []})
    e["n"] += 1
    s = str(value).strip()[:40]
    if s and s not in e["ex"] and len(e["ex"]) < 3:
        e["ex"].append(s)


def _col_kind(values, c, last_lab) -> str:
    """제목 없는 칸(J 제외) 뜻 — 'vn'(베트남어 글이 반 넘게) · '-ma_lh'('A41' 꼴만) · '-outside'(제목 칸보다 오른쪽) · ''."""
    vals = [str(v).strip() for v in values if not _blank(v)]
    if not vals:
        return ""
    if sum(1 for v in vals if _VN_CH.search(v)) * 2 >= len(vals):
        return "vn"
    if all(re.fullmatch(r"[A-Z]\d{2}", v) for v in vals):
        return "-ma_lh"
    if c > last_lab:
        return "-outside"
    return ""


def _equip_block(cells) -> dict:
    """표 위 장비 묶음 → {관리코드: {model, ename, eqty}} — 제목이 'MODEL·품명·수량' 또는 '품명·품명·금액'(260824)."""
    for r in range(18, 31):
        for c in range(10, 23):
            if _norm(_v(cells, r, c)) != "관리코드":
                continue
            heads = [(cc, _norm(_v(cells, r, cc))) for cc in range(c + 1, c + 8) if not _blank(_v(cells, r, cc))]
            col_model = next((cc for cc, t in heads if t == "MODEL"), None)
            names = [cc for cc, t in heads if t == "품명"]
            if col_model is None and len(names) >= 2:
                col_model, col_en = names[0], names[1]
            else:
                col_en = names[0] if names else None
            col_qty = next((cc for cc, t in heads if t in ("수량", "Q'TY", "QTY")), None)
            out = {}
            for rr in range(r + 1, r + 31):
                code = _v(cells, rr, c)
                if _blank(code):
                    break
                out[str(code).strip()] = {"model": _v(cells, rr, col_model) if col_model else None,
                                          "ename": _v(cells, rr, col_en) if col_en else None,
                                          "eqty": _v(cells, rr, col_qty) if col_qty else None}
            return out
    return {}


def _pl_extract(cells) -> dict:
    head = next((r for r in range(20, 46) if any(isinstance(_v(cells, r, c), str) and "Description" in _v(cells, r, c)
                                                 for c in range(1, 10))), None)
    out = {"items": [], "box": {}, "head": head, "unl": {},
           "header": {(r, c): _v(cells, r, c) for r in range(1, (head or 36)) for c in range(1, 11) if not _blank(_v(cells, r, c))}}
    if not head:
        return out
    for c in range(11, 19):
        v = _v(cells, head, c)
        if isinstance(v, str):
            bm = {"NO": "no", "SIZE": "size", "G/W": "weight", "WEIGHT": "weight", "GW": "weight"}.get(_norm(v))
            if bm:
                out["box"][c] = bm
    top = max((r for r, _ in cells), default=head)
    for r in range(head + 2, top + 1):
        if any(isinstance(_v(cells, r, c), str) and _TOTAL.match(_v(cells, r, c)) for c in range(1, 5)):
            break
        vals = {c: _v(cells, r, c) for c in range(1, 19) if not _blank(_v(cells, r, c))}
        if not vals or all(isinstance(v, str) and _norm(v) == "WEIGHT" for v in vals.values()):
            continue                                            # 머리글 둘째 줄('Weight')
        it = {"row": r, "left": {}, "box": {}, "f": {}, "unl": {}}
        for c, v in vals.items():
            if c <= 10:
                it["left"][c] = v
                fv = _f(cells, r, c)
                if fv:
                    it["f"][c] = fv
            elif c in out["box"]:
                it["box"][out["box"][c]] = v
            else:
                it["unl"][c] = v
                out["unl"][c] = out["unl"].get(c, 0) + 1
        out["items"].append(it)
    return out


def _photos(z, sc, src) -> dict:
    """품목 줄에 걸친 그림 → {(시트, 줄): [{ext, bytes, cx, cy}]} — 한 줄에 여러 장이면 모두(문서 순서)."""
    names = set(z.namelist())
    rows_of = {}
    for it in src["items"]:
        rows_of.setdefault(it["sheet"], set()).add(it["row"])
    out = {}
    for sh in sc["sheets"]:
        items = rows_of.get(sh["title"], set())
        if not items:
            continue
        for dp in [t for t in H._rels(z, sh["path"]).values() if "/drawings/" in t and t.endswith(".xml") and t in names]:
            dx = z.read(dp).decode("utf-8", "replace")
            dr = H._rels(z, dp)
            for am in re.finditer(r"<((?:\w+:)?)(twoCellAnchor|oneCellAnchor)\b.*?</\1\2>", dx, re.S):
                a = am.group(0)
                if not re.search(r"<(?:\w+:)?pic\b", a):
                    continue
                fr = re.search(r"<(?:\w+:)?from>.*?<(?:\w+:)?row>(\d+)</", a, re.S)
                if not fr:
                    continue
                to = re.search(r"<(?:\w+:)?to>.*?<(?:\w+:)?row>(\d+)</", a, re.S)
                r0 = int(fr.group(1)) + 1
                r1 = max(r0, int(to.group(1)) + 1) if to else r0
                row = next((r for r in range(r0, r1 + 1) if r in items), None)
                if row is None:
                    continue
                ext = re.search(r"<a:ext\b[^>]*\bcx=\"(\d+)\"[^>]*\bcy=\"(\d+)\"", a)
                for e in re.findall(r'<(?:\w+:)?blip\b[^>]*?\br:embed="([^"]+)"', a):
                    mp = dr.get(e)
                    if mp and mp in names:
                        out.setdefault((sh["title"], row), []).append(
                            {"ext": mp.rsplit(".", 1)[-1].lower(), "bytes": z.read(mp),
                             "cx": int(ext.group(1)) if ext else 800000, "cy": int(ext.group(2)) if ext else 360000})
                        break
    return out


def guess_kind(src) -> tuple:
    """옛 양식 → ('수책'|'소모품', 근거) — 표시 점수: 수책 = 관리코드(006M2510 꼴 · 3) · 장비 묶음(3) · J 「장비명(N대)」(1) ·
    SUPPLIER · CATEGORY · Loại hình(각 1) / 일반 = invoice % · C/O · Manufacturer · IMAGE(각 1) · 품목 사진(1). 같으면 일반.
    (10-28 실측: 수책 폴더 260121-3 은 일반 칸 모양 · 260401 은 품목 사진이 있다 — 관리코드가 둘 다 수책으로 가른다)"""
    means = {_mean_of(t) for t in src["right"].values()}
    items = src["items"]
    n_code = sum(1 for it in items if any(_CODE.match(str(it["left"].get(c) or "").strip()) for c in (2, 3)))
    n_equip_txt = sum(1 for it in items if _EQUIP.match(str(it["unl"].get(10) or "")))
    s_sig = [m for m in ("supplier", "category", "-loai_hinh") if m in means]
    m_sig = [m for m in ("inv_pct", "co", "maker", "image") if m in means]
    s = len(s_sig) + (3 if items and n_code * 2 >= len(items) else 0) + (3 if src["equip"] else 0) + (1 if n_equip_txt else 0)
    m = len(m_sig) + (1 if src["photos"] else 0)
    # 근거 글은 화면에 그대로 보인다 — 칸 이름은 엑셀에 적힌 이름으로(SUPPLIER · invoice % …)
    name = dict(_LABEL, **{"-loai_hinh": "Loại hình"})
    if s > m:
        why = "수책통관 표시 %d(관리코드 %d줄%s%s) > 일반통관 표시 %d" % (
            s, n_code, " · 장비 묶음" if src["equip"] else "", "".join(" · " + name[x] for x in s_sig), m)
        return "수책", why
    return "소모품", "일반통관 표시 %d(%s%s) ≥ 수책통관 표시 %d" % (
        m, " · ".join(name[x] for x in m_sig) or "칸 없음", " · 품목 사진" if src["photos"] else "", s)


# ─────────────────────────────────────────────────────────────
# 줄 → 최종 양식 칸 값
# ─────────────────────────────────────────────────────────────
def _row_values(it, kind, src, tinfo, report) -> dict:
    """{칸 번호: 값} — 왼쪽 A~H(I 금액은 따로) + 오른쪽 뜻 칸."""
    out = {}
    for c in (1, 2, 3, 4, 5, 6, 8):
        if c in it["left"]:
            out[c] = it["left"][c]
    if 7 in it["left"]:
        _drop(report, "G", "g", it["left"][7])
    cols = tinfo["cols"]
    right = dict(it["right"])
    unl = dict(it["unl"])
    if "vn" not in right and "vn2" not in right:
        # Tên hàng 칸이 없거나 빈 줄인데 다른 칸에 베트남어 품명이 있으면 그것이 Tên hàng(260507 은 SIZE 칸에 적었다)
        for m, v in list(right.items()):
            if m not in ("hs",) and isinstance(v, str) and _VN_CH.search(v):
                right["vn"] = right.pop(m)
                report.setdefault("vn_rescued", {})[_LABEL.get(m, m)] = report.setdefault("vn_rescued", {}).get(_LABEL.get(m, m), 0) + 1
                break
        else:
            for c, v in list(unl.items()):
                if isinstance(v, str) and _VN_CH.search(v):
                    right["vn"] = unl.pop(c)
                    lb = H._col_letter(c)
                    report.setdefault("vn_rescued", {})[lb] = report.setdefault("vn_rescued", {}).get(lb, 0) + 1
                    break
    if "vn2" in right:                                       # Tên hàng 이 두 칸(제목 없음 · 260804-1) — 앞 칸이 비면 뒤 칸
        if "vn" not in right:
            right["vn"] = right.pop("vn2")
        else:
            _drop(report, "Tên hàng(둘째 칸)", "vn2", right.pop("vn2"))
    used = set()
    for m in ("supplier", "maker"):
        if m in cols and m not in right and _FALLBACK[m] in right:
            right[m] = right[_FALLBACK[m]]
            used.add(_FALLBACK[m])
            key = "%s←%s" % (m, _FALLBACK[m])
            report.setdefault("fallback", {})[key] = report.setdefault("fallback", {}).get(key, 0) + 1
    j = unl.get(10)
    if kind == "수책":
        code = next((str(it["left"].get(c)).strip() for c in (2, 3) if _CODE.match(str(it["left"].get(c) or "").strip())), "")
        if code and "code" in cols and "code" not in right:
            right["code"] = code
        eq = src["equip"].get(code) if code else None
        if eq:
            for m in ("model", "ename", "eqty"):
                if m not in right and not _blank(eq.get(m)):
                    right[m] = eq[m]
        if not _blank(j):
            mm = _EQUIP.match(str(j))
            if mm or not _DIM.search(str(j)):
                name, qty = (mm.group(1).strip(), int(mm.group(2))) if mm else (str(j).strip().lstrip("'").strip(), None)
                if "model" not in right:
                    right["model"] = name
                    report["j_model"] = report.get("j_model", 0) + 1
                else:
                    used.add("j")
                if "eqty" not in right and qty is not None:
                    right["eqty"] = qty
            else:
                _drop(report, "J(크기)", "size_no_place", j)         # 260420 J 「Ф84 * 128」 — 수책 최종 양식에 SIZE 칸 없음
    else:
        if not _blank(j):
            if _DIM.search(str(j)) and "size" not in right:
                right["size"] = j
                report["j_size"] = report.get("j_size", 0) + 1
            elif "company" not in right:
                right["company"] = j
                report["j_company"] = report.get("j_company", 0) + 1
            else:
                _drop(report, "J", "unl", j)
    for m, v in right.items():
        if m in cols and m != "image":
            out[cols[m]] = v
        elif m != "image" and m not in used:
            _drop(report, _LABEL.get(m, m), "no_place", v)
    for c, v in unl.items():
        if c != 10:
            _drop(report, H._col_letter(c), "unl", v)
    return out


# ─────────────────────────────────────────────────────────────
# XML — 수식 칸 주소 옮기기 · 공유 수식 풀기 · 줄 늘리기 · 칸 쓰기
# ─────────────────────────────────────────────────────────────
_REF = H._FREF
_CELL = re.compile(r'<c\b[^>]*?\br="([A-Z]+)(\d+)"[^>]*?(?:/>|>.*?</c>)', re.S)
_ROW = re.compile(r'<row\b[^>]*?\br="(\d+)"[^>]*?(?:/>|>.*?</row>)', re.S)


def _esc_f(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _shift_formula(f: str, shifts: dict, own: str) -> str:
    """수식 안 칸 주소 — 시트별 (끝 품목 줄 last, k): last 보다 아래 줄 주소는 k 만큼 내린다(절대 주소 포함 · 따옴표 글자 안 제외)."""
    out, pos, in_str = [], 0, False
    for m in _REF.finditer(f):
        seg = f[pos:m.start()]
        in_str ^= (seg.count('"') % 2 == 1)
        out.append(seg)
        pos = m.end()
        if in_str or (m.start() > 0 and (f[m.start() - 1].isalnum() or f[m.start() - 1] in "_.")):
            out.append(m.group(0))
            continue
        sheet = (m.group(1) or "")[:-1].strip("'") if m.group(1) else own
        last, k = shifts.get(sheet, (None, 0))
        row = int(m.group(5))
        if last is not None and k and row > last:
            row += k
        out.append("%s%s%s%s%d" % (m.group(1) or "", m.group(2), m.group(3), m.group(4), row))
    out.append(f[pos:])
    return "".join(out)


def _unshare(xml: str) -> str:
    """공유 수식을 칸마다 풀어 쓴다 — 줄을 늘리거나 칸을 값으로 바꿔도 엑셀이 '복구'를 묻지 않게."""
    masters = {}
    for cm in _CELL.finditer(xml):
        fm = re.search(r'<f\b([^>]*)>(.*?)</f>', cm.group(0), re.S)
        if fm and 't="shared"' in fm.group(1):
            si = re.search(r'\bsi="(\d+)"', fm.group(1)).group(1)
            masters[si] = (H._col_num(cm.group(1)), int(cm.group(2)), H._unesc(fm.group(2)))
    if not masters:
        return xml

    def fix(cm):
        cell = cm.group(0)
        fm = re.search(r'<f\b([^>]*?)(?:/>|>(.*?)</f>)', cell, re.S)
        if not fm or 't="shared"' not in fm.group(1):
            return cell
        si = re.search(r'\bsi="(\d+)"', fm.group(1)).group(1)
        c0, r0, text = masters[si]
        new = "<f>%s</f>" % _esc_f(H.translate_formula(text, int(cm.group(2)) - r0, H._col_num(cm.group(1)) - c0))
        return cell[:fm.start()] + new + cell[fm.end():]
    return _CELL.sub(fix, xml)


def _shift_range(ref: str, first: int, last: int, k: int, extend: bool) -> str:
    """'A1:B2' 또는 'A1' — last 아래면 내리고, extend 이고 끝 품목 줄(last)을 덮으면(시작 ≤ last ≤ 끝) 끝만 늘린다."""
    m = re.match(r"^(\$?[A-Z]{1,3}\$?)(\d+)(?::(\$?[A-Z]{1,3}\$?)(\d+))?$", ref)
    if not m:
        return ref
    c1, r1 = m.group(1), int(m.group(2))
    c2, r2 = (m.group(3), int(m.group(4))) if m.group(3) else (c1, r1)
    if r1 > last:
        r1 += k
        r2 = r2 + k if r2 < 1048576 else r2
    elif extend and r2 >= last and r2 < 1048576:
        r2 += k
    return "%s%d" % (c1, r1) if not m.group(3) else "%s%d:%s%d" % (c1, r1, c2, min(r2, 1048576))


def _renumber_row(row_xml: str, r_old: int, r_new: int) -> str:
    row_xml = re.sub(r'(<row\b[^>]*?\br=")%d(")' % r_old, r"\g<1>%d\g<2>" % r_new, row_xml, count=1)
    return re.sub(r'(<c\b[^>]*?\br="[A-Z]+)%d(")' % r_old, r"\g<1>%d\g<2>" % r_new, row_xml)


def _fix_formulas_all(xml: str, shifts: dict, own: str) -> str:
    return re.sub(r"(<f\b[^>]*>)(.*?)(</f>)",
                  lambda fm: fm.group(1) + _esc_f(_shift_formula(H._unesc(fm.group(2)), shifts, own)) + fm.group(3), xml, flags=re.S)


def _new_row(pat_xml: str, r_pat: int, r_new: int) -> str:
    """끝 품목 줄 모양으로 새 줄 — 값은 비우고 서식은 그대로 · 수식(금액)은 그 줄 주소로."""
    x = _renumber_row(pat_xml, r_pat, r_new)

    def cell(cm):
        c = cm.group(0)
        head = c[:c.index(">") + 1]
        if head.endswith("/>"):
            return c
        f = re.search(r"<f\b[^>]*>(.*?)</f>", c, re.S)
        head = re.sub(r'\s+t="[^"]*"', "", head)
        if f:
            return head + "<f>%s</f></c>" % _esc_f(H.translate_formula(H._unesc(f.group(1)), r_new - r_pat))
        return head[:-1] + "/>"
    return _CELL.sub(cell, x)


def _expand(xml: str, first: int, last: int, k: int, own: str, shifts: dict) -> str:
    """품목 끝 줄(last) 뒤에 k 줄을 끼운다 — 새 줄은 끝 줄 모양(서식·병합·금액 수식) · 그 아래는 모두 k 만큼 내린다."""
    rows = list(_ROW.finditer(xml))
    if not any(int(m.group(1)) == last for m in rows):
        raise ValueError("틀의 끝 품목 줄(%d)을 찾지 못했습니다" % last)
    pieces, pos = [], 0
    for m in rows:
        r = int(m.group(1))
        pieces.append(xml[pos:m.start()])
        pos = m.end()
        row_xml = _fix_formulas_all(m.group(0), shifts, own)
        if r > last:
            row_xml = _renumber_row(row_xml, r, r + k)
        pieces.append(row_xml)
        if r == last:
            pieces += [_new_row(m.group(0), last, last + i) for i in range(1, k + 1)]
    pieces.append(xml[pos:])
    xml = "".join(pieces)
    mc = re.search(r"<mergeCells\b[^>]*>(.*?)</mergeCells>", xml, re.S)
    if mc:
        new_refs = []
        for ref in re.findall(r'<mergeCell ref="([^"]+)"/>', mc.group(1)):
            mm = re.match(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$", ref)
            if not mm:
                new_refs.append(ref)
                continue
            r1, r2 = int(mm.group(2)), int(mm.group(4))
            if r1 > last:
                new_refs.append("%s%d:%s%d" % (mm.group(1), r1 + k, mm.group(3), r2 + k))
            elif r1 <= first and r2 >= last:                      # 품목 덩어리를 세로로 덮는 병합(패킹 중량) — 늘림
                new_refs.append("%s%d:%s%d" % (mm.group(1), r1, mm.group(3), r2 + k))
            else:
                new_refs.append(ref)
                if r1 == r2 == last:                              # 끝 줄 병합(F:G) — 새 줄마다
                    new_refs += ["%s%d:%s%d" % (mm.group(1), last + i, mm.group(3), last + i) for i in range(1, k + 1)]
        head = re.sub(r'\bcount="\d+"', 'count="%d"' % len(new_refs), mc.group(0)[:mc.group(0).index(">") + 1])
        xml = xml[:mc.start()] + head + "".join('<mergeCell ref="%s"/>' % r for r in new_refs) + "</mergeCells>" + xml[mc.end():]

    def sq(m, extend=True):
        return m.group(1) + " ".join(_shift_range(r, first, last, k, extend) for r in m.group(2).split()) + m.group(3)
    xml = re.sub(r'(<conditionalFormatting\b[^>]*\bsqref=")([^"]+)(")', sq, xml)
    xml = re.sub(r'(<dataValidation\b[^>]*\bsqref=")([^"]+)(")', sq, xml)
    xml = re.sub(r'(<autoFilter\b[^>]*\bref=")([^"]+)(")', sq, xml)
    xml = re.sub(r'(<hyperlink\b[^>]*\bref=")([^"]+)(")', lambda m: sq(m, False), xml)
    xml = re.sub(r'(<dimension ref="[A-Z]+\d+:[A-Z]+)(\d+)(")', lambda m: "%s%d%s" % (m.group(1), int(m.group(2)) + k, m.group(3)), xml)
    xml = re.sub(r'(<brk\b[^>]*\bid=")(\d+)(")',
                 lambda m: "%s%d%s" % (m.group(1), int(m.group(2)) + (k if int(m.group(2)) > last else 0), m.group(3)), xml)
    return xml


def _cell_xml(ref: str, style, v) -> str:
    st = (' s="%s"' % style) if style is not None else ""
    if _blank(v):
        return '<c r="%s"%s/>' % (ref, st)
    if isinstance(v, tuple) and v[0] == "f":
        return '<c r="%s"%s><f>%s</f></c>' % (ref, st, _esc_f(v[1]))
    if isinstance(v, bool):
        return '<c r="%s"%s t="b"><v>%d</v></c>' % (ref, st, 1 if v else 0)
    if isinstance(v, (_dt.datetime, _dt.date)):
        if not isinstance(v, _dt.datetime):
            v = _dt.datetime(v.year, v.month, v.day)
        v = (v - _dt.datetime(1899, 12, 30)).total_seconds() / 86400.0
    if isinstance(v, (int, float)):
        return '<c r="%s"%s><v>%s</v></c>' % (ref, st, repr(v) if isinstance(v, float) else str(v))
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(v))
    return '<c r="%s"%s t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, st, _xml_escape(s))


def _write_cells(xml: str, writes: dict, style_col: dict) -> str:
    """writes = {(줄, 칸): 값} — 칸 서식은 그 칸 것(없으면 같은 칸 첫 품목 줄 서식) · 값만 바꾼다."""
    by_row = {}
    for (r, c), v in writes.items():
        by_row.setdefault(r, {})[c] = v

    def fix_row(rm):
        r = int(rm.group(1))
        if r not in by_row:
            return rm.group(0)
        row_xml = rm.group(0)
        if row_xml.rstrip().endswith("/>") and "</row>" not in row_xml:
            head, body = row_xml.rstrip()[:-2] + ">", ""
        else:
            head = row_xml[:row_xml.index(">") + 1]
            body = row_xml[len(head):-len("</row>")]
        cells, order = {}, []
        for cm in _CELL.finditer(body):
            c = H._col_num(cm.group(1))
            cells[c] = cm.group(0)
            order.append(c)
        for c, v in by_row[r].items():
            old = cells.get(c)
            sm = re.search(r'\bs="(\d+)"', old[:old.index(">") + 1]) if old else None
            cells[c] = _cell_xml("%s%d" % (H._col_letter(c), r), sm.group(1) if sm else style_col.get(c), v)
            if c not in order:
                order.append(c)
        order.sort()
        sp = re.search(r'\bspans="(\d+):(\d+)"', head)
        if sp and order and order[-1] > int(sp.group(2)):
            head = head.replace(sp.group(0), 'spans="%s:%d"' % (sp.group(1), order[-1]))
        return head + "".join(cells[c] for c in order) + "</row>"
    return _ROW.sub(fix_row, xml)


def _styles_of_row(xml: str, r: int) -> dict:
    m = next((m for m in _ROW.finditer(xml) if int(m.group(1)) == r), None)
    out = {}
    if m:
        for cm in _CELL.finditer(m.group(0)):
            sm = re.search(r'\bs="(\d+)"', cm.group(0)[:cm.group(0).index(">") + 1])
            if sm:
                out[H._col_num(cm.group(1))] = sm.group(1)
    return out


def _shift_drawing(dx: str, last: int, k: int) -> str:
    """그림판 — last 줄 아래(0부터 센 줄 ≥ last)에 걸린 그림은 k 줄 내린다(서명·도장)."""
    return re.sub(r"(<(?:\w+:)?row>)(\d+)(</(?:\w+:)?row>)",
                  lambda m: "%s%d%s" % (m.group(1), int(m.group(2)) + (k if int(m.group(2)) >= last else 0), m.group(3)), dx)


def _defined_names(wbx: str, sheet: str, first: int, last: int, k: int) -> str:
    """인쇄 영역 · 필터 이름 — 그 시트 주소만 내리거나 늘린다."""
    def one(m):
        body = m.group(2)

        def ref(mm):
            return mm.group(1) + _shift_range(mm.group(2), first, last, k, True)
        return m.group(1) + re.sub(r"('?%s'?!)(\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?)" % re.escape(sheet), ref, body) + m.group(3)
    return re.sub(r"(<definedName\b[^>]*>)(.*?)(</definedName>)", one, wbx, flags=re.S)


# ─────────────────────────────────────────────────────────────
# 저장값 — 틀의 합계 칸 · 패킹 머리 참조 칸에는 대표 원본(261015 · 260921)의 값이 저장값으로 남아 있다(10-28 실측: TOTAL = 261015 합계 ·
#   패킹 G4 KNK-261015-1). 엑셀은 열 때 다시 계산하지만(fullCalcOnLoad) 이음 미리보기 · 아이폰 보기처럼 다시 계산 안 하는 화면은
#   저장값을 그대로 보여 준다 → 바꾼 시트의 수식 칸은 저장값을 새로 센다(SUM · 사칙 · 칸 참조). 못 세는 수식은 저장값을 지운다
#   (틀린 숫자보다 빈칸 · 엑셀은 열 때 센다).
# ─────────────────────────────────────────────────────────────
_ETOK = re.compile(r"\s*(?:(?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)|(?P<fn>SUM)\s*\(|"
                   r"(?P<ref>(?:(?:'[^']+'|[A-Za-z_][\w.]*)!)?\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?)|(?P<op>[-+*/(),]))", re.I)
_NOVAL = object()


class _NoCalc(Exception):
    pass


def _calc_formula(f: str, get, own: str):
    """수식 하나 — SUM(범위 · 칸 · 식) · + - * / · 괄호 · 칸 참조(다른 시트 포함)만. 그 밖은 _NoCalc.
    엑셀처럼: 빈 칸 = 0 · 앞의 + 는 글자도 그대로 · SUM 안 범위의 글자는 건너뜀 · 셈에 글자가 끼면 못 셈."""
    toks, pos, f = [], 0, f.strip()
    while pos < len(f):
        m = _ETOK.match(f, pos)
        if not m or m.end() == pos:
            raise _NoCalc(f)
        k = next(n for n in ("num", "fn", "ref", "op") if m.group(n) is not None)
        toks.append((k, m.group(k).upper() if k == "fn" else m.group(k)))
        pos = m.end()
    i = [0]

    def peek(d=0):
        return toks[i[0] + d] if i[0] + d < len(toks) else (None, None)

    def take():
        i[0] += 1
        return toks[i[0] - 1] if i[0] <= len(toks) else (None, None)

    def num(v):
        if v is _NOVAL:
            raise _NoCalc("못 센 칸")
        if v is None:
            return 0
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, (int, float)):
            return v
        raise _NoCalc("글자 셈")

    def cells_of(ref):
        sheet, rng = own, ref.replace("$", "")
        if "!" in rng:
            sheet, rng = rng.rsplit("!", 1)
            sheet = sheet.strip("'")
        a, _, b = rng.partition(":")
        ma, mb = re.match(r"([A-Z]+)(\d+)$", a, re.I), re.match(r"([A-Z]+)(\d+)$", b or a, re.I)
        c1, c2 = sorted((H._col_num(ma.group(1).upper()), H._col_num(mb.group(1).upper())))
        r1, r2 = sorted((int(ma.group(2)), int(mb.group(2))))
        if (r2 - r1 + 1) * (c2 - c1 + 1) > 200000:
            raise _NoCalc("범위가 너무 큼")
        return [get(sheet, r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]

    def atom():
        k, t = take()
        if k == "num":
            return float(t) if re.search(r"[.eE]", t) else int(t)
        if k == "ref":
            if ":" in t:
                raise _NoCalc("범위는 SUM 안에서만")
            return cells_of(t)[0]
        if k == "fn":                                          # SUM(…)
            total = 0
            if peek() == ("op", ")"):
                take()
                return total
            while True:
                if peek()[0] == "ref" and peek(1) in (("op", ","), ("op", ")")):
                    for v in cells_of(take()[1]):
                        if v is _NOVAL:
                            raise _NoCalc("못 센 칸")
                        if isinstance(v, (int, float)) and not isinstance(v, bool):
                            total += v
                else:
                    total += num(expr())
                sep = take()
                if sep == ("op", ")"):
                    return total
                if sep != ("op", ","):
                    raise _NoCalc(f)
        if (k, t) == ("op", "("):
            v = expr()
            if take() != ("op", ")"):
                raise _NoCalc(f)
            return v
        raise _NoCalc(f)

    def unary():
        if peek() == ("op", "+"):
            take()
            return unary()
        if peek() == ("op", "-"):
            take()
            return -num(unary())
        return atom()

    def term():
        v = unary()
        while peek() in (("op", "*"), ("op", "/")):
            op = take()[1]
            a, b = num(v), num(unary())
            if op == "/" and b == 0:
                raise _NoCalc("0으로 나눔")
            v = a * b if op == "*" else a / b
        return v

    def expr():
        v = term()
        while peek() in (("op", "+"), ("op", "-")):
            op = take()[1]
            a, b = num(v), num(term())
            v = a + b if op == "+" else a - b
        return v

    v = expr()
    if i[0] != len(toks):
        raise _NoCalc(f)
    if v is _NOVAL:
        raise _NoCalc("못 센 칸")
    return 0 if v is None else v


def _num_txt(v) -> str:
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)
    return str(v)


def _recalc(sheets_x: dict, ss) -> tuple:
    """sheets_x = {시트 이름: 시트 XML} → ({시트 이름: 저장값 고친 XML}, {calc: 센 수, cleared: 지운 수, ex: 못 센 수식 예})."""
    cells = {name: H.sheet_cells_xml(x, ss) for name, x in sheets_x.items()}
    memo, busy = {}, set()

    def get(sheet, r, c):
        key = (sheet, r, c)
        if key in memo:
            return memo[key]
        cell = cells.get(sheet, {}).get((r, c))
        if cell is None:
            return None
        val, f = cell
        if f is None:
            return val
        if key in busy:
            return _NOVAL                                      # 돌고 도는 수식
        busy.add(key)
        try:
            v = _calc_formula(f, get, sheet)
        except (_NoCalc, ArithmeticError, ValueError, AttributeError, RecursionError):
            v = _NOVAL
        finally:
            busy.discard(key)
        memo[key] = v
        return v

    info = {"calc": 0, "cleared": 0, "ex": []}
    out = {}
    for name, x in sheets_x.items():
        def fix(cm, name=name):
            cell = cm.group(0)
            hend = cell.index(">") + 1
            head = cell[:hend]
            if head.endswith("/>") or "<f" not in cell:
                return cell
            r, c = int(cm.group(2)), H._col_num(cm.group(1))
            if (r, c) not in cells[name] or cells[name][(r, c)][1] is None:
                return cell
            v = get(name, r, c)
            head = re.sub(r'\s+t="[^"]*"', "", head)
            body = re.sub(r"<v>.*?</v>|<v/>", "", cell[hend:], flags=re.S)
            if v is _NOVAL:
                info["cleared"] += 1
                if len(info["ex"]) < 5:
                    info["ex"].append("%s!%s%d %s" % (name, cm.group(1), r, cells[name][(r, c)][1][:40]))
                return head + body
            info["calc"] += 1
            if isinstance(v, bool):
                head, vx = head[:-1] + ' t="b">', "1" if v else "0"
            elif isinstance(v, (int, float)):
                vx = _num_txt(v)
            else:
                head, vx = head[:-1] + ' t="str">', _xml_escape(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(v)))
            return head + re.sub(r"(</f>|<f\b[^>]*/>)", lambda fm: fm.group(1) + "<v>%s</v>" % vx, body, count=1)
        out[name] = _CELL.sub(fix, x)
    return out, info


# ─────────────────────────────────────────────────────────────
# 만들기
# ─────────────────────────────────────────────────────────────
def build(src: dict, kind: str) -> tuple:
    """(새 엑셀 bytes, 기대값 {inv:{(줄,칸): 값}, pl:{…}, photos:{줄: 장 수}, k_inv, k_pl}, report)"""
    T = _template(kind)
    z = zipfile.ZipFile(io.BytesIO(T["bytes"]))
    inv, pl = T["sheets"]["INV"], T["sheets"].get("PL")
    report = {"kind": kind, "items": len(src["items"]), "pl_items": len(src["pl"]["items"]), "expanded": 0, "pl_expanded": 0,
              "photos": 0, "photos_dropped": 0, "equip": len(src["equip"]), "sheets": src["sheets"],
              "named": sum(1 for it in src["items"] if not _blank(it["left"].get(4))),      # 품명 있는 줄(① 채움 품목 수와 맞춰 본다)
              "dropped": {k: dict(v, ex=list(v["ex"])) for k, v in src["dropped"].items()}}
    k_inv = max(0, len(src["items"]) - (inv["last"] - inv["first"] + 1))
    k_pl = max(0, len(src["pl"]["items"]) - (pl["last"] - pl["first"] + 1)) if pl else 0
    shifts = {inv["name"]: (inv["last"], k_inv)}
    if pl:
        shifts[pl["name"]] = (pl["last"], k_pl)
    changed = {}
    x_inv = _unshare(z.read(inv["path"]).decode("utf-8"))
    style_inv = _styles_of_row(x_inv, inv["first"])
    if k_inv:
        x_inv = _expand(x_inv, inv["first"], inv["last"], k_inv, inv["name"], shifts)    # 다른 시트 주소도 함께(shifts)
    elif pl and k_pl:
        x_inv = _fix_formulas_all(x_inv, {pl["name"]: shifts[pl["name"]]}, inv["name"])
    report["expanded"] = k_inv
    exp_inv, exp_pl = {}, {}
    # 머리: 인보이스마다 다른 묶음(INCOTERMS · 결제 · 제목 …)은 원본 그대로 · 번호 · 날짜 · 선적일
    w, moved = _header_blocks(lambda r, c: src["header"].get((r, c)), inv["hcells"])
    exp_inv.update(w)
    report["header_moved"] = moved
    for key in ("no", "date", "sail"):
        rc = inv[key + "_cell"]
        v = src.get(key)
        if key == "no" and _blank(v):
            v = src.get("invoice_no")              # 「DATE:」 글자가 없어 번호 칸을 못 찾았으면 머리에서 찾은 KNK-… 번호(10-28 회귀에서 찾음)
        if rc and not _blank(v):
            exp_inv[rc] = v
    amount_vals = 0
    for i, it in enumerate(src["items"]):
        r = inv["first"] + i
        for c, v in _row_values(it, kind, src, inv, report).items():
            exp_inv[(r, c)] = v
        # 금액: 원본이 '수량×단가' 수식이면 틀 수식 그대로 · 원본 칸이 비었으면 비움(없던 금액을 만들지 않게) · 아니면 원본 값
        af = (it.get("amount_f") or "").replace(" ", "")
        if re.fullmatch(r"\+*F%d\*H%d" % (it["row"], it["row"]), af) or re.fullmatch(r"\+*H%d\*F%d" % (it["row"], it["row"]), af):
            pass
        elif 9 in it["left"]:
            exp_inv[(r, 9)] = it["left"][9]
            amount_vals += 1
        else:
            exp_inv[(r, 9)] = None
        if kind == "소모품" and (r, 3) not in exp_inv and r > inv["last"]:
            exp_inv[(r, 3)] = i + 1                          # 일반: 늘린 줄의 번호(C) — 틀 줄은 틀 번호 그대로
    report["amount_values"] = amount_vals
    changed[inv["path"]] = _write_cells(x_inv, exp_inv, style_inv)
    if pl:
        x_pl = _unshare(z.read(pl["path"]).decode("utf-8"))
        style_pl = _styles_of_row(x_pl, pl["first"])
        if k_pl:
            x_pl = _expand(x_pl, pl["first"], pl["last"], k_pl, pl["name"], shifts)       # 인보이스 시트 주소도 함께(한 번만)
        elif k_inv:
            x_pl = _fix_formulas_all(x_pl, {inv["name"]: shifts[inv["name"]]}, pl["name"])
        report["pl_expanded"] = k_pl
        w2, moved2 = _header_blocks(lambda r, c: src["pl"].get("header", {}).get((r, c)), pl["hcells"])
        exp_pl.update(w2)
        report["header_moved"] += [dict(m, block="패킹 " + m["block"]) for m in moved2]
        put_top = {}
        for i, it in enumerate(src["pl"]["items"]):
            r = pl["first"] + i
            for c, v in it["left"].items():
                if c == 7:
                    _drop(report, "패킹 G", "g", v)
                    continue
                val = ("f", it["f"][c]) if (c in it["f"] and not re.search(r"[A-Z]{1,3}\$?\d", it["f"][c])) else v
                if c in pl["vmerge"]:                         # 세로로 합친 칸(수책 중량·부피 · 일반 부피) — 위 칸 하나에
                    put_top.setdefault(c, []).append((val, v))
                    continue
                exp_pl[(r, c)] = val
            for bm, v in it["box"].items():
                if bm in pl["box"]:
                    exp_pl[(r, pl["box"][bm])] = v
            for c, v in it["unl"].items():
                _drop(report, "패킹 " + H._col_letter(c), "pl_unl", v)
        for c, vs in put_top.items():
            if len(vs) == 1:
                exp_pl[(pl["first"], c)] = vs[0][0]
            elif all(isinstance(x, (int, float)) and not isinstance(x, bool) for _, x in vs):
                # 합친 칸인데 원본이 여러 줄에 적었다(260331 부피 2줄) — 숫자면 합계 하나로(합친 칸은 덩어리 전체의 값)
                exp_pl[(pl["first"], c)] = round(sum(x for _, x in vs), 10)
                report.setdefault("pl_merged_sum", {})[H._col_letter(c)] = [x for _, x in vs]
            else:
                exp_pl[(pl["first"], c)] = vs[0][0]
                for _, x in vs[1:]:
                    _drop(report, "패킹 " + H._col_letter(c), "합친 칸에 값이 여러 개 — 첫 값만", x)
        changed[pl["path"]] = _write_cells(x_pl, exp_pl, style_pl)
    # 저장값 새로 셈(합계 · 금액 · 패킹 머리 참조) — 다시 계산 안 하는 보기 화면에 틀 원본(261015 · 260921) 숫자가 보이지 않게
    sx = {inv["name"]: changed[inv["path"]]}
    if pl:
        sx[pl["name"]] = changed[pl["path"]]
    sx, report["cached"] = _recalc(sx, H.shared_strings(z))
    changed[inv["path"]] = sx[inv["name"]]
    if pl:
        changed[pl["path"]] = sx[pl["name"]]
    media_add, ct_add, photos_expect = {}, set(), {}
    for key, info, kk in (("INV", inv, k_inv), ("PL", pl, k_pl)):
        if not info:
            continue
        dp = next((t for t in H._rels(z, info["path"]).values() if "/drawings/" in t and t.endswith(".xml")), None)
        if not dp:
            continue
        dx = z.read(dp).decode("utf-8")
        if kk:
            dx = _shift_drawing(dx, info["last"], kk)                # 서명·도장 내리기
        if key == "INV" and "image" in info["cols"]:
            dx, add = _add_photos(z, dp, dx, src, inv, report, photos_expect)
            media_add.update(add["media"])
            ct_add |= add["ct"]
            if add["rels"]:
                changed[add["rels_path"]] = add["rels"]
        changed[dp] = dx
    if kind == "수책" and src["photos"]:
        report["photos_dropped"] = sum(len(v) for v in src["photos"].values())
        for (_t, row), pics in src["photos"].items():
            for _p in pics:
                _drop(report, "사진", "photo", "%d줄" % row)
    wbx = z.read("xl/workbook.xml").decode("utf-8")
    if k_inv:
        wbx = _defined_names(wbx, inv["name"], inv["first"], inv["last"], k_inv)
    if pl and k_pl:
        wbx = _defined_names(wbx, pl["name"], pl["first"], pl["last"], k_pl)
    cp = re.search(r"<calcPr\b[^>]*?/>", wbx)
    if cp and "fullCalcOnLoad" not in cp.group(0):                  # 엑셀은 열 때 다시 셈(틀에 이미 있음 — 틀이 바뀌어도 지키게)
        wbx = wbx.replace(cp.group(0), cp.group(0)[:-2] + ' fullCalcOnLoad="1"/>')
    changed["xl/workbook.xml"] = wbx
    if ct_add:
        ct = z.read("[Content_Types].xml").decode("utf-8")
        for ext in sorted(ct_add):
            if not re.search(r'<Default\b[^>]*\bExtension="%s"' % ext, ct, re.I):
                mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "bmp": "image/bmp",
                        "emf": "image/x-emf", "wmf": "image/x-wmf", "tif": "image/tiff", "tiff": "image/tiff"}.get(ext, "application/octet-stream")
                ct = ct.replace("<Default ", '<Default Extension="%s" ContentType="%s"/><Default ' % (ext, mime), 1)
        changed["[Content_Types].xml"] = ct
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for info_z in z.infolist():
            buf = changed.get(info_z.filename)
            buf = buf.encode("utf-8") if isinstance(buf, str) else (buf if buf is not None else z.read(info_z.filename))
            zi = zipfile.ZipInfo(info_z.filename, date_time=info_z.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info_z.external_attr
            zo.writestr(zi, buf)
        for name, buf in media_add.items():
            zi = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zo.writestr(zi, buf)
    return out.getvalue(), {"inv": exp_inv, "pl": exp_pl, "photos": photos_expect, "k_inv": k_inv, "k_pl": k_pl}, report


def _add_photos(z, dp, dx, src, inv, report, photos_expect) -> tuple:
    """일반통관 IMAGE 칸에 품목 사진 — 한 줄에 여러 장이면 칸 안에 나란히(가로를 나눠) · 비율 그대로 칸 크기 안으로."""
    col = inv["cols"]["image"] - 1
    d, b = dp.rsplit("/", 1)
    rels_path = d + "/_rels/" + b + ".rels"
    rels = z.read(rels_path).decode("utf-8") if rels_path in z.namelist() else \
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
    rid_n = max([int(x) for x in re.findall(r'\bId="rId(\d+)"', rels)] or [0])
    pid = max([int(x) for x in re.findall(r'<xdr:cNvPr\b[^>]*\bid="(\d+)"', dx)] or [1])
    mnum = len([n for n in z.namelist() if n.startswith("xl/media/")])
    row_of = {(it["sheet"], it["row"]): inv["first"] + i for i, it in enumerate(src["items"])}
    anchors, media, ct = [], {}, set()
    for key, pics in sorted(src["photos"].items(), key=lambda kv: row_of.get(kv[0], 0)):
        r = row_of.get(key)
        if r is None:
            continue
        bw, bh = PHOTO_BOX[0] // len(pics), PHOTO_BOX[1]
        for i, p in enumerate(pics):
            mnum += 1
            rid_n += 1
            pid += 1
            ext = p["ext"] if p["ext"] in ("png", "jpg", "jpeg", "gif", "bmp", "emf", "wmf", "tif", "tiff") else "png"
            name = "xl/media/z1191u_%d.%s" % (mnum, ext)
            media[name] = p["bytes"]
            ct.add(ext)
            rels = rels.replace("</Relationships>",
                                '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                                'Target="../media/%s"/></Relationships>' % (rid_n, name.rsplit("/", 1)[1]))
            cx, cy = max(p["cx"], 1), max(p["cy"], 1)
            s = min(bw / cx, bh / cy, 1.0)
            w, h = int(cx * s), int(cy * s)
            off = i * bw
            anchors.append(
                '<xdr:twoCellAnchor editAs="oneCell"><xdr:from><xdr:col>%d</xdr:col><xdr:colOff>%d</xdr:colOff><xdr:row>%d</xdr:row>'
                '<xdr:rowOff>0</xdr:rowOff></xdr:from><xdr:to><xdr:col>%d</xdr:col><xdr:colOff>%d</xdr:colOff><xdr:row>%d</xdr:row>'
                '<xdr:rowOff>%d</xdr:rowOff></xdr:to><xdr:pic><xdr:nvPicPr><xdr:cNvPr id="%d" name="Picture %d"/><xdr:cNvPicPr>'
                '<a:picLocks noChangeAspect="1"/></xdr:cNvPicPr></xdr:nvPicPr><xdr:blipFill><a:blip '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:embed="rId%d"/><a:stretch><a:fillRect/>'
                '</a:stretch></xdr:blipFill><xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect">'
                '<a:avLst/></a:prstGeom></xdr:spPr></xdr:pic><xdr:clientData/></xdr:twoCellAnchor>'
                % (col, off, r - 1, col, off + w, r - 1, h, pid, pid, rid_n, w, h))
            photos_expect[r] = photos_expect.get(r, 0) + 1
            report["photos"] += 1
    if anchors:
        close = re.search(r"</(\w+:)?wsDr>\s*$", dx)
        dx = dx[:close.start()] + "".join(anchors) + dx[close.start():]
    return dx, {"media": media, "ct": ct, "rels": rels if anchors else None, "rels_path": rels_path}


# ─────────────────────────────────────────────────────────────
# 대조 — 새 파일을 다시 읽어 기대값과 칸마다 · 품목 수 · 금액 합 · 사진
# ─────────────────────────────────────────────────────────────
def _serial(x):
    if isinstance(x, _dt.datetime):
        return round((x - _dt.datetime(1899, 12, 30)).total_seconds() / 86400.0, 6)
    if isinstance(x, _dt.date):
        return float((x - _dt.date(1899, 12, 30)).days)
    return x


def _same(a, b) -> bool:
    if _blank(a) and _blank(b):
        return True
    if isinstance(a, tuple) and a[0] == "f":
        return isinstance(b, tuple) and b[1] is not None and b[1].replace(" ", "") == a[1].replace(" ", "")
    if isinstance(b, tuple):
        b = b[0]
    a, b = _serial(a), _serial(b)
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a)))
    return str(a) == str(b)


def verify(out: bytes, src: dict, kind: str, exp: dict) -> list:
    """새 파일 ↔ 기대값(칸마다) · 합계 수식이 늘린 줄까지 · 품목 수 · 금액 합 · 사진 → 다른 점(비면 맞음)."""
    T = _template(kind)
    bad = []
    bk = _book(out)
    for key, info, ex, kk in (("INVOICE", T["sheets"]["INV"], exp["inv"], exp["k_inv"]),
                              ("PACKING LIST", T["sheets"].get("PL"), exp["pl"], exp["k_pl"])):
        if not info:
            continue
        cells = bk["cells"](info["path"])
        for (r, c), v in ex.items():
            got = cells.get((r, c))
            if isinstance(v, tuple):
                ok = _same(v, got)
            elif _blank(v):
                ok = got is None or (_blank(got[0]) and not got[1])      # 비운 칸 — 값도 수식도 없어야
            else:
                ok = _same(v, got[0] if got else None)
            if not ok:
                bad.append("%s %s%d: 기대 %r · 새 파일 %r" % (key, H._col_letter(c), r, v, got))
                if len(bad) > 30:
                    return bad
        tr, last = info["total"] + kk, info["last"] + kk
        for c in range(1, 11):
            f = _f(cells, tr, c)
            if f and "SUM" in f.upper():
                ends = [int(x) for x in re.findall(r":\$?[A-Z]{1,3}\$?(\d+)", f)]
                if ends and max(ends) < last:
                    bad.append("%s 합계 %s%d 수식 %s 가 끝 줄 %d 을 안 덮음" % (key, H._col_letter(c), tr, f, last))
    sc = H.scan_fast(out)
    if src.get("invoice_no") and sc.get("invoice_no") != src["invoice_no"]:
        bad.append("인보이스 번호: 원본 %s · 새 파일 %s" % (src["invoice_no"], sc.get("invoice_no") or "없음"))
    n_src = sum(1 for it in src["items"] if not _blank(it["left"].get(4)))
    n_out = sum(len(s["items"]) for s in sc["sheets"])
    if n_src != n_out:
        bad.append("품목(품명 있는 줄) 수: 원본 %d · 새 파일 %d" % (n_src, n_out))
    # 금액 합(품명 있는 줄): 원본 금액 칸 ↔ 새 파일(수식 줄은 수량×단가 · 값 줄은 그 값)
    #   원본 금액이 '수량×단가' 수식인데 저장값이 없으면(엑셀이 아닌 도구로 저장한 파일) 수량×단가로 센다 — 엑셀이 열면 셀 값
    def _num(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _src_amt(it):
        a = it["left"].get(9)
        if _num(a):
            return float(a)
        af = (it.get("amount_f") or "").replace(" ", "")
        q, p = it["left"].get(6), it["left"].get(8)
        if a is None and _num(q) and _num(p) and (re.fullmatch(r"\+*F%d\*H%d" % (it["row"], it["row"]), af)
                                                 or re.fullmatch(r"\+*H%d\*F%d" % (it["row"], it["row"]), af)):
            return float(q) * float(p)
        return 0.0
    s_src = sum(_src_amt(it) for it in src["items"] if not _blank(it["left"].get(4)))
    s_out = 0.0
    for s in sc["sheets"]:
        for itm in s["items"]:
            a = itm.get("amount")
            if a is None and itm.get("qty") is not None and itm.get("price") is not None:
                a = itm["qty"] * itm["price"]
            s_out += a or 0.0
    if abs(s_src - s_out) > 0.005 + 1e-9 * abs(s_src):
        bad.append("금액 합(품명 있는 줄): 원본 %.2f · 새 파일 %.2f" % (s_src, s_out))
    if exp["photos"]:
        got = {}
        for (_t, row), _img in H.row_images(out, sc).items():
            got[row] = got.get(row, 0) + 1
        miss = [r for r in exp["photos"] if r not in got]
        if miss:
            bad.append("사진 빠진 줄 %d개(예: %s)" % (len(miss), miss[:5]))
    return bad


_KEEP_BLOCKS = [("1) Shipper / Exporter(보내는 곳)", r"Shipper\s*/\s*Exporter", 7, 4),
                ("2) For Account & Risk of Messrs(받는 곳)", r"For\s*Account", 8, 4)]


def _header_diffs(src, kind) -> list:
    """보내는 곳 · 받는 곳 — 원본과 다르면 최종 양식 것을 썼다는 알림(주소 PROVINCE→CITY · TAX ID · TEL …)."""
    inv = _template(kind)["sheets"]["INV"]

    def tget(r, c):
        x = inv["hcells"].get((r, c))
        return x[0] if x else None

    def sget(r, c):
        return src["header"].get((r, c))
    out = []
    for name, rx, nr, nc in _KEEP_BLOCKS:
        ls, lt = _find_label(sget, rx), _find_label(tget, rx)
        if not ls or not lt:
            continue
        sv = [sget(ls[0] + dr, ls[1] + 1 + dc) for dr in range(1, nr + 1) for dc in range(nc)]
        tv = [tget(lt[0] + dr, lt[1] + 1 + dc) for dr in range(1, nr + 1) for dc in range(nc)]
        if any(not _same(a, b) for a, b in zip(sv, tv)):
            out.append({"block": name, "src": [str(v).strip() for v in sv if not _blank(v)],
                        "final": [str(v).strip() for v in tv if not _blank(v)]})
    return out


def convert(data: bytes, want: str = "auto") -> dict:
    """올린 인보이스 → {final(이미 최종 양식), converted, ok, out, kind, auto, why, report, bad, header_diffs, error}
    want = 'auto' | '수책' | '소모품'. 이미 최종 양식이면 converted=False(손대지 않음)."""
    try:
        bk = _book(data)
    except zipfile.BadZipFile:
        return {"final": False, "converted": False, "ok": False, "error": "엑셀(.xlsx) 파일이 아닙니다"}
    k0 = layout_kind(data, bk)
    if k0:
        return {"final": True, "converted": False, "ok": True, "kind": k0}
    try:
        src = extract(data, bk)
    except Exception as e:
        return {"final": False, "converted": False, "ok": False, "error": "옛 양식을 읽지 못했습니다 — %s" % str(e)[:160]}
    if not src["items"]:
        return {"final": False, "converted": False, "ok": False, "error": "품목 줄이 없습니다"}
    if src["layout_bad"]:
        return {"final": False, "converted": False, "ok": False, "layout": True,
                "error": "KNK 인보이스 칸 모양(D 품명 · F 수량 · H 단가 · I 금액)이 아니라 바꾸지 않았습니다(%s)"
                         % " · ".join(src["layout_bad"])}
    if len(src["sheets"]) > 1:
        # 인보이스 시트가 여럿(10-28 실측 260121: 001M2509 = KNK-260121-1 · 002M2509 = KNK-260121-2) — 최종 양식은 인보이스 1장이라
        #   합치면 인보이스 2장이 번호 하나 · 합계 하나가 된다(법적 서류가 바뀜) → 바꾸지 않는다(부르는 쪽은 올린 모양 그대로 채운다)
        nos = " · ".join("%s %s" % (t, n if not _blank(n) else "번호 없음") for t, n in src["sheet_nos"])
        return {"final": False, "converted": False, "ok": False, "multi": True,
                "error": "인보이스 시트가 %d개입니다(%s) — 최종 양식은 인보이스 1장이라 합치지 않았습니다"
                         % (len(src["sheets"]), nos)}
    if want in TEMPLATES:
        kind, why, auto = want, "본사가 고름", False
    else:
        (kind, why), auto = guess_kind(src), True
    try:
        out, exp, report = build(src, kind)
        bad = verify(out, src, kind, exp)
    except Exception as e:
        return {"final": False, "converted": False, "ok": False, "kind": kind, "auto": auto,
                "error": "최종 양식으로 옮기지 못했습니다 — %s: %s" % (type(e).__name__, str(e)[:160])}
    return {"final": False, "converted": True, "ok": not bad, "out": out, "kind": kind, "auto": auto, "why": why,
            "report": report, "bad": bad, "header_diffs": _header_diffs(src, kind)}
