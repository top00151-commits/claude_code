# -*- coding: utf-8 -*-
"""z1191z108 시험 — 매출 홈 「진행 중인 프로젝트」 창 「출하 전 / 전체」 풍선
(대표 11-22 「출하 전/전체 이게 무슨 뜻이지? 마우스 포인트 올리면 설명 보이게 해줘」)
  §1 머리글에 마우스 풍선(뜻 · 예) · 공용 풍선(data-fx-tip) 사용
  §2 줄마다 풍선 = 전체 · 아직 출하 전 · 출하 끝 · 보류(있을 때만) 숫자
"""
import contextlib
import html as _h
import io
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z108-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z108_")
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
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상대표', 'ceo', 'Z108', 'Z108', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z108'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")
    CU = conn.execute("SELECT id FROM customers WHERE name='가상고객'").fetchone()[0]

    def proj(code, sts):
        conn.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, currency, order_amount, order_date, due_date, "
                     "stage, biz_div) VALUES (?, '가상 장비', ?, '가상고객', 'KRW', 1000, ?, ?, '수주확정', ?)", (code, CU, T0, T0, code[3]))
        pid = conn.execute("SELECT id FROM projects WHERE mgmt_code=?", (code,)).fetchone()[0]
        conn.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, total_amount, order_date, due_date, status) "
                     "VALUES (?, ?, ?, 'KRW', 1000, ?, ?, 'CONFIRMED')", (pid, "Z-" + code, CU, T0, T0))
        oid = conn.execute("SELECT id FROM orders WHERE order_no=?", ("Z-" + code,)).fetchone()[0]
        for i, st in enumerate(sts):
            conn.execute("INSERT INTO order_items (order_id, amount, unit_label, unit_status, due_date) VALUES (?, 100, ?, ?, ?)",
                         (oid, "%d호기" % (i + 1), st, T0))

    proj("981T2611", ["", "", "출하", "출하", "보류"])   # 전체 5 · 출하 전 2 · 출하 끝 2 · 보류 1
    proj("982M2611", ["", "", ""])                     # 3 / 3

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: CEO
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


r = cl.get("/sales")
h = r.text
check("매출 홈 열림 200", r.status_code == 200, r.status_code)
tips = [_h.unescape(t) for t in re.findall(r'data-fx-tip="([^"]*)"', h)]

print("§1 머리글 풍선")
head = [t for t in tips if t.startswith("출하 전 / 전체 —")]
check("머리글 「출하 전 / 전체」에 풍선 한 개", len(head) == 1 and '>출하 전 / 전체</span></th>' in h, len(head))
ht = head[0] if head else ""
check("뜻: 출하 전 = 아직 출하 안 한 호기·품목 · 전체 = 수주된 전체(출하 포함 · 취소 뺌)",
      "출하 전 = 아직 출하하지 않은 호기·품목 수" in ht and "이미 출하한 것 포함" in ht and "취소된 수주는 뺌" in ht)
check("예 · 보류 설명", "15 / 15 = 15개 모두 아직 출하 전" in ht and "(보류 N)" in ht)
check("키보드로 와도 보임(tabindex)", 'tabindex="0" data-fx-tip="출하 전 / 전체' in h)
check("공용 풍선 장치가 화면에 있음", "window.__knkFxTipZ104" in h)

print("§2 줄마다 풍선")
t1 = [t for t in tips if t.startswith("981T2611 —")]
check("보류 있는 줄: 전체 5 · 출하 전 2 · 출하 끝 2 · 보류 1",
      len(t1) == 1 and "전체 5개" in t1[0] and "아직 출하 전 2개" in t1[0] and "출하 끝 2개" in t1[0] and "보류 1개" in t1[0], t1)
t2 = [t for t in tips if t.startswith("982M2611 —")]
check("보류 없는 줄: 3 / 3 · 출하 끝 0 · 보류 줄 없음",
      len(t2) == 1 and "전체 3개" in t2[0] and "아직 출하 전 3개" in t2[0] and "출하 끝 0개" in t2[0] and "보류" not in t2[0], t2)
check("숫자 모양 그대로(굵은 출하 전 / 전체)", "<b>2</b> / 5</span>" in h and "<b>3</b> / 3</span>" in h)

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
