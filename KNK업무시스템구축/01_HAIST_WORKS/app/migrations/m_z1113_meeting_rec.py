"""
녹음 중 서버 저장 (2026-09-18 대표 지시) — meetings.rec_state · rec_json (idempotent · ALTER)

대표 신고: 회의 녹음 중 휴대폰으로 다른 앱을 쓰다 창이 닫히면 그때까지 녹음한 것이 전부 사라지고,
          돌아갈 화면이 없어 「회의 종료」조차 누를 수 없었다(증상=창이 닫혀 있었음).
고침: 녹음하는 동안 조각을 서버 파일에 이어 붙이고, 그 상태를 아래 두 칸에 적는다.
  - meetings.rec_state : '' | 'recording'   (목록·상세의 「🔴 녹음 중」 표시)
  - meetings.rec_json  : {session, part, seq, bytes, secs, by, by_name, started_at, last_at, pending[]}
                         pending[] = 아직 글자로 안 바꾼 녹음 파일들(순서 보존)

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
        if "rec_state" not in mc:
            c.execute("ALTER TABLE meetings ADD COLUMN rec_state TEXT DEFAULT ''")
            added.append("meetings.rec_state")
        if "rec_json" not in mc:
            c.execute("ALTER TABLE meetings ADD COLUMN rec_json TEXT DEFAULT ''")
            added.append("meetings.rec_json")
    conn.commit()
    conn.close()
    return {"added": added}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, "..", "..", "data", "knk.db"))
    print(migrate(db))
