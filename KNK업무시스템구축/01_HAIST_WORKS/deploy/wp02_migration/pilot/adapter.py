# -*- coding: utf-8 -*-
"""WP-02 파일럿 — SQLite·PostgreSQL 양쪽에서 도는 얇은 이식층 (C안 1단계 시제품)

⛔ 운영 코드가 아닙니다. 파일럿 측정 전용이며 앱이 import 하지 않습니다.

목적: "코드 5,600곳을 어떻게 고칠 것인가"를 **가정이 아니라 실물로** 확인한다.
      원본 SQL 문장을 **그대로 두고** 실행 직전에 번역하는 방식이 가능한지,
      그리고 무엇이 자동 번역으로 안 되는지(=사람이 판단해야 하는 곳)를 센다.

방침:
  · 자동 번역 가능한 것 → 어댑터가 처리 (기존 코드 무변경)
  · 자동 번역 불가한 것 → `manual_review` 로 표시해 **사람이 고칠 목록**을 만든다
"""
import re

# ── 자동 번역 규칙 (원본 SQL은 손대지 않는다) ─────────────────────────────
_RE_DATETIME_NOW = re.compile(r"datetime\(\s*'now'\s*,\s*'localtime'\s*\)", re.I)
_RE_DATE_NOW = re.compile(r"date\(\s*'now'\s*,\s*'localtime'\s*\)", re.I)
_RE_DATETIME_NOW2 = re.compile(r"datetime\(\s*'now'\s*\)", re.I)
_RE_STRFTIME = re.compile(r"strftime\(\s*'([^']+)'\s*,\s*([^)]+)\)", re.I)
_RE_LASTROWID = re.compile(r"SELECT\s+last_insert_rowid\(\s*\)", re.I)
_RE_INS_IGNORE = re.compile(r"INSERT\s+OR\s+IGNORE\s+INTO", re.I)
_RE_INS_REPLACE = re.compile(r"INSERT\s+OR\s+REPLACE\s+INTO", re.I)
_RE_IFNULL = re.compile(r"\bIFNULL\s*\(", re.I)
_RE_LIKE = re.compile(r"\bLIKE\b", re.I)

# strftime 형식 → PostgreSQL to_char 형식
_FMT = {"%Y": "YYYY", "%m": "MM", "%d": "DD", "%H": "HH24", "%M": "MI", "%S": "SS", "%y": "YY"}

# 시간대 규정(KNK 시간대 표준 v1) — 날짜 경계는 '입력자 소속' 기준.
# 서버 지역시간에 의존하던 datetime('now','localtime') 을 대체할 때 이 값을 쓴다.
TZ_HQ = "Asia/Seoul"        # 본사 +9
TZ_VN = "Asia/Ho_Chi_Minh"  # 베트남 +7


def to_pg(sql: str, tz: str = TZ_HQ) -> tuple:
    """SQLite 문장을 PostgreSQL 문장으로. (변환된SQL, 적용한규칙목록) 반환."""
    applied = []

    def mark(name):
        applied.append(name)

    if _RE_DATETIME_NOW.search(sql):
        sql = _RE_DATETIME_NOW.sub(f"to_char(now() AT TIME ZONE '{tz}', 'YYYY-MM-DD HH24:MI:SS')", sql)
        mark("datetime('now','localtime')→시간대 명시")
    if _RE_DATE_NOW.search(sql):
        sql = _RE_DATE_NOW.sub(f"to_char(now() AT TIME ZONE '{tz}', 'YYYY-MM-DD')", sql)
        mark("date('now','localtime')→시간대 명시")
    if _RE_DATETIME_NOW2.search(sql):
        sql = _RE_DATETIME_NOW2.sub(f"to_char(now() AT TIME ZONE '{tz}', 'YYYY-MM-DD HH24:MI:SS')", sql)
        mark("datetime('now')→시간대 명시")

    def _sf(m):
        fmt, expr = m.group(1), m.group(2)
        for k, v in _FMT.items():
            fmt = fmt.replace(k, v)
        return f"to_char(({expr})::timestamp, '{fmt}')"

    if _RE_STRFTIME.search(sql):
        sql = _RE_STRFTIME.sub(_sf, sql)
        mark("strftime→to_char")

    if _RE_INS_IGNORE.search(sql):
        sql = _RE_INS_IGNORE.sub("INSERT INTO", sql) + " ON CONFLICT DO NOTHING"
        mark("INSERT OR IGNORE→ON CONFLICT DO NOTHING")
    if _RE_INS_REPLACE.search(sql):
        mark("★INSERT OR REPLACE→사람 판단 필요(어느 키로 충돌 판정할지)")
    if _RE_IFNULL.search(sql):
        sql = _RE_IFNULL.sub("COALESCE(", sql)
        mark("IFNULL→COALESCE")

    # LIKE: SQLite 는 영문 대소문자를 무시, PostgreSQL 은 구분한다.
    # 검색 결과가 달라지는 곳이므로 **자동으로 ILIKE 로 바꾸지 않고** 표시만 한다(사람 판단).
    if _RE_LIKE.search(sql):
        mark("★LIKE — 대소문자 동작 다름(ILIKE 여부 판단 필요)")

    if _RE_LASTROWID.search(sql):
        mark("★last_insert_rowid→RETURNING 으로 구조 변경 필요")

    # 자리표: ? → %s  (문자열 리터럴 안의 ? 는 건드리지 않는다)
    out, in_str, quote = [], False, ""
    for ch in sql:
        if in_str:
            out.append(ch)
            if ch == quote:
                in_str = False
            continue
        if ch in ("'", '"'):
            in_str, quote = True, ch
            out.append(ch)
        elif ch == "?":
            out.append("%s")
        else:
            out.append(ch)
    sql2 = "".join(out)
    if sql2 != sql:
        mark("? → %s")
    return sql2, applied


def manual_review(sql: str) -> list:
    """자동 번역으로 끝나지 않아 **사람이 봐야 하는** 지점만 뽑는다."""
    _, applied = to_pg(sql)
    return [a for a in applied if a.startswith("★")]
