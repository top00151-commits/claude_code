"""
v5H226z412 (2026-06-14) — KNK Meeting (회의록) Phase 1: 모드 A 텍스트 회의

(z410=빅터 AI 자연어 인식, z411=직원 업무패턴 으로 같은 날 선점됨 → 회의록은 z412 로 분리)

프로젝트: 16_KNK_Meeting — 회의 3 모드(텍스트·음성·통역) 통합 도구.
  · 이번 차수는 모드 A(텍스트 회의)만. 음성/통역(모드 B·C)은 Phase 2~3로 미룸.
  · 핵심 가치 루프: 회의 원문 텍스트 입력 → AI 결정사항·할 일·요약 추출
    → 사용자 검토 후 1-클릭으로 일일업무카드(tasks) 연동.

DB 신규 테이블 4종 (idempotent — CREATE TABLE IF NOT EXISTS):
  - meetings           : 회의 헤더(제목·날짜·참석자텍스트·원문·요약·공개범위)
  - meeting_decisions  : 결정사항 (누가/무엇을/언제까지) — AI 추출 또는 수기
  - meeting_actions    : 할 일 (담당·내용·기한·일일카드 연동상태)
  - meeting_attendees  : 참석자 (사용자 연결, 선택)

공개범위(visibility) — 절대준수 제약2(권한 분기):
  · 'team'    : 작성자 소속팀 + 참석자 + leader/executive/ceo/admin  (기본값)
  · 'private' : 작성자 + 참석자만 (임원·민감 회의)
  · 'all'     : 전 직원
권한 판정은 main.py _can_view_meeting() 에서 수행. visibility 는 생성 시 지정.

음성/통역 확장 대비: meetings.mode 컬럼('A'/'B'/'C')과 audio_path(nullable)를
지금 만들어 두어 Phase 2에서 ALTER 없이 바로 쓸 수 있게 한다.
"""

import sqlite3
import os


def _has_table(c, table: str) -> bool:
    r = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return bool(r)


SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS meetings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT NOT NULL,
    meeting_date   TEXT NOT NULL,
    mode           TEXT NOT NULL DEFAULT 'A',          -- A 텍스트 / B 음성 / C 통역 (Phase 2~3)
    team_id        INTEGER REFERENCES teams(id),
    owner_id       INTEGER REFERENCES users(id),
    location       TEXT DEFAULT '',
    tags           TEXT DEFAULT '',
    attendees_text TEXT DEFAULT '',                    -- 자유 입력 참석자(쉼표 구분)
    body           TEXT DEFAULT '',                    -- 회의 원문 텍스트(모드 A) / STT 결과(모드 B·C)
    summary        TEXT DEFAULT '',                    -- AI 한 줄/불릿 요약
    audio_path     TEXT DEFAULT '',                    -- 모드 B·C 음성 파일 경로(Phase 2)
    visibility     TEXT NOT NULL DEFAULT 'team',       -- team / private / all
    status         TEXT NOT NULL DEFAULT 'draft',      -- draft / done
    created_at     TEXT DEFAULT (datetime('now','localtime')),
    updated_at     TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS meeting_decisions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id     INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    who            TEXT DEFAULT '',
    what           TEXT NOT NULL,
    due            TEXT DEFAULT '',
    source         TEXT NOT NULL DEFAULT 'ai',         -- ai / manual
    created_at     TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS meeting_actions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id        INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    assignee_name     TEXT DEFAULT '',
    assignee_user_id  INTEGER REFERENCES users(id),    -- 이름이 사번부서 단일후보로 매칭될 때만(데이터 연결 안전)
    task              TEXT NOT NULL,
    due_date          TEXT DEFAULT '',
    source            TEXT NOT NULL DEFAULT 'ai',       -- ai / manual
    linked_task_id    INTEGER REFERENCES tasks(id),     -- 일일카드 연동 시 채워짐(중복등록 방지)
    status            TEXT NOT NULL DEFAULT 'open',      -- open / linked
    created_at        TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS meeting_attendees (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id     INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_id        INTEGER REFERENCES users(id),
    name           TEXT DEFAULT '',
    created_at     TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS ix_meetings_date     ON meetings(meeting_date);
CREATE INDEX IF NOT EXISTS ix_meetings_owner    ON meetings(owner_id);
CREATE INDEX IF NOT EXISTS ix_meetings_team     ON meetings(team_id);
CREATE INDEX IF NOT EXISTS ix_mdec_meeting      ON meeting_decisions(meeting_id);
CREATE INDEX IF NOT EXISTS ix_mact_meeting      ON meeting_actions(meeting_id);
CREATE INDEX IF NOT EXISTS ix_matt_meeting      ON meeting_attendees(meeting_id);
"""


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    before = [t for t in ("meetings", "meeting_decisions", "meeting_actions",
                          "meeting_attendees") if _has_table(c, t)]

    for stmt in SCHEMA_SQL.split(";"):
        if stmt.strip():
            c.execute(stmt)

    conn.commit()

    after = [t for t in ("meetings", "meeting_decisions", "meeting_actions",
                         "meeting_attendees") if _has_table(c, t)]
    conn.close()

    created = [t for t in after if t not in before]
    return {"created": created}


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, "..", "..", "data", "knk.db"))
    print(migrate(db))
