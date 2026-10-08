"""
🎤 음성 메모 (2026-10-08 대표 지시) — voice_notes 새 표 (idempotent · CREATE TABLE IF NOT EXISTS)

대표 지시: 「이 녹음파일 올려서 정리하는 걸 지금은 회의록 들어가서 새 회의록을 눌러야만 하는데…
          회의록 말고 **일반적인 의견 내용을 녹음한 걸 정리해주는 것도** 필요해」
대표 결정(2026-10-08):
  · 쓰임새 = 떠오른 생각·지시사항 / 전화 통화·고객 방문 / 현장·설비 메모 / 직원 보고를 말로 (네 가지 모두)
  · 남길 곳 = **새 목록 「🎤 음성 메모」**(회의록과 섞지 않는다)
  · 쓰는 사람 = **전 직원** · 보기 = **내 것만**

🔴 왜 meetings 표에 같이 담지 않았나:
  meetings 는 이음과 얽혀 있다(회의 카드·참석자 동기화·회의 삭제 연동).
  거기에 메모를 섞으면 조회하는 자리마다 「메모는 빼라」 조건을 빠짐없이 넣어야 하고,
  한 군데만 빠져도 사람의 개인 메모가 이음 회의 카드로 새어 나간다.

칸:
  - owner_id   : 만든 사람(users.id) — 보기·고치기·지우기는 이 사람만
  - title      : 제목(비우면 AI 가 지어 준다)
  - body       : 받아쓴 원문(사람이 고칠 수 있다)
  - summary    : AI 정리(요점·할 일) — 사람이 고칠 수 있다
  - audio_path : 올린 녹음 파일 경로(voice_notes/note_{id}/rec_*.m4a)

⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(새 표 하나) · 업무데이터는 건드리지 않는다.
"""
import sqlite3


def _has_table(c, t: str) -> bool:
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone())


SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS voice_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER REFERENCES users(id),
    title       TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    summary     TEXT NOT NULL DEFAULT '',
    audio_path  TEXT NOT NULL DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    updated_at  TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_voice_notes_owner ON voice_notes(owner_id, id DESC);
"""


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    made = []
    if not _has_table(c, "voice_notes"):
        made.append("voice_notes")
    c.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    return {"added": made}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    print(migrate(os.path.join(here, "..", "..", "data", "knk.db")))
