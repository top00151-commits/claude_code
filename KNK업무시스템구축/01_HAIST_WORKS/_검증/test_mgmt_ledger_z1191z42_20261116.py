# -*- coding: utf-8 -*-
"""z1191z42 시험 (대표 2026-11-16 「제작요청서목록 옆에 "관리번호대장" — 지금까지 부여한 관리번호·수주번호를 한번에 ·
  엑셀은 참고만, 이음웍스에 등록된 사항 기준」)
  ① 한 줄 = 관리번호 하나(프로젝트·소모품) · 그 관리번호의 수주번호 전부(취소는 줄 그음) · 수주 없으면 「없음」
  ② 폐기한 프로젝트도 「폐기」로 남김 · 최근 발행 순(연월 ↓ · 번호 ↓) · 소모품 관리번호(C)
  ③ 거르기(사업부·발행 연도·검색 — 수주번호로도) · 권한(매출 못 보면 못 들어옴) · 프로젝트 화면 3곳 탭
  ④ z1191z43: 수주번호 = 링크(?so= 그 수주 기준) · 칸 너비 끌어서 조절
  ⑤ z1191z44: 수주가 여럿이면 최근 수주 하나 + 「▾ 외 N건」(누르면 전부) · 모두 펼치기 · 수주번호로 찾은 줄은 펼친 채
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z42-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z42_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()


def ins(c, table, row):
    cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % table)}
    ks = [k for k in row if k in cols]
    c.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, ",".join('"%s"' % k for k in ks), ",".join("?" * len(ks))), [row[k] for k in ks])
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T942', 'T942', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T942'").fetchone())
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('물류만', 'user', 'T943', 'T943', 'sso_only_no_local_password', 1, 1, 0, 0, 1, 1)")
    NOSALES = dict(c.execute("SELECT * FROM users WHERE employee_no='T943'").fetchone())
    CU = ins(c, "customers", {"name": "주식회사 드림텍", "alias": "드림텍"})

    def proj(code, model, equip, status="수주확정", arch=0, **kw):
        row = {"code": code, "mgmt_code": code, "name": "PBA", "model_name": model, "equip_name": equip, "biz_div": code[3:4] or "T",
               "customer_id": CU, "customer_name": "주식회사 드림텍", "status": status, "is_archived": arch,
               "sales_name": "이현", "server_path": "Z:\\2.검사기\\" + code, "logi_note": "비고 " + code}
        row.update(kw)
        return ins(c, "projects", row)

    def order(pid, no, od, st="CONFIRMED"):
        return ins(c, "orders", {"order_no": no, "project_id": pid, "customer_id": CU, "order_date": od, "status": st})

    P1 = proj("001T2610", "SM-S928U", "OS 검사기"); order(P1, "T-261005-1", "2026-10-05")
    P2 = proj("015T2611", "VMA0386", "VSWR 검사기"); order(P2, "T-261110-1", "2026-11-10"); order(P2, "T-261112-2", "2026-11-12")
    order(P2, "T-261113-9", "2026-11-13", "CANCELLED")
    P3 = proj("003T2611", "SM-X356B", "기능 검사기")                       # 수주 없음
    P4 = proj("002M2511", "HCM STOCKER", "HCM STOCKER", status="출하"); order(P4, "M-251120-1", "2025-11-20", "SHIPPED")
    P5 = proj("009T2611", "옛모델", "폐기된 검사기", arch=1); order(P5, "T-261101-3", "2026-11-01")
    P6 = proj("", "번호 없음", "번호 없는 프로젝트")                          # 관리번호 없음 → 대장에 없음
    for no, st in (("C-261103-2", "CONFIRMED"),):   # 소모품 관리번호는 발주 하나에 하나(UNIQUE)
        ins(c, "consumable_orders", {"co_no": no, "mgmt_code": "004C2611", "customer_name": "주식회사 드림텍", "customer_id": CU,
                                     "currency": "KRW", "total_amount": 1000, "status": st, "biz_div": "T", "order_date": "2026-11-0" + no[-3],
                                     "model_name": "소모품", "equip_name": "핀 2종", "project_name": "SENSOR", "sales_name": "안지연"})

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
CUR = {"u": ADMIN}
M.get_user = lambda request: CUR["u"]
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,)))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


with D.db_session() as c:
    R = M._z42_ledger_rows(c)
B = {x["code"]: x for x in R}

print("§1 한 줄 = 관리번호 하나 · 수주번호")
check([x["code"] for x in R] == ["015T2611", "009T2611", "004C2611", "003T2611", "001T2610", "002M2511"],
      "최근 발행 순(2611 ↓ 번호 ↓ → 2610 → 2511) · 관리번호 없는 프로젝트는 없음", [x["code"] for x in R])
check([s["no"] for s in B["015T2611"]["sos"]] == ["T-261110-1", "T-261112-2", "T-261113-9"] and B["015T2611"]["sos"][2]["cancel"],
      "수주 여럿 = 수주번호 전부(발주일 순) · 취소 표시", B["015T2611"]["sos"])
check(B["003T2611"]["sos"] == [], "수주 없는 관리번호도 줄로(수주번호 없음)")
check(B["009T2611"]["arch"] is True, "폐기한 프로젝트도 남김(폐기 표시)")
c4 = B["004C2611"]
check(c4["kind"] == "C" and [s["no"] for s in c4["sos"]] == ["C-261103-2"] and c4["status"] == "진행중" and c4["sales"] == "안지연",
      "소모품: 관리번호(C) 한 줄 · 소모품 발주번호 · 상태 · 영업 담당", c4)
p2 = B["015T2611"]
check((p2["model"], p2["equip"], p2["cust"], p2["sales"], p2["ym"], p2["biz_label"]) == ("VMA0386", "VSWR 검사기", "드림텍", "이현", "2026-11", "🔬 검사기"),
      "칸: 모델명 · 설비명 · 고객사(시스템명) · 영업 담당 · 발행월 · 사업부(등록 화면 아이콘)", p2)

print("§2 화면")
r = q(cl.get, "/projects/ledger")
h = r.text
check(r.status_code == 200, "관리번호대장 열림", r.status_code)
codes = re.findall(r'class="lg-code" href="[^"]+">([^<]+)</a>', h)
check(codes == [x["code"] for x in R], "표 줄 = 대장 순서", codes)
check(('href="/project/%d"' % P2) in h and "/consumables/" in h, "관리번호 누르면 프로젝트 · 소모품 화면")
check(re.search(r'class="lg-so cancel[^"]*"[^>]*>T-261113-9<', h), "취소 수주번호는 줄 그음")
# z1191z44 (대표 11-17 「수주번호가 여러 개 있는 건 한번에 보이게 하지 말고 … 내리기 버튼 누르면 다 보일 수 있게」)
_p2 = re.search(r'<div class="lg-sos" data-n="3">(.*?)</div>', h, re.S)
_p2h = _p2.group(1) if _p2 else ""
_shown = re.findall(r'<a class="lg-so"[^>]*>([^<]+)</a>', _p2h)
_fold = re.findall(r'<a class="lg-so[^"]*lg-sox"[^>]*>([^<]+)</a>', _p2h)
check(_shown == ["T-261112-2"] and sorted(_fold) == ["T-261110-1", "T-261113-9"],
      "z44: 수주 3건 → 처음엔 가장 최근 수주(취소 아닌 것) 하나만 · 나머지는 접힘", (_shown, _fold))
check('<button type="button" class="lg-more" data-more="2"' in _p2h and "▾ 외 2건" in _p2h, "z44: 「▾ 외 2건」 단추(누르면 전부)")
_p1 = re.search(r'<td>(<a class="lg-so"[^>]*>T-261005-1</a>)</td>', h)
check(_p1 and "lg-more" not in _p1.group(0), "z44: 수주 하나면 그대로(단추 없음)")
check(h.count('class="lg-sos"') == 1 and 'id="lgSoAll"' in h and "수주번호 모두 펼치기" in h, "z44: 위에 「▾ 수주번호 모두 펼치기」 · 접는 칸은 수주 여럿인 줄만")
check(".lg-sos:not(.open) .lg-sox { display:none; }" in h and "classList.add('hit')" in h, "z44: 접힘은 화면 규칙 · 수주번호로 찾으면 그 줄 펼침")
# z1191z43 (대표 「수주번호도 누르면 해당 수주번호에 프로젝트 정보창」): 수주번호 = 링크(그 수주가 메인 카드 · ?so=)
check(('<a class="lg-so" href="/project/%d?so=T-261112-2"' % P2) in h, "z43: 수주번호 누르면 그 프로젝트(그 수주 기준 · ?so=)")
check(re.search(r'<a class="lg-so" href="/consumables/\d+"[^>]*>C-261103-2</a>', h), "z43: 소모품 발주번호 누르면 소모품 화면")
# z1191z43 (대표 「항목별 칸 너비를 조정할수잇게 · 특히 설비명·모델명·프로젝트명」): 모든 칸 머리글에 너비 손잡이 · 기본 너비 colgroup · 처음대로 단추
_rz = re.findall(r'class="lg-rz" data-rz="(\w+)"', h)
check(len(_rz) == 13 and all(k in _rz for k in ("model", "equip", "pname")), "z43: 칸 13개 모두 너비 손잡이(설비명·모델명·프로젝트명 포함)", _rz)
check(re.search(r'<col data-col="model" style="width:\d+px">', h) and 'id="lgRzReset"' in h and "knk.ledger.colw" in h,
      "z43: 기본 너비(colgroup) · 「↺ 칸 너비 처음대로」 · 내 브라우저에 기억")
check('<span class="lg-none">없음</span>' in h, "수주 없으면 「없음」")
check("lg-archb" in h and "폐기" in h, "폐기 표시")
check("관리번호 <b" in h and re.search(r"관리번호 <b[^>]*>6</b>개 · 수주번호 <b[^>]*>6</b>건", h), "요약: 관리번호 6개 · 수주번호 6건(취소 빼고)")
check('<span class="on">📒 관리번호대장</span>' in h, "탭에 관리번호대장(지금 화면)")

print("§3 거르기 · 권한 · 탭")
hm = q(cl.get, "/projects/ledger?biz=M").text
check(re.findall(r'class="lg-code" href="[^"]+">([^<]+)</a>', hm) == ["002M2511"], "사업부 자동화만")
hy = q(cl.get, "/projects/ledger?year=2025").text
check(re.findall(r'class="lg-code" href="[^"]+">([^<]+)</a>', hy) == ["002M2511"], "2025년 발행만")
hq = q(cl.get, "/projects/ledger?q=T-261112-2").text
check(re.findall(r'class="lg-code" href="[^"]+">([^<]+)</a>', hq) == ["015T2611"], "수주번호로 찾기")
hq2 = q(cl.get, "/projects/ledger?q=C-261103").text
check(re.findall(r'class="lg-code" href="[^"]+">([^<]+)</a>', hq2) == ["004C2611"], "소모품 발주번호로 찾기")
check(re.search(r'자동화<b>1</b>', h) and re.search(r'소모품<b>1</b>', h) and re.search(r'전체<b>6</b>', h), "사업부 칩 개수")
CUR["u"] = NOSALES
r2 = q(cl.get, "/projects/ledger")
check(r2.status_code == 303 and "no_perm=sales" in r2.headers.get("location", ""), "매출 권한 없으면 못 들어옴(안내로)", (r2.status_code, r2.headers.get("location")))
CUR["u"] = ADMIN
for path in ("/projects", "/prod-requests"):
    t = q(cl.get, path).text
    check('href="/projects/ledger"' in t and "관리번호대장" in t, "%s 탭에 「📒 관리번호대장」" % path)
src = open(os.path.join(ROOT, "app", "templates", "project_new_chooser.html"), encoding="utf-8").read()
check('href="/projects/ledger"' in src, "등록 화면 탭에도")

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
