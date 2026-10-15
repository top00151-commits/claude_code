"""
🗂 z1183 — 회의록·음성 메모 「이전 정리 보관」 + 「사람이 고친 표시」 칸 (idempotent · 칸만 더한다)

대표 2026-10-15 정리 품질 기준 「7. 사용자가 수정한 회의록을 재생성 과정에서 임의로 덮어쓰지 않는가?」
대표 확인: 「확인 + 이전 정리 보관」 — 고친 적이 있으면 다시 정리 전에 묻고, 덮어쓰면 이전 정리를 보관해 되돌린다.
  · 전에는 「✏ 고치기」로 고친 정리도 「🔄 다시 정리」·새 녹음 자동 정리가 **확인 없이 덮어썼다**
    (같은 화면을 띄운 채 고쳤을 때만 화면이 물었다).

칸 (모두 TEXT · 빈 글이 기본 — 기존 행은 「이전 정리 없음 · 고친 적 없음」으로 시작):
  meetings    : summary_prev(이전 정리 글) · summary_prev_items(그때의 AI 결정·할 일 JSON) ·
                summary_prev_at(보관 시각) · summary_edited_at(사람이 고친 시각 · 새 AI 정리 때 비움)
  voice_notes : summary_prev · summary_prev_at · summary_edited_at

⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(칸이 이미 있으면 건너뜀) · 업무데이터는 건드리지 않는다(ALTER 만).
"""
import sqlite3

COLS = {
    "meetings": [("summary_prev", "TEXT NOT NULL DEFAULT ''"),
                 ("summary_prev_items", "TEXT NOT NULL DEFAULT ''"),
                 ("summary_prev_at", "TEXT NOT NULL DEFAULT ''"),
                 ("summary_edited_at", "TEXT NOT NULL DEFAULT ''")],
    "voice_notes": [("summary_prev", "TEXT NOT NULL DEFAULT ''"),
                    ("summary_prev_at", "TEXT NOT NULL DEFAULT ''"),
                    ("summary_edited_at", "TEXT NOT NULL DEFAULT ''")],
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
