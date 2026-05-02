"""
╔══════════════════════════════════════════════════════════════╗
║  KNK PMS V4 — 05_소모품 config.py                             ║
║  품목관리 + 출하관리 (가장 단순한 구조)                        ║
║  완전 독립 모듈                                                ║
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
    TAB_INPUT, TAB_VIEW, TAB_VIEW2,
    ACCT, ACCT_USD, PCT, money_fmt,
    R3_GUIDE, R4_AREA, SHEET_PASSWORD,
    apply_r3_guide, apply_r4_header, apply_protection, make_comment,
    setup_r1, format_data_rows, auto_fit_columns, fmt_cell,
)

# ═══════════════════════════════════════════════════════════════
# A. 경로
# ═══════════════════════════════════════════════════════════════
DIR_DATA  = MODULE_DIR
DIR_LOGS  = os.path.join(BASE_DIR, "80_logs")

TYPE_NAME = "소모품"
TYPE_CODE = "05"

def consumables_path():
    return os.path.join(DIR_DATA, f"KNK_{TYPE_NAME}_출하대장_{YEAR}.xlsx")

def log_dir():
    os.makedirs(DIR_LOGS, exist_ok=True)
    return DIR_LOGS


# ═══════════════════════════════════════════════════════════════
# B. 소모품목록 시트 (10열)
# ═══════════════════════════════════════════════════════════════
CONS_LIST_MAX_COL = 10
CONS_LIST_LABELS = [
    "NO", "품목코드", "품명", "규격", "단위", "메이커",
    "기본단가\n(KRW)", "카테고리", "비고", "등록일",
]

R3_MAP_CONS_LIST = {c: "input" for c in range(1, 11)}
R3_MAP_CONS_LIST[1] = "auto"   # NO
R3_MAP_CONS_LIST[10] = "auto"  # 등록일

R4_MAP_CONS_LIST = {c: "id" for c in range(1, 11)}

CONS_CATEGORIES = ["지그부품","검사핀","커넥터","케이블","기타"]

# ═══════════════════════════════════════════════════════════════
# C. 출하관리 시트 (LI 40열 기반 — 소모품 특화)
# ═══════════════════════════════════════════════════════════════
LI_MAX_COL = 40
LI = {}
LI["관리코드"]=1; LI["수주번호"]=2; LI["품명"]=3; LI["규격"]=4; LI["메이커"]=5
LI["업체명"]=6; LI["단위"]=7; LI["원산지"]=8; LI["수량"]=9; LI["통화"]=10
LI["단가"]=11; LI["금액"]=12; LI["HS_CODE"]=13
LI["발주일"]=14; LI["입고상태"]=15; LI["입고일"]=16
LI["출하코드"]=17; LI["출하차수"]=18; LI["거래유형"]=19; LI["통관구분"]=20; LI["통관분류"]=21
LI["환율"]=22; LI["상승률"]=23; LI["출하일"]=24; LI["출하상태"]=25
LI["DUTY"]=26; LI["VAT"]=27; LI["INV단가"]=28; LI["INV금액"]=29
LI["INV단가USD"]=30; LI["INV금액USD"]=31; LI["관세KRW"]=32; LI["관세USD"]=33
LI["BOX번호"]=34; LI["BOX수량"]=35; LI["무게_KG"]=36; LI["PALLET_SIZE"]=37
LI["통관상태"]=38; LI["VN입고일"]=39; LI["비고"]=40

LI_HEADER_LABELS = [
    "관리코드", "수주번호", "품명", "규격", "메이커", "업체명",
    "단위", "원산지", "수량", "통화", "단가", "금액", "HS CODE",
    "발주일", "입고상태", "입고일",
    "INV번호\n(출하코드)", "출하차수", "거래유형", "통관구분", "통관분류",
    "환율", "상승률(%)", "출하일", "출하상태",
    "DUTY(%)", "VAT(%)",
    "인보이스단가\n(KRW)", "인보이스금액\n(KRW)",
    "인보이스단가\n(USD)", "인보이스금액\n(USD)",
    "관세(KRW)", "관세(USD)",
    "BOX번호", "BOX수량", "무게(Kg)", "PALLET SIZE",
    "통관상태", "VN입고일", "비고",
]

# 소모품 출하관리 R3 (관리코드·수주번호도 입력)
R3_MAP_CONSUMABLES = {
    1:"input", 2:"input", 3:"input", 4:"input", 5:"input",
    6:"input", 7:"select", 8:"select",
    9:"input", 10:"select", 11:"input", 12:"auto_calc", 13:"input",
    14:"input", 15:"select", 16:"input",
    17:"input", 18:"input", 19:"select", 20:"select", 21:"select",
    22:"input", 23:"input", 24:"input", 25:"select",
    26:"input", 27:"input",
    28:"auto_calc", 29:"auto_calc", 30:"auto_calc", 31:"auto_calc",
    32:"auto_calc", 33:"auto_calc",
    34:"input", 35:"input", 36:"input", 37:"input",
    38:"select", 39:"input", 40:"memo",
}

LI_AREA_COLORS = {
    "A_품목": "2E5090", "B_발주": "00695C", "C_출하": "6A1B9A",
    "C2_인보": "BF360C", "D_포장": "37474F", "E_통관": "1B5E20",
}
LI_COL_AREA = {}
for c in range(1, 14):  LI_COL_AREA[c] = "A_품목"
for c in range(14, 17): LI_COL_AREA[c] = "B_발주"
for c in range(17, 26): LI_COL_AREA[c] = "C_출하"
for c in range(26, 34): LI_COL_AREA[c] = "C2_인보"
for c in range(34, 38): LI_COL_AREA[c] = "D_포장"
for c in range(38, 41): LI_COL_AREA[c] = "E_통관"

# 드롭다운
RECEIPT_STATUSES   = ["미입고", "입고완료"]
SHIP_ITEM_STATUSES = ["미출하", "출하완료"]
CUSTOMS_TYPES      = ["국내", "수책통관", "정식통관"]
TRADE_TYPES        = ["부품판매", "위탁가공"]
SHIP_TYPES         = ["해상", "항공", "특송", "핸드캐리", "기타"]
SHIP_STATUSES      = ["준비중","입고대기","포장완료","선적완료","통관중","통관완료","VN입고완료"]
ORIGINS            = ["KOREA","JAPAN","CHINA","TAIWAN","USA","GERMANY","FRANCE","기타"]
UNITS              = ["EA","SET","M","KG","BOX","ROLL","PAIR","기타"]
CURRENCIES         = ["KRW","USD"]
