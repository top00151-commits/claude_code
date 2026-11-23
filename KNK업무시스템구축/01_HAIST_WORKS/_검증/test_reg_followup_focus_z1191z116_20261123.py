# -*- coding: utf-8 -*-
"""z1191z116 시험 — 이새롬 프로 신고 「3호기 추가로 등록 후 화면이 1호기 프로젝트 정보가 뜹니다」 + 실무자 시뮬레이션에서 찾은 2가지
  §1 추가 등록 → 다음 화면 주소에 새 수주번호(so=) → 상세 맨 위(메인) 카드 = 방금 수주(3호기)
  §2 등록 성공 → 다음 화면 주소에 qf_done=<사업부> (상세가 등록 화면 임시본을 지움) · 거절되면 안 붙음(임시본으로 입력값 되살림)
  §3 등록 화면 입력 칸 Enter 로 저장되지 않게(저장은 「＋ 등록」 단추로만) · 상세 화면에 임시본 지우는 조각
"""
import contextlib, io, os, re, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z116-test-only-not-a-real-key"
import app.database as D                                   # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z116_"); _REAL = D.DB_PATH; D.DB_PATH = os.path.join(TMP, "t.db"); assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        conn.execute("INSERT INTO teams (id, name, code) VALUES (1, '기술영업팀', '01')")
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상영업', 'member', 'Z116', 'Z116', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 0, 0)")
    U = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z116'").fetchone())
    conn.execute("INSERT INTO customers (name, alias) VALUES ('가상고객(주)', '가상고객')")
    CID = conn.execute("SELECT id FROM customers WHERE name='가상고객(주)'").fetchone()[0]
import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402
M.get_user = lambda request: U
cl = TestClient(M.app)
OK = FAIL = 0
def check(label, cond, got=None):
    global OK, FAIL
    if cond: OK += 1; print("  ✅", label)
    else: FAIL += 1; print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:400])
def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)
def txt(h):
    h = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", h); return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))
def form(**kw):
    f = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규", "customer_name": "가상고객(주)", "customer_id": str(CID),
         "name": "가상 검사기", "model": "Z116-MODEL", "equip_name": "가상 장비", "shipment_form": "ASSEMBLY", "is_export": "0",
         "unit_qty": "1", "unit_price": "1000000", "order_date": "2026-11-23", "due_date": "2026-12-20", "prod_mode": "none", "currency": "KRW"}
    f.update(kw); return f
def post(f):
    return q(cl.post, "/projects/new", data=f, follow_redirects=False)

print("§1·2 신규 → 추가 등록")
r = post(form(unit_qty="2", **{"unit_amount[]": ["1000000", "1000000"]}))
loc = r.headers.get("location", "")
m = re.match(r"/project/(\d+)", loc)
check("신규 등록 → 프로젝트 상세로 · qf_done=T(임시본 지움 표시)", r.status_code == 303 and m is not None and "qf_done=T" in loc, (r.status_code, loc))
PID = int(m.group(1)) if m else 0
with D.db_session() as c:
    code = c.execute("SELECT mgmt_code FROM projects WHERE id=?", (PID,)).fetchone()[0]
r = post(form(po_type="추가", mgmt_code=code, unit_qty="1", unit_price="1500000", due_date="2026-12-24"))
loc = r.headers.get("location", "")
with D.db_session() as c:
    o = c.execute("SELECT id, order_no FROM orders WHERE project_id=? ORDER BY id DESC LIMIT 1", (PID,)).fetchone()
    labs = [x[0] for x in c.execute("SELECT unit_label FROM order_items WHERE order_id=?", (o[0],)).fetchall()] if o else []
check("추가 등록 → 새 수주 · 3호기", o is not None and labs == ["3호기"], (o and o[1], labs))
check("추가 등록 다음 주소 = /project/{id}?followup=1&qf_done=T&so=<새 수주번호>", loc.startswith("/project/%d?followup=1" % PID) and ("so=" + (o[1] if o else "?")) in loc and "qf_done=T" in loc, loc)
h = txt(q(cl.get, loc.replace("&qf_done=T", "")).text)
i = h.find("수주 내역"); seg = h[i:h.find("참고 · 추가 수주", i)] if i >= 0 else ""
first = re.search(r"([TMLC]-\d{6}-\d+)", seg)
check("다음 화면 맨 위 카드 = 방금 수주(3호기) · 최초 수주는 「참고 · 추가 수주」로", first is not None and o is not None and first.group(1) == o[1] and "3호기" in seg and "1호기" not in seg, (first and first.group(1), seg[:200]))
r = post(form(model="", equip_name=""))   # 신규 · 모델명·장비명 비움 → 서버가 필수 항목으로 거절
loc = r.headers.get("location", "")
check("거절(모델명·장비명 비움) → 등록 화면으로 · qf_done 안 붙음(임시본으로 입력값 되살림)", "/projects/quick" in loc and "qf_done" not in loc, loc)

print("§3 화면 조각")
hq = q(cl.get, "/projects/quick?biz_div=T").text
check("등록 화면: 입력 칸 Enter 로 저장 막는 조각(z1191z116 ③)", "z1191z116 ③" in hq and "e.isComposing" in hq and "e.preventDefault()" in hq)
hd = q(cl.get, "/project/%d?qf_done=T" % PID).text
check("상세 화면: qf_done 이면 등록 화면 임시본(knk.qf.draft.<사업부>) 지움 + 주소에서 뺌", "localStorage.removeItem('knk.qf.draft.' + b)" in hd and "q.delete('qf_done')" in hd)
print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
