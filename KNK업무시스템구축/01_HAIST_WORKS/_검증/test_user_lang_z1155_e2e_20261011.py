#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1155 통짜 시험 — 사람마다의 WORKS 언어 = 이음 메신저에서 고른 언어 · 한국어·베트남어 (대표 2026-10-10).

`test_user_lang_z1155_20261011.py` 는 함수를 하나씩 본다. 이 파일은 **앱을 통째로 띄워** 진짜 주소로 들어간다.

  §1 「내 프로필」(/me · /profile) — 언어는 보여 주기만 · 베트남어인 사람이 이메일만 고쳐 저장해도 vi 그대로
  §2 언어 바꾸기 주소(/api/set-lang) — 한국어·베트남어만 · 모르는 값은 아무것도 안 바꾸고 거절
  §3 번역되는 화면(견적서 인쇄) — 사람 언어대로 말이 바뀐다 · 옛 en 값은 한국어 · 문서 언어(?lang=en)는 그대로
  §4 관리자 「메신저 직원 동기화」 — 미리보기에 바뀌는 사람 · 적용하면 DB · 되돌려 바꾸기(vi→ko)
  §5 새벽 자동 동기화 — 기록(로그)에 이름·사번·전→후

⛔ 운영 DB·운영 이음을 열지 않는다(임시 DB · 이음 응답은 가짜). 실명 없음(가상 자료).
   fastapi 가 깔린 파이썬이 필요하다.

실행:  python _검증/test_user_lang_z1155_e2e_20261011.py
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1155-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1155_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
D.init_db()
# 운영 users 엔 있는데 코드(SCHEMA+마이그레이션)가 안 만드는 칸 — 운영과 같은 모양으로 맞춘다
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))

import app.main as appmain                                 # noqa: E402
from app import sso_client as SC                           # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

CUR = {"id": None}


def _get_user(request):
    if not CUR["id"]:
        return None
    with D.db_session() as c:
        r = c.execute("SELECT * FROM users WHERE id=? AND is_active=1", (CUR["id"],)).fetchone()
    return dict(r) if r else None


appmain.get_user = _get_user
cl = TestClient(appmain.app, follow_redirects=False)

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  ✅" if ok else "  ❌") + " %02d %s" % (CNT, name) + ("" if ok else "   ← %s" % (detail,)))
    if not ok:
        FAIL.append(name)


def lang_of(uid):
    with D.db_session() as c:
        return c.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()["lang"]


def set_lang(uid, v):
    with D.db_session() as c:
        c.execute("UPDATE users SET lang=? WHERE id=?", (v, uid))


# ── 가상 자료 ─────────────────────────────────────────────────────────
#   id, 이름, 사번, lang, 법인, role, 영업권한
PEOPLE = [
    (901, "시험관리자", "900", "ko", "KOR", "admin", 1),
    (902, "가법인장", "VN001", "vi", "VN", "member", 1),     # 한국 직원인데 vi(실측 5명의 모양) — 이음에선 ko
    (903, "나베트남", "VN265", "ko", None, "member", 0),     # 베트남 직원인데 ko(실측 26명의 모양) — 이음에선 vi
    (904, "다본사", "101", "ko", "KOR", "member", 1),
    (905, "라옛값", "102", "zh", "KOR", "member", 0),         # 목록 밖 옛 값
    (906, "마영어", "103", "en", "KOR", "member", 1),         # 옛 en 값
]
with D.db_session() as conn:
    for uid, name, eno, lang, ent, role, sales in PEOPLE:
        conn.execute("INSERT INTO users(id, name, login_id, password, role, lang, employee_no, entity, email, can_use_sales) "
                     "VALUES(?,?,?,'x',?,?,?,?,?,?)", (uid, name, eno, role, lang, eno, ent, "u%d@t.test" % uid, sales))
    conn.execute("INSERT INTO customers(id, name) VALUES(77, '시험고객(주)')")
    conn.execute("INSERT INTO quotations(id, quote_no, customer_id, total_amount, status, created_by) "
                 "VALUES(55, 'QT-202610-0001', 77, 1000000, 'DRAFT', 901)")

# ════════════════════════════════════════════════════════════════════
print("\n§1 「내 프로필」 — 언어는 보여 주기만")
CUR["id"] = 902
r = cl.get("/me")
h = r.text
check("vi 인 사람이 /me 를 열면 200", r.status_code == 200, r.status_code)
check("언어 칸에 「Tiếng Việt」이 보인다(고친 뒤엔 보여 주기만)",
      re.search(r'value="Tiếng Việt"\s+disabled[^>]*data-z1155-lang', h) is not None)
check("언어를 바꾸는 칸(name=\"lang\")이 없다 — 대표 결정 「이음 따름 표시만」", 'name="lang"' not in h)
check("안내: 이음 「🟢 내 상태」 → 「언어 / Language」(이음의 한국어 글자 그대로)",
      "「🟢 내 상태」 → 「언어 / Language」" in h)
check("안내: 베트남어 화면 글자도(「🟢 Trạng thái của tôi」 → 「Ngôn ngữ / Language」)",
      "「🟢 Trạng thái của tôi」 → 「Ngôn ngữ / Language」" in h)
CUR["id"] = 904
check("ko 인 사람은 「한국어」", 'value="한국어"' in cl.get("/profile").text)
CUR["id"] = 905
check("목록 밖 옛 값(zh)은 숨기지 않고 「zh (목록에 없음 · 화면은 한국어)」",
      'value="zh (목록에 없음 · 화면은 한국어)"' in cl.get("/profile").text)

CUR["id"] = 902
r = cl.post("/me", data={"email": "new902@t.test", "phone": "010-1", "dept": "총괄", "lang": "ko"})
with D.db_session() as c:
    em = c.execute("SELECT email FROM users WHERE id=902").fetchone()["email"]
check("🔴 vi 인 사람이 이메일만 고쳐 저장 → 저장됨(303) · 이메일 바뀜", r.status_code == 303 and em == "new902@t.test",
      (r.status_code, em))
check("🔴 그래도 언어는 vi 그대로 — 옛 화면이 lang=ko 를 실어 보내도(지시서 검증 2번)", lang_of(902) == "vi", lang_of(902))
CUR["id"] = 904
cl.post("/me", data={"email": "u904@t.test", "lang": "vi"})
check("ko 인 사람이 lang=vi 를 보내도 /me 는 언어를 안 바꾼다(이음 따름)", lang_of(904) == "ko", lang_of(904))

# ════════════════════════════════════════════════════════════════════
print("\n§2 언어 바꾸기 주소 /api/set-lang — 한국어·베트남어만")
CUR["id"] = 904
for body, what in [({"lang": "zh"}, "zh"), ({"lang": "en"}, "en"), ({}, "빈 값")]:
    r = cl.post("/api/set-lang", json=body)
    check("POST %s → 400 · 아무것도 안 바뀜(ko 그대로)" % what, r.status_code == 400 and lang_of(904) == "ko",
          (r.status_code, lang_of(904)))
r = cl.post("/api/set-lang", json={"lang": "vi"})
check("POST vi → 200 · vi", r.status_code == 200 and r.json().get("lang") == "vi" and lang_of(904) == "vi",
      (r.status_code, lang_of(904)))
r = cl.get("/api/set-lang?lang=ko", headers={"referer": "/profile"})
check("GET ?lang=ko → 303(보던 화면으로) · ko — 한국어로 되돌리기(지시서 검증 3번)",
      r.status_code == 303 and r.headers.get("location") == "/profile" and lang_of(904) == "ko",
      (r.status_code, r.headers.get("location"), lang_of(904)))
r = cl.get("/api/set-lang?lang=zh")
check("GET ?lang=zh → 303 · 아무것도 안 바뀜", r.status_code == 303 and lang_of(904) == "ko", (r.status_code, lang_of(904)))
r = cl.get("/api/set-lang")
check("GET 언어 없이 → 303 · 아무것도 안 바뀜(예전엔 한국어로 덮었다)", r.status_code == 303 and lang_of(904) == "ko",
      (r.status_code, lang_of(904)))

# ════════════════════════════════════════════════════════════════════
print("\n§3 번역되는 화면 — 견적서 인쇄(번역 사전을 실제로 쓰는 유일한 화면)")
CUR["id"] = 902
h = cl.get("/sales/quotations/55/print").text
check("vi 인 사람 → 베트남어(← Danh sách báo giá)", "← Danh sách báo giá" in h)
CUR["id"] = 904
h = cl.get("/sales/quotations/55/print").text
check("ko 인 사람 → 한국어(← 견적 목록)", "← 견적 목록" in h)
CUR["id"] = 906
h = cl.get("/sales/quotations/55/print").text
check("옛 en 값인 사람 → 한국어(사람 언어는 한국어·베트남어만)", "← 견적 목록" in h and "← Quotation List" not in h)
h = cl.get("/sales/quotations/55/print?lang=en").text
check("문서 언어 고르기(?lang=en)는 그대로 — 고객에게 내는 영문 견적서", "← Quotation List" in h)

# ════════════════════════════════════════════════════════════════════
print("\n§4 관리자 「메신저 직원 동기화」 — 이음 언어를 사람마다 옮긴다")


class FakeResp:
    def __init__(self, users):
        self.status_code = 200
        self._j = {"users": users, "count": len(users), "source": "knk-messenger"}

    def json(self):
        return self._j


def directory(langs):
    """지금 DB 의 사번 있는 사람 전원 + 이음 언어(langs 에 없으면 lang 칸을 아예 안 싣는다 = 지금 이음)."""
    out = []
    with D.db_session() as c:
        for r in c.execute("SELECT name, employee_no FROM users WHERE COALESCE(TRIM(employee_no),'')<>''"):
            u = {"employee_no": r["employee_no"], "name_kr": r["name"], "name_en": None, "name_vi": None,
                 "dept": None, "position": None, "entity": None, "email": None, "phone": None,
                 "is_admin": False, "works_access": True, "active": True, "status": "online"}
            if r["employee_no"] in langs:
                u["lang"] = langs[r["employee_no"]]
            out.append(u)
    return out


_real_get = SC.httpx.get
try:
    set_lang(905, "ko")
    set_lang(906, "ko")
    EUM = {"900": "ko", "VN001": "ko", "VN265": "vi", "101": "ko", "102": "ko", "103": "ko"}
    SC.httpx.get = lambda *a, **k: FakeResp(directory(EUM))
    CUR["id"] = 901
    r = cl.get("/admin/sync-employees")
    h = r.text
    check("미리보기 화면 200", r.status_code == 200, r.status_code)
    check("미리보기에 「🌐 언어가 바뀌는 사람 (2명)」", "🌐 언어가 바뀌는 사람 (2명)" in h)
    check("  가법인장(VN001) Tiếng Việt → 한국어 · 나베트남(VN265) 한국어 → Tiếng Việt (국기 없는 이름표)",
          "가법인장(VN001) Tiếng Việt → 한국어" in h and "나베트남(VN265) 한국어 → Tiếng Việt" in h)
    check("동기화 안내문에 언어 줄(「언어는 사람마다 이음 메신저에서 고른 언어로」)",
          "<b>언어</b>는 사람마다 <b>이음 메신저에서 고른 언어</b>로 맞춥니다" in h)
    check("미리보기는 DB 를 안 바꾼다", lang_of(902) == "vi" and lang_of(903) == "ko", (lang_of(902), lang_of(903)))
    r = cl.post("/admin/sync-employees", data={"confirm": "직원동기화"})
    h = r.text
    check("적용 → DB 가 이음 값으로(VN001 ko · VN265 vi)", lang_of(902) == "ko" and lang_of(903) == "vi",
          (r.status_code, lang_of(902), lang_of(903)))
    check("적용 결과에 「언어 바뀜(이음 설정을 따름): 2명」", "언어 바뀜(이음 설정을 따름)</b>: <b>2</b>명" in h)
    # 그 사람이 이음에서 다시 바꾸면(vi→ko) 다음 동기화 때 WORKS 도 되돌아간다
    EUM["VN265"] = "ko"
    r = cl.post("/admin/sync-employees", data={"confirm": "직원동기화"})
    check("이음에서 vi→ko 로 바꾸면 다음 동기화 때 WORKS 도 ko(되돌아갈 길)", lang_of(903) == "ko", lang_of(903))
    # 이음이 아직 언어를 안 보내면(지금 이음) 아무도 안 바뀐다
    set_lang(903, "vi")
    SC.httpx.get = lambda *a, **k: FakeResp(directory({}))
    r = cl.post("/admin/sync-employees", data={"confirm": "직원동기화"})
    check("이음이 언어를 안 보내면(지금 이음) 아무도 안 바뀐다 → WORKS 먼저 배포해도 안전",
          lang_of(903) == "vi" and "언어 바뀜" not in r.text, (lang_of(903),))

    # ════════════════════════════════════════════════════════════════
    print("\n§5 새벽 자동 동기화 — 기록에 이름·사번·전→후")
    SC.httpx.get = lambda *a, **k: FakeResp(directory({"VN265": "ko"}))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        appmain._run_directory_autosync()
    log = buf.getvalue()
    check("새벽 동기화가 이음 값으로(VN265 vi→ko)", lang_of(903) == "ko", lang_of(903))
    check("기록: [DIR-SYNC] 언어 바뀜(이음 따름) 1명: 나베트남(VN265) vi→ko",
          "[DIR-SYNC] 언어 바뀜(이음 따름) 1명: 나베트남(VN265) vi→ko" in log, log[-400:])
    check("기존 기록 줄(신고·갱신·삭제·보류)은 그대로", "[DIR-SYNC] 자동 명부 동기화 완료 — 신규" in log)
finally:
    SC.httpx.get = _real_get

print("\n" + "=" * 60)
print("결과: %d개 중 실패 %d" % (CNT, len(FAIL)))
for n in FAIL:
    print("  ❌", n)
sys.exit(1 if FAIL else 0)
