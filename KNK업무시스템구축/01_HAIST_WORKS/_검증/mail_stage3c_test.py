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
import _mail_ico; _mail_ico.install()  # noqa: E402  11-28 4단계: 화면의 선 아이콘을 [i:이름] 으로 읽음(그림 문자 대신 · 아이콘 이름까지 확인)
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
                "ALTER TABLE users ADD COLUMN entity TEXT", "ALTER TABLE users ADD COLUMN name_en TEXT",
                "ALTER TABLE users ADD COLUMN name_vi TEXT"):
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
    c.execute("UPDATE users SET name_vi='Trần Thị Hà' WHERE id=9803")   # 이음 메신저 베트남 이름(가짜)
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
# 11-22 대표 「디자이너라면」 새 기본 틀: 「이름 직책 · 부서」 / 영문 / M·T·F / E·W / 회사 · 주소
check("첫 줄 = 「이름 직책 · 부서」(웍스 직원 명단)", lines[0] == "조민혁 과장 · 시험품질팀", lines)
check("본사 = 웍스 회사 정보(회사 이름·주소·전화) 먼저(11-23 주식회사 → (주))", "(주)시험회사 · 경기도 시험시 시험로 1" in lines and "M. 010-3333-4444 · T. 031-000-0000 · F. 031-267-0407" in lines, lines)
check("웍스 회사 정보 팩스가 비면 대표 팩스(031-267-0407 · 대표 11-22)", "F. 031-267-0407" in f["text"], f["text"])
check("토막 빼기 규칙: 값이 빈 토막만 뺌(전화는 남음)", mg.fill("T. {전화} · F. {팩스}", {"tel": "02-1", "fax": ""})["text"] == "T. 02-1")
check("휴대폰·메일 = 직원 명단 · 홈페이지", "M. 010-3333-4444" in f["text"] and "E. t1102@knknara.co.kr · W. www.knknara.com" in lines, lines)
check("영문 이름을 알 수 없으면(명단 칸 없음 · 메일 주소가 이름 꼴 아님) 영문 줄 통째로 빠짐", len(lines) == 4, lines)
check("빈 칸 안내 = 영문 이름(직원 명단) · 회사 정보 칸은 대표번호·팩스·주소로 채워져 안내 없음",
      any(k == "영문이름" for k, _ in f["missing"]) and not any(w == "웍스 회사 정보" for _, w in f["missing"]), f["missing"])
with _db.db_session() as c:
    _vh = mg.values_for(c, U["jo"]["id"], "ko", {}, m.rank_label, "")
    _vv = mg.values_for(c, U["vn"]["id"], "ko", {}, m.rank_label, "")
    _ven = mg.values_for(c, U["jo"]["id"], "en", {}, m.rank_label, "")
check("웍스 회사 정보가 모두 비어도 본사 = 대표 전화 031-8009-0407 · 대표 팩스 031-267-0407 · 본사 주소(대표 11-22)",
      _vh["tel"] == "031-8009-0407" and _vh["fax"] == "031-267-0407" and _vh["address"] == "경기도 화성시 병점구 기산로 87번길 2(기산동)", _vh)
check("베트남 법인 서명엔 본사 대표번호·팩스 안 들어감", _vv["tel"] == "" and _vv["fax"] == "" and _vv["address"] == mg.VN_ADDRESS, _vv)
check("영어 서명: 전화·팩스 = 대표번호 · 영문 주소 = 대표가 준 본사 영문 주소(우편번호 18387)", _ven["tel"] == "031-8009-0407"
      and _ven["address"] == "2, Gisan-ro 87beon-gil, Byeongjeom-gu, Hwaseong-si, Gyeonggi-do, Republic of Korea (18387)", _ven)
with _db.db_session() as _c9:
    _en_def = mg.values_for(_c9, U["jo"]["id"], "en", {"company_name_en": "KNK Co., Ltd."}, m.rank_label, "")["company"]
    _en_own = mg.values_for(_c9, U["jo"]["id"], "en", {"company_name_en": "KNK Test Inc."}, m.rank_label, "")["company"]
check("영어 서명 회사 이름 = 「KNK CO.,LTD」(대표 11-24) · 회사 정보에 다른 영문 이름을 넣으면 그 값",
      _ven["company"] == "KNK CO.,LTD" and _en_def == "KNK CO.,LTD" and _en_own == "KNK Test Inc.", (_ven, _en_def, _en_own))
check("첫 줄 굵게 · 줄바꿈 <br>", f["html"].startswith("<b>조민혁 과장 · 시험품질팀</b><br>"), f["html"][:80])

v, f = sigs("vn")
check("베트남 법인(사번 VN…) → 회사 = KNK VINA Co., Ltd.", v["_corp"] == "vn" and "KNK VINA Co., Ltd." in f["text"], f["text"])
check("베트남 법인 → 본사 주소·전화 안 들어감 · 그 줄 빼고 안내", "경기도" not in f["text"] and "031-000-0000" not in f["text"]
      and "베트남 법인 것은 웍스 회사 정보에 아직 칸이 없어" in mg.missing_note(f["missing"], "vn"), (f["text"], f["missing"]))
check("직책 비면 첫 줄은 「이름 · 부서」(빈칸 한 칸)", f["text"].split("\n")[0] == "쩐티하 · 시험구매팀", f["text"])
check("베트남 법인 → 주소 = 베트남 공장 주소(대표 11-22 서명 · 겹친 부분 뺌)", mg.VN_ADDRESS in f["text"] and f["text"].count("Bắc Ninh") == 1, f["text"])
check("휴대폰 없음 → 「M.」 토막만 빠지고 메일은 남음", "M." not in f["text"] and "E. tvn201@knknara.co.kr" in f["text"], f["text"])

v, f = sigs("odd")
check("이름의 꺾쇠는 HTML 로 안전하게(태그로 안 들어감)", "&lt;b&gt;꺾쇠&lt;/b&gt;" in f["html"] and "<b><b>" not in f["html"], f["html"])
check("부서 없는 사람 → 첫 줄 = 이름만", f["text"].split("\n")[0] == "<b>꺾쇠</b>", f["text"])

v, f = sigs("jo", "en")
# 11-22 영어 틀 = 「{영문이름} · {영문직책}」 다음 줄 「{한국이름} {한국직책} · {부서}」 — 영문 이름을 모르면 영문 줄은 빠지고 한국 이름 줄이 첫 줄
check("영어 틀: 영문 이름 모르면 첫 줄 = 한국 이름 줄 · 회사 영문 이름", f["text"].split("\n")[0] == "조민혁 과장 · 시험품질팀" and "Test Co., Ltd." in f["text"], f["text"])
with _db.db_session() as c:
    _ve = mg.values_for(c, U["jo"]["id"], "en", CO, m.rank_label, "minhyuk.jo@knknara.co.kr")
_fe = mg.fill(mg.DEFAULT["en"], _ve)["text"].split("\n")
check("영어 틀: 첫 줄 영문(Minhyuk Jo · Manager) · 둘째 줄 한국 이름 그대로(영문 되풀이 아님)", _fe[0] == "Minhyuk Jo · Manager" and _fe[1] == "조민혁 과장 · 시험품질팀", _fe)
check("웍스 회사 정보 영문 주소 비면 본사 영문 주소(대표 11-22) · 한국어 주소 섞지 않음", "경기도" not in f["text"] and mg.HQ_ADDRESS_EN in f["text"] and ("주소", "웍스 회사 정보") not in f["missing"], f["text"])
v, f = sigs("ceo", "en")
check("영문 이름이 있으면 영어 틀에 영문 이름", f["text"].startswith("Test Ceo"), f["text"][:40])
check("자리 값이 모두 빈 줄은 통째로 빠짐", mg.fill("A\n{팩스}\nB", {"fax": ""})["text"] == "A\nB")

# ═══════════════════════ ⑧-2 서명 모양 · 보안 문구 (대표 11-22) ═══════════════════════
print("\n⑧-2 서명 모양 · 보안 문구")
import base64 as _b64t
from app import mail_send as _msend
from app import mail_store as _mailbox_t
v, f = sigs("jo")
h = mg.design_html(f["text"], v["_corp"], "ko")
check("맨 위 로고 + 오른쪽 QR = 본문에 품은 그림 둘(data:image/png) · 로고 너비(원본 비율 · 11-28 0단계 mg.SIG_LOGO_W) · QR 56", h.count('src="data:image/png;base64,') == 2 and ('width="%d"' % mg.SIG_LOGO_W) in h
      and 'alt="KNK HAIST Innovation"' in h and 'width="56" height="56" alt="QR www.knknara.com"' in h, h[:200])
check("로고·QR 을 누르면 홈페이지(https://www.knknara.com)", h.count('<a href="https://www.knknara.com" target="_blank"') == 2)
try:
    import cv2 as _cv2
    _qr = _cv2.QRCodeDetector().detectAndDecode(_cv2.imdecode(__import__("numpy").fromfile(os.path.join(ROOT, "static", "mail_sig_qr.png"), dtype="uint8"), 1))[0]
    check("QR 그림을 읽으면 = https://www.knknara.com(대표 11-22)", _qr == "https://www.knknara.com", _qr)
except ImportError:
    print("  (QR 읽기 도구 없음 — 그림 읽기 확인은 건너뜀)")
check("첫 줄 = 굵게 15px · 마지막 줄(회사·주소) = 회색", "font-size:15px;font-weight:bold;color:#111827;line-height:1.5\">조민혁 과장 · 시험품질팀<" in h
      and "color:#6b7280;line-height:1.6\">(주)시험회사 · 경기도 시험시 시험로 1<" in h, h[-1600:-1200])
nko, nen = h.find("이 메일(첨부 파일 포함)은"), h.find("This email, including any attachments")
check("본사 한국어 서명 = 보안 문구 한국어 먼저 · 영어 다음", 0 < nko < nen, (nko, nen))
check("보안 문구 고친 점: 법률 정식 이름 · 첨부 포함 · 손으로 끊은 줄 없음",
      "「부정경쟁방지 및 영업비밀보호에 관한 법률」" in mg.NOTICE["ko"] and "첨부 파일 포함" in mg.NOTICE["ko"] and "\n" not in mg.NOTICE["ko"]
      and "금지됩니다" in mg.NOTICE["ko"] and "본 문서" not in mg.NOTICE["ko"])
check("영어 보안 문구: 받는 사람 여럿 · 대한민국 법 · 첨부 · 중간 빈 줄 없음",
      "addressee(s)" in mg.NOTICE["en"] and "Trade Secret Protection Act of the Republic of Korea" in mg.NOTICE["en"]
      and "including any attachments" in mg.NOTICE["en"] and "\n" not in mg.NOTICE["en"])
v2, f2 = sigs("vn")
h2 = mg.design_html(f2["text"], v2["_corp"], "ko")
check("베트남 법인 서명 = 보안 문구 영어 먼저", 0 < h2.find("This email, including") < h2.find("이 메일(첨부 파일 포함)은"))
v3, f3 = sigs("jo", "en")
h3 = mg.design_html(f3["text"], v3["_corp"], "en")
check("본사 영어 서명 = 보안 문구 영어 먼저", 0 < h3.find("This email, including") < h3.find("이 메일(첨부 파일 포함)은"))
check("이름의 꺾쇠는 서명 모양에서도 글자로(태그 안 됨)", "&lt;b&gt;꺾쇠&lt;/b&gt;" in mg.design_html(sigs("odd")[1]["text"], "kr") and "<b>꺾쇠</b>" not in mg.design_html(sigs("odd")[1]["text"], "kr"))
check("영문 이름 = 메일 주소 이름 부분(jiman.park → Jiman Park) · 꼴이 다르면 빈 값",
      mg.en_name_from_mail("jiman.park@knknara.co.kr") == "Jiman Park" and mg.en_name_from_mail("hyun_lee@x") == "Hyun Lee"
      and mg.en_name_from_mail("knksales@knknara.co.kr") == "" and mg.en_name_from_mail("t1102@knknara.co.kr") == "")
with _db.db_session() as c:
    vv = mg.values_for(c, U["jo"]["id"], "ko", CO, m.rank_label, "minhyuk.jo@knknara.co.kr")
check("영문 줄 = 「Minhyuk Jo · Manager」(과장 → Manager)", mg.fill(mg.DEFAULT["ko"], vv)["text"].split("\n")[1] == "Minhyuk Jo · Manager", mg.fill(mg.DEFAULT["ko"], vv)["text"])
with _db.db_session() as c:
    vv = mg.values_for(c, U["jo"]["id"], "ko", CO, lambda r, l: r, "minhyuk.jo@knknara.co.kr")
check("영어로 못 바꾼 직책(한글 그대로)은 영문 줄에 안 넣음", mg.fill(mg.DEFAULT["ko"], vv)["text"].split("\n")[1] == "Minhyuk Jo", mg.fill(mg.DEFAULT["ko"], vv)["text"])
_san = _mailbox_t.sanitize_html_for_view("<div>" + h + "</div>", 0, [])
check("보낼 때 거르기(위생 처리)를 거쳐도 로고·QR·링크·글자 모양 그대로", _san.count('src="data:image/png;base64,') == 2
      and _san.count('href="https://www.knknara.com"') == 2 and "font-size:15px" in _san)
_html_s, _imgs = _msend._inline_data_images(_san)
check("보낼 때 로고·QR = 인라인 첨부(cid) 둘로 바뀜(받는 쪽에서도 보임)", len(_imgs) == 2 and "data:image" not in _html_s and _html_s.count('src="cid:') == 2, len(_imgs))
# 11-28 0단계: 서명 로고 = 스킬 knk-brand 원본 PNG 그대로(static/img/brand/) — 원본이라 예전 줄인 그림(40KB 아래)보다 큼 → 70KB 아래로 봄
_lg = os.path.join(ROOT, "static", *mg.SIG_LOGO_FILE.split("/"))
_lg_src = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "00_스킬규정", "knk-brand", "assets", "logo", "png", os.path.basename(_lg))
check("서명용 로고 = 스킬 원본 파일 그대로(70KB 아래) · QR 4KB 아래", 0 < os.path.getsize(_lg) < 70000
      and (not os.path.exists(_lg_src) or open(_lg, "rb").read() == open(_lg_src, "rb").read())
      and 0 < os.path.getsize(os.path.join(ROOT, "static", "mail_sig_qr.png")) < 4000)

# ═══════════════════════ ⑧-3 사람마다 회사 서명 · 기본 서명 (대표 11-22) ═══════════════════════
print("\n⑧-3 사람마다 회사 서명 · 기본 서명")
with _db.db_session() as c:
    L_jo, L_vn = mg.sig_langs(c, U["jo"]["id"]), mg.sig_langs(c, U["vn"]["id"])
    c.execute("UPDATE users SET lang='ko' WHERE id=9803")
    L_vk = mg.sig_langs(c, U["vn"]["id"])
    c.execute("UPDATE users SET lang='vi' WHERE id=9803")
check("본사 = 한국어(기본)·영어", L_jo == ["ko", "en"], L_jo)
check("베트남 법인 베트남 사람(이음 쓰는 말 = 베트남어) = 베트남어(기본)·한국어·영어", L_vn == ["vi", "ko", "en"], L_vn)
check("베트남 법인 한국 사람(쓰는 말 = 한국어) = 한국어(기본)·영어", L_vk == ["ko", "en"], L_vk)
v4, f4 = sigs("vn", "vi")
h4 = mg.design_html(f4["text"], v4["_corp"], "vi")
L4 = f4["text"].split("\n")
check("베트남어 서명 첫 줄 = 이음 메신저 베트남 이름 · 둘째 줄 = 한국 이름 · 부서", L4[0] == "Trần Thị Hà" and L4[1] == "쩐티하 · 시험구매팀", L4)
check("베트남어 서명: 회사 = Công ty KNK Vina · 베트남 주소", L4[-1] == "Công ty KNK Vina · " + mg.VN_ADDRESS, L4[-1])
check("베트남어 서명 보안 문구 = 베트남어 먼저 · 영어 다음(한국어 없음)",
      0 < h4.find("Thư điện tử này") < h4.find("This email, including") and "이 메일(첨부 파일 포함)은" not in h4)
v5, f5 = sigs("vn", "ko")
check("베트남 법인 한국어 서명: 회사 = KNK VINA Co., Ltd. · 첫 줄 한국 이름", "KNK VINA Co., Ltd. · " + mg.VN_ADDRESS in f5["text"] and f5["text"].startswith("쩐티하 · 시험구매팀"), f5["text"])
as_("vn")
cpv = k.get("/mail/compose").text
check("베트남 사람 쓰기 화면: 「🏢 회사 서명 (베트남어)」 골라져 있음 · 한국어·영어도 고를 수 있음",
      'value="co-vi" selected>🏢 회사 서명 (베트남어)<' in cpv and 'value="co-ko">' in cpv and 'value="co-en">' in cpv)
mmv = re.search(r'<textarea id="cSigHtml" style="display:none">(.*?)</textarea>', cpv, re.S)
check("새 메일에 들어갈 서명 = 베트남어 회사 서명", mmv and "Trần Thị Hà" in __import__("html").unescape(mmv.group(1)), "")
as_("jo")
cpj = k.get("/mail/compose").text
mmj = re.search(r'<textarea id="cSigHtml" style="display:none">(.*?)</textarea>', cpj, re.S)
check("본사 사람 새 메일 = 한국어 회사 서명이 기본으로 들어감", mmj and "조민혁 과장 · 시험품질팀" in __import__("html").unescape(mmj.group(1))
      and 'value="co-ko" selected>' in cpj, "")
spj = k.get("/mail/signature").text
check("서명 화면: 「✉ 새 메일에 기본으로 넣을 서명」 고르기(회사 기본 = 한국어)", 'id="sigDefSel"' in spj and "회사 기본(🏢 회사 서명 (한국어))" in spj, "")
r = k.post("/mail/signature/default", data={"slot": "co-en"})
cpj2 = k.get("/mail/compose").text
check("기본을 영어로 바꾸면 새 메일에 영어 서명 골라져 있음", r.json().get("ok") and 'value="co-en" selected>' in cpj2 and 'value="co-ko" selected>' not in cpj2)
# 11-22 대표 「서명은 공통 · 보안 문구 무조건」 — 「서명 없음」·개인 서명은 기본으로 못 고름 · 쓰기 화면에도 없음
r = k.post("/mail/signature/default", data={"slot": "none"})
cpj3 = k.get("/mail/compose").text
check("「서명 없음」은 기본으로 못 고름(400) · 쓰기 화면에 「서명 없음」 없음 · 영어 그대로", r.status_code == 400 and 'value="none"' not in cpj3 and 'value="co-en" selected>' in cpj3)
_sel3 = cpj3[cpj3.find('id="cSigSel"'):cpj3.find("</select>", cpj3.find('id="cSigSel"'))]
check("쓰기 화면 서명 고르기 = 회사 서명만(개인 「기본 서명」 없음)", _sel3 and 'value="0"' not in _sel3 and ">기본 서명<" not in _sel3 and 'value="co-ko"' in _sel3, _sel3[:200])
check("모르는 서명 값 → 400", k.post("/mail/signature/default", data={"slot": "co-xx"}).status_code == 400)
r = k.post("/mail/signature/default", data={"slot": "1"})
check("개인 서명은 기본으로 못 고름(400)", r.status_code == 400)
r = k.post("/mail/signature/default", data={"slot": ""})
check("「회사 기본」으로 되돌리기", r.json().get("ok") and 'value="co-ko" selected>' in k.get("/mail/compose").text)
as_("ceo")

# ═══════════════════════ ⑧-4 내 서명 정보(개인 칸만) · 보안 문구 무조건 (대표 11-22) ═══════════════════════
print("\n⑧-4 내 서명 정보 · 보안 문구 무조건")
as_("jo")
sp4 = k.get("/mail/signature").text
check("내 서명 정보 칸 = 이름·직책·부서·영문 이름·영문 직책·휴대폰·메일(본사 = 베트남 이름 칸 없음)",
      all(('name="f_%s"' % x) in sp4 for x in ("name", "rank", "dept", "name_en", "rank_en", "mobile", "email")) and 'name="f_name_vi"' not in sp4)
# 11-22 대표 「자동으로 확인 가능한 건 칸 아래 「자동: …」 말고 입력칸에 채워」
check("자동 값 = 입력칸에 채워 보임(이음 → 웍스 명단 · 휴대폰 010-3333-4444) · 칸 아래 「자동: …」 없음",
      'value="010-3333-4444"' in sp4 and 'value="조민혁"' in sp4 and "자동: 010-3333-4444" not in sp4)
r = k.post("/mail/signature/me", data={"f_mobile": "010-9999-8888", "f_name_en": "Minhyuk Jo", "f_rank": "차장"})
with _db.db_session() as c:
    _v8 = mg.values_for(c, U["jo"]["id"], "ko", CO, m.rank_label, "")
    _p8 = mg.person_values(c, U["jo"]["id"], m.rank_label, "")
check("고친 칸만 서명에 씀(휴대폰·영문 이름·직책) · 나머지는 자동", r.json().get("ok") and _v8["mobile"] == "010-9999-8888" and _v8["name_en"] == "Minhyuk Jo"
      and _v8["rank_ko"] == "차장" and _v8["dept"] == "시험품질팀" and _v8["name_ko"] == "조민혁", _v8)
check("직책을 고치면 영문 직책도 따라감(차장 → 영어)", _v8["rank_en"] and _v8["rank_en"] != "차장" and _v8["rank_en"] == m.rank_label("차장", "en"), _v8["rank_en"])
check("자동 값은 그대로 보관(되돌릴 수 있게)", _p8["auto"]["mobile"] == "010-3333-4444" and _p8["auto"]["rank"] == "과장", _p8["auto"])
with _db.db_session() as c:
    _snapj = c.execute("SELECT phone, rank FROM users WHERE id=?", (U["jo"]["id"],)).fetchone()
check("웍스 직원 명단은 안 바뀜(서명용 값만 따로)", _snapj["phone"] == "010-3333-4444" and _snapj["rank"] == "과장", dict(_snapj))
sp5 = k.get("/mail/signature").text
check("서명 화면: 고친 칸은 노란 칸 · 「✏️ 직접 고친 값 · ↺ 자동 값으로」", 'value="010-9999-8888"' in sp5 and "[i:square-pen] 직접 고친 값" in sp5 and "↺ 자동 값으로" in sp5 and 'data-auto="010-3333-4444"' in sp5)
for bad, why in (({"f_email": "abc"}, "메일 꼴"), ({"f_mobile": "공일공"}, "휴대폰 꼴"), ({"f_name": "<b>x</b>"}, "꺾쇠"), ({"f_dept": "가" * 81}, "80자")):
    check("잘못된 값은 저장 안 함(400) — " + why, k.post("/mail/signature/me", data=bad).status_code == 400)
r = k.post("/mail/signature/me", data={"f_mobile": "", "f_name_en": "", "f_rank": ""})
with _db.db_session() as c:
    _v9 = mg.values_for(c, U["jo"]["id"], "ko", CO, m.rank_label, "")
# 11-22 대표 「칸에 내용을 비우면 없는 걸로 · 부서가 없으면 「김정락 대표이사」」
check("비우면 없음(휴대폰·직책 = 서명에서 뺌)", r.json().get("ok") and _v9["mobile"] == "" and _v9["rank_ko"] == "", _v9)
r = k.post("/mail/signature/me", data={"f_dept": ""})
with _db.db_session() as c:
    _f9 = mg.fill("{이름} {직책} · {부서}", mg.values_for(c, U["jo"]["id"], "ko", CO, m.rank_label, ""))["text"]
check("부서를 비우면 「이름 직책 · 부서」 줄에서 「 · 부서」가 빠짐(예: 김정락 대표이사)", _f9 == "조민혁", _f9)
check("비운 칸은 화면에 「비움 — 서명에 넣지 않음」 · ↺ 자동 값으로", "비움 — 서명에 넣지 않음" in k.get("/mail/signature").text)
with _db.db_session() as c:
    _nt = " ".join(x.get("note", "") for x in mg.company_sigs(c, U["jo"]["id"], CO, m.rank_label, ""))
check("일부러 비운 칸은 「…에 비어 있어 뺐습니다」 안내에 안 나옴(부서)", "부서" not in _nt, _nt)
r = k.post("/mail/signature/me", data={"f_dept": "시험품질팀", "f_mobile": "010-3333-4444", "f_rank": "과장"})
with _db.db_session() as c:
    _ovx = mg.get_overrides(c, U["jo"]["id"])
check("자동 값과 같은 값으로 저장 = 자동을 따름(고친 값 지움 · 이음이 바뀌면 같이 바뀜)", r.json().get("ok") and not any(x in _ovx for x in ("dept", "mobile", "rank")), _ovx)
k.post("/mail/signature/me", data={"f_name_en": ""})
r = k.post("/mail/signature/me", data={"reset": "1", "f_name_en": ""})
with _db.db_session() as c:
    _v9 = mg.values_for(c, U["jo"]["id"], "ko", CO, m.rank_label, "")
    _ovx = mg.get_overrides(c, U["jo"]["id"])
check("「↺ 모두 자동 값으로」 = 고친 값 모두 지움(휴대폰·직책 자동)", r.json().get("ok") and not _ovx and _v9["mobile"] == "010-3333-4444" and _v9["rank_ko"] == "과장", (_ovx, _v9))
as_("vn")
check("베트남 법인 = 「베트남 이름」 칸도 있음", 'name="f_name_vi"' in k.get("/mail/signature").text)
as_("jo")

with _db.db_session() as c:
    b1, h1, a1 = mg.ensure_notice(c, U["jo"]["id"], "안녕하세요", "<div>안녕하세요</div>")
    b2, h2, a2 = mg.ensure_notice(c, U["jo"]["id"], b1, h1)
    q_old = '<div><br></div><div class="knk-quote"><div>보낸 사람: x</div><blockquote>' + mg.notice_html(("ko", "en")) + '</blockquote></div>'
    b3, h3, a3 = mg.ensure_notice(c, U["jo"]["id"], "답장입니다", "<div>답장입니다</div>" + q_old)
    b4, h4, a4 = mg.ensure_notice(c, U["vn"]["id"], "Xin chao", "<div>Xin chao</div>")
    b5, h5, a5 = mg.ensure_notice(c, U["jo"]["id"], "글자만 보내는 메일", "")
check("보안 문구 없는 메일 → 붙임(한국어 먼저 · 영어)", a1 and h1.count('class="knk-notice"') == 1 and h1.find("이 메일(첨부 파일 포함)은") < h1.find("This email, including") and mg.NOTICE["ko"] in b1)
check("이미 붙어 있으면 다시 안 붙임(두 번 안 됨)", not a2 and h2 == h1 and b2 == b1)
check("답장: 인용된 옛 메일에 보안 문구가 있어도 내가 쓴 부분 끝(인용 앞)에 붙임",
      a3 and h3.find('class="knk-notice"') < h3.find('class="knk-quote"') and h3.count("이 메일(첨부 파일 포함)은") == 2)
check("베트남 사람 메일 = 베트남어 먼저 · 영어", a4 and 0 < h4.find("Thư điện tử này") < h4.find("This email, including") and "이 메일(첨부" not in h4)
check("HTML 없는 글자만 메일도 붙임", a5 and h5 == "" and b5.startswith("글자만 보내는 메일") and mg.NOTICE["ko"] in b5)
with _db.db_session() as c:
    _cs = [x for x in mg.company_sigs(c, U["jo"]["id"], CO, m.rank_label, "")]
    _bx, _hx, _ax = mg.ensure_notice(c, U["jo"]["id"], "", "<div>본문</div><div class=\"knk-sig\">--<br>" + _cs[0]["body"] + "</div>")
check("회사 서명이 들어간 메일엔 더 안 붙임(서명 속 보안 문구로 충분)", "class=\"knk-notice\"" not in _hx)
src_main = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
_core = src_main[src_main.find("def _mail_send_core("):src_main.find("def _mail_send_core(") + 3000]
check("보내기 한 곳(_mail_send_core = 지금 보내기·예약·자동 응답)에서 보안 문구 확인", "_mguide.ensure_notice(c, u[\"id\"], body, body_html)" in _core and _core.find("ensure_notice") < _core.find("sanitize_html_for_view"))
as_("ceo")

# ═══════════════════════ ⑧ 화면 ═══════════════════════
print("\n⑧ 쓰기 화면 · 서명 화면")
as_("jo")
cp = k.get("/mail/compose").text
check("쓰기 화면 「✍」 고르기에 「🏢 회사 서명 (한국어)」(기본 · 골라져 있음)·「(English)」", 'value="co-ko" selected>🏢 회사 서명 (한국어)<' in cp and 'value="co-en">🏢 회사 서명 (English)<' in cp
      and 'value="co-vi"' not in cp, cp[:0])
mm = re.search(r"window\.CMP_SIGS = (\[.*?\]);", cp)
cs = json.loads(mm.group(1)) if mm else []
check("쓰기 화면 회사 서명 = 새 모양(로고·보안 문구)", any(x.get("slot") == "co-ko" and 'class="knk-co-sig"' in x.get("body", "") and "이 메일(첨부 파일 포함)은" in x.get("body", "") for x in cs), "")
check("고르면 넣을 회사 서명 = 내 정보로 채운 것", any(x.get("slot") == "co-ko" and "조민혁 과장 · 시험품질팀" in x.get("body", "") for x in cs), cs[:1])
sp = k.get("/mail/signature").text
check("서명 화면: 회사 서명 미리 보기 + 「✏️ 내 서명 정보」 + 빈 칸 안내 · 자유 서명 편집기·「회사 서명 쓰기」 없음", "[i:square-pen] 내 서명 정보" in sp and 'id="sBody"' not in sp and "[i:building-2] 회사 서명 쓰기" not in sp and "조민혁 과장 · 시험품질팀" in sp and "에 비어 있어 뺐습니다" in sp and "팩스 —" not in sp, "")
check("직원에겐 「🔧 회사 서명 틀 고치기」 없음", "/mail/signature/company" not in sp)
as_("ceo")
check("대표에겐 「🔧 회사 서명 틀 고치기(관리자)」", "[i:wrench] 회사 서명 틀 고치기(관리자)" in k.get("/mail/signature").text)

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
_vi0 = _mn.find('data-lang="vi"')
_mn_novi = _mn[:_vi0] if _vi0 > 0 else _mn
check("틀 화면: 베트남어는 「베트남어」 서명 칸에만(11-22 대표 베트남어 서명) · 나머지 본문은 없음", _vi0 > 0 and _mn_novi and not VI_CH.search(_mn_novi), VI_CH.findall(_mn_novi)[:5])
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
check("틀을 바꾸면 직원 쓰기 화면 회사 서명도 바뀜", ko2 and "x(주)시험회사 | 조민혁 과장" in ko2[0]["body"] and "☎ 031-000-0000" in ko2[0]["body"], ko2)
as_("adm")
check("빈 틀 저장 → 400(끄기는 따로)", k.post("/mail/signature/company", data={"lang": "en", "body": "  ", "mode": "save"}).status_code == 400)
check("영어 「이 말은 쓰지 않기」", k.post("/mail/signature/company", data={"lang": "en", "mode": "off"}).json().get("ok"))
as_("jo")
cp3 = k.get("/mail/compose").text
_m3 = re.search(r'<textarea id="cSigHtml" style="display:none">(.*?)</textarea>', cp3, re.S)
check("끈 말은 직원 화면에서 빠짐 · 하나만 남으면 고르기 없이 그 서명이 들어감", 'value="co-en"' not in cp3 and _m3 and "knk-co-sig" in __import__("html").unescape(_m3.group(1)))
as_("adm")
check("모르는 말 → 400", k.post("/mail/signature/company", data={"lang": "ja", "body": "{이름}", "mode": "save"}).status_code == 400)
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
check("메일 앱 머리에 처음 안내·「🎓 처음 안내 다시 보기」·「🖨 설명서(인쇄용)」", 'id="mailTour"' in hd and "[i:graduation-cap] 처음 안내 다시 보기" in hd and 'href="/mail/help"' in hd, len(hd))
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
# 11-28 앱 모드 머리에 공용 달력(knk_datepicker)이 들어와 베트남 휴일 이름(자료 · <script> 안)이 실림 → 화면 글만 봄
_txt = lambda x: re.sub(r"(?is)<script\b.*?</script>", "", x)
check("설명서에 베트남어 없음(화면 글)", not VI_CH.search(_txt(h)) and "lang=vi" not in _txt(h), VI_CH.findall(_txt(h))[:5])
as_("vn")
hv = km.get("/mail/help").text
check("사용자 말이 vi 여도 한국어만(베트남어 보류)", "HAIST WORKS 메일 설명서" in hv and not VI_CH.search(_txt(hv)))
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
HAY = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", _mail_ico.ico("\n".join(hay))))   # 11-28 4단계: 화면 원문의 {{ mi('이름') }}·mdI('이름') → [i:이름]


def on_screen(lbl):
    # 설명서·안내 글의 그림 문자는 화면에선 같은 이름의 선 아이콘 — 둘 중 하나로 화면에 있어야 함(아이콘 이름까지 같아야)
    return re.sub(r"\s+", "", lbl) in HAY or re.sub(r"\s+", "", _mail_ico.emo2tok(lbl)) in HAY


labs = mg.manual_labels()
miss = [x for x in labs if not on_screen(x)]
check("설명서 단추 이름 %d개 모두 화면에 있음" % len(labs), not miss, miss)
tour = _mail_ico.ico(io.open(os.path.join(TPL, "_v5_partials", "mail_tour.html"), encoding="utf-8").read())
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
