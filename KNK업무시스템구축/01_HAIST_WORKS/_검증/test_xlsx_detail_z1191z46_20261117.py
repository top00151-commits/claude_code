# -*- coding: utf-8 -*-
"""z1191z46 시험 (대표 2026-11-17 요청사항 1·2)
  ① 작업일정표에서 줄을 고르고 [엑셀로 저장] → 첫 시트 「일괄등록」= 고른 줄만(고른 순서) · 그 뒤 = 고른 수주마다 상세내역 한 시트
     · 안 고르면 지금과 같음(시트 하나 · 같은 머리글) · 「전체에서 찾기」(검색어)는 화면처럼 전 기간(전엔 이번 달만)
  ② 소모품 상세 [📥 엑셀로 저장] → 그 수주 한 건 상세내역(사진 포함)
  · 금액 = 저장된 값 그대로 · 칸 서식으로 둘째 자리까지(달러) → 엑셀 합계 = WORKS 합계
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, sys, tempfile, shutil
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z46-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z46_")
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


# 사진(썸네일) — 작업 사본 uploads 아래 임시 폴더(끝나면 지움)
IMG_DIR = os.path.join(ROOT, "uploads", "z46test")
os.makedirs(IMG_DIR, exist_ok=True)
from PIL import Image as _PI  # noqa: E402
_PI.new("RGB", (240, 120), (200, 30, 30)).save(os.path.join(IMG_DIR, "p_thumb.jpg"))

IT = {}
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T945', 'T945', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T945'").fetchone())
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('아무권한없음', 'user', 'T947', 'T947', 'sso_only_no_local_password', 1, 1, 0, 0, 0, 0)")
    NONE = dict(c.execute("SELECT * FROM users WHERE employee_no='T947'").fetchone())
    VN = ins(c, "customers", {"name": "KNK VINA", "alias": "KNK VINA"})
    LG = ins(c, "customers", {"name": "엘지전자", "alias": "엘지전자"})

    def proj(code, cid, cname, ccy="USD", od="2026-05-05"):
        return ins(c, "projects", {"code": code, "mgmt_code": code, "name": "WATCH 검사기", "model_name": "WATCH9", "equip_name": "HRM 검사기",
                                   "biz_div": code[3], "customer_id": cid, "customer_name": cname, "status": "진행중",
                                   "currency": ccy, "order_date": od, "due_date": "2026-05-30", "is_archived": 0, "is_export": 1})

    def order(pid, cid, no, od="2026-05-05", ccy="USD"):
        return ins(c, "orders", {"order_no": no, "project_id": pid, "customer_id": cid, "order_date": od,
                                 "due_date": "2026-05-28", "status": "CONFIRMED", "currency": ccy, "ship_to": "베트남 공장"})

    def item(oid, key, label, qty, up, amt, ccy="USD", due="2026-05-28", **kw):
        row = {"order_id": oid, "qty": qty, "unit_price": up, "amount": amt, "unit_status": "진행중",
               "due_date": due, "order_date": "2026-05-05", "currency": ccy, "unit_label": label}
        row.update(kw)
        IT[key] = ins(c, "order_items", row)

    # 프로젝트 P1: 수주 둘(T-1 · T-2) → 작업일정표에서 수주마다 줄
    P1 = proj("001T2605", VN, "KNK VINA")
    o1 = order(P1, VN, "T-1")
    for k in (1, 2, 3):   # 운영 T-260615-8 처럼 셋째 자리까지 저장된 금액
        item(o1, "t1_%d" % k, "%d호기" % k, 1, 3951.657, 3951.657, line_note="추가 호기")
    o2 = order(P1, VN, "T-2", od="2026-05-06")
    item(o2, "t2_1", "4호기", 1, 1000.0, 1000.0, due="2026-05-29", spec="SPEC-A", maker="메이커X", image_thumb_path="/uploads/z46test/p_thumb.jpg")
    # 프로젝트 P2: 수주 하나 · 통화 섞임 → 합계 줄 없음
    P2 = proj("002M2605", LG, "엘지전자", ccy="KRW")
    o3 = order(P2, LG, "M-5", ccy="KRW")
    item(o3, "m5_1", "SENSOR", 108, 4.2533, 459.0, ccy="USD")
    item(o3, "m5_2", "CP", 2, 50000, 100000, ccy="KRW")
    # 소모품 C-1(달러) · C-2(원화 · 작년 12월 = 이번 달 화면에 없음)
    C1 = ins(c, "consumable_orders", {"co_no": "C-1", "mgmt_code": "113C2605", "customer_name": "KNK VINA", "customer_id": VN, "currency": "USD",
                                      "total_amount": 120.48, "status": "SHIPPED", "order_date": "2026-05-02", "due_date": "2026-05-10",
                                      "secondary_customer": "DSV", "is_export": 1, "model_name": "소모품", "equip_name": "DSV 소모품 2종",
                                      "statement_date": "2026-05-11", "tax_invoice_date": "2026-05-12", "tax_invoice_amt1": 120.48, "form_type": "제품"})
    ins(c, "consumable_order_items", {"co_id": C1, "line_no": 1, "part_name": "POGO PIN", "spec": "DPT014", "qty": 2, "unit": "EA",
                                      "unit_price": 31.432, "amount": 62.86, "note": "인보이스 단가", "image_thumb_path": "/uploads/z46test/p_thumb.jpg"})
    ins(c, "consumable_order_items", {"co_id": C1, "line_no": 2, "part_name": "FLOATING", "spec": "KNK-SM/F966", "qty": 2, "unit": "EA",
                                      "unit_price": 28.808, "amount": 57.62, "secondary_customer": "SEV"})
    C2 = ins(c, "consumable_orders", {"co_no": "C-2", "mgmt_code": "114C2512", "customer_name": "엘지전자", "customer_id": LG, "currency": "KRW",
                                      "total_amount": 350000, "status": "SHIPPED", "order_date": "2025-12-02", "due_date": "2025-12-10"})
    ins(c, "consumable_order_items", {"co_id": C2, "line_no": 1, "part_name": "PCB", "spec": "KNK-P-5002", "qty": 1, "unit": "EA",
                                      "unit_price": 350000, "amount": 350000})

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
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


def book(resp):
    return load_workbook(io.BytesIO(resp.content))


def table(ws):
    """상세 시트 → (정보 dict, 머리글, 줄들, 합계 줄)"""
    vals = [[c.value for c in r] for r in ws.iter_rows()]
    hi = next(i for i, r in enumerate(vals) if r and r[0] == "No")
    info = {}
    for r in vals[1:hi]:
        for j in range(0, len(r) - 1, 2):
            if r[j]:
                info[r[j]] = r[j + 1]
    hdr = [h for h in vals[hi] if h is not None]
    body = [r[:len(hdr)] for r in vals[hi + 1:] if r and r[0] not in (None, "")]
    tot = [r for r in body if r[0] == "합계"]
    body = [r for r in body if r[0] != "합계"]
    return info, hdr, body, (tot[0] if tot else None), hi


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


try:
    print("§1 안 고르면 지금과 같음")
    r = q(cl.get, "/sales/schedule/export.xlsx?ym=2026-05")
    wb = book(r)
    check(r.status_code == 200 and wb.sheetnames == ["일괄등록"], "시트 하나 「일괄등록」", wb.sheetnames)
    H = [c.value for c in wb["일괄등록"][1]]
    check(H[:7] == ["관리번호", "수주번호", "프로젝트명", "모델명", "장비명", "기타사항", "수량"] and {"단가", "금액", "통화", "영업담당자"} <= set(H), "머리글 그대로(일괄등록 양식)", H)
    so_col = H.index("수주번호")
    SOS = [row[so_col].value for row in list(wb["일괄등록"].iter_rows())[1:]]
    check(sorted(SOS) == ["C-1", "M-5", "M-5", "T-1", "T-2"], "이번 달 줄: 소모품 C-1 · 수주 줄(T-1 한 줄 · M-5 단가 달라 두 줄 · T-2)", SOS)
    check("C-2" not in SOS, "작년 12월 소모품 C-2 는 이번 달 저장에 없음(지금과 같음)")

    print("§2 「전체에서 찾기」(검색어) = 화면처럼 전 기간")
    r = q(cl.get, "/sales/schedule/export.xlsx?ym=2026-05&cust=" + "엘지전자")
    SO2 = [row[so_col].value for row in list(book(r)["일괄등록"].iter_rows())[1:]]
    check(sorted(SO2) == ["C-2", "M-5", "M-5"], "엘지전자로 찾기 → 작년 12월 C-2 까지(전엔 이번 달 M-5 만)", SO2)
    r = q(cl.get, "/sales/schedule/export.xlsx?ym=2026-05&pf=2025-12-01&pt=2025-12-31")
    SO3 = [row[so_col].value for row in list(book(r)["일괄등록"].iter_rows())[1:]]
    check(SO3 == ["C-2"], "기간 보기(2025-12) → 그 기간 줄만", SO3)
    check("작업일정표_2025-12-01~2025-12-31" in r.headers.get("content-disposition", "").encode().decode("utf-8") or "2025-12-01" in r.headers.get("content-disposition", ""), "파일 이름에 기간", r.headers.get("content-disposition"))

    print("§3 고른 줄 + 수주마다 상세내역 시트")
    rows = q(M.build_schedule_board_rows, ADMIN, 2026, 5)["rows"]
    def tok(rw):
        ids = ".".join(str(x) for x in sorted(rw.get("unit_iids") or [])) if (rw.get("is_unit") and rw.get("unit_iids")) else ""
        return "|".join([rw["kind"], str(rw["ref_id"]), ids, rw.get("so_no") or ""])
    pick = [next(x for x in rows if x["kind"] == "consumable" and x["so_no"] == "C-1")]
    pick += [x for x in rows if x["kind"] == "project" and x["so_no"] == "T-1"][:1]
    pick += [next(x for x in rows if x["kind"] == "project" and x["so_no"] == "M-5")]
    pick += [next(x for x in rows if x["kind"] == "project" and x["so_no"] == "T-2")]
    sel = "\n".join(tok(x) for x in pick) + "\n" + tok(pick[0])   # 같은 줄 두 번 → 시트 하나
    r = q(cl.post, "/sales/schedule/export.xlsx?ym=2026-05&cust=", data={"sel": sel})
    wb = book(r)
    check(r.status_code == 200 and wb.sheetnames == ["일괄등록", "C-1", "T-1", "M-5", "T-2"], "시트 = 일괄등록 + 고른 순서대로 수주마다 하나(겹친 줄은 한 번)", wb.sheetnames)
    S1 = [row[so_col].value for row in list(wb["일괄등록"].iter_rows())[1:]]
    check(S1 == ["C-1", "T-1", "M-5", "T-2"], "「일괄등록」= 고른 줄만 · 고른 순서", S1)
    check("%EC%84%A0%ED%83%9D" in r.headers.get("content-disposition", ""), "파일 이름 「작업일정표_선택…줄」", r.headers.get("content-disposition"))

    info, hdr, body, tot, hi = table(wb["C-1"])
    check(hdr[:3] == ["No", "소모품 품명", "규격"] and "금액" in hdr and "연결 관리번호" in hdr, "소모품 시트 = 화면 「라인 항목」 칸 순서", hdr)
    A = hdr.index("금액"); P = hdr.index("단가")
    check([b[1] for b in body] == ["POGO PIN", "FLOATING"] and [b[A] for b in body] == [62.86, 57.62], "줄 = 품목 2개 · 금액 저장값 그대로", [(b[1], b[A]) for b in body])
    check(body[0][P] == 31.432, "단가는 저장된 값 그대로(셋째 자리까지) — 칸 서식으로만 둘째 자리 표시", body[0][P])
    ws = wb["C-1"]
    check(ws.cell(hi + 2, A + 1).number_format == "#,##0.00" and ws.cell(hi + 2, P + 1).number_format == "#,##0.00", "달러 칸 서식 = 둘째 자리", ws.cell(hi + 2, A + 1).number_format)
    check(tot is not None and abs(tot[A] - 120.48) < 1e-9, "합계 줄 = 120.48 = WORKS 합계(total_amount)", tot)
    check(info.get("관리번호") == "113C2605" and info.get("수주번호") == "C-1" and info.get("고객사") == "KNK VINA" and info.get("2차 고객사") == "DSV" and info.get("통화") == "USD",
          "위쪽 기본 정보(관리번호·수주번호·고객사·2차·통화)", info)
    check(body[1][hdr.index("2차 고객사")] == "SEV" and body[0][hdr.index("세금계산서\n금액")] == 120.48, "품목별 2차 고객사 · 발주 공통 칸(세금계산서 금액)", body[1])
    check(len(ws._images) == 1, "사진 있는 줄 = 엑셀 안에 사진", len(ws._images))

    info, hdr, body, tot, hi = table(wb["T-1"])
    A = hdr.index("금액")
    check([b[1] for b in body] == ["1호기", "2호기", "3호기"] and all(b[A] == 3951.657 for b in body), "프로젝트 수주 T-1 = 호기 3줄 · 금액 저장값(셋째 자리) 그대로", [(b[1], b[A]) for b in body])
    check(tot and abs(tot[A] - 11854.971) < 1e-9, "합계 = 11,854.971(화면 표시 $11,854.97 · 엑셀도 서식으로 11,854.97)", tot)
    check("메이커" not in hdr and "규격" not in hdr and "사진" not in hdr and "비고" in hdr and "납품위치" in hdr, "빈 칸(메이커·규격·사진)은 빼고 · 값 있는 칸(비고·납품위치)만", hdr)
    check(info.get("프로젝트명") == "WATCH 검사기" and info.get("고객사") == "KNK VINA" and info.get("호기·품목 수") == 3, "기본 정보(프로젝트명·고객사·줄 수)", info)
    info, hdr, body, tot, hi = table(wb["T-2"])
    check("규격" in hdr and "메이커" in hdr and "사진" in hdr and len(wb["T-2"]._images) == 1, "T-2: 규격·메이커·사진 칸 있음(값이 있으니)", hdr)
    info, hdr, body, tot, hi = table(wb["M-5"])
    check(tot is None and info.get("합계") == "통화가 섞여 합계 없음", "통화가 섞인 수주(M-5: USD+KRW)는 합계를 더하지 않음", (tot, info.get("합계")))
    C = hdr.index("통화")
    check([b[C] for b in body] == ["USD", "KRW"], "줄마다 통화", [b[C] for b in body])

    print("§4 이상한 입력 · 겹치는 시트 이름")
    r = q(cl.post, "/sales/schedule/export.xlsx?ym=2026-05", data={"sel": "evil|1;drop\nproject|abc|1|x\n"})
    wb = book(r)
    check(r.status_code == 200 and wb.sheetnames == ["일괄등록"], "알아볼 수 없는 고른 줄 → 무시하고 지금처럼(화면 전체)", wb.sheetnames)
    used = set()
    n1 = M._z46_sname("T-1", used); n2 = M._z46_sname("t-1", used); n3 = M._z46_sname("A/B:C*?" + "X" * 40, used)
    check((n1, n2) == ("T-1", "t-1(2)") and "/" not in n3 and len(n3) <= 31, "시트 이름: 겹치면 (2) · 금지 글자 바꿈 · 31자", (n1, n2, n3))

    print("§5 소모품 상세 [📥 엑셀로 저장]")
    r = q(cl.get, "/consumables/%d/export.xlsx" % C1)
    wb = book(r)
    check(r.status_code == 200 and wb.sheetnames == ["C-1"], "그 수주 한 건 시트", wb.sheetnames)
    info, hdr, body, tot, hi = table(wb["C-1"])
    check(len(body) == 2 and abs(tot[hdr.index("금액")] - 120.48) < 1e-9 and len(wb["C-1"]._images) == 1, "줄 2 · 합계 120.48 · 사진", (len(body), tot))
    check("113C2605_C-1" in __import__("urllib.parse").parse.unquote(r.headers.get("content-disposition", "")), "파일 이름 = 관리번호_수주번호_상세내역", r.headers.get("content-disposition"))
    r = q(cl.get, "/consumables/%d/export.xlsx" % C2)
    info, hdr, body, tot, hi = table(book(r)["C-2"])
    ws = book(r)["C-2"]
    check(ws.cell(hi + 2, hdr.index("금액") + 1).number_format == "#,##0", "원화 = 정수 서식", ws.cell(hi + 2, hdr.index("금액") + 1).number_format)
    r = q(cl.get, "/consumables/999999/export.xlsx")
    check(r.status_code == 303, "없는 수주 → 목록으로", r.status_code)
    html = q(cl.get, "/consumables/%d" % C1).text
    check("/consumables/%d/export.xlsx" % C1 in html and "📥 엑셀로 저장" in html, "소모품 상세 화면에 [📥 엑셀로 저장] 단추")

    print("§6 작업일정표 화면 단추")
    html = q(cl.get, "/sales/schedule?ym=2026-05").text
    check('id="schedXlsxBtn"' in html and "function schedExportXlsx()" in html and "schedXlsxN" in html and "window.schedExportXlsx = schedExportXlsx" in html, "단추 → schedExportXlsx(고른 줄 있으면 POST) · 전역에 걸어 둠(스크립트가 함수 안이라 onclick 이 못 찾던 것)")
    check("&pf=" not in html.split("function schedExportXlsx()")[1].split("var sel")[0], "월 보기: 기간 값 안 붙음")
    html = q(cl.get, "/sales/schedule?pf=2025-12-01&pt=2025-12-31").text
    check("&pf=2025-12-01&pt=2025-12-31" in html.split("function schedExportXlsx()")[1].split("var sel")[0], "기간 보기: 저장 주소에 기간(화면과 같은 줄)")

    print("§6b 프로젝트 상세 「📥 엑셀 다운로드」(수주 한 건) — 달러는 둘째 자리 서식")
    r = q(cl.get, "/projects/%d/orders/%d/export-xlsx" % (P1, o1))
    ws = book(r).active
    fm = [ws.cell(rr, cc).number_format for rr in range(1, ws.max_row + 1) for cc in range(1, ws.max_column + 1) if ws.cell(rr, cc).value == 3951.657]
    check(r.status_code == 200 and fm and all(f == "#,##0.00" for f in fm), "달러 수주 T-1: 단가·금액 칸 = #,##0.00(전엔 #,##0 → 센트 안 보임)", fm)
    r = q(cl.get, "/projects/%d/orders/%d/export-xlsx" % (P2, o3))
    ws = book(r).active
    fm = [ws.cell(rr, cc).number_format for rr in range(1, ws.max_row + 1) for cc in range(1, ws.max_column + 1) if ws.cell(rr, cc).value == 100000]
    check(fm and all(f == "#,##0" for f in fm), "원화 수주: 정수 서식 그대로", fm)

    print("§7 권한")
    CUR["u"] = NONE
    r = q(cl.get, "/consumables/%d/export.xlsx" % C1)
    check(r.status_code == 303 and "/home" in r.headers.get("location", ""), "소모품 권한 없음 → 홈", (r.status_code, r.headers.get("location")))
    r = q(cl.post, "/sales/schedule/export.xlsx?ym=2026-05", data={"sel": tok(pick[0])})
    check(r.status_code == 303 and "/dept/schedule" in r.headers.get("location", ""), "매출 못 보는 사람 → 고른 줄 저장도 부서 일정표로", (r.status_code, r.headers.get("location")))
    CUR["u"] = ADMIN
finally:
    shutil.rmtree(IMG_DIR, ignore_errors=True)
    try:
        os.rmdir(os.path.join(ROOT, "uploads"))
    except Exception:
        pass

print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
