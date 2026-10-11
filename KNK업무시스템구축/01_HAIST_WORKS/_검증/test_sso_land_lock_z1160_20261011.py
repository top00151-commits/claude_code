#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1160 시험 — 로그인 들어오는 길(/sso/land)의 계정 저장이 DB 잠김일 때.

운영 기록(2026-09-14 · 10-02): 입장 때 계정 저장(upsert_user_from_payload)이
「sqlite3.OperationalError: database is locked」로 끝나 **500** 이 됐다(9/8~10/11 로그인 약 290번 중 1번).
다른 쓰기가 DB 를 busy_timeout(5초) 넘게 잡고 있으면 생긴다.

  §1 평소(잠김 없음) — 있는 직원은 정보가 갱신되고 · 처음 온 사람은 만들어지고 · 둘 다 /home 으로
  §2 **진짜 잠김**(다른 연결이 BEGIN IMMEDIATE 로 쓰기를 잡음) — 있는 재직 직원은 갱신 없이 입장(500 아님)
  §3 **진짜 잠김** — 처음 온 사람은 세 번 해 보고 안내 화면(500 아님)
  §4 잠김을 흉내 — 두 번 잠기고 세 번째에 풀리면 입장 · 기다림 0.5초→1.0초
  §5 퇴사(비활성) 직원·봇 계정은 잠김 때 들여보내지 않는다
  §6 잠김이 **아닌** DB 오류는 숨기지 않는다(그대로 500)
  §7 원문 — /sso/land 가 저장을 도우미(_sso_land_upsert) 한 곳으로만 한다

⛔ 운영 DB·운영 이음을 열지 않는다(임시 DB · 입장 토큰은 가짜). 실명 없음.
   fastapi 가 깔린 파이썬이 필요하다.   실행:  python _검증/test_sso_land_lock_z1160_20261011.py
"""
import base64
import json
import os
import re
import sqlite3
import sys
import tempfile
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1160_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
D.init_db()
with D.db_session() as conn:   # 운영 users 엔 있는데 코드가 안 만드는 칸 — 운영과 같은 모양으로
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))

import app.main as appmain                                 # noqa: E402
from app import sso_client as SC                           # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  ✅" if ok else "  ❌") + " %02d %s" % (CNT, name) + ("" if ok else "   ← %s" % (detail,)))
    if not ok:
        FAIL.append(name)


PAY = {}
SC.verify_token = lambda t: PAY.get(t)          # sso_land 는 부를 때마다 sso_client 에서 가져온다
_REAL_UPSERT = SC.upsert_user_from_payload


def pay(emp, name, **kw):
    p = {"sub": emp, "employee_no": emp, "name_kr": name, "dept": "01_KOR/01", "entity": "KOR",
         "works_access": True, "is_admin": False, "pwv": 1}
    p.update(kw)
    return p


def add_user(emp, name, active=1):
    with D.db_session() as c:
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version) "
                  "VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', ?, 1)",   # 저장 함수와 같은 모양
                  (name, emp, emp, active))
        return c.execute("SELECT id FROM users WHERE employee_no=?", (emp,)).fetchone()["id"]


def user_row(emp):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM users WHERE employee_no=?", (emp,)).fetchone()
    return dict(r) if r else None


def session_uid(resp):
    """응답이 심은 세션 쿠키에서 user_id 를 꺼낸다(서명은 안 본다 · 값만)."""
    for k, v in resp.headers.items():
        if k.lower() != "set-cookie":
            continue
        m = re.match(r"\s*([^=]+)=([^;]+)", v)
        if not m:
            continue
        raw = m.group(2).strip('"').split(".")[0]
        try:
            data = json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
        except Exception:
            continue
        if isinstance(data, dict) and "user_id" in data:
            return data["user_id"]
    return None


def land(token, client=None):
    cl = client or TestClient(appmain.app, follow_redirects=False, raise_server_exceptions=False)
    t0 = time.time()
    r = cl.get("/sso/land", params={"token": token})
    return r, time.time() - t0


class Blocker:
    """다른 연결이 쓰기 잠금을 잡고 있는 상태(운영의 「긴 쓰기」 흉내) — 임시 DB 에만."""

    def __enter__(self):
        self.c = sqlite3.connect(D.DB_PATH, timeout=1, isolation_level=None)
        self.c.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(self, *a):
        self.c.execute("ROLLBACK")
        self.c.close()


print("§1 평소(잠김 없음)")
uid_a = add_user("T001", "가상직원A")
PAY["tA"] = pay("T001", "가상직원A새이름")
r, sec = land("tA")
check("있는 직원 → 303 /home", r.status_code == 303 and r.headers.get("location") == "/home", (r.status_code, r.headers.get("location")))
check("세션에 그 직원 id", session_uid(r) == uid_a, session_uid(r))
check("정보 갱신됨(이름)", (user_row("T001") or {}).get("name") == "가상직원A새이름", user_row("T001"))
PAY["tN"] = pay("T002", "가상신입B")
r, sec = land("tN")
check("처음 온 사람 → 만들어지고 303 /home", r.status_code == 303 and user_row("T002") is not None, (r.status_code, user_row("T002")))
check("세션에 새 id", session_uid(r) == (user_row("T002") or {}).get("id"), session_uid(r))

print("§2 진짜 잠김 — 있는 재직 직원")
PAY["tA2"] = pay("T001", "잠김중바꾼이름")
with Blocker():
    r, sec = land("tA2")
check("500 이 아니라 303 /home", r.status_code == 303 and r.headers.get("location") == "/home", (r.status_code, r.text[:200]))
check("세션에 그 직원 id", session_uid(r) == uid_a, session_uid(r))
check("잠김이라 정보는 갱신 안 됨(새벽 동기화 몫)", (user_row("T001") or {}).get("name") == "가상직원A새이름", user_row("T001"))
check("기다린 시간 = 한 번의 busy_timeout 남짓(4~9초)", 4.0 <= sec <= 9.0, "%.1f초" % sec)

print("§3 진짜 잠김 — 처음 온 사람")
PAY["tC"] = pay("T003", "가상신입C")
with Blocker():
    r, sec = land("tC")
check("500 이 아니라 안내 화면(200)", r.status_code == 200, (r.status_code, r.text[:200]))
check("안내 문구 「잠시 저장이 밀려」", "잠시 저장이 밀려" in r.text, r.text[:300])
check("사람은 안 만들어짐", user_row("T003") is None, user_row("T003"))
check("세션 없음", session_uid(r) is None, session_uid(r))
check("세 번 해 봄(약 15초 + 쉼 1.5초)", 14.0 <= sec <= 24.0, "%.1f초" % sec)
r, sec = land("tC")
check("잠김이 풀린 뒤 다시 열면 → 만들어지고 303", r.status_code == 303 and user_row("T003") is not None, (r.status_code, user_row("T003")))

print("§4 잠김 흉내 — 두 번 잠기고 세 번째에 풀림 · 기다림")
_calls, _sleeps = {"n": 0}, []
_real_sleep = time.sleep


def flaky(c, payload, *a, **kw):
    _calls["n"] += 1
    if _calls["n"] <= 2:
        raise sqlite3.OperationalError("database is locked")
    return _REAL_UPSERT(c, payload, *a, **kw)


SC.upsert_user_from_payload = flaky
time.sleep = lambda s: _sleeps.append(s)
PAY["tD"] = pay("T004", "가상신입D")
try:
    r, sec = land("tD")
finally:
    time.sleep = _real_sleep
    SC.upsert_user_from_payload = _REAL_UPSERT
check("세 번째에 저장 → 303", r.status_code == 303 and user_row("T004") is not None, (r.status_code, user_row("T004")))
check("저장 시도 3번", _calls["n"] == 3, _calls["n"])
check("사이 기다림 0.5초 → 1.0초", _sleeps == [0.5, 1.0], _sleeps)

print("§5 퇴사(비활성) 직원 · 봇 계정은 잠김 때 들여보내지 않는다")


def always_locked(c, payload, *a, **kw):
    raise sqlite3.OperationalError("database is locked")


add_user("T005", "가상퇴사E", active=0)
PAY["tE"] = pay("T005", "가상퇴사E")
add_user("zz_bot", "봇")
PAY["tZ"] = pay("zz_bot", "봇")
SC.upsert_user_from_payload = always_locked
time.sleep = lambda s: None
try:
    rE, _ = land("tE")
    rZ, _ = land("tZ")
finally:
    time.sleep = _real_sleep
    SC.upsert_user_from_payload = _REAL_UPSERT
check("비활성 직원 → 안내 화면 · 세션 없음", rE.status_code == 200 and session_uid(rE) is None and "잠시 저장이 밀려" in rE.text, (rE.status_code, session_uid(rE)))
check("봇 계정 → 안내 화면 · 세션 없음", rZ.status_code == 200 and session_uid(rZ) is None, (rZ.status_code, session_uid(rZ)))

print("§6 잠김이 아닌 DB 오류는 숨기지 않는다")


def other_error(c, payload, *a, **kw):
    raise sqlite3.OperationalError("no such column: zz_not_here")


SC.upsert_user_from_payload = other_error
try:
    r = TestClient(appmain.app, follow_redirects=False, raise_server_exceptions=False).get("/sso/land", params={"token": "tA"})
finally:
    SC.upsert_user_from_payload = _REAL_UPSERT
check("그대로 500", r.status_code == 500, r.status_code)

print("§7 원문")
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
m = re.search(r"\ndef sso_land\(req: Request\):(.*?)\n@app\.", src, re.S)
body = m.group(1) if m else ""
check("/sso/land 가 저장을 _sso_land_upsert 로 한다", "_sso_land_upsert(payload)" in body, body[:200])
check("/sso/land 안에 직접 저장(upsert_user_from_payload(c, …))이 남아 있지 않다",
      re.search(r"upsert_user_from_payload\(\s*c\s*,", body) is None, "")
check("잠김 판정은 「locked」 글자로만 — 다른 OperationalError 는 다시 올림",
      re.search(r'if "locked" not in str\(e\)\.lower\(\):\s*\n\s*raise', src) is not None, "")
mh = re.search(r"\ndef _sso_land_upsert\(.*?\n\n\n", src, re.S)
hb = mh.group(0) if mh else ""
check("저장 전에 쓰기 자리를 먼저 잡는다(BEGIN IMMEDIATE → upsert 순서)",
      re.search(r'c\.execute\("BEGIN IMMEDIATE"\)\s*\n\s*uid = upsert_user_from_payload\(c, payload\)', hb) is not None, hb[:120])

print("")
print("결과: %d개 중 실패 %d" % (CNT, len(FAIL)))
for f in FAIL:
    print("   ❌", f)
sys.exit(1 if FAIL else 0)
