# -*- coding: utf-8 -*-
"""z1191z58 시험 (대표 2026-11-18 「처음부터 발행할 때 묶어서 발행」 · 고름 = 등록 화면에서 묶기 + 목록에서 골라 + 「묶어서 다시 발행」)
  ① 등록 화면: 묶어서 발행(기다림) → 요청서 안 나감 · 마지막 관리번호 「지금 발행」 때 기다리던 것과 한 장(처음 발행 · 수정발행 아님)
  ② 기다림 목록 API(같은 발주일 먼저 · 다른 발주일 표시 · 요청서 있으면 빠짐)
  ③ 작업일정표에서 골라 온 새 작성(?with) — 미리 묶음 · 다른 고객사는 뺌
  ④ 이미 보낸 요청서를 묶으면 「묶어서 다시 발행」 — 새 요청서 · 앞 요청서 「묶음으로 바뀜」(취소 아님) · 카드 replaces · 일부만 겹치면 그대로
  ⑤ 요청서 화면 「수정하기」: 관리번호 붙이기 대신 「🔗 관리번호 더 묶어서 다시 발행」(?from — 글·받는 사람 불러옴)
  임시 DB · TestClient · 이음 보내기는 가짜 · 운영 아님
"""
import contextlib, io, json, os, re, sys, tempfile
from datetime import date, timedelta
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z58-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z58_")
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


FUT = (date.today() + timedelta(days=20)).isoformat()
OD = "2026-11-13"
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    TEAM = ins(c, "teams", {"name": "가상검사기팀", "code": "T58", "entity": "KOR", "display_order": 1})
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T958', 'T958', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T958'").fetchone())
    for i in (1, 2):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id) VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', 1, 1, ?)",
                  ("가상받는이%d" % i, "T95%d" % (i + 5), "T95%d" % (i + 5), TEAM))
    CU = ins(c, "customers", {"name": "한국가상전(주)", "alias": "가상전"})
    CU2 = ins(c, "customers", {"name": "다른고객(주)", "alias": "다른"})

    def proj(code, cust=CU, **kw):
        row = {"code": code, "name": "PBA", "mgmt_code": code, "customer_id": cust, "customer_name": ("한국가상전(주)" if cust == CU else "다른고객(주)"), "currency": "KRW",
               "status": "수주확정", "biz_div": "T", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "order_date": OD, "due_date": FUT, "is_archived": 0,
               "unit_qty": 1, "model_name": "VPL-" + code[:3], "equip_name": "가상 검사기 " + code[:3]}
        row.update(kw)
        return ins(c, "projects", row)

    def order(pid, no, created, cust=CU):
        return ins(c, "orders", {"order_no": no, "customer_id": cust, "order_date": created[:10], "due_date": FUT, "total_amount": 1000, "status": "CONFIRMED",
                                 "created_at": created, "project_id": pid, "unit_label": "1호기", "unit_qty": 1, "currency": "KRW", "so_type": "EQUIPMENT", "po_type": "신규"})
    X = proj("060T2611"); OX = order(X, "T-261113-20", "2026-11-16 09:00:00")
    Y = proj("061T2611"); OY = order(Y, "T-261113-21", "2026-11-16 09:01:00")
    P = proj("062T2611"); OP = order(P, "T-261113-22", "2026-11-16 09:02:00")
    Q = proj("063T2611"); OQ = order(Q, "T-261113-23", "2026-11-16 09:03:00")
    R = proj("064T2611"); OR_ = order(R, "T-261113-24", "2026-11-16 09:04:00")
    Z = proj("065T2611"); OZ1 = order(Z, "T-261113-25", "2026-11-16 09:05:00"); OZ2 = order(Z, "T-261117-9", "2026-11-17 09:00:00")
    W = proj("066T2611"); OW = order(W, "T-261113-26", "2026-11-16 09:06:00")
    OTH = proj("070T2611", cust=CU2); OOTH = order(OTH, "T-261113-30", "2026-11-16 09:07:00", cust=CU2)

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


def prq(where, args=()):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM prod_requests WHERE " + where + " ORDER BY id", args).fetchall()]


def waits():
    with D.db_session() as c:
        try:
            return sorted(r[0] for r in c.execute("SELECT project_id FROM prq_waits").fetchall())
        except Exception:
            return []


REG = {"quick": "1", "customer_name": "한국가상전(주)", "customer_id": str(CU), "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규",
       "status": "진행중", "confirm_now": "1", "order_date": OD, "due_date": FUT, "currency": "KRW", "unit_qty": "1", "unit_price": "1000",
       "name": "PBA", "pr_cust_req": "1. 검사기 : 1호기", "pr_team_ids": str(TEAM)}


def reg(model, equip, **kw):
    f = dict(REG, model=model, equip_name=equip)
    f.update(kw)
    r = q(cl.post, "/projects/new", data=f)
    loc = r.headers.get("location", "")
    m = re.search(r"/project/(\d+)", loc)
    return (int(m.group(1)) if m else None), loc


print("§1 등록 화면: 묶어서 발행(기다림) → 마지막 「지금 발행」 때 한 장")
h = q(cl.get, "/projects/quick?biz_div=T").text
check('name="prod_mode" value="now" checked' in h and 'value="wait"' in h and 'value="none"' in h and 'id="z58Waits"' in h,
      "등록 화면에 지금 발행 / 묶어서 발행(기다림) / 발행 안 함 · 기다리는 관리번호 칸")
A, la = reg("VPL2132", "SENSOR 1연배", prod_mode="wait")
B, lb = reg("VPL2133", "SENSOR MAP 2연배", prod_mode="wait")
check(A and B and "prod_wait=1" in la and not prq("project_id IN (?,?)", (A, B)) and waits() == sorted([A, B]),
      "두 건을 「묶어서 발행(기다림)」으로 등록 → 요청서 안 나감 · 기다림 2건", (la, waits()))
j = q(cl.get, "/api/prod-request/waits?customer_id=%d&order_date=%s" % (CU, OD)).json()
check([x["pid"] for x in j["items"]] == [A, B] and all(x["same"] for x in j["items"]), "기다림 목록(같은 고객사 · 같은 발주일)", j)
j2 = q(cl.get, "/api/prod-request/waits?customer_name=%s&order_date=2026-11-20" % "가상전").json()
check(len(j2["items"]) == 2 and not any(x["same"] for x in j2["items"]), "시스템명으로도 찾음 · 다른 발주일이면 「다른 발주일」 표시(미리 고르지 않음)", j2)
check(q(cl.get, "/api/prod-request/waits?customer_id=%d" % CU2).json()["items"] == [], "다른 고객사는 안 나옴")
CARDS.clear()
C, lc = reg("VPL2134", "SENSOR DOM 2연배", prod_mode="now", prod_notify="1", prq_bundle_pids=[str(A), str(B)], pr_bundle_model="VPL2132_2134")
rows = prq("project_id IN (?,?,?)", (A, B, C))
lead = [r for r in rows if r["project_id"] == C]
check(lead and len(rows) == 3 and all(r["bundle_id"] == lead[0]["id"] for r in rows) and "prod_bundled=2" in lc,
      "마지막 관리번호 「지금 발행」 → 기다리던 2건과 한 장(대표 = 마지막 등록 · 묶음 3줄)", (lc, [(r["project_id"], r["bundle_id"]) for r in rows]))
k = CARDS[0]["card"] if CARDS else {}
check(k.get("is_revision") is False and "replaces" not in k and len(k.get("items") or []) == 3 and k.get("model") == "VPL2132_2134"
      and "[수정]" not in CARDS[0]["title"] and "다시 발행" not in CARDS[0]["title"], "처음 발행(수정발행 아님) · 카드 품목 3줄 · 묶음 이름", (CARDS[0]["title"] if CARDS else None, k.get("items")))
with D.db_session() as c:
    nrev = c.execute("SELECT COUNT(*) FROM prod_request_revs WHERE prod_request_id=?", (lead[0]["id"],)).fetchone()[0] if lead else -1
check(nrev == 0 and waits() == [], "수정 이력 없음 · 기다림 비워짐", (nrev, waits()))
D_, ld = reg("VPL2135", "제안 단계", prod_mode="none")
check(D_ and not prq("project_id=?", (D_,)) and waits() == [], "발행 안 함 → 요청서도 기다림도 없음")

print("§2 작업일정표에서 골라 온 새 작성(?with)")
hs = q(cl.get, "/sales/schedule").text
check('id="schedPrqBtn"' in hs and "schedPrqBundle" in hs, "작업일정표에 [📋 골라서 제작요청서]")
hw = q(cl.get, "/project/%d/prod-request/edit?new=1&with=%d:%d,%d:%d,%d:%d" % (X, X, OX, Y, OY, OTH, OOTH)).text
m = re.search(r'id="z58Pre">(.*?)</script>', hw, re.S); pre = json.loads(m.group(1)) if m else {}
check(pre.get("members") == [Y] and pre.get("lead_oid") == OX and pre.get("skipped") == ["070T2611"] and pre.get("orders") == {str(Y): OY},
      "골라 온 X·Y·다른 고객사 → Y 를 묶고 대표 X 수주 · 다른 고객사(070T2611)는 뺌", pre)

print("§3 이미 보낸 요청서를 묶음 → 「묶어서 다시 발행」")
base = {"full_edit": "", "server_path": "", "model_name": "", "engraving": ""}


def issue(pid, oid, members=(), **kw):
    d = dict(base, cust_req="1. 요청 %d" % pid, order_ids=[str(oid)], add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % pid)
    if members:
        d["bundle_pids"] = [str(x) for x, _ in members]
        for x, o in members:
            d["m_order_%d" % x] = str(o)
    d.update(kw)
    r = q(cl.post, "/project/%d/prod-request/new" % pid, data=d)
    return r.headers.get("location", "")


issue(X, OX); issue(Y, OY)
oldX = prq("project_id=?", (X,))[0]["id"]; oldY = prq("project_id=?", (Y,))[0]["id"]
CARDS.clear()
loc = issue(X, OX, [(Y, OY)])
newid = int(re.search(r"prid=(\d+)", loc).group(1))
ox, oy = prq("id=?", (oldX,))[0], prq("id=?", (oldY,))[0]
check(ox["cancel_kind"] == "replace" and oy["cancel_kind"] == "replace" and ox["replaced_by"] == newid and oy["replaced_by"] == newid and ox["cancelled_at"],
      "X·Y 따로 보낸 요청서 → 묶어 새로 발행하면 앞 요청서 둘 다 「묶음으로 바뀜」(replaced_by = 새 요청서)", (ox["cancel_kind"], oy["cancel_kind"], ox["replaced_by"]))
k = CARDS[0]["card"] if CARDS else {}
check("rebundled=2" in loc and "[묶어서 다시 발행]" in CARDS[0]["title"] and sorted(k.get("replaces") or []) == sorted([oldX, oldY]) and k.get("rebundle") is True
      and k.get("is_revision") is False and k.get("prid") == newid, "제목 「[묶어서 다시 발행]」 · 카드 replaces=[앞 요청서] · rebundle · 수정발행 아님",
      (CARDS[0]["title"] if CARDS else None, k.get("replaces"), loc))
hv = q(cl.get, "/project/%d/prod-request/edit?prid=%d" % (X, oldX)).text
check("묶음 요청서로 다시 발행됐습니다" in hv and "z58-rep" in hv and "prid=%d" % newid in hv and "취소된 제작요청서입니다" not in hv,
      "앞 요청서 화면: 「묶음 요청서로 다시 발행됐습니다(취소 아님)」 · 「묶음으로 바뀜」 도장 · 새 요청서로 가는 길")
check("🔗 묶음으로 바뀜" in hv, "앞 요청서 이력에 「🔗 묶음으로 바뀜」")
r = q(cl.post, "/project/%d/prod-request/%d/cancel" % (X, oldX), data={"cancel_reason": "또"})
check("prod_cancelled=1" in r.headers.get("location", ""), "바뀐 앞 요청서는 취소·수정 막힘(이미 닫힘)", r.headers.get("location"))
hl = q(cl.get, "/prod-requests").text
check(hl.count("060T2611") >= 1 and "061T2611" in hl, "목록은 새 묶음 카드")
with D.db_session() as c:
    sup = c.execute("SELECT COUNT(*), SUM(COALESCE(superseded,0)) FROM notifications WHERE kind='prod_request' AND prod_prid IN (?,?)", (oldX, oldY)).fetchone()
check(sup[0] and sup[0] == sup[1], "웍스 알림의 앞 카드도 흑백", tuple(sup))

print("§3-2 일부만 겹치면 앞 요청서 그대로 · 다른 수주면 그대로")
issue(P, OP, [(Q, OQ)])
oldPQ = prq("project_id=?", (P,))[0]["id"]
loc = issue(P, OP, [(R, OR_)])
check(prq("id=?", (oldPQ,))[0]["cancelled_at"] in (None, "") and "rebundled" not in loc,
      "앞 묶음(P+Q) · 새 묶음(P+R) → Q 가 빠지므로 앞 요청서 그대로(Q 가 요청서를 잃지 않게)", loc)
issue(Z, OZ1)
oldZ = prq("project_id=?", (Z,))[0]["id"]
loc = issue(Z, OZ2, [(W, OW)])
check(prq("id=?", (oldZ,))[0]["cancelled_at"] in (None, ""), "같은 관리번호라도 다른 수주(추가 발주)면 앞 요청서 그대로", loc)

print("§4 요청서 화면 「수정하기」 → 「🔗 관리번호 더 묶어서 다시 발행」(?from)")
he = q(cl.get, "/project/%d/prod-request/edit?prid=%d" % (P, oldPQ)).text
ef = he[he.find('id="prqEditForm"'):]
check("z58-rebtn" in he and "from=%d" % oldPQ in he and 'name="bundle_pids"' not in ef,
      "수정하기에는 관리번호 붙이기 칸 대신 「🔗 관리번호 더 묶어서 다시 발행」(수정발행으로 붙이지 않음)")
hf = q(cl.get, "/project/%d/prod-request/edit?new=1&from=%d" % (P, oldPQ)).text
m = re.search(r'id="z58Pre">(.*?)</script>', hf, re.S); pre = json.loads(m.group(1)) if m else {}
check(pre.get("from", {}).get("id") == oldPQ and pre.get("members") == [Q] and pre.get("text", {}).get("cust_req") == "1. 요청 %d" % P and pre.get("teams") == [TEAM],
      "?from → 그 요청서의 관리번호(Q)·글·받는 부서를 불러옴", pre)
loc = issue(P, OP, [(Q, OQ), (W, OW)])
check("rebundled=1" in loc and prq("id=?", (oldPQ,))[0]["cancel_kind"] == "replace", "P+Q 에 W 를 더 묶어 다시 발행 → 앞 묶음(P+Q) 「묶음으로 바뀜」", loc)

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
