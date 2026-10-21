# -*- coding: utf-8 -*-
"""z1191f 시험 — 담당 사업부·센터 진입 권한 「한꺼번에 설정」 화면
   (대표 2026-10-21 「담당사업부 선택 및 센터진입권한을 개인별 페이지로 들어가지 말고 한번에 일괄 설정할수있는 항목이 있으면
    좋겠어.. 한명식 들어가서 설정하기 너무 힘들어.」 → 계획 보고 → 「진행해」)
  §1 서버(임시 DB · TestClient): 화면(근무 중인 사람만·잠금 칸) · 관리자만 · 저장 규칙(잠금 건너뜀·등록→보기·먼저 바뀐 칸
     덮어쓰기 막기·모르는 칸/글자/사람 무시) · 칸마다 변경 이력 · 이력 못 쓰면 하나도 안 바뀜 · 사람 수정 화면도 이력
  §2 실제 화면(Chromium): 처음=본사 · 칸 누르기 · 등록→보기 · 보기 끄면 등록도 · 「모두」는 보이는 사람만 · 되돌리기 ·
     책갈피 넘어 바꾼 것도 저장 · 먼저 바뀐 칸 알림 · 다시 열기 · 틀 고정(윗부분·머리줄 · z1191i) · 칸 흔들림 없음 · 스크립트 오류 0
  §3 바뀐 곳 원문
"""
import contextlib
import io
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191f-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191f_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
FLAGS = ("can_view_sales", "can_use_sales", "can_view_logistics", "can_use_logistics")
with D.db_session() as conn:
    HAS_UH = bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_history'").fetchone())
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0"), ("email", "TEXT"), ("rank", "TEXT"), ("team_id", "INTEGER")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "entity" not in {r[1] for r in conn.execute("PRAGMA table_info(teams)")}:
        conn.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    TEAM = {}
    for key, nm, ent, od in (("K0", "가상총괄", "KOR", 0), ("K1", "가상설계팀", "KOR", 1), ("K2", "가상구매팀", "KOR", 2),
                             ("K3", "가상가공팀", "KOR", 3), ("V1", "가상설계팀", "VN", 10), ("V2", "가상생산팀", "VN", 11)):
        conn.execute("INSERT INTO teams (name, entity, code, display_order) VALUES (?,?,?,?)", (nm, ent, "Z" + key, od))
        TEAM[key] = conn.execute("SELECT MAX(id) FROM teams").fetchone()[0]
    PEOPLE = [  # 이름, 사번, 팀, 역할, 근무, (매출보기, 매출등록, 자재보기, 자재등록), 사업부  — 팀 순서 = 운영처럼 총괄 먼저
        ("가상관리자", "T901", "K0", "admin", 1, (0, 0, 0, 0), ""),
        ("가상대표", "T900", "K0", "ceo", 1, (1, 1, 1, 1), ""),
        ("가상팀장", "T850", "K1", "leader", 1, (1, 0, 1, 0), ""),
        ("가상본사1", "T801", "K1", "member", 1, (0, 0, 0, 0), ""),
        ("가상본사2", "T802", "K1", "member", 1, (0, 0, 0, 0), ""),
        ("가상구매1", "T803", "K2", "member", 1, (0, 0, 1, 1), ""),
        ("가상퇴사", "T899", "K1", "member", 0, (0, 0, 0, 0), ""),
        ("가상베트남1", "VN801", "V1", "member", 1, (0, 0, 0, 0), ""),
        ("가상베트남2", "VN802", "V2", "member", 1, (0, 0, 0, 0), ""),
        ("가상베트남3", "VN803", "V2", "member", 1, (0, 0, 0, 0), "T,M,L,E"),
    ] + [("가상가공%02d" % i, "T7%02d" % i, "K3", "member", 1, (0, 0, 0, 0), "") for i in range(1, 41)]   # 머리줄 고정 보려고 줄 늘림
    ID = {}
    for nm, sb, tk, role, act, fl, bd in PEOPLE:
        conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, email, "
                     "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics, biz_divs) "
                     "VALUES (?,?,?,?,'x',?,1,?,?,?,?,?,?,?)",
                     (nm, role, sb, sb, act, TEAM.get(tk), sb.lower() + "@example.invalid") + fl + (bd,))
        ID[sb] = conn.execute("SELECT MAX(id) FROM users").fetchone()[0]
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T901'").fetchone())
    MEMBER = dict(conn.execute("SELECT * FROM users WHERE employee_no='T801'").fetchone())
    N_ACT = conn.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0]
    N_VN = sum(1 for p in PEOPLE if p[4] and p[2] in ("V1", "V2"))
N_KR = N_ACT - N_VN

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


def urow(sb):
    with D.db_session() as c:
        return dict(c.execute("SELECT COALESCE(biz_divs,'') AS bd, " + ", ".join("COALESCE(%s,0) AS %s" % (f, f) for f in FLAGS)
                              + " FROM users WHERE id=?", (ID[sb],)).fetchone())


def hist(sb, note=None):
    with D.db_session() as c:
        q = "SELECT field, old_value, new_value, note, changed_by FROM user_history WHERE user_id=?"
        a = [ID[sb]]
        if note is not None:
            q += " AND note=?"
            a.append(note)
        return [tuple(r) for r in c.execute(q + " ORDER BY id", a).fetchall()]


print("=" * 78)
print("§1 서버")
print("=" * 78)
check("0 새 DB 에도 변경 이력 표가 생김(init_db · 운영과 같은 모양)", HAS_UH)
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/admin/users/perms")
h = r.text
check("1 화면 200 · 근무 중인 사람만 %d줄(퇴사 1명 빠짐)" % N_ACT,
      r.status_code == 200 and h.count('class="prow"') == N_ACT and "가상퇴사" not in h, (r.status_code, h.count('class="prow"')))
check("   잠긴 칸 = 대표 4 · 팀장 보기 2 = 6 (z1191g: 관리자는 잠그지 않고 체크대로)", h.count('<td class="lk"') == 6, h.count('<td class="lk"'))
import re                                                   # noqa: E402
_kr = len(re.findall(r'<tr class="prow"[^>]*data-corp="본사"', h))
_vn = len(re.findall(r'<tr class="prow"[^>]*data-corp="베트남법인"', h))
check("   본사 %d · 베트남법인 %d 줄 표시(법인 규칙 = 사용자 목록과 같음)" % (N_KR, N_VN), _kr == N_KR and _vn == N_VN, (_kr, _vn))
check("   사업부 4칸·센터 4칸 체크(잠긴 칸 빼고) · 사업부 T,M,L,E 사람은 네 칸 모두 켜짐",
      h.count('data-f="biz" data-v=') == N_ACT * 4 + 4 and h.count('class="pc" data-f="can_') == N_ACT * 4 - 6
      and 'data-bd="T,M,L,E"' in h)
M.get_user = lambda request: MEMBER
with contextlib.redirect_stdout(io.StringIO()):
    r_m = cl.get("/admin/users/perms")
    r_mp = cl.post("/admin/users/perms", json={"changes": [{"id": ID["T801"], "f": "can_view_sales", "old": 0, "new": 1}]})
M.get_user = lambda request: ADMIN
check("2 관리자·대표 아니면 화면 못 엶(303) · 저장 403 · 값 그대로",
      r_m.status_code == 303 and r_mp.status_code == 403 and urow("T801")["can_view_sales"] == 0, (r_m.status_code, r_mp.status_code))

CH = [
    {"id": ID["T801"], "f": "biz_divs", "old": "", "new": "M,T"},
    {"id": ID["T801"], "f": "can_use_sales", "old": 0, "new": 1},            # 보기는 안 보냈지만 켜져야
    {"id": ID["T803"], "f": "can_view_logistics", "old": 1, "new": 0},
    {"id": ID["T803"], "f": "can_use_logistics", "old": 1, "new": 0},
    {"id": ID["VN801"], "f": "can_view_logistics", "old": 0, "new": 1},
    {"id": ID["VN801"], "f": "biz_divs", "old": "", "new": "X,L"},           # 모르는 글자 X 버림
    {"id": ID["T900"], "f": "can_view_sales", "old": 1, "new": 0},           # 대표 = 역할 잠금
    {"id": ID["T850"], "f": "can_view_logistics", "old": 1, "new": 0},       # 팀장 보기 = 역할 잠금
    {"id": ID["T850"], "f": "can_use_logistics", "old": 0, "new": 1},        # 팀장 등록은 됨
    {"id": ID["T802"], "f": "can_view_sales", "old": 1, "new": 0},           # 화면 연 뒤 바뀐 칸(지금 0) → 덮어쓰기 막음
    {"id": ID["T802"], "f": "is_admin", "old": 0, "new": 1},                 # 모르는 칸 → 무시
    {"id": 999999, "f": "can_view_sales", "old": 0, "new": 1},               # 없는 사람
]
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/admin/users/perms", json={"changes": CH})
j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
check("3 저장 200 · 4명 · 8칸", r.status_code == 200 and j.get("ok") and j.get("people") == 4 and j.get("cells") == 8,
      (r.status_code, {k: j.get(k) for k in ("ok", "people", "cells", "error")}))
u801, u803, u_vn1, u850, u900, u802 = urow("T801"), urow("T803"), urow("VN801"), urow("T850"), urow("T900"), urow("T802")
check("   본사1: 사업부 'M,T'→'T,M'(순서 맞춤) · 매출 등록 켬 → 보기도 켬",
      u801["bd"] == "T,M" and u801["can_use_sales"] == 1 and u801["can_view_sales"] == 1, u801)
check("   구매1: 자재 보기·등록 끔 · 베트남1: 자재 보기 켬 · 사업부 'X,L'→'L'",
      u803["can_view_logistics"] == 0 and u803["can_use_logistics"] == 0 and u_vn1["can_view_logistics"] == 1 and u_vn1["bd"] == "L",
      (u803, u_vn1))
check("   대표 칸 그대로 · 팀장 보기 그대로(1) · 팀장 자재 등록 켬",
      u900["can_view_sales"] == 1 and u850["can_view_logistics"] == 1 and u850["can_use_logistics"] == 1, (u900, u850))
check("   먼저 바뀐 칸 1개(본사2 매출 보기 · 지금 0) → 안 바꿈 · 모르는 칸 is_admin 무시",
      [(c["id"], c["f"], c["now"]) for c in j.get("conflicts", [])] == [(ID["T802"], "can_view_sales", 0)]
      and u802["can_view_sales"] == 0, j.get("conflicts"))
sk = sorted((c["name"], c["f"], c["why"]) for c in j.get("skipped", []))
check("   건너뜀 3 = 대표 매출 보기·팀장 자재 보기(역할상 항상 열림) · 없는 사람",
      sk == sorted([("가상대표", "can_view_sales", "역할상 항상 열림"), ("가상팀장", "can_view_logistics", "역할상 항상 열림"),
                    ("#999999", "", "없는 사람")]), sk)
rows = j.get("rows") or {}
check("   돌려준 지금 값: 본사2(먼저 바뀐 칸)·대표 포함 · 없는 사람 빠짐",
      set(rows) == {str(ID[k]) for k in ("T801", "T803", "VN801", "T900", "T850", "T802")}
      and rows[str(ID["T801"])]["biz_divs"] == "T,M" and rows[str(ID["T802"])]["can_view_sales"] == 0, sorted(rows))
h801 = hist("T801", "일괄 설정")
check("4 변경 이력 — 본사1 세 줄(사업부 공통→검사기·자동화 · 매출 보기·등록 끔→켬) · 바꾼 사람 = 관리자",
      sorted(x[:3] for x in h801) == sorted([("담당 사업부", "공통", "검사기·자동화"), ("매출·영업 보기", "끔", "켬"),
                                             ("매출·영업 등록·편집", "끔", "켬")]) and all(x[4] == ADMIN["id"] for x in h801), h801)
n_all = sum(len(hist(k, "일괄 설정")) for k in ("T801", "T803", "VN801", "T850", "T900", "T802"))
check("   이력 줄 수 = 저장한 칸 수(8) · 대표·본사2 이력 없음", n_all == 8 and not hist("T900") and not hist("T802"), n_all)

with contextlib.redirect_stdout(io.StringIO()):
    r_e = cl.post("/admin/users/perms", json={"changes": []})
    r_e2 = cl.post("/admin/users/perms", json={"changes": [{"id": "abc", "f": "can_view_sales"}, {"id": 1, "f": "nope"}]})
check("5 빈 요청·못 읽는 칸만 → 400", r_e.status_code == 400 and r_e2.status_code == 400, (r_e.status_code, r_e2.status_code))

with D.db_session() as c:
    c.execute("ALTER TABLE user_history RENAME TO user_history_z1191f_tmp")
with contextlib.redirect_stdout(io.StringIO()):
    r_f = cl.post("/admin/users/perms", json={"changes": [{"id": ID["T802"], "f": "can_view_sales", "old": 0, "new": 1}]})
with D.db_session() as c:
    c.execute("ALTER TABLE user_history_z1191f_tmp RENAME TO user_history")
jf = r_f.json() if r_f.headers.get("content-type", "").startswith("application/json") else {}
check("6 이력을 못 쓰면 500 · 안내 글 · 값도 안 바뀜(한 덩어리로 되돌림 — 조용히 넘어가지 않음)",
      r_f.status_code == 500 and not jf.get("ok") and "아무것도 바뀌지 않았" in (jf.get("error") or "")
      and urow("T802")["can_view_sales"] == 0, (r_f.status_code, jf))

with contextlib.redirect_stdout(io.StringIO()):
    r_s = cl.post("/admin/users/%d/edit" % ID["VN802"],
                  data={"name": "가상베트남2", "login_id": "VN802", "role": "member", "team_id": str(TEAM["V2"]), "rank": "",
                        "email": "vn802@example.invalid", "is_active": "1", "biz_divs": ["L", "T"], "can_use_logistics": "on"})
u_vn2 = urow("VN802")
h_vn2 = hist("VN802", "")
check("7 사람 수정 화면 저장: 자재 등록 켬 → 보기도 켬(재기동 때와 같게)",
      r_s.status_code == 303 and u_vn2["can_use_logistics"] == 1 and u_vn2["can_view_logistics"] == 1, (r_s.status_code, u_vn2))
check("   사람 수정 화면도 변경 이력 — 사업부 공통→검사기·라이프밸류 · 자재 보기·등록 끔→켬(전에는 안 남았다)",
      sorted(x[:3] for x in h_vn2) == sorted([("담당 사업부", "공통", "검사기·라이프밸류"), ("자재·구매 보기", "끔", "켬"),
                                              ("자재·구매 등록·편집", "끔", "켬")]), h_vn2)

print()
print("=" * 78)
print("§2 실제 화면 — Chromium · 시험용 서버(임시 DB)")
print("=" * 78)
DRIVER = r'''
import json, sqlite3, sys
from playwright.sync_api import sync_playwright
BASEURL, SHOT, DBP = sys.argv[1], sys.argv[2], sys.argv[3]
ID = json.loads(sys.argv[4])
out = {"page_errors": [], "dialogs": []}
def st(pg):
    return pg.evaluate("""()=>{ var tabs=[].map.call(document.querySelectorAll('.ucf-tab'), function(t){ return {corp:t.getAttribute('data-corp'), on:t.classList.contains('on'), n:(t.querySelector('.n')||{}).textContent}; });
        var vis=[].filter.call(document.querySelectorAll('#pgGrid tr.prow'), function(r){ return r.style.display!=='none'; });
        var corps={}; vis.forEach(function(r){ var c=r.getAttribute('data-corp'); corps[c]=(corps[c]||0)+1; });
        var depts=[].slice.call(document.querySelectorAll('#pgDept option')).map(function(o){ return o.value; }).filter(Boolean);
        var ds=document.getElementById('pgDept'), q=document.getElementById('pgQ');
        return {tabs:tabs, vis:vis.length, corps:corps, depts:depts, chg:document.getElementById('pgChg').textContent,
                flags:document.querySelectorAll('#pgGrid td.knk-row-flag').length, cnt:document.getElementById('pgCnt').textContent,
                dw:Math.round(ds.getBoundingClientRect().width*10)/10, qx:Math.round(q.getBoundingClientRect().left*10)/10}; }""")
def cell(pg, sb, f, v=None):
    sel = 'tr.prow[data-id="%d"] input.pc[data-f="%s"]%s' % (ID[sb], f, ('[data-v="%s"]' % v) if v else '')
    return sel
def val(pg, sel):
    return pg.evaluate("(s)=>{ var x=document.querySelector(s); return x? (x.checked?1:0) : null; }", sel)
def click_cell(pg, sel):
    pg.evaluate("(s)=>{ var x=document.querySelector(s); x.parentNode.click(); }", sel)   # 칸(label)을 누른다
    pg.wait_for_timeout(120)
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1400, "height": 900})
    ctx.add_init_script("try{sessionStorage.setItem('knkAutoReloadTs', String(Date.now()));}catch(e){}")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: out["page_errors"].append(str(e)[:200]))
    def on_dialog(d):
        out["dialogs"].append({"type": d.type, "msg": d.message[:600]})
        d.accept()
    pg.on("dialog", on_dialog)
    pg.goto(BASEURL + "/admin/users/perms")
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    pg.wait_for_timeout(500)
    out["first"] = st(pg)
    # ① 칸 누르기: 본사2 자재 등록 → 보기도 켜짐 → 보기 끄면 등록도 꺼짐
    click_cell(pg, cell(pg, "T802", "can_use_logistics"))
    out["imply"] = {"use": val(pg, cell(pg, "T802", "can_use_logistics")), "view": val(pg, cell(pg, "T802", "can_view_logistics")), "st": st(pg)}
    click_cell(pg, cell(pg, "T802", "can_view_logistics"))
    out["drop"] = {"use": val(pg, cell(pg, "T802", "can_use_logistics")), "view": val(pg, cell(pg, "T802", "can_view_logistics")), "st": st(pg)}
    # ② 부서 거르기 + 「모두」(기타) → 보이는 3명만
    pg.select_option("#pgDept", "본사 · 가상설계팀"); pg.wait_for_timeout(200)
    pg.evaluate("()=>{ var a=document.querySelector('thead input.pall[data-f=\"biz\"][data-v=\"E\"]'); a.click(); }"); pg.wait_for_timeout(200)
    out["all"] = {"st": st(pg), "e_801": val(pg, cell(pg, "T801", "biz", "E")), "e_803": val(pg, cell(pg, "T803", "biz", "E")),
                  "e_701": val(pg, cell(pg, "T701", "biz", "E"))}
    # ③ 되돌리기
    pg.click("#pgUndo"); pg.wait_for_timeout(200)
    out["undo"] = {"st": st(pg), "e_801": val(pg, cell(pg, "T801", "biz", "E"))}
    pg.select_option("#pgDept", ""); pg.wait_for_timeout(150)
    # ④ 저장할 것: 본사2 매출 보기 · 구매1 사업부 검사기 · 팀장 매출 등록 · (베트남법인 책갈피) 베트남3 기타 끔
    click_cell(pg, cell(pg, "T802", "can_view_sales"))
    click_cell(pg, cell(pg, "T803", "biz", "T"))
    click_cell(pg, cell(pg, "T850", "can_use_sales"))
    pg.click('.ucf-tab[data-corp="베트남법인"]'); pg.wait_for_timeout(250)
    click_cell(pg, cell(pg, "VN803", "biz", "E"))
    out["vn"] = st(pg)
    wrap = pg.query_selector("main.main")   # z1191i: 윗부분이 따로 묶여 .pg-wrap 이 둘 → 화면 전체를 찍는다
    if wrap:
        wrap.screenshot(path=SHOT + "_vn.png")
    pg.click('.ucf-tab.all'); pg.wait_for_timeout(250)
    out["alltab"] = st(pg)
    pg.click('.ucf-tab[data-corp="본사"]'); pg.wait_for_timeout(250)
    out["kr_before_save"] = st(pg)
    if wrap:
        wrap.screenshot(path=SHOT + "_kr.png")
    # ⑤ 화면을 연 뒤 다른 곳에서 구매1 사업부가 바뀜(→ 먼저 바뀐 칸)
    con = sqlite3.connect(DBP); con.execute("UPDATE users SET biz_divs='M' WHERE id=?", (ID["T803"],)); con.commit(); con.close()
    pg.click("#pgSave")
    pg.wait_for_function("()=>{ var m=document.getElementById('pgMsg'); return m && m.textContent.length>0; }", timeout=15000)
    pg.wait_for_timeout(300)
    out["saved"] = {"msg": pg.evaluate("()=>document.getElementById('pgMsg').textContent"),
                    "cls": pg.evaluate("()=>document.getElementById('pgMsg').className"), "st": st(pg),
                    "t803_T": val(pg, cell(pg, "T803", "biz", "T")), "t803_M": val(pg, cell(pg, "T803", "biz", "M")),
                    "t802_vs": val(pg, cell(pg, "T802", "can_view_sales"))}
    if wrap:
        wrap.screenshot(path=SHOT + "_saved.png")
    # ⑥ 틀 고정(z1191i) — 대표가 한 그대로: 윗부분 위에서 휠 · 표 위에서 휠 → 화면은 내려가도 윗부분·머리 두 줄은 제자리
    FIX = """()=>{ var m=document.querySelector('.main'), f=document.querySelector('.pg-fixed'), t=document.querySelector('.page-title'),
        sv=document.getElementById('pgSave'), g=document.querySelector('#pgGrid thead tr.g th[colspan]'), c=document.querySelector('#pgGrid thead tr.c th');
        var R=function(e){ return e.getBoundingClientRect(); };
        return {main:Math.round(m.scrollTop), title:Math.round(R(t).top), save:Math.round(R(sv).top), fix_bottom:(f? Math.round(R(f).bottom) : null),
                g_top:Math.round(R(g).top), g_h:Math.round(R(g).height), c_top:Math.round(R(c).top),
                msg:(document.getElementById('pgMsg').textContent||'').length>0, box_scroll:getComputedStyle(document.querySelector('.pg-scroll')).overflowY}; }"""
    st0 = pg.evaluate(FIX)
    pg.mouse.move(700, 230); pg.mouse.wheel(0, 700); pg.wait_for_timeout(400)
    st1 = pg.evaluate(FIX)
    pg.mouse.move(700, 820); pg.mouse.wheel(0, 3000); pg.wait_for_timeout(500)
    st2 = pg.evaluate(FIX)
    out["sticky"] = {"before": st0, "wheel_top": st1, "wheel_table": st2}
    if wrap:
        pg.screenshot(path=SHOT + "_fixed.png")
    pg.reload()
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    pg.wait_for_timeout(500)
    out["reload"] = {"st": st(pg), "t802_vs": val(pg, cell(pg, "T802", "can_view_sales"))}
    br.close()
print("@@RESULT@@" + json.dumps(out, ensure_ascii=False))
'''


def find_pw_python():
    cands = [sys.executable, os.environ.get("KNK_PW_PY", ""),
             os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe"), "python"]
    for c in cands:
        if not c:
            continue
        try:
            if subprocess.run([c, "-c", "import playwright.sync_api"], capture_output=True, timeout=60).returncode == 0:
                return c
        except Exception:
            pass
    return None


import uvicorn                                              # noqa: E402

_sk = socket.socket()
_sk.bind(("127.0.0.1", 0))
PORT = _sk.getsockname()[1]
_sk.close()
srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, lifespan="off", log_level="warning"))
threading.Thread(target=srv.run, daemon=True).start()
for _ in range(150):
    if srv.started:
        break
    time.sleep(0.1)
check("시험용 서버 뜸(127.0.0.1 · 빈 포트 · 시작 작업 끔)", srv.started, PORT)
PWPY = find_pw_python()
check("Playwright 있는 파이썬 찾음", bool(PWPY), PWPY)
DRV = os.path.join(TMP, "pw_driver.py")
io.open(DRV, "w", encoding="utf-8").write(DRIVER)
SHOT = os.environ.get("KNK_SHOT_PREFIX") or os.path.join(TMP, "shot")
H0 = {k: len(hist(k, "일괄 설정")) for k in ("T802", "T803", "T850", "VN803")}
res = {}
if PWPY:
    rr = subprocess.run([PWPY, DRV, "http://127.0.0.1:%d" % PORT, SHOT, D.DB_PATH, json.dumps(ID)], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=900, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    line = [x for x in (rr.stdout or "").splitlines() if x.startswith("@@RESULT@@")]
    res = json.loads(line[-1][len("@@RESULT@@"):]) if line else {"page_errors": ["(브라우저 결과 없음) " + (rr.stderr or "")[-800:]]}
tab = lambda s, c: next((t for t in (s.get("tabs") or []) if t.get("corp") == c), {})   # noqa: E731
F1 = res.get("first") or {}
check("A 처음 = 본사 책갈피 · 본사 %d명 · 숫자(본사 %d · 베트남법인 %d · 전체 %d) · 부서 = 본사만" % (N_KR, N_KR, N_VN, N_ACT),
      tab(F1, "본사").get("on") and F1.get("vis") == N_KR and tab(F1, "본사").get("n") == str(N_KR)
      and tab(F1, "베트남법인").get("n") == str(N_VN) and tab(F1, "").get("n") == str(N_ACT)
      and F1.get("depts") and all(d.startswith("본사") for d in F1.get("depts"))
      and F1.get("chg") == "바뀐 곳 0칸 · 0명", F1)
IM, DR = res.get("imply") or {}, res.get("drop") or {}
check("B 칸 누르기: 자재 등록 켬 → 보기도 켬 · 두 칸 노랑 · 「바뀐 곳 2칸 · 1명」",
      IM.get("use") == 1 and IM.get("view") == 1 and (IM.get("st") or {}).get("flags") == 2
      and (IM.get("st") or {}).get("chg") == "바뀐 곳 2칸 · 1명", IM)
check("   보기 끄면 등록도 꺼짐 → 「바뀐 곳 0칸 · 0명」", DR.get("use") == 0 and DR.get("view") == 0
      and (DR.get("st") or {}).get("chg") == "바뀐 곳 0칸 · 0명", DR)
AL = res.get("all") or {}
check("C 「모두」(기타)는 보이는 사람(설계팀 3명)만 · 안 보이는 구매1·가공은 그대로",
      (AL.get("st") or {}).get("vis") == 3 and AL.get("e_801") == 1 and AL.get("e_803") == 0 and AL.get("e_701") == 0
      and (AL.get("st") or {}).get("chg") == "바뀐 곳 3칸 · 3명", AL)
UN = res.get("undo") or {}
check("D 되돌리기 → 0칸 · 체크도 원래대로", (UN.get("st") or {}).get("chg") == "바뀐 곳 0칸 · 0명" and UN.get("e_801") == 0, UN)
VN, KB = res.get("vn") or {}, res.get("kr_before_save") or {}
check("E 베트남법인 책갈피에서 바꾼 것까지 합쳐 「바뀐 곳 4칸 · 4명」(안 보이는 줄도 저장 대상) · 부서 = 베트남만",
      VN.get("vis") == N_VN and VN.get("chg") == "바뀐 곳 4칸 · 4명" and KB.get("chg") == "바뀐 곳 4칸 · 4명"
      and VN.get("depts") and all(d.startswith("베트남") for d in VN.get("depts")), (VN, KB.get("chg")))
dws = [s.get("dw") for s in (F1, VN, res.get("alltab") or {}, KB)]
qxs = [s.get("qx") for s in (F1, VN, res.get("alltab") or {}, KB)]
check("   책갈피를 바꿔도 부서 칸 폭·검색 칸 자리 그대로", all(dws) and max(dws) - min(dws) <= 0.5 and max(qxs) - min(qxs) <= 0.5,
      {"폭": dws, "자리": qxs})
dl = [d for d in res.get("dialogs", []) if d.get("type") == "confirm"]
check("F 저장 전 확인 창에 사람·칸이 말로 나옴(4명 · 4칸 · 이름)",
      len(dl) == 1 and dl[0]["msg"].startswith("4명 · 4칸을 저장합니다") and "가상팀장 — 매출·영업 등록·편집 켬" in dl[0]["msg"]
      and "가상베트남3 — 담당 사업부 검사기·자동화·라이프밸류·기타→검사기·자동화·라이프밸류" in dl[0]["msg"], dl)
SV = res.get("saved") or {}
check("G 저장 뒤 안내: 3명 · 3칸 저장 · 먼저 바뀐 칸 1개(구매1 사업부) 알림 · 노랑 0",
      "저장했습니다 — 3명 · 3칸" in (SV.get("msg") or "") and "먼저 바뀐 칸 1개" in (SV.get("msg") or "")
      and "가상구매1 담당 사업부" in (SV.get("msg") or "") and "warn" in (SV.get("cls") or "")
      and (SV.get("st") or {}).get("chg") == "바뀐 곳 0칸 · 0명" and (SV.get("st") or {}).get("flags") == 0, SV)
check("   먼저 바뀐 칸은 지금 값으로 바꿔 보임(구매1 = 자동화만) · 본사2 매출 보기 켜진 채",
      SV.get("t803_M") == 1 and SV.get("t803_T") == 0 and SV.get("t802_vs") == 1, SV)
u802b, u850b, u_vn3, u803b = urow("T802"), urow("T850"), urow("VN803"), urow("T803")
check("   DB: 본사2 매출 보기 1 · 팀장 매출 등록 1 · 베트남3 사업부 T,M,L · 구매1 사업부 'M'(다른 곳 값 지킴)",
      u802b["can_view_sales"] == 1 and u850b["can_use_sales"] == 1 and u_vn3["bd"] == "T,M,L" and u803b["bd"] == "M",
      (u802b, u850b, u_vn3, u803b))
H1 = {k: len(hist(k, "일괄 설정")) for k in H0}
check("   이력 +1씩(본사2·팀장·베트남3) · 구매1 은 안 늘어남",
      H1["T802"] - H0["T802"] == 1 and H1["T850"] - H0["T850"] == 1 and H1["VN803"] - H0["VN803"] == 1 and H1["T803"] == H0["T803"], (H0, H1))
SK = res.get("sticky") or {}
s0, s1, s2 = SK.get("before") or {}, SK.get("wheel_top") or {}, SK.get("wheel_table") or {}
check("H 틀 고정(z1191i): 윗부분·표 위에서 휠 → 화면은 내려감 · 제목·저장 단추 자리 그대로(저장 안내가 뜬 상태)",
      s1.get("main", 0) > 300 and s2.get("main", 0) > s1.get("main", 0) and s0.get("msg")
      and all(abs(s.get("title", -99) - s0.get("title", 99)) <= 1 and abs(s.get("save", -99) - s0.get("save", 99)) <= 1 for s in (s1, s2)), SK)
check("   머리 두 줄은 윗부분 바로 아래에 붙어 있음 · 표 자체 스크롤 없음(스크롤은 화면 하나)",
      all((s.get("fix_bottom") is not None and abs(s.get("g_top", 99) - s.get("fix_bottom")) <= 2) and abs(s.get("c_top", 99) - s.get("g_top", 0) - s.get("g_h", 0)) <= 3
          for s in (s1, s2)) and s2.get("box_scroll") == "visible", SK)
RL = res.get("reload") or {}
check("I 다시 열면: 마지막 책갈피(본사) · 저장한 값 · 바뀐 곳 0", tab(RL.get("st") or {}, "본사").get("on") and RL.get("t802_vs") == 1
      and (RL.get("st") or {}).get("chg") == "바뀐 곳 0칸 · 0명", RL)
check("화면 스크립트 오류 0", not res.get("page_errors"), res.get("page_errors"))

print()
print("=" * 78)
print("§3 바뀐 곳 원문")
print("=" * 78)
T = os.path.join(ROOT, "app", "templates")
ad = open(os.path.join(T, "admin.html"), encoding="utf-8").read()
uf = open(os.path.join(T, "admin_user_form.html"), encoding="utf-8").read()
pt = open(os.path.join(T, "admin_users_perms.html"), encoding="utf-8").read()
check("관리자 사용자 탭 단추 · 사람 수정 화면 안내 줄", 'href="/admin/users/perms"' in ad and 'href="/admin/users/perms"' in uf)
js = pt.split("<script>", 1)[1] if "<script>" in pt else ""
check("새 화면 스크립트에 Jinja 기호 없음", js and not any(s in js for s in ("{{", "{%", "{#")))
mn = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("저장은 한 거래(db_session 하나) · 이력 실패를 넘기지 않음(except pass 없음)",
      mn.count("def admin_users_perms_save(") == 1 and "cells += _z1191f_history(c, uid, u.get(\"id\"), before, after, \"일괄 설정\")" in mn)

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
