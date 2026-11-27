# -*- coding: utf-8 -*-
"""z1191z183 (대표 11-27 「거래명세서 날짜를 쓰면 다른 줄에 입력됨 · 이새롬 프로 확인」):
   ① 발행일·세금계산서(프로젝트) = 그 줄 호기에만(같은 관리번호의 다른 수주에 안 퍼짐) ② 줄 호기 없이 수주 2개+ = 막음
   ③ 수주 1개 = 예전처럼 그 수주 전체 ④ 이력(전→후 · 수주 · 호기) ⑤ 화면: 저장에 uids · 날짜 Enter = 달력 닫고 바로 저장."""
import contextlib, io, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z183-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D   # noqa: E402
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_z183_"), "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
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
    P = ins(c, "projects", {"code": "906T2610", "mgmt_code": "906T2610", "name": "가상", "is_archived": 0, "biz_div": "T"})
    O1 = ins(c, "orders", {"project_id": P, "order_no": "T-1", "status": "CONFIRMED", "currency": "KRW"})
    O2 = ins(c, "orders", {"project_id": P, "order_no": "T-2", "status": "CONFIRMED", "currency": "KRW"})
    I1 = ins(c, "order_items", {"order_id": O1, "unit_label": "1호기", "qty": 1})
    I2 = ins(c, "order_items", {"order_id": O2, "unit_label": "R0.2A", "qty": 1})
    P1 = ins(c, "projects", {"code": "907T2610", "mgmt_code": "907T2610", "name": "한 수주", "is_archived": 0, "biz_div": "T"})
    Q1 = ins(c, "orders", {"project_id": P1, "order_no": "T-9", "status": "CONFIRMED", "currency": "KRW"})
    J1 = ins(c, "order_items", {"order_id": Q1, "unit_label": "1호기", "qty": 1})
    J2 = ins(c, "order_items", {"order_id": Q1, "unit_label": "2호기", "qty": 1})


def val(iid, col="statement_date"):
    with D.db_session() as c:
        return c.execute("SELECT %s FROM order_items WHERE id=?" % col, (iid,)).fetchone()[0]


print("§1 거래명세서 = 그 줄 호기에만")
ok, msg = D.schedule_cell_update("project", P, "statement_date", "2026-11-25", iids=[str(I1)], user_id=86)
check(ok and val(I1) == "2026-11-25" and val(I2) is None, "1호기 줄에 넣으면 그 줄만 · 다른 수주(R0.2A) 그대로", (ok, msg, val(I1), val(I2)))
ok, msg = D.schedule_cell_update("project", P, "statement_date", "2026-11-29", iids=None, user_id=86)
check(not ok and "수주가 2개 이상" in msg and val(I1) == "2026-11-25" and val(I2) is None, "줄 호기 없이 수주 2개+ = 막음(아무것도 안 바뀜)", (ok, msg))
ok, msg = D.schedule_cell_update("project", P, "statement_date", "2026-11-26", iids=["999999"], user_id=86)
check(not ok and val(I1) == "2026-11-25", "다른 관리번호 호기 번호 = 저장 안 함", (ok, msg))
ok, msg = D.schedule_cell_update("project", P1, "statement_date", "2026-11-27", iids=None, user_id=86)
check(ok and val(J1) == "2026-11-27" and val(J2) == "2026-11-27", "수주 1개 관리번호 = 예전처럼 그 수주 호기 전체", (ok, msg))
print("§2 세금계산서도 같음")
ok, msg = D.schedule_cell_update("project", P, "tax_invoice_date", "2026-12-01", iids=[str(I2)], user_id=86)
check(ok and val(I2, "tax_invoice_date") == "2026-12-01" and val(I1, "tax_invoice_date") is None, "세금계산서 발행일 = 그 줄만", (ok, msg))
ok, msg = D.schedule_cell_update("project", P, "tax_invoice_amt1", "1000000", iids=[str(I2)], user_id=86)
check(ok and float(val(I2, "tax_invoice_amt1") or 0) == 1000000 and not val(I1, "tax_invoice_amt1"), "세금계산서 금액 = 그 줄만(다른 수주에 나눠 넣지 않음)", (ok, msg))
print("§3 이력")
with D.db_session() as c:
    H = c.execute("SELECT project_id, changed_by, field, old_value, new_value, note FROM project_history WHERE note LIKE 'z1191z183%' ORDER BY id").fetchall()
check(any(h[0] == P and h[2] == "거래명세서 발행일" and h[4] == "2026-11-25" and "T-1" in h[5] and "1호기" in h[5] and h[1] == 86 for h in H), "이력 = 거래명세서 발행일 · 전→후 · 수주 · 호기 · 누가", H[:3])
check(any(h[2] == "세금계산서 1차 금액" for h in H) and any(h[2] == "세금계산서 1차 발행일" for h in H), "세금계산서 이력 이름(1차 발행일·금액)", [h[2] for h in H])
print("§4 화면")
t = open(os.path.join(ROOT, "app", "templates", "schedule_board.html"), encoding="utf-8").read()
check(t.count("uids:tr.dataset.uids||''") >= 2, "칸 저장에 그 줄 호기(uids)를 보냄", t.count("uids:tr.dataset.uids||''"))
check("KnkCal.hide(); }catch(e){} } inp.blur();" in t, "날짜 Enter = 달력 닫고 바로 저장")
print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
