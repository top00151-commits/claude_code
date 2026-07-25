# -*- coding: utf-8 -*-
"""
v5H226z1053 (2026-07-25, ERP V1 전환 WP-03) — 프로젝트 호기·일련번호 (Project Unit·Serial)
게이트 검토판정(2026-07-25) P0/P1 반영본.

ADR-001 (3단계):
    프로젝트(관리번호) → [수주(선택·다건)] → 프로젝트 호기(Project Unit·필수) → 실물 일련번호(Serial·후발급)
  · project_unit(id) = 앞으로 BOM·자재출고·실투입·변경·출하가 붙는 **영구 축**(내부 PK)
  · equipment_serial = 표시·조회 식별값(관계 PK 아님)·**법인 내 영구 유일**·출하 전 필수·초기엔 빔

⭐ 순수 추가(additive): 기존 order_items·작업일정표·수주내역은 **건드리지 않는다**(교량 조건).

게이트 반영:
  · [P0-01] 일련번호 = 법인 내 **영구 유일(과거 포함·대소문자 무시)** = UNIQUE(entity, serial_no COLLATE NOCASE)
           호기당 **활성 일련번호 최대 1건** = UNIQUE(project_unit_id) WHERE active=1
           교체 시 이전행에 종료 메타(deactivated_at/by/reason) + supersedes 연결(누가·언제·왜·무엇을)
  · [P0-04] entity **NOT NULL CHECK(KOR/VN)** — Unit·Serial 법인 무결성
  · [P1-7.2] seed_order_no·seed_unit_label = 원본 스냅샷(수주·품목 삭제돼도 출처 보존)
  · [P0-01-5] equipment_serials→project_units FK = NO ACTION(RESTRICT) — 호기 삭제는 앱 가드가 먼저 차단

규정: 수량 컬럼 없음(호기 대수=행 수·z1048) · 날짜=TEXT datetime localtime(시간대 표준)

idempotent — 이미 있으면 건너뜀. main.py startup() 에서 1회.
"""
import sqlite3


def migrate(db_path: str) -> dict:
    created = []
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        have = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        if "project_units" not in have:
            cur.execute("""
                CREATE TABLE project_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    order_id INTEGER,
                    seed_order_item_id INTEGER,
                    seed_order_no TEXT,
                    seed_unit_label TEXT,
                    unit_no TEXT NOT NULL,
                    equipment_type TEXT,
                    entity TEXT NOT NULL DEFAULT 'KOR' CHECK (entity IN ('KOR','VN')),
                    status TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft','active','shipped','cancelled')),
                    note TEXT,
                    created_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE SET NULL,
                    FOREIGN KEY(seed_order_item_id) REFERENCES order_items(id) ON DELETE SET NULL
                )
            """)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_project_unit_no "
                        "ON project_units(project_id, unit_no)")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_project_unit_seed "
                        "ON project_units(seed_order_item_id) "
                        "WHERE seed_order_item_id IS NOT NULL")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_project_unit_proj "
                        "ON project_units(project_id, status)")
            created.append("project_units")

        if "equipment_serials" not in have:
            cur.execute("""
                CREATE TABLE equipment_serials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_unit_id INTEGER NOT NULL,
                    serial_no TEXT NOT NULL,
                    entity TEXT NOT NULL DEFAULT 'KOR' CHECK (entity IN ('KOR','VN')),
                    active INTEGER NOT NULL DEFAULT 1,
                    note TEXT,
                    issued_by INTEGER,
                    issued_at TEXT DEFAULT (datetime('now','localtime')),
                    supersedes_serial_id INTEGER,
                    deactivated_at TEXT,
                    deactivated_by INTEGER,
                    deactivation_reason TEXT,
                    FOREIGN KEY(project_unit_id) REFERENCES project_units(id),
                    FOREIGN KEY(supersedes_serial_id) REFERENCES equipment_serials(id) ON DELETE SET NULL
                )
            """)
            # 법인 내 영구 유일(과거 포함·대소문자 무시) — 한 번 쓴 일련번호는 재사용 불가
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_equipment_serial_entity "
                        "ON equipment_serials(entity, serial_no COLLATE NOCASE)")
            # 호기당 활성 일련번호 최대 1건 (PG 동시요청에서도 2개 활성 방지)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_equipment_serial_active "
                        "ON equipment_serials(project_unit_id) WHERE active=1")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_equipment_serial_unit "
                        "ON equipment_serials(project_unit_id)")
            created.append("equipment_serials")

        conn.commit()
    finally:
        conn.close()
    return {"created": created}


if __name__ == "__main__":
    import sys
    print(migrate(sys.argv[1] if len(sys.argv) > 1 else "data/knk.db"))
