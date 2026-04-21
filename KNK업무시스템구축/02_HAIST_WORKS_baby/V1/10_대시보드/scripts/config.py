"""
╔══════════════════════════════════════════════════════════════╗
║  KNK PMS V4 — 10_대시보드 config.py                           ║
║  5개 소스 통합 집계·검색 (조회 전용)                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(SCRIPT_DIR)
BASE_DIR   = os.path.dirname(MODULE_DIR)
sys.path.insert(0, BASE_DIR)

from shared.styles import (
    YEAR, YYMM, TODAY,
    FT_DATA, FT_BOLD, FT_HEAD, AL_C, AL_R, THIN,
    FILL_WHITE, FILL_ALT, FILL_KNK_RED, FILL_KNK_DARK, FILL_KNK_GRAY,
    ACCT, ACCT_USD, PCT,
    TAB_VIEW, TAB_VIEW2, SHEET_PASSWORD,
    setup_r1, apply_r3_guide, apply_r4_header, apply_protection,
    format_data_rows, auto_fit_columns,
)

# ═══════════════════════════════════════════════════════════════
# A. 경로 (5개 소스 참조)
# ═══════════════════════════════════════════════════════════════
DIR_DASHBOARD = MODULE_DIR
DIR_LOGS = os.path.join(BASE_DIR, "80_logs")

# 소스 경로
# 2026-04-15: 03/04 부품출하 보류 — 자재 ERP 설계 확정 후 재개 예정
SOURCES = {
    "01_검사기_완제품": os.path.join(BASE_DIR, "01_검사기_완제품"),
    "02_자동화_완제품": os.path.join(BASE_DIR, "02_자동화_완제품"),
    "05_소모품": os.path.join(BASE_DIR, "05_소모품"),
}

def dashboard_path():
    return os.path.join(DIR_DASHBOARD, f"KNK_경영현황_{YEAR}.xlsx")

def log_dir():
    os.makedirs(DIR_LOGS, exist_ok=True)
    return DIR_LOGS

# ═══════════════════════════════════════════════════════════════
# B. 대시보드 시트 구조
# ═══════════════════════════════════════════════════════════════

# 시트1: 매출총괄 (유형별 집계)
SUMMARY_MAX_COL = 10
SUMMARY_LABELS = [
    "매출유형", "진행중\n건수", "완료\n건수", "총건수",
    "수주금액\n(KRW)", "수주금액\n(USD)", "INV금액\n(USD)",
    "평균\n진척률", "지연\n건수", "비고",
]

# 시트2: 전체 프로젝트 목록 (검색용)
PROJECT_MAX_COL = 12
PROJECT_LABELS = [
    "NO", "매출유형", "관리코드", "수주번호", "고객사", "품명",
    "금액", "진행상태", "진척률", "납기일", "D-day", "최종업데이트",
]

# 시트3: 출하현황 통합
SHIP_MAX_COL = 12
SHIP_LABELS = [
    "NO", "매출유형", "출하구분", "관리코드", "고객사", "품명",
    "출하일", "금액(KRW)", "INV(USD)", "통관상태", "VN입고일", "비고",
]
