"""
🌐 z1199 — 회의록 내용 번역 저장 표 (idempotent · 표만 만든다)

대표 2026-10-28 「베트남직원이 포함된 회의록은 베트남 직원이 봤을때 베트남어로 표현이 되는거야?」 → 시안 → A안 ·
베트남어 참석자가 있으면 정리 직후 미리 번역 · 범위 = 정리·결정·할 일·제목 + 양식·한눈에 보기 (z1200 음성 메모도 같은 표).

content_tr      : 종류(kind: mtg · vn) · 번호(ref_id) · 조각(part: title · summary · dec:N · act:N · viz) · 언어(lang: vi) ·
                  원문 지문(src_sig — 같으면 다시 번역하지 않는다) · 번역(text) · 실패 까닭(fail — 같은 원문으로 다시 부르지 않게) ·
                  모델 · 시각. 같은 (kind, ref_id, part, lang) 은 한 줄.
content_tr_log  : 번역 한 번마다 숫자만(조각 수 · 통과 · 실패 · 토큰 · 초 · 모델) — 비용 실측용.

⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(있으면 건너뜀) · 회의록 글은 건드리지 않는다(표만 더함).
"""
import sqlite3

DDL = [
    """CREATE TABLE IF NOT EXISTS content_tr (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        kind      TEXT NOT NULL,
        ref_id    INTEGER NOT NULL,
        part      TEXT NOT NULL,
        lang      TEXT NOT NULL,
        src_sig   TEXT NOT NULL,
        text      TEXT NOT NULL DEFAULT '',
        fail      TEXT NOT NULL DEFAULT '',
        model     TEXT NOT NULL DEFAULT '',
        at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        UNIQUE(kind, ref_id, part, lang)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_content_tr_ref ON content_tr(kind, ref_id)",
    """CREATE TABLE IF NOT EXISTS content_tr_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        kind       TEXT NOT NULL,
        ref_id     INTEGER NOT NULL,
        why        TEXT NOT NULL DEFAULT '',
        parts      INTEGER NOT NULL DEFAULT 0,
        ok         INTEGER NOT NULL DEFAULT 0,
        fail       INTEGER NOT NULL DEFAULT 0,
        tokens_in  INTEGER NOT NULL DEFAULT 0,
        tokens_out INTEGER NOT NULL DEFAULT 0,
        calls      INTEGER NOT NULL DEFAULT 0,
        secs       REAL NOT NULL DEFAULT 0,
        model      TEXT NOT NULL DEFAULT '',
        error      TEXT NOT NULL DEFAULT '',
        at         TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    )""",
]


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    have = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for q in DDL:
        c.execute(q)
    conn.commit()
    now = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    return {"added": sorted(now - have)}
