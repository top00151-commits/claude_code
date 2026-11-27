# -*- coding: utf-8 -*-
"""z1191z181 시험 — 남은 「처음 등록 값」 화면(수주 기준) + 저장 순간 통화·거래구분 알림이 없던 길 3곳

임시 DB(실제 운영 DB 아님) · TestClient. 실제와 같은 모양:
  관리번호 911T2601 — 등록 고객 = SAMSUNG INDIA(처음 등록 때 값) · 수주 3건:
      OA SAMSUNG INDIA · USD 3,000 · 2026-02-10 / OB 삼성전자 · KRW 5,000,000 · 2026-03-01 / OX KNK VINA · 취소
  관리번호 912T2601 — 수주 없음 · 등록 고객 「BRAVO INDIA」(수주 없는 관리번호만 등록 값)
  관리번호 913T2601 — 등록 고객 = 삼성전자 · 수주 1건 = SAMSUNG INDIA(같은 날 2026-02-10) → 묶음 후보
  관리번호 914T2601 — 등록 고객 = SAMSUNG INDIA · 수주 1건 = 삼성전자만 → SAMSUNG INDIA 묶음 후보 아님
  관리번호 915T2601 — 수주 1건 · 발주일 빈칸(호기도 빈칸) · 등록 발주일 2026-04-04 → 매출 「처음 등록 발주일로 셈」
  A §1 진행 대시보드·진행 상세 · §2 진행률 찾기 · §3 고객사 목록 정렬·건수 · §4 묶음 후보 · §5 관리자 표 · §6 매출 발주일 · §7 책갈피
  B §8 새 관리번호 등록(추가 발주) · §9 엑셀 일괄 등록 확정 · §10 정보 수정 — 저장은 됨 · 알림 · 확인한 것은 안 뜸
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z181-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z181_")
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


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    TEAM = ins(c, "teams", {"name": "기술영업팀", "code": "01", "entity": "KOR", "display_order": 1})
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales, "
              "can_view_logistics, can_use_logistics) VALUES ('가상대표', 'ceo', 'Z181', 'Z181', 'sso_only_no_local_password', 1, 1, ?, 1, 1, 1, 1)", (TEAM,))
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='Z181'").fetchone())
    c.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', ?)", (TEAM,))
    CU1 = ins(c, "customers", {"name": "SAMSUNG INDIA ELECTRONICS PVT. LTD.", "alias": "SAMSUNG INDIA", "tier_score": 0})
    CU2 = ins(c, "customers", {"name": "삼성전자(주)", "alias": "삼성전자", "tier_score": 0})
    CU3 = ins(c, "customers", {"name": "KNK VINA CO., LTD", "alias": "KNK VINA", "tier_score": 0})
    CU4 = ins(c, "customers", {"name": "BRAVO INDIA PVT LTD", "alias": "BRAVO INDIA", "tier_score": 0})

    def proj(code, cu, cname, od="2026-02-10", ccy="USD", amt=100000, iex=1):
        return ins(c, "projects", {"code": code, "mgmt_code": code, "name": "가상 " + code, "customer_id": cu, "customer_name": cname,
                                   "po_type": "신규", "is_export": iex, "currency": ccy, "order_amount": amt, "order_date": od,
                                   "due_date": "2026-06-16", "status": "진행중", "stage": "진행", "biz_div": "T", "project_type": "NEW_EQUIP",
                                   "shipment_form": "ASSEMBLY", "model_name": "M-" + code, "equip_name": "가상 검사기", "unit_qty": 1,
                                   "is_archived": 0, "sales_name": "가상대표"})

    def so(pid, no, cu, ccy, st, od, lines, amt=None):
        oid = ins(c, "orders", {"project_id": pid, "order_no": no, "customer_id": cu, "currency": ccy,
                                "total_amount": amt if amt is not None else 1000 * len(lines),
                                "order_date": od, "due_date": "2026-06-16", "status": st, "po_type": "신규", "end_customer": "",
                                "unit_qty": len(lines), "so_type": "EQUIPMENT", "created_at": (od or "2026-01-01") + " 09:00:00"})
        ids = []
        per = (amt if amt is not None else 1000 * len(lines)) / max(1, len(lines))
        for lb, iex, ust in lines:
            ids.append(ins(c, "order_items", {"order_id": oid, "qty": 1, "unit_price": per, "amount": per, "unit_label": lb, "is_export": iex,
                                              "currency": ccy, "unit_status": ust}))
        return oid, ids

    P = proj("911T2601", CU1, "SAMSUNG INDIA ELECTRONICS PVT. LTD.")
    OA, _ = so(P, "T-260210-1", CU1, "USD", "CONFIRMED", "2026-02-10", [("1호기", 1, "진행중")], amt=3000)
    OB, _ = so(P, "T-260301-1", CU2, "KRW", "CONFIRMED", "2026-03-01", [("2호기", 0, "진행중")], amt=9000000)
    OX, _ = so(P, "T-260302-9", CU3, "KRW", "CANCELLED", "2026-03-02", [("3호기", 0, "진행중")], amt=7000000)
    P2 = proj("912T2601", CU4, "BRAVO INDIA PVT LTD")
    P3 = proj("913T2601", CU2, "삼성전자(주)")
    O3, _ = so(P3, "T-260210-3", CU1, "USD", "CONFIRMED", "2026-02-10", [("1호기", 1, "진행중")], amt=1000)
    P4 = proj("914T2601", CU1, "SAMSUNG INDIA ELECTRONICS PVT. LTD.")
    O4, _ = so(P4, "T-260210-4", CU2, "KRW", "CONFIRMED", "2026-02-10", [("1호기", 0, "진행중")], amt=1000)
    P5 = proj("915T2601", CU2, "삼성전자(주)", od="2026-04-04", ccy="KRW", amt=2000, iex=0)
    O5, _ = so(P5, "T-260404-5", CU2, "KRW", "CONFIRMED", "", [("1호기", 0, "진행중")], amt=2000)
    c.execute("UPDATE projects SET status='진행중' WHERE id IN (?,?,?,?,?)", (P, P2, P3, P4, P5))
    for _mm in range(1, 13):
        ins(c, "exchange_rates", {"rate_date": "2026-%02d-01" % _mm, "from_currency": "USD", "to_currency": "KRW", "rate": 1300})

import app.main as M                                        # noqa: E402
import app.project_workflow as PW                           # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

_WHO = {"u": ADMIN}
M.get_user = lambda request: _WHO["u"]
M._can_manual_mgmt = lambda u: True
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
cl = TestClient(M.app)
OKN = FAIL = 0


def check(label, cond, got=None):
    global OKN, FAIL
    if cond:
        OKN += 1
        print("  ✅", label)
    else:
        FAIL += 1
        print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:700])


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or ""))


def get(url):
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.get(url)
    return r.status_code, r.text


def seg(html, key, n=1500):
    i = html.find(key)
    return text(html[i:i + n]) if i >= 0 else ""


# ─────────────────────────────────────────
print("§1 진행 대시보드 · 진행 상세 — 고객사·수주액 = 수주")
st, H = get("/progress-dashboard")
cd = seg(H, "911T2601", 2500)
check("카드 고객사 = 수주 1차 「SAMSUNG INDIA 외 1곳」(취소 수주 KNK VINA 빠짐)", st == 200 and "고객사 SAMSUNG INDIA 외 1곳" in cd and "KNK VINA" not in cd, cd[:400])
check("카드 수주액 = 통화별 수주 합계($3,000 · ₩9,000,000 — 처음 등록 금액 100,000 아님 · 취소 7,000,000 빠짐)",
      "3,000" in cd and "9,000,000" in cd and "100,000" not in cd and "7,000,000" not in cd, cd[:400])
cd2 = seg(H, "912T2601", 1500)
check("수주 없는 관리번호 = 등록 고객 그대로(BRAVO INDIA)", "BRAVO INDIA" in cd2, cd2[:300])
st, H = get("/progress/%d" % P)
mt = seg(H, "관리코드 <b>911T2601", 600)
check("진행 상세 머리 고객사 = 「SAMSUNG INDIA 외 1곳」", st == 200 and "SAMSUNG INDIA 외 1곳" in mt, mt[:300])
st, H = get("/progress/%d" % P2)
check("진행 상세(수주 없음) = 등록 고객", st == 200 and "BRAVO INDIA" in seg(H, "관리코드 <b>912T2601", 600))

# ─────────────────────────────────────────
print("§2 진행률 표 고객사로 찾기 = 수주 고객")
codes = lambda xs: sorted(x["mgmt_code"] for x in xs)   # noqa: E731
check("「삼성전자」 → 수주 고객이 삼성전자인 911·914·915(등록 고객이 삼성전자라도 수주가 SAMSUNG INDIA 뿐인 913 빠짐)",
      codes(D.progress_matrix(customer="삼성전자")) == ["911T2601", "914T2601", "915T2601"], codes(D.progress_matrix(customer="삼성전자")))
check("「KNK VINA」(취소 수주에만) → 없음", codes(D.progress_matrix(customer="KNK VINA")) == [], codes(D.progress_matrix(customer="KNK VINA")))
check("「BRAVO」 → 수주 없는 912(등록 고객)", codes(D.progress_matrix(customer="BRAVO")) == ["912T2601"], codes(D.progress_matrix(customer="BRAVO")))

# ─────────────────────────────────────────
print("§3 고객사 목록 정렬·건수 = 수주마다 1차 고객")
with D.db_session() as c:
    c.execute("UPDATE customers SET tier_score=0")   # 등급 점수(시작 때 다시 셈)를 같게 — 금액 순서만 본다
st, H = get("/customers")
order = [int(x) for x in re.findall(r'data-cid="(\d+)"', H)]
order = [x for i, x in enumerate(order) if x not in order[:i]]
check("목록 순서(같은 등급 점수) = 원화 환산 큰 순: BRAVO(수주 없음 · 등록 $100,000) → 삼성전자(수주 ₩9,003,000) → SAMSUNG INDIA(수주 $4,000 ≈ ₩5,200,000) → KNK VINA(취소만 = 0) · "
      "(예전: 등록 고객으로 세어 SAMSUNG INDIA $200,000 이 맨 앞)", st == 200 and order == [CU4, CU2, CU1, CU3], order)

# ─────────────────────────────────────────
print("§4 제작요청서 묶음 후보 — 대표 판단 대기(고른 수주 고객으로 좁힐지 · 11-27) · 이번 배포에선 예전 그대로라 건너뜀")
if False:
    with D.db_session() as c:
        pa = dict(c.execute("SELECT * FROM projects WHERE id=?", (P3,)).fetchone())
        cands = M._z49_candidates(c, pa, {P3})
    ids = [d["id"] for d in cands]
    check("913(수주 고객 SAMSUNG INDIA) 후보 = 911(SAMSUNG INDIA 수주 있음) · 914(등록 고객만 SAMSUNG INDIA · 수주는 삼성전자) 빠짐",
          P in ids and P4 not in ids, ids)
    dd = [d for d in cands if d["id"] == P]
    check("911 = 같은 발주일(수주 2026-02-10) 권함 · 화면 발주 글자 = 수주 발주일 「2026-03-01 외 1건」",
          dd and dd[0]["same_day"] and dd[0]["so_date181"] == "2026-03-01 외 1건", dd and {k: dd[0].get(k) for k in ("same_day", "so_date181", "suggest")})
    with D.db_session() as c:
        pb = dict(c.execute("SELECT * FROM projects WHERE id=?", (P4,)).fetchone())
        ids4 = [d["id"] for d in M._z49_candidates(c, pb, {P4})]
    check("914(수주 고객 삼성전자) 후보 = 911·915(삼성전자 수주) · 913(등록 고객 삼성전자 · 수주 SAMSUNG INDIA) 빠짐", P in ids4 and P5 in ids4 and P3 not in ids4, ids4)
    st, H = get("/project/%d/prod-request/edit?new=1" % P3)
    check("작성 화면 후보 줄 「발주 2026-03-01 외 1건」", st == 200 and "발주 2026-03-01 외 1건" in text(H), st)

    # ─────────────────────────────────────────

print("§5 관리자 화면(/admin/console) 프로젝트 표")
st, H = get("/admin/console")
i = H.find(">911T2601<")
rw = text(H[i:H.find("</tr>", i)]) if i >= 0 else ""
check("고객사 「SAMSUNG INDIA 외 1곳」 · 수주액 통화별($3,000 · ₩9,000,000)", st == 200 and "SAMSUNG INDIA 외 1곳" in rw and "3,000" in rw and "9,000,000" in rw and "100,000" not in rw, rw[:300])
i = H.find(">912T2601<")
rw2 = text(H[i:H.find("</tr>", i)]) if i >= 0 else ""
check("수주 없는 관리번호 = 등록 고객·등록 금액", "BRAVO INDIA" in rw2 and "100,000" in rw2, rw2[:300])

# ─────────────────────────────────────────
print("§6 매출 — 수주 발주일 빈칸 = 처음 등록 발주일로 셈(계산 그대로 · 화면에 밝힘)")
with D.db_session() as c:
    fb = M._z181_od_fb(c, "2026", "year", "1", "1")
    fb_all = M._z181_od_fb(c)
    fb_25 = M._z181_od_fb(c, "2025", "year", "1", "1")
    rates = M._fx_load_rates(c)
    oi_map, _pi = M._board_tax_oi_map()
    k = M._sales_3way(c, rates, oi_map, "month", "2026", "2", "4")["kpi"]
check("찾음 = 915 수주 한 건(2026-04-04) · 다른 해는 없음", [x["so"] for x in fb] == ["T-260404-5"] and fb[0]["pdate"] == "2026-04-04" and len(fb_all) == 1 and not fb_25, (fb, fb_25))
check("계산은 그대로 — 2026년 4월 수주매출에 915 금액 ₩2,000 이 들어 있음", abs(float(k.get("order") or 0) - 2000) < 0.5, k.get("order"))
st, H = get("/sales")
check("매출 홈에 「📅 수주 발주일이 빈 수주 1건 — 처음 등록 발주일로 셈(금액은 그대로)」 + 수주번호", st == 200 and "수주 발주일이 빈 수주 1건 — 처음 등록 발주일로 셈(금액은 그대로)" in H and "T-260404-5" in H, st)
st, H = get("/sales?mode=year&year=2025")
check("다른 해(2025) = 알림 없음", st == 200 and "수주 발주일이 빈 수주" not in H, st)
st, H = get("/sales/glance")
check("한눈에 보기에도 같은 알림", st == 200 and "처음 등록 발주일로 셈" in H, st)
st, H = get("/sales/report?mode=year&year=2026")
check("매출 보고서에도 같은 알림", st == 200 and "처음 등록 발주일로 셈" in H, st)
check("화면 글에 「대표값」「관리번호 값」 없음", "대표값" not in text(H) and "관리번호 값" not in text(H))

# ─────────────────────────────────────────
print("§7 프로젝트 목록 📎 견적서·발주서 책갈피 — 고객사 = 수주")
src = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "docs_board_z150.html"), encoding="utf-8").read()
check("책갈피 고객 칸 = so165(프로젝트 목록과 같은 수주 요약) · 수주 없는 줄만 등록 고객(z165-ok)", "_s181 = (so165|default({},true)).get(p.id)" in src and "z165-ok: 수주 없는 관리번호만" in src)


# ─────────────────────────────────────────
def warn_api(oids):
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.get("/api/trade-ccy-warn?oids=" + ",".join(str(x) for x in oids))
    return r.json().get("trade_ccy_warn") or [], r.headers.get("X-KNK-Trade-Warn")


def ack(oid):
    with D.db_session() as c:
        w = {x["order_id"]: x for x in PW.trade_ccy_mismatch(c, order_ids=[oid])}.get(oid)
    with contextlib.redirect_stdout(io.StringIO()):
        return cl.post("/api/trade-ccy-ack/%d" % oid, data={"sig": w["sig"]}).json()


print("§8 새 관리번호 등록 화면(추가 발주) 제출 → 상세로 돌아가며 바로 알림")
base = {"quick": "1", "po_type": "추가", "mgmt_code": "911T2601", "biz_div": "T", "name": "가상 911T2601", "model": "M1", "equip_name": "E1",
        "order_date": "2026-11-27", "due_date": "2026-12-27", "unit_price": "1000", "unit_qty": "1", "currency": "USD", "shipment_form": "ASSEMBLY",
        "is_export": "0", "stage": "진행중", "status": "진행중", "customer_name": "SAMSUNG INDIA ELECTRONICS PVT. LTD.", "customer_id": str(CU1), "fx_rate": "1300"}
with D.db_session() as c:
    n0 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P,)).fetchone()[0]
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/projects/new", data=base, follow_redirects=False)
loc = r.headers.get("location", "")
with D.db_session() as c:
    nw = c.execute("SELECT id, currency FROM orders WHERE project_id=? ORDER BY id DESC LIMIT 1", (P,)).fetchone()
    n1 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P,)).fetchone()[0]
NEW8 = nw[0] if nw else 0
check("저장은 됨(수주 1건 늘어남 · USD)", n1 == n0 + 1 and nw[1] == "USD", (n0, n1, nw and tuple(nw)))
m8 = re.search(r"[?&]tcw178=([0-9,]+)", loc)
check("돌아가는 주소 = /project/911… 에 tcw178=새 수주 id(그 수주만 · 원래 있던 OA·OB 없음)", r.status_code == 303 and loc.startswith("/project/%d" % P) and m8 and m8.group(1) == str(NEW8), loc)
ws, hd = warn_api([NEW8])
check("상세가 묻는 곳 → 알림 1건 「💱 외화(USD) 수주인데 내수 품목 1줄」 · 머리 X-KNK-Trade-Warn", len(ws) == 1 and ws[0]["msg"] == "💱 외화(USD) 수주인데 내수 품목 1줄" and hd == "1", (ws, hd))
st, H = get(loc)
check("돌아간 상세 화면 200 · 공용 knk_busy 가 tcw178 을 읽는 코드", st == 200 and "tcw178=" in H and "/api/trade-ccy-warn?oids=" in H, st)
check("「확인했음」 저장", ack(NEW8).get("ok"))
ws, hd = warn_api([NEW8])
check("확인한 수주 = 다시 물어도 안 뜸(머리 없음)", ws == [] and hd is None, (ws, hd))
b2 = dict(base, currency="KRW", order_date="2026-11-28")
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/projects/new", data=b2, follow_redirects=False)
check("맞는 저장(KRW·내수) = 주소에 표시 없음", r.status_code == 303 and "tcw178" not in r.headers.get("location", ""), r.headers.get("location"))

NEWB = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중", "confirm_now": "1",
        "order_date": "2026-07-01", "due_date": "2026-08-01", "currency": "USD", "fx_rate": "1300", "is_export": "0",
        "equip_name": "가상장비", "unit_qty": "1", "model": "가상모델", "prod_mode": "none", "unit_price": "1000", "order_amount": "1000",
        "unit_label[]": "1호기", "unit_amount[]": "1000", "shipment_form": "ASSEMBLY", "project_name": "가상 새 관리번호", "customer_name": "BRAVO INDIA PVT LTD", "customer_id": str(CU4), "sales": "가상대표"}
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/projects/new", data=NEWB, follow_redirects=False)
loc = r.headers.get("location", "")
mp = re.match(r"/project/(\d+)", loc)
with D.db_session() as c:
    nos = [tuple(x) for x in c.execute("SELECT id, currency FROM orders WHERE project_id=?", (int(mp.group(1)) if mp else 0,))]
check("새 관리번호(수주 확정 동시) 저장은 됨 · 수주 USD 1건", mp and len(nos) == 1 and nos[0][1] == "USD", (loc, nos))
mn = re.search(r"[?&]tcw178=([0-9,]+)", loc)
check("새 관리번호도 돌아가는 주소에 tcw178=그 수주 → 묻는 곳 알림 1건", mn and nos and mn.group(1) == str(nos[0][0]) and len(warn_api([nos[0][0]])[0]) == 1, loc)

# ─────────────────────────────────────────
print("§9 엑셀 일괄 등록 확정 → 응답에 알림")
rows = [{"mgmt_code_input": "913T2601", "biz_div": "T", "name": "가상 913T2601", "model_name": "ADD", "unit_qty": 1, "unit_price": 1000,
         "amount": 1000, "currency": "USD", "order_date": "2026-09-03", "due_date": "2026-10-01", "po_type": "추가", "form_type": "완제품",
         "shipment_form": "ASSEMBLY", "status": "진행중", "_followup": True, "_errors": [], "is_export": "내수",
         "customer_name": "SAMSUNG INDIA", "row_no": 3, "note": "엑셀 줄"}]
with D.db_session() as c:
    n0 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P3,)).fetchone()[0]
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/projects/import-confirm", json={"rows": rows})
jj = r.json()
with D.db_session() as c:
    nw9 = c.execute("SELECT id FROM orders WHERE project_id=? ORDER BY id DESC LIMIT 1", (P3,)).fetchone()
    n1 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P3,)).fetchone()[0]
NEW9 = nw9[0] if nw9 else 0
check("저장은 됨(913 수주 1건 늘어남 · 응답 ok · 실패 0)", jj.get("ok") and n1 == n0 + 1 and not jj.get("failed"), (jj.get("failed"), n0, n1))
tw = jj.get("trade_ccy_warn") or []
check("응답 trade_ccy_warn = 새 수주 하나(외화+내수) · 머리 X-KNK-Trade-Warn=1 · 미리 있던 수주(O3) 안 섞임",
      [w["order_id"] for w in tw] == [NEW9] and tw[0]["kind"] == "fx_dom" and r.headers.get("X-KNK-Trade-Warn") == "1", (tw, r.headers.get("X-KNK-Trade-Warn")))
check("응답의 원래 칸(created_count 등)은 그대로", "created_count" in jj and "so_warnings" in jj, list(jj)[:8])
check("「확인했음」 → 다시 물어도 안 뜸", ack(NEW9).get("ok") and warn_api([NEW9])[0] == [])

# ─────────────────────────────────────────
print("§10 프로젝트 정보 수정 제출 → 상세로 돌아가며 바로 알림")
with D.db_session() as c:
    P6 = ins(c, "projects", {"code": "916T2601", "mgmt_code": "916T2601", "name": "가상 916", "customer_id": CU2, "customer_name": "삼성전자(주)",
                             "po_type": "신규", "is_export": 0, "currency": "KRW", "order_amount": 1000, "order_date": "2026-05-01",
                             "due_date": "2026-06-16", "status": "진행중", "stage": "진행", "biz_div": "T", "project_type": "NEW_EQUIP",
                             "shipment_form": "ASSEMBLY", "model_name": "M6", "equip_name": "가상 검사기", "unit_qty": 1, "is_archived": 0})
    O6 = ins(c, "orders", {"project_id": P6, "order_no": "T-260501-6", "customer_id": CU2, "currency": "KRW", "total_amount": 1000,
                           "order_date": "2026-05-01", "due_date": "2026-06-16", "status": "CONFIRMED", "po_type": "신규", "unit_qty": 1, "so_type": "EQUIPMENT"})
    ins(c, "order_items", {"order_id": O6, "qty": 1, "unit_price": 1000, "amount": 1000, "unit_label": "1호기", "is_export": 0, "currency": "KRW", "unit_status": "진행중"})
f = {"unlock_verified": "1", "name": "가상 916", "customer_name": "삼성전자(주)", "customer_id": str(CU2), "biz_div": "T", "project_type": "NEW_EQUIP",
     "po_type": "신규", "status": "진행중", "equip_name": "가상 검사기", "model": "M6", "shipment_form": "ASSEMBLY", "currency": "USD", "is_export": "0",
     "unit_qty": "1", "order_amount": "1000", "order_date": "2026-05-01", "due_date": "2026-06-16", "fx_rate": "1300"}
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/projects/%d/edit" % P6, data=f, follow_redirects=False)
loc = r.headers.get("location", "")
with D.db_session() as c:
    occy = c.execute("SELECT currency FROM orders WHERE id=?", (O6,)).fetchone()[0]
    pccy = c.execute("SELECT currency FROM projects WHERE id=?", (P6,)).fetchone()[0]
check("저장은 됨(관리번호 통화 USD · 수주 하나라 수주 통화도 USD)", pccy == "USD" and occy == "USD", (pccy, occy))
m10 = re.search(r"[?&]tcw178=([0-9,]+)", loc)
check("돌아가는 주소 /project/916… 에 tcw178=그 수주", r.status_code == 303 and loc.startswith("/project/%d" % P6) and m10 and m10.group(1) == str(O6), loc)
ws, _hd = warn_api([O6])
check("알림 = 「💱 외화(USD) 수주인데 내수 품목 1줄」", len(ws) == 1 and ws[0]["kind"] == "fx_dom", ws)
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/projects/%d/edit" % P6, data=dict(f, name="가상 916 이름만"), follow_redirects=False)
check("같은 불일치 그대로 다시 저장(이름만 고침) = 새로 생긴 것이 아니라 주소 표시 없음(상세 수주 카드에는 그대로 보임)",
      r.status_code == 303 and "tcw178" not in r.headers.get("location", ""), r.headers.get("location"))
check("「확인했음」 → 안 뜸", ack(O6).get("ok") and warn_api([O6])[0] == [])
with D.db_session() as c:
    iex = c.execute("SELECT is_export FROM order_items WHERE order_id=?", (O6,)).fetchone()[0]
check("값은 저절로 안 바뀜(품목 거래구분 내수 그대로)", iex == 0, iex)
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/api/trade-ccy-warn?oids=abc,%d" % O6)
check("묻는 곳: 숫자 아닌 값은 무시 · 확인한 것 빠짐", r.status_code == 200 and (r.json().get("trade_ccy_warn") or []) == [], r.text[:200])

print("\n결과: 통과 %d · 실패 %d" % (OKN, FAIL))
sys.exit(1 if FAIL else 0)
