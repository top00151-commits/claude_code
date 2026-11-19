# -*- coding: utf-8 -*-
"""z1191z69 시험 (대표 2026-11-19 「제작요청서 오른쪽 상단 작성자 … 작성자 바로 윗줄에 칸없이 조금만하게 "작성자 기술영업팀 안지연프로" ·
  지금 양식에 작성자는 "영업담당자" 로 변경하고 실제 이 아이템을 진행한는 기술영업팀 영업 담당자 이름을 적을수있게해줘」)
  ① 보기: 제목 줄에 작게 「작성자 <팀> <이름><직책>」 · 오른쪽 위 칸 = 「영업담당자」(프로젝트 영업담당자 · 직책 붙여) · 휴대폰 카드도
  ② 작성·수정 화면: 「영업담당자」 칸 + 기술영업팀 고르기 목록 → 저장 = projects.sales_name(이름만) · 변경 이력 · 관리번호대장 「영업 담당」도 같은 값
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z69-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z69_")
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


FUT = (date.today() + timedelta(days=10)).isoformat()
PAST = (date.today() - timedelta(days=5)).isoformat()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    TEAM = ins(c, "teams", {"name": "가상검사기팀", "code": "T48", "entity": "KOR", "display_order": 1})
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T948', 'T948', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T948'").fetchone())
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id) "
              "VALUES ('가상받는이', 'member', 'T949', 'T949', 'sso_only_no_local_password', 1, 1, ?)", (TEAM,))
    CU = ins(c, "customers", {"name": "가상고객(주)", "alias": "가상고객"})

    def proj(code, **kw):
        row = {"code": code, "name": "PBA", "mgmt_code": code, "customer_id": CU, "customer_name": "가상고객(주)", "currency": "KRW", "status": "진행중",
               "biz_div": "T", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "order_date": "2026-11-13", "due_date": FUT, "is_archived": 0,
               "unit_qty": 1, "model_name": "VPL-1", "equip_name": "가상 검사기", "cc_name": "홍길동", "cc_position": "계장"}
        row.update(kw)
        return ins(c, "projects", row)

    def order(pid, no, po, label, created, status="CONFIRMED"):
        return ins(c, "orders", {"order_no": no, "customer_id": CU, "order_date": created[:10], "due_date": FUT, "total_amount": 1000, "status": status,
                                 "created_at": created, "project_id": pid, "unit_label": label, "unit_qty": 1, "currency": "KRW", "so_type": "EQUIPMENT", "po_type": po})
    P1 = proj("020T2611", server_path="Z:\\가상고객\\TSP\\VPL-1\\9. 제품자료", engraving="VPL-1 FUNCTION TESTER")
    O1 = order(P1, "T-261113-5", "신규", "1호기", "2026-11-16 09:47:20")
    P2 = proj("028T2601", due_date=PAST)
    A1 = order(P2, "T-260126-3", "신규", "1호기", "2026-01-26 10:00:00")
    A2 = order(P2, "T-260202-2", "추가", "2호기", "2026-02-02 10:00:00")
    A3 = order(P2, "T-260311-5", "추가", "3호기", "2026-03-11 10:00:00")
    AX = order(P2, "T-260401-9", "추가", "9호기", "2026-04-01 10:00:00", status="CANCELLED")
    A4 = order(P2, "T-261116-5", "개조", "38호기", "2026-11-17 09:00:00")
    P3 = proj("030T2611")
    # z48e: 자동화·상품 수주처럼 「호기 표시」 칸에 부품 이름 목록이 든 것 · 호기가 길게 이어진 것
    P6 = proj("001M2607", biz_div="M", model_name="DWMT4400", equip_name="가상 자동화 설비")
    F1 = order(P6, "M-260707-1", "신규", " · ".join(["SENSOR", "CP", "SMPS (찬넬형)", "TOWER LAMP", "CONNECT PLUG", "EARTH BAR", "TOUCH SCREEN", "LM GUIDE"] * 30), "2026-07-07 14:57:00")
    P7 = proj("029T2601")
    G1 = order(P7, "T-260323-8", "추가", " · ".join("%d호기" % n for n in range(6, 16)) + " · 22호기 · 23호기 · 30호기", "2026-03-23 10:00:00")
    P4 = proj("031T2611")
    B1 = order(P4, "T-261117-1", "신규", "1호기", "2026-11-17 09:00:00")
    CO1 = ins(c, "consumable_orders", {"co_no": "C-261117-1", "mgmt_code": "010C2611", "customer_name": "가상고객 인도", "currency": "USD", "total_amount": 1000,
                                       "status": "CONFIRMED", "biz_div": "T", "order_date": "2026-11-17", "due_date": FUT, "cc_name": "Rohan", "equip_name": "인도 소모품 3종",
                                       "model_name": "소모품", "created_by": ADMIN["id"],
                                       "note": "-. Z:\\가상\\소모품\\11월\n-. 경로: Z:\\가상\\제조\\SM-S956\\1. 013T2606_기능검사기\n납품 전 연락"})
    ins(c, "consumable_order_items", {"co_id": CO1, "line_no": 1, "part_name": "PCB", "spec": "KNK-P-4963", "qty": 2, "unit": "EA", "model_use": "SM-S956",
                                      "image_path": "/uploads/x.jpg", "image_thumb_path": "/uploads/x_t.jpg", "linked_project_id": P1})
    ins(c, "consumable_order_items", {"co_id": CO1, "line_no": 2, "part_name": "PINBLOCK", "spec": "KNK-SM-S956 SUB-AP1", "qty": 1, "unit": "EA"})
    ins(c, "consumable_order_items", {"co_id": CO1, "line_no": 3, "part_name": "POGOPIN", "spec": "", "qty": 400, "unit": "EA"})
    P5 = proj("TMP-NOMG", mgmt_code="")
    E1 = order(P5, "T-261117-9", "신규", "1호기", "2026-11-17 09:30:00")
    CO3 = ins(c, "consumable_orders", {"co_no": "C-261117-9", "mgmt_code": "", "customer_name": "가상고객(주)", "currency": "KRW", "total_amount": 1, "status": "CONFIRMED",
                                       "biz_div": "T", "order_date": "2026-11-17", "due_date": FUT})
    CO2 = ins(c, "consumable_orders", {"co_no": "C-260907-1", "mgmt_code": "001C2609", "customer_name": "가상고객(주)", "currency": "KRW", "total_amount": 1000,
                                       "status": "CONFIRMED", "biz_div": "T", "order_date": "2026-09-07", "due_date": PAST, "model_name": "ON 2,3,4 FRC"})
    ins(c, "consumable_order_items", {"co_id": CO2, "line_no": 1, "part_name": "러버", "spec": "빗살무늬", "qty": 40, "unit": "EA"})

import app.main as M  # noqa: E402
import app.sso_client as SSO  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()   # 운영은 기동 때 더해지는 칸(prod_requests 통보 칸 등)
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
    _have = {r[1] for r in c.execute("PRAGMA table_info(prod_requests)")}
    # 옛 요청서(가리키는 수주 저장 없음)
    L1 = ins(c, "prod_requests", {"project_id": P1, "mgmt_code": "020T2611", "cust_req": "1. 가상 검사기 : 1호기\n-. 케이스 포함", "note": "# 마킹 적용",
                                  "created_at": "2026-11-16 10:09", "created_date": "2026-11-16", "issued_by": ADMIN["id"], "issued_by_name": "가상관리자"})
    L2 = ins(c, "prod_requests", {"project_id": P2, "mgmt_code": "028T2601", "cust_req": "추가 2호기", "created_at": "2026-02-05 11:00", "created_date": "2026-02-05",
                                  "issued_by_name": "가상관리자"})
    L6 = ins(c, "prod_requests", {"project_id": P6, "mgmt_code": "001M2607", "cust_req": "자동화 요청", "created_at": "2026-07-07 14:57", "created_date": "2026-07-07", "issued_by_name": "가상관리자"})
    L7 = ins(c, "prod_requests", {"project_id": P7, "mgmt_code": "029T2601", "cust_req": "추가 호기", "created_at": "2026-03-23 11:00", "created_date": "2026-03-23", "issued_by_name": "가상관리자"})
    L3 = ins(c, "prod_requests", {"project_id": P3, "mgmt_code": "030T2611", "cust_req": "수주 없는 건", "created_at": "2026-11-17 10:00", "created_date": "2026-11-17",
                                  "issued_by_name": "가상관리자"})
    try:
        ins(c, "prod_request_images", {"prod_request_id": L1, "project_id": P1, "url": "/uploads/prod_requests/1/a.jpg", "thumb_url": "/uploads/prod_requests/1/a_t.jpg", "orig_name": "마킹 위치.jpg"})
    except Exception as _e:
        print("이미지 표 없음:", _e)
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def _z65_meta(html, key):
    """z1191z65: 맨 아래 정보 칸(파란 이름 칸 위 · 값 아래)에서 이름 → 값."""
    t = re.search(r'<table class="z65-meta">(.*?)</table>', html, re.S)
    if not t:
        return None
    rows = [[re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)] for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t.group(1), re.S)]
    if len(rows) < 2 or key not in rows[0]:
        return None
    return rows[1][rows[0].index(key)]


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
    """보기 화면의 넓은 화면용 표만."""
    m = re.search(r'<div id="prqView">(.*?)<div class="z48-mob">', h, re.S)
    return m.group(1) if m else ""


def cells(h, label):
    """품목 줄: [No, 관리코드, 수주번호, 호기, 모델명, 품명, 수량, 일정]"""
    m = re.search(r'<tr><td>1</td>(.*?)</tr>', view(h), re.S)
    return [re.sub(r"<[^>]+>", " ", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), re.S)] if m else []




print("§1 보기 — 작성자는 제목 줄에 작게 · 오른쪽 위 칸 = 영업담당자")
with D.db_session() as c:
    TS = ins(c, "teams", {"name": "기술영업팀", "code": "01", "entity": "KOR", "display_order": 0})
    c.execute("UPDATE users SET team_id=?, rank='프로', name='안지연' WHERE id=?", (TS, ADMIN["id"]))   # 발행한 사람 = 기술영업팀 안지연 프로
    for nm, rk in (("이현", "매니저"), ("오경환", "프로")):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, rank) VALUES (?,?,?,?,?,1,1,?,?)",
                  (nm, "member", "S" + nm, "S" + nm, "sso_only_no_local_password", TS, rk))
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, rank) VALUES ('퇴사자','member','SX','SX','x',0,1,?,'프로')", (TS,))
    c.execute("UPDATE projects SET sales_name='이현' WHERE id=?", (P1,))
ADMIN.update({"team_id": TS, "rank": "프로", "name": "안지연"})
h = q(cl.get, "/project/%d/prod-request/edit" % P1).text
v = view(h)
check('<span class="z69-writer" title="이 제작요청서를 작성(발행)한 사람">작성자 기술영업팀 안지연프로</span>' in v,
      "제목 줄 오른쪽 아래 작게 「작성자 기술영업팀 안지연프로」(칸 없음)", re.findall(r'class="z69-writer"[^>]*>([^<]*)<', v))
check(">영업담당자</td><td" in v and "이현 매니저</td>" in v and ">작성자</td>" not in v, "오른쪽 위 칸 = 「영업담당자 · 이현 매니저」(작성자 칸 없음)")
mob = h[h.find('<div class="z48-mob">'):]
check('<div class="z69-writer-m">작성자 기술영업팀 안지연프로</div>' in mob and '<div class="k">영업담당자</div><div class="v">이현 매니저</div>' in mob
      and '<div class="k">작성자</div>' not in mob, "휴대폰 카드도 같게(제목 아래 작성자 · 영업담당자 칸)")
with D.db_session() as c:
    c.execute("UPDATE projects SET sales_name=NULL WHERE id=?", (P1,))
v = view(q(cl.get, "/project/%d/prod-request/edit" % P1).text)
check(re.search(r'>영업담당자</td><td[^>]*>—</td>', v), "영업담당자 비었으면 「—」")

print("§2 작성·수정 화면 — 영업담당자 칸 · 기술영업팀 고르기")
he = q(cl.get, "/project/%d/prod-request/edit" % P1).text
m = re.search(r'name="sales_name" list="(z69Sales[NE])" value="([^"]*)"', he)
opts = re.findall(r'<option value="([^"]+)">([^<]+)</option>', he[he.find('<datalist id="z69SalesE">'):he.find('</datalist>', he.find('<datalist id="z69SalesE">'))])
check(m and m.group(1) == "z69SalesE" and m.group(2) == "", "수정 화면에 「영업담당자」 칸(지금 값 = 빈칸)", m and m.groups())
check([o[0] for o in opts] == ["안지연", "오경환", "이현"] and ("이현", "이현 매니저") in opts, "고르기 목록 = 기술영업팀 재직자(이름 · 직책) · 퇴사자 없음", opts)
hn = q(cl.get, "/project/%d/prod-request/edit?new=1" % P1).text
check('list="z69SalesN"' in hn and '<datalist id="z69SalesN">' in hn, "새 작성 화면에도 같은 칸")
base = {"full_edit": "", "server_path": "", "model_name": "VPL-1", "engraving": ""}
r = q(cl.post, "/project/%d/prod-request/%d/update" % (P1, L1), data=dict(base, cust_req="1. 가상 검사기 : 1호기\n-. 케이스 포함", note="# 마킹 적용",
                                                                     order_ids=[str(O1)], sales_name="오경환 프로", _back="/project/%d/prod-request/edit?prid=%d" % (P1, L1)))
with D.db_session() as c:
    sn = c.execute("SELECT sales_name FROM projects WHERE id=?", (P1,)).fetchone()[0]
    hist = [dict(x) for x in c.execute("SELECT changed_by, field, old_value, new_value, note FROM project_history WHERE project_id=? AND field='영업담당자'", (P1,))]
check(r.status_code == 303 and sn == "오경환", "「오경환 프로」를 골라 저장 → 프로젝트 영업담당자 = 「오경환」(이름만)", (r.status_code, sn))
check(len(hist) == 1 and hist[0]["changed_by"] == ADMIN["id"] and hist[0]["old_value"] == "" and hist[0]["new_value"] == "오경환" and "안지연" in hist[0]["note"],
      "변경 이력 = 누가(번호·이름) · 빈칸 → 오경환", hist)
v = view(q(cl.get, "/project/%d/prod-request/edit" % P1).text)
check("오경환 프로</td>" in v, "보기 칸 = 「오경환 프로」")
r = q(cl.post, "/project/%d/prod-request/%d/update" % (P1, L1), data=dict(base, cust_req="1. 가상 검사기 : 1호기\n-. 케이스 포함", note="# 마킹 적용",
                                                                     order_ids=[str(O1)], _back="/project/%d/prod-request/edit?prid=%d" % (P1, L1)))
with D.db_session() as c:
    sn2 = c.execute("SELECT sales_name FROM projects WHERE id=?", (P1,)).fetchone()[0]
    nh = c.execute("SELECT COUNT(*) FROM project_history WHERE project_id=? AND field='영업담당자'", (P1,)).fetchone()[0]
check(sn2 == "오경환" and nh == 1, "영업담당자 칸 없이 저장(다른 화면) → 그대로 · 이력 안 늘어남", (sn2, nh))
r = q(cl.post, "/project/%d/prod-request/%d/update" % (P1, L1), data=dict(base, cust_req="1. 가상 검사기 : 1호기\n-. 케이스 포함", note="# 마킹 적용",
                                                                     order_ids=[str(O1)], sales_name="오경환", _back="/project/%d/prod-request/edit?prid=%d" % (P1, L1)))
with D.db_session() as c:
    nh = c.execute("SELECT COUNT(*) FROM project_history WHERE project_id=? AND field='영업담당자'", (P1,)).fetchone()[0]
check(nh == 1, "같은 사람으로 다시 저장 → 이력 안 늘어남", nh)
r = q(cl.post, "/project/%d/prod-request/new" % P4, data=dict(base, cust_req="새 요청", note="", order_ids=[str(B1)], add_team_ids=[str(TEAM)],
                                                             sales_name="  외부  담당  ", _back="/project/%d/prod-request/edit" % P4))
with D.db_session() as c:
    sn4 = c.execute("SELECT sales_name FROM projects WHERE id=?", (P4,)).fetchone()[0]
check(r.status_code == 303 and sn4 == "외부 담당", "새 작성에서 직접 적은 이름도 저장(목록에 없는 이름 · 빈칸 정리)", (r.status_code, sn4))
hl = q(cl.get, "/projects/ledger").text
check(re.search(r'>020T2611</a>.*?<td class="nw">오경환</td>', hl, re.S), "관리번호대장 「영업 담당」도 같은 값(오경환)")

print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
