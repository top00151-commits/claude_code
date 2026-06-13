# -*- coding: utf-8 -*-
"""
KNK 대용량 첨부 검증 — 토큰·파일명 안전·등록·만료·다운로드·링크 블록 (대표 지시)
"""
import os, sys, sqlite3

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "01_HAIST_WORKS")))

from app import database as DB
from app import mail_store as MS

PASS, FAIL = 0, 0
def check(n, c, e=""):
    global PASS, FAIL
    if c: PASS += 1; print(f"  [PASS] {n}" + (f"  ({e})" if e else ""))
    else: FAIL += 1; print(f"  [FAIL] {n}" + (f"  ({e})" if e else ""))
def section(t): print("\n" + "=" * 60 + f"\n{t}\n" + "=" * 60)

con = sqlite3.connect(":memory:")
con.row_factory = sqlite3.Row
con.execute("PRAGMA foreign_keys=ON")
con.executescript(DB.SCHEMA)
con.execute("INSERT INTO users(id,name,login_id,password,role,is_active) VALUES(1,'김정락','kjr','x','ceo',1)")
con.commit()

section("스키마·토큰·파일명 안전")
cols = [r[1] for r in con.execute("PRAGMA table_info(mail_large_files)").fetchall()]
check("mail_large_files 테이블 생성", all(x in cols for x in ("token","path","expires_at","download_count")), str(cols))
t1, t2 = MS.new_large_token(), MS.new_large_token()
check("토큰 충분히 길고 유일", len(t1) >= 20 and t1 != t2, f"len={len(t1)}")
check("파일명 경로조작 제거", MS.safe_filename("../../etc/passwd") == "passwd", MS.safe_filename("../../etc/passwd"))
check("파일명 역슬래시 처리", MS.safe_filename("..\\..\\win.ini") == "win.ini", MS.safe_filename("..\\..\\win.ini"))
check("위험문자 치환", "/" not in MS.safe_filename('a/b:c*.zip') and MS.safe_filename('a/b:c*.zip') != "")
check("빈 파일명 폴백", MS.safe_filename("") == "file")

section("등록·조회·만료·다운로드 카운트")
tok = MS.new_large_token()
exp = MS.register_large_file(con, token=tok, user_id=1, filename="대용량보고서.zip",
                            mime="application/zip", path="/tmp/x/대용량보고서.zip",
                            size=45*1024*1024, expiry_days=30)
con.commit()
check("등록 시 만료일(30일 후) 생성", bool(exp), exp)
info = MS.get_large_file(con, tok)
check("조회 성공", info and info["filename"] == "대용량보고서.zip")
check("아직 만료 아님", info and info["expired"] is False)
# 만료 처리(과거로 변경)
con.execute("UPDATE mail_large_files SET expires_at='2000-01-01 00:00:00' WHERE token=?", (tok,))
con.commit()
check("만료된 링크 → expired=True", MS.get_large_file(con, tok)["expired"] is True)
check("없는 토큰 → None", MS.get_large_file(con, "nope") is None)
# 다운로드 카운트
MS.bump_large_download(con, tok); MS.bump_large_download(con, tok)
n = con.execute("SELECT download_count FROM mail_large_files WHERE token=?", (tok,)).fetchone()[0]
check("다운로드 카운트 증가", n == 2, f"count={n}")

section("용량 표기·본문 링크 블록")
check("human_size MB", MS.human_size(45*1024*1024) == "45.0 MB", MS.human_size(45*1024*1024))
check("human_size KB", MS.human_size(2048) == "2.0 KB", MS.human_size(2048))
check("human_size B", MS.human_size(500) == "500 B", MS.human_size(500))
# 유효 2건 + 만료 1건(tok) → 유효만 블록에
a = MS.new_large_token(); b = MS.new_large_token()
MS.register_large_file(con, token=a, user_id=1, filename="설계도.pdf", mime="application/pdf", path="/tmp/a", size=12*1024*1024)
MS.register_large_file(con, token=b, user_id=1, filename="영상.mp4", mime="video/mp4", path="/tmp/b", size=300*1024*1024)
con.commit()
block = MS.large_links_block(con, [a, b, tok, "ghost"], "https://works.knknara.co.kr")
check("블록에 유효 2건 파일명", "설계도.pdf" in block and "영상.mp4" in block)
check("블록에 다운로드 URL", f"/dl/{a}" in block and f"/dl/{b}" in block)
check("만료/없는 토큰은 블록 제외", tok not in block and "ghost" not in block)
check("블록 헤더 표기", "대용량 첨부파일" in block and "30일" in block)
check("빈 토큰이면 빈 블록", MS.large_links_block(con, [], "https://x") == "")

print("\n" + "=" * 60)
print(f"결과: PASS={PASS}  FAIL={FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
