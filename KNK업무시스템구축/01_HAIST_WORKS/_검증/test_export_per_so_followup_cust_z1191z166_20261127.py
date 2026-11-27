# -*- coding: utf-8 -*-
"""z1191z166 시험 — 수출 서류 수주(구매자)별 + 추가 발주 1차 고객사 필수 (대표 11-27)

가상 관리번호 하나(903M2509):
  수주 4건 살아 있음 — KRW 국내 내수 1(O1) · USD 수출 3(O2·O3·O4 · 구매자 3곳) + 취소 1(OX · 수출)
  §1 so 없이 들어오면 「어느 수주의 서류인지」 고르기 화면(PL·CI·엑셀·신고용·출고) · 내수 수주는 서류 단추 없음
  §2 수주별 PL/CI 인쇄·엑셀·신고용 엑셀 200 · 구매자 하나만 · 품목은 그 수주 것만 · 서류 번호 겹치지 않음 · 한 통화
  §3 내수 수주·취소 수주를 so 로 고르면 고르기 화면 + 안내
  §4 수주 1개 관리번호 = 예전처럼 바로
  §5 통관 입력 상세 = 수주별 서류 단추 · 신고 서류 정보는 고른 수주 · 옛 관리번호 값은 「처음 값」(복사 저장 안 함) · 수주별 저장
  §6 금액 대조 — 수주별 합 = 예전(관리번호 통째) 합 − 내수 수주 몫
  §7 출고 QR — 수주 QR 주소에 so · 옛 라벨(so 없이 b 만)도 그대로 열림
  §8 추가 발주(화면 창) — 1차 고객 없이 = 저장 안 됨 + 안내 · 고객 있으면 저장(그 고객)
  §9 추가 발주(등록 화면) — 고객 이름 후보 여럿(번호 못 정함) = 저장 안 하고 되돌림 · 화면 글 · 고른 번호면 저장
  §10 add_followup_order 직접 — 고객 없으면 저장 안 함(처음 고객으로 채우지 않음)
"""
import contextlib
import io
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z166-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z166_")
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
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    TEAM = ins(c, "teams", {"name": "기술영업팀", "code": "01", "entity": "KOR", "display_order": 1})
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales, "
              "can_view_logistics, can_use_logistics) VALUES ('가상대표', 'ceo', 'Z166', 'Z166', 'sso_only_no_local_password', 1, 1, ?, 1, 1, 1, 1)", (TEAM,))
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='Z166'").fetchone())
    c.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', ?)", (TEAM,))
    CK = ins(c, "customers", {"name": "국내전자(주)", "alias": "국내전자"})
    CA = ins(c, "customers", {"name": "ALPHA VIETNAM CO LTD", "alias": "알파베트남"})
    CB = ins(c, "customers", {"name": "BRAVO INDIA PVT LTD", "alias": "브라보인도"})
    CC = ins(c, "customers", {"name": "CHARLIE INDONESIA PT", "alias": "찰리인니"})
    CX = ins(c, "customers", {"name": "취소된구매자 LTD", "alias": "취소구매자"})
    ins(c, "customers", {"name": "드림텍", "alias": "드림텍(본사)"})          # 이름 후보 여럿
    ins(c, "customers", {"name": "(주) 드림텍 아산", "alias": "드림텍"})
    # 관리번호 처음 등록 값 = 국내전자 · 내수 · KRW (화면·서류에 쓰면 틀린 값)
    P = ins(c, "projects", {"code": "903M2509", "mgmt_code": "903M2509", "name": "가상 수출 부품", "customer_id": CK, "customer_name": "국내전자(주)",
                            "po_type": "신규", "is_export": 0, "currency": "KRW", "order_amount": 5000000, "order_date": "2025-09-01",
                            "due_date": "2025-10-31", "status": "진행중", "stage": "수주확정", "biz_div": "M", "project_type": "PARTS",
                            "shipment_form": "PARTS", "is_archived": 0, "secondary_customer": "처음2차"})

    def so(no, cu, ccy, amt, od, due, st, items):
        oid = ins(c, "orders", {"project_id": P, "order_no": no, "customer_id": cu, "currency": ccy, "total_amount": amt, "order_date": od,
                                "due_date": due, "status": st, "po_type": "추가", "unit_qty": 1, "so_type": "PARTS_EXPORT",
                                "created_at": od + " 09:00:00"})
        for lab, q, up, iex, box in items:
            ins(c, "order_items", {"order_id": oid, "qty": q, "unit_price": up, "amount": q * up, "unit_label": lab, "is_export": iex,
                                   "currency": ccy, "unit_status": "진행중", "invoice_unit_price_usd": (up if ccy == "USD" else None),
                                   "box_no": box, "weight_kg": 2.5, "hs_code": "8473.30", "origin": "KR"})
        return oid
    O1 = so("M-250901-1", CK, "KRW", 5000000, "2025-09-01", "2025-10-31", "CONFIRMED", [("국내-부품", 10, 500000, 0, "")])
    O2 = so("M-251122-2", CA, "USD", 1500, "2025-11-22", "2025-12-20", "IN_PRODUCTION",
            [("A-부품1", 2, 500, 1, "BOX-1"), ("A-부품2", 1, 500, 1, "BOX-1")])
    O3 = so("M-260805-1", CB, "USD", 800, "2026-08-05", "2026-09-10", "SHIPPED", [("B-부품1", 4, 200, 1, "BOX-2")])
    O4 = so("M-260105-1", CC, "USD", 300, "2026-01-05", "2026-02-10", "CONFIRMED", [("C-부품1", 3, 100, 1, "BOX-3")])
    OX = so("M-260901-9", CX, "USD", 9999, "2026-09-01", "2026-09-30", "CANCELLED", [("X-부품", 1, 9999, 1, "BOX-9")])
    # 수주 1개 관리번호(예전처럼 바로)
    P1 = ins(c, "projects", {"code": "904M2510", "mgmt_code": "904M2510", "name": "가상 한 수주", "customer_id": CA, "customer_name": "ALPHA VIETNAM CO LTD",
                             "po_type": "신규", "is_export": 1, "currency": "USD", "status": "진행중", "biz_div": "M", "project_type": "PARTS", "is_archived": 0})
    P1O = ins(c, "orders", {"project_id": P1, "order_no": "M-251001-1", "customer_id": CA, "currency": "USD", "total_amount": 700, "order_date": "2025-10-01",
                            "due_date": "2025-11-01", "status": "CONFIRMED", "po_type": "신규"})
    ins(c, "order_items", {"order_id": P1O, "qty": 7, "unit_price": 100, "amount": 700, "unit_label": "ONE-부품", "is_export": 1, "currency": "USD",
                           "unit_status": "진행중", "invoice_unit_price_usd": 100})
    # 추가 발주 대상(장비 관리번호)
    P3 = ins(c, "projects", {"code": "905T2511", "mgmt_code": "905T2511", "name": "가상 장비", "customer_id": CK, "customer_name": "국내전자(주)",
                             "po_type": "신규", "is_export": 0, "currency": "KRW", "status": "진행중", "biz_div": "T", "project_type": "NEW_EQUIP",
                             "shipment_form": "ASSEMBLY", "model_name": "M1", "equip_name": "E1", "is_archived": 0})
    ins(c, "orders", {"project_id": P3, "order_no": "T-251101-1", "customer_id": CK, "currency": "KRW", "total_amount": 1000000,
                      "order_date": "2025-11-01", "status": "CONFIRMED", "po_type": "신규", "so_type": "EQUIPMENT"})

import app.main as M                                        # noqa: E402
import app.sso_client as SSO                                # noqa: E402
import app.project_workflow as PW                           # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: ADMIN
M._can_manual_mgmt = lambda u: True
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
SSO.notify_via_messenger = lambda *a, **k: {"ok": True, "sent": 0}
QR = []
_orig_qr = M._make_qr_svg
M._make_qr_svg = lambda data, *a, **k: (QR.append(data) or _orig_qr(data, *a, **k))
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅", label)
    else:
        FAIL += 1
        print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:600])


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or ""))


def get(url):
    r = cl.get(url)
    return r.status_code, r.text


def xl(url):
    r = cl.get(url)
    if r.status_code != 200 or "spreadsheet" not in (r.headers.get("content-type") or ""):
        return r.status_code, None, r.headers.get("content-disposition", "")
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(r.content))
    vals = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            vals.append(" | ".join("" if v is None else str(v) for v in row))
    return 200, "\n".join(vals), r.headers.get("content-disposition", "")


ITEMS = {O2: ["A-부품1", "A-부품2"], O3: ["B-부품1"], O4: ["C-부품1"]}
BUY = {O2: "ALPHA VIETNAM CO LTD", O3: "BRAVO INDIA PVT LTD", O4: "CHARLIE INDONESIA PT"}
NO = {O1: "M-250901-1", O2: "M-251122-2", O3: "M-260805-1", O4: "M-260105-1", OX: "M-260901-9"}
ALL_LABELS = ["국내-부품", "A-부품1", "A-부품2", "B-부품1", "C-부품1", "X-부품"]

# ─────────────────────────────────────────
print("§1 so 없이 = 고르기 화면")
for path in ("packing-list", "invoice", "packing-list.xlsx", "invoice.xlsx", "invoice-pl.xlsx"):
    st, H = get("/export/prep/%d/%s" % (P, path))
    ht = text(H)
    check("%s (so 없음) → 고르기 화면(섞어 만들지 않음)" % path,
          st == 200 and "어느 수주의 서류인지 골라 주세요" in ht and "903M2509" in ht and not any(l in ht for l in ALL_LABELS), (st, ht[:200]))
st, H = get("/export/prep/%d/invoice" % P)
ht = text(H)
check("고르기 화면 = 살아 있는 수주 4건 · 취소 수주 안 보임", all(NO[o] in ht for o in (O1, O2, O3, O4)) and NO[OX] not in ht, ht[:400])
check("고르기 화면 = 구매자·통화·품목 수·납기", "알파베트남" in ht and "브라보인도" in ht and "찰리인니" in ht and "USD" in ht and "2025-12-20" in ht, ht[:600])
check("내수 수주 = 「내수 — 수출 서류 없음」 · 서류 단추 없음", "내수 — 수출 서류 없음" in ht and ("so=%d" % O1) not in H, ("so=%d" % O1) in H)
check("수출 수주마다 PL·CI·엑셀·신고용 단추", all(("packing-list?so=%d" % o) in H and ("invoice?so=%d" % o) in H and ("invoice.xlsx?so=%d" % o) in H
                                         and ("invoice-pl.xlsx?so=%d" % o) in H for o in (O2, O3, O4)))
check("고르기 화면에 「✕ 닫기」 · 순서 줄(지금 할 일)", "knk-close-btn" in H and "수주 고르기" in ht and "👉 지금 하실 일" in ht)
check("화면 글에 「대표값」「관리번호 값」 없음", "대표값" not in ht and "관리번호 값" not in ht)

# ─────────────────────────────────────────
print("§2 수주별 서류")
nos = set()
for o in (O2, O3, O4):
    st, H = get("/export/prep/%d/packing-list?so=%d" % (P, o))
    ht = text(H)
    others = [l for l in ALL_LABELS if l not in ITEMS[o]]
    check("PL %s 200 · 구매자 = %s 하나만" % (NO[o], BUY[o]), st == 200 and BUY[o] in ht and not any(BUY[x] in ht for x in BUY if x != o), ht[:300])
    check("PL %s 품목 = 그 수주 것만" % NO[o], all(l in ht for l in ITEMS[o]) and not any(l in ht for l in others), [l for l in others if l in ht])
    m = re.search(r'class="doc-no">([^<]+)<', H)
    pl_no = m.group(1).strip() if m else ""
    check("PL 번호에 수주번호 (%s)" % pl_no, pl_no == "PL-903M2509-%s" % NO[o], pl_no)
    nos.add(pl_no)
    st, H = get("/export/prep/%d/invoice?so=%d" % (P, o))
    ht = text(H)
    m = re.search(r'class="doc-no">([^<]+)<', H)
    ci_no = m.group(1).strip() if m else ""
    check("CI %s 200 · 구매자 하나 · 통화 USD · 번호 %s" % (NO[o], ci_no),
          st == 200 and BUY[o] in ht and not any(BUY[x] in ht for x in BUY if x != o) and ci_no == "CI-903M2509-%s" % NO[o]
          and "통화가 여러 개" not in ht and "처음2차" not in ht, ht[:300])
    nos.add(ci_no)
    for path in ("packing-list.xlsx", "invoice.xlsx", "invoice-pl.xlsx"):
        st, X, cd = xl("/export/prep/%d/%s?so=%d" % (P, path, o))
        check("%s %s 200 · 그 수주 품목·구매자만 · 파일 이름에 수주번호" % (path, NO[o]),
              st == 200 and X is not None and all(l in X for l in ITEMS[o]) and not any(l in X for l in others)
              and (path == "invoice-pl.xlsx" or BUY[o] in X) and NO[o] in cd.replace("%2D", "-"), (st, cd, (X or "")[:300]))
check("서류 번호 6개 모두 다름(겹치지 않음)", len(nos) == 6, nos)
with D.db_session() as c:
    _p, ci3, l3 = M._export_ci_build(c, P, O3)
check("CI 금액(O3) = 4×200 = 800 USD", ci3["currency"] == "USD" and abs(ci3["total_amount"] - 800) < 0.01 and len(l3) == 1, (ci3["currency"], ci3["total_amount"]))

# ─────────────────────────────────────────
print("§3 내수·취소 수주를 so 로")
st, H = get("/export/prep/%d/invoice?so=%d" % (P, O1))
check("내수 수주 so → 고르기 화면 + 「내수라 수출 서류가 없습니다」", st == 200 and "어느 수주의 서류인지" in text(H) and "내수" in text(H) and "국내-부품" not in text(H))
st, H = get("/export/prep/%d/packing-list?so=%d" % (P, OX))
check("취소 수주 so → 고르기 화면 + 「살아 있는 수주가 아닙니다」", st == 200 and "살아 있는 수주가 아닙니다" in text(H) and "X-부품" not in text(H))
st, H = get("/export/prep/%d/packing-list?so=abc" % P)
check("엉뚱한 so → 고르기 화면(500 아님)", st == 200 and "어느 수주의 서류인지" in text(H))
st, H = get("/export/prep/%d/packing-list?so=%d" % (P, P1O))
check("다른 관리번호 수주 so → 고르기 화면(남의 수주 품목 안 보임)", st == 200 and "ONE-부품" not in text(H))

# ─────────────────────────────────────────
print("§4 수주 1개 관리번호 = 예전처럼 바로")
st, H = get("/export/prep/%d/packing-list" % P1)
check("PL 바로 열림 · 그 수주 품목", st == 200 and "ONE-부품" in text(H) and "어느 수주의 서류인지" not in text(H), text(H)[:200])
st, H = get("/export/prep/%d/invoice" % P1)
check("CI 바로 열림", st == 200 and "ONE-부품" in text(H) and "CI-904M2510-M-251001-1" in H)
st, X, cd = xl("/export/prep/%d/invoice-pl.xlsx" % P1)
check("신고용 엑셀 바로", st == 200 and X and "ONE-부품" in X)
st, H = get("/export/prep/%d" % P1)
check("통관 입력 상세 = 신고 서류 정보 칸 바로(그 수주)", st == 200 and ('data-so="%d"' % P1O) in H)

# ─────────────────────────────────────────
print("§5 통관 입력 상세 · 신고 서류 정보 수주별")
with D.db_session() as c:
    M._doc_meta_ensure(c)
    c.execute("INSERT INTO export_doc_meta(project_id, invoice_no, consignee, carrier, incoterms) VALUES(?,?,?,?,?)",
              (P, "KNK-OLD-7", "ALPHA VIETNAM CO LTD\nHanoi", "OLD-CARRIER", "FOB"))
st, H = get("/export/prep/%d" % P)
ht = text(H)
check("상세 200 · 수주별 서류 표(내수 줄 회색 · 수출 3줄 단추)", st == 200 and "수주별 수출 서류" in ht and all(("invoice?so=%d" % o) in H for o in (O2, O3, O4))
      and ("invoice?so=%d" % O1) not in H and "내수 — 수출 서류 없음" in ht, ht[:300])
check("수출 수주 여럿 · so 없음 = 서류 정보 칸 대신 「수주를 고르세요」 안내", 'id="dmForm"' not in H and "서류 정보" in ht and "수주마다 따로 저장" in ht)
check("머리 단추(패킹리스트 등) = so 없이 → 고르기 화면으로", ('/export/prep/%d/packing-list"' % P) in H)
st, H = get("/export/prep/%d?so=%d" % (P, O3))
ht = text(H)
check("so=O3 상세 = 그 수주 서류 정보 · 옛 값 「처음 값」 · Invoice No 끝 -순번",
      ('data-so="%d"' % O3) in H and "관리번호 하나로 저장한 값" in ht and "KNK-OLD-7-" in H and "OLD-CARRIER" in H, ht[:300])
check("받는 곳이 이 수주 구매자와 다르면 알림(막지 않음)", "BRAVO INDIA PVT LTD" in ht and "이름이 보이지 않습니다" in ht)
check("머리 단추 = 고른 수주(?so=O3)", ("/export/prep/%d/packing-list?so=%d" % (P, O3)) in H)
r = cl.post("/export/prep/%d/doc-meta" % P, data={"invoice_no": "X-1", "consignee": "C"})
check("저장 so 없음(수출 수주 여럿) = 400 · 저장 안 함", r.status_code == 400 and "골라" in r.json().get("error", ""), r.text[:200])
r = cl.post("/export/prep/%d/doc-meta" % P, data={"so": str(O2), "invoice_no": "INV-A-1", "consignee": "ALPHA VIETNAM CO LTD\nHCMC", "incoterms": "CIF"})
check("저장 so=O2 = 성공", r.status_code == 200 and r.json().get("ok") and r.json().get("order_no") == NO[O2], r.text[:200])
r = cl.post("/export/prep/%d/doc-meta" % P, data={"so": str(O1), "invoice_no": "INV-K"})
check("내수 수주로 저장 = 400", r.status_code == 400)
with D.db_session() as c:
    old = dict(c.execute("SELECT * FROM export_doc_meta WHERE project_id=?", (P,)).fetchone())
    rows = [dict(x) for x in c.execute("SELECT * FROM export_doc_meta_so")]
    L = M._z166_doc_orders(c, P)
    o3 = next(x for x in L["doc"] if x["id"] == O3)
    dm3 = M._doc_meta_get(c, P, None, o3)
    o2 = next(x for x in L["doc"] if x["id"] == O2)
    dm2 = M._doc_meta_get(c, P, None, o2)
check("옛 관리번호 단위 값 그대로(지우지 않음)", old["invoice_no"] == "KNK-OLD-7" and old["carrier"] == "OLD-CARRIER", old)
check("수주별 표 = O2 한 줄만(O3 에 저절로 복사 저장 안 함)", len(rows) == 1 and rows[0]["order_id"] == O2 and rows[0]["project_id"] == P, rows)
check("O2 = 저장 값 · O3 = 아직 옛 값(처음 값)", dm2["_src"] == "so" and dm2["invoice_no"] == "INV-A-1" and dm3["_src"] == "old" and dm3["carrier"] == "OLD-CARRIER",
      (dm2.get("_src"), dm2.get("invoice_no"), dm3.get("_src")))
st, X, cd = xl("/export/prep/%d/invoice-pl.xlsx?so=%d" % (P, O2))
check("신고용 엑셀(O2) 머리 = 저장한 O2 값(INV-A-1 · CIF · HCMC)", X and "INV-A-1" in X and "CIF" in X and "HCMC" in X, (X or "")[:300])
st, X, cd = xl("/export/prep/%d/invoice-pl.xlsx?so=%d" % (P, O4))
check("신고용 엑셀(O4) 머리 = 옛 값 + 순번(발주일 순 2번째 → KNK-OLD-7-2) · O2 값 안 섞임", X and "KNK-OLD-7-2" in X and "INV-A-1" not in X, (X or "")[:300])

# ─────────────────────────────────────────
print("§6 금액 대조(관리번호 통째 → 수주별)")
with D.db_session() as c:
    _p, ci_all, l_all = M._export_ci_build(c, P)          # 예전 방식(so 없음)
    per = [M._export_ci_build(c, P, o) for o in (O2, O3, O4)]
    _p, ci1, l1 = M._export_ci_build(c, P, O1)
sum_per = round(sum(x[1]["total_amount"] for x in per), 2)
n_per = sum(len(x[2]) for x in per)
check("예전 통째 = 5줄 · 5,002,600(KRW 500만 + USD 2,600 섞임 · 통화 여러 개 알림)",
      len(l_all) == 5 and round(ci_all["total_amount"], 2) == 5002600 and any("통화가 여러 개" in w for w in ci_all["ci_warn155"]), (len(l_all), ci_all["total_amount"]))
check("수주별 합 = USD 2,600(4줄) = 통째 − 내수 수주 몫(5,000,000 KRW · 1줄)",
      sum_per == 2600 and n_per == 4 and round(ci_all["total_amount"] - ci1["total_amount"], 2) == sum_per and len(l1) == 1, (sum_per, n_per, ci1["total_amount"]))
check("취소 수주(9,999) 어디에도 안 섞임", all("X-부품" not in [l["part_name"] for l in x[2]] for x in per) and "X-부품" not in [l["part_name"] for l in l_all])
print("    대조: 통째 %s줄 %s · 수주별 %s줄 %s · 내수 %s줄 %s" % (len(l_all), ci_all["total_amount"], n_per, sum_per, len(l1), ci1["total_amount"]))

# ─────────────────────────────────────────
print("§7 출고 QR")
QR.clear()
r = cl.get("/export/ship/%d/qr.svg?so=%d" % (P, O3))
check("수주 QR = 주소에 so", r.status_code == 200 and QR and QR[-1].endswith("/export/ship/%d?so=%d" % (P, O3)), QR[-1:])
r = cl.get("/export/ship/%d/box-qr.svg?so=%d&b=BOX-2" % (P, O3))
check("박스 QR = ?so=…&b=BOX-2", r.status_code == 200 and QR[-1].endswith("/export/ship/%d?so=%d&b=BOX-2" % (P, O3)), QR[-1:])
r = cl.get("/export/ship/%d/box-qr.svg?b=BOX-2" % P)
check("so 없이 부르면 옛 주소 그대로(?b=BOX-2)", r.status_code == 200 and QR[-1].endswith("/export/ship/%d?b=BOX-2" % P), QR[-1:])
st, H = get("/export/ship/%d?b=BOX-2" % P)
check("옛 박스 라벨(?b= 만) 그대로 열림 · 그 박스 품목", st == 200 and "B-부품1" in text(H) and "옛 라벨" in text(H), text(H)[:300])
st, H = get("/export/ship/%d" % P)
check("옛 출하 건 라벨(so·b 없음) = 고르기 화면", st == 200 and "어느 수주의 서류인지" in text(H))
st, H = get("/export/ship/%d?so=%d" % (P, O4))
check("수주 출고 보기 = 그 수주 품목만 · 박스 링크에 so", st == 200 and "C-부품1" in text(H) and "A-부품1" not in text(H) and ("?so=%d&amp;b=" % O4 in H or "?so=%d&b=" % O4 in H), text(H)[:300])
st, H = get("/export/ship/%d/qr/print?so=%d" % (P, O2))
check("QR 라벨 인쇄(O2) = 수주번호 · QR 그림 주소에 so", st == 200 and NO[O2] in H and ("qr.svg?scale=6&amp;so=%d" % O2 in H or "qr.svg?scale=6&so=%d" % O2 in H), st)
st, H = get("/export/ship/%d/qr/print" % P)
check("QR 라벨 인쇄 so 없음 = 고르기 화면", st == 200 and "어느 수주의 서류인지" in text(H))

# ─────────────────────────────────────────
print("§8 추가 발주(프로젝트 상세 창)")
with D.db_session() as c:
    n0 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P3,)).fetchone()[0]
r = cl.post("/projects/%d/add-followup-order" % P3, data={"order_date": "2026-11-27", "total_amount": "1000", "qty": "1", "currency": "KRW"})
j = r.json()
with D.db_session() as c:
    n1 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P3,)).fetchone()[0]
check("고객 없이 = 저장 안 됨 + 「👉 고객사를 등록(선택)해 주세요」", r.status_code == 400 and j.get("need_customer") and "고객사를 등록(선택)해 주세요" in j.get("message", "")
      and "세금계산서를 받는 1차 고객사" in j.get("message", "") and n1 == n0, (r.status_code, j, n0, n1))
r = cl.post("/projects/%d/add-followup-order" % P3, data={"order_date": "2026-11-27", "total_amount": "1000", "qty": "1", "currency": "KRW", "customer_id": "99999"})
check("없는 고객 번호 = 저장 안 됨", r.status_code == 400)
r = cl.post("/projects/%d/add-followup-order" % P3, data={"order_date": "2026-11-27", "total_amount": "1000", "qty": "1", "currency": "KRW", "customer_id": str(CB)})
j = r.json()
with D.db_session() as c:
    row = c.execute("SELECT customer_id FROM orders WHERE id=?", (j.get("order_id"),)).fetchone() if j.get("order_id") else None
check("고객 고르면 저장 · 그 수주 고객 = 고른 고객(처음 고객 아님)", j.get("ok") and row and row[0] == CB, (j, row and row[0]))
st, H = get("/project/%d" % P3)
check("상세 창에 1차 고객사 칸(필수 표시) · 고객사 등록 안내", st == 200 and 'data-cust-name="fup_customer_name"' in H and "/customers/new" in H, st)

# ─────────────────────────────────────────
print("§9 추가 발주(등록 화면)")
base = {"quick": "1", "po_type": "추가", "mgmt_code": "905T2511", "biz_div": "T", "name": "가상 장비", "model": "M1", "equip_name": "E1",
        "order_date": "2026-11-27", "due_date": "2026-12-27", "unit_price": "1000", "unit_qty": "1", "currency": "KRW", "shipment_form": "ASSEMBLY",
        "is_export": "0", "stage": "진행중", "status": "진행중"}
with D.db_session() as c:
    n0 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P3,)).fetchone()[0]
r = cl.post("/projects/new", data=dict(base, customer_name="드림텍"), follow_redirects=False)
loc = r.headers.get("location", "")
with D.db_session() as c:
    n1 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P3,)).fetchone()[0]
check("고객 이름 후보 여럿(번호 못 정함) = 저장 안 하고 되돌림(error=followup_customer_required)",
      r.status_code == 303 and "error=followup_customer_required" in loc and n1 == n0, (r.status_code, loc, n0, n1))
st, H = get("/projects/quick?error=followup_customer_required&biz_div=T")
check("등록 화면 글 = 「👉 고객사를 등록(선택)해 주세요 — 이 수주의 세금계산서를 받는 1차 고객사입니다」",
      st == 200 and "followup_customer_required:'👉 고객사를 등록(선택)해 주세요 — 이 수주의 세금계산서를 받는 1차 고객사입니다" in H, st)
check("등록 화면 = 되돌아오면 보낸 값 되살림(sessionStorage 임시본)", ".sent'" in H and "sessionStorage.setItem(QF_KEY+'.sent'" in H)
r = cl.post("/projects/new", data=dict(base, customer_name="BRAVO INDIA PVT LTD", customer_id=str(CB)), follow_redirects=False)
with D.db_session() as c:
    n2 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P3,)).fetchone()[0]
    last = c.execute("SELECT customer_id FROM orders WHERE project_id=? ORDER BY id DESC LIMIT 1", (P3,)).fetchone()
check("고객 번호 고르면 저장 · 그 고객", r.status_code == 303 and n2 == n1 + 1 and last[0] == CB, (r.status_code, r.headers.get("location"), n1, n2, last and last[0]))

# ─────────────────────────────────────────
print("§10 add_followup_order 직접")
with D.db_session() as c:
    n0 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P3,)).fetchone()[0]
    res = PW.add_followup_order(c, P3, order_date="2026-11-27", total_amount=100, qty=1)
    n1 = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P3,)).fetchone()[0]
check("고객 안 넘기면 저장 안 함(처음 고객으로 안 채움)", (not res.get("ok")) and res.get("need_customer") and n1 == n0, (res, n0, n1))
with D.db_session() as c:
    res = PW.add_followup_order(c, P3, order_date="2026-11-27", total_amount=100, qty=1, order_customer_id=CC)
    cu = c.execute("SELECT customer_id FROM orders WHERE id=?", (res.get("order_id"),)).fetchone()
check("고객 넘기면 그 고객으로 저장", res.get("ok") and cu and cu[0] == CC, (res, cu and cu[0]))
with D.db_session() as c:
    res = PW.add_followup_order(c, P3, order_date="2026-11-27", total_amount=100, qty=1, order_customer_id=None, customer_required=False)
    cu = c.execute("SELECT customer_id FROM orders WHERE id=?", (res.get("order_id"),)).fetchone()
check("customer_required=False(새 관리번호의 추가 품목 전용) = 고객 빈칸으로 저장(처음 고객 안 채움)", res.get("ok") and cu and cu[0] is None, (res, cu and cu[0]))

print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
