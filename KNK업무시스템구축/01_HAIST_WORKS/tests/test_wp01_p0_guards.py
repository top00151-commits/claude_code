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
    for uid, nm, tid, role in ((501, "조회자", 3, "member"), (502, "구매팀원", 10, "member"),
                               (503, "대표", 11, "ceo"), (504, "시스템관리자", 11, "admin")):
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

    # ── v4 시드 (게이트 v3 F-01/F-02/F-05) ──
    P_DIR = _part("WPR-DIR", "직접출고 시험 자재")          # 재고 2 = 원장 2 (기준 일치)
    c.execute("INSERT INTO stock_movements (movement_no, part_id, kind, quantity, unit_price, remaining_qty, occurred_at)"
              " VALUES ('WPDIR-0',?,'IN',2,100,2,?)", (P_DIR, D(2)))
    c.execute("UPDATE parts SET stock_qty=2 WHERE id=?", (P_DIR,))
    P_RCV = _part("WPR-RCV", "입고 시험 자재")               # 재고 0 = 원장 0
    c.execute("INSERT INTO purchase_orders (po_number, status, order_date) VALUES ('WP-RCV','발주완료',?)", (TODAY.isoformat(),))
    PO_RECV = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO po_items (po_id, line_no, part_id, quantity, received_qty, unit, unit_price) VALUES (?,1,?,10,0,'EA',100)", (PO_RECV, P_RCV))
    POI_A = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO po_items (po_id, line_no, part_id, quantity, received_qty, unit, unit_price) VALUES (?,2,?,5,0,'EA',100)", (PO_RECV, P_RCV))
    POI_B = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    # 변경·품질 이력만 있는 프로젝트(관리번호 없음) — 게이트 v3 F-02 독립 재현 조건
    c.execute("INSERT INTO projects (name, status) VALUES ('오등록(이력 있음)','진행중')")
    PJ_HIST = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO changes (change_no, change_type, title, project_id, author_id) VALUES ('CHG-WP01-1','BOM','변경 1건',?,503)", (PJ_HIST,))
    CHG_1 = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO change_reads (change_id, user_id, read_at) VALUES (?,503,datetime('now'))", (CHG_1,))
    c.execute("INSERT INTO issues (issue_no, title, project_id) VALUES ('ISS-WP01-1','품질이슈 1건',?)", (PJ_HIST,))
    ISS_1 = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO issue_logs (issue_id, user_id, action, content) VALUES (?,503,'코멘트','로그 1건')", (ISS_1,))
    # 참조 0건 프로젝트(관리번호 없음) — 오등록 정리는 계속 가능해야 함
    c.execute("INSERT INTO projects (name, status) VALUES ('오등록(무이력)','진행중')")
    PJ_EMPTY = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    # ── v5 시드 (게이트 v4 F-01): 이름이 다른 별칭 FK·프로젝트 자기참조 ──
    c.execute("INSERT INTO projects (name, status) VALUES ('소모품 연결만 있는 건','진행중')")
    PJ_LINK = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO consumable_orders (co_no, customer_name, status) VALUES ('CO-WP01','시험고객','진행중')")
    CO_1 = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO consumable_order_items (co_id, line_no, part_name, qty, linked_project_id)"
              " VALUES (?,1,'소모품 품목',1,?)", (CO_1, PJ_LINK))
    COI_1 = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO projects (name, status) VALUES ('부모 장비(관리번호 없음)','진행중')")
    PJ_PARENT = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO projects (name, status, parent_project_id) VALUES ('자식 수리건','진행중',?)", (PJ_PARENT,))
    PJ_CHILD = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    # 혼합(직접 project_id + 간접 + 별칭 FK) — 한 프로젝트에 섞인 경우
    c.execute("INSERT INTO consumable_order_items (co_id, line_no, part_name, qty, linked_project_id)"
              " VALUES (?,2,'혼합 시험 품목',1,?)", (CO_1, PJ_HIST))
    # 자재 병합 대체컬럼 2번째 — merged_part_id 명시 시험 (게이트 v3 §5-2)
    P_MERGED = _part("WPR-MGD", "병합된(흡수) 자재")
    c.execute("INSERT INTO part_merge_log (canonical_id, merged_part_id, canonical_part_no, merged_part_no) VALUES (?,?,?,?)",
              (999998, P_MERGED, "WPR-CANON", "WPR-MGD"))

    # KPI 시드: 오늘-6(경계 포함)·오늘-7(경계 밖)·오늘-2 입고 3행
    for i, (d_, q) in enumerate(((D(6), 1), (D(7), 1), (D(2), 2))):
        c.execute(
            "INSERT INTO stock_movements (movement_no, part_id, kind, quantity, unit_price, remaining_qty, occurred_at)"
            " VALUES (?,?, 'IN', ?, 100, ?, ?)", (f"WPK-{i}", P_STOCK, q, q, d_))

print("═══ A부: 함수 수준 ═══")
print("[A1] stock_kpi 계약 (P0-01·F-07 경계)")
k = db.stock_kpi()
chk("recent_receipts=달력 7일(오늘-6 포함·오늘-7 제외) 품목행 6건", k.get("recent_receipts") == 6, k.get("recent_receipts"))
chk("total_qty=활성 수량 합(100+4+2=106)", k.get("total_qty") == 106, k.get("total_qty"))
chk("po_pending=작성중2+발주완료2+부분입고1=5", k.get("po_pending") == 5, k.get("po_pending"))
chk("기존 키 불변", all(x in k for x in ("stock_value", "low_stock", "in_30d", "out_30d", "parts_total")))

print("[A2] parts_delete — 전참조 차단 (F-01: part_id·*_part_id·명시 컬럼)")
for pid, ref_t, ref_col, nm in (
    (P_ISSUE, "issues_out", "part_id", "출고요청 참조"),
    (P_BOM, "bom_items", "part_id", "BOM 참조"),
    (P_REG, "material_request_items", "registered_part_id", "구매요청 대체컬럼 참조"),
    (P_MERGE, "part_merge_log", "canonical_id", "병합 Audit 참조"),
    (P_MERGED, "part_merge_log", "merged_part_id", "병합 Audit 참조(merged_part_id)"),
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

print("[A5] stock_issue — 직접차감 출고 잠금 + 기준 대조 (게이트 v3 F-01)")
os.environ.pop("KNK_ENABLE_STOCK_DIRECT_ISSUE", None)
mv0, s0 = cnt("stock_movements"), stock_of(P_DIR)
try:
    db.stock_issue({"part_id": P_DIR, "quantity": 1}, 502)
    chk("잠금 상태 직접출고 차단", False, "예외 없이 출고됨!")
except ValueError as e:
    chk("잠금 상태 직접출고 차단(ValueError)", "잠겨" in str(e), str(e)[:60])
chk(f"  원장 {mv0}건·재고 {s0} 불변", cnt("stock_movements") == mv0 and stock_of(P_DIR) == s0)
os.environ["KNK_ENABLE_STOCK_DIRECT_ISSUE"] = "1"
try:
    db.stock_issue({"part_id": P_STOCK, "quantity": 3}, 502)
    chk("기준 불일치(재고 100·원장 4) 직접출고 차단", False, "예외 없이 출고됨! (100→1 손상 재현)")
except ValueError as e:
    chk("기준 불일치(재고 100·원장 4) 직접출고 차단(ValueError)", "기준수량" in str(e), str(e)[:70])
chk("  재고 100 유지·원장 불변 (판정서 §7 증빙표)", stock_of(P_STOCK) == 100 and cnt("stock_movements") == mv0)
try:
    db.stock_issue({"part_id": P_DIR, "quantity": 5}, 502)
    chk("가용량 초과 차단", False, "예외 없이 출고됨!")
except ValueError as e:
    chk("가용량 초과 차단(음수 재고 금지)", "재고 부족" in str(e), str(e)[:60])
db.stock_issue({"part_id": P_DIR, "quantity": 1}, 502)
chk("잠금 해제+기준 일치 시 정상 출고(재고 2→1·OUT 1행)",
    stock_of(P_DIR) == 1 and cnt("stock_movements") == mv0 + 1)
os.environ.pop("KNK_ENABLE_STOCK_DIRECT_ISSUE", None)

print("[A6] po_receive — 입고 단일 Transaction·실패 Rollback (게이트 v3 F-05)")


def po_state():
    with db.db_session() as c:
        rq = c.execute("SELECT COALESCE(SUM(received_qty),0) FROM po_items WHERE po_id=?", (PO_RECV,)).fetchone()[0]
        st = c.execute("SELECT status FROM purchase_orders WHERE id=?", (PO_RECV,)).fetchone()[0]
    return (rq, st, cnt("stock_movements"), stock_of(P_RCV))


_rcv_before = po_state()
# ⓪ 운영 잠금 — 스위치 없으면 입고 자체가 막힌다 (검수·격리재고 없는 가용재고 증가 차단)
os.environ.pop("KNK_ENABLE_PO_RECEIVE", None)
res = db.po_receive(PO_RECV, [{"po_item_id": POI_A, "receive_qty": 3}], 502)
chk("잠금 상태 발주 입고 차단(ok=False)", (not res.get("ok")) and "준비 중" in res.get("error", ""), res)
chk(f"  PO 수량·상태·원장·재고 불변 {_rcv_before}", po_state() == _rcv_before)
os.environ["KNK_ENABLE_PO_RECEIVE"] = "1"
_orig_tx = db.stock_movement_create_tx


def _boom_tx(*a, **k):
    raise RuntimeError("주입: 입고 원장 저장 실패")


db.stock_movement_create_tx = _boom_tx
try:
    db.po_receive(PO_RECV, [{"po_item_id": POI_A, "receive_qty": 3}], 502)
    chk("실패 주입 입고 — 오류 전파", False, "예외 없이 통과!")
except RuntimeError:
    chk("실패 주입 입고 — 오류 전파(RuntimeError)", True)
db.stock_movement_create_tx = _orig_tx
chk(f"  전부 Rollback — PO 수량·상태·원장·재고 불변 {_rcv_before} (판정서 §7 증빙표)",
    po_state() == _rcv_before and _rcv_before[0] == 0)
res = db.po_receive(PO_RECV, [{"po_item_id": POI_A, "receive_qty": 3},
                              {"po_item_id": POI_B, "receive_qty": 99}], 502)
chk("한 라인이 발주 수량 초과면 전부 Rollback(앞 라인도 커밋 안 됨)",
    (not res.get("ok")) and po_state() == _rcv_before, f"{res} / {po_state()}")
res = db.po_receive(PO_RECV, [{"po_item_id": POI_A, "receive_qty": 3}], 502)
chk("잠금 해제 시 정상 입고 — 수량 3·상태 부분입고·원장 +1행·재고 3",
    res.get("ok") and po_state() == (3, "부분입고", _rcv_before[2] + 1, 3), po_state())
os.environ.pop("KNK_ENABLE_PO_RECEIVE", None)

print("[A7] projects_delete_logi — 완전삭제 운영 잠금 + 전참조 (게이트 v3 F-02 · 대표 결정)")


def hist5():
    return (cnt("projects", "id=?", (PJ_HIST,)), cnt("changes", "project_id=?", (PJ_HIST,)),
            cnt("change_reads", "change_id=?", (CHG_1,)), cnt("issues", "project_id=?", (PJ_HIST,)),
            cnt("issue_logs", "issue_id=?", (ISS_1,)))


os.environ.pop("KNK_ENABLE_PROJECT_HARD_DELETE", None)
_h0 = hist5()
try:
    db.projects_delete_logi(PJ_HIST, force=True)
    chk("변경·품질 이력만 있는 프로젝트 완전폐기 차단", False, "예외 없이 삭제됨!")
except PermissionError as e:
    chk("변경·품질 이력 프로젝트 완전폐기(force) 차단(PermissionError)", "이력" in str(e), str(e)[:70])
chk(f"  프로젝트·변경·확인·이슈·로그 5종 각 1건 불변 {_h0}", hist5() == _h0 == (1, 1, 1, 1, 1))
try:
    db.projects_delete_logi(PJ_REAL, force=True)
    chk("운영 관리번호 프로젝트 완전폐기 차단", False, "예외 없이 삭제됨!")
except PermissionError as e:
    chk("운영 관리번호(002M2599) 완전폐기 차단", "관리번호" in str(e), str(e)[:70])
# 게이트 v4 F-01: 이름이 다른 별칭 FK(consumable_order_items.linked_project_id)


def link_state(coi, pj):
    with db.db_session() as c:
        lp = c.execute("SELECT linked_project_id FROM consumable_order_items WHERE id=?", (coi,)).fetchone()[0]
    return (cnt("projects", "id=?", (pj,)), cnt("consumable_order_items", "id=?", (coi,)), lp)


_l0 = link_state(COI_1, PJ_LINK)
try:
    db.projects_delete_logi(PJ_LINK, force=True)
    chk("소모품 연결(linked_project_id)만 있는 프로젝트 삭제 차단", False, "예외 없이 삭제됨!")
except PermissionError as e:
    chk("소모품 연결(linked_project_id) 프로젝트 삭제 차단(PermissionError)",
        "linked_project_id" in str(e), str(e)[:80])
chk(f"  프로젝트·소모품 품목·연결값 불변 {_l0}", link_state(COI_1, PJ_LINK) == _l0 and _l0[2] == PJ_LINK)
# 게이트 v4 F-01: 프로젝트 자기참조(projects.parent_project_id)


def parent_state():
    with db.db_session() as c:
        pp = c.execute("SELECT parent_project_id FROM projects WHERE id=?", (PJ_CHILD,)).fetchone()[0]
    return (cnt("projects", "id=?", (PJ_PARENT,)), cnt("projects", "id=?", (PJ_CHILD,)), pp)


_p0 = parent_state()
try:
    db.projects_delete_logi(PJ_PARENT, force=True)
    chk("자식(parent_project_id)이 있는 부모 프로젝트 삭제 차단", False, "예외 없이 삭제됨!")
except PermissionError as e:
    chk("자식(parent_project_id) 있는 부모 프로젝트 삭제 차단(PermissionError)",
        "parent_project_id" in str(e), str(e)[:80])
chk(f"  부모·자식·연결값 불변 {_p0}", parent_state() == _p0 and _p0[2] == PJ_PARENT)
# 혼합(직접 project_id + 간접 자식 + 별칭 FK)이 한 프로젝트에 섞인 경우 — 전부 열거하며 차단
try:
    db.projects_delete_logi(PJ_HIST, force=True)
    chk("혼합 참조 프로젝트 삭제 차단", False, "예외 없이 삭제됨!")
except PermissionError as e:
    _msg = str(e)
    chk("혼합 참조 — 직접·간접·별칭을 모두 열거하며 차단",
        "changes.project_id" in _msg and "linked_project_id" in _msg
        and ("change_reads" in _msg or "issue_logs" in _msg or "issues.project_id" in _msg), _msg[:140])
db.projects_delete_logi(PJ_EMPTY)
chk("참조 0건 오등록 프로젝트는 정상 삭제(기존 정리 기능 유지)", cnt("projects", "id=?", (PJ_EMPTY,)) == 0)

print("═══ B부: 라우트 수준 (실HTTP·TestClient) ═══")
import app.main as appmain  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

CURRENT = {"u": None}
appmain.get_user = lambda request: CURRENT["u"]  # 인증만 대체 — 인가(can_*)는 실제 로직 실행
client = TestClient(appmain.app, follow_redirects=False)

VIEW = {"id": 501, "name": "조회자", "role": "member", "team_id": 3, "can_use_logistics": 0, "can_view_logistics": 1}
USE = {"id": 502, "name": "구매팀원", "role": "member", "team_id": 10, "can_use_logistics": 0, "can_view_logistics": 1}
CEO = {"id": 503, "name": "대표", "role": "ceo", "team_id": 11, "can_use_logistics": 1, "can_view_logistics": 1}
# 게이트 v3 F-03: 시스템 관리 역할만 있고 자재 담당·물류 권한은 없는 사용자 (업무 승인 불가여야 함)
ADMIN = {"id": 504, "name": "시스템관리자", "role": "admin", "team_id": 11, "can_use_logistics": 0, "can_view_logistics": 1}


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

# ── 게이트 v3 F-01 필수 증빙: '쓰기 권한' 사용자도 직접출고 불가 (서버 잠금) ──
CURRENT["u"] = USE
r = client.get("/stock/issue")
chk("쓰기 권한 GET /stock/issue → 출고 요청 화면으로 안내(직접차감 화면 차단)",
    r.status_code == 303 and "/stock/issues" in loc(r))
mvA, stA, rcA = cnt("stock_movements"), stock_of(P_STOCK), cnt("receipts")
r = client.post("/stock/issue", data={"part_id": str(P_STOCK), "quantity": "3"})
chk("쓰기 권한 POST /stock/issue → 403 차단", r.status_code == 403, r.status_code)
chk(f"  원장·재고·입고문서 불변 ({mvA}건·{stA}·{rcA}건)",
    cnt("stock_movements") == mvA and stock_of(P_STOCK) == stA and cnt("receipts") == rcA)
r = client.post("/stock/receipts", data={"part_id": str(P_STOCK), "qty": "5"})
chk("POST /stock/receipts(골격 입고) → 403 잠금 (F-05)", r.status_code == 403, r.status_code)
chk("  입고문서·원장 불변", cnt("receipts") == rcA and cnt("stock_movements") == mvA)

# ── 게이트 v4 F-02 필수 증빙: 발주서 입고도 화면·서버 2겹 차단 ──
_po_before = po_state()
r = client.get(f"/po/{PO_RECV}/receive")
chk("GET /po/{id}/receive → 발주 상세로 '준비 중' 안내(303)", r.status_code == 303 and "error" in loc(r))
r = client.post(f"/po/{PO_RECV}/receive", data={"po_item_id": str(POI_A), "receive_qty": "3"})
chk("POST /po/{id}/receive → 403 차단", r.status_code == 403, r.status_code)
chk(f"  PO 수량·상태·원장·재고 불변 {_po_before} · 입고문서 {rcA}건 불변",
    po_state() == _po_before and cnt("receipts") == rcA)
# 화면 링크 자체가 남아 있지 않은지 (버튼 숨김이 아니라 제거 — F-01)
for _tpl in ("app/templates/stock_issues.html", "app/templates/_v5_partials/chrome.html",
             "app/templates/logistics_home.html"):
    _txt = open(_tpl, encoding="utf-8").read()
    chk(f"  {os.path.basename(_tpl)} 에 /stock/issue 링크 없음",
        '"/stock/issue"' not in _txt and "'/stock/issue'" not in _txt)
# 게이트 v4 F-03: 잠긴 기능은 '준비 중'을 진입 전에 알린다 + 사실과 다른 문구 제거
_t_po = open("app/templates/po_detail.html", encoding="utf-8").read()
chk("po_detail.html — 입고 처리 링크 제거 + '준비 중' 표시", "/receive\"" not in _t_po and "준비 중" in _t_po)
_t_pol = open("app/templates/po_list.html", encoding="utf-8").read()
chk("po_list.html — 없는 절차('검수 종결')를 화면에 표시하지 않음(주석 제외)",
    ">검수 종결<" not in _t_pol and ">발주 수량 충족<" in _t_pol)
chk("chrome.html — 사이드바 '출고 요청 (준비 중)'",
    "출고 요청 (준비 중)" in open("app/templates/_v5_partials/chrome.html", encoding="utf-8").read())
_t_home = open("app/templates/logistics_home.html", encoding="utf-8").read()
chk("logistics_home.html — 빠른 실행 입고·출고 '(준비 중)'",
    "입고 처리 (준비 중)" in _t_home and "출고 요청 (준비 중)" in _t_home)

print("[B2] 출고 확정 = 운영 잠금·승인권한 분리·자기승인 차단·단일 Transaction (게이트 v3 F-03 + v2 F-02/F-03)")
CURRENT["u"] = USE
# ① 기준 일치 자재(P_LEDGER: 재고 4 = 원장 합계 4) — 요청≠차감 → 확정 시 정확 수량
mv0 = cnt("stock_movements")
r = client.post("/stock/issues", data={"part_id": str(P_LEDGER), "qty": "3"})
chk("요청 생성 성공(303)", r.status_code == 303 and "success" in loc(r))
with db.db_session() as c:
    gi = c.execute("SELECT id FROM issues_out WHERE part_id=? ORDER BY id DESC", (P_LEDGER,)).fetchone()[0]
chk(f"  요청만으로 원장·재고 불변(원장 {mv0}건·재고 4)", cnt("stock_movements") == mv0 and stock_of(P_LEDGER) == 4)


def issue_state(gid):
    with db.db_session() as c:
        return c.execute("SELECT status FROM issues_out WHERE id=?", (gid,)).fetchone()[0]


# ⓪ 운영 잠금 — 스위치 없으면 승인 자체가 막힌다 (WP-08 전 임시 구조)
os.environ.pop("KNK_ENABLE_STOCK_ISSUE_APPROVE", None)
r = client.post(f"/stock/issues/{gi}/approve")
chk("잠금 상태 승인 차단(303 안내)", r.status_code == 303 and "error" in loc(r))
chk("  PENDING 유지·원장·재고 불변",
    issue_state(gi) == "PENDING" and cnt("stock_movements") == mv0 and stock_of(P_LEDGER) == 4)
os.environ["KNK_ENABLE_STOCK_ISSUE_APPROVE"] = "1"
# ①-a 자기승인 차단 (요청자 = 현재 사용자) — 판정서 §7 증빙표
r = client.post(f"/stock/issues/{gi}/approve")
chk("자기승인 차단(요청자 본인) — PENDING 유지·OUT 0건·재고 불변",
    r.status_code == 303 and "error" in loc(r) and issue_state(gi) == "PENDING"
    and cnt("stock_movements") == mv0 and stock_of(P_LEDGER) == 4)
# ①-b 시스템 관리 역할만으로는 승인 불가 (등록권한·승인권한 분리)
CURRENT["u"] = ADMIN
r = client.post(f"/stock/issues/{gi}/approve")
chk("관리자 역할만으로 승인 불가(403) + 불변",
    r.status_code == 403 and issue_state(gi) == "PENDING" and cnt("stock_movements") == mv0)
# ①-c 자재 승인 권한자(요청자와 다른 사람)가 승인 → 정확 수량
CURRENT["u"] = CEO
r = client.post(f"/stock/issues/{gi}/approve")
with db.db_session() as c:
    _st = c.execute("SELECT status FROM issues_out WHERE id=?", (gi,)).fetchone()[0]
    _led = c.execute("SELECT COALESCE(SUM(quantity),0) FROM stock_movements WHERE part_id=?", (P_LEDGER,)).fetchone()[0]
chk("확정(ISSUED): 재고 4→1 · 원장 합계 4→1 · OUT 1행 (정확 수량 대조)",
    stock_of(P_LEDGER) == 1 and _led == 1 and _st == "ISSUED" and cnt("stock_movements") == mv0 + 1)
r = client.post(f"/stock/issues/{gi}/approve")
chk("중복 승인 차단(CAS 원자 점유·재기록 없음)", "already" in loc(r) and cnt("stock_movements") == mv0 + 1 and stock_of(P_LEDGER) == 1)
# ② 기준 불일치 자재(P_STOCK: 재고 100 ≠ 원장 4) — 확정 차단 = '100→1 덮어쓰기' 원천 방지
CURRENT["u"] = USE          # 요청자
r = client.post("/stock/issues", data={"part_id": str(P_STOCK), "qty": "3"})
with db.db_session() as c:
    gi2 = c.execute("SELECT id FROM issues_out WHERE part_id=? ORDER BY id DESC", (P_STOCK,)).fetchone()[0]
mv1 = cnt("stock_movements")
CURRENT["u"] = CEO          # 승인자(요청자와 다른 사람)
r = client.post(f"/stock/issues/{gi2}/approve")
chk("기준 불일치(100 vs 4) 확정 차단 — PENDING 유지·원장 불변·재고 100 유지",
    r.status_code == 303 and issue_state(gi2) == "PENDING"
    and cnt("stock_movements") == mv1 and stock_of(P_STOCK) == 100)
# ③ 중간 실패 주입 — 원장 저장 실패 시 ISSUED까지 전부 Rollback (판정서 §7 증빙표)
CURRENT["u"] = USE
r = client.post("/stock/issues", data={"part_id": str(P_LEDGER), "qty": "1"})
with db.db_session() as c:
    gi3 = c.execute("SELECT id FROM issues_out WHERE part_id=? ORDER BY id DESC", (P_LEDGER,)).fetchone()[0]
CURRENT["u"] = CEO
_orig_tx = db.stock_movement_create_tx
def _boom(*a, **k):
    raise RuntimeError("주입: 원장 저장 실패")
db.stock_movement_create_tx = _boom
r = client.post(f"/stock/issues/{gi3}/approve")
db.stock_movement_create_tx = _orig_tx
chk("실패 주입 Rollback — PENDING 유지·OUT 0건 증가·재고 1 유지",
    r.status_code == 303 and issue_state(gi3) == "PENDING"
    and cnt("stock_movements") == mv1 and stock_of(P_LEDGER) == 1)
r = client.post(f"/stock/issues/{gi3}/approve")
chk("주입 해제 후 정상 확정(재고 1→0·원장 합계 0)", stock_of(P_LEDGER) == 0)
os.environ.pop("KNK_ENABLE_STOCK_ISSUE_APPROVE", None)

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

print("[B5] 프로젝트 삭제 3경로 — 자재·수주·변경·품질 이력 보존 (게이트 v3 F-02 · 대표 결정)")
b = (cnt("bom_items", "project_id=?", (PJ_REAL,)), cnt("bom_uploads", "project_id=?", (PJ_REAL,)), cnt("bom_item_history", "project_id=?", (PJ_REAL,)))
try:
    db.projects_delete_logi(PJ_REAL, force=True)
    chk("완전폐기(force) 차단", False, "예외 없이 삭제됨!")
except PermissionError as e:
    chk("완전폐기(force)도 차단(PermissionError)", "관리번호" in str(e), str(e)[:70])
after = (cnt("bom_items", "project_id=?", (PJ_REAL,)), cnt("bom_uploads", "project_id=?", (PJ_REAL,)), cnt("bom_item_history", "project_id=?", (PJ_REAL,)))
chk(f"  BOM 3표 불변 {b}→{after} (판정서 §7 증빙표)", b == after and all(b))
CURRENT["u"] = CEO
r = client.post(f"/projects/{PJ_REAL}/delete", data={})
chk("일반 삭제 라우트 차단 + 프로젝트 보존", r.status_code in (403, 500) and cnt("projects", "id=?", (PJ_REAL,)) == 1)
r = client.post("/projects/bulk-delete", data={"ids": str(PJ_REAL)})
chk("일괄 삭제도 차단(실패 집계) + BOM 보존",
    cnt("projects", "id=?", (PJ_REAL,)) == 1 and cnt("bom_items", "project_id=?", (PJ_REAL,)) == b[0])
# 변경·확인·이슈·로그 각 1건인 프로젝트: 일반·일괄 라우트도 차단 + 5종 행 수 불변 (§7-6)
_h1 = hist5()
r = client.post(f"/projects/{PJ_HIST}/delete", data={})
chk("변경·품질 이력 프로젝트 — 일반 삭제 라우트 차단", r.status_code in (403, 500))
r = client.post("/projects/bulk-delete", data={"ids": str(PJ_HIST)})
chk(f"  일괄 삭제도 차단 · 프로젝트·변경·확인·이슈·로그 5종 불변 {_h1}",
    hist5() == _h1 == (1, 1, 1, 1, 1), hist5())
# 잠금 해제(대표 지시 임시 활성) 시에만 완전삭제 가능 — 테스트 정리·데모 초기화용
os.environ["KNK_ENABLE_PROJECT_HARD_DELETE"] = "1"
db.projects_delete_logi(PJ_TEST2, force=True)
chk("잠금 임시 해제 시 완전삭제 가능(테스트 정리 경로 유지)", cnt("projects", "id=?", (PJ_TEST2,)) == 0)
os.environ.pop("KNK_ENABLE_PROJECT_HARD_DELETE", None)

print(f"\n==== 결과: PASS {ok} / FAIL {fail} ====")
sys.exit(1 if fail else 0)
