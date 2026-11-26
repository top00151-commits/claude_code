# -*- coding: utf-8 -*-
"""z1191z61 시험 (대표 2026-11-18 「이화면에서 견적서 등록을 할수있게 … 견적서에 기록되어있는 기본적인 정보들이 자동으로 작성」)
  대표 결정: 품명→장비명 · 모델명은 MODEL 칸 있을 때만 · 파일은 프로젝트에 첨부로 보관 · AI 로 읽기
  ① 값 정리(숫자 쪼개짐·통화·날짜·호칭) · 경고(받은 견적서 · 수량×단가≠합계)
  ② /api/project-quote/read — 저장 위치·표·고객사 맞추기(하나/여럿/없음)·권한·금액 권한·확장자·크기·AI 없음
  ③ [등록] 하면 그 프로젝트에 붙음 · 남의 것은 안 붙음 · 변경 이력 · 상세에 📄 링크(금액 권한자만) · 파일 열기 권한
  ④ 3일 지난 미등록 파일 정리 · 다시 열었을 때 상태 · 등록 화면에 띠(수정 화면엔 없음)
  임시 DB · TestClient · AI 는 가짜(실제 호출 없음) · 운영 아님
"""
import contextlib, io, json, os, re, sys, tempfile
from datetime import date, timedelta, datetime, timezone
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z61-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z61_")
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


FUT = (date.today() + timedelta(days=20)).isoformat()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT"), ("rank", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    for col in ("alias", "sub_biz_no"):
        if col not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
            c.execute("ALTER TABLE customers ADD COLUMN %s TEXT" % col)
    TEAM = ins(c, "teams", {"name": "가상검사기팀", "code": "T61", "entity": "KOR", "display_order": 1})
    for nm, emp, vs, us in (("가영업", "T961", 1, 1), ("나등록", "T962", 0, 1), ("다물류", "T963", 0, 0), ("라영업", "T964", 1, 1)):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics, rank, team_id) "
                  "VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', 1, 1, ?, ?, 1, 1, '프로', ?)", (nm, emp, emp, vs, us, TEAM))
    UA = dict(c.execute("SELECT * FROM users WHERE employee_no='T961'").fetchone())
    UB = dict(c.execute("SELECT * FROM users WHERE employee_no='T962'").fetchone())
    UC = dict(c.execute("SELECT * FROM users WHERE employee_no='T963'").fetchone())
    UD = dict(c.execute("SELECT * FROM users WHERE employee_no='T964'").fetchone())
    CU = ins(c, "customers", {"name": "가상전자(주)", "alias": "가상전자"})
    CM1 = ins(c, "customers", {"name": "삼가상기 수원", "sub_biz_no": "0001"})
    CM2 = ins(c, "customers", {"name": "삼가상기 부산", "sub_biz_no": "0002"})

import app.main as M  # noqa: E402
import app.ai_client as AI  # noqa: E402
import app.quote_reader as QR  # noqa: E402
import app.sso_client as SSO  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
CUR = {"u": UA}
M.get_user = lambda request: CUR["u"]
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
SSO.notify_via_messenger = lambda *a, **k: {"ok": True, "sent": 0}   # 이음 보내기 막기(시험)
CALLS = []
AIRESP = {"v": None, "avail": True}
AI.ai_available = lambda: AIRESP["avail"]
AI.ai_vision = lambda img, mime, prompt, **k: (CALLS.append(("vision", len(img), prompt)) or (True, AIRESP["v"]))
AI.ai_chat = lambda prompt, **k: (CALLS.append(("chat", 0, prompt)) or (True, AIRESP["v"]))
cl = TestClient(M.app, follow_redirects=False)
# z1191z76 (대표 11-19 「견적서 등록은 무조건 엑셀파일만」): 운영은 이제 엑셀만 받는다. 이 시험은 읽기·보관·빼기를 보려고
#   예전 파일 종류(PDF·사진)를 그대로 쓴다 — 엑셀만 규칙은 test_project_quote_excel_only_z1191z76_20261119.py 에서 본다.
M._Z76_XL_EXTS = M._qr61.EXTS
M._z76_is_excel = lambda name, raw: True
M._Z76_XL_MSG = "PDF·엑셀(xlsx·xls)·사진(png·jpg) 파일만 올릴 수 있습니다."
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


def as_(u):
    CUR["u"] = u


def png_bytes():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (60, 40), (255, 255, 255)).save(b, format="PNG"); return b.getvalue()


PNG = png_bytes()
TOUCH = {"supplier": "주식회사 케이엔케이", "customer": "가상전자", "customer_dept": "", "contact_name": "차주송 님", "contact_title": "팀장",
         "supplier_pic": "", "item_name": "TOUCH 타공검사기", "model_code": "", "qty": 1, "unit": "SET", "currency": "₩",
         "unit_price": "11,300,000", "amount": 11300000, "quote_date": "2026. 11. 13.", "quote_no": "",
         "delivery_terms": "발주서 접수 후 4주 소요", "valid_terms": "발행일로부터 1개월", "payment_terms": "납품일로 부터 30일 이내"}


def upload(name="TOUCH 센서검사기 견적서_261113.png", raw=PNG, resp=TOUCH):
    AIRESP["v"] = json.dumps(resp, ensure_ascii=False) if isinstance(resp, dict) else resp
    return q(cl.post, "/api/project-quote/read", files={"file": (name, raw, "application/octet-stream")})


def row(tok):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM project_quote_files WHERE tok=?", (tok,)).fetchone()
        return dict(r) if r else None


print("§1 값 정리 · 경고")
check(QR.to_num("₩ 1 3,000,000") == 13000000 and QR.to_num("11,300,000") == 11300000 and QR.to_num(1730000) == 1730000 and QR.to_num("abc") is None,
      "숫자: 「₩ 1 3,000,000」→13,000,000 · 쉼표 · 숫자 · 글자는 없음")
check(QR.to_num("1.840.000") is None, "베트남식 「1.840.000」은 짐작하지 않음(없음)")
check(QR.norm_currency("₩") == "KRW" and QR.norm_currency("\\") == "KRW" and QR.norm_currency("VND") == "VND" and QR.norm_currency("₫") == "VND" and QR.norm_currency("$") == "USD" and QR.norm_currency("?") == "",
      "통화: ₩·\\→KRW · VND·₫→VND · $→USD · 모르면 빈칸")
check(QR.norm_date("2026. 11. 13.") == "2026-11-13" and QR.norm_date("2026년 11월 03일") == "2026-11-03" and QR.norm_date("2026-11-11") == "2026-11-11" and QR.norm_date("2026. 13. 40") == "",
      "날짜: 「2026. 11. 13.」·「2026년 11월 03일」→YYYY-MM-DD · 틀린 날짜는 빈칸")
n = QR.normalize(TOUCH)
check(n["contact_name"] == "차주송" and n["qty"] == 1 and n["unit_price"] == 11300000 and n["currency"] == "KRW" and n["quote_date"] == "2026-11-13",
      "정리: 「차주송 님」→차주송 · 수량 1 · 단가 11,300,000 · KRW · 2026-11-13", n)
check(QR.normalize({"qty": 1.5})["qty"] is None and QR.normalize({"qty": "2"})["qty"] == 2, "수량은 정수만(1.5 는 비움)")
check(QR.checks(n) == [], "KNK 가 낸 견적서 · 1×11,300,000=11,300,000 → 경고 없음", QR.checks(n))
# z1191z160 (대표 11-26 「검토하는 기능을 빼줘 · 사용자들이 등록하는 걸 믿고 진행」): 경고 없음(예전: 공급자·수량×단가·품명 경고)
w = QR.checks(QR.normalize({"supplier": "(주)티케이비앤티", "customer": "(주)케이엔케이", "item_name": "EN13"}))
check(w == [], "z1191z160: 공급자가 다른 회사여도 경고 없음", w)
w = QR.checks(QR.normalize({"supplier": "(주)케이엔케이", "item_name": "Barrel Transfer 자동화 설비", "qty": 2, "unit_price": 70000000, "amount": 150000000}))
check(w == [], "z1191z160: 2×70,000,000 ≠ 150,000,000 이어도 경고 없음", w)
check(QR.checks(QR.normalize({"supplier": "KNK VINA"})) == [], "z1191z160: 품명 못 찾아도 경고 없음")
_qf160 = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "quote_fill.html"), encoding="utf-8").read()
check("j.warnings" not in _qf160, "z1191z160: 「견적서로 채우기」 화면에 ⚠ 경고 줄 그리는 스크립트 없음")
check(QR.is_knk("CÔNG TY TNHH KNK VINA") and QR.is_knk("주식회사 케이엔케이") and not QR.is_knk("시스콘로보틱스"), "KNK 판정: VINA·본사 · 다른 회사 아님")

print("§2 올리기 · 읽기 · 보관")
as_(UA); CALLS.clear()
r = upload(); j = r.json()
check(r.status_code == 200 and j["ok"] and j["read_ok"] and len(j["tok"]) == 24, "가영업이 올리면 읽음 · 표지(tok)", j.get("message"))
f = j["fields"]
check(f["item_name"] == "TOUCH 타공검사기" and f["model_code"] == "" and f["contact_name"] == "차주송" and f["unit_price"] == 11300000 and f["amount"] == 11300000,
      "품명 TOUCH 타공검사기 · 모델 비움 · 담당 차주송 · 단가·금액", f)
check(j["cust"]["id"] == CU and j["cust"]["label"] == "가상전자", "업체명 「가상전자」 → 등록 고객사 하나(가상전자(주))로 맞춤", j["cust"])
check(CALLS and CALLS[0][0] == "vision" and "TOUCH" not in CALLS[0][2] and "MODEL" in CALLS[0][2], "사진은 그림으로 AI 에 · 지시문에 「MODEL 칸 있을 때만」")
rw = row(j["tok"])
fp = os.path.join(TMP, "project_quotes", rw["stored"])
check(rw and rw["project_id"] is None and rw["by_id"] == UA["id"] and rw["orig_name"] == "TOUCH 센서검사기 견적서_261113.png" and rw["size"] == len(PNG) and os.path.isfile(fp),
      "표에 「아직 프로젝트 없음」 · 올린 사람 · 원래 이름 · 파일은 data/project_quotes/YYYYMM/ (공개 uploads 아님)", rw)
check(open(fp, "rb").read() == PNG and json.loads(rw["read_json"])["fields"]["item_name"] == "TOUCH 타공검사기", "파일 그대로 저장 · 읽은 결과도 남김")
TOK1 = j["tok"]

j2 = upload(resp=dict(TOUCH, customer="삼가상기")).json()
check(j2["cust"]["id"] is None and sorted(x["id"] for x in j2["cust"]["cands"]) == sorted([CM1, CM2]) and "[0001]" in j2["cust"]["cands"][0]["label"] + j2["cust"]["cands"][1]["label"],
      "이름이 겹치는 고객사 둘(수원·부산) → 고르지 않고 후보 둘", j2["cust"])
j3 = upload(resp=dict(TOUCH, customer="없는회사")).json()
check(j3["cust"]["id"] is None and j3["cust"]["cands"] == [], "등록 안 된 회사 → 비움(짐작 안 함)", j3["cust"])
j4 = upload(resp=dict(TOUCH, customer="(주)가상전자")).json()
check(j4["cust"]["id"] == CU, "「(주)가상전자」도 같은 회사로(㈜·주식회사 떼고 비교)", j4["cust"])

j5 = upload(name="a.docx").json()
check(not j5["ok"] and "PDF" in j5["message"], "docx → 「PDF·엑셀·사진만」", j5)
_mb = QR.MAX_BYTES; QR.MAX_BYTES = 100
j6 = upload().json(); QR.MAX_BYTES = _mb
check(not j6["ok"] and "20MB" in j6["message"], "너무 크면 거절", j6)
AIRESP["avail"] = False
j7 = upload().json(); AIRESP["avail"] = True
check(j7["ok"] and not j7["read_ok"] and j7["tok"] and "AI" in j7["message"] and row(j7["tok"]), "AI 못 쓰면 읽지는 못해도 파일은 받아 둠(등록 때 보관)", j7.get("message"))
j8 = upload(resp="이건 JSON 아님").json()
check(j8["ok"] and not j8["read_ok"] and "다시" in j8["message"], "AI 답이 엉망이면 「다시 올려 보세요」", j8.get("message"))
j9 = upload(name="가상.pdf", raw=b"%PDF-1.4 broken").json()
check(j9["ok"] and not j9["read_ok"], "깨진 PDF → 읽지 못함 안내(서버 오류 아님)", j9.get("message"))

as_(UC)
r = upload()
check(r.status_code == 403, "등록 권한 없는 다물류 → 403", r.status_code)
as_(UB)
jb = upload().json()
check(jb["ok"] and jb["fields"]["unit_price"] == 11300000, "나등록(등록 권한 = 금액 보기도 함께 · can_view_sales 규칙)도 올림·읽음")
TOKB = jb["tok"]

print("§3 다시 열었을 때 상태")
as_(UA)
s = q(cl.get, "/api/project-quote/" + TOK1).json()
check(s["usable"] and s["name"].startswith("TOUCH"), "올린 사람: 아직 붙일 수 있음 · 이름", s)
as_(UD)
check(q(cl.get, "/api/project-quote/" + TOK1).json()["usable"] is False, "다른 사람(라영업)에겐 안 보임")

print("§4 [등록] 하면 그 프로젝트에 붙음")
as_(UA)
REG = {"quick": "1", "customer_name": "가상전자(주)", "customer_id": str(CU), "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규",
       "status": "진행중", "confirm_now": "1", "order_date": "2026-11-18", "due_date": FUT, "currency": "KRW", "unit_qty": "1", "unit_price": "11,300,000",
       "name": "TSP", "model": "", "equip_name": "TOUCH 타공검사기", "quotation_date": "2026-11-13", "quote_tok": TOK1}


def reg(**kw):
    f = dict(REG); f.update(kw)
    f.setdefault("model", "TP-1")
    r = q(cl.post, "/projects/new", data=f)
    loc = r.headers.get("location", "")
    m = re.search(r"/project/(\d+)", loc)
    return (int(m.group(1)) if m else None), loc


P1, loc = reg(model="TP-61")
check(P1, "등록 됨", loc)
rw = row(TOK1)
check(rw["project_id"] == P1 and rw["attached_at"], "견적서가 그 프로젝트에 붙음", rw)
with D.db_session() as c:
    h = [dict(x) for x in c.execute("SELECT changed_by, field, new_value, note FROM project_history WHERE project_id=? AND field='견적서 파일'", (P1,)).fetchall()]
    qd = c.execute("SELECT quotation_date FROM projects WHERE id=?", (P1,)).fetchone()[0]
check(len(h) == 1 and h[0]["changed_by"] == UA["id"] and h[0]["new_value"].startswith("TOUCH") and "z1191z61" in h[0]["note"],
      "변경 이력 「견적서 파일」 · 올린 사람(가영업 본인)", h)
check(str(qd or "")[:10] == "2026-11-13", "견적일자 → 프로젝트 「견적서」 날짜", qd)
check(q(cl.get, "/api/project-quote/" + TOK1).json()["usable"] is False, "붙은 뒤엔 다시 못 씀(다시 열어도 안 보임)")
P2, _ = reg(model="TP-62", quote_tok=TOK1)
check(P2 and row(TOK1)["project_id"] == P1, "같은 표지로 또 등록해도 앞 프로젝트에 그대로(두 번 안 붙음)")
P3, _ = reg(model="TP-63", quote_tok=TOKB)
with D.db_session() as c:
    nB = c.execute("SELECT COUNT(*) FROM project_quote_files WHERE project_id=?", (P3,)).fetchone()[0]
check(P3 and nB == 0 and row(TOKB)["project_id"] is None, "남(나등록)이 올린 견적서는 내 등록에 안 붙음", nB)

print("§5 상세 화면 · 파일 열기")
as_(UA)
hd = q(cl.get, "/project/%d" % P1).text
m = re.search(r'<a class="z61-qf" href="/projects/%d/quote-files/(\d+)"[^>]*>📄 ([^<]+)</a>' % P1, hd)
check(m and m.group(2).startswith("TOUCH 센서검사기"), "상세 「견적서」 칸에 📄 파일 링크(금액 권한자)", m and m.group(0)[:120])
FID = int(m.group(1)) if m else 0
check("2026-11-13" in hd, "상세 「견적서」 날짜 2026-11-13")
r = q(cl.get, "/projects/%d/quote-files/%d" % (P1, FID))
check(r.status_code == 200 and r.content == PNG and r.headers["content-type"].startswith("image/png") and r.headers["content-disposition"].startswith("inline")
      and "no-store" in r.headers.get("cache-control", ""), "열기 = 원본 그대로 · 그림/PDF 는 브라우저에서 바로 · 저장 안 함(no-store)", dict(r.headers))
r = q(cl.get, "/projects/%d/quote-files/%d" % (P2, FID))
check(r.status_code == 404, "다른 프로젝트 번호로는 못 엶", r.status_code)
as_(UC)
hc = q(cl.get, "/project/%d" % P1).text
check("견적서 파일" in hc, "변경 이력에는 「견적서 파일 → 이름」만 남음(단가 없음 · 파일은 못 엶)")
check('class="z61-qf"' not in hc, "금액 볼 권한 없는 다물류 → 상세에 파일 링크 없음")
check(q(cl.get, "/projects/%d/quote-files/%d" % (P1, FID)).status_code == 403, "금액 볼 권한 없으면 파일도 403")

print("§6 3일 지난 미등록 파일 정리")
as_(UA)
old_tok = upload().json()["tok"]
old = row(old_tok); old_fp = os.path.join(TMP, "project_quotes", old["stored"])
with D.db_session() as c:
    c.execute("UPDATE project_quote_files SET created_at='2026-01-01 09:00' WHERE tok=?", (old_tok,))
    c.execute("UPDATE project_quote_files SET created_at='2026-01-01 09:00' WHERE tok=?", (TOK1,))   # 이미 붙은 건 날짜가 지나도 안 지움
upload()
check(row(old_tok) is None and not os.path.exists(old_fp), "3일 지난 미등록 → 표·파일 지움")
check(row(TOK1) and os.path.isfile(os.path.join(TMP, "project_quotes", row(TOK1)["stored"])), "프로젝트에 붙은 견적서는 날짜가 지나도 그대로")

print("§7 등록 화면 띠")
as_(UA)
hq = q(cl.get, "/projects/quick?biz_div=T").text
check('id="z61q" class="z61q" data-mode="new"' in hq and 'name="quote_tok" id="z61qTok"' in hq and "견적서로 채우기" in hq and 'id="z61qFile"' in hq, "등록 화면에 「📄 견적서로 채우기」 · 숨은 칸 quote_tok")
fi = re.search(r'<input type="file" id="z61qFile"[^>]*>', hq)
check(fi and "name=" not in fi.group(0) and "data-knk-no-dropzone" in fi.group(0), "파일 칸엔 name 없음(등록 때 파일을 또 보내지 않음) · 공용 끌어놓기 제외")
i_band = hq.find('id="z61q"'); i_cover = hq.find('id="qLockCover"'); i_form = hq.find('id="quickForm"'); i_end = hq.find("</form>", i_form)
check(i_form < i_band < i_end, "띠는 양식 안(다른 사람이 잡고 있으면 가림막 아래)")
he = q(cl.get, "/projects/%d/edit" % P1).text
check('id="z61q"' in he and 'data-mode="edit"' in he, "z62 부터 수정 화면(고급 편집)에도 띠 · 수정 모드")

print()
print("결과: ✅ %d · ❌ %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
