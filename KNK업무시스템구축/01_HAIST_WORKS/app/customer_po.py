# -*- coding: utf-8 -*-
"""z1191z143 (대표 11-24 「견적 관리 화면에 고객사에서 받은 발주서도 등록할수있게 · 등록한 발주서는 관리번호 또는
수주번호 상세보기에서 견적서처럼 볼수있게」 → 빅터 안 → 「진행」): 고객 발주서 파일 — 규칙·읽기 도구(AI 없음).

  · 자리 = 관리번호(order_id 없음) 또는 수주번호마다 · 파일 = PDF · 사진(jpg·png) · 엑셀(xlsx·xlsm·xls)
  · z1191z160 (대표 11-26 「검토하는 기능을 빼줘 · 여러 개 등록될 수 있게 제한을 풀어줘」):
    한 수주에 발주서를 여러 장 올려도 모두 같은 자격으로 남는다(「최종」·「이전 발주서」 구분 없음 · 올린 순서 최근 위)
  · 엑셀 발주서는 금액을 읽어 보여 주기만 한다 — 수주 금액과 비교·경고·「확인했음」 없음
"""
import re

EXTS = {".pdf": "pdf", ".png": "img", ".jpg": "img", ".jpeg": "img", ".xlsx": "xl", ".xlsm": "xl", ".xls": "xl"}
ACCEPT = ".pdf,.png,.jpg,.jpeg,.xlsx,.xlsm,.xls"
MSG_EXT = "고객 발주서는 PDF · 사진(jpg·png) · 엑셀(xlsx·xls) 파일만 올릴 수 있습니다."
MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12", ".xls": "application/vnd.ms-excel"}


def ext_of(name):
    m = re.search(r"(\.[A-Za-z0-9]{1,5})$", (name or "").strip())
    return m.group(1).lower() if m else ""


def kind_of(name, raw):
    """파일 종류 = 확장자로 정한다.
    z1191z163 (대표 11-26 발주서 등록이 안 됨 「⚠ 파일 내용이 이름과 다릅니다」 → 「검토하는 기능을 빼줘 · 사용자들이 등록하는걸 믿고」):
      예전엔 첫 바이트가 확장자와 맞아야만 받았다 → 문서 보안(DRM)이 걸린 엑셀·PDF, 앞에 다른 글자가 붙은 PDF 같은 정상 발주서도
      「이름만 바꾼 파일」로 막혔다. 이제 확장자가 PDF·사진·엑셀이면 받는다(내용을 못 읽으면 웍스 안 보기 대신 원본 받기로 보임).
      확장자 목록 밖(exe 등)은 그대로 막는다."""
    return EXTS.get(ext_of(name))


def table(c):
    c.execute("""CREATE TABLE IF NOT EXISTS project_po_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tok TEXT UNIQUE NOT NULL,
        project_id INTEGER, order_id INTEGER,
        orig_name TEXT, stored TEXT, size INTEGER, sha256 TEXT, kind TEXT,
        by_id INTEGER, by_name TEXT, created_at TEXT, attached_at TEXT,
        amount REAL, currency TEXT, amount_label TEXT, book_gz BLOB, book_err TEXT,
        amt_ack_by INTEGER, amt_ack_name TEXT, amt_ack_at TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_ppo_project ON project_po_files(project_id)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_ppo_order ON project_po_files(order_id)")
    # z1191z201 (대표 11-28 「보관했다가 삭제해.. 삭제할때 안내문도 붙이고..」): 빼기 = 표시만(removed_at·누가) · 30일 보관 뒤 밤에 지움
    _cols = {r[1] for r in c.execute("PRAGMA table_info(project_po_files)").fetchall()}
    for _cn, _ct in (("removed_at", "TEXT"), ("removed_by", "INTEGER"), ("removed_by_name", "TEXT")):
        if _cn not in _cols:
            c.execute(f"ALTER TABLE project_po_files ADD COLUMN {_cn} {_ct}")


# ── 엑셀 발주서 금액 읽기(AI 없음) — 합계 글자 옆(오른쪽 또는 아래) 숫자 ──
_TOTAL_SUPPLY = re.compile(r"^(공\s*급\s*가\s*액?|공급\s*금액|발\s*주\s*금\s*액|합\s*계\s*금\s*액|총\s*공\s*급\s*가|sub\s*-?\s*total|net\s*amount|amount\s*\(?excl)", re.I)
_TOTAL_ANY = re.compile(r"^(합\s*계|총\s*액|총\s*금\s*액|총\s*합\s*계|합\s*계\s*금\s*액|grand\s*total|total(\s*amount)?|합\s*계\s*\(.*\)|총\s*계)\s*[:：]?\s*$", re.I)
_VAT_INCL = re.compile(r"(vat|부\s*가\s*세)\s*(포\s*함|incl)", re.I)
_CCY = [("USD", re.compile(r"\bUSD\b|US\$|\$")), ("VND", re.compile(r"\bVND\b|₫")), ("JPY", re.compile(r"\bJPY\b|¥")),
        ("CNY", re.compile(r"\bCNY\b|\bRMB\b")), ("EUR", re.compile(r"\bEUR\b|€")), ("KRW", re.compile(r"\bKRW\b|￦|₩|원\s*정|\(원\)|단위\s*[:：]?\s*원"))]


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if v == v else None
    s = str(v or "").replace(",", "").replace("₩", "").replace("￦", "").replace("$", "").strip()
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", s)
    return float(s) if m else None


def read_amount(book):
    """읽어 둔 엑셀(quote_sheets.read_book) → (금액, 통화, 머리 글) · 못 찾으면 (None, 통화, '').
    공급가 글(공급가액·발주금액·Sub Total) 옆 숫자 먼저 · 없으면 합계·Total 옆 숫자(부가세 포함 글이면 그대로 두고 비교 때 ×1.1 도 봄)."""
    supply, anyt = [], []
    ccy = ""
    for sh in (book or {}).get("sheets") or []:
        rows = sh.get("rows") or []
        for ri, r in enumerate(rows):
            for ci, v in enumerate(r):
                if not isinstance(v, str):
                    continue
                s = v.strip()
                if not ccy:
                    for code, rx in _CCY:
                        if rx.search(s):
                            ccy = code
                            break
                key = re.sub(r"\s+", " ", s)[:40]
                bucket = supply if _TOTAL_SUPPLY.match(key) else (anyt if _TOTAL_ANY.match(key) else None)
                if bucket is None:
                    continue
                val = None
                for cj in range(ci + 1, min(ci + 12, len(r))):   # 오른쪽 숫자
                    n = _num(r[cj])
                    if n is not None and n > 0:
                        val = n
                        break
                if val is None and ri + 1 < len(rows) and ci < len(rows[ri + 1]):   # 바로 아래 숫자
                    n = _num(rows[ri + 1][ci])
                    if n is not None and n > 0:
                        val = n
                if val is not None:
                    bucket.append((val, key))
    if supply:
        v, k = max(supply, key=lambda x: x[0])
        return v, ccy, k
    if anyt:
        v, k = max(anyt, key=lambda x: x[0])
        return v, ccy, k
    return None, ccy, ""


def slot_status(files, order_total=None, order_ccy=None):
    """z1191z160: 한 수주(또는 수주번호를 아직 안 고른 옛 자리)의 발주서 줄 → {files: [줄 · 최근 위], st: 'ok'|'none'}.
    최종·이전 구분 없음 · 금액 비교 없음(order_total·order_ccy 는 옛 부르는 곳 호환용 · 쓰지 않음)."""
    fs = sorted(files or [], key=lambda x: x.get("id") or 0, reverse=True)
    return {"files": fs, "st": "ok" if fs else "none"}
