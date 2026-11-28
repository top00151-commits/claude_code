"""
z1214 (대표 2026-11-28 「3. 남겨」): 회의록 할 일 담당을 **사람이 정했는지** — meeting_actions.assignee_manual (idempotent · ALTER)
  - assignee_manual = 1 : 담당 바꾸기(POST /api/meeting/{mid}/action/{aid}/assignee) · 📄 양식 담당 칸 고치기로 사람이 정했다
                          → 「🔄 다시 정리」·「↩ 이전 정리」가 이 할 일을 지우지 않는다(화면 표시 「사람이 고름」)
  - assignee_manual = 0 : 그 밖(AI 정리 그대로 · 옛 기록)
⚠ 옛 줄은 0 그대로(저절로 바꾸지 않음) · 인덱스 없음 · startup() 에서 1회.
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
    if _has_table(c, "meeting_actions"):
        if "assignee_manual" not in _cols(c, "meeting_actions"):
            c.execute("ALTER TABLE meeting_actions ADD COLUMN assignee_manual INTEGER DEFAULT 0")
            added.append("meeting_actions.assignee_manual")
    conn.commit()
    conn.close()
    return {"added": added}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, "..", "..", "data", "knk.db"))
    print(migrate(db))
