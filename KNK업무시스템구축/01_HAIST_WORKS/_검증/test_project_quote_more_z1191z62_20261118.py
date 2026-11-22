# -*- coding: utf-8 -*-
"""z1191z62 시험(z61 바탕) (대표 2026-11-18 「이화면에서 견적서 등록을 할수있게 … 견적서에 기록되어있는 기본적인 정보들이 자동으로 작성」)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z62-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z62_")
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



# ─────────────── z1191z62 ───────────────
#  대표 11-18: ① 「수정화면에서는 견적서 등록하는곳이 없는데」 → 수정 두 곳(금액·수량은 참고) · [저장] 때 보관 · 상세 「＋ 견적서 올리기」
#             ② 「암호가 걸려있는 엑셀을 넣으면 업로드 화면에서 비밀번호를 입력하고 등록」
import types  # noqa: E402
PW_OK = "Kz-9!암호"


def xlsx_bytes(rows):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active
    for r in rows:
        ws.append(r)
    b = io.BytesIO(); wb.save(b); return b.getvalue()


PLAIN = xlsx_bytes([["견 적 서"], ["업 체 명", "가상전자"], ["품 명", "가상 패널 검사기"], ["수량", 1, "단가", 5000000]])
LOCKED = QR._OLE + b"FAKE-ENCRYPTED-PAYLOAD" * 20   # 암호 걸린 xlsx = OLE 통(가짜 내용)


class FakeOffice:   # msoffcrypto 대역 — 맞는 비밀번호면 PLAIN 을 내놓는다
    def __init__(self, fh):
        self.raw = fh.read(); self.pw = None

    def is_encrypted(self):
        return self.raw[:8] == QR._OLE

    def load_key(self, password=None):
        self.pw = password

    def decrypt(self, out):
        if self.pw != PW_OK:
            raise ValueError("bad key")
        out.write(PLAIN)


FAKE = types.ModuleType("msoffcrypto"); FAKE.OfficeFile = FakeOffice
sys.modules["msoffcrypto"] = FAKE
XL_RESP = dict(TOUCH, customer="가상전자", item_name="가상 패널 검사기", contact_name="", contact_title="", unit_price=5000000, amount=5000000)

TOK1 = ""
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



print("§1 암호 걸린 엑셀 — 비밀번호 칸 → 틀림 → 맞음")
as_(UA); CALLS.clear()
check(QR.office_locked(LOCKED, ".xlsx") and not QR.office_locked(PLAIN, ".xlsx"), "OLE 통 xlsx = 암호 · 보통 xlsx(zip) = 아님")
j = upload(name="가상 견적서(암호).xlsx", raw=LOCKED, resp=XL_RESP).json()
check(j["ok"] and j["need_password"] and not j["bad_password"] and not j["read_ok"] and j["tok"] and "비밀번호" in j["message"] and not CALLS,
      "암호 엑셀 올리면 「비밀번호를 넣으면 풀어서 읽습니다」 · 파일은 받아 둠(표지) · AI 안 부름", j.get("message"))
TOKX = j["tok"]
r = q(cl.post, "/api/project-quote/reread", data={"tok": TOKX, "password": "틀린비번"}); jx = r.json()
check(jx["ok"] and jx["need_password"] and jx["bad_password"] and "맞지 않습니다" in jx["message"] and not CALLS, "틀린 비밀번호 → 「맞지 않습니다」 · 다시 칸", jx.get("message"))
jx = q(cl.post, "/api/project-quote/reread", data={"tok": TOKX, "password": PW_OK}).json()
check(jx["ok"] and jx["read_ok"] and not jx["need_password"] and jx["fields"]["item_name"] == "가상 패널 검사기" and jx["cust"]["id"] == CU,
      "맞는 비밀번호 → 풀어서 읽음 · 품명·고객사", jx.get("message"))
check(CALLS and CALLS[-1][0] == "chat" and "가상 패널 검사기" in CALLS[-1][2] and PW_OK not in CALLS[-1][2],
      "AI 에는 푼 내용만(엑셀은 글자) · 비밀번호는 안 보냄")
rw = row(TOKX)
check(open(os.path.join(TMP, "project_quotes", rw["stored"]), "rb").read() == LOCKED, "보관 파일은 암호 걸린 원본 그대로(푼 파일로 바꾸지 않음)")
check(json.loads(rw["read_json"]).get("locked") is True, "풀어 읽은 뒤에도 「암호 파일」 표시는 남음(상세 🔒)")
dump = []
with D.db_session() as c:
    for (tn,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        try:
            for rr in c.execute('SELECT * FROM "%s"' % tn).fetchall():
                dump.append(" ".join(str(v) for v in tuple(rr)))
        except Exception:
            pass
check(not any(PW_OK in x for x in dump), "비밀번호는 DB 어디에도 없음(표 전부 훑음)")
as_(UD)
check(not q(cl.post, "/api/project-quote/reread", data={"tok": TOKX, "password": PW_OK}).json()["ok"], "남(라영업)은 내 견적서를 비밀번호로 못 읽음")
as_(UA)
check(not q(cl.post, "/api/project-quote/reread", data={"tok": TOKX, "password": ""}).json()["ok"], "비밀번호 빈칸 → 「넣어 주세요」")
sys.modules["msoffcrypto"] = None   # 서버에 도구가 아직 없을 때
jn = upload(name="b.xlsx", raw=LOCKED, resp=XL_RESP).json()
jn2 = q(cl.post, "/api/project-quote/reread", data={"tok": jn["tok"], "password": PW_OK}).json()
check(jn["need_password"] and jn2["ok"] and not jn2["read_ok"] and not jn2["need_password"] and "도구가 서버에 아직 없어" in jn2["message"] and row(jn["tok"]),
      "도구 없으면 「아직 못 읽음 — 파일은 그대로 보관」(오류 아님)", jn2.get("message"))
sys.modules["msoffcrypto"] = FAKE
jp = upload(name="c.xlsx", raw=PLAIN, resp=XL_RESP).json()
check(jp["read_ok"] and not jp["need_password"], "암호 없는 엑셀은 바로 읽음")

print("§2 암호 걸린 PDF")
_pl = QR.pdf_locked
QR.pdf_locked = lambda raw, password="": password != "pdfpw"
j = upload(name="잠긴.pdf", raw=b"%PDF-1.7 locked", resp=TOUCH).json()
check(j["need_password"] and "PDF" in j["message"], "암호 PDF → 비밀번호 칸", j.get("message"))
jb = q(cl.post, "/api/project-quote/reread", data={"tok": j["tok"], "password": "x"}).json()
jg = q(cl.post, "/api/project-quote/reread", data={"tok": j["tok"], "password": "pdfpw"}).json()
check(jb["bad_password"] and not jg["need_password"], "틀리면 다시 · 맞으면 통과(그다음 읽기로)", jg.get("message"))
QR.pdf_locked = _pl

print("§3 수정 화면 두 곳 · [저장] 때 보관")
as_(UA)
P9, _ = reg(model="TP-90", quote_tok="")
hq = q(cl.get, "/projects/%d/quick-edit" % P9).text
check('id="z61q" class="z61q" data-mode="edit"' in hq and "[저장]하면 이 프로젝트에 견적서로 보관" in hq and "금액·수량은 수주 카드에서" in hq,
      "간편 수정 화면에 띠 · 「[저장]하면 보관 · 금액·수량은 수주 카드에서」")
he = q(cl.get, "/projects/%d/edit" % P9).text
i_unl = he.find('id="pfUnlockedBanner"'); i_b = he.find('id="z61q"'); i_f = he.find('<form method="post" action="/projects/%d/edit"' % P9); i_fe = he.find("</form>", i_f)
check(i_f < i_unl < i_b < i_fe and 'data-mode="edit"' in he, "고급 편집: 잠금 해제 띠 바로 아래(양식 안)")
check(he.count('id="z61q"') == 1 and hq.count('id="z61q"') == 1 and hq.count("function z61init") == 1, "띠·스크립트는 한 벌씩")
jt = upload(name="수정용 견적서.png").json()
f = {"unlock_verified": "1", "name": "TSP", "customer_name": "가상전자(주)", "customer_id": str(CU), "model": "TP-90", "equip_name": "TOUCH 타공검사기",
     "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중", "quote_tok": jt["tok"], "quotation_date": "2026-11-13"}
r = q(cl.post, "/projects/%d/edit" % P9, data=f)
with D.db_session() as c:
    h = [dict(x) for x in c.execute("SELECT field, new_value, note FROM project_history WHERE project_id=? AND field='견적서 파일'", (P9,)).fetchall()]
check(r.status_code == 303 and r.headers.get("location", "").endswith("/project/%d" % P9) and row(jt["tok"])["project_id"] == P9
      and len(h) == 1 and "z1191z62 수정 화면" in h[0]["note"], "수정 [저장] → 견적서가 그 프로젝트에 붙음 · 이력 「수정 화면」", (r.headers.get("location"), h))
jt2 = upload(name="안 저장.png").json()
r = q(cl.post, "/projects/%d/edit" % P9, data=dict(f, unlock_verified="", quote_tok=jt2["tok"]))
check("unlock_required" in r.headers.get("location", "") and row(jt2["tok"])["project_id"] is None, "잠금 해제 안 하고 저장(거절)되면 안 붙음")

print("§4 상세 「＋ 견적서 올리기」")
as_(UA)
hd = q(cl.get, "/project/%d" % P9).text
check('class="z62-up"' in hd and "＋ 견적서 엑셀 올리기" in hd and 'data-pid="%d"' % P9 in hd, "상세 「견적서」 칸에 「＋ 견적서 엑셀 올리기」(금액·등록 권한자 · z1191z76 이름)")
CALLS.clear()
r = q(cl.post, "/api/project-quote/attach/%d" % P9, files={"file": ("나중에 받은 견적서.pdf", b"%PDF-1.4 x", "application/pdf")})
with D.db_session() as c:
    rr = dict(c.execute("SELECT * FROM project_quote_files WHERE project_id=? ORDER BY id DESC LIMIT 1", (P9,)).fetchone())
    hh = c.execute("SELECT COUNT(*) FROM project_history WHERE project_id=? AND note LIKE 'z1191z62 상세%'", (P9,)).fetchone()[0]
check(r.json()["ok"] and rr["orig_name"] == "나중에 받은 견적서.pdf" and rr["attached_at"] and rr["by_id"] == UA["id"] and hh == 1 and not CALLS,
      "올리면 바로 보관(AI·칸 채우기 없음) · 이력 「상세 화면」", rr.get("orig_name"))
hd = q(cl.get, "/project/%d" % P9).text
# z1191z105 (대표 11-22 「1,2 추천대로」): 대표 견적 자리 1장 — 상세에서 올리면 수정 때 올린 것을 바꿈(예전 것 지움)
check(hd.count('class="z61-qf"') == 1 and "나중에 받은 견적서.pdf" in hd and r.json().get("replaced") == 1,
      "상세에서 올리면 대표 견적 자리 1장으로 바꿈(z1191z105 · 수정 때 올린 것은 지움)", (hd.count('class="z61-qf"'), r.json()))
check('<dt class="fullw">견적서</dt>' in hd and "나중에 받은 견적서.pdf</a>" in hd[hd.find('<dt class="fullw">견적서</dt>'):],
      "프로젝트 정보 「견적서」 칸(한 줄 전체)에 그 견적서")
check(hd.count('class="z62-view"') == 1 and 'data-kind="pdf"' in hd, "줄에 「👁 보기」(PDF → 미리보기 창)")
check(q(cl.post, "/api/project-quote/attach/%d" % P9, files={"file": ("x.docx", b"abc", "application/octet-stream")}).json()["ok"] is False, "docx 거절")
check(q(cl.post, "/api/project-quote/attach/999999", files={"file": ("x.pdf", b"%PDF", "application/pdf")}).status_code == 404, "없는 프로젝트 404")
as_(UC)
check(q(cl.post, "/api/project-quote/attach/%d" % P9, files={"file": ("x.pdf", b"%PDF", "application/pdf")}).status_code == 403
      and 'class="z62-up"' not in q(cl.get, "/project/%d" % P9).text, "금액·등록 권한 없는 다물류 → 단추 없음 · 403")

print()
print("결과: ✅ %d · ❌ %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
