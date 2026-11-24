# -*- coding: utf-8 -*-
"""z1191z143 (대표 11-24 「견적 관리 화면에 고객사에서 받은 발주서도 등록할수있게 · 등록한 발주서는 관리번호 또는
수주번호 상세보기에서 견적서처럼 볼수있게」 → 빅터 안 → 「진행」): 고객 발주서 파일 — 규칙·읽기 도구(AI 없음).

  · 자리 = 관리번호(order_id 없음) 또는 수주번호마다 · 파일 = PDF · 사진(jpg·png) · 엑셀(xlsx·xlsm·xls)
  · 다시 올리면 새 것이 「최종」, 예전 것은 지우지 않고 「이전 발주서」로 남는다(고객이 수정 발주서를 보내는 경우 · 빅터 권한 안)
    최종 = 그 자리에서 가장 나중에 올린 것(id 가 가장 큰 것) · 최종을 빼면 바로 앞 것이 다시 최종
  · 엑셀 발주서만 금액을 읽어 수주 금액과 비교(막지 않음 · 「확인했음」) — PDF·사진은 비교하지 않음
  · 「같은 금액」 = 견적서 z105·z141 규칙(통화가 적혀 있으면 같아야 · 원화 1원 · 외화 0.01) + 부가세 포함 합계(×1.1)도 같음으로 봄
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
    """확장자 + 파일 첫 바이트가 맞아야 그 종류 — 이름만 바꾼 파일은 None."""
    ext = ext_of(name)
    k = EXTS.get(ext)
    head = bytes((raw or b"")[:8])
    if k == "pdf":
        return k if head.startswith(b"%PDF") else None
    if ext == ".png":
        return k if head.startswith(b"\x89PNG") else None
    if ext in (".jpg", ".jpeg"):
        return k if head.startswith(b"\xff\xd8\xff") else None
    if k == "xl":
        return k if (head.startswith(b"PK\x03\x04") or head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")) else None
    return None


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


def same(a, ccy_a, b, ccy_b):
    """None = 비교 못 함 · True/False — 견적서 z105 규칙 + 부가세 포함(×1.1)도 같음."""
    if a is None or b is None:
        return None
    ca, cb = (ccy_a or "").upper(), (ccy_b or "KRW").upper()
    if ca and ca != cb:
        return False
    tol = 1 if cb == "KRW" else 0.01
    a, b = float(a), float(b)
    return abs(a - b) < tol or abs(a - round(b * 1.1, 2)) < max(tol, 1 if cb == "KRW" else 0.05)


def slot_status(files, order_total=None, order_ccy=None):
    """한 자리(관리번호 또는 수주번호)의 발주서 줄들 → {final, prev[], st('ok'|'diff'|'none'|'nocmp'), cmp}
    files = 그 자리의 줄(dict · id 오름차순). 최종 = 마지막."""
    if not files:
        return {"final": None, "prev": [], "st": "none", "cmp": None}
    fs = sorted(files, key=lambda x: x["id"])
    fin = fs[-1]
    prev = list(reversed(fs[:-1]))
    st, cmp_ = "nocmp", None
    if fin.get("kind") == "xl" and order_total is not None and fin.get("amount") is not None:
        cmp_ = same(fin.get("amount"), fin.get("currency"), order_total, order_ccy)
        st = "diff" if (cmp_ is False and not fin.get("amt_ack_at")) else "ok"
    return {"final": fin, "prev": prev, "st": st, "cmp": cmp_}
