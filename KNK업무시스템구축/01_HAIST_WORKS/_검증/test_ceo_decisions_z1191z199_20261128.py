# -*- coding: utf-8 -*-
"""z1191z199 대표 결정 3가지(2026-11-28 08시대) — 시험 사본(임시 DB · 가상 직원 · 운영 DB 아님)
   §1 홈 「이번 달 수주」 카드 = 매출 홈 수주매출과 같은 공용 계산(_sales_3way) · 같은 기간(이번 달 1일~오늘 vs 작년 같은 달 1일~같은 날)
      · 작년 같은 기간이 0 이면 비교 글 안 보임 · 취소 수주 제외 · 관리번호 처음 등록 금액(projects.order_amount)은 쓰지 않음
   §2 「일 순서 만들기」(/workflow) = 대표 김정락(users.id 85)만 — 메뉴 · 허브 · 만들기 길잡이(GET·POST) · 홈/일일업무의 일 자세히는 그대로
   §3 권한 없을 때 말없이 /home 으로 보내던 곳 196줄 = /home?no_perm=<키>(센터 안내) · 로그인 풀림 = 로그인 화면 · 권한 있으면 그대로 열림"""
import calendar, contextlib, io, json, os, re, sys, tempfile
from datetime import datetime, timezone, timedelta
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z199-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D   # noqa: E402
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_z199_"), "t.db")
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


T = datetime.now(timezone(timedelta(hours=9))).date()   # 본사 시간
LY = T.year - 1
LD = min(T.day, calendar.monthrange(LY, T.month)[1])
LMEND = calendar.monthrange(LY, T.month)[1]

with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_vi", "TEXT")]:   # name_vi = 운영엔 있음(시험 사본만 더함)
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    cols = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    tid = [r[0] for r in c.execute("SELECT id FROM teams ORDER BY id LIMIT 2")]

    def mk(uid, name, role, flags=0, team=None):
        d = {"id": uid, "name": name, "role": role, "login_id": "u%d" % uid, "password": "sso_only_no_local_password", "is_active": 1,
             "password_version": 1, "can_view_logistics": flags, "can_use_logistics": flags, "can_view_sales": 0, "can_use_sales": 0,
             "team_id": team}
        d = {k: v for k, v in d.items() if k in cols}
        c.execute("INSERT INTO users (%s) VALUES (%s)" % (",".join(d), ",".join("?" * len(d))), list(d.values()))
        return dict(c.execute("SELECT u.*, t.name AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.id=?", (uid,)).fetchone())
    OWNER = mk(85, "가상대표", "ceo")
    OTHER_CEO = mk(2, "다른대표역할", "ceo")
    ADMIN = mk(30, "가상관리자", "admin")
    NOPE = mk(40, "권한없는직원", "member")
    LOGI = mk(41, "자재권한직원", "member", flags=1)
    LEADER = mk(42, "가상팀장", "leader", team=tid[0] if tid else None)
    # 매출 자료(가상) — 이번 달 1일 · 작년 같은 달 1일 · (오늘 뒤 날짜는 작년 같은 기간에서 빠져야 함) · 취소 수주
    pc = {r[1] for r in c.execute("PRAGMA table_info(projects)")}

    def proj(pid, code, amt, od):
        d = {"id": pid, "mgmt_code": code, "name": "가상프로젝트%d" % pid, "order_amount": amt, "order_date": od, "currency": "KRW", "is_archived": 0}
        d = {k: v for k, v in d.items() if k in pc}
        c.execute("INSERT INTO projects (%s) VALUES (%s)" % (",".join(d), ",".join("?" * len(d))), list(d.values()))
    oc = {r[1] for r in c.execute("PRAGMA table_info(orders)")}
    ic = {r[1] for r in c.execute("PRAGMA table_info(order_items)")}

    def so(oid, pid, od, amt, status="CONFIRMED", ccy="KRW"):
        d = {"id": oid, "project_id": pid, "order_no": "SO-T%d" % oid, "order_date": od, "status": status, "currency": ccy, "total_amount": amt}
        d = {k: v for k, v in d.items() if k in oc}
        c.execute("INSERT INTO orders (%s) VALUES (%s)" % (",".join(d), ",".join("?" * len(d))), list(d.values()))
        e = {"order_id": oid, "amount": amt, "unit_status": "", "order_date": od, "currency": ccy}
        e = {k: v for k, v in e.items() if k in ic}
        c.execute("INSERT INTO order_items (%s) VALUES (%s)" % (",".join(e), ",".join("?" * len(e))), list(e.values()))
    THIS1 = "%04d-%02d-01" % (T.year, T.month)
    LAST1 = "%04d-%02d-01" % (LY, T.month)
    proj(901, "KNKT-901", 999999999, THIS1)      # 관리번호 처음 등록 금액(쓰면 안 됨)
    so(9001, 901, THIS1, 3000000)                # 이번 달 수주
    so(9002, 901, THIS1, 700000)                 # 추가 수주(같은 프로젝트)
    so(9003, 901, THIS1, 5000000, status="CANCELLED")   # 취소 — 빼야 함
    proj(902, "KNKT-902", 888888888, LAST1)
    so(9004, 902, LAST1, 2000000)                # 작년 같은 달 1일
    LATE = None
    if LD < LMEND:                               # 작년 같은 달 「오늘 뒤」 날 — 같은 기간 비교에서 빠져야 함
        LATE = "%04d-%02d-%02d" % (LY, T.month, LD + 1)
        so(9005, 902, LATE, 40000000)

import app.main as M   # noqa: E402
from fastapi.testclient import TestClient   # noqa: E402
CUR = {"u": None}
M.get_user = lambda request: CUR["u"]
# 일 순서(workflow_builder) 경로는 등록 때 받은 get_user 를 쓰므로 그 칸도 시험 사용자로 바꾼다
for _r in M.app.routes:
    if getattr(_r, "path", "").startswith("/workflow"):
        for _cell in (getattr(_r.endpoint, "__closure__", None) or ()):
            try:
                if callable(_cell.cell_contents) and getattr(_cell.cell_contents, "__name__", "") == "get_user":
                    _cell.cell_contents = lambda request: CUR["u"]
            except ValueError:
                pass
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
cl = TestClient(M.app)
cl_safe = TestClient(M.app, raise_server_exceptions=False)   # 막히지 않아 저장까지 가면(원래 판) 500 으로 받는다


def loc(r):
    return (r.status_code, r.headers.get("location"))


print("§1 홈 「이번 달 수주」 = 매출 홈 수주매출 · 같은 기간")
CUR["u"] = OWNER
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    full_this = M._sales_3way(c, rates, {}, "month", str(T.year), "1", str(T.month))["kpi"]["order"]
    try:
        same_last = M._sales_3way(c, rates, {}, "month", str(LY), "1", str(T.month), day_to=LD)["kpi"]["order"]
    except TypeError as _e:
        same_last = "day_to 없음(%s)" % _e
    full_last = M._sales_3way(c, rates, {}, "month", str(LY), "1", str(T.month))["kpi"]["order"]
check(full_this == 3700000, "이번 달 수주 = 수주 둘(추가 수주 포함) · 취소 제외 · 관리번호 금액 안 씀 = 3,700,000", full_this)
check(same_last == 2000000, "작년 같은 기간(1~%d일) = 2,000,000(그 뒤 날짜 빠짐)" % LD, same_last)
if LATE:
    check(full_last == 42000000, "작년 같은 달 전체 = 42,000,000(같은 기간 계산과 다름 확인)", full_last)
h = cl.get("/home").text
want = "{:,.0f}".format(3700000)
check(want in h and "999,999,999" not in h, "홈 카드 숫자 = 3,700,000(관리번호 처음 등록 금액 999,999,999 아님)",
      re.findall(r"이번 달 수주</div>\s*<div[^>]*>([^<]*)<", h))
exp_pct = round((3700000 - 2000000) / 2000000 * 100, 1)
txt = "작년 같은 기간(1~%d일) 대비 %+.1f%%" % (LD, exp_pct)
check(txt in h, "비교 글 = 「%s」" % txt, re.findall(r'card-trend[^>]*>([^<]*(?:대비|동월)[^<]*)<', h))
check("전년 동월" not in h, "옛 글 「전년 동월」 없음")
s = cl.get("/sales?mode=month&year=%d&m=%d" % (T.year, T.month)).text
check(want in s, "매출 홈(월간 · 이번 달) 수주매출에 같은 숫자 3,700,000")
try:
    with D.db_session() as c:
        home_this = M._sales_3way(c, rates, {}, "month", str(T.year), "1", str(T.month), day_to=T.day)["kpi"]["order"]
except TypeError as _e:
    home_this = "day_to 없음"
check(home_this == full_this, "이번 달 1일~오늘 = 매출 홈 이번 달(오늘 뒤 날짜 수주 없음)", (home_this, full_this))
with D.db_session() as c:   # 작년 같은 기간 0 → 비교 글 숨김
    c.execute("UPDATE orders SET status='CANCELLED' WHERE id=9004")   # 작년 같은 기간 수주를 취소로(그 뒤 날짜 9005 는 기간 밖)
h0 = cl.get("/home").text
check("작년 같은 기간" not in h0 and "전년 동월" not in h0 and want in h0, "작년 같은 기간 0 → 비교 글 안 보임(숫자는 그대로)")
CUR["u"] = NOPE
check("이번 달 수주" not in cl.get("/home").text, "경영진이 아니면 카드 없음(is_executive 그대로)")

print("§2 「일 순서 만들기」 = 대표(85)만")
MENU = re.compile(r'href="/workflow"')
for who, u in (("대표(85)", OWNER), ("다른 대표 역할(2)", OTHER_CEO), ("관리자(30)", ADMIN), ("팀장", LEADER), ("일반 직원", NOPE)):
    CUR["u"] = u
    hh = cl.get("/home").text
    on = bool(MENU.search(hh))
    check(on == (u is OWNER), "%s 메뉴 「일 순서 만들기」 %s" % (who, "보임" if u is OWNER else "없음"), on)
    r1, r2 = cl.get("/workflow", follow_redirects=False), cl.get("/workflow/wizard", follow_redirects=False)
    r3 = None if u is OWNER else cl_safe.post("/workflow/wizard", data={"project_id": "1", "customer_country": "KR", "po_entity": "KR", "mech_design_split": "KR",
                                           "elec_design_split": "KR", "sw_design_split": "KR"}, follow_redirects=False)
    if u is OWNER:
        check(r1.status_code == 200 and r2.status_code == 200, "대표 허브·길잡이 열림", (r1.status_code, r2.status_code))
    else:
        for nm, r in (("허브 GET /workflow", r1), ("길잡이 GET", r2), ("길잡이 저장 POST", r3)):
            check(loc(r) == (303, "/home?no_perm=page"), "%s %s → /home?no_perm=page(안내)" % (who, nm), loc(r))
CUR["u"] = NOPE
r = cl.get("/workflow/node/999999", follow_redirects=False)
check(loc(r) != (303, "/home?no_perm=page"), "일 자세히(/workflow/node/…) = 홈·일일업무에서 쓰므로 막지 않음", loc(r))
r = cl.get("/workflow/my", follow_redirects=False)
check(r.status_code == 200, "내 할 일(/workflow/my) 그대로 열림", r.status_code)
CUR["u"] = None
check(loc(cl.get("/workflow", follow_redirects=False)) == (303, "/login"), "로그인 풀림 → 로그인 화면")
ch = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "chrome.html"), encoding="utf-8").read()
check("{% if user.id == 85 %}{{ a('/workflow'," in ch and "{% if _is_pm %}{{ a('/workflow'," not in ch, "메뉴 줄 조건 = user.id == 85 (_is_pm 은 다른 곳 그대로)")
check("k === 'page' ? CH.no_perm_page" in ch, "토스트 키 page = 「이 화면을 볼 권한이 없습니다」")
i18 = open(os.path.join(ROOT, "app", "i18n.py"), encoding="utf-8").read()
check('"ch_no_perm_page": {"ko": "이 화면을 볼 권한이 없습니다."' in i18, "한·베 문구(ch_no_perm_page)")
for f in ("node_detail.html", "project.html"):
    t = open(os.path.join(ROOT, "app", "templates", "workflow", f), encoding="utf-8").read()
    bare = [m.start() for m in re.finditer(r'href="/workflow(?:/wizard[^"]*)?"', t)]
    guarded = all("user.id == 85" in t[max(0, i - 400):i] for i in bare)
    check(bare and guarded, "workflow/%s 안 허브·길잡이 링크 = 대표만" % f, len(bare))

print("§3 권한 없음 → /home?no_perm=<키> · 로그인 풀림 → 로그인 · 권한 있으면 그대로")
ROUTES = json.loads(r'''[["GET", "/team/permissions", "page", "P", "nope"], ["GET", "/team/{team_id:int}/permissions", "page", "P", "nope"], ["POST", "/team/{team_id:int}/permissions", "page", "P", "nope"], ["POST", "/team/{team_id:int}/permissions", "page", "P", "leader_other"], ["GET", "/suppliers/export.xlsx", "page", "P", "nope"], ["GET", "/parts/import", "logistics", "P", "nope"], ["POST", "/parts/import", "logistics", "P", "nope"], ["POST", "/parts/import/apply", "logistics", "P", "nope"], ["POST", "/parts/import/marked-xlsx", "logistics", "P", "nope"], ["GET", "/parts/import/template.xlsx", "logistics", "P", "nope"], ["GET", "/parts", "logistics", "P", "nope"], ["GET", "/parts/new", "logistics", "P", "nope"], ["POST", "/parts/new", "logistics", "P", "nope"], ["GET", "/parts/reclassify", "logistics", "P", "nope"], ["POST", "/parts/reclassify/apply", "logistics", "P", "nope"], ["GET", "/parts/dedup", "logistics", "P", "nope"], ["POST", "/parts/dedup/merge", "logistics", "P", "nope"], ["POST", "/parts/dedup/dismiss", "logistics", "P", "nope"], ["POST", "/parts/dedup/dismiss/undo", "logistics", "P", "nope"], ["POST", "/parts/dedup/unmerge/{log_id}", "logistics", "P", "nope"], ["GET", "/projects/{pid:int}/baseline", "logistics", "P", "nope"], ["GET", "/bom/tools", "logistics", "P", "nope"], ["GET", "/bom/tools/download/{run_id:int}", "logistics", "P", "nope"], ["GET", "/projects/{pid:int}/bom", "logistics", "P", "nope"], ["GET", "/bom/uploads/{uid:int}/report", "logistics", "P", "nope"], ["POST", "/bom/items/{iid:int}/edit", "logistics", "P", "nope"], ["POST", "/projects/{pid:int}/bom/buyat", "logistics", "P", "nope"], ["POST", "/projects/{pid:int}/bom/purge", "logistics", "P", "nope"], ["GET", "/projects/{pid:int}/bom/export.xlsx", "logistics", "P", "nope"], ["GET", "/parts/{pid}/qr/print", "logistics", "P", "nope"], ["GET", "/po/{po_id}/qr/print", "logistics", "P", "nope"], ["GET", "/parts/{pid}/edit", "logistics", "P", "nope"], ["POST", "/parts/{pid}/edit", "logistics", "P", "nope"], ["POST", "/parts/{pid}/delete", "logistics", "P", "nope"], ["GET", "/suppliers", "logistics", "P", "nope"], ["GET", "/suppliers/new", "logistics", "P", "nope"], ["POST", "/suppliers/new", "logistics", "P", "nope"], ["GET", "/suppliers/{sid}/edit", "logistics", "P", "nope"], ["POST", "/suppliers/{sid}/edit", "logistics", "P", "nope"], ["POST", "/suppliers/{sid}/delete", "logistics", "P", "nope"], ["GET", "/suppliers/import", "logistics", "P", "nope"], ["POST", "/suppliers/import", "logistics", "P", "nope"], ["POST", "/suppliers/import/apply", "logistics", "P", "nope"], ["GET", "/suppliers/import/template.xlsx", "logistics", "P", "nope"], ["GET", "/po", "logistics", "P", "nope"], ["GET", "/po/new", "logistics", "P", "nope"], ["POST", "/po/new", "logistics", "P", "nope"], ["GET", "/po/{po_id}", "logistics", "P", "nope"], ["GET", "/po/{po_id}/edit", "logistics", "P", "nope"], ["POST", "/po/{po_id}/edit", "logistics", "P", "nope"], ["POST", "/po/{po_id}/delete", "logistics", "P", "nope"], ["GET", "/rates", "logistics", "P", "nope"], ["POST", "/rates/new", "logistics", "P", "nope"], ["POST", "/parts/{pid}/prices/new", "logistics", "P", "nope"], ["GET", "/parts/{pid:int}", "logistics", "P", "nope"], ["GET", "/po/{po_id}/receive", "logistics", "P", "nope"], ["POST", "/po/{po_id}/receive", "logistics", "P", "nope"], ["GET", "/stock/issue", "logistics", "P", "skip"], ["POST", "/stock/issue", "logistics", "P", "skip"], ["GET", "/stock/adjust", "logistics", "P", "nope"], ["POST", "/stock/adjust", "logistics", "P", "nope"], ["POST", "/parts/{pid}/attach", "logistics", "P", "nope"], ["GET", "/parts/{pid}/attachments/{aid}", "logistics", "P", "nope"], ["POST", "/parts/{pid}/attachments/{aid}/delete", "logistics", "P", "nope"], ["GET", "/stock/movements", "logistics", "P", "nope"], ["POST", "/po/{po_id}/items/{iid}/link-project", "logistics", "P", "nope"], ["POST", "/po/links/{link_id}/delete", "logistics", "P", "nope"], ["GET", "/bom/upload", "page", "P", "nope"], ["POST", "/bom/upload", "page", "P", "nope"], ["POST", "/bom/upload/apply", "page", "P", "nope"], ["GET", "/project/{pid:int}/units", "page", "P", "nope"], ["GET", "/project/{pid:int}/units/candidates", "page", "P", "nope"], ["POST", "/project/{pid:int}/units/candidates/apply", "page", "P", "nope"], ["POST", "/project/{pid:int}/units/create", "page", "P", "nope"], ["POST", "/units/{unit_id:int}/unit-no", "page", "P", "nope"], ["POST", "/units/{unit_id:int}/confirm", "page", "P", "nope"], ["POST", "/units/{unit_id:int}/cancel", "page", "P", "nope"], ["POST", "/units/{unit_id:int}/order-link", "page", "P", "nope"], ["GET", "/project/{pid:int}/units/status-sync", "page", "P", "nope"], ["POST", "/project/{pid:int}/units/status-sync/apply", "page", "P", "nope"], ["GET", "/suppliers", "page", "P", "logi_nosup"], ["GET", "/suppliers/new", "page", "P", "logi_nosup"], ["POST", "/suppliers/new", "page", "P", "logi_nosup"], ["GET", "/suppliers/{sid}/edit", "page", "P", "logi_nosup"], ["POST", "/suppliers/{sid}/edit", "page", "P", "logi_nosup"], ["POST", "/suppliers/{sid}/delete", "page", "P", "logi_nosup"], ["GET", "/suppliers/import", "page", "P", "logi_nosup"], ["POST", "/suppliers/import", "page", "P", "logi_nosup"], ["POST", "/suppliers/import/apply", "page", "P", "logi_nosup"], ["GET", "/suppliers/import/template.xlsx", "page", "P", "logi_nosup"], ["GET", "/stock/audits", "page", "P", "nope"], ["POST", "/stock/audits/new", "page", "P", "nope"], ["GET", "/stock/audits/{audit_id:int}", "page", "P", "nope"], ["POST", "/stock/audits/{audit_id}/items", "page", "P", "nope"], ["GET", "/stock/adjustments", "page", "P", "nope"], ["POST", "/stock/adjustments/{adj_id}/attach", "page", "P", "nope"], ["GET", "/stock/adjustments/{adj_id}/attachments", "page", "P", "nope"], ["GET", "/stock/adjustments/{adj_id}/attachments/{att_id}/download", "page", "P", "nope"], ["GET", "/fx/rates", "page", "P", "nope"], ["POST", "/fx/rates", "page", "P", "nope"], ["GET", "/parts/{part_id}/prices", "page", "P", "nope"], ["POST", "/parts/{part_id}/prices", "page", "P", "nope"], ["GET", "/consumables/{co_id:int}/export.xlsx", "page", "P", "nope"], ["GET", "/consumables", "page", "P", "nope"], ["GET", "/consumables/new", "page", "P", "nope"], ["POST", "/consumables/create-direct", "page", "P", "nope"], ["GET", "/consumables/import-template", "page", "P", "nope"], ["GET", "/consumables/import-bulk-template", "page", "P", "nope"], ["GET", "/consumables/{co_id:int}", "page", "P", "nope"], ["POST", "/consumables/{co_id:int}/delete", "page", "P", "nope"], ["GET", "/sales/schedule/bulk-template.xlsx", "sales", "P", "nope"], ["GET", "/projects/import-product-template", "sales", "P", "nope"], ["GET", "/sales/schedule/diag", "sales", "P", "nope"], ["GET", "/projects/export.xlsx", "sales", "P", "nope"], ["GET", "/projects/new", "sales", "P", "nope"], ["GET", "/projects/quick", "sales", "P", "nope"], ["GET", "/projects/{pid}/quick-edit", "sales", "P", "nope"], ["GET", "/projects/so-check", "sales", "P", "nope"], ["POST", "/projects/new", "sales", "P", "nope"], ["GET", "/projects/import-template", "sales", "P", "nope"], ["GET", "/projects/import-template/{kind}", "sales", "P", "nope"], ["GET", "/projects/import-template/biz/{biz}", "sales", "P", "nope"], ["GET", "/projects/import-template-mgmt", "sales", "P", "nope"], ["GET", "/as", "sales", "P", "nope"], ["GET", "/as/new", "sales", "P", "nope"], ["POST", "/as/new", "sales", "P", "nope"], ["GET", "/as/{as_id}", "sales", "P", "nope"], ["POST", "/as/{as_id}/status", "sales", "P", "nope"], ["POST", "/as/{as_id}/edit", "sales", "P", "nope"], ["GET", "/customers/import-template", "sales", "P", "nope"], ["GET", "/projects/{pid}/edit", "sales", "P", "nope"], ["POST", "/projects/{pid}/edit", "sales", "P", "nope"], ["GET", "/sales/quotations/export.xlsx", "sales", "G", "nope"], ["GET", "/sales/quotes/new", "sales", "G", "nope"], ["POST", "/sales/quotes/new", "sales", "G", "nope"], ["GET", "/sales/quotes/{qid:int}", "sales", "G", "nope"], ["GET", "/sales/quotations/{quote_id}/print", "sales", "G", "nope"], ["GET", "/sales/production", "sales", "G", "nope"], ["GET", "/sales/shipments-receipts", "sales", "G", "nope"], ["GET", "/sales/dashboard", "sales", "G", "nope"], ["GET", "/sales/forecast", "sales", "G", "nope"], ["GET", "/sales/aging", "sales", "G", "nope"], ["GET", "/stock/balances", "logistics", "G", "nope"], ["GET", "/stock/balances/fifo/{part_id}", "logistics", "G", "nope"], ["GET", "/stock/abc", "logistics", "G", "nope"], ["GET", "/stock/turnover", "logistics", "G", "nope"], ["GET", "/stock/receipts", "logistics", "G", "nope"], ["GET", "/stock/qc/disposition/{qc_id}", "logistics", "G", "nope"], ["GET", "/stock/qc/{po_item_id}", "logistics", "G", "nope"], ["GET", "/stock/issues", "logistics", "G", "nope"], ["GET", "/stock/safety", "logistics", "G", "nope"], ["POST", "/stock/safety/{part_id}", "logistics", "G", "nope"], ["GET", "/stock/reorder-recommendations", "logistics", "G", "nope"], ["GET", "/sales/bank-recon", "page", "G", "nope"], ["POST", "/sales/bank-recon", "page", "G", "nope"], ["GET", "/export/old", "page", "G", "nope"], ["GET", "/export/prep", "page", "G", "nope"], ["GET", "/export/prep/{pid:int}", "page", "G", "nope"], ["GET", "/export/hs-dict/review.xlsx", "page", "G", "nope"], ["GET", "/export/hs-dict", "page", "G", "nope"], ["GET", "/export/hs-fill", "page", "G", "nope"], ["GET", "/export/hs-fill/form/{kind}", "page", "G", "nope"], ["GET", "/export/hs-fill/{lid:int}/download", "page", "G", "nope"], ["GET", "/export/prep/{pid:int}/invoice-pl.xlsx", "page", "G", "nope"], ["GET", "/export/prep/{pid:int}/packing-list", "page", "G", "nope"], ["GET", "/export/prep/{pid:int}/packing-list.xlsx", "page", "G", "nope"], ["GET", "/export/prep/{pid:int}/invoice", "page", "G", "nope"], ["GET", "/export/prep/{pid:int}/invoice.xlsx", "page", "G", "nope"], ["GET", "/export/ship/{pid:int}/qr/print", "page", "G", "nope"], ["GET", "/export/orders/new", "page", "G", "nope"], ["GET", "/export/orders/{eo_id}", "page", "G", "nope"], ["GET", "/export/ci/{eo_id}", "page", "G", "nope"], ["GET", "/export/pl/{eo_id}", "page", "G", "nope"], ["GET", "/export/bl/{eo_id}", "page", "G", "nope"], ["GET", "/export/customs/{eo_id}", "page", "G", "nope"], ["GET", "/export/ci/{ci_id}/print", "page", "G", "nope"], ["GET", "/export/pl/{pl_id}/print", "page", "G", "nope"], ["GET", "/export/bl/{bl_id}/print", "page", "G", "nope"], ["GET", "/export/fta", "page", "G", "nope"], ["GET", "/export/fta/new", "page", "G", "nope"], ["GET", "/export/fta/{cert_id}", "page", "G", "nope"], ["GET", "/export/fta/{cert_id}/print", "page", "G", "nope"], ["GET", "/qc/inspection-reports", "page", "G", "nope"], ["GET", "/qc/inspection-reports/new", "page", "G", "nope"], ["GET", "/qc/inspection-reports/{report_id}", "page", "G", "nope"], ["GET", "/qc/inspection-reports/{report_id}/print", "page", "G", "nope"], ["GET", "/production/work-orders", "page", "G", "nope"], ["GET", "/production/work-orders/new", "page", "G", "nope"], ["GET", "/production/work-orders/{wo_id}", "page", "G", "nope"], ["GET", "/production/work-orders/{wo_id}/print", "page", "G", "nope"], ["GET", "/admin/note-sweep", "page", "G", "nope"], ["POST", "/admin/note-sweep/clear", "page", "G", "nope"], ["GET", "/export", "page", "G", "nope"], ["GET", "/export/s/{no}", "page", "G", "nope"], ["GET", "/export/s/{no}/file/{fid:int}", "page", "G", "nope"], ["GET", "/export/rules", "page", "G", "nope"]]''')
WHO = {"nope": NOPE, "logi_nosup": LOGI, "leader_other": LEADER}
from fastapi.routing import APIRoute   # noqa: E402
RT = {(m, r.path): r for r in M.app.routes if isinstance(r, APIRoute) for m in r.methods}


def url_of(p):
    return re.sub(r"\{(\w+)(:\w+)?\}", lambda m: "T" if m.group(1) == "biz" else ("x" if m.group(1) in ("kind", "no") else "1"), p)


def body_of(meth, p):
    r = RT.get((meth, p))
    data, files = {}, {}
    if r is not None and meth == "POST":
        for bp in r.dependant.body_params:
            ann = repr(getattr(bp, "type_", "")) + repr(getattr(getattr(bp, "field_info", None), "annotation", ""))
            if "UploadFile" in ann:
                files[bp.alias] = ("t.xlsx", b"x", "application/octet-stream")
            else:
                data[bp.alias] = "1"
    return data, files


def hit(meth, url, p):
    data, files = body_of(meth, p)
    if meth == "GET":
        return cl_safe.get(url, follow_redirects=False)
    return cl_safe.post(url, data=data, files=files or None, follow_redirects=False)


bad, tested, static_only = [], 0, []
for meth, p, key, kind, who in ROUTES:
    if who == "skip":
        static_only.append((meth, p)); continue
    if who == "leader_other":
        CUR["u"] = LEADER
        url = p.replace("{team_id:int}", str(tid[1] if len(tid) > 1 else 99999))
    else:
        CUR["u"] = WHO[who]; url = url_of(p)
    r = hit(meth, url, p)
    tested += 1
    if loc(r) != (303, "/home?no_perm=%s" % key):
        bad.append((meth, url, who, loc(r)))
check(not bad, "권한 없는 계정으로 %d곳 → /home?no_perm=<센터 키>" % tested, (len(bad), bad[:12]))
print("     (서버로 못 부르는 곳 = 재고 출고 두 번째 문 — 대표만 통과하는 첫 문 뒤 · 글자로 확인:", static_only, ")")
mn = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check(mn.count('if not can_use_logistics(u):\n        return RedirectResponse("/home?no_perm=logistics", 303)') >= 2, "재고 출고 두 번째 문 = ?no_perm=logistics(글자)")
CUR["u"] = None
badg = []
for meth, p, key, kind, who in ROUTES:
    if kind != "G":
        continue
    url = url_of(p)
    r = hit(meth, url, p)
    if loc(r) != (303, "/login"):
        badg.append((meth, url, loc(r)))
check(not badg, "로그인 풀림 = 로그인 화면(가드 %d곳)" % sum(1 for x in ROUTES if x[3] == "G"), badg[:10])
CUR["u"] = OWNER
okp = ["/parts", "/po", "/suppliers", "/stock/movements", "/as", "/consumables", "/export", "/stock/balances", "/sales/production",
       "/qc/inspection-reports", "/production/work-orders", "/fx/rates", "/rates", "/bom/upload", "/stock/audits", "/stock/adjustments",
       "/export/fta", "/export/prep", "/sales/dashboard", "/sales/forecast", "/stock/safety", "/admin/note-sweep", "/sales/bank-recon",
       "/projects/new", "/parts/import", "/projects/export.xlsx", "/suppliers/export.xlsx", "/team/permissions"]
badk = []
for p in okp:
    r = cl.get(p, follow_redirects=False)
    if r.status_code >= 500 or (r.status_code in (302, 303) and (r.headers.get("location") or "").startswith("/home")):
        badk.append((p, loc(r)))
check(not badk, "대표(85)는 %d곳 그대로 열림(홈으로 안 감 · 오류 없음)" % len(okp), badk)
CUR["u"] = LOGI
badl = [(p, loc(cl.get(p, follow_redirects=False))) for p in ("/parts", "/po", "/stock/movements", "/stock/balances")]
badl = [x for x in badl if x[1][0] != 200]
check(not badl, "자재 권한 직원 = 자재 화면 그대로 열림", badl)
CUR["u"] = NOPE
check(loc(cl.get("/", follow_redirects=False)) == (303, "/home"), "GET / → /home 그대로(정상 이동)")
check(cl.get("/home?no_perm=page").status_code == 200, "돌아온 /home?no_perm=page 정상으로 열림")

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(0 if FAIL == 0 else 1)
