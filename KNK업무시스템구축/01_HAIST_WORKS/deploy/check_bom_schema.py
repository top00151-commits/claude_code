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
import contextlib
import io
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

# ── 한 칸만 있는 DB (반쪽 마이그레이션 뒤 재기동) ──────────────────
db_half = os.path.join(TMP, "half.db")
ch = sqlite3.connect(db_half)
ch.executescript(OLD_SCHEMA)
ch.execute("ALTER TABLE bom_tool_runs ADD COLUMN has_price INTEGER")
for i in range(4):
    ch.execute("INSERT INTO bom_tool_runs(mgmt_code, step, has_price) VALUES(?,?,?)",
               (f"01{i}M2606", "draft", 1))
ch.commit(); ch.close()
D.DB_PATH = db_half
D.init_db()
ch = sqlite3.connect(db_half)
hcols = [r[1] for r in ch.execute("PRAGMA table_info(bom_tool_runs)")]
hn = ch.execute("SELECT COUNT(*) FROM bom_tool_runs").fetchone()[0]
hkeep = ch.execute("SELECT COUNT(*) FROM bom_tool_runs WHERE has_price=1").fetchone()[0]
check("한 칸만 있던 DB 에 모자란 칸만 추가된다",
      "has_price" in hcols and "has_vendor" in hcols, str(hcols[-3:]))
check("그때도 기존 기록 4건과 값이 보존된다", hn == 4 and hkeep == 4, f"{hn}건 / 값 {hkeep}건")

# ── 표가 없던 DB = **정상 생성** 경로 (실패 사례가 아니다) ──────────
db2 = os.path.join(TMP, "fresh.db")
sqlite3.connect(db2).close()
D.DB_PATH = db2
D.init_db()
con2 = sqlite3.connect(db2)
cols3 = [r[1] for r in con2.execute("PRAGMA table_info(bom_tool_runs)")]
check("표가 없던 DB 에서도 칸이 갖춰진다(정상 생성)",
      "has_price" in cols3 and "has_vendor" in cols3, str(cols3[-3:]))

# ── 🔴 진짜 실패를 일부러 만들어 본다 ──────────────────────────────
#    여기까지 안 하면 "실패를 조용히 넘기지 않는다"는 **한 번도 시험된 적이 없다.**
#    (지적 2026-09-10: 표가 없는 DB 는 정상 생성이지 칼럼 추가 실패가 아니다)
class _FailAlter(sqlite3.Connection):
    """bom_tool_runs 에 칸 추가만 실패시킨다. 다른 표는 그대로 둔다."""

    def execute(self, sql, *a, **k):
        flat = " ".join(str(sql).split()).upper()
        if flat.startswith("ALTER TABLE BOM_TOOL_RUNS ADD COLUMN"):
            raise sqlite3.OperationalError("일부러 실패시킨 칸 추가 (시험)")
        return super().execute(sql, *a, **k)


db3 = os.path.join(TMP, "failadd.db")
cf = sqlite3.connect(db3)
cf.executescript(OLD_SCHEMA)
for i in range(5):
    cf.execute("INSERT INTO bom_tool_runs(mgmt_code, step) VALUES(?,?)", (f"02{i}M2606", "draft"))
cf.commit(); cf.close()

_real_connect = sqlite3.connect


def _connect_failing(*a, **k):
    k["factory"] = _FailAlter
    return _real_connect(*a, **k)


D.DB_PATH = db3
D.sqlite3.connect = _connect_failing
buf = io.StringIO()
alive = False
try:
    with contextlib.redirect_stdout(buf):
        D.init_db()
    alive = True                       # 예외로 멈추지 않고 여기까지 왔다
except Exception as e:
    alive = False
    boom = e
finally:
    D.sqlite3.connect = _real_connect
out = buf.getvalue()

cf = _real_connect(db3)
fcols = [r[1] for r in cf.execute("PRAGMA table_info(bom_tool_runs)")]
fn = cf.execute("SELECT COUNT(*) FROM bom_tool_runs").fetchone()[0]
missing = [x for x in ("has_price", "has_vendor") if x not in fcols]

check("칸 추가가 실패하면 **사유가 기록된다**",
      ("bom_tool_runs" in out and "실패" in out and "OperationalError" in out),
      repr(out[-200:]))
check("실패 기록에 기존 기록 건수가 함께 남는다", "5" in out, repr(out[-200:]))
check("실패했으므로 칸 검증이 **모자람을 돌려준다**", missing == ["has_price", "has_vendor"], str(fcols[-3:]))
check("실패해도 기존 기록 5건은 그대로다", fn == 5, f"{fn}건")
check("실패해도 **기동이 죽지 않는다**(예외가 밖으로 안 나감)",
      alive, "init_db 가 예외를 던졌다" if not alive else "")

# 위 시험이 헛돌지 않는지 — 실패를 안 만들면 칸이 정상 생성돼야 한다
D.DB_PATH = os.path.join(TMP, "control.db")
sqlite3.connect(D.DB_PATH).close()
D.init_db()
cc = sqlite3.connect(D.DB_PATH)
ccols = [r[1] for r in cc.execute("PRAGMA table_info(bom_tool_runs)")]
check("역검사: 실패를 안 만들면 같은 자리에서 칸이 생긴다",
      "has_price" in ccols and "has_vendor" in ccols, str(ccols[-3:]))

print("-" * 70)
print(f"  확인 {CNT}건 / 실패 {len(FAIL)}건" + ("" if not FAIL else " -> " + ", ".join(FAIL)))
sys.exit(1 if FAIL else 0)
