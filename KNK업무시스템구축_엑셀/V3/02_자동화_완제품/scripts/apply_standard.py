"""
╔══════════════════════════════════════════════════════════════╗
║  02_자동화_완제품 apply_standard.py                            ║
║  스펙 §19 원칙 1 — 빌드·동기화 직후 이 스크립트 1회 실행       ║
║  스펙 §20 체크리스트 20항 일괄 보장                            ║
║  실행: python scripts/apply_standard.py                       ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    TYPE_NAME, YEAR, DEPTS, DEPT_SUB_ITEMS, DEPT_MILESTONES,
    PMS_HEADER_LABELS, MAX_COL, R3_MAP_PROJ, R4_MAP_PROJ,
    SHIP_SUMMARY_MAX_COL, SHIP_SUMMARY_LABELS, R3_MAP_SHIP, R4_MAP_SHIP,
    C_QTY, C_CURRENCY, C_UPRICE, C_TOTAL, C_DDAY, C_STATUS, C_DEPT_START,
    DROPDOWN_MAP,
    pms_path, dept_path,
)
from shared.knk_standard import normalize_file, wrap_label_2lines


def _log(msg):
    print(msg)


def _wrap_dept_name(name):
    """v3.1: 부서명 4글자 초과 시 4글자+\n+나머지 (열 너비 통일)
    예: '전장설계팀'(5)→'전장설계\n팀', '소프트웨어팀'(6)→'소프트웨\n어팀',
        '제조기술2팀'(6)→'제조기술\n2팀', '설계팀'(3)→그대로
    """
    if len(name) > 4:
        return name[:4] + "\n" + name[4:]
    return name


DEPT_COL_WIDTH = 7   # v3.1: 부서 컬럼 통일 너비


def _pms_specs():
    # v2026.04e: 1_프로젝트등록 = 31열 (부서 7 + 매출·수금 2)
    mc = MAX_COL  # 31
    dept_labels = [_wrap_dept_name(d) for d in DEPTS]
    labels = list(PMS_HEADER_LABELS) + dept_labels + ["계산서\n발행일", "입금일"]
    r3 = dict(R3_MAP_PROJ)
    r4 = dict(R4_MAP_PROJ)

    # 부서 컬럼 너비 통일
    dept_widths = {c: DEPT_COL_WIDTH for c in range(C_DEPT_START, C_DEPT_START + len(DEPTS))}

    proj_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 프로젝트 등록 │ {YEAR}",
        "purpose": "자동화 PMS 전용",
        # v2026.04c: 1_프로젝트등록 전용 안내문구 — 빈 공간 제거 대신 신규 수주 입력 방법 안내
        "slogan":  "㈜케이엔케이 자동화 PMS   │   💡 신규 수주 입력:  Ctrl+End (입력된 데이터 마지막 행 이동) → 다음 행에 입력 → 실행_PMS(영업·PM).bat 실행",
        "max_col": mc,
        "labels":  labels,
        "r3_map":  r3,
        "r4_map":  r4,
        "freeze":  "auto",   # 품명(C7)까지 고정 — A~G열 + R1~R4
        "qty_cols":     [C_QTY],
        "money_cols":   [C_UPRICE, C_TOTAL],
        "currency_col": C_CURRENCY,
        "dday_col":     C_DDAY,
        "status_col":   C_STATUS,
        "dropdown_map": dict(DROPDOWN_MAP),
        "fixed_widths": dept_widths,
    }

    # 2_진행현황
    prog_labels = ["NO","관리코드","수주번호","고객사","모델","품명","진행상태","전체\n진척률(%)"]
    for dept in DEPTS:
        wrapped = _wrap_dept_name(dept)
        for sub in DEPT_SUB_ITEMS.get(dept, []):
            prog_labels.append(f"{wrapped}\n{sub}")
        prog_labels.append(f"{wrapped}\n소계")
    prog_mc = len(prog_labels)
    prog_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 진행현황 │ {YEAR}",
        "purpose": "자동화 진행현황",
        "max_col": prog_mc,
        "labels":  prog_labels,
        "r3_map":  {c: "auto" for c in range(1, prog_mc + 1)},
        "r4_map":  {c: ("id" if c <= 8 else "dept") for c in range(1, prog_mc + 1)},
        "freeze":  "auto",
    }

    # 3_출하현황
    ship_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 출하현황 │ {YEAR}",
        "purpose": "자동화 출하현황",
        "max_col": SHIP_SUMMARY_MAX_COL,
        "labels":  list(SHIP_SUMMARY_LABELS),
        "r3_map":  dict(R3_MAP_SHIP),
        "r4_map":  dict(R4_MAP_SHIP),
        "freeze":  "auto",
    }

    # 4_완료이력
    arch_spec = dict(proj_spec)
    arch_spec["title"]   = f"㈜케이엔케이 │ {TYPE_NAME} │ 완료이력 │ {YEAR}"
    arch_spec["purpose"] = "자동화 완료이력"
    arch_spec["freeze"]  = "auto"

    # 5/6/7 대장류
    map_labels = ["NO","관리코드","수주번호","고객사","모델","품명","진행상태","수주일"]
    map_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 매핑조회(수주번호) │ {YEAR}",
        "purpose": "자동화 매핑조회",
        "max_col": len(map_labels),
        "labels":  map_labels,
        "r3_map":  {c: "auto" for c in range(1, len(map_labels) + 1)},
        "r4_map":  {c: "id" for c in range(1, len(map_labels) + 1)},
        "freeze":  "auto",
        "row_end": 1000,
    }
    code_labels = ["NO","관리코드","수주번호","고객사","품명","발행일","발행사유"]
    code_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 관리코드발행대장 │ {YEAR}",
        "purpose": "자동화 관리코드발행",
        "max_col": len(code_labels),
        "labels":  code_labels,
        "r3_map":  {c: "auto" for c in range(1, len(code_labels) + 1)},
        "r4_map":  {c: "id" for c in range(1, len(code_labels) + 1)},
        "freeze":  "auto",
        "row_end": 5000,
    }
    sj_labels = ["NO","수주번호","관리코드","고객사","품명","생성일"]
    sj_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 수주번호생성대장 │ {YEAR}",
        "purpose": "자동화 수주번호생성",
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
    settled_spec["purpose"] = "자동화 매출마감 (계산서+입금 완료)"

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


INPUT_COL_WIDTH = 7   # v3.1: 부서 입력칸 통일 너비 (한3자=6단위 + 여유 1)


def _dept_spec(dept):
    subs_raw = DEPT_SUB_ITEMS.get(dept, [])
    milestones_raw = DEPT_MILESTONES.get(dept, [])
    # v3.1.2: 항목별 [%·예정일] 짝 배치 — 한 항목 = 진척률 컬럼 + 예정일 컬럼
    subs = [wrap_label_2lines(s) for s in subs_raw]
    milestones = list(milestones_raw)
    n_sub = len(subs)        # 세부항목 개수
    n_pair = n_sub * 2        # 진척률 + 예정일 컬럼 합계
    n_ms = len(milestones)
    # v2026.04b: auto_cols 11열 — C10=담당자 추가 + 모델/품명 순서 swap
    # v3.1: K11 = "부서진척률(%)" (본인 부서 세부항목 평균 자동 계산)
    auto_cols = ["NO","관리코드","수주번호","고객사","모델","품명",
                 "PO유형","영업단계","진행상태","담당자","부서진척률(%)"]
    n_auto = len(auto_cols)     # 11
    C_DEPT_PIC = 10

    # 라벨: auto_cols + (sub, 예정일) 짝 + 마일스톤 + 상태/메모
    labels = list(auto_cols)
    for sub in subs:
        labels.append(sub)               # 진척률 컬럼
        labels.append("예정일")          # 예정일 컬럼 (메모로 어떤 항목인지 명시)
    labels += list(milestones) + ["상태", "메모"]
    mc = len(labels)

    sub_start = n_auto + 1                 # 첫 세부항목 컬럼
    ms_start  = n_auto + n_pair + 1        # 마일스톤 시작
    status_col = ms_start + n_ms           # 상태
    memo_col   = ms_start + n_ms + 1       # 메모

    r3 = {}
    for c in range(1, n_auto + 1):
        r3[c] = "auto"
    r3[C_DEPT_PIC] = "input"                  # 담당자
    # 세부항목 짝: % = input, 예정일 = po_input
    for i in range(n_sub):
        r3[sub_start + i*2]     = "input"     # 진척률
        r3[sub_start + i*2 + 1] = "po_input"  # 예정일
    # 마일스톤
    for c in range(ms_start, ms_start + n_ms):
        r3[c] = "po_input"
    r3[status_col] = "select"
    r3[memo_col]   = "memo"

    r4 = {}
    for c in range(1, n_auto + 1):
        r4[c] = "id"
    r4[C_DEPT_PIC] = "dept"
    # v3.1.2 (옵션 B): 한 항목의 [%·예정일] 두 컬럼 = 같은 색
    #   항목별 청·주황 교대 — 항목 1=청, 2=주황, 3=청, 4=주황, ...
    for i in range(n_sub):
        color = "pair_a" if i % 2 == 0 else "pair_b"
        r4[sub_start + i*2]     = color   # 진척률
        r4[sub_start + i*2 + 1] = color   # 예정일 (같은 색)
    for c in range(ms_start, ms_start + n_ms):
        r4[c] = "payment"
    r4[status_col] = "status"
    r4[memo_col]   = "status"

    # v3.1.2: 모든 입력 컬럼 너비 7 통일
    fixed_widths = {c: INPUT_COL_WIDTH
                    for c in range(sub_start, ms_start + n_ms)}

    # v3.1.2: 각 "예정일" 컬럼에 항목별 메모 (어느 항목 예정일인지 명시)
    comments = {}
    for i, sub_raw in enumerate(subs_raw):
        due_col = sub_start + i*2 + 1
        sub_clean = sub_raw.replace("\n", "")
        comments[due_col] = (
            f"▣ {sub_clean} — 완료 예정일\n\n"
            f"★ 날짜 입력 (% 아님 ⚠️)\n\n"
            f"• 형식: YYYY-MM-DD  예: 2026-07-15\n"
            f"• {sub_clean} 작업의 ★완료 예정일★ 기입\n\n"
            f"📋 운영:\n"
            f"  ▸ 좌측 셀 = 진척률(%)\n"
            f"  ▸ 이 셀  = {sub_clean} 완료 목표일\n"
            f"  ▸ 진척률과 비교 → 일정 대비 진행도 추적\n"
            f"  ▸ 예: 7/15까지 100% 목표인데 7/10 현재 50% → 일정 빠름\n\n"
            f"• 비워두면: 일정 미정 또는 해당없음"
        )

    return {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ {dept} │ {YEAR}",
        "purpose": f"자동화 {dept} 전용",
        "max_col": mc,
        "labels":  labels,
        "r3_map":  r3,
        "r4_map":  r4,
        "freeze":  "auto",
        "fixed_widths": fixed_widths,
        "comments": comments,
    }


def apply_all():
    print("=" * 60)
    print(f"  [APPLY_STANDARD] {TYPE_NAME}")
    print(f"  스펙 v2026.04d — 체크리스트 20항 일괄 적용 (29열, 부서 복원)")
    print("=" * 60)

    pms_fp = pms_path()
    if os.path.exists(pms_fp):
        normalize_file(pms_fp, _pms_specs(), fix_vml=True, log=_log)

    for dept in DEPTS:
        fp = dept_path(dept)
        if os.path.exists(fp):
            normalize_file(fp, {"부서진척입력": _dept_spec(dept)}, fix_vml=True, log=_log)

    print("=" * 60)


if __name__ == "__main__":
    apply_all()
