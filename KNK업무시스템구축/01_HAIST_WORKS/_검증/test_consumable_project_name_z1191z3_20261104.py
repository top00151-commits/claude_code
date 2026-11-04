# -*- coding: utf-8 -*-
"""z1191z3 시험 — 소모품 프로젝트명(TSP · PBA · SENSOR 고르기 · 직접 입력) · 비우면 지금처럼 「소모품」
   이새롬 프로 요청(2026-11-04) 「소모품에도 TSP,PBA,SENSOR 프로젝트 생성 부탁드립니다.」 → 대표 「진행해.
   확인 부탁 사항에는 2번으로 진행.고를수있게하고 또 직접 써 넣을수도 있게..」
  §1 이름 다듬기(pba → PBA · 「소모품」 = 빈칸 · 40자) · 표시 이름(비면 「소모품」)
  §2 서버(임시 DB · TestClient): 칸 생김 · 직접 등록에 프로젝트명 · 상세 한 칸 저장(PBA 맞춤 · 변경 이력) · 💾 수정 반영 ·
     상세 화면 칸·고르기 목록(직접 쓴 이름도) · 검색 · 프로젝트 목록 · 작업일정표(화면 · 엑셀 저장 경로) · 비운 건 「소모품」
  §3 일괄 양식: K4 프로젝트명(고르기 · 목록 밖 글자도 허용) · 올리기 → 미리보기 → 확정에 저장
  §4 원문: 기존 「소모품」 고정 3곳이 모두 표시 함수로 · 등록 화면 칸
"""
import contextlib
import io
import json
import os
import re
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z3-test-only-not-a-real-key"   # 시험용 가짜 값

import openpyxl                                            # noqa: E402
import app.database as D                                   # noqa: E402
from app import consumables as CO                          # noqa: E402

OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


print("§1 이름 다듬기 · 표시 이름")
check("고를 이름은 대소문자 맞춤(pba → PBA · ' Sensor ' → SENSOR · tsp → TSP)",
      CO.norm_project_name("pba") == "PBA" and CO.norm_project_name(" Sensor ") == "SENSOR" and CO.norm_project_name("tsp") == "TSP")
check("직접 쓴 이름은 그대로(겹친 빈칸만 정리) · 40자까지 · 「소모품」·빈칸·None = 빈칸",
      CO.norm_project_name("NE1  PE 지그") == "NE1 PE 지그" and len(CO.norm_project_name("가" * 60)) == 40
      and CO.norm_project_name("소모품") == "" and CO.norm_project_name("") == "" and CO.norm_project_name(None) == "")
check("표시 이름: 적힌 이름 · 비면 「소모품」", CO.project_label({"project_name": "PBA"}) == "PBA"
      and CO.project_label({"project_name": ""}) == "소모품" and CO.project_label({}) == "소모품" and CO.project_label(None) == "소모품")
check("고를 이름 = TSP · PBA · SENSOR · 상세 저장 허용 목록에 프로젝트명", CO.PROJECT_NAME_CHOICES == ("TSP", "PBA", "SENSOR")
      and CO._ORDER_FIELD_LABELS.get("project_name") == "프로젝트명")

print("§2 서버 — 임시 DB · TestClient")
TMP = tempfile.mkdtemp(prefix="knk_z1191z3_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, "
                 "can_view_logistics, can_use_logistics) VALUES ('가상영업', 'admin', 'Z931', 'Z931', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    U = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z931'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('(주)가상성수')")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(consumable_orders)")}
check("init_db → consumable_orders.project_name 칸 생김", "project_name" in cols)

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: U
cl = TestClient(M.app, follow_redirects=False)


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def co_row(co_id):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM consumable_orders WHERE id=?", (co_id,)).fetchone())


def direct(pj, od="2026-11-04"):
    r = q(cl.post, "/consumables/create-direct", data={"mode": "json", "biz_div": "T", "customer_name": "(주)가상성수",
                                                         "order_date": od, "due_date": od, "currency": "KRW", "project_name": pj})
    return r.json().get("co_id") if r.status_code == 200 else None


A = direct("pba")
B = direct("")
Cc = direct("NE1 PE 지그")
check("직접 등록: 프로젝트명 pba → PBA 저장 · 비우면 빈칸 · 직접 쓴 이름 그대로",
      A and co_row(A)["project_name"] == "PBA" and B and not co_row(B)["project_name"] and Cc and co_row(Cc)["project_name"] == "NE1 PE 지그",
      (A, B, Cc))
r = q(cl.post, "/consumables/%d/edit-field" % B, json={"field": "project_name", "value": "sensor"})
check("상세 한 칸 저장(자동저장): sensor → SENSOR · 돌려준 값도 SENSOR", r.status_code == 200 and r.json().get("value") == "SENSOR"
      and co_row(B)["project_name"] == "SENSOR", r.text[:200])
with D.db_session() as c:
    hist = [dict(x) for x in c.execute("SELECT * FROM consumable_order_history WHERE co_id=?", (B,))] \
        if "consumable_order_history" in {t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'")} else []
hl = CO.co_history_list(B)
check("변경 이력에 「프로젝트명」 (빈칸 → SENSOR)", any("프로젝트명" in json.dumps(h, ensure_ascii=False) and "SENSOR" in json.dumps(h, ensure_ascii=False)
                                               for h in hl), hl[:3])
r = q(cl.post, "/consumables/%d/edit-field" % B, json={"field": "project_name", "value": "소모품"})
check("「소모품」이라고 쓰면 빈칸으로(기본값) — 화면은 「소모품」", r.status_code == 200 and r.json().get("value") == "" and not co_row(B)["project_name"])
r = q(cl.post, "/consumables/%d/save-all" % B, json={"header": {"project_name": "tsp"}, "lines": []})
check("💾 수정 반영(save-all)에서도 저장 · tsp → TSP", r.status_code == 200 and co_row(B)["project_name"] == "TSP", (r.status_code, r.text[:160]))
html = q(cl.get, "/consumables/%d" % A).text
check("상세 화면: 프로젝트명 칸(data-field=project_name · 값 PBA) · 고르기 목록 TSP·PBA·SENSOR + 직접 쓴 이름",
      'data-field="project_name"' in html and 'value="PBA"' in html and 'id="coProjList"' in html
      and all('<option value="%s"></option>' % n in html for n in ("TSP", "PBA", "SENSOR", "NE1 PE 지그")), html.count("coProjList"))
nf = q(cl.get, "/consumables/new").text
check("등록 화면: 프로젝트명 칸(name=project_name · 고르기 목록)", 'name="project_name"' in nf and 'id="coProjListNew"' in nf)
check("검색: PBA 로 찾으면 그 소모품", any(x["id"] == A for x in CO.co_list(q="PBA")) and not any(x["id"] == Cc for x in CO.co_list(q="PBA")))
D2 = direct("")                                             # 아무것도 안 고른 건 → 「소모품」
pl = q(cl.get, "/projects?project_type=CONSUMABLE").text
check("프로젝트 목록: 소모품 줄 이름 = PBA · NE1 PE 지그 · 비운 건 「소모품」", "PBA" in pl and "NE1 PE 지그" in pl and "소모품" in pl,
      (pl.count("PBA"), pl.count("NE1 PE 지그")))
res = q(M.build_schedule_board_rows, U, 2026, 11)
names = {r.get("ref_id"): r.get("name") for r in (res.get("rows") or []) if r.get("ref_id") in (A, B, Cc, D2)}
check("작업일정표 줄(엑셀 저장 경로): PBA · TSP · NE1 PE 지그 · 비운 건 「소모품」",
      names.get(A) == "PBA" and names.get(B) == "TSP" and names.get(Cc) == "NE1 PE 지그" and names.get(D2) == "소모품", names)
# 작업일정표 화면은 매출 열람 권한자만(z843) — 시험 계정 = 센터 4칸 켠 관리자(z1191g)
rs = q(cl.get, "/sales/schedule?ym=2026-11")
sb = rs.text
check("작업일정표 화면에도 PBA · TSP", rs.status_code == 200 and "PBA" in sb and "TSP" in sb, (rs.status_code, sb.count("PBA"), sb.count("TSP")))

print("§3 일괄 양식")
buf = CO.build_co_bulk_template_buf()
wb = openpyxl.load_workbook(buf)
ws = wb["소모품"]
dvs = [d for d in ws.data_validations.dataValidation if "K4" in str(d.sqref)]
check("양식 J4 「프로젝트명」 · K4 고르기(TSP,PBA,SENSOR) · 목록 밖 글자도 허용(showErrorMessage 꺼짐) · 안내 시트",
      ws["J4"].value == "프로젝트명" and dvs and dvs[0].formula1 == '"TSP,PBA,SENSOR"' and not dvs[0].showErrorMessage
      and any((r[0].value or "").startswith("프로젝트명") for r in wb["작성안내"].iter_rows()), (ws["J4"].value, [(d.formula1, d.showErrorMessage) for d in dvs]))
ws["B4"] = "(주)가상성수"
ws["B8"] = "2026-11-04"
ws["K4"] = "sensor"
for rr in (12, 13):
    for ci in range(1, 17):
        ws.cell(rr, ci).value = None
ws["A12"], ws["G12"], ws["H12"], ws["I12"] = "GRIP PAD", 2, "EA", 1000
p = os.path.join(TMP, "bulk.xlsx")
wb.save(p)
with contextlib.redirect_stdout(io.StringIO()):
    parsed = CO.parse_co_bulk_xlsx(p)
o0 = (parsed.get("orders") or [{}])[0]
check("일괄 읽기: K4 sensor → SENSOR", parsed.get("ok") and o0.get("project_name") == "SENSOR", (parsed.get("error"), o0.get("project_name")))
with open(p, "rb") as fh:
    pv = q(cl.post, "/consumables/import-bulk", files={"file": ("bulk.xlsx", fh.read())}).json()
cf = q(cl.post, "/consumables/import-bulk-confirm", json={"orders": pv.get("orders") or [], "token": pv.get("token") or ""}).json()
cno = (cf.get("created") or [{}])[0].get("co_no")
with D.db_session() as c:
    rw = c.execute("SELECT project_name FROM consumable_orders WHERE co_no=?", (cno,)).fetchone()
check("일괄 확정: 프로젝트명 SENSOR 저장", cf.get("ok") and rw and rw[0] == "SENSOR", (cf.get("created"), cf.get("failed"), rw and rw[0]))

print("§4 원문")
src = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("「소모품」 고정 3곳이 모두 표시 함수로(프로젝트 목록 · 작업일정표 둘)",
      src.count("_co_mod.project_label(cr)") == 4 and '"name": "소모품",' not in src and '"project_name": "소모품",' not in src)
check("v5H226z931 설명은 남기고 바뀐 까닭 한 줄", "v5H226z931 (대표 지시): 소모품 행 프로젝트명" in src and "z1191z3 (대표 2026-11-04): 프로젝트명 = 소모품에 적은 이름" in src)

print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
