# -*- coding: utf-8 -*-
"""z1191g 시험 — 관리자(admin)는 「관리 일」만 역할로, 매출·영업·자재·구매는 체크한 대로
   (대표 2026-10-21 「관리자가 … 자기 부서가 아닌 업무를 다 볼수있다는건 좀 아닌것 같아… 대표는 기존과 동일하게」
    「베트남 이용식 법인장이 관리자인데… 본사 매출영업,자재구매를 다 볼수있다는것도 이상해」)
  §1 판정 함수: 센터 4곳 · 금액 열람(관리자 = 자기 센터 체크대로 · 그 밖엔 팀 정책) · 대표·임원 그대로 · 팀장 보기 그대로
  §2 화면·경로(임시 DB · TestClient): 체크 없는 관리자 = 매출·자재·수출입·환율·은행 대사·작업일정표 못 들어감 ·
     대시보드는 열리되 매출·미수금·수출·재고 카드 없음 · 홈 경영진 매출 카드 없음 · 관리자 화면·일괄 설정은 그대로 ·
     체크 있는 관리자·대표·임원은 그대로 · 은행 대사 메뉴는 매출 등록 체크 있는 관리자만 · 일괄 설정에서 관리자 칸 저장됨
  §3 알림 받는 사람(코드의 실제 SQL 을 시험 DB 에 그대로 돌림) · 재기동(init_db)해도 관리자 체크 그대로 · 원문
"""
import contextlib
import io
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191g-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191g_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
FLAGS = ("can_view_sales", "can_use_sales", "can_view_logistics", "can_use_logistics")
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0"), ("email", "TEXT"), ("rank", "TEXT"), ("team_id", "INTEGER")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "entity" not in {r[1] for r in conn.execute("PRAGMA table_info(teams)")}:
        conn.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    TEAM = {}
    for key, nm, ent, od in (("HQ", "가상총괄", "KOR", 0), ("SL", "가상기술영업팀", "KOR", 1), ("MG", "가상관리팀", "KOR", 2),
                             ("DV", "가상개발혁신팀", "KOR", 3), ("VH", "가상총괄", "VN", 10)):
        conn.execute("INSERT INTO teams (name, entity, code, display_order) VALUES (?,?,?,?)", (nm, ent, "Z" + key, od))
        TEAM[key] = conn.execute("SELECT MAX(id) FROM teams").fetchone()[0]
    # 금액 열람 팀 정책 = 운영과 같은 모양(총괄·기술영업·관리 → 매출금액·구매단가·구매처) — 개발혁신팀·베트남 총괄은 없음
    conn.execute("DELETE FROM field_access_policy")
    for cat in ("sales_amount", "purchase_price", "supplier_info"):
        for tk in ("HQ", "SL", "MG"):
            conn.execute("INSERT INTO field_access_policy (category, team_id) VALUES (?,?)", (cat, TEAM[tk]))
    PEOPLE = [  # 사번, 이름, 역할, 팀, (매출보기, 매출등록, 자재보기, 자재등록)
        ("Z900", "가상대표", "ceo", "HQ", (1, 1, 1, 1)),
        ("Z910", "가상임원", "executive", "DV", (0, 0, 0, 0)),
        ("Z920", "가상법인장관리자", "admin", "VH", (0, 0, 0, 0)),     # 이용식 법인장 같은 경우
        ("Z921", "가상관리팀관리자", "admin", "MG", (1, 1, 1, 1)),     # 관리팀 — 대표가 4칸 켜 둔 경우
        ("Z922", "가상개발관리자", "admin", "DV", (1, 1, 1, 1)),       # 신준엽 같은 경우(팀은 금액 정책 밖)
        ("Z923", "가상영업관리자", "admin", "SL", (1, 1, 0, 0)),       # 매출만
        ("Z924", "가상관리팀관리자0", "admin", "MG", (0, 0, 0, 0)),    # 체크 없음 · 팀은 금액 정책 안
        ("Z925", "가상보기만관리자", "admin", "SL", (1, 0, 0, 0)),     # 매출 보기만
        ("Z930", "가상영업팀원", "member", "SL", (1, 1, 0, 0)),
    ]
    ID, U = {}, {}
    for sb, nm, role, tk, fl in PEOPLE:
        conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                     "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) VALUES (?,?,?,?,'x',1,1,?,?,?,?,?)",
                     (nm, role, sb, sb, TEAM[tk]) + fl)
        ID[sb] = conn.execute("SELECT MAX(id) FROM users").fetchone()[0]
    for sb in ID:
        U[sb] = dict(conn.execute("SELECT * FROM users WHERE id=?", (ID[sb],)).fetchone())

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

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


def as_(sb):
    M.get_user = lambda request, _u=U[sb]: _u


def get(sb, path):
    as_(sb)
    with contextlib.redirect_stdout(io.StringIO()):
        return cl.get(path)


def cen(sb):
    u = U[sb]
    return (int(bool(M.can_view_sales(u))), int(bool(M.can_use_sales(u))),
            int(bool(M.can_view_logistics(u))), int(bool(M.can_use_logistics(u))))


def fld(sb):
    pol = None
    with D.db_session() as c:
        pol = M.load_field_access_policy(c)
    return tuple(int(bool(M.can_view_field(U[sb], k, pol))) for k in ("sales_amount", "purchase_price", "supplier_info"))


print("=" * 78)
print("§1 판정 함수")
print("=" * 78)
check("1 체크 없는 관리자(베트남 법인장 같은) = 센터 4곳 모두 닫힘", cen("Z920") == (0, 0, 0, 0), cen("Z920"))
check("   4칸 켠 관리자(관리팀·개발) = 4곳 모두 열림", cen("Z921") == (1, 1, 1, 1) and cen("Z922") == (1, 1, 1, 1), (cen("Z921"), cen("Z922")))
check("   매출만 켠 관리자 = 매출 2곳만 · 매출 보기만 켠 관리자 = 매출 보기만", cen("Z923") == (1, 1, 0, 0) and cen("Z925") == (1, 0, 0, 0),
      (cen("Z923"), cen("Z925")))
check("   대표·임원 = 체크와 상관없이 4곳 모두(그대로) · 팀원 = 체크대로(그대로)",
      cen("Z900") == (1, 1, 1, 1) and cen("Z910") == (1, 1, 1, 1) and cen("Z930") == (1, 1, 0, 0), (cen("Z910"), cen("Z930")))
check("2 금액 열람: 체크 없는 베트남 관리자 = 매출금액·구매단가·구매처 모두 가림", fld("Z920") == (0, 0, 0), fld("Z920"))
check("   개발혁신팀 관리자(팀은 정책 밖) + 4칸 = 세 가지 모두 보임(신준엽 그대로)", fld("Z922") == (1, 1, 1), fld("Z922"))
check("   관리팀 관리자 체크 없음 = 팀 정책으로 보임(관리팀은 정책 안)", fld("Z924") == (1, 1, 1), fld("Z924"))
check("   대표·임원 = 모두 보임(그대로)", fld("Z900") == (1, 1, 1) and fld("Z910") == (1, 1, 1), (fld("Z900"), fld("Z910")))

print()
print("=" * 78)
print("§2 화면·경로")
print("=" * 78)
loc = lambda r: (r.status_code, r.headers.get("location", ""))   # noqa: E731
r1, r2, r3, r4, r5, r6 = (get("Z920", p) for p in ("/sales", "/logistics", "/sales/bank-recon", "/export", "/fx/rates", "/sales/schedule"))
check("3 체크 없는 관리자: 매출·자재·은행 대사·수출입·환율 → 홈으로(303) · 작업일정표 → 전사일정표",
      all(loc(r) == (303, "/home") for r in (r1, r2, r3, r4, r5)) and loc(r6) == (303, "/dept/schedule"),
      [loc(r) for r in (r1, r2, r3, r4, r5, r6)])
d0 = get("Z920", "/dashboard")
check("   대시보드는 열림(200) · 매출·미수금·수출·재고 카드 없음 · 품질·완료율·지연·환율 카드는 있음",
      d0.status_code == 200 and not any(x in d0.text for x in ("이번달 매출", "미수금 잔액", "수출 오더 진행", "활성 재고 품목"))
      and all(x in d0.text for x in ("품질 미해결", "이번주 완료율", "지연 프로젝트", "USD 환율")), d0.status_code)
h0 = get("Z920", "/home")
check("   홈은 열림 · 경영진 매출 카드(이번 달 수주) 없음", h0.status_code == 200 and "home-exec-bento" not in h0.text, h0.status_code)
a0, p0 = get("Z920", "/admin"), get("Z920", "/admin/users/perms")
check("   관리 일은 그대로: 관리자 화면 200 · 권한 한꺼번에 설정 200", a0.status_code == 200 and p0.status_code == 200,
      (a0.status_code, p0.status_code))
ok1 = [get("Z921", p) for p in ("/sales", "/logistics", "/sales/bank-recon", "/export", "/fx/rates", "/sales/schedule")]
check("4 4칸 켠 관리자: 매출·자재·은행 대사·수출입·환율·작업일정표 모두 200", [r.status_code for r in ok1] == [200] * 6,
      [loc(r) for r in ok1])
d1, h1 = get("Z921", "/dashboard"), get("Z921", "/home")
check("   대시보드 매출·미수금·수출·재고 카드 있음 · 홈 경영진 매출 카드 있음",
      all(x in d1.text for x in ("이번달 매출", "미수금 잔액", "수출 오더 진행", "활성 재고 품목")) and "home-exec-bento" in h1.text)
d5 = get("Z925", "/dashboard")
r5b = get("Z925", "/sales/bank-recon")
s5 = get("Z925", "/sales")
s3 = get("Z923", "/sales")
check("5 매출 보기만 켠 관리자: 매출 센터 200 · 은행 대사는 못 함(매출 등록 필요) · 메뉴에도 은행 대사 없음 · 재고 카드 없음",
      s5.status_code == 200 and loc(r5b) == (303, "/home") and "/sales/bank-recon" not in s5.text
      and "이번달 매출" in d5.text and "활성 재고 품목" not in d5.text, (s5.status_code, loc(r5b)))
check("   매출 등록까지 켠 관리자는 메뉴에 은행 대사 있음", s3.status_code == 200 and "/sales/bank-recon" in s3.text, s3.status_code)
dc, de = get("Z900", "/dashboard"), get("Z910", "/dashboard")
sc = [get("Z900", p).status_code for p in ("/sales", "/logistics", "/sales/bank-recon")]
check("6 대표: 매출·자재·은행 대사 200 · 대시보드 카드 모두(그대로) · 임원 대시보드 카드 모두",
      sc == [200, 200, 200] and "이번달 매출" in dc.text and "활성 재고 품목" in dc.text and "이번달 매출" in de.text, sc)
lk = len(re.findall(r'<tr class="prow" data-id="%d"[^>]*>.*?</tr>' % ID["Z920"], p0.text, re.S))
row0 = re.search(r'<tr class="prow" data-id="%d"[^>]*>(.*?)</tr>' % ID["Z920"], p0.text, re.S)
rowc = re.search(r'<tr class="prow" data-id="%d"[^>]*>(.*?)</tr>' % ID["Z900"], p0.text, re.S)
check("7 일괄 설정: 관리자 줄 센터 칸 잠금 없음(체크 4개) · 대표 줄은 🔒 4개 · 관리자 표시 설명 바뀜",
      row0 and row0.group(1).count('class="pc" data-f="can_') == 4 and '<td class="lk"' not in row0.group(1)
      and rowc and rowc.group(1).count('<td class="lk"') == 4 and "센터는 체크한 대로" in row0.group(1), lk)
as_("Z921")
with contextlib.redirect_stdout(io.StringIO()):
    rs = cl.post("/admin/users/perms", json={"changes": [{"id": ID["Z920"], "f": "can_view_logistics", "old": 0, "new": 1}]})
js = rs.json()
with D.db_session() as c:
    v920 = c.execute("SELECT can_view_logistics FROM users WHERE id=?", (ID["Z920"],)).fetchone()[0]
    c.execute("UPDATE users SET can_view_logistics=0 WHERE id=?", (ID["Z920"],))     # 되돌림(아래 재기동 시험용)
check("   관리자 칸 저장됨(건너뜀 없음 · 1명 · 1칸)", js.get("ok") and js.get("cells") == 1 and not js.get("skipped") and v920 == 1, js)
fm = get("Z921", "/admin/users/%d/edit" % ID["Z920"])
check("8 사람 수정 화면 안내: 「대표·임원은 역할상 항상 · 관리자도 체크한 대로만」",
      fm.status_code == 200 and "<b>관리자</b>도 여기 체크한 대로만 열립니다" in fm.text and "대표·임원·관리자</b>는" not in fm.text)

print()
print("=" * 78)
print("§3 알림 받는 사람 · 재기동 · 원문")
print("=" * 78)
src = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
q_recv = re.search(r'"(SELECT id FROM users WHERE can_use_sales=1 OR role=\'ceo\')"', src)
q_exp = re.search(r'"SELECT id FROM users WHERE is_active=1 AND "\s*"(\(team_id=12 OR role IN \(\'ceo\',\'executive\'\) OR '
                  r'\(role=\'admin\' AND COALESCE\(can_use_sales,0\)=1\)\))"', src)
check("9 원문: 수금 알림·수출 알림 받는 사람 SQL 이 바뀜(관리자 = 매출 등록 체크로)", bool(q_recv) and bool(q_exp))
if q_recv and q_exp:
    with D.db_session() as c:
        got_r = {r[0] for r in c.execute(q_recv.group(1)).fetchall()}
        got_e = {r[0] for r in c.execute("SELECT id FROM users WHERE is_active=1 AND " + q_exp.group(1)).fetchall()}
    want_r = {ID[k] for k in ("Z900", "Z921", "Z922", "Z923", "Z930")}
    check("   수금 알림: 대표 + 매출 등록 체크한 사람(관리자 3·팀원 1) · 체크 없는 관리자 둘·보기만 관리자 빠짐",
          want_r <= got_r and not ({ID["Z920"], ID["Z924"], ID["Z925"]} & got_r), sorted(got_r))
    want_e = {ID[k] for k in ("Z900", "Z910", "Z921", "Z922", "Z923")}
    check("   수출 알림: 대표·임원 + 매출 등록 체크한 관리자 · 체크 없는 관리자 빠짐 · 팀원은 그대로(안 받음)",
          want_e <= got_e and not ({ID["Z920"], ID["Z924"], ID["Z925"], ID["Z930"]} & got_e), sorted(got_e))
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as c:
    after = {sb: tuple(c.execute("SELECT " + ", ".join(FLAGS) + " FROM users WHERE id=?", (ID[sb],)).fetchone())
             for sb in ("Z920", "Z921", "Z924")}
check("10 재기동(init_db)해도 관리자 체크 그대로(시드는 대표·임원·팀장만 켬)",
      after["Z920"] == (0, 0, 0, 0) and after["Z921"] == (1, 1, 1, 1) and after["Z924"] == (0, 0, 0, 0), after)

body = {n: re.search(r'def %s\(user\).*?(?=\ndef )' % n, src, re.S).group(0) for n in ("can_view_sales", "can_use_sales",
                                                                                         "can_view_logistics", "can_use_logistics")}
check("11 원문: 센터 판정 4곳에 관리자 자동 허용 없음", all('"admin"' not in b.split('"""', 2)[-1] for b in body.values()),
      [n for n, b in body.items() if '"admin"' in b.split('"""', 2)[-1]])

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
