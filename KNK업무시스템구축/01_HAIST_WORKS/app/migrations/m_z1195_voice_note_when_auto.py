"""
🎤 음성 메모 「📁 녹음 다시 올리기」 (z1195 · 대표 2026-10-21) — voice_notes 새 칸 1 (idempotent · 칸만)

대표 지시(2026-10-21): 「그리고 음성메모 녹음파일을 한번 잘 못 올리면 수정할 방법이 없어... 파일 다시 올리기 기능이 필요해.」
대표 선택: 「이대로 만들기」 — 받아쓴 원문은 새 녹음으로 바꾸고 · 정리는 새로(지금 정리는 「↩ 이전 정리」) ·
          **자동으로 채운 일시만** 새 녹음 기준으로 다시(사람이 적은 일시·제목은 그대로) · 먼저 올린 녹음 파일은 서버에 남김

칸:
  - meta_when_auto : 서버가 녹음 파일로 **자동으로 채운** 일시 글(z1194 `_vn_when_from_file`) 그대로.
                     지금 일시(meta_when)가 이것과 같으면 「사람이 손대지 않은 자동 일시」 → 다시 올리기 때 새 녹음 기준으로 바꾼다.
                     다르면(사람이 고쳐 적음) 그대로 둔다. 🔵 이 칸이 생기기 전에 자동으로 채운 일시는 빈 글 → 사람이 적은 것으로 보고 그대로 둔다.

⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(칸만 더함) · 업무데이터는 건드리지 않는다.
"""
import sqlite3


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='voice_notes'").fetchone():
            return {"added": [], "skip": "voice_notes 없음"}
        have = {r[1] for r in c.execute("PRAGMA table_info(voice_notes)")}
        added = []
        if "meta_when_auto" not in have:
            c.execute("ALTER TABLE voice_notes ADD COLUMN meta_when_auto TEXT NOT NULL DEFAULT ''")
            added.append("voice_notes.meta_when_auto")
        conn.commit()
        return {"added": added}
    finally:
        conn.close()


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    print(migrate(os.path.join(here, "..", "..", "data", "knk.db")))
