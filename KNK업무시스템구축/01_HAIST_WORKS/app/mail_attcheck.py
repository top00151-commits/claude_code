# -*- coding: utf-8 -*-
"""메일 첨부 안전 검사(대표 11-18 「위험한 피싱 파일들도 자동으로 찾아 안전하게」).

이름만 보지 않고 **파일 속(앞머리 바이트·압축 안 목록·문서 속 매크로)**까지 본다. 밖으로 보내지 않는다(이 서버 안에서만).
  - block : 열면 바로 감염될 수 있는 것(위장 실행파일 · 실행파일인데 이름을 바꾼 것 · 압축 안 실행파일)
  - exec  : 실행파일(이름 그대로) — 경고 뒤 받기(지금까지와 같음)
  - warn  : 매크로 문서 · 웹페이지(HTML/SVG) 파일 · 비밀번호 압축 · 이름과 속이 다른 PDF
  - ok
반환 dict: {"kind": ..., "why": 사람이 읽는 이유, "inside": [압축 안 파일 이름 몇 개]}
"""
import io
import zipfile

from .mail_guard import EXEC_EXTS, MACRO_EXTS, HTML_EXTS, ARCHIVE_EXTS, DOC_LIKE, name_ext as _name_ext

MAX_SCAN = 25 * 1024 * 1024        # 이보다 크면 속은 안 봄(이름만)
_OOXML = {".docx", ".xlsx", ".pptx", ".dotx", ".xltx", ".potx", ".ppsx"}
_OLE_DOC = {".doc", ".xls", ".ppt", ".dot", ".xlt"}
_VBA_UTF16 = "_VBA_PROJECT".encode("utf-16-le")
_RASTER = ("image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/bmp", "image/x-icon")


def ext_of(name) -> str:
    """11-26 — 끝 점·빈칸·보이지 않는 글자를 떼고 읽음(판정과 같게 · mail_guard.name_ext)."""
    return _name_ext(name)


def _base_ext(name) -> str:
    from .mail_guard import _NAME_TAIL
    n = _NAME_TAIL.sub("", (name or "").strip().lower())
    e = ext_of(n)
    return ext_of(n[: -len(e)]) if e else ""


def quick(filename, mime="") -> dict:
    """이름·종류만으로(속은 안 봄) — 읽기 화면 꼬리표용. 빠름."""
    e = ext_of(filename)
    m = (mime or "").lower()
    if e in EXEC_EXTS:
        if _base_ext(filename) in DOC_LIKE:
            return {"kind": "block", "why": "문서로 위장한 실행파일", "inside": []}
        return {"kind": "exec", "why": "실행파일", "inside": []}
    if e in MACRO_EXTS:
        return {"kind": "warn", "why": "매크로가 든 문서 — 열 때 「콘텐츠 사용」을 누르지 마세요", "inside": []}
    if e in HTML_EXTS or m in ("text/html", "image/svg+xml", "application/xhtml+xml"):
        return {"kind": "warn", "why": "웹페이지 파일 — 로그인 화면 위장에 흔함(비밀번호 넣지 마세요)", "inside": []}
    return {"kind": "ok", "why": "", "inside": []}


def _zip_scan(data: bytes) -> dict:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        return {}
    names, enc, bad, html = [], False, [], []
    try:
        for zi in zf.infolist()[:500]:
            nm = zi.filename or ""
            names.append(nm)
            if zi.flag_bits & 0x1:
                enc = True
            e = ext_of(nm)
            if e in EXEC_EXTS:
                bad.append(nm)
            elif e in HTML_EXTS:
                html.append(nm)
    except Exception:
        return {}
    return {"names": names, "enc": enc, "bad": bad, "html": html, "zf": zf}


def inspect(filename, mime="", data=b"") -> dict:
    """이름 + 파일 속까지. data 가 없거나 너무 크면 이름만(quick)."""
    q = quick(filename, mime)
    if q["kind"] == "block":
        return q
    if not data or len(data) > MAX_SCAN:
        return q
    e = ext_of(filename)
    head = bytes(data[:8])
    # ① 실행파일인데 이름을 바꾼 것(윈도 실행파일 MZ · 리눅스 ELF)
    if (head[:2] == b"MZ" or head[:4] == b"\x7fELF") and e not in EXEC_EXTS:
        return {"kind": "block", "why": "속은 실행파일인데 이름을 「%s」로 바꿈" % (e or "확장자 없음"), "inside": []}
    # ② 압축(zip 계열) — 안의 파일 이름 보기
    if head[:2] == b"PK" and e not in _OOXML and e not in MACRO_EXTS:
        z = _zip_scan(data)
        if z:
            ins = z["names"][:6]
            if z["bad"]:
                return {"kind": "block", "why": "압축 안에 실행파일(%s)" % ", ".join(z["bad"][:2]), "inside": ins}
            if z["enc"]:
                return {"kind": "warn", "why": "비밀번호 걸린 압축 — 백신 검사를 피하는 수법(보낸 사람에게 전화로 확인)", "inside": ins}
            if z["html"]:
                return {"kind": "warn", "why": "압축 안에 웹페이지 파일(%s) — 로그인 화면 위장에 흔함" % ", ".join(z["html"][:2]), "inside": ins}
            if q["kind"] == "ok":
                return {"kind": "ok", "why": "", "inside": ins}
    # ③ 워드·엑셀 새 형식(.docx/.xlsx)인데 속에 매크로가 숨은 것
    if e in _OOXML and head[:2] == b"PK":
        z = _zip_scan(data)
        if z and any(n.lower().endswith("vbaproject.bin") for n in z["names"]):
            return {"kind": "warn", "why": "매크로가 숨어 있는 문서(이름은 %s) — 「콘텐츠 사용」을 누르지 마세요" % e, "inside": []}
    # ④ 옛 형식(.doc/.xls) 속 매크로
    if e in _OLE_DOC and head[:4] == b"\xd0\xcf\x11\xe0" and _VBA_UTF16 in data:
        return {"kind": "warn", "why": "매크로가 든 문서 — 「콘텐츠 사용」을 누르지 마세요", "inside": []}
    # ⑤ PDF 라면서 속은 PDF 가 아님
    if e == ".pdf" and b"%PDF" not in data[:1024]:
        return {"kind": "warn", "why": "이름은 PDF 인데 속은 PDF 가 아님", "inside": []}
    return q


def inline_ok(mime, filename="") -> bool:
    """브라우저 안에서 바로 열어도 되는가 — 그림(래스터)·PDF 만. SVG·HTML 은 스크립트가 들 수 있어 안 됨."""
    m = (mime or "").lower().split(";")[0].strip()
    if ext_of(filename) in HTML_EXTS:
        return False
    return m in _RASTER or m == "application/pdf"
