# -*- coding: utf-8 -*-
"""z1191z178 시험 — 통화·거래구분 안 맞음 알림(대표 11-27 「023T2602 T-260616-6 은 USD 수주인데 22·23호기가 『내수』 · 이런 맞지 않는 상황이 나오면 알람」)

임시 DB(실제 운영 DB 아님) · TestClient. 실제와 같은 모양:
  관리번호 903T2602 — 수주 OU(USD · 21호기 수출 · 22·23호기 내수 · 24호기 내수인데 취소 · 25호기 미기재)
                     수주 OK(KRW · 1건 수출) · 수주 OC(USD 취소 · 내수) · 수주 ON(USD · 미기재) · 수주 OG(KRW · 내수)
  §1 판정 한 곳(trade_ccy_mismatch) — USD+내수 2줄(22·23호기) · KRW+수출 · 취소·미기재 제외
  §2 화면 — 프로젝트 상세 수주 카드 · 수주 상세 · 확인 필요 화면(개수 포함) · 수출 서류 고르기 · 통관 입력 상세
  §3 「확인했음」 — 지문 다르면 저장 안 함 · 맞으면 회색 「✓ 확인함(이름 날짜)」 · 개수 줄어듦 · 이력 두 곳
  §4 내용이 바뀌면(내수 줄 하나 더) 다시 알림 — 저장 응답 warn · 저장은 그대로
  §5 다른 저장 길 — 수주 카드 통화(quick-edit) · 작업일정표 한 칸(trade) · 확인 필요 거래구분 · 상세 품목 줄 고치기 · 값 저절로 안 바뀜
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z178-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z178_")
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
              "can_view_logistics, can_use_logistics) VALUES ('가상대표', 'ceo', 'Z178', 'Z178', 'sso_only_no_local_password', 1, 1, ?, 1, 1, 1, 1)", (TEAM,))
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='Z178'").fetchone())
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales) "
              "VALUES ('가상보기', 'staff', 'Z178V', 'Z178V', 'sso_only_no_local_password', 1, 1, ?, 1, 0)", (TEAM,))
    VIEWER = dict(c.execute("SELECT * FROM users WHERE employee_no='Z178V'").fetchone())
    c.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', ?)", (TEAM,))
    CU1 = ins(c, "customers", {"name": "SAMSUNG INDIA ELECTRONICS PVT. LTD.", "alias": "SAMSUNG INDIA"})
    CU2 = ins(c, "customers", {"name": "삼성전자(주)", "alias": "삼성전자"})
    P = ins(c, "projects", {"code": "903T2602", "mgmt_code": "903T2602", "name": "가상 검사기", "customer_id": CU1, "customer_name": "SAMSUNG INDIA ELECTRONICS PVT. LTD.",
                            "po_type": "신규", "is_export": 1, "currency": "USD", "order_amount": 100000, "order_date": "2026-02-10",
                            "due_date": "2026-06-16", "status": "진행중", "stage": "수주확정", "biz_div": "T", "project_type": "NEW_EQUIP",
                            "shipment_form": "ASSEMBLY", "model_name": "M1", "equip_name": "가상 검사기", "unit_qty": 5, "is_archived": 0,
                            "sales_name": "가상대표"})

    def so(no, cu, ccy, st, od, lines):
        oid = ins(c, "orders", {"project_id": P, "order_no": no, "customer_id": cu, "currency": ccy, "total_amount": 1000 * len(lines),
                                "order_date": od, "due_date": "2026-06-16", "status": st, "po_type": "신규", "end_customer": "",
                                "unit_qty": len(lines), "so_type": "EQUIPMENT", "created_at": od + " 09:00:00"})
        ids = []
        for lb, iex, ust in lines:
            ids.append(ins(c, "order_items", {"order_id": oid, "qty": 1, "unit_price": 1000, "amount": 1000, "unit_label": lb, "is_export": iex,
                                              "currency": ccy, "unit_status": ust}))
        return oid, ids
    OU, IU = so("T-260616-6", CU1, "USD", "CONFIRMED", "2026-02-10",
                [("21호기", 1, "진행중"), ("22호기", 0, "진행중"), ("23호기", 0, "진행중"), ("24호기", 0, "취소"), ("25호기", None, "진행중")])
    OK, IK = so("T-260701-1", CU2, "KRW", "CONFIRMED", "2026-03-01", [("1건", 1, "진행중")])
    OC, IC = so("T-260702-9", CU1, "USD", "CANCELLED", "2026-03-02", [("31호기", 0, "진행중")])
    ON, IN = so("T-260703-1", CU1, "USD", "CONFIRMED", "2026-03-03", [("41호기", None, "진행중")])
    OG, IG = so("T-260704-1", CU2, "KRW", "CONFIRMED", "2026-03-04", [("51호기", 0, "진행중")])
    OK2, IK2 = so("T-260705-1", CU2, "KRW", "CONFIRMED", "2026-03-05", [("61호기", 0, "진행중")])

import app.main as M                                        # noqa: E402
import app.project_workflow as PW                           # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

_WHO = {"u": ADMIN}
M.get_user = lambda request: _WHO["u"]
M._can_manual_mgmt = lambda u: True
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
cl = TestClient(M.app)
OKN = FAIL = 0


def check(label, cond, got=None):
    global OKN, FAIL
    if cond:
        OKN += 1
        print("  ✅", label)
    else:
        FAIL += 1
        print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:700])


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or ""))


def mm():
    with D.db_session() as c:
        return {w["order_id"]: w for w in PW.trade_ccy_mismatch(c)}


def iex(iid):
    with D.db_session() as c:
        return c.execute("SELECT is_export FROM order_items WHERE id=?", (iid,)).fetchone()[0]


# ─────────────────────────────────────────
print("§1 판정 한 곳")
W = mm()
check("걸린 수주 = USD 수주(OU) + KRW 수출(OK) 두 건만", sorted(W) == sorted([OU, OK]), sorted(W))
wu = W.get(OU) or {}
check("OU = 외화+내수 · 22호기·23호기 2줄(취소된 24호기·미기재 25호기·수출 21호기 빠짐)",
      wu.get("kind") == "fx_dom" and wu.get("items") == ["22호기", "23호기"] and wu.get("n") == 2, wu)
check("OU 글 = 「💱 외화(USD) 수주인데 내수 품목 2줄」", wu.get("msg") == "💱 외화(USD) 수주인데 내수 품목 2줄", wu.get("msg"))
check("OK = 원화+수출 1줄", (W.get(OK) or {}).get("kind") == "krw_exp" and (W.get(OK) or {}).get("msg") == "💱 원화(KRW) 수주인데 수출 품목 1줄", W.get(OK))
check("취소 수주(OC)·미기재(ON)·맞는 수주(OG) 제외", OC not in W and ON not in W and OG not in W)
check("아직 확인 안 함", not wu.get("acked") and wu.get("ack") is None)
with D.db_session() as c:
    check("order_ids 로 고르면 그 수주만", [w["order_id"] for w in PW.trade_ccy_mismatch(c, order_ids=[OK])] == [OK])
    check("값은 하나도 안 바뀜(읽기만)", c.execute("SELECT COUNT(*) FROM order_items WHERE is_export=0").fetchone()[0] == 6)

# ─────────────────────────────────────────
print("§2 화면")
r = cl.get("/project/%d" % P)
H = r.text
check("프로젝트 상세 200", r.status_code == 200, r.status_code)
check("상세: 수주 카드에 노란 알림 + 호기 이름 + 「확인했음」",
      'data-tcw-oid="%d"' % OU in H and "외화(USD) 수주인데 내수 품목 2줄" in H and "22호기 · 23호기" in H and "tcw-ack" in H, text(H)[:300])
check("상세: 위쪽 요약 「통화·거래구분이 안 맞는 수주 2건」", "통화·거래구분이 안 맞는 수주 2건" in text(H))
check("상세: KRW 수출 수주(OK)도 알림", 'data-tcw-oid="%d"' % OK in H)
check("상세: 맞는 수주(OG)·미기재(ON)는 알림 없음", 'data-tcw-oid="%d"' % OG not in H and 'data-tcw-oid="%d"' % ON not in H)
r = cl.get("/sales/orders/%d" % OU)
check("수주 상세 OU: 알림 + 22호기·23호기", r.status_code == 200 and "외화(USD) 수주인데 내수 품목 2줄" in r.text and "22호기 · 23호기" in r.text, r.status_code)
r = cl.get("/sales/orders/%d" % OG)
check("수주 상세 OG(맞음): 알림 없음", r.status_code == 200 and not re.search(r'data-tcw-oid="\d+"', r.text), re.findall(r'data-tcw-oid="\d+"', r.text))
r = cl.get("/projects/so-check")
T = text(r.text)
check("확인 필요 화면: 새 묶음 「통화·거래구분 안 맞음 2건」", r.status_code == 200 and "통화·거래구분 안 맞음 2건" in T and "T-260616-6" in r.text, T[:400])
with D.db_session() as c:
    N0 = M._z154_check_count(c)
    base = len(M._z154_check_rows(c)) + len(M._z156_noso_files(c))
check("확인 필요 개수(메뉴·배지) = 수주 칸 + 파일 + 통화·거래구분 2", N0 == base + 2, (N0, base))
for url, nm in (("/export/prep/%d" % P, "통관 입력 상세"), ("/export/prep/%d/packing-list" % P, "수출 서류 고르기(수출 수주 2건)")):
    r = cl.get(url)
    check("%s %s: 수주 줄에 알림(22호기 · 23호기)" % (nm, url), r.status_code == 200 and 'data-tcw-oid="%d"' % OU in r.text and "22호기 · 23호기" in r.text,
          (r.status_code, re.findall(r'data-tcw-oid="\d+"', r.text)))
# 수출 서류 고르기 · 통관 입력 상세 틀을 직접 그려 확인(주소 모양과 무관하게)
with D.db_session() as c:
    _ords = [{"id": OU, "order_no": "T-260616-6", "customer_id": CU1, "cust": "SAMSUNG INDIA", "currency": "USD", "total_amount": 5000,
              "n_items": 5, "order_date": "2026-02-10", "due_date": "2026-06-16", "trade": "수출·내수", "why": "", "doc": True}]
for tn in ("export_doc_pick.html",):
    try:
        src = M.tpl.env.get_template(tn)
        html = src.render(request=None, user=ADMIN, p={"id": P, "mgmt_code": "903T2602"}, L={"orders": _ords, "doc": _ords}, can_money=True,
                          money=lambda a, c=None: str(a), want="", ct=lambda k: "")
        check("%s: 수주 줄에 알림" % tn, 'data-tcw-oid="%d"' % OU in html and "22호기 · 23호기" in html)
    except Exception as _e:
        src = open(os.path.join(ROOT, "app", "templates", tn), encoding="utf-8").read()
        check("%s: 알림 틀 들어 있음(직접 그리기 안 됨: %s)" % (tn, str(_e)[:60]), "trade_ccy_warn.html" in src and "trade_ccy_warn(p.id)" in src)
src = open(os.path.join(ROOT, "app", "templates", "export_prep_detail.html"), encoding="utf-8").read()
check("export_prep_detail.html: 수주 표 줄 + 품목 묶음 머리에 알림 틀", src.count("trade_ccy_warn.html") == 2)

# ─────────────────────────────────────────
print("§3 「확인했음」")
r = cl.post("/api/trade-ccy-ack/%d" % OU, data={"sig": "틀린지문"})
check("지문 다르면 저장 안 함(409 · 다시 불러오라고)", r.status_code == 409 and not r.json().get("ok") and "바뀌었습니다" in r.json().get("message", ""), r.text[:200])
_WHO["u"] = VIEWER
r = cl.post("/api/trade-ccy-ack/%d" % OU, data={"sig": wu["sig"]})
check("영업 등록 권한 없으면 403", r.status_code == 403, r.status_code)
_WHO["u"] = ADMIN
r = cl.post("/api/trade-ccy-ack/%d" % OU, data={"sig": wu["sig"]})
j = r.json()
check("맞는 지문 → ✅ 확인 저장 · 누가 남음", r.status_code == 200 and j.get("ok") and "가상대표" in (j.get("by_name") or ""), j)
W = mm()
check("판정: OU acked · 이름·날짜", W[OU]["acked"] and "가상대표" in W[OU]["ack"]["by_name"] and len(W[OU]["ack"]["at"]) >= 10, W[OU].get("ack"))
check("값은 그대로(22·23호기 내수 유지)", iex(IU[1]) == 0 and iex(IU[2]) == 0)
H = cl.get("/project/%d" % P).text
check("상세: 회색 「✓ 확인함(가상대표 …)」 · 요약은 1건으로", "✓ 확인함(가상대표" in H and "통화·거래구분이 안 맞는 수주 1건" in text(H), text(H)[:200])
T = text(cl.get("/projects/so-check").text)
check("확인 필요 화면: 1건으로 줄어듦(OU 빠짐)", "통화·거래구분 안 맞음 1건" in T and "T-260616-6" not in T.split("통화·거래구분 안 맞음 1건")[1][:600], T[:300])
with D.db_session() as c:
    check("확인 필요 개수 1 줄어듦", M._z154_check_count(c) == N0 - 1, (M._z154_check_count(c), N0))
    h1 = c.execute("SELECT note FROM order_status_history WHERE order_id=? AND note LIKE '%z1191z178%'", (OU,)).fetchall()
    h2 = c.execute("SELECT field, new_value, note FROM project_history WHERE project_id=? AND field='통화·거래구분 확인'", (P,)).fetchall()
check("수주 변경 이력 한 줄(22호기 · 23호기 · 이름)", len(h1) == 1 and "22호기 · 23호기" in h1[0][0] and "가상대표" in h1[0][0], h1)
check("프로젝트 이력 한 줄", len(h2) == 1 and h2[0][1] == "확인했음", h2)

# ─────────────────────────────────────────
print("§4 내용이 바뀌면 다시 알림 · 저장 응답 warn · 저장은 됨")
r = cl.post("/sales/schedule/unit-field", json={"iid": IU[0], "field": "is_export", "value": "0"})   # 21호기 수출 → 내수
j = r.json()
check("작업일정표 호기 줄 저장 ok", r.status_code == 200 and j.get("ok"), r.text[:200])
check("저장은 됨(21호기 = 내수)", iex(IU[0]) == 0)
wl = j.get("trade_ccy_warn") or []
check("응답에 warn(머리 X-KNK-Trade-Warn) · 내수 3줄 · 21·22·23호기",
      r.headers.get("X-KNK-Trade-Warn") == "1" and wl and wl[0]["order_id"] == OU and wl[0]["n"] == 3 and wl[0]["items_txt"] == "21호기 · 22호기 · 23호기", (r.headers.get("X-KNK-Trade-Warn"), wl))
W = mm()
check("내용이 바뀌어 확인 풀림(다시 노란색)", not W[OU]["acked"] and W[OU]["n"] == 3)
r = cl.post("/sales/schedule/unit-field", json={"iid": IU[0], "field": "note", "value": "메모"})
check("거래구분 아닌 칸 저장은 warn 없음", r.json().get("ok") and "trade_ccy_warn" not in r.json() and not r.headers.get("X-KNK-Trade-Warn"))
r = cl.post("/sales/schedule/unit-field", json={"iid": IU[0], "field": "is_export", "value": "1"})   # 되돌림 → 처음 확인한 내용과 같음
check("다시 수출로 되돌리면 처음 확인한 내용과 같아 알림 없음(확인 유지)", r.json().get("ok") and not r.json().get("trade_ccy_warn") and mm()[OU]["acked"], r.json())

# ─────────────────────────────────────────
print("§5 다른 저장 길")
r = cl.post("/sales/orders/%d/quick-edit" % OG, data={"currency": "USD"})   # KRW 내수 수주 → USD 로
j = r.json()
check("수주 카드 통화 저장 ok · 저장됨(USD)", r.status_code == 200 and j.get("ok"), r.text[:200])
with D.db_session() as c:
    check("수주 통화 = USD 로 저장 · 품목 거래구분은 그대로(내수)", c.execute("SELECT currency FROM orders WHERE id=?", (OG,)).fetchone()[0] == "USD" and iex(IG[0]) == 0)
check("응답 warn = 외화(USD) 내수 1줄(51호기)", (j.get("trade_ccy_warn") or [{}])[0].get("items_txt") == "51호기" and j["trade_ccy_warn"][0]["kind"] == "fx_dom", j.get("trade_ccy_warn"))
r = cl.post("/sales/schedule/cell", json={"kind": "project", "ref_id": P, "field": "trade", "value": "내수", "so_oid": ON})
j = r.json()
check("작업일정표 한 칸 거래구분(USD 수주 ON → 내수) 저장 ok", r.status_code == 200 and j.get("ok") and iex(IN[0]) == 0, r.text[:200])
check("응답 warn = ON 41호기", (j.get("trade_ccy_warn") or [{}])[0].get("order_id") == ON and j["trade_ccy_warn"][0]["items_txt"] == "41호기", j.get("trade_ccy_warn"))
r = cl.post("/sales/schedule/cell", json={"kind": "project", "ref_id": P, "field": "trade", "value": "수출", "so_oid": ON})
check("다시 수출로 고치면 warn 없음", r.json().get("ok") and not r.json().get("trade_ccy_warn") and ON not in mm(), r.json())
# 확인 필요 화면 거래구분 정하기(빈 줄) — 새 USD 수주 + 빈 품목 줄
with D.db_session() as c:
    OB = ins(c, "orders", {"project_id": P, "order_no": "T-260706-1", "customer_id": CU1, "currency": "USD", "total_amount": 1000,
                           "order_date": "2026-03-06", "status": "CONFIRMED", "po_type": "신규", "end_customer": ""})
    IB = ins(c, "order_items", {"order_id": OB, "qty": 1, "unit_price": 1000, "amount": 1000, "unit_label": "71호기", "is_export": None, "currency": "USD", "unit_status": "진행중"})
r = cl.post("/api/so-check/%d" % OB, data={"field": "is_export", "action": "set", "value": "내수"})
j = r.json()
check("확인 필요 화면 「내수로 확정」 저장 ok · 저장됨", r.status_code == 200 and j.get("ok") and iex(IB) == 0, r.text[:200])
check("응답 warn = 외화(USD) 수주인데 내수 1줄(71호기)", (j.get("trade_ccy_warn") or [{}])[0].get("items_txt") == "71호기", j.get("trade_ccy_warn"))
# 상세 품목 줄 고치기(KRW 수주 OK2 의 61호기 내수 → 수출)
r = cl.post("/sales/orders/items/%d/edit" % IK2[0], data={"label": "61호기", "amount": "1000", "is_export": "1"})
j = r.json()
check("상세 품목 줄 고치기 저장 ok · 저장됨(수출)", r.status_code == 200 and j.get("ok") and iex(IK2[0]) == 1, r.text[:200])
check("응답 warn = 원화(KRW) 수주인데 수출 1줄", (j.get("trade_ccy_warn") or [{}])[0].get("msg") == "💱 원화(KRW) 수주인데 수출 품목 1줄", j.get("trade_ccy_warn"))
# 작업일정표 일괄(trade)
r = cl.post("/sales/schedule/bulk-cell", json={"field": "trade", "value": "내수", "targets": [{"kind": "project", "ref_id": P, "so_oid": OK}]})
j = r.json()
check("작업일정표 일괄 거래구분(OK → 내수) 저장 ok · 원화+내수라 알림 없음", j.get("ok") and j.get("ok_count") == 1 and not j.get("trade_ccy_warn") and iex(IK[0]) == 0, j)
r = cl.post("/sales/schedule/bulk-cell", json={"field": "trade", "value": "내수", "targets": [{"kind": "project", "ref_id": P, "so_oid": ON}]})
j = r.json()
check("작업일정표 일괄 거래구분(USD 수주 ON → 내수) = warn", j.get("ok") and (j.get("trade_ccy_warn") or [{}])[0].get("order_id") == ON, j)

# ─────────────────────────────────────────
print("§6 공용 알림 JS · 등록 화면 즉시 알림")
kb = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "knk_busy.html"), encoding="utf-8").read()
check("공용 fetch 가 X-KNK-Trade-Warn 을 보고 노란 알림(닫기 · 확인 단추)", "X-KNK-Trade-Warn" in kb and "tcw-x" in kb and "tcw-ack" in kb and "/api/trade-ccy-ack/" in kb)
check("공용 틀(모든 쪽)에는 「확인했음」·「✕ 닫기」 글자가 그대로 안 실림(글자 번호로) — 다른 화면 글자 찾기에 안 섞임", "확인했음" not in kb and "✕ 닫기" not in kb)
qf = open(os.path.join(ROOT, "app", "templates", "project_quick_form.html"), encoding="utf-8").read()
check("등록·정보 수정 화면: 통화·거래구분 고르는 즉시 알림(막지 않음)", "qTcm178" in qf and "막지 않음" in qf)
r = cl.get("/projects/%d/quick-edit" % P)
check("정보 수정 화면 열림 · 알림 자리 있음", r.status_code == 200 and 'id="qTcm178"' in r.text, r.status_code)

print("\n결과: 통과 %d · 실패 %d" % (OKN, FAIL))
sys.exit(1 if FAIL else 0)
