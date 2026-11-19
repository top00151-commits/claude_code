# -*- coding: utf-8 -*-
"""z1191z67 시험 (대표 2026-11-19 「다른 엑셀도 바꿔」 「양식 이미지를 최대한 KNK 우리회사 느낌에 이미지로 양식 이미지 통일화」)
  ① 공용 목록 내려받기(_make_xlsx_response · 수주·견적·발주·재고·이슈 등) = KNK 양식(로고 · 제목 · 빨강 띠 · 빨강 머리)
  ② 다시 올리는 파일(공급사 · 작업일정표) = 1행 머리 유지 + KNK 색 → 공급사 올리기가 그대로 읽음
  ③ 프로젝트 목록 엑셀 = KNK 양식 · 금액 칸 쉼표
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z67-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z67_")
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
import app.knk_xlsx as KX  # noqa: E402


def get(url):
    r = q(cl.get, url)
    wb = openpyxl.load_workbook(io.BytesIO(r.content)) if r.status_code == 200 else None
    return r, wb


def is_knk_banner(ws, head, frz="A7"):
    """KNK 양식: 로고 그림 1개(A1) · 2행 제목 · 4행 빨강 띠 · 6행 빨강 머리(흰 굵은 글) · 맑은 고딕 · 눈금선 끔 · 인쇄 A4 폭 한 장."""
    h = [ws.cell(row=6, column=i).value for i in range(1, len(head) + 1)]
    return (len(ws._images) == 1 and ws._images[0].anchor._from.row == 0 and ws["A2"].font.b and ws["A4"].fill.fgColor.rgb.endswith("A5282C")
            and h == head and ws["A6"].fill.fgColor.rgb.endswith("A5282C") and ws["A6"].font.color.rgb.endswith("FFFFFF") and ws["A6"].font.b
            and ws["A6"].font.name == "맑은 고딕" and ws.sheet_view.showGridLines is False and ws.freeze_panes == frz
            and ws.page_setup.paperSize == 9 and ws.page_setup.fitToWidth == 1 and ws.print_title_rows == "$6:$6"), h


with D.db_session() as c:
    ins(c, "suppliers", {"name": "가상정밀(주)", "biz_no": "123-45-67890", "contact": "김가상", "phone": "010-0000-0000", "email": "a@b.c",
                         "country": "KR", "currency": "KRW", "is_active": 1, "note": "=SUM(1,2)"})

print("§1 공용 목록 내려받기 = KNK 양식")
r, wb = get("/sales/orders/export.xlsx")
ws = wb["수주"] if wb else None
ok, h = is_knk_banner(ws, ["ID", "수주번호", "주문일", "납기", "상태", "수주액(원)", "고객사"]) if ws else (False, None)
check(r.status_code == 200 and ok, "수주 엑셀(수주 시트) = 로고·제목·빨강 띠·빨강 머리·고정·인쇄", h)
check(wb and wb.sheetnames == ["수주", "수주라인"] and is_knk_banner(wb["수주라인"], ["수주번호", "품번", "품명", "수량", "단가", "금액"])[0], "둘째 시트(수주라인)도 같은 양식", wb and wb.sheetnames)
check(ws and ws["A2"].value == "수주" and "건 · 내려받은 시각" in (ws["A3"].value or ""), "제목 = 시트 이름 · 안내 = 건수·내려받은 시각", ws and (ws["A2"].value, ws["A3"].value))
cd = r.headers.get("content-disposition", "")
check("%EC%88%98%EC%A3%BC_" in cd and r.headers.get("cache-control") == "no-store", "파일 이름(수주_날짜) 그대로 · 보관 안 함", cd)
for url, sheet, head0 in (("/sales/quotations/export.xlsx", "견적", "ID"), ("/po/export.xlsx", None, None), ("/stock/balances/export.xlsx", None, None),
                          ("/issues/export.xlsx", None, None), ("/tickets/export.xlsx", None, None), ("/changes/export.xlsx", None, None),
                          ("/production/work-orders/export.xlsx", None, None), ("/qc/inspection-reports/export.xlsx", None, None), ("/stock/movements/export.xlsx", None, None)):
    r, wb = get(url)
    if r.status_code != 200:
        check(r.status_code in (303, 403), "%s — 권한 없음은 그대로(%s)" % (url, r.status_code)); continue
    w = wb.worksheets[0]
    check(len(w._images) == 1 and w["A6"].fill.fgColor.rgb.endswith("A5282C") and w["A4"].fill.fgColor.rgb.endswith("A5282C") and w.freeze_panes == "A7",
          "%s = KNK 양식" % url, (len(w._images), w["A6"].value))

print("§2 다시 올리는 파일 — 공급사(1행 머리 유지)")
r, wb = get("/suppliers/export.xlsx")
w = wb.active
check(r.status_code == 200 and w["A1"].value == "ID" and w["B1"].value == "공급사명" and len(w._images) == 0 and w["A1"].fill.fgColor.rgb.endswith("A5282C")
      and w["A1"].font.color.rgb.endswith("FFFFFF") and w["B2"].font.name == "맑은 고딕" and w.freeze_panes == "A2", "1행 = 머리(로고·제목 없음) · KNK 빨강 머리 · 맑은 고딕", [c.value for c in w[1]][:4])
check(w["P2"].value == "=SUM(1,2)" and w["P2"].data_type == "s", "「=」 글 = 글자 그대로", (w["P2"].value, w["P2"].data_type))
from app.database import suppliers_bulk_import_excel as _sbi  # noqa: E402
_tp = os.path.join(TMP, "sup.xlsx"); open(_tp, "wb").write(r.content)
res = _sbi(_tp, dry_run=True)
check(not res.get("error") and res.get("parsed") == 1 and "name" in res.get("header_map", {}).values(), "받은 공급사 파일을 「공급사 올리기」가 그대로 읽음(1줄 · 이름 칸 인식)", {k: res.get(k) for k in ("error", "parsed", "total")})

print("§3 다시 올리는 파일 — 작업일정표(일괄등록 · 1행 머리)")
r, wb = get("/sales/schedule/export.xlsx")
w = wb["일괄등록"] if wb and "일괄등록" in wb.sheetnames else None
check(r.status_code == 200 and w is not None and w["A1"].fill.fgColor.rgb.endswith("A5282C") and len(w._images) == 0 and "관리번호" in [c.value for c in w[1]],
      "작업일정표 = 시트 「일괄등록」 · 1행 머리(관리번호…) · KNK 빨강 · 로고 없음", w and [c.value for c in w[1]][:5])

print("§4 프로젝트 목록 엑셀 = KNK 양식")
r, wb = get("/projects/export.xlsx")
w = wb.active
ok, h = is_knk_banner(w, ["관리코드", "프로젝트명", "장비명", "모델명", "고객사", "출고형태", "상태", "수주액(원)", "발주일"], "B7")
check(r.status_code == 200 and ok and w["A2"].value.startswith("프로젝트 목록 — "), "로고·제목·빨강 띠·빨강 머리", h)
amt = [w.cell(row=rr, column=8) for rr in range(7, w.max_row + 1) if isinstance(w.cell(row=rr, column=8).value, (int, float))]
check(amt and all(c.number_format == "#,##0" for c in amt) and w.freeze_panes == "B7", "수주액 = 천 단위 쉼표 · 관리코드 고정", [c.number_format for c in amt][:3])

print("§5 공용 양식 자체")
wb = KX.new_book("시험"); hr = KX.table_sheet(wb.active, "시험", "안내", KX.auto_cols(["번호", "금액(원)", "이름"], [[1, 1000, "가"], [2, 2500, "나"]]), [[1, 1000, "가"], [2, 2500, "나"]])
w = openpyxl.load_workbook(io.BytesIO(KX.xlsx_bytes(wb))).active
check(hr == 6 and w["B7"].number_format == "#,##0" and w["B7"].alignment.horizontal == "right" and w["A7"].number_format == "General" and w["A8"].fill.fgColor.rgb.endswith("F6F7F4"),
      "자동 칸: 금액 = 쉼표·오른쪽 · 번호는 쉼표 없음 · 한 줄 건너 바탕", (w["B7"].number_format, w["A7"].number_format))
_old = KX._LOGO; KX._LOGO = "없는파일.png"; KX._LOGO_CACHE.clear()
wb = KX.new_book("x"); KX.table_sheet(wb.active, "x", "", [{"h": "a"}], [["1"]])
check(wb.active["A1"].value == "KNK" and len(wb.active._images) == 0, "로고 파일이 없어도 멈추지 않음(빨강 「KNK」 글자)")
KX._LOGO = _old; KX._LOGO_CACHE.clear()

print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
