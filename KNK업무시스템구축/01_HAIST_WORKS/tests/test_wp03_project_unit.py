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
from app.migrations.m_z1054_unit_work_status import migrate as _mig54  # noqa: E402
print("마이그레이션:", _mig(db.DB_PATH))
print("마이그레이션(z1054):", _mig54(db.DB_PATH))
with db.db_session() as _c0:
    for _col in ("po_entity", "ship_entity"):
        try:
            _c0.execute(f"ALTER TABLE projects ADD COLUMN {_col} TEXT")
        except Exception:
            pass
from app import project_unit as pu  # noqa: E402

# ── 과거 데이터 보정 잠금과 시험의 관계 (2026-07-26 대표 지시) ──────────────────
#   운영에는 이 환경변수가 없어 **항상 잠김**이다. 다만 지시서 §4.3 이
#   "이미 구현·배포된 WP-03 기능은 삭제하거나 되돌리지 않는다"고 했으므로,
#   보정 **로직**(멱등·예외·감사·단일 트랜잭션)은 시험에서 계속 검증한다.
#   ⭐ **잠금 자체는 §M 에서 이 변수를 도로 지우고** 검증한다(운영과 같은 상태로).
os.environ["KNK_ENABLE_UNIT_STATUS_SYNC"] = "1"

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


_MK_SEQ = [0]


def mkproject(tag="", entity="KOR", code=None):
    """[규정 V1] 시작 법인은 **관리번호**로 정해진다 → 시험 데이터도 정식 형식으로 만든다.
    본사 `[순번3][업무구분][YYMM]` · 베트남 `[순번3][V][업무구분][YYMM]`."""
    if code is None:
        _MK_SEQ[0] += 1
        code = f"{_MK_SEQ[0]:03d}{'V' if entity == 'VN' else ''}T2601"
    with db.db_session() as c:
        c.execute("INSERT INTO projects (mgmt_code, name, status) VALUES (?,?,?)",
                  (code, f"P-{tag or code}", "진행중"))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def mkorder(pid, no):
    with db.db_session() as c:
        c.execute("INSERT INTO orders (order_no, project_id, status) VALUES (?,?, 'CONFIRMED')",
                  (no, pid))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def mkline(oid, label, qty=1, status=None, due=None):
    """status = 작업일정표 상태(출하/진행중/보류/취소) · due = 납품 예정일"""
    with db.db_session() as c:
        c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, "
                  "unit_status, due_date) VALUES (?,?,0,0,?,?,?)", (oid, qty, label, status, due))
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

# ── 시나리오 D: 시작 법인 = **관리번호가 단일 근거** (F-08 · 대표 규정 V1 2026-07-26) ──
#   §3 본사 8자리 / 베트남 9자리(V) · §4 시작한 법인 기준(출하처 아님) · §7 임의 KOR 금지
for _code, _want in (("005T2601", "KOR"), ("016C2607", "KOR"), ("001VT2701", "VN"),
                     ("016VC2607", "VN"), ("A01T2606", "KOR")):
    chk(f"D 관리번호 {_code} → 시작 법인 {_want}", pu.mgmt_code_entity(_code) == _want,
        pu.mgmt_code_entity(_code))
for _bad in ("", "ZZZ2512", "005T260", "005X2601", "5T2601", "005VV T2601"):
    try:
        pu.mgmt_code_entity(_bad)
        chk(f"D 읽을 수 없는 관리번호 거부 · {_bad!r}", False)
    except ValueError:
        chk(f"D 읽을 수 없는 관리번호 거부 · {_bad!r}", True)
PD_VN = mkproject("베트남시작", entity="VN")
chk("D' 베트남 시작 프로젝트 → 호기 법인 VN", (lambda u: (
    pu.get_unit(u)["entity"] == "VN"))(pu.create_unit(PD_VN, working_name="VN개발")))
PD_KR = mkproject("본사시작")
chk("D'' 본사 시작 프로젝트 → 호기 법인 KOR", (lambda u: (
    pu.get_unit(u)["entity"] == "KOR"))(pu.create_unit(PD_KR, working_name="본사개발")))
PD_BAD = mkproject(code="ZZZ2512")          # 규격을 벗어난 옛 관리번호
try:
    pu.create_unit(PD_BAD, working_name="개발X")
    chk("D''' 관리번호를 못 읽으면 중단(임의 KOR 부여 없음)", False)
except ValueError as e:
    chk("D''' 관리번호를 못 읽으면 중단(임의 KOR 부여 없음)", "관리번호" in str(e), str(e))
# ⛔ [규정 V1 §4] 주문 법인·출하 법인이 달라도 **충돌이 아니다**(한국 수주 → 베트남 출하 = 정상)
with db.db_session() as c:
    try:
        c.execute("UPDATE projects SET po_entity='KR', ship_entity='VN' WHERE id=?", (PD_KR,))
    except Exception:
        pass
chk("D'''' 주문=한국·출하=베트남 이어도 정상 생성(더 이상 '충돌' 아님)",
    pu.create_unit(PD_KR, working_name="한국수주-베트남출하") > 0)

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

    def _loc(rr):
        return rr.headers.get("location", "")
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
    # (확정 후 취소에 요청자를 요구하는 승인서 §4.2 규칙은 아래 K부에서 확정 호기로 검증한다.
    #  여기 uid_r 은 호기번호가 없어 아직 확정되지 않은 상태다.)
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
    # [승인서 §4.2 개정] 일반 기술영업 업무도 **감사기록은 남긴다**(예전엔 아예 안 남겼다).
    #   다만 '관리자 비상복구'와는 분명히 구분된다.
    _n3 = len(pu.get_audit())
    _as(SALES_LEAD, f"/project/{PR}/units/create", {"working_name": "정상업무"})
    _aud3 = pu.get_audit()
    chk("§4.2 일반 기술영업 업무도 감사 기록(예전엔 0건이었다)", len(_aud3) == _n3 + 1)
    chk("§4.2' 일반 업무는 '관리자 비상복구'와 구분",
        _aud3 and "관리자 비상복구" not in (_aud3[0]["note"] or ""), str(_aud3[:1]))

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
    # [승인서 §4.2] 소급 효력일 변경은 요청자 필수 — 없으면 업무 변경 전에 거부
    _rnoreq = _as(SALES_LEAD, f"/units/{UF10}/unit-no",
                  {"new_unit_no": "77호기", "reason": "소급인데 요청자 없음",
                   "effective_from": "2026-06-01"})
    chk("§8-10'a 소급 효력일인데 요청자 없음 → 거부(승인서 §4.2)",
        "error=" in _loc(_rnoreq)
        and cnt("project_unit_identifier_history", "project_unit_id=?", (UF10,)) == _h0, _loc(_rnoreq))
    _reff = _as(SALES_LEAD, f"/units/{UF10}/unit-no",
                {"new_unit_no": "77호기", "reason": "정상 소급 정정",
                 "effective_from": "2026-06-01", "requester": "기술영업팀 김프로"})
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

    # ── 후보 수 = **아직 반영 안 한 것만** (대표 지적 07-26) ──
    #   전체 줄 수를 그대로 보이면 다 끝낸 뒤에도 '후보 23'이 남아 할 일이 있는 것처럼 읽힌다.
    PH = mkproject("후보수")
    OH = mkorder(PH, "SO-H-1")
    LH1, LH2, LH3 = mkline(OH, "1호기"), mkline(OH, "2호기"), mkline(OH, "3호기")
    _s0 = pu.project_unit_summary(PH)
    chk("H-1 반영 전: 남은 후보 3 · 전체 3 · 반영됨 0",
        (_s0["candidates"], _s0["candidates_total"], _s0["candidates_done"]) == (3, 3, 0), str(_s0))
    pu.apply_candidate_decisions(PH, [dec(LH1, "new_no"), dec(LH2, "new")], reason="일부 반영")
    _s1 = pu.project_unit_summary(PH)
    chk("H-2 2건 반영 후: 남은 후보 1 · 반영됨 2",
        (_s1["candidates"], _s1["candidates_done"]) == (1, 2), str(_s1))
    pu.apply_candidate_decisions(PH, [dec(LH3, "new")], reason="나머지 반영")
    _s2 = pu.project_unit_summary(PH)
    chk("H-3 전부 반영 후: **남은 후보 0**(전체 3은 그대로 보관)",
        (_s2["candidates"], _s2["candidates_total"], _s2["candidates_done"]) == (0, 3, 3), str(_s2))
    _html_h = _as(SALES_LEAD, f"/project/{PH}/units").text
    chk("H-4 화면이 '전부 반영됨'으로 말한다(‘후보 3’ 이라고 하지 않음)",
        "전부 반영됨" in _html_h and "아직 반영 안 한 후보" not in _html_h)
    chk("H-5 남은 후보 있을 땐 개수를 붙여 보여준다",
        "아직 반영 안 한 후보" in _as(SALES_LEAD, f"/project/{PG}/units").text)
    m.get_user = lambda req: CEO

    # ═══════ I. 작업일정표 상태 반영 — 게이트 §10 확산 전 필수 테스트 10종 ═══════
    #   ⭐§4 신원(unit_state)과 진행(work_status)은 **다른 값** — 하나로 합쳐 저장하지 않는다.
    #   ⛔§2.1 납품일이 지났다는 것만으로 완료·확정 처리하지 않는다.
    print("\n── I. 작업일정표 상태 반영 (게이트 §10 필수 10종) ──")
    _PAST = "2026-01-15"                      # 이미 지난 납품 예정일
    PI = mkproject("상태반영")
    OI1 = mkorder(PI, "SO-I-1")
    LI_run = mkline(OI1, "1호기", status="진행중", due=_PAST)
    LI_hold = mkline(OI1, "2호기", status="보류", due=_PAST)
    LI_ship = mkline(OI1, "3호기", status="출하", due=_PAST)
    LI_cxl = mkline(OI1, "4호기", status="취소", due=_PAST)
    LI_none = mkline(OI1, "5호기", status=None, due=_PAST)
    mkline(OI1, "예비품 세트", qty=2, status="취소")     # 호기로 식별 안 되는 취소 줄

    _sc = pu.scan_candidates(PI)
    _by = {x["order_item_id"]: x for x in _sc["candidates"]}
    # ① 납품일 경과 + 진행중 → 확정되지 않음
    chk("§10-1 납품일 지난 '진행중' → 확정 아님(개발·미확정)",
        (_by[LI_run]["planned_state"], _by[LI_run]["planned_work"]) == ("PROVISIONAL", "IN_PROGRESS"))
    # ② 납품일 경과 + 보류 → 보류 유지
    chk("§10-2 납품일 지난 '보류' → 개발·미확정 + 보류 유지",
        (_by[LI_hold]["planned_state"], _by[LI_hold]["planned_work"]) == ("PROVISIONAL", "ON_HOLD"))
    # ③ 출하 + 유효한 호기 → 확정 및 출하 보존
    chk("§10-3 '출하' → 확정 + 출하 상태 보존",
        (_by[LI_ship]["planned_state"], _by[LI_ship]["planned_work"]) == ("CONFIRMED", "SHIPPED"))
    chk("§10-3' 상태 없는 줄은 **확정하지 않는다**(빈값을 함부로 승격 금지)",
        (_by[LI_none]["planned_state"], _by[LI_none]["planned_work"]) == ("PROVISIONAL", "IN_PROGRESS")
        and _by[LI_none]["schedule_label"] == pu.SCHEDULE_UNSET)
    chk("§10-3'' 납품 예정일을 화면에 낼 수 있게 내려준다(§8)", _by[LI_ship]["due_date"] == _PAST)
    # ⑤⑥ 취소 두 갈래
    chk("§10-5 취소 + 호기 식별 있음 → 취소 호기로 보존",
        (_by[LI_cxl]["planned_state"], _by[LI_cxl]["planned_work"]) == ("CANCELLED", "CANCELLED"))
    chk("§10-6 취소 + 호기 식별 없음 → 후보 제외 + **사유 보존**",
        len(_sc["excluded"]) == 1 and "취소" in _sc["excluded"][0]["skip_reason"],
        str(_sc["excluded"]))
    # 권한: 확정·취소로 가는 줄은 승인권자만
    m.get_user = lambda req: SALES_DELEG        # 기술영업 위임자(팀원) — 확정 권한 없음
    _r_np = client.post(f"/project/{PI}/units/candidates/apply",
                        data={"pick": [str(LI_ship)], f"action_{LI_ship}": "new_no",
                              "reason": "위임자 시험"}, follow_redirects=False)
    chk("§10-권한 위임자(팀원)는 '출하→확정' 줄을 반영할 수 없다",
        cnt("project_units", "project_id=? AND seed_order_item_id=?", (PI, LI_ship)) == 0)
    m.get_user = lambda req: SALES_LEAD         # 기술영업팀장 = 승인권자
    client.post(f"/project/{PI}/units/candidates/apply",
                data={"pick": [str(LI_run), str(LI_hold), str(LI_ship), str(LI_cxl), str(LI_none)],
                      f"action_{LI_run}": "new_no", f"action_{LI_hold}": "new_no",
                      f"action_{LI_ship}": "new_no", f"action_{LI_cxl}": "new_no",
                      f"action_{LI_none}": "new_no", "reason": "과거 데이터 반영"},
                follow_redirects=False)
    _u = {u["seed_order_item_id"]: u for u in pu.get_units(PI)}
    chk("§10-3''' 반영 결과: 출하 호기 = 확정 + SHIPPED",
        (_u[LI_ship]["unit_state"], _u[LI_ship]["work_status"]) == ("CONFIRMED", "SHIPPED"))
    chk("§10-1' 반영 결과: 진행중 호기 = 개발·미확정 + IN_PROGRESS",
        (_u[LI_run]["unit_state"], _u[LI_run]["work_status"]) == ("PROVISIONAL", "IN_PROGRESS"))
    chk("§10-2' 반영 결과: 보류 호기 = 개발·미확정 + ON_HOLD",
        (_u[LI_hold]["unit_state"], _u[LI_hold]["work_status"]) == ("PROVISIONAL", "ON_HOLD"))
    chk("§10-5' 반영 결과: 취소 호기 = 취소 + CANCELLED(물리삭제 없음)",
        (_u[LI_cxl]["unit_state"], _u[LI_cxl]["work_status"]) == ("CANCELLED", "CANCELLED")
        and cnt("project_units", "id=?", (_u[LI_cxl]["id"],)) == 1)
    chk("§10-4 같은 수주에 출하·진행중이 섞여 있어도 **호기별로** 다르게 유지(부분출하)",
        _u[LI_ship]["unit_state"] == "CONFIRMED" and _u[LI_run]["unit_state"] == "PROVISIONAL")
    chk("§10-4' 신원과 진행을 **따로** 보존(한 칸으로 합치지 않음)",
        all(("unit_state" in x and "work_status" in x) for x in _u.values()))
    # ④ 수주번호 전체 완료로 넘겨짚지 않는다
    _sm = pu.project_unit_summary(PI)
    chk("§10-4'' 출하 호기 수를 진행중과 구분해 센다",
        (_sm["shipped"], _sm["on_hold"]) == (1, 1), str(_sm))

    # ⑦ 반복 실행 → 중복 없음  ⑨ 상태 충돌 → 덮어쓰지 않음
    _pv = pu.status_backfill_preview(PI)
    chk("§10-7 이미 맞춰진 뒤 대조하면 **바뀔 것 0**(재실행해도 무동작)",
        _pv["summary"]["change"] == 0, str(_pv["summary"]))
    _n_units0 = cnt("project_units", "project_id=?", (PI,))
    _r1 = pu.status_backfill_apply(PI, reason="1차 보정")
    _r2 = pu.status_backfill_apply(PI, reason="2차 보정(같은 조건)")
    chk("§10-7' 두 번 실행해도 호기 수 불변 · 보정 0건",
        cnt("project_units", "project_id=?", (PI,)) == _n_units0
        and _r1["changed"] == 0 and _r2["changed"] == 0)
    chk("§10-7'' 바뀐 게 없으면 보정 이력도 늘지 않음",
        cnt("project_unit_status_backfill", "project_id=?", (PI,)) == 0)
    chk("§10-6' 제외한 줄은 보정 실행 때 **기록으로 남는다**",
        cnt("project_unit_candidate_skips", "project_id=?", (PI,)) == 1)

    # 보정이 실제로 일하는 경우 — 나중에 작업일정표가 '출하'로 바뀐 호기
    with db.db_session() as c:
        c.execute("UPDATE order_items SET unit_status='출하' WHERE id=?", (LI_run,))
    _pv2 = pu.status_backfill_preview(PI)
    chk("§10-3'''' 작업일정표가 출하로 바뀌면 대조표에 '확정 예정'으로 뜬다",
        _pv2["summary"]["change"] == 1 and _pv2["summary"]["to_confirmed"] == 1, str(_pv2["summary"]))
    _r3 = pu.status_backfill_apply(PI, reason="출하 반영")
    _u2 = {u["seed_order_item_id"]: u for u in pu.get_units(PI)}
    chk("§10-3''''' 보정 실행 → 확정 + SHIPPED · 이력 1건",
        (_u2[LI_run]["unit_state"], _u2[LI_run]["work_status"]) == ("CONFIRMED", "SHIPPED")
        and _r3["changed"] == 1
        and cnt("project_unit_status_backfill", "project_id=?", (PI,)) == 1)
    # ⑨ 충돌: 이미 확정인데 작업일정표가 '진행중'으로 되돌아감 → 덮어쓰지 않음
    with db.db_session() as c:
        c.execute("UPDATE order_items SET unit_status='진행중' WHERE id=?", (LI_run,))
    _pv3 = pu.status_backfill_preview(PI)
    _row = [x for x in _pv3["rows"] if x["unit_id"] == _u2[LI_run]["id"]][0]
    chk("§10-9 확정된 호기를 되돌리는 방향은 **덮어쓰지 않고 예외로 표시**",
        (not _row["change"]) and "되돌리지 않음" in (_row["conflict"] or ""), str(_row["conflict"]))
    _r4 = pu.status_backfill_apply(PI, reason="충돌 확인")
    chk("§10-9' 예외 건은 실행해도 그대로",
        pu.get_unit(_u2[LI_run]["id"])["unit_state"] == "CONFIRMED" and _r4["skipped"] >= 1)
    # ⑩ 보정 전후 총수량·상태별 수량 일치
    _sm2 = pu.project_unit_summary(PI)
    chk("§10-10 총수량 보존(5대) · 상태별 합이 총수와 일치",
        _sm2["units"] == 5
        and (_sm2["provisional"] + _sm2["confirmed"] + _sm2["cancelled"]) == _sm2["units"]
        and (_sm2["shipped"] + _sm2["on_hold"] + _sm2["in_progress"]
             + _sm2["work_cancelled"]) == _sm2["units"], str(_sm2))
    # ⑧ 감사기록 실패 주입 → 보정 전체 롤백
    with db.db_session() as c:
        c.execute("UPDATE order_items SET unit_status='출하' WHERE id=?", (LI_hold,))
        c.execute("CREATE TRIGGER IF NOT EXISTS t_bf_fail BEFORE INSERT ON project_unit_audit "
                  "BEGIN SELECT RAISE(ABORT, '감사 실패(주입)'); END")
    _before_bf = cnt("project_unit_status_backfill", "project_id=?", (PI,))
    try:
        pu.status_backfill_apply(PI, reason="감사 실패 시험",
                                 audit={"actor_id": 1, "action": "x", "target": "y", "note": "z"})
    except Exception:
        pass
    with db.db_session() as c:
        c.execute("DROP TRIGGER IF EXISTS t_bf_fail")
    chk("§10-8 감사기록 실패 → 보정 **전체 롤백**(상태·이력 모두 그대로)",
        pu.get_unit(_u2[LI_hold]["id"])["unit_state"] == "PROVISIONAL"
        and cnt("project_unit_status_backfill", "project_id=?", (PI,)) == _before_bf)
    chk("§10-8' 주입 해제 후에는 정상 보정됨",
        pu.status_backfill_apply(PI, reason="정상 재실행")["changed"] == 1
        and pu.get_unit(_u2[LI_hold]["id"])["unit_state"] == "CONFIRMED")
    # 화면 §8 필수 표시
    _html_i = _as(SALES_LEAD, f"/project/{PI}/units/status-sync").text
    for _need in ("관리번호", "수주번호", "호기번호", "납품 예정일", "작업일정표 상태",
                  "원본 출처", "법인", "반영 예정", "그대로 둠"):
        chk(f"§8 대조 화면에 '{_need}' 표시", _need in _html_i)
    chk("§8' 상태를 **글자로** 표시(색만 쓰지 않음)",
        "출하" in _html_i and "보류" in _html_i)
    # [게이트 §4·§11] 호기 목록에서도 신원과 진행을 **따로** 보여준다(한 칸으로 뭉치지 않음)
    _html_list = _as(SALES_LEAD, f"/project/{PI}/units").text
    chk("§4 호기 목록에 '진행' 칸이 신원과 따로 있다",
        "<th>진행</th>" in _html_list and 'class="wk ' in _html_list, "진행 칸 없음")
    chk("§4' 호기 목록 머리글에 진행 상태별 수량 표시",
        "진행중" in _html_list and "보류" in _html_list and "출하" in _html_list)
    chk("§9 대조 화면은 읽기 전용 — 조회만으로 아무것도 안 바뀜",
        pu.status_backfill_preview(PI)["summary"]["change"] == 0)

    # ── 실행 전 게이트(2026-07-26) §1.1 — **이미 확정인 호기를 다시 확정하지 않는다** ──
    #   기존 확정자·확정시각을 보정이 덮어쓰면 "누가 언제 확정했나"가 이번 작업으로 바뀐다.
    PJ = mkproject("기존확정")
    OJ1 = mkorder(PJ, "SO-J-1")
    LJ1 = mkline(OJ1, "1호기", status="진행중")
    pu.apply_candidate_decisions(PJ, [dec(LJ1, "new_no")], reason="먼저 진행중으로 등록")
    _uj = pu.get_units(PJ)[0]["id"]
    pu.confirm_unit(_uj, actor_id=777)                       # 원래 확정자 = 777
    _orig = pu.get_unit(_uj)
    with db.db_session() as c:                               # 나중에 작업일정표가 출하로 바뀜
        c.execute("UPDATE order_items SET unit_status='출하' WHERE id=?", (LJ1,))
    _pvj = pu.status_backfill_preview(PJ)
    _rj = [x for x in _pvj["rows"] if x["unit_id"] == _uj][0]
    chk("§1.1 이미 확정 + 출하 → 신원은 그대로, **진행상태만** 바뀜",
        _rj["change"] and _rj["after_state"] == "CONFIRMED"
        and _rj["before_state"] == "CONFIRMED" and _rj["after_work"] == "SHIPPED")
    chk("§1.1' 변경 필드 목록에 확정자·확정시각이 **없다**",
        "confirmed_by" not in _rj["fields"] and "confirmed_at" not in _rj["fields"]
        and "unit_state" not in _rj["fields"], str(_rj["fields"]))
    pu.status_backfill_apply(PJ, reason="진행상태만 보정", actor_id=999)
    _after = pu.get_unit(_uj)
    chk("§1.1'' 보정 후에도 **원래 확정자·확정시각 그대로**(999로 덮어쓰지 않음)",
        _after["confirmed_by"] == _orig["confirmed_by"] == 777
        and _after["confirmed_at"] == _orig["confirmed_at"],
        f"{_orig['confirmed_by']}→{_after['confirmed_by']}")
    chk("§1.1''' 진행상태만 SHIPPED 로 반영됨", _after["work_status"] == "SHIPPED")
    # [승인서 §3.3 수량 계약] 화면 숫자도 '새로 확정'과 '이미 확정'을 뭉치면 안 된다
    chk("§3.3 요약이 '새로 확정 0 · 이미 확정이라 진행상태만 1' 로 갈라져 보인다",
        _pvj["summary"]["to_confirmed"] == 0 and _pvj["summary"]["already_confirmed"] == 1,
        str(_pvj["summary"]))
    # [§1.2] 실제 출하일을 지어내지 않는다
    chk("§1.2 실제 출하일은 **미확인(빈값)** — 납품 예정일·보정일을 복사하지 않음",
        not (_after.get("shipped_on") or "").strip(), str(_after.get("shipped_on")))
    # [§3 제출표] 행별 필수 항목이 모두 내려온다
    for _k in ("unit_id", "order_nos", "unit_no", "due_date", "shipped_on", "schedule_label",
               "before_state", "before_work", "after_state", "after_work", "fields", "action"):
        chk(f"§3 제출표 항목 '{_k}' 제공", _k in _rj)
    chk("§3' 처리 구분은 변경/유지/예외 셋 중 하나",
        all(x["action"] in ("변경", "유지", "예외") for x in _pvj["rows"]))
    m.get_user = lambda req: CEO

    # ══════════ K. 최종 실행 승인서(2026-07-26) §4.2 — 감사기록·요청자·사유 정책 ══════════
    #   "285개 확산 전에는 **정상 호기 확정도** 처리자·시각·상태변경 감사기록이 반드시
    #    생성되는지 검증하라. 관리자 대행, 과거 데이터 보정, 확정 후 정정·취소에는
    #    요청자와 사유를 필수로 한다." (대표 지시)
    print("\n── K. 승인서 §4.2 감사기록·요청자·사유 정책 ──")
    PK = mkproject("999K001")
    OK1 = mkorder(PK, "SO-K-1")
    _uk = pu.create_unit(PK, working_name="개발1호기", unit_no="1호기", actor_id=13)

    # ① 본인이 정상 권한으로 하는 **최초 확정** — 요청자·사유 없이 되고, 감사는 반드시 남는다
    _ak0 = len(pu.get_audit())
    _rk1 = _as(SALES_LEAD, f"/units/{_uk}/confirm", {})
    _ak1 = pu.get_audit()
    chk("§4.2-1 정상 최초 확정은 요청자·사유 없이 수행", "success=" in _loc(_rk1), _loc(_rk1))
    chk("§4.2-2 **정상 확정도 감사기록 1건 생성**(예전엔 0건)", len(_ak1) == _ak0 + 1)
    chk("§4.2-3 감사에 처리자(실행자) 기록",
        _ak1 and "실행:" in (_ak1[0]["note"] or "") and _ak1[0]["actor_id"] == 13, str(_ak1[:1]))
    chk("§4.2-4 감사에 처리시각 기록", _ak1 and (_ak1[0]["created_at"] or "").strip())
    chk("§4.2-5 감사에 **어떤 상태에서 어떤 상태로** 기록",
        _ak1 and "PROVISIONAL" in (_ak1[0]["note"] or "")
        and "CONFIRMED" in (_ak1[0]["note"] or ""), str(_ak1[:1]))
    chk("§4.2-6 감사에 대상 Unit 기록",
        _ak1 and f"unit#{_uk}" in (_ak1[0]["target"] or ""), str(_ak1[:1]))

    # ② 확정 후 **호기번호 정정** — 요청자 없으면 업무 변경 전 거부
    _no0 = pu.get_unit(_uk)["current_unit_no"]
    _rk2 = _as(SALES_LEAD, f"/units/{_uk}/unit-no", {"new_unit_no": "5호기", "reason": "정정"})
    chk("§4.2-7 확정 후 번호 정정 · 요청자 없음 → 거부", "error=" in _loc(_rk2), _loc(_rk2))
    chk("§4.2-7' 거부 시 현재 호기번호 불변", pu.get_unit(_uk)["current_unit_no"] == _no0)

    # ③ **과거 데이터 보정** — 승인 근거(요청자) 없으면 거부, DB 불변
    PK2 = mkproject("999K002")
    LK2 = mkline(mkorder(PK2, "SO-K-2"), "1호기", status="진행중", due="2026-05-01")
    pu.apply_candidate_decisions(PK2, [dec(LK2, "new_no")], reason="먼저 등록")
    _uk2 = pu.get_units(PK2)[0]["id"]
    with db.db_session() as c:      # 나중에 작업일정표가 '출하'로 바뀐 상황(=과거 데이터 보정 대상)
        c.execute("UPDATE order_items SET unit_status='출하' WHERE id=?", (LK2,))
    _st0, _abf = pu.get_unit(_uk2)["unit_state"], len(pu.get_audit())
    _rk3 = _as(SALES_LEAD, f"/project/{PK2}/units/status-sync/apply", {"reason": "보정 사유만"})
    chk("§4.2-8 과거 데이터 보정 · 승인 근거 없음 → 거부", "error=" in _loc(_rk3), _loc(_rk3))
    chk("§4.2-8' 거부 시 신원·감사 **모두 불변**",
        pu.get_unit(_uk2)["unit_state"] == _st0 and len(pu.get_audit()) == _abf)
    _rk4 = _as(SALES_LEAD, f"/project/{PK2}/units/status-sync/apply",
               {"reason": "과거 출하 사실 복원", "requester": "대표 승인 2026-07-26"})
    _ak4 = pu.get_audit()
    chk("§4.2-9 승인 근거+사유 있으면 보정 수행", "success=" in _loc(_rk4), _loc(_rk4))
    chk("§4.2-10 감사에 **승인자와 실행자를 구분**해 기록",
        _ak4 and "요청·승인: 대표 승인 2026-07-26" in (_ak4[0]["note"] or "")
        and "실행:" in (_ak4[0]["note"] or ""), str(_ak4[:1]))
    chk("§4.2-11 감사에 처리 유형·근거·실제 출하일 미확인 기록",
        _ak4 and "과거 데이터 보정" in (_ak4[0]["note"] or "")
        and "근거: 작업일정표 원본 상태" in (_ak4[0]["note"] or "")
        and "실제 출하일 미확인" in (_ak4[0]["note"] or ""), str(_ak4[:1]))
    chk("§4.2-12 보정으로 실제 출하일을 지어내지 않음",
        not (pu.get_unit(_uk2).get("shipped_on") or "").strip())

    # ④ 관리자 대행은 유형과 관계없이 여전히 둘 다 필수(기존 계약 유지)
    _uk3 = pu.create_unit(PK, working_name="개발2호기", unit_no="2호기", actor_id=13)
    chk("§4.2-13 관리자 대행 · 요청자·사유 없음 → 거부(유형 무관)",
        "error=" in _loc(_as(ADMIN, f"/units/{_uk3}/confirm", {})))

    # ══════════ L. 게이트 UI 판정(2026-07-26) §8 — 작업영역 접기·수주 선택 14항 ══════════
    #   대표 지적: 작업 칸의 수주 선택창에 첫 수주번호가 저절로 떠서 **저장된 연결값으로 오해**된다.
    #   판정: 빈 기본값 + 고르기 전 버튼 비활성 + 작업폼은 '작업 열기' 아래로 접고 한 번에 하나만.
    print("\n── L. 호기 목록 작업영역 UI (게이트 §8 14항) ──")
    import re as _re
    PL = mkproject("999L001")
    OL1, OL2 = mkorder(PL, "SO-L-1"), mkorder(PL, "SO-L-2")
    PLX = mkproject("999L002")                       # 다른 관리번호(연결 불가여야 함)
    OLX = mkorder(PLX, "SO-LX-1")
    UL1 = pu.create_unit(PL, working_name="개발1호기", unit_no="1호기", actor_id=13)
    UL2 = pu.create_unit(PL, working_name="개발2호기", unit_no="2호기", actor_id=13)
    pu.link_order(UL1, OL1, relation_type="ORIGIN", actor_id=13)

    _hl = _as(SALES_LEAD, f"/project/{PL}/units").text
    _seg1 = _hl.split(f'id="ops-{UL1}"')[1].split("</tr>")[0]
    _sel1 = _seg1.split('name="order_id"')[1].split("</select>")[0] \
        if 'name="order_id"' in _seg1 else ""

    chk("§8-1 수주 선택 첫 항목이 **빈값** — 고르기 전 수주번호를 보여주지 않음",
        '<option value="" selected>— 연결할 수주 선택 —</option>' in _hl)
    _btn = _re.search(r"<button[^>]*js-ops-linkbtn[^>]*>", _hl)
    chk("§8-2 고르기 전 **연결 버튼 비활성**", bool(_btn) and "disabled" in _btn.group(0),
        _btn.group(0) if _btn else "버튼 없음")

    _l0, _a0 = cnt("project_unit_order_links"), len(pu.get_audit())
    _r3 = _as(SALES_LEAD, f"/units/{UL1}/order-link", {"order_id": "", "relation_type": "ADDITIONAL"})
    chk("§8-3 빈 수주 ID 를 직접 보내도 **서버가 거부**", "error=" in _loc(_r3), _loc(_r3))
    chk("§8-3' 거부 시 연결·감사 모두 불변",
        cnt("project_unit_order_links") == _l0 and len(pu.get_audit()) == _a0)
    chk("§8-3'' 무엇을 해야 하는지 안내", "고르지" in _loc(_r3) or "%EA%B3%A0%EB%A5%B4" in _loc(_r3))

    _r4 = _as(SALES_LEAD, f"/units/{UL1}/order-link",
              {"order_id": str(OLX), "relation_type": "ADDITIONAL"})
    chk("§8-4 **다른 관리번호의 수주** 는 거부", "error=" in _loc(_r4))
    chk("§8-4' 거부 시 연결 불변", cnt("project_unit_order_links") == _l0)

    chk("§8-5 이미 연결된 수주는 **그 호기 목록에서 빠짐**",
        "SO-L-2" in _sel1 and "SO-L-1" not in _sel1, _sel1[:160])
    _r5 = _as(SALES_LEAD, f"/units/{UL1}/order-link",
              {"order_id": str(OL1), "relation_type": "ORIGIN"})
    chk("§8-5' 그래도 직접 보내면 서버가 거부(중복 연결)", "error=" in _loc(_r5))

    _r6 = _as(SALES_LEAD, f"/units/{UL2}/order-link",
              {"order_id": str(OL1), "relation_type": "ORIGIN"})
    chk("§8-6 **한 수주번호를 여러 호기에** 연결 가능(KNK 정상 업무)",
        "success=" in _loc(_r6), _loc(_r6))

    _trm = _re.search(r'<tr[^>]*id="ops-%d"[^>]*>' % UL1, _hl)
    chk("§8-7 작업 패널은 **열기 전 화면에 안 나온다**(hidden)",
        bool(_trm) and " hidden" in _trm.group(0), _trm.group(0) if _trm else "패널 없음")
    chk("§8-7' 입력폼도 전부 접힌 상태로 내려온다",
        _seg1.count('class="ops-form') == _seg1.count("hidden") - 1
        or all(x in _seg1 for x in ('data-op="no"', 'data-op="link"', 'data-op="cancel"')))
    for _op in ("no", "link", "cancel"):
        _fm = _re.search(r'<form[^>]*data-op="%s"[^>]*>' % _op, _seg1)
        chk(f"§8-8 '{_op}' 작업폼이 따로 있고 처음엔 접혀 있다",
            bool(_fm) and "hidden" in _fm.group(0), _fm.group(0)[:120] if _fm else "없음")
    chk("§8-8' 작업 열기 버튼은 호기마다 하나", _hl.count("js-ops-open") >= 2)
    chk("§8-9 작업을 닫으면 입력하던 값을 **지운다**(다음에 잘못 저장되지 않게)",
        "hideForms(uid, true)" in _hl and "i.value = ''" in _hl)
    chk("§8-9' 취소 폼은 일상 작업과 분리·위험 표시",
        "ops-danger" in _hl and "되돌리기 어려운 작업" in _hl)

    _hd = _as(DESIGN, f"/project/{PL}/units").text
    chk("§8-10 권한 없는 사용자에겐 작업 버튼·작업폼 자체가 안 나온다",
        '<tr class="ops-row"' not in _hd and 'class="ops-form' not in _hd
        and "js-ops-open" not in _hd)

    chk("§8-11 확정 호기 정정·취소는 요청자 필수 유지(화면 표시)",
        'name="requester"' in _seg1)

    _a12 = len(pu.get_audit())
    _r12 = _as(SALES_LEAD, f"/units/{UL1}/order-link",
               {"order_id": str(OL2), "relation_type": "ADDITIONAL", "reason": "추가 발주"})
    _h12 = _as(SALES_LEAD, f"/project/{PL}/units").text
    chk("§8-12 연결 성공 → **연결된 수주 칸**에 반영 + 감사 기록",
        "success=" in _loc(_r12) and "SO-L-2" in _h12.split('id="ops-')[0]
        and len(pu.get_audit()) == _a12 + 1, _loc(_r12))
    _seg1b = _h12.split(f'id="ops-{UL1}"')[1].split("</tr>")[0]
    _sel1b = _seg1b.split('name="order_id"')[1].split("</select>")[0] \
        if 'name="order_id"' in _seg1b else "연결 가능한 수주 없음"
    chk("§8-12' 연결한 수주는 그 호기 목록에서 즉시 빠짐",
        "SO-L-2" not in _sel1b, _sel1b[:160])

    _l13, _a13 = cnt("project_unit_order_links"), len(pu.get_audit())
    _r13 = _as(SALES_LEAD, f"/units/{UL1}/order-link",
               {"order_id": str(OL2), "relation_type": "ADDITIONAL"})
    chk("§8-13 오류(중복) 시 업무 데이터·감사 **모두 불변**",
        "error=" in _loc(_r13) and cnt("project_unit_order_links") == _l13
        and len(pu.get_audit()) == _a13)

    chk("§8-14 좁은 화면(폰)에서 라벨이 값 위로 — 가로 스크롤 없이 읽힘",
        "@media (max-width:640px)" in _hl and "flex-direction:column" in _hl)
    chk("§8-14' 표는 자기 영역 안에서만 가로 스크롤", 'class="scroll"' in _hl
        and "overflow-x:auto" in _hl)
    chk("§5.2 연결 전 **무엇을 하는지 사람 말로** 보여준다",
        "linkecho-" in _hl and "로 연결합니다" in _hl)

    # [게이트 UI 판정 §7-5 · 기술영업팀 확인 지적] 잘못된 걸 봤을 때 어디에 요청하는지 화면이 답해야 한다
    chk("§7-5 고칠 수 있는 사람에겐 '작업 열기에서 직접 고치라'고 알려준다",
        'class="fixnote"' in _hl and "작업 열기" in _hl.split('class="fixnote"')[1][:400])
    chk("§7-5' 조회만 하는 사람에겐 **기술영업팀에 요청**하라고 알려준다",
        'class="fixnote"' in _hd and "기술영업팀" in _hd.split('class="fixnote"')[1][:400], "안내 없음")
    chk("§7-5'' 요청할 때 무엇을 알려야 하는지까지(관리번호·호기번호)",
        "관리번호" in _hd.split('class="fixnote"')[1][:600]
        and "호기번호" in _hd.split('class="fixnote"')[1][:600])

    chk("분할·통합 실행 경로 없음(404)",
        client.post(f"/units/{uid_r}/split", data={}, follow_redirects=False).status_code == 404)

    # ══════════ M. 과거 데이터 보정 실행 잠금 (대표 지시 2026-07-26 · 확산 승인 철회) ══════════
    #   허용 범위는 딱 넷: ①실행 차단 ②차단 안내문 ③기존 데이터 불변 ④후보 반영 회귀.
    #   ⭐ 여기서는 환경변수를 **도로 지워** 운영과 똑같은 잠김 상태로 만들고 검증한다.
    print("\n── M. 과거 데이터 보정 실행 잠금 (대표 지시 §잠금 2항) ──")
    os.environ.pop("KNK_ENABLE_UNIT_STATUS_SYNC", None)

    PM = mkproject("999M001")
    OM = mkorder(PM, "SO-M-1")
    LM1 = mkline(OM, "1호기", status="진행중")
    pu.apply_candidate_decisions(PM, [dec(LM1, "new_no")], reason="잠금 시험용 등록", actor_id=13)
    # 등록 뒤에 작업일정표를 '출하'로 바꿔 둔다 → 보정할 거리가 **실제로 있는** 상태에서 잠금을 시험한다
    with db.db_session() as _c:
        _c.execute("UPDATE order_items SET unit_status='출하' WHERE id=?", (LM1,))
    chk("§M-0 보정할 거리가 실제로 있는 상태에서 시험한다(잠금이 '할 일 없음'에 가려지지 않게)",
        pu.status_backfill_preview(PM)["summary"]["change"] == 1,
        str(pu.status_backfill_preview(PM)["summary"]))
    _um = pu.get_units(PM)[0]
    _before = (_um["unit_state"], _um["work_status"])
    _n_units, _n_log, _n_audit = cnt("project_units"), cnt("project_unit_status_backfill"), len(pu.get_audit())

    # ── ① 실행 차단 ──────────────────────────────────────────────────────────
    chk("§M-1 잠금 판정 함수가 '잠김'이라고 답한다", pu.status_sync_locked() is True)
    try:
        pu.status_backfill_apply(PM, reason="화면을 거치지 않고 함수 직접 호출")
        _m2 = False
    except PermissionError:
        _m2 = True
    except Exception as _e:
        _m2 = False
    chk("§M-2 **화면을 거치지 않고 함수를 직접 불러도** 거부된다(가장 깊은 자리)", _m2)

    _rm3 = _as(SALES_LEAD, f"/project/{PM}/units/status-sync/apply",
               {"reason": "보정", "requester": "대표 승인"})
    chk("§M-3 승인권자(기술영업팀장)가 보내도 서버가 **403 으로 거부**",
        _rm3.status_code == 403, f"status={_rm3.status_code}")
    _rm4 = _as(CEO, f"/project/{PM}/units/status-sync/apply",
               {"reason": "보정", "requester": "대표 승인"})
    chk("§M-4 **대표 계정이어도** 잠금이 우선한다(403)", _rm4.status_code == 403,
        f"status={_rm4.status_code}")

    # ── ③ 기존 데이터 변경 없음 ───────────────────────────────────────────────
    _um2 = pu.get_units(PM)[0]
    chk("§M-5 거부된 뒤 호기의 신원·진행상태가 **그대로**",
        (_um2["unit_state"], _um2["work_status"]) == _before, f"{_before} → {(_um2['unit_state'], _um2['work_status'])}")
    chk("§M-6 호기 수·보정이력·감사기록 **셋 다 불변**",
        cnt("project_units") == _n_units
        and cnt("project_unit_status_backfill") == _n_log
        and len(pu.get_audit()) == _n_audit)
    chk("§M-7 아무것도 안 바뀐 실행조차 **감사기록을 남기지 않는다**(거부는 업무가 아님)",
        len(pu.get_audit()) == _n_audit)

    # ── ② 실행 차단 안내문 ────────────────────────────────────────────────────
    _hm = _as(SALES_LEAD, f"/project/{PM}/units/status-sync").text
    chk("§M-8 화면에 **잠김 안내**가 보인다", "🔒" in _hm and "잠겨" in _hm)
    chk("§M-9 안내 문구는 **서버 한 곳**에서 온다(화면과 서버가 다른 말을 하지 않게)",
        pu.STATUS_SYNC_LOCK_MSG.split(".")[0] in _hm, "문구 불일치")
    chk("§M-10 실행 폼(syncForm) **자체가 그려지지 않는다**",
        'id="syncForm"' not in _hm and "status-sync/apply" not in _hm)
    chk("§M-11 **못 하는 일을 시키지 않는다** — '맨 아래에서 반영하세요' 안내가 사라짐",
        "맨 아래에서 반영하세요" not in _hm)
    chk("§M-12 그래도 **대조표·이력은 그대로 보인다**(보기는 막지 않음)",
        "1호기" in _hm and "작업 일정표" in _hm)
    _hm2 = _as(SALES_LEAD, f"/project/{PM}/units").text
    chk("§M-13 **들어가는 버튼 글도** 잠김을 그대로 말한다(눌렀다 잠긴 화면 만나지 않게)",
        "🔒 작업일정표 상태 대조 (보기만)" in _hm2 and "🔄 작업일정표 상태 맞추기" not in _hm2)

    # ── ④ 수주내역 후보 반영 회귀 — 대표가 유지하라고 한 6개 조건 ───────────────
    PM2 = mkproject("999M002")
    OM2 = mkorder(PM2, "SO-M2-1")
    LM2, LM3 = mkline(OM2, "1호기", status="진행중"), mkline(OM2, "2호기", status="진행중")
    _a_before = len(pu.get_audit())
    _rm14 = _as(SALES_LEAD, f"/project/{PM2}/units/candidates/apply",
                {"reason": "신규 프로젝트 호기 등록", "pick": [str(LM2), str(LM3)],
                 f"action_{LM2}": "new_no", f"action_{LM3}": "new_no"})
    _um3 = pu.get_units(PM2)
    chk("§M-14 [회귀] 잠금과 무관하게 **수주내역 후보 반영은 정상 동작**한다",
        "success=" in _loc(_rm14) and len(_um3) == 2, _loc(_rm14))
    chk("§M-15 [조건] 기술영업팀 권한만 — 설계팀은 여전히 차단",
        _blocked(_as(DESIGN, f"/project/{PM2}/units/candidates/apply",
                     {"reason": "권한 없는 시도", "pick": [str(LM2)], f"action_{LM2}": "new_no"})))
    chk("§M-16 [조건] **개발·미확정 상태 허용** — 반영해도 확정되지 않는다",
        all(x["unit_state"] == "PROVISIONAL" for x in _um3),
        str([x["unit_state"] for x in _um3]))
    chk("§M-17 [조건] **과거 프로젝트 자동확정 금지** — 후보 반영이 확정을 만들지 않음",
        cnt("project_units", "project_id=? AND unit_state='CONFIRMED'", (PM2,)) == 0)
    chk("§M-18 [조건] **작업자·시각·변경이력**이 남는다",
        len(pu.get_audit()) > _a_before
        and cnt("project_unit_identifier_history", "project_unit_id IN (?,?)",
                (_um3[0]["id"], _um3[1]["id"])) == 2)
    chk("§M-19 [조건] **관리번호 한 건씩** — 여러 관리번호를 한 번에 받는 경로가 없다",
        client.post("/project/units/candidates/apply", data={}, follow_redirects=False).status_code == 404)

    # ── 잠금 스위치가 배포 전 검사기에 편입됐는가 ────────────────────────────────
    chk("§M-20 새 잠금이 **배포 전 검사기 목록**에 들어가 자동 점검된다",
        "KNK_ENABLE_UNIT_STATUS_SYNC" in db.WP01_LOCK_SWITCHES)

    os.environ["KNK_ENABLE_UNIT_STATUS_SYNC"] = "1"   # 뒤에 다른 시험이 붙어도 로직 검증은 계속되게
except ImportError as e:
    print(f"  SKIP 라우트 테스트 (패키지 없음: {e})")

print(f"\n{'=' * 52}\n결과: PASS {ok} · FAIL {fail}")
sys.exit(0 if fail == 0 else 1)
