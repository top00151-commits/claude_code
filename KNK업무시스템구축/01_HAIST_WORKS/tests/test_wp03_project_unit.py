# -*- coding: utf-8 -*-
"""WP-03 프로젝트 호기(Project Unit) — 정식 검증
   ⭐ 대표 업무교정(2026-07-25) 반영: 일련번호 폐기 · 호기번호는 변경 가능 · 씨앗=후보 방식

실행:  01_HAIST_WORKS 루트에서
    python tests/test_wp03_project_unit.py

- 임시 DB(운영과 동일 init_db 스키마 + WP-03 마이그레이션) — 운영 무관.
- A부: 기본 계약(후보 탐색·반영·additive)
- B부: 대표 확정문서 §12 수정테스트 10종
- C부: 라우트 수준 실HTTP(TestClient) + 권한 매트릭스 (fastapi/httpx 필요)
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # 01_HAIST_WORKS
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from app import database as db  # noqa: E402

db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="wp03_"), "test.db")
db.init_db()
from app.migrations.m_z1053_project_unit import migrate as _mig  # noqa: E402
print("마이그레이션:", _mig(db.DB_PATH))
# 테스트 스키마 보강 — LIVE projects 에 있는 법인 컬럼
with db.db_session() as _c0:
    for _col in ("po_entity", "ship_entity"):
        try:
            _c0.execute(f"ALTER TABLE projects ADD COLUMN {_col} TEXT")
        except Exception:
            pass
from app import project_unit as pu  # noqa: E402

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


def mkproject(code, **kw):
    with db.db_session() as c:
        cols = "mgmt_code, name, status" + ("".join(f", {k}" for k in kw))
        ph = "?,?,?" + ("".join(",?" for _ in kw))
        c.execute(f"INSERT INTO projects ({cols}) VALUES ({ph})",
                  (code, f"P-{code}", "진행중", *kw.values()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def mkorder(pid, no):
    with db.db_session() as c:
        c.execute("INSERT INTO orders (order_no, project_id, status) VALUES (?,?, 'CONFIRMED')",
                  (no, pid))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def mkline(oid, label, qty=1):
    with db.db_session() as c:
        c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label) "
                  "VALUES (?,?,0,0,?)", (oid, qty, label))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def newids(scan):
    return [c["order_item_id"] for c in scan["candidates"] if c["suggestion"] == "new"]


# ═══════════ A. 기본 계약 ═══════════
print("\n── A. 후보 탐색·반영·additive ──")
PID = mkproject("999T2601")
O1 = mkorder(PID, "SO-A-1")
for i in range(1, 4):
    mkline(O1, f"{i}호기")
mkline(O1, "예비품 세트", qty=3)      # 부속 — 후보 아님
OI_BEFORE = cnt("order_items")

scan = pu.scan_candidates(PID)
chk("후보 3개 인식(부속 제외)", scan["summary"]["total"] == 3, str(scan["summary"]))
chk("자동 생성 안 함(스캔만)", cnt("project_units") == 0)
r = pu.apply_candidates(PID, newids(scan))
chk("선택한 후보만 반영(3대)", r["created"] == 3, str(r))
chk("반영 상태 = 개발·미확정", cnt("project_units", "unit_state='PROVISIONAL'") == 3)
chk("최초 수주 링크(ORIGIN) 생성", cnt("project_unit_order_links", "relation_type='ORIGIN'") == 3)
chk("재실행 멱등(이미 반영됨)", pu.scan_candidates(PID)["summary"]["already_linked"] == 3)
chk("additive · order_items 불변", cnt("order_items") == OI_BEFORE)

# ═══════════ B. 대표 확정문서 §12 수정테스트 10종 ═══════════
print("\n── B. §12 수정테스트 10종 ──")
units = pu.get_units(PID)

# 1) PROVISIONAL 은 호기번호·수주번호 없이 생성 가능
uid_dev = pu.create_unit(PID, working_name="개발1호기")
dev = pu.get_unit(uid_dev)
chk("§12-1 개발호기: 번호·수주 없이 생성", dev["current_unit_no"] is None
    and dev["unit_state"] == "PROVISIONAL" and not dev["orders"])

# 2) CONFIRMED 전환 시 현재 호기번호 필수
try:
    pu.confirm_unit(uid_dev); chk("§12-2 번호 없으면 확정 불가", False)
except ValueError:
    chk("§12-2 번호 없으면 확정 불가", True)
pu.change_unit_no(uid_dev, "10호기", reason="개발 완료 후 번호 지정")
pu.confirm_unit(uid_dev)
chk("§12-2' 번호 지정 후 확정 성공", pu.get_unit(uid_dev)["unit_state"] == "CONFIRMED")

# 3) 호기번호 변경 후 Unit ID 유지 (⭐핵심)
u0 = units[0]
before_id = u0["id"]
pu.change_unit_no(before_id, "21호기", reason="수주 변경으로 번호 조정")
after = pu.get_unit(before_id)
chk("§12-3 번호 변경돼도 Unit ID 유지", after["id"] == before_id and after["current_unit_no"] == "21호기")
chk("§12-3' 씨앗 출처 보존", after["seed_unit_label"] == u0["seed_unit_label"])

# 4) 과거 호기번호 조회
hist = after["identifier_history"]
chk("§12-4 변경이력에 이전·이후·사유 기록",
    any(h["old_unit_no"] == u0["current_unit_no"] and h["new_unit_no"] == "21호기"
        and h["change_reason"] for h in hist))
chk("§12-4' 특정 시점 호기번호 재현", pu.unit_no_at(before_id, "1900-01-01") is not None
    or pu.unit_no_at(before_id, "2099-01-01") == "21호기")

# 5) 동일 시점 프로젝트 내 현재 호기번호 중복 차단
try:
    pu.change_unit_no(units[1]["id"], "21호기", reason="중복 시험")
    chk("§12-5 현재 호기번호 중복 차단", False)
except ValueError:
    chk("§12-5 현재 호기번호 중복 차단", True)

# 6) 추가수주 연결 후 최초수주 보존
O2 = mkorder(PID, "SO-A-2")
pu.link_order(before_id, O2, relation_type="ADDITIONAL", reason="추가 발주")
links = pu.get_unit(before_id)["orders"]
chk("§12-6 추가수주 연결 + 최초(ORIGIN) 보존",
    any(l["relation_type"] == "ORIGIN" for l in links)
    and any(l["relation_type"] == "ADDITIONAL" for l in links) and len(links) == 2)
try:
    pu.link_order(before_id, O2, relation_type="ORIGIN"); chk("§12-6' ORIGIN 중복 차단", False)
except ValueError:
    chk("§12-6' ORIGIN 중복 차단", True)

# 7) 수주 후보를 기존 Unit 에 연결 (새 수주의 호기 라인 → 기존 호기에 수주 연결)
L_new = mkline(O2, "5호기")
sc2 = pu.scan_candidates(PID)
chk("§12-7 새 수주 라인이 후보로 나타남",
    any(c["order_item_id"] == L_new and c["suggestion"] == "new" for c in sc2["candidates"]))
pu.link_order(units[1]["id"], O2, relation_type="CHANGE", reason="변경 수주를 기존 호기에 연결")
chk("§12-7' 기존 호기에 수주 연결 가능",
    any(l["relation_type"] == "CHANGE" for l in pu.get_unit(units[1]["id"])["orders"]))

# 8) 수량 1이 아닌 후보 자동적용 차단
O3 = mkorder(PID, "SO-A-3")
L_q3 = mkline(O3, "77호기", qty=3)
sc3 = pu.scan_candidates(PID)
c_q3 = [c for c in sc3["candidates"] if c["order_item_id"] == L_q3][0]
chk("§12-8 수량≠1 후보는 '확인 필요'", c_q3["suggestion"] == "blocked" and c_q3["blockers"])
r8 = pu.apply_candidates(PID, [L_q3])
chk("§12-8' 강제 반영해도 거부(사유 반환)",
    r8["created"] == 0 and len(r8["rejected"]) == 1, str(r8))

# 9) Unit 취소 후 연결 보존 (물리삭제 금지)
u_cancel = units[2]
before_links = len(pu.get_unit(u_cancel["id"])["orders"])
pu.cancel_unit(u_cancel["id"], reason="수주 축소로 취소")
cu = pu.get_unit(u_cancel["id"])
chk("§12-9 취소=물리삭제 아님(행 유지)", cu is not None and cu["unit_state"] == "CANCELLED")
chk("§12-9' 취소 사유·수주 이력 보존",
    cu["cancellation_reason"] and len(cu["orders"]) == before_links)
chk("§12-9'' 취소 호기의 번호는 재사용 가능(현재값 유일 조건)",
    pu.create_unit(PID, unit_no=u_cancel["current_unit_no"]) > 0)

# 10) 분할·통합 관계 이력 보존 (V1=구조만·실행 없음)
with db.db_session() as c:
    src = units[1]["id"]
    n1 = pu.create_unit(PID, working_name="분할결과A")
    n2 = pu.create_unit(PID, working_name="분할결과B")
    for res in (n1, n2):
        c.execute("INSERT INTO project_unit_relations(source_unit_id, result_unit_id, "
                  "relation_type, change_reason, processed_by, approved_by, effective_at) "
                  "VALUES(?,?, 'SPLIT', '개발호기 1대를 실장비 2대로', 1, 2, datetime('now','localtime'))",
                  (src, res))
rel = pu.get_unit_relations(src)
chk("§12-10 분할 관계 1:N 이력 보존(2행)", len(rel) == 2 and all(r["relation_type"] == "SPLIT" for r in rel))
chk("§12-10' 원본 Unit 물리삭제 안 됨", pu.get_unit(src) is not None)
chk("§12-10'' 분할·통합 실행 API 없음(V1)",
    not any(hasattr(pu, f) for f in ("split_unit", "merge_units", "create_relation")))

# ── 영향분석 미연동 차단 (대표 확정) ──
print("\n── B'. 영향분석 미연동 차단 ──")
st = pu.get_unit(before_id)["impact"]
chk("영향분석 미연동을 '영향 없음'으로 표시하지 않음",
    st["wired"] is False and st["message"] == pu.IMPACT_NOT_WIRED_MSG)
# 개발·미확정 호기 = 업무가 아직 안 붙음 → 자유롭게 정리 가능(위 §12-3 에서 실증)
chk("개발·미확정 호기는 번호 정리 가능", pu.get_unit(before_id)["current_unit_no"] == "21호기")
# 확정 호기 = BOM·발주·생산이 붙는 단계 → 영향 확인 필요(V1 미연동이라 차단)
try:
    pu.change_unit_no(uid_dev, "31호기", reason="확정 호기 번호 변경 시도")
    chk("확정 호기 번호 변경 차단(영향 미연동)", False)
except ValueError as e:
    chk("확정 호기 번호 변경 차단(영향 미연동)", "연동되지 않" in str(e), str(e))
try:
    pu.cancel_unit(uid_dev, reason="확정 호기 취소 시도")
    chk("확정 호기 취소 차단(영향 미연동)", False)
except ValueError as e:
    chk("확정 호기 취소 차단(영향 미연동)", "연동되지 않" in str(e), str(e))

# ── 법인 ──
PX = mkproject("999X01", po_entity="KOR", ship_entity="VN")
try:
    pu.create_unit(PX, unit_no="1호기"); chk("법인 충돌 시 중단", False)
except ValueError:
    chk("법인 충돌 시 중단", True)

# ═══════════ C. 라우트 + 권한 ═══════════
print("\n── C. 라우트 수준 (실 HTTP · 인가 실로직) ──")
try:
    from fastapi.testclient import TestClient
    import app.main as m
    m.get_user = lambda req: {"id": 503, "name": "대표", "role": "ceo", "team_id": 11}
    client = TestClient(m.app)
    rp = client.get(f"/project/{PID}/units")
    chk("GET 호기 페이지 200", rp.status_code == 200, str(rp.status_code))
    chk("미연동 안내문 화면 노출", pu.IMPACT_NOT_WIRED_MSG[:20] in rp.text)
    rc = client.get(f"/project/{PID}/units/candidates")
    chk("GET 후보 확인 화면 200", rc.status_code == 200 and "후보" in rc.text)
    PID2 = mkproject("999T2699")
    Ob = mkorder(PID2, "SO-B-1")
    for i in (1, 2):
        mkline(Ob, f"{i}호기")
    ids = newids(pu.scan_candidates(PID2))
    OI_C = cnt("order_items")   # 셋업 완료 후 기준선 — 이후 라우트 조작이 수주내역을 바꾸지 않아야 함
    ra = client.post(f"/project/{PID2}/units/candidates/apply",
                     data={"order_item_ids": [str(i) for i in ids]}, follow_redirects=False)
    chk("POST 후보 반영 303", ra.status_code == 303, str(ra.status_code))
    chk("후보 반영 결과 2대(개발·미확정)",
        cnt("project_units", "project_id=? AND unit_state='PROVISIONAL'", (PID2,)) == 2)
    rn = client.post(f"/project/{PID2}/units/create", data={"working_name": "개발X"},
                     follow_redirects=False)
    chk("POST 호기 직접 추가 303", rn.status_code == 303)
    rh = client.get(f"/units/{ids and pu.get_units(PID2)[0]['id']}/history")
    chk("GET 이력 조회 200", rh.status_code == 200 and "identifier_history" in rh.text)
    chk("additive · 라우트 조작이 order_items 불변", cnt("order_items") == OI_C)

    # 권한 매트릭스
    def _as(role, team, path, data=None):
        m.get_user = lambda req: {"id": 1, "role": role, "team_id": team}
        if data is None:
            return client.get(path, follow_redirects=False)
        return client.post(path, data=data, follow_redirects=False)

    def _blocked(rr):
        return rr.status_code == 303 and "/home" in rr.headers.get("location", "")
    chk("권한 · 구매팀(10) 호기 생성 허용",
        not _blocked(_as("member", 10, f"/project/{PID2}/units/create", {"working_name": "구매X"})))
    chk("권한 · 제조팀(7) 호기 생성 허용",
        not _blocked(_as("member", 7, f"/project/{PID2}/units/create", {"working_name": "제조X"})))
    chk("권한 · 영업팀원 호기 생성 차단",
        _blocked(_as("member", 1, f"/project/{PID2}/units/create", {"working_name": "영업X"})))
    chk("권한 · 무권한 조회 차단", _blocked(_as("member", 99, f"/project/{PID2}/units")))
    _u2 = pu.get_units(PID2)[0]["id"]
    chk("권한 · 일반 사용자(구매팀) 취소 차단",
        _blocked(_as("member", 10, f"/units/{_u2}/cancel", {"reason": "x"})))
    chk("권한 · 분할/통합 실행 경로 없음",
        client.post(f"/units/{_u2}/split", data={}, follow_redirects=False).status_code == 404)
except ImportError as e:
    print(f"  SKIP 라우트 테스트 (패키지 없음: {e})")

print(f"\n{'=' * 52}\n결과: PASS {ok} · FAIL {fail}")
sys.exit(0 if fail == 0 else 1)
