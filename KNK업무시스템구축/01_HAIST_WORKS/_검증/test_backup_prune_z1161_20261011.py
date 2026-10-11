#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1161 시험 — 앱이 뜨는 DB 사본은 기능마다 최근 7개 · 2026-09-02 이전 기록용은 지우지 않는다
(대표 2026-10-11 「사본 쌓임 막기」 · 「최근 7개」 · 「9/2 이전 기록용은 자동으로 지우지 않음」).

  §1 공용 정리 함수 prune_db_backups — 진짜 함수를 임시 폴더에서
  §2 실제 기능 — 초기화(reset_demo_apply)가 사본을 뜨고 정리한다(임시 DB)
  §3 실제 기능 — 04:10 자동 직원 동기화가 공용 함수로 7개를 지킨다(이음은 가짜 · DB 저장 없음)
  §4 실제 기능 — 관리자 「메신저 직원 동기화」 실행(앱 통째)이 사본을 뜨고 정리한다
  §5 원문 — 사본을 뜨는 곳 8곳이 모두 정리를 부른다 · 한 번만 도는 이관은 허용 표시
  §6 배포 전 검사기 + 되돌림 6종

⛔ 운영 DB·운영 사본 폴더를 열지 않는다(임시 폴더만). fastapi 가 깔린 파이썬이 필요하다.
실행:  python _검증/test_backup_prune_z1161_20261011.py
"""
import contextlib
import io
import os
import re
import shutil
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
sys.path.insert(0, os.path.join(ROOT, "deploy"))
os.environ["KNK_SSO_SERVICE_KEY"] = "z1161-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1161_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
BDIR = os.path.join(TMP, "backups")
assert os.path.dirname(BDIR) == os.path.dirname(D.DB_PATH)

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  ✅" if ok else "  ❌") + " %02d %s" % (CNT, name) + ("" if ok else "   ← %s" % (detail,)))
    if not ok:
        FAIL.append(name)


def touch(d, name):
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, name), "w").close()


def names(d, prefix):
    return sorted(f for f in os.listdir(d) if f.startswith(prefix)) if os.path.isdir(d) else []


def fresh(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)


print("§1 공용 정리 함수")
U = os.path.join(TMP, "u1")
fresh(U)
for k in range(1, 11):
    touch(U, "knk.db.bak_resetgrp_202610%02d_120000" % k)
touch(U, "knk.db.bak_resetgrp_20261001_120000-wal")
touch(U, "knk.db.bak_resetgrp_20261001_120000-shm")
touch(U, "knk.db.bak_resetgrp_20260705_224023")            # 9/2 이전 기록용
for k in range(1, 10):
    touch(U, "knk.db.bak_reset_202610%02d_090000" % k)         # 다른 기능(이름이 비슷)
touch(U, "knk.db.bak_resetgrp_memo")                          # 시각 없는 이름
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    gone = D.prune_db_backups(U, "knk.db.bak_resetgrp_")
check("최근 7개만 남기고 가장 오래된 3개를 지움",
      sorted(gone) == ["knk.db.bak_resetgrp_202610%02d_120000" % k for k in (1, 2, 3)], gone)
left = names(U, "knk.db.bak_resetgrp_2026")
check("남은 것 = 10/4~10/10 7개 + 9/2 이전 기록용 1개",
      left == sorted(["knk.db.bak_resetgrp_202610%02d_120000" % k for k in range(4, 11)] + ["knk.db.bak_resetgrp_20260705_224023"]), left)
check("지운 사본의 보조 파일(-wal·-shm)도 함께 지움", not any(f.endswith(("-wal", "-shm")) for f in os.listdir(U)), os.listdir(U))
check("다른 기능(bak_reset_) 9개는 그대로", len(names(U, "knk.db.bak_reset_2")) == 9, names(U, "knk.db.bak_reset_2"))
check("시각 없는 이름은 그대로", os.path.exists(os.path.join(U, "knk.db.bak_resetgrp_memo")))
check("기록 한 줄 「[BACKUP] 사본 정리 …: 3개 지움(최근 7개 유지)」", "[BACKUP] 사본 정리 knk.db.bak_resetgrp_*: 3개 지움(최근 7개 유지)" in buf.getvalue(), buf.getvalue()[:200])
check("한 번 더 돌리면 지울 것 없음", D.prune_db_backups(U, "knk.db.bak_resetgrp_") == [])

R = os.path.join(TMP, "u2")
fresh(R)
tg = ["001T2607", "id1051", "002T2607", "id1094", "004T2510", "id1126", "999M2601", "006T2607", "id1062"]
for k, t in enumerate(tg, 1):
    touch(R, "knk.db.bak_retire_%s_202610%02d_100000" % (t, k))
touch(R, "knk.db.bak_retire_id1094_20260820_125408")          # 9/2 이전 기록용
gone = D.prune_db_backups(R, "knk.db.bak_retire_")
check("폐기 사본은 대상이 달라도 한 기능 — 가장 오래된 2개만 지움",
      sorted(gone) == ["knk.db.bak_retire_001T2607_20261001_100000", "knk.db.bak_retire_id1051_20261002_100000"], gone)
check("폐기 9/2 이전 기록용은 그대로", os.path.exists(os.path.join(R, "knk.db.bak_retire_id1094_20260820_125408")))

S = os.path.join(TMP, "u3")
fresh(S)
for k in range(1, 6):
    touch(S, "knk.db.bak_empsync_202610%02d_080000" % k)
check("7개보다 적으면 아무것도 안 지움", D.prune_db_backups(S, "knk.db.bak_empsync_") == [] and len(os.listdir(S)) == 5)
check("이름 앞부분에 밑줄이 없으면 거절(아무것도 안 지움)", D.prune_db_backups(S, "knk.db.bak_empsync") == [] and len(os.listdir(S)) == 5)
check("남길 수가 0 이하면 거절", D.prune_db_backups(S, "knk.db.bak_empsync_", keep=0) == [] and len(os.listdir(S)) == 5)
try:
    r = D.prune_db_backups(os.path.join(TMP, "없는폴더"), "knk.db.bak_empsync_")
    ok = (r == [])
except Exception as e:
    ok = False
    r = e
check("없는 폴더여도 예외 없이 빈 목록(원래 작업을 막지 않는다)", ok, r)
check("기준값 = 7 · 20260902", D.BACKUP_KEEP_PER_KIND == 7 and D.BACKUP_PRUNE_SINCE == "20260902",
      (D.BACKUP_KEEP_PER_KIND, D.BACKUP_PRUNE_SINCE))

print("§2 실제 기능 — 초기화(reset_demo_apply)")
fresh(BDIR)
for k in range(1, 9):
    touch(BDIR, "knk.db.bak_reset_202610%02d_070000" % k)
touch(BDIR, "knk.db.bak_reset_20260531_120000")                # 9/2 이전
touch(BDIR, "knk.db.bak_resetgrp_20261001_070000")
touch(BDIR, "knk.db.bak_resetgrp_20261002_070000")
with contextlib.redirect_stdout(io.StringIO()):
    res = D.reset_demo_apply("z1161 시험")
check("초기화 성공", bool(res.get("ok")), res)
new_bak = os.path.basename(res.get("backup") or "")
post = [f for f in names(BDIR, "knk.db.bak_reset_") if f >= "knk.db.bak_reset_20260902"]
check("초기화 사본(9/2 이후) 7개", len(post) == 7, post)
check("방금 뜬 사본은 남음", new_bak in post, (new_bak, post))
check("가장 오래된 2개(10/1·10/2) 지워짐", "knk.db.bak_reset_20261001_070000" not in post and "knk.db.bak_reset_20261002_070000" not in post, post)
check("9/2 이전 기록용 그대로", os.path.exists(os.path.join(BDIR, "knk.db.bak_reset_20260531_120000")))
check("다른 기능(그룹 비우기) 사본 그대로", len(names(BDIR, "knk.db.bak_resetgrp_")) == 2)

import app.main as appmain                                 # noqa: E402
from app import sso_client as SC                           # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

print("§3 실제 기능 — 04:10 자동 직원 동기화")
fresh(BDIR)
for k in range(1, 10):
    touch(BDIR, "knk.db.bak_autoempsync_202610%02d_041000" % k)
_real_sync = SC.sync_employees_from_messenger_api
SC.sync_employees_from_messenger_api = lambda c, **kw: {"ok": False, "error": "z1161 시험 — 이음 부르지 않음"}
try:
    with contextlib.redirect_stdout(io.StringIO()):
        appmain._run_directory_autosync()
finally:
    SC.sync_employees_from_messenger_api = _real_sync
auto = names(BDIR, "knk.db.bak_autoempsync_")
check("자동 사본 7개(새 것 1 + 최근 6)", len(auto) == 7, auto)
check("10/1·10/2·10/3 지워짐", not any(("202610%02d" % k) in "".join(auto) for k in (1, 2, 3)), auto)

print("§4 실제 기능 — 관리자 「메신저 직원 동기화」 실행(앱 통째)")
fresh(BDIR)
for k in range(1, 9):
    touch(BDIR, "knk.db.bak_empsync_202610%02d_151244" % k)
touch(BDIR, "knk.db.bak_empsync_20260901_083914")              # 9/2 이전 기록용
with D.db_session() as c:
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version) "
              "VALUES ('가상관리자', 'admin', 'T900', 'T900', 'sso_only_no_local_password', 1, 1)")
    ADMIN = c.execute("SELECT * FROM users WHERE employee_no='T900'").fetchone()
ADMIN = dict(ADMIN)
appmain.get_user = lambda request: ADMIN
SC.sync_employees_from_messenger_api = lambda c, **kw: {"ok": False, "error": "z1161 시험 — 이음 부르지 않음"}
try:
    with contextlib.redirect_stdout(io.StringIO()):
        r = TestClient(appmain.app, follow_redirects=False).post("/admin/sync-employees", data={"confirm": "직원동기화"})
finally:
    SC.sync_employees_from_messenger_api = _real_sync
emp = names(BDIR, "knk.db.bak_empsync_")
emp_post = [f for f in emp if f >= "knk.db.bak_empsync_20260902"]
check("화면 응답 200(동기화 실패 안내라도 화면은 뜸)", r.status_code == 200, r.status_code)
check("수동 동기화 사본(9/2 이후) 7개", len(emp_post) == 7, emp_post)
check("9/2 이전 기록용 그대로", "knk.db.bak_empsync_20260901_083914" in emp, emp)

print("§5 원문 — 사본을 뜨는 곳 8곳")
srcM = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
srcD = io.open(os.path.join(ROOT, "app", "database.py"), encoding="utf-8").read()
for kind, src, where in [("resetgrp", srcD, "그룹 비우기"), ("co_reset", srcD, "소모품 전체 초기화"),
                         ("resetdiv", srcD, "사업부 초기화"), ("reset", srcD, "데모 초기화"),
                         ("autoempsync", srcM, "04:10 자동 동기화"), ("empsync", srcM, "수동 직원 동기화"),
                         ("sobackfill", srcM, "SO 보정"), ("retire", srcM, "폐기")]:
    check("%s 가 정리를 부른다(\"knk.db.bak_%s_\")" % (where, kind),
          re.search(r'prune(?:_db_backups|_bak)\([^)]*"knk\.db\.bak_%s_"' % re.escape(kind), src) is not None)
check("한 번만 도는 이관(상호 중복 해제) 사본은 허용 표시", re.search(r"knk\.db\.bak_custuniq_.*z1161-허용", srcD) is not None)
check("main.py 에 손으로 돌며 지우는 코드 없음", 'startswith("knk.db.bak_' not in srcM)

print("§6 배포 전 검사기 + 되돌림")
import check_standards as CS                               # noqa: E402
now_bad = CS.check_backup_prune([])
check("지금 코드: 위반 0", now_bad == [], now_bad[:3])
_root = CS.ROOT
MUT = [
    ("app/database.py", '    prune_db_backups(bdir, "knk.db.bak_resetgrp_")', "    pass  # 되돌림", "①", "그룹 비우기 정리 호출을 뺌"),
    ("app/main.py", "    _logi.prune_db_backups(_bdir, \"knk.db.bak_retire_\")", "    pass  # 되돌림", "①", "폐기 정리 호출을 뺌"),
    ("app/main.py", "\ndef _run_directory_autosync():", "\ndef _z1161_mut(ts=0):\n    return f\"knk.db.bak_newfeat_{ts}\"\n\n\ndef _run_directory_autosync():", "①", "새 사본 기능을 정리 없이 더함"),
    ("app/database.py", " · z1161-허용: 한 번만 도는 이관(상호 중복 해제)의 사본 — 개수 정리 대상 아님", "", "①", "1회성 이관의 허용 표시를 지움"),
    ("app/main.py", '        _prune_bak(bdir, "knk.db.bak_autoempsync_")',
     '        _fs = sorted(f for f in _os.listdir(bdir) if f.startswith("knk.db.bak_autoempsync_"))\n        _prune_bak(bdir, "knk.db.bak_autoempsync_")', "②", "손으로 돌며 지우는 코드를 되살림"),
    ("app/database.py", "BACKUP_KEEP_PER_KIND = 7", "BACKUP_KEEP_PER_KIND = 5", "③", "남길 개수를 5 로"),
    ("app/database.py", "if not m or m.group(1) < BACKUP_PRUNE_SINCE:", "if not m:", "④", "9/2 이전 기록용도 지우게 함"),
]
for rel, old, new, mark, what in MUT:
    tmp = tempfile.mkdtemp(prefix="mut_z1161_")
    try:
        os.makedirs(os.path.join(tmp, "app"))
        for f in os.listdir(os.path.join(ROOT, "app")):
            if f.endswith(".py"):
                shutil.copyfile(os.path.join(ROOT, "app", f), os.path.join(tmp, "app", f))
        p = os.path.join(tmp, rel)
        s = io.open(p, encoding="utf-8", newline="").read()
        nl = "\r\n" if "\r\n" in s else "\n"
        s2 = s.replace("\r\n", "\n")
        assert s2.count(old) == 1, (rel, old[:40], s2.count(old))
        s2 = s2.replace(old, new)
        io.open(p, "w", encoding="utf-8", newline="").write(s2.replace("\n", nl))
        CS.ROOT = tmp
        got = CS.check_backup_prune([])
    finally:
        CS.ROOT = _root
        shutil.rmtree(tmp, ignore_errors=True)
    check("되돌림 「%s」 → %s 로 잡힘" % (what, mark), any(m_.startswith(mark) for _f, _l, m_ in got), [x[2][:60] for x in got][:3])

print("")
print("결과: %d개 중 실패 %d" % (CNT, len(FAIL)))
for f in FAIL:
    print("   ❌", f)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
