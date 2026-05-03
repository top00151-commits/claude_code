"""
v5H57 (2026-05-03) — 사업자등록증 자동 파서

PDF / 이미지(JPG/PNG) → 사업자번호·상호·대표자·주소 자동 추출.

[지원 입력]
  · 텍스트 PDF (정부24/홈택스 발급분) — pdfplumber 단독 (외부 의존 0)
  · 스캔 PDF / 이미지 (.pdf .jpg .jpeg .png) — pytesseract (Tesseract 별도 설치 필요)

[Tesseract 설치 (Windows, 한 번만)]
  https://github.com/UB-Mannheim/tesseract/wiki
  -> tesseract-ocr-w64-setup-v5.x.x.exe 다운로드 -> 설치 시 "Korean" 언어팩 체크
  -> 설치 경로: C:/Program Files/Tesseract-OCR/tesseract.exe
  -> 자동 감지됨 (수동 PATH 설정 불필요)

[정책]
  · 외부 API 0건. 모든 OCR 로컬 실행.
  · 데이터 외부 송신 0건.
  · Tesseract 미설치 시 PDF만 동작 + 친절한 안내 메시지.
"""

import os
import re
import subprocess

# Tesseract 자동 경로 탐색 (Windows 표준 설치 경로)
_TESS_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Tesseract-OCR\tesseract.exe",
]

# 앱 내부 tessdata 디렉터리 (관리자 권한 불필요)
_APP_TESSDATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "tessdata"
)
os.makedirs(_APP_TESSDATA_DIR, exist_ok=True)


def _setup_tesseract_path() -> str | None:
    """Tesseract 실행 파일 경로 자동 탐색. 발견 시 pytesseract에 등록."""
    try:
        import pytesseract
    except ImportError:
        return None
    # 환경 변수 우선
    env_path = os.environ.get("TESSERACT_CMD")
    if env_path and os.path.isfile(env_path):
        pytesseract.pytesseract.tesseract_cmd = env_path
        return env_path
    # PATH 기본 탐색
    import shutil
    found = shutil.which("tesseract")
    if found:
        pytesseract.pytesseract.tesseract_cmd = found
        return found
    # 표준 경로 후보
    for cand in _TESS_CANDIDATES:
        if os.path.isfile(cand):
            pytesseract.pytesseract.tesseract_cmd = cand
            return cand
    return None


def has_tesseract() -> bool:
    return _setup_tesseract_path() is not None


def get_installed_langs() -> list[str]:
    """Tesseract 에 설치된 언어 코드 목록 (예: ['eng','kor','osd'])."""
    tess = _setup_tesseract_path()
    if not tess:
        return []
    langs = set()
    # 1) Tesseract 기본 tessdata 디렉터리
    try:
        r = subprocess.run([tess, "--list-langs"], capture_output=True,
                           text=True, timeout=5)
        for line in (r.stdout or "").splitlines():
            line = line.strip()
            if line and not line.startswith("List"):
                langs.add(line)
    except Exception:
        pass
    # 2) 앱 내부 tessdata (관리자 권한 없이 추가한 언어)
    if os.path.isdir(_APP_TESSDATA_DIR):
        for fn in os.listdir(_APP_TESSDATA_DIR):
            if fn.endswith(".traineddata"):
                langs.add(fn[:-len(".traineddata")])
    return sorted(langs)


def has_korean() -> bool:
    return "kor" in get_installed_langs()


def download_korean_traineddata() -> dict:
    """한국어 traineddata 자동 다운로드 (사용자 명시적 트리거).
    GitHub tessdata_best 에서 ~28MB. 앱 내부 tessdata 폴더에 저장.
    이미 있으면 skip. 반환: {ok, message, path, size}"""
    target = os.path.join(_APP_TESSDATA_DIR, "kor.traineddata")
    if os.path.isfile(target) and os.path.getsize(target) > 1_000_000:
        return {"ok": True, "message": "이미 설치되어 있습니다.",
                "path": target, "size": os.path.getsize(target)}
    import urllib.request
    sources = [
        # 1순위: tessdata_best (LSTM 최고 정확도)
        "https://github.com/tesseract-ocr/tessdata_best/raw/main/kor.traineddata",
        # 2순위: tessdata (표준)
        "https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata",
        # 3순위: tessdata_fast (작은 크기)
        "https://github.com/tesseract-ocr/tessdata_fast/raw/main/kor.traineddata",
    ]
    last_err = None
    for url in sources:
        try:
            tmp = target + ".part"
            urllib.request.urlretrieve(url, tmp)
            size = os.path.getsize(tmp)
            if size < 1_000_000:
                os.unlink(tmp)
                last_err = f"다운로드 파일이 너무 작음 ({size} bytes) — 손상 의심"
                continue
            os.replace(tmp, target)
            return {"ok": True,
                    "message": f"한국어 데이터 다운로드 완료 ({size/1024/1024:.1f}MB)",
                    "path": target, "size": size, "source": url}
        except Exception as e:
            last_err = str(e)
            continue
    return {"ok": False,
            "message": f"다운로드 실패: {last_err}\n수동 다운로드: "
                       f"https://github.com/tesseract-ocr/tessdata_best/raw/main/kor.traineddata\n"
                       f"파일을 다음 경로에 저장: {_APP_TESSDATA_DIR}\\kor.traineddata"}


def _tess_env() -> dict:
    """Tesseract 실행 시 환경변수 — 앱 tessdata 우선."""
    env = os.environ.copy()
    # 앱 내부 + 시스템 tessdata 둘 다 검색 가능하도록
    sys_tessdata = None
    tess = _setup_tesseract_path()
    if tess:
        sys_tessdata = os.path.join(os.path.dirname(tess), "tessdata")
    paths = [_APP_TESSDATA_DIR]
    if sys_tessdata and os.path.isdir(sys_tessdata):
        paths.append(sys_tessdata)
    env["TESSDATA_PREFIX"] = paths[0]  # primary
    return env


def _preprocess_image(img):
    """OCR 정확도 향상을 위한 이미지 전처리.
    - 그레이스케일 변환
    - 작으면 2x 업스케일 (한글 인식률 향상)
    - 자동 대비 (autocontrast)
    """
    try:
        from PIL import Image, ImageOps, ImageFilter
        # 그레이스케일
        if img.mode != "L":
            img = img.convert("L")
        # 너무 작으면 업스케일 (300dpi 기준 권장)
        w, h = img.size
        min_side = min(w, h)
        if min_side < 1000:
            scale = max(2.0, 1500 / min_side)
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        # 자동 대비
        img = ImageOps.autocontrast(img, cutoff=2)
        # 가벼운 샤프닝 (스캔본 외곽 선명화)
        img = img.filter(ImageFilter.SHARPEN)
        return img
    except Exception:
        return img


# =====================================================
# 텍스트 추출 — PDF / 이미지 자동 구분
# =====================================================
def extract_text(file_path: str, original_name: str = "") -> tuple[str, str]:
    """
    파일에서 텍스트 추출. 반환: (text, mode)
      mode: 'pdf-text' | 'pdf-ocr' | 'image-ocr' | 'error:<message>'
    """
    name = (original_name or file_path).lower()
    is_pdf = name.endswith(".pdf")
    is_image = name.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"))

    if is_pdf:
        # 1) 텍스트 PDF 시도 (정부24·홈택스 발급분)
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                pages_text = []
                for p in pdf.pages:
                    t = p.extract_text() or ""
                    pages_text.append(t)
                text = "\n".join(pages_text).strip()
            if text and len(text) > 30:
                return text, "pdf-text"
        except ImportError:
            return "", "error:pdfplumber 미설치 — pip install pdfplumber"
        except Exception as e:
            pass  # 텍스트 추출 실패 → OCR 폴백

        # 2) 스캔 PDF — Tesseract OCR 폴백 (pdf2image 로 페이지 → 이미지)
        if not has_tesseract():
            return "", "error:tesseract_not_found"
        if not has_korean():
            return "", "error:korean_lang_not_found"
        try:
            import pytesseract
            from pdf2image import convert_from_path
            try:
                images = convert_from_path(file_path, dpi=300)
            except Exception as e:
                # poppler 미설치 — Windows 안내
                return "", f"error:poppler_not_found ({str(e)[:80]})"
            env = _tess_env()
            for k, v in env.items():
                os.environ[k] = v
            text = "\n".join(
                pytesseract.image_to_string(_preprocess_image(img), lang="kor+eng")
                for img in images
            )
            return text.strip(), "pdf-ocr"
        except ImportError:
            return "", "error:pytesseract 또는 pdf2image 미설치"

    if is_image:
        if not has_tesseract():
            return "", "error:tesseract_not_found"
        if not has_korean():
            return "", "error:korean_lang_not_found"
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(file_path)
            img = _preprocess_image(img)
            env = _tess_env()
            for k, v in env.items():
                os.environ[k] = v
            text = pytesseract.image_to_string(img, lang="kor+eng")
            return text.strip(), "image-ocr"
        except ImportError:
            return "", "error:pytesseract 또는 PIL 미설치"
        except Exception as e:
            return "", f"error:OCR 실패 ({str(e)[:80]})"

    return "", "error:지원하지 않는 파일 형식 (PDF/JPG/PNG 만 가능)"


# =====================================================
# 사업자등록증 정규식 파서
# 표준 양식 (홈택스/세무서 발급) 기준 — 라벨 + 값 패턴
# =====================================================
_BIZ_PATTERNS = {
    "biz_no": [
        # "등록번호 : 123-45-67890" 또는 "사업자등록번호: ..." (공백/콜론 변형 허용)
        r"(?:사업자\s*등록\s*번호|등\s*록\s*번\s*호)\s*[:：]?\s*(\d{3}\s*-\s*\d{2}\s*-\s*\d{5})",
        # 아무데서나 사업자번호 패턴 — 폴백
        r"(\d{3}-\d{2}-\d{5})",
    ],
    "name": [
        r"(?:상\s*호|법\s*인\s*명|회\s*사\s*명)\s*[\(:（：]?[^\):\)）]*[\):\)）]?\s*[:：]?\s*([^\n\r]{2,40}?)(?:\s{2,}|\s*\(|\n)",
        r"상\s*호\s*[:：]\s*([^\n]{2,40})",
    ],
    "ceo_name": [
        # "대표자(성명) : 김정락" — 괄호·공백 변형 허용
        r"대\s*표\s*자\s*[\(（]?\s*성\s*명\s*[\)）]?\s*[:：]\s*([가-힣]{2,5})",
        # "대표자 : 김정락"
        r"대\s*표\s*자\s*[:：]\s*([가-힣]{2,5})",
        # "성    명 : 김정락" (단독)
        r"^\s*성\s+명\s*[:：]\s*([가-힣]{2,5})",
    ],
    "address": [
        r"(?:사업장\s*소재지|사업장\s*주소|소\s*재\s*지|주\s*소)\s*[:：]?\s*([^\n\r]{8,120})",
    ],
    "biz_kind": [
        # 업태/종목 — 참고용
        r"업\s*태\s*[:：]?\s*([^\n\r]{2,40})",
    ],
    "biz_item": [
        r"(?:종\s*목|종목명)\s*[:：]?\s*([^\n\r]{2,80})",
    ],
}


def parse_biz_doc(text: str) -> dict:
    """OCR/PDF 텍스트에서 사업자등록증 표준 필드 추출.
    반환: {biz_no, name, ceo_name, address, biz_kind, biz_item, raw_text(snippet)}
    """
    out = {
        "biz_no": "", "name": "", "ceo_name": "", "address": "",
        "biz_kind": "", "biz_item": "",
    }
    if not text:
        return out
    # 줄바꿈/공백 정리 — OCR에서 이상한 공백 끼는 경우 흡수
    norm = re.sub(r"[ \t]+", " ", text)
    norm = re.sub(r" ", " ", norm)  # non-breaking space
    for field, patterns in _BIZ_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, norm, re.MULTILINE)
            if m:
                val = m.group(1).strip()
                # 사업자번호: 공백 제거하여 표준 포맷으로
                if field == "biz_no":
                    digits = re.sub(r"\D", "", val)
                    if len(digits) == 10:
                        val = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
                # 상호: 후행 영문/괄호 정리
                if field == "name":
                    val = re.sub(r"\s{2,}.*$", "", val).strip()
                    val = re.sub(r"\s*\([^)]*\).*$", "", val).strip()
                out[field] = val
                break
    return out


def parse_file(file_path: str, original_name: str = "") -> dict:
    """파일 → 텍스트 추출 → 사업자등록증 필드 파싱 (one-shot).
    반환: {ok, mode, fields, message, raw_excerpt}
    """
    text, mode = extract_text(file_path, original_name)
    if mode.startswith("error:"):
        err = mode[6:]
        msg = _friendly_error(err)
        return {"ok": False, "mode": mode, "fields": {}, "message": msg,
                "raw_excerpt": ""}
    fields = parse_biz_doc(text)
    found_count = sum(1 for v in fields.values() if v)
    return {
        "ok": found_count > 0,
        "mode": mode,
        "fields": fields,
        "found_count": found_count,
        "message": (f"{found_count}개 필드 추출 성공" if found_count
                    else "텍스트는 추출되었지만 표준 항목을 찾지 못했습니다. 수동 입력해주세요."),
        "raw_excerpt": text[:300],
    }


def _friendly_error(err: str) -> str:
    """기술적 에러 메시지 → 사용자 친화 안내."""
    if err == "tesseract_not_found":
        return ("이미지/스캔 PDF 인식을 위해 Tesseract OCR 설치가 필요합니다.\n"
                "설치: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "(설치 시 Korean 언어팩 반드시 체크 — 한국어 인식)\n"
                "텍스트 PDF (홈택스 발급분)는 추가 설치 없이 즉시 작동합니다.")
    if err == "korean_lang_not_found":
        return "KOREAN_DATA_MISSING"  # UI 가 인식하여 자동 다운로드 버튼 표시
    if err.startswith("poppler_not_found"):
        return ("스캔 PDF 변환을 위해 Poppler 설치가 필요합니다.\n"
                "Windows: https://github.com/oschwartz10612/poppler-windows/releases\n"
                "→ bin 폴더를 PATH에 추가 또는 환경변수 POPPLER_PATH 설정\n"
                "또는 PDF 대신 JPG/PNG 이미지로 업로드하세요.")
    return err
