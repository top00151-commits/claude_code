# -*- coding: utf-8 -*-
"""
v5H226z1053 (2026-07-25, ERP V1 전환 WP-03) — 프로젝트 호기(Project Unit)

⭐ 대표 업무교정(2026-07-25) 반영본:
   · KNK는 **일련번호(S/N)를 쓰지 않는다** → equipment_serials 폐기.
     실제 식별 = 관리번호(프로젝트) + 수주번호(발주차수) + 호기번호.
   · 프로젝트는 **개발호기로 시작**하고 개발·수주 변경에 따라 **호기번호·구성이 바뀐다**
     (대수 변경·번호 변경·추가·취소·분할·통합·수주 후행 발행).
   → **호기번호는 영구 식별자가 아니다.** 영구 식별자는 `project_units.id` 하나뿐이며
     BOM·설계변경·자재·생산·검사·출하는 전부 이 id 에 연결한다.

표 4개:
  ① project_units                     — 장비 단위(영구 id). 개발호기명·현재 호기번호(NULL 가능)·상태
  ② project_unit_identifier_history   — 호기번호 변경이력(이전·이후·사유·변경자·시각·Change·적용시점)
  ③ project_unit_order_links          — 수주번호 **다중 관계**(ORIGIN/ADDITIONAL/CHANGE/CANCEL·덮어쓰기·삭제 금지)
  ④ project_unit_relations            — 분할·통합 관계 이력(SPLIT/MERGE·1:N·N:1)
     ⛔ **V1은 구조만**: 실행 버튼·API·승인 없음. 일반 사용자 생성 차단(앱에 쓰기 경로 없음).
        BOM·발주·생산 영향 분석이 연결되는 WP-04 이후에 실행 기능 구현.

상태(V1 최소): PROVISIONAL(개발·미확정) / CONFIRMED(확정) / CANCELLED(취소·물리삭제 금지)

규정: 수량 컬럼 없음(호기 대수=행 수·z1048) · 날짜=TEXT datetime localtime(시간대 표준)
      법인 entity NOT NULL CHECK(KOR/VN)

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

        # ① 장비 단위 — 영구 id. 호기번호는 '현재값'일 뿐 식별자가 아니다.
        if "project_units" not in have:
            cur.execute("""
                CREATE TABLE project_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    working_name TEXT,
                    current_unit_no TEXT,
                    unit_state TEXT NOT NULL DEFAULT 'PROVISIONAL'
                        CHECK (unit_state IN ('PROVISIONAL','CONFIRMED','CANCELLED')),
                    equipment_type TEXT,
                    -- [게이트 v4 P0-02] 법인은 프로젝트 확정값에서 **명시적으로** 넘겨야 저장된다.
                    --   기본값(DEFAULT 'KOR')을 두면 배치·마이그레이션·향후 API 가 법인을 생략했을 때
                    --   DB 가 조용히 KOR 를 넣어 '빈값이면 중단' 정책이 무력화된다.
                    entity TEXT NOT NULL CHECK (entity IN ('KOR','VN')),
                    seed_order_item_id INTEGER,
                    seed_order_no TEXT,
                    seed_unit_label TEXT,
                    note TEXT,
                    created_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_by INTEGER,
                    updated_at TEXT DEFAULT (datetime('now','localtime')),
                    confirmed_by INTEGER,
                    confirmed_at TEXT,
                    cancelled_by INTEGER,
                    cancelled_at TEXT,
                    cancellation_reason TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(seed_order_item_id) REFERENCES order_items(id) ON DELETE SET NULL
                )
            """)
            # 현재 호기번호는 '같은 시점 · 같은 프로젝트'에서만 유일 — 취소된 호기는 번호를 비워주므로 제외.
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_project_unit_current_no "
                        "ON project_units(project_id, current_unit_no) "
                        "WHERE current_unit_no IS NOT NULL AND unit_state <> 'CANCELLED'")
            # 같은 수주 호기 라인을 두 번 씨앗하지 않도록(멱등)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_project_unit_seed "
                        "ON project_units(seed_order_item_id) "
                        "WHERE seed_order_item_id IS NOT NULL")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_project_unit_proj "
                        "ON project_units(project_id, unit_state)")
            created.append("project_units")

        # ② 호기번호 변경이력 — 번호가 바뀌어도 Unit id 는 유지되고, 과거 표시값을 재현할 수 있어야 한다.
        if "project_unit_identifier_history" not in have:
            cur.execute("""
                CREATE TABLE project_unit_identifier_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_unit_id INTEGER NOT NULL,
                    old_unit_no TEXT,
                    new_unit_no TEXT,
                    change_reason TEXT,
                    changed_by INTEGER,
                    changed_at TEXT DEFAULT (datetime('now','localtime')),
                    change_id TEXT,
                    effective_from TEXT,
                    effective_to TEXT,
                    FOREIGN KEY(project_unit_id) REFERENCES project_units(id)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_punit_idhist "
                        "ON project_unit_identifier_history(project_unit_id, id)")
            created.append("project_unit_identifier_history")

        # ③ 수주 연결 = 관계(소유필드 아님). 최초=ORIGIN, 추가·변경은 새 행. 덮어쓰기·삭제 금지.
        if "project_unit_order_links" not in have:
            cur.execute("""
                CREATE TABLE project_unit_order_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_unit_id INTEGER NOT NULL,
                    order_id INTEGER,
                    order_no TEXT,
                    relation_type TEXT NOT NULL DEFAULT 'ORIGIN'
                        CHECK (relation_type IN ('ORIGIN','ADDITIONAL','CHANGE','CANCEL')),
                    active INTEGER NOT NULL DEFAULT 1,
                    reason TEXT,
                    change_id TEXT,
                    linked_by INTEGER,
                    linked_at TEXT DEFAULT (datetime('now','localtime')),
                    unlinked_by INTEGER,
                    unlinked_at TEXT,
                    FOREIGN KEY(project_unit_id) REFERENCES project_units(id),
                    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE SET NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_punit_orderlink "
                        "ON project_unit_order_links(project_unit_id, active)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_punit_orderlink_ord "
                        "ON project_unit_order_links(order_id)")
            # [게이트 v4 P1] 앱 함수뿐 아니라 **DB 에서도** 중복 연결을 막는다
            #   (동시 요청·향후 다른 입력 경로 대비). PostgreSQL 도 동일 제약을 건다.
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_punit_orderlink_active "
                        "ON project_unit_order_links(project_unit_id, order_id, relation_type) "
                        "WHERE active=1")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_punit_orderlink_origin "
                        "ON project_unit_order_links(project_unit_id) "
                        "WHERE active=1 AND relation_type='ORIGIN'")
            created.append("project_unit_order_links")

        # ④ 분할·통합 관계 이력 — 1:N(SPLIT)·N:1(MERGE) 둘 다 되도록 **행 단위 관계**로.
        #    ⛔ V1: 구조만. 앱에 쓰기 경로 없음(실행·승인은 WP-04 영향분석 연결 후).
        if "project_unit_relations" not in have:
            cur.execute("""
                CREATE TABLE project_unit_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_unit_id INTEGER NOT NULL,
                    result_unit_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL CHECK (relation_type IN ('SPLIT','MERGE')),
                    change_reason TEXT,
                    change_id TEXT,
                    effective_at TEXT,
                    processed_by INTEGER,
                    approved_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY(source_unit_id) REFERENCES project_units(id),
                    FOREIGN KEY(result_unit_id) REFERENCES project_units(id)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_punit_rel_src "
                        "ON project_unit_relations(source_unit_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_punit_rel_res "
                        "ON project_unit_relations(result_unit_id)")
            created.append("project_unit_relations")

        # ⑤ 권한 우회(시스템 관리자 복구) 감사 기록 — 대표 확정 §3 "사용자·시각·사유를 남긴다"
        if "project_unit_audit" not in have:
            cur.execute("""
                CREATE TABLE project_unit_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id INTEGER,
                    actor_name TEXT,
                    action TEXT NOT NULL,
                    target TEXT,
                    note TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            created.append("project_unit_audit")

        # ── 기존 적용 DB 보정 (게이트 v4 P0-02·P1 · §8-4) ──────────────────────
        #   v3/v4 마이그레이션이 이미 돌아간 DB 는 project_units.entity 에 DEFAULT 'KOR' 이 남아 있다.
        #   SQLite 는 컬럼 기본값만 떼어낼 수 없으므로 표를 재작성한다(데이터 보존).
        fixed = []
        row = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='project_units'").fetchone()
        if row and row[0] and "DEFAULT 'KOR'" in row[0]:
            cur.execute("PRAGMA foreign_keys=OFF")
            # ⚠ 기본 동작은 RENAME 시 **다른 표의 FK 참조까지 새 이름으로 따라 고친다**
            #   (identifier_history 등이 project_units_old_z1053 을 가리키게 되어 깨짐).
            #   legacy_alter_table=ON 으로 두면 참조를 건드리지 않아 원래 이름을 계속 가리킨다.
            cur.execute("PRAGMA legacy_alter_table=ON")
            cur.execute("ALTER TABLE project_units RENAME TO project_units_old_z1053")
            cur.execute("""
                CREATE TABLE project_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    working_name TEXT,
                    current_unit_no TEXT,
                    unit_state TEXT NOT NULL DEFAULT 'PROVISIONAL'
                        CHECK (unit_state IN ('PROVISIONAL','CONFIRMED','CANCELLED')),
                    equipment_type TEXT,
                    entity TEXT NOT NULL CHECK (entity IN ('KOR','VN')),
                    seed_order_item_id INTEGER,
                    seed_order_no TEXT,
                    seed_unit_label TEXT,
                    note TEXT,
                    created_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_by INTEGER,
                    updated_at TEXT DEFAULT (datetime('now','localtime')),
                    confirmed_by INTEGER,
                    confirmed_at TEXT,
                    cancelled_by INTEGER,
                    cancelled_at TEXT,
                    cancellation_reason TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(seed_order_item_id) REFERENCES order_items(id) ON DELETE SET NULL
                )
            """)
            old_cols = [r[1] for r in cur.execute(
                "PRAGMA table_info(project_units_old_z1053)").fetchall()]
            new_cols = [r[1] for r in cur.execute("PRAGMA table_info(project_units)").fetchall()]
            common = [c0 for c0 in new_cols if c0 in old_cols]
            cur.execute(f"INSERT INTO project_units ({','.join(common)}) "
                        f"SELECT {','.join(common)} FROM project_units_old_z1053")
            cur.execute("DROP TABLE project_units_old_z1053")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_project_unit_current_no "
                        "ON project_units(project_id, current_unit_no) "
                        "WHERE current_unit_no IS NOT NULL AND unit_state <> 'CANCELLED'")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_project_unit_seed "
                        "ON project_units(seed_order_item_id) "
                        "WHERE seed_order_item_id IS NOT NULL")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_project_unit_proj "
                        "ON project_units(project_id, unit_state)")
            cur.execute("PRAGMA foreign_keys=ON")
            fixed.append("project_units.entity DEFAULT 'KOR' 제거")
        # 기존 DB 에 링크 중복 제약이 없으면 추가(P1)
        if "project_unit_order_links" in have:
            idx = {r[0] for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND tbl_name='project_unit_order_links'").fetchall()}
            if "uq_punit_orderlink_active" not in idx:
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_punit_orderlink_active "
                            "ON project_unit_order_links(project_unit_id, order_id, relation_type) "
                            "WHERE active=1")
                fixed.append("수주연결 활성 중복 제약 추가")
            if "uq_punit_orderlink_origin" not in idx:
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_punit_orderlink_origin "
                            "ON project_unit_order_links(project_unit_id) "
                            "WHERE active=1 AND relation_type='ORIGIN'")
                fixed.append("활성 ORIGIN 1개 제약 추가")

        conn.commit()
    finally:
        conn.close()
    return {"created": created, "fixed": fixed}


if __name__ == "__main__":
    import sys
    print(migrate(sys.argv[1] if len(sys.argv) > 1 else "data/knk.db"))
