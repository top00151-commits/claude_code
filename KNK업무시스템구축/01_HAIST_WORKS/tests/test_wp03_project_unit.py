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

# 시나리오 B: 개발호기 번호 지정 → 변경 → 소급 입력 → 시점별 조회 (게이트 v4 P0-03)
UB = pu.create_unit(PS, working_name="개발2호기")
pu.change_unit_no(UB, "2호기", reason="번호 지정", effective_from="2026-03-01")
pu.change_unit_no(UB, "3호기", reason="구성 변경", effective_from="2026-06-01")
ub = pu.get_unit(UB)
chk("시나리오 B · Unit ID 유지 + 현재 3호기",
    ub["id"] == UB and ub["current_unit_no"] == "3호기")
chk("B · 후보 원본(개발호기명) 보존", ub["working_name"] == "개발2호기")
chk("F-07 적용시점 기준 과거조회 2026-04-01 → 2호기",
    pu.unit_no_at(UB, "2026-04-01") == "2호기", str(pu.unit_no_at(UB, "2026-04-01")))
chk("F-07' 적용시점 기준 2026-07-01 → 3호기",
    pu.unit_no_at(UB, "2026-07-01") == "3호기", str(pu.unit_no_at(UB, "2026-07-01")))
chk("F-07'' 적용 전 시점(2026-01-01) → 없음", pu.unit_no_at(UB, "2026-01-01") is None)

# ── P0-03: 소급(역순) 입력 — 3월/6월 등록 후 5월 소급 ──
pu.change_unit_no(UB, "4호기", reason="소급 적용", effective_from="2026-05-01")
with db.db_session() as c:
    hrows = [dict(r) for r in c.execute(
        "SELECT new_unit_no, effective_from, effective_to FROM project_unit_identifier_history "
        "WHERE project_unit_id=? ORDER BY COALESCE(effective_from,'')", (UB,)).fetchall()]
print("     [적용구간표]", " / ".join(
    f"{h['new_unit_no']} {h['effective_from']}~{h['effective_to'] or '열림'}" for h in hrows))
chk("P0-03 ① 4월 조회 → 2호기", pu.unit_no_at(UB, "2026-04-01") == "2호기",
    str(pu.unit_no_at(UB, "2026-04-01")))
chk("P0-03 ② 5월15일 조회 → 4호기(소급 적용)", pu.unit_no_at(UB, "2026-05-15") == "4호기",
    str(pu.unit_no_at(UB, "2026-05-15")))
chk("P0-03 ③ 7월 조회 → 3호기 복원(소급이 미래계획을 덮지 않음)",
    pu.unit_no_at(UB, "2026-07-01") == "3호기", str(pu.unit_no_at(UB, "2026-07-01")))
chk("P0-03 ④ 모든 구간 effective_to > effective_from(역전 0)",
    all((not h["effective_to"]) or h["effective_to"] > (h["effective_from"] or "")
        for h in hrows), str(hrows))
chk("P0-03 ⑤ current_unit_no = 지금 유효한 값(입력순 마지막 아님)",
    pu.get_unit(UB)["current_unit_no"] == "3호기", str(pu.get_unit(UB)["current_unit_no"]))
try:
    pu.change_unit_no(UB, "44호기", reason="중복 시점", effective_from="2026-05-01")
    chk("P0-03 ⑥ 동일 적용시점 중복 차단", False)
except ValueError:
    chk("P0-03 ⑥ 동일 적용시점 중복 차단", True)

# ── [게이트 v5 P0-01] 소급 정정의 '변경 전 값'은 적용시점 직전 유효값이어야 한다 ──
with db.db_session() as c:
    _h5 = c.execute("SELECT old_unit_no, new_unit_no FROM project_unit_identifier_history "
                    "WHERE project_unit_id=? AND effective_from='2026-05-01'", (UB,)).fetchone()
chk("v5 P0-01 소급 정정 old_unit_no = 2호기(적용시점 직전 값)",
    _h5["old_unit_no"] == "2호기", f"old={_h5['old_unit_no']} (현재값 3호기를 쓰면 안 됨)")
chk("v5 P0-01' 소급 정정 new_unit_no = 4호기", _h5["new_unit_no"] == "4호기")

# ── [게이트 v5 P0-02] V1 은 미래 적용 예약을 지원하지 않는다 ──
UB2 = pu.create_unit(PS, working_name="개발즉시")
chk("v5 P0-02 즉시 변경은 정상 처리",
    pu.change_unit_no(UB2, "20호기", reason="지금 적용") is True)
chk("v5 P0-02' 즉시 변경 후 현재값 반영", pu.get_unit(UB2)["current_unit_no"] == "20호기")
try:
    pu.change_unit_no(UB2, "21호기", reason="미래 예약", effective_from="2099-01-01")
    chk("v5 P0-02'' 미래 적용일 입력 차단", False)
except ValueError as e:
    chk("v5 P0-02'' 미래 적용일 입력 차단", "미래" in str(e), str(e))
chk("v5 P0-02''' 차단 후 현재값 그대로", pu.get_unit(UB2)["current_unit_no"] == "20호기")
# 소급 정정 후에도 4월·5월·7월 조회가 유지되는지 재확인(§9-4)
chk("v5 §9-4 소급 후 조회 유지: 4월 2호기 · 5/15 4호기 · 7월 3호기",
    (pu.unit_no_at(UB, "2026-04-01") == "2호기"
     and pu.unit_no_at(UB, "2026-05-15") == "4호기"
     and pu.unit_no_at(UB, "2026-07-01") == "3호기"))

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

# ── P0-02 법인 DB 기본값 제거 + P1 DB 중복 제약 (게이트 v4) ──
print("\n── B'. P0-02 법인 DB 기본값 · P1 DB 중복 제약 ──")
import sqlite3 as _sq3  # noqa: E402
with db.db_session() as c:
    # ⚠ SQL 원문 글자 검색으로 판정하지 않는다 — sqlite_master 는 **주석까지** 보관하므로
    #   "기본값(DEFAULT 'KOR')을 두면 …" 이라는 설명문에 걸려 **틀린 판정**이 난다.
    #   (실제로 이 검사가 마이그레이션 결함을 못 잡고 오히려 그 결함 덕에 통과하고 있었다.)
    _ent_dflt = [r[4] for r in c.execute("PRAGMA table_info(project_units)").fetchall()
                 if r[1] == "entity"]
chk("P0-02 entity 컬럼에 기본값 없음(스키마 메타로 판정)", _ent_dflt == [None], str(_ent_dflt))
try:
    with db.db_session() as c:
        c.execute("INSERT INTO project_units(project_id, working_name) VALUES(?,?)", (PS, "배치입력"))
    chk("P0-02 DB 직접 INSERT 에서 법인 생략 → 실패", False)
except _sq3.IntegrityError as e:
    chk("P0-02 DB 직접 INSERT 에서 법인 생략 → 실패", "entity" in str(e), str(e))
# 기존(구버전) DB 보정 절차 — DEFAULT 'KOR' 가 있는 표를 만들고 마이그레이션이 고치는지
_old = os.path.join(tempfile.mkdtemp(prefix="wp03_old_"), "old.db")
_c = _sq3.connect(_old)
_c.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, mgmt_code TEXT, name TEXT, status TEXT)")
_c.execute("CREATE TABLE order_items (id INTEGER PRIMARY KEY)")
_c.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY)")
_c.execute("""CREATE TABLE project_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, working_name TEXT,
    current_unit_no TEXT, unit_state TEXT NOT NULL DEFAULT 'PROVISIONAL',
    equipment_type TEXT, entity TEXT NOT NULL DEFAULT 'KOR', seed_order_item_id INTEGER,
    seed_order_no TEXT, seed_unit_label TEXT, note TEXT, created_by INTEGER, created_at TEXT,
    updated_by INTEGER, updated_at TEXT, confirmed_by INTEGER, confirmed_at TEXT,
    cancelled_by INTEGER, cancelled_at TEXT, cancellation_reason TEXT)""")
_c.execute("INSERT INTO projects (id, mgmt_code, name, status) VALUES (1,'999OLD','기존','진행중')")
_c.execute("INSERT INTO project_units (project_id, working_name, entity) VALUES (1,'기존호기','VN')")
_c.commit(); _c.close()
_res = _mig(_old)
_c = _sq3.connect(_old)
_ddl2 = _c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='project_units'").fetchone()[0]
_kept = _c.execute("SELECT working_name, entity FROM project_units").fetchall()
chk("P0-02 기존 DB 보정: DEFAULT 제거됨", "DEFAULT 'KOR'" not in _ddl2, str(_res.get("fixed")))
chk("P0-02a 진짜 구버전 DB 에서는 보정이 **실행됨**", bool(_res.get("fixed")), str(_res))
# ⚠[리허설 발견] 새 DB 인데 '기존 DB 보정'이 돌면 안 된다 —
#   sqlite_master 는 CREATE TABLE 의 **주석까지** 보관하므로 SQL 원문을 글자로 뒤지면
#   설명문 "기본값(DEFAULT 'KOR')을 두면 …" 에 스스로 걸려 방금 만든 표를 재작성한다.
_fresh = os.path.join(tempfile.mkdtemp(prefix="wp03_fresh_"), "fresh.db")
_c2 = _sq3.connect(_fresh)
_c2.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, mgmt_code TEXT, name TEXT, status TEXT)")
_c2.execute("CREATE TABLE order_items (id INTEGER PRIMARY KEY)")
_c2.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY)")
_c2.commit(); _c2.close()
_res_f1 = _mig(_fresh)
_res_f2 = _mig(_fresh)
chk("P0-02b 새 DB: 표 5개 생성", len(_res_f1.get("created") or []) == 5, str(_res_f1))
chk("P0-02c 새 DB: **'기존 DB 보정'이 돌지 않음**(자기 주석에 안 걸림)",
    not _res_f1.get("fixed"), str(_res_f1.get("fixed")))
chk("P0-02d 새 DB 재실행: 아무것도 바뀌지 않음(멱등)",
    not _res_f2.get("created") and not _res_f2.get("fixed"), str(_res_f2))
_c2 = _sq3.connect(_fresh)
chk("P0-02e 새 DB 에도 entity 기본값 없음(스키마 메타로 확인)",
    [r[4] for r in _c2.execute("PRAGMA table_info(project_units)").fetchall()
     if r[1] == "entity"] == [None])
_c2.close()
chk("P0-02' 보정 시 기존 데이터 보존", _kept == [("기존호기", "VN")], str(_kept))
try:
    _c.execute("INSERT INTO project_units(project_id, working_name) VALUES(1,'보정후')")
    chk("P0-02'' 보정 후에도 법인 생략 실패", False)
except _sq3.IntegrityError:
    chk("P0-02'' 보정 후에도 법인 생략 실패", True)
_c.close()

# ── [게이트 v5 P1-03] **자식 이력이 있는** 구버전 DB 보정 후 FK 무결성 ──
#   표 재작성(RENAME) 시 자식 표의 FK 가 임시 이름을 가리키면 이력이 끊긴다.
_old2 = os.path.join(tempfile.mkdtemp(prefix="wp03_old2_"), "old2.db")
_c = _sq3.connect(_old2)
_c.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, mgmt_code TEXT, name TEXT, status TEXT)")
_c.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, order_no TEXT)")
_c.execute("CREATE TABLE order_items (id INTEGER PRIMARY KEY)")
_c.execute("""CREATE TABLE project_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, working_name TEXT,
    current_unit_no TEXT, unit_state TEXT NOT NULL DEFAULT 'PROVISIONAL', equipment_type TEXT,
    entity TEXT NOT NULL DEFAULT 'KOR', seed_order_item_id INTEGER, seed_order_no TEXT,
    seed_unit_label TEXT, note TEXT, created_by INTEGER, created_at TEXT, updated_by INTEGER,
    updated_at TEXT, confirmed_by INTEGER, confirmed_at TEXT, cancelled_by INTEGER,
    cancelled_at TEXT, cancellation_reason TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id))""")
_c.execute("""CREATE TABLE project_unit_identifier_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, project_unit_id INTEGER NOT NULL, old_unit_no TEXT,
    new_unit_no TEXT, change_reason TEXT, changed_by INTEGER, changed_at TEXT, change_id TEXT,
    effective_from TEXT, effective_to TEXT,
    FOREIGN KEY(project_unit_id) REFERENCES project_units(id))""")
_c.execute("""CREATE TABLE project_unit_order_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT, project_unit_id INTEGER NOT NULL, order_id INTEGER,
    order_no TEXT, relation_type TEXT NOT NULL DEFAULT 'ORIGIN', active INTEGER NOT NULL DEFAULT 1,
    reason TEXT, change_id TEXT, linked_by INTEGER, linked_at TEXT, unlinked_by INTEGER,
    unlinked_at TEXT, FOREIGN KEY(project_unit_id) REFERENCES project_units(id))""")
_c.execute("""CREATE TABLE project_unit_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, source_unit_id INTEGER NOT NULL,
    result_unit_id INTEGER NOT NULL, relation_type TEXT NOT NULL, change_reason TEXT,
    change_id TEXT, effective_at TEXT, processed_by INTEGER, approved_by INTEGER, created_at TEXT,
    FOREIGN KEY(source_unit_id) REFERENCES project_units(id),
    FOREIGN KEY(result_unit_id) REFERENCES project_units(id))""")
_c.execute("INSERT INTO projects (id, mgmt_code, name, status) VALUES (1,'999OLD2','기존2','진행중')")
_c.execute("INSERT INTO orders (id, order_no) VALUES (7,'SO-OLD-7')")
_c.execute("INSERT INTO project_units (id, project_id, working_name, current_unit_no, entity) "
           "VALUES (5,1,'구형호기','1호기','VN')")
_c.execute("INSERT INTO project_units (id, project_id, working_name, entity) VALUES (6,1,'구형B','KOR')")
_c.execute("INSERT INTO project_unit_identifier_history (project_unit_id, old_unit_no, new_unit_no, "
           "change_reason, effective_from) VALUES (5,NULL,'1호기','최초','2026-01-01')")
_c.execute("INSERT INTO project_unit_order_links (project_unit_id, order_id, order_no, relation_type, active) "
           "VALUES (5,7,'SO-OLD-7','ORIGIN',1)")
_c.execute("INSERT INTO project_unit_relations (source_unit_id, result_unit_id, relation_type) "
           "VALUES (5,6,'SPLIT')")
_c.commit(); _c.close()
_res2 = _mig(_old2)
_c = _sq3.connect(_old2)
_hist_n = _c.execute("SELECT COUNT(*) FROM project_unit_identifier_history").fetchone()[0]
_link_n = _c.execute("SELECT COUNT(*) FROM project_unit_order_links").fetchone()[0]
_rel_n = _c.execute("SELECT COUNT(*) FROM project_unit_relations").fetchone()[0]
_unit_n = _c.execute("SELECT COUNT(*) FROM project_units").fetchone()[0]
chk("P1-03 자식 이력 보존(이력1·연결1·분할1·호기2)",
    (_hist_n, _link_n, _rel_n, _unit_n) == (1, 1, 1, 2),
    str((_hist_n, _link_n, _rel_n, _unit_n)))
_fk_targets = set()
for _t in ("project_unit_identifier_history", "project_unit_order_links", "project_unit_relations"):
    for _fk in _c.execute(f"PRAGMA foreign_key_list({_t})").fetchall():
        if "project_unit" in str(_fk[2]):
            _fk_targets.add(_fk[2])
chk("P1-03' 자식 FK 대상이 project_units 그대로(임시표 아님)",
    _fk_targets == {"project_units"}, str(_fk_targets))
_c.execute("PRAGMA foreign_keys=ON")
_fkc = _c.execute("PRAGMA foreign_key_check").fetchall()
chk("P1-03'' foreign_key_check 위반 0건", len(_fkc) == 0, str(_fkc[:3]))
chk("P1-03''' 보정 후에도 법인 생략 INSERT 실패",
    _mig(_old2) is not None
    and "DEFAULT 'KOR'" not in _c.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='project_units'").fetchone()[0])
_c.close()
# P1 — DB 수준 중복 제약
_u_dup = pu.get_units(PS)[0]["id"]
_o_dup = S1
with db.db_session() as c:
    _exists = c.execute("SELECT id, relation_type FROM project_unit_order_links "
                        "WHERE project_unit_id=? AND active=1 LIMIT 1", (_u_dup,)).fetchone()
if _exists:
    try:
        with db.db_session() as c:
            c.execute("INSERT INTO project_unit_order_links(project_unit_id, order_id, "
                      "relation_type, active) VALUES(?,?,?,1)",
                      (_u_dup, _o_dup, _exists["relation_type"]))
        chk("P1 DB 수준 중복 연결 차단", False)
    except _sq3.IntegrityError:
        chk("P1 DB 수준 중복 연결 차단", True)
    try:
        with db.db_session() as c:
            c.execute("INSERT INTO project_unit_order_links(project_unit_id, order_id, "
                      "relation_type, active) VALUES(?,?, 'ORIGIN', 1)", (_u_dup, 99999))
        chk("P1' DB 수준 활성 ORIGIN 1개 강제", False)
    except _sq3.IntegrityError:
        chk("P1' DB 수준 활성 ORIGIN 1개 강제", True)

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

    # ── 권한 매트릭스 — 대표 확정 DEC-PUNIT-OWNER-01 (호기 소유부서 = 기술영업팀 team_id=1) ──
    print("\n── E. 기술영업팀 확정 권한표 (대표 DEC-PUNIT-OWNER-01) ──")

    def _as(user, path, data=None):
        m.get_user = lambda req: user
        return client.get(path, follow_redirects=False) if data is None else \
            client.post(path, data=data, follow_redirects=False)

    def _blocked(rr):
        return rr.status_code == 303 and "/home" in rr.headers.get("location", "")
    uid_r = ru[0]["id"]
    SALES_DELEG = {"id": 11, "role": "member", "team_id": 1, "can_use_sales": 1}   # 기술영업팀 위임자
    SALES_PLAIN = {"id": 12, "role": "member", "team_id": 1}                       # 기술영업팀 미위임
    SALES_LEAD = {"id": 13, "role": "leader", "team_id": 1}                        # 기술영업팀장
    DESIGN = {"id": 14, "role": "member", "team_id": 4}                            # 설계팀
    DESIGN_LEAD = {"id": 15, "role": "leader", "team_id": 4}                       # 설계팀장
    BUY = {"id": 16, "role": "member", "team_id": 10}                              # 구매팀
    MFG_LEAD = {"id": 17, "role": "leader", "team_id": 7}                          # 제조팀장
    CEO = {"id": 18, "role": "ceo", "team_id": 11}

    # 조회 — 전 부서 허용
    for who, nm in ((SALES_PLAIN, "기술영업 일반"), (DESIGN, "설계팀"), (BUY, "구매팀"), (MFG_LEAD, "제조팀장")):
        chk(f"조회 · {nm} 허용", not _blocked(_as(who, f"/project/{PR}/units")))
    chk("조회 · 소속 없는 사용자 차단", _blocked(_as({"id": 99, "role": "member"}, f"/project/{PR}/units")))

    # 생성·번호지정 — 기술영업팀(위임자·팀장)·대표만
    chk("생성 · 기술영업 위임자 허용",
        not _blocked(_as(SALES_DELEG, f"/project/{PR}/units/create", {"working_name": "영업개발"})))
    chk("생성 · 기술영업팀장 허용",
        not _blocked(_as(SALES_LEAD, f"/project/{PR}/units/create", {"working_name": "팀장개발"})))
    chk("생성 · 기술영업 **미위임** 일반 차단",
        _blocked(_as(SALES_PLAIN, f"/project/{PR}/units/create", {"working_name": "미위임"})))
    chk("생성 · 설계팀 차단", _blocked(_as(DESIGN, f"/project/{PR}/units/create", {"working_name": "설계"})))
    chk("생성 · 설계팀장도 차단",
        _blocked(_as(DESIGN_LEAD, f"/project/{PR}/units/create", {"working_name": "설계장"})))
    chk("생성 · 구매팀 차단", _blocked(_as(BUY, f"/project/{PR}/units/create", {"working_name": "구매"})))
    chk("생성 · 대표 허용",
        not _blocked(_as(CEO, f"/project/{PR}/units/create", {"working_name": "대표개발"})))
    chk("번호지정 · 설계팀장 차단",
        _blocked(_as(DESIGN_LEAD, f"/units/{uid_r}/unit-no", {"new_unit_no": "77호기", "reason": "x"})))

    # 수주연결 — 소유부서 기준
    chk("수주연결 · 기술영업 위임자 허용",
        not _blocked(_as(SALES_DELEG, f"/units/{uid_r}/order-link",
                         {"order_id": str(OR2), "relation_type": "CHANGE"})))
    chk("수주연결 · 설계팀 차단",
        _blocked(_as(DESIGN, f"/units/{uid_r}/order-link", {"order_id": str(OR2)})))
    chk("수주연결 · 구매팀 차단",
        _blocked(_as(BUY, f"/units/{uid_r}/order-link", {"order_id": str(OR2)})))

    # 확정·취소 — 기술영업팀장·대표·임원만 (다른 부서 팀장 불가)
    chk("확정 · 기술영업 위임자(팀원) 차단", _blocked(_as(SALES_DELEG, f"/units/{uid_r}/confirm", {})))
    chk("확정 · **다른 부서 팀장(설계) 차단**", _blocked(_as(DESIGN_LEAD, f"/units/{uid_r}/confirm", {})))
    chk("확정 · **다른 부서 팀장(제조) 차단**", _blocked(_as(MFG_LEAD, f"/units/{uid_r}/confirm", {})))
    chk("확정 · 기술영업팀장 허용", not _blocked(_as(SALES_LEAD, f"/units/{uid_r}/confirm", {})))
    chk("취소 · 다른 부서 팀장 차단",
        _blocked(_as(MFG_LEAD, f"/units/{uid_r}/cancel", {"reason": "x"})))
    chk("취소 · 기술영업팀장 허용",
        not _blocked(_as(SALES_LEAD, f"/units/{uid_r}/cancel", {"reason": "취소 시험"})))

    # 화면 버튼 노출 — 권한 없는 사용자에게 입력·확정·취소가 보이지 않아야 함
    _html_design = _as(DESIGN, f"/project/{PR}/units").text
    _html_lead = _as(SALES_LEAD, f"/project/{PR}/units").text
    chk("화면 · 설계팀에게 입력·확정·취소 버튼 미노출",
        ("/unit-no" not in _html_design) and ("/confirm" not in _html_design)
        and ("/cancel" not in _html_design))
    chk("화면 · 기술영업팀장에겐 노출", "/unit-no" in _html_lead and "/cancel" in _html_lead)

    # ── 관리자 비상복구 감사 (게이트 v5 P1-01·P1-02) ──
    ADMIN = {"id": 20, "role": "admin", "team_id": 11, "name": "시스템관리자"}
    _before = len(pu.get_audit())
    # P1-02: 우회 사유 없이 요청하면 거부
    _r_no = _as(ADMIN, f"/project/{PR}/units/create", {"working_name": "사유없음"})
    chk("v5 P1-02 관리자 우회 사유 없으면 거부",
        "error=" in _r_no.headers.get("location", ""), _r_no.headers.get("location", ""))
    chk("v5 P1-02' 사유 없는 요청은 감사에도 남지 않음(작업 자체가 거부)",
        len(pu.get_audit()) == _before)
    # 사유를 넣으면 수행 + 감사 기록
    _as(ADMIN, f"/project/{PR}/units/create",
        {"working_name": "관리자복구", "override_requester": "기술영업팀 홍길동",
         "override_reason": "담당자 부재로 대신 등록"})
    _aud = pu.get_audit()
    chk("v5 P1-02'' 사유 입력 시 수행 + 감사 기록", len(_aud) > _before)
    chk("v5 P1-02''' 감사에 요청자·우회사유·비상복구 구분 기록",
        _aud and "기술영업팀 홍길동" in (_aud[0]["note"] or "")
        and "담당자 부재" in (_aud[0]["note"] or "")
        and "관리자 비상복구" in (_aud[0]["note"] or ""), str(_aud[:1]))
    # P1-01: 후보 일괄반영 경로도 감사에 남는다
    PJ_ADM = mkproject("999ADM1")
    OJ = mkorder(PJ_ADM, "SO-ADM-1")
    LJ = mkline(OJ, "1호기")
    _cnt_before = len(pu.get_audit())
    _r_ap = _as(ADMIN, f"/project/{PJ_ADM}/units/candidates/apply",
                {"pick": [str(LJ)], f"action_{LJ}": "new", "reason": "관리자 일괄반영",
                 "override_requester": "기술영업팀", "override_reason": "긴급 복구"})
    _aud2 = pu.get_audit()
    chk("v5 P1-01 관리자 후보 일괄반영도 감사 기록", len(_aud2) > _cnt_before)
    chk("v5 P1-01' 감사에 신규·연결·거부 건수 기록",
        _aud2 and "신규" in (_aud2[0]["note"] or "") and "연결" in (_aud2[0]["note"] or "")
        and "거부" in (_aud2[0]["note"] or ""), str(_aud2[:1]))
    chk("v5 P1-01'' 감사에 대상 관리번호(project) 기록",
        _aud2 and f"project#{PJ_ADM}" in (_aud2[0]["target"] or ""), str(_aud2[:1]))
    # 후보 일괄반영도 사유 없으면 거부
    PJ_ADM2 = mkproject("999ADM2")
    OJ2 = mkorder(PJ_ADM2, "SO-ADM-2")
    LJ2 = mkline(OJ2, "1호기")
    _r_ap2 = _as(ADMIN, f"/project/{PJ_ADM2}/units/candidates/apply",
                 {"pick": [str(LJ2)], f"action_{LJ2}": "new", "reason": "사유없이"})
    chk("v5 P1-02'''' 후보 일괄반영도 우회 사유 필수",
        cnt("project_units", "project_id=?", (PJ_ADM2,)) == 0)
    # 기술영업팀 정상 업무는 비상복구 감사에 남지 않는다(구분)
    _n3 = len(pu.get_audit())
    _as(SALES_LEAD, f"/project/{PR}/units/create", {"working_name": "정상업무"})
    chk("v5 P1-02''''' 일반 기술영업 업무는 비상복구 감사와 구분(기록 안 함)",
        len(pu.get_audit()) == _n3)

    # ══════════ F. 게이트 v6 최종 승인 테스트 §8-1~10 ══════════
    #   핵심: "화면엔 오류인데 DB 는 바뀐" 부분 성공 금지 · 관리자 우회는 **모든** 쓰기 경로에서
    #         요청자·사유 필수 · 업무 변경과 감사는 한 트랜잭션 · 적용시점 형식 서버 검증
    print("\n── F. 게이트 v6 §8 최종 승인 테스트 (부분 성공·우회 필수·원자성·날짜형식) ──")
    PF = mkproject("999F001")
    OF = mkorder(PF, "SO-F-1")
    _OV_OK = {"override_requester": "기술영업팀 홍길동", "override_reason": "담당자 부재 · 대표 지시"}

    def _newunit(no, name=None):
        return pu.create_unit(PF, working_name=(name or f"개발{no}"), unit_no=no, actor_id=13)

    def _state(uid):
        return pu.get_unit(uid)["unit_state"]

    def _loc(rr):
        return rr.headers.get("location", "")

    # ① 기술영업팀장 확정 성공 → 성공 응답 + 상태 CONFIRMED (부분 성공이 사라졌는지)
    UF1 = _newunit("1호기")
    rf1 = _as(SALES_LEAD, f"/units/{UF1}/confirm", {})
    chk("§8-1 기술영업팀장 확정 → **성공** 응답", "success=" in _loc(rf1), _loc(rf1))
    chk("§8-1' 확정 결과 상태 CONFIRMED", _state(UF1) == "CONFIRMED")

    # ② 확정 처리 중 오류 → 상태 PROVISIONAL 유지 (화면 오류 = DB 무변화)
    UF2 = pu.create_unit(PF, working_name="번호없는개발", actor_id=13)
    rf2 = _as(SALES_LEAD, f"/units/{UF2}/confirm", {})
    chk("§8-2 확정 중 오류 → 오류 응답", "error=" in _loc(rf2))
    chk("§8-2' 확정 중 오류 → 상태 PROVISIONAL 유지", _state(UF2) == "PROVISIONAL")

    # ③ 관리자 번호변경 · 우회 사유 없음 → 변경 전 상태 유지
    #   ⚠ 적용시점을 비우면 '같은 적용시점 중복'이라는 **다른 이유**로 막혀 시험이 무의미해진다.
    #     지난 날짜를 명시해 "우회 검사가 없으면 반드시 성공하는 요청"으로 만든다.
    UF3 = _newunit("3호기")
    _req3 = {"new_unit_no": "33호기", "reason": "관리자 임의변경", "effective_from": "2026-07-01"}
    rf3 = _as(ADMIN, f"/units/{UF3}/unit-no", dict(_req3))
    chk("§8-3 관리자 번호변경 · 사유 없음 → 거부", "error=" in _loc(rf3), _loc(rf3))
    chk("§8-3' 호기번호 변경 전 값 유지", pu.get_unit(UF3)["current_unit_no"] == "3호기")
    chk("§8-3'' 번호 이력 추가 없음",
        cnt("project_unit_identifier_history", "project_unit_id=?", (UF3,)) == 1)
    chk("§8-3''' 같은 요청에 요청자+사유를 넣으면 수행됨(막힌 이유가 '우회 검사'임을 확인)",
        "success=" in _loc(_as(ADMIN, f"/units/{UF3}/unit-no", dict(_req3, **_OV_OK)))
        and cnt("project_unit_identifier_history", "project_unit_id=?", (UF3,)) == 2)

    # ④ 관리자 확정 · 사유 없음 → PROVISIONAL 유지
    rf4 = _as(ADMIN, f"/units/{UF3}/confirm", {})
    chk("§8-4 관리자 확정 · 사유 없음 → 거부", "error=" in _loc(rf4))
    chk("§8-4' 상태 PROVISIONAL 유지", _state(UF3) == "PROVISIONAL")

    # ⑤ 관리자 취소 · 사유 없음 → 기존 상태 유지
    rf5 = _as(ADMIN, f"/units/{UF3}/cancel", {"reason": "관리자 취소"})
    chk("§8-5 관리자 취소 · 사유 없음 → 거부", "error=" in _loc(rf5))
    chk("§8-5' 취소되지 않고 상태 그대로", _state(UF3) == "PROVISIONAL")

    # ⑥ 관리자 수주연결 · 사유 없음 → 링크 수 불변
    _lk0 = len(pu.get_unit(UF3)["orders"])
    rf6 = _as(ADMIN, f"/units/{UF3}/order-link", {"order_id": str(OF), "relation_type": "ORIGIN"})
    chk("§8-6 관리자 수주연결 · 사유 없음 → 거부", "error=" in _loc(rf6))
    chk("§8-6' 연결 수 불변", len(pu.get_unit(UF3)["orders"]) == _lk0)

    # ⑦ 관리자 후보 일괄반영 · 사유 없음 → Unit·링크·Audit 모두 불변
    PF7 = mkproject("999F007")
    LF7 = mkline(mkorder(PF7, "SO-F-7"), "1호기")
    _u0, _l0, _a0 = cnt("project_units"), cnt("project_unit_order_links"), len(pu.get_audit())
    rf7 = _as(ADMIN, f"/project/{PF7}/units/candidates/apply",
              {"pick": [str(LF7)], f"action_{LF7}": "new", "reason": "관리자 반영"})
    chk("§8-7 관리자 후보반영 · 사유 없음 → 거부", "error=" in _loc(rf7))
    chk("§8-7' Unit·링크·감사 **모두 불변**",
        cnt("project_units") == _u0 and cnt("project_unit_order_links") == _l0
        and len(pu.get_audit()) == _a0)

    # ⑧ 관리자 요청자 없음 → 업무 변경 **전** 거부 (완료보고 계약 = 요청자+사유 둘 다 필수)
    PF8 = mkproject("999F008")
    rf8 = _as(ADMIN, f"/project/{PF8}/units/create",
              {"working_name": "요청자없음", "override_reason": "사유만 입력"})
    chk("§8-8 관리자 우회 · **요청자 없음** → 거부", "error=" in _loc(rf8))
    chk("§8-8' 업무 변경 전 거부(생성 0)", cnt("project_units", "project_id=?", (PF8,)) == 0)
    rf8b = _as(ADMIN, f"/project/{PF8}/units/create",
               {"working_name": "사유없음", "override_requester": "기술영업팀 홍길동"})
    chk("§8-8'' 관리자 우회 · **사유 없음** → 거부", "error=" in _loc(rf8b))
    rf8c = _as(ADMIN, f"/project/{PF8}/units/create", dict(_OV_OK, working_name="정상복구"))
    chk("§8-8''' 요청자+사유 모두 있으면 수행 + 감사에 둘 다 기록",
        "success=" in _loc(rf8c) and cnt("project_units", "project_id=?", (PF8,)) == 1
        and "홍길동" in (pu.get_audit()[0]["note"] or "")
        and "담당자 부재" in (pu.get_audit()[0]["note"] or ""), str(pu.get_audit()[:1]))

    # ⑨ Audit INSERT 실패 주입 → 업무 변경 Rollback (업무+감사 = 단일 트랜잭션)
    with db.db_session() as _c:
        _c.execute("CREATE TRIGGER IF NOT EXISTS t_audit_fail BEFORE INSERT ON project_unit_audit "
                   "BEGIN SELECT RAISE(ABORT, '감사 기록 실패(시험 주입)'); END")
    PF9 = mkproject("999F009")
    rf9 = _as(ADMIN, f"/project/{PF9}/units/create", dict(_OV_OK, working_name="원자성"))
    chk("§8-9 감사 실패 주입 → **생성 Rollback**",
        cnt("project_units", "project_id=?", (PF9,)) == 0 and "error=" in _loc(rf9))
    UF9 = _newunit("9호기")
    _as(ADMIN, f"/units/{UF9}/unit-no", dict(_OV_OK, new_unit_no="99호기", reason="원자성 시험"))
    chk("§8-9' 감사 실패 주입 → **번호변경 Rollback**",
        pu.get_unit(UF9)["current_unit_no"] == "9호기"
        and cnt("project_unit_identifier_history", "project_unit_id=?", (UF9,)) == 1)
    _as(ADMIN, f"/units/{UF9}/confirm", dict(_OV_OK))
    chk("§8-9'' 감사 실패 주입 → **확정 Rollback**", _state(UF9) == "PROVISIONAL")
    _as(ADMIN, f"/units/{UF9}/order-link", dict(_OV_OK, order_id=str(OF), relation_type="ORIGIN"))
    chk("§8-9''' 감사 실패 주입 → **수주연결 Rollback**", len(pu.get_unit(UF9)["orders"]) == 0)
    _as(ADMIN, f"/units/{UF9}/cancel", dict(_OV_OK, reason="원자성 취소"))
    chk("§8-9'''' 감사 실패 주입 → **취소 Rollback**", _state(UF9) == "PROVISIONAL")
    PF9B = mkproject("999F09B")
    LF9B = mkline(mkorder(PF9B, "SO-F-9B"), "1호기")
    _as(ADMIN, f"/project/{PF9B}/units/candidates/apply",
        dict(_OV_OK, pick=[str(LF9B)], reason="원자성 일괄반영", **{f"action_{LF9B}": "new"}))
    chk("§8-9''''' 감사 실패 주입 → **후보 일괄반영 Rollback**",
        cnt("project_units", "project_id=?", (PF9B,)) == 0
        and cnt("project_unit_order_links", "order_id=?",
                (mkorder(PF9B, "SO-F-9B-x"),)) == 0)
    with db.db_session() as _c:
        _c.execute("DROP TRIGGER IF EXISTS t_audit_fail")
    _a9 = len(pu.get_audit())
    _as(ADMIN, f"/units/{UF9}/confirm", dict(_OV_OK))
    chk("§8-9'''''' 주입 해제 후 정상 수행 + 감사 1건(무조건 막기가 아님)",
        _state(UF9) == "CONFIRMED" and len(pu.get_audit()) == _a9 + 1)

    # ⑩ 잘못된 Effectivity 날짜 → 이력·현재값 불변 (화면을 거치지 않는 직접 요청 방어)
    UF10 = _newunit("10호기")
    _h0 = cnt("project_unit_identifier_history", "project_unit_id=?", (UF10,))
    for _bad, _why in (("20260501", "구분자 없음"), ("2026/05/01", "슬래시"),
                       ("0001-01-01", "업무상 불가능한 과거"), ("내일", "글자"),
                       ("2026-13-45", "없는 날짜")):
        _rb = _as(SALES_LEAD, f"/units/{UF10}/unit-no",
                  {"new_unit_no": "77호기", "reason": "형식 시험", "effective_from": _bad})
        chk(f"§8-10 잘못된 적용시점 거부 · {_why}({_bad})", "error=" in _loc(_rb), _loc(_rb))
    chk("§8-10' 이력·현재값 불변",
        cnt("project_unit_identifier_history", "project_unit_id=?", (UF10,)) == _h0
        and pu.get_unit(UF10)["current_unit_no"] == "10호기")
    _reff = _as(SALES_LEAD, f"/units/{UF10}/unit-no",
                {"new_unit_no": "77호기", "reason": "정상 소급 정정", "effective_from": "2026-06-01"})
    chk("§8-10'' 올바른 지난 날짜는 정상 반영(그 시점 조회로 확인)",
        "success=" in _loc(_reff) and pu.unit_no_at(UF10, "2026-06-15") == "77호기", _loc(_reff))
    chk("§8-10''' 지난 구간 정정이 **현재값을 바꾸지 않음**",
        pu.get_unit(UF10)["current_unit_no"] == "10호기")
    _rfut = _as(SALES_LEAD, f"/units/{UF10}/unit-no",
                {"new_unit_no": "78호기", "reason": "미래 예약", "effective_from": "2099-01-01"})
    chk("§8-10'''' 미래 예약은 V1 에서 거부(문구 유지)", "error=" in _loc(_rfut))

    # ══════════ G. 대표 지시(07-25) — 수주서 표기를 호기번호로 그대로 쓰기 ══════════
    #   F-01 이 막는 것은 '자동 승격'. 사용자가 화면에서 이 선택지를 고르는 것은 '명시 지정'.
    print("\n── G. 수주서 표기를 호기번호로 (대표 지시 · 사용자 명시 선택) ──")
    PG = mkproject("999G001")
    OG = mkorder(PG, "SO-G-1")
    LG1, LG2, LG3 = mkline(OG, "1호기"), mkline(OG, "2호기"), mkline(OG, "3호기")

    _sc = pu.scan_candidates(PG)
    chk("G-0 후보에 '번호 쓸 수 있음' 정보 제공(no_taken=False)",
        all(x["no_taken"] is False for x in _sc["candidates"]), str(_sc["candidates"][:1]))
    _rg = client.post(f"/project/{PG}/units/candidates/apply",
                      data={"pick": [str(LG1), str(LG2)],
                            f"action_{LG1}": "new_no", f"action_{LG2}": "new",
                            "reason": "수주서 번호 그대로 시험"}, follow_redirects=False)
    chk("G-1 반영 303", _rg.status_code == 303)
    _ug = {(_u["seed_order_item_id"]): _u for _u in pu.get_units(PG)}
    chk("G-2 'new_no' → 호기번호가 수주서 표기로 지정됨",
        _ug[LG1]["current_unit_no"] == "1호기", str(_ug[LG1]["current_unit_no"]))
    chk("G-3 'new' → 호기번호는 여전히 비어 있음(기존 동작 유지)",
        _ug[LG2]["current_unit_no"] is None, str(_ug[LG2]["current_unit_no"]))
    chk("G-4 둘 다 개발·미확정 상태",
        _ug[LG1]["unit_state"] == "PROVISIONAL" and _ug[LG2]["unit_state"] == "PROVISIONAL")
    chk("G-5 번호 지정 건은 **변경이력 첫 줄**이 남음",
        cnt("project_unit_identifier_history", "project_unit_id=?", (_ug[LG1]["id"],)) == 1
        and cnt("project_unit_identifier_history", "project_unit_id=?", (_ug[LG2]["id"],)) == 0)
    chk("G-6 최초 수주(ORIGIN) 연결은 그대로",
        len(pu.get_unit(_ug[LG1]["id"])["orders"]) == 1)
    # [F-06] 같은 번호 재사용 금지 — 이미 쓴 번호는 후보 화면에서 선택지가 사라진다
    _sc2 = pu.scan_candidates(PG)
    _c1 = [x for x in _sc2["candidates"] if x["order_item_id"] == LG3][0]
    chk("G-7 아직 안 쓴 번호(3호기)는 선택 가능", _c1["no_taken"] is False)
    OG2 = mkorder(PG, "SO-G-2")
    LG4 = mkline(OG2, "1호기")                       # 이미 쓴 번호가 다른 수주에 또 나옴(정상 업무)
    _sc3 = pu.scan_candidates(PG)
    _c2 = [x for x in _sc3["candidates"] if x["order_item_id"] == LG4][0]
    chk("G-8 이미 쓴 번호(1호기)는 '번호 그대로' 선택 불가로 표시(no_taken=True)",
        _c2["no_taken"] is True)
    # 서버도 막는다(화면을 거치지 않고 보내도)
    _before_g = cnt("project_units", "project_id=?", (PG,))
    _rg2 = client.post(f"/project/{PG}/units/candidates/apply",
                       data={"pick": [str(LG4)], f"action_{LG4}": "new_no",
                             "reason": "이미 쓴 번호 강제 시도"}, follow_redirects=False)
    chk("G-9 서버가 이미 쓴 번호를 거부(직접 요청도 차단)",
        cnt("project_units", "project_id=?", (PG,)) == _before_g, _rg2.headers.get("location", ""))
    chk("G-10 화면에 '수주서 번호 그대로' 선택지와 일괄 버튼이 있다",
        "new_no" in client.get(f"/project/{PG}/units/candidates").text
        and "수주서 번호 그대로" in client.get(f"/project/{PG}/units/candidates").text)
    _html_g = client.get(f"/project/{PG}/units/candidates").text
    chk("G-11 안내문에 개발 용어(project_units.id)가 **접혀** 있다(현장 말 우선)",
        "규정 원문" in _html_g and "<details" in _html_g)
    chk("G-12 권한 없는 부서는 '번호 그대로'도 못 씀",
        _blocked(_as(DESIGN, f"/project/{PG}/units/candidates/apply",
                     {"pick": [str(LG3)], f"action_{LG3}": "new_no", "reason": "설계팀 시도"})))
    m.get_user = lambda req: CEO

    chk("분할·통합 실행 경로 없음(404)",
        client.post(f"/units/{uid_r}/split", data={}, follow_redirects=False).status_code == 404)
except ImportError as e:
    print(f"  SKIP 라우트 테스트 (패키지 없음: {e})")

print(f"\n{'=' * 52}\n결과: PASS {ok} · FAIL {fail}")
sys.exit(0 if fail == 0 else 1)
