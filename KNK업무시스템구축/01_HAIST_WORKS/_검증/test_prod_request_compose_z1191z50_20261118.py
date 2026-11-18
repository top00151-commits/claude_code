# -*- coding: utf-8 -*-
"""z1191z50 시험 (대표 2026-11-17 「2차 진행해」 · 2-2 작성 화면 편의)
  ① 새 작성 화면: 참고 이미지 칸(고르기·끌어다 놓기·Ctrl+V) · 「품목 번호 넣기」에 쓸 품명·수량·호기 · 「지난 요청서 불러오기」 목록
  ② 이미지를 붙여 발행 = 새 요청서(묶음이면 대표 줄)에 붙음 · 알림·카드에 장수 · 못 붙인 것 안내 · 20장 한도
  ③ 묶음 품목 줄 호기 칸 = 호기만(z48e 규칙)
  ④ 이미지 없이 발행은 지금과 같음
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z50-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z50_")
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
    P = proj("050T2611", shipment_form="PARTS", equip_name="가상 자동화 장비", unit_qty=2)                                  # 상품 수주 = 호기 칸에 부품 이름 목록
    OP = order(P, "M-261113-1", "신규", "SENSOR BRKT · CABLE ASSY x2 · BASE PLATE · COVER", "2026-11-16 12:00:00")

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
    ins(c, "prod_requests", {"project_id": E, "mgmt_code": "010T2609", "cust_req": "", "note": "", "created_at": "2026-09-02 11:00", "created_date": "2026-09-02"})      # 글 빈 요청서 → 목록에 안 나옴
    ins(c, "prod_requests", {"project_id": H, "mgmt_code": "032T2611", "cust_req": "폐기된 것", "created_at": "2026-11-16 10:30", "created_date": "2026-11-16"})          # 폐기 프로젝트 → 안 나옴
    ins(c, "prod_requests", {"project_id": G, "mgmt_code": "031T2611", "cust_req": "다른 고객사 것", "created_at": "2026-11-16 10:30", "created_date": "2026-11-16"})      # 다른 고객사 → A 목록엔 안 나옴
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


def png(seed):
    from PIL import Image
    im = Image.new("RGB", (64, 48), ((seed * 40) % 255, 120, 200))
    for x in range(0, 64, 4):
        im.putpixel((x, seed % 48), (255, 255, 255))
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()


def past_of(h):
    m = re.search(r'<script type="application/json" id="z50PastData">(.*?)</script>', h, re.S)
    return json.loads(m.group(1)) if m else None


def new_form(h):
    i = h.find('<form id="prqNewForm"')
    return h[i:h.find("</form>", i)] if i >= 0 else ""


def imgs_of(prid):
    with D.db_session() as c:
        return [tuple(r) for r in c.execute("SELECT id, url, orig_name FROM prod_request_images WHERE prod_request_id=? ORDER BY id", (prid,))]


base = {"full_edit": "", "server_path": "Z:\\가상전\\TSP\\VPL\\9. 제품자료", "model_name": "", "engraving": ""}

print("§1 작성 화면 — 이미지 칸 · 품목 번호 넣기 · 지난 요청서")
hn = q(cl.get, "/project/%d/prod-request/edit?new=1" % A).text
nf = new_form(hn)
check('enctype="multipart/form-data"' in nf[:300], "새 작성 폼은 이미지를 함께 보냄(multipart)")
check('id="z50ImgInput" name="pr_images"' in nf and "Ctrl+V" in nf and 'id="z50Drop"' in nf, "새 작성 폼 안에 참고 이미지 칸(고르기 · 끌어다 놓기 · Ctrl+V)")
check(nf.count("z50Number(this)") == 1 and "🔢 품목 번호 넣기" in nf, "「🔢 품목 번호 넣기」 단추")
pa = past_of(hn)
check(pa is not None and [d["mgmt"] for d in pa] == ["010T2609"] and pa[0]["mine"] is False and pa[0]["cust_req"] == "예전 요청" and "(이 관리번호)" not in hn,
      "지난 요청서: 이 관리번호엔 없음 → 같은 고객사 것(010T2609)만 · 글이 빈 것 · 폐기 · 다른 고객사는 뺌", pa)
check('data-mgmt="021T2611" data-equip="가상 검사기 021" data-qty="1"' in hn and '<input type="hidden" name="m_order_%d" value="%d" data-hogi="1호기">' % (B, OB) in hn,
      "묶을 관리번호 줄에 품명 · 수량 · 호기(품목 번호 넣기용)")
check('<option value="%d" data-hogi="2호기">' % OD2 in hn, "수주를 고르는 줄에도 호기")
_i = hn.find('data-mgmt="050T2611"')
check(_i > 0 and '<input type="hidden" name="m_order_%d" value="%d" data-hogi="">' % (P, OP) in hn[_i:_i + 1500], "상품 수주(부품 이름 목록)는 호기를 비움 → 「수량 N대」로 들어감")
he = q(cl.get, "/project/%d/prod-request/edit?new=1" % E).text
pe = past_of(he) or []
check(len(pe) == 1 and pe[0]["mgmt"] == "010T2609" and pe[0]["mine"] and "(이 관리번호)" in he and pe[0]["head"] == "예전 요청", "010T2609 로 새 작성: 자기 지난 요청서(이 관리번호) · 글 빈 요청서는 안 보임", pe)
with D.db_session() as c:   # 요청서가 하나도 없는 새 고객사
    CU3 = ins(c, "customers", {"name": "새고객(주)", "alias": "새"})
    Z = ins(c, "projects", {"code": "060T2611", "name": "PBA", "mgmt_code": "060T2611", "customer_id": CU3, "customer_name": "새고객(주)", "currency": "KRW", "status": "수주확정",
                            "biz_div": "T", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "order_date": "2026-11-13", "due_date": FUT, "is_archived": 0, "unit_qty": 1})
    ins(c, "orders", {"order_no": "T-261113-60", "customer_id": CU3, "order_date": "2026-11-13", "due_date": FUT, "total_amount": 1000, "status": "CONFIRMED",
                      "created_at": "2026-11-16 13:00:00", "project_id": Z, "unit_label": "1호기", "unit_qty": 1, "currency": "KRW", "so_type": "EQUIPMENT", "po_type": "신규"})
hx = q(cl.get, "/project/%d/prod-request/edit?new=1" % Z).text
check(past_of(hx) is None and 'class="z50-past"' not in new_form(hx) and "새 제작요청서 작성 · 060T2611" in hx, "지난 요청서가 하나도 없으면 불러오기 줄 자체가 없음")
hv = q(cl.get, "/project/%d/prod-request/edit" % E).text
check('id="z50PastData"' not in hv and 'id="z50ImgInput"' not in hv and "z50Number(this)" in hv, "발행된 요청서 화면: 불러오기 · 발행 전 이미지 칸 없음 · 수정 폼에 품목 번호 넣기")

print("§2 이미지를 붙여 발행")
_cwd = os.getcwd(); os.chdir(TMP)   # 이미지 저장 위치(uploads/…)를 임시 폴더로
CARDS.clear()
files = [("pr_images", ("도면1.png", png(1), "image/png")), ("pr_images", ("붙여넣기_101010_1.png", png(2), "image/png")),
         ("pr_images", ("메모.txt", b"x" * 100, "text/plain"))]
r = q(cl.post, "/project/%d/prod-request/new" % S1, data=dict(base, cust_req="1. 가상 검사기 040 : 1호기\n-. 케이스 포함", note="", gist="이미지 함께",
                                                             order_ids=[str(OS1)], add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % S1), files=files)
loc = r.headers.get("location", ""); mm = re.search(r"prid=(\d+)", loc); NEW = int(mm.group(1)) if mm else 0
im = imgs_of(NEW)
check(r.status_code == 303 and "prod_created=1" in loc and "prod_img=2" in loc and "prod_imgskip=1" in loc and len(im) == 2, "이미지 2장 + 글 파일 1개 → 새 요청서에 2장 붙음 · 1개는 못 붙임(까닭 표시)", (loc, im))
check(all(os.path.exists(os.path.join(TMP, u.lstrip("/"))) for _, u, _ in im) and [x[2] for x in im] == ["도면1.png", "붙여넣기_101010_1.png"], "이미지 파일이 저장됨 · 원래 이름(붙여넣기 이름 포함)", im)
check(CARDS and "📷 참고 이미지 2장" in CARDS[0]["body"] and CARDS[0]["card"].get("image_count") == 2, "알림 글 · 이음 카드에 「참고 이미지 2장」", CARDS and CARDS[0]["body"][-200:])
hg = q(cl.get, loc).text
check("참고 이미지 2장" in hg and "이미지 1장은 붙이지 못했습니다" in hg and hg.count('class="prq-imgcell"') == 2, "발행 뒤 화면: 「참고 이미지 2장」 · 못 붙인 1장 안내 · 이미지 칸에 2장")

print("§3 묶어서 발행 + 이미지 · 묶음 줄 호기")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % A, data=dict(base, cust_req="1. 가\n-. a", note="", gist="묶음 이미지", order_ids=[str(OA)], bundle_pids=[str(P), str(B)],
                                                            add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % A, **{"m_order_%d" % B: str(OB), "m_order_%d" % P: str(OP)}),
      files=[("pr_images", ("케이스.png", png(3), "image/png"))])
loc = r.headers.get("location", ""); mm = re.search(r"prid=(\d+)", loc); LEAD = int(mm.group(1)) if mm else 0
rws = prq("bundle_id=?", (LEAD,))
check(LEAD and [x[1] for x in rws] == [A, B, P] and len(imgs_of(LEAD)) == 1 and all(not imgs_of(x[0]) for x in rws[1:]) and "prod_img=1" in loc,
      "묶음 발행: 이미지는 대표 줄에 한 번(구성원 줄엔 따로 안 붙음)", (rws, loc))
check(len(CARDS) == 2 and "📷 참고 이미지 1장" in CARDS[0]["body"], "묶음 알림에도 이미지 장수", CARDS and CARDS[0]["body"][-120:])
h = q(cl.get, "/project/%d/prod-request/edit" % A).text; rw, me = rows(h)
check([x[1] for x in rw] == ["020 T 2611", "021 T 2611", "050 T 2611"] and rw[1][3] == "1호기" and rw[2][3] == "—" and "CABLE" not in view(h),
      "묶음 품목 줄 호기 칸 = 호기만(상품 수주의 부품 이름 목록이 안 나옴)", [x[:4] for x in rw])
ef = h[h.find('<form id="prqEditForm"'):]
ef = ef[:ef.find("</form>")]
check("z50Number(this)" in ef and 'data-mgmt="020T2611" data-equip="가상 검사기 020" data-qty="1" data-hogi="1호기" data-lead="1"' in ef
      and 'data-mgmt="050T2611" data-equip="가상 자동화 장비" data-qty="2" data-hogi=""' in ef, "수정 폼: 품목 번호 넣기 · 묶인 관리번호 칩에 품명 · 수량 · 호기", re.findall(r'<span class="z49-chip"[^>]*>', ef))
hb = q(cl.get, "/project/%d/prod-request/edit?new=1" % B).text
pb = past_of(hb) or []
check(pb and pb[0]["mine"] and pb[0]["gist"] == "묶음 이미지" and sum(1 for d in pb if d["gist"] == "묶음 이미지") == 1, "묶인 관리번호(021T2611)로 새 작성: 그 묶음 요청서가 한 번만(이 관리번호)", [(d["mgmt"], d["gist"], d["mine"]) for d in pb])

print("§4 이미지 없이 발행 = 지금과 같음 · 한도")
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % S1, data=dict(base, cust_req="이미지 없음", note="", order_ids=[str(OS1)], add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % S1))
loc = r.headers.get("location", "")
check("prod_created=1" in loc and "prod_img" not in loc and CARDS and "📷" not in CARDS[0]["body"] and not CARDS[0]["card"].get("image_count"), "이미지 없이 발행(옛 폼 모양)은 그대로", loc)
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % S1, data=dict(base, cust_req="21장", note="", order_ids=[str(OS1)], add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % S1),
      files=[("pr_images", ("p%02d.png" % i, png(i), "image/png")) for i in range(21)])
loc = r.headers.get("location", ""); mm = re.search(r"prid=(\d+)", loc)
check("prod_img=20" in loc and "prod_imgskip=1" in loc and mm and len(imgs_of(int(mm.group(1)))) == 20 and "참고 이미지 20장" in CARDS[0]["body"], "21장 → 20장까지만 붙음 · 1장은 못 붙임 안내", loc)
os.chdir(_cwd)

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
