# -*- coding: utf-8 -*-
"""이음웍스 엑셀 내려받기 공용 양식 — KNK 회사 양식으로 통일.
  z1191z66 (대표 2026-11-19 「엑셀파일을 직접 결재를 올리는건 아니지만 그래도 양식을 깔끔하게 항상」)
  z1191z67 (대표 2026-11-19 「다른 엑셀도 바꿔」 「양식 이미지를 최대한 KNK 우리회사 느낌에 이미지로 양식 이미지 통일화」)

새 엑셀 내려받기는 반드시 이 모듈로 만든다(제각각 꾸미지 않음):
    wb = new_book("관리번호대장")
    table_sheet(wb.active, "관리번호대장", "조건 · 개수 · 내려받은 시각", COLS, ROWS, freeze_cols=2)
    return xlsx_response(wb, "KNK_관리번호대장_전체_20261119_0807.xlsx")

KNK 양식(모든 내려받기가 같은 모양)
  · 맨 위 KNK 로고(웍스 머리와 같은 그림) · 제목(굵게) · 조건·개수·내려받은 시각(회색) · KNK 빨강 띠
  · 머리 줄 = KNK 빨강(#A5282C) 바탕 · 흰 굵은 글 · 가운데
  · 본문 맑은 고딕 10 · 옅은 칸 줄 · 한 줄 건너 옅은 바탕 · 칸마다 정렬 · 줄 높이는 글 길이에 맞춰
  · 머리 줄(+앞 칸) 고정 · 거르기 단추 · 눈금선 끔 · 칸 너비 ≥ 머리 글자 + 거르기 단추 자리
  · 인쇄: A4 · 넓으면 가로 · 폭 한 장 · 장마다 머리 줄 반복 · 아래 「제목 · 쪽/전체 · KNK 이음웍스」
  · 「=」로 시작하는 글은 글자 그대로(엑셀이 계산식으로 읽지 않게)
  · banner=False = 「다시 올리는 파일」(예: 작업일정표 → 일괄업로드)용 — 1행이 머리 줄(읽는 쪽이 1행을 머리로 봄) · 색·글꼴·고정은 같음
"""
import io
import math
import os
import unicodedata
from urllib.parse import quote

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

FONT = "맑은 고딕"
KNK_RED = "A5282C"            # 웍스 --knk-brand (로고 색)
INK = "27302B"                 # 웍스 --knk-text-primary
INK_2 = "46524B"               # 웍스 --knk-text-secondary
MUTED = "657169"               # 웍스 --knk-text-muted
DIM = "9AA39D"
HEAD_FILL = PatternFill("solid", fgColor=KNK_RED)
BAR_FILL = PatternFill("solid", fgColor=KNK_RED)
ZEBRA_FILL = PatternFill("solid", fgColor="F6F7F4")   # 웍스 --knk-bg-inset
LINE = Side(style="thin", color="D4DAD4")             # 웍스 --knk-border-default
HEAD_LINE = Side(style="thin", color="8B1F23")        # 웍스 --knk-brand-hover
HEAD_ROW = 6                   # banner=True 일 때 머리 줄
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "logo.png")
_LOGO_CACHE = {}


def new_book(sheet_name="목록", title=None):
    wb = Workbook()
    wb.active.title = safe_sheet_name(sheet_name or "목록")
    wb.properties.creator = "KNK 이음웍스"
    wb.properties.title = title or sheet_name
    return wb


def safe_sheet_name(name, used=None):
    s = "".join("_" if ch in '[]:*?/\\' else ch for ch in str(name or "시트"))[:31] or "시트"
    if used is not None:
        base, n = s, 2
        while s in used:
            s = (base[:28] + "(%d)" % n); n += 1
        used.add(s)
    return s


def strike(text, color="9CA3AF"):
    """취소 같은 글 — 회색 줄 그음(엑셀 칸 안 일부만)."""
    return ("strike", str(text), color)


def _w(s):
    """칸 너비 단위로 본 글 길이 — 맑은 고딕 10 실측(엑셀로 열어 봄): 한글·한자 ≈ 1.65 · 영문·숫자 ≈ 0.95."""
    n = 0.0
    for ch in s:
        n += 1.65 if unicodedata.east_asian_width(ch) in ("W", "F") else 0.95
    return n


def _plain(v):
    if isinstance(v, list):
        return "\n".join(_plain(p) for p in v)
    if isinstance(v, tuple) and len(v) == 3 and v[0] == "strike":
        return v[1]
    return "" if v is None else str(v)


def _lines(text, width):
    usable = max(width - 1.2, 3)
    return sum(max(1, math.ceil(_w(part) / usable)) for part in (text.split("\n") or [""]))


def _value(v, base_font):
    """칸 값 — 조각 목록이면 한 칸 안에 줄바꿈으로(strike 조각은 회색 줄 그음)."""
    if isinstance(v, list):
        parts = []
        for i, p in enumerate(v):
            sep = "\n" if i else ""   # 줄바꿈은 다음 조각 앞에 붙임(줄바꿈만 든 조각은 엑셀이 버림)
            if isinstance(p, tuple) and len(p) == 3 and p[0] == "strike":
                parts.append(TextBlock(InlineFont(rFont=FONT, sz=base_font.sz, strike=True, color=p[2]), sep + p[1]))
            else:
                parts.append(sep + _plain(p))
        return CellRichText(*parts) if any(isinstance(x, TextBlock) for x in parts) else "".join(_plain(x) for x in parts)
    if isinstance(v, tuple) and len(v) == 3 and v[0] == "strike":
        return CellRichText(TextBlock(InlineFont(rFont=FONT, sz=base_font.sz, strike=True, color=v[2]), v[1]))
    return v


def _logo_image():
    """웍스 머리의 KNK 로고(static/logo.png) — 선명하게 2배로 줄여 넣고, 보이는 크기는 높이 34px."""
    try:
        from openpyxl.drawing.image import Image as XLImage
        from PIL import Image as PILImage
        if "png" not in _LOGO_CACHE:
            im = PILImage.open(_LOGO).convert("RGBA")
            h = 68
            im = im.resize((round(im.width * h / im.height), h), PILImage.LANCZOS)
            b = io.BytesIO(); im.save(b, "PNG"); _LOGO_CACHE["png"] = b.getvalue(); _LOGO_CACHE["wh"] = im.size
        img = XLImage(io.BytesIO(_LOGO_CACHE["png"]))
        w, h = _LOGO_CACHE["wh"]
        img.height = 34; img.width = round(w * 34 / h)
        return img
    except Exception:
        return None


def auto_cols(headers, rows, max_w=48, money=("금액", "액(", "단가", "합계", "수량", "공급가", "부가세")):
    """머리·값 길이로 칸 정의를 만든다(일반 목록용). 숫자 칸은 오른쪽 · 금액·수량 머리면 천 단위 쉼표 · 길면 줄바꿈."""
    cols = []
    for j, h in enumerate(headers):
        vals = [r[j] for r in rows if j < len(r)]
        width = max([_w(str(h))] + [max((_w(x) for x in _plain(v).split("\n")), default=0) for v in vals[:2000]] + [6])
        nums = [v for v in vals if v not in (None, "")]
        isnum = bool(nums) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in nums)
        c = {"h": str(h), "w": min(max_w, round(width + 2, 1))}
        if isnum:
            c["al"] = "r"
            if any(k in str(h) for k in money):
                c["fmt"] = "#,##0" if all(isinstance(v, int) or float(v).is_integer() for v in nums) else "#,##0.00"
        elif width <= 12:
            c["al"] = "c"
        if width > max_w:
            c["wrap"] = True
        cols.append(c)
    return cols


def table_sheet(ws, title, info, cols, rows, freeze_cols=1, note=None, dim_rows=(), banner=True):
    """cols = [{"h": 머리 글, "w": 너비, "al": "l"|"c"|"r", "wrap": bool, "bold": bool, "fmt": 숫자 모양}, …]
    rows = [[칸 값, …], …] · 칸 값에 [조각, strike(조각), …] 을 주면 한 칸 안에 줄바꿈 · dim_rows = 흐리게 할 줄 번호(0부터)
    banner=False = 1행이 머리 줄(다시 올리는 파일용). 돌려주는 값 = 머리 줄 번호."""
    cols = [dict(c, w=max(c.get("w", 12), round(_w(str(c["h"])) + 4.5, 1))) for c in cols]
    nc = len(cols)
    last = get_column_letter(nc)
    tot_w = sum(c["w"] for c in cols)
    ws.sheet_view.showGridLines = False
    hr = HEAD_ROW if banner else 1
    if banner:
        img = _logo_image()
        if img is not None:
            ws.add_image(img, "A1")
        else:
            ws["A1"] = "KNK"
            ws["A1"].font = Font(name=FONT, size=20, bold=True, color=KNK_RED)
        ws.row_dimensions[1].height = 34
        ws["A2"] = title
        ws["A2"].font = Font(name=FONT, size=15, bold=True, color=INK)
        ws["A2"].alignment = Alignment(vertical="center")
        ws.row_dimensions[2].height = 26
        ws["A3"] = info or ""
        ws["A3"].font = Font(name=FONT, size=9.5, color=MUTED)
        ws["A3"].alignment = Alignment(vertical="center")
        ws.row_dimensions[3].height = 17
        for rr in (2, 3):
            ws.merge_cells("A%d:%s%d" % (rr, last, rr))
        for i in range(1, nc + 1):
            ws.cell(row=4, column=i).fill = BAR_FILL     # KNK 빨강 띠
        ws.row_dimensions[4].height = 3
        ws.row_dimensions[5].height = 7
    # 머리
    for i, c in enumerate(cols, 1):
        cl = ws.cell(row=hr, column=i, value=c["h"])
        cl.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        cl.fill = HEAD_FILL
        cl.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cl.border = Border(top=HEAD_LINE, left=HEAD_LINE, right=HEAD_LINE, bottom=HEAD_LINE)
        ws.column_dimensions[get_column_letter(i)].width = c["w"]
    ws.row_dimensions[hr].height = 24
    # 본문
    dim = set(dim_rows or ())
    AL = {"l": "left", "c": "center", "r": "right"}
    for n, row in enumerate(rows):
        r = hr + 1 + n
        nlines = 1
        for i, c in enumerate(cols, 1):
            v = row[i - 1] if i - 1 < len(row) else None
            f = Font(name=FONT, size=10, bold=bool(c.get("bold")), color=(DIM if n in dim else INK))
            cl = ws.cell(row=r, column=i, value=_value(v, f))
            if isinstance(cl.value, str) and cl.value.startswith("="):
                cl.data_type = "s"   # 글자 그대로(계산식 아님)
            cl.font = f
            wrap = bool(c.get("wrap")) or ("\n" in _plain(v))
            _h = AL.get(c.get("al", "l"), "left")
            cl.alignment = Alignment(horizontal=_h, vertical="center", wrap_text=wrap, indent=(1 if _h != "center" else 0))   # 칸 끝에 붙지 않게
            cl.border = Border(top=LINE, bottom=LINE, left=LINE, right=LINE)
            if n % 2 == 1:
                cl.fill = ZEBRA_FILL
            if c.get("fmt") and isinstance(v, (int, float)) and not isinstance(v, bool):
                cl.number_format = c["fmt"]
            if wrap:
                nlines = max(nlines, _lines(_plain(v), c["w"]))
        ws.row_dimensions[r].height = max(18, 14 * nlines + 4)
    end = hr + len(rows)
    if note:
        ws.cell(row=end + 2, column=1, value=note).font = Font(name=FONT, size=9, color=MUTED)
    # 고정 · 거르기
    ws.freeze_panes = ws.cell(row=hr + 1, column=freeze_cols + 1).coordinate
    if rows:
        ws.auto_filter.ref = "A%d:%s%d" % (hr, last, end)
    # 인쇄
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.orientation = "landscape" if tot_w > 95 else "portrait"
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "%d:%d" % (hr, hr)
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = 0.55
    ws.page_margins.bottom = 0.6
    ws.oddFooter.left.text = str(title or "")[:60]
    ws.oddFooter.left.size = 8
    ws.oddFooter.center.text = "&P / &N"
    ws.oddFooter.center.size = 8
    ws.oddFooter.right.text = "KNK 이음웍스"
    ws.oddFooter.right.size = 8
    ws.oddFooter.right.color = KNK_RED
    return hr


def xlsx_bytes(wb):
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def xlsx_response(wb, filename, ascii_name="KNK_download.xlsx"):
    from fastapi.responses import Response
    return Response(content=xlsx_bytes(wb), media_type=XLSX_MIME,
                    headers={"Content-Disposition": "attachment; filename=\"%s\"; filename*=UTF-8''%s" % (ascii_name, quote(filename)),
                             "Cache-Control": "no-store"})
