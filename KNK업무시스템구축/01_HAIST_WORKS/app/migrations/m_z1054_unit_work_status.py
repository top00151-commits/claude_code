# -*- coding: utf-8 -*-
# ============================================================
# v5H226z1054 (2026-07-26) — 호기의 **업무 진행상태**를 신원 상태와 분리해 보존
# ------------------------------------------------------------
# [게이트 판정 `CHATGPT_WP03_과거데이터_작업일정표상태_반영판정_2026-07-26.md`]
#   §4 두 상태는 **의미가 다르다** — 하나로 합쳐 저장하지 말 것:
#       · 호기 **신원** 상태 : 이 장비가 몇 호기인지 확정됐는가?
#                             `unit_state` = PROVISIONAL / CONFIRMED / CANCELLED
#       · 업무 **진행** 상태 : 장비가 지금 어느 단계인가?
#                             `work_status` = IN_PROGRESS / ON_HOLD / SHIPPED / CANCELLED
#   §11 "출하 = CONFIRMED 하나로만 저장하는 구조는 금지" — 이후 BOM·생산·품질·출하·A/S 가
#       각각 다른 의미로 쓰기 때문이다.
#   §3 과거 데이터 보정 매핑: 출하→CONFIRMED+SHIPPED · 진행중→PROVISIONAL+IN_PROGRESS
#                            · 보류→PROVISIONAL+ON_HOLD · 취소→CANCELLED(또는 후보 제외)
#   §8 화면에 **원본 데이터 출처**와 **작업일정표 상태**를 함께 보여야 하므로 근거도 같이 보관한다.
#
# ⭐ 순수 추가(ALTER ADD COLUMN)만 한다 — 기존 표·행 무변화.
# ============================================================
import sqlite3

# 업무 진행상태 — 작업일정표(order_items.unit_status) 어휘와 1:1
WORK_STATES = ("IN_PROGRESS", "ON_HOLD", "SHIPPED", "CANCELLED")

_COLS = (
    # 업무 진행상태. 직접 만든 개발호기는 아직 아무 일도 안 일어났으므로 진행중이 기본.
    ("work_status", "TEXT NOT NULL DEFAULT 'IN_PROGRESS'"),
    # 이 상태를 무엇을 보고 정했는지(§8 원본 데이터 출처) — 예: '작업일정표', '수동'
    ("work_status_src", "TEXT"),
    # 원본 작업일정표 표기 그대로(출하/진행중/보류/취소) — 화면에 사용자 말로 보여주기 위함
    ("work_status_label", "TEXT"),
    ("work_status_at", "TEXT"),
)


def _cols(cur, table):
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def migrate(db_path: str) -> dict:
    added = []
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        have_tbl = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "project_units" not in have_tbl:
            return {"added": [], "skipped": "project_units 없음(z1053 먼저)"}

        have = _cols(cur, "project_units")
        for col, decl in _COLS:
            if col not in have:
                cur.execute(f"ALTER TABLE project_units ADD COLUMN {col} {decl}")
                added.append(f"project_units.{col}")

        # 상태별 목록 조회(출하만 보기 등)용
        cur.execute("CREATE INDEX IF NOT EXISTS idx_project_unit_work "
                    "ON project_units(project_id, work_status)")

        # ── 과거 데이터 보정 이력 (§9-7 원본 상태와 보정 근거를 감사기록으로) ──────
        #   ⛔ 덮어쓰기만 하고 끝내지 않는다: 무엇이 무엇으로 왜 바뀌었는지 남긴다.
        #   같은 보정을 다시 실행해도(§9-8) 바뀐 게 없으면 이력도 늘지 않는다(호출부 책임).
        if "project_unit_status_backfill" not in have_tbl:
            cur.execute("""
                CREATE TABLE project_unit_status_backfill (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_unit_id INTEGER NOT NULL,
                    project_id INTEGER,
                    order_item_id INTEGER,
                    source_label TEXT,            -- 원본 작업일정표 표기(출하/진행중/보류/취소)
                    old_unit_state TEXT,
                    new_unit_state TEXT,
                    old_work_status TEXT,
                    new_work_status TEXT,
                    reason TEXT,
                    actor_id INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY(project_unit_id) REFERENCES project_units(id)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_punit_backfill "
                        "ON project_unit_status_backfill(project_id, project_unit_id)")
            added.append("project_unit_status_backfill")

        # ── 후보에서 **제외한 줄**의 이력 (§3.4 "아무 기록 없이 제외해서는 안 된다") ──
        if "project_unit_candidate_skips" not in have_tbl:
            cur.execute("""
                CREATE TABLE project_unit_candidate_skips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    order_item_id INTEGER NOT NULL,
                    order_no TEXT,
                    unit_label TEXT,
                    source_label TEXT,            -- 그때의 작업일정표 상태
                    skip_reason TEXT NOT NULL,    -- 예: '작업일정표 취소'
                    actor_id INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_punit_skip "
                        "ON project_unit_candidate_skips(project_id, order_item_id)")
            added.append("project_unit_candidate_skips")

        conn.commit()
        return {"added": added}
    finally:
        conn.close()
