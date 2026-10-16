"""
🗂 z1185 — 회의록 「사람이 원문을 쓰거나 고친 시각」 칸 (idempotent · 칸만 더한다)

대표 2026-10-16 (세션 10 전달 · 사진): 「회의록이 녹음 원문 또는 수기 작성이 되지 않았을때는 회의록보기 아이콘은
비활성화가 되어야함.. 회의록보기 아이콘은 회의록이 작성되었을때만 활성화하는게 맞음.」
  · 이음 「▶ 회의 시작」으로 만든 회의록은 원문 = 이음 회의 메모(씨앗)로 시작한다. 메모만 있는 채로 정리를 누르면
    회의 내용 없는 정리가 생기고, 그것이 「정리 끝」(이음 「📋 회의록 보기」·「회의록 등록」 알림)이 됐다(운영 3건).
  · 「사람이 이음웍스에서 원문을 쓰거나 고쳤다」를 가리려면 그 시각이 있어야 한다 → 이 칸.

칸 (TEXT · 빈 글이 기본 — 기존 행은 「고친 적 없음」으로 시작 · 앞으로 저장할 때부터 적힌다):
  meetings : body_edited_at(사람이 이음웍스에서 원문을 쓰거나 고친 시각)

⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(칸이 이미 있으면 건너뜀) · 업무데이터는 건드리지 않는다(ALTER 만).
"""
import sqlite3

COLS = {
    "meetings": [("body_edited_at", "TEXT NOT NULL DEFAULT ''")],
}


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


if __name__ == "__main__":
    import os
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "knk.db")
    print(migrate(p))
