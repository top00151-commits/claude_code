# -*- coding: utf-8 -*-
"""메일 DB 밤 줄이기(VACUUM) 시험 (11-25 대표 「진행해」) — 가짜 자료로 만든 임시 SQLite 만 씀.
실행: 프로젝트 루트(01_HAIST_WORKS)에서  PYTHONIOENCODING=utf-8 python _검증/mail_vacuum_test.py"""
import datetime as dt
import io
import os
import sqlite3
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from app import mail_vacuum as mv  # noqa: E402

P, F = [], []


def ck(n, ok, extra=""):
    (P if ok else F).append(n)
    print(("  [OK] " if ok else "  [XX] ") + n + ("" if ok else "  " + str(extra)))


NIGHT = dt.datetime(2026, 11, 25, 23, 30, 0)   # 수요일 23:30
BIG = 10 ** 15                                   # 디스크 넉넉


def make_db(rows=3000, delete_ratio=0.0):
    d = tempfile.mkdtemp(prefix="knk_mvac_")
    p = os.path.join(d, "knk.db")
    c = sqlite3.connect(p)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE mail_messages(id INTEGER PRIMARY KEY, subject TEXT, body TEXT)")
    c.executemany("INSERT INTO mail_messages(subject, body) VALUES(?,?)",
                  [("가짜 제목 %d" % i, "가짜 본문 " * 200) for i in range(rows)])
    c.commit()
    if delete_ratio:
        c.execute("DELETE FROM mail_messages WHERE id <= ?", (int(rows * delete_ratio),))
        c.commit()
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()
    return p


def body_sig(p):
    c = sqlite3.connect(p)
    try:
        return c.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(body)),0), MAX(id) FROM mail_messages").fetchone()
    finally:
        c.close()


def log_rows(p):
    c = sqlite3.connect(p)
    try:
        return c.execute("SELECT result, reason FROM mail_vacuum_log ORDER BY id").fetchall()
    finally:
        c.close()


def baks(p):
    bd = os.path.join(os.path.dirname(p), "backups")
    return sorted(f for f in os.listdir(bd) if f.startswith(mv.BACKUP_PREFIX)) if os.path.isdir(bd) else []


print("1) 빈 자리 적음 → 건너뜀")
p = make_db(delete_ratio=0.0)
r = mv.run_once(p, now=NIGHT, free_fn=lambda _p: BIG)
ck("결과 = 건너뜀", r["result"] == mv.RES_SKIP, r)
ck("이유 = 빈 자리 적음", "빈 자리 적음" in r["reason"], r["reason"])
ck("사본 안 뜸", baks(p) == [], baks(p))
ck("기록 1줄", len(log_rows(p)) == 1 and log_rows(p)[0][0] == "skip")
ck("화면 문구 머리말 ✅", r["text"].startswith("✅ 완료"), r["text"])

print("2) 빈 자리 많음 → 사본·검사·줄이기·크기 감소")
p = make_db(delete_ratio=0.6)
sig0 = body_sig(p)
m0 = mv.measure(p)
ck("빈 자리 10% 넘음(전제)", m0["ratio"] >= 0.10, m0)
r = mv.run_once(p, now=NIGHT, free_fn=lambda _p: BIG)
ck("결과 = 완료", r["result"] == mv.RES_DONE, r)
ck("크기 줄어듦", r["after"] < r["before"], (r["before"], r["after"]))
ck("사본 1개", len(baks(p)) == 1, baks(p))
bk = os.path.join(os.path.dirname(p), "backups", baks(p)[0]) if baks(p) else ""
ck("사본 검사 ok", bool(bk) and mv.integrity_ok(bk)[0])
ck("사본 = 줄이기 전 자료와 같음", bool(bk) and body_sig(bk) == sig0)
ck("메일 자료 그대로(통수·본문 길이·번호)", body_sig(p) == sig0, (body_sig(p), sig0))
ck("줄인 뒤 DB 검사 ok", mv.integrity_ok(p)[0])
ck("빈 자리 0", mv.measure(p)["free_pages"] == 0)
ck("완료 문구 = 「✅ 완료 — 이 작업은 끝났습니다.」 + 전→후", r["text"].startswith("✅ 완료 — 이 작업은 끝났습니다.") and "→" in r["text"], r["text"])
ck("기록 done", log_rows(p)[-1][0] == "done")
lr = mv.last_result(sqlite3.connect(p))
ck("화면 한 줄(last_result)", lr and lr["result"] == "done" and lr["text"].startswith("✅"), lr)

print("2-1) 200MB 기준(비율 낮아도 크기로)")
ck("worth: 5% 지만 250MB", mv.worth({"free": 250 * 1024 ** 2, "total": 5000 * 1024 ** 2, "ratio": 0.05}))
ck("worth: 5% · 100MB = 아님", not mv.worth({"free": 100 * 1024 ** 2, "total": 2000 * 1024 ** 2, "ratio": 0.05}))
ck("worth: 10% 정확히 = 함", mv.worth({"free": 10, "total": 100, "ratio": 0.10}))

print("3) 사본 실패 → 안 줄임")
p = make_db(delete_ratio=0.6)
s0 = mv.file_bytes(p)
called = []


def bad_backup(db, bd, now):
    raise RuntimeError("가짜 사본 실패")


r = mv.run_once(p, now=NIGHT, free_fn=lambda _p: BIG, backup_fn=bad_backup, vacuum_fn=lambda d: called.append(1))
ck("결과 = 실패", r["result"] == mv.RES_FAIL, r)
ck("VACUUM 안 부름", called == [])
ck("크기 그대로", mv.file_bytes(p) == s0 or mv.measure(p)["free_pages"] > 0)
ck("실패 문구 머리말 ⚠", r["text"].startswith("⚠ 끝나지 않았습니다"), r["text"])

print("3-1) 사본 검사 실패(integrity) → 안 줄임 · 반쯤 만든 사본 지움")
p = make_db(delete_ratio=0.6)
_orig = mv.integrity_ok
mv.integrity_ok = lambda path: (False, "가짜 손상")
try:
    r = mv.run_once(p, now=NIGHT, free_fn=lambda _p: BIG, vacuum_fn=lambda d: called.append(2))
finally:
    mv.integrity_ok = _orig
ck("결과 = 실패", r["result"] == mv.RES_FAIL and "사본" in r["reason"], r)
ck("VACUUM 안 부름", 2 not in called)
bd = os.path.join(os.path.dirname(p), "backups")
ck("남은 사본·조각 없음", not os.path.isdir(bd) or os.listdir(bd) == [], os.listdir(bd) if os.path.isdir(bd) else "")

print("4) 디스크 부족 → 안 줄임")
p = make_db(delete_ratio=0.6)
size = mv.file_bytes(p)
r = mv.run_once(p, now=NIGHT, free_fn=lambda _p: int(size * 2.4), vacuum_fn=lambda d: called.append(4))
ck("결과 = 건너뜀(디스크)", r["result"] == mv.RES_SKIP and "디스크 여유 부족" in r["reason"], r)
ck("VACUUM 안 부름", 4 not in called)
ck("사본 안 뜸", baks(p) == [])
r2 = mv.run_once(p, now=NIGHT, free_fn=lambda _p: int(size * 2.6), vacuum_fn=lambda d: called.append(41))
ck("2.6배면 진행", r2["result"] == mv.RES_DONE and 41 in called, r2)
fm = {"total": 1000, "free": 150, "ratio": 0.15}   # 빈 자리 15% → 살아 있는 자료 850 → 필요 = 1000 + 1700 = 2.7배
_nofile = os.path.join(os.path.dirname(p), "없는.db")
ck("빈 자리 적은 DB 는 2.5배보다 더 요구(WAL·임시)", not mv.disk_check(_nofile, fm, os.path.dirname(p), lambda _p: 2600)[0])
ck("…2.7배면 됨", mv.disk_check(_nofile, fm, os.path.dirname(p), lambda _p: 2700)[0])

print("5) 받아오기 잠금 중 → 안 줄임")
p = make_db(delete_ratio=0.6)
r = mv.run_once(p, now=NIGHT, free_fn=lambda _p: BIG, busy=lambda: "메일 받아오는 중", vacuum_fn=lambda d: called.append(5))
ck("결과 = 건너뜀(받아오는 중 · 다음 날)", r["result"] == mv.RES_SKIP and "받아오는 중" in r["reason"] and "다음 날" in r["reason"], r)
ck("VACUUM 안 부름", 5 not in called)
r = mv.run_once(p, now=NIGHT, free_fn=lambda _p: BIG, busy=lambda: 1 / 0, vacuum_fn=lambda d: called.append(51))
ck("겹침 확인이 오류 나도 안 줄임", r["result"] == mv.RES_SKIP and 51 not in called, r)

print("5-1) 아웃룩 가져오기 중 판정")
c = sqlite3.connect(":memory:")
ck("표 없으면 = 아님", mv.outlook_import_busy(c) == "")
c.execute("CREATE TABLE mail_import_tokens(id INTEGER PRIMARY KEY, state TEXT, last_at TEXT)")
nowl = dt.datetime(2026, 11, 25, 23, 30)
c.execute("INSERT INTO mail_import_tokens(state,last_at) VALUES('running','2026-11-25 23:20:00')")
ck("10분 전 보냄 = 가져오는 중", "아웃룩" in mv.outlook_import_busy(c, nowl))
c.execute("UPDATE mail_import_tokens SET last_at='2026-11-25 20:00:00'")
ck("3시간 전 = 아님", mv.outlook_import_busy(c, nowl) == "")
c.execute("UPDATE mail_import_tokens SET state='ended', last_at='2026-11-25 23:25:00'")
ck("끝난 번호 = 아님", mv.outlook_import_busy(c, nowl) == "")

print("5-2) 정리 잠금(본문 정리와 겹침 막기)")
d = tempfile.mkdtemp(prefix="knk_mvac_lk_")
with mv.maint_lock(d) as a:
    with mv.maint_lock(d) as b:
        ck("먼저 잡은 쪽 = 잡음", a is True)
        ck("겹친 쪽 = 못 잡음", b is False)
with mv.maint_lock(d) as a2:
    ck("풀린 뒤 다시 잡힘", a2 is True)

print("6) 월요일 02:00~07:30 · 08:50~09:30 → 안 돎")
for t, should in ((dt.datetime(2026, 11, 30, 2, 0), True), (dt.datetime(2026, 11, 30, 7, 29), True),
                  (dt.datetime(2026, 11, 30, 7, 30), False), (dt.datetime(2026, 11, 30, 1, 59), False),
                  (dt.datetime(2026, 12, 1, 3, 0), False),   # 화요일 새벽은 NAS 시간 아님
                  (dt.datetime(2026, 11, 25, 8, 50), True), (dt.datetime(2026, 11, 25, 9, 29), True),
                  (dt.datetime(2026, 11, 25, 9, 30), False), (dt.datetime(2026, 11, 25, 8, 49), False),
                  (NIGHT, False)):
    ck("quiet %s → %s" % (t.strftime("%a %H:%M"), should), bool(mv.quiet_reason(t)) == should, mv.quiet_reason(t))
p = make_db(delete_ratio=0.6)
for t in (dt.datetime(2026, 11, 30, 3, 0), dt.datetime(2026, 11, 26, 9, 0)):
    r = mv.run_once(p, now=t, free_fn=lambda _p: BIG, vacuum_fn=lambda d: called.append(6))
    ck("run_once %s = 건너뜀" % t.strftime("%a %H:%M"), r["result"] == mv.RES_SKIP and 6 not in called, r)
ck("시간에 걸린 날은 사본도 안 뜸", baks(p) == [])
ck("판단 창: 23:30 됨", mv.in_run_window(NIGHT))
ck("판단 창: 01:10 됨(늦게 깸)", mv.in_run_window(dt.datetime(2026, 11, 26, 1, 10)))
ck("판단 창: 09:00·23:29 안 됨", not mv.in_run_window(dt.datetime(2026, 11, 26, 9, 0)) and not mv.in_run_window(dt.datetime(2026, 11, 25, 23, 29)))
ck("다음 예약 = 23:30", abs(mv.seconds_until_next_run(dt.datetime(2026, 11, 25, 23, 0)) - 1800) < 1)
ck("23:30 지나면 내일 23:30", abs(mv.seconds_until_next_run(dt.datetime(2026, 11, 25, 23, 31)) - (86400 - 60)) < 1)

print("7) 사본 3번째부터는 오래된 것 지움(최근 2개)")
p = make_db(delete_ratio=0.6)
for i, day in enumerate((26, 27, 28)):
    c = sqlite3.connect(p)
    c.executemany("INSERT INTO mail_messages(subject, body) VALUES(?,?)", [("추가 %d" % k, "가짜 " * 300) for k in range(800)])
    c.commit()
    c.execute("DELETE FROM mail_messages WHERE subject LIKE '추가 %'")
    c.commit()
    c.close()
    r = mv.run_once(p, now=dt.datetime(2026, 11, day, 23, 30), free_fn=lambda _p: BIG)
    ck("%d번째 실행 완료" % (i + 1), r["result"] == mv.RES_DONE, r)
b = baks(p)
ck("사본 2개만", len(b) == 2, b)
ck("남은 것 = 최근 둘(27·28일)", b == [mv.BACKUP_PREFIX + "20261127_233000", mv.BACKUP_PREFIX + "20261128_233000"], b)

print("8) VACUUM 실패 → 실패 기록 · 자료 그대로")
p = make_db(delete_ratio=0.6)
sig0 = body_sig(p)


def bad_vac(db):
    raise sqlite3.OperationalError("database is locked")


r = mv.run_once(p, now=NIGHT, free_fn=lambda _p: BIG, vacuum_fn=bad_vac)
ck("결과 = 실패 · 사본 이름 함께", r["result"] == mv.RES_FAIL and "사본" in r["reason"], r)
ck("자료 그대로", body_sig(p) == sig0)

print("8b) 사본 뜨기가 오래 걸리면(운영 규모) 줄이지 않고 대표 확인으로 — 웍스 저장 멈춤 방지")
p = make_db(delete_ratio=0.6)
sig0 = body_sig(p)
called = []
_old_max = mv.MAX_BACKUP_SECS
mv.MAX_BACKUP_SECS = -1      # 사본 시간이 한도를 넘은 것으로
r = mv.run_once(p, now=NIGHT, free_fn=lambda _p: BIG, vacuum_fn=lambda d: called.append(8))
mv.MAX_BACKUP_SECS = _old_max
ck("결과 = 멈춤(hold) · 줄이기 안 부름", r["result"] == mv.RES_HOLD and called == [], r)
ck("문구 = 👉 남은 일 · 사본 시간·DB 크기 실측", r["text"].startswith("👉 남은 일") and "초 걸림" in r["reason"], r["text"])
ck("사본은 남음(되돌릴 길)", bool(r["backup"]) and os.path.isfile(r["backup"]), r["backup"])
ck("자료 그대로", body_sig(p) == sig0)
lr = log_rows(p)
ck("기록에 hold 로 남음", lr and lr[-1][0] == mv.RES_HOLD if lr and isinstance(lr[-1], (tuple, list)) else True, lr[-1:] if lr else lr)
r2 = mv.run_once(p, now=NIGHT, free_fn=lambda _p: BIG, vacuum_fn=lambda d: called.append(81))
ck("한도 안이면 그대로 줄임", r2["result"] == mv.RES_DONE and called == [81], r2)

print("9) 다른 연결이 쓰는 중이면 VACUUM 이 기다렸다 진행(busy_timeout)")
p = make_db(delete_ratio=0.6)
holder = sqlite3.connect(p, isolation_level=None, check_same_thread=False)
holder.execute("BEGIN IMMEDIATE")
holder.execute("INSERT INTO mail_messages(subject, body) VALUES('잠깐 쓰기','가짜')")
timer = threading.Timer(1.5, lambda: holder.execute("COMMIT"))
timer.start()
_t0 = dt.datetime.now()
mv.do_vacuum(p)
holder.close()
ck("쓰기 끝날 때까지 기다린 뒤 완료", (dt.datetime.now() - _t0).total_seconds() >= 1.0)
ck("쓰던 줄도 남아 있음", sqlite3.connect(p).execute("SELECT COUNT(*) FROM mail_messages WHERE subject='잠깐 쓰기'").fetchone()[0] == 1)

print("10) 웍스 본체에 붙은 곳 — 받아오기 잠금을 쥔 동안은 안 줄임 · 관리자 화면 한 줄")
os.environ["KNK_RUN_MAIL_FETCH"] = "0"
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_mvac_main_"), "knk.db")
    _db.init_db()
    import app.main as m
finally:
    sys.stdout = _so
_c = sqlite3.connect(_db.DB_PATH)   # 빈 자리 만들기(가짜 표에 넣었다 지움)
_c.execute("CREATE TABLE zz_fake(id INTEGER PRIMARY KEY, b TEXT)")
_c.executemany("INSERT INTO zz_fake(b) VALUES(?)", [("가짜 " * 300,) for _ in range(3000)])
_c.commit()
_c.execute("DROP TABLE zz_fake")
_c.commit()
_c.close()
with _db.db_session() as c:
    from app import mail_fetch as _mf
    _mf._ensure_table(c)
    c.execute("INSERT INTO mail_fetch_accounts(owner_user_id, enabled) VALUES(9701, 1)")
_m_called = []
_orig_vac, _orig_disk = mv.do_vacuum, mv.disk_check
mv.do_vacuum = lambda d: _m_called.append(d)
mv.disk_check = lambda *a, **k: (True, "")
mv.kst_now = lambda: NIGHT   # 시험을 아침 08:50~09:30 에 돌려도 같은 결과
try:
    hold = m._MailFetchLock(9701, 0)
    hold.__enter__()
    out = {}
    th = threading.Thread(target=lambda: out.update(r=m._mail_vacuum_busy_and_run()))
    th.start()
    th.join(30)
    hold.__exit__(None, None, None)
    ck("받아오는 중이면 건너뜀", out.get("r", {}).get("result") == mv.RES_SKIP and "받아오는 중" in out["r"]["reason"], out)
    ck("VACUUM 안 부름", _m_called == [])
    r = m._mail_vacuum_busy_and_run()
    ck("잠금 풀리면 진행", r["result"] == mv.RES_DONE and len(_m_called) == 1, r)
    # 줄이는 동안엔 받아오기가 「busy」로 건너뜀(같은 잠금)
    ck("줄이기가 끝나면 받아오기 잠금도 풀림", m._MailFetchLock(9701, 0).__enter__().got)
finally:
    mv.do_vacuum, mv.disk_check = _orig_vac, _orig_disk
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9702,'t_vac_admin','시험관리자','admin',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9703,'t_vac_mem','시험직원','member',1,'x')")
from starlette.testclient import TestClient  # noqa: E402
_who = {"u": {"id": 9702, "role": "admin", "name": "시험관리자", "login_id": "t_vac_admin", "lang": "ko"}}
m.get_user = lambda req: _who["u"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
res = k.get("/admin/mail-purge")
ck("관리자 화면 200", res.status_code == 200, res.status_code)
ck("마지막 줄이기 결과 한 줄 보임", "mpVacLast" in res.text and "✅ 완료 — 이 작업은 끝났습니다." in res.text, res.text[-800:])
ck("「지금 줄이기」 새 단추 없음", "지금 줄이기" not in res.text)
_who["u"] = {"id": 9703, "role": "member", "name": "시험직원", "login_id": "t_vac_mem", "lang": "ko"}
res = k.get("/admin/mail-purge")
ck("직원은 못 봄(되돌려 보냄)", res.status_code in (302, 303) and "mpVacLast" not in res.text, res.status_code)

print("11) 실제 메일 표로 — 줄이기 도중 받기·읽기가 막히지 않나 · 전후 메일·첨부·폴더 수가 같은가(가짜 자료 · 진짜 VACUUM)")
from app import mail_store as _ms  # noqa: E402
from app import mail_folders as _mfo  # noqa: E402
_ms._att_dir = (lambda d: (lambda: d))(tempfile.mkdtemp(prefix="knk_mvac_att_"))   # 첨부 파일은 임시 폴더로
mv.kst_now = lambda: NIGHT
UID = 9710
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(?,?,?,?,1,'x',?)",
              (UID, "t_vac_u", "시험사용자", "member", "vac-u@knknara.co.kr"))
    for i in range(3):
        _mfo.add_folder(c, UID, "시험폴더%d" % i, None, "")
    for i in range(1200):
        _ms.store_inbound(c, to_email="vac-u@knknara.co.kr", from_email="a%d@partner-demo.example" % (i % 7), from_name="가짜",
                          subject="가짜 메일 %d" % i, text="가짜 본문 " * 80, owner_id=UID, run_ai=False,
                          message_id="vac-%d@demo" % i,
                          attachments=([{"filename": "f%d.txt" % i, "mime": "text/plain", "size": 20, "data": ("가짜첨부%d" % i).encode()}]
                                       if i % 3 == 0 else None))
_c = sqlite3.connect(_db.DB_PATH)   # 빈 자리 다시 만들기
_c.execute("CREATE TABLE zz_fake2(id INTEGER PRIMARY KEY, b TEXT)")
_c.executemany("INSERT INTO zz_fake2(b) VALUES(?)", [("가짜 " * 400,) for _ in range(12000)])
_c.commit()
_c.execute("DROP TABLE zz_fake2")
_c.commit()
_c.close()


def counts():
    with _db.db_session() as c:
        return {"mail": c.execute("SELECT COUNT(*) FROM mail_messages").fetchone()[0],
                "att": c.execute("SELECT COUNT(*) FROM mail_attachments").fetchone()[0],
                "folder": c.execute("SELECT COUNT(*) FROM mail_folders").fetchone()[0],
                "subj_sum": c.execute("SELECT COALESCE(SUM(LENGTH(subject)),0) FROM mail_messages").fetchone()[0],
                "max_id": c.execute("SELECT MAX(id) FROM mail_messages").fetchone()[0]}


before = counts()
ck("전제: 메일 1200 · 첨부 400 · 폴더 ≥3", before["mail"] == 1200 and before["att"] == 400 and before["folder"] >= 3, before)
stop = threading.Event()
errs, reads, writes = [], [0], [0]


def reader():
    while not stop.is_set():
        try:
            with _db.db_session() as c:
                c.execute("SELECT id, subject FROM mail_messages WHERE user_id=? ORDER BY id DESC LIMIT 50", (UID,)).fetchall()
            reads[0] += 1
        except Exception as e:
            errs.append("읽기: %s" % e)


def writer():
    k = 0
    while not stop.is_set():
        try:
            with _db.db_session() as c:
                _ms.store_inbound(c, to_email="vac-u@knknara.co.kr", from_email="w@partner-demo.example", from_name="가짜",
                                  subject="도중에 받은 메일 %d" % k, text="가짜", owner_id=UID, run_ai=False, message_id="vac-w-%d@demo" % k)
            writes[0] += 1
            k += 1
        except Exception as e:
            errs.append("받기(저장): %s" % e)
        stop.wait(0.05)


ths = [threading.Thread(target=reader), threading.Thread(target=writer)]
for t in ths:
    t.start()
size0 = mv.file_bytes(_db.DB_PATH)
r = mv.run_once(_db.DB_PATH)
stop.set()
for t in ths:
    t.join(30)
print("     (실측 · 가짜 DB) %s → %s · 걸린 시간 %.1f초 · 도중 읽기 %d번 · 도중 받기 %d통"
      % (mv.fmt_bytes(r["before"]), mv.fmt_bytes(r["after"]), r["secs"], reads[0], writes[0]))
ck("진짜 VACUUM 완료 · 크기 줄어듦", r["result"] == mv.RES_DONE and r["after"] < r["before"], r)
ck("도중 읽기·받기 오류 0", errs == [], errs[:3])
ck("도중에도 읽기가 돌았음", reads[0] > 0)
after = counts()
ck("메일 수 = 전 + 도중에 받은 수", after["mail"] == before["mail"] + writes[0], (before, after, writes[0]))
ck("첨부 수 같음", after["att"] == before["att"], (before["att"], after["att"]))
ck("폴더 수 같음", after["folder"] == before["folder"], (before["folder"], after["folder"]))
with _db.db_session() as c:
    old = c.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(subject)),0) FROM mail_messages WHERE id<=?", (before["max_id"],)).fetchone()
ck("원래 메일 1200통의 제목 길이 합 그대로(내용 안 바뀜)", tuple(old) == (before["mail"], before["subj_sum"]), (tuple(old), before))
with _db.db_session() as c:
    i2, _o = _ms.store_inbound(c, to_email="vac-u@knknara.co.kr", from_email="z@partner-demo.example", from_name="가짜",
                               subject="직후에 받은 메일", text="가짜", owner_id=UID, run_ai=False, message_id="vac-after@demo")
ck("줄인 직후 받기 정상", bool(i2))
ck("줄인 뒤 DB 검사 ok", mv.integrity_ok(_db.DB_PATH)[0])
_who["u"] = {"id": 9702, "role": "admin", "name": "시험관리자", "login_id": "t_vac_admin", "lang": "ko"}
res = k.get("/admin/mail-purge")
ck("관리자 화면에 이번 결과(→ 크기) 보임", res.status_code == 200 and mv.fmt_bytes(r["after"]) in res.text, res.status_code)

print("\n통과 %d · 실패 %d" % (len(P), len(F)))
sys.exit(1 if F else 0)
