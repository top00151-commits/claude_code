# -*- coding: utf-8 -*-
"""
KNK Mail 편의기능 검증 — 검색·별표/안읽음 필터·서명·받는사람 자동완성 (대표 지시)
"""
import os, sys, sqlite3

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "01_HAIST_WORKS")))
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

# 받은 메일 4건(별표/읽음 섞기)
def ins_in(frm, fnm, subj, body, read=0, star=0):
    con.execute("INSERT INTO mail_messages(user_id,direction,from_email,from_name,subject,body_text,category,is_read,is_starred) "
                "VALUES(1,'in',?,?,?,?,'일반',?,?)", (frm, fnm, subj, body, read, star))
ins_in("sales@abc.com", "이상우", "견적 요청드립니다", "KNK-INS-300 견적 부탁", read=0, star=1)
ins_in("po@dream.co.kr", "박발주", "발주서 송부", "자동화 설비 발주합니다", read=1, star=0)
ins_in("kh@vn.com", "Tran", "báo giá", "베트남 고객 문의", read=0, star=0)
ins_in("tax@x.com", "세무대리", "세금계산서", "인보이스 첨부", read=1, star=1)
# 보낸 메일 2건
con.execute("INSERT INTO mail_messages(user_id,direction,to_email,from_name,subject,body_text,category,is_read) "
            "VALUES(1,'out','client@corp.com','김정락','회신: 견적서','견적서 보냅니다','일반',1)")
con.execute("INSERT INTO mail_messages(user_id,direction,to_email,from_name,subject,body_text,category,is_read) "
            "VALUES(1,'out','vn@partner.com','김정락','발주 확인','발주 확인합니다','일반',1)")
# 전사 연락처
for n, em, co, po in [("이상우","sangwoo@abc.com","ABC상사","부장"),
                      ("이상우","sangwoo@abc.com","ABC상사","부장"),  # 중복 메일
                      ("김영희","younghee@dream.co.kr","드림텍","대리"),
                      ("Nguyen","nguyen@vn-corp.com","VN코프","구매"),
                      ("주소없음","","노메일","")]:
    con.execute("INSERT INTO shared_contacts(name,email,company,position) VALUES(?,?,?,?)", (n, em, co, po))
con.commit()

section("메일 검색 (받은편지함)")
r = MS.list_inbox(con, 1, q="견적")
check("제목/본문 '견적' 검색", len(r) == 1 and "견적" in r[0]["subject"], f"n={len(r)}")
r = MS.list_inbox(con, 1, q="이상우")
check("보낸사람 이름 검색", len(r) == 1 and r[0]["from_name"] == "이상우")
r = MS.list_inbox(con, 1, q="발주")
check("본문 '발주' 검색", len(r) == 1, f"n={len(r)}")
r = MS.list_inbox(con, 1, q="없는키워드xyz")
check("없는 키워드 → 0건", len(r) == 0)

section("필터 — 별표 / 안읽음")
r = MS.list_inbox(con, 1, starred=True)
check("별표만(2건)", len(r) == 2 and all(x["is_starred"] for x in r), f"n={len(r)}")
r = MS.list_inbox(con, 1, unread=True)
check("안읽음만(2건)", len(r) == 2 and all(not x["is_read"] for x in r), f"n={len(r)}")
r = MS.list_inbox(con, 1, starred=True, q="견적")
check("별표+검색 조합", len(r) == 1 and r[0]["subject"].startswith("견적"))

section("메일 검색 (보낸편지함)")
r = MS.list_sent(con, 1, q="견적")
check("보낸함 제목/본문 검색", len(r) == 1 and "견적" in r[0]["subject"], f"n={len(r)}")
r = MS.list_sent(con, 1, q="partner.com")
check("보낸함 받는주소 검색", len(r) == 1 and "partner" in r[0]["to_email"])
check("보낸함 전체(검색없음) 2건", len(MS.list_sent(con, 1)) == 2)

section("서명 저장/조회")
check("초기 서명 빈값", MS.get_signature(con, 1) == "")
MS.save_signature(con, 1, "㈜케이엔케이 김정락 대표\nMobile. 010-0000-0000")
con.commit()
check("서명 저장 후 조회", "김정락 대표" in MS.get_signature(con, 1))
MS.save_signature(con, 1, "수정된 서명")
con.commit()
check("서명 덮어쓰기(1인 1개)", MS.get_signature(con, 1) == "수정된 서명")
MS.save_signature(con, 1, "")
con.commit()
check("빈값 저장=서명 해제", MS.get_signature(con, 1) == "")

section("받는사람 자동완성 (전사 연락처)")
r = MS.search_contacts(con, "이상우")
check("이름 검색", len(r) == 1 and r[0]["email"] == "sangwoo@abc.com", f"n={len(r)}")
check("중복 메일 제거", len([x for x in MS.search_contacts(con, "sangwoo") if x["email"] == "sangwoo@abc.com"]) == 1)
r = MS.search_contacts(con, "드림")
check("회사명 검색", len(r) == 1 and r[0]["name"] == "김영희")
r = MS.search_contacts(con, "vn-corp")
check("메일주소 검색", len(r) == 1 and r[0]["name"] == "Nguyen")
check("메일 없는 연락처 제외", all(x["email"] for x in MS.search_contacts(con, "주소없음")) and len(MS.search_contacts(con, "주소없음")) == 0)
check("빈 검색어 → 0건", MS.search_contacts(con, "") == [])

print("\n" + "=" * 60)
print(f"결과: PASS={PASS}  FAIL={FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
