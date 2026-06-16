"""
v5H226z430 (2026-06-14, 대표 지시) — 회의록 ↔ 프로젝트·영업기회 연결

대표 지시: 회의록을 진행하던 프로젝트(관리코드)와 연결, 영업기회와도 연결.
회의록에서 '새 영업기회 등록' 누르면 회의록 정보로 영업기회 생성 + 양방향 연결.

추가 컬럼 (idempotent · ALTER):
  - meetings.project_id        : 연결된 프로젝트(projects.id)
  - meetings.opportunity_id    : 연결된 영업기회(sales_opportunities.id)
  - sales_opportunities.meeting_id : 역참조(이 영업기회가 나온 회의록)

대상 테이블이 아직 없으면 건너뜀(다른 마이그가 먼저 만들어야 함). startup()에서 1회 호출.
"""
import sqlite3


def _has_table(c, t: str) -> bool:
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone())


def _cols(c, t: str) -> set:
    return {r[1] for r in c.execute(f"PRAGMA table_info({t})").fetchall()}


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    added = []
    if _has_table(c, "meetings"):
        mc = _cols(c, "meetings")
        if "project_id" not in mc:
            c.execute("ALTER TABLE meetings ADD COLUMN project_id INTEGER")
            added.append("meetings.project_id")
        if "opportunity_id" not in mc:
            c.execute("ALTER TABLE meetings ADD COLUMN opportunity_id INTEGER")
            added.append("meetings.opportunity_id")
        c.execute("CREATE INDEX IF NOT EXISTS ix_meetings_proj ON meetings(project_id)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_meetings_opp ON meetings(opportunity_id)")
    if _has_table(c, "sales_opportunities"):
        oc = _cols(c, "sales_opportunities")
        if "meeting_id" not in oc:
            c.execute("ALTER TABLE sales_opportunities ADD COLUMN meeting_id INTEGER")
            added.append("sales_opportunities.meeting_id")
    conn.commit()
    conn.close()
    return {"added": added}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, "..", "..", "data", "knk.db"))
    print(migrate(db))
