# -*- coding: utf-8 -*-
"""z1191z66 시험 (대표 2026-11-19 「관리번호 대장을 엑셀로 다운로드 받을수있게 메뉴 구성해줘」)
  ① 화면 「⬇ 엑셀로 내려받기」 = 지금 조건(사업부·발행 연도·검색) 그대로 · 결과 없으면 단추 없음
  ② 엑셀 = 화면과 같은 줄·순서 · 수주번호 한 칸 줄바꿈(취소 표시) · 폐기 · 맨 위 조건·시각 · 머리 고정·거르기
  ③ 거른 조건 그대로  ④ 「=」 글자 그대로 · 권한(화면과 같음)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z66-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z66_")
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

import openpyxl  # noqa: E402


def xl(url):
    r = q(cl.get, url)
    if r.status_code != 200:
        return r, None, None
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    ws = wb.active
    rows = [[c.value for c in row] for row in ws.iter_rows(min_row=1)]
    return r, ws, rows


print("§1 화면에 「⬇ 엑셀로 내려받기」 — 지금 조건 그대로")
h = q(cl.get, "/projects/ledger").text
m = re.search(r'<a class="lg-xls" id="lgXls" href="([^"]+)"[^>]*>⬇ 엑셀로 내려받기 <span[^>]*>\((\d+)줄\)</span></a>', h)
check(m and m.group(1).replace("&amp;", "&") == "/projects/ledger/excel?biz=&year=&q=" and m.group(2) == "6", "전체 화면: 단추 · 「(6줄)」 · 조건 없음", m and m.groups())
h2 = q(cl.get, "/projects/ledger?biz=T&year=2026&q=" + "T-2611").text
m2 = re.search(r'id="lgXls" href="([^"]+)"', h2)
check(m2 and m2.group(1).replace("&amp;", "&") == "/projects/ledger/excel?biz=T&year=2026&q=T-2611", "거른 화면: 단추 주소에 사업부·연도·검색 그대로", m2 and m2.group(1))
h3 = q(cl.get, "/projects/ledger?q=" + "없는글자zz").text
check('id="lgXls"' not in h3, "결과가 없으면 단추 없음")

print("§2 내려받은 엑셀 = 화면과 같은 줄")
r, ws, rows = xl("/projects/ledger/excel")
check(r.status_code == 200 and r.headers.get("content-type", "").startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), "엑셀 파일(.xlsx)", r.status_code)
cd = r.headers.get("content-disposition", "")
check("attachment" in cd and "filename*=UTF-8''KNK_%EA%B4%80%EB%A6%AC%EB%B2%88%ED%98%B8%EB%8C%80%EC%9E%A5_%EC%A0%84%EC%B2%B4_" in cd and cd.endswith(".xlsx"),
      "파일 이름 = KNK_관리번호대장_전체_날짜시각.xlsx", cd)
check(r.headers.get("cache-control") == "no-store", "보관 안 함(no-store)")
check(ws.title == "관리번호대장" and rows[1][0] == "관리번호대장" and "사업부 전체 · 발행 연도 전체" in rows[2][0] and "관리번호 6개" in rows[2][0]
      and "수주번호 6건(취소 빼고)" in rows[2][0] and "내려받은 시각" in rows[2][0], "맨 위 = 제목 · 조건 · 개수 · 내려받은 시각", rows[2][0])
check(rows[5][:14] == ["#", "관리번호", "사업부", "발행월", "수주번호", "수주 수", "모델명", "설비명", "프로젝트명", "고객사", "영업 담당", "상태", "서버경로", "비고"],
      "머리 줄 = 화면 칸 + 수주 수", rows[5])
body = [x for x in rows[6:] if isinstance(x[0], int)]
codes = [x[1] for x in body]
check(codes == ["015T2611", "009T2611", "004C2611", "003T2611", "001T2610", "002M2511"], "줄 순서 = 화면(최근 발행 ↓)", codes)
d = {x[1]: x for x in body}
check(d["015T2611"][4] == "T-261110-1\nT-261112-2\nT-261113-9 (취소)" and d["015T2611"][5] == 2, "수주번호 = 한 칸 줄바꿈 · 취소는 「(취소)」 · 수주 수는 취소 빼고", d["015T2611"][4:6])
check(d["003T2611"][4] in (None, "") and d["003T2611"][5] == 0, "수주 없는 관리번호 = 빈 칸 · 0", d["003T2611"][4:6])
check(d["009T2611"][11].endswith("· 폐기"), "폐기한 프로젝트 = 상태에 「폐기」", d["009T2611"][11])
check(d["004C2611"][2] == "소모품" and d["015T2611"][2] == "검사기" and d["002M2511"][2] == "자동화", "사업부 = 글자(그림 문자 없이)", [d[k][2] for k in ("004C2611", "015T2611", "002M2511")])
check(d["015T2611"][3] == "2026-11" and d["015T2611"][6] == "VMA0386" and d["015T2611"][7] == "VSWR 검사기" and d["015T2611"][9] == "드림텍"
      and d["015T2611"][10] == "이현" and d["015T2611"][12] == r"Z:\2.검사기\015T2611" and d["015T2611"][13] == "비고 015T2611", "나머지 칸 = 화면 값", d["015T2611"])
check(ws.freeze_panes == "C7" and ws.auto_filter.ref == "A6:N12", "머리 줄·관리번호 고정 · 거르기 단추", (ws.freeze_panes, ws.auto_filter.ref))
check(not any(h and ("금액" in h or "가격" in h) for h in rows[5]), "금액 칸 없음(화면과 같음)")

print("§2-1 깔끔한 공용 양식(대표 11-19 「양식을 깔끔하게 항상」 · app/knk_xlsx.py)")
from openpyxl.cell.rich_text import CellRichText  # noqa: E402
wb2 = openpyxl.load_workbook(io.BytesIO(q(cl.get, "/projects/ledger/excel").content), rich_text=True); w2 = wb2.active
check(len(w2._images) == 1 and w2._images[0].anchor._from.row == 0 and w2["A2"].font.b and w2["A2"].font.sz == 15
      and "A2:N2" in [str(x) for x in w2.merged_cells.ranges] and "A3:N3" in [str(x) for x in w2.merged_cells.ranges] and w2["A4"].fill.fgColor.rgb.endswith("A5282C") and w2["N4"].fill.fgColor.rgb.endswith("A5282C"),
      "z67 KNK 양식: 맨 위 KNK 로고 그림 · 제목 굵게 15 · 안내 줄 · KNK 빨강 띠", (len(w2._images), w2["A2"].font.sz, w2["A4"].fill.fgColor.rgb))

hd = w2["E6"]
check(hd.font.b and hd.fill.fgColor.rgb.endswith("A5282C") and hd.font.color.rgb.endswith("FFFFFF") and hd.alignment.horizontal == "center",
      "머리 = KNK 빨강 바탕 · 흰 굵은 글 · 가운데", (hd.fill.fgColor.rgb, hd.font.color.rgb))
check(all(w2.cell(row=7, column=i).font.name == "맑은 고딕" for i in range(1, 15)) and w2["B7"].font.b and w2["B7"].alignment.horizontal == "center",
      "본문 글꼴 맑은 고딕 · 관리번호 굵게 가운데")
check(w2["A8"].fill.fgColor.rgb.endswith("F6F7F4") and w2["A7"].fill.fill_type in (None, "none"), "한 줄 건너 옅은 바탕")
ce = w2["E7"].value
check(isinstance(ce, CellRichText) and any(getattr(b, "font", None) is not None and b.font.strike for b in ce if not isinstance(b, str)) and str(ce).endswith("T-261113-9 (취소)"),
      "취소 수주번호 = 회색 줄 그음(칸 안 일부만)", str(ce))
check(w2.row_dimensions[7].height >= 14 * 3, "수주번호 3줄 → 줄 높이도 3줄", w2.row_dimensions[7].height)
r9 = [row for row in w2.iter_rows(min_row=7) if row[1].value == "009T2611"][0]
check(r9[1].font.color.rgb.endswith("9AA39D"), "폐기한 프로젝트 줄 = 흐리게", r9[1].font.color.rgb)
check(w2.sheet_view.showGridLines is False and w2.page_setup.orientation == "landscape" and w2.page_setup.paperSize == 9 and w2.page_setup.fitToWidth == 1
      and w2.page_setup.fitToHeight == 0 and w2.sheet_properties.pageSetUpPr.fitToPage and w2.print_title_rows == "$6:$6" and "&P / &N" in (w2.oddFooter.center.text or ""),
      "눈금선 끔 · 인쇄 A4 가로 · 폭 한 장 · 장마다 머리 줄 · 아래 쪽 번호", (w2.print_title_rows, w2.page_setup.orientation))
check(any(isinstance(row[0], str) and row[0].startswith("※ 줄 그은 수주번호 = 취소") for row in rows), "맨 아래 읽는 법 한 줄")
check(wb2.properties.creator == "KNK 이음웍스", "파일 만든 이 = KNK 이음웍스")

print("§3 거른 조건 그대로")
r, ws, rows = xl("/projects/ledger/excel?biz=T&year=2026&q=T-2611")
body = [x for x in rows[6:] if isinstance(x[0], int)]
check([x[1] for x in body] == ["015T2611", "009T2611"] and "사업부 검사기 · 발행 연도 2026년 · 검색 「T-2611」" in rows[2][0], "검사기 · 2026 · 「T-2611」 = 화면과 같은 2줄", ([x[1] for x in body], rows[1][0]))
cd = r.headers.get("content-disposition", "")
check("%EA%B2%80%EC%82%AC%EA%B8%B0_2026_" in cd, "파일 이름에 사업부·연도", cd)
hv = q(cl.get, "/projects/ledger?biz=T&year=2026&q=T-2611").text
check(hv.count('<a class="lg-code"') == len(body), "엑셀 줄 수 = 화면 줄 수", (hv.count('<a class="lg-code"'), len(body)))
r, ws, rows = xl("/projects/ledger/excel?q=" + "없는글자zz")
check(r.status_code == 200 and [x for x in rows[6:] if x and isinstance(x[0], int)] == [] and "관리번호 0개" in rows[2][0], "결과 없음 = 머리 줄만", rows[2][0])

print("§4 엑셀 안전 · 권한")
with D.db_session() as c:
    ins(c, "projects", {"code": "016T2611", "mgmt_code": "016T2611", "name": "=HYPERLINK(\"http://x\",\"x\")", "model_name": "M", "equip_name": "E",
                        "biz_div": "T", "customer_id": CU, "customer_name": "주식회사 드림텍", "status": "수주확정", "is_archived": 0})
r, ws, rows = xl("/projects/ledger/excel")
cell = [c for c in ws[ws.max_row - 0] if False]
x = [row for row in ws.iter_rows(min_row=7) if row[1].value == "016T2611"][0]
check(x[8].data_type == "s" and x[8].value.startswith("=HYPERLINK"), "「=」로 시작하는 글 = 글자 그대로(계산식 아님)", (x[8].data_type, x[8].value))
CUR["u"] = NOSALES
r = q(cl.get, "/projects/ledger/excel")
check(r.status_code == 303 and "no_perm=sales" in r.headers.get("location", ""), "매출 못 보는 사람 = 못 내려받음(화면과 같음)", r.status_code)
CUR["u"] = None
r = q(cl.get, "/projects/ledger/excel")
check(r.status_code == 303 and r.headers.get("location", "") == "/login", "로그인 안 하면 로그인으로", r.headers.get("location"))
CUR["u"] = ADMIN

print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
