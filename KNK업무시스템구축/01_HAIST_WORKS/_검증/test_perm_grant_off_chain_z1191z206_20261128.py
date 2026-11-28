# -*- coding: utf-8 -*-
"""z1191z206 대표 결정(2026-11-28 「추천대로 해」) — 시험 사본(임시 DB · 가상 직원 · 운영 DB 아님)
   §1 A 「권한 부여」(/admin/permissions/grant) 입구 0 — 화면 글(옛 보관 _legacy_v5mig·그 화면 템플릿 자신 빼고)에 그 주소로 가는 링크 없음
   §2 A 주소를 직접 열면(GET) · 옛 양식을 보내면(POST) 저장 0 · 권한 관리 화면 안내(?moved=grant)로 감 · 안내가 가리키는 세 화면이 실제로 열림
   §3 B 수주 상세 「N 연결」 6칸(견적 → 수주 → 제작요청 → 출하 → 세금계산서 → 입금) = 가상 수주 5개(견적 있음/없음/지운 것/옛 관리번호 견적 ·
      제작요청 번호 있음/비어 있고 수주 하나/비어 있고 수주 둘(애매)/취소 · 출하 전부/일부/옛 출하 표 · 세금계산서·입금 있음/없음/일부 ·
      베트남 고객 USD 수주) 의 DB 값과 화면 값 대조 · 화면 열기 전후 DB 같음(읽기만) · 금액 못 보는 사람은 견적 칸이 링크 아님
   §4 (선택) 실제 자료 사본 서버 대조 — 환경 KNK_Z206_REAL_DB(시험 사본 DB 파일) + KNK_Z206_REAL_URL(그 사본으로 띄운 시험 서버) 가 있을 때만
실행:  python _검증/test_perm_grant_off_chain_z1191z206_20261128.py"""
import contextlib, hashlib, io, os, re, sqlite3, sys, tempfile, urllib.request
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z206-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D   # noqa: E402
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_z206_"), "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, " ←", got)


def rd(rel):
    return io.open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8").read()


# ── §1 A 입구 ──
print("§1 A 「권한 부여」 입구")
TPL = os.path.join(ROOT, "app", "templates")
hits = []
for dp, dn, fn in os.walk(TPL):
    if "_legacy_v5mig" in dp:
        continue
    for f in fn:
        if f.endswith(".html") and f != "admin_permissions_grant.html":
            s = io.open(os.path.join(dp, f), encoding="utf-8").read()
            if re.search(r"""(href|action)\s*=\s*["'][^"']*/admin/permissions/grant(?![-\w])""", s):
                hits.append(os.path.relpath(os.path.join(dp, f), TPL))
check(hits == [], "화면 글 어디에도 /admin/permissions/grant 로 가는 링크·양식 없음(옛 보관 빼고)", hits)
ap = rd("app/templates/admin_permissions.html")
check('href="/admin/staff"' in ap and "권한 주기 → 👤 직원" in ap, "권한 관리 첫 화면: 「권한 부여」 카드 자리 = 👤 직원(실제로 권한을 주는 곳)")
tp = rd("app/templates/admin_team_perms.html")
check('href="/admin/staff/{{ m.id }}"' in tp and "권한 바꾸기" in tp, "팀 권한 줄 단추 = 그 사람 직원 화면(/admin/staff/<번호>)")
check(os.path.isfile(os.path.join(TPL, "admin_permissions_grant.html")), "옛 화면 템플릿은 지우지 않고 남김(막기만)")
src = rd("app/main.py")
check("async def _z206_grant_submit_off(" in src, "옛 저장 본문은 남기되 어느 주소에도 걸지 않음")

# ── 가상 자료 ──
import app.main as M   # noqa: E402
from fastapi.testclient import TestClient   # noqa: E402
CUR = {"u": None}
M.get_user = lambda request: CUR["u"]
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)

with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_vi", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    ucols = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    tids = [r[0] for r in c.execute("SELECT id FROM teams ORDER BY display_order LIMIT 2")]

    def mk(uid, name, role, sales=0):
        d = {"id": uid, "name": name, "role": role, "login_id": "u%d" % uid, "password": "sso_only_no_local_password", "is_active": 1,
             "password_version": 1, "can_view_sales": sales, "can_use_sales": sales, "team_id": tids[0] if tids else None}
        d = {k: v for k, v in d.items() if k in ucols}
        c.execute("INSERT INTO users (%s) VALUES (%s)" % (",".join(d), ",".join("?" * len(d))), list(d.values()))
        return dict(c.execute("SELECT u.*, t.name AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.id=?", (uid,)).fetchone())
    CEO = mk(901, "가상대표", "ceo", 1)
    ADMIN = mk(902, "가상관리자", "admin", 0)
    STAFF = mk(903, "금액못보는직원", "member", 0)
    M._z61_table(c)   # 견적서 표(운영엔 있음)
    cc = {r[1] for r in c.execute("PRAGMA table_info(customers)")}
    for cid, nm, ctry in ((801, "가상국내고객", ""), (802, "가상베트남고객", "Vietnam")):
        d = {k: v for k, v in {"id": cid, "name": nm, "country": ctry, "is_overseas": 1 if ctry else 0, "is_active": 1}.items() if k in cc}
        c.execute("INSERT INTO customers (%s) VALUES (%s)" % (",".join(d), ",".join("?" * len(d))), list(d.values()))
    pc = {r[1] for r in c.execute("PRAGMA table_info(projects)")}
    for pid, code in ((701, "T001X2611"), (702, "T002X2611"), (703, "T003X2611"), (704, "T004X2611")):
        d = {k: v for k, v in {"id": pid, "mgmt_code": code, "name": "가상%d" % pid, "currency": "KRW", "is_archived": 0, "customer_id": 801}.items() if k in pc}
        c.execute("INSERT INTO projects (%s) VALUES (%s)" % (",".join(d), ",".join("?" * len(d))), list(d.values()))
    oc = {r[1] for r in c.execute("PRAGMA table_info(orders)")}
    ic = {r[1] for r in c.execute("PRAGMA table_info(order_items)")}

    def so(oid, pid, cid, status, ccy="KRW", total=2000000, od="2026-10-01"):
        d = {k: v for k, v in {"id": oid, "order_no": "SO-Z206-%d" % oid, "project_id": pid, "customer_id": cid, "status": status,
                               "currency": ccy, "total_amount": total, "order_date": od, "created_at": od + " 09:00"}.items() if k in oc}
        c.execute("INSERT INTO orders (%s) VALUES (%s)" % (",".join(d), ",".join("?" * len(d))), list(d.values()))

    def it(iid, oid, label, ust, sdate="", ti=None, exp=0, amt=1000000):
        d = {"id": iid, "order_id": oid, "unit_label": label, "qty": 1, "unit_price": amt, "amount": amt, "unit_status": ust,
             "status_date": sdate, "is_export": exp}
        for n, (dv, av) in enumerate(ti or [], 1):
            d["tax_invoice_date" if n == 1 else "tax_invoice_date%d" % n] = dv
            d["tax_invoice_amt%d" % n] = av
        d = {k: v for k, v in d.items() if k in ic}
        c.execute("INSERT INTO order_items (%s) VALUES (%s)" % (",".join(d), ",".join("?" * len(d))), list(d.values()))

    def qf(fid, pid, oid, created, removed=None):
        c.execute("INSERT INTO project_quote_files(id, tok, project_id, order_id, orig_name, stored, created_at, removed_at, read_json) "
                  "VALUES(?,?,?,?,?,?,?,?,?)", (fid, "z206tok%d" % fid, pid, oid, "견적%d.xlsx" % fid, "x", created, removed, "{}"))

    def pr(prid, pid, oids, created, cancelled=None):
        c.execute("INSERT INTO prod_requests(id, project_id, mgmt_code, order_ids, created_at, created_date, cancelled_at) VALUES(?,?,?,?,?,?,?)",
                  (prid, pid, "x", oids, created, created[:10], cancelled))

    def rp(oid, amt, at, ccy="KRW"):
        c.execute("INSERT INTO receipts_payment(order_id, amount, received_at, currency) VALUES(?,?,?,?)", (oid, amt, at, ccy))
    # O1 = 다 있음(입금 완료) — 견적 2장 · 제작요청 번호로 · 호기 2 모두 출하 · 계산서 2장 · 입금 완료(PAID)
    so(6001, 701, 801, "PAID")
    it(7001, 6001, "1호기", "출하", "2026-10-20", [("2026-10-21", 1000000)])
    it(7002, 6001, "2호기", "출하", "2026-10-25", [("2026-10-26", 1000000)])
    qf(51, 701, 6001, "2026-09-20 10:00"); qf(52, 701, 6001, "2026-09-25 10:00")
    pr(41, 701, "6001", "2026-10-02 09:00")
    rp(6001, 2200000, "2026-11-20")
    # O2·O3 = 같은 관리번호(702) 살아 있는 수주 둘 — 수주 번호 없는 옛 제작요청서(애매 → 둘 다 없음) · 수주 번호 없는 옛 견적서(→ 없음)
    so(6002, 702, 801, "CONFIRMED")
    it(7003, 6002, "1호기", "진행중")
    so(6003, 702, 801, "SHIPPED")
    it(7004, 6003, "1호기", "출하", "2026-11-01", [("2026-11-02", 1000000)])
    it(7005, 6003, "2호기", "진행중")
    qf(53, 702, None, "2026-09-01 10:00")          # 옛 관리번호 견적(수주 번호 없음)
    qf(54, 702, 6003, "2026-09-02 10:00", "2026-09-03 10:00")   # 지운 견적
    pr(42, 702, "", "2026-10-03 09:00")
    rp(6003, 500000, "2026-11-10")               # 일부 입금(미수 남음)
    # O4 = 베트남 고객 USD 수출 수주 · 관리번호에 수주 하나 · 수주 번호 없는 옛 제작요청서(→ 이 수주) · 입금 없음
    so(6004, 703, 802, "SHIPPED", "USD", 5000)
    it(7006, 6004, "1호기", "출하", "2026-11-05", [("2026-11-06", 2500), ("2026-11-16", 2500)], exp=1, amt=5000)
    qf(55, 703, 6004, "2026-10-10 10:00")
    pr(43, 703, None, "2026-10-12 09:00")
    # O5 = 옛 출하 표(shipments)만 · 취소된 제작요청서만 · 견적·계산서·입금 없음
    so(6005, 704, 801, "CONFIRMED")
    it(7007, 6005, "1호기", "진행중")
    c.execute("INSERT INTO shipments(order_id, shipped_at, shipped_qty) VALUES(?,?,?)", (6005, "2026-11-11 10:00", 1))
    pr(44, 704, "6005", "2026-10-13 09:00", "2026-10-14 09:00")
    # 원래 판 POST 가 저장하는지 보는 표(위임 토큰)
    _cnt = lambda t: c.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]


def tcount(t):
    with D.db_session() as c:
        try:
            return c.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
        except Exception:
            return None


def db_hash():
    with D.db_session() as c:
        h = hashlib.sha256()
        for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
            if t in ("app_logs", "slow_request_log", "request_log", "page_views", "user_activity", "access_log", "audit_log"):
                continue
            for r in c.execute('SELECT * FROM "%s" ORDER BY rowid' % t).fetchall():
                h.update(repr(tuple(r)).encode("utf-8"))
        return h.hexdigest()


cl = TestClient(M.app, raise_server_exceptions=False)

# ── §2 A 직접 열기 ──
print("§2 A 주소를 직접 열면")
CUR["u"] = ADMIN
r = cl.get("/admin/permissions/grant", follow_redirects=False)
check(r.status_code == 303 and r.headers.get("location") == "/admin/permissions?moved=grant", "GET /admin/permissions/grant → 권한 관리 안내(?moved=grant)", (r.status_code, r.headers.get("location")))
r = cl.get("/admin/permissions/grant?user_id=903", follow_redirects=False)
check(r.status_code == 303 and r.headers.get("location") == "/admin/permissions?moved=grant", "옛 팀 권한 단추 주소(?user_id=)도 같은 안내", (r.status_code, r.headers.get("location")))
n_tok, n_perm = tcount("delegation_tokens"), tcount("permissions")
for form in ({"to_user": "금액못보는직원", "resource": "sales", "action": "read", "expires_at": "2027-01-01", "reason": "시험"},
             {"user_id": "903", "permission_id": "1"}):
    r = cl.post("/admin/permissions/grant", data=form, follow_redirects=False)
    check(r.status_code == 303 and r.headers.get("location") == "/admin/permissions?moved=grant", "POST(%s) → 저장 없이 안내" % ",".join(form), (r.status_code, r.headers.get("location"), r.text[:120]))
check(tcount("delegation_tokens") == n_tok and tcount("permissions") == n_perm, "POST 뒤 위임 토큰·권한 표 줄 수 그대로(저장 0)",
      (n_tok, tcount("delegation_tokens"), n_perm, tcount("permissions")))
r = cl.get("/admin/permissions?moved=grant")
t = r.text
check(r.status_code == 200 and "「권한 부여」 화면은 쓰지 않습니다" in t and "아무것도 저장되지 않았습니다" in t, "안내 띠 보임(무엇이 일어났는지 · 저장 안 됨)", r.status_code)
for href, nm in (("/admin/staff", "👤 직원"), ("/admin/users/perms", "🔑 여러 명 권한 한꺼번에"), ("/team/permissions", "🔐 팀 권한")):
    check(('href="%s"' % href) in t and nm in t, "안내가 가리키는 화면 %s(%s)" % (nm, href))
    rr = cl.get(href)
    check(rr.status_code == 200, "  └ 그 화면 실제로 열림(관리자) %s" % href, rr.status_code)
check("「권한 부여」 화면은 쓰지 않습니다" not in cl.get("/admin/permissions").text, "그냥 열면 안내 띠 없음")
CUR["u"] = STAFF
r = cl.get("/admin/permissions/grant", follow_redirects=False)
check(r.status_code == 303 and r.headers.get("location") == "/login", "권한 없는 직원 = 예전 그대로(/login)", (r.status_code, r.headers.get("location")))
r = cl.post("/admin/permissions/grant", data={"to_user": "x"}, follow_redirects=False)
check(r.status_code == 401, "권한 없는 직원 POST = 예전 그대로 401", r.status_code)


# ── §3 B 「N 연결」 ──
CHAIN_RE = re.compile(r'<(a|div) class="k-chain-item (\w+)"(?: href="([^"]*)")? data-chain="(\w+)"[^>]*>\s*<b>([^<]*)(?:<span[^>]*>[^<]*</span>)?</b><small>([^<]*)</small>')


def parse_chain(html):
    out = {}
    for tag, st, href, key, label, small in CHAIN_RE.findall(html):
        out[key] = {"st": st, "href": href or None, "label": label.strip(), "sub": small.replace("&amp;", "&").strip()}
    conns = re.findall(r'<span class="k-conn( off)?" aria-hidden="true">', html)
    return out, [not x for x in conns]


def expect(cx, oid, can_sales=True):
    """화면과 따로 DB 에서 계산한 기대값(같은 판정 규칙 · 화면 코드를 부르지 않음)."""
    o = cx.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    pid, st = o["project_id"], str(o["status"] or "").upper()
    E = {}
    q = cx.execute("SELECT id, created_at FROM project_quote_files WHERE project_id=? AND order_id=? AND removed_at IS NULL ORDER BY id DESC",
                   (pid, oid)).fetchall() if (pid and st != "CANCELLED") else []
    if q:
        E["quote"] = ("done", ("%d장 · %s" % (len(q), q[0][1][:10])) if len(q) > 1 else "올림 · %s" % q[0][1][:10], ("/quotes/%d" % q[0][0]) if can_sales else None)
    else:
        E["quote"] = ("wait", "없음", None)
    kr = {"CONFIRMED": "수주확정", "IN_PRODUCTION": "진행중", "SHIPPED": "출하", "PAID": "수금완료", "READY_TO_SHIP": "납품대기", "INVOICED": "송장발행", "DRAFT": "임시", "CANCELLED": "취소"}
    E["order"] = ("now", "지금 보는 것 · %s · %s" % (str(o["order_date"])[:10], kr.get(st, st)), None)
    live = [r[0] for r in cx.execute("SELECT id FROM orders WHERE project_id=? AND COALESCE(order_no,'')<>'' AND UPPER(COALESCE(status,''))<>'CANCELLED'", (pid,))] if pid else []
    prs = []
    if pid:
        for r in cx.execute("SELECT id, COALESCE(order_ids,''), created_at FROM prod_requests WHERE project_id=? AND cancelled_at IS NULL ORDER BY id DESC", (pid,)):
            ids = [int(x) for x in str(r[1]).replace(";", ",").split(",") if x.strip().isdigit()]
            if (oid in ids) if ids else (live == [oid]):
                prs.append(r)
    E["prod"] = (("done", ("%d장 · " % len(prs) if len(prs) > 1 else "발행 · ") + prs[0][2][:10], "/project/%d/prod-request/edit?prid=%d" % (pid, prs[0][0]))
                 if prs else ("wait", "없음", None))
    items = cx.execute("SELECT unit_status, COALESCE(status_date,'') FROM order_items WHERE order_id=?", (oid,)).fetchall()
    ns = sum(1 for x in items if x[0] == "출하")
    sd = sorted(x[1][:10] for x in items if x[0] == "출하" and x[1].strip())
    old = cx.execute("SELECT COUNT(*), MAX(shipped_at) FROM shipments WHERE order_id=?", (oid,)).fetchone()
    unit = "품목" if str(o["so_type"] if "so_type" in o.keys() else "").upper() == "PARTS_EXPORT" else "호기"
    if ns or old[0]:
        last = sd[-1] if sd else str(old[1] or "")[:10]
        txt = ("%s 모두" % unit) if (ns and ns == len(items)) else (("%d / %d %s" % (ns, len(items), unit)) if ns else "%d건" % old[0])
        E["ship"] = ("done" if (not ns or ns == len(items)) else "part", txt + ((" · " + last) if last else ""), ("/project/%d" % pid) if pid else None)
    else:
        E["ship"] = ("wait", "없음", None)
    tis = set()
    for r in cx.execute("SELECT * FROM order_items WHERE order_id=?", (oid,)):
        for n in range(1, 11):
            dv = str(r["tax_invoice_date" if n == 1 else "tax_invoice_date%d" % n] or "").strip()[:10]
            av = r["tax_invoice_amt%d" % n]
            if dv and av:
                tis.add((dv, n))
    E["ti"] = (("done", "%d장 · %s" % (len(tis), max(d for d, _ in tis)), "#so-ti") if tis else ("wait", "없음", None))
    rps = sorted(str(r[0] or "")[:10] for r in cx.execute("SELECT received_at FROM receipts_payment WHERE order_id=?", (oid,)))
    if st == "PAID":
        E["pay"] = ("done", "입금 완료" + ((" · " + rps[-1]) if rps else ""), "#so-rcv")
    elif rps:
        E["pay"] = ("?", "%d건 · %s" % (len(rps), rps[-1]), "#so-rcv")   # 미수 남음 여부 = 화면 미수금 칸과 같은 계산(아래에서 맞춰 봄)
    else:
        E["pay"] = ("wait", "없음", None)
    return E


def compare(html, E, tag):
    got, conns = parse_chain(html)
    check(list(got) == ["quote", "order", "prod", "ship", "ti", "pay"], "%s 칸 6개 · 순서 견적→수주→제작요청→출하→세금계산서→입금" % tag, list(got))
    for k, (st, sub, href) in E.items():
        g = got.get(k) or {}
        if st == "?":   # 입금 일부/다 받음 — 미수 남음이면 part + 「· 미수 남음」
            ok = (g.get("st") == "part" and g.get("sub") == sub + " · 미수 남음") or (g.get("st") == "done" and g.get("sub") == sub)
            check(ok and g.get("href") == href, "%s %s = %s" % (tag, k, g.get("sub")), (g, sub))
        else:
            check(g.get("st") == st and g.get("sub") == sub and g.get("href") == href, "%s %s = %s %s" % (tag, k, st, sub), (g, (st, sub, href)))
    sts = [got[k]["st"] for k in ("quote", "order", "prod", "ship", "ti", "pay") if k in got]
    want = [(i + 1 < len(sts)) and sts[i] != "wait" and sts[i + 1] != "wait" for i in range(len(sts) - 1)]
    check(conns == want, "%s 사선 = 앞뒤 칸 모두 있으면 빨강 · 아니면 회색 점선" % tag, (conns, want))
    for k in ("ti", "pay"):
        if (got.get(k) or {}).get("href"):
            check(('id="%s"' % got[k]["href"][1:]) in html, "%s %s 칸 → 같은 화면 아래 표(%s)가 있음" % (tag, k, got[k]["href"]))
    return got


print("§3 B 수주 상세 「N 연결」(가상 수주 5개)")
CUR["u"] = CEO
cx = sqlite3.connect(D.DB_PATH); cx.row_factory = sqlite3.Row
WANT = {
    6001: {"quote": ("done", "2장 · 2026-09-25", "/quotes/52"), "prod": ("done", "발행 · 2026-10-02", "/project/701/prod-request/edit?prid=41"),
           "ship": ("done", "호기 모두 · 2026-10-25", "/project/701"), "ti": ("done", "2장 · 2026-10-26", "#so-ti"), "pay": ("done", "입금 완료 · 2026-11-20", "#so-rcv")},
    6002: {"quote": ("wait", "없음", None), "prod": ("wait", "없음", None), "ship": ("wait", "없음", None), "ti": ("wait", "없음", None), "pay": ("wait", "없음", None)},
    6003: {"quote": ("wait", "없음", None), "prod": ("wait", "없음", None), "ship": ("part", "1 / 2 호기 · 2026-11-01", "/project/702"),
           "ti": ("done", "1장 · 2026-11-02", "#so-ti"), "pay": ("part", "1건 · 2026-11-10 · 미수 남음", "#so-rcv")},
    6004: {"quote": ("done", "올림 · 2026-10-10", "/quotes/55"), "prod": ("done", "발행 · 2026-10-12", "/project/703/prod-request/edit?prid=43"),
           "ship": ("done", "호기 모두 · 2026-11-05", "/project/703"), "ti": ("done", "2장 · 2026-11-16", "#so-ti"), "pay": ("wait", "없음", None)},
    6005: {"quote": ("wait", "없음", None), "prod": ("wait", "없음", None), "ship": ("done", "1건 · 2026-11-11", "/project/704"),
           "ti": ("wait", "없음", None), "pay": ("wait", "없음", None)},
}
NOTE = {6001: "견적2·제작요청·출하 전부·계산서2·입금 완료", 6002: "관리번호 수주 둘 · 번호 없는 옛 제작요청(애매)·옛 관리번호 견적 → 없음",
        6003: "지운 견적 · 출하 일부 · 계산서 1 · 일부 입금", 6004: "베트남 고객 USD · 수주 하나라 번호 없는 제작요청 연결", 6005: "옛 출하 표만 · 취소된 제작요청"}
for oid, W in WANT.items():
    h0 = db_hash()
    r = cl.get("/sales/orders/%d" % oid)
    check(r.status_code == 200, "수주 %d 상세 열림 (%s)" % (oid, NOTE[oid]), r.status_code)
    E = expect(cx, oid)
    for k, v in W.items():   # 손으로 적은 답 = DB 로 따로 계산한 답(시험 자신 점검)
        e = E[k]
        same = (e == v) or (e[0] == "?" and v[0] in ("part", "done") and v[1].startswith(e[1]) and v[2] == e[2])
        check(same, "  └ 시험 자신 점검 %d %s: DB 계산 = 손 답" % (oid, k), (e, v))
    got = compare(r.text, E, "  수주 %d" % oid)
    for k, v in W.items():
        g = got.get(k) or {}
        check((g.get("st"), g.get("sub"), g.get("href")) == v, "  수주 %d %s 화면 = %s" % (oid, k, v[1]), (g, v))
    check(db_hash() == h0, "  수주 %d 화면 열기 전후 DB 같음(읽기만)" % oid)
    if oid == 6003:
        check('data-chain="quote"' in r.text and "quotes/54" not in r.text and "quotes/53" not in r.text, "  지운 견적(54)·수주 번호 없는 옛 견적(53)은 잇지 않음")
CUR["u"] = STAFF
r = cl.get("/sales/orders/6001")
g, _ = parse_chain(r.text)
check(r.status_code == 200 and g.get("quote", {}).get("st") == "done" and g["quote"]["href"] is None and "/quotes/" not in r.text,
      "금액 못 보는 직원 = 견적 칸 있음·링크 없음(견적서 화면이 막혀 있음)", g.get("quote"))
CUR["u"] = CEO
r = cl.get("/sales/orders/6001")
_ic, _ik, _ih = r.text.find('data-dn="so-chain"'), r.text.find('data-dn="kpi-bento"'), r.text.find('</header>')
check(0 <= _ih < _ic < _ik, "자리 = 제목 띠(header) 밖 바로 아래 · 숫자 칸(KPI) 위 — 제목 띠 높이 그대로", (_ih, _ic, _ik))
cs = rd("static/css/knk-components.css")
blk = cs[cs.find(".k-chain{"):cs.find("/* ── 회사 표식 ④")]
check("a.k-chain-item{" in blk and ".k-chain-item.part{" in blk and "@media (max-width:640px)" in blk and not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", blk),
      "공용 N 연결 모양(누르는 칸·일부·휴대폰 줄바꿈) = knk-components.css · 색 = var(--knk-*) 만")
sd = rd("app/templates/sales_order_detail.html")
check('class="k-chain"' in sd and 'id="so-ti"' in sd and 'id="so-rcv"' in sd, "수주 상세 = 공용 .k-chain · 세금계산서·수금 표 자리 표시")
r = cl.get("/sales/orders/6001")
check(re.search(r'data-chain="ti"[^>]*onclick="var t=document.getElementById\(\'so-ti\'\);if\(t\)\{event.preventDefault\(\);t.scrollIntoView', r.text)
      and re.search(r'data-chain="pay"[^>]*onclick="var t=document.getElementById\(\'so-rcv\'\)', r.text),
      "같은 화면 아래 표로 가는 칸 = 주소(#)를 바꾸지 않고 내려감(주소가 바뀌면 부분 전환이 본문을 다시 받아 맨 위로 감)")

# ── §4 (선택) 실제 자료 사본 서버 ──
RDB, RURL = os.environ.get("KNK_Z206_REAL_DB"), os.environ.get("KNK_Z206_REAL_URL")
if RDB and RURL:
    print("§4 실제 자료 사본 대조 (%s)" % RURL)
    rx = sqlite3.connect("file:%s?mode=ro" % RDB, uri=True); rx.row_factory = sqlite3.Row
    can_sales = os.environ.get("KNK_Z206_CAN_SALES", "1") == "1"
    picks = []

    def pick(label, sql):
        r = rx.execute(sql).fetchone()
        if r:
            picks.append((label, r[0]))
        else:
            print("  (없음)", label)
    pick("견적 있음", "SELECT o.id FROM orders o JOIN project_quote_files f ON f.order_id=o.id AND f.project_id=o.project_id AND f.removed_at IS NULL ORDER BY o.id LIMIT 1")
    pick("견적 있음·제작요청 번호로", "SELECT o.id FROM orders o JOIN prod_requests p ON p.project_id=o.project_id AND p.cancelled_at IS NULL AND (','||p.order_ids||',') LIKE '%,'||o.id||',%' ORDER BY o.id DESC LIMIT 1")
    pick("제작요청 번호 없음(옛 요청서)", "SELECT o.id FROM orders o JOIN prod_requests p ON p.project_id=o.project_id AND p.cancelled_at IS NULL AND COALESCE(p.order_ids,'')='' ORDER BY o.id LIMIT 1")
    pick("취소된 제작요청서", "SELECT o.id FROM orders o JOIN prod_requests p ON p.project_id=o.project_id AND p.cancelled_at IS NOT NULL ORDER BY o.id LIMIT 1")
    pick("입금 완료(PAID)", "SELECT id FROM orders WHERE status='PAID' ORDER BY id DESC LIMIT 1")
    pick("출하 일부", "SELECT o.id FROM orders o WHERE (SELECT COUNT(*) FROM order_items i WHERE i.order_id=o.id AND i.unit_status='출하') BETWEEN 1 AND (SELECT COUNT(*) FROM order_items i WHERE i.order_id=o.id)-1 ORDER BY o.id DESC LIMIT 1")
    pick("출하 없음", "SELECT o.id FROM orders o WHERE NOT EXISTS(SELECT 1 FROM order_items i WHERE i.order_id=o.id AND i.unit_status='출하') AND COALESCE(o.status,'')<>'CANCELLED' ORDER BY o.id DESC LIMIT 1")
    pick("계산서 있고 입금 없음", "SELECT o.id FROM orders o WHERE COALESCE(o.status,'') NOT IN ('PAID','CANCELLED') AND EXISTS(SELECT 1 FROM order_items i WHERE i.order_id=o.id AND COALESCE(i.tax_invoice_date,'')<>'') AND NOT EXISTS(SELECT 1 FROM receipts_payment r WHERE r.order_id=o.id) ORDER BY o.id DESC LIMIT 1")
    pick("일부 입금(PAID 아님)", "SELECT o.id FROM orders o WHERE COALESCE(o.status,'') NOT IN ('PAID','CANCELLED') AND EXISTS(SELECT 1 FROM receipts_payment r WHERE r.order_id=o.id) ORDER BY o.id DESC LIMIT 1")
    pick("베트남 고객 수주", "SELECT o.id FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.country='Vietnam' ORDER BY o.id DESC LIMIT 1")
    pick("USD 수출 수주", "SELECT o.id FROM orders o WHERE o.currency='USD' AND EXISTS(SELECT 1 FROM order_items i WHERE i.order_id=o.id AND i.is_export=1) ORDER BY o.id LIMIT 1")
    pick("상품(부품) 수주", "SELECT id FROM orders WHERE UPPER(COALESCE(so_type,''))='PARTS_EXPORT' ORDER BY id DESC LIMIT 1")
    for label, oid in picks:
        html = urllib.request.urlopen(RURL.rstrip("/") + "/sales/orders/%d" % oid, timeout=120).read().decode("utf-8")
        E = expect(rx, oid, can_sales)
        compare(html, E, "  [%s] 수주 %d" % (label, oid))
else:
    print("§4 건너뜀 — KNK_Z206_REAL_DB · KNK_Z206_REAL_URL 없음(실제 자료 사본 서버 대조는 선택)")

print("\n결과: ✅ %d · ❌ %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
