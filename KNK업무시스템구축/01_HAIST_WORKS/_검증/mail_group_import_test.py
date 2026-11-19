# -*- coding: utf-8 -*-
"""그룹 메일 명단 — 하이웍스 「그룹메일」 파일 올리기(대표 2026-11-20 「주기적으로 업데이트할 수 있게 설정에 메뉴 · 인원이 바뀔 때마다 이 파일을 올려서」).
운영 무접촉 · 임시 DB · 가짜 파일(하이웍스와 같은 모양 · 가짜 그룹·사람).

증명할 것
  ① 읽기: 하이웍스 .xls(속은 HTML 표 · 그룹 칸 rowspan) · .xlsx · .csv · 옛 .xls(이진) 은 안내 · 머리 줄 없으면 안내 · 계정수와 다르면 경고 · 틀린 주소 건너뜀
  ② 미리 보기: 저장 안 함 · 새 그룹 · 바뀐 그룹(들어옴·빠짐·이름) · 그대로 · 파일에 없는 그룹(파일로 올린 것=지움 / 손으로 등록=남김)
  ③ 반영: 파일대로 · 직원은 웍스 이름 · 원본↔저장 대조 ✅ · 마지막 올린 기록 · 다시 올리면 바뀐 것만 · 「지우기」 끄면 남김
  ④ 권한·화면: 관리자만(직원 403) · 설정 줄(관리자만) · 묶음 화면 「📥 하이웍스 파일로 올리기」·마지막 올린 때
"""
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mgimp_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_work as mw
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:400])


def hiworks(groups, declared=None):
    """하이웍스가 내려 주는 모양 그대로(HTML 표 · 그룹 칸 rowspan · 「그룹명 ( 계정수 )」)."""
    h = ['<meta http-equiv="Content-Type" content="application/vnd.ms-excel; charset=utf-8"><table border=\'1\'>'
         '<tr><td>그룹명( 계정수 )</td><td>그룹메일주소</td><td>사용자명</td><td>메일주소</td></tr>']
    for gi, (name, addr, mem) in enumerate(groups):
        n = len(mem)
        dn = (declared or {}).get(addr, n)
        for i, (un, ue) in enumerate(mem):
            if i == 0:
                h.append("<tr><td rowspan='%d'>%s ( %d )</td><td rowspan='%d'>%s</td><td>%s</td><td>%s</td></tr>" % (n, name, dn, n, addr, un, ue))
            else:
                h.append("<tr><td>%s</td><td>%s</td></tr>" % (un, ue))
    h.append("</table>")
    return "".join(h).encode("utf-8")


OWN, MEM = 9701, 9702
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(9701,'T9701','가짜영업팀',1)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9701,'kjr','시험대표','ceo',1,'x','boss@knknara.co.kr',NULL)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9702,'t9702','시험직원','member',1,'x','m@knknara.co.kr',NULL)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9703,'t9703','웍스이름','member',1,'x','g1@knknara.co.kr',9701)")
U_CEO = {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": ""}
U_MEM = {"id": MEM, "role": "member", "name": "시험직원", "team_id": None, "team_name": ""}
_U = {"v": dict(U_CEO)}
m.get_user = lambda req: _U["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
km = TestClient(m.app, base_url="http://127.0.0.1:5053", raise_server_exceptions=False, follow_redirects=False)
km.headers.update({"host": "kmail.knknara.co.kr", "x-forwarded-proto": "https"})


def up(data, mode="preview", name="knknara.co.kr_그룹메일.xls", rm="1"):
    return k.post("/mail/groups/import", data={"mode": mode, "remove_missing": rm}, files={"file": (name, data, "application/vnd.ms-excel")})


F1 = [("가짜 영업 공용", "fsales@knknara.co.kr", [("파일이름", "g1@knknara.co.kr"), ("가짜둘", "g2@knknara.co.kr"), ("가짜셋", "g3@knknara.co.kr")]),
      ("가짜 품질 공용", "fqc@knknara.co.kr", [("가짜넷", "g4@knknara.co.kr")])]

print("== ① 읽기 ==")
r = mw.parse_group_file(hiworks(F1))
check("하이웍스 .xls(HTML 표 · rowspan) = 그룹 2 · 사람 4 · 경고 없음", len(r["groups"]) == 2 and sum(len(g["members"]) for g in r["groups"]) == 4 and not r["warnings"] and not r["error"], r)
check("그룹 이름에서 「( 계정수 )」 뺌 · 주소 소문자", r["groups"][0]["name"] == "가짜 영업 공용" and r["groups"][0]["address"] == "fsales@knknara.co.kr" and r["groups"][0]["declared"] == 3)
r = mw.parse_group_file(hiworks(F1, declared={"fsales@knknara.co.kr": 5}))
check("계정수와 읽은 수가 다르면 경고", any("계정수 5" in w for w in r["warnings"]), r["warnings"])
bad = hiworks([("이상", "not-an-address", [("a", "a@knknara.co.kr")]), ("좋음", "ok@knknara.co.kr", [("b", "b@knknara.co.kr"), ("c", "broken")])])
r = mw.parse_group_file(bad)
check("틀린 그룹 주소·사람 주소는 건너뛰고 알림", [g["address"] for g in r["groups"]] == ["ok@knknara.co.kr"] and len(r["groups"][0]["members"]) == 1 and len(r["warnings"]) == 3 and any("계정수 2" in w for w in r["warnings"]), r)
csvb = "그룹명,그룹메일주소,사용자명,메일주소\n가짜 CSV,fcsv@knknara.co.kr,하나,c1@knknara.co.kr\n,,둘,c2@knknara.co.kr\n".encode("utf-8-sig")
r = mw.parse_group_file(csvb)
check("CSV(그룹 칸 빈 줄 = 위 그룹)", len(r["groups"]) == 1 and len(r["groups"][0]["members"]) == 2, r)
from openpyxl import Workbook  # noqa: E402
wb = Workbook()
ws = wb.active
ws.append(["그룹명( 계정수 )", "그룹메일주소", "사용자명", "메일주소"])
ws.append(["가짜 엑셀 ( 2 )", "fx@knknara.co.kr", "엑셀하나", "x1@knknara.co.kr"])
ws.append([None, None, "엑셀둘", "x2@knknara.co.kr"])
bio = io.BytesIO()
wb.save(bio)
r = mw.parse_group_file(bio.getvalue())
check("엑셀(.xlsx · 합친 칸 = 빈칸)", len(r["groups"]) == 1 and len(r["groups"][0]["members"]) == 2 and not r["warnings"], r)
check("옛 .xls(이진)은 안내", "옛 엑셀" in mw.parse_group_file(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 100)["error"])
check("머리 줄 없으면 안내", "머리 줄" in mw.parse_group_file("<table><tr><td>아무거나</td></tr></table>".encode())["error"])
check("빈 파일 안내", mw.parse_group_file(b"")["error"])

print("== ② 미리 보기 ==")
with _db.db_session() as c:
    mw.ensure(c)
k.post("/mail/groups/save", data={"kind": "company", "name": "손으로 등록", "address": "manual@knknara.co.kr", "members": "z@knknara.co.kr"})
j = up(hiworks(F1)).json()
check("미리 보기 = 새 그룹 2 · 사람 4 · 손으로 등록한 그룹 = 파일에 없음(남김)", j["ok"] and len(j["plan"]["new"]) == 2 and j["plan"]["people"] == 4
      and [x["from_file"] for x in j["plan"]["missing"]] == [False], j)
with _db.db_session() as c:
    n = c.execute("SELECT COUNT(*) FROM mail_groups WHERE kind='company'").fetchone()[0]
check("미리 보기는 저장 안 함", n == 1, n)

print("== ③ 반영 ==")
j = up(hiworks(F1), "apply").json()
x = j["res"]
check("반영 = 새 2 · 원본↔저장 대조 ✅ · 손으로 등록한 것은 남김", j["ok"] and x["added"] == 2 and x["verify_ok"] and x["kept"] == 1 and x["removed"] == 0, x)
info = k.get("/api/mail/addrinfo?a=fsales@knknara.co.kr").json()["info"]["fsales@knknara.co.kr"]
check("직원은 웍스 이름(파일 「파일이름」 아님) · 3명", info["kind"] == "group" and info["n"] == 3 and info["members"][0]["name"] == "웍스이름" and "가짜영업팀" in info["members"][0]["disp"], info)
with _db.db_session() as c:
    last = mw.import_last(c)
check("마지막 올린 기록(언제·누가·그룹·사람·대조)", last.get("by") == "시험대표" and last.get("groups") == 2 and last.get("people") == 4 and last.get("ok") is True and last.get("at"), last)
F2 = [("가짜 영업 공용(새 이름)", "fsales@knknara.co.kr", [("파일이름", "g1@knknara.co.kr"), ("새사람", "g9@knknara.co.kr")]),
      ("가짜 설계 공용", "fdsn@knknara.co.kr", [("설계", "g5@knknara.co.kr")])]
j = up(hiworks(F2)).json()
p = j["plan"]
ch = p["changed"][0] if p["changed"] else {}
check("두 번째 파일 미리 보기 = 새 1 · 바뀜 1(들어옴 새사람 · 빠짐 가짜둘·가짜셋 · 이름 바뀜) · 파일에 없는 것 2(파일로 올린 품질=지움 · 손으로=남김)",
      len(p["new"]) == 1 and len(p["changed"]) == 1 and ch.get("add") == ["새사람"] and sorted(ch.get("rem")) == ["가짜둘", "가짜셋"]
      and ch.get("old_name") == "가짜 영업 공용" and sorted((y["address"], y["from_file"]) for y in p["missing"]) == [("fqc@knknara.co.kr", True), ("manual@knknara.co.kr", False)], p)
j = up(hiworks(F2), "apply", rm="0").json()
x = j["res"]
check("「지우기」를 끄면 파일에 없는 그룹도 남김", x["removed"] == 0 and x["kept"] == 2 and x["verify_ok"], x)
j = up(hiworks(F2), "apply").json()
x = j["res"]
check("다시 올리면 그대로 2 · 파일로 올렸던 품질 그룹 지움 · 손으로 등록은 남김", x["same"] == 2 and x["removed"] == 1 and x["kept"] == 1 and x["verify_ok"], x)
with _db.db_session() as c:
    addrs = sorted(r[0] for r in c.execute("SELECT address FROM mail_groups WHERE kind='company'").fetchall())
check("남은 그룹 = 영업·설계(파일) + 손으로 등록", addrs == ["fdsn@knknara.co.kr", "fsales@knknara.co.kr", "manual@knknara.co.kr"], addrs)
check("못 읽는 파일은 반영 안 함", up(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 50, "apply").status_code == 400)

print("== ④ 권한·화면 ==")
_U["v"] = dict(U_MEM)
check("직원은 올리기 못 함(403)", up(hiworks(F1), "apply").status_code == 403)
tl = km.get("/mail/tools").text
check("직원 설정 화면엔 「그룹 메일 명단 올리기」 없음", "그룹 메일 명단 올리기" not in tl)
hg = km.get("/mail/groups").text
check("직원 묶음 화면엔 올리기 단추 없음 · 명단은 보임", "📥 하이웍스 파일로 올리기" not in hg and "fsales@knknara.co.kr" in hg)
_U["v"] = dict(U_CEO)
tl = km.get("/mail/tools").text
check("관리자 설정 화면 「📥 그룹 메일 명단 올리기(하이웍스 파일)」 · 마지막 올린 때 · 그룹 수", "그룹 메일 명단 올리기" in tl and 'href="/mail/groups#import"' in tl and "마지막 " in tl and "그룹 메일 3개" in tl)
hg = km.get("/mail/groups").text
check("관리자 묶음 화면 「📥 하이웍스 파일로 올리기」 · 끌어다 놓기 · 마지막으로 올린 파일 ✅", "📥 하이웍스 파일로 올리기" in hg and 'id="gpDrop"' in hg and "마지막으로 올린 파일" in hg and "✅ 원본과 같음" in hg)

print("== ⑤ 📇 주소록 창 「👥 그룹 메일 · 묶음」 탭(대표 11-20) ==")
_U["v"] = dict(U_MEM)
ga = k.get("/api/mail/groups/all").json()
fs = next((g for g in ga.get("company", []) if g["address"] == "fsales@knknara.co.kr"), {})
check("직원도 그룹 메일 목록·명단을 받음(주소·이름 직책 부서)", ga.get("ok") and fs and len(fs["members"]) == 2 and fs["members"][0]["name"] == "웍스이름"
      and "가짜영업팀" in fs["members"][0]["disp"], fs)
check("부서 묶음도 함께", any(g["name"] == "가짜영업팀 전체" for g in ga.get("dept", [])), ga.get("dept"))
_U["v"] = dict(U_CEO)
cpz = open(os.path.join(ROOT, "app", "templates", "mail_compose.html"), encoding="utf-8").read()
check("주소록 창 탭 「📇 연락처 / 👥 그룹 메일 · 묶음」 · 펼치기 · 몇 사람만 고르기 · 그룹이면 「N명이 받음」",
      'id="abTabG"' in cpz and "function abGLoad" in cpz and "fetch('/api/mail/groups/all')" in cpz and "펼치기 ▾" in cpz
      and "function abMTick" in cpz and "명이 받음)" in cpz)
check("주소록에서 넣으면 받는 사람 칸 아래 그룹 명단도 바로", "if(window.cmpGrpCheck) cmpGrpCheck();   // 11-20" in cpz)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
