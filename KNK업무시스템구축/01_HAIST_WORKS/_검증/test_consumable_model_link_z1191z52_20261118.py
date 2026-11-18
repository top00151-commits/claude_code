# -*- coding: utf-8 -*-
"""z1191z52 시험 (대표 2026-11-18 「연결 장비 모델 자동」 · 2차 2-4)
  소모품 요청서 품목 표 「모델명」 = 줄의 연결 장비 모델명 · 줄에 모델 입력 칸은 없음(z730 그대로)
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
from datetime import date, timedelta
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z52-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z52_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()


def ins(c, table, row):
    cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % table)}
    ks = [k for k in row if k in cols]
    c.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, ",".join('"%s"' % k for k in ks), ",".join("?" * len(ks))), [row[k] for k in ks])
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


FUT = (date.today() + timedelta(days=14)).isoformat()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    TEAM = ins(c, "teams", {"name": "가상검사기팀", "code": "T49", "entity": "KOR", "display_order": 1})
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T950', 'T950', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T950'").fetchone())
    for i in (1, 2):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id) VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', 1, 1, ?)",
                  ("가상받는이%d" % i, "T95%d" % i, "T95%d" % i, TEAM))
    CU = ins(c, "customers", {"name": "한국가상전(주)", "alias": "가상전"})
    CU2 = ins(c, "customers", {"name": "다른고객(주)", "alias": "다른"})

    def proj(code, cust=CU, **kw):
        row = {"code": code, "name": "PBA", "mgmt_code": code, "customer_id": cust, "customer_name": ("한국가상전(주)" if cust == CU else "다른고객(주)"), "currency": "KRW",
               "status": "수주확정", "biz_div": "T", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "order_date": "2026-11-13", "due_date": FUT, "is_archived": 0,
               "unit_qty": 1, "model_name": "VPL-" + code[:3], "equip_name": "가상 검사기 " + code[:3], "cc_name": "정가상", "cc_position": "계장", "engraving": "ENG-" + code[:3]}
        row.update(kw)
        return ins(c, "projects", row)

    def order(pid, no, po, label, created, status="CONFIRMED"):
        return ins(c, "orders", {"order_no": no, "customer_id": CU, "order_date": created[:10], "due_date": FUT, "total_amount": 1000, "status": status,
                                 "created_at": created, "project_id": pid, "unit_label": label, "unit_qty": 1, "currency": "KRW", "so_type": "EQUIPMENT", "po_type": po})
    A = proj("020T2611", server_path="Z:\\가상전\\TSP\\VPL\\9. 제품자료"); OA = order(A, "T-261113-5", "신규", "1호기", "2026-11-16 09:47:00")
    B = proj("021T2611"); OB = order(B, "T-261113-6", "신규", "1호기", "2026-11-16 09:48:00")
    Cc = proj("022T2611", engraving=""); OC = order(Cc, "T-261113-7", "신규", "1호기", "2026-11-16 09:49:00")
    Dd = proj("023T2611"); OD1 = order(Dd, "T-261113-8", "신규", "1호기", "2026-11-16 09:50:00"); OD2 = order(Dd, "T-261117-3", "추가", "2호기", "2026-11-17 09:00:00")
    E = proj("010T2609", order_date="2026-09-01"); OE = order(E, "T-260901-1", "신규", "1호기", "2026-09-01 10:00:00")       # 같은 고객사 · 다른 날
    F = proj("030T2611")                                                                                                # 같은 날 · 수주 없음 → 못 묶음
    G = proj("031T2611", cust=CU2); OG = order(G, "T-261113-9", "신규", "1호기", "2026-11-16 10:00:00")                    # 다른 고객사 → 못 묶음
    H = proj("032T2611", is_archived=1); OH = order(H, "T-261113-10", "신규", "1호기", "2026-11-16 10:00:00")              # 폐기 → 못 묶음
    S1 = proj("040T2611", order_date="2026-11-14"); OS1 = order(S1, "T-261114-1", "신규", "1호기", "2026-11-16 11:00:00")  # 따로 발행할 것

import app.main as M  # noqa: E402
import app.sso_client as SSO  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
CARDS = []
SSO.notify_via_messenger = lambda emp_nos, title, body, link, card=None, **k: (CARDS.append({"emp": list(emp_nos or []), "title": title, "body": body, "card": card}) or {"ok": True, "sent": len(emp_nos or [])})
with D.db_session() as c:
    _have = {r[1] for r in c.execute("PRAGMA table_info(prod_requests)")}
    for _col in ("recipients", "wt_team_ids", "user_ids", "updated_at", "updated_by_name", "dept_names", "sent_to", "dept_count",
                 "msg_sent", "created_date", "issued_by_name", "cust_req", "note", "mgmt_code", "issued_by", "team_ids"):
        if _col not in _have:
            c.execute("ALTER TABLE prod_requests ADD COLUMN %s TEXT" % _col)
    ins(c, "prod_requests", {"project_id": E, "mgmt_code": "010T2609", "cust_req": "예전 요청", "created_at": "2026-09-01 11:00", "created_date": "2026-09-01", "issued_by_name": "가상관리자"})
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,)))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def view(h):
    m = re.search(r'<div id="prqView">(.*?)<div class="z48-mob">', h, re.S)
    return m.group(1) if m else ""


def rows(h):
    """품목 줄들: [[No, 관리코드, 수주번호, 호기, 모델명, 품명, 수량, 일정], …] + 노란 칠 줄 번호"""
    out, me = [], []
    for m in re.finditer(r'<tr( class="[^"]*")?><td>(\d+)</td>(.*?)</tr>', view(h), re.S):
        cells = [re.sub(r"<[^>]+>", " ", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", m.group(3), re.S)]
        if len(cells) == 7:
            out.append([m.group(2)] + cells)
            if m.group(1) and "z49-me" in m.group(1):
                me.append(m.group(2))
    return out, me


def prq(where="1=1", args=()):
    with D.db_session() as c:
        return [tuple(r) for r in c.execute("SELECT id, project_id, COALESCE(bundle_id,0), COALESCE(order_ids,''), COALESCE(cust_req,''), COALESCE(gist,''), COALESCE(bundle_model,'') "
                                            "FROM prod_requests WHERE " + where + " ORDER BY id", args)]


def notif_n():
    with D.db_session() as c:
        return c.execute("SELECT COUNT(*) FROM notifications WHERE kind='prod_request'").fetchone()[0]


with D.db_session() as c:
    CO1 = ins(c, "consumable_orders", {"co_no": "C-261117-1", "mgmt_code": "010C2611", "customer_name": "가상고객 인도", "customer_id": CU, "currency": "USD", "total_amount": 1000,
                                       "status": "CONFIRMED", "order_date": "2026-11-17", "due_date": FUT, "model_name": "소모품", "equip_name": "인도 소모품 3종"})
    ins(c, "consumable_order_items", {"co_id": CO1, "line_no": 1, "part_name": "PCB", "spec": "KNK-P-4963", "qty": 2, "unit": "EA", "linked_project_id": A})
    ins(c, "consumable_order_items", {"co_id": CO1, "line_no": 2, "part_name": "PINBLOCK", "spec": "KNK-SM-S957 SUB-AP1", "qty": 1, "unit": "EA", "linked_project_id": Dd})
    ins(c, "consumable_order_items", {"co_id": CO1, "line_no": 3, "part_name": "POGOPIN", "spec": "SP100F", "qty": 400, "unit": "EA"})
    ins(c, "consumable_order_items", {"co_id": CO1, "line_no": 4, "part_name": "러버", "spec": "R-1", "qty": 4, "unit": "EA", "model_use": "옛줄모델", "linked_project_id": A})
    CO2 = ins(c, "consumable_orders", {"co_no": "C-261117-2", "mgmt_code": "011C2611", "customer_name": "가상고객 인도", "customer_id": CU, "currency": "KRW", "total_amount": 1,
                                       "status": "CONFIRMED", "order_date": "2026-11-17", "due_date": FUT, "model_name": "VPL-HEAD", "equip_name": "헤드"})
    ins(c, "consumable_order_items", {"co_id": CO2, "line_no": 1, "part_name": "PCB", "spec": "X-1", "qty": 1, "unit": "EA"})


def co_rows(h):
    ts = re.findall(r'<table class="z48-prs z48-desk">.*?</table>', h, re.S)   # 머리 칸 표 · 품목 표 순
    t = ts[1] if len(ts) > 1 else ""
    out = []
    for tr in re.findall(r"<tr>\s*<td>(\d+)</td>(.*?)</tr>", t, re.S):
        cells = [re.sub(r"<[^>]+>", " ", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr[1], re.S)]
        out.append([tr[0]] + [re.sub(r"\s+", " ", x) for x in cells])
    return out


print("§1 소모품 요청서 모델명 = 연결 장비 모델")
h = q(cl.get, "/consumables/%d/prod-request" % CO1).text
rw = co_rows(h)
mi = 1   # 사진이 없는 소모품 → 칸: 모델명 · 품명 · 수량 · 납기 · 연결 장비
models = [r[mi] for r in rw] if rw else []
check(models[:4] == ["VPL-020", "VPL-023", "—", "옛줄모델"], "줄 모델명: 연결 장비 020T2611 → VPL-020 · 023T2611 → VPL-023 · 연결 없음 → — · 옛 자료에 줄 모델이 있으면 그것", rw)
check(">소모품<" not in "".join(models), "대표 모델명 「소모품」을 모델명처럼 찍지 않음")
mob = h[h.find('<div class="z48-mob">'):]
check("VPL-020 · 연결 장비" in re.sub(r"<[^>]+>", "", mob) and "VPL-023 · 연결 장비" in re.sub(r"<[^>]+>", "", mob), "휴대폰 카드에도 연결 장비 모델명")
h2 = q(cl.get, "/consumables/%d/prod-request" % CO2).text
rw2 = co_rows(h2)
check(rw2 and "VPL-HEAD" in rw2[0], "연결 장비가 없고 대표 모델명이 실제 모델이면 그것(지금과 같음)", rw2)
hd = q(cl.get, "/consumables/%d" % CO1)
check(hd.status_code == 200 and 'data-k="model_use"' not in hd.text, "소모품 상세 줄 표에는 모델 칸이 여전히 없음(z730 그대로)")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
