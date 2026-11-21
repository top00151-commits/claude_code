# -*- coding: utf-8 -*-
"""z1191z90 시험 — 관리번호 수동발행(엑셀에서 매긴 번호 그대로 넣기) = 기술영업팀 전원 + 대표 지정 3명
   대표 11-21: 「수동발행은 기존 엑셀에서 발행한 관리번호를 그대로 입력해야 할 때 쓰려고 만든 것 ·
               실무자 모두 사용할 때는 기술영업팀 사용자 모두 동일하게 사용할 수 있도록 · 오늘 수정해서 배포」
  §1 판정 함수: 기술영업팀(teams.id=1) 사람 = 가능 · 다른 팀 = 불가 · 대표(총괄 · 사번 5)·지정 3명 = 그대로 가능
  §2 화면(임시 DB · TestClient): 간편 등록 폼 「🔧 수동발행」 칸 · 소모품 등록 「관리번호 수동 지정」 칸 — 기술영업팀은 보이고 다른 팀은 안 보임
  §3 [검증] 단추 서버(/api/mgmt-code/check): 기술영업팀 200 · 다른 팀 403
"""
import contextlib
import io
import os
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z90-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


def setup_db():
    tmp = tempfile.mkdtemp(prefix="knk_z1191z90_")
    real = D.DB_PATH
    D.DB_PATH = os.path.join(tmp, "t.db")
    assert D.DB_PATH != real
    with contextlib.redirect_stdout(io.StringIO()):
        D.init_db()
    with D.db_session() as c:
        have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
        for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                         ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                         ("must_change_pw", "INTEGER DEFAULT 0")]:
            if col not in have:
                c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
        tcols = {r[1] for r in c.execute("PRAGMA table_info(teams)")}
        for tid, code, nm in ((1, "01", "기술영업팀"), (2, "02", "가상설계팀"), (15, "00", "총괄")):
            if not c.execute("SELECT 1 FROM teams WHERE id=?", (tid,)).fetchone():
                if "code" in tcols:
                    c.execute("INSERT INTO teams (id, code, name) VALUES (?,?,?)", (tid, code, nm))
                else:
                    c.execute("INSERT INTO teams (id, name) VALUES (?,?)", (tid, nm))
        users = {}
        # 모두 매출 등록 권한(can_use_sales=1)은 같게 — 팀만 다르게 해서 팀 판정만 본다
        for key, nm, emp, team, role in (("sales", "가상영업", "Z901", 1, "member"),
                                         ("other", "가상설계", "Z902", 2, "member"),
                                         ("ceo", "김정락", "5", 15, "ceo")):
            c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                      "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                      "VALUES (?, ?, ?, ?, 'sso_only_no_local_password', 1, 1, ?, 1, 1, 1, 1)", (nm, role, emp, emp, team))
            row = dict(c.execute("SELECT u.*, t.name AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id "
                                 "WHERE u.employee_no=?", (emp,)).fetchone())
            users[key] = row
    return users


def main():
    U = setup_db()
    import app.main as M                                    # noqa: E402
    from fastapi.testclient import TestClient              # noqa: E402

    print("§1 판정 함수")
    f = M._can_manual_mgmt
    check("기술영업팀(팀 1) 일반 직원 = 가능", f(U["sales"]) is True)
    check("다른 팀 직원(매출 등록 권한 있어도) = 불가", f(U["other"]) is False)
    check("대표(총괄 · 사번 5) = 그대로 가능", f(U["ceo"]) is True)
    check("지정 3명(사번 67·306) = 그대로 가능", f({"employee_no": "67", "team_id": 1}) and f({"employee_no": "306", "team_id": 9}))
    check("실제 기술영업팀 4명(이해림·이현·오경환·배승진 · 팀 1) = 가능",
          all(f({"employee_no": e, "team_id": 1, "role": "member"}) for e in ("111", "252", "283", "343")))
    check("팀 번호 없음·이상한 값 = 불가(오류 없이)", f({"employee_no": "999"}) is False and f({"team_id": "x"}) is False and f(None) is False)

    S = {"user": None}
    M.get_user = lambda request: S["user"]
    cl = TestClient(M.app)

    print("§2 화면")
    for key, want in (("sales", True), ("other", False), ("ceo", True)):
        S["user"] = U[key]
        r = cl.get("/projects/quick?biz_div=T")
        h = r.text
        check("간편 등록 폼 %s — 「🔧 수동발행」 칸 %s" % (U[key]["name"], "보임" if want else "안 보임"),
              r.status_code == 200 and (('id="qManualChk"' in h) == want), (r.status_code, 'id="qManualChk"' in h))
    for key, want in (("sales", True), ("other", False)):
        S["user"] = U[key]
        r = cl.get("/consumables/new")
        h = r.text
        has = 'name="manual_mgmt_code"' in h
        check("소모품 등록 %s — 관리번호 수동 지정 칸 %s" % (U[key]["name"], "보임" if want else "안 보임"),
              r.status_code == 200 and has == want, (r.status_code, has))

    print("§3 [검증] 단추 서버")
    for key, want in (("sales", 200), ("other", 403), ("ceo", 200)):
        S["user"] = U[key]
        r = cl.get("/api/mgmt-code/check", params={"code": "901T2611", "biz_div": "T", "ptype": "NEW_EQUIP"})
        check("%s → %d" % (U[key]["name"], want), r.status_code == want, (r.status_code, r.text[:120]))
    S["user"] = U["sales"]
    j = cl.get("/api/mgmt-code/check", params={"code": "901T2611", "biz_div": "T", "ptype": "NEW_EQUIP"}).json()
    check("기술영업팀 직원 검증 결과 = 사용 가능(빈 번호)", j.get("ok") is True and j.get("available") is True, j)
    j2 = cl.get("/api/mgmt-code/check", params={"code": "901M2611", "biz_div": "T", "ptype": "NEW_EQUIP"}).json()
    check("사업부 글자가 다르면 「사용 불가」(검증 규칙은 그대로)", j2.get("available") is False, j2)

    print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
