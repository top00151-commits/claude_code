# -*- coding: utf-8 -*-
"""z1191z49 시험 (대표 2026-11-17 「제작 요청서를 여러 개를 한 번에 묶어서 발행」 · 「2차 진행해」)
  ① 묶을 수 있는 관리번호(같은 고객사 · 수주 있음 · 같은 날 발주·요청서 없는 것 먼저)
  ② 묶어서 새 발행 = 관리번호마다 줄 · 통보 한 번 · 알림 글·이음 카드에 품목 줄
  ③ 보기 = 한 장에 품목 여러 줄 · 구성원 관리번호로 들어와도 같은 한 장(그 줄 노란 칠)
  ④ 수정발행 = 묶음 전체 · 관리번호 더 붙이기 · 통보 한 번
  ⑤ 안 묶으면 지금과 같음 · 필수 규칙 그대로
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z49-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z49_")
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


print("§1 묶을 수 있는 관리번호")
with D.db_session() as c:
    pa = dict(c.execute("SELECT * FROM projects WHERE id=?", (A,)).fetchone())
    cands = M._z49_candidates(c, pa, {A})
ids = [d["id"] for d in cands]
check(ids[:3] == [B, Cc, Dd] and all(cands[i]["suggest"] for i in range(3)), "같은 날 발주 · 요청서 없는 관리번호 3건이 맨 앞(권함 · 관리번호 순)", ids)
check(E in ids and not [d for d in cands if d["id"] == E][0]["suggest"] and S1 in ids, "같은 고객사의 다른 날 것도 고를 수는 있음(권하지는 않음)")
check(F not in ids and G not in ids and H not in ids and A not in ids, "수주 없는 것 · 다른 고객사 · 폐기 · 자기 자신은 못 묶음")
hn = q(cl.get, "/project/%d/prod-request/edit?new=1" % A).text
check("같은 날 발주된 관리번호가 <b>3건</b> 더 있습니다" in hn and "모두 묶기" in hn and hn.count('name="bundle_pids"') == len(ids), "작성 화면: 「함께 발주된 3건 · 모두 묶기」 + 고를 수 있는 목록", hn.count('name="bundle_pids"'))
check(re.search(r'<select name="m_order_%d"[^>]*><option value="%d"(?: data-hogi="[^"]*")?>T-261117-3 · 추가 · 2호기</option><option value="%d"(?: data-hogi="[^"]*")?>T-261113-8' % (Dd, OD2, OD1), hn) is not None
      and '<input type="hidden" name="m_order_%d" value="%d" data-hogi=' % (B, OB) in hn, "수주가 여러 건인 관리번호는 그 줄에서 수주를 고름(기본 = 최근) · 한 건이면 자동")
check('name="bundle_model"' in hn, "MODEL(묶음 이름) 칸")

print("§2 묶어서 새 발행")
base = {"full_edit": "", "server_path": "Z:\\가상전\\TSP\\VPL\\9. 제품자료", "model_name": "VPL-020", "engraving": "ENG-020"}
CARDS.clear(); n0 = notif_n()
r = q(cl.post, "/project/%d/prod-request/new" % A, data=dict(base, cust_req="1. 1연배\n2. MAP\n3. DOM\n4. ECALL", note="# 마킹", gist="신규 4종", order_ids=[str(OA)],
                                                            bundle_pids=[str(Dd), str(F), str(Cc), str(G), str(B), str(H)], bundle_model="VPL2132_2138",   # 어떤 순서로 넘어와도
                                                            add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % A, **{"m_order_%d" % Dd: str(OD1), "m_order_%d" % B: str(OB), "m_order_%d" % Cc: str(OC)}))
loc = r.headers.get("location", ""); mm = re.search(r"prid=(\d+)", loc); LEAD = int(mm.group(1)) if mm else 0
rws = prq("bundle_id=?", (LEAD,))
check(r.status_code == 303 and "prod_created=1" in loc and LEAD and [x[1] for x in rws] == [A, B, Cc, Dd], "관리번호 4개 묶음 → 줄 4개(수주 없는 것·다른 고객사·폐기는 버림) · 고른 순서가 아니라 관리번호 순", (loc, rws))
check([x[3] for x in rws] == [str(OA), str(OB), str(OC), str(OD1)] and len({x[4] for x in rws}) == 1 and {x[5] for x in rws} == {"신규 4종"} and {x[6] for x in rws} == {"VPL2132_2138"},
      "줄마다 자기 수주(고른 것) · 글·요지·묶음 이름은 같음", rws)
check(notif_n() - n0 == 3 and len(CARDS) == 2, "통보는 한 번(받는 사람 2명 + 발행자 확인 1 · 이음 카드도 한 묶음으로)", (notif_n() - n0, len(CARDS)))
cd = CARDS[0]
check("[020T2611 외 3건] VPL2132_2138" in cd["title"], "알림 제목 「020T2611 외 3건」 + 묶음 이름", cd["title"])
check("■ 품목 4건 · MODEL VPL2132_2138" in cd["body"] and "  1. 020T2611 · 가상 검사기 020 · 수량 1" in cd["body"] and "  4. 023T2611" in cd["body"] and "수주 T-261113-8" in cd["body"]
      and "■ 품명 :" not in cd["body"] and "■ 요지 : 신규 4종" in cd["body"], "알림 글에 품목 줄 4개", cd["body"][:400])
k = cd["card"]
check(k["mgmt"] == "020T2611 외 3건" and k["so_nos"] == ["T-261113-5", "T-261113-6", "T-261113-7", "T-261113-8"] and k["model"] == "VPL2132_2138"
      and [i["mgmt"] for i in k["items"]] == ["020T2611", "021T2611", "022T2611", "023T2611"] and k["items"][3]["so_nos"] == ["T-261113-8"], "이음 카드: 관리번호 「외 3건」 · 수주번호 전부 · 새 칸 items", {x: k.get(x) for x in ("mgmt", "so_nos", "model")})
with D.db_session() as c:
    st = [r_[0] for r_ in c.execute("SELECT status FROM projects WHERE id IN (?,?,?,?) ORDER BY id", (A, B, Cc, Dd))]
check(st == ["진행중"] * 4, "묶인 관리번호 모두 상태 수주확정 → 진행중", st)

print("§3 보기 = 한 장")
h = q(cl.get, "/project/%d/prod-request/edit" % A).text; rw, me = rows(h)
check([x[1] for x in rw] == ["020 T 2611", "021 T 2611", "022 T 2611", "023 T 2611"] and [x[2] for x in rw] == ["T-261113-5", "T-261113-6", "T-261113-7", "T-261113-8"] and not me,
      "대표 관리번호로 열기: 품목 4줄(관리코드·수주번호) · 노란 칠 없음", (rw, me))
check(rw[1][4:7] == ["VPL-021", "가상 검사기 021", "1"] and rw[1][7].startswith(FUT) and "D-14" in rw[1][7], "구성원 줄: 모델명·품명·수량·일정+남은 날", rw[1])
v = view(h)
check(">MODEL</td><td>VPL2132_2138</td>" in v and "외 3건" in h and "묶어서 발행한 요청서" in h, "MODEL = 묶음 이름 · 머리글 「외 3건」")
eng = re.search(r'각인</td></tr>\s*(?:\{#.*?#\}\s*)?<tr><td colspan="8">(.*?)</td></tr>', v, re.S)
et = re.sub(r"<[^>]+>", " ", eng.group(1)) if eng else ""
check("1)" in et and "ENG-020" in et and "ENG-021" in et and "4)" in et and "ENG-023" in et and "3)" not in et, "각인은 품목마다(번호 붙여) · 각인이 없는 품목은 줄 없음", et)
hb = q(cl.get, "/project/%d/prod-request/edit" % Cc).text; rwb, meb = rows(hb)
check([x[1] for x in rwb] == [x[1] for x in rw] and meb == ["3"] and 'action="/project/%d/prod-request/%d/update"' % (A, LEAD) in hb, "구성원(022T2611)으로 열어도 같은 한 장 · 그 줄 노란 칠 · 수정은 묶음 전체로", (meb,))
mob = hb[hb.find('<div class="z48-mob">'):]
check(mob.count('class="z48-it') == 4 and 'class="z48-it z49-me"' in mob, "휴대폰 카드에도 품목 4개 · 그 줄 표시")
hnew = q(cl.get, "/project/%d/prod-request/edit?new=1" % Cc).text
check("새 제작요청서 작성 · 022T2611" in hnew, "구성원 관리번호에서 「새로 작성」은 그 관리번호의 새 요청서")
for u in ("/prod-requests", "/project/%d" % B):
    check(q(cl.get, u).status_code == 200, "%s 열림" % u)

print("§4 수정발행 = 묶음 전체 + 더 붙이기")
CARDS.clear(); n0 = notif_n()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (Cc, prq("project_id=?", (Cc,))[0][0]),
      data=dict(base, cust_req="1. 1연배\n2. MAP\n3. DOM · 손잡이 변경\n4. ECALL", note="# 마킹", gist="신규 5종", order_ids=[str(OA)], bundle_pids=[str(S1), str(B)],
                bundle_model="VPL2132_2138", _back="/project/%d/prod-request/edit?prid=%d" % (A, LEAD), **{"m_order_%d" % S1: str(OS1)}))
rws = prq("bundle_id=?", (LEAD,))
check(r.status_code == 303 and "prod_updated=1" in r.headers.get("location", "") and [x[1] for x in rws] == [A, B, Cc, Dd, S1], "구성원 줄 번호로 수정발행해도 묶음 전체 · 새 관리번호 한 개 붙음(이미 묶인 것은 그대로)", (r.headers.get("location"), [x[1] for x in rws]))
check(len({x[4] for x in rws}) == 1 and "손잡이 변경" in rws[0][4] and {x[5] for x in rws} == {"신규 5종"} and rws[4][3] == str(OS1), "글·요지가 모든 줄에 같게 바뀜 · 붙인 줄은 자기 수주", rws[-1])
check(len(CARDS) == 2 and "외 4건" in CARDS[0]["title"] and "[수정]" in CARDS[0]["title"] and len(CARDS[0]["card"]["items"]) == 5 and CARDS[0]["card"]["is_revision"] is True
      and notif_n() - n0 == 3, "수정 통보도 한 번 · 「외 4건」 · 품목 5개", (len(CARDS), CARDS and CARDS[0]["title"], notif_n() - n0))
h = q(cl.get, "/project/%d/prod-request/edit" % S1).text; rw, me = rows(h)
check(len(rw) == 5 and me == ["5"] and "이미 묶인 관리번호입니다" in h, "붙인 관리번호로 열어도 같은 한 장(5줄)", (len(rw), me))

print("§5 안 묶으면 지금과 같음 · 필수 규칙")
with D.db_session() as c:
    c.execute("DELETE FROM prod_requests WHERE project_id=? AND bundle_id IS NOT NULL", (S1,))
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % S1, data=dict(base, cust_req="혼자 발행", note="", order_ids=[str(OS1)], add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % S1))
one = prq("project_id=?", (S1,))
check(len(one) == 1 and one[0][2] == 0 and one[0][6] == "" and CARDS and "외" not in CARDS[0]["title"] and CARDS[0]["card"]["mgmt"] == "040T2611" and "items" not in CARDS[0]["card"]
      and "■ 품명 : PBA · 수량 1" in CARDS[0]["body"], "묶지 않은 발행 = 묶음 표시 없음 · 알림·카드 지금 모양 그대로", (one, CARDS and CARDS[0]["title"]))
h1 = q(cl.get, "/project/%d/prod-request/edit" % S1).text; rw1, me1 = rows(h1)
check(len(rw1) == 1 and not me1 and "묶어서 발행한 요청서" not in h1, "보기도 한 줄 그대로")
with D.db_session() as c:
    c.execute("UPDATE orders SET status='CANCELLED' WHERE id=?", (OB,))   # 묶인 관리번호의 수주가 사라짐
CARDS.clear()
with contextlib.redirect_stdout(io.StringIO()):
    res = M._prod_request_notify_core(A, "x", "", [TEAM], ADMIN, record=False, is_update=True, prid=LEAD)
check(res.get("ok") is False and res.get("error") == "need_mgmt_order" and res.get("need") == "member" and res.get("who") == "021T2611" and not CARDS,
      "묶인 관리번호에 수주가 없어지면 수정발행을 막음(수주번호 필수) · 어느 관리번호인지 알려 줌", res)

before = prq("bundle_id=?", (LEAD,))
r = q(cl.post, "/project/%d/prod-request/%d/update" % (A, LEAD), data=dict(base, cust_req="막혀야 함", note="", gist="", order_ids=[str(OA)], _back="/project/%d/prod-request/edit?prid=%d" % (A, LEAD)))
check("prod_need=member" in r.headers.get("location", "") and prq("bundle_id=?", (LEAD,)) == before and not CARDS, "화면에서 수정발행해도 저장 전에 막힘 · 아무것도 안 바뀜", r.headers.get("location"))
hm = q(cl.get, r.headers["location"]).text
check('id="z48NeedMsg"' in hm and "함께 묶은 관리번호 중에 수주가 없는 것" in hm, "돌아온 화면에 막힌 까닭")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
