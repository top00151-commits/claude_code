# -*- coding: utf-8 -*-
"""z1191z105 시험 — 견적 관리 = 관리번호·수주번호별 최종 견적서(엑셀) 올리기·보기
(대표 11-22 「관리번호별, 수주번호별 최종 견적서(엑셀) 등록 또는 등록된 상태를 보는걸로 … 1호기 가격과 2호기, 3호기 가격이 다를수있어서」
 → 「1,2 추천대로(바꾸면 예전 것 지움 · 🆕 등록 견적서 카드 빼고 견적 관리로) · 3번(상세 올리기 단추)은 그대로」)
  §1 화면 · 요약 칸(없음 · 금액 다름 · 수주 전)
  §2 엑셀을 넣으면 후보 찾기(수주번호 · 관리번호+금액 · 고객사) · 붙이기 · 검색
  §3 금액 다름 → 「확인했음」 · 바꾸기 = 예전 파일 지움(파일·줄) · 이력에 누가
  §4 바꾸기 권한(남의 것 = 올린 사람·기술영업팀만)
  §5 상세 「＋ 견적서 엑셀 올리기」 = 대표 견적 자리(그대로 · 바꾸면 예전 것 지움) · 프로젝트 견적서 칸 = 대표 견적만 · 수주 카드 📋 견적서 줄
  §6 🆕 등록 카드 → 견적 관리 · 예전 견적서 작성 주소 → 견적 관리 · 메뉴 찾기 · 엑셀 내려받기 · 👤 내 건만
"""
import contextlib
import io
import json
import os
import re
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z105-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z105_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
    for tid, code, nm in ((1, "01", "기술영업팀"), (2, "02", "관리팀")):
        if not conn.execute("SELECT 1 FROM teams WHERE id=?", (tid,)).fetchone():
            if "code" in tcols:
                conn.execute("INSERT INTO teams (id, code, name) VALUES (?, ?, ?)", (tid, code, nm))
            else:
                conn.execute("INSERT INTO teams (id, name) VALUES (?, ?)", (tid, nm))
        else:
            conn.execute("UPDATE teams SET name=? WHERE id=?", (nm, tid))
    ins = ("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
           "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
           "VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', 1, 1, ?, 1, ?, 0, 0)")
    conn.execute(ins, ("가상영업", "Z501", "Z501", 1, 1))
    conn.execute(ins, ("가상영업둘", "Z502", "Z502", 1, 1))
    conn.execute(ins, ("가상관리", "Z503", "Z503", 2, 1))
    U = {k: dict(conn.execute("SELECT * FROM users WHERE employee_no=?", (k,)).fetchone()) for k in ("Z501", "Z502", "Z503")}
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 2)")
    conn.execute("INSERT INTO customers (name) VALUES ('가상수출고객')")
    CU = conn.execute("SELECT id FROM customers WHERE name='가상수출고객'").fetchone()[0]

    def proj(code, name, ccy, amt, od, sales):
        conn.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, currency, order_amount, order_date, "
                     "due_date, stage, sales_name) VALUES (?, ?, ?, '가상수출고객', ?, ?, ?, ?, '수주확정', ?)",
                     (code, name, CU, ccy, amt, od, od, sales))
        return conn.execute("SELECT id FROM projects WHERE mgmt_code=?", (code,)).fetchone()[0]

    def so(pid, no, ccy, amt, od, label):
        conn.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, total_amount, order_date, due_date, status) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFIRMED')", (pid, no, CU, ccy, amt, od, od))
        oid = conn.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
        conn.execute("INSERT INTO order_items (order_id, amount, unit_label) VALUES (?, ?, ?)", (oid, amt, label))
        return oid

    from datetime import date as _d
    T0 = _d.today().isoformat()
    PA = proj("951M2611", "가상 장비A", "USD", 45000, T0, "가상영업")
    O1 = so(PA, "Z-261101-1", "USD", 15000, T0, "1호기")
    O2 = so(PA, "Z-261101-2", "USD", 14000, T0, "2호기")
    O3 = so(PA, "Z-261102-1", "USD", 16000, T0, "3호기")
    PB = proj("952T2611", "가상 수주 전 장비", "KRW", 0, T0, "다른사람")

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

S = {"user": U["Z501"]}
M.get_user = lambda request: S["user"]
FAKE = {"fields": {}}
M._qr61.read_quote = lambda raw, name, pw="": {"ok": True, "fields": dict(FAKE["fields"]), "warnings": []}
cl = TestClient(M.app)
OK = FAIL = 0
XL = b"PK\x03\x04" + b"0" * 64


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅", label)
    else:
        FAIL += 1
        print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:500])


def read(name, fields):
    FAKE["fields"] = fields
    return cl.post("/api/project-quote/read", files={"file": (name, XL, "application/vnd.ms-excel")}).json()


def files_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT id, project_id, order_id, orig_name, stored, amt_ack_name FROM project_quote_files "
                                           "WHERE project_id=? ORDER BY id", (pid,)).fetchall()]


print("§1 화면")
r = cl.get("/sales/quotations?period=all")
h = r.text
check("열림 200", r.status_code == 200, r.status_code)
check("관리번호 줄 + 수주번호 줄 3개", h.count('class="so qm-slot"') == 3 and "951M2611" in h and "Z-261101-2" in h)
check("호기 표시(1호기·2호기·3호기)", all(x in h for x in ("1호기", "2호기", "3호기")))
check("수주 금액 $15,000.00", "$15,000.00" in h)
check("요약: 견적서 없음 3건", re.search(r"정말 없음</div><div class=\"n\">3건", h) is not None)
check("요약: 수주 전 1건", re.search(r"수주 전</div><div class=\"n\">1건", h) is not None)   # z1191z156: 「(관리번호만)」 뺌
check("올리기 칸(끌어다 놓기) 보임", 'id="qmTopDrop"' in h)

print("§2 엑셀을 넣으면 후보 찾기 · 붙이기")
j = read("견적_Z-261101-1_최종.xlsx", {"customer": "가상수출고객", "amount": 15000, "currency": "USD", "item_name": "장비A"})
check("읽기 ok · 표지(tok)", j.get("ok") and j.get("tok"), j)
c = cl.get("/api/quotes-z105/cands?tok=" + j["tok"]).json()
check("파일 이름의 수주번호로 후보 1개 · 미리 고름", c.get("pick") == 0 and len(c.get("cands") or []) == 1
      and c["cands"][0]["oid"] == O1 and "수주번호" in c.get("why", ""), c)
p = cl.post("/api/project-quote/place", data={"tok": j["tok"], "pid": PA, "order_id": O1}).json()
check("붙이기 ok(Z-261101-1)", p.get("ok") and p.get("replaced") == 0 and p.get("slot") == "Z-261101-1", p)
check("파일 줄 order_id = 1호기 수주", [f["order_id"] for f in files_of(PA)] == [O1], files_of(PA))
j2 = read("견적서 951M2611 2호기.xlsx", {"customer": "가상수출고객", "amount": 14000, "currency": "USD"})
c2 = cl.get("/api/quotes-z105/cands?tok=" + j2["tok"]).json()
# z1191z156: 관리번호 자리 없음 · 수주 2개 이상이면 빈칸으로 시작(금액 같음은 표시만)
check("관리번호로 찾기: 수주 3개만(관리번호 자리 없음) · 미리 안 고름 · 2호기 「금액 같음」",
      len(c2["cands"]) == 3 and c2["pick"] is None and [x["same"] for x in c2["cands"] if x["oid"] == O2] == [True], c2)
j3 = read("quote.xlsx", {"customer": "가상수출고객", "amount": 16000, "currency": "USD"})
c3 = cl.get("/api/quotes-z105/cands?tok=" + j3["tok"]).json()
check("고객사로 찾기: 후보 여럿 → 미리 안 고름 · 3호기 「금액 같음」(z1191z156)", c3["pick"] is None and [x["same"] for x in c3["cands"] if x["oid"] == O3] == [True], c3)
j4 = read("quote2.xlsx", {"customer": "없는회사", "amount": 1})
c4 = cl.get("/api/quotes-z105/cands?tok=" + j4["tok"]).json()
check("못 찾으면 후보 0 · 미리 고르지 않음", c4["cands"] == [] and c4["pick"] is None, c4)
s = cl.get("/api/quotes-z105/search?q=951M").json()
check("검색: 관리번호 → 대표 견적 + 수주 3줄", len(s["items"]) == 4 and s["items"][0]["oid"] is None, s)
p = cl.post("/api/project-quote/place", data={"tok": j3["tok"], "pid": PA, "order_id": O1 + 999}).json()
check("다른 관리번호의 수주번호로는 못 붙임", not p.get("ok"), p)

print("§3 금액 다름 · 확인했음 · 바꾸기")
p = cl.post("/api/project-quote/place", data={"tok": j2["tok"], "pid": PA, "order_id": O2}).json()
with D.db_session() as cc:
    cc.execute("UPDATE project_quote_files SET read_json=? WHERE order_id=?",
               (json.dumps({"fields": {"amount": 14500, "currency": "USD"}}), O2))
h = cl.get("/sales/quotations?period=all").text
check("2호기: 견적 $14,500.00 · 다름 알림", "견적 $14,500.00 · 다름" in h)
check("요약: 금액 다름 1건", re.search(r"⚠ 금액 다름\(확인 필요\)</div><div class=\"n\">1건", h) is not None)
fid2 = [f for f in files_of(PA) if f["order_id"] == O2][0]["id"]
a = cl.post("/api/project-quote/ack/%d" % fid2).json()
h = cl.get("/sales/quotations?period=all").text
check("확인했음 → 금액 다름 0건 · 누가 확인했는지 보임", a.get("ok") and re.search(r"⚠ 금액 다름\(확인 필요\)</div><div class=\"n\">0건", h)
      and "금액 다름 확인 " in h)
old = [f for f in files_of(PA) if f["order_id"] == O1][0]
old_fp = os.path.join(M._z61_dir(), old["stored"])
check("바꾸기 전 예전 파일이 디스크에 있음", os.path.isfile(old_fp))
j5 = read("1호기_최종_v2.xlsx", {"amount": 15000, "currency": "USD"})
p = cl.post("/api/project-quote/place", data={"tok": j5["tok"], "pid": PA, "order_id": O1}).json()
now = [f for f in files_of(PA) if f["order_id"] == O1]
check("바꾸기: 1호기 자리 1장(새 파일) · replaced 1", p.get("replaced") == 1 and [f["orig_name"] for f in now] == ["1호기_최종_v2.xlsx"], (p, now))
check("예전 파일은 디스크에서도 지움", not os.path.isfile(old_fp))
with D.db_session() as cc:
    hist = [r[0] for r in cc.execute("SELECT note FROM project_history WHERE project_id=? AND field='견적서 파일' ORDER BY id", (PA,))]
check("변경 이력: 올리기·바꾸기(예전 것 지움) 누가", any("견적 관리 「올리기」 · Z-261101-1" in n for n in hist)
      and any("견적서 바꾸기(예전 것 지움)" in n and "가상영업" in n for n in hist), hist[-3:])

print("§4 바꾸기 권한")
S["user"] = U["Z503"]   # 관리팀(매출 등록 권한 있음 · 기술영업팀 아님)
j6 = read("관리팀이_올림.xlsx", {"amount": 15000, "currency": "USD"})
p = cl.post("/api/project-quote/place", data={"tok": j6["tok"], "pid": PA, "order_id": O1}).json()
check("남이 올린 견적서는 관리팀이 못 바꿈(올린 사람·기술영업팀만)", not p.get("ok") and "기술영업팀" in (p.get("message") or ""), p)
p = cl.post("/api/project-quote/place", data={"tok": j6["tok"], "pid": PA, "order_id": O3}).json()
check("빈 자리(3호기)는 관리팀도 올림", p.get("ok"), p)
S["user"] = U["Z502"]   # 같은 기술영업팀 다른 사람
j7 = read("3호기_기술영업이_바꿈.xlsx", {"amount": 16000, "currency": "USD"})
p = cl.post("/api/project-quote/place", data={"tok": j7["tok"], "pid": PA, "order_id": O3}).json()
check("기술영업팀은 남이 올린 것도 바꿈", p.get("ok") and p.get("replaced") == 1, p)
p = cl.post("/api/project-quote/place", data={"tok": j6["tok"], "pid": PA, "order_id": O3}).json()
check("남의 표지(tok)로는 못 붙임", not p.get("ok"), p)
S["user"] = U["Z501"]

print("§5 상세 화면")
# z1191z156: 관리번호 자리 없음 — 수주 3개라 안 고르면 저장 안 함 · 고른 수주(2호기)에만 · 다시 올리면 그 수주 것만 바뀜
r0 = cl.post("/api/project-quote/attach/%d" % PA, files={"file": ("대표견적.xlsx", XL, "application/vnd.ms-excel")}).json()
r1 = cl.post("/api/project-quote/attach/%d" % PA, data={"order_id": O2}, files={"file": ("2호기견적.xlsx", XL, "application/vnd.ms-excel")}).json()
r2 = cl.post("/api/project-quote/attach/%d" % PA, data={"order_id": O2}, files={"file": ("2호기견적_v2.xlsx", XL, "application/vnd.ms-excel")}).json()
rep_rows = [f for f in files_of(PA) if f["order_id"] is None]
check("상세 「＋ 견적서 엑셀 올리기」 = 수주 안 고르면 멈춤 · 고른 수주 자리 1장(두 번째가 바꿈)", (not r0.get("ok")) and r0.get("need_so")
      and r1.get("ok") and r2.get("replaced") == 1 and rep_rows == [] and [f["orig_name"] for f in files_of(PA) if f["order_id"] == O2] == ["2호기견적_v2.xlsx"],
      (r0, r1, r2, files_of(PA)))
check("프로젝트 견적서 칸 = 수주번호마다 붙은 견적서 전부(z1191z156)", "2호기견적_v2.xlsx" in [x["orig_name"] for x in M._z61_quote_files(PA)]
      and all(x["order_id"] for x in M._z61_quote_files(PA)))
h = cl.get("/project/%d" % PA).text
check("상세: 「＋ 견적서 엑셀 올리기」 단추 그대로", "＋ 견적서 엑셀 올리기" in h)
check("상세 수주 카드: 📋 견적서 줄 · 1호기 파일 받기", "📋 견적서" in h and "🟢 1호기_최종_v2.xlsx" in h)   # z1191z121 👁 → z1191z141 🟢 이 수주 견적
h = cl.get("/sales/quotations?period=all").text
check("견적 관리: 관리번호 견적서 표시 없음 · 2호기 견적 보임(z1191z156)", "관리번호 견적서</span>" not in h and "2호기견적_v2.xlsx" in h)
# z1191z156: 2호기는 방금 「2호기견적_v2」(금액 못 읽음·다를 수 있음)로 바꿨으므로 있음/금액 다름 수는 고정하지 않고 「없음 0건」만
check("요약: 없음 0건(세 수주 모두 자기 견적)", re.search(r"정말 없음</div><div class=\"n\">0건", h) is not None)

print("§5b 입금 끝난 수주는 기본으로 숨김 · 부품 줄은 「품목 N줄」")
with D.db_session() as cc:
    cc.execute("UPDATE orders SET status='PAID' WHERE id=?", (O3,))
h = cl.get("/sales/quotations?period=all").text
check("입금 끝난 3호기 수주는 기본으로 안 보임", "Z-261102-1" not in h and "Z-261101-1" in h)
h = cl.get("/sales/quotations?period=all&done=1").text
check("「입금 끝난 수주도 보기」면 보임", "Z-261102-1" in h and "입금 끝난 수주도 보는 중" in h)
with D.db_session() as cc:
    cc.execute("UPDATE orders SET status='CONFIRMED' WHERE id=?", (O3,))
check("호기 줄 = 1호기~4호기 (4줄) · 부품 이름 줄 = 품목 N줄",
      M._z105_units_txt(["1호기", "2호기", "3호기", "4호기"]) == "1호기~4호기 (4줄)"
      and M._z105_units_txt(["DOOR SENSOR", "산업용 PC", "케이블"]) == "품목 3줄" and M._z105_units_txt(["1호기"]) == "1호기" and M._z105_units_txt(["1건", "2건"]) == "품목 2줄")

print("§6 연결·메뉴·엑셀")
r = cl.get("/sales/quotes/new", follow_redirects=False)
check("예전 견적서 작성 주소 → 견적 관리로", r.status_code == 303 and r.headers.get("location") == "/sales/quotations", (r.status_code, r.headers.get("location")))
h = cl.get("/projects/new").text
check("🆕 등록 카드 → 견적 관리(작성 화면 아님)", 'href="/sales/quotations"' in h and 'href="/sales/quotes/new"' not in h and "견적서(엑셀)" in h)
from app import menu_catalog as MC
row = [x for x in MC._RAW if x[0] == "M-01-02-N"]
check("메뉴 찾기: 견적서 올리기 = /sales/quotations", len(row) == 1 and row[0][3] == "/sales/quotations", row)
r = cl.get("/sales/quotations/export.xlsx?period=all")
check("엑셀 내려받기 200", r.status_code == 200 and r.content[:2] == b"PK", r.status_code)
h = cl.get("/sales/quotations?period=all&mine=1").text
check("👤 내 건만: 내 담당(951M2611)만 · 남의 건(952T2611) 숨김", "951M2611" in h and "952T2611" not in h)
cl.get("/sales/quotations?mine=0")
h = cl.get("/sales/quotations?period=all&only=none").text
check("없음만: 견적 없는 수주가 없으면 아무 관리번호도 안 남음(수주 전 관리번호는 올릴 자리가 없어 뺌 · z1191z156)", "952T2611" not in h and "951M2611" not in h)
r = cl.post("/api/project-quote/read", files={"file": ("사진.png", b"\x89PNG0000", "image/png")}).json()
check("엑셀 아닌 파일은 안 받음", not r.get("ok"), r)

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
