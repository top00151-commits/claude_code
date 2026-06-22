"""
v5H227 (2026-05-31 대표 지시) — 전사 공유 연락처(주소록)

전 직원이 거래처·고객 명함을 등록하면 회사 전체가 함께 검색·열람하는 공용 주소록.

[자동등록 3경로]
  · 명함 사진/스캔 (.jpg .png .pdf)  → biz_doc.extract_text() (Tesseract OCR, 로컬) → parse_card_text()
  · 메일 서명 텍스트 붙여넣기          → parse_signature()
  · 직접 입력 폼                       → 사람이 그대로 입력

3경로 모두 "자동 채움 → 사람이 한 번 확인 → 저장" 흐름. OCR 오인식 안전망.

[정책]
  · OCR·서명 분석 모두 로컬 처리. 외부 API/송신 0건 (biz_doc 와 동일 — 사내 정책 유지).
  · 열람·검색: 전 직원 / 수정·삭제: 등록 본인 + 관리자(admin·ceo).
  · 거래처 종속 customer_contacts 와 별개 테이블(shared_contacts).
"""
from __future__ import annotations

import io
import re
import csv

from .database import db_session

# 저장 컬럼 (입력 폼·OCR·서명 공통 키)
FIELD_KEYS = (
    "name", "position", "company", "department",
    "mobile", "phone", "fax", "email", "address", "note",
)

# ─────────────────────────────────────────────────────────────────────────────
#  파서용 정규식 / 사전
# ─────────────────────────────────────────────────────────────────────────────
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# 휴대폰: 010/011/016/017/018/019 - 3~4 - 4
_RE_MOBILE = re.compile(r"01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}")
# 일반 전화: 02 또는 0XX(X) - 3~4 - 4  (대표전화 1588-XXXX 포함)
_RE_PHONE = re.compile(r"(?:0\d{1,2}|1\d{3})[-.\s]?\d{3,4}[-.\s]?\d{4}")
# 회사명 신호
# 주의: 바레 'Co' 는 이메일 도메인 '.co.kr' 의 'co' 에 오매칭 → 제외. 'Co.,Ltd' 형태만 허용.
_RE_COMPANY = re.compile(
    r"(주식회사|\(주\)|㈜|유한회사|\(유\)|Co\.,?\s*Ltd|\bLtd\b|\bInc\b|\bCorp\b|\bLLC\b|회사|그룹|상사|산업|전자|테크|엔지니어링)",
    re.IGNORECASE,
)
# 직책 사전 (긴 단어 우선 매칭)
_POSITIONS = (
    "대표이사", "부사장", "전무이사", "상무이사", "사외이사", "수석연구원", "책임연구원",
    "선임연구원", "연구소장", "본부장", "사업부장", "센터장", "공장장", "연구원",
    "대표", "사장", "회장", "전무", "상무", "이사", "부장", "차장", "과장",
    "대리", "주임", "사원", "팀장", "실장", "소장", "원장", "부원장",
    "매니저", "선임", "책임", "수석", "엔지니어", "기사", "기장", "주무관", "주사",
)
# 부서 신호 (접미사)
_RE_DEPT = re.compile(r"\S*?(사업부|본부|연구소|연구원|센터|팀|실|부|과|그룹|지사|지점)\b")
# 주소 신호
_RE_ADDR = re.compile(
    r"(특별시|광역시|특별자치|[가-힣]+(시|도)\s|[가-힣]+(시|군|구)\s|[가-힣]+(로|길)\s|번지|\d+층|\d+호|우편)"
)
_RE_ZIP = re.compile(r"\(?\d{5}\)?")
# 라벨(서명) 사전 — 키워드 → 표준 필드
_LABELS = {
    "name":       ("성명", "이름", "name", "담당자", "성함"),
    "position":   ("직책", "직위", "position", "title", "직급"),
    "company":    ("회사", "상호", "company", "법인", "소속"),
    "department": ("부서", "department", "dept", "팀명"),
    "mobile":     ("휴대폰", "휴대전화", "핸드폰", "mobile", "cell", "h.p", "hp", "m.", "m ", "010"),
    "phone":      ("전화", "유선", "사무실", "tel", "phone", "t.", "office", "대표번호", "대표전화"),
    "fax":        ("팩스", "fax", "f.", "f "),
    "email":      ("이메일", "메일", "e-mail", "email", "mail"),
    "address":    ("주소", "address", "addr", "소재지"),
}


def _empty_fields() -> dict:
    return {k: "" for k in FIELD_KEYS}


def _norm_phone(s: str) -> str:
    """전화번호 정규화 — 숫자만 추출 후 하이픈 표기."""
    digits = re.sub(r"\D", "", s or "")
    if not digits:
        return ""
    # 휴대폰
    if digits.startswith("01") and len(digits) in (10, 11):
        if len(digits) == 11:
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    # 서울 02
    if digits.startswith("02"):
        if len(digits) == 9:
            return f"02-{digits[2:5]}-{digits[5:]}"
        if len(digits) == 10:
            return f"02-{digits[2:6]}-{digits[6:]}"
    # 대표번호 1588 등
    if digits.startswith("1") and len(digits) == 8:
        return f"{digits[:4]}-{digits[4:]}"
    # 일반 지역번호 0XX
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return s.strip()


def _looks_like_korean_name(line: str) -> bool:
    """순수 한글 2~4자(공백 허용) — 회사/직책/부서 신호가 없을 때 이름 후보."""
    t = line.strip()
    if not (2 <= len(t.replace(" ", "")) <= 5):
        return False
    if not re.fullmatch(r"[가-힣]{2,5}", t.replace(" ", "")):
        return False
    if _RE_COMPANY.search(t) or _RE_DEPT.search(t):
        return False
    if any(p in t for p in _POSITIONS):
        return False
    return True


def _extract_position(line: str) -> str:
    for p in _POSITIONS:  # 긴 단어 우선
        if p in line:
            return p
    return ""


def _extract_name(lines: list[str], company: str = "") -> str:
    """이름 추출 — 명함/서명 공통. 우선순위:
    1) 직책과 같은 줄("홍길동 부장")의 직책 앞 한글 토큰
    2) 단독 한글 2~4자 줄
    3) 회사/부서/주소/이메일 아닌 줄의 첫 한글 2~4자 토큰"""
    pos_set = set(_POSITIONS)

    def _ok(t: str) -> bool:
        return bool(t) and t not in pos_set and not _RE_COMPANY.search(t)

    # 1) "이름 직책" 같은 줄
    for ln in lines:
        if company and ln == company:
            continue
        if _RE_EMAIL.search(ln):
            continue
        for p in _POSITIONS:
            idx = ln.find(p)
            if idx > 0:
                head = ln[:idx]
                for t in re.findall(r"[가-힣]{2,5}", head):
                    if _ok(t):
                        return t
    # 2) 단독 한글 2~4자 줄
    for ln in lines:
        if company and ln == company:
            continue
        t = ln.strip()
        if re.fullmatch(r"[가-힣]{2,4}", t) and _ok(t):
            return t
    # 3) 회사/부서/주소/이메일 아닌 줄의 첫 한글 토큰
    for ln in lines:
        if company and ln == company:
            continue
        if _RE_COMPANY.search(ln) or _RE_DEPT.search(ln) or _RE_ADDR.search(ln) or _RE_EMAIL.search(ln):
            continue
        for t in re.findall(r"[가-힣]{2,4}", ln):
            if _ok(t):
                return t
    return ""


# 전화 종류 라벨 (소문자 비교). 같은 줄에 Tel/Fax 가 함께 있어도 라벨 위치로 구분.
_LAB_FAX = ("fax", "팩스", "f.", "f:", "f )")
_LAB_TEL = ("tel", "전화", "유선", "사무", "office", "t.", "t:", "대표")
_LAB_MOBILE = ("mobile", "cell", "휴대", "핸드폰", "h.p", "hp", "m.", "m:", "p.", "phone")


def _extract_phones(lines: list[str]) -> dict:
    """줄별로 전화번호를 찾아 라벨 위치(가장 가까운 선행 라벨)로 mobile/phone/fax 분류.
    01x 패턴은 라벨과 무관하게 휴대폰. 라벨 없는 번호는 unknown → 전화로 폴백."""
    res = {"mobile": "", "phone": "", "fax": ""}
    unknown = []
    for ln in lines:
        low = ln.lower()
        labs = []
        for lab in _LAB_FAX:
            i = low.find(lab)
            if i >= 0:
                labs.append((i, "fax"))
        for lab in _LAB_TEL:
            i = low.find(lab)
            if i >= 0:
                labs.append((i, "phone"))
        for lab in _LAB_MOBILE:
            i = low.find(lab)
            if i >= 0:
                labs.append((i, "mobile"))
        labs.sort()
        for m in _RE_PHONE.finditer(ln):
            num = _norm_phone(m.group(0))
            digits = re.sub(r"\D", "", m.group(0))
            if digits.startswith("01") and len(digits) >= 10:
                if not res["mobile"]:
                    res["mobile"] = num
                continue
            kind = None
            for pos, k in labs:
                if pos <= m.start():
                    kind = k
            if kind and not res[kind]:
                res[kind] = num
            elif kind is None:
                unknown.append(num)
    if not res["phone"] and unknown:
        res["phone"] = unknown[0]
    return res


# ─────────────────────────────────────────────────────────────────────────────
#  명함 텍스트 파서
# ─────────────────────────────────────────────────────────────────────────────
def parse_card_text(text: str) -> dict:
    """명함 OCR 텍스트 → 연락처 필드 best-effort 추출.
    OCR 은 줄 순서/오탈자가 흔하므로 결과는 사람이 확인 후 저장하는 전제."""
    f = _empty_fields()
    if not text:
        return f
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    joined = "\n".join(lines)

    # 이메일 — OCR 이 '@' 주변에 공백을 넣는 경우가 많아 정규화 후 검색
    m = _RE_EMAIL.search(re.sub(r"\s*@\s*", "@", joined))
    if m:
        f["email"] = m.group(0).strip().rstrip(".")

    # 전화/휴대폰/팩스 — 라벨 위치 기반 분류 (한 줄 Tel/Fax 혼재 대응)
    ph = _extract_phones(lines)
    f["mobile"], f["phone"], f["fax"] = ph["mobile"], ph["phone"], ph["fax"]

    # 회사
    for ln in lines:
        if _RE_COMPANY.search(ln) and len(ln) <= 40:
            f["company"] = ln
            break

    # 직책
    for ln in lines:
        p = _extract_position(ln)
        if p:
            f["position"] = p
            break

    # 부서
    for ln in lines:
        if ln == f.get("company"):
            continue
        dm = _RE_DEPT.search(ln)
        if dm and not _RE_COMPANY.search(ln) and len(ln) <= 25 and not _RE_EMAIL.search(ln):
            f["department"] = ln
            break

    # 이름
    f["name"] = _extract_name(lines, f.get("company") or "")

    # 주소
    for ln in lines:
        if _RE_ADDR.search(ln) and len(ln) >= 8:
            f["address"] = ln
            break

    return f


# ─────────────────────────────────────────────────────────────────────────────
#  메일 서명 파서
# ─────────────────────────────────────────────────────────────────────────────
def _label_of(line: str):
    """줄 앞부분이 'XXX :' / 'XXX)' 형태 라벨이면 (필드키, 값) 반환."""
    m = re.match(r"\s*([A-Za-z가-힣.\s]{1,12})[)\]:：>\-]\s*(.+)$", line)
    if not m:
        return None, None
    key_raw = m.group(1).strip().lower()
    val = m.group(2).strip()
    for field, kws in _LABELS.items():
        for kw in kws:
            if kw in key_raw:
                return field, val
    return None, None


def parse_signature(text: str) -> dict:
    """메일 서명 텍스트 → 연락처 필드. 라벨('전화:', 'E-mail:') 우선, 없으면 패턴."""
    f = _empty_fields()
    if not text:
        return f
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # 1) 라벨 기반
    for ln in lines:
        field, val = _label_of(ln)
        if field and not f.get(field) and val:
            if field in ("mobile", "phone", "fax"):
                mm = (_RE_MOBILE.search(val) or _RE_PHONE.search(val))
                f[field] = _norm_phone(mm.group(0)) if mm else val
            elif field == "email":
                em = _RE_EMAIL.search(val)
                f[field] = em.group(0) if em else val
            else:
                f[field] = val

    # 2) 패턴 보강 (라벨이 없던 항목)
    joined = "\n".join(lines)
    if not f["email"]:
        m = _RE_EMAIL.search(re.sub(r"\s*@\s*", "@", joined))
        if m:
            f["email"] = m.group(0).rstrip(".")
    if not (f["mobile"] and f["phone"] and f["fax"]):
        ph = _extract_phones(lines)
        f["mobile"] = f["mobile"] or ph["mobile"]
        f["phone"] = f["phone"] or ph["phone"]
        f["fax"] = f["fax"] or ph["fax"]
    if not f["company"]:
        for ln in lines:
            if _RE_COMPANY.search(ln) and len(ln) <= 40:
                f["company"] = ln
                break
    if not f["position"]:
        for ln in lines:
            p = _extract_position(ln)
            if p:
                f["position"] = p
                break
    if not f["name"]:
        f["name"] = _extract_name(lines, f.get("company") or "")
    return f


# ─────────────────────────────────────────────────────────────────────────────
#  사내 AI 항목 분리 (E — 2026-05-31 대표 승인)
#  · OCR 로 읽은 "텍스트만" AI 에 전송 (이미지는 절대 전송 안 함).
#  · AI 미설정/실패/형식오류 시 None 반환 → 호출부가 정규식 결과로 자동 폴백.
# ─────────────────────────────────────────────────────────────────────────────
_AI_CARD_SYSTEM = (
    "너는 비즈니스 명함에서 연락처 항목을 추출하는 도우미다. "
    "명함은 한국어·영어·중국어(中)·베트남어(越) 등 어떤 언어든 될 수 있다. "
    "다음 키만 가진 JSON 하나만 출력하라(설명·코드블록 금지): "
    "name(이름), position(직책/직위), company(회사명), department(부서), "
    "mobile(휴대폰), phone(회사전화), fax(팩스), email(이메일), address(주소), note(비고). "
    "name·position·company·department·address 는 명함에 적힌 **원문 언어 그대로** 적어라(번역하지 마라). "
    "단, 명함이 한국어가 아닌 외국어(중국어·베트남어·영어 등)인 경우 note 에 한국 직원이 읽을 수 있도록 "
    "'한글: <이름 한글발음> / <회사 한글표기 또는 뜻>' 형식으로 한글 병기를 넣어라. "
    "한국어 명함이면 note 는 빈 문자열로 둬라. "
    "전화번호는 010-1234-5678 형식으로 정규화하라. "
    "확실하지 않은 값은 빈 문자열로 둬라. 없는 키는 빈 문자열. 추측으로 지어내지 마라."
)


def _ai_json_to_fields(resp: str) -> dict | None:
    """AI 응답(JSON 문자열, 잡텍스트/코드블록 가능) → 필드 dict. 실패 시 None."""
    if not resp:
        return None
    import json
    m = re.search(r"\{.*\}", resp, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    out = _empty_fields()
    for k in FIELD_KEYS:
        v = data.get(k)
        if isinstance(v, str):
            out[k] = v.strip()
        elif v is not None:
            out[k] = str(v).strip()
    for k in ("mobile", "phone", "fax"):  # 전화류 정규화
        if out[k]:
            out[k] = _norm_phone(out[k])
    return out


def ai_parse_card(text: str) -> dict | None:
    """OCR 텍스트 → AI 로 항목 분리. AI 비활성/실패 시 None (호출부 폴백)."""
    if not text or not text.strip():
        return None
    try:
        from . import ai_client
    except Exception:
        return None
    if not ai_client.ai_available():
        return None
    ok, resp = ai_client.ai_chat(text[:4000], system=_AI_CARD_SYSTEM,
                                 max_tokens=400, temperature=0)
    if not ok:
        return None
    return _ai_json_to_fields(resp)


# 비전(이미지 직접 판독) 지시문 — 이미지를 AI 가 직접 읽고 항목 추출
_AI_VISION_PROMPT = (
    "이 이미지는 비즈니스 명함이다. 명함에 보이는 정보를 읽어 연락처 항목을 추출하라. "
    "명함 언어가 한국어가 아니어도(영어·중국어·베트남어 등) 그대로 읽어라. "
    "외국어 명함이면 note 에 이름·회사의 한글 병기를 넣어라."
)


def ai_vision_card(image_path: str) -> dict | None:
    """명함 이미지 → 멀티모달 AI(비전)로 직접 판독·항목 추출. 실패/비활성 시 None.
    Tesseract 보다 실제 명함 인식율이 크게 높음. PDF·비활성·오류 시 None 반환(폴백)."""
    if not image_path or image_path.lower().endswith(".pdf"):
        return None  # PDF 는 비전 경로 제외 → Tesseract 폴백
    try:
        from . import ai_client
    except Exception:
        return None
    if not ai_client.ai_available():
        return None
    # 모든 포맷을 JPEG 로 정규화 + 과대 이미지 축소(토큰·비용 절감)
    try:
        from PIL import Image
        import io as _io, base64 as _b64
        im = Image.open(image_path)
        if im.mode != "RGB":
            im = im.convert("RGB")
        w, h = im.size
        m = max(w, h)
        if m > 1600:
            s = 1600.0 / m
            im = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
        buf = _io.BytesIO()
        im.save(buf, "JPEG", quality=90)
        b64 = _b64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None
    ok, resp = ai_client.ai_vision(b64, "image/jpeg", _AI_VISION_PROMPT,
                                   system=_AI_CARD_SYSTEM, max_tokens=600)
    if not ok:
        return None
    return _ai_json_to_fields(resp)


def _merge_fields(primary: dict, secondary: dict) -> dict:
    """primary 우선, 빈 항목만 secondary 로 채움."""
    out = _empty_fields()
    for k in FIELD_KEYS:
        out[k] = (primary.get(k) or "").strip() or (secondary.get(k) or "").strip()
    return out


def parse_card_best(variants: list, use_ai: bool = True) -> dict:
    """명함 다중-PSM 결과 리스트([(psm, text), ...]) → 최적 항목 dict.
    1) 각 PSM 텍스트를 정규식 파싱 → 항목 수 최다 결과 채택
    2) (use_ai) 항목 최다 텍스트를 AI 로 재분리 → AI 우선·정규식 보완 병합
    반환: {**fields, '_engine': 'ai+regex'|'regex', '_raw': best_text}"""
    if not variants:
        return {**_empty_fields(), "_engine": "none", "_raw": ""}
    best_fields, best_text, best_score = _empty_fields(), "", -1
    for _psm, txt in variants:
        ff = parse_card_text(txt)
        score = sum(1 for v in ff.values() if v)
        if score > best_score:
            best_fields, best_text, best_score = ff, txt, score
    engine = "regex"
    result = best_fields
    if use_ai:
        ai_fields = ai_parse_card(best_text)
        if ai_fields and sum(1 for v in ai_fields.values() if v) > 0:
            result = _merge_fields(ai_fields, best_fields)  # AI 우선, 정규식 보완
            engine = "ai+regex"
    return {**result, "_engine": engine, "_raw": best_text}


# ─────────────────────────────────────────────────────────────────────────────
#  중복 감지
# ─────────────────────────────────────────────────────────────────────────────
def find_duplicates(c, mobile: str = "", email: str = "", phone: str = "",
                    exclude_id: int = 0) -> list[dict]:
    """같은 휴대폰/이메일/전화(숫자 일치)를 가진 기존 연락처 목록."""
    keys = []
    if mobile:
        keys.append(("mobile", re.sub(r"\D", "", mobile)))
    if email:
        keys.append(("email", email.strip().lower()))
    if phone:
        keys.append(("phone", re.sub(r"\D", "", phone)))
    if not keys:
        return []
    rows = c.execute("SELECT * FROM shared_contacts").fetchall()
    out = []
    for r in rows:
        if exclude_id and r["id"] == exclude_id:
            continue
        hit = False
        for field, val in keys:
            if not val:
                continue
            cur = (r[field] or "")
            if field == "email":
                if cur.strip().lower() == val:
                    hit = True
            else:
                if re.sub(r"\D", "", cur) == val and val:
                    hit = True
        if hit:
            out.append(dict(r))
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  CRUD
# ─────────────────────────────────────────────────────────────────────────────
VISIBILITIES = ("private", "dept", "company")   # v5H226z580 공유 범위


def _vis_clause(user) -> tuple[str, list]:
    """v5H226z580 가시성 필터 (SQL 조각, 파라미터).
    내가 볼 수 있는 연락처 = ①내가 등록 + ②전사 공유 + ③내 부서로 공유.
    user None → 필터 없음(내부/시스템용). 관리자도 남의 '개인'은 못 봄(대표 결정)."""
    if not user:
        return "", []
    uid = user.get("id")
    tid = user.get("team_id")
    return (
        "(sc.created_by=? OR sc.visibility='company'"
        " OR (sc.visibility='dept' AND sc.share_team_id IS NOT NULL AND sc.share_team_id=?))",
        [uid, tid],
    )


def list_contacts(c, q: str = "", user=None) -> list[dict]:
    """연락처 목록 — 가시성 필터(개인/부서/전사) 적용.
    검색어 있으면 이름·회사·전화·이메일·부서·직책 LIKE."""
    q = (q or "").strip()
    where, params = [], []
    if q:
        like = f"%{q}%"
        where.append(
            "(sc.name LIKE ? OR sc.company LIKE ? OR sc.mobile LIKE ?"
            " OR sc.phone LIKE ? OR sc.email LIKE ? OR sc.department LIKE ?"
            " OR sc.position LIKE ? OR sc.note LIKE ?)"
        )
        params += [like] * 8
    vsql, vparams = _vis_clause(user)
    if vsql:
        where.append(vsql)
        params += vparams
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    rows = c.execute(
        "SELECT sc.*, u.name AS creator_name, t.name AS share_team_name "
        "FROM shared_contacts sc "
        "LEFT JOIN users u ON sc.created_by = u.id "
        "LEFT JOIN teams t ON sc.share_team_id = t.id "
        + wsql + " ORDER BY sc.name COLLATE NOCASE",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def get_contact(c, cid: int):
    row = c.execute(
        """SELECT sc.*, u.name AS creator_name, u2.name AS updater_name,
                  cu.name AS customer_name, t.name AS share_team_name
           FROM shared_contacts sc
           LEFT JOIN users u  ON sc.created_by = u.id
           LEFT JOIN users u2 ON sc.updated_by = u2.id
           LEFT JOIN customers cu ON sc.customer_id = cu.id
           LEFT JOIN teams t ON sc.share_team_id = t.id
           WHERE sc.id = ?""",
        (cid,),
    ).fetchone()
    return dict(row) if row else None


def can_see(contact: dict, user: dict) -> bool:
    """v5H226z580 가시성 단건 판정 — 상세/내보내기 게이트."""
    if not contact or not user:
        return False
    vis = contact.get("visibility") or "private"
    if vis == "company":
        return True
    if contact.get("created_by") == user.get("id"):
        return True
    if vis == "dept" and contact.get("share_team_id") and \
       contact.get("share_team_id") == user.get("team_id"):
        return True
    return False


def _norm_share(visibility, team_id) -> tuple[str, int | None]:
    """v5H226z580 공유 범위 정규화 — dept 만 team_id 보존, 그 외 NULL."""
    vis = (visibility or "private").strip()
    if vis not in VISIBILITIES:
        vis = "private"
    stid = (team_id or None) if vis == "dept" else None
    return vis, stid


def create_contact(c, data: dict, user_id: int) -> int:
    vis, stid = _norm_share(data.get("visibility"), data.get("share_team_id"))
    cur = c.execute(
        """INSERT INTO shared_contacts
           (name, position, company, department, mobile, phone, fax, email,
            address, note, card_image, source, customer_id,
            visibility, share_team_id, created_by, updated_by)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            (data.get("name") or "").strip(),
            (data.get("position") or "").strip() or None,
            (data.get("company") or "").strip() or None,
            (data.get("department") or "").strip() or None,
            (data.get("mobile") or "").strip() or None,
            (data.get("phone") or "").strip() or None,
            (data.get("fax") or "").strip() or None,
            (data.get("email") or "").strip() or None,
            (data.get("address") or "").strip() or None,
            (data.get("note") or "").strip() or None,
            (data.get("card_image") or "").strip() or None,
            (data.get("source") or "manual").strip(),
            data.get("customer_id") or None,
            vis,
            stid,
            user_id,
            user_id,
        ),
    )
    return cur.lastrowid


def set_share(c, cid: int, visibility: str, team_id, user_id: int) -> None:
    """v5H226z580 연락처 공유 범위 변경 (개인/부서/전사). 부서=team_id 대상."""
    vis, stid = _norm_share(visibility, team_id)
    c.execute(
        """UPDATE shared_contacts SET
             visibility=?, share_team_id=?,
             updated_by=?, updated_at=datetime('now','localtime')
           WHERE id=?""",
        (vis, stid, user_id, cid),
    )


def update_contact(c, cid: int, data: dict, user_id: int) -> None:
    c.execute(
        """UPDATE shared_contacts SET
             name=?, position=?, company=?, department=?, mobile=?, phone=?,
             fax=?, email=?, address=?, note=?, customer_id=?,
             updated_by=?, updated_at=datetime('now','localtime')
           WHERE id=?""",
        (
            (data.get("name") or "").strip(),
            (data.get("position") or "").strip() or None,
            (data.get("company") or "").strip() or None,
            (data.get("department") or "").strip() or None,
            (data.get("mobile") or "").strip() or None,
            (data.get("phone") or "").strip() or None,
            (data.get("fax") or "").strip() or None,
            (data.get("email") or "").strip() or None,
            (data.get("address") or "").strip() or None,
            (data.get("note") or "").strip() or None,
            data.get("customer_id") or None,
            user_id,
            cid,
        ),
    )


def delete_contact(c, cid: int) -> None:
    c.execute("DELETE FROM shared_contacts WHERE id=?", (cid,))


def can_edit(contact: dict, user: dict) -> bool:
    """수정·삭제 권한 — 등록 본인 + 관리자(admin·ceo)."""
    if not user or not contact:
        return False
    if user.get("role") in ("admin", "ceo"):
        return True
    return contact.get("created_by") == user.get("id")


# ─────────────────────────────────────────────────────────────────────────────
#  CSV 내보내기 (UTF-8 BOM — 사내 정책: openpyxl 미사용)
# ─────────────────────────────────────────────────────────────────────────────
def export_csv_bytes(c, user=None) -> bytes:
    rows = list_contacts(c, user=user)   # v5H226z580 내가 볼 수 있는 것만
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["이름", "직책", "회사", "부서", "휴대폰", "회사전화", "팩스",
                "이메일", "주소", "비고", "등록자", "등록일시"])
    for r in rows:
        w.writerow([
            r.get("name") or "", r.get("position") or "", r.get("company") or "",
            r.get("department") or "", r.get("mobile") or "", r.get("phone") or "",
            r.get("fax") or "", r.get("email") or "", r.get("address") or "",
            r.get("note") or "", r.get("creator_name") or "", r.get("created_at") or "",
        ])
    return ("﻿" + buf.getvalue()).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
#  vCard(.vcf) / QR / Outlook CSV 내보내기 (휴대폰·메일·아웃룩 반영용)
#  vCard 는 휴대폰·메일·아웃룩이 모두 가져오는 만국 표준. QR 은 휴대폰 즉시 추가용.
# ─────────────────────────────────────────────────────────────────────────────
def _vcard_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace("\n", "\\n") \
                    .replace(",", "\\,").replace(";", "\\;")


def to_vcard(ct: dict) -> str:
    """연락처 dict → vCard 3.0 텍스트 (UTF-8, CRLF). 휴대폰/아웃룩/메일 공통."""
    e = _vcard_escape
    name = (ct.get("name") or "").strip()
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:{e(name)};;;;", f"FN:{e(name)}"]
    org, dept = (ct.get("company") or ""), (ct.get("department") or "")
    if org or dept:
        lines.append(f"ORG:{e(org)};{e(dept)}")
    if ct.get("position"):
        lines.append(f"TITLE:{e(ct['position'])}")
    if ct.get("mobile"):
        lines.append(f"TEL;TYPE=CELL:{e(ct['mobile'])}")
    if ct.get("phone"):
        lines.append(f"TEL;TYPE=WORK,VOICE:{e(ct['phone'])}")
    if ct.get("fax"):
        lines.append(f"TEL;TYPE=WORK,FAX:{e(ct['fax'])}")
    if ct.get("email"):
        lines.append(f"EMAIL;TYPE=INTERNET,WORK:{e(ct['email'])}")
    if ct.get("address"):
        lines.append(f"ADR;TYPE=WORK:;;{e(ct['address'])};;;;")
    if ct.get("note"):
        lines.append(f"NOTE:{e(ct['note'])}")
    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


def vcards_all(c, user=None) -> str:
    """내가 볼 수 있는 연락처 → vCard 묶음 (.vcf 한 파일에 여러 장). v5H226z580."""
    return "".join(to_vcard(r) for r in list_contacts(c, user=user))


def vcard_qr_png(ct: dict) -> bytes | None:
    """연락처 vCard → QR 코드 PNG bytes. 휴대폰 카메라로 스캔 → 즉시 연락처 추가.
    qrcode 미설치 시 None."""
    try:
        import qrcode
    except Exception:
        return None
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(to_vcard(ct))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def export_outlook_csv_bytes(c, user=None) -> bytes:
    """Outlook 가져오기용 CSV (영문 헤더 — Outlook 가져오기 마법사가 자동 매핑).
    한글 이름은 First Name 에 넣어 표시명으로 사용. UTF-8 BOM."""
    rows = list_contacts(c, user=user)   # v5H226z580 내가 볼 수 있는 것만
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["First Name", "Last Name", "Title", "Company", "Department",
                "Mobile Phone", "Business Phone", "Business Fax",
                "E-mail Address", "Business Street", "Notes"])
    for r in rows:
        w.writerow([
            r.get("name") or "", "", r.get("position") or "", r.get("company") or "",
            r.get("department") or "", r.get("mobile") or "", r.get("phone") or "",
            r.get("fax") or "", r.get("email") or "", r.get("address") or "",
            r.get("note") or "",
        ])
    return ("﻿" + buf.getvalue()).encode("utf-8")
