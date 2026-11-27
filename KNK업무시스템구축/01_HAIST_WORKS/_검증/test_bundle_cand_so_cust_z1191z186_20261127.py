# -*- coding: utf-8 -*-
"""z1191z186 (대표 11-27 「고른 수주의 고객으로 좁혀」): 제작요청서 「함께 묶을 관리번호」 후보
   ① 후보 = 수주 1차 고객이 같은 관리번호(처음 등록 고객 아님) ② 고른 수주의 고객만 ③ 저장 때도 고른 수주 고객으로 다시 확인
   ④ 화면: 수주 칸 data-cid · 후보 data-cids · 수주 바꾸면 다시 거르는 스크립트."""
import contextlib, io, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z186-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D   # noqa: E402
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_z186_"), "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
import app.main as M   # noqa: E402
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, " ←", got)


def ins(c, t, d):
    cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % t)}
    d = {k: v for k, v in d.items() if k in cols}
    c.execute("INSERT INTO %s(%s) VALUES(%s)" % (t, ",".join(d), ",".join("?" * len(d))), list(d.values()))
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


with D.db_session() as c:
    A = ins(c, "customers", {"name": "KNK VINA CO LTD"})
    B = ins(c, "customers", {"name": "삼성전자(주)"})
    X0 = ins(c, "customers", {"name": "처음등록만"})

    def proj(code, cust):
        return ins(c, "projects", {"code": code, "mgmt_code": code, "name": code, "customer_id": cust, "is_archived": 0, "biz_div": "T"})

    def order(pid, no, cust, od):
        return ins(c, "orders", {"project_id": pid, "order_no": no, "customer_id": cust, "order_date": od, "status": "CONFIRMED", "currency": "KRW"})
    P = proj("001T2612", X0)                               # 처음 등록 고객 = 엉뚱 · 수주 = VINA·삼성 두 곳
    O1 = order(P, "T-1", A, "2026-12-01"); O2 = order(P, "T-2", B, "2026-12-02")
    XA = proj("002T2612", B); order(XA, "T-3", A, "2026-12-01")   # 처음 등록 삼성 · 수주 VINA → VINA 후보
    XB = proj("003T2612", A); order(XB, "T-4", B, "2026-12-05")   # 처음 등록 VINA · 수주 삼성 → 삼성 후보
    XN = proj("004T2612", X0); order(XN, "T-5", X0, "2026-12-01")  # 다른 고객 → 후보 아님
    p = dict(c.execute("SELECT * FROM projects WHERE id=?", (P,)).fetchone())

print("§1 후보 = 수주 1차 고객")
with D.db_session() as c:
    allc = {d["id"]: d for d in M._z49_candidates(c, p, set(), limit=None)}
check(set(allc) == {XA, XB}, "고른 수주 없이 = 이 관리번호 수주 고객(VINA·삼성) 의 관리번호 · 처음 등록 고객 무관 · 다른 고객 빠짐", sorted(allc))
check(allc[XA]["cids"] == [A] and allc[XB]["cids"] == [B], "후보마다 맞는 고객 번호(cids)", (allc[XA]["cids"], allc[XB]["cids"]))
check(allc[XA]["same_day"] and not allc[XB]["same_day"] and allc[XA]["so_date"] == "2026-12-01", "같은 발주일 = 수주 발주일", (allc[XA]["same_day"], allc[XB]["same_day"], allc[XA]["so_date"]))
print("§2 고른 수주의 고객만")
with D.db_session() as c:
    cA, dA = M._z186_order_cids(c, P, [O1])
    onlyA = [d["id"] for d in M._z49_candidates(c, p, set(), limit=None, cids=cA, pods=dA)]
check(onlyA == [XA], "VINA 수주(T-1) 고르면 = VINA 수주 있는 관리번호만", onlyA)
print("§3 저장 때 다시 확인")


class F(dict):
    def getlist(self, k):
        v = self.get(k)
        return v if isinstance(v, list) else ([] if v is None else [v])


with D.db_session() as c:
    mem = M._z49_pick_members(c, P, [XA, XB, XN], F({"order_ids": [str(O1)]}))
got = sorted(int(m["pid"]) for m in mem) if mem and isinstance(mem[0], dict) else mem
check(got == [XA], "고른 수주가 VINA 면 삼성 후보(XB)·다른 고객(XN)은 저장 때 버림", got)
print("§4 화면")
t = open(os.path.join(ROOT, "app", "templates", "prod_request_edit.html"), encoding="utf-8").read()
check('data-cid="{{ o.customer_id or \'\' }}"' in t and 'data-cids="{{ (d.cids or [])|join(\',\') }}"' in t, "수주 칸 data-cid · 후보 data-cids")
check("window.z186Sync" in t and ".z49-item.z186-off { display:none !important; }" in t and "is-sug:not(.z186-off)" in t, "수주 바꾸면 다시 거름 · 「모두 묶기」는 보이는 후보만")
print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
