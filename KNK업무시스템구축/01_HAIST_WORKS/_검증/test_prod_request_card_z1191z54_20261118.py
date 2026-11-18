# -*- coding: utf-8 -*-
"""z1191z54 시험 (2차 2-5 · 이음 v966 회신에 맞춘 웍스 카드)
  ① 카드에 요지(gist · 120자) ② 바뀐 줄 7줄 안(6 + 「… 외 N줄」) ③ 취소 카드(cancelled=true · 사유 · 누가 · 언제 · 상태 「취소」 · 같은 prid) + 글 그대로
  임시 DB · TestClient · 이음 보내기는 가짜 · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
from datetime import date, timedelta
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z54-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z54_")
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


FUT = (date.today() + timedelta(days=14)).isoformat()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    TEAM = ins(c, "teams", {"name": "가상검사기팀", "code": "T49", "entity": "KOR", "display_order": 1})
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T950', 'T950', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T950'").fetchone())
    for i in (1, 2):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id) VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', 1, 1, ?)",
                  ("가상받는이%d" % i, "T95%d" % i, "T95%d" % i, TEAM))
    CU = ins(c, "customers", {"name": "한국가상전(주)", "alias": "가상전"})
    CU2 = ins(c, "customers", {"name": "다른고객(주)", "alias": "다른"})

    def proj(code, cust=CU, **kw):
        row = {"code": code, "name": "PBA", "mgmt_code": code, "customer_id": cust, "customer_name": ("한국가상전(주)" if cust == CU else "다른고객(주)"), "currency": "KRW",
               "status": "수주확정", "biz_div": "T", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "order_date": "2026-11-13", "due_date": FUT, "is_archived": 0,
               "unit_qty": 1, "model_name": "VPL-" + code[:3], "equip_name": "가상 검사기 " + code[:3], "cc_name": "정가상", "cc_position": "계장", "engraving": "ENG-" + code[:3]}
        row.update(kw)
        return ins(c, "projects", row)

    def order(pid, no, po, label, created, status="CONFIRMED"):
        return ins(c, "orders", {"order_no": no, "customer_id": CU, "order_date": created[:10], "due_date": FUT, "total_amount": 1000, "status": status,
                                 "created_at": created, "project_id": pid, "unit_label": label, "unit_qty": 1, "currency": "KRW", "so_type": "EQUIPMENT", "po_type": po})
    A = proj("020T2611", server_path="Z:\\가상전\\TSP\\VPL\\9. 제품자료"); OA = order(A, "T-261113-5", "신규", "1호기", "2026-11-16 09:47:00")
    B = proj("021T2611"); OB = order(B, "T-261113-6", "신규", "1호기", "2026-11-16 09:48:00")
    Cc = proj("022T2611", engraving=""); OC = order(Cc, "T-261113-7", "신규", "1호기", "2026-11-16 09:49:00")
    Dd = proj("023T2611"); OD1 = order(Dd, "T-261113-8", "신규", "1호기", "2026-11-16 09:50:00"); OD2 = order(Dd, "T-261117-3", "추가", "2호기", "2026-11-17 09:00:00")
    E = proj("010T2609", order_date="2026-09-01"); OE = order(E, "T-260901-1", "신규", "1호기", "2026-09-01 10:00:00")       # 같은 고객사 · 다른 날
    F = proj("030T2611")                                                                                                # 같은 날 · 수주 없음 → 못 묶음
    G = proj("031T2611", cust=CU2); OG = order(G, "T-261113-9", "신규", "1호기", "2026-11-16 10:00:00")                    # 다른 고객사 → 못 묶음
    H = proj("032T2611", is_archived=1); OH = order(H, "T-261113-10", "신규", "1호기", "2026-11-16 10:00:00")              # 폐기 → 못 묶음
    S1 = proj("040T2611", order_date="2026-11-14"); OS1 = order(S1, "T-261114-1", "신규", "1호기", "2026-11-16 11:00:00")  # 따로 발행할 것

import app.main as M  # noqa: E402
import app.sso_client as SSO  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
CARDS = []
SSO.notify_via_messenger = lambda emp_nos, title, body, link, card=None, **k: (CARDS.append({"emp": list(emp_nos or []), "title": title, "body": body, "card": card}) or {"ok": True, "sent": len(emp_nos or [])})
with D.db_session() as c:
    _have = {r[1] for r in c.execute("PRAGMA table_info(prod_requests)")}
    for _col in ("recipients", "wt_team_ids", "user_ids", "updated_at", "updated_by_name", "dept_names", "sent_to", "dept_count",
                 "msg_sent", "created_date", "issued_by_name", "cust_req", "note", "mgmt_code", "issued_by", "team_ids"):
        if _col not in _have:
            c.execute("ALTER TABLE prod_requests ADD COLUMN %s TEXT" % _col)
    ins(c, "prod_requests", {"project_id": E, "mgmt_code": "010T2609", "cust_req": "예전 요청", "created_at": "2026-09-01 11:00", "created_date": "2026-09-01", "issued_by_name": "가상관리자"})
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


def view(h):
    m = re.search(r'<div id="prqView">(.*?)<div class="z48-mob">', h, re.S)
    return m.group(1) if m else ""


def rows(h):
    """품목 줄들: [[No, 관리코드, 수주번호, 호기, 모델명, 품명, 수량, 일정], …] + 노란 칠 줄 번호"""
    out, me = [], []
    for m in re.finditer(r'<tr( class="[^"]*")?><td>(\d+)</td>(.*?)</tr>', view(h), re.S):
        cells = [re.sub(r"<[^>]+>", " ", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", m.group(3), re.S)]
        if len(cells) == 7:
            out.append([m.group(2)] + cells)
            if m.group(1) and "z49-me" in m.group(1):
                me.append(m.group(2))
    return out, me


def prq(where="1=1", args=()):
    with D.db_session() as c:
        return [tuple(r) for r in c.execute("SELECT id, project_id, COALESCE(bundle_id,0), COALESCE(order_ids,''), COALESCE(cust_req,''), COALESCE(gist,''), COALESCE(bundle_model,'') "
                                            "FROM prod_requests WHERE " + where + " ORDER BY id", args)]


def notif_n():
    with D.db_session() as c:
        return c.execute("SELECT COUNT(*) FROM notifications WHERE kind='prod_request'").fetchone()[0]


base = {"full_edit": "", "server_path": "Z:\\가상전\\TSP\\VPL\\9. 제품자료", "model_name": "", "engraving": ""}

print("§1 요지 · 바뀐 줄 7줄 안")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % S1, data=dict(base, cust_req="\n".join("%d. 줄 %d" % (i, i) for i in range(1, 11)), note="# 메모1\n# 메모2", gist="요지 " + "가" * 150,
                                                             order_ids=[str(OS1)], add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % S1))
P1 = int(re.search(r"prid=(\d+)", r.headers["location"]).group(1))
k = CARDS[0]["card"] if CARDS else {}
check(k.get("gist", "").startswith("요지 가") and len(k["gist"]) == 120, "새 발행 카드에 요지(gist · 120자까지)", len(k.get("gist", "")))
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (S1, P1),
      data=dict(base, rev_reason="사양 변경", cust_req="\n".join("%d. 바뀐 줄 %d" % (i, i) for i in range(1, 11)), note="# 메모1\n# 메모2 바뀜", gist="요지 짧게",
                order_ids=[str(OS1)], _back="/project/%d/prod-request/edit?prid=%d" % (S1, P1)))
k = CARDS[0]["card"] if CARDS else {}
cl7 = k.get("changed_lines") or []
check(len(cl7) == 7 and cl7[-1].startswith("… 외 ") and cl7[-1].endswith("줄") and k.get("gist") == "요지 짧게" and k.get("revision_reason") == "사양 변경",
      "수정발행 카드: 바뀐 줄은 요청사항·기타 합쳐 7줄(6 + 「… 외 N줄」) · 요지 · 사유", cl7)
b = CARDS[0]["body"] if CARDS else ""
check(b.count("\n   ") == 7 and "… 외 " in b, "알림 글의 바뀐 줄도 같은 7줄", b[:300])

print("§2 취소 카드")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/cancel" % (S1, P1), data={"cancel_reason": "중복 발행"})
k = CARDS[0]["card"] if CARDS else None
check(k and k.get("cancelled") is True and k.get("cancel_reason") == "중복 발행" and k.get("cancelled_by") == "가상관리자" and k.get("cancelled_at") and k.get("status") == "취소"
      and k.get("is_revision") is False and k.get("prid") == P1 and k.get("issue_token"), "취소 카드: cancelled=true · 사유 · 누가 · 언제 · 상태 「취소」 · 같은 prid · 새 발행 토큰",
      {x: (k or {}).get(x) for x in ("cancelled", "cancel_reason", "cancelled_by", "status", "is_revision", "prid")})
check(CARDS and CARDS[0]["title"].startswith("🚫 제작요청 취소 [040T2611]") and "■ 취소 사유 : 중복 발행" in CARDS[0]["body"], "제목·본문 글(「🚫 제작요청 취소 … 사유」)도 그대로(휴대폰 알림·방 목록)")
check(len(CARDS) == 2 and CARDS[1]["card"] and CARDS[1]["card"].get("cancelled") is True, "취소한 사람 확인 알림에도 취소 카드")
check("revision_reason" not in (k or {}) and "changed_lines" not in (k or {}), "취소 카드에는 수정 사유·바뀐 줄 칸 없음")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
