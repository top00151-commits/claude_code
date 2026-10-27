"""
🗣 z1196 — 통역 대조 칸 (idempotent · 칸만 더한다)

대표 2026-10-27: 「통역이 제대로 통역을 했을까?」 → 베트남 회의 녹음 37분을 화자 구분 받아쓰기 + 빅터AI 독립 번역으로 대조한 엑셀 →
화면 시안 → 「음성 메모 + 회의록 둘 다 · 대표·임원만 · 사람이 단추 눌러야 · 이대로 만들어 회귀 통과하면 올리기」.
  · 📊 한눈에 보기(z1193)처럼 **추가 화면** — 받아쓴 글·정리는 손대지 않는다.

칸 (TEXT · 빈 글이 기본 — 기존 메모·회의는 「대조 없음」으로 시작 · 「🗣 통역 대조 만들기」를 누르면 채워진다):
  voice_notes · meetings :
    interp_json(대조표 JSON) · interp_at(만든 시각) · interp_prev(이전 대조표 — 「↩ 이전 대조」) · interp_prev_at ·
    interp_state(''|running|done|error — 서버가 다시 켜져 끊긴 일을 알아보려고 DB 에도 적는다) · interp_error(실패 까닭 · 사람말) ·
    interp_usage(쓴 토큰 JSON · 비용 기록)

⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(칸이 이미 있으면 건너뜀) · 업무데이터는 건드리지 않는다(ALTER 만).
"""
import sqlite3

_COLS = [("interp_json", "TEXT NOT NULL DEFAULT ''"), ("interp_at", "TEXT NOT NULL DEFAULT ''"),
         ("interp_prev", "TEXT NOT NULL DEFAULT ''"), ("interp_prev_at", "TEXT NOT NULL DEFAULT ''"),
         ("interp_state", "TEXT NOT NULL DEFAULT ''"), ("interp_error", "TEXT NOT NULL DEFAULT ''"),
         ("interp_usage", "TEXT NOT NULL DEFAULT ''")]
COLS = {"voice_notes": list(_COLS), "meetings": list(_COLS)}


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
    here = os.path.dirname(os.path.abspath(__file__))
    print(migrate(os.path.join(here, "..", "..", "data", "knk.db")))
