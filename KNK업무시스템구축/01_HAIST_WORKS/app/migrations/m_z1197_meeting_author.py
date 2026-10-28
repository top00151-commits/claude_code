"""
✍ z1197 — 회의록 「작성자」 표시용 칸 + 녹음 올린 사람 (idempotent · 칸만 더한다)

대표 2026-10-28(세션 10 전달문): 「회의작성자는 기본적으로 녹음 파일을 올린 사람으로 우선하고 이 작성자를 수정할수있게도 해줘.
(수정은 녹음파일 올리는 사람이 할수있게)」 → 대표 결정 10-28 「표시용 칸 새로」(권한 칸 owner_id 는 그대로).

칸 (meetings):
  author_id      INTEGER  — 보이는 「작성자」(양식 「부서/작성자」 · 상세 · 목록 ✍ · 찾기). NULL 이면 owner_id(만든 사람) 그대로 = 지금과 같음.
  author_set_by  INTEGER  — 사람이 손으로 정했으면 그 사람 번호(NULL = 자동: 녹음이 올라올 때마다 올린 사람으로).
  author_set_at  TEXT     — 손으로 정한 시각.
  audio_by       INTEGER  — 마지막으로 녹음 파일을 올린 사람(📁 올리기·다시 올리기 · 공유로 붙이기 · 폰 자동 녹음 끝).
  audio_by_at    TEXT

⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(칸이 이미 있으면 건너뜀) · 업무데이터는 건드리지 않는다(ALTER 만 · 기존 회의록은 author NULL = 만든 사람 표시 그대로).
⚠ 권한 판정(보기·고치기·삭제·종료)은 이 칸을 보지 않는다 — owner_id 그대로.
"""
import sqlite3

COLS = {"meetings": [("author_id", "INTEGER"), ("author_set_by", "INTEGER"), ("author_set_at", "TEXT NOT NULL DEFAULT ''"),
                     ("audio_by", "INTEGER"), ("audio_by_at", "TEXT NOT NULL DEFAULT ''")]}


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    added = []
    for t, cols in COLS.items():
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone():
            continue
        have = {r[1] for r in c.execute("PRAGMA table_info(%s)" % t)}
        for name, decl in cols:
            if name not in have:
                c.execute("ALTER TABLE %s ADD COLUMN %s %s" % (t, name, decl))
                added.append("%s.%s" % (t, name))
    conn.commit()
    conn.close()
    return {"added": added}
