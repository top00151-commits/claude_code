#!/usr/bin/env python3
"""
baby V2 Excel → HAIST WORKS DB 마이그레이션 (템플릿)
====================================================

⚠️ 정책 (system_scope_policy.md):
  baby는 임시 다리. web 완료 후 폐기.
  이 스크립트는 **1회성 실 데이터 이관 도구**다.

⚠️ 실행 전 필수:
  1. scripts/backup_db.py 로 DB 백업
  2. --dry-run 으로 결과 미리 확인
  3. 팀장 승인 후 실행

사용법:
    python scripts/migrate_baby_v2.py --dry-run       # 시뮬레이션만
    python scripts/migrate_baby_v2.py --source T      # 검사기만
    python scripts/migrate_baby_v2.py --source M      # 자동화만
    python scripts/migrate_baby_v2.py                 # 전체

NOTE:
  baby PMS 엑셀의 컬럼 매핑은 팀/버전마다 다를 수 있음.
  이 스크립트는 **기본 매핑 템플릿**이며, 실 파일 열어보고 조정 필요.
"""
import argparse
import os
import sys
from datetime import datetime

# Windows 콘솔 UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BABY_BASE = os.path.join(os.path.dirname(BASE), "HAIST_WORKS_baby", "V2")

PMS_FILES = {
    "T": os.path.join(BABY_BASE, "01_검사기_완제품", "KNK_검사기_완제품_PMS_2026.xlsx"),
    "M": os.path.join(BABY_BASE, "02_자동화_완제품", "KNK_자동화_완제품_PMS_2026.xlsx"),
}

# 컬럼 매핑 — 실제 baby PMS 구조 확인 후 조정
# 일반적인 baby PMS 컬럼 예상: 관리번호 / 프로젝트명 / 고객사 / 단계 / 금액 / 납기 / PM / 영업
COLUMN_MAP_TEMPLATE = {
    # 관리코드
    "관리번호":   "mgmt_code", "관리코드": "mgmt_code", "PMS": "mgmt_code",
    "PMS번호":    "mgmt_code", "PMS_NO": "mgmt_code", "코드": "mgmt_code",
    # 프로젝트/장비명
    "프로젝트명": "name", "제품명": "name", "장비명": "name",
    "모델명":     "name", "모델":   "name", "제품": "name",
    "PROJECT":    "name", "Project": "name", "ITEM": "name",
    # 고객
    "고객사":     "customer_name", "고객": "customer_name",
    "수요처":     "customer_name", "거래처": "customer_name",
    "CUSTOMER":   "customer_name",
    # 단계
    "단계":       "stage", "영업단계": "stage", "STAGE": "stage",
    "진행상태":   "status", "상태": "status", "STATUS": "status",
    # 금액
    "수주금액":   "order_amount", "금액": "order_amount",
    "수주액":     "order_amount", "AMOUNT": "order_amount",
    # 일정
    "수주일":     "order_date", "발주일": "order_date",
    "납기":       "due_date", "납기일": "due_date", "납품일": "due_date",
    # 담당
    "PM":         "pm_name", "담당": "pm_name", "담당자": "pm_name",
    "영업":       "sales_name", "영업담당": "sales_name",
    # 비고
    "비고":       "logi_note", "NOTE": "logi_note", "메모": "logi_note",
}


def read_pms(path: str) -> list[dict]:
    """PMS 엑셀에서 프로젝트 행 읽기. 첫 시트 헤더 기반 매핑."""
    try:
        import openpyxl
    except ImportError:
        print("[ERROR] openpyxl 필요. pip install openpyxl")
        sys.exit(1)

    if not os.path.exists(path):
        print(f"[SKIP] 파일 없음: {path}")
        return []

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    # PMS 시트 찾기 (첫 시트 기본)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    # 헤더 탐지: 매핑 키가 가장 많이 매치되는 행
    best_row, best_hits = 0, 0
    for i, row in enumerate(rows[:10]):
        hits = sum(1 for c in row if c and str(c).strip() in COLUMN_MAP_TEMPLATE)
        if hits > best_hits:
            best_hits, best_row = hits, i
    if best_hits < 2:
        print(f"[WARN] {os.path.basename(path)}: 헤더를 찾지 못함 (매칭 {best_hits}개)")
        return []

    headers = [str(c).strip() if c else "" for c in rows[best_row]]
    items = []
    for row in rows[best_row + 1:]:
        if not any(row):
            continue
        rec = {}
        for i, val in enumerate(row):
            if i >= len(headers):
                break
            col_name = headers[i]
            if col_name in COLUMN_MAP_TEMPLATE:
                db_col = COLUMN_MAP_TEMPLATE[col_name]
                rec[db_col] = val
        if rec.get("mgmt_code") or rec.get("name"):
            items.append(rec)
    return items


def import_to_db(items: list[dict], biz_div: str, dry_run: bool) -> dict:
    """items를 projects 테이블에 upsert (mgmt_code 기준)"""
    sys.path.insert(0, BASE)
    from app.database import db_session, init_db
    init_db()

    stats = {"new": 0, "updated": 0, "skipped": 0}
    with db_session() as c:
        for rec in items:
            mgmt = str(rec.get("mgmt_code") or "").strip()
            name = str(rec.get("name") or "").strip()
            if not name:
                stats["skipped"] += 1
                continue

            # 수주금액 숫자 변환
            amt_raw = rec.get("order_amount") or 0
            try:
                amount = float(str(amt_raw).replace(",", "").replace("원", "").strip())
            except (ValueError, TypeError):
                amount = 0

            existing = None
            if mgmt:
                existing = c.execute(
                    "SELECT id FROM projects WHERE mgmt_code=?", (mgmt,)
                ).fetchone()

            if existing:
                if not dry_run:
                    c.execute(
                        """UPDATE projects
                           SET name=?, customer_name=?, stage=?, order_amount=?,
                               order_date=?, due_date=?, pm_name=?, sales_name=?,
                               logi_note=?, biz_div=?, updated_at=?
                           WHERE id=?""",
                        (name, rec.get("customer_name"), rec.get("stage"),
                         amount, rec.get("order_date"), rec.get("due_date"),
                         rec.get("pm_name"), rec.get("sales_name"),
                         rec.get("logi_note"), biz_div,
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         existing["id"]),
                    )
                stats["updated"] += 1
            else:
                if not dry_run:
                    c.execute(
                        """INSERT INTO projects
                           (mgmt_code, name, customer_name, stage, order_amount,
                            order_date, due_date, pm_name, sales_name, logi_note,
                            biz_div, status)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?, 'active')""",
                        (mgmt or None, name, rec.get("customer_name"),
                         rec.get("stage"), amount, rec.get("order_date"),
                         rec.get("due_date"), rec.get("pm_name"),
                         rec.get("sales_name"), rec.get("logi_note"), biz_div),
                    )
                stats["new"] += 1
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["T", "M", "all"], default="all")
    ap.add_argument("--dry-run", action="store_true", help="DB 변경 없이 시뮬레이션")
    args = ap.parse_args()

    sources = ["T", "M"] if args.source == "all" else [args.source]
    print(f"{'='*60}")
    print(f"baby V2 → HAIST WORKS 마이그레이션 ({'DRY-RUN' if args.dry_run else 'LIVE'})")
    print(f"{'='*60}")
    total_stats = {"new": 0, "updated": 0, "skipped": 0}
    for biz in sources:
        path = PMS_FILES.get(biz)
        if not path:
            continue
        print(f"\n[{biz}] {os.path.basename(path)}")
        items = read_pms(path)
        print(f"  읽음: {len(items)}건")
        if not items:
            continue
        # 샘플 출력
        for r in items[:3]:
            print(f"    샘플: {r.get('mgmt_code','?')} {r.get('name','?')} "
                  f"/ {r.get('customer_name','')} / {r.get('stage','')}")
        stats = import_to_db(items, biz, args.dry_run)
        print(f"  결과: 신규 {stats['new']} / 갱신 {stats['updated']} / 스킵 {stats['skipped']}")
        for k in total_stats:
            total_stats[k] += stats[k]

    print(f"\n{'='*60}")
    print(f"합계: 신규 {total_stats['new']}, 갱신 {total_stats['updated']}, "
          f"스킵 {total_stats['skipped']}")
    if args.dry_run:
        print("⚠️  DRY-RUN 모드 — 실제 DB에 반영되지 않음")
        print("   실행: python scripts/migrate_baby_v2.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
