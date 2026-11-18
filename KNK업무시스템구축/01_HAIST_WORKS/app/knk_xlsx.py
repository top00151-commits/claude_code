# -*- coding: utf-8 -*-
"""이음웍스 엑셀 내려받기 공용 양식 — z1191z66 (대표 2026-11-19 「엑셀로 다운로드 하는 엑셀파일을 직접 결재를 올리는건 아니지만
그래도 양식을 깔끔하게 항상 만들어서 다운로드 될수있게 해줘」).

새 엑셀 내려받기는 이 모듈로 만든다(제각각 꾸미지 않음):
    wb = new_book("관리번호대장")
    table_sheet(wb.active, "관리번호대장", "조건 · 개수 · 내려받은 시각", COLS, ROWS, freeze_cols=2)
    return xlsx_response(wb, "KNK_관리번호대장_전체_20261119_0807.xlsx")

양식(한 번에 같은 모양)
  · 1줄 제목(굵게 16) · 2줄 조건·개수·내려받은 시각(회색) · 4줄 머리(회사 양식 파랑 #B8CCE4 · 굵게 · 가운데)
  · 본문 맑은 고딕 10 · 옅은 칸 줄 · 한 줄 건너 옅은 바탕 · 칸마다 정렬(왼/가운데/오른) · 줄 높이는 글 길이에 맞춰
  · 머리 줄(+앞 칸) 고정 · 거르기 단추 · 눈금선 끔
  · 인쇄: A4 · 넓으면 가로 · 폭 한 장에 맞춤 · 장마다 머리 줄 반복 · 아래 「쪽/전체」 · 가운데 정렬
  · 「=」로 시작하는 글은 글자 그대로(엑셀이 계산식으로 읽지 않게)
"""
import io
import math
import unicodedata
from urllib.parse import quote

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

FONT = "맑은 고딕"
HEAD_FILL = PatternFill("solid", fgColor="B8CCE4")     # 제작요청서 종이 양식과 같은 파랑
ZEBRA_FILL = PatternFill("solid", fgColor="F5F8FC")
LINE = Side(style="thin", color="C9D3DF")
HEAD_LINE = Side(style="thin", color="7F8FA6")
HEAD_BOTTOM = Side(style="medium", color="44546A")
HEAD_ROW = 4
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def new_book(sheet_name="목록", title=None):
    wb = Workbook()
    wb.active.title = (sheet_name or "목록")[:31]
    wb.properties.creator = "KNK 이음웍스"
    wb.properties.title = title or sheet_name
    return wb


def strike(text, color="9CA3AF"):
    """취소 같은 글 — 회색 줄 그음(엑셀 칸 안 일부만)."""
    return ("strike", str(text), color)


def _w(s):
    """칸 너비 단위로 본 글 길이(한글·한자 ≈ 1.8 · 영문·숫자 ≈ 1)."""
    n = 0.0
    for ch in s:
        n += 1.8 if unicodedata.east_asian_width(ch) in ("W", "F") else 1.0
    return n


def _plain(v):
    if isinstance(v, (list, tuple)) and not (len(v) == 3 and v[0] == "strike"):
        return "\n".join(_plain(p) for p in v)
    if isinstance(v, tuple):
        return v[1]
    return "" if v is None else str(v)


def _lines(text, width):
    usable = max(width - 1.5, 3)
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


def table_sheet(ws, title, info, cols, rows, freeze_cols=1, note=None, dim_rows=()):
    """cols = [{"h": 머리 글, "w": 너비, "al": "l"|"c"|"r", "wrap": bool, "bold": bool, "fmt": 숫자 모양}, …]
    rows = [[칸 값, …], …] · 칸 값에 [조각, strike(조각), …] 을 주면 한 칸 안에 줄바꿈 · dim_rows = 흐리게 할 줄 번호(0부터)."""
    # 칸 너비는 「머리 글자 + 거르기 단추 자리」보다 좁지 않게(단추가 머리 글자를 가리지 않게)
    cols = [dict(c, w=max(c.get("w", 12), round(_w(c["h"]) + 4.5, 1))) for c in cols]
    nc = len(cols)
    last = get_column_letter(nc)
    tot_w = sum(c.get("w", 12) for c in cols)
    ws.sheet_view.showGridLines = False
    # 제목 · 안내
    ws["A1"] = title
    ws["A1"].font = Font(name=FONT, size=16, bold=True, color="1F2937")
    ws["A1"].alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30
    ws["A2"] = info or ""
    ws["A2"].font = Font(name=FONT, size=9.5, color="475569")
    ws["A2"].alignment = Alignment(vertical="center")
    ws.row_dimensions[2].height = 18
    ws.merge_cells("A1:%s1" % last)
    ws.merge_cells("A2:%s2" % last)
    ws.row_dimensions[3].height = 6
    # 머리
    for i, c in enumerate(cols, 1):
        cl = ws.cell(row=HEAD_ROW, column=i, value=c["h"])
        cl.font = Font(name=FONT, size=10, bold=True, color="111827")
        cl.fill = HEAD_FILL
        cl.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cl.border = Border(top=HEAD_LINE, left=HEAD_LINE, right=HEAD_LINE, bottom=HEAD_BOTTOM)
        ws.column_dimensions[get_column_letter(i)].width = c.get("w", 12)
    ws.row_dimensions[HEAD_ROW].height = 24
    # 본문
    dim = set(dim_rows or ())
    AL = {"l": "left", "c": "center", "r": "right"}
    for n, row in enumerate(rows):
        r = HEAD_ROW + 1 + n
        nlines = 1
        for i, c in enumerate(cols, 1):
            v = row[i - 1] if i - 1 < len(row) else None
            f = Font(name=FONT, size=10, bold=bool(c.get("bold")), color=("9CA3AF" if n in dim else "1F2937"))
            cl = ws.cell(row=r, column=i, value=_value(v, f))
            if isinstance(cl.value, str) and cl.value.startswith("="):
                cl.data_type = "s"   # 글자 그대로(계산식 아님)
            cl.font = f
            wrap = bool(c.get("wrap"))
            cl.alignment = Alignment(horizontal=AL.get(c.get("al", "l"), "left"), vertical="center", wrap_text=wrap)
            cl.border = Border(top=LINE, bottom=LINE, left=LINE, right=LINE)
            if n % 2 == 1:
                cl.fill = ZEBRA_FILL
            if c.get("fmt"):
                cl.number_format = c["fmt"]
            if wrap:
                nlines = max(nlines, _lines(_plain(v), c.get("w", 12)))
        ws.row_dimensions[r].height = max(18, 14 * nlines + 4)
    end = HEAD_ROW + len(rows)
    if note:
        ws.cell(row=end + 2, column=1, value=note).font = Font(name=FONT, size=9, color="64748B")
    # 고정 · 거르기
    ws.freeze_panes = ws.cell(row=HEAD_ROW + 1, column=freeze_cols + 1).coordinate
    if rows:
        ws.auto_filter.ref = "A%d:%s%d" % (HEAD_ROW, last, end)
    # 인쇄
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.orientation = "landscape" if tot_w > 95 else "portrait"
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "%d:%d" % (HEAD_ROW, HEAD_ROW)
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = 0.55
    ws.page_margins.bottom = 0.6
    ws.oddFooter.center.text = "&P / &N"
    ws.oddFooter.center.size = 8
    ws.oddFooter.right.text = "KNK 이음웍스"
    ws.oddFooter.right.size = 8
    return ws


def xlsx_bytes(wb):
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def xlsx_response(wb, filename, ascii_name="KNK_download.xlsx"):
    from fastapi.responses import Response
    return Response(content=xlsx_bytes(wb), media_type=XLSX_MIME,
                    headers={"Content-Disposition": "attachment; filename=\"%s\"; filename*=UTF-8''%s" % (ascii_name, quote(filename)),
                             "Cache-Control": "no-store"})
