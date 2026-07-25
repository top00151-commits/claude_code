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

print("\n── B. 라우트 수준 (실 HTTP · 인가 실로직) ──")
try:
    from fastapi.testclient import TestClient
    import app.main as m
    m.get_user = lambda req: {"id": 503, "name": "대표", "role": "ceo", "team_id": 11}
    client = TestClient(m.app)
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
    chk("additive · order_items 여전히 불변", cnt("order_items") == OI_BEFORE)
except ImportError as e:
    print(f"  SKIP 라우트 테스트 (패키지 없음: {e})")

print(f"\n{'=' * 52}\n결과: PASS {ok} · FAIL {fail}")
sys.exit(0 if fail == 0 else 1)
