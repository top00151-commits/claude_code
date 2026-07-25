# -*- coding: utf-8 -*-
"""
v5H226z1053 (2026-07-25, ERP V1 전환 WP-03) — 프로젝트 호기·일련번호 (Project Unit·Serial)

ADR-001 (3단계):
    프로젝트(관리번호) → [수주(선택·다건)] → 프로젝트 호기(Project Unit·필수) → 실물 일련번호(Serial·후발급)
  · project_unit(id) = 앞으로 BOM·자재출고·실투입·변경·출하가 붙는 **영구 축**(내부 PK)
  · equipment_serial = 표시·조회 식별값(관계 PK 아님)·**법인 내 유일**·출하 전 필수·초기엔 빔

⭐ 순수 추가(additive): 기존 order_items·작업일정표·수주내역은 **건드리지 않는다**(교량 조건).
   호기는 order_items(호기 라인)에서 '씨앗'으로 만든다 → project_unit.seed_units_from_orders().
   씨앗 규칙 = 기존 시스템의 정식 호기 라벨 `^\\d+호기$`(z779 재번호 대상)만. 부속/부품 라인 제외.

추가 테이블 (idempotent — 이미 있으면 건너뜀. main.py startup() 에서 1회):
  project_units — 프로젝트 제작 단위(호기)
    · project_id(관리번호 FK·NOT NULL) → FK 로 'Project 없는 호기' 원천 차단(RS-01)
    · order_id(수주 FK·선택)·seed_order_item_id(씨앗 추적·선택)
    · unit_no(프로젝트 내 제작번호 '1호기' 등)·equipment_type·entity(법인·기본 KOR)·status·note
    · UNIQUE(project_id, unit_no) — 같은 프로젝트 제작번호 중복 차단(RS-01 차단조건)
    · UNIQUE(seed_order_item_id) WHERE NOT NULL — 같은 호기 라인 이중 씨앗 방지(멱등)
  equipment_serials — 실물 일련번호(호기당 이력·활성 1건)
    · project_unit_id(FK)·serial_no·entity(법인)·active·issued_at
    · UNIQUE(entity, serial_no) WHERE active=1 — 법인 내 유일(RS-01 차단조건)

규정 준수:
  · 수량 정수 규정(z1048): 호기 '대수'는 **행 수**로 표현 — 수량 컬럼을 두지 않음(정수 오염 원천 차단).
  · 날짜(KNK 시간대 표준): created_at 등은 TEXT + datetime('now','localtime') — 기존 패턴 동일.
  · FK ON: projects/orders/order_items 참조. 호기 라인·수주가 지워져도 호기는 남도록 SET NULL
    (기존 '호기 라인 삭제' 기능을 깨지 않기 위함 — additive 원칙).
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
                    unit_no TEXT NOT NULL,
                    equipment_type TEXT,
                    entity TEXT DEFAULT 'KOR',
                    status TEXT DEFAULT 'draft'
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
            # 같은 프로젝트 안에서 제작번호(호기) 중복 차단 (RS-01)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_project_unit_no "
                        "ON project_units(project_id, unit_no)")
            # 같은 호기 라인을 두 번 씨앗하지 않도록 (재씨앗 멱등)
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
                    entity TEXT DEFAULT 'KOR',
                    active INTEGER DEFAULT 1,
                    note TEXT,
                    issued_by INTEGER,
                    issued_at TEXT DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY(project_unit_id) REFERENCES project_units(id) ON DELETE CASCADE
                )
            """)
            # 법인 내 활성 일련번호 유일 (RS-01: '각 Serial 은 한국 법인 안에서 유일')
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_equipment_serial_entity "
                        "ON equipment_serials(entity, serial_no) WHERE active=1")
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
