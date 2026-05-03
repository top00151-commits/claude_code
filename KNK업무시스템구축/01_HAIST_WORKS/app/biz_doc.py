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

# v5H63: tessdata 는 반드시 ASCII 경로에 두어야 함
# (앱 경로에 한글이 있으면 Tesseract subprocess 인코딩 깨짐 → cp949 디코드 에러)
# 우선순위: LOCALAPPDATA (Windows 표준) → 앱 내부 → TEMP
def _pick_ascii_tessdata_dir() -> str:
    candidates = []
    la = os.environ.get("LOCALAPPDATA")
    if la and la.isascii():
        candidates.append(os.path.join(la, "KNK_HAIST_WORKS", "tessdata"))
    # 앱 내부 (경로가 ASCII 인 경우만)
    app_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tessdata")
    if app_dir.isascii():
        candidates.append(app_dir)
    # TEMP 폴백
    import tempfile
    candidates.append(os.path.join(tempfile.gettempdir(), "knk_tessdata"))
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            continue
    return candidates[-1]

_APP_TESSDATA_DIR = _pick_ascii_tessdata_dir()

# 기존 앱 경로에 kor.traineddata 가 있으면 ASCII 경로로 자동 이동 (1회)
def _migrate_legacy_tessdata():
    legacy = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tessdata")
    if legacy == _APP_TESSDATA_DIR:
        return
    if not os.path.isdir(legacy):
        return
    for fn in os.listdir(legacy):
        if not fn.endswith(".traineddata"):
            continue
        src = os.path.join(legacy, fn)
        dst = os.path.join(_APP_TESSDATA_DIR, fn)
        if os.path.isfile(dst):
            continue
        try:
            import shutil
            shutil.copy2(src, dst)
        except Exception:
            pass

_migrate_legacy_tessdata()


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


def _copy_kor_to_system(app_kor_path: str) -> tuple[bool, str]:
    """앱 디렉터리의 kor.traineddata 를 Tesseract 시스템 디렉터리로 복사.
    관리자 권한 없으면 실패 — 그래도 OK (fallback 동작).
    반환: (성공여부, 메시지)"""
    sys_dir = _system_tessdata_dir()
    if not sys_dir:
        return False, "시스템 tessdata 디렉터리를 찾을 수 없음"
    sys_kor = os.path.join(sys_dir, "kor.traineddata")
    if os.path.isfile(sys_kor) and os.path.getsize(sys_kor) > 1_000_000:
        return True, "이미 시스템 디렉터리에 존재"
    try:
        import shutil
        shutil.copy2(app_kor_path, sys_kor)
        return True, f"시스템 디렉터리로 복사 완료: {sys_kor}"
    except PermissionError:
        return False, ("관리자 권한 필요 — 시스템 디렉터리 쓰기 거부됨. "
                       "앱 내부 디렉터리 사용 (--tessdata-dir 폴백).")
    except Exception as e:
        return False, f"복사 실패: {e}"


def download_korean_traineddata() -> dict:
    """한국어 traineddata 자동 다운로드 (사용자 명시적 트리거).
    GitHub tessdata_best 에서 ~28MB. 앱 내부 tessdata 폴더에 저장.
    이미 있으면 skip. 반환: {ok, message, path, size}"""
    target = os.path.join(_APP_TESSDATA_DIR, "kor.traineddata")
    if os.path.isfile(target) and os.path.getsize(target) > 1_000_000:
        # 이미 다운로드됨 → 시스템 디렉터리에도 복사 시도 (관리자 권한 있으면)
        ok, msg = _copy_kor_to_system(target)
        return {"ok": True,
                "message": f"이미 설치되어 있습니다. ({msg})",
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
            # 다운로드 성공 → 시스템 디렉터리에도 복사 시도 (인코딩 문제 회피)
            ok, sys_msg = _copy_kor_to_system(target)
            extra = f" + {sys_msg}" if ok else ""
            return {"ok": True,
                    "message": f"한국어 데이터 다운로드 완료 ({size/1024/1024:.1f}MB){extra}",
                    "path": target, "size": size, "source": url,
                    "system_copy": ok}
        except Exception as e:
            last_err = str(e)
            continue
    return {"ok": False,
            "message": f"다운로드 실패: {last_err}\n수동 다운로드: "
                       f"https://github.com/tesseract-ocr/tessdata_best/raw/main/kor.traineddata\n"
                       f"파일을 다음 경로에 저장: {_APP_TESSDATA_DIR}\\kor.traineddata"}


def _system_tessdata_dir() -> str | None:
    """Tesseract 설치된 표준 tessdata 디렉터리 반환."""
    tess = _setup_tesseract_path()
    if not tess:
        return None
    d = os.path.join(os.path.dirname(tess), "tessdata")
    return d if os.path.isdir(d) else None


def _ensure_unified_tessdata_dir() -> str:
    """kor + eng + osd 모두 들어 있는 통합 tessdata 디렉터리 보장 후 경로 반환.
    - 앱 디렉터리(data/tessdata/)에 kor 있으면 → 시스템 eng/osd 를 hardlink/copy
    - 없으면 시스템 디렉터리 그대로 사용
    이 디렉터리를 --tessdata-dir 로 Tesseract 에 명시 전달."""
    sys_dir = _system_tessdata_dir()
    app_kor = os.path.join(_APP_TESSDATA_DIR, "kor.traineddata")

    # kor 가 앱 디렉터리에 있으면 → 통합 디렉터리는 앱 디렉터리
    if os.path.isfile(app_kor) and sys_dir:
        # 앱 디렉터리에 eng/osd 가 없으면 시스템에서 복사
        for lang in ("eng", "osd"):
            src = os.path.join(sys_dir, f"{lang}.traineddata")
            dst = os.path.join(_APP_TESSDATA_DIR, f"{lang}.traineddata")
            if os.path.isfile(src) and not os.path.isfile(dst):
                try:
                    # hardlink 시도 (디스크 절약), 실패 시 복사
                    try:
                        os.link(src, dst)
                    except (OSError, AttributeError):
                        import shutil
                        shutil.copy2(src, dst)
                except Exception:
                    pass
        return _APP_TESSDATA_DIR

    # kor 없으면 시스템 디렉터리 (eng/osd 만 있음 — kor 인식 불가)
    return sys_dir or _APP_TESSDATA_DIR


def _tess_config(psm: int = 6) -> str:
    """pytesseract config — Tesseract 정확도 최적화 옵션.
    - PSM 6 (단일 균일 텍스트 블록) — 사업자등록증/표준 양식 최적
    - OEM 1 (LSTM only) — 가장 정확한 신경망 엔진
    - DPI 300 명시 — 한글 인식률 ↑
    - --tessdata-dir 명시 — 한국어 데이터 위치 (ASCII 경로)"""
    d = _ensure_unified_tessdata_dir().replace(chr(92), "/")
    return f"--tessdata-dir {d} --oem 1 --psm {psm} -c user_defined_dpi=300"


def _tess_env() -> dict:
    """레거시 호환 — 이제 _tess_config() 사용 권장."""
    env = os.environ.copy()
    env["TESSDATA_PREFIX"] = _ensure_unified_tessdata_dir()
    return env


def _preprocess_image(img):
    """v5H65: OCR 정확도 향상을 위한 이미지 전처리 — 근본 원인 해결.
    파이프라인 (OpenCV 우선, 없으면 PIL fallback):
      1. 그레이스케일
      2. 업스케일 (300+ DPI 기준 충분히 크게 — 4x 또는 min 2400px)
      3. denoise (bilateral filter — 글자 보존하며 노이즈 제거)
      4. deskew (기울기 자동 보정 — 비뚤게 찍은 사진)
      5. binarization (Otsu adaptive — 그림자/조명 보정)
    이게 OCR 자체 정확도를 90%+ 끌어올리는 핵심.
    """
    # OpenCV 우선 (deskew + Otsu 가능)
    try:
        import cv2
        import numpy as np
        from PIL import Image
        # PIL → OpenCV (BGR ndarray)
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # 1. 업스케일 (목표: 짧은변 2400+px, 한글 인식 최적)
        h, w = gray.shape
        min_side = min(h, w)
        if min_side < 2400:
            scale = max(2.0, 2400 / min_side)
            new_w = int(w * scale)
            new_h = int(h * scale)
            gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        # 2. denoise (글자 보존, 노이즈/그림자 제거)
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7,
                                          searchWindowSize=21)

        # 3. deskew (기울기 보정) — 글자 영역 기반 회전각 추정
        try:
            coords = np.column_stack(np.where(gray < 200))  # 어두운 픽셀(글자)
            if len(coords) > 100:
                rect = cv2.minAreaRect(coords)
                angle = rect[-1]
                # OpenCV minAreaRect 각도 정규화
                if angle < -45:
                    angle = 90 + angle
                # 너무 큰 회전(>10도)은 의심 — skip
                if abs(angle) < 10 and abs(angle) > 0.3:
                    (cy, cx) = (gray.shape[0] // 2, gray.shape[1] // 2)
                    M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
                    gray = cv2.warpAffine(gray, M, (gray.shape[1], gray.shape[0]),
                                           flags=cv2.INTER_CUBIC,
                                           borderMode=cv2.BORDER_REPLICATE)
        except Exception:
            pass

        # 4. 가벼운 contrast 향상 (CLAHE — Adaptive Histogram)
        # Adaptive threshold 는 한국어 글자를 일부 깎아내는 부작용 있어 미사용.
        # 대신 CLAHE 로 부드럽게 대비 ↑ (글자 보존).
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        except Exception:
            pass

        # OpenCV ndarray → PIL Image
        return Image.fromarray(gray)
    except ImportError:
        pass

    # OpenCV 없을 때 PIL fallback (효과 제한적)
    try:
        from PIL import Image, ImageOps, ImageFilter
        if img.mode != "L":
            img = img.convert("L")
        w, h = img.size
        min_side = min(w, h)
        if min_side < 2400:
            scale = max(2.0, 2400 / min_side)
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        img = ImageOps.autocontrast(img, cutoff=2)
        img = img.filter(ImageFilter.SHARPEN)
        return img
    except Exception:
        return img


def _validate_biz_no(biz_no: str) -> bool:
    """한국 사업자번호 체크섬 검증 (국세청 알고리즘).
    예: 498-62-00471 → 유효, 498-62-00411 → 무효"""
    digits = re.sub(r"\D", "", biz_no or "")
    if len(digits) != 10:
        return False
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    s = sum(int(digits[i]) * weights[i] for i in range(9))
    s += (int(digits[8]) * 5) // 10
    check = (10 - s % 10) % 10
    return check == int(digits[9])


def _try_correct_biz_no(biz_no: str) -> str:
    """사업자번호 OCR 오인식 자동 교정 — 체크섬 통과하는 단 1개 후보만 채택.
    여러 후보가 있으면 부정확 위험 → 원본 유지 + 무효 표시.
    매우 보수적인 confusable 매핑 (모양 거의 동일한 것만)."""
    digits = re.sub(r"\D", "", biz_no or "")
    if len(digits) != 10:
        return biz_no
    if _validate_biz_no(digits):
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    # 모양 매우 비슷한 것만 (보수적). 0/9, 4/1, 5/6 같이 모양 다른 건 제외
    confusables = {
        "1": ["7"],   # 1과 7 모양 비슷 (OCR 잦은 오인식)
        "7": ["1"],
        "0": ["8"],   # 둥근 형태 비슷
        "8": ["0", "3"],
        "3": ["8"],
    }
    # 1자리 변형 — 유효 후보 모두 수집
    cands = set()
    for i, d in enumerate(digits):
        for alt in confusables.get(d, []):
            c = digits[:i] + alt + digits[i+1:]
            if _validate_biz_no(c):
                cands.add(c)
    if len(cands) == 1:
        c = cands.pop()
        return f"{c[:3]}-{c[3:5]}-{c[5:]}"
    # 후보 없거나 여러 개면 → 원본 유지 (사용자 검수)
    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


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
            cfg = _tess_config()
            text = "\n".join(
                pytesseract.image_to_string(_preprocess_image(img),
                                             lang="kor+eng", config=cfg)
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
            cfg = _tess_config()
            text = pytesseract.image_to_string(img, lang="kor+eng", config=cfg)
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
# v5H61 (2026-05-03): 케이앤테크 PDF 등 실제 양식 분석 후 정규식 전면 보강.
# 핵심: "성 명 : 김정락 생 년 월 일 : 1981 ..." / "사업의 종류 : 업태 ... 종목 ..."
# 같이 한 줄에 여러 필드가 들어가는 케이스를 정확히 분리.
# 줄 단위 매칭(MULTILINE) + 한국어 이름 정확 캡처(2~4자) + 종목/업태 한 줄 분해.
# v5H64: OCR 노이즈 흡수 강화. 실제 케이스에서 발견된 오인식:
#  - "498-62-00471" → "498-62-004/1" (1을 /로)
#  - "성 명" → "Al 명" (성을 Al로)
#  - "사업장 소재지" → "사업장 소 THA" (재지를 THA로)
#  - "업태|부동산업" (라벨 사이 | 끼임)
# 정규식을 더 느슨하게 + 후처리 정상화 단계 추가.
_BIZ_PATTERNS = {
    "biz_no": [
        # 표준 + OCR 노이즈 흡수 (1 ↔ /, 0 ↔ O/o)
        r"(?:사업자\s*등록\s*번호|등\s*록\s*번\s*호)\s*[:：]\s*([\d/lOo\-―\s]{12,20})",
        # 폴백: 표준 패턴
        r"(\d{3}\s*[-―]\s*\d{2}\s*[-―]\s*\d{5})",
    ],
    "name": [
        # 1순위: 정확한 "상호 :" 라벨
        r"(?:^|\n)\s*상\s*호\s*[:：]\s*([^\n\r:：]{2,40}?)\s*(?:\n|$)",
        # 2순위: "법인명/회사명/단체명 :"
        r"(?:^|\n)\s*(?:법\s*인\s*명|회\s*사\s*명|단\s*체\s*명)\s*[\(（]?[^:：\)）\n]*[\)）]?\s*[:：]\s*([^\n\r:：]{2,40}?)\s*(?:\n|$)",
        r"법\s*인\s*명\s*\([^\)]*\)\s*[:：]\s*([^\n\r:：]{2,40}?)\s*(?:\n|$)",
        # 3순위 OCR 폴백: "X 호 :" — 상이 한 글자(영문/한글)로 깨진 경우
        # (등록번호 줄과 구분 위해 "호" 라벨 + 한글 값 강제)
        r"(?:^|\n)\s*[A-Za-z가-힣]{1,3}\s+호\s*[:：]\s*([가-힣][^\n\r:：]{1,40}?)\s*(?:\n|$)",
    ],
    "ceo_name": [
        r"성\s*명\s*[:：]\s*([가-힣]{2,5})(?=\s|$)",
        # OCR 폴백: '성' 자가 깨져 'Al'/'A'/'일'로 인식된 경우 — 라벨 자릿수만 보고 매칭
        r"(?:^|\n)\s*[A-Za-z가-힣]{1,3}\s*명\s*[:：]\s*([가-힣]{2,5})(?=\s|$)",
        r"대\s*표\s*자\s*[\(（]?\s*성\s*명\s*[\)）]?\s*[:：]\s*([가-힣]{2,5})",
        r"대\s*표\s*자\s*[:：]\s*([가-힣]{2,5})",
    ],
    "address": [
        # 표준 라벨
        r"(?:사업장\s*소재지|사업장\s*주소|본점\s*소재지|소\s*재\s*지)\s*[:：]\s*([^\n\r]{8,120})",
        # OCR 폴백: '소재지' 가 'THA'/'재 지'/'소 THA' 등으로 깨진 경우
        # — "사업장" 뒤에 임의 한글/영문/공백 조합 (1~12자) + ":" 만 있으면 주소
        r"(?:^|\n)\s*사\s*업\s*장\s+[가-힣A-Za-z\s]{1,12}?\s*[:：]\s*([^\n\r]{8,120})",
        r"(?:^|\n)\s*주\s*소\s*[:：]\s*([^\n\r]{8,120})",
    ],
    "biz_kind": [
        # 1순위: 명시 라벨 "업태"
        r"사\s*업\s*의?\s*종\s*류\s*[:：][\s|｜:：\[\]]*업\s*태[\s|｜:：\[\]]*([^\n\r|｜\[\]]+?)[\s|｜\[\]]+(?:종\s*목)",
        r"(?:^|\n)\s*[\[\|｜]?\s*업\s*태\s*[\]\|｜:：]+\s*([^\n\r|｜\[\]]+?)(?:\s*[\[\|｜]\s*종\s*목|\s*$|\n)",
    ],
    "biz_item": [
        r"사\s*업\s*의?\s*종\s*류\s*[:：][^\n]*?종\s*목[\s|｜\]\[]+([^\n\r]+?)\s*(?:\n|$)",
        r"(?:^|\n)\s*[\[\|｜]?\s*(?:종\s*목|종목명)\s*[\]\|｜:：]+\s*([^\n\r]{2,80})",
    ],
    # 라벨 없이 한 줄 전체 — 후처리에서 업태/종목 분리
    "_biz_kind_item_combined": [
        r"사\s*업\s*의?\s*종\s*류\s*[:：]\s*([^\n\r]+)",
    ],
    "open_date": [
        r"개\s*업\s*연\s*월\s*일\s*[:：]\s*(\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일)",
    ],
}


def _normalize_biz_no(raw: str) -> str:
    """사업자번호 OCR 노이즈 정상화 + 체크섬 자동 교정.
    '498-62-004/1' → '498-62-00471' (1을 /로, 1을 7로 잘못)"""
    if not raw:
        return ""
    # 1차: 글자→숫자 매핑
    s = raw.translate(str.maketrans({"O": "0", "o": "0", "l": "1", "/": "1",
                                       "I": "1", "B": "8", "S": "5", "Z": "2"}))
    digits = re.sub(r"\D", "", s)
    if len(digits) != 10:
        return raw.strip()
    # 2차: 체크섬 검증 + 자동 교정
    return _try_correct_biz_no(digits)


def parse_biz_doc(text: str) -> dict:
    """OCR/PDF 텍스트에서 사업자등록증 표준 필드 추출.
    반환: {biz_no, name, ceo_name, address, biz_kind, biz_item, raw_text(snippet)}
    """
    out = {
        "biz_no": "", "name": "", "ceo_name": "", "address": "",
        "biz_kind": "", "biz_item": "", "open_date": "",
        "biz_no_valid": False,  # 체크섬 통과 여부 (UI 표시용)
    }
    if not text:
        return out
    # 줄바꿈/공백 정리 — OCR에서 이상한 공백 끼는 경우 흡수
    norm = re.sub(r"[ \t]+", " ", text)
    norm = re.sub(r" ", " ", norm)  # non-breaking space
    for field, patterns in _BIZ_PATTERNS.items():
        if field.startswith("_"):
            continue  # 후처리 전용 (combined 등)
        for pat in patterns:
            m = re.search(pat, norm, re.MULTILINE)
            if m:
                val = m.group(1).strip()
                # 사업자번호: OCR 노이즈 정상화 (O→0, /→1 등) + 체크섬 검증
                if field == "biz_no":
                    val = _normalize_biz_no(val)
                    if not re.match(r"^\d{3}-\d{2}-\d{5}$", val):
                        continue
                    out["biz_no_valid"] = _validate_biz_no(val)
                # 상호: 콜론 뒤 잔여 / 후행 정리 + "성 년 월 일" 같은 다른 라벨 잘라냄
                if field == "name":
                    # "김정락 생 년 월 일 : ..." 같이 잘못 잡힌 경우 차단
                    if re.search(r"생\s*년\s*월\s*일|성\s*명\s*[:：]", val):
                        continue
                    val = re.sub(r"\s{2,}.*$", "", val).strip()
                    val = re.sub(r"\s*\([^)]*\)\s*$", "", val).strip()
                # 다른 필드도 후행 다른 라벨 잘라냄 (한국어 라벨 패턴)
                if field in ("biz_kind", "biz_item", "address"):
                    val = re.sub(r"\s+(?:업\s*태|종\s*목|발\s*급|공\s*동|성\s*명|개\s*업).*$", "", val).strip()
                    # 라벨 잔존 |, [, ] 제거
                    val = re.sub(r"^[\[\|｜\s]+", "", val)
                    val = re.sub(r"[\[\]\|｜\s]+$", "", val).strip()
                out[field] = val
                break

    # v5H65 후처리: 라벨 없이 한 줄에 업태+종목이 섞여 있는 케이스
    # 예: "사업의 종류 : 부동산업 비주거용 건물 임대업(점포, AI)"
    if not out["biz_kind"] or not out["biz_item"]:
        for pat in _BIZ_PATTERNS["_biz_kind_item_combined"]:
            m = re.search(pat, norm, re.MULTILINE)
            if not m:
                continue
            line = m.group(1).strip()
            line = re.sub(r"\s+(?:발\s*급|공\s*동|성\s*명|개\s*업).*$", "", line)
            # "업태:" / "종목:" 라벨 명시 시 분리, 아니면 첫 단어 = 업태(2~6자)
            mk = re.search(r"업\s*태[\s|｜:：\[\]]+([^\n\r|｜\[\]]+?)(?:\s+종\s*목|$)", line)
            mi = re.search(r"종\s*목[\s|｜:：\[\]]+([^\n\r|｜\[\]]+)", line)
            if mk and not out["biz_kind"]:
                out["biz_kind"] = mk.group(1).strip()
            if mi and not out["biz_item"]:
                out["biz_item"] = mi.group(1).strip()
            if not (mk or mi):
                # 라벨 없음 — 한국 업종명 형태로 업태/종목 분리
                # 업태 형태:
                #   - "○○업" (제조업, 부동산업)
                #   - "○○ 및 ○○업" (도매 및 소매업)
                #   - "○○산업" (정보통신산업)
                #   - "○○서비스" / "○○서비스업"
                #   - 끝에 "업" 으로 종결되는 경우가 99%
                wm = re.match(
                    r"^((?:[가-힣]{1,5}\s*(?:및|또는)\s*)?[가-힣\s]{1,12}?(?:업|산업|서비스))"
                    r"(?:[\s,]+(.+))?$",
                    line
                )
                if wm:
                    kind = re.sub(r"\s+", " ", wm.group(1)).strip()
                    if not out["biz_kind"]:
                        out["biz_kind"] = kind
                    if not out["biz_item"] and wm.group(2):
                        item = re.sub(r"\s+", " ", wm.group(2)).strip()
                        out["biz_item"] = item
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
    # found_count 는 텍스트 필드만 (boolean valid 플래그 제외)
    found_count = sum(1 for k, v in fields.items()
                       if v and isinstance(v, str))
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
