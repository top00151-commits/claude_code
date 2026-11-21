# -*- coding: utf-8 -*-
"""z1191z92 시험 — 기술영업팀 전원 사용 전 P0 (대표 11-21 「P0 7가지 먼저 진행해」) 세션 01 몫 5가지
  §1 P0-2 메뉴: 매출·영업 첫 줄 「🆕 등록」(→ /projects/new) · 맨 아래 「📖 처음이면」 안내 · 등록 폼에 있을 때 「🆕 등록」에 불
  §2 P0-5 고객 PO 번호: 등록 폼에 칸이 보이고(한 번만) · 등록하면 프로젝트(customer_po)에 저장(수주 표엔 PO 칸 없음) · 수정 화면에 값이 보이는 칸
  §3 P0-6 👤 내 건만: 이름 맞춤(직책·띄어쓰기·여럿) · 프로젝트 목록 줄 표시 · 작업 일정표 거름 · 내 계정에 기억 · 내 건 0이면 단추 없음
  §4 P0-1 미수 화면 띠: 정리 전이면 미수금·납품·수금·채권 노화·매출 분석에 띠 · 'ar_baseline_done'=1 이면 사라짐
  §5 P0-7 안내 화면: /sales/flow-guide 200 · 단계 7개 · 화면 단추 이름이 실제 화면 글자와 같음
"""
import contextlib
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z92-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z92_")
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
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
        if "code" in tcols:
            conn.execute("INSERT INTO teams (id, code, name) VALUES (1, '01', '기술영업팀')")
        else:
            conn.execute("INSERT INTO teams (id, name) VALUES (1, '기술영업팀')")
    # 기술영업팀 일반 직원(실제 4명과 같은 권한 모양) — 이름 「가상영업」
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상영업', 'member', 'Z921', 'Z921', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 0, 0)")
    SALES = dict(conn.execute("SELECT u.*, t.name AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE employee_no='Z921'").fetchone())
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상관리자', 'ceo', 'Z922', 'Z922', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z922'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")
    # 작업 일정표·프로젝트 목록을 보려면 매출 금액 열람 정책(기술영업 팀)이 있어야 함 — 시드에 없으면 넣음
    try:
        conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")
    except Exception as e:
        print("  (정책 표 준비 건너뜀)", e)

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

S = {"user": SALES}
M.get_user = lambda request: S["user"]
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "T", "project_type": "NEW_EQUIP",
        "po_type": "신규", "status": "진행중", "confirm_now": "1", "order_date": "2026-11-21",
        "due_date": "2026-12-20", "currency": "KRW", "equip_name": "가상장비", "unit_qty": "1",
        "model": "가상모델", "prod_mode": "none", "unit_price": "1000000", "order_amount": "1000000"}


def post(**kw):
    f = dict(BASE)
    f.update(kw)
    return q(cl.post, "/projects/new", data=f, follow_redirects=False)


print("§1 메뉴")
h = q(cl.get, "/sales").text
sb = re.findall(r'<a class="sb-item[^"]*" href="([^"]+)"', h)
check("매출·영업 첫 줄 매출 홈 — 그다음 「🆕 등록」(z1191z97 대표 11-22 순서)", sb[:2] == ["/sales", "/projects/new"], sb[:3])
check("매출·영업 맨 아래 「📖 처음이면 — 등록부터 입금까지」(/sales/flow-guide) · 묶음 머리 글자는 그대로",
      bool(sb) and sb[sb.index("/export") + 1 if "/export" in sb else 0] == "/sales/flow-guide" and "📖 처음이면 — 등록부터 입금까지" in h
      and '<div class="sb-group">매출·영업</div>' in h, sb)
hq = q(cl.get, "/projects/quick?biz_div=T").text
m = re.search(r'<a class="sb-item active" href="([^"]+)"', hq)
check("등록 폼(/projects/quick)에 있을 때 「🆕 등록」에 불", bool(m) and m.group(1) == "/projects/new", m.group(1) if m else None)

print("§2 고객 PO 번호")
check("등록 폼에 「고객 PO 번호」 칸이 보임(이름 customer_po 한 번만)",
      "고객 PO 번호" in hq and hq.count('name="customer_po"') == 1 and 'type="hidden" name="customer_po"' not in hq,
      hq.count('name="customer_po"'))
r = post(project_name="PO칸시험", customer_po="PO-4500123", sales="가상영업")
check("등록 보내기 = 303 · 프로젝트 화면으로(오류 아님)", r.status_code == 303 and r.headers.get("location", "").startswith("/project/"), (r.status_code, r.headers.get("location")))
with D.db_session() as c:
    pr = c.execute("SELECT id, customer_po FROM projects WHERE name='PO칸시험'").fetchone()
check("프로젝트에 고객 PO 번호 저장", bool(pr) and pr[1] == "PO-4500123", pr and pr[1])
PID = pr[0] if pr else 0
he = q(cl.get, "/projects/%d/quick-edit" % PID).text
check("수정 화면에 값이 보이는 칸으로(숨은 칸 아님 · 한 번만)",
      'id="qCustPo"' in he and 'value="PO-4500123"' in he and he.count('name="customer_po"') == 1, he.count('name="customer_po"'))

print("§3 👤 내 건만")
k = M._is_mine_z92
U = {"name": "가상영업"}
check("이름 맞춤: 같은 이름 · 직책 붙음 · 띄어쓰기 · 여럿 중 하나",
      k(U, "가상영업") and k(U, "가상영업 프로") and k(U, " 가상 영업 ") and k(U, "다른사람/가상영업"))
check("다른 이름·일부만 같은 이름·빈칸은 아님",
      not k(U, "가상영") and not k(U, "가상영업부") and not k(U, "") and not k({"name": "이"}, "이"))
check("실제 모양: 「이현」 ≠ 「이현우」 · 「이해림 이사」 = 이해림", (not k({"name": "이현"}, "이현우")) and k({"name": "이해림"}, "이해림 이사"))
post(project_name="남의건", sales="다른사람")
hp = q(cl.get, "/projects").text
check("프로젝트 목록 「👤 내 건만 1」 단추", re.search(r'👤 내 건만 <b>1</b>', hp) is not None)
check("줄마다 내 건 표시(data-mine 1 · 0 둘 다)", 'data-mine="1"' in hp and 'data-mine="0"' in hp)
hp1 = q(cl.get, "/projects?mine=1").text
check("누르면 켜짐(window.__projMine = true)", "window.__projMine = true;" in hp1)
hp2 = q(cl.get, "/projects").text
check("다음에 열어도 기억(내 계정)", "window.__projMine = true;" in hp2)
hs = q(cl.get, "/sales/schedule?ym=2026-11").text
check("작업 일정표도 같은 기억으로 내 건만(남의건 안 보임)", "PO칸시험" in hs and "남의건" not in hs and 'id="sbMineBtn"' in hs,
      ("PO칸시험" in hs, "남의건" in hs, 'id="sbMineBtn"' in hs))
hs0 = q(cl.get, "/sales/schedule?ym=2026-11&mine=0").text
check("다시 누르면(mine=0) 전체", "PO칸시험" in hs0 and "남의건" in hs0)
check("끈 것도 기억 → 프로젝트 목록도 꺼짐", "window.__projMine = false;" in q(cl.get, "/projects").text)
S["user"] = CEO
hc = q(cl.get, "/projects").text
check("내 이름 건이 0이면 단추 없음(대표 계정)", 'id="projMineBtn"' not in hc)
S["user"] = SALES

print("§4 미수 화면 띠")
for path in ("/sales/outstanding", "/sales/shipments-receipts", "/sales/aging", "/sales/dashboard"):
    r = q(cl.get, path)
    check("%s — 정리 전 띠" % path, r.status_code == 200 and "아래 미수 숫자는 아직 실제 미수가 아닙니다" in r.text, r.status_code)
ho = q(cl.get, "/sales/orders").text
check("수주 목록 미수금 칸에 「입금 기록 정리 전」", "입금 기록 정리 전" in ho)
with D.db_session() as c:
    c.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('ar_baseline_done', '1')")
check("정리 끝 표시(ar_baseline_done=1) → 띠 사라짐",
      "아래 미수 숫자는 아직 실제 미수가 아닙니다" not in q(cl.get, "/sales/outstanding").text
      and "입금 기록 정리 전" not in q(cl.get, "/sales/orders").text)
with D.db_session() as c:
    c.execute("DELETE FROM app_settings WHERE key='ar_baseline_done'")

print("§5 안내 화면")
r = q(cl.get, "/sales/flow-guide")
g = r.text
check("/sales/flow-guide 200 · 단계 7개", r.status_code == 200 and g.count('class="fg-no"') == 7, (r.status_code, g.count('class="fg-no"')))
check("기술영업팀 직원에게 🔧 수동발행 안내가 보임", "🔧 수동발행" in g)
check("입금 확인 단계 = 입금 확인 화면 안내(z94) + 정리 전 경고", "입금 확인 — 예정일 된 고객사" in g and "아직 실제와 다릅니다" in g)
# 안내에 적은 단추 이름이 실제 화면 글자와 같은지(템플릿 원문으로 확인)
T = os.path.join(ROOT, "app", "templates")
src = ""
for fn in ("schedule_board.html", "prod_request_edit.html", "project_quick_form.html", "_v5_partials/prq_default_rcpt.html", "sales_home.html"):
    src += io.open(os.path.join(T, fn), encoding="utf-8").read()
src = re.sub(r"<span class=\"ti\">([^<]*)</span>\s*", r"\1 ", src)
names = ["🔁 수정발행 · 부서 다시 통보", "🚫 취소 발행", "🚚 일괄출하", "📄 묶어 발행", "⚙ 도구 ▾", "지금 고른 것을 기본으로 저장", "📊 매출 보고서", "＋ 등록", "🔧 수동발행"]
miss = [n for n in names if n not in src]
check("안내의 단추 이름 9개 = 실제 화면 글자", not miss, miss)
check("안내에도 그 이름 그대로", all(n in g for n in names), [n for n in names if n not in g])
S["user"] = dict(SALES, can_view_sales=0, can_use_sales=0, role="member")
r = q(cl.get, "/sales/flow-guide", follow_redirects=False)
check("매출 보기 권한 없으면 홈으로(안내 붙여)", r.status_code == 303 and "no_perm=sales" in r.headers.get("location", ""), (r.status_code, r.headers.get("location")))

print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
