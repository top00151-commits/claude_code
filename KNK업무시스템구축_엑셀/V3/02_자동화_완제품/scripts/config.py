"""
╔══════════════════════════════════════════════════════════════╗
║  KNK PMS V4 — 02_자동화_완제품 config.py                      ║
║  수주→설계→제작→셋업→납품 (PMS + 부서진척)                    ║
║  완전 독립 모듈: 이 파일 변경이 다른 유형에 영향 없음          ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(SCRIPT_DIR)
BASE_DIR   = os.path.dirname(MODULE_DIR)
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
DIR_DATA       = MODULE_DIR
DIR_LOGS       = os.path.join(BASE_DIR, "80_logs")
DIR_SCRIPTS    = SCRIPT_DIR

BIZ_NAME  = "자동화"
BIZ_CODE  = "M"
TYPE_NAME = "자동화_완제품"
TYPE_CODE = "02"

def pms_path():
    return os.path.join(DIR_DATA, f"KNK_{TYPE_NAME}_PMS_{YEAR}.xlsx")

def dept_path(dept):
    return os.path.join(DIR_DATA, f"KNK_{TYPE_NAME}_{dept}_입력_{YEAR}.xlsx")

def log_dir():
    os.makedirs(DIR_LOGS, exist_ok=True)
    return DIR_LOGS

# ═══════════════════════════════════════════════════════════════
# B. PMS 컬럼 매핑 (29열 — v2026.04d 부서 컬럼 복원, 자동화 7부서)
# ═══════════════════════════════════════════════════════════════
# A.식별정보 (1~7) — 모델 C6, 품명 C7
C_NO=1; C_CODE=2; C_SJNUM=3; C_CUST=4; C_CUST_PIC=5; C_MODEL=6; C_PROD=7
# B.영업정보 (8~11)
C_POTYPE=8; C_STAGE=9; C_SALES=10; C_PM=11
# C.수주정보 (12~17)
C_QTY=12; C_CURRENCY=13; C_UPRICE=14; C_TOTAL=15; C_SJDATE=16; C_DUE=17
# D.현황 (18~21)
C_LOGISTICS=18; C_PROG=19; C_DDAY=20; C_STATUS=21
# E.비고 (22)
C_NOTE=22
# F.부서담당자 (23~28) — v3.0: 가공팀 폐기. 부서 7→6개
C_DEPT_START = 23
# G.매출·수금 (29~30) — v3.0: 가공팀 폐기로 -1
C_INVOICE_DATE = 29
C_PAYMENT_DATE = 30
MAX_COL = 30

PMS_HEADER_LABELS = [
    "NO", "관리코드", "수주번호", "고객사", "고객사\n담당자",
    "모델", "품명",                              # v2026.04b 순서 swap
    "PO유형", "영업단계", "담당영업", "PM",
    "수량", "통화", "단가", "금액", "수주일", "납기일",
    "출하경로", "전체\n진척률(%)", "D-day", "진행상태",
    "비고",
]

# ═══════════════════════════════════════════════════════════════
# C. 부서 구성 (자동화 7개 부서)
# ═══════════════════════════════════════════════════════════════
# v3.0: 가공팀 폐기 (의뢰 부서가 추적 — 신규=설계팀, 양산=구매팀)
DEPTS = ["설계팀","전장설계팀","소프트웨어팀","구매팀","제조기술2팀","베트남"]

DEPT_SUB_ITEMS = {
    "설계팀":      ["상세컨셉","3D/2D설계","BOM작성","가공품발주","메뉴얼"],
    "전장설계팀":  ["기구검토","IO맵/리스트","설계","BOM작성"],
    "소프트웨어팀":["검토","프로그램","DRYRUN","AUTORUN"],
    "구매팀":      ["BOM작성","구매검토","구매품발주","가공품발주","입고"],
    "제조기술2팀": ["조립","전장","TURN-ON","IO체크"],
    "베트남":      ["설계","SW","전장","가공","조립","DRYRUN","AUTORUN"],
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
EXCLUDE_OPT    = ["제외"]
STAGE_NO_CODE  = {"제안작성", "제안제출"}

DROPDOWN_MAP = {
    C_POTYPE:    (PO_TYPES,        True),
    C_STAGE:     (STAGES,          True),
    C_CURRENCY:  (CURRENCIES,      True),
    C_STATUS:    (STATUSES,        True),
    C_LOGISTICS: (LOGISTICS_TYPES, False),
}
# v3.0: 부서담당자 컬럼 — "제외" 드롭다운 + 이름 직접 입력 허용 (가공팀 폐기, 6부서)
for _i in range(len(DEPTS)):
    DROPDOWN_MAP[C_DEPT_START + _i] = (EXCLUDE_OPT, True)

# ═══════════════════════════════════════════════════════════════
# E. R3·R4 매핑 (자동화 — v2026.04b 22열, 부서담당자 제거)
# ═══════════════════════════════════════════════════════════════
R3_MAP_PROJ = {
    1:"auto", 2:"auto_input", 3:"auto",
    4:"input", 5:"input",                            # 고객사, 고객사담당자
    6:"input", 7:"input",                             # 모델, 품명
    8:"select", 9:"select", 10:"input", 11:"input",   # PO유형, 영업단계, 담당영업, PM
    12:"po_input", 13:"po_select",                    # 수량, 통화
    14:"po_input", 15:"auto_calc",                    # 단가, 금액
    16:"po_input", 17:"po_input",                     # 수주일, 납기일
    18:"po_select", 19:"auto", 20:"auto", 21:"auto",  # 출하경로, 진척률, D-day, 진행상태
    22:"memo",                                         # 비고
    # v3.0: 23~28 부서담당자 6개 (가공팀 폐기)
    23:"sel_input", 24:"sel_input", 25:"sel_input", 26:"sel_input",
    27:"sel_input", 28:"sel_input",
    # 29~30: 매출·수금
    29:"po_input",   # 계산서 발행일
    30:"po_input",   # 입금일
}
R4_MAP_PROJ = {
    1:"id", 2:"id", 3:"id",
    4:"sales", 5:"sales", 6:"sales", 7:"sales",
    8:"sales", 9:"sales", 10:"sales", 11:"sales",
    12:"po", 13:"po", 14:"po", 15:"po", 16:"po", 17:"po",
    18:"status", 19:"status", 20:"status", 21:"status",
    22:"manage",
    # v3.0: 23~28 부서 6개
    23:"dept", 24:"dept", 25:"dept", 26:"dept",
    27:"dept", 28:"dept",
    # 29~30: 매출·수금 (payment)
    29:"payment", 30:"payment",
}

R3_MAP_SHIP = {c: "auto" for c in range(1, 24)}
R4_MAP_SHIP = {
    1:"id", 2:"id", 3:"id", 4:"id", 5:"id", 6:"id", 7:"id",
    8:"status", 9:"status", 10:"status", 11:"status",
    12:"po", 13:"po", 14:"po", 15:"po", 16:"po", 17:"po",
    18:"ship", 19:"ship",
    20:"procure", 21:"procure", 22:"procure", 23:"procure",
}

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
FORMAT_EXTRA = {
    "default":              2000,
    "6_관리코드발행대장":    5000,
    "5_매핑조회(수주번호)":  1000,
}
