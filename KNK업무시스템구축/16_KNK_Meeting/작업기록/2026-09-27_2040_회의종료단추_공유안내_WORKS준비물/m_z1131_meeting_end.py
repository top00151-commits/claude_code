"""
회의 종료 단추 (2026-09-27 대표 지시) — meetings.ended_at (idempotent · ALTER)

대표 질문: 「회의 종료는 어디서 선택할 수 있지? 종료 조건이 시간이 완료되면 종료 처리 되는 걸로 아는데…
          종료시간 이전에 끝났을 때는 종료 처리를 어디서 해야 하는지?」
지금 규칙: ①녹음이 붙거나 정리되면 즉시 종료 ②녹음 없으면 예정 끝 시각에 자동 종료
          ③녹음 중이면 끝 시각 뒤 12시간까지 「회의 중」 — 사람이 누를 곳은 없었다.
고침: 「⏹ 회의 종료」를 누른 시각을 아래 칸에 적고, 회의 카드가 그 값을 먼저 본다.
  - meetings.ended_at : '' | 'YYYY-MM-DD HH:MM:SS'

⚠ 인덱스는 만들지 않는다(칸 하나) · startup()에서 1회 호출 · 기존 DB 에도 안전(ALTER 한 번).
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
        if "ended_at" not in _cols(c, "meetings"):
            c.execute("ALTER TABLE meetings ADD COLUMN ended_at TEXT DEFAULT ''")
            added.append("meetings.ended_at")
    conn.commit()
    conn.close()
    return {"added": added}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, "..", "..", "data", "knk.db"))
    print(migrate(db))
