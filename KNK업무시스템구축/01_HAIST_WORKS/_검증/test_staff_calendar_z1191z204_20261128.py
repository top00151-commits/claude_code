# -*- coding: utf-8 -*-
"""z1191z204 시험 — 웍스 명단·달력 기준 맞춤(대표 2026-11-28 「진행해」 · 스킬 knk-staff-list · knk-calendar)
  §1 본사/베트남법인 판정 = 부서(부서 코드 02_VN/ → 팀 → 사람) · 팀 번호 12 고정 없음
  §2 공용 명단 staff_pick_rows: 본사 먼저 · 00_총괄 맨 앞 · 부서 순 · 「이름 직책 · 부서」 · 베트남 「원래 이름 (부르는 이름)」 · 잠긴 계정 뺌(지금 담당은 남김)
  §3 담당자 칸 = 공용 조각(data-knk-staff · 🇰🇷 본사 / 🇻🇳 베트남법인 묶음) — AS 접수·상세 · 일 시키기 · 팀장 · QA 매니저 · 부서 요청 · 일 순서 단계
      · 저장 값 = 사용자 번호 그대로(AS 접수 → 다시 열어 같은 번호 · 베트남 직원 · 잠긴 담당은 그대로 남음)
  §4 기존 책갈피 고르기(_knk_picker): 「🇰🇷 본사 / 🇻🇳 베트남법인」 · 숫자 = 전체 인원 · 관리자 사용자 목록 법인 = 부서 기준
  §5 월간 달력: 「다가오는 날」 베트남 휴일도 빨강·K/V 표시 · 칸 안 휴일 이름 한국·베트남 · 안내문 국기 그림 없음 · 일정표 오늘 = 호박색
  §6 웍스 달력(KnkCal): 머리 「📅 YYYY.MM」 + 「← 오늘 →」 · 월 칸·날짜시각 칸에도 붙음 · 값 모양 그대로(YYYY-MM · YYYY-MM-DDTHH:MM)
  §7 화면에서 실제로 눌러 보기(크롬 · 바깥 연결 막음): 고르기 창 → 베트남법인 책갈피 → 사람 → 셀렉트 값 = 번호 · 초성 검색 · ✕ 닫기 · 월 고르기 · 날짜시각
  임시 DB · TestClient · 운영 아님"""
import contextlib
import io
import os
import re
import sys
import tempfile
from datetime import date, timedelta

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z204-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z204_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("rank", "TEXT")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
    if "entity" not in tcols:
        conn.execute("ALTER TABLE teams ADD COLUMN entity TEXT")

    def team(code, name, ent):
        conn.execute("INSERT INTO teams (code, name, entity) VALUES (?, ?, ?)", (code, name, ent))
        return conn.execute("SELECT id FROM teams WHERE code=?", (code,)).fetchone()[0]
    TK0 = team("Z00", "가상총괄", "KOR")
    TK1 = team("Z01", "가상영업팀", "KOR")
    TV4 = team("ZV4", "가상가공팀", "VN")
    TVX = team("ZVX", "가상법인팀", "VN")
    ins = ("INSERT INTO users (name, name_vi, rank, role, employee_no, login_id, password, is_active, password_version, team_id, dept_code, entity, "
           "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics, can_use_quality) "
           "VALUES (?, ?, ?, ?, ?, ?, 'sso_only_no_local_password', ?, 1, ?, ?, ?, 1, 1, 1, 1, 1)")
    conn.execute(ins, ("가상대표", None, "대표", "admin", "Z9001", "Z9001", 1, TK0, "01_KOR/00_총괄", "KOR"))
    conn.execute(ins, ("가상영업", None, "프로", "member", "Z9002", "Z9002", 1, TK1, "01_KOR/01_가상영업팀", "KOR"))
    conn.execute(ins, ("가상다른영업", None, "과장", "member", "Z9003", "Z9003", 1, TK1, "01_KOR/01_가상영업팀", "KOR"))
    conn.execute(ins, ("카이", "Nguyễn Văn Khải", "Staff", "member", "VN9004", "VN9004", 1, TV4, "02_VN/04_가상가공팀", "VN"))
    conn.execute(ins, ("가상부서코드없음", None, "", "member", "VN9005", "VN9005", 1, TVX, "", None))   # 부서 코드 없음 → 팀(VN)
    conn.execute(ins, ("가상팀어긋남", None, "", "member", "VN9006", "VN9006", 1, TK1, "02_VN/04_가상가공팀", "KOR"))   # 부서 코드가 기준
    conn.execute(ins, ("가상퇴사", None, "프로", "member", "Z9007", "Z9007", 0, TK1, "01_KOR/01_가상영업팀", "KOR"))
    UID = {r[1]: r[0] for r in conn.execute("SELECT id, employee_no FROM users WHERE employee_no LIKE 'Z9%' OR employee_no LIKE 'VN9%'")}
    BOSS = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z9001'").fetchone())

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: BOSS
cl = TestClient(M.app, follow_redirects=False)
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:400]))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def get(url):
    r = q(cl.get, url)
    return r.status_code, r.text


def staff_sel(html, name):
    m = re.search(r'<select[^>]*name="%s"[^>]*>(.*?)</select>' % re.escape(name), html, re.S) or \
        re.search(r'<select[^>]*id="%s"[^>]*>(.*?)</select>' % re.escape(name), html, re.S)
    return (m.group(0) if m else "")


def tag_of(html, name):
    m = re.search(r'<select[^>]*(?:name|id)="%s"[^>]*>' % re.escape(name), html)
    return m.group(0) if m else ""


SRC = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
WFB = open(os.path.join(ROOT, "app", "workflow_builder.py"), encoding="utf-8").read()
TPL = os.path.join(ROOT, "app", "templates")


def tpl(rel):
    return open(os.path.join(TPL, *rel.split("/")), encoding="utf-8").read()


# ───────────────────────────────────────────────────────────────
print("§1 본사/베트남법인 판정 = 부서")
sc = getattr(M, "staff_corp", None)
check("공용 판정 staff_corp 가 있다", callable(sc))
if callable(sc):
    check("부서 코드 02_VN/ → 베트남법인(팀이 본사로 잘못 돼 있어도)", sc({"dept_code": "02_VN/04_가공팀", "team_entity": "KOR"}) == "VN")
    check("부서 코드 01_KOR/ → 본사(팀이 VN 이어도)", sc({"dept_code": "01_KOR/04_설계팀", "team_entity": "VN"}) == "KOR")
    check("부서 코드 없음 → 팀 법인(VN)", sc({"dept_code": "", "team_entity": "VN"}) == "VN")
    check("팀도 없음 → 사람 법인(VN)", sc({"dept_code": None, "team_entity": None, "entity": "VN"}) == "VN")
    check("팀 번호 12 라는 것만으로 베트남이 되지 않음(번호 고정 없음)", sc({"team_id": 12, "dept_code": "01_KOR/00_총괄", "team_entity": "KOR"}) == "KOR")
check("관리자 사용자 목록·권한 화면·직원 목록에 팀 번호 12 고정이 없다",
      "u.team_id==12" not in tpl("admin.html") and 'd.get("team_id") == 12' not in SRC
      and 'row.get("team_id") == 12' not in open(os.path.join(ROOT, "app", "admin_people.py"), encoding="utf-8").read())

print("§2 공용 명단")
rows = []
if hasattr(M, "staff_pick_rows"):
    with D.db_session() as c:
        rows = M.staff_pick_rows(c)
        rows_inc = M.staff_pick_rows(c, include_ids=[UID["Z9007"]])
mine = [r for r in rows if r["id"] in UID.values()]
check("공용 명단 staff_pick_rows 가 있다", bool(rows))
if rows:
    corps = [r["corp"] for r in rows]
    check("본사가 먼저 · 베트남법인이 뒤(섞이지 않음)", corps == sorted(corps, key=lambda x: 0 if x == "KOR" else 1), corps)
    kor = [r for r in rows if r["corp"] == "KOR"]
    check("00_총괄이 본사 맨 앞", kor and kor[0]["dkey"].startswith("01_KOR/00_"), kor[:1])
    dk = [r["dkey"] for r in rows if r["corp"] == "KOR"]
    check("부서 순(부서 코드 순)", dk == sorted(dk), dk)
    by = {r["id"]: r for r in rows}
    k = by.get(UID["VN9004"], {})
    check("베트남 직원 이름 = 「원래 이름 (부르는 이름)」 · 직책 · 부서", k.get("disp") == "Nguyễn Văn Khải (카이)" and k.get("sub") == "Staff · 가상가공팀"
          and k.get("label") == "Nguyễn Văn Khải (카이) Staff · 가상가공팀", k)
    check("본사 직원 = 「이름 직책 · 부서」", by.get(UID["Z9002"], {}).get("label") == "가상영업 프로 · 가상영업팀", by.get(UID["Z9002"]))
    check("부서 코드 없는 사람 = 팀 법인으로 베트남법인", by.get(UID["VN9005"], {}).get("corp") == "VN")
    check("팀이 본사여도 부서 코드 02_VN/ 이면 베트남법인", by.get(UID["VN9006"], {}).get("corp") == "VN")
    check("잠긴(퇴사) 계정은 명단에 없음", UID["Z9007"] not in by)
    inc = {r["id"]: r for r in rows_inc}
    check("지금 담당이면 잠긴 계정도 남음(표시 「잠긴 계정」)", UID["Z9007"] in inc and inc[UID["Z9007"]]["inactive"] and "잠긴 계정" in inc[UID["Z9007"]]["label"])
    check("값 = 사용자 번호(정수)", all(isinstance(r["id"], int) for r in rows))

# ───────────────────────────────────────────────────────────────
print("§3 담당자 칸 = 공용 조각 · 저장 값 = 번호")
st, h = get("/as/new")
s = staff_sel(h, "assignee_id")
check("AS 접수 화면 열림", st == 200, st)
check("AS 접수 담당자 = data-knk-staff", "data-knk-staff" in tag_of(h, "assignee_id"), tag_of(h, "assignee_id"))
check("AS 접수 담당자 = 🇰🇷 본사 / 🇻🇳 베트남법인 묶음", '<optgroup label="🇰🇷 본사">' in s and '<optgroup label="🇻🇳 베트남법인">' in s, s[:300])
check("AS 접수 담당자 옵션 = 「이름 직책 · 부서」 · 베트남 이름", ">가상영업 프로 · 가상영업팀<" in s and ">Nguyễn Văn Khải (카이) Staff · 가상가공팀<" in s, s[:600])
vn_pos = s.find('label="🇻🇳 베트남법인"')
check("베트남 직원은 베트남법인 묶음 안", vn_pos > 0 and s.find('value="%d"' % UID["VN9004"]) > vn_pos)
check("고르기 창 공용 조각(KNKPicker.staff)이 화면에 실림", "KNKPicker.staff" in h and "staffEnhance" in h)
r = q(cl.post, "/as/new", data={"customer_name": "가상고객", "received_date": date.today().isoformat(), "assignee_id": str(UID["VN9004"])})
loc = r.headers.get("location", "")
aid = int(re.findall(r"/as/(\d+)", loc)[0]) if re.findall(r"/as/(\d+)", loc) else 0
with D.db_session() as c:
    saved = c.execute("SELECT assignee_id FROM as_tickets WHERE id=?", (aid,)).fetchone() if aid else None
check("AS 접수 저장 → 베트남 직원 번호 그대로", saved and saved[0] == UID["VN9004"], (loc, saved))
st, h = get("/as/%d" % aid) if aid else (0, "")
s = staff_sel(h, "assignee_id")
check("AS 상세 다시 열기 → 같은 사람이 고른 상태", re.search(r'value="%d"[^>]*selected' % UID["VN9004"], s) is not None, s[:400])
with D.db_session() as c:
    c.execute("UPDATE as_tickets SET assignee_id=? WHERE id=?", (UID["Z9007"], aid))
st, h = get("/as/%d" % aid)
s = staff_sel(h, "assignee_id")
check("AS 상세: 지금 담당이 잠긴 계정이어도 목록에 남고 고른 상태(저장 때 말없이 안 지워짐)",
      re.search(r'value="%d"[^>]*selected' % UID["Z9007"], s) is not None, s[:400])
r = q(cl.post, "/as/%d/edit" % aid, data={"assignee_id": str(UID["Z9002"]), "note": "x"})
with D.db_session() as c:
    saved = c.execute("SELECT assignee_id FROM as_tickets WHERE id=?", (aid,)).fetchone()
check("AS 상세에서 담당 바꿔 저장 → 새 번호", saved and saved[0] == UID["Z9002"], saved)

st, h = get("/daily")
check("일 시키기(받을 사람) = data-knk-staff · 본사/베트남법인 묶음 · 나 빼고",
      st == 200 and "data-knk-staff" in tag_of(h, "woUser") and "🇻🇳 베트남법인" in staff_sel(h, "woUser")
      and ('value="%d"' % BOSS["id"]) not in staff_sel(h, "woUser"), (st, staff_sel(h, "woUser")[:300]))
st, h = get("/admin/teams/new")
s = staff_sel(h, "leader_id")
check("팀장 고르기 = data-knk-staff · 「이름 직책 · 부서」", st == 200 and "data-knk-staff" in tag_of(h, "leader_id") and ">가상영업 프로 · 가상영업팀<" in s, (st, s[:300]))
check("팀장 고르기 = 역할 조건 그대로(관리자 계정 빠짐)", ('value="%d"' % BOSS["id"]) not in s)
st, h = get("/qc/inspection-reports/new")
s = staff_sel(h, "qa_manager_id")
check("QA 매니저 고르기 칸에 명단이 들어감(예전엔 늘 빈 칸)", st == 200 and "data-knk-staff" in tag_of(h, "qa_manager_id") and ('value="%d"' % UID["Z9002"]) in s, (st, s[:300]))
dr = tpl("dept_requests.html")
check("부서 요청 구성원 추가 = 공용 조각(staff_options · data-knk-staff · 고르기 창)",
      "staff_options(all_users" in dr and 'name="user_id" required data-knk-staff' in dr and '{% include "_knk_picker.html" %}' in dr)
nd = tpl("workflow/node_detail.html")
check("일 순서 단계 담당 = 공용 조각 · 300명 잘림 없음",
      'id="userSel" data-knk-staff' in nd and "staff_pick_rows" in WFB and "ORDER BY name LIMIT 300" not in WFB)
try:
    mac = M.tpl.env.get_template("_v5_partials/knk_staff_pick.html").module.staff_options
    with D.db_session() as c:
        out = str(mac(M.staff_pick_rows(c), UID["VN9004"], "— 구성원 추가 —"))
except Exception as _e:   # 원래 판엔 공용 조각이 없다
    out = "없음: %s" % _e
check("공용 조각 staff_options: 빈 값 첫 줄 · 고른 사람 selected · data-corp", out.startswith('<option value="">— 구성원 추가 —</option>')
      and re.search(r'value="%d" data-corp="VN"[^>]*selected' % UID["VN9004"], out) is not None, out[:300])
check("AS·일 시키기·부서 요청 서버 = 공용 명단 하나(staff_pick_rows)",
      "return staff_pick_rows(c, include_ids=include_ids)" in SRC and "wo_users = staff_pick_rows(c2" in SRC and "all_users = staff_pick_rows(c)" in SRC)

# ───────────────────────────────────────────────────────────────
print("§4 기존 책갈피 고르기 · 관리자 목록")
kp = tpl("_knk_picker.html")
check("책갈피 이름 = 「🇰🇷 본사」「🇻🇳 베트남법인」(화면마다 다른 🏢/🌏 글자 덮음)", '"🇰🇷 본사"' in kp and '"🇻🇳 베트남법인"' in kp)
check("책갈피 숫자 = 그 책갈피 전체 인원(totalOf) · 고른 수는 따로 ✓N", "function totalOf(p)" in kp and "knkp-tab-n" in kp and "✓' + chk" in kp)
check("고른 책갈피 = 진한 회사 색 바탕 + 흰 글씨", ".knkp-tab.active{background:var(--knk-action);color:var(--knk-text-inverse)" in kp)
st, h = get("/admin/console")
m = re.search(r'<tr class="urow" data-corp="([^"]+)"[^>]*>(?:(?!</tr>).)*?VN9006', h, re.S)
check("관리자 사용자 목록: 팀이 본사여도 부서 코드 02_VN/ 이면 베트남법인", st == 200 and m and m.group(1) == "베트남법인", (st, m.group(1) if m else None))

# ───────────────────────────────────────────────────────────────
print("§5 월간 달력 · 일정표 오늘")
today = date.today()
tgt = None
for i in range(1, 7):
    d = today + timedelta(days=i)
    if d.weekday() < 5 and not M.HOLIDAYS_KR.get(d.isoformat()) and not M.HOLIDAYS_VN.get(d.isoformat()):
        tgt = d
        break
_saved = M.HOLIDAYS_VN.get(tgt.isoformat()) if tgt else None
if tgt:
    M.HOLIDAYS_VN[tgt.isoformat()] = "시험베트남휴일"
    try:
        st, h = get("/calendar")
    finally:
        M.HOLIDAYS_VN.pop(tgt.isoformat(), None)
    m = re.search(r'<a href="/daily/%s"\s+class="upcoming-item[^"]*">(.*?)</a>' % tgt.isoformat(), h, re.S)
    blk = m.group(1) if m else ""
    check("다가오는 날: 베트남 휴일(평일)도 날짜 빨강", re.search(r'<div class="day sun">%d</div>' % tgt.day, blk) is not None, blk[:300])
    check("다가오는 날: 베트남 휴일 = 주황 「V」 표시 · 국기 그림 없음", ">V</span>" in blk and "🇻🇳" not in blk, blk[:400])
st, h = get("/calendar/2027-02")
grid = h.split('data-dn="cal-grid"', 1)[-1].split('data-dn="cal-upcoming"', 1)[0]
check("달력 칸 안 휴일 이름 = 베트남 휴일 이름도(hol-name vn)", st == 200 and 'class="hol-name vn"' in grid, st)
check("달력 마우스 안내문 = 국기 그림 없음 · 「베트남 공휴일:」", "🇰🇷" not in grid and "🇻🇳" not in grid and "베트남 공휴일:" in grid)
check("수주 달력·옛 수주 달력 조각 안내문에도 국기 그림 없음",
      "· 🇰🇷 {{ d.hol_kr }}" not in tpl("sales_orders.html") and "· 🇰🇷 {{ d.hol_kr }}" not in tpl("_v5_partials/so_calendar.html"))
css = open(os.path.join(ROOT, "static", "css", "schedule_board.css"), encoding="utf-8").read()
ds = tpl("dept_schedule.html")
check("작업일정표 오늘 = 호박색 테두리(빨강 아님)",
      ".sched .day.today { box-shadow: inset 2px 0 0 #d4a574, inset -2px 0 0 #d4a574;" in css and "today { box-shadow: inset 2px 0 0 #b91c1c" not in css
      and "border-left:2px solid #b91c1c" not in css)
check("전사일정표 오늘 = 호박색 테두리", ".dsx td.day.today,.dsx th.day.today{box-shadow:inset 2px 0 0 #d4a574" in ds)

# ───────────────────────────────────────────────────────────────
print("§6 웍스 달력(KnkCal)")
kc = tpl("_v5_partials/knk_datepicker.html")
check("머리 = 「📅 YYYY.MM」", "'📅 ' + viewY + '.' + pad2(viewM + 1)" in kc)
check("단추 = 「← 오늘 →」", '>←</button>' in kc and '>오늘</button>' in kc and '>→</button>' in kc and '>●</button>' not in kc)
check("월 칸·날짜시각 칸 모드(값 모양 그대로)", "_knkCalMode = (_ot === 'month') ? 'month'" in kc and "v + 'T' + tm.value" in kc)
st, h = get("/issues/new")
check("이슈 발생일시 = 웍스 달력(class knk-cal)", st == 200 and re.search(r'<input type="datetime-local" name="occurred_at" class="knk-cal">', h) is not None, st)
st, h = get("/sales/opportunities/new")
check("영업 기회 예상 수주월 = 웍스 달력(class knk-cal)", 'type="month" class="knk-cal" name="expected_order_ym"' in h, st)
check("수주 달력 빠른 이동·입출금 월 = 웍스 달력", 'type="month" class="knk-cal" value="{{ _nav.current }}"' in tpl("sales_orders.html")
      and 'type="month" class="knk-cal" id="srDMonth"' in tpl("sales_shipments_receipts.html"))
check("세션 15 메일 날짜시각 칸은 그대로(자동으로 안 붙음 — class 단 칸만)", "input.knk-cal, input[type=\"date\"]" in kc and "input[type=\"month\"]" not in kc)

# ───────────────────────────────────────────────────────────────
print("§7 화면에서 실제로 눌러 보기(크롬 · 바깥 연결 막음)")
# 크롬 시험 도구(playwright)는 이 PC 에서 파이썬 3.12 쪽에만 있어, 그려진 화면을 파일로 넘기고 그쪽에서 누른다.
import json  # noqa: E402
import subprocess  # noqa: E402
_BROWSER = r'''
import json, re, sys
from playwright.sync_api import sync_playwright
a = json.loads(open(sys.argv[1], encoding="utf-8").read())
o = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    errs = []
    def newpg():   # 화면마다 새 창(앞 화면 전역 값이 남지 않게)
        q = b.new_page(viewport={"width": 1440, "height": 900})
        q.route("**/*", lambda route: route.abort())
        q.on("pageerror", lambda e: errs.append(str(e)))
        return q
    pg = newpg()
    pg.set_content(open(a["as"], encoding="utf-8").read(), wait_until="domcontentloaded"); pg.wait_for_timeout(300)
    btn = pg.locator('.knks-btn[data-for-name="assignee_id"]')
    o["btn_n"] = btn.count(); o["btn0"] = btn.inner_text() if btn.count() else ""
    btn.click(); pg.wait_for_timeout(150)
    o["tabs"] = pg.locator(".knks-pop .knkp-tab").all_inner_texts()
    o["heads"] = pg.locator(".knks-pop .knks-dh").all_inner_texts()
    o["x"] = pg.locator(".knks-pop .knks-x").inner_text().strip()
    pg.locator('.knks-pop .knkp-tab[data-tab="VN"]').click(); pg.wait_for_timeout(100)
    pg.locator('.knks-pop .knks-row[data-v="%d"]' % a["vn"]).click(); pg.wait_for_timeout(100)
    o["v1"] = pg.eval_on_selector('select[name="assignee_id"]', "e=>e.value"); o["btn1"] = btn.inner_text()
    o["closed1"] = pg.locator(".knks-pop").get_attribute("hidden") is not None
    btn.click(); pg.wait_for_timeout(100)
    o["reopen_tab"] = pg.locator('.knks-pop .knkp-tab[data-tab="VN"]').get_attribute("class") or ""
    pg.locator('.knks-pop .knkp-tab[data-tab="KOR"]').click()
    pg.fill(".knks-pop .knks-q", "ㄱㅅㄷㄹ"); pg.wait_for_timeout(100)
    o["vis"] = pg.locator(".knks-pop .knks-row[data-d]:not([hidden]) .nm").all_inner_texts()
    pg.keyboard.press("Enter"); pg.wait_for_timeout(100)
    o["v2"] = pg.eval_on_selector('select[name="assignee_id"]', "e=>e.value")
    btn.click(); pg.wait_for_timeout(100)
    pg.locator(".knks-pop .knks-x").click(); pg.wait_for_timeout(100)
    o["closed2"] = pg.locator(".knks-pop").get_attribute("hidden") is not None
    o["v3"] = pg.eval_on_selector('select[name="assignee_id"]', "e=>e.value")
    btn.click(); pg.wait_for_timeout(100)
    pg.locator(".knks-pop .knks-none").click(); pg.wait_for_timeout(100)
    o["v4"] = pg.eval_on_selector('select[name="assignee_id"]', "e=>e.value")
    o["fd"] = pg.evaluate("()=>{const s=document.querySelector('select[name=assignee_id]'); s.value='%d'; return new FormData(s.form).get('assignee_id');}" % a["vn"])
    pg = newpg()
    pg.set_content(open(a["is"], encoding="utf-8").read(), wait_until="domcontentloaded"); pg.wait_for_timeout(300)
    pg.click('input[name="occurred_at"]'); pg.wait_for_timeout(150)
    o["cal_ttl"] = pg.locator(".knk-cal-pop .head .title").inner_text()
    o["cal_nav"] = pg.locator(".knk-cal-pop .head .nav button").all_inner_texts()
    o["tline"] = pg.locator(".knk-cal-pop .tline").is_visible()
    pg.locator(".knk-cal-pop [data-time]").fill("14:30")
    pg.locator(".knk-cal-pop .day:not(.out)").nth(9).click(); pg.wait_for_timeout(100)
    o["dt"] = pg.eval_on_selector('input[name="occurred_at"]', "e=>e.value")
    pg.locator(".knk-cal-pop [data-act=close]").click()
    pg = newpg()
    pg.set_content(open(a["op"], encoding="utf-8").read(), wait_until="domcontentloaded"); pg.wait_for_timeout(300)
    pg.click('input[name="expected_order_ym"]'); pg.wait_for_timeout(150)
    o["mon_ttl"] = pg.locator(".knk-cal-pop .head .title").inner_text()
    o["mon_n"] = pg.locator(".knk-cal-pop .mon").count()
    o["tline_mon"] = pg.locator(".knk-cal-pop .tline").is_visible()
    pg.locator(".knk-cal-pop [data-act=next]").click()
    pg.locator('.knk-cal-pop .mon[data-ym$="-03"]').click(); pg.wait_for_timeout(100)
    o["ym"] = pg.eval_on_selector('input[name="expected_order_ym"]', "e=>e.value")
    o["errs"] = [e for e in errs if ("knks" in e or "KnkCal" in e or "staff" in e.lower() or "knk-cal" in e)]
    b.close()
print("@@" + json.dumps(o, ensure_ascii=False))
'''


def _py_with_playwright():
    cands = [sys.executable, os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "Python", "Python312", "python.exe")]
    for py in cands:
        if os.path.exists(py) and subprocess.run([py, "-c", "import playwright.sync_api"], capture_output=True).returncode == 0:
            return py
    return None


PYB = _py_with_playwright()
check("크롬 시험 도구(playwright)가 있는 파이썬 찾음", PYB is not None)
if PYB:
    files = {}
    for k, url in (("as", "/as/new"), ("is", "/issues/new"), ("op", "/sales/opportunities/new")):
        fp = os.path.join(TMP, "z204_%s.html" % k)
        open(fp, "w", encoding="utf-8").write(get(url)[1])
        files[k] = fp
    files["vn"] = UID["VN9004"]
    arg = os.path.join(TMP, "z204_args.json"); open(arg, "w", encoding="utf-8").write(json.dumps(files))
    scr = os.path.join(TMP, "z204_browser.py"); open(scr, "w", encoding="utf-8").write(_BROWSER)
    pr = subprocess.run([PYB, scr, arg], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    mm = re.search(r"^@@(.*)$", pr.stdout or "", re.M)
    o = json.loads(mm.group(1)) if mm else {}
    check("크롬에서 화면 열고 누르기 끝까지 돎", bool(o), (pr.stdout or "")[-300:] + (pr.stderr or "")[-600:])
    if o:
        nk = sum(1 for r in rows if r["corp"] == "KOR"); nv = sum(1 for r in rows if r["corp"] == "VN")
        tabs = o["tabs"]
        check("AS 접수: 담당자 칸 = 고르기 단추(처음 「— 선택 —」)", o["btn_n"] == 1 and "— 선택 —" in o["btn0"], o["btn0"])
        check("고르기 창 책갈피 = 「🇰🇷 본사 N」「🇻🇳 베트남법인 N」(수 = 실제 인원)",
              len(tabs) == 2 and "🇰🇷 본사" in tabs[0] and "🇻🇳 베트남법인" in tabs[1] and [t.split()[-1] for t in tabs] == [str(nk), str(nv)], (tabs, nk, nv))
        check("본사 책갈피 부서 머리 = 00_총괄 맨 앞", o["heads"][:1] == ["가상총괄"], o["heads"])
        check("창 안 「✕ 닫기」", o["x"] == "✕ 닫기", o["x"])
        check("베트남법인 책갈피 → 카이 → 셀렉트 값 = 그 사람 번호", o["v1"] == str(UID["VN9004"]), o["v1"])
        check("단추 글 = 「Nguyễn Văn Khải (카이)」 + 「Staff · 가상가공팀」", "Nguyễn Văn Khải (카이)" in o["btn1"] and "Staff · 가상가공팀" in o["btn1"], o["btn1"])
        check("고른 뒤 창 닫힘", o["closed1"])
        check("다시 열면 고른 사람 책갈피(베트남법인)로 열림", "active" in o["reopen_tab"], o["reopen_tab"])
        check("초성 「ㄱㅅㄷㄹ」 → 보이는 책갈피 안에서 가상다른영업만", o["vis"] == ["가상다른영업"], o["vis"])
        check("검색 칸 Enter → 첫 사람 고름", o["v2"] == str(UID["Z9003"]), o["v2"])
        check("✕ 닫기 → 창 닫힘 · 값 그대로", o["closed2"] and o["v3"] == str(UID["Z9003"]), (o["closed2"], o["v3"]))
        check("「— 선택 —」 줄 → 담당 비움", o["v4"] == "", o["v4"])
        check("양식으로 보내는 값 = assignee_id=번호(이름·모양 그대로)", o["fd"] == str(UID["VN9004"]), o["fd"])
        check("달력 머리 = 「📅 YYYY.MM」 · 「← 오늘 →」", re.fullmatch(r"📅 \d{4}\.\d{2}", o["cal_ttl"]) is not None and o["cal_nav"] == ["←", "오늘", "→"], (o["cal_ttl"], o["cal_nav"]))
        check("날짜시각 칸 = 시각 줄 보임", o["tline"])
        check("날짜 누름 → 값 = YYYY-MM-10T14:30(예전 datetime-local 과 같은 모양)", re.fullmatch(r"\d{4}-\d{2}-10T14:30", o["dt"] or "") is not None, o["dt"])
        check("월 칸 = 12달 고르기(머리 「📅 YYYY」) · 시각 줄 없음", re.fullmatch(r"📅 \d{4}", o["mon_ttl"]) is not None and o["mon_n"] == 12 and not o["tline_mon"], (o["mon_ttl"], o["mon_n"]))
        check("다음 해 3월 → 값 = YYYY-03(예전 type=month 와 같은 모양)", o["ym"] == "%d-03" % (today.year + 1), o["ym"])
        check("고르기 창·달력 스크립트 오류 0", not o["errs"], o["errs"][:3])

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
