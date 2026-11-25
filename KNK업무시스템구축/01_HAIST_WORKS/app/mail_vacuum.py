# -*- coding: utf-8 -*-
"""메일 DB 빈 자리 밤 줄이기(VACUUM) — 대표 2026-11-25 「진행해」

메일은 웍스 본 DB(data/knk.db) 안에 함께 저장된다. 메일을 지워도 파일 크기는 그대로(빈 자리 = freelist)라
밤에 한 번 「할 가치가 있을 때만」 파일을 실제로 줄인다. 메일 내용은 바꾸지 않는다(VACUUM 은 파일 정리만).

순서(하나라도 안 맞으면 줄이지 않고 이유를 기록):
  ① 시각 — 매일 23:30(한국시간)에 판단 · 월요일 02:00~07:30(NAS 백업) · 08:50~09:30 에는 절대 안 돎
  ② 겹침 — 메일 받아오기·아웃룩 옛 메일 가져오기·본문 정리가 도는 중이면 다음 날로
  ③ 가치 — 빈 자리(freelist_count × page_size)가 전체의 10% 이상 또는 200MB 이상일 때만
  ④ 디스크 — 남은 공간이 DB 크기의 2.5배(사본 + VACUUM 임시 공간) 밑이면 안 함
  ⑤ 사본 — SQLite backup API 로 사본 → 사본 integrity_check = ok 여야 다음 · 사본은 최근 2개만
  ⑥ VACUUM → WAL 비우기(checkpoint TRUNCATE) → 전/후 크기 기록
기록: mail_vacuum_log 표(최근 60줄) · 관리자 「메일 정리」 화면에 마지막 결과 한 줄.
"""
import datetime as _dt
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from contextlib import contextmanager

RUN_AT = (23, 30)                       # 매일 판단 시각(한국시간)
TRIGGER_RATIO = 0.10                    # 빈 자리 비율 기준
TRIGGER_BYTES = 200 * 1024 * 1024       # 빈 자리 크기 기준
DISK_FACTOR = 2.5                       # 남은 디스크 ≥ DB 크기 × 2.5
KEEP_BACKUPS = 2
BACKUP_PREFIX = "knk.db.bak_mailvacuum_"
LOG_KEEP = 60
BUSY_TIMEOUT_MS = 60000                 # VACUUM 연결이 남의 짧은 쓰기를 기다리는 시간
QUIET_MORNING = ((8, 50), (9, 30))      # 출근 직후 — 안 돎
NAS_WEEKDAY, NAS_START, NAS_END = 0, (2, 0), (7, 30)   # 월요일 NAS 백업 — 안 돎

RES_DONE, RES_SKIP, RES_FAIL, RES_HOLD = "done", "skip", "fail", "hold"
# 11-25 안전장치: 줄이기(VACUUM) 동안 웍스 전체 저장이 멈춘다(같은 knk.db · z521 로그인 충돌 전례).
#   사본 뜨기(읽기만 · 저장을 막지 않음)에 걸린 시간을 실측해, 그보다 오래 멈출 것 같으면 줄이지 않고 대표 확인으로 넘긴다.
MAX_BACKUP_SECS = 90

_MAINT_TL = threading.Lock()


def kst_now():
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) + _dt.timedelta(hours=9)


def quiet_reason(now):
    """돌면 안 되는 시간이면 이유 글, 아니면 ""."""
    hm = (now.hour, now.minute)
    if now.weekday() == NAS_WEEKDAY and NAS_START <= hm < NAS_END:
        return "월요일 NAS 백업 시간(02:00~07:30)"
    if QUIET_MORNING[0] <= hm < QUIET_MORNING[1]:
        return "출근 시간(08:50~09:30)"
    return ""


def in_run_window(now):
    """판단해도 되는 때 = 23:30~01:59(타이머가 조금 늦게 깨어나도 같은 밤으로 봄)."""
    return (now.hour, now.minute) >= RUN_AT or now.hour < 2


def seconds_until_next_run(now):
    slot = now.replace(hour=RUN_AT[0], minute=RUN_AT[1], second=0, microsecond=0)
    if slot <= now:
        slot += _dt.timedelta(days=1)
    return max(60.0, (slot - now).total_seconds())


def fmt_secs(s):
    s = float(s or 0)
    return ("%.1f" % s) if s < 10 else ("%d" % int(round(s)))


def fmt_bytes(n):
    n = float(n or 0)
    if n >= 1024 ** 3:
        return "%.1fGB" % (n / 1024 ** 3)
    if n >= 1024 ** 2:
        return "%.1fMB" % (n / 1024 ** 2)
    return "%.0fKB" % (n / 1024)


def file_bytes(db_path):
    """DB 파일 + -wal 크기(디스크에서 실제 차지하는 것)."""
    t = 0
    for p in (db_path, db_path + "-wal"):
        if os.path.isfile(p):
            t += os.path.getsize(p)
    return t


def measure(db_path):
    """{"page_size", "pages", "free_pages", "total", "free", "ratio"} — 읽기만."""
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        ps = conn.execute("PRAGMA page_size").fetchone()[0]
        pc = conn.execute("PRAGMA page_count").fetchone()[0]
        fc = conn.execute("PRAGMA freelist_count").fetchone()[0]
    finally:
        conn.close()
    total, free = ps * pc, ps * fc
    return {"page_size": ps, "pages": pc, "free_pages": fc, "total": total, "free": free,
            "ratio": (free / float(total)) if total else 0.0}


def worth(m):
    return m["free"] >= TRIGGER_BYTES or (m["total"] > 0 and m["ratio"] >= TRIGGER_RATIO)


def disk_check(db_path, m, backup_dir, free_fn=None, tmp_dir=None):
    """줄일 만큼 디스크가 있나 → (ok, 이유). 기준 = DB 크기 × 2.5 (사본 1 + VACUUM 임시·WAL 1.5).
    임시 폴더가 다른 디스크면 그 디스크도 살아 있는 자료 크기만큼은 있어야 한다."""
    free_fn = free_fn or (lambda p: shutil.disk_usage(p).free)
    size = max(file_bytes(db_path), m["total"])
    # WAL 모드 VACUUM = 임시 DB(살아 있는 자료만큼) + WAL(또 그만큼) → 빈 자리가 적은 큰 DB 는 2.5배를 넘을 수 있어 큰 쪽을 씀
    live = max(0, m["total"] - m["free"])
    need = max(int(size * DISK_FACTOR), size + 2 * live)
    have = free_fn(backup_dir)
    if have < need:
        return False, "디스크 여유 부족 · 남은 %s < 필요 %s(DB %s × %.1f)" % (fmt_bytes(have), fmt_bytes(need), fmt_bytes(size), DISK_FACTOR)
    tmp_dir = tmp_dir or tempfile.gettempdir()
    try:
        other = os.stat(tmp_dir).st_dev != os.stat(backup_dir).st_dev
    except OSError:
        other = False
    if other:
        live = m["total"] - m["free"]
        t_have = free_fn(tmp_dir)
        if t_have < int(live * 1.1):
            return False, "임시 폴더 디스크 여유 부족 · 남은 %s < 필요 %s" % (fmt_bytes(t_have), fmt_bytes(int(live * 1.1)))
    return True, ""


def integrity_ok(path):
    conn = sqlite3.connect(path, timeout=30)
    try:
        r = conn.execute("PRAGMA integrity_check").fetchall()
    finally:
        conn.close()
    return len(r) == 1 and str(r[0][0]).lower() == "ok", (str(r[0][0]) if r else "결과 없음")


def make_backup(db_path, backup_dir, now):
    """backup API 로 사본 → 검사 ok 면 최종 이름으로. 실패하면 반쯤 만든 사본은 지우고 예외."""
    os.makedirs(backup_dir, exist_ok=True)
    final = os.path.join(backup_dir, BACKUP_PREFIX + now.strftime("%Y%m%d_%H%M%S"))
    part = final + ".part"
    try:
        src = sqlite3.connect(db_path, timeout=60)
        try:
            dst = sqlite3.connect(part)
            try:
                with dst:
                    src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        ok, msg = integrity_ok(part)
        if not ok:
            raise RuntimeError("사본 검사 실패(integrity_check: %s)" % msg[:80])
        os.replace(part, final)
        return final
    except Exception:
        for g in (part, part + "-wal", part + "-shm", part + "-journal"):
            if os.path.isfile(g):
                os.remove(g)
        raise


def prune_backups(backup_dir, keep=KEEP_BACKUPS):
    from .database import prune_db_backups
    return prune_db_backups(backup_dir, BACKUP_PREFIX, keep=keep)


def do_vacuum(db_path):
    conn = sqlite3.connect(db_path, isolation_level=None, timeout=BUSY_TIMEOUT_MS / 1000.0)
    try:
        conn.execute("PRAGMA busy_timeout = %d" % BUSY_TIMEOUT_MS)
        conn.execute("VACUUM")
        try:   # WAL 로 쓴 새 페이지를 본 파일로 옮기고 -wal 을 비움(읽는 사람이 있으면 다음 체크포인트 때)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
        except sqlite3.OperationalError as e:
            print("[MAIL-VACUUM] WAL 비우기 다음으로 미룸: %s" % e, flush=True)
    finally:
        conn.close()


# ─── 같이 돌면 안 되는 정리 작업끼리 잠금(본문 정리 · 줄이기) — 일꾼 둘이어도 하나만 ───
@contextmanager
def maint_lock(data_dir, wait=0.0):
    """잡으면 True, 못 잡으면 False 를 내준다. 리눅스 = 데이터 폴더 잠금 파일(flock) · 윈도 시험 PC = 스레드 잠금."""
    got_t = _MAINT_TL.acquire(timeout=wait) if wait > 0 else _MAINT_TL.acquire(False)
    if not got_t:
        yield False
        return
    f = None
    try:
        try:
            import fcntl as _fc
        except ImportError:
            _fc = None
        if _fc is not None:
            f = open(os.path.join(data_dir, ".mail_maint.lock"), "a")
            try:
                _fc.flock(f.fileno(), _fc.LOCK_EX | _fc.LOCK_NB)
            except OSError:
                f.close()
                f = None
                yield False
                return
        yield True
    finally:
        if f is not None:
            import fcntl as _fc
            _fc.flock(f.fileno(), _fc.LOCK_UN)
            f.close()
        _MAINT_TL.release()


def outlook_import_busy(c, now=None, minutes=30):
    """아웃룩 옛 메일 가져오기가 최근 N분 안에 메일을 보냈으면 이유 글."""
    try:
        has = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='mail_import_tokens'").fetchone()
    except sqlite3.Error as e:
        return "아웃룩 가져오기 상태 확인 실패(%s)" % str(e)[:60]
    if not has:
        return ""
    now = now or _dt.datetime.now()
    since = (now - _dt.timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    r = c.execute("SELECT COUNT(*) FROM mail_import_tokens WHERE state IN ('ready','running') AND COALESCE(last_at,'')>=?",
                  (since,)).fetchone()
    return "아웃룩 옛 메일 가져오는 중" if (r and r[0]) else ""


# ─── 기록 ───
def ensure_log(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_vacuum_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        secs REAL DEFAULT 0,
        result TEXT NOT NULL,
        reason TEXT DEFAULT '',
        before_bytes INTEGER DEFAULT 0,
        after_bytes INTEGER DEFAULT 0,
        free_bytes INTEGER DEFAULT 0,
        backup TEXT DEFAULT '')""")


def write_log(db_path, rec):
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout = 30000")
        with conn:
            ensure_log(conn)
            conn.execute("INSERT INTO mail_vacuum_log(started_at, secs, result, reason, before_bytes, after_bytes, free_bytes, backup) "
                         "VALUES(?,?,?,?,?,?,?,?)",
                         (rec["started_at"], rec["secs"], rec["result"], rec["reason"], rec["before"], rec["after"],
                          rec["free"], os.path.basename(rec.get("backup") or "")))
            conn.execute("DELETE FROM mail_vacuum_log WHERE id NOT IN (SELECT id FROM mail_vacuum_log ORDER BY id DESC LIMIT ?)",
                         (LOG_KEEP,))
    finally:
        conn.close()


def last_result(c):
    """화면 한 줄용 — 기록이 없으면 None."""
    ensure_log(c)
    r = c.execute("SELECT * FROM mail_vacuum_log ORDER BY id DESC LIMIT 1").fetchone()
    if not r:
        return None
    d = dict(r) if hasattr(r, "keys") else dict(zip(["id", "started_at", "secs", "result", "reason", "before_bytes",
                                                      "after_bytes", "free_bytes", "backup"], r))
    d["text"] = result_text(d["result"], d["reason"], d["before_bytes"], d["after_bytes"], d["secs"])
    return d


def result_text(result, reason, before, after, secs):
    """KNK 규정(knk-done-status) 머리말."""
    if result == RES_DONE:
        return "✅ 완료 — 이 작업은 끝났습니다. %s → %s(%s초) · 더 하실 일은 없습니다." % (fmt_bytes(before), fmt_bytes(after), fmt_secs(secs))
    if result == RES_SKIP:
        return "✅ 완료 — 이번엔 줄이지 않았습니다(%s) · 다음 밤 23:30에 다시 봅니다 · 하실 일은 없습니다." % (reason or "건너뜀")
    if result == RES_HOLD:
        return "👉 남은 일 — 줄이지 않고 멈췄습니다(%s) · 메일과 파일은 그대로입니다 · 대표님 확인 뒤에 줄입니다." % (reason or "확인 필요")
    return "⚠ 끝나지 않았습니다 — %s · 파일은 줄이기 전 그대로이고 메일은 바뀌지 않았습니다 · 다음 밤 23:30에 다시 시도합니다." % (reason or "실패")


# ─── 한 번 실행 ───
def run_once(db_path, backup_dir=None, now=None, busy=None, free_fn=None, tmp_dir=None, log=True,
             backup_fn=None, vacuum_fn=None):
    """판단 → (필요하면) 사본·검사·줄이기 → 기록. 돌려줌 = 기록 dict(result · reason · before · after · free · secs · backup · text).
    busy() 가 이유 글을 돌려주면(받아오는 중 등) 줄이지 않는다. backup_fn·vacuum_fn 은 시험용 바꿔 끼우기."""
    now = now or kst_now()
    backup_dir = backup_dir or os.path.join(os.path.dirname(db_path), "backups")
    t0 = time.time()
    rec = {"started_at": now.strftime("%Y-%m-%d %H:%M:%S"), "result": RES_SKIP, "reason": "", "before": file_bytes(db_path),
           "after": 0, "free": 0, "secs": 0.0, "backup": ""}

    def _end(result, reason=""):
        rec["result"], rec["reason"] = result, reason
        rec["after"] = file_bytes(db_path)
        rec["secs"] = round(time.time() - t0, 1)
        rec["text"] = result_text(result, reason, rec["before"], rec["after"], rec["secs"])
        print("[MAIL-VACUUM] %s" % rec["text"], flush=True)
        if log:
            try:
                write_log(db_path, rec)
            except Exception as e:   # 기록 실패도 숨기지 않는다
                print("[MAIL-VACUUM] 기록 저장 실패: %s" % str(e)[:160], flush=True)
                rec["log_error"] = str(e)[:160]
        return rec

    q = quiet_reason(now)
    if q:
        return _end(RES_SKIP, q)
    try:
        b = busy() if busy else ""
    except Exception as e:
        return _end(RES_SKIP, "겹침 확인 실패(%s) — 안전하게 다음 날로" % str(e)[:80])
    if b:
        return _end(RES_SKIP, b + " — 다음 날로")
    try:
        m = measure(db_path)
    except Exception as e:
        return _end(RES_FAIL, "빈 자리 재기 실패(%s)" % str(e)[:80])
    rec["free"] = m["free"]
    if not worth(m):
        return _end(RES_SKIP, "빈 자리 적음 · %s(%.1f%%)" % (fmt_bytes(m["free"]), m["ratio"] * 100))
    ok, why = disk_check(db_path, m, backup_dir if os.path.isdir(backup_dir) else os.path.dirname(db_path), free_fn, tmp_dir)
    if not ok:
        return _end(RES_SKIP, why)
    try:
        rec["backup"] = (backup_fn or make_backup)(db_path, backup_dir, now)
    except Exception as e:
        return _end(RES_FAIL, "사본을 못 떠서 줄이지 않음(%s)" % str(e)[:100])
    prune_backups(backup_dir)
    bk_secs = round(time.time() - t0, 1)
    if bk_secs > MAX_BACKUP_SECS:
        return _end(RES_HOLD, "사본 뜨기에 %s초 걸림 → 줄이면 그 이상 웍스 저장이 멈출 수 있음 · DB %s · 빈 자리 %s"
                    % (fmt_secs(bk_secs), fmt_bytes(rec["before"]), fmt_bytes(m["free"])))
    try:
        (vacuum_fn or do_vacuum)(db_path)
    except Exception as e:
        return _end(RES_FAIL, "줄이기 실패(%s) · 사본 %s" % (str(e)[:100], os.path.basename(rec["backup"])))
    return _end(RES_DONE, "빈 자리 %s 회수" % fmt_bytes(m["free"]))
