# -*- coding: utf-8 -*-
"""z1191z51 시험 (대표 2026-11-17 「2차 진행해」 · 2-3 재발행)
  ① 수정 사유 · 바뀐 줄(알림 · 보기 · 이력)  ② 묶음에서 빼기 · 다시 붙이기  ③ 취소 발행(사유 필수 · 묶음 전체 · 글 알림 · 고치기 막음)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z51-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z51_")
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


import json  # noqa: E402
base = {"full_edit": "", "server_path": "Z:\\가상전\\TSP\\VPL\\9. 제품자료", "model_name": "", "engraving": ""}


def revs(lead):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT rev_no, kind, COALESCE(reason,'') AS reason, COALESCE(changes,'') AS changes, COALESCE(cust_req,'') AS cust_req "
                                           "FROM prod_request_revs WHERE prod_request_id=? ORDER BY rev_no", (lead,))]


def rowx(where, args=()):
    with D.db_session() as c:
        return [tuple(r) for r in c.execute("SELECT id, project_id, COALESCE(bundle_id,0), COALESCE(cancelled_at,''), COALESCE(cancel_kind,''), COALESCE(cancel_reason,'') "
                                            "FROM prod_requests WHERE " + where + " ORDER BY id", args)]


def edit_form(h):
    i = h.find('<form id="prqEditForm"')
    return h[i:h.find("</form>", i)] if i >= 0 else ""


print("§1 수정 사유 · 바뀐 줄")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % S1, data=dict(base, cust_req="1. 가상 검사기 040 : 1호기\n-. 케이스 포함\n2. 지그 : 1호기", note="# 마킹", gist="처음",
                                                             order_ids=[str(OS1)], add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % S1))
P1 = int(re.search(r"prid=(\d+)", r.headers["location"]).group(1))
h = q(cl.get, "/project/%d/prod-request/edit" % S1).text
ef = edit_form(h)
check('name="rev_reason"' in ef and ">수량 변경</button>" in ef and ">납기 변경</button>" in ef and ef.find('name="rev_reason"') < ef.find("🧾 수주번호"),
      "수정 폼 맨 위에 「수정 사유」 칸 + 눌러서 고르는 단추(수량 변경 · 납기 변경 …)")
check("🚫 취소 발행" in h and 'action="/project/%d/prod-request/%d/cancel"' % (S1, P1) in h and ">고객사 취소 요청</button>" in h, "보기 화면에 「🚫 취소 발행」 + 사유 단추")
check(not revs(P1), "발행만 하면 이력 없음(고칠 때 처음 글을 0번으로 남김)")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (S1, P1),
      data=dict(base, full_edit="1", unit_qty="2", rev_reason="수량 변경", cust_req="1. 가상 검사기 040 : 1~2호기\n-. 케이스 포함\n2. 지그 : 1호기", note="# 마킹",
                gist="처음", order_ids=[str(OS1)], _back="/project/%d/prod-request/edit?prid=%d" % (S1, P1)))
rv = revs(P1)
check(r.status_code == 303 and "prod_updated=1" in r.headers.get("location", "") and [x["kind"] for x in rv] == ["issue", "update"] and rv[1]["reason"] == "수량 변경"
      and "요청사항 1줄" in rv[1]["changes"] and "수량" in rv[1]["changes"] and rv[0]["cust_req"].startswith("1. 가상 검사기 040 : 1호기"),
      "수정발행 → 이력 0번(처음 글) + 1번(사유 · 바뀐 것: 요청사항 1줄 · 수량)", rv)
b = CARDS[0]["body"] if CARDS else ""
check("✏️ 수정 사유 : 수량 변경" in b and "+ 1. 가상 검사기 040 : 1~2호기" in b and "− 1. 가상 검사기 040 : 1호기" in b and "2. 지그" not in b.split("✏️ 바뀐 줄")[1].split("■")[0],
      "알림 글 맨 위에 수정 사유 + 바뀐 줄만(+ 새 줄 · − 지운 줄)", b[:400])
k = CARDS[0]["card"] if CARDS else {}
check(k.get("is_revision") is True and k.get("revision_reason") == "수량 변경" and "+ 1. 가상 검사기 040 : 1~2호기" in (k.get("changed_lines") or []),
      "이음 카드: 수정발행 표시 그대로 + 새 칸 revision_reason · changed_lines(세션 10 이 그리면 보임)", {x: k.get(x) for x in ("is_revision", "revision_reason", "changed_lines")})
with D.db_session() as c:
    rn = c.execute("SELECT revision_note FROM notifications WHERE kind='prod_request' AND prod_prid=? AND COALESCE(superseded,0)=0 AND card_json IS NOT NULL ORDER BY id DESC LIMIT 1", (P1,)).fetchone()
check(rn and str(rn[0]).startswith("사유: 수량 변경"), "웍스 종 알림의 수정 내용도 「사유: 수량 변경 · …」", rn and rn[0])
h = q(cl.get, "/project/%d/prod-request/edit" % S1).text; v = view(h)
check("사유: <b>수량 변경</b>" in v and "요청사항 1줄" in v and '<span class="z51-l z51-add">1. 가상 검사기 040 : 1~2호기' in v and '<span class="z51-l z51-del">1. 가상 검사기 040 : 1호기' in v
      and "바뀐 곳 숨기기" in v, "보기: 맨 위 띠(사유 · 바뀐 것) + 요청사항에서 바뀐 줄 노랗게 · 지운 줄 빨갛게 · 숨기기 단추")
check("🕘 수정 이력 1건" in h and "— 사유: 수량 변경" in h, "수정 이력 1건")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (S1, P1),
      data=dict(base, cust_req="1. 가상 검사기 040 : 1~2호기\n-. 케이스 포함\n2. 지그 : 1호기\n3. 커버 : 1호기", note="# 마킹", gist="처음", order_ids=[str(OS1)],
                _back="/project/%d/prod-request/edit?prid=%d" % (S1, P1)))
rv = revs(P1); h = q(cl.get, "/project/%d/prod-request/edit" % S1).text; v = view(h)
check(len(rv) == 3 and rv[2]["reason"] == "" and '<span class="z51-l z51-add">3. 커버 : 1호기</span>' in v and "z51-add\">1. 가상 검사기 040 : 1~2호기" not in v
      and "✏️ 수정 사유" not in CARDS[0]["body"] and "+ 3. 커버 : 1호기" in CARDS[0]["body"], "두 번째 수정(사유 없음): 바로 앞 수정과 비교해 새 줄만 노랗게 · 알림엔 바뀐 줄만", [x["kind"] for x in rv])

print("§2 묶음에서 빼기")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % A, data=dict(base, cust_req="1. 1연배\n2. MAP\n3. DOM\n4. ECALL", note="", gist="4종", order_ids=[str(OA)],
                                                            bundle_pids=[str(B), str(Cc), str(Dd)], add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % A,
                                                            **{"m_order_%d" % B: str(OB), "m_order_%d" % Cc: str(OC), "m_order_%d" % Dd: str(OD1)}))
LEAD = int(re.search(r"prid=(\d+)", r.headers["location"]).group(1))
h = q(cl.get, "/project/%d/prod-request/edit" % A).text; ef = edit_form(h)
check('name="remove_pids" value="%d"' % B in ef and 'name="remove_pids" value="%d"' % A not in ef and "대표 관리번호 — 뺄 수 없습니다" in ef and "× 로 뺄 수 있고" in ef,
      "수정 폼: 묶인 관리번호 칩에 × (대표 관리번호는 못 뺌)")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (A, LEAD), data=dict(base, rev_reason="품목 제외", cust_req="1. 1연배\n2. MAP\n3. ECALL", note="", gist="3종",
                                                                         order_ids=[str(OA)], remove_pids=[str(Cc), str(A)], _back="/project/%d/prod-request/edit?prid=%d" % (A, LEAD)))
rx = rowx("bundle_id=?", (LEAD,))
cx_c = [x for x in rx if x[1] == Cc][0]
check(cx_c[4] == "remove" and cx_c[3] and cx_c[5].startswith("묶음에서 뺌") and all(not x[3] for x in rx if x[1] != Cc), "022T2611 줄만 「묶음에서 뺌」(대표 관리번호는 빼라고 해도 안 빠짐)", rx)
h = q(cl.get, "/project/%d/prod-request/edit" % A).text; rw, me = rows(h)
check([x[1] for x in rw] == ["020 T 2611", "021 T 2611", "023 T 2611"] and "외 2건" in h, "보기: 품목 3줄 · 「외 2건」", [x[1] for x in rw])
b = CARDS[0]["body"] if CARDS else ""
check(CARDS and "외 2건" in CARDS[0]["title"] and "✏️ 빠진 품목 : 022T2611" in b and len(CARDS[0]["card"]["items"]) == 3 and CARDS[0]["card"].get("removed") == ["022T2611"],
      "알림: 「외 2건」 · 빠진 품목 022T2611 · 카드 품목 3개", CARDS and CARDS[0]["title"])
check("품목 제외 022T2611" in revs(LEAD)[-1]["changes"], "이력: 품목 제외 022T2611", revs(LEAD)[-1])
hc = q(cl.get, "/project/%d/prod-request/edit" % Cc).text
check("묶음에서 뺀 관리번호입니다" in hc and "020T2611 묶음 요청서 보기" in hc and 'id="prqEditForm"' not in hc and "📋 새로 작성" in hc and "제작요청서 · 022T2611" in hc,
      "빠진 관리번호(022T2611)로 열면: 「묶음에서 뺀 관리번호」 띠 · 묶음 요청서로 가는 길 · 고치기 없음 · 새로 작성")
h = q(cl.get, "/project/%d/prod-request/edit" % A).text
# z1191z58 (대표 11-18): 이미 보낸 요청서에 붙이는 것은 수정발행이 아니라 「묶어서 다시 발행」(?from) — 수정하기에는 붙이기 목록 대신 그 단추
hf = q(cl.get, "/project/%d/prod-request/edit?new=1&from=%d" % (A, LEAD)).text
check("z58-rebtn" in h and 'name="bundle_pids"' not in edit_form(h) and 'name="bundle_pids" value="%d"' % Cc in hf,
      "뺀 관리번호는 「🔗 관리번호 더 묶어서 다시 발행」 화면의 목록에 돌아옴(수정하기에서는 안 붙임 · z1191z58)")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (A, LEAD), data=dict(base, rev_reason="품목 추가", cust_req="1. 1연배\n2. MAP\n3. DOM\n4. ECALL", note="", gist="4종",
                                                                         order_ids=[str(OA)], bundle_pids=[str(Cc)], _back="/project/%d/prod-request/edit?prid=%d" % (A, LEAD),
                                                                         **{"m_order_%d" % Cc: str(OC)}))
h = q(cl.get, "/project/%d/prod-request/edit" % A).text; rw, me = rows(h)
check([x[1] for x in rw] == ["020 T 2611", "021 T 2611", "022 T 2611", "023 T 2611"] and "품목 추가 022T2611" in revs(LEAD)[-1]["changes"], "다시 붙이면 4줄 · 이력 「품목 추가 022T2611」", [x[1] for x in rw])

print("§3 취소 발행")
with D.db_session() as c:
    c.execute("UPDATE projects SET status='수주확정' WHERE id=?", (A,))
before = rowx("bundle_id=?", (LEAD,))
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/cancel" % (A, LEAD), data={"cancel_reason": "  "})
check("prod_cxneed=1" in r.headers.get("location", "") and rowx("bundle_id=?", (LEAD,)) == before and not CARDS, "사유 없이 취소 → 막힘 · 아무것도 안 바뀜")
PB = [x[0] for x in rowx("bundle_id=? AND project_id=?", (LEAD, B))][0]
with D.db_session() as c:
    old_live = c.execute("SELECT COUNT(*) FROM notifications WHERE kind='prod_request' AND prod_prid=? AND COALESCE(superseded,0)=0", (LEAD,)).fetchone()[0]
r = q(cl.post, "/project/%d/prod-request/%d/cancel" % (B, PB), data={"cancel_reason": "고객사 취소 요청"})   # 구성원 줄로 들어와도 묶음 전체
loc = r.headers.get("location", "")
rx = rowx("bundle_id=?", (LEAD,))
live = [x for x in rx if x[4] != "remove"]
check("prod_cxdone=1" in loc and "prid=%d" % LEAD in loc and all(x[3] and x[4] == "cancel" and x[5] == "고객사 취소 요청" for x in live) and len(live) == 4,
      "구성원(021T2611) 줄로 취소해도 묶음 4건 모두 취소 · 사유 저장", (loc, rx))
check(rowx("id=?", (cx_c[0],))[0][4] == "remove", "앞서 묶음에서 뺀 줄은 「뺌」 그대로")
cd = CARDS[0] if CARDS else {}
check(cd and cd["card"] and cd["card"].get("cancelled") is True and cd["card"].get("status") == "취소" and cd["title"].startswith("🚫 제작요청 취소 [020T2611 외 3건]") and "■ 취소 사유 : 고객사 취소 요청" in cd["body"] and "이 제작요청서는 진행하지 않습니다" in cd["body"]
      and "📝 요청사항" not in cd["body"] and "4. 023T2611" in cd["body"], "이음: 취소 카드(z1191z54 · cancelled · 상태 「취소」) + 「🚫 제작요청 취소」 글(사유 · 품목 줄 · 요청사항은 뺌)", cd and (cd["title"], cd["body"][:300]))
check(len(CARDS) == 2 and CARDS[1]["title"].startswith("🚫 내가 취소한 제작요청"), "취소한 사람에게도 확인 알림", [x["title"] for x in CARDS])
with D.db_session() as c:
    sup = c.execute("SELECT COUNT(*) FROM notifications WHERE kind='prod_request' AND prod_prid=? AND COALESCE(superseded,0)=1", (LEAD,)).fetchone()[0]
    nn = [tuple(x) for x in c.execute("SELECT title, COALESCE(revision_note,'') FROM notifications WHERE kind='prod_request' AND prod_prid=? AND COALESCE(superseded,0)=0", (LEAD,))]
    st = c.execute("SELECT status FROM projects WHERE id=?", (A,)).fetchone()[0]
check(sup >= old_live and nn and all("취소" in t for t, _ in nn) and any(n_ == "취소 — 고객사 취소 요청" for _, n_ in nn), "웍스 종 알림: 앞 알림은 흐리게(지난 것) · 새 알림 「취소 — 사유」", nn)
check(st == "수주확정", "취소해도 프로젝트 상태는 그대로(사람이 판단)", st)
h = q(cl.get, "/project/%d/prod-request/edit" % A).text
check("취소된 제작요청서입니다" in h and "사유: <b>고객사 취소 요청</b>" in h and 'class="z51-cxp"' in h and 'id="prqEditForm"' not in h and 'onclick="z51CancelOpen()"' not in h
      and "📋 새로 작성" in h and "🚫 취소됨" in h and "<b style=\"color:#b91c1c;\">🚫 취소</b>" in h, "보기: 취소 띠 · 「취소」 도장 · 고치기·취소 단추 없음 · 새로 작성 · 이력에 취소")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (A, LEAD), data=dict(base, cust_req="되살리기", note="", order_ids=[str(OA)], _back="/project/%d/prod-request/edit?prid=%d" % (A, LEAD)))
check("prod_cancelled=1" in r.headers.get("location", "") and not CARDS and rowx("id=?", (LEAD,))[0][3], "취소한 요청서는 수정발행이 막힘")
r = q(cl.post, "/project/%d/prod-request/%d/cancel" % (A, LEAD), data={"cancel_reason": "또"})
check("prod_cancelled=1" in r.headers.get("location", "") and not CARDS, "두 번 취소도 막힘")
hl = q(cl.get, "/prod-requests").text
check("🚫 취소" in hl, "제작요청서 목록 카드에 「🚫 취소」")
hn = q(cl.get, "/project/%d/prod-request/edit?new=1" % A).text
m = re.search(r'id="z50PastData">(.*?)</script>', hn, re.S); pa = json.loads(m.group(1)) if m else []
check(pa and pa[0]["mine"] and pa[0]["cx"] and "(이 관리번호) (취소됨)" in hn, "새 작성: 지난 요청서에 취소한 것도 「(취소됨)」으로 보임 → 글을 그대로 가져와 다시 발행 가능", [(d["mgmt"], d["cx"]) for d in pa])
check("같은 날 발주된 관리번호가" in hn, "취소된 요청서는 「요청서 있음」으로 안 침 → 같은 날 발주 묶기 권함이 다시 나옴")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
