# -*- coding: utf-8 -*-
"""z1191z77 시험 (대표 2026-11-19 「여기 연락처를 개인연락처, 부서연락처, 전사공개연락처 로 구분할수있게 구성해줘... 혹시 전화번호를 더
  효율적으로 관리할수있는 방법 있으면 우리 직원들 입장에서 어떻게 정리하면 좋을지 검토해서 적용해봐.」
  + 「개인연락처는 본인만 볼수있는 연락처 · 부서연락처는 우리부서원들 누구나 볼수있는 연락처 · 전사공개연락처는 우리회사 전체 누구나 볼수있는 연락처」)
  임시 DB · TestClient · 가짜 자료 · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z77-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z77_")
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


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("rank", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    T1 = ins(c, "teams", {"name": "가상영업팀", "code": "T77A", "display_order": 1})
    T2 = ins(c, "teams", {"name": "가상구매팀", "code": "T77B", "display_order": 2})

    def user(nm, emp, team, phone, entity="KOR", active=1, role="member"):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, phone, entity, rank, email) "
                  "VALUES (?, ?, ?, ?, 'sso_only_no_local_password', ?, 1, ?, ?, ?, '프로', ?)", (nm, role, emp, emp, active, team, phone, entity, emp.lower() + "@example.test"))
        return dict(c.execute("SELECT * FROM users WHERE employee_no=?", (emp,)).fetchone())
    UA = user("가영업", "T771", T1, "010-1111-2222")
    UB = user("나영업", "T772", T1, "01033334444")
    UC = user("다구매", "T773", T2, "010 5555 6666")
    UV = user("반 끄엉", "VN771", T2, "0912 345 678", entity="VN")
    UX = user("퇴사자", "T779", T1, "010-9999-0000", active=0)
    UN = user("부서없음", "T778", None, "010-8888-7777")

    def ct(nm, by, vis="private", team=None, **kw):
        row = dict(name=nm, created_by=by, visibility=vis, share_team_id=team, source="manual")
        row.update(kw)
        return ins(c, "shared_contacts", row)
    A1 = ct("'썬텔제조1곽일용부장'", UA["id"], mobile=None, email="kiy102@example.test")          # 메일에서 들어온 따옴표 이름 · 휴대폰 없음
    A2 = ct("=?utf-8?B?JyLsnoTrs5HrrLgiJw==?=", UA["id"], company="가상상사", mobile="010-3308-5245")  # 인코딩 글자 이름
    A3 = ct("박부서", UA["id"], "dept", T1, company="가상고객", mobile="01077778888", phone="0212345678")
    A4 = ct("최전사", UA["id"], "company", None, company="가상협력", mobile="010-2222-3333")
    C1 = ct("정개인", UC["id"], mobile="010-4444-5555")
    C2 = ct("한구매부서", UC["id"], "dept", T2, mobile="010-6666-7777")
    C3 = ct("오전사", UC["id"], "company", None, mobile="010-8888-9999")

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app.contacts as CT  # noqa: E402
CUR = {"u": UA}
M.get_user = lambda request: CUR["u"]
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


def ids(html):
    return sorted(int(x) for x in re.findall(r'<tr data-id="(\d+)"', html))


def counts(html):
    return dict(re.findall(r'href="/contacts\?tab=(\w+)[^"]*"[^>]*>[^<]*(?:<small[^>]*>[^<]*</small>)?<span class="n">(\d+)</span>', html))


print("§1 책갈피 — 누가 무엇을 보나(개인 = 본인만 · 부서 = 우리 부서원 누구나 · 전사 = 회사 전체 누구나)")
CUR["u"] = UA
h = q(cl.get, "/contacts").text
check(counts(h) == {"all": "5", "private": "2", "dept": "1", "company": "2", "staff": "5"}, "가영업(영업팀): 전체 5 · 🔒 개인 2 · 👥 부서 1 · 🌐 전사 2 · 🏢 직원 5", counts(h))
check(ids(q(cl.get, "/contacts?tab=private").text) == sorted([A1, A2]), "🔒 개인 = 내가 등록한 개인 것만")
check(ids(q(cl.get, "/contacts?tab=dept").text) == [A3], "👥 부서 = 우리 부서(영업팀) 것")
check(ids(q(cl.get, "/contacts?tab=company").text) == sorted([A4, C3]), "🌐 전사 = 누가 등록했든 전사 공개")
CUR["u"] = UB
hb = q(cl.get, "/contacts").text
check(counts(hb)["private"] == "0" and ids(q(cl.get, "/contacts?tab=dept").text) == [A3] and ids(hb) == sorted([A3, A4, C3]),
      "나영업(같은 영업팀): 남의 개인은 안 보임 · 부서 것(박부서)은 보임 · 전사 보임", ids(hb))
CUR["u"] = UC
hc = q(cl.get, "/contacts").text
check(ids(hc) == sorted([C1, C2, C3, A4]) and A3 not in ids(hc), "다구매(구매팀): 영업팀 부서 것은 안 보임", ids(hc))
check('<small style="font-weight:600;">(가상구매팀)</small>' in hc, "부서 책갈피에 내 부서 이름")
CUR["u"] = UA

print("§2 보기 정리 — None · 이름 · 번호")
h = q(cl.get, "/contacts?tab=private").text
check(">None<" not in h and "None</td>" not in h, "빈 칸에 「None」이 안 찍힘(「—」)")
check("<b>썬텔제조1곽일용부장</b>" in h and "&#39;썬텔제조1곽일용부장&#39;" in h, "따옴표 이름 → 따옴표 빼고 보임(저장값은 그대로 · 마우스 올리면 원래 글)")
check(CT.display_name("=?utf-8?B?JyLsnoTrs5HrrLgiJw==?=") == '임병문' or "임병문" in CT.display_name("=?utf-8?B?JyLsnoTrs5HrrLgiJw==?="), "인코딩 글자 이름 → 풀어서 보임", CT.display_name("=?utf-8?B?JyLsnoTrs5HrrLgiJw==?="))
check([CT.phone_display(x) for x in ("01077778888", "0212345678", "021234567", "0311234567", "010-1234-5678", "0912 345 678", "+82 10 1234 5678")]
      == ["010-7777-8888", "02-1234-5678", "02-123-4567", "0311234567", "010-1234-5678", "0912 345 678", "+82 10 1234 5678"],
      "번호 보기: 한국 휴대폰·서울 번호만 010-7777-8888 · 02-1234-5678 (지역번호 10자리·베트남·해외·이미 맞는 것은 짐작 안 하고 그대로)")
hd = q(cl.get, "/contacts?tab=dept").text
check('<a class="cx-tel" href="tel:01077778888"' in hd and ">010-7777-8888</a>" in hd, "번호를 누르면 전화(tel:) · 보기는 010-7777-8888")
check(CT.tel_href("") == "" and CT.tel_href("+84 912 345 678") == "tel:+84912345678", "빈 번호는 전화 단추 없음 · 해외 번호 + 유지")

print("§3 전화번호 찾기 — 숫자만 · 뒷자리만")
for qq, want in (("33085245", [A2]), ("010-3308-5245", [A2]), ("5245", [A2]), ("010 7777", [A3]), ("12345678", [A3]), ("가상협력", [A4])):
    got = ids(q(cl.get, "/contacts", params={"q": qq}).text)
    check(got == want, "「%s」로 찾기 → %s" % (qq, want), got)
check(CT.phone_query_digits("가영업") == "" and CT.phone_query_digits("12") == "", "글자·두 자리 이하는 번호 찾기 안 함")

print("§4 고른 연락처 공유 범위 한 번에")
r = q(cl.post, "/contacts/bulk-share", json={"ids": [A1, C3], "visibility": "dept"}).json()
check(r["ok"] and r["done"] == 1 and r["skipped"] == 1 and "내가 등록하지 않은 1명" in r["message"], "가영업: 내 것 1명만 👥 부서로 · 남의 것(오전사)은 그대로", r)
with D.db_session() as c:
    row = dict(c.execute("SELECT visibility, share_team_id FROM shared_contacts WHERE id=?", (A1,)).fetchone())
    row3 = dict(c.execute("SELECT visibility FROM shared_contacts WHERE id=?", (C3,)).fetchone())
check(row == {"visibility": "dept", "share_team_id": T1} and row3["visibility"] == "company", "부서 = 바꾼 사람의 부서(영업팀)", (row, row3))
CUR["u"] = UB
check(A1 in ids(q(cl.get, "/contacts?tab=dept").text), "같은 부서 나영업에게 바로 보임")
CUR["u"] = UA
r = q(cl.post, "/contacts/bulk-share", json={"ids": [A1, A2], "visibility": "company"}).json()
check(r["ok"] and r["done"] == 2, "둘 다 🌐 전사로", r)
CUR["u"] = UC
check({A1, A2} <= set(ids(q(cl.get, "/contacts?tab=company").text)), "다른 부서 다구매에게도 보임")
CUR["u"] = UA
r = q(cl.post, "/contacts/bulk-share", json={"ids": [A2], "visibility": "private"}).json()
CUR["u"] = UC
check(r["ok"] and A2 not in ids(q(cl.get, "/contacts").text), "다시 🔒 개인으로 → 다구매에게서 사라짐")
CUR["u"] = UN
r = q(cl.post, "/contacts/bulk-share", json={"ids": [], "visibility": "dept"})
check(r.status_code == 400, "고른 것 없음 → 거절")
with D.db_session() as c:
    N1 = ins(c, "shared_contacts", {"name": "부서없는이의것", "created_by": UN["id"], "visibility": "private"})
r = q(cl.post, "/contacts/bulk-share", json={"ids": [N1], "visibility": "dept"}).json()
check(not r["ok"] and "소속 부서가 없어" in r["message"], "부서 없는 사람 → 👥 부서로 못 바꿈(안내)", r)
check(q(cl.post, "/contacts/bulk-share", json={"ids": [N1], "visibility": "all"}).status_code == 400, "이상한 범위 → 거절")
CUR["u"] = UA
h = q(cl.get, "/contacts").text
check('onclick="cxShareSelected(\'dept\')"' in h and "👥 우리 부서로" in h and "🌐 전사로" in h and "🔒 개인으로" in h, "도구 줄 「고른 N명 → 🔒 개인으로 · 👥 우리 부서로 · 🌐 전사로」")

print("§5 🏢 우리 회사 직원 — 인사 명부 그대로")
h = q(cl.get, "/contacts?tab=staff").text
names = re.findall(r"<tr><td><b>([^<]+)</b></td>", h)
check(sorted(names) == sorted(["가영업", "나영업", "다구매", "반 끄엉", "부서없음"]) and "퇴사자" not in h, "재직 직원만(퇴사자 빼고)", names)
check('<span class="cx-corp vn">KNK VINA</span>' in h and '<span class="cx-corp">KNK</span>' in h, "법인 KNK · KNK VINA 표시")
check('href="tel:01033334444"' in h and ">📞 010-3333-4444</a>" in h, "직원 번호도 누르면 전화 · 보기 정리")
check('id="cxTbl"' not in h and "cxShareSelected" not in h.split('id="cxStaff"')[0][-3000:], "직원 책갈피엔 삭제·공유 바꾸기 없음(읽기만)")
hs = q(cl.get, "/contacts", params={"tab": "staff", "q": "5555"}).text
check(re.findall(r"<tr><td><b>([^<]+)</b></td>", hs) == ["다구매"], "직원도 번호 뒷자리로 찾기(띄어쓰기 상관없이)")

print("§6 휴대폰 저장(vCard) = 지금 책갈피 것만")
v = q(cl.get, "/contacts/vcards.vcf?tab=company")
check(v.status_code == 200 and "최전사" in v.text and "정개인" not in v.text and "박부서" not in v.text, "🌐 전사 책갈피 → 전사 것만", v.text.count("BEGIN:VCARD"))
v2 = q(cl.get, "/contacts/vcards.vcf?tab=staff")
check("FN:반 끄엉" in v2.text and "퇴사자" not in v2.text and "ORG:KNK VINA" in v2.text, "🏢 직원 책갈피 → 직원 명부 vCard")
v3 = q(cl.get, "/contacts/vcards.vcf")
check("FN:썬텔제조1곽일용부장" in v3.text, "vCard 이름도 따옴표 빼고")
check('href="/contacts/vcards.vcf?tab=company"' in q(cl.get, "/contacts?tab=company").text, "책갈피의 「휴대폰에 저장」 링크 = 그 책갈피")

print("§7 상세 화면 None 안 보이게")
hd = q(cl.get, "/contacts/%d" % A3).text
check(q(cl.get, "/contacts/%d" % A3).status_code == 200 and ">None<" not in hd, "상세 화면에도 「None」 없음")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
