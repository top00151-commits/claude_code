"""
🎤 음성 메모 일시 · 장소 · 참여자 (z1194 · 대표 2026-10-21) — voice_notes 새 칸 3 (idempotent · 칸만)

대표 지시(2026-10-21): 「그리고 정리할때 대화참여자,장소,시간도 기록할수있으면 좋겠어.」
  · 계기 — 대표가 자기 음성 메모 정리 글 맨 위에 「참여자 …」 한 줄을 **손으로** 적어 넣었다(적을 칸이 없어서).
  · 함께 지시 — 「음성메모 정리된걸 … 이미지로 복사해서 붙여 넣을수있게」 → 🖼 이미지 · 📝 파일 · 📋 복사 맨 위에 이 세 줄이 나온다.

칸 (모두 비워도 된다 · 사람이 적은 글 그대로 보여 준다 — 날짜 계산·검색에 쓰지 않는다):
  - meta_when   : 일시(글) — 녹음 파일을 올릴 때 파일 시각·길이로 먼저 채운다(비어 있을 때만 · 사람이 고칠 수 있다)
  - meta_place  : 장소(글)
  - meta_people : 참여자(글) — 바깥 사람(고객·회계사 등)도 적을 수 있게 글로 둔다

🔴 AI 정리 지시문(실증된 프롬프트)은 손대지 않는다 — 이 세 칸은 정리 글 **위에 붙여 보여 주기만** 한다.
⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(칸만 더함) · 업무데이터는 건드리지 않는다.
"""
import sqlite3

_COLS = (
    ("meta_when", "TEXT NOT NULL DEFAULT ''"),
    ("meta_place", "TEXT NOT NULL DEFAULT ''"),
    ("meta_people", "TEXT NOT NULL DEFAULT ''"),
)


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='voice_notes'").fetchone():
            return {"added": [], "skip": "voice_notes 없음"}
        have = {r[1] for r in c.execute("PRAGMA table_info(voice_notes)")}
        added = []
        for name, decl in _COLS:
            if name not in have:
                c.execute("ALTER TABLE voice_notes ADD COLUMN %s %s" % (name, decl))
                added.append("voice_notes." + name)
        conn.commit()
        return {"added": added}
    finally:
        conn.close()


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    print(migrate(os.path.join(here, "..", "..", "data", "knk.db")))
