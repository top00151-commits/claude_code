# -*- coding: utf-8 -*-
"""메일 용량 재기 시험 (11-23) — 빈 임시 DB · 가짜 자료만.
실행: 프로젝트 루트(01_HAIST_WORKS)에서  python _검증/mail_storage_test.py"""
import io
import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
import app.database as _db  # noqa: E402
_db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_storage_"), "t.db")
_db.init_db()
from app import mail_store as ms  # noqa: E402
from app import mail_storage as mst  # noqa: E402
sys.stdout = _so

P, F = [], []


def ck(n, ok, extra=""):
    (P if ok else F).append(n)
    print(("  [OK] " if ok else "  [XX] ") + n + ("" if ok else "  " + str(extra)))


with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9101,'t_st','시험','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9102,'t_st2','남','member',1,'x')")
SECRET = "비밀제목ZQX"


def put(uid, frm, subj, html, days, blocked=0, atts=None, mid="x"):
    with _db.db_session() as c:
        i, _o = ms.store_inbound(c, to_email="t@knknara.co.kr", from_email=frm, from_name="가짜", subject=subj, text="",
                                 html=html, owner_id=uid, run_ai=False, attachments=atts, message_id=mid)
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?), is_blocked=? WHERE id=?", ("-%d days" % days, blocked, i))
    return i


BIG = "<p>" + "가짜 반복 글 " * 400 + "</p>"
JPG = os.urandom(30000)
put(9101, "a@partner-demo.example", SECRET + " 거래처", BIG, 10, mid="m1")
put(9101, "news@shop-demo.example", "(광고) 소식", BIG, 200, mid="m2")
put(9101, "p1@knknara.co.kr", "제작요청 건", BIG, 400, mid="m3")
put(9101, "p2@knknara.co.kr", "점심 안내", BIG, 400, mid="m4")
put(9101, "x@spam-demo.example", "스팸", BIG, 30, blocked=1, mid="m5")
put(9101, "noreply@svc-demo.example", "알림", BIG, 500, mid="m6")
att = [{"filename": "a.jpg", "mime": "image/jpeg", "size": len(JPG), "content_id": "", "inline": 0, "data": JPG}]
put(9101, "a@partner-demo.example", "첨부1", "<p>a</p>", 5, atts=att, mid="m7")
put(9101, "a@partner-demo.example", "첨부2 같은 파일", "<p>b</p>", 6, atts=att, mid="m8")
csv = ("a,b,c\n" * 5000).encode()
put(9101, "a@partner-demo.example", "csv", "<p>c</p>", 7, atts=[{"filename": "a.csv", "mime": "text/csv", "size": len(csv), "content_id": "", "inline": 0, "data": csv}], mid="m9")
put(9102, "p1@knknara.co.kr", "제작요청 건", BIG, 400, mid="m3")      # 다른 사람이 받은 같은 공지

r = mst.run(_db.db_session, 9101, whole=True)
cells = r["cells"]
ck("통수 = 내 메일 9통", r["rows"] == 9, r["rows"])
ck("6개월 안 · 거래처 = 4통(거래처 1 + 첨부 메일 3)", cells["a6|partner"]["n"] == 4, cells["a6|partner"])
ck("6개월 안 · 스팸 1", cells["a6|spam"]["n"] == 1)
ck("6~12개월 · 광고 1((광고) 제목)", cells["a12|bulk"]["n"] == 1)
ck("12개월 넘음 · 내부 업무 1(제작요청)", cells["old|work"]["n"] == 1)
ck("12개월 넘음 · 내부 기타 1", cells["old|internal"]["n"] == 1)
ck("12개월 넘음 · 자동 발송 주소 = 광고·알림 1", cells["old|bulk"]["n"] == 1)
ck("한 통씩 압축 < 본문", sum(c["body_z"] for c in cells.values()) < sum(c["body"] for c in cells.values()))
ck("같은 첨부 두 번 → 실제 크기는 한 번", cells["a6|partner"]["att_physical"] == len(JPG) + len(csv)
   and cells["a6|partner"]["att_logical"] == 2 * len(JPG) + len(csv), cells["a6|partner"])
ck("첨부: 이미 압축된 형식(jpg)·압축되는 형식(csv) 나눔", r["att"]["packed_bytes"] == len(JPG) and r["att"]["compressible_bytes"] == len(csv), r["att"])
ck("첨부: csv 실제로 압축해 봄(크게 줄어듦)", r["att"]["sample_n"] == 1 and r["att"]["sample_xz"] < r["att"]["sample_raw"] / 10, r["att"])
mb = r["month_bundle"]
ck("월별 묶음(6개월 넘은 것) 실제로 압축", mb["raw"] > 0 and 0 < mb["xz"] < mb["raw"], mb)
sv = r["server"]
ck("서버 전체: 두 사람 · 10통", sv["users"] == 2 and sv["mail_rows"] == 10, sv)
ck("서버 전체: 같은 본문 겹침 > 0(같은 공지 · 같은 반복 글)", sv["body_dup"] > 0, sv)
blob = json.dumps(r, ensure_ascii=False)
ck("⭐돌려주는 값에 제목·주소·내용이 없음(숫자만)", SECRET not in blob and "partner-demo" not in blob and "가짜 반복" not in blob)

# 상태 파일(일꾼 둘이어도 같은 답)
st = mst.start(_db.db_session, 9101, whole=False)
ck("시작 → running", st.get("state") == "running")
for _ in range(100):
    s2 = mst.status(9101)
    if s2.get("state") != "running":
        break
    time.sleep(0.1)
ck("상태 파일로 끝난 결과를 읽음", s2.get("state") == "done" and s2["result"]["rows"] == 9, s2.get("state"))
ck("상태 파일은 데이터 폴더(.mail_storage_9101.json)", os.path.exists(os.path.join(os.path.dirname(_db.DB_PATH), ".mail_storage_9101.json")))
print("결과: %d 통과 / %d 실패" % (len(P), len(F)))
