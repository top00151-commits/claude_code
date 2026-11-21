# -*- coding: utf-8 -*-
"""메일 3단계(대표 2026-11-20 「다음 진행해」) — ⑧ 🏢 회사 공통 서명 틀 · ⑨ 처음 안내 + 인쇄용 설명서(한국어).
운영 무접촉 · 임시 DB(knk_ms3c_*) · 가짜 사람·가짜 회사 정보만. 베트남어는 대표 지시(11-20 「베트남어는 아직 진행하지마」)로 보류 → 화면에 안 나오는지 봄.

증명할 것
  ⑧ 채우기: 「이름 직책 부서」 첫 줄 · 본사 = 웍스 회사 정보 · 베트남 법인 = KNK VINA(주소·전화 칸 없음 → 그 줄 빼고 안내)
     · 빈 값 줄은 통째로 · 「 · 」 토막은 빈 것만 빼기 · 영어 틀 = 직책 영어 · 값은 HTML 로 안전하게(꺾쇠 그대로 안 나감)
     · 쓰기 화면 「✍」 고르기에 「🏢 회사 서명」 · 서명 화면 「🏢 회사 서명 쓰기」
  ⑧ 틀 저장은 관리자만: 직원 화면 = 서명 화면으로 · 저장·미리 보기 403 · 틀 바꾸면 직원 것도 바뀜 · 끄기 · 기본으로 · 빈 틀 거절 · 꺾쇠 지움
  웍스 직원·회사 표(users · teams · app_settings)는 바뀌지 않음(읽기만)
  ⑨ 처음 안내: 처음엔 보임 · 「다시 보지 않기」 = 서버 사용자별(다른 사람은 그대로) · 다시 켜기 · 맡기기 장은 시험 명단만
     · 메일 머리에 안내·「🎓 처음 안내 다시 보기」·「🖨 설명서(인쇄용)」
  ⑨ 설명서: 200 · 한국어 · 인쇄 때 메뉴 숨김 · A4 · 베트남어 없음(사용자 말이 vi 여도) · 맡기기는 시험 명단에게만
     · 설명서·안내의 단추 이름 = 실제 템플릿 글자
"""
import ast
import io
import json
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
    _TMP = tempfile.mkdtemp(prefix="knk_ms3c_")
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


VI_CH = re.compile(r"[ạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđĐơưƠƯ]")

with _db.db_session() as c:
    for ddl in ("ALTER TABLE users ADD COLUMN employee_no TEXT", "ALTER TABLE users ADD COLUMN phone TEXT",
                "ALTER TABLE users ADD COLUMN entity TEXT", "ALTER TABLE users ADD COLUMN name_en TEXT"):
        try:
            c.execute(ddl)
        except Exception:
            pass
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id IN ('kjr')")
    c.execute("INSERT INTO teams(id, code, name, display_order, entity) VALUES(9801,'T9801','시험품질팀',3,'KOR')")
    c.execute("INSERT INTO teams(id, code, name, display_order, entity) VALUES(9802,'V9802','시험구매팀',60,'VN')")
    ppl = [  # id, login, 이름, 역할, 사번, 부서, 직책, 휴대폰, 영문 이름, 말
        (9801, "kjr", "시험대표", "ceo", "5", 9801, "대표이사", "010-1111-2222", "Test Ceo", "ko"),
        (9802, "t1102", "조민혁", "member", "1102", 9801, "과장", "010-3333-4444", "", "ko"),
        (9803, "tvn201", "쩐티하", "member", "VN201", 9802, "", "", "", "vi"),
        (9804, "t777", "<b>꺾쇠</b>", "member", "777", None, "", "", "", "ko"),
        (9805, "tadm", "시험관리자", "admin", "888", 9801, "부장", "", "", "ko"),
    ]
    for uid, lid, nm, role, emp, team, rank, ph, ne, lg in ppl:
        c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id, rank, employee_no, phone, name_en, lang) "
                  "VALUES(?,?,?,?,1,'x',?,?,?,?,?,?,?)", (uid, lid, nm, role, lid + "@knknara.co.kr", team, rank, emp, ph, ne, lg))
    for kk, vv in (("company_name_ko", "주식회사 시험회사"), ("company_name_en", "Test Co., Ltd."),
                   ("company_address", "경기도 시험시 시험로 1"), ("company_tel", "031-000-0000"), ("company_fax", "")):
        c.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES(?,?)", (kk, vv))
U = {k: {"id": p[0], "role": p[3], "name": p[2], "team_id": p[5], "team_name": "", "employee_no": p[4], "rank": p[6],
         "login_id": p[1], "email": p[1] + "@knknara.co.kr", "lang": p[9]}
     for k, p in zip(("ceo", "jo", "vn", "odd", "adm"), ppl)}
_U = {"v": dict(U["ceo"])}
m.get_user = lambda req: _U["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
km = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
km.headers.update({"host": "kmail.knknara.co.kr", "x-forwarded-proto": "https"})


def as_(key):
    _U["v"] = dict(U[key])


def snap_works():
    with _db.db_session() as c:
        return json.dumps([[dict(r) for r in c.execute("SELECT * FROM users ORDER BY id").fetchall()],
                           [dict(r) for r in c.execute("SELECT * FROM teams ORDER BY id").fetchall()],
                           [dict(r) for r in c.execute("SELECT * FROM app_settings ORDER BY key").fetchall()]],
                          ensure_ascii=False, default=str)


SNAP0 = snap_works()
CO = m._company_info_dict()


def sigs(key, lang="ko"):
    with _db.db_session() as c:
        v = mg.values_for(c, U[key]["id"], lang, CO, m.rank_label, "")
        return v, mg.fill(mg.get_templates(c)[lang]["body"], v)


# ═══════════════════════ ⑧ 채우기 ═══════════════════════
print("\n⑧ 회사 서명 채우기")
v, f = sigs("jo")
lines = f["text"].split("\n")
check("첫 줄 = 「이름 직책 부서」(웍스 직원 명단)", lines[0] == "조민혁 과장 시험품질팀", lines)
check("본사 = 웍스 회사 정보(회사 이름·주소·전화)", "주식회사 시험회사" in lines and "경기도 시험시 시험로 1" in lines and "T. 031-000-0000" in lines, lines)
check("팩스가 비면 그 토막만 뺌(전화는 남음)", "F." not in f["text"] and "T. 031-000-0000" in f["text"], f["text"])
check("휴대폰·메일 = 직원 명단", "M. 010-3333-4444 · E. t1102@knknara.co.kr" in lines, lines)
check("빈 칸 안내 = 팩스 · 웍스 회사 정보", ("팩스", "웍스 회사 정보") in f["missing"] and "팩스" in mg.missing_note(f["missing"], "kr"), f["missing"])
check("첫 줄 굵게 · 줄바꿈 <br>", f["html"].startswith("<b>조민혁 과장 시험품질팀</b><br>"), f["html"][:80])

v, f = sigs("vn")
check("베트남 법인(사번 VN…) → 회사 = KNK VINA Co., Ltd.", v["_corp"] == "vn" and "KNK VINA Co., Ltd." in f["text"], f["text"])
check("베트남 법인 → 본사 주소·전화 안 들어감 · 그 줄 빼고 안내", "경기도" not in f["text"] and "031-000-0000" not in f["text"]
      and "베트남 법인 것은 웍스 회사 정보에 아직 칸이 없어" in mg.missing_note(f["missing"], "vn"), (f["text"], f["missing"]))
check("직책 비면 첫 줄은 「이름 부서」(빈칸 한 칸)", f["text"].split("\n")[0] == "쩐티하 시험구매팀", f["text"])
check("휴대폰 없음 → 「M.」 토막만 빠지고 메일은 남음", "M." not in f["text"] and "E. tvn201@knknara.co.kr" in f["text"], f["text"])

v, f = sigs("odd")
check("이름의 꺾쇠는 HTML 로 안전하게(태그로 안 들어감)", "&lt;b&gt;꺾쇠&lt;/b&gt;" in f["html"] and "<b><b>" not in f["html"], f["html"])
check("부서 없는 사람 → 첫 줄 = 이름만", f["text"].split("\n")[0] == "<b>꺾쇠</b>", f["text"])

v, f = sigs("jo", "en")
check("영어 틀 = 직책 영어(과장 → Manager) · 회사 영문 이름", f["text"].split("\n")[0].startswith("조민혁 Manager") and "Test Co., Ltd." in f["text"], f["text"])
check("영문 주소 비면 그 줄 빼고 안내(한국어 주소 섞지 않음)", "경기도" not in f["text"] and ("주소", "웍스 회사 정보") in f["missing"], f["text"])
v, f = sigs("ceo", "en")
check("영문 이름이 있으면 영어 틀에 영문 이름", f["text"].startswith("Test Ceo"), f["text"][:40])
check("자리 값이 모두 빈 줄은 통째로 빠짐", mg.fill("A\n{팩스}\nB", {"fax": ""})["text"] == "A\nB")

# ═══════════════════════ ⑧ 화면 ═══════════════════════
print("\n⑧ 쓰기 화면 · 서명 화면")
as_("jo")
cp = k.get("/mail/compose").text
check("쓰기 화면 「✍」 고르기에 「🏢 회사 서명 (한국어)」·「(English)」", 'value="co-ko">🏢 회사 서명 (한국어)<' in cp and 'value="co-en">🏢 회사 서명 (English)<' in cp, cp[:0])
mm = re.search(r"window\.CMP_SIGS = (\[.*?\]);", cp)
cs = json.loads(mm.group(1)) if mm else []
check("고르면 넣을 회사 서명 = 내 정보로 채운 것", any(x.get("slot") == "co-ko" and "조민혁 과장 시험품질팀" in x.get("body", "") for x in cs), cs[:1])
sp = k.get("/mail/signature").text
check("서명 화면: 「🏢 회사 서명 쓰기」 + 미리 보기 + 빈 칸 안내", "🏢 회사 서명 쓰기" in sp and "조민혁 과장 시험품질팀" in sp and "팩스 — 웍스 회사 정보에 비어 있어 뺐습니다" in sp, "")
check("직원에겐 「🔧 회사 서명 틀 고치기」 없음", "/mail/signature/company" not in sp)
as_("ceo")
check("대표에겐 「🔧 회사 서명 틀 고치기(관리자)」", "🔧 회사 서명 틀 고치기(관리자)" in k.get("/mail/signature").text)

# ═══════════════════════ ⑧ 관리자만 ═══════════════════════
print("\n⑧ 틀 저장 = 관리자만")
as_("jo")
r = k.get("/mail/signature/company")
check("직원이 틀 화면 → 내 서명 화면으로(303)", r.status_code == 303 and r.headers.get("location", "").endswith("/mail/signature"), r.status_code)
r = k.post("/mail/signature/company", data={"lang": "ko", "body": "해킹 {이름}", "mode": "save"})
check("직원 저장 → 403", r.status_code == 403, r.status_code)
check("직원 미리 보기 → 403", k.post("/api/mail/company-sig/preview", data={"lang": "ko", "body": "x"}).status_code == 403)
with _db.db_session() as c:
    check("직원 저장 시도 뒤 틀은 그대로(기본 틀)", not mg.get_templates(c)["ko"]["custom"])
as_("adm")
r = k.get("/mail/signature/company")
check("관리자(admin) 틀 화면 200 · 자리 단추 · 웍스 회사 정보 안내", r.status_code == 200 and "{휴대폰}" in r.text and "웍스 「회사 정보」에서 고치기" in r.text, r.status_code)
_mn = r.text[r.text.find('<main'):r.text.find('</main>')]   # 웍스 공통 틀(chrome.html 앱 설치 안내)의 원래 글은 빼고 이 화면 본문만
check("틀 화면 본문에 베트남어 없음(보류)", _mn and not VI_CH.search(_mn) and "Tiếng" not in _mn, VI_CH.findall(_mn)[:5])
r = k.post("/api/mail/company-sig/preview", data={"lang": "ko", "body": "{이름} / {직책}\n{없는칸}\n{팩스}"})
j = r.json()
check("미리 보기 = 관리자 본인 정보 · 저장 안 함", j.get("ok") and "시험관리자 / 부장" in j.get("html", ""), j)
r = k.post("/mail/signature/company", data={"lang": "ko", "body": "<script>x</script>{회사} | {이름} {직책}\n☎ {전화}", "mode": "save"})
check("관리자 저장 200", r.status_code == 200 and r.json().get("ok"), r.text)
with _db.db_session() as c:
    t = mg.get_templates(c)["ko"]
check("틀은 글자만 — 꺾쇠(태그) 지움 · 회사가 정한 틀로 표시", t["custom"] and "<script>" not in t["body"] and t["body"].startswith("x{회사}"), t)
as_("jo")
cs2 = json.loads(re.search(r"window\.CMP_SIGS = (\[.*?\]);", k.get("/mail/compose").text).group(1))
ko2 = [x for x in cs2 if x.get("slot") == "co-ko"]
check("틀을 바꾸면 직원 쓰기 화면 회사 서명도 바뀜", ko2 and "x주식회사 시험회사 | 조민혁 과장" in ko2[0]["body"] and "☎ 031-000-0000" in ko2[0]["body"], ko2)
as_("adm")
check("빈 틀 저장 → 400(끄기는 따로)", k.post("/mail/signature/company", data={"lang": "en", "body": "  ", "mode": "save"}).status_code == 400)
check("영어 「이 말은 쓰지 않기」", k.post("/mail/signature/company", data={"lang": "en", "mode": "off"}).json().get("ok"))
as_("jo")
cp3 = k.get("/mail/compose").text
check("끈 말은 직원 화면에서 빠짐 · 하나만 남으면 이름은 「🏢 회사 서명」", 'value="co-en"' not in cp3 and 'value="co-ko">🏢 회사 서명<' in cp3)
as_("adm")
check("모르는 말 → 400", k.post("/mail/signature/company", data={"lang": "vi", "body": "{이름}", "mode": "save"}).status_code == 400)
check("기본 틀로 되돌리기", k.post("/mail/signature/company", data={"lang": "ko", "mode": "default"}).json().get("ok"))
with _db.db_session() as c:
    tt = mg.get_templates(c)
check("되돌린 뒤 한국어 = 기본 틀 · 영어 = 꺼짐", (not tt["ko"]["custom"]) and tt["ko"]["body"] == mg.DEFAULT["ko"] and not tt["en"]["on"], tt)
check("웍스 직원·부서·회사 정보 표는 그대로(읽기만)", snap_works() == SNAP0)

# ═══════════════════════ ⑨ 처음 안내 ═══════════════════════
print("\n⑨ 처음 안내")
as_("jo")
j = k.get("/api/mail/tour").json()
check("처음엔 보임 · 맡기기 장 없음(시험 명단 아님)", j.get("ok") and j.get("show") is True and j.get("dl") is False, j)
check("「다시 보지 않기」 저장", k.post("/api/mail/tour", data={"seen": "1"}).json().get("seen") is True)
check("다시 물으면 안 보임(서버에 저장)", k.get("/api/mail/tour").json().get("show") is False)
with _db.db_session() as c:
    row = c.execute("SELECT value FROM mail_user_prefs WHERE user_id=9802 AND key='tour_seen'").fetchone()
check("저장 자리 = 서버 표 mail_user_prefs(사용자별)", row and row[0] == "1", row)
as_("ceo")
j = k.get("/api/mail/tour").json()
check("다른 사람은 그대로 보임 · 시험 명단(대표)은 맡기기 장 포함", j.get("show") is True and j.get("dl") is True, j)
as_("jo")
k.post("/api/mail/tour", data={"seen": "0"})
check("다시 켜기(seen=0) → 다시 보임", k.get("/api/mail/tour").json().get("show") is True)
hd = km.get("/mail/inbox").text
check("메일 앱 머리에 처음 안내·「🎓 처음 안내 다시 보기」·「🖨 설명서(인쇄용)」", 'id="mailTour"' in hd and "🎓 처음 안내 다시 보기" in hd and 'href="/mail/help"' in hd, len(hd))
check("처음 안내는 받은편지함에서만 저절로 · 이번만 닫기 = 이 창(sessionStorage)", "location.pathname.indexOf('/mail/inbox')===0" in hd and "knkmail.tour.closed" in hd)
check("안내에 베트남어 없음", not VI_CH.search(hd[hd.find('id="mailTour"'):hd.find('id="mailTour"') + 6000]))

# ═══════════════════════ ⑨ 설명서 ═══════════════════════
print("\n⑨ 인쇄용 설명서")
as_("jo")
r = km.get("/mail/help")
h = r.text
check("설명서 200 · 한국어 제목", r.status_code == 200 and "HAIST WORKS 메일 설명서" in h, r.status_code)
check("인쇄 때 메뉴·도구 줄·인쇄 단추 숨김 · A4", "@media print" in h and ".mail-app-fixed, .mail-help, .mail-theme-pop, .mtour, .hp-bar" in h and "size:A4" in h)
check("구역은 쪽 사이에서 안 잘림", "page-break-inside:avoid" in h)
check("화면용 감싸개에 폭 상한·가운데 정렬 없음", not re.search(r"\.hp(-doc)?\{[^}]*(max-width|margin:\s*0 auto)", h))
check("맡기기 구역은 시험 명단이 아니면 안 실림", 'id="sec-dlg"' not in h and 'id="sec-write"' in h)
check("설명서에 베트남어 없음", not VI_CH.search(h) and "lang=vi" not in h, VI_CH.findall(h)[:5])
as_("vn")
hv = km.get("/mail/help").text
check("사용자 말이 vi 여도 한국어만(베트남어 보류)", "HAIST WORKS 메일 설명서" in hv and not VI_CH.search(hv))
as_("ceo")
check("시험 명단(대표)에겐 맡기기 구역 실림", 'id="sec-dlg"' in km.get("/mail/help").text)
check("WORKS 주소로 열어도 200", k.get("/mail/help").status_code == 200)

# ═══════════════════════ 단추 이름 = 화면 글자 ═══════════════════════
print("\n설명서·안내의 단추 이름 = 실제 템플릿 글자")
TPL = os.path.join(ROOT, "app", "templates")
hay = []
for dp, _dn, fs in os.walk(TPL):
    for fn in fs:
        if fn.endswith(".html") and fn not in ("mail_help_print.html", "mail_tour.html"):
            hay.append(io.open(os.path.join(dp, fn), encoding="utf-8", errors="replace").read())
HAY = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", "\n".join(hay)))


def on_screen(lbl):
    return re.sub(r"\s+", "", lbl) in HAY


labs = mg.manual_labels()
miss = [x for x in labs if not on_screen(x)]
check("설명서 단추 이름 %d개 모두 화면에 있음" % len(labs), not miss, miss)
tour = io.open(os.path.join(TPL, "_v5_partials", "mail_tour.html"), encoding="utf-8").read()
_cards = tour[tour.find("var CARDS="):tour.find("];", tour.find("var CARDS="))]   # 안내 장 글만(안내 창 자기 단추는 빼고)
tl = re.findall(r"「([^」]+)」", _cards)
miss2 = [x for x in tl if not on_screen(x)]
check("처음 안내 단추 이름 %d개 모두 화면에 있음" % len(tl), not miss2, miss2)
check("일부러 틀린 이름은 잡힘(검사가 살아 있음)", not on_screen("✏️ 새 편지") and not on_screen("📮 답장하기"))

# ═══════════════════════ 그 밖 ═══════════════════════
print("\n그 밖")
for p in ("app/mail_guide.py", "app/main.py"):
    try:
        ast.parse(io.open(os.path.join(ROOT, p), encoding="utf-8").read(), feature_version=(3, 8))
        ok = True
    except SyntaxError as e:
        ok = e
    check("파이썬 3.8 문법: %s" % p, ok is True, ok)
for p in ("app/mail_guide.py", "app/templates/mail_help_print.html", "app/templates/mail_company_sig.html", "app/templates/_v5_partials/mail_tour.html"):
    src = io.open(os.path.join(ROOT, p), encoding="utf-8").read()
    check("베트남어 글 없음: %s" % p, not VI_CH.search(src), VI_CH.findall(src)[:5])
as_("jo")
tl_ = k.get("/mail/tools").text
check("⚙ 설정·정리: 직원에겐 「🖨 설명서(인쇄용)」 줄 · 회사 서명 틀 줄 없음", "설명서(인쇄용)" in tl_ and "/mail/signature/company" not in tl_)
as_("ceo")
check("⚙ 설정·정리: 관리자에겐 「회사 서명 틀」 줄", "/mail/signature/company" in k.get("/mail/tools").text)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
