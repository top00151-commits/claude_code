# -*- coding: utf-8 -*-
"""
v5H226z103 (2026-05-16) — 자재 테스트 데이터 일괄 생성 스크립트
========================================================

대상: parts 테이블의 모든 활성 자재
생성: 용도(purpose) + 사진 + 도면 + 데이터시트 PDF
방식: 100% 로컬 생성 (인터넷·외부 자산 사용 안 함 — 상표권·라이선스 정책 준수)
모든 생성물에 "TEST DATA"/"가상 데이터" 명시 — 실제 도면·사진과 오인 방지

실행:
    python scripts/gen_test_attachments.py
"""
from __future__ import annotations
import os, sys, sqlite3, random, hashlib
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================
# 경로 설정
# ============================================================
ROOT     = Path(__file__).resolve().parent.parent   # 01_HAIST_WORKS
DB_PATH  = ROOT / "data" / "knk.db"
# main.py 의 _PARTS_UPLOAD_ROOT 와 일치: 01_HAIST_WORKS/uploads/parts/
UPLOAD_ROOT = ROOT / "uploads" / "parts"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# 한글 폰트
FONT_KR = "C:/Windows/Fonts/malgun.ttf"
FONT_KR_BD = "C:/Windows/Fonts/malgunbd.ttf"

# ============================================================
# 용도 생성 — 카테고리/자재명 키워드 룰 기반
# ============================================================
# 카테고리별 기본 용도 문구
CAT_TEMPLATES = {
    "전장 부품":      ["장비 제어반 내 전기 신호 처리용", "전원 분배·차단·보호용", "장비 제어반 내 회로 구성용"],
    "AIR SYSTEM":   ["공압 라인 구성 부품", "에어 실린더 구동 회로용", "공기 압력 제어·분배용"],
    "SENSOR & TRAY PP": ["트레이 감지·정렬 센싱용", "위치 감지 및 피드백 신호 생성용", "트레이 픽업 위치 검출용"],
    "ATTACH PP":     ["부품 부착·고정 메커니즘 구성", "어태치 유닛 가공·이송용", "부착 공정 보조 메커니즘"],
    "TRAY LIFT UNIT": ["트레이 승강 메커니즘 구성", "Z축 리프트 구동·가이드 부품", "트레이 적재·인출 구동부"],
    "TOP FRAME":      ["상부 프레임 구조 보강용", "상부 커버·도어 결합용", "장비 외관 상단 마감재"],
    "BOTTOM FRAME":   ["베이스 프레임 구조용", "장비 하단부 강성 보강", "장착 베이스 플레이트"],
    "ALIGN SHUTTLE":  ["정렬 셔틀 메커니즘 구성", "X/Y 축 정렬 가이드 부품", "셔틀 이송 메커니즘 보조"],
    "CV#1 & CV#2":    ["컨베이어 라인 구성 부품", "벨트 컨베이어 구동·가이드", "이송 라인 메커니즘"],
    "PEELING UNIT":   ["박리 유닛 메커니즘 구성", "필 공정 가이드·구동부", "박리 작업 보조 부품"],
}
# 자재명 키워드 매칭 (우선순위 ↑)
NAME_KEYWORDS = {
    "모터":    ["축 회전 구동용 모터. 정밀 위치 제어 가능 (PWM/엔코더 피드백 지원)", "장비 메커니즘 구동용 서보·스테핑 모터"],
    "MOTOR":   ["Drive shaft motor for axis rotation", "축 회전 구동용 모터 — 위치 제어 및 토크 출력"],
    "센서":    ["근접·위치·압력 감지용 센서. 디지털/아날로그 출력 지원", "물체 감지·계측·피드백용 센서"],
    "SENSOR":  ["감지·계측·피드백용 센서. 디지털/아날로그 출력 지원", "근접·위치·압력 감지용 센서"],
    "볼트":    ["부품 체결용 볼트. 토크 규정값 준수 필요", "체결·고정용 표준 볼트 (KS B 1002)"],
    "BOLT":    ["부품 체결용 볼트. 토크 규정값 준수", "체결·고정용 표준 볼트"],
    "너트":    ["볼트 체결용 너트. 풀림 방지 조치 필요한 경우 록타이트 적용", "체결 마감용 너트"],
    "NUT":     ["볼트 체결용 너트. 풀림 방지 조치 필요", "체결 마감용 너트"],
    "베어링":   ["축 회전 지지용 베어링. 정기 그리스 주입 권장", "회전축 지지·마찰 저감용 베어링"],
    "BEARING": ["축 회전 지지용 베어링. 정기 그리스 주입 권장", "회전축 지지·마찰 저감용 베어링"],
    "케이블":   ["전원·신호 전송용 케이블. 굴곡 반복부는 가요 케이블 사용 권장", "장비 내부 배선용 케이블"],
    "CABLE":   ["전원·신호 전송용 케이블", "장비 내부 배선용 케이블"],
    "팬":      ["장비 내부 발열 부품 냉각용. 정기 먼지 청소 권장", "냉각용 축류팬. 풍량/소음 등급 확인 필요"],
    "FAN":     ["장비 내부 발열 부품 냉각용. 정기 먼지 청소 권장", "냉각용 축류팬"],
    "냉각":    ["장비 내부 발열 부품 냉각용", "열 발생부 냉각용 메커니즘 부품"],
    "커넥터":   ["배선 접속·분리용 커넥터. 핀 손상 주의", "신호·전원 배선 결합 부품"],
    "CONNECTOR": ["배선 접속·분리용 커넥터", "신호·전원 배선 결합 부품"],
    "HOOD":    ["커넥터 외피·보호용 후드. 차폐·결선 마감 역할", "D-SUB 등 커넥터 보호 외피"],
    "D-SUB":   ["D-SUB 커넥터 — 시리얼·병렬 신호 전송용. 핀 수에 따라 신호 채널 차이", "산업용 표준 D-SUB 커넥터"],
    "실린더":   ["공압 실린더 — 직선 왕복 운동 구동용. 압력·스트로크 사양 확인 필수", "공압식 액추에이터"],
    "CYLINDER": ["공압 실린더 — 직선 왕복 운동 구동용", "공압식 액추에이터"],
    "밸브":    ["유체·공기 흐름 제어용 밸브", "공압/유압 회로 제어 부품"],
    "VALVE":   ["유체·공기 흐름 제어용 밸브", "공압/유압 회로 제어 부품"],
    "스위치":   ["수동/자동 신호 차단·연결용 스위치", "조작·감지용 스위치 (리밋·근접 등)"],
    "SWITCH":  ["수동/자동 신호 차단·연결용 스위치", "조작·감지용 스위치"],
    "프레임":   ["구조 보강·장착용 프레임 부재", "장비 골격 구성 부품"],
    "FRAME":   ["구조 보강·장착용 프레임 부재", "장비 골격 구성 부품"],
    "PLATE":   ["베이스·마운트용 플레이트", "부품 장착 기준 플레이트"],
    "플레이트":  ["베이스·마운트용 플레이트", "부품 장착 기준 플레이트"],
    "BRACKET": ["부품 장착·지지용 브라켓", "센서·모듈 마운트 브라켓"],
    "브라켓":   ["부품 장착·지지용 브라켓", "센서·모듈 마운트 브라켓"],
    "GUIDE":   ["직선 운동 가이드. LM 가이드/리니어 부시 등", "정밀 직선 운동 안내부"],
    "가이드":   ["직선 운동 가이드. LM 가이드/리니어 부시 등", "정밀 직선 운동 안내부"],
    "BELT":    ["동력 전달·이송용 벨트", "타이밍·V-벨트 — 정기 장력 점검 필요"],
    "벨트":     ["동력 전달·이송용 벨트", "타이밍·V-벨트 — 정기 장력 점검 필요"],
    "PULLEY":  ["벨트 구동용 풀리", "동력 전달 풀리 (타이밍/V형)"],
    "풀리":     ["벨트 구동용 풀리", "동력 전달 풀리"],
    "커버":     ["부품 보호·차폐용 커버", "장비 외관·내부 마감 커버"],
    "COVER":   ["부품 보호·차폐용 커버", "장비 외관·내부 마감 커버"],
    "스틸망":   ["통풍·이물질 차단용 메탈 메시", "팬 그릴·통풍구 보호망"],
    "MESH":    ["통풍·이물질 차단용 메탈 메시", "팬 그릴·통풍구 보호망"],
}
# 두 번째 문장 (운영/관리 안내) — 시드별 선택
SECOND_LINES = [
    "정기 점검 시 마모/오염 여부 확인 권장.",
    "단종 시 동일 사양 대체 자재로 교체.",
    "장착 위치는 도면 기준. 토크값 준수.",
    "재고 부족 시 사전 발주 (LT 2~4주).",
    "장비 가동 중 점검 시 안전 차단 필수.",
    "교체 주기: 사용 빈도에 따라 6개월~2년.",
    "예비 자재 1~2개 상비 권장.",
    "취급 시 정전기 주의 (필요 시 ESD 매트 사용).",
    "보관 시 직사광선·습기 회피.",
    "장기 미사용 시 방청 처리.",
]
# 세 번째 문장 (사용처/라인) — 시드별 선택
THIRD_LINES = [
    "검사기·자동화 라인 공용 부품.",
    "주요 사용 라인: M사업부 자동화 라인 #1~#3.",
    "주요 사용 라인: T사업부 검사기 모델 K-시리즈.",
    "전 사업부 공통 표준 부품.",
    "MAINT-RUN 사이클 부품군 — 마모성 소모재.",
    "신규 라인 셋업 시 우선 검토 부품.",
    "기존 라인 호환 — 동일 part_no 유지 권장.",
    "프로젝트별 사용량은 BOM 참조.",
]

def make_purpose(part: dict) -> str:
    """자재 메타로 자연스러운 용도 문장 생성."""
    seed = part["id"] or 0
    rnd = random.Random(seed * 7919 + 13)

    name_u = (part.get("part_name") or "") + " " + (part.get("part_no") or "")
    name_u = name_u.upper()
    cat    = (part.get("category") or "").strip()

    # 1차: 자재명 키워드 매칭
    primary = None
    for kw, candidates in NAME_KEYWORDS.items():
        if kw in name_u or kw in (part.get("part_name") or ""):
            primary = rnd.choice(candidates)
            break
    # 2차: 카테고리 템플릿
    if not primary:
        tmpls = CAT_TEMPLATES.get(cat)
        if tmpls:
            primary = rnd.choice(tmpls)
    # 3차: 기본
    if not primary:
        primary = "장비 메커니즘 구성 부품. 사양·치수는 도면 기준."

    second = rnd.choice(SECOND_LINES)
    third  = rnd.choice(THIRD_LINES)
    return f"{primary}. {second} {third}"


# ============================================================
# 사진 — PIL 800×600 카테고리 컬러 + 자재정보 + TEST DATA
# ============================================================
CAT_COLORS = {
    "전장 부품":         (45, 95, 165),
    "AIR SYSTEM":      (32, 130, 145),
    "SENSOR & TRAY PP":(160, 80, 120),
    "ATTACH PP":        (100, 90, 155),
    "TRAY LIFT UNIT":  (75, 130, 95),
    "TOP FRAME":         (145, 110, 60),
    "BOTTOM FRAME":      (105, 90, 75),
    "ALIGN SHUTTLE":     (80, 105, 145),
    "CV#1 & CV#2":      (165, 100, 50),
    "PEELING UNIT":     (130, 75, 110),
}
def _color_for(cat: str) -> tuple:
    if cat in CAT_COLORS:
        return CAT_COLORS[cat]
    # 카테고리 해시로 안정적 색상
    h = int(hashlib.md5((cat or "").encode("utf-8")).hexdigest()[:6], 16)
    r = 60 + (h & 0xFF) % 120
    g = 60 + ((h >> 8) & 0xFF) % 120
    b = 60 + ((h >> 16) & 0xFF) % 120
    return (r, g, b)

def gen_photo(part: dict, out_path: Path) -> int:
    """800×600 가상 사진. 카테고리 컬러 그라데이션 + 자재 정보."""
    W, H = 800, 600
    bg = _color_for(part.get("category") or "")
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    # 그라데이션 (위는 밝게)
    for y in range(H):
        ratio = y / H
        color = tuple(int(c * (1.0 + 0.3 * (1 - ratio))) for c in bg)
        color = tuple(min(255, c) for c in color)
        draw.line([(0, y), (W, y)], fill=color)
    # 중앙 박스 (자재 실물 느낌)
    bw, bh = 480, 320
    bx, by = (W - bw) // 2, (H - bh) // 2 - 20
    draw.rounded_rectangle((bx, by, bx+bw, by+bh), radius=20,
                           fill=(40, 40, 40), outline=(200, 200, 200), width=3)
    # 박스 내부 디테일 (LED 3개)
    for i, dx in enumerate([100, 240, 380]):
        draw.ellipse((bx+dx, by+40, bx+dx+22, by+62),
                     fill=(255, 200, 80) if i == 1 else (80, 220, 120))
    # 라벨 영역
    draw.rectangle((bx+40, by+100, bx+bw-40, by+200), fill=(255, 255, 255))
    # 텍스트
    f_big   = ImageFont.truetype(FONT_KR_BD, 28)
    f_med   = ImageFont.truetype(FONT_KR, 18)
    f_small = ImageFont.truetype(FONT_KR, 14)
    f_water = ImageFont.truetype(FONT_KR_BD, 20)

    pname = (part.get("part_name") or "")[:24]
    pno   = (part.get("part_no")   or "")[:30]
    maker = (part.get("maker")     or "")[:20]
    draw.text((bx+60, by+115), pno,   fill=(20, 20, 20),  font=f_big)
    draw.text((bx+60, by+155), pname, fill=(60, 60, 60),  font=f_med)
    if maker:
        draw.text((bx+60, by+220), f"제조사: {maker}", fill=(220, 220, 220), font=f_small)
    cat = (part.get("category") or "")
    draw.text((bx+60, by+250), f"분류: {cat}", fill=(220, 220, 220), font=f_small)

    # 워터마크 — 가상 데이터 명시
    wm_text = "⚠ TEST DATA · 가상 이미지 · 실제 자재 사진 아님"
    tw = draw.textlength(wm_text, font=f_water)
    draw.rectangle((0, H-44, W, H), fill=(0, 0, 0))
    draw.text(((W-tw)//2, H-36), wm_text, fill=(255, 200, 50), font=f_water)
    # 상단 라벨
    draw.text((20, 14), "KNK HAIST WORKS · 자재 사진 (TEST)", fill=(255, 255, 255), font=f_small)

    img.save(out_path, "JPEG", quality=82)
    return out_path.stat().st_size


# ============================================================
# 도면 — PIL 1000×700 도면 풍 박스 + 치수
# ============================================================
def gen_drawing(part: dict, out_path: Path) -> int:
    W, H = 1000, 700
    img = Image.new("RGB", (W, H), (252, 252, 248))
    draw = ImageDraw.Draw(img)
    # 외곽 테두리 (도면 프레임)
    draw.rectangle((20, 20, W-20, H-20), outline=(40, 40, 40), width=2)
    draw.rectangle((30, 30, W-30, H-30), outline=(40, 40, 40), width=1)

    f_title = ImageFont.truetype(FONT_KR_BD, 22)
    f_body  = ImageFont.truetype(FONT_KR, 14)
    f_small = ImageFont.truetype(FONT_KR, 12)
    f_water = ImageFont.truetype(FONT_KR_BD, 18)

    # 헤더
    draw.text((50, 45), "MECHANICAL DRAWING · 기계 도면", fill=(20, 20, 20), font=f_title)
    draw.line([(50, 80), (W-50, 80)], fill=(40, 40, 40), width=1)

    # 좌측 도면 박스 (단순 사각형 부품)
    bx, by, bw, bh = 120, 130, 480, 380
    draw.rectangle((bx, by, bx+bw, by+bh), outline=(20, 20, 20), width=2, fill=(245, 245, 240))
    # 내부 보조선
    draw.line([(bx+80, by), (bx+80, by+bh)], fill=(150, 150, 150), width=1)
    draw.line([(bx, by+80), (bx+bw, by+80)], fill=(150, 150, 150), width=1)
    draw.line([(bx+bw-80, by), (bx+bw-80, by+bh)], fill=(150, 150, 150), width=1)
    draw.line([(bx, by+bh-80), (bx+bw, by+bh-80)], fill=(150, 150, 150), width=1)
    # 4개 마운팅 홀
    for px, py in [(bx+40, by+40), (bx+bw-40, by+40), (bx+40, by+bh-40), (bx+bw-40, by+bh-40)]:
        draw.ellipse((px-8, py-8, px+8, py+8), outline=(20, 20, 20), width=1)
        draw.line([(px-12, py), (px+12, py)], fill=(20, 20, 20), width=1)
        draw.line([(px, py-12), (px, py+12)], fill=(20, 20, 20), width=1)

    # 치수선 (가로)
    dy = by + bh + 30
    draw.line([(bx, dy), (bx+bw, dy)], fill=(180, 60, 60), width=1)
    draw.line([(bx, dy-6), (bx, dy+6)], fill=(180, 60, 60), width=1)
    draw.line([(bx+bw, dy-6), (bx+bw, dy+6)], fill=(180, 60, 60), width=1)
    # 시드 치수 — part_id 기반 가상 수치
    rnd = random.Random((part["id"] or 0) * 31 + 7)
    dim_w = rnd.choice([80, 100, 120, 150, 180, 200])
    dim_h = rnd.choice([60, 80, 100, 120, 150])
    draw.text((bx+bw//2-20, dy+4), f"{dim_w} mm", fill=(180, 60, 60), font=f_body)
    # 치수선 (세로)
    dx2 = bx + bw + 30
    draw.line([(dx2, by), (dx2, by+bh)], fill=(180, 60, 60), width=1)
    draw.line([(dx2-6, by), (dx2+6, by)], fill=(180, 60, 60), width=1)
    draw.line([(dx2-6, by+bh), (dx2+6, by+bh)], fill=(180, 60, 60), width=1)
    draw.text((dx2+8, by+bh//2-8), f"{dim_h} mm", fill=(180, 60, 60), font=f_body)

    # 우측 타이틀 블록
    tb_x, tb_y, tb_w, tb_h = 650, 130, 320, 380
    draw.rectangle((tb_x, tb_y, tb_x+tb_w, tb_y+tb_h), outline=(20, 20, 20), width=2)
    rows = [
        ("PART NO",  (part.get("part_no") or "—")[:24]),
        ("NAME",     (part.get("part_name") or "—")[:24]),
        ("MAKER",    (part.get("maker") or "—")[:24]),
        ("SPEC",     (part.get("spec") or "—")[:24]),
        ("CATEGORY", (part.get("category") or "—")[:24]),
        ("MATERIAL", rnd.choice(["SUS304","AL6061","SS400","ABS","POM"])),
        ("FINISH",   rnd.choice(["흑색 아노다이징","무도장","크롬 도금","파우더 코팅"])),
        ("TOL",      rnd.choice(["±0.1","±0.05","±0.2"]) + " mm"),
        ("DATE",     datetime.now().strftime("%Y-%m-%d")),
        ("REV",      "A"),
    ]
    rh = tb_h // len(rows)
    for i, (k, v) in enumerate(rows):
        ry = tb_y + i * rh
        if i > 0:
            draw.line([(tb_x, ry), (tb_x+tb_w, ry)], fill=(20, 20, 20), width=1)
        draw.line([(tb_x+95, ry), (tb_x+95, ry+rh)], fill=(20, 20, 20), width=1)
        draw.text((tb_x+8, ry+rh//2-8), k, fill=(80, 80, 80), font=f_small)
        draw.text((tb_x+102, ry+rh//2-8), v, fill=(20, 20, 20), font=f_body)

    # 워터마크
    wm = "⚠ DRAWING · TEST DATA · 시스템 테스트용 가상 도면"
    tw = draw.textlength(wm, font=f_water)
    draw.rectangle((0, H-44, W, H-20), fill=(180, 30, 30))
    draw.text(((W-tw)//2, H-38), wm, fill=(255, 255, 255), font=f_water)

    img.save(out_path, "PNG", optimize=True)
    return out_path.stat().st_size


# ============================================================
# 데이터시트 — reportlab 1page PDF
# ============================================================
# 한글 폰트 등록 (전역 1회)
_PDF_FONT_REGISTERED = False
def _ensure_pdf_font():
    global _PDF_FONT_REGISTERED
    if not _PDF_FONT_REGISTERED:
        pdfmetrics.registerFont(TTFont("Malgun",   FONT_KR))
        pdfmetrics.registerFont(TTFont("MalgunBD", FONT_KR_BD))
        _PDF_FONT_REGISTERED = True

def gen_datasheet_pdf(part: dict, out_path: Path) -> int:
    _ensure_pdf_font()
    c = rl_canvas.Canvas(str(out_path), pagesize=A4)
    W, H = A4
    rnd = random.Random((part["id"] or 0) * 17 + 3)

    # 헤더
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.rect(0, H-35*mm, W, 35*mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("MalgunBD", 22)
    c.drawString(20*mm, H-20*mm, "DATA SHEET · 자재 사양서")
    c.setFont("Malgun", 11)
    c.drawString(20*mm, H-28*mm, "KNK HAIST WORKS · Test Data")

    # 핵심 정보 박스
    y = H - 50*mm
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("MalgunBD", 14)
    c.drawString(20*mm, y, part.get("part_no") or "-")
    c.setFont("Malgun", 12)
    c.drawString(20*mm, y-6*mm, part.get("part_name") or "-")
    if part.get("maker"):
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.setFont("Malgun", 10)
        c.drawString(20*mm, y-12*mm, f"제조사: {part['maker']}")

    # 사양 표
    table_y = y - 25*mm
    rows = [
        ("분류 (Category)",    part.get("category") or "-"),
        ("규격 (Spec)",        part.get("spec") or "-"),
        ("단위 (Unit)",        part.get("unit") or "EA"),
        ("재질 (Material)",    rnd.choice(["SUS304", "Aluminum 6061-T6", "SS400", "ABS", "POM (Delrin)", "PC"])),
        ("표면 처리 (Finish)",  rnd.choice(["흑색 아노다이징", "무도장", "크롬 도금", "파우더 코팅"])),
        ("동작 온도 (Op.Temp)", f"-{rnd.randint(10,30)}°C ~ +{rnd.randint(50,85)}°C"),
        ("정격 전압 (Voltage)", rnd.choice(["DC 5V", "DC 12V", "DC 24V", "AC 220V", "N/A"])),
        ("질량 (Weight)",      f"{rnd.uniform(0.05, 2.5):.2f} kg"),
        ("리드타임 (LT)",       f"{rnd.choice([2,3,4,6,8])} weeks"),
        ("원산지 (Origin)",     part.get("origin") or rnd.choice(["대한민국","일본","독일","중국"])),
    ]
    rh = 8*mm
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    for i, (k, v) in enumerate(rows):
        ry = table_y - i*rh
        c.setFillColorRGB(0.96, 0.96, 0.93) if i % 2 == 0 else c.setFillColorRGB(1, 1, 1)
        c.rect(20*mm, ry-rh, 170*mm, rh, fill=1, stroke=0)
        c.setFillColorRGB(0.3, 0.3, 0.3); c.setFont("Malgun", 10)
        c.drawString(22*mm, ry-rh+2.5*mm, k)
        c.setFillColorRGB(0.1, 0.1, 0.1); c.setFont("MalgunBD", 10)
        c.drawString(85*mm, ry-rh+2.5*mm, str(v))
    c.setStrokeColorRGB(0.7, 0.7, 0.7); c.setLineWidth(0.5)
    c.rect(20*mm, table_y - len(rows)*rh, 170*mm, len(rows)*rh, fill=0, stroke=1)

    # 용도 설명
    note_y = table_y - len(rows)*rh - 15*mm
    c.setFillColorRGB(0.1, 0.1, 0.1); c.setFont("MalgunBD", 12)
    c.drawString(20*mm, note_y, "용도 · Application")
    c.setFillColorRGB(0.2, 0.2, 0.2); c.setFont("Malgun", 10)
    purp = part.get("purpose") or "장비 메커니즘 구성 부품."
    # 줄바꿈 (50자 단위)
    words = purp.split(". ")
    cy = note_y - 6*mm
    for w in words:
        if not w.strip(): continue
        line = w.strip() + ("." if not w.endswith(".") else "")
        c.drawString(22*mm, cy, line[:90])
        cy -= 5*mm

    # 워터마크 푸터
    c.setFillColorRGB(0.7, 0.2, 0.2); c.setFont("MalgunBD", 11)
    c.drawCentredString(W/2, 15*mm, "⚠ TEST DATA · 본 문서는 시스템 테스트용 가상 데이터입니다 ⚠")
    c.setFillColorRGB(0.5, 0.5, 0.5); c.setFont("Malgun", 8)
    c.drawCentredString(W/2, 10*mm, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} · KNK HAIST WORKS")

    c.showPage()
    c.save()
    return out_path.stat().st_size


# ============================================================
# 메인
# ============================================================
def main():
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}"); sys.exit(1)

    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    rows = cur.execute(
        "SELECT id, part_no, part_name, spec, maker, origin, unit, category "
        "FROM parts WHERE is_active=1 ORDER BY id"
    ).fetchall()
    total = len(rows)
    print(f"대상 자재: {total}건")
    print(f"업로드 루트: {UPLOAD_ROOT}")

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    sz_photo = sz_drawing = sz_pdf = 0
    upd_purpose = ins_attach = 0

    for i, r in enumerate(rows, 1):
        part = dict(r)
        pid = part["id"]
        part_dir = UPLOAD_ROOT / str(pid)
        part_dir.mkdir(parents=True, exist_ok=True)

        # 1. 용도
        purp = make_purpose(part)
        cur.execute("UPDATE parts SET purpose=?, updated_at=? WHERE id=?",
                    (purp, now_iso, pid))
        upd_purpose += 1
        part["purpose"] = purp

        # 2. 사진
        photo_name = f"{ts}_test_photo_{pid}.jpg"
        photo_path = part_dir / photo_name
        sz = gen_photo(part, photo_path)
        sz_photo += sz
        cur.execute(
            "INSERT INTO part_attachments (part_id, file_path, file_name, file_size, mime_type, kind, uploaded_by, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, str(photo_path.resolve()), photo_name, sz, "image/jpeg", "photo", None, now_iso)
        )
        ins_attach += 1

        # 3. 도면
        draw_name = f"{ts}_test_drawing_{pid}.png"
        draw_path = part_dir / draw_name
        sz = gen_drawing(part, draw_path)
        sz_drawing += sz
        cur.execute(
            "INSERT INTO part_attachments (part_id, file_path, file_name, file_size, mime_type, kind, uploaded_by, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, str(draw_path.resolve()), draw_name, sz, "image/png", "drawing", None, now_iso)
        )
        ins_attach += 1

        # 4. 데이터시트 PDF
        pdf_name = f"{ts}_test_datasheet_{pid}.pdf"
        pdf_path = part_dir / pdf_name
        sz = gen_datasheet_pdf(part, pdf_path)
        sz_pdf += sz
        cur.execute(
            "INSERT INTO part_attachments (part_id, file_path, file_name, file_size, mime_type, kind, uploaded_by, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, str(pdf_path.resolve()), pdf_name, sz, "application/pdf", "datasheet", None, now_iso)
        )
        ins_attach += 1

        if i % 20 == 0 or i == total:
            con.commit()
            print(f"  진행: {i}/{total} ({i*100//total}%) · [{pid}] {part.get('part_name','')[:25]}")

    con.commit()
    con.close()

    print()
    print("=" * 60)
    print(f"완료. 자재 {total}건 처리")
    print(f"  · 용도 UPDATE: {upd_purpose}건")
    print(f"  · 첨부 INSERT: {ins_attach}건 (사진+도면+PDF)")
    print(f"  · 디스크 사용:")
    print(f"      사진 JPG  : {sz_photo/1024/1024:.1f} MB")
    print(f"      도면 PNG  : {sz_drawing/1024/1024:.1f} MB")
    print(f"      PDF       : {sz_pdf/1024/1024:.1f} MB")
    print(f"      합계      : {(sz_photo+sz_drawing+sz_pdf)/1024/1024:.1f} MB")

if __name__ == "__main__":
    main()
