"""
╔══════════════════════════════════════════════════════════════╗
║  01_검사기_완제품 apply_standard.py                            ║
║  스펙 §19 원칙 1 — 빌드·동기화 직후 이 스크립트 1회 실행       ║
║  스펙 §20 체크리스트 20항 일괄 보장                            ║
║  실행: python scripts/apply_standard.py                       ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    MODULE_DIR, TYPE_NAME, YEAR, DEPTS, DEPT_SUB_ITEMS, DEPT_MILESTONES,
    PMS_HEADER_LABELS, MAX_COL, R3_MAP_PROJ, R4_MAP_PROJ,
    SHIP_SUMMARY_MAX_COL, SHIP_SUMMARY_LABELS, R3_MAP_SHIP, R4_MAP_SHIP,
    C_QTY, C_CURRENCY, C_UPRICE, C_TOTAL, C_DDAY, C_STATUS,
    DROPDOWN_MAP,
    pms_path, dept_path,
)
from shared.knk_standard import normalize_file


def _log(msg):
    print(msg)


# ═══════════════════════════════════════════════════════════════
# PMS 통합 파일 (7시트) specs
# ═══════════════════════════════════════════════════════════════
def _pms_specs():
    # v2026.04e: 1_프로젝트등록 = 33열 (부서 8 + 매출·수금 2)
    mc = MAX_COL  # 33
    labels = list(PMS_HEADER_LABELS) + list(DEPTS) + ["계산서\n발행일", "입금일"]
    r3 = dict(R3_MAP_PROJ)
    r4 = dict(R4_MAP_PROJ)

    proj_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 프로젝트 등록 │ {YEAR}",
        "purpose": "검사기 PMS 전용",
        # v2026.04c: 1_프로젝트등록 전용 안내문구 — 빈 공간 제거 대신 신규 수주 입력 방법 안내
        "slogan":  "㈜케이엔케이 검사기 PMS   │   💡 신규 수주 입력:  Ctrl+End (입력된 데이터 마지막 행 이동) → 다음 행에 입력 → 실행_PMS(영업·PM).bat 실행",
        "max_col": mc,
        "labels":  labels,
        "r3_map":  r3,
        "r4_map":  r4,
        "freeze":  "auto",   # 품명(C8)까지 고정 — A~H열 + R1~R4
        "qty_cols":       [C_QTY],
        "money_cols":     [C_UPRICE, C_TOTAL],
        "currency_col":   C_CURRENCY,
        "dday_col":       C_DDAY,
        "status_col":     C_STATUS,
        "dropdown_map":   dict(DROPDOWN_MAP),
    }

    # 2_진행현황 (v3.1 — 부서당 1컬럼 = 완료일/입고일)
    prog_labels = ["NO","관리코드","수주번호","고객사","모델","품명","진행상태","전체\n진척률(%)"]
    for dept in DEPTS:
        prog_labels.append(f"{dept}\n완료일")
    prog_mc = len(prog_labels)
    prog_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 진행현황 │ {YEAR}",
        "purpose": "검사기 진행현황 (v3.1 부서별 완료일)",
        "max_col": prog_mc,
        "labels":  prog_labels,
        "r3_map":  {c: "auto" for c in range(1, prog_mc + 1)},
        "r4_map":  {c: ("id" if c <= 8 else "dept") for c in range(1, prog_mc + 1)},
        "freeze":  "auto",
    }

    # 3_출하현황
    ship_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 출하현황 │ {YEAR}",
        "purpose": "검사기 출하현황",
        "max_col": SHIP_SUMMARY_MAX_COL,
        "labels":  list(SHIP_SUMMARY_LABELS),
        "r3_map":  dict(R3_MAP_SHIP),
        "r4_map":  dict(R4_MAP_SHIP),
        "freeze":  "auto",
    }

    # 4_완료이력 (1_프로젝트등록과 동일 구조)
    arch_spec = dict(proj_spec)
    arch_spec["title"]   = f"㈜케이엔케이 │ {TYPE_NAME} │ 완료이력 │ {YEAR}"
    arch_spec["purpose"] = "검사기 완료이력"
    arch_spec["freeze"]  = "auto"
    # 완료이력은 정렬 불필요, D-day도 납품완료이므로 자동 공란 — 그대로 유지

    # 5_매핑조회
    map_labels = ["NO","관리코드","수주번호","고객사","모델","품명","진행상태","수주일"]
    map_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 매핑조회(수주번호) │ {YEAR}",
        "purpose": "검사기 매핑조회",
        "max_col": len(map_labels),
        "labels":  map_labels,
        "r3_map":  {c: "auto" for c in range(1, len(map_labels) + 1)},
        "r4_map":  {c: "id" for c in range(1, len(map_labels) + 1)},
        "freeze":  "auto",
        "row_end": 1000,
    }

    # 6_관리코드발행대장
    code_labels = ["NO","관리코드","수주번호","고객사","품명","발행일","발행사유"]
    code_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 관리코드발행대장 │ {YEAR}",
        "purpose": "검사기 관리코드발행",
        "max_col": len(code_labels),
        "labels":  code_labels,
        "r3_map":  {c: "auto" for c in range(1, len(code_labels) + 1)},
        "r4_map":  {c: "id" for c in range(1, len(code_labels) + 1)},
        "freeze":  "auto",
        "row_end": 5000,
    }

    # 7_수주번호생성대장
    sj_labels = ["NO","수주번호","관리코드","고객사","품명","생성일"]
    sj_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 수주번호생성대장 │ {YEAR}",
        "purpose": "검사기 수주번호생성",
        "max_col": len(sj_labels),
        "labels":  sj_labels,
        "r3_map":  {c: "auto" for c in range(1, len(sj_labels) + 1)},
        "r4_map":  {c: "id" for c in range(1, len(sj_labels) + 1)},
        "freeze":  "auto",
        "row_end": 5000,
    }

    # 8_매출마감 — 1_프로젝트등록/4_완료이력과 동일 구조
    settled_spec = dict(proj_spec)
    settled_spec["title"]   = f"㈜케이엔케이 │ {TYPE_NAME} │ 매출마감 │ {YEAR}"
    settled_spec["purpose"] = "검사기 매출마감 (계산서+입금 완료)"

    return {
        "1_프로젝트등록":       proj_spec,
        "2_진행현황":           prog_spec,
        "3_출하현황":           ship_spec,
        "4_완료이력":           arch_spec,
        "5_매핑조회(수주번호)": map_spec,
        "6_관리코드발행대장":   code_spec,
        "7_수주번호생성대장":   sj_spec,
        "8_매출마감":           settled_spec,
    }


# ═══════════════════════════════════════════════════════════════
# 부서입력 파일 (부서별 컬럼 다름)
# ═══════════════════════════════════════════════════════════════
def _dept_spec(dept):
    subs = DEPT_SUB_ITEMS.get(dept, [])
    milestones = DEPT_MILESTONES.get(dept, [])    # v3.0 마일스톤·입고일 컬럼
    n_sub = len(subs)
    n_ms = len(milestones)
    # v2026.04b: auto_cols 11열 — C10=담당자 추가 + 모델/품명 순서 swap
    # v3.1: K11 = "부서진척률(%)" (본인 부서 0/50/100 자동) — '전체진척률'(프로젝트 전체)과 구분
    auto_cols = ["NO","관리코드","수주번호","고객사","모델","품명",
                 "PO유형","영업단계","진행상태","담당자","부서진척률(%)"]
    n_auto = len(auto_cols)     # 11
    C_DEPT_PIC = 10
    labels = list(auto_cols) + list(subs) + list(milestones) + ["상태", "메모"]
    mc = len(labels)

    r3 = {}
    for c in range(1, n_auto + 1):
        r3[c] = "auto"
    r3[C_DEPT_PIC] = "input"                         # 담당자는 직접 입력
    # 세부항목 진척률 (input)
    for c in range(n_auto + 1, n_auto + n_sub + 1):
        r3[c] = "input"
    # v3.0 마일스톤·입고일 (po_input — PO 후 입력)
    for c in range(n_auto + n_sub + 1, n_auto + n_sub + n_ms + 1):
        r3[c] = "po_input"
    r3[n_auto + n_sub + n_ms + 1] = "select"      # 상태
    r3[n_auto + n_sub + n_ms + 2] = "memo"         # 메모

    r4 = {}
    for c in range(1, n_auto + 1):
        r4[c] = "id"
    r4[C_DEPT_PIC] = "dept"                          # 담당자 부서색
    # 세부항목 (status 영역색)
    for c in range(n_auto + 1, n_auto + n_sub + 1):
        r4[c] = "status"
    # v3.0 마일스톤·입고일 (payment 영역색 — 황금)
    for c in range(n_auto + n_sub + 1, n_auto + n_sub + n_ms + 1):
        r4[c] = "payment"
    r4[n_auto + n_sub + n_ms + 1] = "status"      # 상태
    r4[n_auto + n_sub + n_ms + 2] = "status"      # 메모

    return {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ {dept} │ {YEAR}",
        "purpose": f"검사기 {dept} 전용",
        "max_col": mc,
        "labels":  labels,
        "r3_map":  r3,
        "r4_map":  r4,
        "freeze":  "auto",
    }


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════
def apply_all():
    print("=" * 60)
    print(f"  [APPLY_STANDARD] {TYPE_NAME}")
    print(f"  스펙 v2026.04 — 체크리스트 20항 일괄 적용")
    print("=" * 60)

    # PMS 파일
    pms_fp = pms_path()
    if os.path.exists(pms_fp):
        normalize_file(pms_fp, _pms_specs(), fix_vml=True, log=_log)

    # 부서입력 파일
    for dept in DEPTS:
        fp = dept_path(dept)
        if os.path.exists(fp):
            normalize_file(fp, {"부서진척입력": _dept_spec(dept)}, fix_vml=True, log=_log)

    print("=" * 60)
    print(f"  완료 — 재검증은 diag.py 또는 openpyxl로 확인")
    print("=" * 60)


if __name__ == "__main__":
    apply_all()
