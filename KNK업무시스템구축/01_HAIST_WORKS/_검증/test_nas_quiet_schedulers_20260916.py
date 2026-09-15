#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1101 NAS 백업 시간 예약 작업 시험 (2026-09-16)

무엇을 막는가
  매주 월요일 02:00~07:30(한국시간) NAS 가 스냅샷 → 로컬 백업 → 서버간 백업을 연쇄로 도는 동안
  WORKS 의 묶음 작업이 끼는 것. (전산 최보현 상무이사 확정 2026-09-15 16:05 · 세션10 전달 지시서)
  실측(2026-09-16): 04:10 명부 동기화가 9/14(월) 04:10 에도 돌며 DB 사본 약 280MB 를 썼다.
  등급 재계산은 기동 뒤 24시간마다라 재기동 시각을 따라 떠다니고, 기동 직후에도 한 번 돈다.

대표 결정 (2026-09-16)
  · 월요일 명부 동기화 = **07:40 에 실행**(건너뛰지 않음)
  · 쌓인 DB 사본 74.7GB = 이번에 손대지 않음(별건)

⛔ 운영 DB·네트워크를 쓰지 않는다. app/main.py 의 **실제 함수 원문**만 뽑아 실행한다.
실행:  python _검증/test_nas_quiet_schedulers_20260916.py   → "실패 0" 이어야 통과
"""
import ast
import builtins
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import types
from datetime import datetime as _DT, timedelta as _TD, timezone as _TZ

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAIN_PY = os.path.join(ROOT, "app", "main.py")
SRC = io.open(MAIN_PY, encoding="utf-8").read()
TREE = ast.parse(SRC)

PASS, FAIL = [], []


def chk(no, name, cond, detail=""):
    (PASS if cond else FAIL).append(no)
    print("  %s %2s. %s%s" % ("OK  " if cond else "실패", no, name,
                              ("" if cond else "   → " + str(detail))))


# ── 가짜 부품: 타이머·등급 모듈·DB·출력 (실제 스레드·DB 를 돌리지 않는다) ─────
class FakeTimer:
    made = []

    def __init__(self, delay, fn):
        self.delay, self.fn, self.daemon, self.started = delay, fn, False, False
        FakeTimer.made.append(self)

    def start(self):
        self.started = True


CALLS = {"tier": 0, "dir": 0}
LOGS = []
_fake_threading = types.SimpleNamespace(Timer=FakeTimer)


def _fake_refresh(c):
    CALLS["tier"] += 1
    return 80


_fake_ct = types.SimpleNamespace(refresh_all_customer_tiers=_fake_refresh)
_real_import = builtins.__import__


def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "threading":
        return _fake_threading
    if level == 1 and "customer_tier" in (fromlist or ()):
        return types.SimpleNamespace(customer_tier=_fake_ct)
    return _real_import(name, globals, locals, fromlist, level)


_fb = dict(vars(builtins))
_fb["__import__"] = _fake_import
_fb["print"] = lambda *a, **k: LOGS.append(" ".join(str(x) for x in a))

# ── main.py 에서 필요한 것만 뽑는다 (모듈 맨 위 datetime 가져오기까지 — 전역 의존 확인) ──
WANT = {"NAS_QUIET_WEEKDAY", "NAS_QUIET_START", "NAS_QUIET_END", "_kst_wall_now",
        "_nas_quiet_wait_secs", "_nas_quiet_now", "_seconds_until_next_0410",
        "_tier_refresh_tick", "_start_tier_refresh_scheduler",
        "_directory_sync_tick", "_start_directory_sync_scheduler"}
_picked, _found = [], set()
for _n in TREE.body:
    if isinstance(_n, ast.ImportFrom) and _n.module == "datetime" and not _n.level:
        _picked.append(_n)
        continue
    _nm = None
    if isinstance(_n, ast.FunctionDef):
        _nm = _n.name
    elif (isinstance(_n, ast.Assign) and len(_n.targets) == 1
          and isinstance(_n.targets[0], ast.Name)):
        _nm = _n.targets[0].id
    if _nm in WANT:
        _picked.append(_n)
        _found.add(_nm)
_miss = sorted(WANT - _found)
assert not _miss, "main.py 에서 못 찾은 것: %s" % _miss

M = types.ModuleType("z1101_subset")
M.__dict__["__builtins__"] = _fb


@contextlib.contextmanager
def _fake_db():
    yield object()


def _fake_autosync():
    CALLS["dir"] += 1


exec(compile(ast.Module(body=_picked, type_ignores=[]), MAIN_PY, "exec"), M.__dict__)
M.db_session = _fake_db
M._run_directory_autosync = _fake_autosync
REAL_WAIT = M._nas_quiet_wait_secs
REAL_NOW = M._nas_quiet_now


def stub_quiet(val):
    """인자 없이 부르면(=지금) val 로 답하고, 시각을 주면 진짜 판정을 쓴다."""
    def w(now_kst=None):
        return val if now_kst is None else REAL_WAIT(now_kst)

    def q(now_kst=None):
        return (val > 0) if now_kst is None else REAL_NOW(now_kst)
    M._nas_quiet_wait_secs = w
    M._nas_quiet_now = q


def restore():
    M._nas_quiet_wait_secs = REAL_WAIT
    M._nas_quiet_now = REAL_NOW


def K(y, mo, d, h, mi, s=0, us=0):
    return _DT(y, mo, d, h, mi, s, us)


MON = (2026, 9, 21)   # 다음 월요일 — 실제 첫 적용일


# ═══════════════════════════════════════════════════════════════════════════
print("\n§1 공용 판정 — 월요일 02:00 부터 07:30 전까지")
chk(1, "2026-09-21 은 월요일 (시험 기준일 확인)", _DT(*MON).weekday() == 0)
chk(2, "상수 = 월요일 · 02:00 · 07:30",
    M.NAS_QUIET_WEEKDAY == 0 and M.NAS_QUIET_START == (2, 0) and M.NAS_QUIET_END == (7, 30),
    (M.NAS_QUIET_WEEKDAY, M.NAS_QUIET_START, M.NAS_QUIET_END))
for _no, _nm, _t, _exp in (
        (3, "월 01:59:59 → 0 (아직 아님)", K(*MON, 1, 59, 59), 0),
        (4, "월 02:00:00 → 19,800초 (5시간 30분)", K(*MON, 2, 0, 0), 19800),
        (5, "월 04:10:00 → 12,000초 (명부 동기화 원래 시각이 금지 시간 안)", K(*MON, 4, 10, 0), 12000),
        (6, "월 07:29:59 → 1초", K(*MON, 7, 29, 59), 1),
        (7, "월 07:29:59.6 → 1초 (0 으로 떨어져 곧바로 돌지 않게)", K(*MON, 7, 29, 59, 600000), 1),
        (8, "월 07:30:00 → 0 (07:30 정각부터 다시 돈다)", K(*MON, 7, 30, 0), 0),
        (9, "일 03:00 → 0 (다른 요일 새벽은 해당 없음)", K(2026, 9, 20, 3, 0), 0),
        (10, "화 03:00 → 0", K(2026, 9, 22, 3, 0), 0)):
    _got = M._nas_quiet_wait_secs(_t)
    chk(_no, _nm, _got == _exp, _got)
chk(11, "_nas_quiet_now 는 남은 초 > 0 과 같다",
    M._nas_quiet_now(K(*MON, 3, 0)) is True and M._nas_quiet_now(K(*MON, 8, 0)) is False)
_kn = M._kst_wall_now()
_ref = _DT.now(_TZ.utc).replace(tzinfo=None) + _TD(hours=9)
chk(12, "한국시간 벽시계 = 협정세계시 + 9시간 (컨테이너 시간대 설정에 기대지 않음)",
    abs((_kn - _ref).total_seconds()) < 5, (_kn, _ref))
chk(13, "한국시간 벽시계에는 시간대 정보가 없다 (비교가 섞여 오류 나지 않게)", _kn.tzinfo is None)


# ═══════════════════════════════════════════════════════════════════════════
print("\n§2 명부 동기화 시각 — 평소 04:10 · 월요일 07:40 (대표 결정)")


def nxt(now):
    return now + _TD(seconds=M._seconds_until_next_0410(now))


def hm(t):
    return t.strftime("%m-%d %a %H:%M")


for _no, _nm, _now, _exp in (
        (14, "수 12:00 → 목 04:10 (평일은 예전과 같다)", K(2026, 9, 16, 12, 0), K(2026, 9, 17, 4, 10)),
        (15, "일 23:00 → 월 07:40", K(2026, 9, 20, 23, 0), K(*MON, 7, 40)),
        (16, "월 01:00 → 월 07:40", K(*MON, 1, 0), K(*MON, 7, 40)),
        (17, "월 03:00 → 월 07:40", K(*MON, 3, 0), K(*MON, 7, 40)),
        (18, "월 05:00 에 재기동돼도 그날 07:40 에 돈다 (건너뛰지 않음)", K(*MON, 5, 0), K(*MON, 7, 40)),
        (19, "월 07:41 → 화 04:10", K(*MON, 7, 41), K(2026, 9, 22, 4, 10)),
        (20, "토 05:00 → 일 04:10", K(2026, 9, 19, 5, 0), K(2026, 9, 20, 4, 10))):
    _got = nxt(_now)
    chk(_no, _nm, _got == _exp, hm(_got))
_d21 = M._seconds_until_next_0410(K(2026, 9, 22, 4, 9, 0))
chk(21, "화 04:09:00 → 60초 뒤 (최소 간격 60초는 예전 그대로)", _d21 == 60.0, _d21)
_d22 = M._seconds_until_next_0410(K(*MON, 7, 39, 30))
chk(22, "월 07:39:30 → 60초 뒤", _d22 == 60.0, _d22)

_runs, _t = [], K(2026, 9, 20, 0, 0)          # 일요일 자정부터 8번 돌려 본다
for _ in range(8):
    _t = nxt(_t)
    _runs.append(_t)
    _t = _t + _TD(seconds=5)                  # 동기화가 몇 초 걸린 뒤 다음 예약
_exp_runs = [K(2026, 9, 20, 4, 10), K(*MON, 7, 40), K(2026, 9, 22, 4, 10), K(2026, 9, 23, 4, 10),
             K(2026, 9, 24, 4, 10), K(2026, 9, 25, 4, 10), K(2026, 9, 26, 4, 10), K(2026, 9, 27, 4, 10)]
chk(23, "일주일 흐름 = 일 04:10 · 월 07:40 · 화~일 04:10", _runs == _exp_runs, [hm(x) for x in _runs])
chk(24, "일주일 동안 금지 시간 안에서 도는 경우 0번", not any(REAL_NOW(x) for x in _runs))
chk(25, "하루에 한 번씩만 돈다 (겹침·누락 없음)", len({x.date() for x in _runs}) == 8)


# ═══════════════════════════════════════════════════════════════════════════
print("\n§3 타이머 동작 — 가짜 타이머로 실제 함수를 그대로 돌린다")
FakeTimer.made.clear()
CALLS["tier"] = 0
LOGS.clear()
stub_quiet(12000)
M._tier_refresh_tick()
chk(26, "월요일 백업 시간에 깨면 등급 재계산을 돌리지 않는다", CALLS["tier"] == 0, CALLS)
chk(27, "대신 07:30 까지 남은 12,000초 뒤로 다시 예약한다",
    len(FakeTimer.made) == 1 and FakeTimer.made[0].delay == 12000 and FakeTimer.made[0].started,
    [(x.delay, x.started) for x in FakeTimer.made])
chk(28, "미뤘다는 기록을 로그에 남긴다", any("NAS" in x and "미룸" in x for x in LOGS), LOGS)

FakeTimer.made.clear()
CALLS["tier"] = 0
stub_quiet(0)
M._tier_refresh_tick()
chk(29, "백업 시간이 아니면 한 번 재계산하고 24시간 뒤를 예약한다 (예전과 같음)",
    CALLS["tier"] == 1 and len(FakeTimer.made) == 1 and FakeTimer.made[0].delay == 86400,
    (CALLS, [x.delay for x in FakeTimer.made]))

FakeTimer.made.clear()
stub_quiet(5000)
M._start_tier_refresh_scheduler()
chk(30, "백업 시간에 기동되면 첫 재계산을 07:30 에 (5,000초 뒤) 잡는다",
    len(FakeTimer.made) == 1 and FakeTimer.made[0].delay == 5000, [x.delay for x in FakeTimer.made])
FakeTimer.made.clear()
stub_quiet(0)
M._start_tier_refresh_scheduler()
chk(31, "평소 기동이면 예전처럼 24시간 뒤",
    len(FakeTimer.made) == 1 and FakeTimer.made[0].delay == 86400, [x.delay for x in FakeTimer.made])

FakeTimer.made.clear()
CALLS["dir"] = 0
LOGS.clear()
stub_quiet(3000)
M._directory_sync_tick()
chk(32, "월요일 백업 시간에 깨면 명부 동기화(= DB 사본 280MB)를 돌리지 않는다", CALLS["dir"] == 0, CALLS)
chk(33, "그래도 다음 예약은 잡는다 (멈춰 버리지 않음)",
    len(FakeTimer.made) == 1 and FakeTimer.made[0].delay >= 60 and FakeTimer.made[0].started,
    [(x.delay, x.started) for x in FakeTimer.made])

FakeTimer.made.clear()
CALLS["dir"] = 0
LOGS.clear()
stub_quiet(0)
M._directory_sync_tick()
chk(34, "평소엔 한 번 돌리고 다음을 예약한다", CALLS["dir"] == 1 and len(FakeTimer.made) == 1, CALLS)
chk(35, "로그에 다음 실행 시각(한국시간)을 적는다 — 9/21 실제 확인용",
    any("다음 자동 명부 동기화" in x and "한국시간" in x for x in LOGS), LOGS)

FakeTimer.made.clear()
LOGS.clear()
restore()
M._start_directory_sync_scheduler()
chk(36, "기동 로그에도 다음 실행 시각(한국시간)을 적는다",
    any("다음 실행" in x and "한국시간" in x for x in LOGS) and len(FakeTimer.made) == 1, LOGS)
restore()


# ═══════════════════════════════════════════════════════════════════════════
print("\n§4 배포 전 검사기(check_nas_quiet_schedulers) — 일부러 틀린 코드로 시험")
_spec = importlib.util.spec_from_file_location(
    "knk_check_standards", os.path.join(ROOT, "deploy", "check_standards.py"))
CS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CS)
_LAB = tempfile.mkdtemp(prefix="knk_nasq_")
os.makedirs(os.path.join(_LAB, "app"), exist_ok=True)


def probe(src):
    io.open(os.path.join(_LAB, "app", "main.py"), "w", encoding="utf-8", newline="").write(src)
    _old = CS.ROOT
    CS.ROOT = _LAB
    try:
        return CS.check_nas_quiet_schedulers()
    finally:
        CS.ROOT = _old


def fnode(name, tree=None):
    for n in (tree or TREE).body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise KeyError(name)


def splice(src, node, text):
    ls = src.split("\n")
    return "\n".join(ls[:node.lineno - 1] + text.split("\n") + ls[node.end_lineno:])


def hits(res, key):
    return [m for _f, _l, m in res if key in m]


_real = CS.check_nas_quiet_schedulers()
chk(37, "고친 main.py 는 검사를 통과한다", _real == [], _real)

OLD_TIER_TICK = '''def _tier_refresh_tick():
    import threading as _th
    try:
        from . import customer_tier as _ct
        with db_session() as c:
            n = _ct.refresh_all_customer_tiers(c)
        print(f"[TIER-AUTO] refreshed {n} customers")
    except Exception as e:
        print(f"[TIER-AUTO ERR] {e}")
    timer = _th.Timer(86400, _tier_refresh_tick)  # 24h
    timer.daemon = True
    timer.start()'''
_r = probe(splice(SRC, fnode("_tier_refresh_tick"), OLD_TIER_TICK))
chk(38, "② 등급 재계산 타이머에서 판정을 빼면 잡는다 (수정 전 코드)",
    bool(hits(_r, "② _tier_refresh_tick")), _r)

_r = probe(SRC + '''

def _nightly_export_tick():
    import threading as _th
    # _nas_quiet_now() 를 주석에만 적어 두면 인정하지 않는다
    t = _th.Timer(3600, _nightly_export_tick)
    t.start()
''')
chk(39, "② 새로 만든 예약 작업이 판정을 안 거치면 잡는다 (주석에 이름만 적은 건 인정 안 함)",
    bool(hits(_r, "② _nightly_export_tick")), _r)

OLD_0410 = '''def _seconds_until_next_0410():
    from datetime import datetime as _dt, timedelta as _td
    now = _dt.now()
    target = now.replace(hour=4, minute=10, second=0, microsecond=0)
    if target <= now:
        target += _td(days=1)
    return max(60.0, (target - now).total_seconds())'''
_r = probe(splice(SRC, fnode("_seconds_until_next_0410"), OLD_0410))
chk(40, "④ 명부 동기화 시각 계산이 월요일을 안 피하면 잡는다 (수정 전 코드)",
    bool(hits(_r, "④ _seconds_until_next_0410")), _r)

_st = fnode("startup")
_try = next(n for n in ast.walk(_st) if isinstance(n, ast.Try)
            and any(isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "refresh_all_customer_tiers"
                    for c in ast.walk(n)))
OLD_STARTUP_TRY = '''    try:
        from . import customer_tier as _ct
        with db_session() as c:
            n = _ct.refresh_all_customer_tiers(c)
        print(f"[TIER] {n} customers tier auto-computed")
    except Exception as _e:
        print(f"[TIER ERR] {_e}")'''
_r = probe(splice(SRC, _try, OLD_STARTUP_TRY))
chk(41, "⑤ 기동 직후 등급 재계산이 판정 밖에 있으면 잡는다 (수정 전 코드)",
    bool(hits(_r, "⑤ startup")), _r)

_BAD_IF = '''    try:
        if _nas_quiet_now():
            from . import customer_tier as _ct
            with db_session() as c:
                n = _ct.refresh_all_customer_tiers(c)
    except Exception as _e:
        print(f"[TIER ERR] {_e}")'''
_r = probe(splice(SRC, _try, _BAD_IF))
chk(42, "⑤ 판정 안쪽이라도 '백업 시간일 때' 쪽에서 돌리면 잡는다 (조건 뒤집기)",
    bool(hits(_r, "⑤ startup")), _r)

assert SRC.count("NAS_QUIET_END = (7, 30)") == 1
_r = probe(SRC.replace("NAS_QUIET_END = (7, 30)", "NAS_QUIET_END = (7, 0)"))
chk(43, "① 끝 시각을 07:00 으로 바꾸면 잡는다", bool(hits(_r, "① NAS_QUIET_END")), _r)

assert SRC.count("if start <= k < end:") == 1
_r = probe(SRC.replace("if start <= k < end:", "if start <= k <= end:"))
chk(44, "① 07:30 정각을 포함하도록(<=) 바꾸면 잡는다", bool(hits(_r, "① 경계")), _r)

_tk = fnode("_tier_refresh_tick")
_ls = SRC.split("\n")
_ins = _tk.body[0].end_lineno          # 'import threading as _th' 바로 다음 줄에 끼워 넣는다
_r = probe("\n".join(_ls[:_ins] + ["    from . import customer_tier as _ct0",
                                   "    _ct0.refresh_all_customer_tiers(None)"] + _ls[_ins:]))
chk(45, "③ 판정보다 무거운 작업이 먼저 돌면 잡는다", bool(hits(_r, "③ _tier_refresh_tick")), _r)

OLD_DIR_TICK = '''def _directory_sync_tick():
    import threading as _th
    try:
        _run_directory_autosync()
    except Exception as e:
        print(f"[DIR-SYNC tick ERR] {e}")
    timer = _th.Timer(_seconds_until_next_0410(), _directory_sync_tick)
    timer.daemon = True
    timer.start()'''
_r = probe(splice(SRC, fnode("_directory_sync_tick"), OLD_DIR_TICK))
chk(46, "③ 명부 동기화 타이머가 판정 전에 동기화부터 돌리면 잡는다 (수정 전 코드)",
    bool(hits(_r, "③ _directory_sync_tick")), _r)

assert SRC.count("def _mail_fetch_tick():") == 1
_r = probe(SRC.replace("def _mail_fetch_tick():", "def _mail_fetch_tick_copy():"))
chk(47, "면제는 이름으로만 — 메일 타이머를 다른 이름으로 복사하면 잡는다",
    bool(hits(_r, "② _mail_fetch_tick_copy")), _r)
chk(48, "면제 목록에 사유가 적혀 있다 (평일 16:30 · 메일 5분)",
    "평일 16:30" in io.open(os.path.join(ROOT, "deploy", "check_standards.py"), encoding="utf-8").read()
    and "메일 5분" in io.open(os.path.join(ROOT, "deploy", "check_standards.py"), encoding="utf-8").read())


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 66)
print("  통과 %d건 · 실패 %d건" % (len(PASS), len(FAIL)))
if FAIL:
    print("  실패 번호: %s" % ", ".join(str(x) for x in FAIL))
print("=" * 66)
sys.exit(1 if FAIL else 0)
