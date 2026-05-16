"""
v5H226z107 (2026-05-16) — 업무카드 통합

대표 결재:
  - 통합 방향: B+A 혼합 (보기 합치기 + 자동 태스크 생성)
  - 용어: 워크플로우 "노드" + 일일업무 "태스크" → 통일 "업무카드"
  - 자유 잡일: hybrid (tasks.workflow_node_id NULL이면 자유 업무)
  - 부서 칸반: /workflow/team 신규 페이지 (팀장 권한 게이트)

DB 변경:
  - tasks 테이블에 workflow_node_id 컬럼 추가 (nullable)
    · NULL  → 자유 업무카드 (회의·출장·기타)
    · NOTNULL → 워크플로우 노드 연결 업무카드
"""

import sqlite3
import os


def _has_col(c, table, col):
    rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    added = []
    if not _has_col(c, 'tasks', 'workflow_node_id'):
        c.execute("ALTER TABLE tasks ADD COLUMN workflow_node_id INTEGER")
        c.execute("CREATE INDEX IF NOT EXISTS ix_tasks_wf_node ON tasks(workflow_node_id)")
        added.append('workflow_node_id')

    conn.commit()
    conn.close()
    return {'added_cols': added}


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, '..', '..', 'data', 'knk.db'))
    print(migrate(db))
