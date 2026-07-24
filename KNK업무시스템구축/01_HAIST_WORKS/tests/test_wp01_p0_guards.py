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

    # ── v3 시드 (게이트 v2 F-01/F-02/F-03/F-04 검증용) ──
    P_REG = _part("WPR-REG", "구매요청 대체컬럼 참조 자재")
    c.execute("INSERT INTO material_requests (request_no, request_type, title, status) VALUES ('WPRQ-1','general','참조 시험','제출')")
    MRQ = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO material_request_items (request_id, registered_part_id) VALUES (?,?)", (MRQ, P_REG))
    P_MERGE = _part("WPR-MG", "병합 대표 자재")
    c.execute("INSERT INTO part_aliases (part_id, alias_part_no, alias_part_no_norm) VALUES (?,?,?)", (P_MERGE, "WPR-OLD", "wprold"))
    c.execute("INSERT INTO part_merge_log (canonical_id, merged_part_id, canonical_part_no, merged_part_no) VALUES (?,?,?,?)", (P_MERGE, 999999, "WPR-MG", "WPR-OLD"))
    # 원장으로 완전히 뒷받침되는 자재 (stock 4 = 원장 합계 4) — 확정 수량 대조용
    P_LEDGER = _part("WPR-LG", "원장 기반 재고 자재")
    for _i, _q in enumerate((1, 1, 2)):
        c.execute("INSERT INTO stock_movements (movement_no, part_id, kind, quantity, unit_price, remaining_qty, occurred_at) VALUES (?,?,'IN',?,100,?,?)", (f"WPL-{_i}", P_LEDGER, _q, _q, D(2)))
    c.execute("UPDATE parts SET stock_qty=4 WHERE id=?", (P_LEDGER,))
    # 테스트 접두 프로젝트 2호(폐기 예외 확인용)
    c.execute("INSERT INTO projects (mgmt_code, name, status) VALUES ('999T002','테스트2','진행중')")
    PJ_TEST2 = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO bom_items (project_id, part_no, part_name, status) VALUES (?,?,?, '활성')", (PJ_TEST2, "B-T2", "BOM행-T2"))

    # KPI 시드: 오늘-6(경계 포함)·오늘-7(경계 밖)·오늘-2 입고 3행
    for i, (d_, q) in enumerate(((D(6), 1), (D(7), 1), (D(2), 2))):
        c.execute(
            "INSERT INTO stock_movements (movement_no, part_id, kind, quantity, unit_price, remaining_qty, occurred_at)"
            " VALUES (?,?, 'IN', ?, 100, ?, ?)", (f"WPK-{i}", P_STOCK, q, q, d_))

print("═══ A부: 함수 수준 ═══")
print("[A1] stock_kpi 계약 (P0-01·F-07 경계)")
k = db.stock_kpi()
chk("recent_receipts=달력 7일(오늘-6 포함·오늘-7 제외) 품목행 5건", k.get("recent_receipts") == 5, k.get("recent_receipts"))
chk("total_qty=활성 수량 합(100+4=104)", k.get("total_qty") == 104, k.get("total_qty"))
chk("po_pending=작성중2+발주완료1+부분입고1=4", k.get("po_pending") == 4, k.get("po_pending"))
chk("기존 키 불변", all(x in k for x in ("stock_value", "low_stock", "in_30d", "out_30d", "parts_total")))

print("[A2] parts_delete — 전참조 차단 (F-01: part_id·*_part_id·명시 컬럼)")
for pid, ref_t, ref_col, nm in (
    (P_ISSUE, "issues_out", "part_id", "출고요청 참조"),
    (P_BOM, "bom_items", "part_id", "BOM 참조"),
    (P_REG, "material_request_items", "registered_part_id", "구매요청 대체컬럼 참조"),
    (P_MERGE, "part_merge_log", "canonical_id", "병합 Audit 참조"),
):
    before = (cnt("parts", "id=?", (pid,)), cnt(ref_t, f"{ref_col}=?", (pid,)))
    try:
        db.parts_delete(pid)
        chk(f"{nm} 자재 삭제 차단", False, "예외 없이 삭제됨!")
    except ValueError as e:
        chk(f"{nm} 자재 삭제 차단(ValueError)", "업무 참조" in str(e), str(e)[:60])
    after = (cnt("parts", "id=?", (pid,)), cnt(ref_t, f"{ref_col}=?", (pid,)))
    chk(f"  행 수 불변 {before}→{after}", before == after and before[0] == 1 and before[1] >= 1)
chk("병합 대표 자재의 별칭도 보존(자재 1+참조 1, 판정서 §7 증빙표)",
    cnt("part_aliases", "part_id=?", (P_MERGE,)) == 1)
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

print("[A4] bom_purge_project — 환경 잠금+운영 차단 (F-03·v2 F-05 함수층)")
before = (cnt("bom_items", "project_id=?", (PJ_REAL,)), cnt("bom_uploads", "project_id=?", (PJ_REAL,)), cnt("bom_item_history", "project_id=?", (PJ_REAL,)))
from app import bom as bom_mod
os.environ.pop("KNK_ENABLE_BOM_PURGE", None)
try:
    bom_mod.bom_purge_project(PJ_REAL)
    chk("환경 잠금(스위치 없음) 차단", False, "예외 없이 삭제됨!")
except ValueError as e:
    chk("환경 잠금(스위치 없음) 차단(ValueError)", "잠겨" in str(e))
os.environ["KNK_ENABLE_BOM_PURGE"] = "1"
try:
    bom_mod.bom_purge_project(PJ_REAL)
    chk("운영 관리번호 폐기 차단", False, "예외 없이 삭제됨!")
except ValueError as e:
    chk("운영 관리번호 폐기 차단(ValueError)", "테스트 관리번호" in str(e))
os.environ.pop("KNK_ENABLE_BOM_PURGE", None)
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

print("[B2] 출고 확정 = 단일 Transaction·정확 수량·실패 Rollback (게이트 v2 F-02/F-03)")
CURRENT["u"] = USE
# ① 기준 일치 자재(P_LEDGER: 재고 4 = 원장 합계 4) — 요청≠차감 → 확정 시 정확 수량
mv0 = cnt("stock_movements")
r = client.post("/stock/issues", data={"part_id": str(P_LEDGER), "qty": "3"})
chk("요청 생성 성공(303)", r.status_code == 303 and "success" in loc(r))
with db.db_session() as c:
    gi = c.execute("SELECT id FROM issues_out WHERE part_id=? ORDER BY id DESC", (P_LEDGER,)).fetchone()[0]
chk(f"  요청만으로 원장·재고 불변(원장 {mv0}건·재고 4)", cnt("stock_movements") == mv0 and stock_of(P_LEDGER) == 4)
r = client.post(f"/stock/issues/{gi}/approve")
with db.db_session() as c:
    _st = c.execute("SELECT status FROM issues_out WHERE id=?", (gi,)).fetchone()[0]
    _led = c.execute("SELECT COALESCE(SUM(quantity),0) FROM stock_movements WHERE part_id=?", (P_LEDGER,)).fetchone()[0]
chk("확정(ISSUED): 재고 4→1 · 원장 합계 4→1 · OUT 1행 (정확 수량 대조)",
    stock_of(P_LEDGER) == 1 and _led == 1 and _st == "ISSUED" and cnt("stock_movements") == mv0 + 1)
r = client.post(f"/stock/issues/{gi}/approve")
chk("중복 승인 차단(CAS 원자 점유·재기록 없음)", "already" in loc(r) and cnt("stock_movements") == mv0 + 1 and stock_of(P_LEDGER) == 1)
# ② 기준 불일치 자재(P_STOCK: 재고 100 ≠ 원장 4) — 확정 차단 = '100→1 덮어쓰기' 원천 방지
r = client.post("/stock/issues", data={"part_id": str(P_STOCK), "qty": "3"})
with db.db_session() as c:
    gi2 = c.execute("SELECT id FROM issues_out WHERE part_id=? ORDER BY id DESC", (P_STOCK,)).fetchone()[0]
mv1 = cnt("stock_movements")
r = client.post(f"/stock/issues/{gi2}/approve")
with db.db_session() as c:
    _st2 = c.execute("SELECT status FROM issues_out WHERE id=?", (gi2,)).fetchone()[0]
chk("기준 불일치(100 vs 4) 확정 차단 — PENDING 유지·원장 불변·재고 100 유지",
    r.status_code == 303 and _st2 == "PENDING" and cnt("stock_movements") == mv1 and stock_of(P_STOCK) == 100)
# ③ 중간 실패 주입 — 원장 저장 실패 시 ISSUED까지 전부 Rollback (판정서 §7 증빙표)
r = client.post("/stock/issues", data={"part_id": str(P_LEDGER), "qty": "1"})
with db.db_session() as c:
    gi3 = c.execute("SELECT id FROM issues_out WHERE part_id=? ORDER BY id DESC", (P_LEDGER,)).fetchone()[0]
_orig_tx = db.stock_movement_create_tx
def _boom(*a, **k):
    raise RuntimeError("주입: 원장 저장 실패")
db.stock_movement_create_tx = _boom
r = client.post(f"/stock/issues/{gi3}/approve")
db.stock_movement_create_tx = _orig_tx
with db.db_session() as c:
    _st3 = c.execute("SELECT status FROM issues_out WHERE id=?", (gi3,)).fetchone()[0]
chk("실패 주입 Rollback — PENDING 유지·OUT 0건 증가·재고 1 유지",
    r.status_code == 303 and _st3 == "PENDING" and cnt("stock_movements") == mv1 and stock_of(P_LEDGER) == 1)
r = client.post(f"/stock/issues/{gi3}/approve")
chk("주입 해제 후 정상 확정(재고 1→0·원장 합계 0)", stock_of(P_LEDGER) == 0)

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

print("[B4] BOM 폐기 라우트 — 환경 잠금 + 매트릭스 (F-03·v2 F-05)")
b = (cnt("bom_items", "project_id=?", (PJ_TEST,)), cnt("bom_uploads", "project_id=?", (PJ_TEST,)), cnt("bom_item_history", "project_id=?", (PJ_TEST,)))
os.environ.pop("KNK_ENABLE_BOM_PURGE", None)
CURRENT["u"] = CEO
r = client.post(f"/projects/{PJ_TEST}/bom/purge", data={"confirm_code": "999T001"})
chk("환경 잠금: 스위치 없으면 관리자+테스트 접두라도 차단", r.status_code == 303 and "error" in loc(r))
chk(f"  BOM 3표 불변 {b}", (cnt("bom_items", "project_id=?", (PJ_TEST,)), cnt("bom_uploads", "project_id=?", (PJ_TEST,)), cnt("bom_item_history", "project_id=?", (PJ_TEST,))) == b)
os.environ["KNK_ENABLE_BOM_PURGE"] = "1"
CURRENT["u"] = USE  # 관리자 아님
r = client.post(f"/projects/{PJ_TEST}/bom/purge", data={"confirm_code": "999T001"})
chk("비관리자 폐기 차단(관리자 전용)", r.status_code == 303 and "error" in loc(r))
chk(f"  BOM 3표 불변 {b}", (cnt("bom_items", "project_id=?", (PJ_TEST,)), cnt("bom_uploads", "project_id=?", (PJ_TEST,)), cnt("bom_item_history", "project_id=?", (PJ_TEST,))) == b)
CURRENT["u"] = CEO
r = client.post(f"/projects/{PJ_REAL}/bom/purge", data={"confirm_code": "002M2599"})
chk("운영 관리번호 폐기 차단(라우트층)", r.status_code == 303 and "error" in loc(r) and cnt("bom_items", "project_id=?", (PJ_REAL,)) >= 1)
r = client.post(f"/projects/{PJ_TEST}/bom/purge", data={"confirm_code": "999T001"})
chk("스위치+테스트(999 접두)+관리자+타이핑 일치 → 폐기 허용", r.status_code == 303 and "success" in loc(r) and cnt("bom_items", "project_id=?", (PJ_TEST,)) == 0)

print("[B5] 프로젝트 삭제·완전폐기의 BOM 보존 (게이트 v2 F-04 · 대표 승인)")
b = (cnt("bom_items", "project_id=?", (PJ_REAL,)), cnt("bom_uploads", "project_id=?", (PJ_REAL,)), cnt("bom_item_history", "project_id=?", (PJ_REAL,)))
try:
    db.projects_delete_logi(PJ_REAL, force=True)
    chk("완전폐기(force) 차단", False, "예외 없이 삭제됨!")
except PermissionError as e:
    chk("완전폐기(force)도 자재·구매 이력에 차단(PermissionError)", "자재·구매 이력" in str(e), str(e)[:60])
after = (cnt("bom_items", "project_id=?", (PJ_REAL,)), cnt("bom_uploads", "project_id=?", (PJ_REAL,)), cnt("bom_item_history", "project_id=?", (PJ_REAL,)))
chk(f"  BOM 3표 불변 {b}→{after} (판정서 §7 증빙표)", b == after and all(b))
CURRENT["u"] = CEO
r = client.post(f"/projects/{PJ_REAL}/delete", data={})
chk("일반 삭제 라우트 차단 + 프로젝트 보존", r.status_code in (403, 500) and cnt("projects", "id=?", (PJ_REAL,)) == 1)
r = client.post("/projects/bulk-delete", data={"ids": str(PJ_REAL)})
chk("일괄 삭제도 차단(실패 집계) + BOM 보존",
    cnt("projects", "id=?", (PJ_REAL,)) == 1 and cnt("bom_items", "project_id=?", (PJ_REAL,)) == b[0])
db.projects_delete_logi(PJ_TEST2, force=True)
chk("테스트(999 접두) 프로젝트는 완전삭제 허용(예외 동작 확인)", cnt("projects", "id=?", (PJ_TEST2,)) == 0)

print(f"\n==== 결과: PASS {ok} / FAIL {fail} ====")
sys.exit(1 if fail else 0)
