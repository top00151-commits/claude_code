# -*- coding: utf-8 -*-
"""z1191z55 시험 (대표 2026-11-18 「제작요청서 목록 묶음」)
  ① 카드 = 제작요청서 한 장 — 수주 16건 관리번호에 요청서 1장이면 카드 1장(가리키는 수주만)
  ② 묶음 발행 = 카드 1장 · 「외 N건」 · 카드 안에 관리번호·수주마다 줄 · 누르면 대표 줄 요청서
  ③ 묶음에서 뺀 줄 · 취소한 요청서 = 「🚫 취소」 · 폐기 프로젝트 안 보임
  ④ 사업부·기간·검색은 그대로(묶음은 구성원 관리번호·수주번호로도 찾힘 · 가리키지 않는 수주번호로는 안 찾힘)
  ⑤ 한 건짜리 카드는 지금과 같음 · 소모품 카드 그대로
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
from datetime import date, datetime, timedelta, timezone
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z55-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z55_")
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
NOW = datetime.now(timezone(timedelta(hours=9)))
TODAY = NOW.strftime("%Y-%m-%d")
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T955', 'T955', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T955'").fetchone())
    CU = ins(c, "customers", {"name": "한국가상전(주)", "alias": "가상전"})

    def proj(code, **kw):
        row = {"code": code, "name": "PBA", "mgmt_code": code, "customer_id": CU, "customer_name": "한국가상전(주)", "currency": "KRW",
               "status": "수주확정", "biz_div": code[3], "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "order_date": "2026-11-13", "due_date": FUT,
               "is_archived": 0, "unit_qty": 1, "model_name": "VPL-" + code[:3], "equip_name": "가상 장비 " + code[:3]}
        row.update(kw)
        return ins(c, "projects", row)

    def order(pid, no, created, due=FUT, qty=1, st="진행중", status="CONFIRMED"):
        oid = ins(c, "orders", {"order_no": no, "customer_id": CU, "order_date": created[:10], "due_date": due, "total_amount": 1000, "status": status,
                                "created_at": created, "project_id": pid, "unit_label": "1호기", "unit_qty": 1, "currency": "KRW", "so_type": "EQUIPMENT", "po_type": "신규"})
        iid = ins(c, "order_items", {"order_id": oid, "qty": qty, "unit_price": 1, "amount": qty})
        c.execute("UPDATE order_items SET unit_status=? WHERE id=?", (st, iid))
        return oid

    def preq(pid, code, created, order_ids="", bundle_id=None, **kw):
        row = {"project_id": pid, "mgmt_code": code, "cust_req": "요청", "created_at": created, "created_date": created[:10],
               "issued_by_name": "가상발행자", "order_ids": order_ids, "bundle_id": bundle_id}
        row.update(kw)
        return ins(c, "prod_requests", row)

    # ① 수주 16건 관리번호 · 요청서는 셋째 수주만 가리킴
    P16 = proj("028T2601", order_date="2026-01-05")
    O16 = [order(P16, "T-2601%02d-1" % (i + 1), "2026-01-%02d 09:00:00" % (i + 1), qty=2) for i in range(16)]
    R16 = preq(P16, "028T2601", "2026-11-10 10:00", order_ids=str(O16[2]))
    # ② 묶음 4건(대표 020 · 구성원 021·022·023) · 023 은 수주 2건 중 첫째만 가리킴
    A = proj("020T2611"); OA = order(A, "T-261113-5", "2026-11-16 09:47:00", due="2026-12-01", qty=1)
    B = proj("021T2611"); OB = order(B, "T-261113-6", "2026-11-16 09:48:00", due="2026-11-28", qty=2, st="출하")
    Cc = proj("022T2611"); OC = order(Cc, "T-261113-7", "2026-11-16 09:49:00", qty=2)
    Dd = proj("023T2611"); OD1 = order(Dd, "T-261113-8", "2026-11-16 09:50:00", qty=2); OD2 = order(Dd, "T-261117-3", "2026-11-17 09:00:00", qty=1)
    LEAD = preq(A, "020T2611", TODAY + " 09:10", order_ids=str(OA), bundle_model="VPL2132_2138")
    c.execute("UPDATE prod_requests SET bundle_id=? WHERE id=?", (LEAD, LEAD))
    preq(B, "021T2611", TODAY + " 09:10", order_ids=str(OB), bundle_id=LEAD, bundle_model="VPL2132_2138")
    preq(Cc, "022T2611", TODAY + " 09:10", order_ids=str(OC), bundle_id=LEAD, bundle_model="VPL2132_2138")
    preq(Dd, "023T2611", TODAY + " 09:10", order_ids=str(OD1), bundle_id=LEAD, bundle_model="VPL2132_2138")
    # ③ 묶음에서 뺀 줄(024) · 취소한 한 건(050) · 폐기 프로젝트(060)
    X = proj("024T2611"); OX = order(X, "T-261113-11", "2026-11-16 09:51:00")
    RX = preq(X, "024T2611", TODAY + " 09:10", order_ids=str(OX), bundle_id=LEAD, cancel_kind="remove", cancelled_at=TODAY + " 09:30", cancel_reason="묶음에서 뺌")
    K = proj("050T2611"); OK1 = order(K, "T-261115-1", "2026-11-15 09:00:00")
    RK = preq(K, "050T2611", "2026-11-15 10:00", order_ids=str(OK1), cancelled_at="2026-11-15 11:00", cancel_kind="cancel", cancel_reason="중복 발행")
    Z = proj("060T2611", is_archived=1); OZ = order(Z, "T-261116-9", "2026-11-16 09:00:00")
    preq(Z, "060T2611", "2026-11-16 10:00", order_ids=str(OZ))
    # ④ 자동화 한 건(옛 요청서 · order_ids 없음 → 발행 시각까지 등록된 가장 늦은 수주) · 수주 없는 프로젝트
    Mm = proj("001M2607", order_date="2026-07-07", model_name="자동화모델", equip_name="가상 자동화")
    OM1 = order(Mm, "M-260707-1", "2026-07-07 09:00:00", status="SHIPPED", st="출하"); OM2 = order(Mm, "M-260901-1", "2026-09-01 09:00:00")
    RM = preq(Mm, "001M2607", "2026-07-07 14:57")
    N0 = proj("070T2611", unit_qty=3)
    RN = preq(N0, "070T2611", "2026-11-12 10:00")
    # ⑤ 소모품
    ins(c, "consumable_orders", {"co_no": "C-261117-1", "mgmt_code": "010C2611", "customer_id": CU, "customer_name": "한국가상전(주)", "order_date": "2026-11-17", "status": "CONFIRMED"})
    # 묶음 7건 넘는 것(줄 접기) — 다른 고객사·다른 날이라 위와 안 섞임
    BIG = []
    for i in range(8):
        pid = proj("08%dE2611" % i, order_date="2026-11-01")
        BIG.append((pid, order(pid, "E-261101-%d" % (i + 1), "2026-11-01 09:0%d:00" % i)))
    BL = preq(BIG[0][0], "080E2611", "2026-11-01 10:00", order_ids=str(BIG[0][1]))
    c.execute("UPDATE prod_requests SET bundle_id=? WHERE id=?", (BL, BL))
    for pid, oid in BIG[1:]:
        preq(pid, "08xE2611", "2026-11-01 10:00", order_ids=str(oid), bundle_id=BL)

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
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


def txt(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()


def cards(url):
    r = q(cl.get, url)
    assert r.status_code == 200, (url, r.status_code)
    h = r.text
    out = []
    for part in h.split('<a class="prq-card"')[1:]:
        part = part[:part.find("</a>")]
        href = re.search(r'href="([^"]+)"', part).group(1)
        cells = [txt(x) for x in re.findall(r'<td class="pc-v"[^>]*>(.*?)</td>', part, re.S)]
        lines = [[txt(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)] for tr in re.findall(r"<tr>(.*?)</tr>", part.split('class="pc-lines"')[1], re.S)] if 'class="pc-lines"' in part else []
        st = re.findall(r'class="pc-st2 pc-st-\w+">([^<]*)<', part)
        qty = re.search(r'class="pc-rc pc-qtyv">(.*?)</td>', part, re.S)
        out.append({"href": href, "mgmt": cells[0] if cells else "", "so": cells[1] if len(cells) > 1 else "", "model": cells[2] if len(cells) > 2 else "",
                    "equip": cells[3] if len(cells) > 3 else "", "due": cells[5] if len(cells) > 5 else "", "lines": lines, "st": st[0] if st else "",
                    "qty": txt(qty.group(1)) if qty else "", "raw": part})
    return out, h


def find(cs, mg):
    return [x for x in cs if x["mgmt"].split()[0] == mg]


print("§1 카드 = 제작요청서 한 장")
cs, h = cards("/prod-requests")
c16 = find(cs, "028T2601")
check(len(c16) == 1, "수주 16건 관리번호(028T2601)에 요청서 1장 → 카드 1장(전에는 16장)", len(c16))
check(c16 and c16[0]["so"] == "T-260103-1" and not c16[0]["lines"] and c16[0]["qty"] == "수량 2", "카드의 수주번호 = 요청서가 가리키는 수주(셋째) · 줄 없음 · 수량은 그 수주만", c16 and (c16[0]["so"], c16[0]["qty"]))
check(c16 and c16[0]["href"] == "/project/%d/prod-request/edit?prid=%d" % (P16, R16), "누르면 그 제작요청서", c16 and c16[0]["href"])

print("§2 묶음 발행 = 카드 1장")
cb = [x for x in cs if x["mgmt"].startswith("020T2611")]
check(len(cb) == 1 and not find(cs, "021T2611") and not find(cs, "022T2611") and not find(cs, "023T2611"), "묶음 4건 → 카드 1장(구성원 관리번호 카드 따로 없음)", [x["mgmt"] for x in cs])
b0 = cb[0] if cb else {"mgmt": "", "so": "", "lines": [], "href": "", "model": "", "due": "", "st": "", "qty": ""}
check("외 3건" in b0["mgmt"] and "외 3건" in b0["so"], "관리번호·수주번호 칸에 「외 3건」", (b0["mgmt"], b0["so"]))
check(b0["model"] == "VPL2132_2138", "모델명 = 묶음 이름", b0["model"])
ln = b0["lines"]
check([x[0] for x in ln] == ["020T2611", "021T2611", "022T2611", "023T2611"] and [x[1] for x in ln] == ["T-261113-5", "T-261113-6", "T-261113-7", "T-261113-8"],
      "카드 안 줄 = 관리번호·수주마다(대표 먼저 · 023 은 가리킨 수주 하나만 · T-261117-3 안 나옴)", ln)
check(ln and [x[3] for x in ln] == ["1", "2", "2", "2"] and [x[4] for x in ln] == ["진행중", "출하", "진행중", "진행중"], "줄마다 수량·상태", ln)
check(b0["qty"] == "수량 7" and b0["st"] == "진행중" and b0["due"] == "2026-11-28", "카드 수량 = 줄 합(7) · 상태 = 모아서(진행중) · 납품일 = 가장 이른 것", (b0["qty"], b0["st"], b0["due"]))
check(b0["href"] == "/project/%d/prod-request/edit?prid=%d" % (A, LEAD), "누르면 대표 줄 요청서(같은 한 장)", b0["href"])
check("T-261113-11" not in b0["raw"], "묶음에서 뺀 관리번호(024)는 묶음 카드에 없음")
cg = [x for x in cs if x["mgmt"].startswith("080E2611")]
check(len(cg) == 1 and len(cg[0]["lines"]) == 6 + 1 and "외 2줄" in cg[0]["lines"][-1][0], "8건 묶음 → 줄 6개 + 「… 외 2줄 — 눌러서 전체 보기」", cg and cg[0]["lines"])

print("§3 취소 · 뺀 줄 · 폐기")
cx = find(cs, "024T2611")
check(len(cx) == 1 and "🚫 취소" in cx[0]["mgmt"] and cx[0]["href"].endswith("prid=%d" % RX), "묶음에서 뺀 줄 = 자기 카드 「🚫 취소」", cx and cx[0]["mgmt"])
ck = find(cs, "050T2611")
check(len(ck) == 1 and "🚫 취소" in ck[0]["mgmt"], "취소한 요청서 = 「🚫 취소」", ck and ck[0]["mgmt"])
check(not find(cs, "060T2611"), "폐기 프로젝트는 안 보임")

print("§4 한 건짜리 · 옛 요청서 · 수주 없음 · 소모품")
cm = find(cs, "001M2607")
check(len(cm) == 1 and cm[0]["so"] == "M-260707-1" and cm[0]["st"] == "출하" and not cm[0]["lines"], "옛 요청서(가리킨 수주 저장 없음) → 발행 때 있던 수주 한 장(M-260901-1 카드 안 생김)", cm and (cm[0]["so"], cm[0]["st"]))
cn = find(cs, "070T2611")
check(len(cn) == 1 and cn[0]["so"] == "—" and cn[0]["qty"] == "수량 3", "수주 없는 프로젝트 → 수주 「—」 · 프로젝트 수량", cn and (cn[0]["so"], cn[0]["qty"]))
cc = find(cs, "010C2611")
check(len(cc) == 1 and cc[0]["href"].startswith("/consumables/") and cc[0]["so"] == "C-261117-1", "소모품 카드 그대로", cc and cc[0]["href"])
n_cards = len(cs)
check(n_cards == 8, "전체 카드 = 요청서 장수(028 · 묶음 · 024 · 050 · 001M · 070 · 080E 묶음 · 소모품 = 8장)", [x["mgmt"] for x in cs])
m = re.search(r"제작요청서 <b>(\d+)</b>장 · 수주 <b>(\d+)</b>건", h)
check(m and m.group(1) == "8" and m.group(2) == str(1 + 4 + 1 + 1 + 1 + 0 + 8 + 1), "위 글 = 「제작요청서 8장 · 수주 17건」", m and m.groups())
check("카드 = 제작요청서 한 장" in h and "카드 = 수주 1건" not in h, "안내 글도 바뀜")

print("§5 사업부 · 기간 · 검색")
cs_m, _ = cards("/prod-requests?biz=M")
check([x["mgmt"].split()[0] for x in cs_m] == ["001M2607"], "자동화만 → 001M2607 한 장", [x["mgmt"] for x in cs_m])
cs_t, _ = cards("/prod-requests?biz=T")
check(any(x["mgmt"].startswith("020T2611") for x in cs_t) and not any(x["mgmt"].startswith("080E") for x in cs_t) and not find(cs_t, "010C2611"), "검사기만 → 묶음 카드 있음 · 기타·소모품 없음")
cs_d, _ = cards("/prod-requests?period=day")
check(sorted(x["mgmt"].split()[0] for x in cs_d) == ["020T2611", "024T2611"], "오늘 발행 → 묶음 카드 · 뺀 줄(오늘)만", [x["mgmt"] for x in cs_d])
cs_q, _ = cards("/prod-requests?q=022T2611")
check(len(cs_q) == 1 and cs_q[0]["mgmt"].startswith("020T2611"), "구성원 관리번호(022T2611)로 찾으면 묶음 카드", [x["mgmt"] for x in cs_q])
cs_q2, _ = cards("/prod-requests?q=T-261113-8")
check(len(cs_q2) == 1 and cs_q2[0]["mgmt"].startswith("020T2611"), "구성원 수주번호로도 묶음 카드", [x["mgmt"] for x in cs_q2])
cs_q3, _ = cards("/prod-requests?q=T-261117-3")
check(not cs_q3, "요청서가 가리키지 않는 수주번호(023 의 추가 수주)로는 안 나옴 — 그 수주엔 요청서가 없음", [x["mgmt"] for x in cs_q3])
cs_q4, _ = cards("/prod-requests?q=T-260110-1")
check(not cs_q4, "028T2601 의 다른 수주번호(가리키지 않음)로도 안 나옴", [x["mgmt"] for x in cs_q4])
cs_q5, _ = cards("/prod-requests?q=VPL2132_2138")
check(len(cs_q5) == 1 and cs_q5[0]["mgmt"].startswith("020T2611"), "묶음 이름(모델)으로 찾기", [x["mgmt"] for x in cs_q5])

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
