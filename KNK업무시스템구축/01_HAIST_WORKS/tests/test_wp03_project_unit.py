# -*- coding: utf-8 -*-
"""WP-03 프로젝트 호기·일련번호 (Project Unit·Serial) — 정식 검증 (ERP V1 · RS-01)

실행:  01_HAIST_WORKS 루트에서
    python tests/test_wp03_project_unit.py

- 임시 DB(운영과 동일 init_db 스키마 + WP-03 마이그레이션) — 운영 무관.
- A부: 함수 수준 — 씨앗(호기 수 대조)·멱등·가드(RS-01 차단조건 4종)·additive(order_items 불변).
- B부: 라우트 수준 실HTTP(TestClient) — 인증(get_user)만 대체, 인가(can_*)는 실로직.
  필요 패키지: fastapi + httpx (개발 PC 기준).
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # 01_HAIST_WORKS
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # 템플릿·정적 상대경로 안전

from app import database as db  # noqa: E402

db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="wp03_"), "test.db")
db.init_db()
from app.migrations.m_z1053_project_unit import migrate as _mig  # noqa: E402
print("마이그레이션:", _mig(db.DB_PATH))
# 테스트 스키마 보강 — LIVE projects 에 존재하는 법인 컬럼(§10-6 법인 판정 검증용)
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


# ═══════════ 시드: 프로젝트 1 · 수주 1 · 호기 라인 5(1~5호기) + 비호기 2(부속·소모품) ═══════════
with db.db_session() as c:
    c.execute("INSERT INTO projects (mgmt_code, name, status) VALUES ('999T2601','WP03 시범','진행중')")
    PID = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO orders (order_no, project_id, status) VALUES ('SO-WP03-1', ?, 'CONFIRMED')", (PID,))
    OID = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    for i in range(1, 6):
        c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label) "
                  "VALUES (?,1,0,0,?)", (OID, f"{i}호기"))
    c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label) "
              "VALUES (?,3,0,0,'예비품 세트')", (OID,))
    c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label) "
              "VALUES (?,5,0,0,'소모품 키트')", (OID,))

OI_BEFORE = cnt("order_items")   # additive 대조 기준

print("\n── A. 함수 수준 (씨앗·대조·멱등·가드·additive) ──")
chk("호기 라인 5 인식(비호기 제외)", pu.count_hogi_lines(PID) == 5, f"={pu.count_hogi_lines(PID)}")
r = pu.seed_units_from_orders(PID)
chk("씨앗 5대 생성", r["created"] == 5 and r["target_lines"] == 5, str(r))
chk("호기 수 대조 일치(5=5)", len(pu.get_units(PID)) == 5)
r2 = pu.seed_units_from_orders(PID)
chk("멱등 재씨앗(0 생성·안 늘어남)", r2["created"] == 0 and len(pu.get_units(PID)) == 5, str(r2))
chk("additive · order_items 불변", cnt("order_items") == OI_BEFORE, f"{cnt('order_items')} vs {OI_BEFORE}")

units = pu.get_units(PID)
try:
    pu.create_unit(PID, units[0]["unit_no"]); chk("① 제작번호 중복 차단", False)
except ValueError:
    chk("① 제작번호 중복 차단", True)
try:
    pu.create_unit(9999999, "1호기"); chk("② 프로젝트 없는 호기 차단", False)
except ValueError:
    chk("② 프로젝트 없는 호기 차단", True)
pu.link_serial(units[0]["id"], "SN-KOR-1")
chk("일련번호 연결됨", (pu.get_unit(units[0]["id"])["serials"] or [{}])[0].get("serial_no") == "SN-KOR-1")
try:
    pu.link_serial(units[1]["id"], "SN-KOR-1"); chk("③ 일련번호 중복(법인 내) 차단", False)
except ValueError:
    chk("③ 일련번호 중복(법인 내) 차단", True)
try:
    pu.delete_unit(units[0]["id"]); chk("④ 이력 있는 호기 삭제 차단", False)
except ValueError:
    chk("④ 이력 있는 호기 삭제 차단", True)
clean = [u for u in pu.get_units(PID) if u["serial_count"] == 0 and u["status"] == "draft"]
before_del = len(pu.get_units(PID))
pu.delete_unit(clean[0]["id"])
chk("④' 깨끗한 초안 삭제 허용", len(pu.get_units(PID)) == before_del - 1)

final = pu.get_units(PID)
chk("RS-01 · 관리번호에서 호기·일련번호 조회", len(final) >= 1 and any(u["serial_no"] for u in final))

print("\n── C. 게이트 §10 추가 시나리오 (12종) ──")
with db.db_session() as c:
    c.execute("INSERT INTO projects (mgmt_code, name, status) VALUES ('999T2602','WP03 게이트','진행중')")
    P2 = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO orders (order_no, project_id, status) VALUES ('SO-G-1', ?, 'CONFIRMED')", (P2,))
    O2 = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    for i in range(1, 4):
        c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label) VALUES (?,1,0,0,?)", (O2, f"{i}호기"))
    c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label) VALUES (?,3,0,0,'9호기')", (O2,))

# §10-1 정식 호기 qty!=1 → 전체 씨앗 차단(부분 생성 0)
try:
    pu.seed_units_from_orders(P2); chk("§10-1 qty!=1 전체 씨앗 차단", False)
except ValueError:
    chk("§10-1 qty!=1 전체 씨앗 차단", cnt("project_units", "project_id=?", (P2,)) == 0)
with db.db_session() as c:
    c.execute("DELETE FROM order_items WHERE order_id=? AND unit_label='9호기'", (O2,))
chk("§10-1' 위반 제거 후 정상 씨앗 3대", pu.seed_units_from_orders(P2)["created"] == 3)
gunits = pu.get_units(P2)

# §10-2 한 Unit 활성 Serial 2개 DB 차단
pu.link_serial(gunits[0]["id"], "G-SN-1")
try:
    with db.db_session() as c:
        c.execute("INSERT INTO equipment_serials (project_unit_id, serial_no, entity, active) VALUES (?,?, 'KOR', 1)", (gunits[0]["id"], "G-SN-2"))
    chk("§10-2 한 호기 활성 일련 2개 DB 차단", False)
except Exception:
    chk("§10-2 한 호기 활성 일련 2개 DB 차단", True)

# §10-3 비활성 Serial 다른 Unit 재사용 차단(영구 유일)
pu.link_serial(gunits[0]["id"], "G-SN-3", reason="교체시험")   # G-SN-1 비활성
try:
    pu.link_serial(gunits[1]["id"], "G-SN-1"); chk("§10-3 비활성 일련 재사용 차단", False)
except ValueError:
    chk("§10-3 비활성 일련 재사용 차단(영구 유일)", True)

# §10-4 교체 종료메타 + 이전↔신규 연결
hist = pu.get_serial_history(gunits[0]["id"])
oldrow = [h for h in hist if not h["active"]][0]
newrow = [h for h in hist if h["active"]][0]
chk("§10-4 교체 종료메타(사유·시각)", bool(oldrow["deactivation_reason"]) and bool(oldrow["deactivated_at"]))
chk("§10-4 이전↔신규 연결(supersedes)", newrow["supersedes_serial_id"] == oldrow["id"])

# §10-5 동일 Serial 동일 Unit 재입력 무동작
b5 = len(pu.get_serial_history(gunits[0]["id"]))
pu.link_serial(gunits[0]["id"], "G-SN-3")
chk("§10-5 동일 일련 재입력 무동작(이력 안 늘어남)", len(pu.get_serial_history(gunits[0]["id"])) == b5)

# §10-6 법인 미지정→KOR / 충돌→중단
chk("§10-6 법인 미지정 → KOR", gunits[0]["entity"] == "KOR")
with db.db_session() as c:
    c.execute("INSERT INTO projects (mgmt_code, name, status, po_entity, ship_entity) VALUES ('999X','충돌','진행중','KOR','VN')")
    PX = c.execute("SELECT last_insert_rowid()").fetchone()[0]
try:
    pu.create_unit(PX, "1호기"); chk("§10-6 법인 충돌 → 중단", False)
except ValueError:
    chk("§10-6 법인 충돌 → 중단", True)

# §10-7 동시 조건 활성 Serial (DB 유일이 2개 활성 방지 — §10-2 와 동일 계약 재확인)
chk("§10-7 활성 일련 유일(호기당 1) 계약", cnt("equipment_serials", "project_unit_id=? AND active=1", (gunits[0]["id"],)) == 1)

# §10-8 수동 Unit + 미씨앗 라인 → unseeded 정확
with db.db_session() as c:
    c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label) VALUES (?,1,0,0,'8호기')", (O2,))
pu.create_unit(P2, "100호기")
chk("§10-8 미씨앗 라인 카운트 정확(=1)", pu.count_unseeded_hogi_lines(P2) == 1)

# §10-9 제작번호 충돌 vs 이미 씨앗됨 구분
pu.create_unit(P2, "8호기")
s9 = pu.seed_units_from_orders(P2)
chk("§10-9 이미 씨앗됨/제작번호 충돌 분리", s9["already_seeded"] == 3 and "8호기" in s9["unit_no_conflicts"])

# §10-10 WP-04 참조 생성 후 삭제 차단(동적 전참조 스캔)
with db.db_session() as c:
    c.execute("CREATE TABLE IF NOT EXISTS _wp04_fake (id INTEGER PRIMARY KEY, project_unit_id INTEGER, FOREIGN KEY(project_unit_id) REFERENCES project_units(id))")
draftu = [u for u in pu.get_units(P2) if u["status"] == "draft" and u["serial_count"] == 0][0]
with db.db_session() as c:
    c.execute("INSERT INTO _wp04_fake (project_unit_id) VALUES (?)", (draftu["id"],))
try:
    pu.delete_unit(draftu["id"]); chk("§10-10 WP-04 참조 시 삭제 차단(동적)", False)
except ValueError:
    chk("§10-10 WP-04 참조 시 삭제 차단(동적)", True)
with db.db_session() as c:
    c.execute("DELETE FROM _wp04_fake"); c.execute("DROP TABLE _wp04_fake")

# §10-11 order_item 삭제 후 원본 스냅샷 보존
su = [u for u in pu.get_units(P2) if u["seed_order_item_id"]][0]
snap_no, snap_lbl = su["seed_order_no"], su["seed_unit_label"]
with db.db_session() as c:
    c.execute("DELETE FROM order_items WHERE id=?", (su["seed_order_item_id"],))
af = pu.get_unit(su["id"])
chk("§10-11 order_item 삭제 후 원본추적 보존", af["seed_unit_label"] == snap_lbl and af["seed_order_no"] == snap_no and af["seed_order_item_id"] is None)

print("\n── B. 라우트 수준 (실 HTTP · 인가 실로직) ──")
try:
    from fastapi.testclient import TestClient
    import app.main as m
    m.get_user = lambda req: {"id": 503, "name": "대표", "role": "ceo", "team_id": 11}
    client = TestClient(m.app)
    OI_B = cnt("order_items")   # Part B(라우트) 시작 기준선 — Part C 가 셋업으로 order_items 를 바꿨으므로 재캡처
    rp = client.get(f"/project/{PID}/units")
    chk("GET 호기 페이지 200", rp.status_code == 200, str(rp.status_code))
    chk("페이지에 호기·일련번호 표시", ("호기" in rp.text and "일련번호" in rp.text))
    rs = client.post(f"/project/{PID}/units/seed", follow_redirects=False)
    chk("POST 씨앗 303", rs.status_code == 303, str(rs.status_code))
    rc = client.post(f"/project/{PID}/units/create", data={"unit_no": "99호기"}, follow_redirects=False)
    chk("POST 호기 추가 303", rc.status_code == 303, str(rc.status_code))
    chk("새 호기(99호기) 반영", any(u["unit_no"] == "99호기" for u in pu.get_units(PID)))
    # 권한 없는 사용자 → 차단
    m.get_user = lambda req: {"id": 999, "name": "무권한", "role": "member", "team_id": 99}
    rn = client.post(f"/project/{PID}/units/create", data={"unit_no": "X"}, follow_redirects=False)
    chk("권한 없음 → /home 리다이렉트",
        rn.status_code == 303 and "/home" in rn.headers.get("location", ""))
    chk("additive · 라우트 조작이 order_items 불변", cnt("order_items") == OI_B)
    # §10-12 권한 매트릭스 (영업·구매·제조·관리자)
    def _create_as(role, team, uno):
        m.get_user = lambda req: {"id": 1, "role": role, "team_id": team}
        return client.post(f"/project/{PID}/units/create", data={"unit_no": uno}, follow_redirects=False)
    def _allowed(rr):
        return rr.status_code == 303 and "/home" not in rr.headers.get("location", "")
    chk("§10-12 ceo 생성 허용", _allowed(_create_as("ceo", 11, "PA호기")))
    chk("§10-12 구매팀(10) 생성 허용", _allowed(_create_as("member", 10, "PB호기")))
    chk("§10-12 제조팀(7) 생성 허용", _allowed(_create_as("member", 7, "PC호기")))
    r_sales = _create_as("member", 1, "PD호기")   # 영업팀원(쓰기 권한 없음)
    chk("§10-12 영업팀원(무쓰기) 생성 차단",
        r_sales.status_code == 303 and "/home" in r_sales.headers.get("location", ""))
    m.get_user = lambda req: {"id": 9, "role": "member", "team_id": 99}
    r_view = client.get(f"/project/{PID}/units", follow_redirects=False)
    chk("§10-12 무권한 조회 차단", r_view.status_code == 303 and "/home" in r_view.headers.get("location", ""))
except ImportError as e:
    print(f"  SKIP 라우트 테스트 (패키지 없음: {e})")

print(f"\n{'=' * 52}\n결과: PASS {ok} · FAIL {fail}")
sys.exit(0 if fail == 0 else 1)
