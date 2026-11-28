"""
z1213 (대표 2026-11-28): 회의록 할 일 담당 = 번호로 연결 — meeting_actions.assignee_ext (idempotent · ALTER)
  - assignee_ext = 1 : 사람이 「외부(직원 아님)」 담당으로 정했다 → 화면이 「외부」로 보인다
  - assignee_ext = 0 : 그 밖(번호 연결됨 · 또는 AI·옛 기록이라 연결 안 됨 → 화면이 「👤 담당 확인」)
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
        if "assignee_ext" not in _cols(c, "meeting_actions"):
            c.execute("ALTER TABLE meeting_actions ADD COLUMN assignee_ext INTEGER DEFAULT 0")
            added.append("meeting_actions.assignee_ext")
    conn.commit()
    conn.close()
    return {"added": added}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, "..", "..", "data", "knk.db"))
    print(migrate(db))
