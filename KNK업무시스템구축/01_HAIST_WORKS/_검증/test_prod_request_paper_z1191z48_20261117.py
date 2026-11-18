# -*- coding: utf-8 -*-
"""z1191z48 시험 (대표 2026-11-17 「이음웍스 제작요청서를 기존에 쓰는 제작 요청서와 최대한 비슷하게 · 수주번호」
                「소모품 요청서 … 여기에도 관리번호·수주번호」 「진행해」 · z48c 「관리번호 수주번호는 필수 입력 사항임」)
  ① 가리키는 수주 고르기 규칙(저장값 · 옛 요청서 · 수주 없음 · 취소 수주)
  ② 제작요청서 보기 = 종이 양식(관리코드·수주번호·호기·구분·요지·남은 날·경로 복사·휴대폰 카드·인쇄) · 옛 화면 글자(사업부) 유지
  ③ 작성·수정 폼: 수주 고르기 + 요지 → 저장 · 알림 글 · 이음 카드에 그 수주번호만
  ④ 소모품 요청서 = 종이 양식(관리번호·수주번호 · 내용 · 요청사항 경로 복사 · 사진/연결 장비 칸은 있을 때만)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z48-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z48_")
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


print("§1 가리키는 수주 고르기 규칙")
od = [{"id": 1, "order_no": "A", "created_at": "2026-01-26 10:00:00"}, {"id": 2, "order_no": "B", "created_at": "2026-02-02 10:00:00"}, {"id": 3, "order_no": "C", "created_at": "2026-11-17 09:00:00"}]
pk = M._z48_pick_orders
check([o["order_no"] for o in pk(od, "3,1", "2026-02-05 11:00")] == ["A", "C"], "저장값이 있으면 그 수주들(등록 순)")
check([o["order_no"] for o in pk(od, "", "2026-02-05 11:00")] == ["B"], "옛 요청서 = 발행 시각까지 등록된 것 중 가장 늦은 한 건")
check([o["order_no"] for o in pk(od, "", "2026-01-01 00:00")] == ["A"], "수주를 나중에 등록 = 가장 먼저 등록된 한 건")
check([o["order_no"] for o in pk(od, "99", "2026-12-01 00:00")] == ["C"], "저장값이 이 프로젝트 수주가 아니면 규칙대로")
check(pk([], "1", "2026-02-05") == [], "수주가 없으면 빈 목록")
check(M._z48_mg("020T2611") == "020 T 2611" and M._z48_mg("A01T2607") == "A01T2607" and M._z48_mg("") == "", "관리번호 띄어 쓰기(모양이 다르면 그대로)")
check(M._z48_dday(FUT) == "D-10" and M._z48_dday(PAST) == "" and M._z48_dday(date.today().isoformat()) == "D-day" and M._z48_dday("") == "", "남은 날 — 앞날·오늘만")
with D.db_session() as c:
    cand = [o["order_no"] for o in M._z48_project_orders(c, P2)]
check(cand == ["T-260126-3", "T-260202-2", "T-260311-5", "T-261116-5"], "후보 = 취소 수주 빼고 등록 순", cand)

print("§2 제작요청서 보기 = 종이 양식")
r = q(cl.get, "/project/%d/prod-request/edit" % P1); h = r.text; v = view(h)
check(r.status_code == 200 and 'class="z48-prs z48-desk"' in v and ">제작 요청서<span" in v, "종이 양식 표 + 제목")
row = cells(h, "")
check(row[:6] == ["020 T 2611", "T-261113-5", "1호기", "VPL-1", "가상 검사기", "1"], "품목 줄: 관리코드·수주번호·호기·모델명·품명·수량", row)
check(len(row) == 7 and row[6].startswith(FUT) and "D-10" in row[6], "일정 + 남은 날", row[-1:])
check('class="z48-bdg z48-new"' in v and ">신규</span>" in v, "구분 = 수주의 발주유형(신규)")
check(">고객사</td>" in v and "가상고객(주)" in v and ">작성자</td>" in v and "가상관리자" in v and "홍길동 계장" in v and ">MODEL</td>" in v, "머리: 고객사·작성자·담당자·MODEL")
check(">각인</td>" in v and "VPL-1 FUNCTION TESTER" in v, "각인")
check('data-copy="Z:\\가상고객\\TSP\\VPL-1\\9. 제품자료"' in v and "z48Copy(this)" in v and "📋 경로 복사" in v and "window.z48Copy" in h, "자료 경로 + 「경로 복사」 단추")
check('class="z48-req">1. 가상 검사기 : 1호기\n-. 케이스 포함</td>' in v and 'class="z48-req"># 마킹 적용</td>' in v, "고객사 요청사항 ｜ 기타 요청사항 나란히")
_m = {k: _z65_meta(v, k) for k in ("프로젝트명", "사업부", "형태", "거래구분", "발주일")}   # z1191z65: 한 줄 → 종이 양식 칸
check(_m == {"프로젝트명": "PBA", "사업부": "🔬 검사기", "형태": "🏭 완제품", "거래구분": "🏠 내수", "발주일": "2026-11-13"} and 'class="z48-kv"' not in v,
      "웍스에만 있는 값 = 파란 이름 칸 + 값 칸(프로젝트명·사업부·형태·거래구분·발주일 · 작은 회색 한 줄 없음)", _m)
check("요지</td>" not in v, "요지를 안 썼으면 그 줄 없음")
mob = h[h.find('<div class="z48-mob">'):]
check('<div class="z48-mob">' in h and "020 T 2611" in mob and "T-261113-5" in mob and "@container (max-width:820px)" in h and "container-type:inline-size" in h and "@media (max-width:760px)" in h and h.count(".z48-desk { display:none; }") == 2,
      "좁은 폭(휴대폰 · 좁힌 창) = 카드(표 숨김) — 양식 자리 폭 기준 + 옛 브라우저용 화면 폭 기준")
check("td.z48-h { background:#b8cce4; font-weight:700; white-space:nowrap; }" in h and "letter-spacing:1px; white-space:nowrap; }" in h, "머리글·관리번호·수주번호는 줄바꿈 안 함(글자마다 꺾이지 않게)")
check("@media print" in h and "#z48Paper" in h and 'onclick="window.print()"' in h and "🖨 인쇄" in h and "size:A4" in h, "인쇄 단추 + 인쇄 때 종이 양식만")
check('data-knk-zoom data-knk-name="마킹 위치.jpg"' in h and "prq-imgs z48-imgs" in h and "눌러서 크게 보기" in h, "참고 이미지 크게 · 눌러서 확대")
check("z48-rev" not in v, "수정발행 전에는 수정 띠 없음")
h2 = q(cl.get, "/project/%d/prod-request/edit" % P2).text; row2 = cells(h2, "")
check(row2[:3] == ["028 T 2601", "T-260202-2", "2호기"] and 'class="z48-bdg z48-add"' in view(h2), "수주 4건짜리 관리번호의 옛 요청서 = 발행 무렵 수주 한 건만(추가·2호기)", row2[:3])
check("D-" not in row2[6], "납기가 지난 건에는 남은 날 없음", row2[6:])
h3 = q(cl.get, "/project/%d/prod-request/edit" % P3).text; row3 = cells(h3, "")
check(row3[1:3] == ["—", "—"], "수주가 없으면 수주번호·호기 「—」", row3[:3])

print("§2-1 호기 칸 (z48e · 대표 신고 「웍스에 적용이 잘못된 것 같은데」 — 자동화 요청서 호기 칸에 부품 이름이 줄줄이)")
hg = M._z48_hogi
check(hg("1호기") == "1호기" and hg("1호기 · 2호기") == "1~2호기" and hg("6호기 · 7호기 · 8호기 · 10호기") == "6~8호기, 10호기", "호기만 뽑아 이어진 번호는 묶음")
check(hg("SENSOR · CP · SMPS (찬넬형)") == "" and hg("SM-A27 USB PBA ×3") == "" and hg("") == "" and hg(None) == "" and hg("사양변경") == "", "호기가 아닌 글(부품 이름·모델·메모)은 빈칸")
h6 = q(cl.get, "/project/%d/prod-request/edit" % P6).text; r6 = cells(h6, "")
check(r6[:3] == ["001 M 2607", "M-260707-1", "—"] and "TOWER LAMP" not in view(h6) and len(view(h6)) < 9000, "부품 이름 목록이 든 수주 = 호기 칸 「—」 · 화면에 그 목록 안 나옴", (r6[:3], len(view(h6))))
check(r6[3:6] == ["DWMT4400", "가상 자동화 설비", "1"], "그 줄의 모델명·품명·수량은 그대로 보임", r6[3:6])
mob6 = h6[h6.find('<div class="z48-mob">'):h6.find('{% include', 0) if False else len(h6)]
check("TOWER LAMP" not in mob6.split("고객사 요청사항")[0], "휴대폰 카드에도 그 목록 안 나옴")
h7 = q(cl.get, "/project/%d/prod-request/edit" % P7).text; r7 = cells(h7, "")
check(r7[2] == "6~15호기, 22~23호기, 30호기", "호기 13대 = 「6~15호기, 22~23호기, 30호기」", r7[2])
h6n = q(cl.get, "/project/%d/prod-request/edit?new=1" % P2).text
check("38호기" in h6n, "수주 고르는 목록에는 호기 그대로")

print("§3 작성·수정 폼 — 수주 고르기 + 요지")
hn = q(cl.get, "/project/%d/prod-request/edit?new=1" % P2).text
boxes = re.findall(r'<input type="checkbox" name="order_ids" value="(\d+)"(?: data-hogi="[^"]*")?( checked)?>\s*<b>([^<]+)</b>', hn)   # z50: 호기 속성
check([b[2] for b in boxes] == ["T-261116-5", "T-260311-5", "T-260202-2", "T-260126-3"] and [b[2] for b in boxes if b[1]] == ["T-261116-5"],
      "새 작성: 수주 4건(취소 뺌) 체크 목록 — 최근 것이 맨 위 · 기본 = 가장 최근 수주", boxes)
check('name="gist"' in hn and "수주가 4건 있습니다" in hn, "요지 칸 + 안내 글")
hn1 = q(cl.get, "/project/%d/prod-request/edit?new=1" % P4).text
check('<input type="hidden" name="order_ids" value="%d" data-hogi=' % B1 in hn1 and "T-261117-1" in hn1 and 'type="checkbox" name="order_ids"' not in hn1, "수주가 한 건이면 고르지 않고 자동")
hn3 = q(cl.get, "/project/%d/prod-request/edit?new=1" % P3).text
check('name="order_ids"' not in hn3 and 'class="z48-need"' in hn3 and "수주를 먼저 등록해야" in hn3
      and re.search(r'<button type="submit" form="prqNewForm"[^>]* disabled ', hn3), "수주가 없으면 「먼저 등록」 안내 + 발행 단추 못 누름(필수)")
check(not re.search(r'<button type="submit" form="prqNewForm"[^>]* disabled ', hn) and "(필수)" in hn and "수주번호를 하나 이상 고르세요" in hn, "수주가 있으면 단추 살아 있음 · 「필수」 표시 · 안 고르면 막는 확인")

base = {"full_edit": "", "server_path": "", "model_name": "VPL-1", "engraving": ""}
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % P2, data=dict(base, cust_req="38호기 MODIFY", note="", gist="적층도 변경으로 신규 가공 진행", order_ids=[str(A4)],
                                                              add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % P2))
loc = r.headers.get("location", "")
mprid = re.search(r"prid=(\d+)", loc)
check(r.status_code == 303 and mprid and "prod_created=1" in loc and "prod_sent=1" in loc, "새 발행(개조 수주 한 건 고름 · 요지) → 통보 1명", loc)
NEW = int(mprid.group(1)) if mprid else 0
with D.db_session() as c:
    rw = c.execute("SELECT order_ids, gist FROM prod_requests WHERE id=?", (NEW,)).fetchone()
    nb = c.execute("SELECT body FROM notifications WHERE kind='prod_request' ORDER BY id DESC LIMIT 1").fetchone()
check(rw and rw[0] == str(A4) and rw[1] == "적층도 변경으로 신규 가공 진행", "저장: 가리키는 수주 · 요지", rw and tuple(rw))
check(nb and "■ 요지 : 적층도 변경으로 신규 가공 진행" in nb[0] and "수주 T-261116-5" in nb[0] and "T-260126-3" not in nb[0], "알림 글: 요지 + 그 수주번호만", nb and nb[0][:200])
check(CARDS and CARDS[0]["card"]["so_nos"] == ["T-261116-5"], "이음 카드 수주번호 = 그 수주만(전에는 관리번호의 수주 전부)", CARDS and CARDS[0]["card"].get("so_nos"))
hv = q(cl.get, "/project/%d/prod-request/edit?prid=%d" % (P2, NEW)).text; rv = cells(hv, "")
check(rv[:3] == ["028 T 2601", "T-261116-5", "38호기"] and 'class="z48-bdg z48-mod"' in view(hv) and ">MODIFY</span>" in view(hv), "보기: 그 수주·호기 · 구분 MODIFY", rv[:3])
check('<td colspan="3" class="z48-h">요지</td><td colspan="5" class="z48-gist">적층도 변경으로 신규 가공 진행</td>' in view(hv), "보기: 요지 줄")
boxes = re.findall(r'<input type="checkbox" name="order_ids" value="(\d+)"(?: data-hogi="[^"]*")?( checked)?>', hv)
check([int(b[0]) for b in boxes if b[1]] == [A4] and 'name="gist" maxlength="200" value="적층도 변경으로 신규 가공 진행"' in hv, "수정 폼: 저장된 수주 체크 · 요지 채워짐", boxes)

CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (P2, NEW), data=dict(base, cust_req="38호기 MODIFY · 수정", note="", gist="가공 품목 변경", order_ids=[str(A2), str(A3), str(B1), str(AX)],
                                                                     _back="/project/%d/prod-request/edit?prid=%d" % (P2, NEW)))
with D.db_session() as c:
    rw = c.execute("SELECT order_ids, gist, updated_at FROM prod_requests WHERE id=?", (NEW,)).fetchone()
check(r.status_code == 303 and "prod_updated=1" in r.headers.get("location", "") and rw[0] == "%d,%d" % (A2, A3) and rw[1] == "가공 품목 변경",
      "수정발행: 수주 두 건으로 바꿈(남의 프로젝트 수주·취소 수주는 버림) · 요지 바꿈", (r.headers.get("location"), tuple(rw)))
check(CARDS and CARDS[0]["card"]["so_nos"] == ["T-260202-2", "T-260311-5"] and CARDS[0]["card"]["is_revision"] is True and "■ 요지 : 가공 품목 변경" in CARDS[0]["body"],
      "수정발행 이음 카드·글: 바뀐 수주번호 · 요지", CARDS and (CARDS[0]["card"].get("so_nos"), CARDS[0]["body"][:120]))
hv = q(cl.get, "/project/%d/prod-request/edit?prid=%d" % (P2, NEW)).text; rv = cells(hv, "")
check(rv[1] == "T-260202-2   T-260311-5".replace("   ", "  ") or rv[1].split() == ["T-260202-2", "T-260311-5"], "보기: 수주번호 두 줄", rv[1:3])
check(rv[2].split() == ["2호기", "3호기"], "보기: 호기 두 줄", rv[2])
check('class="z48-rev"' in hv and "수정발행" in hv, "수정발행 뒤 맨 위에 「무엇이 바뀌었나」 띠", re.findall(r'<div class="z48-rev">(.*?)</div>', hv)[:1])
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (P2, NEW), data=dict(base, cust_req="다시 수정", note="", gist="", _back="/project/%d/prod-request/edit?prid=%d" % (P2, NEW)))
with D.db_session() as c:
    rw = c.execute("SELECT order_ids, gist FROM prod_requests WHERE id=?", (NEW,)).fetchone()
with D.db_session() as c:
    cr = c.execute("SELECT cust_req FROM prod_requests WHERE id=?", (NEW,)).fetchone()[0]
check(r.status_code == 303 and "prod_need=pick" in r.headers.get("location", "") and "edit=1" in r.headers.get("location", "") and rw[0] == "%d,%d" % (A2, A3)
      and rw[1] == "가공 품목 변경" and cr == "38호기 MODIFY · 수정" and not CARDS,
      "수주를 하나도 안 고르고 수정발행 = 막힘(필수) · 아무것도 안 바뀜 · 통보 없음", (r.headers.get("location"), tuple(rw), cr, len(CARDS)))
hb = q(cl.get, r.headers["location"]).text
check('id="z48NeedMsg"' in hb and "수주번호를 하나 이상 골라야" in hb, "돌아온 화면에 막힌 까닭")
r = q(cl.post, "/project/%d/prod-request/%d/update" % (P2, NEW), data=dict(base, cust_req="다시 수정", note="", gist="", order_ids=[str(A2), str(A3)], _back="/project/%d/prod-request/edit?prid=%d" % (P2, NEW)))
with D.db_session() as c:
    rw = c.execute("SELECT order_ids, gist FROM prod_requests WHERE id=?", (NEW,)).fetchone()
check(not rw[1] and CARDS and "■ 요지" not in CARDS[0]["body"], "요지는 비우면 비워짐", tuple(rw))
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % P2, data=dict(base, cust_req="안 고르고 발행", note="", add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % P2))
with D.db_session() as c:
    n_after = c.execute("SELECT COUNT(*) FROM prod_requests WHERE project_id=?", (P2,)).fetchone()[0]
check(r.status_code == 303 and "prod_need=pick" in r.headers.get("location", "") and "new=1" in r.headers.get("location", "") and not CARDS and n_after == 2,
      "수주를 안 고르고 새 발행 = 막힘(필수) · 요청서 안 생김 · 통보 없음", (r.headers.get("location"), len(CARDS), n_after))
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/new" % P3, data=dict(base, cust_req="수주 없는 관리번호", note="", add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % P3))
with D.db_session() as c:
    n3 = c.execute("SELECT COUNT(*) FROM prod_requests WHERE project_id=?", (P3,)).fetchone()[0]
check("prod_need=order" in r.headers.get("location", "") and not CARDS and n3 == 1, "수주가 없는 관리번호 = 발행 못 함(수주번호 필수)", (r.headers.get("location"), n3))
r = q(cl.post, "/project/%d/prod-request/new" % P5, data=dict(base, cust_req="관리번호 없음", note="", order_ids=[str(E1)], add_team_ids=[str(TEAM)], _back="/project/%d/prod-request/edit" % P5))
check("prod_need=mgmt" in r.headers.get("location", "") and not CARDS, "관리번호가 없는 프로젝트 = 발행 못 함(관리번호 필수)", r.headers.get("location"))
with contextlib.redirect_stdout(io.StringIO()):
    res3 = M._prod_request_notify_core(P3, "다른 길로 들어옴", "", [TEAM], ADMIN)
    res5 = M._prod_request_notify_core(P5, "다른 길로 들어옴", "", [TEAM], ADMIN)
with D.db_session() as c:
    n3b = c.execute("SELECT COUNT(*) FROM prod_requests WHERE project_id IN (?,?)", (P3, P5)).fetchone()[0]
check(res3 == {"ok": False, "error": "need_mgmt_order", "need": "order"} and res5.get("need") == "mgmt" and not CARDS and n3b == 1,
      "등록하면서 발행·추가 발주 같은 다른 길도 통보 코어에서 막힘(저장·통보 없음)", (res3, res5, n3b))
hd = q(cl.get, "/project/%d?prod_need=order" % P3).text
check("제작요청서를 발행하지 못했습니다" in hd and "수주번호는 필수" in hd, "프로젝트 화면에 막힌 까닭")
CARDS.clear()
with contextlib.redirect_stdout(io.StringIO()):
    res = M._prod_request_notify_core(P4, "등록하면서 발행", "", [TEAM], ADMIN)
with D.db_session() as c:
    rw = c.execute("SELECT order_ids, COALESCE(gist,'') FROM prod_requests WHERE id=?", (res.get("pr_id"),)).fetchone()
check(res.get("ok") and rw and rw[0] == str(B1) and rw[1] == "" and CARDS[0]["card"]["so_nos"] == ["T-261117-1"], "등록 화면에서 발행(옛 부르는 방식 그대로) = 그때의 최근 수주가 저장됨", (res.get("ok"), rw and tuple(rw)))
CARDS.clear()
r = q(cl.post, "/project/%d/prod-request/%d/update" % (P1, L1), data=dict(base, cust_req="옛 요청서 수정", note="", _back="/project/%d/prod-request/edit?prid=%d" % (P1, L1),
                                                                    server_path="Z:\\가상고객\\TSP\\VPL-1\\9. 제품자료", engraving="VPL-1 FUNCTION TESTER", order_ids=[str(O1)]))
check(r.status_code == 303 and "prod_updated=1" in r.headers.get("location", "") and CARDS and CARDS[0]["card"]["so_nos"] == ["T-261113-5"], "옛 요청서 수정발행도 정상", r.headers.get("location"))

print("§4 소모품 요청서 = 종이 양식")
r = q(cl.get, "/consumables/%d/prod-request" % CO1); hc = r.text
pc = hc[hc.find('<div id="z48Paper">'):hc.find('<div class="z48-mob">')]
check(r.status_code == 200 and 'class="z48-tt">소모품 요청서</td>' in pc, "종이 양식 표 + 제목")
check('<td class="z48-hk">관리번호</td><td class="z48-mgc">010 C 2611</td><td class="z48-h">수주번호</td><td class="z48-so">C-261117-1</td>' in pc, "머리에 관리번호·수주번호 한 쌍")
check(">고객사</td><td>가상고객 인도</td>" in pc and ">작성자</td><td>가상관리자" in pc and ">고객사 담당자</td><td>Rohan</td>" in pc and ">내용</td><td>인도 소모품 3종</td>" in pc, "머리: 고객사·작성자·담당자·내용")
hdr = re.findall(r'<td class="z48-h"[^>]*>([^<]+)</td>', pc[pc.find(">NO.<") - 20:pc.find(">요청사항<")])
check(hdr == ["NO.", "사진", "모델명", "품명", "수량", "납기", "연결 장비"], "품목 표 머리(사진·연결 장비 줄이 있을 때)", hdr)
check('<span class="z48-pn">PCB</span>KNK-P-4963' in pc and ">SM-S956</td>" in pc and 'class="z48-mgc" style="font-size:12.5px;">020T2611</td>' in pc and "2 EA" in pc and pc.count(">%s</td>" % FUT) == 3,
      "품목 줄: 모델명 · 품명(종류+규격) · 수량 · 납기 · 연결 장비")
check('data-knk-zoom data-knk-name="KNK-P-4963 사진"' in pc and "z48-thumb" in pc, "줄 사진 — 눌러서 크게")
check(pc.count('class="z48-copy"') == 2 and 'data-copy="Z:\\가상\\제조\\SM-S956\\1. 013T2606_기능검사기"' in pc and "납품 전 연락" in pc, "요청사항: 줄마다 · 경로에는 「복사」(경로 아닌 줄엔 없음)")
m2 = _z65_meta(pc, "사업부")   # z1191z65
check(m2 and m2.split()[0] == "📦" and "D-10" in (_z65_meta(pc, "납기") or "") and _z65_meta(pc, "발주일") == "2026-11-17" and 'class="z48-kv"' not in pc,
      "맨 아래 정보 = 칸(사업부 📦 · 발주일 · 납기 + 남은 날)", m2)
check('<div class="z48-mob">' in hc and "@media print" in hc and 'onclick="window.print()"' in hc and "window.z48Copy" in hc, "휴대폰 카드 · 인쇄 · 복사 스크립트")
hc2 = q(cl.get, "/consumables/%d/prod-request" % CO2).text
pc2 = hc2[hc2.find('<div id="z48Paper">'):hc2.find('<div class="z48-mob">')]
hdr2 = re.findall(r'<td class="z48-h"[^>]*>([^<]+)</td>', pc2[pc2.find(">NO.<") - 20:pc2.find(">요청사항<")])
check(hdr2 == ["NO.", "모델명", "품명", "수량", "납기"] and ">9월 소모품(1종)</td>" in pc2 and ">ON 2,3,4 FRC</td>" in pc2 and "D-" not in pc2,
      "사진·연결 장비가 없는 수주 = 그 칸 없음 · 내용 자동(「9월 소모품(1종)」) · 줄 모델이 비면 수주의 모델명", hdr2)
check("가격" not in pc and "1,000" not in pc and "1000" not in pc, "금액 없음")
check(".z48-prs td.z48-so" in hc and ".z48-prs td.z48-mgc" in hc, "수주번호·관리번호 글자색이 표 안에서도 먹음(표 칸 규칙에 안 눌림)")

CARDS.clear()
with D.db_session() as c:   # 기동할 때 빈 관리번호는 자동으로 채워진다(운영에는 빈 것이 없음) → 막는 자리만 따로 시험하려고 다시 비움
    c.execute("UPDATE consumable_orders SET mgmt_code='' WHERE id=?", (CO3,))
rj = q(cl.post, "/consumables/%d/notify" % CO3, json={"team_ids": [TEAM], "user_ids": []})
check(rj.status_code == 400 and rj.json().get("error") == "need_mgmt_order" and "필수" in rj.json().get("message", "") and not CARDS, "소모품: 관리번호가 없으면 요청서 발행 못 함(필수)", (rj.status_code, rj.text[:120]))
CARDS.clear()
rj = q(cl.post, "/consumables/%d/notify" % CO1, json={"team_ids": [TEAM], "user_ids": []})
check(rj.status_code == 200 and rj.json().get("ok") and CARDS and CARDS[0]["card"]["so_nos"] == ["C-261117-1"] and CARDS[0]["card"]["mgmt"] == "010C2611", "소모품: 둘 다 있으면 지금처럼 발행 · 카드에 관리번호·수주번호", (rj.status_code, rj.text[:160]))

print("§5 다른 화면은 그대로")
for u in ("/prod-requests", "/project/%d" % P1, "/consumables/%d" % CO1):
    rr = q(cl.get, u)
    check(rr.status_code == 200, "%s 열림" % u, rr.status_code)

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
