# -*- coding: utf-8 -*-
"""z1191z165 시험 — 「관리번호에는 고객사가 없다」: 화면·서류·엑셀이 수주마다 값을 쓰는지(대표 11-27)

실제와 같은 모양의 관리번호 하나:
  수주 4건(살아 있음) + 취소 1건 · 1차 고객 4곳(삼성전자 · SAMSUNG INDIA · KNK VINA · PT Samsung Electronics Indonesia)
  2건 입금 끝남(PAID) · 통화 KRW/USD 섞임 · 2차는 일부만 · 관리번호 처음 등록 값 = 「삼성전자 · 신규 · 내수 · KRW」
  §1 공용 요약(orders_summary) — 수주 수·고객 「외 N곳」·통화별 합계·취소 숨김 수
  §2 프로젝트 상세의 수주 수 = 각 화면의 수주 수(숨김 표시 포함)
  §3 프로젝트 목록(고객·PO유형·발주일) · 고객 찾기(수주 고객으로 찾힘)
  §4 프로젝트 목록 엑셀 — 「수주액(원)」 = 발주 달 환율 환산 합계 · 외화가 원으로 안 섞임 · 고객 = 수주 고객 전부
  §5 수주 목록 — 수주마다 고객·PO유형·모델(관리번호 값으로 채우지 않음)
  §6 견적서·발주서 자리 찾기 — 수주 고객으로 찾힘 · 줄마다 그 수주 고객
  §7 관리번호대장(화면·엑셀) — 고객 칸 수주 기준
  §8 수출 — 대상 판정(관리번호 「내수」여도 수출 품목 있으면) · 통관 머리 · PL·CI 구매자·발주일·납기 · 신고 서류 받는 곳 · QR
  §9 제작요청서 — 종이·카드·목록·이음 카드 = 고른 수주 값
  §10 엑셀 일괄 등록 추가 발주 — 고객사 빈칸/이름 후보 여럿 = 저장 안 하고 「확인 필요」 · 다른 줄은 진행
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z165-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z165_")
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
              "can_view_logistics, can_use_logistics) VALUES ('가상대표', 'ceo', 'Z165', 'Z165', 'sso_only_no_local_password', 1, 1, ?, 1, 1, 1, 1)", (TEAM,))
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='Z165'").fetchone())
    c.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', ?)", (TEAM,))
    CU1 = ins(c, "customers", {"name": "삼성전자(주)", "alias": "삼성전자"})
    CU2 = ins(c, "customers", {"name": "SAMSUNG INDIA ELECTRONICS PVT. LTD.", "alias": "SAMSUNG INDIA"})
    CU3 = ins(c, "customers", {"name": "KNK VINA CO LTD", "alias": "KNK VINA"})
    CU4 = ins(c, "customers", {"name": "PT Samsung Electronics Indonesia", "alias": ""})
    CU5 = ins(c, "customers", {"name": "취소된고객(주)", "alias": "취소된고객"})
    # 이름 후보 여럿(한 곳은 정식명 · 다른 곳은 시스템명이 「드림텍」)
    ins(c, "customers", {"name": "드림텍", "alias": "드림텍(본사)"})
    ins(c, "customers", {"name": "(주) 드림텍 아산", "alias": "드림텍"})
    # 월 기준환율(1일 행) — 발주 달 3월 1,400 · 5월 1,380
    ins(c, "exchange_rates", {"rate_date": "2026-03-01", "from_currency": "USD", "to_currency": "KRW", "rate": 1400})
    ins(c, "exchange_rates", {"rate_date": "2026-05-01", "from_currency": "USD", "to_currency": "KRW", "rate": 1380})
    # 관리번호 처음 등록 값 = 삼성전자 · 신규 · 내수 · KRW · 1월 · 모델 FIRST-MODEL
    P = ins(c, "projects", {"code": "901T2601", "mgmt_code": "901T2601", "name": "가상 기능검사기", "customer_id": CU1, "customer_name": "삼성전자(주)",
                            "po_type": "신규", "is_export": 0, "currency": "KRW", "order_amount": 100000000, "order_date": "2026-01-10",
                            "due_date": "2026-02-28", "status": "진행중", "stage": "수주확정", "biz_div": "T", "project_type": "NEW_EQUIP",
                            "shipment_form": "ASSEMBLY", "model_name": "FIRST-MODEL", "equip_name": "가상 검사기", "unit_qty": 1,
                            "secondary_customer": "처음2차", "is_archived": 0, "sales_name": "가상대표"})

    def so(no, cu, ccy, amt, od, due, st, po, iex, end, model, label):
        oid = ins(c, "orders", {"project_id": P, "order_no": no, "customer_id": cu, "currency": ccy, "total_amount": amt, "order_date": od,
                                "due_date": due, "status": st, "po_type": po, "end_customer": end, "model_name": model, "unit_label": label,
                                "unit_qty": 1, "so_type": "EQUIPMENT", "created_at": od + " 09:00:00"})
        ins(c, "order_items", {"order_id": oid, "qty": 1, "unit_price": amt, "amount": amt, "unit_label": label, "is_export": iex,
                               "currency": ccy, "unit_status": "진행중"})
        return oid
    O1 = so("T-260110-1", CU1, "KRW", 100000000, "2026-01-10", "2026-02-28", "CONFIRMED", "신규", 0, None, None, "1호기")
    O2 = so("T-260305-1", CU2, "USD", 50000, "2026-03-05", "2026-04-30", "PAID", "추가", 1, "Samsung Noida", "INDIA-MODEL", "2호기")
    O3 = so("T-260520-1", CU3, "USD", 30000, "2026-05-20", "2026-06-30", "PAID", "추가", 1, None, "VINA-MODEL", "3호기")
    O4 = so("T-260701-1", CU4, "KRW", 20000000, "2026-07-01", "2026-08-31", "IN_PRODUCTION", "개조", 1, None, None, "4호기")
    OX = so("T-260801-9", CU5, "USD", 99999, "2026-08-01", "2026-09-30", "CANCELLED", "추가", 1, None, None, "9호기")
    LIVE = ["T-260110-1", "T-260305-1", "T-260520-1", "T-260701-1"]
    CUSTS = ["삼성전자", "SAMSUNG INDIA", "KNK VINA", "PT Samsung Electronics Indonesia"]
    # 비교용 다른 관리번호 하나(내수 · 고객 1곳)
    P2 = ins(c, "projects", {"code": "902T2601", "mgmt_code": "902T2601", "name": "가상 다른 장비", "customer_id": CU1, "customer_name": "삼성전자(주)",
                             "po_type": "신규", "is_export": 0, "currency": "KRW", "order_amount": 5000000, "order_date": "2026-01-11",
                             "status": "진행중", "biz_div": "T", "project_type": "NEW_EQUIP", "is_archived": 0})
    ins(c, "orders", {"project_id": P2, "order_no": "T-260111-1", "customer_id": CU1, "currency": "KRW", "total_amount": 5000000,
                      "order_date": "2026-01-11", "status": "CONFIRMED", "po_type": "신규"})

EXPECT_KRW = 100000000 + 50000 * 1400 + 30000 * 1380 + 20000000   # 231,400,000

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
CARDS = []
SSO.notify_via_messenger = lambda emp_nos, title, body, link, card=None, **k: (CARDS.append({"title": title, "body": body, "card": card}) or {"ok": True, "sent": len(emp_nos or [])})
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
    """태그 빼고 글만(비교용)."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or ""))


def get(url):
    r = cl.get(url)
    return r.status_code, r.text


def n_live_in(html):
    return sum(1 for no in LIVE if no in (html or ""))


# ─────────────────────────────────────────
print("§1 공용 요약 orders_summary")
with D.db_session() as c:
    S = PW.orders_summary_one(c, P)
    SEL = PW.orders_summary_one(c, P, order_ids=[O2, O3])
check("살아 있는 수주 4건 · 취소 1건은 숨김 수로", S["n"] == 4 and S["n_cancelled"] == 1 and S["n_paid"] == 2, (S["n"], S["n_cancelled"], S["n_paid"]))
check("1차 고객 4곳 · 「삼성전자 외 3곳」", S["custs"] == CUSTS and S["cust_txt"] == "삼성전자 외 3곳", (S["custs"], S["cust_txt"]))
check("통화별 합계(KRW 1.2억 · USD 8만) · 취소 수주 금액 안 섞임", S["by_cur"] == {"KRW": 120000000.0, "USD": 80000.0}, S["by_cur"])
check("PO유형 = 수주마다(신규·추가·개조)", S["po_types"] == ["신규", "추가", "개조"], S["po_types"])
check("2차 = 적힌 것만(Samsung Noida)", S["ends"] == ["Samsung Noida"], S["ends"])
check("거래구분 = 품목 줄(수출·내수 섞임)", S["trades"] == ["수출", "내수"] and S["any_export"], S["trades"])
check("발주일 첫 ~ 마지막", S["date_txt"] == "2026-01-10 ~ 2026-07-01", S["date_txt"])
check("고른 수주만(O2·O3) = SAMSUNG INDIA 외 1곳 · USD만", SEL["cust_txt"] == "SAMSUNG INDIA 외 1곳" and SEL["currencies"] == ["USD"], (SEL["cust_txt"], SEL["currencies"]))

# ─────────────────────────────────────────
print("§2 프로젝트 상세의 수주 수(기준)")
st, H = get("/project/%d" % P)
DETAIL_N = n_live_in(H)
check("프로젝트 상세 열림 · 살아 있는 수주 4건 모두 보임", st == 200 and DETAIL_N == 4, (st, DETAIL_N))

# ─────────────────────────────────────────
print("§3 프로젝트 목록")
st, H = get("/projects")
row = H[H.find("901T2601"):H.find("901T2601") + 6000] if "901T2601" in H else ""
rt = text(row)
check("목록 열림", st == 200, st)
check("고객 = 「삼성전자 외 3곳」(마우스 올리면 4곳 전부)", "삼성전자" in rt and "외 3곳" in rt and "PT Samsung Electronics Indonesia" in row, rt[:300])
check("PO유형 = 첫 수주 값 + 「외 2」(관리번호 「신규」만이 아님)", "외 2" in rt and "수주별 PO유형: 신규 · 추가 · 개조" in row, rt[:400])
check("발주일 = 수주 발주일(첫 + 외 3건)", "2026-01-10 외 3건" in rt, rt[:500])
for q, why in (("SAMSUNG INDIA", "수주 1차 고객 시스템명"), ("Indonesia", "수주 1차 고객 정식명"), ("Samsung Noida", "수주 2차"), ("T-260520-1", "수주번호")):
    st, H = get("/projects?q=" + q)
    check("고객 찾기 「%s」(%s) → 관리번호가 찾힘" % (q, why), st == 200 and "901T2601" in H, st)
st, H = get("/projects?q=취소된고객")
check("취소 수주 고객으로는 안 찾힘", st == 200 and "901T2601" not in H, st)

# ─────────────────────────────────────────
print("§4 프로젝트 목록 엑셀")
from openpyxl import load_workbook                         # noqa: E402
r = cl.get("/projects/export.xlsx")
check("엑셀 내려받기 200", r.status_code == 200, r.status_code)
wb = load_workbook(io.BytesIO(r.content))
ws = wb.active
hdr, xrow = None, None
for rr in ws.iter_rows(values_only=True):
    if rr and "관리코드" in rr:
        hdr = list(rr)
    elif hdr and rr and rr[0] == "901T2601":
        xrow = dict(zip(hdr, rr))
check("머리 칸: 수주액(원) · 수주액(통화별) · 수주 수 · 확인", hdr and all(h in hdr for h in ("수주액(원)", "수주액(통화별)", "수주 수", "확인")), hdr)
check("수주액(원) = 발주 달 환율로 환산한 합계 %s" % format(EXPECT_KRW, ","), xrow and xrow["수주액(원)"] == EXPECT_KRW, xrow and xrow.get("수주액(원)"))
check("외화가 「원」 칸에 숫자 그대로 안 섞임(120,080,000 아님 · 처음 등록 값 100,000,000 아님)",
      xrow and xrow["수주액(원)"] not in (120080000, 100000000), xrow and xrow.get("수주액(원)"))
check("통화별 칸 = KRW 120,000,000 · USD 80,000.00", xrow and xrow["수주액(통화별)"] == "KRW 120,000,000 · USD 80,000.00", xrow and xrow.get("수주액(통화별)"))
check("수주 수 4 = 상세와 같음 · 확인 칸에 「취소 수주 1건 뺌」", xrow and xrow["수주 수"] == DETAIL_N and "취소 수주 1건 뺌" in (xrow["확인"] or ""),
      xrow and (xrow.get("수주 수"), xrow.get("확인")))
check("고객 칸 = 수주 고객 4곳 전부", xrow and all(cn in (xrow["고객사"] or "") for cn in CUSTS), xrow and xrow.get("고객사"))
check("발주일 칸 = 수주 발주일 범위", xrow and xrow["발주일"] == "2026-01-10 ~ 2026-07-01", xrow and xrow.get("발주일"))
# 환율이 없으면 원 칸을 비우고 알림(반쪽 숫자 금지)
with D.db_session() as c:
    c.execute("UPDATE exchange_rates SET rate_date=substr(rate_date,1,8)||'02'")   # 1일 행이 없으면 월 기준환율 없음
r2 = cl.get("/projects/export.xlsx")
ws2 = load_workbook(io.BytesIO(r2.content)).active
xr2 = None
for rr in ws2.iter_rows(values_only=True):
    if rr and rr[0] == "901T2601":
        xr2 = dict(zip(hdr, rr))
check("환율 없음 → 원 칸 비움 + 「환율 없음」 알림", xr2 and xr2["수주액(원)"] in (None, "") and "환율 없음" in (xr2["확인"] or ""), xr2)
with D.db_session() as c:
    c.execute("UPDATE exchange_rates SET rate_date=substr(rate_date,1,8)||'01'")

# ─────────────────────────────────────────
print("§5 수주 목록 /sales/orders")
st, H = get("/sales/orders")
check("수주 목록 열림", st == 200, st)


def so_row(html, no):
    i = html.find(no)
    if i < 0:
        return ""
    j = html.rfind("<tr", 0, i)
    k = html.find("</tr>", i)
    return html[j:k]


r_o2 = text(so_row(H, "T-260305-1"))
r_o4 = text(so_row(H, "T-260701-1"))
check("SAMSUNG INDIA 수주 줄 = 그 수주 모델·PO유형(INDIA-MODEL · 추가)", "INDIA-MODEL" in r_o2 and "추가" in r_o2 and "FIRST-MODEL" not in r_o2, r_o2[:300])
check("모델 안 적힌 수주(O4) = 관리번호 모델(FIRST-MODEL)로 채우지 않음 · PO유형 개조", "FIRST-MODEL" not in r_o4 and "개조" in r_o4, r_o4[:300])
check("수주 줄 고객 = 그 수주 1차 고객(시스템명 우선)", "SAMSUNG INDIA" in r_o2 and "PT Samsung Electronics Indonesia" in r_o4 and "삼성전자" not in r_o2, (r_o2[:200], r_o4[:200]))

# ─────────────────────────────────────────
print("§6 견적서·발주서 자리 찾기")
for api in ("/api/quotes-z105/search", "/api/customer-po/search"):
    j = cl.get(api + "?q=KNK VINA").json()
    items = j.get("items") or []
    head = [x for x in items if x.get("head") and x["pid"] == P]
    slots = [x for x in items if not x.get("head") and x["pid"] == P]
    check("%s 「KNK VINA」(수주 고객) → 관리번호 찾힘" % api, bool(head), items[:3])
    check("%s 머리 줄 고객 = 「삼성전자 외 3곳」" % api, head and "삼성전자 외 3곳" in head[0]["label"], head and head[0]["label"])
    check("%s 수주 자리 4개 = 상세 수주 수 · 줄마다 그 수주 고객" % api,
          len(slots) == DETAIL_N and all(any(cn in x["label"] for cn in CUSTS) for x in slots), [x["label"] for x in slots])
    j = cl.get(api + "?q=취소된고객").json()
    check("%s 취소 수주 고객으로는 안 찾힘" % api, not [x for x in (j.get("items") or []) if x["pid"] == P], j)

# ─────────────────────────────────────────
print("§7 관리번호대장")
st, H = get("/projects/ledger")
i = H.find("901T2601")
lrow = H[i:i + 4000] if i >= 0 else ""
check("대장 고객 칸 = 「삼성전자 외 3곳」(마우스 = 4곳 전부)", st == 200 and "삼성전자 외 3곳" in lrow and "PT Samsung Electronics Indonesia" in lrow, text(lrow)[:300])
st, H = get("/projects/ledger?q=Indonesia")
check("대장 찾기 = 수주 고객으로도 찾힘", st == 200 and "901T2601" in H, st)
r = cl.get("/projects/ledger/excel")
wsl = load_workbook(io.BytesIO(r.content)).active
lx = None
lh = None
for rr in wsl.iter_rows(values_only=True):
    if rr and "관리번호" in rr:
        lh = list(rr)
    elif lh and rr and "901T2601" in rr:
        lx = dict(zip(lh, rr))
check("대장 엑셀 고객 칸 = 수주 고객 4곳 전부 · 수주 수 4", lx and all(cn in (lx["고객사"] or "") for cn in CUSTS) and lx["수주 수"] == DETAIL_N, lx)

# ─────────────────────────────────────────
print("§8 수출")
st, H = get("/export/prep")
check("통관 목록 = 관리번호 「내수」여도 수출 품목 있으면 대상", st == 200 and "901T2601" in H, st)
check("내수 품목만 있는 관리번호는 대상 아님", "902T2601" not in H)
i = H.find("901T2601")
prow = text(H[i:i + 3000])
check("통관 목록 고객 = 「삼성전자 외 3곳」 · 납기 = 수주 납기 범위", "삼성전자 외 3곳" in prow and "2026-02-28 ~ 2026-08-31" in prow, prow[:300])
st, H = get("/export/prep/%d" % P)
ht = text(H)
check("통관 입력 머리 = 고객 「외 3곳」 · 모델 수주 값 · 취소 수주 1건 숨김 · 납기 범위",
      st == 200 and "삼성전자 외 3곳" in ht and "INDIA-MODEL 외 1건" in ht and "취소 수주 1건 숨김" in ht and "2026-02-28 ~ 2026-08-31" in ht, ht[:600])
with D.db_session() as c:
    p_, pl, pl_lines = M._export_pl_build(c, P)
    p_, ci, ci_lines = M._export_ci_build(c, P)
    dm = M._doc_meta_get(c, P, p_)
BUY = "삼성전자(주) / SAMSUNG INDIA ELECTRONICS PVT. LTD. / KNK VINA CO LTD / PT Samsung Electronics Indonesia"
check("PL 구매자 = 수주별 정식명 전부(처음 등록 고객만이 아님)", pl["buyer"] == BUY, pl["buyer"])
check("PL 발주일·납기 = 수주 값", pl["order_date"] == "2026-01-10 ~ 2026-07-01" and pl["due_date"] == "2026-02-28 ~ 2026-08-31", (pl["order_date"], pl["due_date"]))
check("PL 품목 줄 = 살아 있는 수주 4줄(취소 수주 품목 뺌) · 상세 수주 수와 같음", len(pl_lines) == DETAIL_N, len(pl_lines))
check("CI 구매자 = 수주별 전부 · 알림에 「취소된 수주 1건」", ci["buyer"] == BUY and any("취소된 수주 1건" in w for w in ci["ci_warn155"]), (ci["buyer"], ci["ci_warn155"]))
check("CI 금액 = 살아 있는 수주 품목 합(취소 99,999 안 섞임)", round(ci["total_amount"], 2) == round(100000000 + 50000 + 30000 + 20000000, 2), ci["total_amount"])
check("신고 서류 받는 곳(consignee) 기본값 = 수주 고객(처음 등록 고객 아님)", dm["consignee"] == BUY, dm["consignee"])
st, H = get("/export/prep/%d/packing-list" % P)
check("PL 인쇄 화면 = 구매자 수주별 · 취소 알림(인쇄 안 됨 칸)", st == 200 and "SAMSUNG INDIA ELECTRONICS" in H and "취소된 수주 1건" in H, st)
st, H = get("/export/prep/%d/invoice" % P)
check("CI 인쇄 화면 열림 · 구매자 수주별", st == 200 and "KNK VINA CO LTD" in H, st)
st, H = get("/export/ship/%d" % P)
check("출고 보기 머리 = 고객 「외 3곳」 · 통화 KRW·USD · 취소 숨김", st == 200 and "삼성전자 외 3곳" in text(H) and "KRW · USD" in text(H) and "취소 수주 1건 숨김" in text(H), text(H)[:400])
st, H = get("/export/ship/%d/qr/print" % P)
check("QR 라벨 고객 = 「삼성전자 외 3곳」", st == 200 and "삼성전자 외 3곳" in text(H), st)

# ─────────────────────────────────────────
print("§9 제작요청서")
with D.db_session() as c:
    _have = {r[1] for r in c.execute("PRAGMA table_info(prod_requests)")}
    for _col in ("recipients", "wt_team_ids", "user_ids", "updated_at", "updated_by_name", "dept_names", "sent_to", "dept_count",
                 "msg_sent", "created_date", "issued_by_name", "cust_req", "note", "mgmt_code", "issued_by", "team_ids", "order_ids"):
        if _col not in _have:
            c.execute("ALTER TABLE prod_requests ADD COLUMN %s TEXT" % _col)
    PR = ins(c, "prod_requests", {"project_id": P, "mgmt_code": "901T2601", "cust_req": "인도·베트남 추가분", "created_at": "2026-05-21 10:00",
                                  "created_date": "2026-05-21", "issued_by_name": "가상대표", "order_ids": "%d,%d" % (O2, O3)})
st, H = get("/project/%d/prod-request/edit?prid=%d" % (P, PR))
ht = text(H)
check("제작요청서 열림", st == 200, st)
check("종이·카드 고객 = 고른 수주(인도·베트남) 정식명 「SAMSUNG INDIA ELECTRONICS PVT. LTD. 외 1곳」 · 처음 등록 고객(삼성전자) 아님",
      ht.count("SAMSUNG INDIA ELECTRONICS PVT. LTD. 외 1곳") >= 2 and "삼성전자(주)" not in re.sub(r'<input[^>]*>', '', H), ht.count("SAMSUNG INDIA ELECTRONICS PVT. LTD. 외 1곳"))
check("발주일 = 고른 수주 발주일 범위", "2026-03-05 ~ 2026-05-20" in ht, None)
check("MODEL = 고른 수주 모델(INDIA-MODEL 외 1건)", "INDIA-MODEL 외 1건" in ht, None)
check("거래구분 = 고른 수주 품목(수출)", "🚢 수출" in ht, None)
st, H = get("/prod-requests")
i = H.find("901T2601")
crd = text(H[i:i + 3000]) if i >= 0 else ""
check("제작요청서 목록 카드 고객 = 고른 수주 「SAMSUNG INDIA 외 1곳」 · PO유형 추가", st == 200 and "SAMSUNG INDIA 외 1곳" in crd and "추가" in crd, crd[:300])
st, H = get("/prod-requests?q=KNK VINA")
check("제작요청서 목록 찾기 = 수주 고객으로 찾힘", st == 200 and "901T2601" in H, st)
CARDS.clear()
with contextlib.redirect_stdout(io.StringIO()):
    res = M._prod_request_notify_core(P, cust_req="시험", note="", team_ids=[TEAM], user=ADMIN, record=False, is_update=True, prid=PR)
cd = (CARDS[-1]["card"] if CARDS else {}) or {}
bd = CARDS[-1]["body"] if CARDS else ""
check("이음 카드 고객·PO유형 = 고른 수주(정식명 「… 외 1곳」 · 추가)", cd.get("customer") == "SAMSUNG INDIA ELECTRONICS PVT. LTD. 외 1곳" and cd.get("po_type") == "추가", (res, cd.get("customer"), cd.get("po_type")))
check("알림 글 고객 = 고른 수주 · 모델 = 고른 수주 모델", "SAMSUNG INDIA ELECTRONICS PVT. LTD. 외 1곳" in bd and "INDIA-MODEL" in bd and "FIRST-MODEL" not in bd, bd[:300])

# ─────────────────────────────────────────
print("§10 엑셀 일괄 등록 — 추가 발주 고객사")
with D.db_session() as c:
    n_before = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P,)).fetchone()[0]
base = {"mgmt_code_input": "901T2601", "biz_div": "T", "name": "가상 기능검사기", "model_name": "ADD-MODEL", "unit_qty": 1, "unit_price": 1000,
        "amount": 1000, "currency": "KRW", "order_date": "2026-09-01", "due_date": "2026-10-01", "po_type": "추가", "form_type": "완제품",
        "shipment_form": "ASSEMBLY", "status": "진행중", "_followup": True, "_errors": [], "is_export": "내수"}
rows = [dict(base, row_no=5, customer_name="", note="빈칸 줄"),
        dict(base, row_no=6, customer_name="드림텍", note="후보 여럿 줄", order_date="2026-09-02"),
        dict(base, row_no=7, customer_name="SAMSUNG INDIA", note="정상 줄", order_date="2026-09-03")]
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/projects/import-confirm", json={"rows": rows})
jj = r.json()
fl = jj.get("failed") or []
f5 = [x for x in fl if x.get("row_no") == 5]
f6 = [x for x in fl if x.get("row_no") == 6]
check("빈칸 줄 = 「확인 필요 — 고객사를 정해 주세요」로 돌려보냄", f5 and "확인 필요 — 고객사를 정해 주세요" in f5[0]["error"], fl)
check("이름 후보 여럿 줄 = 「확인 필요」로 돌려보냄", f6 and "확인 필요" in f6[0]["error"] and "드림텍" in f6[0]["error"], fl)
with D.db_session() as c:
    new = [dict(x) for x in c.execute("SELECT o.order_date, o.customer_id FROM orders o WHERE project_id=? AND order_date>='2026-09-01'", (P,))]
check("돌려보낸 줄은 저장 안 됨 · 정상 줄(SAMSUNG INDIA)만 저장 · 관리번호 처음 고객(삼성전자) 저장 0",
      [x["order_date"][:10] for x in new] == ["2026-09-03"] and new[0]["customer_id"] == CU2 and not any(x["customer_id"] == CU1 for x in new), new)
# 미리보기 단계에서도 빈칸 추가 발주는 오류로 보임 — 실제 양식(/projects/import-template)에 줄을 적어 파서에 넣는다
from openpyxl import load_workbook as _lw                    # noqa: E402
_t = cl.get("/projects/import-template")
_wb = _lw(io.BytesIO(_t.content))
_ws = next((w for w in _wb.worksheets if w.title.startswith("T_")), _wb.worksheets[0])
_hr, _hm = None, {}
for _ri in range(1, 8):
    _vals = [str(_ws.cell(_ri, _ci).value or "").strip() for _ci in range(1, _ws.max_column + 1)]
    if "관리코드" in " ".join(_vals) and ("고객사" in " ".join(_vals)):
        _hr = _ri
        _hm = {v: i + 1 for i, v in enumerate(_vals) if v}
        break
_prev = None
if _hr:
    for _rr in range(_hr + 1, _ws.max_row + 1):
        for _ci in range(1, _ws.max_column + 1):
            _ws.cell(_rr, _ci).value = None

    def _put(_r, **kw):
        for k, v in kw.items():
            for h, ci in _hm.items():
                if h.replace(" ", "").startswith(k):
                    _ws.cell(_r, ci).value = v
                    break
    _put(_hr + 2, 프로젝트명="가상 기능검사기", 관리코드="901T2601", PO유형="추가", 고객사="", 모델="ADD-MODEL", 거래구분="내수",
         발주일="2026-09-05", 납기="2026-10-05", 단가=1000, 수량=1, 통화="KRW", 상태="진행중")
    _b = io.BytesIO()
    _wb.save(_b)
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            _prev = M._proj_import_parse_xlsx(_b.getvalue())
        except Exception as _e:
            _prev = "오류: %s" % _e
_r5 = [x for x in (_prev or []) if isinstance(x, dict) and x.get("_followup")] if isinstance(_prev, list) else []
check("미리보기: 고객사 빈 추가 발주 줄 = 오류 「확인 필요 — 고객사를 정해 주세요」(등록 불가)",
      _r5 and any("확인 필요 — 고객사를 정해 주세요" in e for e in _r5[0]["_errors"]) and not _r5[0]["_is_warning_only"],
      (_hr, list(_hm)[:12], _prev if not isinstance(_prev, list) else [(x.get("_followup"), x.get("customer_name"), x.get("_errors")) for x in _prev]))

# ─────────────────────────────────────────
print("§11 다른 관리번호는 그대로(고객 1곳 · 외 N곳 없음)")
st, H = get("/projects")
i = H.find("902T2601")
check("고객 1곳 관리번호 = 「삼성전자」만(외 N곳 없음)", i >= 0 and "외" not in text(H[i:i + 1500]).split("가상 다른 장비")[1][:40], text(H[i:i + 600])[:200])

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
