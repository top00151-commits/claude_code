# -*- coding: utf-8 -*-
"""메일 자동 가져오기 스케줄러 검증 — 하이웍스 미접속(POP3 collect 가짜).
_mailfetch_run_owner / _mail_fetch_tick 가 enabled 계정의 새 메일을 실제 store_inbound 로
적재하는지, enabled=0 이면 건너뛰는지, 중복(같은 Message-ID)은 안 쌓이는지 확인.
실행: 프로젝트 루트(01_HAIST_WORKS)에서  python _검증/mailfetch_auto_test.py"""
import os, sys, io, shutil, tempfile
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("KNK_SECRET_KEY", "test_secret_key_at_least_32_chars_long_000")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from email.message import EmailMessage
from app import database as _db
from app import main as M
from app import mail_fetch as _mf

PASS = []; FAIL = []
def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  [OK] " if cond else "  [XX] ") + name)

def make_raw(mid, subj, body, frm="boss@partner.com", to="top0015@knknara.co.kr"):
    m = EmailMessage()
    m["Message-ID"] = "<%s@partner.com>" % mid
    m["From"] = frm; m["To"] = to; m["Subject"] = subj
    m.set_content(body)
    return m.as_bytes()

def main():
    # 1) 실제 dev DB 를 임시본으로 복제 → db_session 이 임시본을 쓰게(실DB 무오염)
    src = _db.DB_PATH
    tmp = tempfile.mktemp(suffix="_mfauto.db")
    shutil.copy(src, tmp)
    _db.DB_PATH = tmp
    try:
        M.DB_PATH = tmp
    except Exception:
        pass
    print("temp DB:", tmp)

    # 2) 테스트 사용자 + fetch 계정(enabled) 준비
    with _db.db_session() as c:
        uid = c.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()[0]
        _mf._ensure_table(c)
        c.execute("DELETE FROM mail_fetch_accounts WHERE owner_user_id=?", (uid,))
        c.execute("INSERT INTO mail_fetch_accounts(owner_user_id,protocol,host,port,use_ssl,username,password_enc,enabled) "
                  "VALUES(?,?,?,?,?,?,?,1)", (uid, "pop3", "pop3s.hiworks.com", 995, 1, "top0015@knknara.co.kr", "ENC"))
        before = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in'", (uid,)).fetchone()[0]
    print("owner uid=%d, 받은메일 시작 %d통" % (uid, before))

    # 3) 비번 복호화 + POP3 수집을 가짜로 — 하이웍스 미접속
    M._mail.decrypt = lambda x: "dummy-pw"
    fake = [
        ("UIDL-A", make_raw("auto-A", "자동 테스트 견적", "본문 A")),
        ("UIDL-B", make_raw("auto-B", "자동 테스트 발주", "본문 B")),
    ]
    _mf.pop3_collect = lambda host, port, ssl, user, pw, seen, limit=100: {
        "ok": True, "messages": [(k, r) for (k, r) in fake if k not in seen]}

    # 4) _mailfetch_run_owner — 2통 적재
    ok, stored, msg = M._mailfetch_run_owner(uid)
    check("run_owner ok=True", ok is True)
    check("새 메일 2통 적재", stored == 2)
    with _db.db_session() as c:
        after = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in'", (uid,)).fetchone()[0]
        st = c.execute("SELECT last_status,last_count FROM mail_fetch_accounts WHERE owner_user_id=?", (uid,)).fetchone()
    check("받은편지함 +2", after == before + 2)
    check("상태=자동 가져오기 기록", st and "자동 가져오기" in (st[0] or ""))

    # 5) 멱등 — 같은 UIDL 재수집(seen 처리됨) → 0통
    ok2, stored2, _ = M._mailfetch_run_owner(uid)
    check("재실행 0통(seen 중복방지)", ok2 is True and stored2 == 0)

    # 6) _mail_fetch_tick — enabled 계정 자동 점검(새 메일 C 1통)
    fake.append(("UIDL-C", make_raw("auto-C", "자동 테스트 추가", "본문 C")))
    M._mail_fetch_tick.__wrapped__ if hasattr(M._mail_fetch_tick, "__wrapped__") else None
    # tick 은 finally 에서 타이머 재예약 → 데몬이라 프로세스 종료 시 정리됨. 1회 호출로 수집만 확인.
    import threading
    _orig = threading.Timer
    threading.Timer = lambda *a, **k: type("T", (), {"daemon": True, "start": lambda self: None})()  # 재예약 무력화
    try:
        M._mail_fetch_tick()
    finally:
        threading.Timer = _orig
    with _db.db_session() as c:
        after2 = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in'", (uid,)).fetchone()[0]
    check("tick 이 enabled 계정에서 +1(C)", after2 == before + 3)

    # 7) enabled=0 이면 tick 이 건너뜀(새 메일 D 추가해도 0)
    with _db.db_session() as c:
        _mf.set_enabled(c, uid, 0)
    fake.append(("UIDL-D", make_raw("auto-D", "꺼짐 테스트", "본문 D")))
    threading.Timer = lambda *a, **k: type("T", (), {"daemon": True, "start": lambda self: None})()
    try:
        M._mail_fetch_tick()
    finally:
        threading.Timer = _orig
    with _db.db_session() as c:
        after3 = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in'", (uid,)).fetchone()[0]
    check("자동 OFF면 tick 건너뜀(증가 0)", after3 == after2)

    # 8) run_owner 도 enabled=0 이면 비활성 반환
    okd, sd, md = M._mailfetch_run_owner(uid)
    check("run_owner enabled=0 → 비활성", okd is False and "비활성" in (md or ""))

    print("\n=== PASS %d / FAIL %d ===" % (len(PASS), len(FAIL)))
    if FAIL:
        print("실패:", FAIL)
    # 정리
    try:
        os.remove(tmp)
    except OSError:
        pass
    sys.exit(0 if not FAIL else 1)

if __name__ == "__main__":
    main()
