# -*- coding: utf-8 -*-
"""z1191l — 베트남 인보이스 HS 자동 채움 (대표 지시 2026-10-26)
   「엑셀 양식은 지금 올려준 양식으로 최종 적용해 … 직원들이 가장 편하고 실수없이 빠르게 할수있는 방법으로」

흐름 (엑셀 왕복 — 법인은 지금처럼 엑셀만 다룬다)
  ① 본사(안지연 프로)가 인보이스(최종 양식: 수책·소모품)를 올린다
     → HS 사전의 **확정(CONFIRMED)** 값으로 HS CODE·Tên hàng 칸만 채운 같은 파일을 돌려준다.
     → 법인이 채울 칸은 노랑, 확인만 할 칸은 주황으로 칠한다.
  ② 법인은 노란 칸만 채워 이음 방으로 회신한다.
  ③ 본사가 회신 파일을 올리면 사전이 자란다(기존 z967 규칙: 새 규격 추가 · 같은 HS 확인 · 다른 HS 는 '확인 대기').

⚠ 파일은 통째로 다시 저장하지 않는다 — 엑셀 도구로 열었다 저장하면 사진·도형·인쇄 설정을 잃을 수 있다.
   엑셀 안쪽 XML 에서 **그 칸들만** 바꾸고 나머지(사진 52장·병합·수식·인쇄 영역)는 바이트 그대로 둔다.
⚠ 두 최종 양식 모두 인쇄 영역이 A~I 열이고 HS·Tên hàng 은 그 밖(R~T 열) → 색이 세관용 인보이스 출력에 안 찍힌다.
⚠ 통관은 법적 신고 — 확정 값만 자동으로 채운다. 확인 대기·AI 추정·후보가 갈리는 것은 채우지 않고 노랑으로 둔다.
"""
import io
import re
import zipfile
from xml.sax.saxutils import escape as _xml_escape

# ── 머리글 찾기 — main.py `_hs_parse_invoice_xlsx` 와 같은 낱말(사전 성장과 같은 칸을 본다) ──
HEAD_HS = re.compile(r"HS\s*CODE|HS\s*code|^HS$", re.I)
HEAD_HS_EXACT = re.compile(r"^\s*HS(\s*CODE)?\s*$", re.I)      # 'HS CODE CHECK' 같은 보조 칸보다 이것을 먼저
HEAD_VN = re.compile(r"T[êe]n\s*h[àa]ng", re.I)
HEAD_DESC = re.compile(r"Description", re.I)
WS_SKIP = re.compile(r"PACKING|P/L|CONTENT|COVER|양식|SAMPLE", re.I)
TOTAL_ROW = re.compile(r"^\s*(SUB\s*)?TOTAL\b|^\s*합\s*계", re.I)
INVOICE_NO = re.compile(r"KNK-\d{6}-\d+")

# 상태 — 화면·기록에 같은 글자를 쓴다
AUTO = "AUTO"          # 확정 값으로 채움(색 없음)
CHECK = "CHECK"        # 채웠지만 확인 필요(주황) — 규격 전체가 아니라 모델 글자만 같았다
CONFLICT = "CONFLICT"  # 이미 적힌 HS 가 사전 확정 값과 다름(주황 · 값은 그대로)
NEED = "NEED"          # 법인이 채울 칸(노랑)
KEEP = "KEEP"          # 이미 적혀 있고 문제없음(그대로)

YELLOW = "FFFFFF00"
ORANGE = "FFFFC000"


def norm_key(s) -> str:
    """사전 키 = 규격 정규화(공백 제거 + 대문자) — main.py `_hs_norm_key` 와 같다."""
    return re.sub(r"\s+", "", str(s or "")).upper()


def tokens(s) -> set:
    """모델 글자 조각 — 5글자 이상이고 숫자가 든 것만(소모품 양식은 'PARTS OF CONNECTORS SP100F…' 처럼
    앞에 분류 글이 붙어 규격 전체로는 사전과 안 맞는다)."""
    out = set()
    for x in re.split(r"[\s()/,]+", str(s or "")):
        x = x.strip(":;,.")
        if len(x) >= 5 and re.search(r"\d", x):
            out.add(norm_key(x))
    return out


def digits(s) -> str:
    return re.sub(r"\D", "", re.sub(r"\.0$", "", str(s if s is not None else "")))


# ─────────────────────────────────────────────────────────────
# 사전 색인
# ─────────────────────────────────────────────────────────────
def build_index(entries) -> dict:
    """entries: export_hs_dict 줄(dict) 목록 → {exact: {키: 줄}, tok: {조각: [줄…]}}"""
    exact, tok = {}, {}
    for e in entries:
        k = e.get("part_key") or ""
        if not k:
            continue
        exact[k] = e
        ts = tokens(e.get("model")) | ({k} if (len(k) >= 5 and re.search(r"\d", k)) else set())
        for t in ts:
            tok.setdefault(t, []).append(e)
    return {"exact": exact, "tok": tok}


def _confirmed(e) -> bool:
    return (e.get("status") or "") == "CONFIRMED" and len(digits(e.get("hs_code"))) == 8


def lookup(index, desc):
    """규격 하나 → (방법, 줄, 메모).
    방법: exact(규격 그대로 · 확정) / token(모델 글자만 · 확정 후보가 모두 같은 HS) /
          pending(사전에 있으나 확정 아님) / ambiguous(후보 HS 가 갈림) / none(사전에 없음)"""
    k = norm_key(desc)
    e = index["exact"].get(k)
    if e is not None:
        if _confirmed(e):
            return "exact", e, ""
        return "pending", e, "사전 %s(%s)" % ({"PENDING": "확인 대기", "AI": "AI 추정"}.get(e.get("status"), e.get("status") or "?"),
                                              digits(e.get("hs_code")) or "HS 없음")
    cands = {}
    for t in tokens(desc):
        for c in index["tok"].get(t, []):
            cands[c.get("part_key")] = c
    if not cands:
        return "none", None, ""
    conf = [c for c in cands.values() if _confirmed(c)]
    if not conf:
        c0 = next(iter(cands.values()))
        return "pending", c0, "같은 모델이 사전에 확정 아님(%s)" % (digits(c0.get("hs_code")) or "HS 없음")
    hs_set = {digits(c.get("hs_code")) for c in conf}
    if len(hs_set) > 1:
        return "ambiguous", None, "같은 모델 후보 HS 가 갈림: " + " · ".join(sorted(hs_set))
    best = sorted(conf, key=lambda c: (0 if (c.get("vn_name") or "").strip() else 1, -(c.get("seen_count") or 0)))[0]
    return "token", best, "모델만 일치: 사전 규격 " + (best.get("model") or best.get("part_key") or "")


# ─────────────────────────────────────────────────────────────
# 엑셀 읽기 — 시트·머리글·품목 줄
# ─────────────────────────────────────────────────────────────
def _sheet_paths(z) -> list:
    """workbook.xml + rels → [(시트 이름, 상태, xml 경로)] (문서 순서)"""
    wb = z.read("xl/workbook.xml").decode("utf-8")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    rid2t = {}
    for m in re.finditer(r"<Relationship\b([^>]*)/?>", rels):
        a = m.group(1)
        i = re.search(r'\bId="([^"]+)"', a)
        t = re.search(r'\bTarget="([^"]+)"', a)
        if i and t:
            rid2t[i.group(1)] = t.group(1)
    out = []
    for m in re.finditer(r"<sheet\b([^>]*)/?>", wb):
        a = m.group(1)
        nm = re.search(r'\bname="([^"]*)"', a)
        st = re.search(r'\bstate="([^"]*)"', a)
        rid = re.search(r'\br:id="([^"]+)"', a) or re.search(r'\bid="([^"]+)"', a)
        if not (nm and rid and rid.group(1) in rid2t):
            continue
        tgt = rid2t[rid.group(1)]
        path = tgt.lstrip("/") if tgt.startswith("/") else "xl/" + tgt
        name = nm.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")
        out.append((name, (st.group(1) if st else "visible"), path))
    return out


def scan(data: bytes) -> dict:
    """인보이스 엑셀 → {sheets:[{title, path, header_row, col_desc, col_hs, col_vn, form, items:[…]}], invoice_no}
    품목 줄 = 머리글 아래에서 Description 칸에 글이 있는 줄(합계 줄 제외)."""
    import openpyxl
    z = zipfile.ZipFile(io.BytesIO(data))
    paths = _sheet_paths(z)
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    res = {"sheets": [], "invoice_no": ""}
    try:
        for title, state, path in paths:
            if state != "visible" or WS_SKIP.search(title or "") or title not in wb.sheetnames:
                continue
            ws = wb[title]
            head = []
            for r, row in enumerate(ws.iter_rows(min_row=1, max_row=45, max_col=30, values_only=True), start=1):
                for c, v in enumerate(row, start=1):
                    if v is None:
                        continue
                    t = str(v).strip()
                    head.append((r, c, t))
                    if not res["invoice_no"] and r <= 15:
                        mm = INVOICE_NO.search(t)
                        if mm:
                            res["invoice_no"] = mm.group(0)
            hs_cells = [(r, c, t) for r, c, t in head if HEAD_HS.search(t) and len(t) < 20]
            if not hs_cells:
                continue
            exact = [x for x in hs_cells if HEAD_HS_EXACT.match(x[2])]
            hr, hc, _ = (exact or hs_cells)[0]
            vn = next(((r, c) for r, c, t in head if HEAD_VN.search(t)), None)
            ds = next(((r, c) for r, c, t in head if HEAD_DESC.search(t)), None)
            if not ds:
                continue
            words = {t.upper() for r, c, t in head if r == hr}
            if {"CATEGORY", "SUPPLIER"} <= words:
                form = "수책"
            elif "IMAGE" in words and "C/O" in words:
                form = "소모품"
            else:
                form = "예전 양식"
            start = max(hr, ds[0], vn[0] if vn else hr) + 1
            items = []
            for r, row in enumerate(ws.iter_rows(min_row=start, max_col=max(hc, vn[1] if vn else hc, ds[1], 4), values_only=True),
                                    start=start):
                # 합계(TOTAL) 줄에서 품목 읽기를 멈춘다 — 그 아래 서명·비고 글을 품목으로 오인해 칠하지 않게(최종 양식은 A열 'TOTAL')
                if any(isinstance(v, str) and TOTAL_ROW.match(v) for v in row[:4]):
                    break
                d = row[ds[1] - 1] if len(row) >= ds[1] else None
                d = "" if d is None else str(d).strip()
                if not d:
                    continue
                h = row[hc - 1] if len(row) >= hc else None
                v = row[vn[1] - 1] if (vn and len(row) >= vn[1]) else None
                items.append({"row": r, "desc": d, "hs_raw": "" if h is None else str(h).strip(),
                              "vn_raw": "" if v is None else str(v).strip()})
            res["sheets"].append({"title": title, "path": path, "header_row": hr, "col_desc": ds[1], "col_hs": hc,
                                  "col_vn": vn[1] if vn else None, "form": form, "items": items})
    finally:
        wb.close()
    return res


# ─────────────────────────────────────────────────────────────
# 채움 계획 — 줄마다 무엇을 쓰고 무엇을 칠할지
# ─────────────────────────────────────────────────────────────
def plan(sc, index) -> list:
    """줄마다 {sheet, row, desc, status, write_hs, write_vn, color_hs, color_vn, why, dict_hs}"""
    acts = []
    for sh in sc["sheets"]:
        has_vn = sh["col_vn"] is not None
        for it in sh["items"]:
            hs0, vn0 = digits(it["hs_raw"]), (it["vn_raw"] or "").strip()
            way, e, memo = lookup(index, it["desc"])
            dhs = digits(e.get("hs_code")) if e else ""
            dvn = (e.get("vn_name") or "").strip() if e else ""
            a = {"sheet": sh["title"], "row": it["row"], "desc": it["desc"], "status": KEEP,
                 "write_hs": None, "write_vn": None, "color_hs": None, "color_vn": None,
                 "why": "", "dict_hs": dhs if way in ("exact", "token", "pending") else ""}
            if it["hs_raw"] and len(hs0) not in (6, 8):
                a.update(status=CONFLICT, color_hs=ORANGE, why="HS 칸 형식 확인(8자리 숫자가 아님): %s" % it["hs_raw"][:20])
                if has_vn and not vn0:
                    a["color_vn"] = YELLOW
            elif hs0:
                # 이미 적힌 HS(본사가 미리 채움 · 장비 6자리 포함) — 값은 절대 덮지 않는다
                if way in ("exact", "token") and len(hs0) == 8 and dhs != hs0:
                    a.update(status=CONFLICT, color_hs=ORANGE, why="적힌 HS %s ↔ 사전 확정 %s" % (hs0, dhs))
                elif way in ("exact", "token") and dhs == hs0 and has_vn and not vn0 and dvn:
                    a.update(status=AUTO, write_vn=dvn, why="HS 는 이미 같음 · 품명만 채움")
                elif has_vn and not vn0:
                    a.update(status=NEED, color_vn=YELLOW, why="베트남어 품명 비어 있음")
            elif way == "exact":
                a.update(status=AUTO, write_hs=dhs, why="사전 확정")
                if has_vn and not vn0:
                    if dvn:
                        a["write_vn"] = dvn
                    else:
                        a.update(color_vn=YELLOW, why="사전 확정 · 품명은 사전에 없음")
            elif way == "token":
                a.update(status=CHECK, write_hs=dhs, color_hs=ORANGE, why=memo)
                if has_vn and not vn0:
                    if dvn:
                        a.update(write_vn=dvn, color_vn=ORANGE)
                    else:
                        a["color_vn"] = YELLOW
            else:
                a.update(status=NEED, color_hs=YELLOW,
                         why={"none": "사전에 없음(새 품목)"}.get(way, memo or "사전에 없음"))
                if has_vn and not vn0:
                    a["color_vn"] = YELLOW
            acts.append(a)
    return acts


def summary(acts) -> dict:
    n = {k: 0 for k in (AUTO, CHECK, CONFLICT, NEED, KEEP)}
    for a in acts:
        n[a["status"]] += 1
    n["total"] = len(acts)
    return n


# ─────────────────────────────────────────────────────────────
# XML 에서 칸만 바꾸기
# ─────────────────────────────────────────────────────────────
def _col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _col_num(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


_CELL_RE = r'<c\b[^>]*?\br="%s"[^>]*?(?:/>|>.*?</c>)'


def _add_styles(styles: str, need: set):
    """need = {(원래 스타일 번호, 색)} → (새 styles.xml, {(원래, 색): 새 번호})
    채우기(fill) 2개를 더하고, 쓰이는 원래 서식(xf)을 복제해 그 채우기만 바꾼다(테두리·글꼴·맞춤은 그대로)."""
    if not need:
        return styles, {}
    fm = re.search(r"<fills\b[^>]*>(.*?)</fills>", styles, re.S)
    if not fm:
        raise ValueError("styles.xml 에 fills 가 없습니다")
    n_fill = len(re.findall(r"<fill\b", fm.group(1)))
    colors = sorted({c for _, c in need})
    fid = {c: n_fill + i for i, c in enumerate(colors)}
    add = "".join('<fill><patternFill patternType="solid"><fgColor rgb="%s"/><bgColor indexed="64"/></patternFill></fill>' % c
                  for c in colors)
    fills_new = re.sub(r'\bcount="\d+"', 'count="%d"' % (n_fill + len(colors)), fm.group(0)[:fm.group(0).index(">") + 1], 1) \
        + fm.group(1) + add + "</fills>"
    styles = styles[:fm.start()] + fills_new + styles[fm.end():]
    cm = re.search(r"<cellXfs\b[^>]*>(.*?)</cellXfs>", styles, re.S)
    if not cm:
        raise ValueError("styles.xml 에 cellXfs 가 없습니다")
    xfs = re.findall(r"<xf\b[^>]*?(?:/>|>.*?</xf>)", cm.group(1), re.S)
    mapping, extra = {}, []
    for (s0, color) in sorted(need):
        base = xfs[s0] if 0 <= s0 < len(xfs) else xfs[0]
        tag_end = base.index(">")
        head, rest = base[:tag_end], base[tag_end:]
        if head.endswith("/"):
            head, rest = head[:-1], "/" + rest
        head = re.sub(r'\s(fillId|applyFill)="[^"]*"', "", head)
        head += ' fillId="%d" applyFill="1"' % fid[color]
        extra.append(head + rest)
        mapping[(s0, color)] = len(xfs) + len(extra) - 1
    open_tag = cm.group(0)[:cm.group(0).index(">") + 1]
    open_tag = re.sub(r'\bcount="\d+"', 'count="%d"' % (len(xfs) + len(extra)), open_tag, 1)
    cell_new = open_tag + cm.group(1) + "".join(extra) + "</cellXfs>"
    styles = styles[:cm.start()] + cell_new + styles[cm.end():]
    return styles, mapping


def _cell_style(cell_xml: str) -> int:
    m = re.search(r'\bs="(\d+)"', cell_xml[:cell_xml.index(">") + 1])
    return int(m.group(1)) if m else 0


def _edit_sheet(xml: str, edits: list, style_of_new, skipped=None) -> tuple:
    """edits: [(줄, 칸 번호, 값 또는 None, 색 또는 None)] → (새 xml, 필요한 스타일 집합, 칸별 원래 스타일)
    1차: 원래 스타일만 모은다(style_of_new=None). 2차: 새 스타일 번호로 실제로 바꾼다.
    ⚠수식이 든 칸에는 값을 쓰지 않는다(색만) — skipped 에 칸 주소를 남긴다."""
    need, orig = set(), {}
    by_row = {}
    for r, c, val, color in edits:
        by_row.setdefault(r, []).append((c, val, color))
    out, pos = [], 0
    for rm in re.finditer(r'<row\b[^>]*?\br="(\d+)"[^>]*?(?:/>|>(.*?)</row>)', xml, re.S):
        r = int(rm.group(1))
        if r not in by_row:
            continue
        row_xml = rm.group(0)
        self_closing = rm.group(2) is None and row_xml.rstrip().endswith("/>")
        if self_closing:
            row_open = row_xml[:-2] + ">"
            body = ""
        else:
            row_open = row_xml[:row_xml.index(">") + 1]
            body = rm.group(2) or ""
        for c, val, color in sorted(by_row[r]):
            ref = "%s%d" % (_col_letter(c), r)
            cm = re.search(_CELL_RE % ref, body, re.S)
            if cm:
                s0 = _cell_style(cm.group(0))
            else:
                # 칸이 없으면 같은 줄 왼쪽 칸이 아니라 '바로 위 품목 줄 같은 칸' 서식을 빌린다 — 없으면 0
                s0 = orig.get(("up", c), 0)
            orig[(r, c)] = s0
            orig[("up", c)] = s0
            if color:
                need.add((s0, color))
            if style_of_new is None:
                continue
            s_new = style_of_new.get((s0, color), s0) if color else s0
            if val is not None and cm and "<f" in cm.group(0):
                if skipped is not None:
                    skipped.append(ref)
                val = None
            if val is not None:
                new_cell = '<c r="%s" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (
                    ref, s_new, _xml_escape(val))
            elif cm:
                head = cm.group(0)[:cm.group(0).index(">") + 1]
                if re.search(r'\bs="\d+"', head):
                    head2 = re.sub(r'\bs="\d+"', 's="%d"' % s_new, head, 1)
                else:
                    head2 = head[:-2] + ' s="%d"/>' % s_new if head.endswith("/>") else head[:-1] + ' s="%d">' % s_new
                new_cell = head2 + cm.group(0)[len(head):]
            else:
                new_cell = '<c r="%s" s="%d"/>' % (ref, s_new)
            if cm:
                body = body[:cm.start()] + new_cell + body[cm.end():]
            else:
                ins = len(body)
                for cc in re.finditer(r'<c\b[^>]*?\br="([A-Z]+)\d+"', body):
                    if _col_num(cc.group(1)) > c:
                        ins = cc.start()
                        break
                body = body[:ins] + new_cell + body[ins:]
                sp = re.search(r'\bspans="(\d+):(\d+)"', row_open)
                if sp and c > int(sp.group(2)):
                    row_open = row_open.replace(sp.group(0), 'spans="%s:%d"' % (sp.group(1), c))
        if style_of_new is not None:
            out.append(xml[pos:rm.start()])
            out.append(row_open + body + "</row>")
            pos = rm.end()
    if style_of_new is None:
        return xml, need, orig
    out.append(xml[pos:])
    xml2 = "".join(out)
    # 칸이 기존 범위 밖이면 dimension 을 넓힌다(엑셀 도구가 범위 밖 칸을 못 읽는 일 방지)
    dm = re.search(r'<dimension ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"/>', xml2)
    if dm and edits:
        mc = max(c for _, c, _, _ in edits)
        if mc > _col_num(dm.group(3)):
            xml2 = xml2.replace(dm.group(0), '<dimension ref="%s%s:%s%s"/>' % (dm.group(1), dm.group(2), _col_letter(mc), dm.group(4)))
    return xml2, need, orig


def apply(data: bytes, sc: dict, acts: list, skipped=None) -> bytes:
    """계획대로 칸 값·색만 바꾼 새 엑셀(bytes). 바뀌는 항목 = 해당 시트 xml · styles.xml · workbook.xml(다시 계산 표시).
    skipped(목록)를 주면 수식이 있어 값을 안 쓴 칸 주소를 담는다."""
    z = zipfile.ZipFile(io.BytesIO(data))
    sheet_of = {s["title"]: s for s in sc["sheets"]}
    per_sheet = {}
    for a in acts:
        sh = sheet_of[a["sheet"]]
        e = per_sheet.setdefault(sh["path"], [])
        if a["write_hs"] is not None or a["color_hs"]:
            e.append((a["row"], sh["col_hs"], a["write_hs"], a["color_hs"]))
        if sh["col_vn"] and (a["write_vn"] is not None or a["color_vn"]):
            e.append((a["row"], sh["col_vn"], a["write_vn"], a["color_vn"]))
    per_sheet = {p: e for p, e in per_sheet.items() if e}
    if not per_sheet:
        return data
    need = set()
    sheet_xml = {}
    for p, edits in per_sheet.items():
        x = z.read(p).decode("utf-8")
        sheet_xml[p] = x
        _, n, _ = _edit_sheet(x, edits, None)
        need |= n
    styles = z.read("xl/styles.xml").decode("utf-8")
    styles2, mapping = _add_styles(styles, need)
    changed = {"xl/styles.xml": styles2.encode("utf-8")}
    for p, edits in per_sheet.items():
        x2, _, _ = _edit_sheet(sheet_xml[p], edits, mapping, skipped)
        changed[p] = x2.encode("utf-8")
    wbx = z.read("xl/workbook.xml").decode("utf-8")
    cp = re.search(r"<calcPr\b[^>]*?/>", wbx)
    if cp and "fullCalcOnLoad" not in cp.group(0):
        wbx = wbx.replace(cp.group(0), cp.group(0)[:-2] + ' fullCalcOnLoad="1"/>')
        changed["xl/workbook.xml"] = wbx.encode("utf-8")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zo:
        for info in z.infolist():
            buf = changed.get(info.filename)
            if buf is None:
                buf = z.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED if info.filename in changed else info.compress_type
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zo.writestr(zi, buf)
    return out.getvalue()


def invoice_no_quick(data: bytes) -> str:
    """회신 파일의 인보이스 번호(KNK-YYMMDD-n) — 글자 표(sharedStrings)·시트 안 글자에서 처음 나오는 것. 없으면 ''."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return ""
    names = [n for n in ("xl/sharedStrings.xml",) if n in z.namelist()]
    names += [p for _, _, p in _sheet_paths(z) if p in z.namelist()]
    for n in names:
        m = INVOICE_NO.search(z.read(n).decode("utf-8", "replace"))
        if m:
            return m.group(0)
    return ""


def file_stem(name: str) -> str:
    """파일 이름 → 비교용 앞부분: 확장자·회신 꼬리(-re · _RE_DOAN · -LAN · (2) …)를 뗀 소문자."""
    s = re.sub(r"\.[A-Za-z0-9]{3,4}$", "", str(name or "")).strip().lower()
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"[\s_\-]*(re|rev\d*|doan|lan|final|ok|v\d+|\(\d{1,2}\))$", "", s)   # (2) 같은 짧은 번호만 — (261022) 날짜는 남긴다
    return s


def fill(data: bytes, entries) -> dict:
    """한 번에: 읽기 → 계획 → 칸 바꾸기. 반환 {ok, out, scan, acts, summary, error}"""
    try:
        sc = scan(data)
    except zipfile.BadZipFile:
        return {"ok": False, "error": "엑셀(.xlsx) 파일이 아닙니다 — 예전 형식(.xls)이면 .xlsx 로 저장해서 올려 주세요"}
    if not sc["sheets"]:
        return {"ok": False, "error": "인보이스 시트를 찾지 못했습니다 — 'HS CODE'·'Description' 머리글이 있는 시트가 필요합니다"}
    if not any(s["items"] for s in sc["sheets"]):
        return {"ok": False, "error": "품목 줄이 없습니다 — Description 칸에 규격이 적힌 줄이 필요합니다"}
    idx = build_index(entries)
    acts = plan(sc, idx)
    skipped = []
    out = apply(data, sc, acts, skipped)
    if skipped:
        sheet_of = {s["title"]: s for s in sc["sheets"]}
        sk = set(skipped)
        for a in acts:
            sh = sheet_of[a["sheet"]]
            refs = {"%s%d" % (_col_letter(sh["col_hs"]), a["row"])}
            if sh["col_vn"]:
                refs.add("%s%d" % (_col_letter(sh["col_vn"]), a["row"]))
            if refs & sk:
                a.update(status=CONFLICT, why="수식이 든 칸이라 값을 쓰지 않았습니다 — 직접 확인")
    return {"ok": True, "out": out, "scan": sc, "acts": acts, "summary": summary(acts), "skipped": skipped}
