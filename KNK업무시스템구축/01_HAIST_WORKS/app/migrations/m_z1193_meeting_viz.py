"""
📊 z1193 — 회의록 「한눈에 보기」(도식화) 그림 자료 칸 (idempotent · 칸만 더한다)

대표 2026-10-20: 「이런 회의에 내용을 만약 이미지로 설명할수있으면 정말 좋을것 같아... 회의 내용을 이미지화 또는 도식화해서
더 쉽게 이해할수있는 페이지를 추가해봤으면 좋겠다」 · 「기존에 글로된 회의록 정리는 그대로 하고 지금하는건 추가로 적용해야해」
  · 빅터AI 가 정리(안건·결정·할 일)와 원문에서 **그림 자료**(종류 · 숫자 · 설비 흐름 · 정한 것 · 확인 필요 · 할 일 · 일정 · 지정 부품 ·
    항목마다 원문 근거 구절)를 JSON 으로 뽑고, 화면(meeting_viz.html)이 그린다. 글 정리는 손대지 않는다.

칸 (TEXT · 빈 글이 기본 — 기존 회의는 「그림 없음」으로 시작 · 「📊 그림 만들기」를 누르면 채워진다):
  meetings : viz_json(그림 자료 JSON) · viz_at(만든 시각) · viz_kind(회의 종류 equip|sales|internal) ·
             viz_sum_sig(그림을 만들 때의 정리 글 지문 — 정리가 바뀌면 「다시 그리기」 안내)

⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(칸이 이미 있으면 건너뜀) · 업무데이터는 건드리지 않는다(ALTER 만).
"""
import sqlite3

COLS = {
    "meetings": [("viz_json", "TEXT NOT NULL DEFAULT ''"), ("viz_at", "TEXT NOT NULL DEFAULT ''"),
                 ("viz_kind", "TEXT NOT NULL DEFAULT ''"), ("viz_sum_sig", "TEXT NOT NULL DEFAULT ''")],
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
