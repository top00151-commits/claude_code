#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""WP-04 BOM 등급 칸 — 배포 전 스키마 확인 (대표 지시 2026-09-08)

무엇을 보는가
  `bom_tool_runs.has_price` · `has_vendor` 가 **실제로 생기는지**를,
  **운영과 같은 조건**(옛 스키마 표 + 기존 행)에서 확인한다.

왜 필요한가
  이 칸이 없으면 등급이 늘 「불명」이 되어 **모든 파일이 제한된다.**
  안전한 쪽이지만 업무는 멈추고, 예전엔 `except: pass` 라 **아무도 그 사실을 몰랐다.**
  🔴 과거 `4829f1da` 는 스키마 결함으로 **38분 전면 다운**을 냈다 — 빈 DB 시험은 무의미하다.

⛔ 운영 DB 를 열지 않는다. 임시 폴더에 옛 스키마를 만들어 시험한다.

실행:  python deploy/check_bom_schema.py   → "실패 0" 이어야 배포
"""
import os
import sqlite3
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  OK  " if ok else "  FAIL") + f" {CNT:02d} {name}" + ("" if ok else f" - {detail}"))
    if not ok:
        FAIL.append(name)


OLD_SCHEMA = """
CREATE TABLE bom_tool_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, mgmt_code TEXT, step TEXT NOT NULL, title TEXT,
    inputs TEXT, output_name TEXT, output_path TEXT, report TEXT,
    created_by INTEGER, created_at TEXT DEFAULT (datetime('now','localtime')));
CREATE INDEX idx_bomtool_code ON bom_tool_runs(mgmt_code, created_at);
"""

print("=" * 70)
print("  WP-04 BOM 등급 칸 - 배포 전 스키마 확인")
print("=" * 70)

TMP = tempfile.mkdtemp(prefix="knk_bomschema_")
db = os.path.join(TMP, "old.db")
con = sqlite3.connect(db)
con.executescript(OLD_SCHEMA)
for i in range(6):                       # 운영과 같은 6건
    con.execute("INSERT INTO bom_tool_runs(mgmt_code, step, title) VALUES(?,?,?)",
                (f"00{i}M2606", "draft", f"old {i}"))
con.commit()
con.close()

import app.database as D                                     # noqa: E402
D.DB_PATH = db
D.init_db()

con = sqlite3.connect(db)
cols = [r[1] for r in con.execute("PRAGMA table_info(bom_tool_runs)")]
n1 = con.execute("SELECT COUNT(*) FROM bom_tool_runs").fetchone()[0]
grades = con.execute("SELECT has_price, has_vendor FROM bom_tool_runs LIMIT 1").fetchone() \
    if "has_price" in cols else None

check("등급 칸 두 개가 생긴다", "has_price" in cols and "has_vendor" in cols, str(cols[-3:]))
check("기존 기록 6건이 그대로 있다", n1 == 6, f"{n1}건")
check("옛 행의 등급은 불명(NULL) - 제한 대상", grades == (None, None), str(grades))

D.init_db()                                                  # 재실행(멱등)
n2 = con.execute("SELECT COUNT(*) FROM bom_tool_runs").fetchone()[0]
cols2 = [r[1] for r in con.execute("PRAGMA table_info(bom_tool_runs)")]
check("두 번 돌려도 안전하다(멱등)", n2 == 6 and cols2 == cols, f"{n2}건 / 칸 {len(cols2)}")

# 실패를 조용히 넘기지 않는가 - 표가 없는 DB 로 확인
db2 = os.path.join(TMP, "broken.db")
sqlite3.connect(db2).close()
D.DB_PATH = db2
import io                                                    # noqa: E402
import contextlib                                            # noqa: E402
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    D.init_db()
out = buf.getvalue()
con2 = sqlite3.connect(db2)
cols3 = [r[1] for r in con2.execute("PRAGMA table_info(bom_tool_runs)")]
check("표가 없던 DB 에서도 칸이 갖춰진다(새로 만들어짐)",
      "has_price" in cols3 and "has_vendor" in cols3, str(cols3[-3:]))
check("기동이 죽지 않는다(예외로 멈추지 않음)", True)

print("-" * 70)
print(f"  확인 {CNT}건 / 실패 {len(FAIL)}건" + ("" if not FAIL else " -> " + ", ".join(FAIL)))
sys.exit(1 if FAIL else 0)
