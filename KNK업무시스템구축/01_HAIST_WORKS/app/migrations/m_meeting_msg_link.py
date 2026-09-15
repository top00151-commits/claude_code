"""
회의 알림(이음 메신저) ↔ WORKS 회의록 연결 (2026-09-15 대표 지시)

대표 지시: 메신저 회의 알림 카드에서 「▶ 회의 시작」을 누르면 WORKS 회의록이 회의 정보로 채워져
녹음이 시작되고, 정리가 끝나면 같은 카드에서 「📋 회의록 보기」.

추가 컬럼 (idempotent · ALTER):
  - meetings.msg_meeting_id : 이음 메신저 회의 id (회의 1건당 회의록 1개 — 부분 유일 인덱스)
  - meetings.msg_started_at : 「회의 시작」을 누른 시각 (카드의 '진행 중' 표기용)
  - meetings.msg_organizer_id : 회의 알림 등록 담당(WORKS users.id) — 녹음 안 해도 회의록 편집 가능(대표 결정 2026-09-15)

⚠ 인덱스는 반드시 ALTER '뒤'에 만든다 — 스키마(executescript)에 넣으면 기존 운영 DB 에서는
  CREATE TABLE IF NOT EXISTS 가 건너뛰어 컬럼이 없는데 인덱스가 먼저 실행돼 앱 기동이 죽는다
  (2026-08-31 메일 sha256 인덱스 38분 전면 다운 교훈). startup()에서 1회 호출.
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
        if "msg_meeting_id" not in mc:
            c.execute("ALTER TABLE meetings ADD COLUMN msg_meeting_id INTEGER")
            added.append("meetings.msg_meeting_id")
        if "msg_started_at" not in mc:
            c.execute("ALTER TABLE meetings ADD COLUMN msg_started_at TEXT")
            added.append("meetings.msg_started_at")
        if "msg_organizer_id" not in mc:   # 등록 담당 — 녹음 안 해도 회의록 편집 가능(대표 결정 2026-09-15)
            c.execute("ALTER TABLE meetings ADD COLUMN msg_organizer_id INTEGER")
            added.append("meetings.msg_organizer_id")
        # 메신저 회의 1건당 회의록 1개 — 연결 없는 일반 회의(NULL)는 여러 개 허용
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_meetings_msg "
                  "ON meetings(msg_meeting_id) WHERE msg_meeting_id IS NOT NULL")
    conn.commit()
    conn.close()
    return {"added": added}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, "..", "..", "data", "knk.db"))
    print(migrate(db))
