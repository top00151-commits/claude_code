"""z1191z61 (대표 2026-11-18 「이 화면에서 견적서 등록을 할수있게 … 견적서에 기록되어있는 기본적인 정보들이 자동으로 작성」):
견적서 파일(PDF·엑셀·사진) → 등록 화면 칸에 넣을 값.

- 대표 결정(11-18): ① 품명 → 장비명 · 모델명은 견적서에 MODEL 칸이 따로 있을 때만(없으면 비움)
                    ② 올린 파일은 프로젝트에 첨부로 보관(이 모듈은 읽기만 · 보관은 main.py)
                    ③ AI 로 읽기(웍스 AI 설정 그대로 — 사업자등록증 판독과 같은 길)
- 실물(대표 메일함 견적서 PDF 3양식 — 본사 검사기 · 본사 자동화 · VINA 한/베/영)에서 PDF 글자는 읽히지만
  금액이 「1 1,300,000」처럼 쪼개져 나온다 → 첫 장 그림을 함께 보내 그림 기준으로 읽게 한다.
- 추측 금지: 견적서에 없는 값은 빈칸. 읽은 값은 화면에서 사람이 확인한 뒤 등록한다.
- z1191z62 (대표 11-18 「엑셀파일에는 기본적으로 암호가 걸려있을수있어 … 비밀번호를 입력하고 등록이 되도록」):
  암호 걸린 엑셀(xlsx·xls)·PDF → need_password · 비밀번호로 풀어서 읽음(msoffcrypto-tool · pdfium).
  비밀번호는 읽는 데만 쓰고 어디에도 저장·기록하지 않는다. 보관 파일은 원본(암호 그대로).
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import unicodedata

MAX_BYTES = 20 * 1024 * 1024
EXTS = (".pdf", ".xlsx", ".xlsm", ".xls", ".png", ".jpg", ".jpeg")
_TEXT_CAP = 6000

FIELDS = ("supplier", "customer", "customer_dept", "contact_name", "contact_title", "supplier_pic",
          "item_name", "model_code", "qty", "unit", "currency", "unit_price", "amount",
          "quote_date", "quote_no", "delivery_terms", "valid_terms", "payment_terms")

SYSTEM = ("당신은 KNK(주식회사 케이엔케이 · KNK VINA)의 견적서 판독기입니다. "
          "견적서에서 각 항목을 원문 그대로 정확히 읽어 JSON 한 개로만 출력합니다. "
          "추측·창작 금지 — 견적서에 없는 항목은 빈 문자열(숫자는 null).")

PROMPT = (
    "이 문서는 견적서(견적서/QUOTATION/BÁO GIÁ)입니다. 아래 JSON 한 개로만 답하세요(설명·코드펜스 금지).\n"
    '{"supplier":"","customer":"","customer_dept":"","contact_name":"","contact_title":"","supplier_pic":"",'
    '"item_name":"","model_code":"","qty":null,"unit":"","currency":"","unit_price":null,"amount":null,'
    '"quote_date":"","quote_no":"","delivery_terms":"","valid_terms":"","payment_terms":""}\n'
    "- supplier: 견적을 낸 회사(공급자 · 상호/Supplier) 이름\n"
    "- customer: 견적을 받는 회사(업체명 · ○○ 귀중 · Customer) 이름 — 원문 그대로\n"
    "- customer_dept: 받는 회사 부서(적혀 있을 때만)\n"
    "- contact_name: 받는 회사 담당자 이름(「담당자」·Requestor·Attention). 호칭 「님」은 빼고 이름만\n"
    "- contact_title: 그 담당자 직책(예: 팀장, 프로, 과장, 차장). 없으면 빈칸\n"
    "- supplier_pic: 공급자 쪽 담당자(PIC) 이름 — 적혀 있을 때만\n"
    "- item_name: 견적 대상 대표 품명(맨 위 「품 명 :」 또는 Item 줄) — 원문 글자 그대로. 세부 부품 줄이 아님\n"
    "- model_code: 「MODEL」·「모델명」이라고 따로 적힌 칸이 있을 때만 그 값. 없으면 빈칸(품명을 넣지 말 것)\n"
    "- qty / unit / unit_price: 대표 품명 줄(제작 금액 줄)의 수량·단위(SET, EA 등)·단가(VAT 별도). 대표 줄이 없으면 null\n"
    "- amount: 공급가액 합계(VAT 별도 · 신규 제작 금액/수정 견적/Total). VAT 포함 최종 금액이 아님\n"
    "- currency: KRW·USD·VND·JPY·CNY·EUR 중 하나(₩·\\·원=KRW, $=USD, VND·₫·동=VND)\n"
    "- quote_date: 견적일자 YYYY-MM-DD\n"
    "- quote_no: 견적 번호(No., Quo No.) — 있을 때만\n"
    "- delivery_terms / valid_terms / payment_terms: 납품(DELIVERY)·유효기간·결제 조건 문장 원문 그대로\n"
    "숫자는 쉼표 없이 숫자로. PDF 에서 뽑은 글자는 숫자 사이에 빈칸이 끼어 「1 1,300,000」처럼 깨질 수 있으니 "
    "그림이 있으면 그림 기준으로 읽고, 수량×단가=금액이 맞는지 확인하세요."
)


def _nfc(s) -> str:
    return unicodedata.normalize("NFC", str(s or "")).strip()


def ext_of(name: str) -> str:
    return os.path.splitext(_nfc(name).lower())[1]


def file_text(raw: bytes, ext: str, password: str = "") -> str:
    """파일에서 글자만(참고용). 실패하면 빈 문자열. (엑셀은 이미 푼 바이트를 받는다 · PDF 는 password)"""
    out = ""
    try:
        if ext == ".pdf":
            import pdfplumber
            with pdfplumber.open(io.BytesIO(raw), password=password or "") as pdf:
                parts = []
                for p in pdf.pages[:4]:
                    parts.append(p.extract_text() or "")
                out = "\n".join(parts)
        elif ext in (".xlsx", ".xlsm"):
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True, read_only=True)
            lines = []
            for ws in wb.worksheets[:3]:
                lines.append(f"[시트 {ws.title}]")
                for row in ws.iter_rows(max_row=150, values_only=True):
                    vals = [str(v).strip() for v in row if v not in (None, "")]
                    if vals:
                        lines.append(" | ".join(vals))
            out = "\n".join(lines)
        elif ext == ".xls":
            import xlrd
            wb = xlrd.open_workbook(file_contents=raw)
            lines = []
            for si in range(min(3, wb.nsheets)):
                sh = wb.sheet_by_index(si)
                lines.append(f"[시트 {sh.name}]")
                for r in range(min(150, sh.nrows)):
                    vals = [str(v).strip() for v in sh.row_values(r) if str(v).strip()]
                    if vals:
                        lines.append(" | ".join(vals))
            out = "\n".join(lines)
    except Exception as e:  # 글자를 못 뽑아도 그림으로 읽을 수 있다
        print(f"[z1191z61] 글자 뽑기 실패({ext}): {str(e)[:120]}")
        out = ""
    return _nfc(out)[:_TEXT_CAP]


def _png_b64(img, max_side: int = 2000) -> str:
    from PIL import Image
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    m = max(w, h)
    if m > max_side:
        sc = max_side / float(m)
        img = img.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def page_image_b64(raw: bytes, ext: str, password: str = "") -> str:
    """PDF 첫 장 또는 사진 → PNG base64. 실패하면 빈 문자열."""
    try:
        if ext == ".pdf":
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(raw, password=password or None)
            try:
                if len(pdf) < 1:
                    return ""
                img = pdf[0].render(scale=2).to_pil()
            finally:
                try:
                    pdf.close()
                except Exception:
                    pass
            return _png_b64(img)
        if ext in (".png", ".jpg", ".jpeg"):
            from PIL import Image
            return _png_b64(Image.open(io.BytesIO(raw)))
    except Exception as e:
        print(f"[z1191z61] 그림 만들기 실패({ext}): {str(e)[:120]}")
    return ""


# ── z1191z62 암호 ─────────────────────────────────────────────
_OLE = bytes.fromhex("d0cf11e0a1b11ae1")   # OLE 통(암호 걸린 xlsx · xls)


def office_locked(raw: bytes, ext: str) -> bool:
    """엑셀에 암호가 걸렸나. xlsx 는 원래 zip(PK) — 암호를 걸면 OLE 통으로 바뀐다. xls 는 열어 봐서."""
    if ext in (".xlsx", ".xlsm"):
        return raw[:8] == _OLE
    if ext == ".xls":
        try:
            import msoffcrypto
            return bool(msoffcrypto.OfficeFile(io.BytesIO(raw)).is_encrypted())
        except ImportError:
            pass
        except Exception:
            return False
        try:
            import xlrd
            xlrd.open_workbook(file_contents=raw, on_demand=True)
            return False
        except Exception as e:
            return "encrypt" in str(e).lower() or "password" in str(e).lower()
    return False


def office_unlock(raw: bytes, password: str):
    """비밀번호로 푼 바이트. 도구 없음 → 'nolib' · 비밀번호 틀림 → None."""
    try:
        import msoffcrypto
    except ImportError:
        return "nolib"
    try:
        of = msoffcrypto.OfficeFile(io.BytesIO(raw))
        of.load_key(password=password)
        out = io.BytesIO()
        of.decrypt(out)
        return out.getvalue()
    except Exception:   # InvalidKeyError·DecryptionError — 비밀번호 틀림(사유 글에 비밀번호가 섞이지 않게 그대로 버림)
        return None


def pdf_locked(raw: bytes, password: str = "") -> bool:
    """PDF 가 (이 비밀번호로) 안 열리나. 비밀번호 때문일 때만 True."""
    try:
        import pypdfium2 as pdfium
        d = pdfium.PdfDocument(raw, password=password or None)
        d.close()
        return False
    except Exception as e:
        return "password" in str(e).lower()


_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def to_num(v):
    """'11,300,000' · '₩ 1 3,000,000' · 11300000 → 숫자. 못 읽으면 None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[\s,₩\\$₫원]", "", _nfc(v))
    s = re.sub(r"(?i)(krw|usd|vnd|won)", "", s)
    m = _NUM_RE.fullmatch(s)
    return float(m.group(0)) if m else None


def norm_currency(v: str) -> str:
    s = _nfc(v).upper()
    if not s:
        return ""
    if s in ("KRW", "USD", "VND", "JPY", "CNY", "EUR"):
        return s
    if any(k in s for k in ("₩", "원", "WON", "\\")):
        return "KRW"
    if "₫" in s or "동" in s or "DONG" in s:
        return "VND"
    if "$" in s or "DOLLAR" in s:
        return "USD"
    if "¥" in s or "円" in s or "엔" in s:
        return "JPY"
    if "€" in s:
        return "EUR"
    return ""


_DATE_RE = re.compile(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})")


def norm_date(v: str) -> str:
    m = _DATE_RE.search(_nfc(v))
    if not m:
        return ""
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return ""
    return f"{y:04d}-{mo:02d}-{d:02d}"


def clean_person(v: str) -> str:
    s = _nfc(v)
    s = re.sub(r"\s*님$", "", s)
    return s.strip()


_TITLE_RE = re.compile(r"\s*(프로|매니저|사원|주임|대리|과장|차장|부장|팀장|실장|파트장|그룹장|책임|선임|수석|연구원|이사|상무|전무|부사장|사장|대표)$")
_KNK_RE = re.compile(r"케이엔케이|케이앤케이|\bKNK\b|K\s*N\s*K\s*VINA", re.I)


def is_knk(name: str) -> bool:
    return bool(_KNK_RE.search(_nfc(name)))


def normalize(data: dict) -> dict:
    """AI 응답 → 정리된 값(글자는 NFC·앞뒤 빈칸 정리 · 숫자/날짜/통화 표준형)."""
    d = data if isinstance(data, dict) else {}
    out = {}
    for k in FIELDS:
        v = d.get(k)
        if k in ("qty", "unit_price", "amount"):
            out[k] = to_num(v)
        elif k == "currency":
            out[k] = norm_currency(v)
        elif k == "quote_date":
            out[k] = norm_date(v)
        elif k in ("contact_name", "supplier_pic"):
            out[k] = clean_person(v)
        else:
            out[k] = _nfc(v) if v is not None else ""
    nm, tt = out.get("contact_name") or "", out.get("contact_title") or ""
    if tt and nm.endswith(tt) and len(nm) > len(tt):          # 「강가상 프로」 + 직책 「프로」 → 이름 「강가상」
        out["contact_name"] = nm[: -len(tt)].strip()
    elif not tt:
        m = _TITLE_RE.search(nm)
        if m and m.start() > 0:
            out["contact_name"], out["contact_title"] = nm[: m.start()].strip(), m.group(1)
    q = out.get("qty")
    if q is not None and (q <= 0 or q != int(q)):
        out["qty"] = None            # 수량은 정수(규정) — 이상하면 비움
    elif q is not None:
        out["qty"] = int(q)
    return out


def checks(f: dict) -> list:
    """z1191z160 (대표 11-26 「검토하는 기능을 빼줘 · 사용자들이 등록하는 걸 믿고 진행」): 경고 없음 — 늘 빈 목록.
    (예전: 공급자 KNK 아님 · 수량×단가≠합계 · 품명 없음 — 아래 옛 판단은 _checks_old_z61 에 기록으로만 남김)"""
    return []


def _checks_old_z61(f: dict) -> list:
    """(z1191z160 전) 쓰지 않음 — 기록용."""
    w = []
    sup, cus = f.get("supplier") or "", f.get("customer") or ""
    if (sup and not is_knk(sup)) or (cus and is_knk(cus)):
        w.append(f"공급자가 「{sup or '?'}」입니다 — 우리 회사가 낸 견적서가 아니라 받은 견적서일 수 있습니다. 맞는 파일인지 확인해 주세요.")
    q, p, a = f.get("qty"), f.get("unit_price"), f.get("amount")
    if q and p and a and abs(q * p - a) > max(1.0, a * 0.001):
        w.append(f"견적서의 수량×단가({q:,} × {p:,.0f} = {q * p:,.0f})와 합계 금액({a:,.0f})이 다릅니다 — 세부 항목이 더 있는지 견적서를 보고 확인해 주세요.")
    if not f.get("item_name"):
        w.append("품명을 찾지 못했습니다 — 장비명은 직접 적어 주세요.")
    return w


def read_quote(raw: bytes, filename: str, password: str = "") -> dict:
    """반환 {ok, mode, fields, warnings, message, need_password, bad_password}. AI 가 없거나 실패해도 예외 없이 ok=False."""
    ext = ext_of(filename)
    res = {"ok": False, "mode": "", "fields": {}, "warnings": [], "message": "", "need_password": False, "bad_password": False}
    if ext not in EXTS:
        res["message"] = "PDF·엑셀(xlsx·xls)·사진(png·jpg) 파일만 읽을 수 있습니다."
        return res
    pdf_pw = ""
    if ext in (".xlsx", ".xlsm", ".xls") and office_locked(raw, ext):
        res["locked"] = True   # 보관 원본은 암호 파일(풀어 읽어도 그대로) — 상세 「🔒 암호 파일」 표시
        if not password:
            res["need_password"] = True
            res["message"] = "암호가 걸린 엑셀입니다 — 비밀번호를 넣으면 풀어서 읽습니다."
            return res
        plain = office_unlock(raw, password)
        if plain == "nolib":
            res["message"] = "암호 걸린 엑셀을 푸는 도구가 서버에 아직 없어 읽지 못했습니다. 파일은 등록할 때 그대로 보관됩니다."
            return res
        if plain is None:
            res["need_password"] = res["bad_password"] = True
            res["message"] = "비밀번호가 맞지 않습니다 — 다시 넣어 주세요."
            return res
        raw = plain
    elif ext == ".pdf" and pdf_locked(raw):
        res["locked"] = True
        if not password:
            res["need_password"] = True
            res["message"] = "암호가 걸린 PDF 입니다 — 비밀번호를 넣으면 풀어서 읽습니다."
            return res
        if pdf_locked(raw, password):
            res["need_password"] = res["bad_password"] = True
            res["message"] = "비밀번호가 맞지 않습니다 — 다시 넣어 주세요."
            return res
        pdf_pw = password
    try:
        from . import ai_client
    except Exception:
        import ai_client  # type: ignore  # 시험용
    if not ai_client.ai_available():
        res["message"] = "AI 를 쓸 수 없어 읽지 못했습니다(관리자 화면의 AI 설정). 파일은 등록할 때 함께 보관됩니다."
        return res
    text = file_text(raw, ext, pdf_pw) if ext in (".pdf", ".xlsx", ".xlsm", ".xls") else ""
    img = page_image_b64(raw, ext, pdf_pw) if ext in (".pdf", ".png", ".jpg", ".jpeg") else ""
    prompt = PROMPT
    if text:
        prompt += "\n\n[파일에서 뽑은 글자 — 참고용 · 숫자 띄어쓰기가 깨졌을 수 있음]\n" + text
    if img:
        ok, resp = ai_client.ai_vision(img, "image/png", prompt, system=SYSTEM, max_tokens=900, temperature=0.0)
        res["mode"] = "ai-vision" + ("+text" if text else "")
    elif text:
        ok, resp = ai_client.ai_chat(prompt, system=SYSTEM, max_tokens=900, temperature=0.0, cache_system=False)
        res["mode"] = "ai-text"
    else:
        res["message"] = "파일에서 글자도 그림도 꺼내지 못했습니다(암호가 걸렸거나 깨진 파일). 파일은 등록할 때 함께 보관됩니다."
        return res
    if not ok:
        print(f"[z1191z61] AI 읽기 실패: {str(resp)[:200]}")
        res["message"] = "AI 가 견적서를 읽지 못했습니다(잠시 뒤 다시 올려 보세요). 파일은 등록할 때 함께 보관됩니다."
        return res
    data = ai_client._parse_json_loose(resp)
    if not isinstance(data, dict):
        res["message"] = "AI 답을 읽지 못했습니다(다시 올려 보세요). 파일은 등록할 때 함께 보관됩니다."
        return res
    f = normalize(data)
    res["fields"] = f
    res["warnings"] = checks(f)
    n = sum(1 for k in FIELDS if f.get(k) not in (None, ""))
    res["ok"] = n > 0
    res["message"] = f"견적서에서 {n}개 항목을 읽었습니다." if n else "견적서에서 읽은 항목이 없습니다."
    return res


def dumps(d) -> str:
    return json.dumps(d, ensure_ascii=False)
