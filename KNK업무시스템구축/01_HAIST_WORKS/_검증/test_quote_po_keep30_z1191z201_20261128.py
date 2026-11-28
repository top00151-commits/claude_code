# -*- coding: utf-8 -*-
"""z1191z201 시험 — 견적서·고객 발주서 「빼기」 = 목록에서 바로 빠짐 · 파일·줄은 30일 보관 뒤 완전 삭제 · 안내문 · 30일 안 되살리기
대표 2026-11-28 원문: 「보관했다가 삭제해.. 삭제할때 안내문도 붙이고..」 → (되살리기) 「넣어」
  §1 빼기 → 줄·파일 남음(removed_at·누가) · 결과 첫 줄 「✅ 완료 — 「이름」을 뺐습니다. 30일 보관 뒤(○월 ○일) 완전히 지워집니다.」 · 이력
  §2 뺀 것은 모든 곳에서 빠짐: 상세 견적서 줄·수주 카드·수주별 표 · 견적 관리 · 프로젝트 목록 📎 · 수주 상세 · 발주서 보기·파일·견적서 보기 404 · zip · 엑셀 · 수주 칸 확인
  §3 안내문(묻는 창): 이름 · 이어진 수주 · 완전 삭제 날(실제 계산) · 「목록에서 바로 빠집니다」 · 「30일 동안 보관」 · 「뺀 파일」에서 되살리기 · ✕ 닫기
  §4 「30일 안에 뺀 파일 N건 · 되살리기」(접힘) · 되살리기 → 목록·합계 다시 보임 · 이력 「되살림」 · 이미 살아 있음 = ok · 권한 없는 계정 403
  §5 밤 정리: 30일 안 된 것 남음 · 30일 지난 것 지움(파일+줄 · 이력 시스템) · 같은 파일을 쓰는 다른 줄 있으면 남김 · 월 02:00~07:30·평일 08:50~09:30 안 함
      · 30일 지난 것 되살리기 404(지우기 전·후 모두)
  §6 완전 삭제 날 계산(22:30 넘으면 다음 날) · 상수 한 곳(30)
  §7 권한 그대로: 남의 것(기술영업팀 아님) 빼기 403 · 자기가 올린 것은 뺌
  §8 그려진 화면 스크립트 문법(node)
  임시 DB · TestClient · 운영 아님"""
import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, date

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z201-test-only-not-a-real-key"   # 시험용 가짜 값
os.environ["KNK_RUN_KEEP30"] = "0"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z201_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        if "code" in tcols:
            conn.execute("INSERT INTO teams (id, code, name) VALUES (1, '01', '기술영업팀')")
        else:
            conn.execute("INSERT INTO teams (id, name) VALUES (1, '기술영업팀')")
    else:
        conn.execute("UPDATE teams SET name='기술영업팀' WHERE id=1")
    if "code" in tcols:
        conn.execute("INSERT INTO teams (code, name) VALUES ('Z2', '가상관리팀')")
    else:
        conn.execute("INSERT INTO teams (name) VALUES ('가상관리팀')")
    T2 = conn.execute("SELECT id FROM teams WHERE name='가상관리팀'").fetchone()[0]
    ins = ("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales, "
           "can_view_logistics, can_use_logistics) VALUES (?, ?, ?, ?, 'sso_only_no_local_password', 1, 1, ?, 1, 1, 1, 1)")
    conn.execute(ins, ("가상영업", "member", "Z201", "Z201", 1))          # 기술영업팀 — 남의 것도 뺌
    conn.execute(ins, ("가상관리", "admin", "Z202", "Z202", T2))          # 관리자지만 기술영업팀 아님 — 남의 것 못 뺌(대표 11-18 「견적은 관리자는 빼자」)
    U1 = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z201'").fetchone())
    U2 = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z202'").fetchone())
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', ?)", (T2,))
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객병')")
    CU = conn.execute("SELECT id FROM customers WHERE name='가상고객병'").fetchone()[0]
    T0 = date.today().isoformat()
    conn.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, currency, order_amount, order_date, due_date, stage, sales_name) "
                 "VALUES ('971M2811', '보관 시험', ?, '가상고객병', 'KRW', 0, ?, ?, '수주확정', '가상영업')", (CU, T0, T0))
    P = conn.execute("SELECT id FROM projects WHERE mgmt_code='971M2811'").fetchone()[0]

    def so(no, amt, label):
        conn.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, total_amount, order_date, due_date, status) "
                     "VALUES (?, ?, ?, 'KRW', ?, ?, ?, 'CONFIRMED')", (P, no, CU, amt, T0, T0))
        oid = conn.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
        conn.execute("INSERT INTO order_items (order_id, amount, unit_price, unit_label) VALUES (?, ?, ?, ?)", (oid, amt, amt, label))
        return oid

    O1 = so("Y-261128-1", 1000000, "1호기")
    O2 = so("Y-261128-2", 2000000, "2호기")

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

WHO = {"u": U1}
M.get_user = lambda request: WHO["u"]
M._qr61.read_quote = lambda raw, name, pw="": {"ok": True, "fields": {"amount": 1000000, "currency": "KRW"}, "warnings": []}
cl = TestClient(M.app, follow_redirects=False)
XL = b"PK\x03\x04" + b"0" * 64
PDF = b"%PDF-1.4 test"
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:400]))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def rows(sql, *a):
    with D.db_session() as c:
        return [tuple(r) for r in c.execute(sql, a).fetchall()]


def kst():
    return datetime.utcnow() + timedelta(hours=9)


def md(d):
    return "%d월 %d일" % (d.month, d.day)


def strip_js(h):
    h = re.sub(r"<script\b.*?</script>", "", h, flags=re.S)
    h = re.sub(r"<style\b.*?</style>", "", h, flags=re.S)
    return re.sub(r"<!--.*?-->", "", h, flags=re.S)


def upq(oid, name):
    j = q(cl.post, "/api/project-quote/attach/%d" % P, data={"order_id": str(oid)}, files={"file": (name, XL, "application/vnd.ms-excel")}).json()
    assert j.get("ok"), j
    return j["fid"]


def upp(oid, name):
    j = q(cl.post, "/api/customer-po/upload", data={"pid": P, "order_id": oid}, files={"file": (name, PDF, "application/pdf")}).json()
    assert j.get("ok"), j
    return j["fid"]


QA = upq(O1, "견적_보관_가.xlsx")      # 뺄 것
QB = upq(O1, "견적_보관_나.xlsx")      # 남길 것
QC = upq(O2, "견적_2호기_하나.xlsx")   # 2호기 하나뿐 → 빼면 2호기 견적 없음
PA = upp(O1, "발주서_보관_가.pdf")
PB = upp(O1, "발주서_보관_나.pdf")
WHO["u"] = U2
QM = upq(O2, "견적_관리팀이_올림.xlsx")   # 관리팀(기술영업팀 아님) 본인이 올린 것
WHO["u"] = U1
st0 = {r[0]: r[1] for r in rows("SELECT id, stored FROM project_quote_files")}
sp0 = {r[0]: r[1] for r in rows("SELECT id, stored FROM project_po_files")}
hd0 = q(cl.get, "/project/%d" % P).text
d0 = M._z150_one(P)

print("§1 빼기 = 표시만 · 줄·파일 남음 · 결과 첫 줄")
exp_day = md((kst() + timedelta(days=30) + (timedelta(days=1) if (kst() + timedelta(days=30)).strftime("%H:%M") >= "22:30" else timedelta(0))).date())
jq = q(cl.post, "/api/project-quote/remove/%d" % QA).json()
check("견적서 빼기 ok · 결과 첫 줄 「✅ 완료 — 「이름」을 뺐습니다. 30일 보관 뒤(%s) 완전히 지워집니다.」" % exp_day,
      jq.get("ok") and jq.get("message") == "✅ 완료 — 「견적_보관_가.xlsx」을 뺐습니다. 30일 보관 뒤(%s) 완전히 지워집니다." % exp_day and jq.get("purge_on") == exp_day, jq)
jp = q(cl.post, "/api/customer-po/remove/%d" % PA).json()
check("발주서 빼기 ok · 같은 꼴 결과 글", jp.get("ok") and jp.get("message", "").startswith("✅ 완료 — 「발주서_보관_가.pdf」을 뺐습니다. 30일 보관 뒤("), jp)
jc = q(cl.post, "/api/project-quote/remove/%d" % QC).json()
check("2호기 하나뿐인 견적서 빼기 ok", jc.get("ok"), jc)
rq = rows("SELECT removed_at, removed_by, removed_by_name, stored FROM project_quote_files WHERE id=?", QA)
check("DB: 견적서 줄 남음 · removed_at·뺀 사람 번호·이름", rq and rq[0][0] and rq[0][1] == U1["id"] and "가상영업" in (rq[0][2] or ""), rq)
check("디스크: 뺀 견적서 파일 그대로", os.path.isfile(os.path.join(M._z61_dir(), st0[QA])))
rp = rows("SELECT removed_at, removed_by FROM project_po_files WHERE id=?", PA)
check("DB: 발주서 줄 남음 · removed_at·누가", rp and rp[0][0] and rp[0][1] == U1["id"], rp)
check("디스크: 뺀 발주서 파일 그대로", os.path.isfile(os.path.join(M._z143_dir(), sp0[PA])))
hist = rows("SELECT note FROM project_history WHERE project_id=? AND note LIKE 'z1191z201%빼기%'", P)
check("변경 이력: 빼기 3건 · 「30일 보관 뒤(날짜) 완전 삭제 · 누가」", len(hist) == 3 and all(("30일 보관 뒤(%s) 완전 삭제" % exp_day) in h[0] and "가상영업" in h[0] for h in hist), hist)
r2 = q(cl.post, "/api/project-quote/remove/%d" % QA)
check("이미 뺀 것 다시 빼기 = 404", r2.status_code == 404, r2.status_code)

print("§2 뺀 것은 모든 곳에서 빠짐(바로 지울 때와 같게)")
hd = q(cl.get, "/project/%d" % P).text
ql = hd[hd.find(">견적서</dt>"):hd.find("고객 발주서</dt>")]
ql = ql[:ql.find('<details class="z201-fold"')] if '<details class="z201-fold"' in ql else ql   # 목록 줄만(아래 「뺀 파일」 접힌 줄 빼고)
check("상세 「견적서」 칸: 뺀 것 줄 없음 · 남은 2장 줄(QB·QM)", ql.count('class="z62-qrow"') == 2 and 'data-fid="%d"' % QA not in ql and 'data-fid="%d"' % QC not in ql, ql.count('class="z62-qrow"'))
t150 = hd[hd.find('id="docs150"'):]
t150 = t150[:t150.find("</dd>")]
check("수주별 표: 뺀 견적서·발주서 칩 없음 · 남은 것 있음", ("/quotes/%d" % QA) not in t150 and ("/customer-po/%d\"" % PA) not in t150
      and ("/quotes/%d" % QB) in t150 and ("/customer-po/%d\"" % PB) in t150, t150[:300])
d1 = M._z150_one(P)
check("수주별 자료: 1호기 견적 1·발주서 1 · 2호기 견적 = 관리팀 것 1장(뺀 것 안 셈)",
      [len(s["q"]["fs"]) for s in d1["sos"]] == [1, 1] and [len(s["p"]["files"]) for s in d1["sos"]] == [1, 0], [(len(s["q"]["fs"]), len(s["p"]["files"])) for s in d1["sos"]])
with D.db_session() as c:
    st = M._z141_project(c, P)
check("수주 카드 계산(_z141): 1호기 1장 · 뺀 것 없음", [f["id"] for f in st[O1]["fs"]] == [QB], st[O1])
check("수주 카드 묶음(z105): 뺀 것 없음", QA not in [f["id"] for f in M._z105_so_quotes(P).get(O1, [])])
check("견적서 목록(_z61_quote_files): 뺀 것 없음", {f["id"] for f in M._z61_quote_files(P)} == {QB, QM})
hq = q(cl.get, "/sales/quotations?period=all").text
check("견적 관리: 뺀 견적서·발주서 이름 없음 · 남은 것 있음", "견적_보관_가.xlsx" not in hq and "발주서_보관_가.pdf" not in hq and "견적_보관_나.xlsx" in hq and "발주서_보관_나.pdf" in hq)
hl = q(cl.get, "/projects?view=docs").text
chips = hl[hl.find("971M2811"):]
chips = chips[:chips.find("</tr>")]
check("프로젝트 목록 📎 칩: 뺀 것 없음", ("/quotes/%d" % QA) not in chips and ("/customer-po/%d\"" % PA) not in chips and ("/quotes/%d" % QB) in chips, chips[:300])
ho = q(cl.get, "/sales/orders/%d" % O1).text
po_sec = ho[ho.find('id="po143"'):][:8000]
check("수주 상세 「고객 발주서」: 뺀 것 줄 없음 · 남은 것 있음", 'href="/customer-po/%d"' % PA not in strip_js(po_sec) and "발주서_보관_나.pdf" in po_sec)
check("발주서 보기·파일: 뺀 것 404", q(cl.get, "/customer-po/%d" % PA).status_code == 404 and q(cl.get, "/customer-po/%d/file" % PA).status_code == 404)
hv = q(cl.get, "/customer-po/%d" % PB).text
check("남은 발주서 보기: 같은 수주 목록에 뺀 것 없음", "발주서_보관_가.pdf" not in strip_js(hv) and "발주서_보관_나.pdf" in hv)
check("견적서 보기·파일: 뺀 것 404", q(cl.get, "/quotes/%d" % QA).status_code == 404 and q(cl.get, "/projects/%d/quote-files/%d" % (P, QA)).status_code == 404)
z = q(cl.get, "/projects/%d/docs.zip" % P)
names = zipfile.ZipFile(io.BytesIO(z.content)).namelist() if z.status_code == 200 else []
check("zip: 뺀 것 없음 · 남은 견적서 2 · 발주서 1", z.status_code == 200 and not any("보관_가" in n for n in names)
      and sum(n.endswith(".xlsx") for n in names) == 2 and sum(n.endswith(".pdf") for n in names) == 1, names)
ex = q(cl.get, "/sales/quotations/export.xlsx?period=all")
import openpyxl  # noqa: E402
flat = " ".join(str(c.value) for r in openpyxl.load_workbook(io.BytesIO(ex.content)).active.iter_rows() for c in r if c.value is not None)
check("엑셀 내보내기: 뺀 것 없음 · 남은 것 있음", ex.status_code == 200 and "견적_보관_가.xlsx" not in flat and "견적_보관_나.xlsx" in flat)
with D.db_session() as c:   # 수주번호 없는 옛 발주서 → 빼면 「수주 칸 확인」에서도 빠짐
    c.execute("INSERT INTO project_po_files(tok, project_id, order_id, orig_name, stored, kind, by_id, by_name, created_at, attached_at) "
              "VALUES('old201', ?, NULL, '옛_발주서.pdf', '202609/old201.pdf', 'pdf', ?, '가상영업', '2026-09-01 10:00', '2026-09-01 10:00')", (P, U1["id"]))
    LP = c.execute("SELECT id FROM project_po_files WHERE tok='old201'").fetchone()[0]
    n_before = len([x for x in M._z156_noso_files(c) if x["kind"] == "po"])
q(cl.post, "/api/customer-po/remove/%d" % LP)
with D.db_session() as c:
    n_after = len([x for x in M._z156_noso_files(c) if x["kind"] == "po"])
check("수주 칸 확인(수주번호 없는 옛 발주서): 빼면 빠짐(1 → 0)", (n_before, n_after) == (1, 0), (n_before, n_after))
rr = q(cl.post, "/api/so-check-file/po/%d" % LP, data={"order_id": O1})
check("수주 칸 확인 붙이기: 뺀 발주서 = 409(찾지 못함)", rr.status_code == 409, rr.status_code)
with D.db_session() as c:
    has = M._z143_has(c)
check("발주서 자리 수(_z143_has): 뺀 것 안 셈(1호기 1장)", has.get((P, O1)) == 1, has)
with D.db_session() as c:
    check("_z143_nprev: 1호기 발주서 1장", M._z143_nprev(c, P, O1) == 1)

print("§3 안내문(묻는 창)")
a = q(cl.get, "/api/keep30/ask?kind=quote&ids=%d" % QB).json()
check("안내 값: 이름 · 이어진 수주 · 완전 삭제 날(지금 빼면 %s)" % exp_day, a.get("ok") and a.get("purge_on") == exp_day
      and a.get("items") == [{"fid": QB, "name": "견적_보관_나.xlsx", "so_no": "Y-261128-1"}], a)
a2 = q(cl.get, "/api/keep30/ask?kind=quote&ids=%d" % QA).json()
check("안내 값: 이미 뺀 것은 없음", a2.get("ok") and a2.get("items") == [], a2)
js = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "keep30_js.html"), encoding="utf-8").read()
for w in ("목록에서 <b>바로 빠집니다</b>", "<b>30일 동안 보관</b>한 뒤", "에 완전히 지워집니다.", "이 화면 아래 「뺀 파일」", "에서 되살릴 수 있습니다.",
          "에 붙어 있습니다.", "✕ 닫기", "↺ 되살리기", "'✅ 완료 — 「' + done[0].name + '」을 뺐습니다. 30일 보관 뒤(' + day + ') 완전히 지워집니다.'",
          "'✅ 완료 — 「' + ok[0] + '」을 되살렸습니다'", "/api/keep30/ask?kind="):
    check("안내문 창 글: " + w[:46], w in js)
check("그려진 상세 화면에 공용 창 스크립트(window.z201) 한 번 정의", hd.count("window.z201 = {remove: remove, restore: restore}") >= 1 and "window.z201.remove('quote'" in hd and "window.z201.remove('po'" in hd)
check("옛 확인 글(「바로 지워지고 되돌릴 수 없습니다」) 없음", "바로 지워지고 되돌릴 수 없" not in hd and "파일이 바로 지워집니다" not in hd)
check("발주서 보기 화면 빼기도 공용 창", "window.z201.remove('po'" in hv)

print("§4 「30일 안에 뺀 파일」 · 되살리기")
fold = hd[hd.find('<details class="z201-fold" data-kind="quote"'):]
fold = fold[:fold.find("</details>")]
check("견적서 칸 아래 접힌 줄: 「30일 안에 뺀 파일 2건 · 되살리기」 · 기본 접힘(open 없음)", "30일 안에 뺀 파일 2건 · 되살리기" in fold and "<details class=\"z201-fold\" data-kind=\"quote\">" in hd, fold[:200])
check("접힌 줄 각 줄: 이름 · 뺀 사람(이름) · 뺀 날 · 완전 삭제 날 · ↺ 되살리기", "견적_보관_가.xlsx" in fold and "가상영업" in fold and ("뺀 날 " + T0) in fold
      and (exp_day + " 완전 삭제") in fold and fold.count('class="z201-rs"') == 2)
fpo = hd[hd.find('<details class="z201-fold" data-kind="po"'):]
fpo = fpo[:fpo.find("</details>")]
check("발주서 칸 아래 접힌 줄(관리번호 모두 · 그때 뺀 것 1건)", "30일 안에 뺀 파일 1건 · 되살리기" in fpo and "발주서_보관_가.pdf" in fpo, fpo[:200])
fso = ho[ho.find('<details class="z201-fold" data-kind="po"'):]
fso = fso[:fso.find("</details>")]
check("수주 상세 발주서 칸 아래: 그 수주 것 1건", "30일 안에 뺀 파일 1건 · 되살리기" in fso and "발주서_보관_가.pdf" in fso, fso[:200])
check("뺀 것 없는 화면엔 접힌 줄 없음(빼기 전 상세)", "z201-fold\" data-kind" not in hd0)
WHO["u"] = U2
r403 = q(cl.post, "/api/project-quote/restore/%d" % QA)
check("되살리기: 권한 없는 계정(관리팀·남의 것) 403", r403.status_code == 403, (r403.status_code, r403.text[:120]))
check("되살리기: 권한 없는 계정 발주서도 403", q(cl.post, "/api/customer-po/restore/%d" % PA).status_code == 403)
hd2 = q(cl.get, "/project/%d" % P).text
f2 = hd2[hd2.find('<details class="z201-fold" data-kind="quote"'):]
f2 = f2[:f2.find("</details>")]
check("권한 없는 계정 화면: 접힌 줄은 보이나 되살리기 단추 없음", "30일 안에 뺀 파일 2건" in f2 and 'class="z201-rs"' not in f2)
WHO["u"] = U1
rs = q(cl.post, "/api/project-quote/restore/%d" % QA).json()
check("되살리기 ok · 결과 첫 줄 「✅ 완료 — 「견적_보관_가.xlsx」을 되살렸습니다.」", rs.get("ok") and rs.get("message") == "✅ 완료 — 「견적_보관_가.xlsx」을 되살렸습니다.", rs)
check("되살린 줄 = removed_at 비움", rows("SELECT removed_at, removed_by, removed_by_name FROM project_quote_files WHERE id=?", QA) == [(None, None, None)])
check("다시 목록·합계에 보임(1호기 견적 2장 · 수주별 표)", {f["id"] for f in M._z61_quote_files(P)} == {QA, QB, QM}
      and [len(s["q"]["fs"]) for s in M._z150_one(P)["sos"]][0] == 2)
check("변경 이력: 「되살림 · 누가」", rows("SELECT COUNT(*) FROM project_history WHERE project_id=? AND note LIKE 'z1191z201 견적서 되살림 · %가상영업%'", P)[0][0] == 1)
rs2 = q(cl.post, "/api/project-quote/restore/%d" % QA).json()
check("이미 살아 있는 것 되살리기 = 그대로 ok", rs2.get("ok") and rs2.get("already"), rs2)
check("없는 것 되살리기 = 404", q(cl.post, "/api/project-quote/restore/999999").status_code == 404)
rsp = q(cl.post, "/api/customer-po/restore/%d" % PA).json()
check("발주서 되살리기 ok · 수주 상세에 다시 보임", rsp.get("ok") and "발주서_보관_가.pdf" in q(cl.get, "/sales/orders/%d" % O1).text)
check("되살린 발주서 보기 200", q(cl.get, "/customer-po/%d" % PA).status_code == 200)

print("§5 밤 정리(30일 보관 뒤)")
q(cl.post, "/api/project-quote/remove/%d" % QA)
q(cl.post, "/api/customer-po/remove/%d" % PA)
now_safe = kst().replace(hour=22, minute=30, second=0, microsecond=0)   # 오늘 22:30(밤 정리 시각 · 금지 시간 아님)
if now_safe < kst():
    now_safe = kst()
res = q(M._z201_purge, now_safe)
check("30일 안 된 것은 정리 안 됨(줄·파일 남음)", res.get("quote", {}).get("del") == 0 and rows("SELECT COUNT(*) FROM project_quote_files WHERE id IN (?,?)", QA, QC)[0][0] == 2
      and os.path.isfile(os.path.join(M._z61_dir(), st0[QA])), res)
old = (kst() - timedelta(days=31)).strftime("%Y-%m-%d %H:%M")
with D.db_session() as c:
    c.execute("UPDATE project_quote_files SET removed_at=? WHERE id IN (?,?)", (old, QA, QC))
    c.execute("UPDATE project_po_files SET removed_at=? WHERE id=?", (old, PA))
    # 같은 파일을 쓰는 다른 줄: QC 의 저장 파일을 살아 있는 다른 줄(QB 복사)이 씀 → QC 는 지우지 않고 남김
    c.execute("INSERT INTO project_quote_files(tok, project_id, order_id, orig_name, stored, by_id, by_name, created_at, attached_at) "
              "VALUES('share201', ?, ?, '같은파일_다른줄.xlsx', ?, ?, '가상영업', ?, ?)", (P, O2, st0[QC], U1["id"], old, old))
r404 = q(cl.post, "/api/project-quote/restore/%d" % QA)
check("30일 지난 것(정리 전) 되살리기 = 404", r404.status_code == 404 and "30일 보관이 끝나" in r404.json().get("message", ""), (r404.status_code, r404.text[:120]))
fold3 = q(cl.get, "/project/%d" % P).text
check("30일 지난 것은 「뺀 파일」 접힌 줄에 안 보임", "견적_보관_가.xlsx" not in fold3[fold3.find('data-kind="quote"'):][:3000] or 'z201-fold" data-kind="quote"' not in fold3)
MON = now_safe
while MON.weekday() != 0:
    MON += timedelta(days=1)
r_mon = q(M._z201_purge, MON.replace(hour=3, minute=0))
check("월 03:00(NAS 백업 시간) = 정리 안 함", r_mon.get("skip") and rows("SELECT COUNT(*) FROM project_quote_files WHERE id=?", QA)[0][0] == 1, r_mon)
r_mon2 = q(M._z201_purge, MON.replace(hour=7, minute=29))
check("월 07:29 = 정리 안 함 · 월 07:30 은 금지 시간 아님", r_mon2.get("skip") and M._z201_quiet(MON.replace(hour=7, minute=30)) == "", r_mon2)
WD = now_safe
while WD.weekday() >= 5:
    WD += timedelta(days=1)
r_am = q(M._z201_purge, WD.replace(hour=9, minute=0))
check("평일 09:00(08:50~09:30) = 정리 안 함", r_am.get("skip") and rows("SELECT COUNT(*) FROM project_quote_files WHERE id=?", QA)[0][0] == 1, r_am)
check("평일 08:49·09:30 은 금지 시간 아님 · 토요일 09:00 도 아님", M._z201_quiet(WD.replace(hour=8, minute=49)) == "" and M._z201_quiet(WD.replace(hour=9, minute=30)) == ""
      and M._z201_quiet((WD + timedelta(days=(5 - WD.weekday()))).replace(hour=9, minute=0)) == "")
res2 = q(M._z201_purge, now_safe)
check("30일 지난 것 정리: 견적서 1 지움 · 1 남김(같은 파일 쓰는 줄) · 발주서 1 지움", res2.get("quote") == {"del": 1, "kept": 1} and res2.get("po") == {"del": 1, "kept": 0}, res2)
check("지운 견적서: 줄·파일 없음", rows("SELECT COUNT(*) FROM project_quote_files WHERE id=?", QA)[0][0] == 0 and not os.path.isfile(os.path.join(M._z61_dir(), st0[QA])))
check("지운 발주서: 줄·파일 없음", rows("SELECT COUNT(*) FROM project_po_files WHERE id=?", PA)[0][0] == 0 and not os.path.isfile(os.path.join(M._z143_dir(), sp0[PA])))
check("같은 파일을 쓰는 줄이 있는 것: 줄·파일 남음", rows("SELECT COUNT(*) FROM project_quote_files WHERE id=?", QC)[0][0] == 1 and os.path.isfile(os.path.join(M._z61_dir(), st0[QC])))
check("30일 안 된 것·살아 있는 것 그대로(QB·PB·QM)", rows("SELECT COUNT(*) FROM project_quote_files WHERE id IN (?,?) AND removed_at IS NULL", QB, QM)[0][0] == 2
      and os.path.isfile(os.path.join(M._z143_dir(), sp0[PB])))
check("이력: 완전 삭제 2건 · 변경자 = 시스템(NULL)", rows("SELECT COUNT(*) FROM project_history WHERE note LIKE 'z1191z201 % 30일 보관 끝 · 완전 삭제(시스템)' AND changed_by IS NULL")[0][0] == 2)
check("정리 뒤 되살리기 = 404", q(cl.post, "/api/project-quote/restore/%d" % QA).status_code == 404 and q(cl.post, "/api/customer-po/restore/%d" % PA).status_code == 404)
check("화면을 여는 것만으로는 지우지 않음(z64 「열 때 지움」 없음)", "removed_at IS NOT NULL" not in open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read().split("def _z61_quote_files")[1].split("def ")[0])

print("§6 날짜 계산 · 상수 한 곳")
check("상수 = 30 (한 곳)", M.Z201_KEEP_DAYS == 30 and open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read().count("Z201_KEEP_DAYS = ") == 1)
check("11-28 10:00 뺌 → 12월 28일", M._z201_md(M._z201_purge_day("2026-11-28 10:00")) == "12월 28일")
check("11-28 23:00 뺌 → 12월 29일(22:30 넘음)", M._z201_md(M._z201_purge_day("2026-11-28 23:00")) == "12월 29일")
check("다음 정리까지 = 22:30 기준", abs(M._z201_secs_until_next(datetime(2026, 11, 28, 22, 0)) - 1800) < 1 and abs(M._z201_secs_until_next(datetime(2026, 11, 28, 22, 31)) - (86400 - 60)) < 1)

print("§7 권한 그대로")
WHO["u"] = U2
r = q(cl.post, "/api/project-quote/remove/%d" % QB)
check("관리팀(기술영업팀 아님)·남의 견적서 빼기 = 403", r.status_code == 403, r.status_code)
check("관리팀·남의 발주서 빼기 = 403", q(cl.post, "/api/customer-po/remove/%d" % PB).status_code == 403)
check("관리팀 안내 값 = 뺄 수 있는 것 없음", q(cl.get, "/api/keep30/ask?kind=quote&ids=%d" % QB).json().get("items") == [])
jm = q(cl.post, "/api/project-quote/remove/%d" % QM).json()
check("관리팀 본인이 올린 것은 뺌 · 되살리기도 본인", jm.get("ok") and q(cl.post, "/api/project-quote/restore/%d" % QM).json().get("ok"))
WHO["u"] = None
check("로그인 안 함 = 401", q(cl.post, "/api/project-quote/restore/%d" % QB).status_code == 401 and q(cl.post, "/api/project-quote/remove/%d" % QB).status_code == 401)
WHO["u"] = U1

print("§8 그려진 화면 스크립트 문법(node)")
node = None
for cand in ("node", r"C:\Program Files\nodejs\node.exe"):
    try:
        subprocess.run([cand, "--version"], capture_output=True, check=True); node = cand; break
    except Exception:
        pass
if node:
    bad = []
    for nm, html in (("상세", q(cl.get, "/project/%d" % P).text), ("수주 상세", q(cl.get, "/sales/orders/%d" % O1).text),
                     ("발주서 보기", q(cl.get, "/customer-po/%d" % PB).text), ("견적 관리", q(cl.get, "/sales/quotations?period=all").text),
                     ("수정 화면", q(cl.get, "/projects/%d/edit" % P).text)):
        for k, m in enumerate(re.finditer(r"<script(?![^>]*src)(?![^>]*type=\"application/(?:ld\+)?json\")[^>]*>(.*?)</script>", html, re.S)):
            fd, fpth = tempfile.mkstemp(suffix=".js"); os.write(fd, m.group(1).encode("utf-8")); os.close(fd)
            r = subprocess.run([node, "--check", fpth], capture_output=True, text=True, encoding="utf-8")
            os.remove(fpth)
            if r.returncode:
                bad.append(nm + "#%d " % k + r.stderr.strip().split("\n")[0][-160:])
    check("그려진 화면 스크립트 문법 모두 통과(node)", not bad, bad)
else:
    print("… node 가 없어 스크립트 문법 검사는 건너뜀")

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
