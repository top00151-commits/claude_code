# -*- coding: utf-8 -*-
"""메일 스팸·피싱 방어 1번 검증 — 차단목록·위험판별·차단함·소급·복구.
실DB 임시본 사용(무오염). 실행: 01_HAIST_WORKS 에서 python _검증/mail_security_test.py"""
import os, sys, shutil, tempfile
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from app import database as _db
from app import mail_store as ms

PASS = []; FAIL = []
def ck(n, c):
    (PASS if c else FAIL).append(n)
    print(("  [OK] " if c else "  [XX] ") + n)

def rlvl(**kw):
    return ms.assess_risk(**kw)[0]

def main():
    src = _db.DB_PATH
    tmp = tempfile.mktemp(suffix="_sec.db")
    shutil.copy(src, tmp)
    _db.DB_PATH = tmp
    print("temp DB:", tmp)

    # 1) 규칙 위험판별
    ck("내부발신 위험0", rlvl(from_email="a@knknara.co.kr", subject="회의", body="내일 봅시다") == 0)
    ck("외부발신 위험1", rlvl(from_email="a@partner.com", subject="견적", body="견적 보냅니다(링크없음)") == 1)
    ck("외부+피싱링크 위험2", rlvl(from_email="a@spam.com", subject="계정 정지 안내",
                                  body="비밀번호 확인하세요 http://phish.example") == 2)
    ck("실행첨부 위험3(내부라도)", rlvl(from_email="a@knknara.co.kr", subject="x", body="x",
                                       attachments=[{"filename": "invoice.exe"}]) == 3)
    ck("확장자 .SCR 위험", ms._att_ext("file.SCR") in ms.DANGEROUS_EXTS)
    ck("확장자 .pdf 안전", ms._att_ext("doc.pdf") not in ms.DANGEROUS_EXTS)

    with _db.db_session() as c:
        uid = c.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()[0]
        ms._ensure_security_cols(c)
        c.execute("DELETE FROM mail_blocklist")

        # 2) 차단목록 매칭
        ms.add_block(c, "evil@spam.com", "email", by=uid)
        ck("이메일 정확매칭", ms.is_sender_blocked(c, "evil@spam.com") is True)
        ck("다른주소 비매칭", ms.is_sender_blocked(c, "good@spam.com") is False)
        ms.add_block(c, "bad.com", "domain", by=uid)
        ck("도메인 매칭", ms.is_sender_blocked(c, "any@bad.com") is True)
        ck("서브도메인 매칭", ms.is_sender_blocked(c, "x@mail.bad.com") is True)
        ck("내부도메인 비매칭", ms.is_sender_blocked(c, "me@knknara.co.kr") is False)

        # 3) store_inbound 자동 차단격리
        ib0 = len(ms.list_inbox(c, uid))
        bl0 = len(ms.list_blocked(c, uid))
        mid_blk, _ = ms.store_inbound(c, to_email="x@knknara.co.kr", from_email="evil@spam.com",
                                      subject="스팸 테스트1", text="본문1", owner_id=uid, run_ai=False)
        mid_ok, _ = ms.store_inbound(c, to_email="x@knknara.co.kr", from_email="boss@partner.com",
                                     subject="정상 테스트1", text="내일 회의합시다", owner_id=uid, run_ai=False)
        rb = c.execute("SELECT is_blocked FROM mail_messages WHERE id=?", (mid_blk,)).fetchone()
        ro = c.execute("SELECT is_blocked FROM mail_messages WHERE id=?", (mid_ok,)).fetchone()
        ck("차단발신 is_blocked=1", rb["is_blocked"] == 1)
        ck("정상발신 is_blocked=0", ro["is_blocked"] == 0)
        ck("받은편지함서 차단 제외(+1만)", len(ms.list_inbox(c, uid)) == ib0 + 1)
        ck("차단함에 포함(+1)", len(ms.list_blocked(c, uid)) == bl0 + 1)

        # 4) 소급 차단(차단목록 추가 전 받은 메일도 격리)
        midx, _ = ms.store_inbound(c, to_email="x@knknara.co.kr", from_email="z@later.com",
                                   subject="나중에 차단할 메일", text="본문", owner_id=uid, run_ai=False)
        ck("미차단 시 받은편지함(is_blocked=0)",
           c.execute("SELECT is_blocked FROM mail_messages WHERE id=?", (midx,)).fetchone()["is_blocked"] == 0)
        ms.add_block(c, "later.com", "domain", by=uid)
        moved = ms.apply_block_to_existing(c, "later.com", "domain")
        ck("소급 차단 옮김 >=1", moved >= 1)
        ck("소급 후 차단됨",
           c.execute("SELECT is_blocked FROM mail_messages WHERE id=?", (midx,)).fetchone()["is_blocked"] == 1)

        # 5) 개별 복구
        ms.set_blocked(c, uid, midx, False)
        ck("복구 is_blocked=0",
           c.execute("SELECT is_blocked FROM mail_messages WHERE id=?", (midx,)).fetchone()["is_blocked"] == 0)

    print("\n=== PASS %d / FAIL %d ===" % (len(PASS), len(FAIL)))
    if FAIL:
        print("실패:", FAIL)
    try:
        os.remove(tmp)
    except OSError:
        pass
    sys.exit(0 if not FAIL else 1)

if __name__ == "__main__":
    main()
