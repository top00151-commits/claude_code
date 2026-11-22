# -*- coding: utf-8 -*-
"""웍스 「회사 정보」 화면 저장 고장 (대표 2026-11-22 「①번으로 진행해」 · 세션 15) — 운영 무접촉 · 임시 DB.

까닭(고치기 전)
  ① 화면이 저장 요청을 없는 주소(/admin/company)로 보냄
  ② 입력 칸 이름이 모두 빈 값 — 서버는 (키, 이름, 기본값) 묶음을 넘기는데 화면은 k.key 를 찾음 · 서버는 k_ 로 시작하는 이름만 저장
  → 6월 화면 개편 뒤 회사 주소·대표 전화·팩스가 들어간 적 없음(메일 회사 서명 · 견적서 머리글이 이 값을 씀)
증명할 것
  ① 화면: 저장 주소 = /admin/company-info · 칸 10개 이름 = k_키 · 빈 이름 없음 · 비었을 때 쓰이는 기본값은 흐린 글씨
  ② 대표·관리자가 저장 → 값이 들어가고 회사 정보로 읽힘 · 메일 회사 서명도 그 값을 먼저 씀
  ③ 정해진 칸만 저장(모르는 칸 무시) · 직원은 저장 못 함 · 비우면 기본값으로
"""
import io
import os
import re
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
os.environ["KNK_RUN_MAIL_FETCH"] = "0"

_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mci_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_guide as mg
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


with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x'")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(9901,'t_ceo','시험대표','대표이사','ceo',1,'x','ceo-t@knknara.co.kr')")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(9902,'t_mem','시험직원','사원','member',1,'x','mem-t@knknara.co.kr')")
    c.execute("DELETE FROM app_settings WHERE key LIKE 'company_%'")
WHO = {"v": {"id": 9901, "role": "ceo", "name": "시험대표", "rank": "대표이사", "login_id": "t_ceo", "email": "ceo-t@knknara.co.kr", "lang": "ko"}}
m.get_user = lambda req: WHO["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

print("① 화면")
h = k.get("/admin/company-info").text
_fi = h.find('class="cfg-form"')
form = h[h.rfind("<form", 0, _fi):h.find("</form>", _fi)] if _fi > 0 else ""   # 공통 틀의 다른 form(빅터 묻기) 말고 회사 정보 form
names = re.findall(r'<input[^>]*\bname="([^"]*)"', form)
check("저장 주소 = /admin/company-info(예전 = 없는 /admin/company)", 'action="/admin/company-info"' in form and 'action="/admin/company"' not in form, form[:120])
check("칸 10개 이름 = k_키 · 빈 이름 없음", len(names) == len(m.COMPANY_INFO_KEYS) and all(n == "k_" + key for n, (key, _l, _d) in zip(names, m.COMPANY_INFO_KEYS)), names)
check("칸 이름표 = 화면 이름(대표 전화 · 팩스 · 회사 주소)", "대표 전화</label>" in form and "팩스</label>" in form and "회사 주소</label>" in form)
check("비었을 때 쓰이는 기본값 = 흐린 글씨(회사명 국문)", 'placeholder="주식회사 케이엔케이 (KNK)"' in form)

print("② 저장")
r = k.post("/admin/company-info", data={"k_company_tel": "02-000-0000", "k_company_fax": "02-000-0001",
                                        "k_company_address": "서울시 시험구 시험로 1", "k_company_address_en": "1, Test-ro, Seoul",
                                        "k_not_a_key": "몰래", "company_tel": "접두어 없음"})
check("저장 → 회사 정보 화면으로(저장 수 표시)", r.status_code == 303 and "/admin/company-info?saved=4" in r.headers.get("location", ""), (r.status_code, r.headers.get("location")))
ci = m._company_info_dict()
check("회사 정보로 읽힘(대표 전화·팩스·주소·영문 주소)", ci["company_tel"] == "02-000-0000" and ci["company_fax"] == "02-000-0001"
      and ci["company_address"] == "서울시 시험구 시험로 1" and ci["company_address_en"] == "1, Test-ro, Seoul", ci)
check("정해진 칸만 저장(모르는 칸·접두어 없는 칸 무시)", _db.get_setting("not_a_key", "") == "" and _db.get_setting("company_tel", "") == "02-000-0000")
h2 = k.get("/admin/company-info?saved=4").text
check("다시 열면 넣은 값이 칸에 보임 · 저장 알림", 'name="k_company_tel" value="02-000-0000"' in h2 and "✓ 저" in h2)
with _db.db_session() as c:
    v = mg.values_for(c, 9901, "ko", m._company_info_dict(), m.rank_label, "")
check("메일 회사 서명 = 회사 정보 값 먼저(대표번호 기본값보다)", v["tel"] == "02-000-0000" and v["fax"] == "02-000-0001" and v["address"] == "서울시 시험구 시험로 1", v)

print("③ 권한 · 비우기")
WHO["v"] = {"id": 9902, "role": "member", "name": "시험직원", "rank": "사원", "login_id": "t_mem", "email": "mem-t@knknara.co.kr", "lang": "ko"}
r = k.post("/admin/company-info", data={"k_company_tel": "몰래 바꿈"})
check("직원은 저장 못 함(로그인 화면으로) · 값 그대로", r.status_code == 303 and "/login" in r.headers.get("location", "") and m._company_info_dict()["company_tel"] == "02-000-0000")
check("직원은 화면도 못 엶", k.get("/admin/company-info").status_code == 303)
WHO["v"] = {"id": 9901, "role": "ceo", "name": "시험대표", "rank": "대표이사", "login_id": "t_ceo", "email": "ceo-t@knknara.co.kr", "lang": "ko"}
k.post("/admin/company-info", data={"k_company_tel": "", "k_company_name_ko": ""})
ci = m._company_info_dict()
check("비우면 기본값으로(회사명 국문 = 기본값 · 대표 전화 = 빈 값)", ci["company_name_ko"] == "주식회사 케이엔케이 (KNK)" and ci["company_tel"] == "", ci)
with _db.db_session() as c:
    v = mg.values_for(c, 9901, "ko", m._company_info_dict(), m.rank_label, "")
check("회사 정보 대표 전화를 비우면 메일 서명 = 회사 대표번호(031-8009-0407)", v["tel"] == "031-8009-0407", v["tel"])

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
