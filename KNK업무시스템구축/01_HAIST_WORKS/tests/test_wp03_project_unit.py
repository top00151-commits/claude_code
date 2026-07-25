# -*- coding: utf-8 -*-
"""WP-03 프로젝트 호기(Project Unit) — 정식 검증 v4
   대표 업무교정(07-25) + 게이트 v3 판정(F-01~F-09) 반영본

실행:  01_HAIST_WORKS 루트에서
    python tests/test_wp03_project_unit.py

⭐ 영구 식별자 계약: 장비 Unit 의 시스템 영구 식별자는 project_units.id 이다.
   관리번호·현재 호기번호·연결된 수주번호는 표시·검색 정보이며 영구 식별자가 아니다.

A부: 후보 계약(F-01·F-02)         B부: 게이트 §5 무결성
C부: 게이트 §6 시나리오 A~E        D부: 라우트·화면 증빙(F-03·F-04)
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from app import database as db  # noqa: E402

db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="wp03_"), "test.db")
db.init_db()
from app.migrations.m_z1053_project_unit import migrate as _mig  # noqa: E402
print("마이그레이션:", _mig(db.DB_PATH))
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


def mkproject(code, entity="KOR"):
    with db.db_session() as c:
        c.execute("INSERT INTO projects (mgmt_code, name, status, po_entity, ship_entity) "
                  "VALUES (?,?,?,?,?)", (code, f"P-{code}", "진행중", entity, entity))
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


def dec(oid, action, unit_id=None, rel=None):
    d = {"order_item_id": oid, "action": action}
    if unit_id:
        d["unit_id"] = unit_id
    if rel:
        d["relation_type"] = rel
    return d


# ═══════════ A. 후보 계약 (F-01 · F-02) ═══════════
print("\n── A. 후보 계약 (F-01 미확정 승격 금지 · F-02 다중수주 정상) ──")
PA = mkproject("999T2601")
OA1 = mkorder(PA, "SO-A-1")
L1 = mkline(OA1, "1호기")
L2 = mkline(OA1, "2호기")
mkline(OA1, "예비품 세트", qty=3)
OI_BASE = cnt("order_items")

scan = pu.scan_candidates(PA)
chk("후보 2개 인식(부속 제외)", scan["summary"]["total"] == 2, str(scan["summary"]))
chk("스캔만으로는 생성 안 함", cnt("project_units") == 0)

r = pu.apply_candidate_decisions(PA, [dec(L1, "new"), dec(L2, "new")], reason="시범 반영")
chk("선택한 후보만 신규 생성(2대)", r["created"] == 2, str(r))
units = pu.get_units(PA)
# ⭐F-01: 후보 라벨이 현재 호기번호로 승격되면 안 됨
chk("F-01 현재 호기번호는 비어 있음(미확정 승격 금지)",
    all(u["current_unit_no"] is None for u in units), str([u["current_unit_no"] for u in units]))
chk("F-01' 후보 원본은 보존(working_name·seed)",
    all(u["working_name"] and u["seed_unit_label"] for u in units))
chk("반영 상태 = 개발·미확정", all(u["unit_state"] == "PROVISIONAL" for u in units))
chk("최초 수주(ORIGIN) 연결 생성", cnt("project_unit_order_links", "relation_type='ORIGIN'") == 2)
try:
    pu.apply_candidate_decisions(PA, [dec(L1, "new")], reason="")
    chk("F-03 반영 사유 필수", False)
except ValueError:
    chk("F-03 반영 사유 필수", True)
chk("additive · order_items 불변", cnt("order_items") == OI_BASE)

# ⭐F-02: 같은 호기번호가 다른 수주에 또 나오는 것은 정상 업무
U1 = units[0]["id"]
pu.change_unit_no(U1, "1호기", reason="개발 확정 후 번호 지정")
OA2 = mkorder(PA, "SO-A-2")
L3 = mkline(OA2, "1호기")
sc2 = pu.scan_candidates(PA)
c3 = [c for c in sc2["candidates"] if c["order_item_id"] == L3][0]
chk("F-02 같은 호기번호 다른 수주 = 차단 아님", c3["suggestion"] == "link" and not c3["blockers"],
    f"{c3['suggestion']} {c3['blockers']}")
chk("F-02' 연결할 기존 호기를 함께 제시",
    any(m["id"] == U1 for m in c3["match_units"]), str(c3["match_units"]))
r2 = pu.apply_candidate_decisions(PA, [dec(L3, "link", unit_id=U1, rel="ADDITIONAL")],
                                  reason="추가 발주")
chk("F-02'' 기존 호기에 추가수주 연결(신규 생성 0)",
    r2["linked"] == 1 and r2["created"] == 0, str(r2))
u1 = pu.get_unit(U1)
chk("F-02''' Unit 1개 · 수주 링크 2개",
    len(pu.get_units(PA)) == 2 and len(u1["orders"]) == 2)

# ═══════════ B. 게이트 §5 무결성 ═══════════
print("\n── B. §5 무결성 ──")
try:
    pu.link_order(U1, OA2, relation_type="ADDITIONAL"); chk("§5-2 동일 Unit·수주·유형 중복 차단", False)
except ValueError:
    chk("§5-2 동일 Unit·수주·유형 중복 차단", True)
try:
    pu.link_order(U1, OA2, relation_type="ORIGIN"); chk("§5-3 ORIGIN 은 Unit당 1개", False)
except ValueError:
    chk("§5-3 ORIGIN 은 Unit당 1개", True)
PB = mkproject("999T2602")
OB = mkorder(PB, "SO-B-1")
try:
    pu.link_order(U1, OB); chk("다른 프로젝트 수주 연결 차단", False)
except ValueError:
    chk("다른 프로젝트 수주 연결 차단", True)
U2 = pu.get_units(PA)[1]["id"]
pu.cancel_unit(U2, reason="수주 축소")
chk("취소=물리삭제 아님", pu.get_unit(U2)["unit_state"] == "CANCELLED")
chk("§5-4 취소해도 수주 연결 행 보존(비활성)",
    len(pu.get_unit(U2)["orders"]) >= 1 and all(not o["active"] for o in pu.get_unit(U2)["orders"]))
try:
    pu.link_order(U2, OA2); chk("§5-1 취소 Unit 에 수주 연결 차단", False)
except ValueError:
    chk("§5-1 취소 Unit 에 수주 연결 차단", True)

# ═══════════ C. 게이트 §6 시나리오 A~E ═══════════
print("\n── C. §6 시나리오 A~E ──")
# 시나리오 A: 관리번호 1 · 수주번호 2 · 같은 호기 → Unit 1개, 링크 2개
PS = mkproject("999S001")
S1, S2 = mkorder(PS, "SO-S-1"), mkorder(PS, "SO-S-2")
SL1, SL2 = mkline(S1, "1호기"), mkline(S2, "1호기")
UA = pu.create_unit(PS, working_name="개발1호기")
chk("A-2 개발호기 생성(번호 미정)", pu.get_unit(UA)["current_unit_no"] is None)
pu.apply_candidate_decisions(PS, [dec(SL1, "link", unit_id=UA, rel="ORIGIN")], reason="최초 발주")
scA = pu.scan_candidates(PS)
cA = [c for c in scA["candidates"] if c["order_item_id"] == SL2][0]
pu.apply_candidate_decisions(PS, [dec(SL2, "link", unit_id=UA, rel="ADDITIONAL")], reason="추가 발주")
uA = pu.get_unit(UA)
chk("시나리오 A · Unit 1개 · 수주 링크 2개(ORIGIN+ADDITIONAL)",
    len(pu.get_units(PS)) == 1 and len(uA["orders"]) == 2
    and {o["relation_type"] for o in uA["orders"]} == {"ORIGIN", "ADDITIONAL"})

# 시나리오 B: 개발호기 번호 지정 → 변경 → 시점별 조회
UB = pu.create_unit(PS, working_name="개발2호기")
pu.change_unit_no(UB, "2호기", reason="번호 지정", effective_from="2026-03-01")
pu.change_unit_no(UB, "3호기", reason="구성 변경", effective_from="2026-06-01")
ub = pu.get_unit(UB)
chk("시나리오 B · Unit ID 유지 + 현재 3호기",
    ub["id"] == UB and ub["current_unit_no"] == "3호기")
chk("B · 후보 원본(개발호기명) 보존", ub["working_name"] == "개발2호기")
chk("F-07 적용시점 기준 과거조회 2026-04-01 → 2호기",
    pu.unit_no_at(UB, "2026-04-01") == "2호기", str(pu.unit_no_at(UB, "2026-04-01")))
chk("F-07' 적용시점 기준 현재 2026-07-01 → 3호기",
    pu.unit_no_at(UB, "2026-07-01") == "3호기", str(pu.unit_no_at(UB, "2026-07-01")))
chk("F-07'' 적용 전 시점(2026-01-01) → 없음", pu.unit_no_at(UB, "2026-01-01") is None)
# 기록일과 적용일이 다른 변경(게이트 F-07 요구 시험)
pu.change_unit_no(UB, "4호기", reason="소급 적용", effective_from="2026-05-01")
chk("F-07''' 기록일≠적용일: 2026-05-15 조회 → 4호기",
    pu.unit_no_at(UB, "2026-05-15") == "4호기", str(pu.unit_no_at(UB, "2026-05-15")))

# 시나리오 C: 취소된 호기번호 재사용 차단 (F-06)
UC = pu.create_unit(PS, working_name="개발9호기")
pu.change_unit_no(UC, "9호기", reason="번호 지정")
pu.cancel_unit(UC, reason="취소 시험")
try:
    pu.create_unit(PS, unit_no="9호기"); chk("시나리오 C · 취소 호기번호 재사용 차단(F-06)", False)
except ValueError:
    chk("시나리오 C · 취소 호기번호 재사용 차단(F-06)", True)
try:
    pu.change_unit_no(UA, "9호기", reason="재사용 시도"); chk("C' 번호 변경으로도 재사용 불가", False)
except ValueError:
    chk("C' 번호 변경으로도 재사용 불가", True)

# 시나리오 D: 법인 미확정 → 중단 (F-08)
PD = mkproject("999D001", entity=None)
with db.db_session() as c:
    c.execute("UPDATE projects SET po_entity=NULL, ship_entity=NULL WHERE id=?", (PD,))
try:
    pu.create_unit(PD, working_name="개발X"); chk("시나리오 D · 법인 미확정이면 중단(KOR 자동부여 없음)", False)
except ValueError as e:
    chk("시나리오 D · 법인 미확정이면 중단(KOR 자동부여 없음)", "법인" in str(e), str(e))
with db.db_session() as c:
    c.execute("UPDATE projects SET po_entity='KOR', ship_entity='KOR' WHERE id=?", (PD,))
chk("D' 법인 확정 후 정상 생성", pu.create_unit(PD, working_name="개발X") > 0)
with db.db_session() as c:
    c.execute("UPDATE projects SET po_entity='KOR', ship_entity='VN' WHERE id=?", (PD,))
try:
    pu.create_unit(PD, working_name="개발Y"); chk("D'' 법인 충돌 → 중단", False)
except ValueError:
    chk("D'' 법인 충돌 → 중단", True)

# 분할·통합 구조(V1) — 실행 API 없음
with db.db_session() as c:
    n1 = pu.create_unit(PS, working_name="분할A")
    n2 = pu.create_unit(PS, working_name="분할B")
    for res in (n1, n2):
        c.execute("INSERT INTO project_unit_relations(source_unit_id, result_unit_id, relation_type,"
                  " change_reason, processed_by, approved_by, effective_at) "
                  "VALUES(?,?, 'SPLIT','개발호기 분할',1,2, datetime('now','localtime'))", (UA, res))
chk("분할 관계 1:N 이력 보존", len(pu.get_unit_relations(UA)) == 2)
chk("분할·통합 실행 함수 없음(V1)",
    not any(hasattr(pu, f) for f in ("split_unit", "merge_units", "create_relation")))

# 영향분석 미연동
st = pu.get_unit(UA)["impact"]
chk("영향분석 미연동을 '영향 없음'으로 표시 안 함",
    st["wired"] is False and st["message"] == pu.IMPACT_NOT_WIRED_MSG)
pu.change_unit_no(UA, "11호기", reason="개발 단계 번호 지정")
pu.confirm_unit(UA)
try:
    pu.change_unit_no(UA, "12호기", reason="확정 후 변경 시도")
    chk("확정 호기 번호변경 차단(미연동)", False)
except ValueError as e:
    chk("확정 호기 번호변경 차단(미연동)", "연동되지 않" in str(e))

# ═══════════ D. 라우트·화면 증빙 (F-03 · F-04) ═══════════
print("\n── D. 라우트·화면 (F-03 기본 미선택·요약 / F-04 화면에서 수주연결) ──")
try:
    from fastapi.testclient import TestClient
    import app.main as m
    m.get_user = lambda req: {"id": 503, "name": "대표", "role": "ceo", "team_id": 11}
    client = TestClient(m.app)
    rp = client.get(f"/project/{PA}/units")
    chk("GET 호기 화면 200", rp.status_code == 200, str(rp.status_code))
    chk("화면에 영구식별자 계약 문구", "영구 식별자는 project_units.id" in rp.text)
    chk("F-04 화면에 수주 연결 입력 존재", "/order-link" in rp.text and "추가 수주" in rp.text)
    rc = client.get(f"/project/{PA}/units/candidates")
    chk("GET 후보 화면 200", rc.status_code == 200)
    chk("F-03 후보 체크박스 기본 미선택(checked 없음)",
        'name="pick"' in rc.text and 'name="pick" value=' in rc.text
        and "checked" not in rc.text.split('name="pick"')[1][:80])
    chk("F-03' 반영 사유 필수 표시", 'name="reason"' in rc.text and "required" in rc.text)
    chk("F-03'' 제출 전 요약 영역", "sumBox" in rc.text and "새 개발호기" in rc.text)
    chk("F-02 화면에 '기존 호기에 이 수주 연결' 선택지",
        "기존 호기에 이 수주 연결" in rc.text)

    # 라우트로 실제 반영 (기본 미선택이므로 pick 을 명시)
    PR = mkproject("999R001")
    OR1 = mkorder(PR, "SO-R-1")
    RL = mkline(OR1, "1호기")
    ra = client.post(f"/project/{PR}/units/candidates/apply",
                     data={"pick": [str(RL)], f"action_{RL}": "new", "reason": "화면 반영 시험"},
                     follow_redirects=False)
    chk("POST 후보 반영 303", ra.status_code == 303, str(ra.status_code))
    ru = pu.get_units(PR)
    chk("반영 결과: 개발·미확정 1대 · 호기번호 비어 있음",
        len(ru) == 1 and ru[0]["unit_state"] == "PROVISIONAL" and ru[0]["current_unit_no"] is None)
    OR2 = mkorder(PR, "SO-R-2")
    rl = client.post(f"/units/{ru[0]['id']}/order-link",
                     data={"order_id": str(OR2), "relation_type": "ADDITIONAL", "reason": "추가"},
                     follow_redirects=False)
    chk("F-04 화면 경로로 수주 연결 성공(303)", rl.status_code == 303)
    chk("F-04' 연결 결과 링크 2개", len(pu.get_unit(ru[0]["id"])["orders"]) == 2)
    rh = client.get(f"/units/{ru[0]['id']}/history?at=2026-07-01")
    chk("이력 조회 200 + 적용시점 조회 지원", rh.status_code == 200 and "unit_no_at" in rh.text)

    # 권한 매트릭스 (F-09)
    def _as(role, team, path, data=None):
        m.get_user = lambda req: {"id": 1, "role": role, "team_id": team}
        return client.get(path, follow_redirects=False) if data is None else \
            client.post(path, data=data, follow_redirects=False)

    def _blocked(rr):
        return rr.status_code == 303 and "/home" in rr.headers.get("location", "")
    uid_r = ru[0]["id"]
    chk("F-09 조회 · 설계팀 허용", not _blocked(_as("member", 4, f"/project/{PR}/units")))
    chk("F-09 조회 · 무권한 차단", _blocked(_as("member", 99, f"/project/{PR}/units")))
    chk("F-09 개발호기 생성 · PM(영업1) 허용",
        not _blocked(_as("member", 1, f"/project/{PR}/units/create", {"working_name": "PM개발"})))
    chk("F-09 개발호기 생성 · 구매팀 차단",
        _blocked(_as("member", 10, f"/project/{PR}/units/create", {"working_name": "구매개발"})))
    chk("F-09 수주연결 · 영업 허용",
        not _blocked(_as("member", 1, f"/units/{uid_r}/order-link",
                         {"order_id": str(OR2), "relation_type": "CHANGE"})))
    chk("F-09 수주연결 · 설계 차단",
        _blocked(_as("member", 4, f"/units/{uid_r}/order-link", {"order_id": str(OR2)})))
    chk("F-09 확정 · 팀원 차단", _blocked(_as("member", 1, f"/units/{uid_r}/confirm", {})))
    chk("F-09 확정 · 팀장 허용", not _blocked(_as("leader", 1, f"/units/{uid_r}/confirm", {})))
    chk("F-09 취소 · 팀원 차단", _blocked(_as("member", 1, f"/units/{uid_r}/cancel", {"reason": "x"})))
    chk("분할·통합 실행 경로 없음(404)",
        client.post(f"/units/{uid_r}/split", data={}, follow_redirects=False).status_code == 404)
except ImportError as e:
    print(f"  SKIP 라우트 테스트 (패키지 없음: {e})")

print(f"\n{'=' * 52}\n결과: PASS {ok} · FAIL {fail}")
sys.exit(0 if fail == 0 else 1)
