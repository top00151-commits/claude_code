# -*- coding: utf-8 -*-
"""WP-01 P0 위험 차단 — 정식 검증 (ChatGPT Gate 판정서 §6-7·F-06 요구)

실행:  01_HAIST_WORKS 루트에서
    python tests/test_wp01_p0_guards.py

- 임시 DB(운영과 동일 init_db 스키마) 사용 — 운영 DB 무관.
- A부: 함수 수준 가드·KPI 계약 (차단 시 '변경 전후 행 수 불변'을 함께 출력)
- B부: 라우트 수준 실HTTP(TestClient) — 인증(get_user)만 대체하고 인가(can_*)는 실로직.
  필요 패키지: fastapi + httpx (개발 PC 기준).
"""
import os
import sys
import tempfile
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # 01_HAIST_WORKS
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # 템플릿·정적 상대경로 안전

from app import database as db  # noqa: E402

db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="wp01_"), "test.db")
db.init_db()

TODAY = datetime.date.today()


def D(n):
    return (TODAY - datetime.timedelta(days=n)).isoformat()


ok = 0
fail = 0


def chk(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name} {detail}")


def cnt(t, where="1=1", args=()):
    with db.db_session() as c:
        return c.execute(f"SELECT COUNT(*) FROM {t} WHERE {where}", args).fetchone()[0]


def stock_of(pid):
    with db.db_session() as c:
        return c.execute("SELECT stock_qty FROM parts WHERE id=?", (pid,)).fetchone()[0]


# ═══════════ 시드 ═══════════
with db.db_session() as c:
    for tid, tnm in ((3, "품질"), (10, "구매"), (11, "관리")):
        c.execute("INSERT OR IGNORE INTO teams (id, code, name) VALUES (?,?,?)", (tid, f"T{tid:02d}", tnm))
    for uid, nm, tid, role in ((501, "조회자", 3, "member"), (502, "구매팀원", 10, "member"), (503, "대표", 11, "ceo")):
        c.execute(
            "INSERT OR IGNORE INTO users (id, name, login_id, password, role, team_id) VALUES (?,?,?,?,?,?)",
            (uid, nm, f"wp01_{uid}", "x", role, tid))

    def _part(no, name, qty=0):
        c.execute("INSERT INTO parts (part_no, part_name, stock_qty, is_active) VALUES (?,?,?,1)", (no, name, qty))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

    P_ISSUE = _part("WPR-ISSUE", "출고요청 참조 자재")
    P_BOM = _part("WPR-BOM", "BOM 참조 자재")
    P_CLEAN = _part("WPR-CLEAN", "무참조 자재")
    P_CLEAN2 = _part("WPR-CLEAN2", "무참조 자재(라우트)")
    P_STOCK = _part("WPR-STK", "재고 시험 자재", qty=100)

    c.execute("INSERT INTO issues_out (part_id, qty, status) VALUES (?,1,'PENDING')", (P_ISSUE,))

    c.execute("INSERT INTO projects (mgmt_code, name, status) VALUES ('002M2599','운영유사 프로젝트','진행중')")
    PJ_REAL = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO projects (mgmt_code, name, status) VALUES ('999T001','테스트 프로젝트','진행중')")
    PJ_TEST = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    for pj, tag in ((PJ_REAL, "R"), (PJ_TEST, "T")):
        c.execute("INSERT INTO bom_uploads (project_id, version_no, source_filename, mode) VALUES (?,1,'t.xlsx','merge')", (pj,))
        c.execute("INSERT INTO bom_items (project_id, part_no, part_name, status) VALUES (?,?,?, '활성')",
                  (pj, f"B-{tag}", f"BOM행-{tag}"))
        iid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        c.execute("INSERT INTO bom_item_history (item_id, project_id, change_type, field) VALUES (?,?,'추가','전체')", (iid, pj))
    # P_BOM 참조행 (테스트 프로젝트에)
    c.execute("INSERT INTO bom_items (project_id, part_no, part_name, part_id, status) VALUES (?,?,?,?, '활성')",
              (PJ_TEST, "WPR-BOM", "BOM 참조 자재", P_BOM))

    def _po(no, st, rcv=None, receipt=False):
        c.execute("INSERT INTO purchase_orders (po_number, status, order_date) VALUES (?,?,?)", (no, st, TODAY.isoformat()))
        po_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        if rcv is not None:
            c.execute("INSERT INTO po_items (po_id, line_no, quantity, received_qty) VALUES (?,1,10,?)", (po_id, rcv))
        if receipt:
            c.execute("INSERT INTO receipts (po_id, total_qty, status) VALUES (?,2,'PENDING')", (po_id,))
        return po_id

    PO_DRAFT = _po("WP-D1", "작성중", rcv=0)
    PO_DRAFT2 = _po("WP-D2", "작성중", rcv=0)
    PO_ISSUED = _po("WP-I", "발주완료", rcv=0)
    PO_PART = _po("WP-P", "부분입고", rcv=5)
    PO_RCPT = _po("WP-R", "입고완료", rcv=0, receipt=True)
    PO_CANCEL = _po("WP-C", "취소", rcv=0)

    # KPI 시드: 오늘-6(경계 포함)·오늘-7(경계 밖)·오늘-2 입고 3행
    for i, (d_, q) in enumerate(((D(6), 1), (D(7), 1), (D(2), 2))):
        c.execute(
            "INSERT INTO stock_movements (movement_no, part_id, kind, quantity, unit_price, remaining_qty, occurred_at)"
            " VALUES (?,?, 'IN', ?, 100, ?, ?)", (f"WPK-{i}", P_STOCK, q, q, d_))

print("═══ A부: 함수 수준 ═══")
print("[A1] stock_kpi 계약 (P0-01·F-07 경계)")
k = db.stock_kpi()
chk("recent_receipts=달력 7일(오늘-6 포함·오늘-7 제외) 품목행 2건", k.get("recent_receipts") == 2, k.get("recent_receipts"))
chk("total_qty=활성 수량 합(100)", k.get("total_qty") == 100, k.get("total_qty"))
chk("po_pending=작성중2+발주완료1+부분입고1=4", k.get("po_pending") == 4, k.get("po_pending"))
chk("기존 키 불변", all(x in k for x in ("stock_value", "low_stock", "in_30d", "out_30d", "parts_total")))

print("[A2] parts_delete — 전참조 차단 (F-01)")
for pid, ref_t, nm in ((P_ISSUE, "issues_out", "출고요청 참조"), (P_BOM, "bom_items", "BOM 참조")):
    before = (cnt("parts", "id=?", (pid,)), cnt(ref_t, "part_id=?", (pid,)))
    try:
        db.parts_delete(pid)
        chk(f"{nm} 자재 삭제 차단", False, "예외 없이 삭제됨!")
    except ValueError as e:
        chk(f"{nm} 자재 삭제 차단(ValueError)", "업무 참조" in str(e), str(e)[:50])
    after = (cnt("parts", "id=?", (pid,)), cnt(ref_t, "part_id=?", (pid,)))
    chk(f"  행 수 불변 {before}→{after}", before == after and before[0] == 1 and before[1] >= 1)
db.parts_delete(P_CLEAN)
chk("무참조 자재는 정상 삭제(기존 기능 유지)", cnt("parts", "id=?", (P_CLEAN,)) == 0)

print("[A3] po_delete — 상태별 매트릭스 (F-02)")
for po_id, st in ((PO_ISSUED, "발주완료"), (PO_PART, "부분입고"), (PO_RCPT, "입고완료"), (PO_CANCEL, "취소")):
    before = (cnt("purchase_orders", "id=?", (po_id,)), cnt("po_items", "po_id=?", (po_id,)))
    try:
        db.po_delete(po_id)
        chk(f"{st} PO 삭제 차단", False, "예외 없이 삭제됨!")
    except ValueError as e:
        chk(f"{st} PO 삭제 차단(ValueError)", "삭제할 수 없습니다" in str(e))
    after = (cnt("purchase_orders", "id=?", (po_id,)), cnt("po_items", "po_id=?", (po_id,)))
    chk(f"  행 수 불변 {before}→{after}", before == after and before[0] == 1)
db.po_delete(PO_DRAFT)
chk("작성중(무입고) PO는 정상 삭제 + 품목 정리", cnt("purchase_orders", "id=?", (PO_DRAFT,)) == 0 and cnt("po_items", "po_id=?", (PO_DRAFT,)) == 0)

print("[A4] bom_purge_project — 운영 차단 (F-03 함수층)")
before = (cnt("bom_items", "project_id=?", (PJ_REAL,)), cnt("bom_uploads", "project_id=?", (PJ_REAL,)), cnt("bom_item_history", "project_id=?", (PJ_REAL,)))
try:
    sys.path.insert(0, ROOT)
    from app import bom as bom_mod
    bom_mod.bom_purge_project(PJ_REAL)
    chk("운영 관리번호 폐기 차단", False, "예외 없이 삭제됨!")
except ValueError as e:
    chk("운영 관리번호 폐기 차단(ValueError)", "테스트 관리번호" in str(e))
after = (cnt("bom_items", "project_id=?", (PJ_REAL,)), cnt("bom_uploads", "project_id=?", (PJ_REAL,)), cnt("bom_item_history", "project_id=?", (PJ_REAL,)))
chk(f"  BOM 3표 불변 {before}→{after}", before == after and all(before))

print("═══ B부: 라우트 수준 (실HTTP·TestClient) ═══")
import app.main as appmain  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

CURRENT = {"u": None}
appmain.get_user = lambda request: CURRENT["u"]  # 인증만 대체 — 인가(can_*)는 실제 로직 실행
client = TestClient(appmain.app, follow_redirects=False)

VIEW = {"id": 501, "name": "조회자", "role": "member", "team_id": 3, "can_use_logistics": 0, "can_view_logistics": 1}
USE = {"id": 502, "name": "구매팀원", "role": "member", "team_id": 10, "can_use_logistics": 0, "can_view_logistics": 1}
CEO = {"id": 503, "name": "대표", "role": "ceo", "team_id": 11, "can_use_logistics": 1, "can_view_logistics": 1}


def loc(r):
    return r.headers.get("location", "")


print("[B1] 조회 권한 차단 + DB 불변 (P0-04)")
CURRENT["u"] = None
r = client.get("/stock/issue")
chk("미로그인 GET /stock/issue → /login", r.status_code == 303 and "/login" in loc(r))
CURRENT["u"] = VIEW
r = client.get("/stock/issue")
chk("조회 GET /stock/issue → /home 차단", r.status_code == 303 and loc(r) == "/home")
mv0, st0 = cnt("stock_movements"), stock_of(P_STOCK)
r = client.post("/stock/issue", data={"part_id": str(P_STOCK), "quantity": "5"})
chk("조회 POST /stock/issue → /home 차단", r.status_code == 303 and loc(r) == "/home")
chk(f"  원장 불변({mv0}건)·재고 불변({st0})", cnt("stock_movements") == mv0 and stock_of(P_STOCK) == st0)
r = client.post("/stock/adjust", data={"part_id": str(P_STOCK), "quantity": "3", "reason": "t"})
chk("조회 POST /stock/adjust → /home 차단 + 불변", r.status_code == 303 and loc(r) == "/home" and cnt("stock_movements") == mv0)

print("[B2] 출고 요청≠차감 → ISSUED 확정 1회 차감 (F-04 해석 고정)")
CURRENT["u"] = USE
mv0, st0 = cnt("stock_movements"), stock_of(P_STOCK)
r = client.post("/stock/issues", data={"part_id": str(P_STOCK), "qty": "3"})
chk("요청 생성 성공(303)", r.status_code == 303 and "success" in loc(r))
with db.db_session() as c:
    gi = c.execute("SELECT id FROM issues_out WHERE part_id=? ORDER BY id DESC", (P_STOCK,)).fetchone()[0]
chk(f"  요청만으로 재고·원장 불변(재고 {st0}·원장 {mv0}건)", cnt("stock_movements") == mv0 and stock_of(P_STOCK) == st0)
# 주의: 요청·승인(S2) 경로의 차감 = 원장(stock_movements) OUT 기록 기준.
#   parts.stock_qty 열은 이 경로에서 갱신되지 않음(직접출고/조정 경로와의 이중 표현 —
#   P0-02/03의 알려진 분리 문제로 WP-07/08 단일 엔진에서 해소. WP-01은 홈 노출 제거로 축소).
r = client.post(f"/stock/issues/{gi}/approve")
with db.db_session() as c:
    _out = c.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE kind='OUT' AND part_id=? AND ABS(quantity)=3", (P_STOCK,)
    ).fetchone()[0]
    _st = c.execute("SELECT status FROM issues_out WHERE id=?", (gi,)).fetchone()[0]
chk("승인·확정(ISSUED) → 원장 OUT 1회 기록 + 상태 ISSUED",
    cnt("stock_movements") == mv0 + 1 and _out == 1 and _st == "ISSUED")
r = client.post(f"/stock/issues/{gi}/approve")
chk("중복 승인 차단(원장 재기록 없음)", "already" in loc(r) and cnt("stock_movements") == mv0 + 1)

print("[B3] 삭제 라우트 차단 (F-01·F-02)")
b = (cnt("parts", "id=?", (P_ISSUE,)), cnt("issues_out", "part_id=?", (P_ISSUE,)))
r = client.post(f"/parts/{P_ISSUE}/delete")
chk("참조 자재 삭제 라우트 400", r.status_code == 400 and "업무 참조" in r.text)
chk(f"  자재·출고요청 불변 {b}", (cnt("parts", "id=?", (P_ISSUE,)), cnt("issues_out", "part_id=?", (P_ISSUE,))) == b)
r = client.post(f"/parts/{P_CLEAN2}/delete")
chk("무참조 자재 삭제 라우트 303", r.status_code == 303 and cnt("parts", "id=?", (P_CLEAN2,)) == 0)
r = client.post(f"/po/{PO_ISSUED}/delete")
chk("발주완료 PO 삭제 라우트 400 + 불변", r.status_code == 400 and cnt("purchase_orders", "id=?", (PO_ISSUED,)) == 1)
r = client.post(f"/po/{PO_DRAFT2}/delete")
chk("작성중 PO 삭제 라우트 303", r.status_code == 303 and cnt("purchase_orders", "id=?", (PO_DRAFT2,)) == 0)

print("[B4] BOM 폐기 라우트 매트릭스 (F-03)")
b = (cnt("bom_items", "project_id=?", (PJ_TEST,)), cnt("bom_uploads", "project_id=?", (PJ_TEST,)), cnt("bom_item_history", "project_id=?", (PJ_TEST,)))
CURRENT["u"] = USE  # 관리자 아님
r = client.post(f"/projects/{PJ_TEST}/bom/purge", data={"confirm_code": "999T001"})
chk("비관리자 폐기 차단(관리자 전용)", r.status_code == 303 and "error" in loc(r))
chk(f"  BOM 3표 불변 {b}", (cnt("bom_items", "project_id=?", (PJ_TEST,)), cnt("bom_uploads", "project_id=?", (PJ_TEST,)), cnt("bom_item_history", "project_id=?", (PJ_TEST,))) == b)
CURRENT["u"] = CEO
r = client.post(f"/projects/{PJ_REAL}/bom/purge", data={"confirm_code": "002M2599"})
chk("운영 관리번호 폐기 차단(라우트층)", r.status_code == 303 and "error" in loc(r) and cnt("bom_items", "project_id=?", (PJ_REAL,)) >= 1)
r = client.post(f"/projects/{PJ_TEST}/bom/purge", data={"confirm_code": "999T001"})
chk("테스트(999 접두)+관리자+타이핑 일치 → 폐기 허용", r.status_code == 303 and "success" in loc(r) and cnt("bom_items", "project_id=?", (PJ_TEST,)) == 0)

print(f"\n==== 결과: PASS {ok} / FAIL {fail} ====")
sys.exit(1 if fail else 0)
