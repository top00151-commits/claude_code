# -*- coding: utf-8 -*-
"""z1191z107 시험 — 견적 관리 사업부 책갈피(대표 11-22 「관리번호를 형태별로 … 책갈피 형태로 전체, 검사기, 자동화,
라이프밸류, 소모품, 기타」 · 「소모품은 보기만」)
  §1 책갈피 여섯 · 숫자 · 사업부 판정(사업부 칸 → 비었으면 관리번호 4번째 글자 · 그 밖 = 기타)
  §2 책갈피 고르면 그 사업부만 · 요약 칸도 그 안에서만 · 다른 거르기 주소에 책갈피 유지
  §3 소모품 = 소모품 주문 보기만(올리기 없음 · 취소 빼고 · 입금 끝난 것은 기본 숨김) · 소모품 상세로 가는 줄
  §4 엑셀 내려받기도 같은 책갈피
"""
import contextlib
import io
import os
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z107-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z107_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
from datetime import date as _d                            # noqa: E402
T0 = _d.today().isoformat()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        conn.execute("INSERT INTO teams (id, code, name) VALUES (1, '01', '기술영업팀')")
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상영업', 'member', 'Z701', 'Z701', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 0, 0)")
    U = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z701'").fetchone())
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")
    CU = conn.execute("SELECT id FROM customers WHERE name='가상고객'").fetchone()[0]

    def proj(code, name, biz, sales="가상영업"):
        conn.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, currency, order_amount, order_date, "
                     "due_date, stage, sales_name, biz_div) VALUES (?, ?, ?, '가상고객', 'KRW', 1000, ?, ?, '수주확정', ?, ?)",
                     (code, name, CU, T0, T0, sales, biz))
        pid = conn.execute("SELECT id FROM projects WHERE mgmt_code=?", (code,)).fetchone()[0]
        no = "Z-" + code
        conn.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, total_amount, order_date, due_date, status) "
                     "VALUES (?, ?, ?, 'KRW', 1000, ?, ?, 'CONFIRMED')", (pid, no, CU, T0, T0))
        return pid

    proj("961T2611", "가상 검사기 하나", "T")
    proj("962T2611", "가상 검사기 둘", "T", "다른사람")
    proj("963M2611", "가상 자동화", "M")
    proj("964L2611", "가상 라이프", "L")
    proj("965E2611", "가상 기타", "E")
    proj("966R2611", "가상 연구", "R")          # 연구 → 기타
    proj("967M2611", "가상 칸 빈 자동화", "")    # 사업부 칸 빔 → 관리번호 4번째 글자 M

    def co(no, code, status, sales="가상영업"):
        conn.execute("INSERT INTO consumable_orders (co_no, mgmt_code, customer_id, customer_name, order_date, due_date, currency, "
                     "total_amount, status, sales_name, project_name, biz_div) VALUES (?, ?, ?, '가상고객', ?, ?, 'KRW', 500, ?, ?, '소모품 3종', 'T')",
                     (no, code, CU, T0, T0, status, sales))
        return conn.execute("SELECT id FROM consumable_orders WHERE co_no=?", (no,)).fetchone()[0]

    C1 = co("C-261122-1", "971C2611", "CONFIRMED")
    C2 = co("C-261122-2", "972C2611", "SHIPPED", "다른사람")
    C3 = co("C-261122-3", "973C2611", "PAID")
    C4 = co("C-261122-4", "974C2611", "CANCELLED")

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: U
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅", label)
    else:
        FAIL += 1
        print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:500])


def tab_n(h, label):
    i = h.find(label + ' <span class="n">')
    if i < 0:
        return None
    j = i + len(label + ' <span class="n">')
    return int(h[j:h.find("<", j)])


print("§1 책갈피 여섯 · 숫자 · 사업부 판정")
r = cl.get("/sales/quotations?period=all&mine=0")
h = r.text
check("열림 200", r.status_code == 200, r.status_code)
labels = ["전체", "🔬 검사기", "🤖 자동화", "💄 라이프밸류", "📦 소모품", "🌐 기타"]
pos = [h.find(l + ' <span class="n">') for l in labels]
check("책갈피 여섯이 대표 말씀 순서(전체·검사기·자동화·라이프밸류·소모품·기타)", all(p > 0 for p in pos) and pos == sorted(pos), pos)
got = {l: tab_n(h, l) for l in labels}
check("숫자: 전체 7 · 검사기 2 · 자동화 2(칸 빈 것 = 관리번호 글자) · 라이프 1 · 기타 2(연구 포함) · 소모품 2(취소·입금 끝 빼고)",
      got == {"전체": 7, "🔬 검사기": 2, "🤖 자동화": 2, "💄 라이프밸류": 1, "📦 소모품": 2, "🌐 기타": 2}, got)
check("전체 책갈피가 켜짐", 'class="qm-bt on" href="?period=all' in h, h[h.find('qm-biz'):h.find('qm-biz') + 400])
check("판정 함수", [M._z107_biz(b, c) for b, c in (("T", "x"), ("", "001M2611"), ("R", "001R2611"), ("", ""), ("c", ""))] == ["T", "M", "E", "E", "C"])

print("§2 책갈피 고르면 그 사업부만")
h = cl.get("/sales/quotations?period=all&mine=0&biz=M").text
check("자동화: 963M·967M 만", "963M2611" in h and "967M2611" in h and "961T2611" not in h and "964L2611" not in h)
check("요약 칸 = 자동화 안에서만(수주 2건)", '수주번호 견적서 있음</div><div class="n">0 <span style="font-size:13px;color:var(--qv-ink-3);font-weight:600;">/ 2건' in h)
check("요약 칸·거르기 주소에 책갈피 유지(biz=M)", 'href="?biz=M&period=all&mine=0&only=none"' in h and 'href="?biz=M&period=2y' in h, None)
check("검색 칸에도 책갈피 유지", '<input type="hidden" name="biz" value="M">' in h)
check("다른 책갈피 숫자는 그대로 보임", tab_n(h, "🔬 검사기") == 2 and tab_n(h, "📦 소모품") == 2)
h = cl.get("/sales/quotations?period=all&mine=0&biz=E").text
check("기타 = E + 연구(R)", "965E2611" in h and "966R2611" in h and "963M2611" not in h)
h = cl.get("/sales/quotations?period=all&mine=1&biz=T").text
check("👤 내 건만 + 검사기 = 961T 만 · 숫자도 내 건 기준", "961T2611" in h and "962T2611" not in h and tab_n(h, "🔬 검사기") == 1, tab_n(h, "🔬 검사기"))
h = cl.get("/sales/quotations?period=all&mine=0&biz=Q").text
check("모르는 책갈피 값 = 전체", "961T2611" in h and "963M2611" in h)
h = cl.get("/sales/quotations?period=all&mine=0&biz=T&q=" + "둘").text
check("검색 + 책갈피", "962T2611" in h and "961T2611" not in h and tab_n(h, "🔬 검사기") == 1)

print("§3 소모품 = 보기만")
h = cl.get("/sales/quotations?period=all&mine=0&biz=C").text
check("소모품 주문 줄 2개(진행중·출하) · 취소 · 입금 끝은 안 보임", "971C2611" in h and "972C2611" in h and "974C2611" not in h and "973C2611" not in h)
check("소모품 상세로 가는 줄", 'href="/consumables/%d"' % C1 in h)
check("보기만 안내 · 위 올리기 칸 없음 · 줄 올리기 단추 없음", "소모품 주문은 보기만" in h and 'id="qmTopDrop"' not in h and "qm-pick" not in h.split("qm-cons")[1].split("</table>")[0])
check("프로젝트 줄·요약 칸 안 보임", "961T2611" not in h and 'class="qm-kpis"' not in h)
check("상태 이름(진행중·출하)", "진행중" in h and "출하" in h)
check("입금 끝난 것 숨김 수 = 1", "1개 관리번호 숨김" in h)
h = cl.get("/sales/quotations?period=all&mine=0&biz=C&done=1").text
check("입금 끝난 수주도 보기 = 소모품 입금 끝도 보임", "973C2611" in h and "974C2611" not in h)
h = cl.get("/sales/quotations?period=all&mine=1&biz=C").text
check("👤 내 건만 = 내 소모품만", "971C2611" in h and "972C2611" not in h)

print("§4 엑셀 내려받기")
import openpyxl                                             # noqa: E402


def xl_rows(qs):
    rr = cl.get("/sales/quotations/export.xlsx" + qs)
    wb = openpyxl.load_workbook(io.BytesIO(rr.content))
    ws = wb.worksheets[0]
    return rr.status_code, [[c.value for c in row] for row in ws.iter_rows()]


st, rows = xl_rows("?period=all&mine=0&biz=M")
codes = {r[0] for r in rows if r and r[0]}
check("자동화 엑셀 = 자동화 관리번호만", st == 200 and "963M2611" in codes and "961T2611" not in codes, (st, codes))
st, rows = xl_rows("?period=all&mine=0&biz=C")
codes = {r[0] for r in rows if r and r[0]}
check("소모품 엑셀 = 소모품 주문 줄(보기만 표시)", st == 200 and "971C2611" in codes and "961T2611" not in codes
      and any("소모품(보기만)" in str(r[-1]) for r in rows), (st, codes))
st, rows = xl_rows("?period=all&mine=0")
codes = {r[0] for r in rows if r and r[0]}
check("전체 엑셀 = 프로젝트 관리번호(소모품 주문 없음 — 화면과 같음)", "961T2611" in codes and "971C2611" not in codes, codes)

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
