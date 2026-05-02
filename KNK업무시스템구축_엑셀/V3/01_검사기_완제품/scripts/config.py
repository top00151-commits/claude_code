"""
╔══════════════════════════════════════════════════════════════╗
║  KNK PMS V4 — 01_검사기_완제품 config.py                      ║
║  수주→설계→제작→셋업→납품 (PMS + 부서진척)                    ║
║  완전 독립 모듈: 이 파일 변경이 다른 유형에 영향 없음          ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, datetime

# shared 모듈 경로 추가
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(SCRIPT_DIR)                    # 01_검사기_완제품/
BASE_DIR   = os.path.dirname(MODULE_DIR)                    # 02_KNK_PMS_5구분/
sys.path.insert(0, BASE_DIR)

from shared.styles import (
    YEAR, YYMM, TODAY,
    FT_DATA, FT_BOLD, FT_HEAD, FT_R3, AL_C, AL_L, AL_R, THIN,
    FILL_WHITE, FILL_ALT, FILL_INPUT, FILL_KNK_RED, FILL_KNK_DARK, FILL_KNK_GRAY,
    FILL_PROGRESS, FILL_DONE, FILL_DELAY, FILL_WAIT,
    DEPT_HEADER_COLORS, TAB_INPUT, TAB_VIEW, TAB_VIEW2,
    ACCT, ACCT_USD, PCT, money_fmt,
    R3_GUIDE, R4_AREA, SHEET_PASSWORD,
    apply_r3_guide, apply_r4_header, apply_protection, make_comment,
    setup_r1, format_data_rows, auto_fit_columns, fmt_cell,
)

# ═══════════════════════════════════════════════════════════════
# A. 경로
# ═══════════════════════════════════════════════════════════════
DIR_DATA       = MODULE_DIR                                  # 01_검사기_완제품/
DIR_LOGS       = os.path.join(BASE_DIR, "80_logs")
DIR_SCRIPTS    = SCRIPT_DIR

BIZ_NAME  = "검사기"
BIZ_CODE  = "T"          # 관리코드 접두: T001YYMM
TYPE_NAME = "검사기_완제품"
TYPE_CODE = "01"

def pms_path():
    return os.path.join(DIR_DATA, f"KNK_{TYPE_NAME}_PMS_{YEAR}.xlsx")

def dept_path(dept):
    return os.path.join(DIR_DATA, f"KNK_{TYPE_NAME}_{dept}_입력_{YEAR}.xlsx")

def log_dir():
    os.makedirs(DIR_LOGS, exist_ok=True)
    return DIR_LOGS

# ═══════════════════════════════════════════════════════════════
# B. PMS 컬럼 매핑 (31열 — v2026.04d 부서 컬럼 복원, 제품구분 유지)
# ═══════════════════════════════════════════════════════════════
# A.식별정보 (1~8) — 제품구분 C6, 모델 C7, 품명 C8
C_NO=1; C_CODE=2; C_SJNUM=3; C_CUST=4; C_CUST_PIC=5
C_PRODTYPE=6; C_MODEL=7; C_PROD=8
# B.영업정보 (9~12)
C_POTYPE=9; C_STAGE=10; C_SALES=11; C_PM=12
# C.수주정보 (13~18)
C_QTY=13; C_CURRENCY=14; C_UPRICE=15; C_TOTAL=16; C_SJDATE=17; C_DUE=18
# D.현황 (19~22)
C_LOGISTICS=19; C_PROG=20; C_DDAY=21; C_STATUS=22
# E.비고 (23)
C_NOTE=23
# F.부서담당자 (24~30) — v3.0: 가공팀 폐기. 부서 8→7개
C_DEPT_START = 24
# G.매출·수금 (31~32) — v3.0: 가공팀 폐기로 -1
C_INVOICE_DATE = 31    # 세금계산서 발행일
C_PAYMENT_DATE = 32    # 입금일
MAX_COL = 32

PMS_HEADER_LABELS = [
    "NO", "관리코드", "수주번호", "고객사", "고객사\n담당자",
    "제품구분",                                   # v2026.04c 신규 (01 전용)
    "모델", "품명",
    "PO유형", "영업단계", "담당영업", "PM",
    "수량", "통화", "단가", "금액", "수주일", "납기일",
    "출하경로", "전체\n진척률(%)", "D-day", "진행상태",
    "비고",
    # F.부서담당자 8개 (C24~C31) — 빌드 시 동적 추가
    # G.매출·수금 2개 (C32~C33) — 빌드 시 추가
]


# ═══════════════════════════════════════════════════════════════
# C. 부서 구성
# ═══════════════════════════════════════════════════════════════
# v3.0: 가공팀 폐기 (의뢰 부서가 추적 — 신규=설계팀, 양산=구매팀)
DEPTS = ["설계팀","검사기팀","개발혁신팀","품질팀","제조기술1팀","구매팀","베트남"]

DEPT_SUB_ITEMS = {
    "설계팀":      ["설계검토","3D/2D설계","BOM작성","가공발주"],
    "검사기팀":    ["검토","PCB","H/W","F/W","동작검증"],
    "개발혁신팀":  ["검토","프로그램","동작검증"],
    "품질팀":      ["동작확인","반복성검증","성적서작성"],
    "제조기술1팀": ["조립","TURN-ON"],
    "구매팀":      ["BOM작성","구매검토","발주","입고"],
    "베트남":      ["설계","가공","조립","동작검증","출하검증"],
}

# ═══════════════════════════════════════════════════════════════
# D. 드롭다운 옵션
# ═══════════════════════════════════════════════════════════════
PO_TYPES       = ["신규", "추가", "수정", "개조", "기타"]   # v2026.04c 확장
STAGES         = ["제안작성","제안제출","수주확정","납품","개조","A/S"]
STATUSES       = ["수주예정","진행중","납품완료","취소","보류"]
TRANSPORTS     = ["국내","항공","해상"]
SETUP_STATUSES = ["예정","진행","완료"]
LOGISTICS_TYPES = ["K→고객사","K→V→K→고객사","K→V→고객사"]
CURRENCIES     = ["KRW","USD"]
PRODUCT_TYPES  = ["PBA", "TSP", "SENSOR", "기타"]   # v2026.04c 제품구분 (01 전용)
EXCLUDE_OPT    = ["제외"]   # 호환용 — 신규 입력은 부서담당자(input)로

STAGE_NO_CODE = {"제안작성", "제안제출"}

DROPDOWN_MAP = {
    C_POTYPE:       (PO_TYPES,        True),
    C_STAGE:        (STAGES,          True),
    C_PRODTYPE:     (PRODUCT_TYPES,   True),         # v2026.04c 제품구분
    C_CURRENCY:     (CURRENCIES,      True),
    C_STATUS:       (STATUSES,        True),
    C_LOGISTICS:    (LOGISTICS_TYPES, False),
}
# v3.0: 부서담당자 컬럼 — "제외" 드롭다운 + 이름 직접 입력 허용 (가공팀 폐기, 7개)
for _i in range(len(DEPTS)):
    DROPDOWN_MAP[C_DEPT_START + _i] = (EXCLUDE_OPT, True)

# ═══════════════════════════════════════════════════════════════
# E. R3·R4 매핑 (v2026.04c — 23열, 제품구분 C6 추가)
# ═══════════════════════════════════════════════════════════════
# 1_프로젝트등록 23열:
#   NO, 관리코드, 수주번호, 고객사, 고객사담당자, 제품구분,
#   모델, 품명,
#   PO유형, 영업단계, 담당영업, PM,
#   수량, 통화, 단가, 금액, 수주일, 납기일,
#   출하경로, 진척률, D-day, 진행상태, 비고
R3_MAP_PROJ = {
    1:"auto", 2:"auto_input", 3:"auto",
    4:"input", 5:"input",                              # 고객사, 고객사담당자
    6:"select",                                         # 제품구분 — 드롭다운
    7:"input", 8:"input",                               # 모델, 품명
    9:"select", 10:"select", 11:"input", 12:"input",    # PO유형, 영업단계, 담당영업, PM
    13:"po_input", 14:"po_select",                      # 수량, 통화
    15:"po_input", 16:"auto_calc",                      # 단가, 금액
    17:"po_input", 18:"po_input",                       # 수주일, 납기일
    19:"po_select", 20:"auto", 21:"auto", 22:"auto",    # 출하경로, 진척률, D-day, 진행상태
    23:"memo",                                           # 비고
    # v3.0: 24~30 부서담당자 7개 — 가공팀 폐기
    24:"sel_input", 25:"sel_input", 26:"sel_input", 27:"sel_input",
    28:"sel_input", 29:"sel_input", 30:"sel_input",
    # 31~32: 매출·수금
    31:"po_input",   # 계산서 발행일
    32:"po_input",   # 입금일
}
R4_MAP_PROJ = {
    1:"id", 2:"id", 3:"id",
    4:"sales", 5:"sales", 6:"sales", 7:"sales", 8:"sales",   # 고객사~품명
    9:"sales", 10:"sales", 11:"sales", 12:"sales",
    13:"po", 14:"po", 15:"po", 16:"po", 17:"po", 18:"po",
    19:"status", 20:"status", 21:"status", 22:"status",
    23:"manage",
    # v3.0: 24~30 부서 7개 (보라)
    24:"dept", 25:"dept", 26:"dept", 27:"dept",
    28:"dept", 29:"dept", 30:"dept",
    # 31~32: 매출·수금 (payment)
    31:"payment", 32:"payment",
}

# 출하현황 R3 (전체 auto)
R3_MAP_SHIP = {c: "auto" for c in range(1, 24)}
R4_MAP_SHIP = {
    1:"id", 2:"id", 3:"id", 4:"id", 5:"id", 6:"id", 7:"id",
    8:"status", 9:"status", 10:"status", 11:"status",
    12:"po", 13:"po", 14:"po", 15:"po", 16:"po", 17:"po",
    18:"ship", 19:"ship",
    20:"procure", 21:"procure", 22:"procure", 23:"procure",
}

# 출하현황 시트 컬럼 (23열)
SHIP_SUMMARY_MAX_COL = 23
SHIP_SUMMARY_LABELS = [
    "NO", "출하구분", "INV번호\n(출하코드)", "관리코드", "수주번호",
    "고객사", "품명", "차수/경로",
    "거래유형", "통관분류", "출하일",
    "통화", "환율", "수량", "BOX수", "금액", "인보이스(USD)",
    "통관상태", "VN입고일",

    "전체\n부품수", "입고\n완료", "출하\n완료", "조달\n진행률",
]

# ═══════════════════════════════════════════════════════════════
# F. 서식 범위

# ═══════════════════════════════════════════════════════════════
# F. 서식 범위
# ═══════════════════════════════════════════════════════════════
FORMAT_EXTRA = {
    "default":              2000,
    "6_관리코드발행대장":    5000,
    "5_매핑조회(수주번호)":  1000,
}
